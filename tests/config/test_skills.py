"""
SkillsHandler 测试
"""

import pytest
from pathlib import Path

from unittest.mock import patch

from aep import EnvManager


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
