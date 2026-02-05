# Agent Environment Protocol (AEP) Architecture

> 一种虚拟文件系统协议，为 AI Agent 提供统一的能力发现和调用接口。

---

## 1. 核心设计理念

### 1.1 协议定位

AEP 是一个**能力注册表**，可直接作为 LLM function calling 的工具集传入。

```python
from aep import AEP

# 初始化 (加载或创建配置)
aep = AEP(config="aep.toml")

# 添加能力
aep.add_tool("./search.py")           # Python 函数
aep.add_tool("mcp://localhost:8000")  # MCP 服务
aep.add_skill("./code_review/")       # 技能文件夹
aep.add_library("./docs/api.md")      # 知识文档

# 作为 function calling 接口
response = llm.chat(
    messages=messages,
    tools=aep.as_tools(),  # 直接传入
)

# 执行 Agent 的调用
for call in response.tool_calls:
    result = aep.execute(call.name, call.arguments)
```

### 1.2 设计哲学

| 原则 | 描述 |
|------|------|
| **虚拟文件系统** | Agent 通过 `aep://` 只读访问，与物理存储解耦 |
| **持久化配置** | 所有能力注册到 `aep.toml`，跨会话保持 |
| **统一抽象** | Python 函数和 MCP 暴露为相同接口 |
| **两层上下文** | index (L0 摘要) + 详情 (L1) 按需加载 |
| **可插拔** | 直接传给任何支持 function calling 的 LLM |

### 1.3 与 MCP 的关系

**AEP 兼容并增强 MCP**：

| 特性 | MCP | AEP |
|------|-----|-----|
| 上下文加载 | 一次性全量 schema | 两层按需加载 |
| 调用语法 | JSON RPC | Python 表达式 |
| 持久化 | 无 | aep.toml 配置 |
| MCP 集成 | 原生 | 自动转换为统一接口 |

---

## 2. 核心接口

### 2.1 AEP 类

```python
class AEP:
    def __init__(self, config: str = "aep.toml"):
        """初始化 AEP，加载或创建配置"""
    
    # === 能力管理 ===
    
    def add_tool(self, source: str) -> None:
        """添加工具
        
        Args:
            source: Python 文件路径 或 MCP 地址
                - "./search.py" - 本地 Python 函数
                - "mcp://localhost:8000" - MCP 服务 (自动拆分所有函数)
        """
    
    def add_skill(self, folder: str) -> None:
        """添加技能 (包含 SKILL.md 和 scripts/ 的文件夹)"""
    
    def add_library(self, file: str) -> None:
        """添加知识文档 (.md 或 .txt)"""
    
    def remove(self, type: str, name: str) -> None:
        """移除已注册的能力"""
    
    # === Agent 接口 ===
    
    def as_tools(self) -> list[dict]:
        """返回 OpenAI function calling 格式的 schema"""
    
    def execute(self, name: str, arguments: dict) -> str:
        """执行 function call"""
    
    # === 虚拟文件系统 (只读) ===
    
    def ls(self, path: str = "/") -> list[str]:
        """列出虚拟目录"""
    
    def cat(self, path: str) -> str:
        """读取虚拟文件"""
    
    def search(self, query: str, path: str = "/") -> list[str]:
        """搜索内容"""
    
    # === 持久化 ===
    
    def save(self) -> None:
        """保存配置 (通常自动调用)"""
```

### 2.2 暴露给 LLM 的 Tools

