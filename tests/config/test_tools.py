"""
ToolsHandler 测试
"""

import pytest
from pathlib import Path

from unittest.mock import patch

from aep import EnvManager


class TestToolsHandler:
    """测试 ToolsHandler"""

    @pytest.fixture
    def manager(self, tmp_path: Path) -> EnvManager:
        return EnvManager(tmp_path / "config")

    @pytest.fixture
    def sample_tool(self, tmp_path: Path) -> Path:
        """创建示例工具文件"""
        tool = tmp_path / "my_tool.py"
        tool.write_text('"""My tool"""\ndef func(): pass')
        return tool

    def test_add_tool_copies_file(self, manager: EnvManager, sample_tool: Path):
        """添加工具会复制文件"""
        result = manager.tools.add(sample_tool)

        assert result.exists()
        assert result.name == "my_tool.py"
        assert result.parent == manager.config.tools_dir

    def test_add_tool_with_custom_name(self, manager: EnvManager, sample_tool: Path):
        """指定自定义名称"""
        result = manager.tools.add(sample_tool, name="custom")

        assert result.name == "custom.py"

    def test_add_tool_with_dependencies(self, manager: EnvManager, sample_tool: Path):
        """添加工具时指定依赖（mock 安装过程）"""
        with patch.object(manager.tools, "install_dependencies"):
            result = manager.tools.add(
                sample_tool, dependencies=["requests>=2.25", "numpy==1.20.0"]
            )

            assert result.exists()
            req_file = manager.config.tools_requirements
            assert req_file.exists()
            content = req_file.read_text()
            assert "requests>=2.25" in content
            assert "numpy==1.20.0" in content

    def test_add_tool_nonexistent_file_raises(
        self, manager: EnvManager, tmp_path: Path
    ):
        """添加不存在的文件抛出异常"""
        with pytest.raises(FileNotFoundError):
            manager.tools.add(tmp_path / "nonexistent.py")

    def test_list_tools(self, manager: EnvManager, sample_tool: Path):
        """列出所有工具"""
        manager.tools.add(sample_tool)

        tools = manager.tools.list()
        assert "my_tool" in tools

    def test_remove_tool(self, manager: EnvManager, sample_tool: Path):
        """删除工具"""
        manager.tools.add(sample_tool)
        assert manager.tools.remove("my_tool")
        assert "my_tool" not in manager.tools.list()

    def test_add_dependencies_only(self, manager: EnvManager):
        """只添加依赖不添加工具（mock 安装过程）"""
        with patch.object(manager.tools, "install_dependencies"):
            manager.tools.add_dependencies("httpx", "pydantic>=2.0")

            req_file = manager.config.tools_requirements
            assert req_file.exists()
            content = req_file.read_text()
            assert "httpx" in content
            assert "pydantic>=2.0" in content
