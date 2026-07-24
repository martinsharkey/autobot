
from __future__ import annotations

import sys
from io import StringIO
from typing import IO

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

_original_stderr = sys.stderr

_plugin_warn_prefixes = (
    "Failed to load plugin",
    "Failed to load tool module",
)


class _PluginWarningFilter(StringIO):
    def write(self, text: str) -> int:
        if any(text.startswith(prefix) for prefix in _plugin_warn_prefixes):
            return len(text)
        _original_stderr.write(text)
        return len(text)

    def flush(self) -> None:
        pass


_plugin_warn_stream: IO[str] = _PluginWarningFilter()
sys.stderr = _plugin_warn_stream

from gateway.routers import agent, chat, coaching, mcp, system
from gateway.state import config

try:
    from autobot.license import check_tamper
    _tamper = check_tamper()
    if _tamper.get("tampered"):
        print(f"[license] tamper detected: {_tamper.get('mismatches')}")
except Exception as _exc:
    print(f"[license] tamper check skipped: {_exc}")

sys.stderr = _original_stderr


def create_app() -> FastAPI:
    app = FastAPI(title="AUTOBOT Gateway", version="2.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def require_gateway_key(request, call_next):
        if config.gateway_api_key and not request.url.path.startswith("/v1/health"):
            auth = request.headers.get("Authorization", "")
            expected = f"Bearer {config.gateway_api_key}"
            if auth != expected:
                return JSONResponse(
                    status_code=401,
                    content={"error": "Missing or invalid gateway API key", "hint": f"Use Authorization: Bearer {config.gateway_api_key}"},
                )
        return await call_next(request)

    app.include_router(system.router)
    app.include_router(chat.router)
    app.include_router(agent.router)
    app.include_router(mcp.router)
    app.include_router(coaching.router)

    @app.on_event("startup")
    async def start_autonomous_loop():
        import asyncio
        import sys
        import subprocess
        try:
            print("[autobot] Starting background ntfy command listener...")
            subprocess.Popen([sys.executable, "autobot/trading/ntfy_daemon.py"])
        except Exception as e:
            print(f"[autobot] Failed to start ntfy daemon: {e}")

        async def autonomous_loop():
            # Wait 10 seconds on startup
            await asyncio.sleep(10)
            while True:
                try:
                    from autobot.runtime import AgentRuntime
                    rt = AgentRuntime.shared()
                    print("[autobot] Running background self-evolution...")
                    evolve_res = await rt.evolve()
                    print(f"[autobot] Self-evolution result: {evolve_res}")
                    
                    print("[autobot] Running background overnight learner...")
                    overnight_res = await rt.overnight()
                    print(f"[autobot] Overnight learner result: {overnight_res}")

                    print("[autobot] Running background trading monitor...")
                    from autobot.trading.monitoring import TradingMonitor
                    from autobot.trading.mutator import TradingStrategyMutator
                    monitor = TradingMonitor()
                    monitor.compile_dashboard()

                    mutator = TradingStrategyMutator()
                    mutation_res = await mutator.mutate_strategies()
                    print(f"[autobot] Strategy mutation result: {mutation_res}")
                except Exception as e:
                    print(f"[autobot] Autonomous loop error: {e}")
                
                # Run once every 2 hours (7200 seconds)
                await asyncio.sleep(7200)
                
        asyncio.create_task(autonomous_loop())

    return app


app = create_app()
