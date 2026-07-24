import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from autobot.consensus import MultiLLMConsensus
from autobot.coaching_framework import AIMentor, CoachingFramework
from autobot.curiosity import CuriosityEngine
from autobot.slm_trainer import SLMTrainingManager


def test_consensus_instantiation():
    consensus = MultiLLMConsensus()
    assert consensus is not None
    assert "groq" in consensus.target_providers
    assert "google-ai-studio" in consensus.target_providers
    print("test_consensus_instantiation passed.")


async def test_consensus_evaluation_fallback():
    consensus = MultiLLMConsensus()
    responses = {
        "provider_a": "The solution is X.",
        "provider_b": "The solution is Y."
    }
    evaluation = await consensus._evaluate_responses(responses, "Solve for Z", judge_provider="invalid-provider")
    assert evaluation is not None
    assert "winner" in evaluation
    assert "scores" in evaluation
    assert evaluation["winner"] == "provider_a"
    print("test_consensus_evaluation_fallback passed.")


def test_mentor_defaults():
    mentor = AIMentor()
    assert mentor.provider == "google-ai-studio"
    assert mentor.model == "gemini-2.5-flash"
    print("test_mentor_defaults passed.")


async def test_curiosity_scan():
    engine = CuriosityEngine()
    peers = await engine.scan_network(ports=[9991, 9992])
    assert isinstance(peers, list)
    assert len(peers) == 0
    print("test_curiosity_scan passed.")


def test_slm_dataset_preparation():
    manager = SLMTrainingManager()
    manager.memory.add(
        "Successful trading analysis for AAPL",
        source="trader",
        metadata={"avg_confidence": 0.9}
    )
    
    data_file = manager.prepare_dataset()
    assert os.path.exists(data_file)
    
    with open(data_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
        assert len(lines) > 0
        first_item = json.loads(lines[0])
        assert "messages" in first_item
        assert len(first_item["messages"]) == 3
        assert first_item["messages"][0]["role"] == "system"
        assert "Successful trading analysis" in first_item["messages"][2]["content"]
        
    try:
        os.remove(data_file)
    except Exception:
        pass
    print("test_slm_dataset_preparation passed.")


async def main():
    test_consensus_instantiation()
    await test_consensus_evaluation_fallback()
    test_mentor_defaults()
    await test_curiosity_scan()
    test_slm_dataset_preparation()
    print("All tests passed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
