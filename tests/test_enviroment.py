"""
工作空间测试
"""

from aep.core.enviroment import AgentEnvironment


class TestAgentEnvironment:
    """AgentEnvironment 类测试"""

    def test_init_creates_structure(self, tmp_path):
        """初始化时应创建目录结构"""
        ws_path = tmp_path / "my_aep"

        AgentEnvironment(ws_path)

        assert ws_path.exists()
        assert (ws_path / "tools").exists()
        assert (ws_path / "skills").exists()
        assert (ws_path / "library").exists()

    def test_ls_root(self, tmp_path):
        """ls / 应返回实际目录内容"""
        ws = AgentEnvironment(tmp_path / "my_aep")

        result = ws.ls("/")

        assert "tools" in result
        assert "skills" in result
        assert "library" in result

    def test_ls_empty_dir(self, tmp_path):
        """ls 空目录应返回空列表"""
        ws = AgentEnvironment(tmp_path / "my_aep")

        result = ws.ls("tools/")

        assert result == []

    def test_ls_with_files(self, tmp_path):
        """ls 应列出实际文件"""
        ws = AgentEnvironment(tmp_path / "my_aep")
        (ws.tools_path / "search.py").write_text("# search")
        (ws.tools_path / "file.py").write_text("# file")

        result = ws.ls("tools/")

        assert "search.py" in result
        assert "file.py" in result

    def test_cat_reads_file(self, tmp_path):
        """cat 应读取文件内容"""
        ws = AgentEnvironment(tmp_path / "my_aep")
        (ws.library_path / "doc.md").write_text("hello world")

        content = ws.cat("library/doc.md")

        assert content == "hello world"

    def test_cat_with_line_range(self, tmp_path):
        """cat 应支持行范围"""
        ws = AgentEnvironment(tmp_path / "my_aep")
        (ws.library_path / "doc.md").write_text("line1\nline2\nline3\nline4\nline5")

        content = ws.cat("library/doc.md", start_line=2, end_line=4)

        assert content == "line2\nline3\nline4"

    def test_cat_file_not_found(self, tmp_path):
        """cat 不存在的文件应抛出异常"""
        ws = AgentEnvironment(tmp_path / "my_aep")

        try:
            ws.cat("library/nonexistent.md")
            assert False, "Should raise FileNotFoundError"
        except FileNotFoundError:
            pass

    def test_grep_finds_matches(self, tmp_path):
        """grep 应找到匹配"""
        ws = AgentEnvironment(tmp_path / "my_aep")
        (ws.library_path / "doc.md").write_text("hello world\nfoo bar\nhello again")

        results = ws.grep("hello", "library/")

        assert len(results) == 2
        assert any("hello world" in r[2] for r in results)

    def test_grep_returns_tuples(self, tmp_path):
        """grep 应返回 (path, line_num, content) 元组"""
        ws = AgentEnvironment(tmp_path / "my_aep")
        (ws.library_path / "doc.md").write_text("test line")

        results = ws.grep("test", "library/")

        assert len(results) == 1
        path, line_num, content = results[0]
        assert "library" in path
        assert line_num == 1
        assert content == "test line"
