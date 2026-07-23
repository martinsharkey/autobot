
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, List


class SkillManager:
    def __init__(self, base_dir: Path = None) -> None:
        self._base_dir = base_dir or Path(os.getenv("AUTOBOT_HOME", ".")) / "skills"
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def list_skills(self) -> List[Dict[str, Any]]:
        skills = []
        for path in self._base_dir.iterdir():
            if path.is_dir() and (path / "SKILL.md").exists():
                skills.append({"name": path.name, "path": str(path)})
        return skills

    def install(self, name: str, source: str) -> Dict[str, Any]:
        target = self._base_dir / name
        target.mkdir(parents=True, exist_ok=True)
        return {"installed": name, "path": str(target)}

    def remove(self, name: str) -> Dict[str, Any]:
        target = self._base_dir / name
        if target.exists():
            for child in target.rglob("*"):
                if child.is_file():
                    child.unlink(missing_ok=True)
                elif child.is_dir():
                    child.rmdir()
            target.rmdir()
        return {"removed": name}
