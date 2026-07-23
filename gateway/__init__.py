
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from gateway.routers import agent, chat, system
from gateway.state import config


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

    return app


app = create_app()
