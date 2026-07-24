from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from autobot.llm import LLMClient, _load_providers

logger = logging.getLogger(__name__)

DATA_DIR = Path(os.getenv("AUTOBOT_HOME", ".")) / "autobot_data"
RATINGS_PATH = DATA_DIR / "provider_ratings.json"


class MultiLLMConsensus:
    def __init__(self, target_providers: Optional[List[str]] = None) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.target_providers = target_providers or ["groq", "google-ai-studio", "deepseek", "siliconflow"]
        self.ratings = self._load_ratings()

    def _load_ratings(self) -> Dict[str, float]:
        if RATINGS_PATH.exists():
            try:
                return json.loads(RATINGS_PATH.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {p: 1.0 for p in self.target_providers}

    def _save_ratings(self) -> None:
        try:
            RATINGS_PATH.write_text(json.dumps(self.ratings, indent=2), encoding="utf-8")
        except Exception as exc:
            logger.debug("failed to save ratings: %s", exc)

    async def get_consensus_response(
        self,
        text: str,
        system: Optional[str] = None,
        judge_provider: str = "google-ai-studio"
    ) -> Dict[str, Any]:
        providers = _load_providers()
        active_targets = []
        for p in providers:
            name = p.get("name", "")
            if name in self.target_providers and p.get("active", True):
                key_env = p.get("api_key_env")
                if key_env and os.getenv(key_env):
                    active_targets.append(p)

        if not active_targets:
            logger.warning("No active consensus target providers found, falling back.")
            client = LLMClient()
            resp = await client.chat(text, system=system)
            return {
                "consensus_text": resp.get("text", ""),
                "responses": {"default": resp.get("text", "")},
                "scores": {"default": 1.0},
                "winner": "default"
            }

        tasks = []
        for p in active_targets:
            name = p.get("name")
            model = p.get("default_model")
            client = LLMClient(provider_name=name, model=model, direct=True)
            tasks.append(self._query_provider(client, name, text, system))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        valid_responses: Dict[str, str] = {}
        for res in results:
            if isinstance(res, tuple) and len(res) == 2:
                name, content = res
                if content:
                    valid_responses[name] = content

        if not valid_responses:
            raise RuntimeError("All parallel LLM consensus queries failed")

        if len(valid_responses) == 1:
            name = list(valid_responses.keys())[0]
            return {
                "consensus_text": valid_responses[name],
                "responses": valid_responses,
                "scores": {name: 1.0},
                "winner": name
            }

        evaluation = await self._evaluate_responses(valid_responses, text, judge_provider)
        
        scores = evaluation.get("scores", {})
        for name, score in scores.items():
            current = self.ratings.get(name, 1.0)
            self.ratings[name] = round(current * 0.8 + score * 0.2, 3)
        self._save_ratings()

        winner = evaluation.get("winner")
        consensus_text = valid_responses.get(winner) or list(valid_responses.values())[0]

        return {
            "consensus_text": consensus_text,
            "responses": valid_responses,
            "scores": scores,
            "winner": winner,
            "evaluation_reason": evaluation.get("reason", "")
        }

    async def _query_provider(self, client: LLMClient, name: str, text: str, system: Optional[str]) -> Tuple[str, str]:
        try:
            resp = await client.chat(text, system=system)
            return name, resp.get("text", "").strip()
        except Exception as exc:
            logger.debug("Provider %s query failed: %s", name, exc)
            return name, ""

    async def _evaluate_responses(self, responses: Dict[str, str], challenge: str, judge_provider: str) -> Dict[str, Any]:
        responses_block = ""
        for name, content in responses.items():
            responses_block += f"--- Response from Provider '{name}': ---\n{content}\n\n"

        prompt = (
            f"You are an expert judge. Evaluate the following AI responses to the challenge below.\n\n"
            f"Original Challenge:\n{challenge}\n\n"
            f"{responses_block}"
            f"Compare the responses for correctness, clarity, completeness, and syntax efficiency. "
            f"Provide your evaluation in strict JSON format: \n"
            f'{{"winner": "<provider_name>", "scores": {{"provider_1": 0.8, "provider_2": 0.5}}, "reason": "<brief reasoning>"}}'
        )

        try:
            judge_client = LLMClient(provider_name=judge_provider, direct=True)
            res = await judge_client.chat(prompt)
            text = res.get("text", "").strip()
            
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                data = json.loads(text[start:end])
                if "winner" in data and "scores" in data:
                    return data
        except Exception as exc:
            logger.warning("Consensus judge evaluation failed: %s", exc)

        default_scores = {name: 1.0 for name in responses}
        return {
            "winner": list(responses.keys())[0],
            "scores": default_scores,
            "reason": "fallback_due_to_evaluation_failure"
        }