```python
aep.as_tools()  # 返回:
[
    {
        "type": "function",
        "function": {
            "name": "aep_ls",
            "description": "列出 AEP 虚拟目录内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "虚拟路径，如 'tools/' 或 'skills/code_review/'"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "aep_cat",
            "description": "读取 AEP 虚拟文件内容，支持按行范围读取",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "虚拟文件路径，如 'tools/file/TOOL.md'"
                    },
                    "start_line": {
                        "type": "integer",
                        "description": "起始行号 (1-indexed)，不指定则从头开始"
                    },
                    "end_line": {
                        "type": "integer",
                        "description": "结束行号 (inclusive)，不指定则读到末尾"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "aep_tools",
            "description": "执行 Python 代码调用工具。代码中可使用 tools.{name}.{func}() 调用任意工具。支持多行代码实现工具编排。",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Python 代码。单行示例: tools.file.read('x.py')。多行编排示例: result = tools.search.find('query')\nfor r in result:\n    print(tools.file.read(r))"
                    }
                },
                "required": ["code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "aep_skills",
            "description": "执行 AEP 技能脚本，在隔离的虚拟环境中运行",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "技能脚本路径，如 'code_review/scripts/review.py'"
                    },
                    "args": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "传递给脚本的参数列表"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "aep_grep",
            "description": "在 AEP 虚拟文件系统中搜索内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "搜索模式 (支持正则表达式)"
                    },
                    "path": {
                        "type": "string",
                        "description": "搜索范围，如 'tools/' 或 'library/'"
                    }
                },
                "required": ["pattern"]
            }
        }
    }
]
```

---

## 3. 虚拟文件系统

### 3.1 路径结构 (只读)

```
aep://
├── tools/
│   ├── index                    # L0: 所有工具一句话摘要
│   ├── file/
│   │   └── TOOL.md              # L1: 详细描述 + 函数签名
│   ├── search_web/              # 来自 MCP
│   │   └── TOOL.md
│   └── github_create_issue/     # 来自 MCP
│       └── TOOL.md
│
├── skills/
│   ├── index                    # L0: 技能列表
│   └── code_review/
│       ├── SKILL.md             # L1: 技能说明
│       └── scripts/
│
└── library/                        # 知识库
    ├── index                       # L0: 文档列表
    └── {doc}.md                    # L1: 文档内容
```

### 3.2 Agent 访问方式

Agent 通过 function call 访问：

```python
# 探索目录
aep.execute("aep_ls", {"path": "tools/"})
# 返回: "file, search_web, github_create_issue"

# 查看工具详情
aep.execute("aep_cat", {"path": "tools/search_web/TOOL.md"})
# 返回: 工具详情 (L1)

# 搜索内容
aep.execute("aep_grep", {"pattern": "search", "path": "tools/"})
# 返回: 匹配的文件和行

# 单次工具调用
aep.execute("aep_tools", {"code": "tools.file.read('README.md')"})
# 返回: 文件内容

# 多工具编排
aep.execute("aep_tools", {"code": """
result = tools.search.find('python tutorial')
for url in result.urls[:3]:
    content = tools.web.read(url)
    print(f"=== {url} ===")
    print(content[:500])
"""})
# 返回: 执行结果

# 执行技能
aep.execute("aep_skills", {
    "path": "code_review/scripts/review.py",
    "args": ["--file", "main.py"]
})
# 返回: 脚本输出
```

---

## 4. 存储结构

### 4.1 配置文件

```toml
# aep.toml
version = "1.0"
data_dir = "_aep_data"

[[tools]]
name = "file"
type = "builtin"

[[tools]]
name = "search_web"
type = "mcp"
server = "mcp://localhost:8000"
function = "search"

[[tools]]
name = "my_tool"
type = "python"
file = "tools/my_tool.py"

[[skills]]
name = "code_review"
folder = "skills/code_review"

[[library]]
name = "api"
file = "library/api.md"
```

### 4.2 内部存储

```
aep.toml                    # 配置索引
_aep_data/                  # 内部存储
├── tools/
│   ├── my_tool.py          # 复制的 Python 代码
│   └── my_tool.yaml        # 元数据 (名称、描述、签名)
├── skills/
│   └── code_review/        # 复制的技能文件夹
│       ├── SKILL.md
│       └── scripts/
└── library/
    └── api.md              # 复制的文档
```

---

## 5. Tools 系统

### 5.1 Python 函数工具

