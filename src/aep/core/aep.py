"""
AEP 主类

提供统一的能力发现和调用接口。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from loguru import logger
from aep.core.enviroment import AgentEnvironment


class AEP:
    """Agent Environment Protocol

    Example:
        >>> aep = AEP("./my_aep")
        >>> aep.ls("tools/")
        >>> aep.cat("tools/search/function.py")
    """

    def __init__(self, path: str | Path):
        """初始化 AEP

        Args:
            path: 工作空间目录路径
        """
        logger.info(f"初始化 AEP: {path}")
        self._agent_environment = AgentEnvironment(path)

    # === 能力管理 (TODO: Phase 2+) ===

    def add_tool(self, source: str) -> None:
        """添加工具"""
        logger.info(f"add_tool: {source}")
        raise NotImplementedError("Phase 2")

    def add_skill(self, folder: str) -> None:
        """添加技能"""
        logger.info(f"add_skill: {folder}")
        raise NotImplementedError("Phase 4")

    def add_library(self, file: str) -> None:
        """添加文档"""
        logger.info(f"add_library: {file}")
        raise NotImplementedError("Phase 5")

    # === 虚拟文件系统 (代理给 AgentEnvironment) ===

    def ls(self, path: str = "/") -> list[str]:
        """列出目录"""
        return self._agent_environment.ls(path)

    def cat(
        self, path: str, start_line: int | None = None, end_line: int | None = None
    ) -> str:
        """读取文件"""
        return self._agent_environment.cat(path, start_line, end_line)

    def grep(self, pattern: str, path: str = "/") -> list[tuple[str, int, str]]:
        """搜索内容"""
        return self._agent_environment.grep(pattern, path)

    # === Agent 接口 ===

    def as_tools(self) -> list[dict[str, Any]]:
        """返回 OpenAI function calling 格式的 schema"""
        # schema 定义太长，这里不再打印日志
        return [
            {
                "type": "function",
                "function": {
                    "name": "aep_ls",
                    "description": "列出 AEP 虚拟目录内容",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "路径"}
                        },
                        "required": ["path"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "aep_cat",
                    "description": "读取文件内容",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "文件路径"},
                            "start_line": {"type": "integer", "description": "起始行"},
                            "end_line": {"type": "integer", "description": "结束行"},
                        },
                        "required": ["path"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "aep_grep",
                    "description": "搜索内容",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "pattern": {"type": "string", "description": "正则模式"},
                            "path": {"type": "string", "description": "搜索范围"},
                        },
                        "required": ["pattern"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "aep_tools",
                    "description": "执行 Python 代码调用工具",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "code": {"type": "string", "description": "Python 代码"}
                        },
                        "required": ["code"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "aep_skills",
                    "description": "执行技能脚本",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "脚本路径"},
                            "args": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "参数",
                            },
                        },
                        "required": ["path"],
                    },
                },
            },
        ]

    def execute(self, name: str, arguments: dict[str, Any]) -> str:
        """执行 function call"""
        logger.info(f"Execute: {name} args={arguments}")
        try:
            if name == "aep_ls":
                items = self.ls(arguments.get("path", "/"))
                return ", ".join(items) if items else "(empty)"

            elif name == "aep_cat":
                return self.cat(
                    arguments["path"],
                    arguments.get("start_line"),
                    arguments.get("end_line"),
                )

            elif name == "aep_grep":
                results = self.grep(arguments["pattern"], arguments.get("path", "/"))
                if not results:
                    return "(no matches)"
                return "\n".join(f"{p}:{n}: {c}" for p, n, c in results)

            elif name == "aep_tools":
                # TODO: Phase 2
                logger.warning(
                    f"NotImplemented: aep_tools code={arguments.get('code')}"
                )
                return f"NotImplemented: {arguments.get('code')}"

            elif name == "aep_skills":
                # TODO: Phase 4
                logger.warning(
                    f"NotImplemented: aep_skills path={arguments.get('path')}"
                )
                return f"NotImplemented: {arguments.get('path')}"

            else:
                logger.error(f"Unknown function: {name}")
                return f"Error: Unknown function '{name}'"

        except Exception as e:
            logger.exception(f"Execution error: {e}")
            return f"Error: {e}"

    # === 属性 ===

    @property
    def path(self) -> Path:
        return self._agent_environment.path

    @property
    def workspace(self) -> AgentEnvironment:
        return self._agent_environment
