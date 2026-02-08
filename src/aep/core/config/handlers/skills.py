"""
SkillsHandler - 技能管理处理器

负责技能的添加、依赖管理。
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional

from loguru import logger

from ..envconfig import EnvConfig
from .base import BaseHandler


class SkillsHandler(BaseHandler):
    """技能管理处理器"""

    def __init__(self, config: EnvConfig):
        self.config = config

    def add(
        self,
        source: str | Path,
        name: Optional[str] = None,
        dependencies: Optional[list[str]] = None,
    ) -> Path:
        """
        添加技能到配置

        Args:
            source: 技能源目录或入口文件
            name: 技能名称，默认使用目录名
            dependencies: Python 依赖列表，支持版本约束

        Returns:
            技能在配置目录中的路径
        """
        source = Path(source).resolve()

        if source.is_file():
            # 单文件技能，创建目录包装
            if name is None:
                name = source.stem
            skill_dir = self.config.skill_dir(name)
            skill_dir.mkdir(exist_ok=True)
            shutil.copy2(source, skill_dir / "main.py")
        elif source.is_dir():
            # 目录技能，整体复制
            if name is None:
                name = source.name
            skill_dir = self.config.skill_dir(name)
            if skill_dir.exists():
                shutil.rmtree(skill_dir)
            shutil.copytree(source, skill_dir)
        else:
            raise FileNotFoundError(f"技能源不存在: {source}")

        logger.info(f"添加技能: {name} <- {source}")

        # 保存依赖到 requirements.txt
        if dependencies:
            self.save_requirements(
                self.config.skill_requirements(name),
                dependencies,
            )

        # 确保 venv 存在
        self.ensure_venv(self.config.skill_venv_dir(name))

        # 安装依赖
        if dependencies:
            self.install_dependencies(
                self.config.skill_venv_dir(name),
                dependencies,
                skill_dir,
            )

        return skill_dir

    def sync_dependencies(self, name: str) -> None:
        """
        同步特定技能的依赖

        Args:
            name: 技能名称
        """
        skill_dir = self.config.skill_dir(name)
        if not skill_dir.exists():
            raise FileNotFoundError(f"技能不存在: {name}")

        # 确保 venv 存在
        self.ensure_venv(self.config.skill_venv_dir(name))

        # 从 requirements.txt 安装
        self.install_from_requirements(
            self.config.skill_venv_dir(name),
            self.config.skill_requirements(name),
        )

    def list(self) -> list[str]:
        """列出所有技能名称"""
        return [
            d.name
            for d in self.config.skills_dir.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        ]

    def remove(self, name: str) -> bool:
        """
        删除技能

        Args:
            name: 技能名称

        Returns:
            是否删除成功
        """
        skill_dir = self.config.skill_dir(name)
        if skill_dir.exists():
            shutil.rmtree(skill_dir)
            logger.info(f"删除技能: {name}")
            return True
        return False

    def generate_index(self) -> None:
        """生成技能索引 index.md"""
        skills = self.list()

        content = "# Skills\n\n"
        if skills:
            content += "可用技能列表：\n\n"
            for skill in sorted(skills):
                content += (
                    f"- `{skill}`: 使用 `skills run {skill}/main.py [args]` 调用\n"
                )
        else:
            content += "_暂无技能_\n"

        (self.config.skills_dir / "index.md").write_text(content, encoding="utf-8")
