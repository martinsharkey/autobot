"""autobot.prompt - System prompt assembly.

Inherits from:
- Hermes Agent: stable/context/volatile tiers, prompt caching invariants
  (system prompt is byte-stable for conversation lifetime)
- Roo Code: mode-based prompt building with roleDefinition + customInstructions
  + sections (capabilities, rules, tool-use, skills)
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from autobot.config import MODE_ROLES, get_mode_config, get_tool_groups
from autobot.memory import MemoryStore
from autobot.skills import SkillManager


# Hermes stable tier: identity + tool guidance + platform hints (byte-stable)
_STABLE_TIER = """You are AUTOBOT, a fully autonomous AI coding and trading agent.

## Identity
Born from Hermes Agent (NousResearch) + Roo Code + TradingAgents.
You combine:
- Hermes self-learning loop, skills creation, and memory consolidation
- Roo Code mode-based task execution and VS Code integration
- TradingAgents multi-agent graph for market analysis and trading decisions

## Core Principles
1. Think step by step before each action
2. Use the right tool for each sub-task
3. Extract learnings from every experience
4. When something fails, diagnose and recover
5. Signal completion with attempt_completion when fully done
6. Be proactive: if you see an improvement, make it
7. Self-healing: if a command/action fails, try a different approach
8. Preserve conversation cache: do NOT mutate past context or toolsets mid-conversation
9. Strict message role alternation: never two same-role messages in a row

## Response Format
- Provide concise reasoning before tool calls
- When calling tools, include only the tool call
- When done, use attempt_completion with a summary"""


def build_system_prompt(
    mode: str,
    memory: Optional[MemoryStore] = None,
    skills: Optional[SkillManager] = None,
    mode_overrides: Optional[Dict[str, Any]] = None,
    custom_instructions: str = "",
    context_files: Optional[List[str]] = None,
) -> str:
    """Build the complete system prompt (Hermes + Roo pattern).

    Three tiers:
    - stable: identity, principles, format (byte-stable)
    - context: mode role, custom instructions, context files
    - volatile: memory, skills, timestamp (changes per turn)
    """
    parts = [_STABLE_TIER]

    # Context tier: mode + instructions (Hermes stable_context)
    mode_conf = get_mode_config(mode)
    parts.append(f"\n## Mode: {mode}\n")
    parts.append(f"{mode_conf.get('roleDefinition', '')}\n")
    if custom_instructions:
        parts.append(f"{custom_instructions}\n")
    if mode_overrides:
        if mode_overrides.get("customInstructions"):
            parts.append(f"\n{mode_overrides['customInstructions']}\n")

    # Context files (Hermes: AGENTS.md, CLAUDE.md, etc.)
    if context_files:
        for filepath in context_files:
            try:
                content = Path(filepath).read_text(encoding="utf-8", errors="replace")
                parts.append(f"\n## Context File: {filepath}\n{content}\n")
            except Exception:
                pass

    # Volatile tier: memory + skills (changes per turn, NOT part of cached prefix)
    volatile_parts = []

    # Memory context (Hermes MemoryManager pattern)
    if memory:
        recent = memory.get_recent(8)
        important = memory.get_important(3)
        if recent or important:
            volatile_parts.append("## Memory Context\n")
            if important:
                volatile_parts.append("Key Learnings:")
                for e in important:
                    volatile_parts.append(f"  - [{e.category}] {e.content[:300]}")
            if recent:
                volatile_parts.append("\nRecent Context:")
                for e in recent:
                    volatile_parts.append(f"  - [{e.category}] {e.content[:300]}")

    # Skills context (Hermes skills guidance + Roo skills section)
    if skills:
        matched_skills = skills.get_matching("")
        if matched_skills:
            volatile_parts.append("\n## Active Skills\n")
            for skill in matched_skills:
                volatile_parts.append(f"\n### {skill.name}: {skill.description}")
                if skill.prompt_addition:
                    volatile_parts.append(f"\n{skill.prompt_addition}")
                if skill.procedure:
                    volatile_parts.append(f"\n{skill.procedure[:800]}")

    # Timestamp (Hermes volatile)
    volatile_parts.insert(0, f"\n[Timestamp: {datetime.now(timezone.utc).isoformat()}]\n")

    parts.append("\n".join(volatile_parts))

    # Tool usage guidance (Roo Code pattern: capabilities + tool-use section)
    mode_groups = get_tool_groups(mode)
    allowed_tools = [g for g, ok in mode_groups.__dict__.items() if ok]
    parts.append(f"\n## Available Tools\nGroups: {', '.join(allowed_tools)}\n")
    parts.append("Use tools to accomplish the user's goal. Make multiple tool calls in parallel when possible.")

    if mode in ("trader",):
        parts.append("\n## Trading Mode\nUse market data tools, analyze multiple perspectives, debate bull/bear cases, and make data-driven trading decisions.")

    return "\n".join(parts)
