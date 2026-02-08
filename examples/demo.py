"""
AEP 使用示例

演示完整的 Config -> Attach -> Session 流程
"""

from pathlib import Path
import tempfile
import shutil

from aep import EnvManager, AEP


def main():
    # 使用临时目录进行演示
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # === 准备测试文件 ===

        # 创建一个示例工具
        tool_source = tmpdir / "grep_tool.py"
        tool_source.write_text(
            '''"""
grep - 在文件中搜索模式

Usage:
    tools run "tools.grep.search(pattern, path)"
    tools run "tools.grep.count(pattern, path)"
"""

import re
from pathlib import Path as P


def search(pattern: str, path: str = ".") -> list[dict]:
    """搜索匹配的行"""
    results = []
    root = P(path)
    
    files = [root] if root.is_file() else root.rglob("*")
    
    for file in files:
        if file.is_file() and file.suffix in [".py", ".md", ".txt", ".json"]:
            try:
                content = file.read_text(encoding="utf-8")
                for i, line in enumerate(content.splitlines(), 1):
                    if re.search(pattern, line):
                        results.append({
                            "file": str(file),
                            "line": i,
                            "content": line.strip()
                        })
            except:
                pass
    
    return results


def count(pattern: str, path: str = ".") -> int:
    """计数匹配数量"""
    return len(search(pattern, path))
''',
            encoding="utf-8",
        )

        # 创建一个示例技能目录
        skill_source = tmpdir / "hello_skill"
        skill_source.mkdir()
        (skill_source / "main.py").write_text(
            '''#!/usr/bin/env python3
"""Hello World 技能"""

import sys

def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "World"
    print(f"Hello, {name}!")

if __name__ == "__main__":
    main()
''',
            encoding="utf-8",
        )
        (skill_source / "SKILL.md").write_text(
            """# Hello Skill

一个简单的问候技能。

## Usage

```bash
skills run hello_skill/main.py [name]
```

## Examples

```bash
skills run hello_skill/main.py
# Output: Hello, World!

skills run hello_skill/main.py Alice
# Output: Hello, Alice!
```
""",
            encoding="utf-8",
        )

        # 创建一个示例资料
        library_source = tmpdir / "api_docs.md"
        library_source.write_text(
            """# API 文档

## 认证

所有 API 请求需要在 Header 中包含 `Authorization: Bearer <token>`。

## 端点

### GET /users

获取用户列表。

### POST /users

创建新用户。

Request Body:
```json
{
  "name": "string",
  "email": "string"
}
```
""",
            encoding="utf-8",
        )

        # === 阶段一：配置阶段 ===
        print("=" * 60)
        print("阶段一：配置阶段 (EnvManager)")
        print("=" * 60)

        config_dir = tmpdir / "agent_capabilities"
        config = EnvManager(config_dir)

        # 添加工具
        config.add_tool(tool_source, name="grep")

        # 添加技能
        config.add_skill(skill_source)

        # 添加资料
        config.add_library(library_source, name="api-docs.md")

        # 生成索引
        config.index()

        print(f"\n配置目录: {config_dir}")
        print("\n目录结构:")
        for item in sorted(config_dir.rglob("*")):
            rel = item.relative_to(config_dir)
            indent = "  " * (len(rel.parts) - 1)
            print(f"  {indent}{item.name}")

        # === 阶段二：挂载阶段 ===
        print("\n" + "=" * 60)
        print("阶段二：挂载阶段 (AEP.attach)")
        print("=" * 60)

        workspace = tmpdir / "my_project"
        workspace.mkdir()

        # 在工作区创建一些测试文件
        src_dir = workspace / "src"
        src_dir.mkdir()
        (src_dir / "main.py").write_text(
            """# TODO: implement main function
def main():
    pass  # TODO: add logic
""",
            encoding="utf-8",
        )

        aep = AEP.attach(workspace=workspace, config=config)

        print(f"\n工作区: {workspace}")
        print("\n.agent/ 结构:")
        agent_dir = workspace / ".agent"
        for item in sorted(agent_dir.iterdir()):
            target = item.resolve() if item.is_symlink() else item
            print(f"  {item.name} -> {target}")

        # === 阶段三：运行时 ===
        print("\n" + "=" * 60)
        print("阶段三：运行时 (AEPSession.exec)")
        print("=" * 60)

        session = aep.create_session()

        # 测试 1: tools list
        print("\n>>> session.exec('tools list')")
        result = session.exec("tools list")
        print(result.stdout)

        # 测试 2: tools info
        print(">>> session.exec('tools info grep')")
        result = session.exec("tools info grep")
        print(
            result.stdout[:200] + "..." if len(result.stdout) > 200 else result.stdout
        )

        # 测试 3: tools run
        print(
            "\n>>> session.exec('tools run \"tools.grep.search(\\'TODO\\', \\'.\\')')\""
        )
        result = session.exec("tools run \"tools.grep.search('TODO', '.')\"")
        print(result.stdout)
        if result.stderr:
            print(f"stderr: {result.stderr}")

        # 测试 4: skills list
        print(">>> session.exec('skills list')")
        result = session.exec("skills list")
        print(result.stdout)

        # 测试 5: skills run
        print(">>> session.exec('skills run hello_skill/main.py AEP')")
        result = session.exec("skills run hello_skill/main.py AEP")
        print(result.stdout)

        # 测试 6: shell 透传
        print(">>> session.exec('ls .agent/library/')")
        result = session.exec("ls .agent/library/")
        print(result.stdout)

        # 测试 7: cat 资料
        print(">>> session.exec('cat .agent/library/api-docs.md')")
        result = session.exec("cat .agent/library/api-docs.md")
        print(
            result.stdout[:300] + "..." if len(result.stdout) > 300 else result.stdout
        )

        # 测试 8: get_context
        print("\n>>> session.get_context()")
        context = session.get_context()
        print(context[:500] + "..." if len(context) > 500 else context)

        print("\n" + "=" * 60)
        print("测试完成！")
        print("=" * 60)


if __name__ == "__main__":
    main()
