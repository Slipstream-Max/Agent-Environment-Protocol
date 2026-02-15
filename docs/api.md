# AEP API Reference

本文档基于当前代码实现，覆盖 `EnvManager`、各 Handler、`AEP` 与 `AEPSession` 的核心接口。

## 1. EnvManager

文件：`src/aep/core/config/envmanager.py`

### 1.1 构造

```python
EnvManager(
    config_dir: str | Path,
    *,
    auto_init_tool_env: bool = False,
    include_default_tool_dependencies: bool = True,
    tool_dependencies: list[str] | None = None,
)
```

### 1.2 处理器属性

- `tools: ToolsHandler`
- `skills: SkillsHandler`
- `library: LibraryHandler`
- `mcp: MCPHandler`

### 1.3 便捷方法

- `add_tool(source, name=None, dependencies=None) -> Path`
- `add_skill(source, name=None, dependencies=None) -> Path`
- `add_library(source, name=None) -> Path`
- `add_mcp_server(name, **kwargs) -> Path`
- `add_tool_dependency(*packages) -> Path`
- `init_tool_environment(*, dependencies=None, include_default=True) -> Path`
- `index() -> None`

### 1.4 目录属性

- `config_dir: Path`
- `tools_dir: Path`
- `skills_dir: Path`
- `library_dir: Path`

## 2. ToolsHandler

文件：`src/aep/core/config/handlers/tools.py`

### 2.1 主要方法

- `add(source, name=None, dependencies=None) -> Path`
- `add_dependencies(*packages) -> Path`
- `sync_dependencies() -> None`
- `list() -> list[str]`
- `remove(name) -> bool`
- `generate_index() -> None`

### 2.2 add 执行顺序

1. 复制工具文件到 `tools/`
2. 写入 `tools/requirements.txt`
3. 确保 `tools/.venv`
4. 安装依赖

## 3. SkillsHandler

文件：`src/aep/core/config/handlers/skills.py`

### 3.1 主要方法

- `add(source, name=None, dependencies=None) -> Path`
- `sync_dependencies(name) -> None`
- `list() -> list[str]`
- `remove(name) -> bool`
- `generate_index() -> None`

### 3.2 add 规则（重点）

`source` 支持目录或单文件 `.md`：

- 目录模式：复制整个目录到 `skills/<name>/`
- 单文件模式：
  - 仅允许 `.md`
  - 解析 frontmatter `name`
  - 目录名以该 `name` 为准
  - 若传入 `name` 且与 frontmatter 不一致，抛错

随后统一做 validator 校验；失败会删除刚复制的技能目录。

### 3.3 索引格式

`generate_index()` 从 `SKILL.md` 读取 frontmatter，输出：

- `name`
- `description`
- `path`（技能目录）

并在底部提示：`skills run xx.py`。

### 3.4 Skills 脚本调用

放在技能目录内任意 `.py` 均可调用，推荐 `scripts/`：

```bash
skills run <skill>/scripts/<file>.py [args]
```

## 4. LibraryHandler

文件：`src/aep/core/config/handlers/library.py`

- `add(source, name=None) -> Path`
- `list() -> list[str]`
- `remove(name) -> bool`
- `generate_index() -> None`

## 5. MCPHandler

文件：`src/aep/core/config/handlers/mcp.py`

### 5.1 MCPTransport

- `MCPTransport.STDIO`
- `MCPTransport.HTTP`

### 5.2 add

```python
add(
    name: str,
    *,
    command: str | None = None,
    args: list[str] | None = None,
    env: dict[str, str] | None = None,
    url: str | None = None,
    headers: dict[str, str] | None = None,
    transport: MCPTransport = MCPTransport.STDIO,
) -> Path
```

### 5.3 其他方法

- `list() -> list[str]`
- `get_config(name) -> MCPServerConfig | None`
- `remove(name) -> bool`
- `refresh(name) -> Path`

## 6. AEP

文件：`src/aep/core/aep.py`

- `AEP.attach(workspace, config, agent_dir=".agents") -> AEP`
- `create_session() -> AEPSession`
- `detach() -> None`

`attach()` 会在工作区建立 `.agents/tools|skills|library` 符号链接。

## 7. AEPSession

文件：`src/aep/core/session.py`

### 7.1 统一入口

- `exec(command: str) -> ExecResult`
- `get_context() -> str`

### 7.2 命令路由

- `tools list|info|run`
- `skills list|info|run`
- `cd`
- `export`
- 其他命令透传 shell

### 7.3 ExecResult

文件：`src/aep/core/executor.py`

```python
@dataclass
class ExecResult:
    stdout: str = ""
    stderr: str = ""
    return_code: int = 0
```

## 8. EnvConfig

文件：`src/aep/core/config/envconfig.py`

### 8.1 目录属性

- `tools_dir`
- `tools_venv_dir`
- `tools_requirements`
- `skills_dir`
- `library_dir`
- `mcp_config_dir`

### 8.2 路径方法

- `tool_path(name) -> Path`
- `skill_dir(name) -> Path`
- `skill_venv_dir(name) -> Path`
- `skill_requirements(name) -> Path`
- `mcp_config_path(name) -> Path`
