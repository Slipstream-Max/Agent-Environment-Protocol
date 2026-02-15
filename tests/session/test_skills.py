"""
Session Skills 命令测试

测试 skills list/info/run 命令的各种场景
"""

import pytest
from pathlib import Path

from aep import AEP, EnvManager, AEPSession


# ==================== Fixtures ====================


@pytest.fixture
def skills_session(tmp_path: Path) -> AEPSession:
    """创建包含多个技能的测试 session"""
    config = EnvManager(tmp_path / "config")

    # 技能1: greeter - 简单问候
    greeter_dir = tmp_path / "greeter"
    greeter_dir.mkdir()
    (greeter_dir / "main.py").write_text('''#!/usr/bin/env python3
"""Hello World 技能"""
import sys

def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "World"
    print(f"Hello, {name}!")

if __name__ == "__main__":
    main()
''')
    (greeter_dir / "SKILL.md").write_text("""---
name: greeter
description: Greets a user by name from CLI args.
---

# Greeter Skill

一个简单的问候技能。

## Usage

```bash
skills run greeter/main.py [name]
```

## Examples

- `skills run greeter/main.py` → Hello, World!
- `skills run greeter/main.py Alice` → Hello, Alice!
""")
    config.add_skill(greeter_dir)

    # 技能2: calculator - 命令行计算器
    calc_dir = tmp_path / "calculator"
    calc_dir.mkdir()
    (calc_dir / "main.py").write_text('''#!/usr/bin/env python3
"""命令行计算器"""
import sys

def main():
    if len(sys.argv) < 4:
        print("Usage: main.py <a> <op> <b>")
        sys.exit(1)
    
    a = float(sys.argv[1])
    op = sys.argv[2]
    b = float(sys.argv[3])
    
    if op == "+":
        print(a + b)
    elif op == "-":
        print(a - b)
    elif op == "*":
        print(a * b)
    elif op == "/":
        print(a / b)
    else:
        print(f"Unknown operator: {op}")
        sys.exit(1)

if __name__ == "__main__":
    main()
''')
    (calc_dir / "SKILL.md").write_text("""---
name: calculator
description: Runs basic arithmetic operations from command line inputs.
---

# Calculator Skill

A command-line calculator.

## Usage

```bash
skills run calculator/main.py <a> <operator> <b>
```

## Supported Operators

- `+` addition
- `-` subtraction
- `*` multiplication
- `/` division
""")
    config.add_skill(calc_dir)

    # 技能3: echo - 多文件技能
    echo_dir = tmp_path / "echo"
    echo_dir.mkdir()
    (echo_dir / "main.py").write_text('''#!/usr/bin/env python3
"""Echo 主入口"""
import sys
from helper import format_message

def main():
    message = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "No message"
    print(format_message(message))

if __name__ == "__main__":
    main()
''')
    (echo_dir / "helper.py").write_text('''"""辅助模块"""

def format_message(msg: str) -> str:
    return f"[ECHO] {msg}"
''')
    (echo_dir / "SKILL.md").write_text("""---
name: echo
description: Echoes messages with a consistent prefix format.
---

# Echo Skill

Echoes messages with formatting.
""")
    config.add_skill(echo_dir)

    config.index()

    workspace = tmp_path / "workspace"
    workspace.mkdir()

    aep = AEP.attach(workspace=workspace, config=config)
    return aep.create_session()


@pytest.fixture
def empty_skills_session(tmp_path: Path) -> AEPSession:
    """创建没有技能的 session"""
    config = EnvManager(tmp_path / "config")
    config.index()

    workspace = tmp_path / "workspace"
    workspace.mkdir()

    aep = AEP.attach(workspace=workspace, config=config)
    return aep.create_session()


# ==================== List Tests ====================


class TestSkillsList:
    """测试 skills list 命令"""

    def test_list_shows_all_skills(self, skills_session: AEPSession):
        """列出所有技能"""
        result = skills_session.exec("skills list")

        assert result.return_code == 0
        assert "greeter" in result.stdout
        assert "calculator" in result.stdout
        assert "echo" in result.stdout

    def test_list_empty_when_no_skills(self, empty_skills_session: AEPSession):
        """无技能时显示空"""
        result = empty_skills_session.exec("skills list")

        assert result.return_code == 0
        assert "暂无" in result.stdout


# ==================== Info Tests ====================


class TestSkillsInfo:
    """测试 skills info 命令"""

    def test_info_shows_skill_md(self, skills_session: AEPSession):
        """显示 SKILL.md 内容"""
        result = skills_session.exec("skills info greeter")

        assert result.return_code == 0
        assert "Greeter" in result.stdout
        assert "Hello" in result.stdout

    def test_info_calculator(self, skills_session: AEPSession):
        """显示 calculator 技能详情"""
        result = skills_session.exec("skills info calculator")

        assert result.return_code == 0
        assert "Calculator" in result.stdout
        assert "operator" in result.stdout.lower()

    def test_info_nonexistent_skill(self, skills_session: AEPSession):
        """不存在的技能返回错误"""
        result = skills_session.exec("skills info nonexistent")

        assert result.return_code == 1
        assert "不存在" in result.stderr

    def test_info_missing_name(self, skills_session: AEPSession):
        """缺少技能名"""
        result = skills_session.exec("skills info")

        assert result.return_code == 1


