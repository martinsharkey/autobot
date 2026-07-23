
from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse, StreamingResponse

from gateway.state import active_agents, agent_task_counter, config
from autobot.runtime import AgentRuntime
from autobot.skills import SkillManager

router = APIRouter()


@router.post("/v1/agent/run")
async def agent_run(req: Any):
    goal = getattr(req, "goal", "")
    mode = getattr(req, "mode", "coder")
    max_loops = getattr(req, "max_loops", 50)
    stream = getattr(req, "stream", False)

    rt = AgentRuntime.shared()
    if mode:
        rt.switch_mode(mode)

    if not stream:
        global agent_task_counter
        agent_task_counter += 1
        task_id = f"task_{int(__import__('time').time()*1000)}_{agent_task_counter}"

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
            for line in text.split("\n"):
                yield f"data: {__import__('json').dumps({'type': 'text', 'text': line})}\n\n"
            yield f"data: {__import__('json').dumps({'type': 'completed'})}\n\n"
        except Exception as e:
            yield f"data: {__import__('json').dumps({'type': 'error', 'text': str(e)})}\n\n"
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
    return {"entries": [e.to_dict() for e in ms.get_recent(20)], "stats": ms.get_stats()}
