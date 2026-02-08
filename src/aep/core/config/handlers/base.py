"""
BaseHandler - 处理器基类

提供共享的 uv/venv 管理功能。
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from loguru import logger


class BaseHandler:
    """处理器基类，提供共享的 venv 管理能力"""

    def _find_uv(self) -> str:
        """查找 uv 可执行文件"""
        if shutil.which("uv"):
            return "uv"
        return "uv"

    def ensure_venv(self, venv_dir: Path) -> None:
        """
        确保虚拟环境存在（仅创建，不安装依赖）

        Args:
            venv_dir: 虚拟环境目录路径
        """
        if venv_dir.exists():
            return

        logger.info(f"创建虚拟环境: {venv_dir}")
        try:
            subprocess.run(
                [self._find_uv(), "venv", str(venv_dir)],
                cwd=str(venv_dir.parent),
                check=True,
                capture_output=True,
            )
        except FileNotFoundError:
            raise RuntimeError(
                "未找到 uv。请先安装: pip install uv 或 "
                "参考 https://docs.astral.sh/uv/getting-started/installation/"
            )

    def install_dependencies(
        self, venv_dir: Path, dependencies: list[str], work_dir: Path | None = None
    ) -> None:
        """
        安装依赖到虚拟环境

        Args:
            venv_dir: 虚拟环境目录
            dependencies: 依赖列表，支持版本约束如 ["torch==2.0.0", "numpy>=1.20"]
            work_dir: 工作目录，默认使用 venv_dir 的父目录
        """
        if not dependencies:
            return

        if work_dir is None:
            work_dir = venv_dir.parent

        logger.info(f"安装依赖: {dependencies}")
        try:
            subprocess.run(
                [self._find_uv(), "pip", "install", *dependencies],
                cwd=str(work_dir),
                env={**os.environ, "VIRTUAL_ENV": str(venv_dir)},
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"依赖安装失败: {e.stderr.decode() if e.stderr else e}")
            raise RuntimeError(f"依赖安装失败: {e}")

    def install_from_requirements(
        self, venv_dir: Path, requirements_file: Path
    ) -> None:
        """
        从 requirements.txt 安装依赖

        Args:
            venv_dir: 虚拟环境目录
            requirements_file: requirements.txt 文件路径
        """
        if not requirements_file.exists():
            return

        logger.info(f"从文件安装依赖: {requirements_file}")
        try:
            subprocess.run(
                [self._find_uv(), "pip", "install", "-r", str(requirements_file)],
                cwd=str(requirements_file.parent),
                env={**os.environ, "VIRTUAL_ENV": str(venv_dir)},
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"依赖安装失败: {e.stderr.decode() if e.stderr else e}")
            raise RuntimeError(f"依赖安装失败: {e}")

    def save_requirements(
        self, requirements_file: Path, dependencies: list[str]
    ) -> None:
        """
        保存依赖到 requirements.txt（追加模式）

        Args:
            requirements_file: requirements.txt 文件路径
            dependencies: 依赖列表
        """
        if not dependencies:
            return

        # 读取现有依赖
        existing = set()
        if requirements_file.exists():
            existing = set(
                line.strip()
                for line in requirements_file.read_text().split("\n")
                if line.strip() and not line.startswith("#")
            )

        # 添加新依赖
        existing.update(dependencies)

        # 写回文件
        requirements_file.write_text("\n".join(sorted(existing)) + "\n")
        logger.info(f"保存依赖到: {requirements_file}")
