"""
SkillsHandler - 技能管理处理器

负责技能的添加、依赖管理。
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional

from loguru import logger
from aep.core.config.handlers.skills_util.parser import parse_frontmatter, read_properties
from aep.core.config.handlers.skills_util.validator import validate

from ..envconfig import EnvConfig
from .base import BaseHandler


class SkillsHandler(BaseHandler):
    """技能管理处理器"""

    def __init__(self, config: EnvConfig):
        self.config = config

    def _validate_skill(self, skill_dir: Path) -> None:
        """使用本地 skills-ref 验证器校验技能目录。"""
        errors = validate(skill_dir)
        if errors:
            details = "\n".join(f"- {error}" for error in errors)
            raise ValueError(
                f"技能 `{skill_dir.name}` 不符合 Agent Skills 规范:\n{details}"
            )

    def _skill_name_from_single_md(self, source: Path) -> str:
        """从单文件 SKILL.md 读取 frontmatter 的 name 字段。"""
        if source.suffix.lower() != ".md":
            raise ValueError("单文件技能仅支持 .md（SKILL.md）输入")

        content = source.read_text(encoding="utf-8")
        metadata, _ = parse_frontmatter(content)
        skill_name = metadata.get("name")
        if not isinstance(skill_name, str) or not skill_name.strip():
            raise ValueError("单文件 SKILL.md 缺少有效的 name 字段")

        return skill_name.strip()

    def add(
        self,
        source: str | Path,
        name: Optional[str] = None,
        dependencies: Optional[list[str]] = None,
    ) -> Path:
        """
        添加技能到配置

        Args:
            source: 技能源目录或单文件 SKILL.md
            name: 技能名称，默认使用目录名
            dependencies: Python 依赖列表，支持版本约束

        Returns:
            技能在配置目录中的路径
        """
        source = Path(source).resolve()

        if source.is_file():
            # 单文件技能：只接受 SKILL.md，并用 frontmatter.name 作为目录名
            parsed_name = self._skill_name_from_single_md(source)
            if name is not None and name != parsed_name:
                raise ValueError(
                    f"单文件技能 name 参数应与 SKILL.md 的 name 一致: "
                    f"{name} != {parsed_name}"
                )
            name = parsed_name
            skill_dir = self.config.skill_dir(name)
            if skill_dir.exists():
                shutil.rmtree(skill_dir)
            skill_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, skill_dir / "SKILL.md")
            logger.warning(
                f"检测到单文件技能，已按 name={name} 写入 skills/{name}/SKILL.md"
            )
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

        try:
            self._validate_skill(skill_dir)
        except Exception:
            # 避免保留不合法技能目录
            if skill_dir.exists():
                shutil.rmtree(skill_dir)
            raise

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
            content += "可用技能列表（name / description / path）：\n\n"
            for skill in sorted(skills):
                skill_dir = self.config.skill_dir(skill)
                try:
                    props = read_properties(skill_dir)
                    description = " ".join(props.description.split())
                    content += (
                        f"- `{props.name}`: {description} "
                        f"(path: `{skill_dir.name}/`)\n"
                    )
                except Exception as exc:
                    logger.warning(f"技能索引解析失败 {skill_dir}: {exc}")
                    content += f"- `{skill}`: (path: `{skill_dir.name}/`)\n"

            content += "\n运行 Python 脚本请使用：`skills run xx.py`\n"
        else:
            content += "_暂无技能_\n"

        (self.config.skills_dir / "index.md").write_text(content, encoding="utf-8")
