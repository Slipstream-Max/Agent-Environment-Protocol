"""
Session Tools 命令测试

测试 tools list/info/run 命令的各种场景
"""

import pytest
from pathlib import Path

from aep import AEP, EnvManager, AEPSession


# ==================== Fixtures ====================


@pytest.fixture
def simple_session(tmp_path: Path) -> AEPSession:
    """创建简单的测试 session (只有基础工具)"""
    config = EnvManager(tmp_path / "config")

    # 添加计算工具
    calc_tool = tmp_path / "calc.py"
    calc_tool.write_text('''"""
calc - 计算工具

Usage:
    tools run "tools.calc.add(a, b)"
    tools run "tools.calc.mul(a, b)"
"""

def add(a, b):
    """加法"""
    return a + b

def mul(a, b):
    """乘法"""
    return a * b

def div(a, b):
    """除法"""
    return a / b
''')
    config.add_tool(calc_tool)
    config.index()

    workspace = tmp_path / "workspace"
    workspace.mkdir()

    aep = AEP.attach(workspace=workspace, config=config)
    return aep.create_session()


@pytest.fixture
def multi_tool_session(tmp_path: Path) -> AEPSession:
    """创建包含多个可组合工具的 session (不依赖外部库)"""
    config = EnvManager(tmp_path / "config")

    # 工具1: 数据生成
    data_tool = tmp_path / "data.py"
    data_tool.write_text('''"""
data - 数据生成工具
"""

def create_list(n: int = 5):
    """生成 0 到 n-1 的列表"""
    return list(range(n))

def create_dict():
    """生成固定字典"""
    return {"a": 10, "b": 20, "c": 30}

def create_nested():
    """生成嵌套数据"""
    return {
        "items": [1, 2, 3, 4, 5],
        "meta": {"count": 5, "sum": 15}
    }
''')
    config.add_tool(data_tool)

    # 工具2: 数据分析
    analyze_tool = tmp_path / "analyze.py"
    analyze_tool.write_text('''"""
analyze - 数据分析工具
"""

def find_max(data):
    """找到列表或字典值的最大值"""
    if isinstance(data, list):
        return max(data)
    elif isinstance(data, dict):
        return max(data.values())
    return data

def sum_all(data):
    """求和"""
    if isinstance(data, list):
        return sum(data)
    elif isinstance(data, dict):
        return sum(data.values())
    return data

def count(data):
    """计数"""
    return len(data)
''')
    config.add_tool(analyze_tool)

    # 工具3: 格式化
    format_tool = tmp_path / "fmt.py"
    format_tool.write_text('''"""
fmt - 格式化工具
"""

def as_json(data):
    """转换为 JSON 字符串"""
    import json
    return json.dumps(data, indent=2)

def as_csv(data):
    """列表转 CSV"""
    if isinstance(data, list):
        return ",".join(str(x) for x in data)
    return str(data)
''')
    config.add_tool(format_tool)

    config.index()

    workspace = tmp_path / "workspace"
    workspace.mkdir()

    aep = AEP.attach(workspace=workspace, config=config)
    return aep.create_session()


# ==================== Basic Tests ====================


class TestToolsList:
    """测试 tools list 命令"""

    def test_list_shows_tools(self, simple_session: AEPSession):
        """列出工具"""
        result = simple_session.exec("tools list")

        assert result.return_code == 0
        assert "calc" in result.stdout

    def test_list_empty_when_no_tools(self, tmp_path: Path):
        """无工具时显示空"""
        config = EnvManager(tmp_path / "config")
        config.index()

        workspace = tmp_path / "workspace"
        workspace.mkdir()

        aep = AEP.attach(workspace=workspace, config=config)
        session = aep.create_session()

        result = session.exec("tools list")

        assert result.return_code == 0
        assert "暂无" in result.stdout


class TestToolsInfo:
    """测试 tools info 命令"""

    def test_info_shows_docstring(self, simple_session: AEPSession):
        """显示工具 docstring"""
        result = simple_session.exec("tools info calc")

        assert result.return_code == 0
        assert "calc" in result.stdout.lower()

    def test_info_nonexistent_tool(self, simple_session: AEPSession):
        """不存在的工具返回错误"""
        result = simple_session.exec("tools info nonexistent")

        assert result.return_code == 1
        assert "不存在" in result.stderr

    def test_info_missing_name(self, simple_session: AEPSession):
        """缺少工具名"""
        result = simple_session.exec("tools info")

        assert result.return_code == 1


