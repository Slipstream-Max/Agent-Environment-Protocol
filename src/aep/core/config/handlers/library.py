"""
LibraryHandler - 资料库管理处理器

负责资料的添加和索引。
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional

from loguru import logger

from ..envconfig import EnvConfig


class LibraryHandler:
    """资料库管理处理器"""

    def __init__(self, config: EnvConfig):
        self.config = config

    def add(self, source: str | Path, name: Optional[str] = None) -> Path:
        """
        添加资料到配置

        Args:
            source: 资料源文件路径
            name: 资料名称，默认使用文件名

        Returns:
            资料在配置目录中的路径
        """
        source = Path(source).resolve()
        if not source.exists():
            raise FileNotFoundError(f"资料文件不存在: {source}")

        if name is None:
            name = source.name

        target = self.config.library_dir / name
        shutil.copy2(source, target)

        logger.info(f"添加资料: {name} <- {source}")
        return target

    def list(self) -> list[str]:
        """列出所有资料名称"""
        return [
            f.name
            for f in self.config.library_dir.iterdir()
            if f.is_file() and f.name != "index.md"
        ]

    def remove(self, name: str) -> bool:
        """
        删除资料

        Args:
            name: 资料名称

        Returns:
            是否删除成功
        """
        target = self.config.library_dir / name
        if target.exists():
            target.unlink()
            logger.info(f"删除资料: {name}")
            return True
        return False

    def generate_index(self) -> None:
        """生成资料索引 index.md"""
        files = self.list()

        content = "# Library\n\n"
        if files:
            content += "可用资料列表：\n\n"
            for f in sorted(files):
                content += f"- `{f}`: 使用 `cat <path_to_library>/{f}` 查看\n"
        else:
            content += "_暂无资料_\n"

        (self.config.library_dir / "index.md").write_text(content, encoding="utf-8")
