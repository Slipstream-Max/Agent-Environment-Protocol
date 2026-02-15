# AEP 开发计划

> 增量交付，每个阶段结束都有可测试的产出。
> 核心理念：AEP 是一个基于 `exec` 的统一接口环境，Agent 通过命令与环境交互，支持 Python 代码编排。

---

## 设计哲学

**借鉴 Harbor 框架的设计**：
- Harbor 通过 `BaseEnvironment.exec()` 暴露终端能力给 Agent
- AEP 采用相同理念：**`exec(command)` 是唯一对外接口**
- Agent 不需要学习多个 tool schemas，只需要执行命令

**核心交互模式**：
```
LLM (Agent) --exec(command)--> AEP Session --路由--> Tools/Skills/Shell
```

**命令类型**：
| 命令前缀 | 处理方式 | 示例 |
|---------|---------|-----|
| `tools ...` | AEP 内置命令 | `tools run "tools.grep.search('TODO', '.')"` |
| `skills ...` | AEP 内置命令 | `skills run web-scraper/main.py --url ...` |
| 其他 | Shell 透传 | `ls -la`, `cat .agents/library/api.md`, `git status` |

---

## 核心架构：Config + Attach 模式

### 设计理念

**问题**：传统方式将工具物理复制到每个工作区，无法复用，难以管理。

**解决方案**：分离"能力配置"和"工作区"，通过**符号链接**真实挂载。

