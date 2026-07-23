"""autobot.fusion - Direct import bridge to Hermes/TradingAgents/Roo repos.

Reads directly from hermes-repo/, trading-repo/, autobot-vscode/src/roo/.
No vendored copies.
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from typing import Any

_AUTOBOT_DIR = Path(__file__).parent
_HERMES_DIR = _AUTOBOT_DIR.parent / "hermes-repo"
_TRADING_DIR = _AUTOBOT_DIR.parent / "trading-repo"
_ROO_DIR = _AUTOBOT_DIR.parent / "autobot-vscode" / "src" / "roo"

for _p in [str(_HERMES_DIR), str(_TRADING_DIR)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)


# ── Hermes core imports ───────────────────────────────────────────────────
from tools.registry import (  # noqa: E402
    discover_builtin_tools,
    registry,
    tool_error,
    tool_result,
    ToolEntry,
    ToolRegistry,
    invalidate_check_fn_cache,
)
from model_tools import (  # noqa: E402
    get_tool_definitions,
    handle_function_call,
    get_toolset_for_tool,
    check_toolset_requirements,
    check_tool_availability,
    get_all_tool_names,
    coerce_tool_args,
)

try:
    from agent.memory_manager import MemoryManager  # noqa: E402
    _HERMES_MEMORY_MANAGER_AVAILABLE = True
except Exception:
    _HERMES_MEMORY_MANAGER_AVAILABLE = False

try:
    from agent.curator import (  # noqa: E402
        apply_automatic_transitions,
        maybe_run_curator,
        run_curator_review,
        is_enabled,
        is_paused,
        load_state,
        save_state,
    )
    _HERMES_CURATOR_AVAILABLE = True
except Exception:
    _HERMES_CURATOR_AVAILABLE = False

try:
    from agent.prompt_builder import (  # noqa: E402
        DEFAULT_AGENT_IDENTITY,
        build_skills_system_prompt,
        build_context_files_prompt,
        build_environment_hints,
        load_soul_md,
    )
    _HERMES_PROMPTS_AVAILABLE = True
except Exception:
    _HERMES_PROMPTS_AVAILABLE = False


# ── TradingAgents direct-file imports ─────────────────────────────────────
_TRADING_BASE = _TRADING_DIR / "tradingagents"


def _ensure_package(dotted: str) -> None:
    parts = dotted.split(".")
    parent = ""
    for part in parts:
        name = f"{parent}.{part}" if parent else part
        if name not in sys.modules:
            mod = types.ModuleType(name)
            pkg_dir = _TRADING_BASE / "/".join(name.split("."))
            if pkg_dir.is_dir():
                mod.__path__ = [str(pkg_dir)]
            sys.modules[name] = mod
        parent = name


def _load_trading_module(dotted_name: str, relpath: str) -> Any:
    _ensure_package(dotted_name)
    path = _TRADING_BASE / relpath
    spec = importlib.util.spec_from_file_location(dotted_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[dotted_name] = mod
    spec.loader.exec_module(mod)
    return mod


def _try(loader):
    try:
        return loader()
    except Exception:
        return None


_TRADING_DEFAULT_CONFIG = _try(lambda: _load_trading_module(
    "tradingagents.default_config", "default_config.py"
).DEFAULT_CONFIG) or {}

create_llm_client = _try(lambda: _load_trading_module(
    "tradingagents.llm_clients", "llm_clients/__init__.py"
).create_llm_client)

_TRADING_PROPAGATOR = _try(lambda: _load_trading_module(
    "tradingagents.graph.propagation", "graph/propagation.py"
).Propagator)

_TRADING_SIGNAL_PROCESSOR = _try(lambda: _load_trading_module(
    "tradingagents.graph.signal_processing", "graph/signal_processing.py"
).SignalProcessor)

_TRADING_STATES_AVAILABLE = _try(lambda: _load_trading_module(
    "tradingagents.agents.utils.agent_states", "agents/utils/agent_states.py"
)) is not None

_TRADING_AVAILABLE = any([
    _TRADING_DEFAULT_CONFIG,
    create_llm_client is not None,
    _TRADING_PROPAGATOR is not None,
    _TRADING_SIGNAL_PROCESSOR is not None,
])


# ── Roo Code references ───────────────────────────────────────────────────
ROO_MODE_DIR = str(_ROO_DIR.resolve())

__version__ = "2.0.0"

__all__ = [
    "discover_builtin_tools",
    "registry",
    "get_tool_definitions",
    "handle_function_call",
    "get_toolset_for_tool",
    "check_toolset_requirements",
    "check_tool_availability",
    "get_all_tool_names",
    "coerce_tool_args",
    "MemoryManager",
    "DEFAULT_AGENT_IDENTITY",
    "build_skills_system_prompt",
    "build_context_files_prompt",
    "build_environment_hints",
    "load_soul_md",
    "apply_automatic_transitions",
    "maybe_run_curator",
    "run_curator_review",
    "is_enabled",
    "is_paused",
    "load_state",
    "save_state",
    "_TRADING_AVAILABLE",
    "_TRADING_DEFAULT_CONFIG",
    "create_llm_client",
    "_TRADING_PROPAGATOR",
    "_TRADING_SIGNAL_PROCESSOR",
    "_TRADING_STATES_AVAILABLE",
    "ROO_MODE_DIR",
]
