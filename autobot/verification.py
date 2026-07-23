
from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class VerificationResult:
    valid: bool
    confidence: float
    issues: List[str] = field(default_factory=list)
    citations: List[Dict[str, str]] = field(default_factory=list)
    schema_errors: List[str] = field(default_factory=list)


class ToolResultVerifier:
    def __init__(self) -> None:
        self._required_citation_tools = {"web_search", "web_fetch", "search_files", "read_file"}
        self._string_schema = {"type": "string", "minLength": 1, "maxLength": 100_000}
        self._list_schema = {"type": "array", "items": {"type": "string"}}
        self._dict_schema = {"type": "object"}

    def verify(self, tool_name: str, args: Dict[str, Any], result: str) -> VerificationResult:
        issues: List[str] = []
        schema_errors: List[str] = []
        citations: List[Dict[str, str]] = []
        confidence = 1.0

        if not isinstance(result, str):
            return VerificationResult(valid=False, confidence=0.0, issues=["Result is not a string"])

        if not result.strip():
            issues.append("Empty result")
            confidence -= 0.3

        if tool_name in self._required_citation_tools:
            citation_result = self._check_citations(tool_name, result)
            citations = citation_result[0]
            issues.extend(citation_result[1])
            if not citations:
                confidence -= 0.2
                issues.append(f"Missing citations for {tool_name}")

        if tool_name in {"read_file", "write_file", "patch"}:
            path_result = self._validate_file_path(args.get("file_path", ""))
            schema_errors.extend(path_result[1])
            if not path_result[0]:
                confidence -= 0.1

        if tool_name in {"execute_code", "process"}:
            cmd_result = self._validate_command(args.get("command", ""))
            schema_errors.extend(cmd_result[1])
            if not cmd_result[0]:
                confidence -= 0.2

        valid = len(schema_errors) == 0 and confidence > 0.0
        return VerificationResult(
            valid=valid,
            confidence=max(0.0, min(1.0, confidence)),
            issues=issues,
            citations=citations,
            schema_errors=schema_errors,
        )

    def _check_citations(self, tool_name: str, result: str) -> Tuple[List[Dict[str, str]], List[str]]:
        citations: List[Dict[str, str]] = []
        issues: List[str] = []

        if tool_name in {"web_search", "web_fetch"}:
            urls = re.findall(r'https?://[^\s)>\]"\']+', result)
            for url in urls:
                citations.append({"url": url, "type": "web"})
            if not urls:
                issues.append("No URLs found in web result")

        if tool_name == "read_file":
            path = result.split("\n")[0] if result else ""
            if path and Path(path).exists():
                citations.append({"file": path, "type": "file", "sha256": self._sha256_file(Path(path))})

        return citations, issues

    def _validate_file_path(self, path: str) -> Tuple[bool, List[str]]:
        errors: List[str] = []
        if not path:
            return False, ["Missing file_path"]
        if ".." in path or path.startswith("/"):
            errors.append("Path traversal risk")
        if len(path) > 4096:
            errors.append("Path too long")
        return len(errors) == 0, errors

    def _validate_command(self, command: str) -> Tuple[bool, List[str]]:
        errors: List[str] = []
        if not command:
            return False, ["Missing command"]
        dangerous = {"rm -rf", "sudo", "chmod 777", "dd if=", "mkfs", "shutdown", "reboot"}
        lower = command.lower()
        for pattern in dangerous:
            if pattern in lower:
                errors.append(f"Dangerous command pattern: {pattern}")
        return len(errors) == 0, errors

    def _sha256_file(self, path: Path) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()[:16]
