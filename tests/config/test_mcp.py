"""
MCPHandler 集成测试

使用 tests/mcp/echo_server.py 作为真实 MCP 服务器进行测试。
"""

import sys
import json
import pytest
from pathlib import Path

from aep import EnvManager
from aep.core.config.handlers.mcp import MCPHandler, MCPTransport

# Echo server 路径
ECHO_SERVER = str(Path(__file__).parent.parent / "mcp" / "echo_server.py")


class TestMCPAddStdio:
    """测试 STDIO 模式添加 MCP 服务器"""

    @pytest.fixture
    def manager(self, tmp_path: Path) -> EnvManager:
        return EnvManager(tmp_path / "config")

    @pytest.fixture
    def handler(self, manager: EnvManager) -> MCPHandler:
        return manager.mcp

    def test_add_discovers_tools(self, handler: MCPHandler):
        """add 能发现 MCP 服务器暴露的工具"""
        stub = handler.add(
            "echo",
            command=sys.executable,
            args=[ECHO_SERVER],
        )

        assert stub.exists()
        assert stub.name == "echo.py"

        # 检查 manifest 中发现了工具
        manifest = handler.get_manifest("echo")
        assert manifest is not None
        tool_names = [t["name"] for t in manifest["tools"]]
        assert "echo" in tool_names
        assert "add" in tool_names

    def test_add_discovers_prompts(self, handler: MCPHandler):
        """add 能发现 MCP 服务器暴露的 prompts"""
        handler.add(
            "echo",
            command=sys.executable,
            args=[ECHO_SERVER],
        )

        manifest = handler.get_manifest("echo")
        assert manifest is not None
        prompt_names = [p["name"] for p in manifest["prompts"]]
        assert "greeting" in prompt_names

    def test_stub_contains_tool_functions(self, handler: MCPHandler):
        """生成的 stub 文件包含发现的工具函数"""
        stub = handler.add(
            "echo",
            command=sys.executable,
            args=[ECHO_SERVER],
        )

        content = stub.read_text(encoding="utf-8")

        # 应包含 echo 和 add 函数定义
        assert "def echo(" in content
        assert "def add(" in content
        # 应包含通用调用入口
        assert "def call(" in content
        # 应包含 MCP SDK 导入
        assert "from mcp import ClientSession" in content

    def test_stub_has_correct_params(self, handler: MCPHandler):
        """生成的 stub 函数有正确的参数签名"""
        stub = handler.add(
            "echo",
            command=sys.executable,
            args=[ECHO_SERVER],
        )

        content = stub.read_text(encoding="utf-8")

        # echo(message: str) 应有 message 参数
        assert "message" in content
        # add(a: int, b: int) 应有 a, b 参数
        assert "a: int" in content
        assert "b: int" in content

    def test_config_saved(self, handler: MCPHandler):
        """配置文件正确保存"""
        handler.add(
            "echo",
            command=sys.executable,
            args=[ECHO_SERVER],
        )

        config = handler.get_config("echo")
        assert config is not None
        assert config.transport == "stdio"
        assert config.command[0] == sys.executable
        assert ECHO_SERVER in config.command

    def test_prompt_docs_generated(self, handler: MCPHandler, manager: EnvManager):
        """MCP prompts 生成 SKILL.md 文档"""
        handler.add(
            "echo",
            command=sys.executable,
            args=[ECHO_SERVER],
        )

        skill_dir = manager.config.mcp_skill_dir("echo")
        skill_md = skill_dir / "SKILL.md"
        assert skill_md.exists()

        content = skill_md.read_text(encoding="utf-8")
        assert "greeting" in content
        assert "name" in content


class TestMCPList:
    """测试列出 MCP 服务器"""

    @pytest.fixture
    def handler(self, tmp_path: Path) -> MCPHandler:
        manager = EnvManager(tmp_path / "config")
        return manager.mcp

    def test_list_empty(self, handler: MCPHandler):
        """空列表"""
        assert handler.list() == []

    def test_list_after_add(self, handler: MCPHandler):
        """添加后能列出"""
        handler.add(
            "echo",
            command=sys.executable,
            args=[ECHO_SERVER],
        )

        servers = handler.list()
        assert "echo" in servers

    def test_list_multiple(self, handler: MCPHandler):
        """多个服务器"""
        handler.add(
            "echo1",
            command=sys.executable,
            args=[ECHO_SERVER],
        )
        handler.add(
            "echo2",
            command=sys.executable,
            args=[ECHO_SERVER],
        )

        servers = handler.list()
        assert "echo1" in servers
        assert "echo2" in servers


