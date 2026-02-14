"""
MCPHandler - MCP 服务器管理处理器

使用官方 mcp SDK 连接 MCP 服务器，自动发现 tool 能力，
并映射到 AEP 的目录结构中：
  - tools → tools/{name}.py (stub 文件)

每次工具调用都会 spawn 一个新的连接。
"""

from __future__ import annotations

import asyncio
import json
import shutil
from contextlib import asynccontextmanager
from enum import Enum
from pathlib import Path
from typing import Any, AsyncIterator, Optional

from loguru import logger

from ..envconfig import EnvConfig, MCPServerConfig
from .base import BaseHandler


class MCPTransport(Enum):
    """MCP 传输方式"""

    STDIO = "stdio"  # 标准输入输出（本地进程，默认）
    HTTP = "http"  # Streamable HTTP（Web 服务）


class MCPHandler(BaseHandler):
    """
    MCP 服务器管理处理器

    核心流程：
    1. add() 接收服务器配置
    2. 检查前置工具 (npx/node/uv)
    3. 连接 MCP 服务器，自动发现 tools
    4. 生成 tool stub（tools/{name}.py）
    5. 保存配置
    """

    def __init__(self, config: EnvConfig):
        self.config = config

    # ==================== Public API ====================

    def add(
        self,
        name: str,
        *,
        # STDIO 模式参数
        command: Optional[str] = None,
        args: Optional[list[str]] = None,
        env: Optional[dict[str, str]] = None,
        # HTTP 模式参数
        url: Optional[str] = None,
        headers: Optional[dict[str, str]] = None,
        # 通用参数
        transport: MCPTransport = MCPTransport.STDIO,
    ) -> Path:
        """
        添加 MCP 服务器

        连接到 MCP 服务器，自动发现 tools，
        并生成对应的 stub 文件。

        Args:
            name: 服务器名称（将作为工具模块名，推荐用下划线命名）
            command: STDIO 模式启动命令 (如 "npx", "uv", "python")
            args: STDIO 模式命令参数
            env: STDIO 模式额外环境变量
            url: HTTP 模式服务 URL
            headers: HTTP 模式请求头
            transport: 传输方式，默认 STDIO

        Returns:
            生成的工具 stub 文件路径

        Example (STDIO)::

            handler.add(
                "figma",
                command="npx",
                args=["figma-mcp-server"],
                env={"FIGMA_API_KEY": "xxx"},
            )

        Example (HTTP)::

            handler.add(
                "remote_tools",
                transport=MCPTransport.HTTP,
                url="http://localhost:8000/mcp",
            )
        """
        self._validate_transport_args(transport, command=command, url=url)

        # 2. 检查前置工具
        if transport == MCPTransport.STDIO:
            self._check_prerequisites(command)

        # 3. 保存服务器配置
        mcp_config = MCPServerConfig(
            name=name,
            transport=transport.value,
            command=[command] + (args or []) if command else None,
            env=env or {},
            url=url,
            headers=headers or {},
            tools=[],  # 将在发现后更新
        )

        config_dir = self.config.mcp_config_path(name)
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "config.json"
        config_file.write_text(
            json.dumps(mcp_config.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        # 4. 连接并发现能力
        logger.info(f"连接 MCP 服务器: {name} ({transport.value})")
        try:
            discovered = asyncio.run(self._discover(name, transport, mcp_config))
        except Exception as e:
            logger.error(f"MCP 服务器连接/发现失败: {e}")
            raise RuntimeError(
                f"无法连接到 MCP 服务器 '{name}': {e}\n"
                f"请确认服务器配置正确且可以正常启动。"
            )

        tools_info = discovered.get("tools", [])

        # 5. 生成 tool stub
        stub_file = self._generate_stub(name, transport, mcp_config, tools_info)

        logger.info(
            f"MCP 服务器添加完成: {name} (发现 {len(tools_info)} 个工具)"
        )
        return stub_file

    def list(self) -> list[str]:
        """列出所有 MCP 服务器名称"""
        if not self.config.mcp_config_dir.exists():
            return []
        return [
            d.name
            for d in self.config.mcp_config_dir.iterdir()
            if d.is_dir() and (d / "config.json").exists()
        ]

    def get_config(self, name: str) -> Optional[MCPServerConfig]:
        """获取 MCP 服务器配置"""
        config_file = self.config.mcp_config_path(name) / "config.json"
        if not config_file.exists():
            return None
        data = json.loads(config_file.read_text(encoding="utf-8"))
        return MCPServerConfig.from_dict(data)

    def remove(self, name: str) -> bool:
        """删除 MCP 服务器（包括 stub 和配置）"""
        removed = False

        # 删除 tool stub
        stub_file = self.config.tool_path(name)
        if stub_file.exists():
            stub_file.unlink()
            removed = True

        # 删除 MCP 配置目录
        config_dir = self.config.mcp_config_path(name)
        if config_dir.exists():
            shutil.rmtree(config_dir)
            removed = True

        if removed:
            logger.info(f"删除 MCP 服务器: {name}")
        return removed

    def refresh(self, name: str) -> Path:
        """重新连接 MCP 服务器，刷新发现的能力"""
        config = self.get_config(name)
        if config is None:
            raise FileNotFoundError(f"MCP 服务器不存在: {name}")

        transport = MCPTransport(config.transport)

        # 重新发现
        logger.info(f"刷新 MCP 服务器: {name}")
        discovered = asyncio.run(self._discover(name, transport, config))

        tools_info = discovered.get("tools", [])

        # 重新生成 stub
        stub_file = self._generate_stub(name, transport, config, tools_info)

        logger.info(
            f"MCP 服务器刷新完成: {name} (发现 {len(tools_info)} 个工具)"
        )
        return stub_file

    # ==================== Discovery ====================

    async def _discover(
        self,
        name: str,
        transport: MCPTransport,
        config: MCPServerConfig,
    ) -> dict[str, list[dict]]:
        """
        连接 MCP 服务器并发现其暴露的 tools

        Returns:
            {"tools": [...]} 
        """
        from mcp import ClientSession

        result: dict[str, list[dict]] = {"tools": []}

        async with self._connect(transport, config) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await self._fetch_tools(session)

        return result

    @asynccontextmanager
    async def _connect(
        self,
        transport: MCPTransport,
        config: MCPServerConfig,
    ) -> AsyncIterator[tuple[Any, Any]]:
        """统一连接抽象：根据 transport 建立会话流。"""
        match transport:
            case MCPTransport.STDIO:
                from mcp import StdioServerParameters
                from mcp.client.stdio import stdio_client

                server_params = StdioServerParameters(
                    command=config.command[0] if config.command else "",
                    args=config.command[1:]
                    if config.command and len(config.command) > 1
                    else [],
                    env=config.env if config.env else None,
                )

                async with stdio_client(server_params) as streams:
                    yield streams

            case MCPTransport.HTTP:
                import httpx
                from mcp.client.streamable_http import streamable_http_client

                async with httpx.AsyncClient(
                    headers=config.headers if config.headers else None
                ) as http_client:
                    async with streamable_http_client(
                        config.url or "",
                        http_client=http_client,
                    ) as (read, write, _):
                        yield (read, write)

            case _:
                raise ValueError(f"不支持的 MCP transport: {transport.value}")

    async def _fetch_tools(self, session: Any) -> dict[str, list[dict]]:
        """从已连接的 session 中获取 tools"""
        tools: list[dict] = []

        # 获取工具列表
        try:
            tools_result = await session.list_tools()
            for tool in tools_result.tools:
                tools.append(
                    {
                        "name": tool.name,
                        "description": tool.description or "",
                        "inputSchema": tool.inputSchema
                        if hasattr(tool, "inputSchema")
                        else {},
                    }
                )
        except Exception as e:
            logger.warning(f"获取工具列表失败: {e}")

        return {"tools": tools}

    # ==================== Prerequisites ====================

    def _check_prerequisites(self, command: str) -> None:
        """检查运行 MCP 服务器所需的前置工具"""
        if not shutil.which(command):
            hints = {
                "npx": "请安装 Node.js: https://nodejs.org/",
                "node": "请安装 Node.js: https://nodejs.org/",
                "uv": "请安装 uv: https://docs.astral.sh/uv/getting-started/installation/",
                "python": "请安装 Python: https://www.python.org/downloads/",
                "uvx": "请安装 uv: https://docs.astral.sh/uv/getting-started/installation/",
            }
            hint = hints.get(command, f"请确保 '{command}' 已安装并在 PATH 中")
            raise RuntimeError(f"未找到命令 '{command}'。{hint}")

        logger.debug(f"前置检查通过: {command}")

    # ==================== Stub Generation ====================

    def _generate_stub(
        self,
        name: str,
        transport: MCPTransport,
        config: MCPServerConfig,
        tools_info: list[dict],
    ) -> Path:
        """生成工具 stub 文件（使用 mcp SDK 调用）"""

        # 构建连接参数的 Python 代码
        connect_code = self._build_connect_code(transport, config)

        # 构建工具方法
        methods_code = self._build_tool_methods(tools_info)

        # 构建 docstring
        if tools_info:
            tools_doc = "\n".join(
                f"  - {t['name']}: {t.get('description', '')}" for t in tools_info
            )
            docstring = (
                f'"""\n'
                f"MCP Server ({transport.value}): {name}\n\n"
                f"可用工具:\n{tools_doc}\n"
                f'"""'
            )
        else:
            docstring = (
                f'"""\n'
                f"MCP Server ({transport.value}): {name}\n\n"
                f"使用 call(tool_name, **kwargs) 调用 MCP 工具\n"
                f'"""'
            )

        stub_content = f'''{docstring}

import asyncio
from mcp import ClientSession

{connect_code}


def _call_mcp(tool_name: str, arguments: dict):
    """调用 MCP 工具（每次 spawn 新连接）"""
    return asyncio.run(_async_call_mcp(tool_name, arguments))


async def _async_call_mcp(tool_name: str, arguments: dict):
    """异步连接 MCP 服务器并调用工具"""
    async with _connect() as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)

            # 提取结果文本
            texts = []
            for content in result.content:
                if hasattr(content, "text"):
                    texts.append(content.text)
                elif hasattr(content, "data"):
                    texts.append(str(content.data))

            return "\\n".join(texts) if texts else None


def call(tool_name: str, **kwargs):
    """
    调用 MCP 工具（通用入口）

    Args:
        tool_name: 工具名称
        **kwargs: 工具参数

    Returns:
        工具返回结果
    """
    return _call_mcp(tool_name, {{k: v for k, v in kwargs.items() if v is not None}})

{methods_code}
'''

        stub_file = self.config.tool_path(name)
        stub_file.write_text(stub_content, encoding="utf-8")
        return stub_file

    def _build_connect_code(
        self,
        transport: MCPTransport,
        config: MCPServerConfig,
    ) -> str:
        """统一连接代码构建入口。"""
        match transport:
            case MCPTransport.STDIO:
                return self._build_stdio_connect_code(config)
            case MCPTransport.HTTP:
                return self._build_http_connect_code(config)
            case _:
                raise ValueError(f"不支持的 MCP transport: {transport.value}")

    def _build_stdio_connect_code(self, config: MCPServerConfig) -> str:
        """生成 STDIO 连接代码"""
        command = config.command[0] if config.command else ""
        args = json.dumps(config.command[1:] if config.command else [])
        env = json.dumps(config.env or {})

        return f'''
from contextlib import asynccontextmanager
from mcp import StdioServerParameters
from mcp.client.stdio import stdio_client

_SERVER_PARAMS = StdioServerParameters(
    command={json.dumps(command)},
    args={args},
    env={env} or None,
)


@asynccontextmanager
async def _connect():
    """建立 STDIO 连接"""
    async with stdio_client(_SERVER_PARAMS) as streams:
        yield streams
'''

    def _build_http_connect_code(self, config: MCPServerConfig) -> str:
        """生成 HTTP (Streamable HTTP) 连接代码"""
        url = json.dumps(config.url or "")
        headers = json.dumps(config.headers or {})

        return f'''
from contextlib import asynccontextmanager
import httpx
from mcp.client.streamable_http import streamable_http_client

_MCP_URL = {url}
_MCP_HEADERS = {headers}


@asynccontextmanager
async def _connect():
    """建立 Streamable HTTP 连接"""
    async with httpx.AsyncClient(headers=_MCP_HEADERS or None) as http_client:
        async with streamable_http_client(_MCP_URL, http_client=http_client) as (read, write, _):
            yield (read, write)
'''

    def _build_tool_methods(self, tools_info: list[dict]) -> str:
        """根据发现的工具定义生成 Python 方法"""
        if not tools_info:
            return ""

        methods = []
        for tool in tools_info:
            tool_name = tool["name"]
            description = tool.get("description", "")
            schema = tool.get("inputSchema", {})

            # 从 schema 提取参数
            properties = schema.get("properties", {})
            required = schema.get("required", [])

            # 生成参数签名
            params = []
            for prop_name, prop_info in properties.items():
                param_type = prop_info.get("type", "any")
                type_hint = {
                    "string": "str",
                    "integer": "int",
                    "boolean": "bool",
                    "number": "float",
                    "object": "dict",
                    "array": "list",
                }.get(param_type, "")

                if prop_name in required:
                    params.append(
                        f"{prop_name}: {type_hint}" if type_hint else prop_name
                    )
                else:
                    default = prop_info.get("default", "None")
                    if isinstance(default, str) and default != "None":
                        default = f'"{default}"'
                    params.append(
                        f"{prop_name}: {type_hint} = {default}"
                        if type_hint
                        else f"{prop_name}={default}"
                    )

            params_str = ", ".join(params)

            # 生成 docstring
            docstring_parts = [description] if description else []
            if properties:
                docstring_parts.append("\nArgs:")
                for prop_name, prop_info in properties.items():
                    prop_desc = prop_info.get("description", "")
                    docstring_parts.append(f"    {prop_name}: {prop_desc}")

            docstring = "\n".join(docstring_parts)

            method = f'''
def {tool_name}({params_str}):
    """
    {docstring}
    """
    return _call_mcp("{tool_name}", {{k: v for k, v in locals().items() if v is not None}})
'''
            methods.append(method)

        return "\n".join(methods)

    # ==================== Internal Utils ====================

    def _validate_transport_args(
        self,
        transport: MCPTransport,
        *,
        command: Optional[str],
        url: Optional[str],
    ) -> None:
        """验证不同 transport 的参数完整性。"""
        match transport:
            case MCPTransport.STDIO:
                if not command:
                    raise ValueError("STDIO 模式需要提供 command 参数")
            case MCPTransport.HTTP:
                if not url:
                    raise ValueError("HTTP 模式需要提供 url 参数")
            case _:
                raise ValueError(f"不支持的 MCP transport: {transport.value}")
