"""
AEP DataFrame 工具示例

演示如何：
1. 使用 add_tool() 添加工具并指定 dependencies 参数
2. 使用 add_dependencies() 单独添加依赖
3. 在单个 tools run "" 中组合调用多个工具

场景：
- 工具1: generate_data - 生成随机 DataFrame
- 工具2: analyze_data - 分析 DataFrame，找到最大值
"""

from pathlib import Path
import tempfile

from aep import EnvManager, AEP


# === 工具代码定义 ===

# 工具1: 生成 DataFrame (返回 DataFrame 对象)
GENERATE_DATA_TOOL = '''
"""
generate_data - 生成随机 DataFrame

Usage:
    # 单独使用
    tools run "df = tools.generate_data.create(rows=100, cols=5)"
    
    # 与其他工具组合使用
    tools run "df = tools.generate_data.create(50, 3); tools.analyze_data.find_max(df)"
"""

import numpy as np
import pandas as pd


def create(rows: int = 100, cols: int = 5) -> pd.DataFrame:
    """
    生成随机数据的 DataFrame
    
    Args:
        rows: 行数
        cols: 列数
    
    Returns:
        pd.DataFrame 对象
    """
    data = np.random.randn(rows, cols)
    columns = [f"col_{i}" for i in range(cols)]
    return pd.DataFrame(data, columns=columns)


def create_named() -> pd.DataFrame:
    """生成带命名列的 DataFrame"""
    return pd.DataFrame({
        "A": np.random.randn(100),
        "B": np.random.randn(100) * 10,
        "C": np.random.randn(100) * 100,
    })
'''

# 工具2: 分析 DataFrame (接收 DataFrame 对象)
ANALYZE_DATA_TOOL = '''
"""
analyze_data - 分析 DataFrame，找到最大值

Usage:
    # 与 generate_data 组合使用
    tools run "df = tools.generate_data.create(50, 3); tools.analyze_data.find_max(df)"
    tools run "df = tools.generate_data.create_named(); tools.analyze_data.summary(df)"
"""

import pandas as pd


def find_max(df: pd.DataFrame) -> dict:
    """
    找到 DataFrame 中的最大值
    
    Args:
        df: pandas DataFrame
    
    Returns:
        包含最大值信息的字典
    """
    max_value = df.max().max()
    
    # 找到最大值所在的位置
    for col in df.columns:
        col_max = df[col].max()
        if col_max == max_value:
            row_idx = df[col].idxmax()
            return {
                "max_value": float(max_value),
                "column": col,
                "row": int(row_idx),
                "message": f"最大值 {max_value:.4f} 位于 [{row_idx}, {col}]"
            }
    
    return {"max_value": float(max_value)}


def summary(df: pd.DataFrame) -> str:
    """返回 DataFrame 的统计摘要"""
    return df.describe().to_string()


def column_max(df: pd.DataFrame, column: str) -> float:
    """获取指定列的最大值"""
    return float(df[column].max())
'''


def demo_with_add_tool_dependencies():
    """
    方法1: 使用 add_tool() 的 dependencies 参数

    在添加工具时同时指定依赖
    """
    print("=" * 60)
    print("方法1: 使用 add_tool(dependencies=[...]) 添加依赖")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # 准备工具源文件
        tool1_source = tmpdir / "generate_data.py"
        tool1_source.write_text(GENERATE_DATA_TOOL, encoding="utf-8")

        tool2_source = tmpdir / "analyze_data.py"
        tool2_source.write_text(ANALYZE_DATA_TOOL, encoding="utf-8")

        # === 配置阶段 ===
        config_dir = tmpdir / "agent_config"
        config = EnvManager(config_dir)

        # 添加工具1，同时指定依赖 (numpy 和 pandas)
        config.add_tool(
            tool1_source, name="generate_data", dependencies=["numpy", "pandas"]
        )

        # 添加工具2，pandas 已经安装，会被跳过
        config.add_tool(
            tool2_source,
            name="analyze_data",
            dependencies=["pandas"],  # 重复依赖不会重复安装
        )

        # 生成索引
        config.index()

        print(f"\n✓ 配置完成: {config_dir}")
        print(f"✓ 工具列表: {config.tools.list()}")

        # === 挂载并运行 ===
        workspace = tmpdir / "workspace"
        workspace.mkdir()

        aep = AEP.attach(workspace=workspace, config=config)
        session = aep.create_session()

        # ⭐ 关键演示: 在单个 tools run 中组合调用两个工具
        print("\n>>> 组合调用: 生成 DataFrame 并找最大值")
        print(
            'tools run "df = tools.generate_data.create(50, 3); tools.analyze_data.find_max(df)"'
        )
        result = session.exec(
            'tools run "df = tools.generate_data.create(50, 3); tools.analyze_data.find_max(df)"'
        )
        print(f"stdout: {result.stdout}")
        if result.stderr:
            print(f"stderr: {result.stderr}")

        # 另一个组合调用示例
        print("\n>>> 组合调用: 生成命名列 DataFrame 并获取摘要")
        print(
            'tools run "df = tools.generate_data.create_named(); tools.analyze_data.summary(df)"'
        )
        result = session.exec(
            'tools run "df = tools.generate_data.create_named(); tools.analyze_data.summary(df)"'
        )
        print(f"stdout: {result.stdout}")
        if result.stderr:
            print(f"stderr: {result.stderr}")


