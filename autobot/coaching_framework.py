 
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from autobot.llm import LLMClient
from autobot.memory import MemoryStore
from autobot.consensus import MultiLLMConsensus

_AUTOBOT_DIR = Path(__file__).parent
_HERMES_DIR = _AUTOBOT_DIR.parent / "hermes-repo"
for _p in [str(_HERMES_DIR)]:
    if _p not in sys.path:
        sys.path.append(_p)

AUTOBOT_GATEWAY = os.getenv("AUTOBOT_GATEWAY", "http://127.0.0.1:8001/v1").rstrip("/")
if not AUTOBOT_GATEWAY.endswith("/v1"):
    AUTOBOT_GATEWAY = AUTOBOT_GATEWAY + "/v1"
AUTOBOT_API_KEY = os.getenv("AUTOBOT_API_KEY", "changeme")

logger = logging.getLogger(__name__)


class CoachingSession:
    def __init__(self, session_id: Optional[str] = None, log_dir: Optional[Path] = None) -> None:
        self.session_id = session_id or f"session_{int(time.time()*1000)}"
        self.log_dir = log_dir or (Path(os.getenv("AUTOBOT_HOME", ".")) / "coaching_logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = self.log_dir / f"{self.session_id}.jsonl"
        self.turns: List[Dict[str, Any]] = []
        self.win_streak = 0
        self.best_win_streak = 0
        self.total_rounds = 0
        self.autobot_wins = 0
        self.mentor_wins = 0

    def log_turn(self, role: str, speaker: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        turn = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "role": role,
            "speaker": speaker,
            "content": content,
            "metadata": metadata or {},
        }
        self.turns.append(turn)
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(turn) + "\n")
        return turn

    def record_round(self, winner: str, reason: str, scores: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        self.total_rounds += 1
        if winner == "autobot":
            self.autobot_wins += 1
            self.win_streak += 1
            if self.win_streak > self.best_win_streak:
                self.best_win_streak = self.win_streak
        else:
            self.mentor_wins += 1
            self.win_streak = 0
        record = {
            "round": self.total_rounds,
            "winner": winner,
            "reason": reason,
            "scores": scores or {},
            "win_streak": self.win_streak,
            "best_win_streak": self.best_win_streak,
        }
        self.log_turn("round_result", "system", f"{winner} wins round {self.total_rounds}: {reason}", metadata=record)
        return record

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "total_rounds": self.total_rounds,
            "autobot_wins": self.autobot_wins,
            "mentor_wins": self.mentor_wins,
            "current_win_streak": self.win_streak,
            "best_win_streak": self.best_win_streak,
            "log_path": str(self.log_path),
        }


class AIMentor:
    def __init__(self, provider: Optional[str] = None, model: Optional[str] = None) -> None:
        self.provider = provider or os.getenv("AUTOBOT_MENTOR_PROVIDER", "google-ai-studio")
        self.model = model or os.getenv("AUTOBOT_MENTOR_MODEL", "gemini-2.5-flash")
        self._client = LLMClient(provider_name=self.provider, model=self.model)

    async def respond(self, text: str, system: Optional[str] = None) -> Dict[str, Any]:
        return await self._client.chat(text, system=system, temperature=0.7)

    async def generate_challenge(self, difficulty: str = "medium", topic: Optional[str] = None) -> str:
        topic_clause = f" on the topic of {topic}" if topic else ""
        prompt = f"You are a challenging AI mentor. Generate a {difficulty}-difficulty reasoning/challenge prompt{topic_clause}. Return ONLY the challenge text, no preamble."
        try:
            result = await self.respond(prompt)
            text = result.get("text", "").strip()
            if not text or len(text) < 20:
                raise ValueError("empty challenge")
            return text
        except Exception as exc:
            logger.warning("mentor challenge generation failed: %s", exc)
            return f"Solve this {difficulty}-difficulty coding problem on {topic or 'algorithms'}: write a function and explain your approach."

    async def evaluate(self, challenge: str, autobot_response: str, mentor_response: str) -> Dict[str, Any]:
        prompt = f"""You are an impartial judge. Compare two AI responses to the challenge below.

Challenge: {challenge}

Response A (Autobot):
{autobot_response}

Response B (Mentor/Kilo):
{mentor_response if mentor_response else "(no response)"}

Provide evaluation in JSON format:
{{"winner": "autobot" or "mentor", "score_autobot": 0-1, "score_mentor": 0-1, "reason": "<brief reason>"}}"""
        try:
            result = await self.respond(prompt)
            text = result.get("text", "").strip()
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(text[start:end])
        except Exception as exc:
            logger.warning("judge evaluation failed: %s", exc)
        return {"winner": "mentor", "score_autobot": 0.5, "score_mentor": 0.5, "reason": "evaluation_failed"}


