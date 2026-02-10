"""
EnvConfig 路径属性测试
"""

from pathlib import Path

from aep.core.config import EnvConfig


class TestEnvConfigPaths:
    """测试 EnvConfig 路径属性"""

    def test_path_properties(self, tmp_path: Path):
        """EnvConfig 正确计算各目录路径"""
        config = EnvConfig(tmp_path / "config")

        assert config.config_dir == (tmp_path / "config").resolve()
        assert config.tools_dir == config.config_dir / "tools"
        assert config.skills_dir == config.config_dir / "skills"
        assert config.library_dir == config.config_dir / "library"
        assert config.mcp_config_dir == config.config_dir / "_mcp"
        assert config.mcp_config_path("test") == config.mcp_config_dir / "test"
        assert config.mcp_skill_dir("test") == config.skills_dir / "test"
        assert config.mcp_library_dir("test") == config.library_dir / "test"

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
