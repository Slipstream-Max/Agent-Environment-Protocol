"""
EnvManager 初始化、索引、便捷方法测试
"""

import pytest
from pathlib import Path

from unittest.mock import patch

from aep import EnvManager
from aep.core.config.handlers import ToolsHandler, SkillsHandler, LibraryHandler


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
        (skill / "SKILL.md").write_text(
            """---
name: scraper
description: Scrape content from test pages.
---
"""
        )
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
        assert "Scrape content from test pages." in content
        assert "scraper/" in content
        assert "skills run xx.py" in content

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
        skill = tmp_path / "analyzer.md"
        skill.write_text(
            """---
name: analyzer
description: Analyze data from markdown-only skill.
---

# Analyzer
"""
        )

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


class TestEnvManagerToolEnvironment:
    """测试 tools 环境初始化"""

    def test_init_tool_environment_with_defaults(self, tmp_path: Path):
        """默认初始化应写入内置依赖"""
        manager = EnvManager(tmp_path / "config")

        with patch.object(manager.tools, "ensure_venv"), patch.object(
            manager.tools, "install_dependencies"
        ):
            req = manager.init_tool_environment()

        content = req.read_text(encoding="utf-8")
        assert "numpy" in content
        assert "pandas" in content
        assert "matplotlib" in content
        assert "mcp" in content

    def test_init_tool_environment_with_custom_dependencies(self, tmp_path: Path):
        """支持追加自定义依赖并去重"""
        manager = EnvManager(tmp_path / "config")

        with patch.object(manager.tools, "ensure_venv"), patch.object(
            manager.tools, "install_dependencies"
        ):
            req = manager.init_tool_environment(
                dependencies=["seaborn", "numpy"],
                include_default=True,
            )

        lines = {
            line.strip()
            for line in req.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        assert "seaborn" in lines
        assert "numpy" in lines
        assert len([x for x in lines if x == "numpy"]) == 1

    def test_auto_init_tool_env_calls_initializer(self, tmp_path: Path):
        """auto_init_tool_env=True 时初始化会自动触发"""
        with patch(
            "aep.core.config.envmanager.EnvManager.init_tool_environment"
        ) as init_env:
            EnvManager(
                tmp_path / "config",
                auto_init_tool_env=True,
                include_default_tool_dependencies=False,
                tool_dependencies=["mcp"],
            )

        init_env.assert_called_once_with(
            dependencies=["mcp"],
            include_default=False,
        )
