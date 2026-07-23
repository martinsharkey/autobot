
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class FactChecker:
    def __init__(self, consensus_threshold: float = 0.7) -> None:
        self._consensus_threshold = consensus_threshold

    def check(self, claim: str, sources: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not sources:
            return {"supported": False, "confidence": 0.0, "reason": "no_sources"}
        supporting = sum(1 for s in sources if self._supports(claim, s))
        confidence = supporting / len(sources)
        return {
            "supported": confidence >= self._consensus_threshold,
            "confidence": round(confidence, 2),
            "supporting": supporting,
            "total": len(sources),
            "reason": "consensus" if confidence >= self._consensus_threshold else "low_consensus",
        }

    def _supports(self, claim: str, source: Dict[str, Any]) -> bool:
        text = str(source.get("text") or source.get("content") or source.get("snippet") or "").lower()
        keywords = [w for w in claim.lower().split() if len(w) > 3][:5]
        return any(keyword in text for keyword in keywords)
