"""
EnvManager - 环境配置管理器

统一管理工具、技能、资料库、MCP 的高层接口。
"""

from __future__ import annotations

from pathlib import Path

from loguru import logger

from .envconfig import EnvConfig
from .handlers import ToolsHandler, SkillsHandler, LibraryHandler, MCPHandler


class EnvManager:
    """
    环境配置管理器

    提供统一的接口来管理工具、技能、资料库和 MCP 服务器。

    目录结构：
    config_dir/
    ├── tools/
    │   ├── .venv/            # 共享虚拟环境 (uv 管理)
    │   ├── requirements.txt  # 依赖清单
    │   ├── index.md          # 工具列表
    │   └── grep.py           # Python 工具 / MCP stub
    ├── skills/
    │   ├── index.md
    │   └── web-scraper/      # 普通技能
    │       ├── .venv/
    │       ├── SKILL.md
    │       └── main.py
    ├── library/
    │   ├── index.md
    │   └── api-docs.md
    └── _mcp/                 # MCP 服务器配置（不挂载到工作区）
        └── figma/
            └── config.json
    """

    DEFAULT_TOOL_DEPENDENCIES = (
        "numpy",
        "pandas",
        "matplotlib",
        "mcp",
    )

    def __init__(
        self,
        config_dir: str | Path,
        *,
        auto_init_tool_env: bool = False,
        include_default_tool_dependencies: bool = True,
        tool_dependencies: list[str] | None = None,
    ):
        """
        初始化配置管理器

        Args:
            config_dir: 配置目录路径，将自动创建子目录结构
            auto_init_tool_env: 是否在初始化时自动准备 tools 环境
            include_default_tool_dependencies: 自动初始化时是否包含默认依赖
            tool_dependencies: 自动初始化时追加的自定义依赖
        """
        self.config = EnvConfig(config_dir)

        # 初始化处理器
        self._tools = ToolsHandler(self.config)
        self._skills = SkillsHandler(self.config)
        self._library = LibraryHandler(self.config)
        self._mcp = MCPHandler(self.config)

        # 创建目录结构
        self._init_dirs()

        if auto_init_tool_env:
            self.init_tool_environment(
                dependencies=tool_dependencies,
                include_default=include_default_tool_dependencies,
            )

        logger.info(f"EnvManager 初始化: {self.config.config_dir}")

    def _init_dirs(self) -> None:
        """创建配置目录结构"""
        self.config.config_dir.mkdir(parents=True, exist_ok=True)
        self.config.tools_dir.mkdir(exist_ok=True)
        self.config.skills_dir.mkdir(exist_ok=True)
        self.config.library_dir.mkdir(exist_ok=True)
        self.config.mcp_config_dir.mkdir(exist_ok=True)

    # === 处理器访问 ===

    @property
    def tools(self) -> ToolsHandler:
        """工具处理器"""
        return self._tools

    @property
    def skills(self) -> SkillsHandler:
        """技能处理器"""
        return self._skills

    @property
    def library(self) -> LibraryHandler:
        """资料库处理器"""
        return self._library

    @property
    def mcp(self) -> MCPHandler:
        """MCP 处理器"""
        return self._mcp

    # === 便捷方法（代理到处理器）===

    def add_tool(self, source, name=None, dependencies=None):
        """添加工具（代理到 tools.add）"""
        return self._tools.add(source, name, dependencies)

    def add_skill(self, source, name=None, dependencies=None):
        """添加技能（代理到 skills.add）"""
        return self._skills.add(source, name, dependencies)

    def add_library(self, source, name=None):
        """添加资料（代理到 library.add）"""
        return self._library.add(source, name)

    def add_mcp_server(self, name, **kwargs):
        """添加 MCP 服务器（代理到 mcp.add）

        连接 MCP 服务器，自动发现 tools。
        详细参数见 MCPHandler.add()
        """
        return self._mcp.add(name, **kwargs)

    def add_tool_dependency(self, *packages):
        """添加工具依赖（代理到 tools.add_dependencies）"""
        return self._tools.add_dependencies(*packages)

    def init_tool_environment(
        self,
        *,
        dependencies: list[str] | None = None,
        include_default: bool = True,
    ) -> Path:
        """
        初始化 tools 运行环境（venv + 默认/自定义依赖）

        Args:
            dependencies: 额外依赖列表
            include_default: 是否包含默认依赖

        Returns:
            tools/requirements.txt 路径
        """
        deps: list[str] = []
        if include_default:
            deps.extend(self.DEFAULT_TOOL_DEPENDENCIES)
        if dependencies:
            deps.extend(dependencies)

        # 去重并移除空字符串
        unique_deps = list(dict.fromkeys(d for d in deps if d and d.strip()))

        if unique_deps:
            logger.info(f"初始化 tools 环境依赖: {unique_deps}")
            return self._tools.add_dependencies(*unique_deps)

        # 仅创建 venv（无依赖）
        self._tools.ensure_venv(self.config.tools_venv_dir)
        return self.config.tools_requirements

    # === 索引生成 ===

    def index(self) -> None:
        """生成所有索引文件"""
        self._tools.generate_index()
        self._skills.generate_index()
        self._library.generate_index()
        logger.info("索引生成完成")

    # === 目录路径属性（代理）===

    @property
    def config_dir(self) -> Path:
        return self.config.config_dir

    @property
    def tools_dir(self) -> Path:
        return self.config.tools_dir

    @property
    def skills_dir(self) -> Path:
        return self.config.skills_dir

    @property
    def library_dir(self) -> Path:
        return self.config.library_dir

    def __repr__(self) -> str:
        return f"EnvManager({self.config.config_dir})"