class AutobotCoachingClient:
    def __init__(self) -> None:
        self._client = LLMClient()

    async def respond(self, challenge: str, mode: str = "coder") -> Dict[str, Any]:
        try:
            from run_agent import AIAgent
            agent = AIAgent(
                base_url=AUTOBOT_GATEWAY,
                api_key=AUTOBOT_API_KEY,
                api_mode="chat_completions",
                model="",
                max_iterations=10,
                enabled_toolsets=["terminal", "file", "search", "code_execution"],
                quiet_mode=True,
            )
            text = agent.run_conversation(challenge)
            return {"status": "ok", "mode": mode, "result": text if isinstance(text, str) else str(text)}
        except Exception as exc:
            logger.warning("Hermes agent coaching failed, falling back to LLM: %s", exc)
            system = "You are a skilled coding assistant. Provide clear, correct, complete answers."
            result = await self._client.chat(challenge, system=system, temperature=0.3)
            return {"status": "ok", "mode": mode, "result": result.get("text", "")}

    async def optimize_with_providers(self, challenge: str) -> Dict[str, Any]:
        try:
            from gateway.state import config
            providers = config.providers
        except Exception:
            providers = []
        active = [p for p in providers if getattr(p, "active", False)]
        best = None
        best_score = -1.0
        for provider in active[:5]:
            try:
                client = LLMClient(provider_name=provider.name, model=getattr(provider, "default_model", ""), direct=True)
                result = await client.chat(challenge)
                score = float(result.get("usage", {}).get("total_tokens", 0) > 0)
                if score > best_score:
                    best_score = score
                    best = {"provider": provider.name, "result": result, "score": score}
            except Exception:
                continue
        return best or {"provider": None, "result": {"text": ""}, "score": 0.0}


class CoachingFramework:
    def __init__(self, log_dir: Optional[Path] = None) -> None:
        self.log_dir = log_dir or (Path(os.getenv("AUTOBOT_HOME", ".")) / "coaching_logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.session = CoachingSession(log_dir=self.log_dir)
        self.mentor = AIMentor()
        self.autobot = AutobotCoachingClient()
        self.consensus = MultiLLMConsensus()
        self.win_target = 50

    async def run_coaching_round(self, difficulty: str = "medium", topic: Optional[str] = None) -> Dict[str, Any]:
        challenge = await self.mentor.generate_challenge(difficulty=difficulty, topic=topic)
        self.session.log_turn("challenge", "mentor", challenge)

        autobot_resp = await self.autobot.respond(challenge, mode="coder")
        autobot_text = autobot_resp.get("result", "")
        self.session.log_turn("response", "autobot", autobot_text, metadata={"provider": "default"})

        mentor_resp = await self.mentor.respond(challenge)
        mentor_text = mentor_resp.get("text", "")
        self.session.log_turn("response", "mentor", mentor_text, metadata={"provider": "mentor"})

        # Evaluate using multi-LLM consensus judge comparing Autobot and Mentor responses
        responses_dict = {
            "autobot": autobot_text,
            "mentor": mentor_text
        }
        evaluation = await self.consensus._evaluate_responses(responses_dict, challenge, judge_provider="google-ai-studio")
        winner = evaluation.get("winner", "mentor")
        reason = evaluation.get("reason", "")
        
        round_record = self.session.record_round(winner, reason, scores={
            "autobot": evaluation.get("scores", {}).get("autobot", 0.0),
            "mentor": evaluation.get("scores", {}).get("mentor", 0.0),
        })

        return {
            "round": round_record,
            "challenge": challenge,
            "autobot_response": autobot_text,
            "mentor_response": mentor_text,
            "evaluation": evaluation,
            "win_streak": self.session.win_streak,
            "best_win_streak": self.session.best_win_streak,
        }

    async def run_until_target(self, difficulty: str = "medium", topic: Optional[str] = None) -> Dict[str, Any]:
        while self.session.win_streak < self.win_target:
            result = await self.run_coaching_round(difficulty=difficulty, topic=topic)
            if result["round"]["winner"] == "autobot":
                logger.info("autobot wins streak=%s best=%s", self.session.win_streak, self.session.best_win_streak)
            else:
                logger.info("mentor wins streak=%s reason=%s", self.session.win_streak, result["evaluation"].get("reason"))
        return self.session.to_dict()

    def get_status(self) -> Dict[str, Any]:
        return self.session.to_dict()

