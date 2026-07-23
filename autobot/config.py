"""autobot.config - Configuration system.

Inherits from:
- Hermes Agent: config.yaml with deep-merge, profile-aware paths, env-var bridge
- Roo Code: mode definitions with roleDefinition + customInstructions + tool groups
- TradingAgents: TRADINGAGENTS_* env-var overrides with type coercion
"""

from __future__ import annotations

import copy
import json
import os
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

# Thread-local config overrides (from Hermes pattern)
_config_local = threading.local()

# Inherited from Hermes: profile-aware home paths
def get_autobot_home() -> Path:
    home = os.environ.get("AUTOBOT_HOME") or str(Path.home() / ".autobot")
    return Path(home)

def display_autobot_home() -> str:
    return str(get_autobot_home())

# Inherited from TradingAgents: env-var override mapping
_ENV_OVERRIDES = {
    "AUTOBOT_GATEWAY_URL": "gateway_url",
    "AUTOBOT_GATEWAY_KEY": "gateway_key",
    "AUTOBOT_MAX_LOOPS": "max_loops",
    "AUTOBOT_TEMPERATURE": "temperature",
    "AUTOBOT_DEFAULT_MODE": "default_mode",
    "AUTOBOT_DEEP_THINK_MODEL": "deep_think_model",
    "AUTOBOT_QUICK_THINK_MODEL": "quick_think_model",
    "AUTOBOT_MEMORY_PROVIDER": "memory_provider",
    "AUTOBOT_CURATOR_INTERVAL_HOURS": "curator_interval_hours",
}

_BOOL_TRUE = ("true", "1", "yes", "on")
_BOOL_FALSE = ("false", "0", "no", "off")


def _coerce(value: str, reference: Any) -> Any:
    """Coerce env-var string to the type of the existing default value."""
    if isinstance(reference, bool):
        normalized = value.strip().lower()
        if normalized in _BOOL_TRUE:
            return True
        if normalized in _BOOL_FALSE:
            return False
        raise ValueError(f"expected boolean, got {value!r}")
    if isinstance(reference, int) and not isinstance(reference, bool):
        return int(value)
    if isinstance(reference, float):
        return float(value)
    return value


def _apply_env_overrides(config: Dict[str, Any]) -> Dict[str, Any]:
    """Apply AUTOBOT_* env vars to config dict (TradingAgents pattern)."""
    for env_var, key in _ENV_OVERRIDES.items():
        raw = os.environ.get(env_var)
        if raw is None or raw == "":
            continue
        try:
            config[key] = _coerce(raw, config.get(key))
        except ValueError as exc:
            raise ValueError(f"Invalid {env_var}: {exc}") from exc
    return config


@dataclass
class ToolGroup:
    """Inherited from Roo Code: permission-based tool visibility per mode."""
    read: bool = True
    edit: bool = True
    command: bool = True
    web: bool = True
    mcp: bool = False


@dataclass
class MemoryProviderConfig:
    """Inherited from Hermes: pluggable memory backend."""
    provider: str = "builtin"
    kwargs: Dict[str, Any] = field(default_factory=dict)


# Inherited from Roo Code: mode definitions with role + instructions + tool groups
# Combined with Hermes' platform-specific roles
MODE_ROLES: Dict[str, Dict[str, Any]] = {
    "architect": {
        "name": "Architect",
        "roleDefinition": "You are AUTOBOT in Architect mode. Design systems, plan architecture, analyze requirements. Focus on reading and planning.",
        "customInstructions": "Break down complex problems into clear architectural decisions. Consider scalability, maintainability, and best practices.",
        "groups": ToolGroup(read=True, edit=False, command=False, web=True, mcp=False),
        "description": "Design systems and plan architecture",
    },
    "coder": {
        "name": "Coder",
        "roleDefinition": "You are AUTOBOT in Code mode. Write, edit, and debug code. Implement features and fix bugs efficiently.",
        "customInstructions": "Write clean, well-tested code. Follow language conventions. Add type hints and docstrings.",
        "groups": ToolGroup(read=True, edit=True, command=True, web=True, mcp=False),
        "description": "Write, edit, and debug code",
    },
    "ask": {
        "name": "Ask",
        "roleDefinition": "You are AUTOBOT in Ask mode. Provide fast answers, explanations, and documentation. Read-only.",
        "customInstructions": "Be concise and accurate. Cite sources. Explain concepts clearly.",
        "groups": ToolGroup(read=True, edit=False, command=False, web=True, mcp=False),
        "description": "Fast answers and explanations",
    },
    "debug": {
        "name": "Debug",
        "roleDefinition": "You are AUTOBOT in Debug mode. Trace issues, add logs, isolate root causes, and fix bugs.",
        "customInstructions": "Reproduce first. Trace data flow. Isolate the minimum failing case. Add diagnostic output.",
        "groups": ToolGroup(read=True, edit=True, command=True, web=True, mcp=False),
        "description": "Trace issues and fix bugs",
    },
    "trader": {
        "name": "Trader",
        "roleDefinition": "You are AUTOBOT in Trader mode. Analyze markets, research instruments, debate bull/bear cases, and make trading decisions.",
        "customInstructions": "Use multiple analysts. Debate bull and bear cases. Consider risk. Make data-driven decisions.",
        "groups": ToolGroup(read=True, edit=False, command=True, web=True, mcp=False),
        "description": "Analyze markets and trade",
    },
    "reflector": {
        "name": "Reflector",
        "roleDefinition": "You are AUTOBOT in Reflect mode. Analyze past actions, extract learnings, identify improvements. Read-only.",
        "customInstructions": "Look for patterns in successes and failures. Extract heuristics. Suggest process improvements.",
        "groups": ToolGroup(read=True, edit=False, command=False, web=False, mcp=False),
        "description": "Analyze and extract insights",
    },
    "learner": {
        "name": "Learner",
        "roleDefinition": "You are AUTOBOT in Learn mode. Research new topics, extract patterns, build skills, expand knowledge.",
        "customInstructions": "Research thoroughly. Document findings. Create reusable skills from discoveries.",
        "groups": ToolGroup(read=True, edit=True, command=True, web=True, mcp=False),
        "description": "Research and build skills",
    },
    "evolver": {
        "name": "Evolver",
        "roleDefinition": "You are AUTOBOT in Evolve mode. Self-improvement, code rewriting, optimization, capability enhancement.",
        "customInstructions": "Analyze your own code and prompts. Propose improvements. Apply safe changes. Never break existing functionality.",
        "groups": ToolGroup(read=True, edit=True, command=True, web=True, mcp=False),
        "description": "Self-improvement and optimization",
    },
}

