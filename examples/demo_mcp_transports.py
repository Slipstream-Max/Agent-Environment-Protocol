"""
AEP MCP 传输方式演示

演示内容:
1. 通过 STDIO 添加并调用 MCP server
2. 通过 Streamable HTTP 添加并调用 MCP server（可选）
3. 在一个 tools run 的 Python 代码块中完成调用

用法:
    python examples/demo_mcp_transports.py
    python examples/demo_mcp_transports.py --streamable-url http://localhost:8000/mcp
"""

from __future__ import annotations

import argparse
import os
import socket
import subprocess
import sys
import tempfile
import textwrap
import time
from contextlib import contextmanager
from pathlib import Path

from aep import AEP, EnvManager
from aep.core.config.handlers.mcp import MCPTransport

ECHO_SERVER = Path(__file__).resolve().parents[1] / "tests" / "mcp" / "echo_server.py"


def build_tools_run_code() -> str:
    """构建单段 Python 代码，用于 tools run"""
    return """
print("=== STDIO MCP ===")
print("echo_stdio.echo =>", tools.echo_stdio.echo(message="hello from stdio"))
print("echo_stdio.add  =>", tools.echo_stdio.add(a=2, b=3))

print("=== Streamable HTTP MCP ===")
if hasattr(tools, "echo_http"):
    print("echo_http.echo  =>", tools.echo_http.echo(message="hello from streamable http"))
    print("echo_http.add   =>", tools.echo_http.add(a=10, b=20))
else:
    print("echo_http not configured, skip streamable demo")
""".strip()


def find_free_port() -> int:
    """获取一个可用本地端口"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def write_streamable_server_script(script_path: Path, port: int) -> None:
    """写入一个最小 Streamable HTTP MCP server 脚本"""
    script = textwrap.dedent(
        f"""
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP("echo-http-server", host="127.0.0.1", port={port}, streamable_http_path="/mcp")

        @mcp.tool()
        def echo(message: str) -> str:
            return f"Echo: {{message}}"

        @mcp.tool()
        def add(a: int, b: int) -> str:
            return str(a + b)

        if __name__ == "__main__":
            mcp.run(transport="streamable-http")
        """
    ).strip()
    script_path.write_text(script, encoding="utf-8")


@contextmanager
def run_streamable_server(script_path: Path, port: int) -> str:
    """启动 Streamable HTTP MCP server 子进程并返回 URL"""
    proc = subprocess.Popen([sys.executable, str(script_path)])
    try:
        # URL 已知，服务是否就绪由 add_mcp_server 重试保证
        url = f"http://127.0.0.1:{port}/mcp"
        yield url
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()


def add_streamable_server_with_retry(config: EnvManager, name: str, url: str) -> None:
    """等待服务就绪后添加 Streamable HTTP MCP server"""
    last_error: Exception | None = None
    for _ in range(20):
        try:
            config.add_mcp_server(
                name,
                transport=MCPTransport.HTTP,
                url=url,
            )
            return
        except Exception as exc:
            last_error = exc
            time.sleep(0.3)

    raise RuntimeError(
        f"streamable MCP 添加失败: {last_error}"
    )


def ensure_local_no_proxy() -> None:
    """确保本地回环地址不走系统代理。"""
    no_proxy_hosts = ["127.0.0.1", "localhost"]
    existing = os.environ.get("NO_PROXY", "").strip()
    merged = [h for h in existing.split(",") if h] + no_proxy_hosts
    os.environ["NO_PROXY"] = ",".join(dict.fromkeys(merged))
    os.environ["no_proxy"] = os.environ["NO_PROXY"]


def main() -> None:
    parser = argparse.ArgumentParser()
    _ = parser.parse_args()

    with tempfile.TemporaryDirectory() as tmpdir:
        ensure_local_no_proxy()
        tmpdir_path = Path(tmpdir)
        config_dir = tmpdir_path / "config"
        workspace = tmpdir_path / "workspace"
        workspace.mkdir()

        config = EnvManager(config_dir)

        # 1) STDIO MCP
        config.add_mcp_server(
            "echo_stdio",
            transport=MCPTransport.STDIO,
            command=sys.executable,
            args=[str(ECHO_SERVER)],
        )

        # 2) Streamable HTTP MCP（脚本内自动起子进程）
        port = find_free_port()
        server_script = tmpdir_path / f"echo_http_server_{port}.py"
        write_streamable_server_script(server_script, port)

        with run_streamable_server(server_script, port) as streamable_url:
            add_streamable_server_with_retry(config, "echo_http", streamable_url)

            # MCP stub 在 tools/.venv 中运行，需要可导入 mcp 包
            config.add_tool_dependency("mcp")

            config.index()

            aep = AEP.attach(workspace=workspace, config=config)
            session = aep.create_session()

            # 在一个 tools run 代码块中同时演示 stdio + streamable
            code = build_tools_run_code()
            command = f"tools run '''{code}'''"
            result = session.exec(command)

            print(">>> streamable_url")
            print(streamable_url)
            print("\n>>> command")
            print(command)
            print("\n>>> stdout")
            print(result.stdout)
            if result.stderr:
                print("\n>>> stderr")
                print(result.stderr)


if __name__ == "__main__":
    main()
