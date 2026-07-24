from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List

from autobot.memory import MemoryStore

logger = logging.getLogger(__name__)

DATA_DIR = Path(os.getenv("AUTOBOT_HOME", ".")) / "autobot_data"
TRAINING_FILE = DATA_DIR / "slm_training_data.jsonl"


class SLMTrainingManager:
    def __init__(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.memory = MemoryStore()

    def prepare_dataset(self) -> str:
        """Scan MemoryStore and extract high-confidence reasoning steps for fine-tuning."""
        entries = self.memory.get_recent(500)
        formatted_count = 0
        
        with open(TRAINING_FILE, "w", encoding="utf-8") as f:
            for entry in entries:
                metadata = entry.metadata or {}
                avg_conf = metadata.get("avg_confidence", 0.0)
                fact_check = metadata.get("fact_check", {})
                
                is_high_quality = (avg_conf >= 0.8) or (fact_check.get("confidence", 0.0) >= 0.8)
                
                if is_high_quality:
                    item = {
                        "messages": [
                            {"role": "system", "content": f"You are Autobot in mode: {entry.source}. Solve the user challenge efficiently."},
                            {"role": "user", "content": entry.text[:1000]},
                            {"role": "assistant", "content": entry.text}
                        ]
                    }
                    f.write(json.dumps(item) + "\n")
                    formatted_count += 1
                    
        logger.info("Successfully extracted %d high-quality trajectories to %s", formatted_count, TRAINING_FILE)
        return str(TRAINING_FILE)

    def upload_to_huggingface(self, repo_id: str, path_in_repo: str = "dataset.jsonl") -> Dict[str, Any]:
        """Upload the extracted dataset or model weights to a free Hugging Face repository."""
        token = os.getenv("HF_API_KEY") or os.getenv("HF_TOKEN")
        if not token:
            return {"status": "failed", "error": "Missing Hugging Face token in environment variables."}
            
        if not TRAINING_FILE.exists():
            return {"status": "failed", "error": f"Training file {TRAINING_FILE} does not exist. Run prepare_dataset first."}
            
        try:
            from huggingface_hub import HfApi
            api = HfApi()
            
            api.create_repo(repo_id=repo_id, token=token, repo_type="dataset", exist_ok=True)
            
            api.upload_file(
                path_or_fileobj=str(TRAINING_FILE),
                path_in_repo=path_in_repo,
                repo_id=repo_id,
                repo_type="dataset",
                token=token
            )
            
            logger.info("Successfully uploaded dataset to Hugging Face repository: %s", repo_id)
            return {"status": "uploaded", "repo_id": repo_id, "path": path_in_repo}
        except ImportError:
            return {"status": "failed", "error": "huggingface_hub python package is not installed."}
        except Exception as exc:
            return {"status": "failed", "error": str(exc)}
