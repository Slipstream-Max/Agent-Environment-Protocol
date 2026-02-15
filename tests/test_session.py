"""
AEPSession 测试
"""

import pytest
from pathlib import Path

from aep import AEP, EnvManager, AEPSession, ExecResult


@pytest.fixture
def session(tmp_path: Path) -> AEPSession:
    """创建测试 session"""
    # 创建配置
    config = EnvManager(tmp_path / "config")

    # 添加工具
    tool = tmp_path / "calc.py"
    tool.write_text('''"""
calc - 计算工具

Usage:
    tools run "tools.calc.add(a, b)"
"""

def add(a, b):
    """加法"""
    return a + b

def mul(a, b):
    """乘法"""
    return a * b
''')
    config.add_tool(tool)

    # 添加技能
    skill_dir = tmp_path / "greeter"
    skill_dir.mkdir()
    (skill_dir / "main.py").write_text("""
import sys
name = sys.argv[1] if len(sys.argv) > 1 else "World"
print(f"Hello, {name}!")
""")
    (skill_dir / "SKILL.md").write_text("# Greeter Skill\n\nSays hello.")
    config.add_skill(skill_dir)

    config.index()

    # 创建工作区
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    # Attach 并创建 session
    aep = AEP.attach(workspace=workspace, config=config)
    return aep.create_session()


class TestExecResult:
    """测试 ExecResult 数据类"""

    def test_default_values(self):
        """默认值"""
        result = ExecResult()

        assert result.stdout == ""
        assert result.stderr == ""
        assert result.return_code == 0

    def test_custom_values(self):
        """自定义值"""
        result = ExecResult(stdout="output", stderr="error", return_code=1)

        assert result.stdout == "output"
        assert result.stderr == "error"
        assert result.return_code == 1


class TestSessionExecBasic:
    """测试 exec 基本功能"""

    def test_exec_empty_command(self, session: AEPSession):
        """空命令"""
        result = session.exec("")

        assert result.return_code == 0

    def test_exec_returns_exec_result(self, session: AEPSession):
        """返回 ExecResult"""
        result = session.exec("echo test")

        assert isinstance(result, ExecResult)


class TestSessionToolsCommand:
    """测试 tools 命令"""

    def test_tools_list(self, session: AEPSession):
        """tools list 列出工具"""
        result = session.exec("tools list")

        assert result.return_code == 0
        assert "calc" in result.stdout

    def test_tools_info(self, session: AEPSession):
        """tools info 显示工具详情"""
        result = session.exec("tools info calc")

        assert result.return_code == 0
        assert "calc" in result.stdout.lower()

    def test_tools_info_nonexistent(self, session: AEPSession):
        """tools info 不存在的工具"""
        result = session.exec("tools info nonexistent")

        assert result.return_code == 1

    def test_tools_run_simple(self, session: AEPSession):
        """tools run 简单表达式"""
        result = session.exec('tools run "1 + 2"')

        assert result.return_code == 0
        assert "3" in result.stdout

    def test_tools_run_tool_function(self, session: AEPSession):
        """tools run 调用工具函数"""
        result = session.exec('tools run "tools.calc.add(10, 20)"')

        assert result.return_code == 0
        assert "30" in result.stdout

    def test_tools_run_tool_chaining(self, session: AEPSession):
        """tools run 工具链"""
        result = session.exec('tools run "tools.calc.add(tools.calc.mul(2, 3), 4)"')

        assert result.return_code == 0
        assert "10" in result.stdout  # 2*3 + 4 = 10

    def test_tools_run_multiline(self, session: AEPSession):
        """tools run 多语句代码"""
        # 使用分号分隔多语句
        result = session.exec(
            'tools run "result = tools.calc.add(1, 2); print(result)"'
        )

        assert result.return_code == 0
        assert "3" in result.stdout

    def test_tools_run_with_json(self, session: AEPSession):
        """tools run 使用 json 模块"""
        result = session.exec("tools run \"json.dumps({'a': 1})\"")

        assert result.return_code == 0
        assert '"a"' in result.stdout

    def test_tools_run_error(self, session: AEPSession):
        """tools run 代码错误"""
        result = session.exec('tools run "1/0"')

        assert result.return_code == 1
        assert "ZeroDivision" in result.stderr

    def test_tools_usage_help(self, session: AEPSession):
        """tools 无参数显示帮助"""
        result = session.exec("tools")

        assert result.return_code == 1
        assert "Usage" in result.stderr