def demo_with_add_dependencies():
    """
    方法2: 使用 add_dependencies() 单独添加依赖

    先添加依赖，再添加工具
    """
    print("\n" + "=" * 60)
    print("方法2: 使用 add_dependencies() 单独添加依赖")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # 准备工具源文件
        tool1_source = tmpdir / "generate_data.py"
        tool1_source.write_text(GENERATE_DATA_TOOL, encoding="utf-8")

        tool2_source = tmpdir / "analyze_data.py"
        tool2_source.write_text(ANALYZE_DATA_TOOL, encoding="utf-8")

        # === 配置阶段 ===
        config_dir = tmpdir / "agent_config"
        config = EnvManager(config_dir)

        # 先安装所有依赖
        print("\n>>> 安装依赖: numpy, pandas")
        config.add_tool_dependency("numpy>=1.20", "pandas>=2.0")

        # 再添加工具 (不需要再指定 dependencies)
        config.add_tool(tool1_source, name="generate_data")
        config.add_tool(tool2_source, name="analyze_data")

        # 生成索引
        config.index()

        print(f"\n✓ 配置完成: {config_dir}")
        print(f"✓ 工具列表: {config.tools.list()}")

        # 查看 requirements.txt
        req_file = config_dir / "tools" / "requirements.txt"
        if req_file.exists():
            print("\n✓ requirements.txt 内容:")
            print(req_file.read_text())

        # === 挂载并运行 ===
        workspace = tmpdir / "workspace"
        workspace.mkdir()

        aep = AEP.attach(workspace=workspace, config=config)
        session = aep.create_session()

        # ⭐ 关键演示: 在单个 tools run 中组合调用
        print(">>> 组合调用: 生成 + 分析 + 获取指定列最大值")
        print(
            "tools run \"df = tools.generate_data.create_named(); print(tools.analyze_data.column_max(df, 'C'))\""
        )
        result = session.exec(
            "tools run \"df = tools.generate_data.create_named(); print(tools.analyze_data.column_max(df, 'C'))\""
        )
        print(f"stdout: {result.stdout}")
        if result.stderr:
            print(f"stderr: {result.stderr}")

        # 更复杂的组合: 生成、分析、打印（多行代码）
        print("\n>>> 复杂组合调用 (多行代码):")
        code = """
df = tools.generate_data.create(100, 5)
result = tools.analyze_data.find_max(df)
print(f"生成了 {df.shape[0]} 行 {df.shape[1]} 列的数据")
print(f"最大值: {result['max_value']:.4f}")
print(f"位置: 第 {result['row']} 行, {result['column']} 列")
"""
        print(f"tools run '''{code}'''")
        result = session.exec(f"tools run '''{code}'''")
        print(f"stdout: {result.stdout}")
        if result.stderr:
            print(f"stderr: {result.stderr}")


def main():
    """运行两种方法的演示"""
    print("AEP DataFrame 工具演示")
    print("展示两种添加依赖的方式 + 组合调用工具\n")

    # 方法1: add_tool(dependencies=[...])
    demo_with_add_tool_dependencies()

    # 方法2: add_dependencies(...)
    demo_with_add_dependencies()

    print("\n" + "=" * 60)
    print("✓ 演示完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()
