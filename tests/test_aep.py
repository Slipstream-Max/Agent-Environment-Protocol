"""
AEP 主类测试
"""

from aep import AEP


class TestAEP:
    """AEP 类测试"""

    def test_init_creates_workspace(self, tmp_path):
        """初始化应创建工作空间"""
        aep = AEP(tmp_path / "my_aep")

        assert aep.path.exists()

    def test_ls_delegates_to_workspace(self, tmp_path):
        """ls 应代理给 workspace"""
        aep = AEP(tmp_path / "my_aep")

        result = aep.ls("/")

        assert "tools" in result
        assert "skills" in result
        assert "library" in result

    def test_cat_delegates_to_workspace(self, tmp_path):
        """cat 应代理给 workspace"""
        aep = AEP(tmp_path / "my_aep")
        (aep.path / "library" / "doc.md").write_text("hello")

        result = aep.cat("library/doc.md")

        assert result == "hello"

    def test_grep_delegates_to_workspace(self, tmp_path):
        """grep 应代理给 workspace"""
        aep = AEP(tmp_path / "my_aep")
        (aep.path / "library" / "doc.md").write_text("hello world")

        result = aep.grep("hello")

        assert len(result) == 1

    def test_as_tools_returns_schema(self, tmp_path):
        """as_tools 应返回 function calling schema"""
        aep = AEP(tmp_path / "my_aep")

        tools = aep.as_tools()

        assert len(tools) == 5
        names = [t["function"]["name"] for t in tools]
        assert "aep_ls" in names
        assert "aep_cat" in names
        assert "aep_grep" in names

    def test_execute_aep_ls(self, tmp_path):
        """execute aep_ls"""
        aep = AEP(tmp_path / "my_aep")

        result = aep.execute("aep_ls", {"path": "/"})

        assert "tools" in result

    def test_execute_aep_cat(self, tmp_path):
        """execute aep_cat"""
        aep = AEP(tmp_path / "my_aep")
        (aep.path / "library" / "doc.md").write_text("content")

        result = aep.execute("aep_cat", {"path": "library/doc.md"})

        assert result == "content"

    def test_execute_aep_grep(self, tmp_path):
        """execute aep_grep"""
        aep = AEP(tmp_path / "my_aep")
        (aep.path / "library" / "doc.md").write_text("hello world")

        result = aep.execute("aep_grep", {"pattern": "hello"})

        assert "hello world" in result
