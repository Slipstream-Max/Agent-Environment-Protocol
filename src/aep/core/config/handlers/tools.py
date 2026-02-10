"""
ToolsHandler - 工具管理处理器

负责工具的添加、依赖管理。
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional

from loguru import logger

from ..envconfig import EnvConfig
from .base import BaseHandler


class ToolsHandler(BaseHandler):
    """工具管理处理器"""

    def __init__(self, config: EnvConfig):
        self.config = config

    def add(
        self,
        source: str | Path,
        name: Optional[str] = None,
        dependencies: Optional[list[str]] = None,
    ) -> Path:
        """
        添加工具到配置

        分离的执行顺序：
        1. 复制工具文件
        2. 保存依赖到 requirements.txt
        3. 确保 venv 存在
        4. 安装依赖

        Args:
            source: 工具源文件路径 (.py)
            name: 工具名称，默认使用文件名
            dependencies: 可选依赖列表，支持版本约束如:
                - "torch==2.0.0"
                - "numpy>=1.20"
                - "requests<=2.28,>=2.25"

        Returns:
            工具在配置目录中的路径
        """
        source = Path(source).resolve()
        if not source.exists():
            raise FileNotFoundError(f"工具文件不存在: {source}")

        if name is None:
            name = source.stem

        # 1. 复制工具文件
        target = self.config.tool_path(name)
        shutil.copy2(source, target)
        logger.info(f"添加工具: {name} <- {source}")

        # 2. 保存依赖到 requirements.txt
        if dependencies:
            self.save_requirements(self.config.tools_requirements, dependencies)

        # 3. 确保 venv 存在
        self.ensure_venv(self.config.tools_venv_dir)

        # 4. 安装依赖
        if dependencies:
            self.install_dependencies(
                self.config.tools_venv_dir,
                dependencies,
                self.config.tools_dir,
            )

        return target

    def add_dependencies(self, *packages: str) -> Path:
        """
        添加工具依赖（不添加工具）

        Args:
            *packages: 要安装的包名，支持版本约束

        Returns:
            requirements.txt 路径
        """
        dependencies = list(packages)

        # 1. 保存依赖
        self.save_requirements(self.config.tools_requirements, dependencies)

        # 2. 确保 venv 存在
        self.ensure_venv(self.config.tools_venv_dir)

        # 3. 安装依赖
        self.install_dependencies(
            self.config.tools_venv_dir,
            dependencies,
            self.config.tools_dir,
        )

        logger.info(f"添加 tools 依赖: {packages}")
        return self.config.tools_requirements

    def sync_dependencies(self) -> None:
        """
        同步依赖：确保 venv 存在并安装 requirements.txt 中的所有依赖
        """
        # 1. 确保 venv 存在
        self.ensure_venv(self.config.tools_venv_dir)

        # 2. 从 requirements.txt 安装
        self.install_from_requirements(
            self.config.tools_venv_dir,
            self.config.tools_requirements,
        )

    def list(self) -> list[str]:
        """列出所有工具名称"""
        return [
            f.stem
            for f in self.config.tools_dir.glob("*.py")
            if not f.stem.startswith("_")
        ]

    def remove(self, name: str) -> bool:
        """
        删除工具

        Args:
            name: 工具名称

        Returns:
            是否删除成功
        """
        tool_path = self.config.tool_path(name)
        if tool_path.exists():
            tool_path.unlink()
            logger.info(f"删除工具: {name}")
            return True
        return False

    def generate_index(self) -> None:
        """生成工具索引 index.md"""
        tools = self.list()

        content = "# Tools\n\n"
        if tools:
            content += "可用工具列表：\n\n"
            for tool in sorted(tools):
                # 检查是否是 MCP 工具（配置在 config_dir/_mcp/ 下）
                mcp_config_dir = self.config.mcp_config_path(tool)
                if (
                    mcp_config_dir.is_dir()
                    and (mcp_config_dir / "config.json").exists()
                ):
                    content += f'- `{tool}` (MCP): 使用 `tools run "tools.{tool}.<func>(...)"`\n'
                else:
                    content += (
                        f'- `{tool}`: 使用 `tools run "tools.{tool}.<func>(...)"`\n'
                    )
        else:
            content += "_暂无工具_\n"

        (self.config.tools_dir / "index.md").write_text(content, encoding="utf-8")