```
┌─────────────────────────────────────────────────────────────────┐
│                     AEPConfig (能力配置)                         │
│  可复用、集中管理、版本控制                                       │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐                │
│  │   tools/    │ │   skills/   │ │  library/   │                │
│  │  grep.py    │ │ web-scraper │ │ api-docs.md │                │
│  │  file_edit  │ │ data-anlys  │ │ standards   │                │
│  └─────────────┘ └─────────────┘ └─────────────┘                │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           │  attach (符号链接挂载)
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Workspace (工作区)                           │
│  ./my_project/                                                   │
│  ├── .agents/              ← 真实目录                             │
│  │   ├── tools/           ← symlink -> config/tools/            │
│  │   ├── skills/          ← symlink -> config/skills/           │
│  │   └── library/         ← symlink -> config/library/          │
│  └── src/                 ← 用户真实代码                         │
│      └── main.py                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 符号链接的优势

Agent 可以像访问普通目录一样操作 `.agents/`：
```bash
# 这些标准 shell 命令都能正常工作
ls .agents/
cd .agents/library
cat .agents/library/api-docs.md
cat .agents/tools/index.md
grep "TODO" .agents/library/*.md
```

### 两阶段 API

```python
# === 阶段一：配置阶段 (Config) ===
from aep import EnvManager

config = EnvManager("./my_agent_capabilities")
config.add_tool("./shared_tools/grep.py")
config.add_tool("./shared_tools/file_edit.py")
config.add_skill("./shared_skills/web-scraper/", dependencies=["requests"])
config.add_library("./docs/api-docs.md")
config.index()  # 生成索引

# 配置目录结构：
# ./my_agent_capabilities/
# ├── tools/
# │   ├── index.md
# │   ├── grep.py
# │   └── grep.md
# ├── skills/
# │   ├── index.md
# │   └── web-scraper/
# │       ├── SKILL.md
# │       ├── main.py
# │       └── venv/
# └── library/
#     ├── index.md
#     └── api-docs.md


# === 阶段二：挂载阶段 (Attach) ===
from aep import AEP

aep = AEP.attach(
    workspace="./my_project",
    config=config,
)

# attach() 内部逻辑：
# 1. 创建 .agents/ 目录
# 2. 创建符号链接:
#    .agents/tools/   -> config/tools/
#    .agents/skills/  -> config/skills/
#    .agents/library/ -> config/library/

session = aep.create_session()
```

### 高级特性：选择性挂载

```python
aep = AEP.attach(
    workspace="./my_project",
    config=config,
    include_tools=["grep", "file_edit"],     # 只挂载这些工具
    exclude_skills=["dangerous-skill"],       # 排除某些技能
)
```

---

## Phase 0: 环境基础 ✅

**目标**: 基础项目结构

| 任务 | 产出 | 状态 |
|------|------|------|
| uv 初始化 | `pyproject.toml` | ✅ Done |
| 基础模块 | `aep/core/` | ✅ Done |
| 日志集成 | Loguru 集成 | ✅ Done |

---

## Phase 1: EnvManager 系统 ✅

**目标**: 实现能力配置的创建和管理

| 任务 | 产出 | 状态 |
|------|------|------|
| EnvManager 类 | `aep/core/config/envmanager.py` | ✅ Done |
| add_tool() | 添加工具到配置 | ✅ Done |
| add_skill() | 添加技能 | ✅ Done (venv 待实现) |
| add_library() | 添加资料 | ✅ Done |
| index() | 生成 L0/L1 索引文档 | ✅ Done |

**配置目录结构**:
```
config_dir/
├── tools/
│   ├── index.md          # L0: 工具列表
│   ├── grep.py           # 工具实现
│   └── grep.md           # L1: 工具详细文档
├── skills/
│   ├── index.md          # L0: 技能列表
│   └── web-scraper/
│       ├── SKILL.md      # L1: 技能文档
│       ├── main.py
│       ├── requirements.txt
│       └── venv/
└── library/
    ├── index.md          # L0: 资料列表
    └── api-docs.md
```

---

## Phase 2: AEP.attach() 与 Session ✅

**目标**: 实现符号链接挂载和会话管理

| 任务 | 产出 | 状态 |
|------|------|------|
| AEP.attach() | 创建 .agents/ + 符号链接 | ✅ Done |
| Session 类 | `aep/core/session.py` | ✅ Done |
| 状态管理 | `cwd`, `env` 持久化 | ✅ Done |
| exec() | 命令执行入口 | ✅ Done |
| 命令路由 | 区分 tools/skills/shell | ✅ Done |

**核心代码**:
```python
class AEP:
    def attach(cls, workspace: Path, config: EnvManager) -> "AEP":
        instance = cls()
        instance.workspace = Path(workspace)
        instance.config = config
        
        # 创建 .agents/ 目录
        agent_dir = instance.workspace / ".agents"
        agent_dir.mkdir(exist_ok=True)
        
        # 创建符号链接 (如果不存在)
        for name in ["tools", "skills", "library"]:
            link = agent_dir / name
            target = getattr(config, f"{name}_dir")
            if not link.exists():
                link.symlink_to(target, target_is_directory=True)
        
        return instance
    
    def create_session(self) -> "AEPSession":
        return AEPSession(self.workspace, self.config)


class AEPSession:
    def __init__(self, workspace: Path, config: EnvManager):
        self.workspace = workspace
        self.config = config
        self.cwd = workspace
        self.env = {}
    
    def exec(self, command: str) -> ExecResult:
        """唯一对外接口"""
        parts = shlex.split(command)
        cmd = parts[0] if parts else ""
        
        if cmd == "tools":
            return self._handle_tools(parts[1:])
        elif cmd == "skills":
            return self._handle_skills(parts[1:])
        else:
            # 所有其他命令直接透传给 shell
            # 包括 ls, cd, cat, grep 等
            return self._shell_passthrough(command)
```

---

## Phase 3: Tools 系统 ✅

**目标**: 实现 `tools` 命令族 + Python 代码执行引擎

| 任务 | 产出 | 状态 |
|------|------|------|
| ToolExecutor | 独立的工具执行器 | ✅ Done |
| tools list | 列出所有工具 | ✅ Done |
| tools info | 显示工具详情 | ✅ Done |
| tools run | 在独立 venv 中执行 Python 代码 | ✅ Done |
| tools install | 安装依赖到 tools 环境 | ✅ Done |
| uv 集成 | 使用 uv 管理虚拟环境 | ✅ Done |

**架构设计**:
```
Session (exec 路由 + 上下文管理)
    └── ToolExecutor (工具执行，共享 venv)
    └── SkillExecutor (技能执行，每个技能独立 venv)
    └── MCPExecutor (MCP 服务器调用)
```

**命令清单**:
```bash
tools list                              # 列出所有工具
tools info <name>                       # 工具详情
tools run "<python_code>"               # 在共享 venv 中执行 Python 代码
tools install <package>...              # 安装依赖到 tools 环境

# 示例
tools run "tools.grep.search('TODO', './src')"
tools install pandas numpy              # 安装数据科学库
```

**工具目录结构**:
```
tools/
├── .venv/             # 共享的虚拟环境 (uv 管理)
├── requirements.txt   # 依赖清单
├── index.md           # 工具列表
├── grep.py            # 工具模块
└── file_edit.py
```

**工具文件规范** (`tools/grep.py`):
```python
"""
grep - Search patterns in files

Usage:
    tools run "tools.grep.search(pattern, path)"
"""

def search(pattern: str, path: str) -> list[dict]:
    """搜索匹配的行"""
    ...

def count(pattern: str, path: str) -> int:
    """计数匹配数量"""
    return len(search(pattern, path))
```

---

## Phase 4: Skills 系统 ✅

**目标**: 复杂能力包，每个技能有独立 venv，支持脚本执行

| 任务 | 产出 | 状态 |
|------|------|------|
| SkillExecutor | 独立的技能执行器 | ✅ Done |
| skills list | 列出所有技能 | ✅ Done |
| skills info | 显示技能详情 | ✅ Done |
| skills run | 在技能 venv 中执行脚本 | ✅ Done |
| skills install | 为技能安装依赖 | ✅ Done |
| uv 集成 | 使用 uv 管理虚拟环境 | ✅ Done |

**命令清单**:
```bash
skills list                             # 列出技能
skills info <name>                      # 技能详情
skills run <path.py> [args]             # 在技能的 venv 中执行脚本
skills install <name> <package>...      # 为技能安装依赖

# 示例
skills run web-scraper/main.py --url "https://example.com"
skills install web-scraper beautifulsoup4
```

---

## Phase 5: Library (纯文件系统)

**目标**: 静态知识库，通过标准 shell 命令访问

**无专门命令**，Agent 直接使用 shell：
```bash
# 列出资料
ls .agents/library/

# 查看内容
cat .agents/library/api-docs.md

# 搜索
grep "authentication" .agents/library/*.md
```

---

## Phase 6: MCP 集成 ✅

**目标**: 支持 MCP Server，使用官方 `mcp` SDK **自动发现**并转换为 tools/skills 统一调用

**核心设计**: MCP 服务器添加时自动连接并查询 `list_tools` 和 `list_prompts`：
1. **Tools** → 自动生成 Python stub 到 `tools/` 目录。
2. **Prompts** → 自动生成 `SKILL.md` 文档到 `skills/{name}/` 目录。

**能力隔离**: MCP 的配置原始文件存放在顶层 `_mcp/` 目录，该目录**不会**被挂载到 `.agents/` 工作区，Agent 仅能看到生成出的工具和文档。

| 任务 | 产出 | 状态 |
|------|------|------|
| mcp SDK 集成 | 引入官方 `mcp` 依赖 | ✅ Done |
| 自动发现机制 | 自动调用 `list_tools`/`list_prompts` | ✅ Done |
| STDIO 传输 | 支持本地进程通信 | ✅ Done |
| HTTP 传输 | 支持 Streamable HTTP | ✅ Done |
| Python stub 生成 | 根据发现的 Tool Schema 生成方法 | ✅ Done |
| Prompt 文档化 | 自动生成 `SKILL.md` 文档 | ✅ Done |

**使用方式**:
```python
from aep import EnvManager, MCPTransport

config = EnvManager("./agent_capabilities")

# 添加时自动连接并发现所有能力
config.mcp.add(
    name="filesystem",
    command="npx",
    args=["@anthropic/mcp-server-filesystem", "/workspace"],
)

# 运行时 - Agent 统一使用 tools 接口
session.exec('tools run "tools.filesystem.read_file(path=\'/etc/hosts\')"')
```

**目录结构**:
```
config_dir/
├── tools/
│   ├── index.md
│   ├── filesystem.py      # 自动生成的 MCP stub (STDIO)
│   └── grep.py            # 普通 Python 工具
├── skills/
│   └── filesystem/        # MCP Prompts 映射
│       └── SKILL.md
└── _mcp/                  # MCP 配置存储（不挂载到工作区）
    └── filesystem/
        ├── config.json
        └── manifest.json
```

---

## Phase 7: Agent 集成接口

**目标**: 完善对外暴露的 API

| 任务 | 产出 | 验证 |
|------|------|------|
| get_context() | 返回 L0 上下文 | 内容检查 |
| 错误处理 | 统一的 ExecResult | 异常捕获 |

---

## 完整使用流程

```python
from aep import EnvManager, AEP

# === 阶段一：配置阶段 (一次性，可复用) ===
config = EnvManager("./agent_capabilities")
config.add_tool("./shared_tools/grep.py")
config.add_tool("./shared_tools/file_edit.py")
config.add_skill("./shared_skills/web-scraper/", dependencies=["requests"])
config.add_library("./docs/api-docs.md")
config.index()


# === 阶段二：挂载阶段 (每个项目) ===
aep = AEP.attach(
    workspace="./my_project",
    config=config,
)
# 结果: ./my_project/.agents/ 下有符号链接指向 config


# === 阶段三：运行时 (暴露给 LLM) ===
session = aep.create_session()

# 获取上下文 (注入 System Prompt)
context = session.get_context()

# exec 是唯一接口
result = session.exec("ls .agents/")                    # 浏览能力目录
result = session.exec("cat .agents/library/api.md")     # 查看资料
result = session.exec("tools list")                    # 列出工具
result = session.exec("tools run \"tools.grep.search('TODO', '.')\"")
result = session.exec("skills run web-scraper/main.py --url '...'")
result = session.exec("git status")                    # 普通 shell
```

---

## 目录结构总览

```
# 配置目录 (集中管理，可复用)
agent_capabilities/
├── tools/
│   ├── .venv/             # 共享虚拟环境 (uv 管理)
│   ├── requirements.txt
│   ├── index.md
│   ├── grep.py            # Python 工具
│   └── filesystem.py      # MCP 工具 (自动生成)
├── skills/
│   ├── index.md
│   ├── web-scraper/       # 技能独立目录
│   └── filesystem/        # MCP Prompts (自动生成)
│       └── SKILL.md
├── library/
│   └── index.md
└── _mcp/                  # MCP 配置存储 (不挂载到工作区)
    └── filesystem/
        ├── config.json
        └── manifest.json

# 工作区 (每个项目)
my_project/
├── .agents/
│   ├── tools/     -> symlink to agent_capabilities/tools/
│   ├── skills/    -> symlink to agent_capabilities/skills/
│   └── library/   -> symlink to agent_capabilities/library/
└── src/
    └── main.py
```

---

## ExecResult 结构

```python
class ExecResult(BaseModel):
    stdout: str | None = None
    stderr: str | None = None
    return_code: int
```

所有 `exec()` 调用都返回统一的 `ExecResult`，Agent 可以通过 `return_code` 判断成功与否。
