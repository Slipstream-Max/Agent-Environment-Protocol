# AEP - Agent Environment Protocol

> 为 AI Agent 提供统一的能力发现和调用接口。

## 核心概念

**AEP 是一个能力注册表协议**，通过目录化的方式管理工具、技能和资料库，让 AI Agent 可以统一发现和调用各种能力。

### 核心组件

| 组件 | 说明 |
|------|------|
| **EnvManager** | 能力配置管理器，管理工具、技能、资料库 |
| **AEP** | 主类，通过 `attach()` 将配置挂载到工作区 |
| **AEPSession** | 会话，通过 `exec()` 执行命令 |

### 目录结构

```
config_dir/
├── tools/                    # 工具目录
│   ├── .venv/               # 共享虚拟环境 (uv 管理)
│   ├── requirements.txt     # 依赖清单
│   ├── index.md             # 工具索引
│   └── grep.py              # Python 工具 / MCP stub
├── skills/                   # 技能目录
│   ├── index.md
│   └── web-scraper/         # 普通技能
├── library/                  # 资料库
│   ├── index.md
│   └── api-docs.md
└── _mcp/                     # MCP 配置（外部存储，不挂载到工作区）
    └── figma/
        ├── config.json
        └── manifest.json
```

## 快速开始

### 安装

```bash
# 使用 uv 安装
uv add aep
```

### 基本使用

```python
from aep import EnvManager, AEP

# === 阶段一：配置阶段 ===
config = EnvManager("./agent_capabilities")

# 添加工具（支持依赖参数）
config.add_tool(
    "./tools/grep.py",
    dependencies=["regex>=2023.0"]
)

# 添加技能
config.add_skill(
    "./skills/web-scraper/",
    dependencies=["requests", "beautifulsoup4"]
)

# 添加资料库
config.add_library("./docs/api-docs.md")

# 生成索引
config.index()

# === 阶段二：挂载阶段 ===
aep = AEP.attach(
    workspace="./my_project",
    config=config,
)

# === 阶段三：运行时 ===
session = aep.create_session()

# exec 是唯一对外接口
result = session.exec("tools list")
result = session.exec('tools run "tools.grep.search(\'TODO\', \'.\')"')
result = session.exec("skills run web-scraper/main.py --url 'https://example.com'")
result = session.exec("ls .agents/library/")  # Shell 透传
```

## 架构设计

### 模块化配置系统

```
aep/core/config/
├── envconfig.py          # 纯配置数据模型
├── envmanager.py         # 统一管理器
└── handlers/             # 独立处理器
    ├── base.py           # 基类 (venv/依赖管理)
    ├── tools.py          # 工具处理器
    ├── skills.py         # 技能处理器
    ├── library.py        # 资料库处理器
    └── mcp.py            # MCP 处理器
```

### 处理器 API

```python
# 通过 EnvManager 访问各处理器
manager = EnvManager("./config")

# 工具处理器
manager.tools.add("tool.py", dependencies=["numpy>=1.20"])
manager.tools.add_dependencies("pandas", "scipy")
manager.tools.list()
manager.tools.remove("tool")

# 技能处理器
manager.skills.add("./skill/", dependencies=["requests"])
manager.skills.list()
manager.skills.remove("skill")

# 资料库处理器
manager.library.add("doc.md")
manager.library.list()
manager.library.remove("doc.md")

# MCP 处理器
from aep.core.config import MCPTransport

# STDIO 模式：自动连接并发现 tools
manager.mcp.add(
    name="figma",
    command="npx",
    args=["figma-mcp-server"],
    env={"FIGMA_API_KEY": "xxx"}
)

# HTTP 模式
manager.mcp.add(
    name="remote_tools",
    transport=MCPTransport.HTTP,
    url="http://localhost:8000/mcp",
)
```

### 依赖管理

工具和技能支持版本约束的依赖声明：

```python
# 添加工具时声明依赖
manager.add_tool(
    "./my_tool.py",
    dependencies=[
        "torch==2.0.0",
        "numpy>=1.20",
        "requests<=2.28,>=2.25"
    ]
)

# 依赖会保存到 requirements.txt 并自动安装
```

执行流程：
1. 复制工具文件
2. 保存依赖到 `requirements.txt`
3. 确保虚拟环境存在
4. 通过 `uv pip install` 安装依赖

## 命令参考

### tools 命令

```bash
tools list                    # 列出所有工具
tools info <name>             # 查看工具详情
tools run "<python_code>"     # 执行 Python 代码

# 示例
tools run "tools.grep.search('TODO', './src')"
tools run "tools.file.read('README.md')"
```

### skills 命令

```bash
skills list                   # 列出所有技能
skills info <name>            # 查看技能详情
skills run <path.py> [args]   # 执行技能脚本

# 示例
skills run web-scraper/main.py --url "https://example.com"
```

### Shell 透传

所有非 `tools`/`skills` 开头的命令都会透传给系统 Shell：

```bash
ls .agents/library/
cat .agents/library/api-docs.md
grep "pattern" .agents/library/*.md
git status
```

## MCP 集成

AEP 使用官方 `mcp` SDK 支持 MCP (Model Context Protocol) 服务器，实现能力的连接与**自动发现**：

1. **自动工具发现**：连接后自动查询服务器工具，生成类型化的 Python stub。
2. **Tool-Only 设计**：仅保留工具能力，不处理 prompts/resources 的映射与落地。
3. **能力隔离**：MCP 配置存储在顶层 `_mcp/` 目录，不暴露给 Agent，仅暴露 tool stub。

```python
from aep import EnvManager, MCPTransport

config = EnvManager("./config")

# 添加时自动连接并发现所有能力
config.mcp.add(
    name="filesystem",
    command="npx",
    args=["@anthropic/mcp-server-filesystem", "/workspace"],
)
```

调用方式与普通工具完全一致：

```python
# 调用发现的工具
session.exec('tools run "tools.filesystem.read_file(path=\'/etc/hosts\')"')
```

## 开发

### 运行测试

```bash
uv run pytest tests/ -v
```

### 项目结构

```
aep/
├── src/aep/
│   ├── __init__.py
│   └── core/
│       ├── aep.py           # AEP 主类
│       ├── session.py       # 会话管理
│       ├── executor.py      # 执行器
│       └── config/          # 配置模块
│           ├── envconfig.py
│           ├── envmanager.py
│           └── handlers/
├── tests/
│   ├── test_aep.py
│   ├── test_config.py
│   └── test_session.py
├── arch.md                  # 架构设计
└── devplan.md               # 开发计划
```

## License

MIT
