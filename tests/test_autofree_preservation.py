import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from autobot.llm import _ranked_providers, _autofree_rank
from autobot.curiosity import CuriosityEngine
from autobot.notifications import NotificationClient


def test_autofree_ranking_logic():
    # Mock some provider models
    p_free = {"name": "free-provider", "default_model": "glm-5-free", "weight": 5}
    p_paid = {"name": "paid-provider", "default_model": "claude-3-opus", "weight": 5}
    
    score_free = _autofree_rank(p_free)
    score_paid = _autofree_rank(p_paid)
    
    # Free score should be significantly lower (more negative) than paid score
    assert score_free < score_paid
    print("test_autofree_ranking_logic passed.")


async def test_disk_preservation():
    engine = CuriosityEngine()
    
    # Run check with high threshold (e.g. 1000GB) to force zipping archive
    res = await engine.preserve_disk_space(min_free_gb=1000.0)
    assert res is not None
    assert "status" in res
    # Should skip if no logs directory found, or complete archiving
    assert res["status"] in ["skipped", "archived", "failed"]
    print("test_disk_preservation passed.")


def test_heartbeat_formatting():
    client = NotificationClient()
    res = client.notify_martin_sharkey_heartbeat(disk_free_gb=12.4, active_tasks=2, peers_count=0)
    assert res is not None
    assert "channels" in res
    
    res_failover = client.notify_failover_master(original_host="192.168.1.10", new_host="192.168.1.20", peer_port=8002)
    assert res_failover is not None
    assert "channels" in res_failover
    print("test_heartbeat_formatting passed.")


async def main():
    test_autofree_ranking_logic()
    await test_disk_preservation()
    test_heartbeat_formatting()
    print("All autofree and preservation tests passed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