# ==================== Run Tests ====================


class TestSkillsRun:
    """测试 skills run 命令"""

    def test_run_greeter_no_args(self, skills_session: AEPSession):
        """运行 greeter 无参数"""
        result = skills_session.exec("skills run greeter/main.py")

        assert result.return_code == 0
        assert "Hello, World!" in result.stdout

    def test_run_greeter_with_name(self, skills_session: AEPSession):
        """运行 greeter 带参数"""
        result = skills_session.exec("skills run greeter/main.py Alice")

        assert result.return_code == 0
        assert "Hello, Alice!" in result.stdout

    def test_run_calculator_add(self, skills_session: AEPSession):
        """计算器加法"""
        result = skills_session.exec("skills run calculator/main.py 10 + 5")

        assert result.return_code == 0
        assert "15" in result.stdout

    def test_run_calculator_mul(self, skills_session: AEPSession):
        """计算器乘法"""
        result = skills_session.exec("skills run calculator/main.py 3 * 4")

        assert result.return_code == 0
        assert "12" in result.stdout

    def test_run_calculator_div(self, skills_session: AEPSession):
        """计算器除法"""
        result = skills_session.exec("skills run calculator/main.py 20 / 4")

        assert result.return_code == 0
        assert "5" in result.stdout

    def test_run_multi_file_skill(self, skills_session: AEPSession):
        """运行多文件技能"""
        result = skills_session.exec("skills run echo/main.py test message")

        assert result.return_code == 0
        assert "[ECHO]" in result.stdout
        assert "test message" in result.stdout

    def test_run_with_special_chars(self, skills_session: AEPSession):
        """参数包含特殊字符"""
        result = skills_session.exec('skills run greeter/main.py "Bob Smith"')

        assert result.return_code == 0
        assert "Bob Smith" in result.stdout


# ==================== Error Handling Tests ====================


class TestSkillsRunErrors:
    """测试 skills run 错误处理"""

    def test_run_nonexistent_skill(self, skills_session: AEPSession):
        """运行不存在的技能"""
        result = skills_session.exec("skills run nonexistent/main.py")

        assert result.return_code == 1
        assert "不存在" in result.stderr

    def test_run_nonexistent_script(self, skills_session: AEPSession):
        """运行不存在的脚本"""
        result = skills_session.exec("skills run greeter/nonexistent.py")

        assert result.return_code == 1
        assert "不存在" in result.stderr

    def test_run_missing_path(self, skills_session: AEPSession):
        """缺少脚本路径"""
        result = skills_session.exec("skills run")

        assert result.return_code == 1

    def test_run_script_with_error(self, tmp_path: Path):
        """运行有错误的脚本"""
        config = EnvManager(tmp_path / "config")

        # 创建一个会报错的技能
        error_dir = tmp_path / "error-skill"
        error_dir.mkdir()
        (error_dir / "main.py").write_text("""
raise ValueError("Intentional error")
""")
        (error_dir / "SKILL.md").write_text(
            """---
name: error-skill
description: Raises an intentional error for testing.
---

# Error Skill
"""
        )
        config.add_skill(error_dir)
        config.index()

        workspace = tmp_path / "workspace"
        workspace.mkdir()

        aep = AEP.attach(workspace=workspace, config=config)
        session = aep.create_session()

        result = session.exec("skills run error-skill/main.py")

        assert result.return_code == 1
        assert "ValueError" in result.stderr or "Intentional error" in result.stderr


# ==================== Usage Help Tests ====================


class TestSkillsUsage:
    """测试 skills 帮助信息"""

    def test_skills_no_args_shows_help(self, skills_session: AEPSession):
        """skills 无参数显示帮助"""
        result = skills_session.exec("skills")

        assert result.return_code == 1
        assert "Usage" in result.stderr

    def test_skills_unknown_subcommand(self, skills_session: AEPSession):
        """未知子命令"""
        result = skills_session.exec("skills unknown")

        assert result.return_code == 1
        assert "未知" in result.stderr


# ==================== Integration Tests ====================


class TestSkillsIntegration:
    """技能集成测试"""

    def test_list_then_run(self, skills_session: AEPSession):
        """先 list 再 run"""
        # 获取列表
        list_result = skills_session.exec("skills list")
        assert list_result.return_code == 0
        assert "greeter" in list_result.stdout

        # 获取详情
        info_result = skills_session.exec("skills info greeter")
        assert info_result.return_code == 0

        # 执行
        run_result = skills_session.exec("skills run greeter/main.py AEP")
        assert run_result.return_code == 0
        assert "Hello, AEP!" in run_result.stdout

    def test_multiple_runs(self, skills_session: AEPSession):
        """多次运行"""
        result1 = skills_session.exec("skills run greeter/main.py Alice")
        result2 = skills_session.exec("skills run greeter/main.py Bob")
        result3 = skills_session.exec("skills run calculator/main.py 1 + 2")

        assert result1.return_code == 0
        assert "Alice" in result1.stdout

        assert result2.return_code == 0
        assert "Bob" in result2.stdout

        assert result3.return_code == 0
        assert "3" in result3.stdout
