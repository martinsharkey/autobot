# Agent Self-Audit - 2026-07-23

Task ID: task_1784809749445_7

Mode: reflector

Response:

**Hermes Agent – Architecture & Reasoning Analysis**

| Aspect | Current State (as described in the *hermes‑agent* skill) |
|--------|--------------------------------------------------------|
| **Core loop** | System‑prompt → LLM → optional tool calls → result → next turn. Context compression runs automatically near the token limit. |
| **Tool orchestration** | Tools are registered in `tools/registry.py` and exposed through *toolsets*. Calls are routed via a JSON‑schema‑driven function‑calling interface. |
| **Memory** | Persistent cross‑session memory (JSON‑backed) plus per‑profile *skills* for procedural knowledge. |
| **Delegation** | `delegate_task` spawns leaf sub‑agents with isolated terminals; limited to one depth and up to three concurrent children. |
| **Profiles & MCP** | Independent profiles keep separate config, skills, auth, and session DB. MCP servers expose remote toolsets. |
| **Compression / checkpoints** | Optional on‑the‑fly context compression and filesystem checkpoints (`checkpoints.enabled`). |
| **Safety layers** | Secret‑redaction, PII‑redaction, approval‑mode for risky shell commands, tool‑requirement checks, and a threat‑pattern scanner for project‑context files. |
| **Gateway & surfaces** | Multi‑platform messaging gateway, desktop app, web dashboard, OpenAI‑compatible proxy. All share the same core loop but have surface‑specific adapters. |

---

## 1️⃣ Enhancement Strategy – **Dynamic Tool‑Capability Graph**

**Problem** – The current tool‑exposure model is static: a toolset either appears or not, based on a simple `check_fn`. When a tool fails at runtime (e.g., missing binary, network outage), the agent still believes it can call it and must resort to “tool‑failed” handling, wasting a turn.

**Solution** – Introduce a *capability graph* that is refreshed at the start of each turn (or on demand) and fed back into the system prompt:

1. **Discovery phase** – Run a lightweight “probe” for every registered tool (e.g., `which <binary>`, a quick API‑key presence test) and produce a **capability map** `{tool_name: {available: bool, reason: str}}`.  
2. **Prompt injection** – Append a short block to the system prompt (`[Tool capabilities: …]`) that the LLM can read.  
3. **LLM‑guided fallback** – Because the map is part of the prompt, the model can decide *before* attempting a call to gracefully avoid a failing tool, or to suggest an alternative (e.g., switch from `browser` → `web`).  
4. **Cache & incremental updates** – Store the map in memory and only recompute when a tool’s environment changes (detected via file‑watch or explicit `/reload‑tools`).  

**Benefits** – Reduces wasted turns, improves reliability on flaky environments (CI runners, remote containers), and lets the model reason about tool availability as a first‑class datum.

---

## 2️⃣ Enhancement Strategy – **Hierarchical, Multi‑Depth Delegation**

**Problem** – `delegate_task` is limited to a single depth and at most three concurrent children. Complex workflows (e.g., a “research‑→‑code‑→‑test‑→‑deploy” pipeline) often need more than three parallel workers and a cascade of sub‑agents that coordinate intermediate artifacts.

**Solution** – Extend the delegation engine to support **configurable depth** and **task‑graph orchestration**:

| Component | Change |
|----------|--------|
| **Sub‑agent model** | Add an `orchestrator` role that can spawn further children, gated by a profile‑level `delegation.max_spawn_depth` (default = 2, user‑adjustable). |
| **Task graph** | Accept a DAG definition (`tasks: [{id, goal, deps: [ids], resources}]`) so children can signal completion and downstream nodes automatically start. |
| **Result stitching** | Provide a built‑in “collector” tool that aggregates child outputs into a single JSON object for the parent LLM. |
| **Resource isolation** | Each node can specify its own `workdir`, `toolset`, and even a different `model/provider`. The engine creates a temporary profile clone for deep branches, preserving the parent’s memory but with isolated tool state. |

**Benefits** – Enables truly *autonomous* multi‑stage pipelines, reduces manual choreography of successive `delegate_task` calls, and scales to larger code‑generation or data‑collection workloads without hitting the three‑child ceiling.

---

## 1️⃣ Urgent Capability Gap – **Robust Windows‑Specific Tooling**

Hermes runs on Windows via MSYS bash, but several critical pain points remain:

- **Process‑level secret redaction fails** on Windows when the BOM or environment variables (`SYSTEMROOT`, `WINDIR`) are stripped, causing sandboxed `execute_code` to crash (`WinError 10106`).  
- **Tool‑failure diagnostics** (`hermes tools list` → “available”) often misreport because the underlying `which` logic uses POSIX `which` that does not resolve Windows executables (`.exe`) correctly.  
- **Interactive PTY spawning** (tmux‑based) is fragile on Windows; many users lack a Unix‑style terminal emulator.

**Immediate fix** – Add a Windows‑aware shim layer:

1. **Path resolution** – Replace `shutil.which` with a wrapper that checks both POSIX and Windows PATHEXT extensions (`.exe`, `.bat`, `.cmd`).  
2. **Env‑preservation** – Ensure the sandbox copy of `SYSTEMROOT` and `COMSPEC` is always injected when `execute_code` launches on Windows.  
3. **Fallback PTY** – Detect missing `tmux` and fall back to `winpty` or plain `conpty` for interactive sub‑agents.

Addressing this gap will dramatically improve reliability for the large user base on Windows (including the current session).

---

## 1️⃣ Safety Concern – **Prompt‑Injection via Project Context Files**

Hermes automatically injects project‑level context (`.hermes.md`, `AGENTS.md`, `CLAUDE.md`) into the system prompt **before** any threat‑pattern scanning. Although the scanner removes obvious injection patterns, it only works on *known* regexes. A malicious actor could craft a context file that:

1. **Encodes a payload using obfuscation** (e.g., base‑64, Unicode homographs) that bypasses the scanner.  
2. **Leverages the “head‑+‑tail” truncation** – insert malicious instructions in the *middle* of a >20 k file that gets stripped, leaving only benign fragments in the prompt while the hidden part is still *read* by the agent (some tools read the raw file, not the truncated version).  
3. **Triggers the “assistant‑turn alternation” rule** – by inserting a simulated assistant message in a context file, the agent could break the enforced user‑assistant alternation, potentially confusing safety‑checks that rely on that invariant.

**Mitigation Recommendations**

- **Sanitize before truncation** – Run the threat‑pattern scanner on the *full* file content **prior** to any head/tail truncation.  
- **Strict size enforcement** – Disallow files > 10 k characters to be automatically loaded; require explicit `/skill` loading for larger docs.  
- **Context‑file validation mode** – Add a `hermes config set security.context_strict true` flag that forces the agent to reject any context file that fails a (configurable) whitelist of allowed directives.  
- **Audit logging** – Log every injection of a project‑context file with its SHA‑256 hash; expose a `/audit‑contexts` command so users can verify which exact file content was incorporated.

Implementing these checks will close a high‑impact attack surface that directly manipulates the system prompt, preserving the core safety invariants around role alternation and tool‑use approval.