class TestToolsRunBasic:
    """测试 tools run 基础功能"""

    def test_run_simple_expression(self, simple_session: AEPSession):
        """执行简单表达式"""
        result = simple_session.exec('tools run "1 + 2"')

        assert result.return_code == 0
        assert "3" in result.stdout

    def test_run_tool_function(self, simple_session: AEPSession):
        """调用工具函数"""
        result = simple_session.exec('tools run "tools.calc.add(10, 20)"')

        assert result.return_code == 0
        assert "30" in result.stdout

    def test_run_tool_chaining(self, simple_session: AEPSession):
        """工具链式调用"""
        result = simple_session.exec(
            'tools run "tools.calc.add(tools.calc.mul(2, 3), 4)"'
        )

        assert result.return_code == 0
        assert "10" in result.stdout  # 2*3 + 4 = 10

    def test_run_with_print(self, simple_session: AEPSession):
        """使用 print 输出"""
        result = simple_session.exec(
            "tools run \"result = tools.calc.add(1, 2); print(f'Result: {result}')\""
        )

        assert result.return_code == 0
        assert "Result: 3" in result.stdout

    def test_run_builtin_modules(self, simple_session: AEPSession):
        """内置模块可用 (json, re, Path)"""
        result = simple_session.exec("tools run \"json.dumps({'a': 1})\"")

        assert result.return_code == 0
        assert '"a"' in result.stdout

    def test_run_error_handling(self, simple_session: AEPSession):
        """错误处理"""
        result = simple_session.exec('tools run "1/0"')

        assert result.return_code == 1
        assert "ZeroDivision" in result.stderr

    def test_run_no_code(self, simple_session: AEPSession):
        """缺少代码"""
        result = simple_session.exec("tools run")

        assert result.return_code == 1


# ==================== Multiline Code Tests ====================


class TestToolsRunMultiline:
    """测试 tools run 多行代码支持"""

    def test_semicolon_separated(self, simple_session: AEPSession):
        """分号分隔的多语句"""
        result = simple_session.exec('tools run "a = 1; b = 2; print(a + b)"')

        assert result.return_code == 0
        assert "3" in result.stdout

    def test_triple_single_quotes(self, simple_session: AEPSession):
        """三单引号包裹多行代码"""
        code = """'''
a = 10
b = 20
result = tools.calc.add(a, b)
print(f"Sum: {result}")
'''"""
        result = simple_session.exec(f"tools run {code}")

        assert result.return_code == 0
        assert "Sum: 30" in result.stdout

    def test_triple_double_quotes(self, simple_session: AEPSession):
        """三双引号包裹多行代码"""
        code = '''"""
x = 5
y = 3
product = tools.calc.mul(x, y)
print(product)
"""'''
        result = simple_session.exec(f"tools run {code}")

        assert result.return_code == 0
        assert "15" in result.stdout

    def test_multiline_with_conditionals(self, simple_session: AEPSession):
        """多行代码包含条件语句"""
        code = """'''
a = tools.calc.add(1, 2)
if a > 2:
    print("Greater than 2")
else:
    print("Not greater")
'''"""
        result = simple_session.exec(f"tools run {code}")

        assert result.return_code == 0
        assert "Greater than 2" in result.stdout

    def test_multiline_with_loop(self, simple_session: AEPSession):
        """多行代码包含循环"""
        code = """'''
total = 0
for i in range(5):
    total = tools.calc.add(total, i)
print(f"Total: {total}")
'''"""
        result = simple_session.exec(f"tools run {code}")

        assert result.return_code == 0
        assert "Total: 10" in result.stdout  # 0+1+2+3+4


# ==================== Multi-Tool Composition Tests ====================