# Backward-compatible aliases for modules still importing old names
AGENT_MODES = MODE_ROLES
MODE_GROUPS = {k: v["groups"] for k, v in MODE_ROLES.items()}


class Config:
    """Singleton config inspired by Hermes config.yaml + TradingAgents env overrides."""

    _instance: Optional["Config"] = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._raw: Dict[str, Any] = {}
        self._load_defaults()
        self._load_config_file()
        _apply_env_overrides(self._raw)
        self._apply_local_overrides()
        _config_local.config = self
        self._initialized = True

    def _load_defaults(self):
        self._raw = _apply_env_overrides({
            "gateway_url": "http://127.0.0.1:8000",
            "gateway_key": "changeme",
            "default_mode": "coder",
            "max_loops": 50,
            "temperature": 0.5,
            "max_tokens": 4096,
            "tool_timeout": 30,
            "max_retries": 3,
            "reflection_interval": 5,
            "curator_interval_hours": 168,
            "curator_min_idle_hours": 2,
            "curator_stale_after_days": 30,
            "curator_archive_after_days": 90,
            # Roo Code: tool group defaults
            "default_tool_groups": ["read", "edit", "command", "web"],
            # Hermes: memory provider
            "memory_provider": "builtin",
            # Hermes: context compression
            "context_compression_enabled": True,
            "context_max_tokens": 100_000,
            # TradingAgents: dual-LLM routing
            "deep_think_model": "",
            "quick_think_model": "",
            "llm_provider": "openrouter",
            "backend_url": "",
            "notification_telegram_token": os.getenv("TELEGRAM_BOT_TOKEN", ""),
            "notification_telegram_chat_id": os.getenv("TELEGRAM_CHAT_ID", ""),
            "notification_whatsapp_token": os.getenv("WHATSAPP_TOKEN", ""),
            "notification_whatsapp_phone": os.getenv("WHATSAPP_PHONE", ""),
            "notification_whatsapp_recipient": os.getenv("WHATSAPP_RECIPIENT", "07405260296"),
            "autonomy_completion_phone": os.getenv("AUTONOMY_COMPLETION_PHONE", "07405260296"),
        })

    def _load_config_file(self):
        """Load from ~/.autobot/config.yaml if it exists (Hermes pattern)."""
        config_path = get_autobot_home() / "config.yaml"
        if not config_path.exists():
            return
        try:
            import yaml
            with open(config_path, "r", encoding="utf-8") as f:
                file_config = yaml.safe_load(f) or {}
            # Deep merge (TradingAgents pattern)
            self._deep_merge(self._raw, file_config)
        except Exception:
            pass

    def _apply_local_overrides(self):
        """Apply thread-local overrides (Hermes pattern for test isolation)."""
        local = getattr(_config_local, "config", None)
        if local and hasattr(local, "_local_overrides"):
            self._deep_merge(self._raw, local._local_overrides)

    @staticmethod
    def _deep_merge(base: Dict, override: Dict) -> Dict:
        """Deep merge override into base (TradingAgents pattern)."""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                Config._deep_merge(base[key], value)
            else:
                base[key] = copy.deepcopy(value)
        return base

    def get(self, key: str, default: Any = None) -> Any:
        return self._raw.get(key, default)

    def set(self, key: str, value: Any):
        self._raw[key] = value

    @property
    def raw(self) -> Dict[str, Any]:
        return self._raw

    def to_dict(self) -> Dict[str, Any]:
        return copy.deepcopy(self._raw)


def get_mode_config(mode: str) -> Dict[str, Any]:
    """Get mode config, falling back to default (Roo Code pattern)."""
    return MODE_ROLES.get(mode, MODE_ROLES["coder"])


def get_tool_groups(mode: str) -> ToolGroup:
    """Get allowed tool groups for a mode (Roo Code pattern)."""
    mode_conf = MODE_ROLES.get(mode, MODE_ROLES["coder"])
    return mode_conf.get("groups", ToolGroup())


def is_tool_allowed(mode: str, tool_group: str) -> bool:
    """Check if a tool group is allowed in the current mode."""
    groups = get_tool_groups(mode)
    return getattr(groups, tool_group, False)
