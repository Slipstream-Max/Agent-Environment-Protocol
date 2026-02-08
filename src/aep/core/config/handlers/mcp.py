"""
MCPHandler - MCP 服务器管理处理器

负责 MCP 服务器的添加、配置和 stub 生成。
"""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
from typing import Optional

from loguru import logger

from ..envconfig import EnvConfig, MCPServerConfig
from .base import BaseHandler


class MCPTransport(Enum):
    """MCP 传输方式"""

    STDIO = "stdio"  # 标准输入输出（本地进程，默认）
    HTTP = "http"  # Streamable HTTP（Web 服务）


class MCPHandler(BaseHandler):
    """MCP 服务器管理处理器"""

    def __init__(self, config: EnvConfig):
        self.config = config

    def add(
        self,
        name: str,
        *,
        # STDIO 模式参数
        command: Optional[list[str]] = None,
        env: Optional[dict[str, str]] = None,
        # HTTP 模式参数
        url: Optional[str] = None,
        headers: Optional[dict[str, str]] = None,
        # 通用参数
        transport: MCPTransport = MCPTransport.STDIO,
        tools: Optional[list[dict]] = None,
        dependencies: Optional[list[str]] = None,
    ) -> Path:
        """
        添加 MCP 服务器并生成工具 stub

        Args:
            name: 服务器名称（将作为工具模块名）
            command: STDIO 模式启动命令
            env: STDIO 模式额外环境变量
            url: HTTP 模式服务 URL
            headers: HTTP 模式请求头
            transport: 传输方式，默认 STDIO
            tools: MCP 工具定义列表
            dependencies: 可选依赖列表

        Returns:
            生成的工具文件路径
        """
        # 验证参数
        if transport == MCPTransport.STDIO:
            if not command:
                raise ValueError("STDIO 模式需要提供 command 参数")
        elif transport == MCPTransport.HTTP:
            if not url:
                raise ValueError("HTTP 模式需要提供 url 参数")

        # 保存 MCP 服务器配置
        mcp_config = MCPServerConfig(
            name=name,
            transport=transport.value,
            command=command,
            env=env or {},
            url=url,
            headers=headers or {},
            tools=tools or [],
        )

        self.config.mcp_config_dir.mkdir(exist_ok=True)
        config_file = self.config.mcp_config_path(name)
        config_file.write_text(
            json.dumps(mcp_config.to_dict(), indent=2), encoding="utf-8"
        )

        # 生成 Python stub
        if transport == MCPTransport.STDIO:
            stub_file = self._generate_stdio_stub(name, command, env, tools)
        else:
            stub_file = self._generate_http_stub(name, url, headers, tools)

        # 处理依赖
        if dependencies:
            from .tools import ToolsHandler

            tools_handler = ToolsHandler(self.config)
            tools_handler.save_requirements(
                self.config.tools_requirements, dependencies
            )

        # 确保 venv 并安装依赖
        self.ensure_venv(self.config.tools_venv_dir)
        if dependencies:
            self.install_dependencies(
                self.config.tools_venv_dir,
                dependencies,
                self.config.tools_dir,
            )

        logger.info(f"添加 MCP 服务器 ({transport.value}): {name} -> tools/{name}.py")
        return stub_file

    def list(self) -> list[str]:
        """列出所有 MCP 服务器名称"""
        if not self.config.mcp_config_dir.exists():
            return []
        return [f.stem for f in self.config.mcp_config_dir.glob("*.json")]

    def get_config(self, name: str) -> Optional[MCPServerConfig]:
        """获取 MCP 服务器配置"""
        config_file = self.config.mcp_config_path(name)
        if not config_file.exists():
            return None
        data = json.loads(config_file.read_text(encoding="utf-8"))
        return MCPServerConfig.from_dict(data)

    def remove(self, name: str) -> bool:
        """删除 MCP 服务器"""
        config_file = self.config.mcp_config_path(name)
        stub_file = self.config.tool_path(name)

        removed = False
        if config_file.exists():
            config_file.unlink()
            removed = True
        if stub_file.exists():
            stub_file.unlink()
            removed = True

        if removed:
            logger.info(f"删除 MCP 服务器: {name}")
        return removed

    def _generate_stdio_stub(
        self,
        name: str,
        command: list[str],
        env: Optional[dict[str, str]],
        tools: Optional[list[dict]],
    ) -> Path:
        """生成 STDIO 模式的 MCP stub 文件"""
        command_str = json.dumps(command)
        env_str = json.dumps(env or {})

        # 生成方法
        if tools:
            methods = self._generate_tool_methods(tools)
            docstring = f'"""\nMCP Server (STDIO): {name}\n\n可用工具:\n'
            for t in tools:
                docstring += f"  - {t['name']}: {t.get('description', '')}\n"
            docstring += '"""'
        else:
            methods = '''
def call(tool_name: str, **kwargs):
    """
    调用 MCP 工具
    
    Args:
        tool_name: 工具名称
        **kwargs: 工具参数
    
    Returns:
        工具返回结果
    """
    return _call_mcp(tool_name, kwargs)
'''
            docstring = f'"""\nMCP Server (STDIO): {name}\n\n使用 call(tool_name, **kwargs) 调用 MCP 工具\n"""'

        stub_content = f'''{docstring}

import json
import subprocess
import os

# MCP 服务器配置 (STDIO)
_MCP_TRANSPORT = "stdio"
_MCP_COMMAND = {command_str}
_MCP_ENV = {env_str}


def _call_mcp(tool_name: str, arguments: dict):
    """内部函数：通过 STDIO 调用 MCP 服务器"""
    request = {{
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {{
            "name": tool_name,
            "arguments": arguments,
        }},
    }}
    
    env = {{**os.environ, **_MCP_ENV}}
    
    try:
        init_request = {{"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {{"protocolVersion": "2024-11-05", "capabilities": {{}}, "clientInfo": {{"name": "aep", "version": "0.1.0"}}}}}}
        
        process = subprocess.Popen(
            _MCP_COMMAND,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True,
        )
        
        # 发送初始化
        process.stdin.write(json.dumps(init_request) + "\\n")
        process.stdin.flush()
        init_response = process.stdout.readline()
        
        # 发送工具调用
        process.stdin.write(json.dumps(request) + "\\n")
        process.stdin.flush()
        response_line = process.stdout.readline()
        process.terminate()
        
        if response_line:
            response = json.loads(response_line)
            if "result" in response:
                return response["result"]
            elif "error" in response:
                raise RuntimeError(f"MCP Error: {{response['error']}}")
        
        return None
        
    except FileNotFoundError:
        raise RuntimeError(f"MCP 命令未找到: {{_MCP_COMMAND[0]}}")
    except Exception as e:
        raise RuntimeError(f"MCP 调用失败: {{e}}")

{methods}
'''

        stub_file = self.config.tool_path(name)
        stub_file.write_text(stub_content, encoding="utf-8")
        return stub_file

    def _generate_http_stub(
        self,
        name: str,
        url: str,
        headers: Optional[dict[str, str]],
        tools: Optional[list[dict]],
    ) -> Path:
        """生成 HTTP 模式的 MCP stub 文件"""
        headers_str = json.dumps(headers or {})

        # 生成方法
        if tools:
            methods = self._generate_tool_methods(tools)
            docstring = f'"""\nMCP Server (HTTP): {name}\nURL: {url}\n\n可用工具:\n'
            for t in tools:
                docstring += f"  - {t['name']}: {t.get('description', '')}\n"
            docstring += '"""'
        else:
            methods = '''
def call(tool_name: str, **kwargs):
    """
    调用 MCP 工具
    
    Args:
        tool_name: 工具名称
        **kwargs: 工具参数
    
    Returns:
        工具返回结果
    """
    return _call_mcp(tool_name, kwargs)
'''
            docstring = f'"""\nMCP Server (HTTP): {name}\nURL: {url}\n\n使用 call(tool_name, **kwargs) 调用 MCP 工具\n"""'

        stub_content = f'''{docstring}

import json

try:
    import httpx
except ImportError:
    raise ImportError("HTTP 模式需要 httpx 库，请运行: tools install httpx")

# MCP 服务器配置 (HTTP)
_MCP_TRANSPORT = "http"
_MCP_URL = "{url}"
_MCP_HEADERS = {headers_str}

# 会话状态
_session_id = None


def _call_mcp(tool_name: str, arguments: dict):
    """内部函数：通过 Streamable HTTP 调用 MCP 服务器"""
    global _session_id
    
    # 如果没有会话，先初始化
    if _session_id is None:
        _initialize()
    
    request = {{
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {{
            "name": tool_name,
            "arguments": arguments,
        }},
    }}
    
    headers = {{
        **_MCP_HEADERS,
        "Content-Type": "application/json",
        "Mcp-Session-Id": _session_id,
    }}
    
    try:
        with httpx.Client() as client:
            response = client.post(
                _MCP_URL,
                json=request,
                headers=headers,
                timeout=60.0,
            )
            response.raise_for_status()
            
            result = response.json()
            if "result" in result:
                return result["result"]
            elif "error" in result:
                raise RuntimeError(f"MCP Error: {{result['error']}}")
            
            return None
            
    except httpx.HTTPError as e:
        raise RuntimeError(f"HTTP 请求失败: {{e}}")
    except Exception as e:
        raise RuntimeError(f"MCP 调用失败: {{e}}")


def _initialize():
    """初始化 MCP 会话"""
    global _session_id
    
    init_request = {{
        "jsonrpc": "2.0",
        "id": 0,
        "method": "initialize",
        "params": {{
            "protocolVersion": "2024-11-05",
            "capabilities": {{}},
            "clientInfo": {{"name": "aep", "version": "0.1.0"}},
        }},
    }}
    
    headers = {{
        **_MCP_HEADERS,
        "Content-Type": "application/json",
    }}
    
    try:
        with httpx.Client() as client:
            response = client.post(
                _MCP_URL,
                json=init_request,
                headers=headers,
                timeout=30.0,
            )
            response.raise_for_status()
            
            # 从响应头获取会话 ID
            _session_id = response.headers.get("Mcp-Session-Id", "default")
            
            result = response.json()
            if "error" in result:
                raise RuntimeError(f"MCP 初始化失败: {{result['error']}}")
                
    except Exception as e:
        raise RuntimeError(f"MCP 初始化失败: {{e}}")

{methods}
'''

        stub_file = self.config.tool_path(name)
        stub_file.write_text(stub_content, encoding="utf-8")
        return stub_file

    def _generate_tool_methods(self, tools: list[dict]) -> str:
        """根据 MCP 工具定义生成 Python 方法"""
        methods = []
        for tool in tools:
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
                    if isinstance(default, str):
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
