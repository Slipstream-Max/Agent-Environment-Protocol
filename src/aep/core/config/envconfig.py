"""
EnvConfig - 纯环境配置数据模型

只负责定义配置结构和路径，不包含任何业务逻辑。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class ToolConfig:
    """单个工具的配置"""

    name: str
    source: Path
    dependencies: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "source": str(self.source),
            "dependencies": self.dependencies,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ToolConfig":
        return cls(
            name=data["name"],
            source=Path(data["source"]),
            dependencies=data.get("dependencies", []),
        )


@dataclass
class SkillConfig:
    """单个技能的配置"""

    name: str
    source: Path
    dependencies: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "source": str(self.source),
            "dependencies": self.dependencies,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SkillConfig":
        return cls(
            name=data["name"],
            source=Path(data["source"]),
            dependencies=data.get("dependencies", []),
        )


@dataclass
class LibraryConfig:
    """单个资料的配置"""

    name: str
    source: Path

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "source": str(self.source),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LibraryConfig":
        return cls(
            name=data["name"],
            source=Path(data["source"]),
        )


@dataclass
class MCPServerConfig:
    """MCP 服务器配置"""

    name: str
    transport: str  # "stdio" | "http"
    # STDIO 模式
    command: Optional[list[str]] = None
    env: dict[str, str] = field(default_factory=dict)
    # HTTP 模式
    url: Optional[str] = None
    headers: dict[str, str] = field(default_factory=dict)
    # 工具定义
    tools: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "transport": self.transport,
            "command": self.command,
            "env": self.env,
            "url": self.url,
            "headers": self.headers,
            "tools": self.tools,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MCPServerConfig":
        return cls(
            name=data["name"],
            transport=data["transport"],
            command=data.get("command"),
            env=data.get("env", {}),
            url=data.get("url"),
            headers=data.get("headers", {}),
            tools=data.get("tools", []),
        )


@dataclass
class EnvConfig:
    """
    环境配置数据结构

    纯数据模型，定义配置目录结构和各项配置数据。
    """

    config_dir: Path

    def __post_init__(self):
        self.config_dir = Path(self.config_dir).resolve()

    # === 目录路径属性 ===

    @property
    def tools_dir(self) -> Path:
        """工具目录"""
        return self.config_dir / "tools"

    @property
    def tools_venv_dir(self) -> Path:
        """工具虚拟环境目录"""
        return self.tools_dir / ".venv"

    @property
    def tools_requirements(self) -> Path:
        """工具依赖文件"""
        return self.tools_dir / "requirements.txt"

    @property
    def skills_dir(self) -> Path:
        """技能目录"""
        return self.config_dir / "skills"

    @property
    def library_dir(self) -> Path:
        """资料库目录"""
        return self.config_dir / "library"

    @property
    def mcp_config_dir(self) -> Path:
        """MCP 配置存储目录 (config_dir/_mcp/)，不挂载到工作区"""
        return self.config_dir / "_mcp"

    # === 辅助方法 ===

    def skill_dir(self, name: str) -> Path:
        """获取特定技能的目录"""
        return self.skills_dir / name

    def skill_venv_dir(self, name: str) -> Path:
        """获取特定技能的虚拟环境目录"""
        return self.skill_dir(name) / ".venv"

    def skill_requirements(self, name: str) -> Path:
        """获取特定技能的依赖文件"""
        return self.skill_dir(name) / "requirements.txt"

    def tool_path(self, name: str) -> Path:
        """获取工具文件路径"""
        return self.tools_dir / f"{name}.py"

    def mcp_config_path(self, name: str) -> Path:
        """获取 MCP 服务器配置目录路径"""
        return self.mcp_config_dir / name

    def __repr__(self) -> str:
        return f"EnvConfig({self.config_dir})"
