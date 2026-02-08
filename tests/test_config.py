"""
EnvManager 及 handlers 测试
"""

import pytest
from pathlib import Path

from unittest.mock import patch

from aep import EnvManager
from aep.core.config import EnvConfig
from aep.core.config.handlers import ToolsHandler, SkillsHandler, LibraryHandler


class TestEnvConfigPaths:
    """测试 EnvConfig 路径属性"""

    def test_path_properties(self, tmp_path: Path):
        """EnvConfig 正确计算各目录路径"""
        config = EnvConfig(tmp_path / "config")

        assert config.config_dir == (tmp_path / "config").resolve()
        assert config.tools_dir == config.config_dir / "tools"
        assert config.skills_dir == config.config_dir / "skills"
        assert config.library_dir == config.config_dir / "library"
        assert config.mcp_config_dir == config.tools_dir / "_mcp"

    def test_tool_path(self, tmp_path: Path):
        """tool_path 返回正确的工具文件路径"""
        config = EnvConfig(tmp_path / "config")

        assert config.tool_path("grep") == config.tools_dir / "grep.py"

    def test_skill_paths(self, tmp_path: Path):
        """技能相关路径正确"""
        config = EnvConfig(tmp_path / "config")

        assert config.skill_dir("scraper") == config.skills_dir / "scraper"
        assert (
            config.skill_venv_dir("scraper") == config.skills_dir / "scraper" / ".venv"
        )
        assert (
            config.skill_requirements("scraper")
            == config.skills_dir / "scraper" / "requirements.txt"
        )


class TestEnvManagerInit:
    """测试 EnvManager 初始化"""

    def test_init_creates_directories(self, tmp_path: Path):
        """初始化时创建目录结构"""
        config_dir = tmp_path / "config"
        manager = EnvManager(config_dir)

        assert config_dir.exists()
        assert manager.config.tools_dir.exists()
        assert manager.config.skills_dir.exists()
        assert manager.config.library_dir.exists()
        assert manager.config.mcp_config_dir.exists()

    def test_init_with_existing_dir(self, tmp_path: Path):
        """使用已存在的目录初始化"""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        manager = EnvManager(config_dir)
        assert manager.config.config_dir == config_dir.resolve()

    def test_handlers_accessible(self, tmp_path: Path):
        """处理器可访问"""
        manager = EnvManager(tmp_path / "config")

        assert isinstance(manager.tools, ToolsHandler)
        assert isinstance(manager.skills, SkillsHandler)
        assert isinstance(manager.library, LibraryHandler)


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


class TestSkillsHandler:
    """测试 SkillsHandler"""

    @pytest.fixture
    def manager(self, tmp_path: Path) -> EnvManager:
        return EnvManager(tmp_path / "config")

    @pytest.fixture
    def sample_skill_dir(self, tmp_path: Path) -> Path:
        """创建示例技能目录"""
        skill_dir = tmp_path / "my_skill"
        skill_dir.mkdir()
        (skill_dir / "main.py").write_text('print("hello")')
        (skill_dir / "utils.py").write_text("def helper(): pass")
        return skill_dir

    @pytest.fixture
    def sample_skill_file(self, tmp_path: Path) -> Path:
        """创建示例技能单文件"""
        skill = tmp_path / "simple_skill.py"
        skill.write_text('print("simple")')
        return skill

    def test_add_skill_from_directory(
        self, manager: EnvManager, sample_skill_dir: Path
    ):
        """从目录添加技能"""
        result = manager.skills.add(sample_skill_dir)

        assert result.is_dir()
        assert result.name == "my_skill"
        assert (result / "main.py").exists()
        assert (result / "utils.py").exists()

    def test_add_skill_from_file(self, manager: EnvManager, sample_skill_file: Path):
        """从单文件添加技能"""
        result = manager.skills.add(sample_skill_file)

        assert result.is_dir()
        assert result.name == "simple_skill"
        assert (result / "main.py").exists()

    def test_add_skill_with_dependencies(
        self, manager: EnvManager, sample_skill_dir: Path
    ):
        """添加技能时指定依赖（mock 安装过程）"""
        with patch.object(manager.skills, "install_dependencies"):
            result = manager.skills.add(
                sample_skill_dir, dependencies=["requests", "pandas>=1.5"]
            )

            req_file = result / "requirements.txt"
            assert req_file.exists()
            content = req_file.read_text()
            assert "requests" in content
            assert "pandas>=1.5" in content

    def test_list_skills(self, manager: EnvManager, sample_skill_dir: Path):
        """列出所有技能"""
        manager.skills.add(sample_skill_dir)

        skills = manager.skills.list()
        assert "my_skill" in skills

    def test_remove_skill(self, manager: EnvManager, sample_skill_dir: Path):
        """删除技能"""
        manager.skills.add(sample_skill_dir)
        assert manager.skills.remove("my_skill")
        assert "my_skill" not in manager.skills.list()


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