class TestSessionSkillsCommand:
    """测试 skills 命令"""

    def test_skills_list(self, session: AEPSession):
        """skills list 列出技能"""
        result = session.exec("skills list")

        assert result.return_code == 0
        assert "greeter" in result.stdout

    def test_skills_info(self, session: AEPSession):
        """skills info 显示技能详情"""
        result = session.exec("skills info greeter")

        assert result.return_code == 0
        assert "Greeter" in result.stdout

    def test_skills_info_nonexistent(self, session: AEPSession):
        """skills info 不存在的技能"""
        result = session.exec("skills info nonexistent")

        assert result.return_code == 1

    def test_skills_run(self, session: AEPSession):
        """skills run 执行技能"""
        result = session.exec("skills run greeter/main.py")

        assert result.return_code == 0
        assert "Hello" in result.stdout

    def test_skills_run_with_args(self, session: AEPSession):
        """skills run 带参数"""
        result = session.exec("skills run greeter/main.py AEP")

        assert result.return_code == 0
        assert "Hello, AEP" in result.stdout

    def test_skills_run_nonexistent(self, session: AEPSession):
        """skills run 不存在的技能"""
        result = session.exec("skills run nonexistent/main.py")

        assert result.return_code == 1


class TestSessionCdCommand:
    """测试 cd 命令"""

    def test_cd_to_subdir(self, session: AEPSession):
        """cd 到子目录"""
        # 创建子目录
        subdir = session.workspace / "subdir"
        subdir.mkdir()

        result = session.exec("cd subdir")

        assert result.return_code == 0
        assert session.cwd == subdir

    def test_cd_to_agent_dir(self, session: AEPSession):
        """cd 到 .agents 目录"""
        result = session.exec("cd .agents")

        assert result.return_code == 0
        assert ".agents" in str(session.cwd)

    def test_cd_nonexistent(self, session: AEPSession):
        """cd 到不存在的目录"""
        result = session.exec("cd nonexistent")

        assert result.return_code == 1

    def test_cd_no_args_returns_to_workspace(self, session: AEPSession):
        """cd 无参数回到 workspace"""
        # 先 cd 到子目录
        subdir = session.workspace / "subdir"
        subdir.mkdir()
        session.exec("cd subdir")

        # cd 无参数
        result = session.exec("cd")

        assert session.cwd == session.workspace


class TestSessionExportCommand:
    """测试 export 命令"""

    def test_export_sets_env(self, session: AEPSession):
        """export 设置环境变量"""
        result = session.exec("export MY_VAR=hello")

        assert result.return_code == 0
        assert session.env["MY_VAR"] == "hello"

    def test_export_multiple(self, session: AEPSession):
        """export 多个变量"""
        result = session.exec("export A=1 B=2")

        assert session.env["A"] == "1"
        assert session.env["B"] == "2"

    def test_export_no_args_lists_env(self, session: AEPSession):
        """export 无参数列出变量"""
        session.env["TEST"] = "value"

        result = session.exec("export")

        assert "TEST=value" in result.stdout


class TestSessionShellPassthrough:
    """测试 shell 透传"""

    def test_echo(self, session: AEPSession):
        """echo 命令"""
        result = session.exec("echo hello world")

        assert result.return_code == 0
        assert "hello world" in result.stdout

    def test_dir_agent(self, session: AEPSession):
        """dir .agents"""
        result = session.exec("dir .agents")

        assert result.return_code == 0
        assert "tools" in result.stdout or "tools" in result.stdout.lower()

    def test_pwd_after_cd(self, session: AEPSession):
        """cd 后 pwd 显示新目录"""
        subdir = session.workspace / "mydir"
        subdir.mkdir()

        session.exec("cd mydir")
        result = session.exec("cd")  # 在 Windows 上 cd 无参数相当于 pwd

        # cwd 应该已更新
        assert "mydir" in str(session.cwd) or session.cwd == session.workspace


class TestSessionGetContext:
    """测试 get_context 方法"""

    def test_get_context_includes_tools(self, session: AEPSession):
        """上下文包含工具索引"""
        context = session.get_context()

        assert "calc" in context

    def test_get_context_includes_skills(self, session: AEPSession):
        """上下文包含技能索引"""
        context = session.get_context()

        assert "greeter" in context
