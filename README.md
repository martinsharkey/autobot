# AUTOBOT — Fully Autonomous AI Agent

AUTOBOT is a fully autonomous, self-healing, self-coding, self-enhancing AI agent that works for you inside VS Code. It combines the best of Roo Code, Kilo Code free LLM discovery, and Hermes Agent self-learning into a single, truly autonomous system.

## Architecture

```
┌─────────────────────────────────────────────┐
│  VS Code Extension (TypeScript)             │
│  - Chat Panel, Memory View, Commands        │
│  ─────────── HTTP / WebSocket ───────────>  │
│  Python Gateway (FastAPI) :8000             │
│  - LLM Router (18+ free providers)          │
│  - Agent Orchestrator                       │
│  - Self-Healer / Self-Coder                 │
│  - Skill Manager                            │
│  - Memory Store                             │
└─────────────────────────────────────────────┘
```

## Quick Start

### 1. Install Python Dependencies

```powershell
python -m pip install -r requirements.txt
```

### 2. Configure Environment

Copy the example environment file and add your API keys:

```powershell
copy .env.example .env
```

Edit `.env` and add at least one provider key (e.g., `OPENROUTER_API_KEY`, `GROQ_API_KEY`, etc.).

### 3. Start the Gateway

```powershell
.\run-gateway.ps1
```

The gateway runs on `http://127.0.0.1:8001` and exposes:
- `GET /v1/health` — health check
- `GET /v1/providers` — list configured providers
- `GET /v1/discover` — discover free LLM providers
- `POST /v1/agent/run` — run an autonomous task
- `GET /v1/agent/status` — check agent status
- `POST /v1/agent/stop` — stop running agent
- `POST /v1/chat/completions` — direct LLM chat
- `GET /v1/memory` — query agent memory (tree view data for VS Code sidebar)
- `GET /v1/skills` — list available skills
- `POST /v1/notifications/telegram/webhook` — Telegram slash command webhook
- `POST /v1/notifications/whatsapp/webhook` — WhatsApp message webhook
- `POST /v1/notifications/send` — send notification via Telegram/WhatsApp
- `GET /v1/mcp/servers` — list MCP server configurations
- `POST /v1/mcp/servers` — add MCP server
- `DELETE /v1/mcp/servers/{name}` — remove MCP server
- `POST /v1/mcp/servers/{name}/connect` — connect to MCP server
- `GET /v1/mcp/tools` — list MCP tools
- `POST /v1/mcp/tools/call` — call an MCP tool

### 4. Use the CLI

```powershell
.\run-autobot.ps1 --goal "Build a hello world API in FastAPI" --mode coder
```

Or start the interactive REPL:

```powershell
.\run-autobot.ps1 --repl
```

### 5. Install the VS Code Extension

1. Open the `autobot-vscode` folder in VS Code
2. Press `F5` to launch an Extension Development Host
3. In the new window, press `Ctrl+Alt+A` to start chatting
4. Use the Command Palette (`Ctrl+Shift+P`) for `AUTOBOT` commands

Or package and install:

```powershell
cd autobot-vscode
npm install
npm run package
code --install-extension autobot-2.0.0.vsix
```

## Features

### Security & IP Protection
- License verification with tamper detection (`autobot/license.py`)
- Baseline hash validation for core files
- Governance audit logging and safety rails
- Tool result verification with confidence scoring

### Fully Autonomous Execution
- Decompose goals into steps
- Execute with tool use (read, write, search, command)
- Self-reflect after major actions
- Adapt strategy based on results

### Self-Healing
- Diagnoses errors when tools/commands fail
- Proposes automatic fixes
- Falls back to alternative providers/tools
- Logs failures for future learning

### Self-Coding
- Agent can read its own codebase
- Proposes improvements to prompts, tools, and logic
- Applies safe, low-risk changes automatically
- Higher-risk changes require review

### Self-Enhancing
- Hermes-style memory consolidation
- Extracts patterns and heuristics from experience
- Learns from successes and failures
- Builds skills over time

### Skill System
- Pluggable skills with trigger keywords
- Agent discovers and chains skills automatically
- Prompts are augmented with active skill context

### Free LLM Routing
- Routes across 19 free/low-cost providers
- Automatic failover on errors
- Health-based load balancing
- GitHub-based provider discovery

### MCP Tools Integration
- Real MCP protocol support via `mcp` Python SDK (stdio, SSE, streamable HTTP)
- Gateway endpoints for MCP server management (`/v1/mcp/servers`, `/v1/mcp/tools`)
- MCP tools appear alongside Hermes tools in the unified tool registry

### Remote Commands & Notifications
- Telegram slash commands (`/status`, `/run`, `/evolve`, `/recover`)
- WhatsApp message webhooks
- Autonomous recovery with completion notifications

### Windows Compatibility
- PATH/.exe resolution shims for `which` logic
- Environment preservation for subprocesses
- Context sanitization with threat-pattern scanning

## Configuration

### Gateway Config (`providers.yaml`)

Add or remove LLM providers. Each provider needs:
- `name`, `base_url`, `completions_path`
- `api_key_env` (matches your `.env` key name)
- `default_model`, `active`, `weight`

### Agent Modes

| Mode | Description |
|------|-------------|
| `architect` | Design systems, plan architecture |
| `coder` | Write, edit, debug code |
| `reflector` | Analyze past actions, extract insights |
| `learner` | Research, build skills, expand knowledge |
| `evolver` | Self-improvement, optimization |

## Development

### Run Tests

```powershell
python -m pytest
```

### Package VS Code Extension

```powershell
cd autobot-vscode
npm run package
```

## Roadmap

- [x] Modular gateway with FastAPI routers
- [x] AgentRuntime single execution interface
- [x] Tool verification and governance layer
- [x] Tool capability graph with per-turn probing
- [x] Hierarchical task delegation (DAG)
- [x] Windows compatibility shims
- [x] Context file sanitization
- [x] Fact-checking and consensus layer
- [x] Semantic RAG retriever with citations
- [x] Safety sandbox with kill-switch
- [x] Telegram/WhatsApp remote commands
- [x] Autonomous recovery protocol
- [x] MT5 connector and risk management
- [x] MCP server integration bridge
- [ ] WebSocket streaming for real-time agent output
- [ ] Vector memory with embeddings
- [ ] Multi-file code editing with AST safety
- [ ] Docker sandboxed execution
- [ ] Voice interaction mode
- [ ] Multi-machine swarm coordination