class TestEnvManagerIndex:
    """测试 index 方法"""

    @pytest.fixture
    def manager_with_content(self, tmp_path: Path) -> EnvManager:
        """创建包含内容的配置"""
        manager = EnvManager(tmp_path / "config")

        # 添加工具
        tool = tmp_path / "grep.py"
        tool.write_text('"""grep tool"""\ndef search(): pass')
        manager.tools.add(tool)

        # 添加技能
        skill = tmp_path / "scraper"
        skill.mkdir()
        (skill / "main.py").write_text('print("scrape")')
        manager.skills.add(skill)

        # 添加资料
        doc = tmp_path / "readme.md"
        doc.write_text("# README")
        manager.library.add(doc)

        return manager

    def test_index_creates_tools_index(self, manager_with_content: EnvManager):
        """生成工具索引"""
        manager_with_content.index()

        index = manager_with_content.config.tools_dir / "index.md"
        assert index.exists()
        content = index.read_text()
        assert "grep" in content

    def test_index_creates_skills_index(self, manager_with_content: EnvManager):
        """生成技能索引"""
        manager_with_content.index()

        index = manager_with_content.config.skills_dir / "index.md"
        assert index.exists()
        content = index.read_text()
        assert "scraper" in content

    def test_index_creates_library_index(self, manager_with_content: EnvManager):
        """生成资料索引"""
        manager_with_content.index()

        index = manager_with_content.config.library_dir / "index.md"
        assert index.exists()
        content = index.read_text()
        assert "readme.md" in content


class TestEnvManagerConvenienceMethods:
    """测试 EnvManager 便捷方法（代理到处理器）"""

    @pytest.fixture
    def manager(self, tmp_path: Path) -> EnvManager:
        return EnvManager(tmp_path / "config")

    def test_add_tool_convenience(self, manager: EnvManager, tmp_path: Path):
        """add_tool 便捷方法"""
        tool = tmp_path / "calc.py"
        tool.write_text("def add(a, b): return a + b")

        result = manager.add_tool(tool)
        assert result.exists()

    def test_add_skill_convenience(self, manager: EnvManager, tmp_path: Path):
        """add_skill 便捷方法"""
        skill = tmp_path / "analyzer.py"
        skill.write_text("print('analyze')")

        result = manager.add_skill(skill)
        assert result.is_dir()

    def test_add_library_convenience(self, manager: EnvManager, tmp_path: Path):
        """add_library 便捷方法"""
        doc = tmp_path / "guide.md"
        doc.write_text("# Guide")

        result = manager.add_library(doc)
        assert result.exists()

    def test_add_tool_dependency_convenience(self, manager: EnvManager):
        """add_tool_dependency 便捷方法（mock 安装过程）"""
        with patch.object(manager.tools, "install_dependencies"):
            result = manager.add_tool_dependency("aiohttp", "websockets>=10.0")

            assert result.exists()
            content = result.read_text()
            assert "aiohttp" in content
            assert "websockets>=10.0" in content
