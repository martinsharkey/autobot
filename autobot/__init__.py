"""autobot - Fusion entrypoint.

Real source lives at:
- hermes-repo/
- trading-repo/
- roo-repo/

This module re-exports the actual repo modules through fusion.py.
"""

from autobot.fusion import (  # noqa: F401
    discover_builtin_tools,
    registry,
    get_tool_definitions,
    handle_function_call,
    get_toolset_for_tool,
    check_toolset_requirements,
    check_tool_availability,
    get_all_tool_names,
    coerce_tool_args,
    MemoryManager,
    DEFAULT_AGENT_IDENTITY,
    build_skills_system_prompt,
    build_context_files_prompt,
    build_environment_hints,
    load_soul_md,
    apply_automatic_transitions,
    maybe_run_curator,
    run_curator_review,
    is_enabled,
    is_paused,
    load_state,
    save_state,
    _TRADING_AVAILABLE,
    _TRADING_DEFAULT_CONFIG,
    create_llm_client,
    _TRADING_PROPAGATOR,
    _TRADING_SIGNAL_PROCESSOR,
    _TRADING_STATES_AVAILABLE,
    ROO_MODE_DIR,
)

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
