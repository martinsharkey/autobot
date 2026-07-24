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

    async def preserve_disk_space(self, min_free_gb: float = 5.0, hf_repo_id: Optional[str] = None) -> Dict[str, Any]:
        """Check local disk space, zip logs and offload them to Hugging Face if low on space."""
        import shutil
        import zipfile
        
        home = Path(os.getenv("AUTOBOT_HOME", "."))
        total, used, free = shutil.disk_usage(str(home.resolve()))
        free_gb = free / (1024 ** 3)
        
        if free_gb >= min_free_gb:
            return {"status": "skipped", "free_gb": round(free_gb, 2), "reason": "space_sufficient"}
            
        logs_dir = home / "coaching_logs"
        zip_path = home / "autobot_data" / "logs_archive.zip"
        
        if not logs_dir.exists():
            return {"status": "skipped", "reason": "no_logs_directory_found"}
            
        try:
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
                for file in logs_dir.glob("*.jsonl"):
                    zip_file.write(file, arcname=file.name)
                    
            upload_status = "skipped"
            if hf_repo_id:
                from autobot.slm_trainer import SLMTrainingManager
                trainer = SLMTrainingManager()
                import autobot.slm_trainer as slm
                old_path = slm.TRAINING_FILE
                slm.TRAINING_FILE = zip_path
                try:
                    res = trainer.upload_to_huggingface(repo_id=hf_repo_id, path_in_repo="logs_archive.zip")
                    upload_status = res.get("status", "failed")
                finally:
                    slm.TRAINING_FILE = old_path
                    
            deleted_count = 0
            if zip_path.exists():
                for file in logs_dir.glob("*.jsonl"):
                    file.unlink()
                    deleted_count += 1
                    
            return {
                "status": "archived",
                "free_gb": round(free_gb, 2),
                "deleted_logs": deleted_count,
                "upload_status": upload_status,
                "archive_path": str(zip_path)
            }
        except Exception as exc:
            logger.warning("failed to preserve disk space: %s", exc)
            return {"status": "failed", "error": str(exc)}
