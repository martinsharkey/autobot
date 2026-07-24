 
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from autobot.llm import LLMClient
from autobot.memory import MemoryStore
from autobot.tools import ToolRegistry

_AUTOBOT_DIR = Path(__file__).parent
_HERMES_DIR = _AUTOBOT_DIR.parent / "hermes-repo"
for _p in [str(_HERMES_DIR)]:
    if _p not in sys.path:
        sys.path.append(_p)

AUTOBOT_GATEWAY = os.getenv("AUTOBOT_GATEWAY", "http://127.0.0.1:8001/v1").rstrip("/")
if not AUTOBOT_GATEWAY.endswith("/v1"):
    AUTOBOT_GATEWAY = AUTOBOT_GATEWAY + "/v1"
AUTOBOT_API_KEY = os.getenv("AUTOBOT_API_KEY", "changeme")


class AutobotAgent:
    def __init__(
        self,
        mode: str = "coder",
        llm: Optional[LLMClient] = None,
        memory: Optional[MemoryStore] = None,
        tools: Optional[ToolRegistry] = None,
        memory_store: Optional[MemoryStore] = None,
        workspace_root: Optional[str] = None,
    ) -> None:
        self.mode = mode
        self.llm = llm or LLMClient()
        self.memory = memory or memory_store or MemoryStore()
        self.tools = tools or ToolRegistry()
        self.workspace_root = workspace_root
        self.last_result: Optional[str] = None
        self._agent = None

    def _get_hermes_agent(self):
        if self._agent is None:
            try:
                from run_agent import AIAgent
                
                def step_cb(api_call_count, prev_tools):
                    if hasattr(self, "on_event") and self.on_event:
                        self.on_event({"type": "loop", "count": api_call_count, "max": 50})
                        
                def tool_start_cb(tool_call_id, name, args):
                    if hasattr(self, "on_event") and self.on_event:
                        self.on_event({"type": "tool_call", "name": name, "args": args})
                        
                def thinking_cb(text):
                    if hasattr(self, "on_event") and self.on_event:
                        self.on_event({"type": "text", "text": text})

                self._agent = AIAgent(
                    base_url=AUTOBOT_GATEWAY,
                    api_key=AUTOBOT_API_KEY,
                    api_mode="chat_completions",
                    model="",
                    max_iterations=50,
                    enabled_toolsets=["terminal", "file", "search", "code_execution"],
                    quiet_mode=True,
                    step_callback=step_cb,
                    tool_start_callback=tool_start_cb,
                    thinking_callback=thinking_cb,
                )
            except Exception:
                self._agent = None
        return self._agent

    async def run(self, goal: str, on_event=None) -> Dict[str, Any]:
        self.on_event = on_event
        if on_event:
            on_event({"type": "started", "text": goal})
        agent = self._get_hermes_agent()
        if agent is None:
            return {"status": "error", "result": "Hermes AIAgent unavailable", "mode": self.mode}
        try:
            result = agent.run_conversation(goal)
            if isinstance(result, dict):
                text = result.get("final_response") or result.get("response") or str(result)
            else:
                text = result if isinstance(result, str) else str(result)
            self.last_result = text
            if on_event:
                on_event({"type": "completed", "text": text})
            return {"status": "ok", "result": text, "mode": self.mode}
        except Exception as exc:
            if on_event:
                on_event({"type": "error", "text": str(exc)})
            return {"status": "error", "result": str(exc), "mode": self.mode}

    async def run_task(self, goal: str, mode: Optional[str] = None, on_event=None) -> Dict[str, Any]:
        if mode:
            self.mode = mode
        result = await self.run(goal, on_event=on_event)
        return result

    def switch_mode(self, mode: str) -> None:
        self.mode = mode
        self._agent = None

    async def close(self) -> None:
        await self.llm.close()

