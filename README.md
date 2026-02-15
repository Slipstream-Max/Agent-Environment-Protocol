# AEP - Agent Environment Protocol

> 为 AI Agent 提供统一的能力发现和调用接口。

## 核心概念

AEP 通过目录化配置管理三类能力：

- `tools/`：Python 工具与 MCP 生成的工具 stub
- `skills/`：脚本型能力（带 `SKILL.md`）
- `library/`：资料文档

运行时通过 `AEP.attach(...)` 挂载到工作区 `.agents/`，再由 `AEPSession.exec(...)` 统一调用。

## 快速开始

### 安装

```bash
uv add aep
```

### 配置 + 挂载 + 运行

```python
from aep import EnvManager, AEP

# 1) 配置阶段
config = EnvManager("./agent_capabilities")

config.add_tool("./tools/grep.py", dependencies=["regex>=2023.0"])
config.add_skill("./skills/web-scraper")
config.add_library("./docs/api-docs.md")

# 生成 index.md（tools/skills/library）
config.index()

# 2) 挂载阶段
aep = AEP.attach(workspace="./my_project", config=config)

# 3) 运行阶段
session = aep.create_session()
print(session.exec("tools list").stdout)
print(session.exec("skills list").stdout)
```

## Skills 规则（当前实现）

### 目录技能

技能目录至少包含 `SKILL.md`，并满足 frontmatter 规范：

```yaml
---
name: web-scraper
description: Crawl and parse web pages. Use when user asks to fetch and extract webpage content.
---
```

约束由内置 validator 校验（基于 Agent Skills 规则），包括：

- `name` 必填、<=64、仅小写字母/数字/连字符
- `description` 必填、非空、<=1024
- 目录名必须与 `name` 一致

### 单文件技能（.md）

`add_skill()` 支持单文件输入，但仅支持 `.md`：

- 从 frontmatter 读取 `name`
- 自动创建 `skills/<name>/SKILL.md`
- 若 `name` 参数与 frontmatter 不一致，直接报错

### 在 skills 里放脚本

推荐结构：

```text
my-skill/
├── SKILL.md
└── scripts/
    └── run.py
```

执行方式：

```bash
skills run my-skill/scripts/run.py [args]
```

`skills index.md` 当前输出字段：`name / description / path`，并附统一提示：`skills run xx.py`。

## 命令参考

### tools

```bash
tools list
tools info <name>
tools run "<python_code>"
```

### skills

```bash
skills list
skills info <name>
skills run <path.py> [args]
```

### 内置命令

```bash
cd [path]
export KEY=VALUE
```

其他命令将透传到系统 shell。

## MCP 集成

AEP 使用官方 `mcp` SDK：

- `config.add_mcp_server(...)` 连接并发现工具
- 自动在 `tools/` 生成 python stub
- 运行期统一通过 `tools run "tools.<mcp_name>.<method>(...)"` 调用

示例：

```python
from aep import EnvManager
from aep.core.config.handlers.mcp import MCPTransport

config = EnvManager("./config")
config.add_mcp_server(
    "filesystem",
    transport=MCPTransport.STDIO,
    command="npx",
    args=["@anthropic/mcp-server-filesystem", "/workspace"],
)
config.index()
```

## 示例脚本

- 完整端到端示例：`examples/demo.py`
- skills/scripts 示例：`examples/demo_skill_scripts.py`

运行：

```bash
uv run python examples/demo.py
uv run python examples/demo_skill_scripts.py
```

## 开发

```bash
uv run pytest tests -q
```

## License

MIT
