import asyncio
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import Config, MODE_GROUPS


class ToolResult:
    def __init__(self, success: bool, output: str = "", error: str = ""):
        self.success = success
        self.output = output
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        return {"success": self.success, "output": self.output, "error": self.error}


class ToolRegistry:
    def __init__(self, workspace_root: Optional[str] = None):
        self.workspace_root = Path(workspace_root or os.getcwd()).resolve()
        self.config = Config()
        self._tools: Dict[str, Any] = {}
        self._register_core()

    def _register_core(self):
        self.register("read_file", self._read_file, "read")
        self.register("write_file", self._write_file, "edit")
        self.register("edit_file", self._edit_file, "edit")
        self.register("list_directory", self._list_directory, "read")
        self.register("search_files", self._search_files, "read")
        self.register("execute_command", self._execute_command, "command")
        self.register("think", self._think, "read")
        self.register("attempt_completion", self._attempt_completion, "read")

    def register(self, name: str, handler: Any, group: str):
        self._tools[name] = {"name": name, "handler": handler, "group": group}

    def get_definitions(self, mode: str) -> List[Dict[str, Any]]:
        allowed_groups = MODE_GROUPS.get(mode, MODE_GROUPS["coder"])
        allowed = {g for g, ok in allowed_groups.__dict__.items() if ok}
        definitions = []
        for tool in self._tools.values():
            if tool["group"] in allowed:
                definitions.append(self._schema(tool["name"]))
        return definitions

    def _schema(self, name: str) -> Dict[str, Any]:
        schemas = {
            "read_file": {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Read the contents of a file",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Relative or absolute path to the file"}
                        },
                        "required": ["path"],
                    },
                },
            },
            "write_file": {
                "type": "function",
                "function": {
                    "name": "write_file",
                    "description": "Write content to a file (creates or overwrites)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "content": {"type": "string"},
                        },
                        "required": ["path", "content"],
                    },
                },
            },
            "edit_file": {
                "type": "function",
                "function": {
                    "name": "edit_file",
                    "description": "Find and replace text in a file",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "old_string": {"type": "string"},
                            "new_string": {"type": "string"},
                        },
                        "required": ["path", "old_string", "new_string"],
                    },
                },
            },
            "list_directory": {
                "type": "function",
                "function": {
                    "name": "list_directory",
                    "description": "List files in a directory",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "recursive": {"type": "boolean", "default": False},
                        },
                        "required": ["path"],
                    },
                },
            },
            "search_files": {
                "type": "function",
                "function": {
                    "name": "search_files",
                    "description": "Search file contents using regex",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "pattern": {"type": "string"},
                            "path": {"type": "string", "default": "."},
                        },
                        "required": ["pattern"],
                    },
                },
            },
            "execute_command": {
                "type": "function",
                "function": {
                    "name": "execute_command",
                    "description": "Run a shell command in the workspace",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {"type": "string"},
                            "timeout": {"type": "number", "default": 30},
                            "cwd": {"type": "string", "default": "."},
                        },
                        "required": ["command"],
                    },
                },
            },
            "think": {
                "type": "function",
                "function": {
                    "name": "think",
                    "description": "Think step by step (no side effects)",
                    "parameters": {
                        "type": "object",
                        "properties": {"thought": {"type": "string"}},
                        "required": ["thought"],
                    },
                },
            },
            "attempt_completion": {
                "type": "function",
                "function": {
                    "name": "attempt_completion",
                    "description": "Signal that the task is complete",
                    "parameters": {
                        "type": "object",
                        "properties": {"result": {"type": "string"}},
                        "required": ["result"],
                    },
                },
            },
        }
        return schemas.get(name, {"type": "function", "function": {"name": name, "description": "", "parameters": {}}})

    async def execute(self, name: str, arguments: Dict[str, Any], mode: str) -> ToolResult:
        if name not in self._tools:
            return ToolResult(False, error=f"Unknown tool: {name}")

        tool = self._tools[name]
        allowed_groups = MODE_GROUPS.get(mode, MODE_GROUPS["coder"])
        if not getattr(allowed_groups, tool["group"], False):
            return ToolResult(False, error=f"Tool '{name}' not allowed in {mode} mode")

        try:
            result = await tool["handler"](arguments)
            if asyncio.iscoroutine(result):
                result = await result
            if isinstance(result, ToolResult):
                return result
            return ToolResult(True, output=str(result))
        except Exception as e:
            return ToolResult(False, error=str(e))

    def _resolve(self, path: str) -> Path:
        p = Path(path)
        if p.is_absolute():
            return p
        return (self.workspace_root / p).resolve()

    async def _read_file(self, args: Dict[str, Any]) -> ToolResult:
        target = self._resolve(args["path"])
        if not target.exists():
            return ToolResult(False, error=f"File not found: {args['path']}")
        if target.is_dir():
            return ToolResult(False, error="Is a directory")
        if target.stat().st_size > 2_000_000:
            return ToolResult(False, error="File too large (>2MB)")
        content = target.read_text(encoding="utf-8", errors="replace")
        return ToolResult(True, output=content)

    async def _write_file(self, args: Dict[str, Any]) -> ToolResult:
        target = self._resolve(args["path"])
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(args["content"], encoding="utf-8")
        return ToolResult(True, output=f"Wrote {len(args['content'])} chars to {args['path']}")

    async def _edit_file(self, args: Dict[str, Any]) -> ToolResult:
        target = self._resolve(args["path"])
        if not target.exists():
            return ToolResult(False, error=f"File not found: {args['path']}")
        content = target.read_text(encoding="utf-8", errors="replace")
        old = args["old_string"]
        new = args["new_string"]
        if old not in content:
            return ToolResult(False, error="old_string not found in file")
        new_content = content.replace(old, new, 1)
        target.write_text(new_content, encoding="utf-8")
        return ToolResult(True, output=f"Edited {args['path']}")

    async def _list_directory(self, args: Dict[str, Any]) -> ToolResult:
        target = self._resolve(args["path"])
        if not target.exists():
            return ToolResult(False, error=f"Directory not found: {args['path']}")
        if not target.is_dir():
            return ToolResult(False, error="Not a directory")
        recursive = args.get("recursive", False)
        entries: List[str] = []

        def walk(dir_path: Path, prefix: str = ""):
            for item in sorted(dir_path.iterdir(), key=lambda x: (x.is_file(), x.name)):
                entries.append(f"{prefix}{item.name}")
                if item.is_dir() and recursive:
                    walk(item, prefix + item.name + "/")

        if recursive:
            walk(target)
        else:
            for item in sorted(target.iterdir(), key=lambda x: (x.is_file(), x.name)):
                entries.append(item.name + ("/" if item.is_dir() else ""))
        return ToolResult(True, output="\n".join(entries[:300]))

    async def _search_files(self, args: Dict[str, Any]) -> ToolResult:
        import re
        pattern = args["pattern"]
        root = self._resolve(args.get("path", "."))
        if not root.exists():
            return ToolResult(False, error=f"Path not found: {args.get('path', '.')}")
        matches = []
        try:
            regex = re.compile(pattern)
        except re.error as e:
            return ToolResult(False, error=f"Invalid regex: {e}")
        for file in root.rglob("*"):
            if file.is_file() and file.suffix.lower() in {
                ".py", ".ts", ".js", ".tsx", ".json", ".yaml", ".yml", ".md", ".txt", ".toml", ".cfg", ".ini"
            }:
                try:
                    text = file.read_text(encoding="utf-8", errors="ignore")
                    for i, line in enumerate(text.splitlines(), 1):
                        if regex.search(line):
                            matches.append(f"{file.relative_to(root)}:{i}: {line.strip()}")
                            if len(matches) >= 100:
                                break
                except Exception:
                    continue
            if len(matches) >= 100:
                break
        return ToolResult(True, output="\n".join(matches) if matches else "No matches")

    async def _execute_command(self, args: Dict[str, Any]) -> ToolResult:
        command = args["command"]
        timeout = args.get("timeout", Config().agent.tool_timeout)
        cwd = args.get("cwd", ".")
        cwd_path = self._resolve(cwd)
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=cwd_path,
                capture_output=True,
                text=True,
                timeout=timeout,
                env={**os.environ},
            )
            output = result.stdout.strip()
            if result.stderr.strip():
                output += "\n" + result.stderr.strip()
            success = result.returncode == 0
            return ToolResult(success=success, output=output[:20000], error="" if success else f"Exit code {result.returncode}")
        except subprocess.TimeoutExpired:
            return ToolResult(False, error=f"Command timed out after {timeout}s")
        except Exception as e:
            return ToolResult(False, error=str(e))

    async def _think(self, args: Dict[str, Any]) -> ToolResult:
        return ToolResult(True, output=f"Thought recorded: {args['thought'][:500]}")

    async def _attempt_completion(self, args: Dict[str, Any]) -> ToolResult:
        return ToolResult(True, output=args["result"], error="")
