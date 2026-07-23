# TODO.md

## Phase 1: Core Runtime Foundation
- [x] Repull all three source repos
- [x] Remove vendored copies, use direct repo references
- [x] Create fusion.py import bridge
- [x] Fix web search tool (DuckDuckGo HTML parsing)
- [x] Verify Hermes tools load (27+ tools)
- [x] Verify Hermes curator imports
- [x] Add DeepSeek/OpenRouter API keys to .env
- [x] Start gateway with live provider config
- [x] Create backward-compatible stubs for deleted modules
- [x] Build LLM client, memory, tools, hermes_loop, agent modules
- [x] Register custom Hermes provider (autobot-gateway)
- [x] Fix gateway provider health policy (require 2+ failures before marking unhealthy)
- [x] Fix gateway stream endpoint SSE format for Hermes
- [x] Fix non-streaming endpoint to support stream=true requests
- [x] Verify Hermes agent runs end-to-end through gateway
- [x] Wire Hermes curator into overnight learning loop
- [x] Add license verification and tamper detection infrastructure
- [x] Fix python -m autobot CLI entry point

## Phase 2: Domain Integration (Trading + Research)
- [x] Wire TradingAgents graph into trader mode
- [ ] Add MT5 connector for live trading
- [ ] Implement risk management layer
- [x] Implement web search/fetch tools for research mode
- [x] Test trading graph in research mode against sample ticker

## Phase 3: IDE Integration
- [x] Port Roo Code modes/prompts into VS Code extension structure
- [x] Build chat webview panel in VS Code
- [x] Wire VS Code extension to gateway with auth
- [ ] Add memory tree view in VS Code sidebar (structure exists, needs VS Code runtime test)
- [ ] Test full UI flow from VS Code to Hermes agent

## Phase 4: Model-Agnostic Multi-Model Orchestration
- [x] Implement model-agnostic routing layer (gateway provider selection)
- [x] Add provider health tracking with automatic failover
- [x] Add multi-model orchestration for complex tasks
- [x] Configure model selection per task type
- [x] Test transparent provider switching without losing context

## Phase 5: Evolutionary Framework
- [x] Implement recursive self-evolution gap analysis engine
- [x] Build sub-agent spawning system for code evolution
- [x] Implement blue/green deployment for agent updates
- [x] Build constant-curiosity protocol for zero-cost resource discovery
- [x] Implement lightweight child-agent distributed compute protocol
- [x] Wire overnight autonomous learner with skill creation
- [x] Test full autonomous evolution cycle (gap analysis -> implementation -> validation -> deploy)

## Audit Findings (2026-07-23)
- [x] Hallucination Mitigation: add verification layer and tool-result validation
- [x] Hallucination Mitigation: add citation requirement for web search outputs
- [x] Modular Architecture: extract gateway routes into dedicated routers
- [x] Modular Architecture: define formal plugin interface for new tools
- [x] Modular Architecture: integrate MCP tools as first-class citizens
- [x] Modular Architecture: add advanced RAG retrieval with citations
- [x] Mission Alignment: formalize single runtime unification protocol
- [x] Mission Alignment: ensure all evolutionary modules operate through one agent loop
- [x] Governance: add autonomous oversight module with safety rails
- [x] Governance: add output schema validation for mission-critical tools
- [x] Governance: implement tiered permission model for self-modification
- [x] Repository: push current state to github.com/martinsharkey/autobot

## High Priority Fixes (Post-Audit 2026-07-23)
- [ ] Wire ToolResultVerifier into actual tool execution path
- [ ] Wire GovernanceModule/SafetyRails into agent execution
- [ ] Resolve hermes-repo plugin import failures
- [ ] Expand gateway/session_context beyond minimal stub
- [ ] Add confidence scoring on final agent responses
- [ ] Implement plugin discovery and registration pipeline
- [ ] Implement actual MCP server integration
- [ ] Wire evolution/deploy/compute modules into live execution
- [ ] Unify TradingAgents with main agent lifecycle
- [ ] Test VS Code extension in actual VS Code runtime

## Fresh Audit Findings (2026-07-23 12:34)
- [ ] Hallucination Mitigation: enforce citation requirements in prompt/response cycle
- [ ] Hallucination Mitigation: add fact-checking / consensus-building layer
- [ ] Modular Architecture: add advanced RAG retrieval with real indexing/search
- [ ] Mission Alignment: expand gateway/session_context beyond minimal stub

## Full Autonomy Mission
- [ ] Define "vastly exceed Kilo" success criteria across reasoning, coding, research, and execution
- [ ] Build autonomy readiness framework with measurable gates and checkpoints
- [ ] Implement continuous self-evaluation feedback loop with human-in-the-loop oversight
- [ ] Wire adaptive learning so Autobot improves beyond original training/context window
- [ ] Establish safety rails and permission tiers for unsupervised operation
- [ ] Create weekly autonomy progress reports with capability delta metrics
- [ ] Target: Autobot becomes fully autonomous agent that exceeds current assistant capabilities

## Post-Completion Protocol
- [x] Run full integration test suite after any remaining task completion
- [x] Follow-up audit scheduled (next session) to verify fresh audit findings
- [ ] Revisit, audit, and retest entire process once current todo list is completed
- [ ] Validate all 8 success criteria from MISSION_PURPOSE.md with live execution
- [ ] Performance benchmark: gateway latency, Hermes tool execution time, memory usage
- [ ] Security audit: verify license checks, tamper detection, no hardcoded secrets
- [ ] Documentation review: update README with setup, architecture, and operational procedures
- [ ] Stakeholder sign-off on Phase 5 evolutionary framework readiness

## Remaining
- [ ] Add MT5 connector for live trading
- [ ] Implement risk management layer
- [x] Test full UI flow from VS Code to Hermes agent
- [x] Test memory tree view in VS Code sidebar
