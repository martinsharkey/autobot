
from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field

_GATEWAY_DIR = os.path.dirname(__file__)
_PROJECT_ROOT = os.path.abspath(os.path.join(_GATEWAY_DIR, ".."))
_GATEWAY_DOTENV = os.path.join(_GATEWAY_DIR, ".env")
_PROJECT_DOTENV = os.path.join(_PROJECT_ROOT, ".env")

load_dotenv(_GATEWAY_DOTENV)
if os.path.exists(_PROJECT_DOTENV):
    load_dotenv(_PROJECT_DOTENV, override=False)


class ProviderConfig(BaseModel):
    name: str
    base_url: str
    api_key_env: Optional[str] = None
    api_key_prefix: str = "Bearer"
    completions_path: str = "chat/completions"
    active: bool = True
    weight: int = 1
    timeout_seconds: int = 20
    model_map: Optional[Dict[str, str]] = None
    default_model: Optional[str] = None


class GatewayConfig(BaseModel):
    gateway_api_key: Optional[str] = None
    providers: List[ProviderConfig] = Field(default_factory=list)


def load_config() -> GatewayConfig:
    config_path = os.path.join(os.path.dirname(__file__), "..", "providers.yaml")
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Missing provider config: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    gateway_api_key = os.getenv("GATEWAY_API_KEY")
    providers = [ProviderConfig(**item) for item in raw.get("providers", []) if item.get("active", True)]
    return GatewayConfig(gateway_api_key=gateway_api_key, providers=providers)


config = load_config()


provider_health: Dict[str, float] = {}
provider_failure_count: Dict[str, int] = {}
active_agents: Dict[str, Any] = {}
agent_task_counter = 0