class TestMCPRemove:
    """测试删除 MCP 服务器"""

    @pytest.fixture
    def manager(self, tmp_path: Path) -> EnvManager:
        return EnvManager(tmp_path / "config")

    @pytest.fixture
    def handler(self, manager: EnvManager) -> MCPHandler:
        return manager.mcp

    def test_remove_cleans_stub(self, handler: MCPHandler, manager: EnvManager):
        """删除时清理 stub 文件"""
        handler.add(
            "echo",
            command=sys.executable,
            args=[ECHO_SERVER],
        )

        stub = manager.config.tool_path("echo")
        assert stub.exists()

        handler.remove("echo")
        assert not stub.exists()

    def test_remove_cleans_config(self, handler: MCPHandler, manager: EnvManager):
        """删除时清理配置目录"""
        handler.add(
            "echo",
            command=sys.executable,
            args=[ECHO_SERVER],
        )

        config_dir = manager.config.mcp_config_path("echo")
        assert config_dir.exists()

        handler.remove("echo")
        assert not config_dir.exists()

    def test_remove_cleans_skills(self, handler: MCPHandler, manager: EnvManager):
        """删除时清理 skill 文档"""
        handler.add(
            "echo",
            command=sys.executable,
            args=[ECHO_SERVER],
        )

        skill_dir = manager.config.mcp_skill_dir("echo")
        assert skill_dir.exists()

        handler.remove("echo")
        assert not skill_dir.exists()

    def test_remove_nonexistent(self, handler: MCPHandler):
        """删除不存在的服务器返回 False"""
        assert handler.remove("nonexistent") is False

    def test_remove_unlists(self, handler: MCPHandler):
        """删除后不再出现在列表中"""
        handler.add(
            "echo",
            command=sys.executable,
            args=[ECHO_SERVER],
        )
        assert "echo" in handler.list()

        handler.remove("echo")
        assert "echo" not in handler.list()


class TestMCPRefresh:
    """测试刷新 MCP 服务器"""

    @pytest.fixture
    def handler(self, tmp_path: Path) -> MCPHandler:
        manager = EnvManager(tmp_path / "config")
        return manager.mcp

    def test_refresh_updates_manifest(self, handler: MCPHandler):
        """刷新后 manifest 更新"""
        handler.add(
            "echo",
            command=sys.executable,
            args=[ECHO_SERVER],
        )

        # 刷新
        stub = handler.refresh("echo")
        assert stub.exists()

        manifest = handler.get_manifest("echo")
        assert manifest is not None
        tool_names = [t["name"] for t in manifest["tools"]]
        assert "echo" in tool_names

    def test_refresh_nonexistent_raises(self, handler: MCPHandler):
        """刷新不存在的服务器抛出异常"""
        with pytest.raises(FileNotFoundError):
            handler.refresh("nonexistent")


class TestMCPValidation:
    """测试参数验证"""

    @pytest.fixture
    def handler(self, tmp_path: Path) -> MCPHandler:
        manager = EnvManager(tmp_path / "config")
        return manager.mcp

    def test_stdio_requires_command(self, handler: MCPHandler):
        """STDIO 模式必须提供 command"""
        with pytest.raises(ValueError, match="command"):
            handler.add("test", transport=MCPTransport.STDIO)

    def test_http_requires_url(self, handler: MCPHandler):
        """HTTP 模式必须提供 url"""
        with pytest.raises(ValueError, match="url"):
            handler.add("test", transport=MCPTransport.HTTP)

    def test_command_not_found_raises(self, handler: MCPHandler):
        """找不到命令时抛出异常"""
        with pytest.raises(RuntimeError, match="未找到命令"):
            handler.add("test", command="nonexistent_cmd_xyz_12345")
