"""
AEP 工作空间

一个工作空间就是一个目录，提供原生文件系统操作。
"""

from __future__ import annotations

from pathlib import Path
from loguru import logger


class AgentEnvironment:
    """AEP 工作空间 - 纯文件系统操作

    一个目录就是一个工作空间，包含:
    - tools/
    - skills/
    - library/

    所有操作都是直接读取文件系统，没有额外的元数据文件。
    """

    def __init__(self, path: str | Path):
        """打开工作空间目录"""
        self.path = Path(path)
        logger.info(f"初始化工作空间: {self.path}")
        self._ensure_structure()

    def _ensure_structure(self) -> None:
        """确保基本目录结构存在"""
        if not self.path.exists():
            logger.info(f"创建工作空间目录: {self.path}")
            self.path.mkdir(parents=True, exist_ok=True)

        for subdir in ["tools", "skills", "library"]:
            target = self.path / subdir
            if not target.exists():
                logger.info(f"创建子目录: {target}")
                target.mkdir()

    # === 原生文件系统操作 ===

    def ls(self, path: str = "/") -> list[str]:
        """列出目录内容 - 直接读取文件系统"""
        logger.debug(f"ls: {path}")
        target = self._resolve_path(path)

        if not target.exists():
            logger.warning(f"ls: 路径不存在 {target}")
            return []

        if target.is_file():
            return [target.name]

        # 目录：列出所有子项
        items = sorted([f.name for f in target.iterdir()])
        logger.debug(f"ls 结果: {len(items)} items")
        return items

    def cat(
        self, path: str, start_line: int | None = None, end_line: int | None = None
    ) -> str:
        """读取文件内容 - 直接读取文件系统"""
        logger.debug(f"cat: {path} (lines {start_line}-{end_line})")
        target = self._resolve_path(path)

        if not target.exists():
            logger.error(f"cat: 文件不存在 {target}")
            raise FileNotFoundError(f"File not found: {path}")

        if not target.is_file():
            logger.error(f"cat: 路径不是文件 {target}")
            raise IsADirectoryError(f"Is a directory: {path}")

        content = target.read_text(encoding="utf-8")

        # 处理行范围
        if start_line is not None or end_line is not None:
            lines = content.splitlines()
            start = (start_line or 1) - 1  # 转为 0-indexed
            end = end_line or len(lines)
            content = "\n".join(lines[start:end])

        logger.debug(f"cat 读取了 {len(content)} 字符")
        return content

    def grep(self, pattern: str, path: str = "/") -> list[tuple[str, int, str]]:
        """搜索文件内容 - 直接读取文件系统

        Returns:
            list of (relative_path, line_number, line_content)
        """
        import re

        logger.debug(f"grep: pattern='{pattern}' path='{path}'")
        target = self._resolve_path(path)
        results: list[tuple[str, int, str]] = []

        if not target.exists():
            logger.warning(f"grep: 路径不存在 {target}")
            return results

        try:
            regex = re.compile(pattern, re.IGNORECASE)
        except re.error as e:
            logger.error(f"grep: 无效正则 {e}")
            raise ValueError(f"Invalid regex pattern: {e}")

        # 确定搜索范围
        if target.is_file():
            files = [target]
        else:
            files = list(target.rglob("*"))

        for file_path in files:
            if not file_path.is_file():
                continue
            if file_path.suffix not in [".md", ".py", ".txt", ".yaml", ".json"]:
                continue

            try:
                content = file_path.read_text(encoding="utf-8")
                for i, line in enumerate(content.splitlines(), 1):
                    if regex.search(line):
                        rel_path = str(file_path.relative_to(self.path))
                        results.append((rel_path, i, line.strip()))
            except Exception as e:
                logger.warning(f"grep: 读取错误 {file_path}: {e}")

        logger.debug(f"grep 找到 {len(results)} 个匹配")
        return results

    def exists(self, path: str) -> bool:
        """检查路径是否存在"""
        return self._resolve_path(path).exists()

    def is_file(self, path: str) -> bool:
        """检查是否是文件"""
        return self._resolve_path(path).is_file()

    def is_dir(self, path: str) -> bool:
        """检查是否是目录"""
        return self._resolve_path(path).is_dir()

    def _resolve_path(self, path: str) -> Path:
        """解析虚拟路径到物理路径"""
        path = path.strip("/")
        if path == "" or path == ".":
            return self.path
        return self.path / path

    # === 便捷属性 ===

    @property
    def tools_path(self) -> Path:
        return self.path / "tools"

    @property
    def skills_path(self) -> Path:
        return self.path / "skills"

    @property
    def library_path(self) -> Path:
        return self.path / "library"
