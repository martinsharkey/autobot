 
from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse

from gateway.state import active_agents, agent_task_counter, config
from autobot.runtime import AgentRuntime
from autobot.skills import SkillManager
from autobot.remote_commands import RemoteCommandProtocol

router = APIRouter()


@router.post("/v1/agent/run")
async def agent_run(request: Request):
    body = await request.json()
    goal = body.get("goal", "")
    mode = body.get("mode", "coder")
    stream = bool(body.get("stream", False))
    source = body.get("source", "api")

    rt = AgentRuntime.shared()
    if mode:
        rt.switch_mode(mode)

    slash_result = None
    if source == "telegram" or source == "whatsapp" or (isinstance(goal, str) and goal.startswith("/")):
        rc = RemoteCommandProtocol()
        if source == "telegram":
            slash_result = rc.handle_telegram_update({"message": {"text": goal, "chat": {"id": body.get("chat_id", "")}}})
        elif source == "whatsapp":
            slash_result = rc.handle_whatsapp_message({"entry": [{"changes": [{"value": {"messages": [{"text": {"body": goal}, "to": body.get("recipient", "")}]}}]}]})
        else:
            slash_result = rc._dispatch_command(goal, source="api")

    if slash_result:
        return {"status": "ok", "mode": mode, "result": str(slash_result), "task_id": ""}

    if not stream:
        import time as _time
        global agent_task_counter
        agent_task_counter += 1
        task_id = f"task_{int(_time.time()*1000)}_{agent_task_counter}"

        active_agents[task_id] = {"status": "running", "mode": mode, "goal": goal}
        try:
            result = await rt.execute(goal, mode=mode)
            active_agents[task_id] = {
                "status": "completed",
                "result": result.get("result", ""),
                "mode": mode,
                "goal": goal,
            }
        except Exception as e:
            active_agents[task_id] = {"status": "failed", "error": str(e), "goal": goal}
        return {"status": "ok", "task_id": task_id, "mode": mode, "result": active_agents.get(task_id, {}).get("result", "")}

    async def generate():
        try:
            result = await rt.execute(goal, mode=mode)
            text = result.get("result", "")
            if not text:
                yield f"data: {json.dumps({'type': 'text', 'text': ''})}\n\n"
            for line in text.split("\n"):
                yield f"data: {json.dumps({'type': 'text', 'text': line})}\n\n"
            yield f"data: {json.dumps({'type': 'completed'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'text': str(e)})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/v1/agent/status")
async def agent_status():
    return {"active_tasks": len(active_agents), "tasks": {k: v for k, v in active_agents.items()}}


@router.post("/v1/agent/stop")
async def agent_stop():
    stopped = list(active_agents.keys())
    for k in stopped:
        active_agents[k] = {**active_agents[k], "status": "stopped"}
    return {"status": "ok", "stopped": len(stopped)}


@router.get("/v1/skills")
async def list_skills():
    sm = SkillManager()
    return {"skills": sm.list_skills()}


@router.get("/v1/memory")
async def get_memory():
    ms = AgentRuntime.shared().get_memory()
    entries = ms.get_recent(20)
    return {
        "entries": [
            {
                "id": str(idx),
                "category": entry.source,
                "content": entry.text,
                "importance": 0.5,
                "created_at": entry.created_at,
                "metadata": entry.metadata,
            }
            for idx, entry in enumerate(entries)
        ],
        "stats": ms.get_stats(),
    }
