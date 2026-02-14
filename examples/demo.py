"""
AEP 快速入门完整示例

流程:
1. 配置阶段: 初始化工具环境、添加 tools/skills/library/MCP
2. 挂载阶段: attach 到 workspace
3. 运行阶段: 统一通过 session.exec() 调用

运行:
    uv run python examples/demo.py
    uv run python examples/demo.py --no-default-deps
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

from aep import AEP, EnvManager
from aep.core.config.handlers.mcp import MCPTransport

ECHO_SERVER = Path(__file__).resolve().parents[1] / "tests" / "mcp" / "echo_server.py"

TOOL_SOURCE = '''"""
data_lab - 数据处理工具（依赖 numpy/pandas/matplotlib）

Usage:
    tools run "df = tools.data_lab.make_df(10); tools.data_lab.describe_df(df)"
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def make_df(rows: int = 20) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    data = {
        "x": np.arange(rows),
        "value": rng.normal(loc=0.0, scale=1.0, size=rows),
    }
    return pd.DataFrame(data)


def describe_df(df: pd.DataFrame) -> dict:
    return {
        "rows": int(df.shape[0]),
        "columns": list(df.columns),
        "mean_of_value": float(df["value"].mean()),
    }


def save_plot(df: pd.DataFrame, output: str = "plot.png") -> str:
    out = Path(output).resolve()
    fig, ax = plt.subplots()
    ax.plot(df["x"], df["value"])
    ax.set_title("data_lab demo")
    fig.savefig(out)
    plt.close(fig)
    return str(out)
'''

SKILL_MAIN = '''#!/usr/bin/env python3
"""生成一段简短报告"""

import sys


def main() -> None:
    name = sys.argv[1] if len(sys.argv) > 1 else "User"
    print(f"[report] Hello, {name}. This report skill is wired and runnable.")


if __name__ == "__main__":
    main()
'''

SKILL_MD = """# Report Skill

一个最小技能示例，用于演示 `skills run`。
"""

LIBRARY_DOC = """# Quickstart Notes

- tools 用于执行 Python 工具代码
- skills 用于执行脚本型能力
- library 用于沉淀文档/知识
- MCP server 会被转成 tools 下的可调用模块
"""


def run_and_print(session, command: str) -> None:
    print(f"\n>>> {command}")
    result = session.exec(command)
    if result.stdout:
        print(result.stdout.strip())
    if result.stderr:
        print("[stderr]")
        print(result.stderr.strip())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--no-default-deps",
        action="store_true",
        help="不自动安装默认工具依赖 (numpy/pandas/matplotlib/mcp)",
    )
    parser.add_argument(
        "--extra-tool-dep",
        action="append",
        default=[],
        help="额外追加工具依赖，可重复传入",
    )
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        config_dir = root / "agent_config"
        workspace = root / "workspace"
        workspace.mkdir()

        # 准备源文件
        tool_file = root / "data_lab.py"
        tool_file.write_text(TOOL_SOURCE, encoding="utf-8")

        skill_dir = root / "report_skill"
        skill_dir.mkdir()
        (skill_dir / "main.py").write_text(SKILL_MAIN, encoding="utf-8")
        (skill_dir / "SKILL.md").write_text(SKILL_MD, encoding="utf-8")

        library_file = root / "quickstart.md"
        library_file.write_text(LIBRARY_DOC, encoding="utf-8")

        print("=" * 64)
        print("1) 配置阶段")
        print("=" * 64)

        config = EnvManager(
            config_dir,
            auto_init_tool_env=True,
            include_default_tool_dependencies=not args.no_default_deps,
            tool_dependencies=args.extra_tool_dep or None,
        )
        print(f"配置目录: {config_dir}")
        print(f"默认工具依赖: {', '.join(config.DEFAULT_TOOL_DEPENDENCIES)}")

        # 添加 tools / skills / library
        config.add_tool(tool_file, name="data_lab")
        config.add_skill(skill_dir, name="report_skill")
        config.add_library(library_file, name="quickstart.md")

        # 添加 MCP server (stdio)
        config.add_mcp_server(
            "echo_mcp",
            transport=MCPTransport.STDIO,
            command=sys.executable,
            args=[str(ECHO_SERVER)],
        )
        config.index()

        req_file = config.tools_dir / "requirements.txt"
        if req_file.exists():
            print("\n[tools requirements.txt]")
            print(req_file.read_text(encoding="utf-8").strip())

        print("\n" + "=" * 64)
        print("2) 挂载阶段")
        print("=" * 64)
        aep = AEP.attach(workspace=workspace, config=config)
        session = aep.create_session()
        print(f"工作区: {workspace}")

        print("\n" + "=" * 64)
        print("3) 运行阶段")
        print("=" * 64)
        run_and_print(session, "tools list")
        run_and_print(session, "skills list")
        run_and_print(session, "cat .agent/library/quickstart.md")

        # 单个 tools run 代码块里同时调用本地工具和 MCP 工具
        code = """
df = tools.data_lab.make_df(12)
summary = tools.data_lab.describe_df(df)
plot_path = tools.data_lab.save_plot(df, output='demo_plot.png')
echo_text = tools.echo_mcp.echo(message='hello from mcp stdio')
sum_text = tools.echo_mcp.add(a=7, b=8)
print('summary:', summary)
print('plot_path:', plot_path)
print('mcp_echo:', echo_text)
print('mcp_add:', sum_text)
""".strip()
        run_and_print(session, f"tools run '''{code}'''")

        run_and_print(session, "skills run report_skill/main.py AEP")

        print("\n" + "=" * 64)
        print("完成: 你现在可以基于这个模板扩展自己的 agent 能力栈")
        print("=" * 64)


if __name__ == "__main__":
    main()