class TestToolsComposition:
    """测试多工具组合调用 (不依赖外部库)"""

    def test_data_to_analyze(self, multi_tool_session: AEPSession):
        """数据生成 -> 分析 (REPL 自动输出)"""
        result = multi_tool_session.exec(
            'tools run "data = tools.data.create_list(10); tools.analyze.find_max(data)"'
        )

        assert result.return_code == 0
        assert "9" in result.stdout  # max of [0..9]

    def test_dict_sum(self, multi_tool_session: AEPSession):
        """字典求和 (REPL 自动输出)"""
        result = multi_tool_session.exec(
            'tools run "d = tools.data.create_dict(); tools.analyze.sum_all(d)"'
        )

        assert result.return_code == 0
        assert "60" in result.stdout  # 10+20+30

    def test_list_to_csv(self, multi_tool_session: AEPSession):
        """列表转 CSV (REPL 自动输出)"""
        result = multi_tool_session.exec(
            'tools run "data = tools.data.create_list(5); tools.fmt.as_csv(data)"'
        )

        assert result.return_code == 0
        assert "0,1,2,3,4" in result.stdout

    def test_nested_data_workflow(self, multi_tool_session: AEPSession):
        """嵌套数据工作流 (REPL 自动输出)"""
        result = multi_tool_session.exec(
            "tools run \"d = tools.data.create_nested(); tools.analyze.sum_all(d['items'])\""
        )

        assert result.return_code == 0
        assert "15" in result.stdout

    def test_multiline_workflow_with_print(self, multi_tool_session: AEPSession):
        """多行代码工作流 (中间步骤需要 print)"""
        code = """'''
# 创建数据
data = tools.data.create_list(10)
d = tools.data.create_dict()

# 分析并输出中间结果
print(f"List max: {tools.analyze.find_max(data)}")
print(f"Dict sum: {tools.analyze.sum_all(d)}")
'''"""
        result = multi_tool_session.exec(f"tools run {code}")

        assert result.return_code == 0
        assert "List max: 9" in result.stdout
        assert "Dict sum: 60" in result.stdout

    def test_multiline_repl_auto_output(self, multi_tool_session: AEPSession):
        """多行代码 REPL 自动输出最后表达式"""
        code = """'''
data = tools.data.create_list(10)
d = tools.data.create_dict()
# 最后一个表达式会自动输出
{"list_max": tools.analyze.find_max(data), "dict_sum": tools.analyze.sum_all(d)}
'''"""
        result = multi_tool_session.exec(f"tools run {code}")

        assert result.return_code == 0
        assert "list_max" in result.stdout
        assert "9" in result.stdout

    def test_three_tool_pipeline(self, multi_tool_session: AEPSession):
        """三工具管道 (REPL 自动输出)"""
        result = multi_tool_session.exec(
            'tools run "data = tools.data.create_dict(); tools.fmt.as_json(data)"'
        )

        assert result.return_code == 0
        assert '"a"' in result.stdout
        assert "10" in result.stdout


# ==================== Quote Handling Tests ====================


class TestToolsRunQuoteHandling:
    """测试引号处理"""

    def test_double_quotes(self, simple_session: AEPSession):
        """双引号包裹"""
        result = simple_session.exec('tools run "1 + 1"')

        assert result.return_code == 0
        assert "2" in result.stdout

    def test_single_quotes(self, simple_session: AEPSession):
        """单引号包裹"""
        result = simple_session.exec("tools run '2 + 2'")

        assert result.return_code == 0
        assert "4" in result.stdout

    def test_nested_quotes(self, simple_session: AEPSession):
        """嵌套引号"""
        result = simple_session.exec("tools run \"print('hello')\"")

        assert result.return_code == 0
        assert "hello" in result.stdout

    def test_no_quotes_fails(self, simple_session: AEPSession):
        """没有引号包裹失败"""
        result = simple_session.exec("tools run 1+1")

        assert result.return_code == 1


# ==================== Edge Cases ====================


class TestToolsRunEdgeCases:
    """边界情况测试"""

    def test_empty_code(self, simple_session: AEPSession):
        """空代码"""
        result = simple_session.exec('tools run ""')

        # 空代码应该正常执行，没有输出
        assert result.return_code == 0

    def test_whitespace_code(self, simple_session: AEPSession):
        """只有空白的代码"""
        result = simple_session.exec('tools run "   "')

        assert result.return_code == 0

    def test_syntax_error(self, simple_session: AEPSession):
        """语法错误"""
        result = simple_session.exec('tools run "def broken("')

        assert result.return_code == 1
        assert "SyntaxError" in result.stderr

    def test_undefined_tool(self, simple_session: AEPSession):
        """调用未定义的工具"""
        result = simple_session.exec('tools run "tools.undefined.func()"')

        assert result.return_code == 1

    def test_tools_usage_help(self, simple_session: AEPSession):
        """tools 无参数显示帮助"""
        result = simple_session.exec("tools")

        assert result.return_code == 1
        assert "Usage" in result.stderr
