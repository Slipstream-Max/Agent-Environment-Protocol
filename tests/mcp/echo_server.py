"""
Echo MCP Server - 用于测试的 MCP 服务器

暴露以下能力:
  Tools:
    - echo: 回显输入消息
    - add: 两数相加
  Prompts:
    - greeting: 生成问候语模板
"""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("echo-server")


# ==================== Tools ====================


@mcp.tool()
def echo(message: str) -> str:
    """Echo back the input message

    Args:
        message: The message to echo back
    """
    return f"Echo: {message}"


@mcp.tool()
def add(a: int, b: int) -> str:
    """Add two numbers together

    Args:
        a: First number
        b: Second number
    """
    return str(a + b)


# ==================== Prompts ====================


@mcp.prompt()
def greeting(name: str) -> str:
    """Generate a greeting prompt for the given name

    Args:
        name: The name of the person to greet
    """
    return f"Please greet {name} warmly and make them feel welcome."


if __name__ == "__main__":
    mcp.run()
