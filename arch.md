# Agent Environment Protocol (AEP) Architecture

## 1. 系统目标

AEP 的目标是把 Agent 能力管理分成三层：

1. 配置层：注册 tools / skills / library / mcp
2. 挂载层：把配置目录挂到工作区 `.agents/`
3. 运行层：通过统一命令执行能力

核心对象：

- `EnvManager`：配置管理
- `AEP`：挂载入口
- `AEPSession`：运行时入口（`exec`）

## 2. 目录结构

配置目录：

```text
config_dir/
├── tools/
│   ├── .venv/
│   ├── requirements.txt
│   ├── index.md
│   └── *.py
├── skills/
│   ├── index.md
│   └── <skill-name>/
│       ├── .venv/
│       ├── SKILL.md
│       ├── requirements.txt
│       └── scripts/...
├── library/
│   ├── index.md
│   └── *.md
└── _mcp/
    └── <server>/
        └── config.json
```

工作区挂载目录：

```text
workspace/.agents/
├── tools   -> symlink to config/tools
├── skills  -> symlink to config/skills
└── library -> symlink to config/library
```

## 3. 核心模块

```text
src/aep/core/
├── aep.py                    # AEP.attach/detach
├── session.py                # AEPSession.exec 路由
├── executor.py               # ToolExecutor / SkillExecutor
└── config/
    ├── envconfig.py          # 路径与配置数据
    ├── envmanager.py         # 统一管理器
    └── handlers/
        ├── base.py           # venv/依赖公共逻辑
        ├── tools.py          # tools 管理
        ├── skills.py         # skills 管理
        ├── library.py        # library 管理
        ├── mcp.py            # MCP 集成
        └── skills_util/      # skills parser/validator（本地实现）
```

## 4. 调用链路

### 4.1 配置阶段

- `EnvManager` 初始化目录
- `add_tool` / `add_skill` / `add_library` / `add_mcp_server`
- `index()` 生成三类索引

### 4.2 挂载阶段

- `AEP.attach(workspace, config)` 创建 `.agents`
- 创建 `tools/skills/library` 三个符号链接

### 4.3 运行阶段

- `AEPSession.exec(command)` 按前缀路由：
  - `tools ...`
  - `skills ...`
  - `cd` / `export`
  - 其他命令透传 shell

执行组件：

- `ToolExecutor`：在 `tools/.venv` 执行 Python 代码
- `SkillExecutor`：在 `skills/<name>/.venv` 执行脚本

## 5. Skills 设计（当前实现）

### 5.1 输入模式

`SkillsHandler.add(source, name=None, dependencies=None)` 支持：

- 目录输入：复制整个 skill 目录
- 单文件输入：仅接受 `.md`，按 frontmatter `name` 建目录并保存为 `SKILL.md`

### 5.2 校验

添加后会调用本地 validator（`handlers/skills_util/validator.py`）做规范校验：

- 必填字段：`name`, `description`
- `name` 格式校验
- `description` 长度校验
- 目录名与 `name` 一致性
- 不允许未定义 frontmatter 字段

校验失败会回滚删除目标 skill 目录。

### 5.3 索引

`skills/index.md` 由 parser 读取 `SKILL.md` frontmatter 生成：

- `name`
- `description`
- `path`（skill 目录）

并追加统一运行提示：`skills run xx.py`。

## 6. MCP 设计

`MCPHandler.add(...)` 支持两种传输：

- `STDIO`：`command + args + env`
- `HTTP`：`url + headers`

流程：

1. 参数校验
2. 前置工具检查（STDIO）
3. 保存 `_mcp/<name>/config.json`
4. 连接并发现 tools
5. 生成 `tools/<name>.py` stub

## 7. 上下文拼装

`AEPSession.get_context()` 会拼接：

- `tools/index.md`
- `skills/index.md`
- `library/index.md`

用于给 Agent 注入 L0 能力概览。

## 8. 关键权衡

- 通过目录和 index 保持可审计与可读性
- skills 强制 frontmatter 校验，降低运行期歧义
- 工具与技能分离 venv，隔离依赖污染
- MCP 统一转换为 tools 调用语法，减少 Agent 侧分支逻辑
