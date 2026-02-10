"""
LibraryHandler 测试
"""

import pytest
from pathlib import Path

from aep import EnvManager


class TestLibraryHandler:
    """测试 LibraryHandler"""

    @pytest.fixture
    def manager(self, tmp_path: Path) -> EnvManager:
        return EnvManager(tmp_path / "config")

    @pytest.fixture
    def sample_doc(self, tmp_path: Path) -> Path:
        """创建示例文档"""
        doc = tmp_path / "api.md"
        doc.write_text("# API Documentation\n\nSome content here.")
        return doc

    def test_add_library_copies_file(self, manager: EnvManager, sample_doc: Path):
        """添加资料会复制文件"""
        result = manager.library.add(sample_doc)

        assert result.exists()
        assert result.name == "api.md"
        assert result.parent == manager.config.library_dir

    def test_add_library_with_custom_name(self, manager: EnvManager, sample_doc: Path):
        """指定自定义名称"""
        result = manager.library.add(sample_doc, name="docs.md")

        assert result.name == "docs.md"

    def test_list_library(self, manager: EnvManager, sample_doc: Path):
        """列出所有资料"""
        manager.library.add(sample_doc)

        files = manager.library.list()
        assert "api.md" in files

    def test_remove_library(self, manager: EnvManager, sample_doc: Path):
        """删除资料"""
        manager.library.add(sample_doc)
        assert manager.library.remove("api.md")
        assert "api.md" not in manager.library.list()
