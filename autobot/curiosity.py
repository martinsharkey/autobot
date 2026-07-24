from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

PEERS_DIR = Path(os.getenv("AUTOBOT_HOME", ".")) / "autobot_data" / "peers"


class CuriosityEngine:
    def __init__(self) -> None:
        PEERS_DIR.mkdir(parents=True, exist_ok=True)
        self._client = httpx.AsyncClient(timeout=5)

    async def scan_network(self, ports: Optional[List[int]] = None) -> List[Dict[str, Any]]:
        """Scan localhost or local subnet ports for active Autobot Gateway nodes."""
        ports = ports or [8001, 8002, 8003, 8004, 8005]
        found_peers = []
        
        for port in ports:
            url = f"http://127.0.0.1:{port}/v1/health"
            try:
                resp = await self._client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    peer = {
                        "port": port,
                        "url": f"http://127.0.0.1:{port}",
                        "status": "active",
                        "info": data
                    }
                    found_peers.append(peer)
                    self._register_peer(port, peer)
            except Exception:
                # Port is closed or not a gateway
                pass
                
        return found_peers

    def _register_peer(self, port: int, peer_info: Dict[str, Any]) -> None:
        peer_file = PEERS_DIR / f"peer_{port}.json"
        try:
            peer_file.write_text(json.dumps(peer_info, indent=2), encoding="utf-8")
            logger.info("Successfully registered curious peer node on port %d", port)
        except Exception as exc:
            logger.debug("Failed to write peer file: %s", exc)

    async def spawn_micro_autobot(self, peer_port: int, initial_task: str) -> Dict[str, Any]:
        """Delegate tasks to a micro-autobot running on another gateway node."""
        peer_file = PEERS_DIR / f"peer_{peer_port}.json"
        if not peer_file.exists():
            return {"status": "failed", "error": f"Peer on port {peer_port} is not registered."}
            
        url = f"http://127.0.0.1:{peer_port}/v1/agent/run"
        payload = {
            "goal": initial_task,
            "mode": "coder",
            "stream": False,
            "source": "curiosity_spider"
        }
        
        try:
            resp = await self._client.post(url, json=payload)
            if resp.status_code == 200:
                return {"status": "spawned", "response": resp.json()}
            return {"status": "failed", "error": f"HTTP status {resp.status_code}"}
        except Exception as exc:
            return {"status": "failed", "error": str(exc)}

    def list_active_micro_nodes(self) -> List[Dict[str, Any]]:
        nodes = []
        for file in PEERS_DIR.glob("*.json"):
            try:
                nodes.append(json.loads(file.read_text(encoding="utf-8")))
            except Exception:
                pass
        return nodes