```python
# ./search.py (用户编写)
def search(query: str, limit: int = 10) -> list[str]:
    """搜索内容
    
    Args:
        query: 搜索关键词
        limit: 返回数量限制
    
    Returns:
        匹配结果列表
    """
    # 实现...
```

添加后自动生成 `TOOL.md`：

```markdown
# search

搜索内容

## 函数

### search(query: str, limit: int = 10) -> list[str]

**参数**:
- `query`: 搜索关键词
- `limit`: 返回数量限制 (默认: 10)

**返回**: 匹配结果列表
```

### 5.2 MCP 工具

```python
aep.add_tool("mcp://localhost:8000")
```

自动：
1. 连接 MCP 服务器
2. 获取所有函数定义
3. 为每个函数生成独立的 `aep://tools/{func}/`
4. 从 MCP schema 生成 `TOOL.md`
5. 创建调用 stub

Agent 调用时语法相同：
```python
tools.search_web.search("query")      # 内置
tools.github.create_issue(...)        # MCP
```

---

## 6. Skills 系统

### 6.1 技能结构

```
code_review/
├── SKILL.md              # 必需
└── scripts/
    └── review.py         # 可执行脚本
```

### 6.2 SKILL.md 格式

```yaml
---
name: code_review
description: 代码审查技能
dependencies:
  - pylsp
---

# Code Review

## 使用

aep_skill code_review/scripts/review.py --file main.py
```

### 6.3 执行

```python
aep.execute("aep_skill", {
    "path": "code_review/scripts/review.py",
    "args": ["--file", "main.py"]
})
# 自动创建 venv，安装依赖，执行脚本
```

---

## 7. Library 系统

### 7.1 添加文档

```python
aep.add_library("./docs/api.md")
aep.add_library("./notes.txt")
```

### 7.2 Agent 访问

```python
aep.execute("aep_ls", {"path": "library/"})
# 返回: "api, notes"

aep.execute("aep_cat", {"path": "library/api.md"})
# 返回: 文档内容

aep.execute("aep_search", {"query": "authentication", "path": "library/"})
# 返回: 匹配的文档路径
```

---

## 8. 完整使用示例

```python
from openai import OpenAI
from aep import AEP
import json

# 初始化
client = OpenAI()
aep = AEP(config="my_agent.toml")

# 首次运行添加能力
aep.add_tool("mcp://localhost:8000")
aep.add_skill("./skills/deploy/")
aep.add_library("./docs/")

# Agent 循环
messages = [{"role": "user", "content": "帮我部署项目"}]

while True:
    response = client.chat.completions.create(
        model="gpt-4",
        messages=messages,
        tools=aep.as_tools(),
    )
    
    msg = response.choices[0].message
    
    if msg.tool_calls:
        messages.append(msg)
        for call in msg.tool_calls:
            result = aep.execute(
                call.function.name,
                json.loads(call.function.arguments)
            )
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": result
            })
    else:
        print(msg.content)
        break

# 配置自动保存，下次运行直接加载
```

---

## 9. 实现架构

```
aep/
├── pyproject.toml
├── src/aep/
│   ├── __init__.py           # AEP 类
│   ├── config.py             # TOML 配置加载/保存
│   │
│   ├── fs/                   # 虚拟文件系统
│   │   ├── virtual.py        # VirtualFS
│   │   └── index.py          # 索引生成
│   │
│   ├── tools/                # Tools 系统
│   │   ├── registry.py       # 工具注册表
│   │   ├── python.py         # Python 函数加载
│   │   ├── mcp.py            # MCP 适配器
│   │   └── executor.py       # 执行引擎
│   │
│   ├── skills/               # Skills 系统
│   │   ├── loader.py         # 技能加载
│   │   ├── venv.py           # 虚拟环境 (uv)
│   │   └── runner.py         # 脚本执行
│   │
│   ├── library/              # Library 系统
│   │   └── store.py          # 文档存储
│   │
│   └── interface/            # Agent 接口
│       ├── schema.py         # function calling schema 生成
│       └── handler.py        # execute() 分发
```
