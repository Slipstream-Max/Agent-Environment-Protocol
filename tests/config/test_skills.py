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
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "main.py").write_text('print("hello")')
        (skill_dir / "utils.py").write_text("def helper(): pass")
        (skill_dir / "SKILL.md").write_text(
            """---
name: my-skill
description: Test skill for handler unit tests.
---
"""
        )
        return skill_dir

    @pytest.fixture
    def sample_skill_file(self, tmp_path: Path) -> Path:
        """创建示例技能单文件"""
        skill = tmp_path / "single-skill.md"
        skill.write_text(
            """---
name: single-skill
description: Single file skill used for tests.
---

# Single Skill
"""
        )
        return skill

    def test_add_skill_from_directory(
        self, manager: EnvManager, sample_skill_dir: Path
    ):
        """从目录添加技能"""
        result = manager.skills.add(sample_skill_dir)

        assert result.is_dir()
        assert result.name == "my-skill"
        assert (result / "main.py").exists()
        assert (result / "utils.py").exists()

    def test_add_skill_from_file(self, manager: EnvManager, sample_skill_file: Path):
        """从单文件添加技能"""
        result = manager.skills.add(sample_skill_file)

        assert result.is_dir()
        assert result.name == "single-skill"
        assert (result / "SKILL.md").exists()

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

    def test_add_skill_single_file_requires_md(self, manager: EnvManager, tmp_path: Path):
        """单文件技能仅允许 md"""
        bad_file = tmp_path / "bad.py"
        bad_file.write_text("print('bad')")

        with pytest.raises(ValueError):
            manager.skills.add(bad_file)

    def test_add_skill_single_file_name_must_match_frontmatter(
        self, manager: EnvManager, sample_skill_file: Path
    ):
        """单文件技能目录名必须来自 frontmatter.name"""
        with pytest.raises(ValueError):
            manager.skills.add(sample_skill_file, name="another-name")

    def test_list_skills(self, manager: EnvManager, sample_skill_dir: Path):
        """列出所有技能"""
        manager.skills.add(sample_skill_dir)

        skills = manager.skills.list()
        assert "my-skill" in skills

    def test_remove_skill(self, manager: EnvManager, sample_skill_dir: Path):
        """删除技能"""
        manager.skills.add(sample_skill_dir)
        assert manager.skills.remove("my-skill")
        assert "my-skill" not in manager.skills.list()

    def test_generate_index_uses_name_description_and_path(
        self, manager: EnvManager, sample_skill_file: Path
    ):
        """索引包含 name/description/path 与统一运行提示"""
        manager.skills.add(sample_skill_file)
        manager.skills.generate_index()

        index_file = manager.skills_dir / "index.md"
        content = index_file.read_text(encoding="utf-8")
        assert "single-skill" in content
        assert "Single file skill used for tests." in content
        assert "single-skill/" in content
        assert "skills run xx.py" in content
