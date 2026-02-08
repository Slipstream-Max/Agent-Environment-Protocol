# EnvManager API 参考

`EnvManager` 是 AEP 的核心配置管理类，提供统一的接口管理工具、技能和资料库。

## 类定义

```python
class EnvManager:
    """环境管理器 - 统一入口"""
    
    def __init__(self, config_dir: str | Path):
        """
        初始化环境管理器
        
        Args:
            config_dir: 配置目录路径，会自动创建目录结构
        """
```

## 属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `config` | `EnvConfig` | 底层配置对象 |
| `tools` | `ToolsHandler` | 工具处理器 |
| `skills` | `SkillsHandler` | 技能处理器 |
| `library` | `LibraryHandler` | 资料库处理器 |
| `mcp` | `MCPHandler` | MCP 处理器 |

## 便捷方法

### add_tool

```python
def add_tool(
    self,
    source: str | Path,
    name: str | None = None,
    dependencies: list[str] | None = None
) -> Path:
    """
    添加工具（代理到 tools.add）
    
    Args:
        source: 工具源文件路径
        name: 可选，自定义工具名称
        dependencies: 可选，依赖列表
    
    Returns:
        工具文件的目标路径
    """
```

### add_skill

```python
def add_skill(
    self,
    source: str | Path,
    name: str | None = None,
    dependencies: list[str] | None = None
) -> Path:
    """
    添加技能（代理到 skills.add）
    
    Args:
        source: 技能源路径（文件或目录）
        name: 可选，自定义技能名称
        dependencies: 可选，依赖列表
    
    Returns:
        技能目录的目标路径
    """
```

### add_library

```python
def add_library(
    self,
    source: str | Path,
    name: str | None = None
) -> Path:
    """
    添加资料（代理到 library.add）
    
    Args:
        source: 资料源文件路径
        name: 可选，自定义文件名
    
    Returns:
        资料文件的目标路径
    """
```

### add_tool_dependency

```python
def add_tool_dependency(self, *deps: str) -> Path:
    """
    添加工具依赖
    
    Args:
        *deps: 依赖字符串，支持版本约束
    
    Returns:
        requirements.txt 路径
    
    Example:
        >>> manager.add_tool_dependency("numpy>=1.20", "pandas")
    """
```

### index

```python
def index(self) -> None:
    """生成所有索引文件"""
```

---

# ToolsHandler API 参考

## add

```python
def add(
    self,
    source: str | Path,
    name: str | None = None,
    dependencies: list[str] | None = None
) -> Path:
    """
    添加工具
    
    执行流程:
    1. 复制工具文件到 tools 目录
    2. 保存依赖到 requirements.txt
    3. 确保虚拟环境存在
    4. 安装依赖
    
    Args:
        source: 工具源文件路径
        name: 可选，自定义名称（不含 .py 后缀）
        dependencies: 可选，依赖列表
    
    Returns:
        工具文件的目标路径
    
    Example:
        >>> handler.add("grep.py", dependencies=["regex>=2023.0"])
    """
```

## add_dependencies

```python
def add_dependencies(self, *deps: str) -> Path:
    """
    添加依赖到工具环境
    
    Args:
        *deps: 依赖字符串
    
    Returns:
        requirements.txt 路径
    """
```

## sync_dependencies

```python
def sync_dependencies(self) -> None:
    """从 requirements.txt 同步安装依赖"""
```

## list

```python
def list(self) -> list[str]:
    """列出所有工具名称"""
```

## remove

```python
def remove(self, name: str) -> bool:
    """删除工具"""
```

## generate_index

```python
def generate_index(self) -> None:
    """生成工具索引文件"""
```

---

# SkillsHandler API 参考

## add

```python
def add(
    self,
    source: str | Path,
    name: str | None = None,
    dependencies: list[str] | None = None
) -> Path:
    """
    添加技能
    
    支持两种模式:
    - 目录模式: 复制整个技能目录
    - 文件模式: 创建技能目录并将文件重命名为 main.py
    
    Args:
        source: 技能源路径
        name: 可选，自定义名称
        dependencies: 可选，依赖列表
    
    Returns:
        技能目录路径
    """
```

## sync_dependencies

```python
def sync_dependencies(self, skill_name: str) -> None:
    """为指定技能同步依赖"""
```

## list

```python
def list(self) -> list[str]:
    """列出所有技能名称"""
```

## remove

```python
def remove(self, name: str) -> bool:
    """删除技能"""
```

---

# LibraryHandler API 参考

## add

```python
def add(self, source: str | Path, name: str | None = None) -> Path:
    """
    添加资料文件
    
    Args:
        source: 源文件路径
        name: 可选，自定义文件名
    
    Returns:
        资料文件的目标路径
    """
```

## list

```python
def list(self) -> list[str]:
    """列出所有资料文件名"""
```

## remove

```python
def remove(self, name: str) -> bool:
    """删除资料文件"""
```

---

# MCPHandler API 参考

## add

```python
def add(
    self,
    name: str,
    command: list[str] | None = None,
    transport: MCPTransport = MCPTransport.STDIO,
    url: str | None = None,
    headers: dict[str, str] | None = None,
    env: dict[str, str] | None = None,
    tools: list[dict] | None = None,
    dependencies: list[str] | None = None
) -> Path:
    """
    添加 MCP 服务器
    
    Args:
        name: 服务器名称
        command: STDIO 模式的启动命令
        transport: 传输类型 (STDIO 或 HTTP)
        url: HTTP 模式的服务器 URL
        headers: HTTP 模式的请求头
        env: 环境变量
        tools: 工具定义列表
        dependencies: 依赖列表
    
    Returns:
        生成的 stub 文件路径
    
    Example:
        # STDIO 模式
        >>> handler.add(
        ...     "filesystem",
        ...     command=["npx", "@anthropic/mcp-server-filesystem"]
        ... )
        
        # HTTP 模式
        >>> handler.add(
        ...     "remote",
        ...     transport=MCPTransport.HTTP,
        ...     url="http://localhost:8000/mcp"
        ... )
    """
```

## list

```python
def list(self) -> list[str]:
    """列出所有 MCP 服务器名称"""
```

## get_config

```python
def get_config(self, name: str) -> dict | None:
    """获取 MCP 服务器配置"""
```

## remove

```python
def remove(self, name: str) -> bool:
    """删除 MCP 服务器"""
```

---

# MCPTransport 枚举

```python
from enum import Enum

class MCPTransport(str, Enum):
    STDIO = "stdio"   # 本地进程，通过 stdin/stdout 通信
    HTTP = "http"     # Streamable HTTP，连接远程服务
```

---

# EnvConfig API 参考

`EnvConfig` 是纯配置数据模型，只定义路径和配置结构，不包含业务逻辑。

## 路径属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `config_dir` | `Path` | 配置根目录 |
| `tools_dir` | `Path` | 工具目录 |
| `skills_dir` | `Path` | 技能目录 |
| `library_dir` | `Path` | 资料库目录 |
| `mcp_config_dir` | `Path` | MCP 配置目录 |
| `tools_venv_dir` | `Path` | 工具虚拟环境目录 |
| `tools_requirements` | `Path` | 工具依赖文件 |

## 路径方法

```python
def tool_path(self, name: str) -> Path:
    """返回工具文件路径"""

def skill_dir(self, name: str) -> Path:
    """返回技能目录路径"""

def skill_venv_dir(self, name: str) -> Path:
    """返回技能虚拟环境目录"""

def skill_requirements(self, name: str) -> Path:
    """返回技能依赖文件路径"""

def mcp_config_path(self, name: str) -> Path:
    """返回 MCP 配置文件路径"""
```
