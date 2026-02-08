"""
AEP 主类测试
"""

import pytest
from pathlib import Path

from aep import AEP, EnvManager


class TestAEPAttach:
    """测试 AEP.attach 方法"""

    @pytest.fixture
    def config(self, tmp_path: Path) -> EnvManager:
        """创建测试配置"""
        config = EnvManager(tmp_path / "config")

        # 添加一个工具
        tool = tmp_path / "calc.py"
        tool.write_text('"""calc"""\ndef add(a, b): return a + b')
        config.add_tool(tool)
        config.index()

        return config

    @pytest.fixture
    def workspace(self, tmp_path: Path) -> Path:
        """创建工作区"""
        ws = tmp_path / "workspace"
        ws.mkdir()
        return ws

    def test_attach_creates_agent_dir(self, workspace: Path, config: EnvManager):
        """attach 创建 .agent 目录"""
        aep = AEP.attach(workspace=workspace, config=config)

        agent_dir = workspace / ".agent"
        assert agent_dir.exists()

    def test_attach_creates_symlinks(self, workspace: Path, config: EnvManager):
        """attach 创建符号链接"""
        aep = AEP.attach(workspace=workspace, config=config)

        agent_dir = workspace / ".agent"

        # 检查链接存在
        assert (agent_dir / "tools").exists()
        assert (agent_dir / "skills").exists()
        assert (agent_dir / "library").exists()

    def test_attach_symlinks_point_to_config(self, workspace: Path, config: EnvManager):
        """符号链接指向配置目录"""
        aep = AEP.attach(workspace=workspace, config=config)

        tools_link = workspace / ".agent" / "tools"
        # 链接指向的目录应该包含工具文件
        assert (tools_link / "calc.py").exists()

    def test_attach_with_path_string(self, workspace: Path, config: EnvManager):
        """支持字符串路径"""
        aep = AEP.attach(workspace=str(workspace), config=config)

        assert aep.workspace == workspace.resolve()

    def test_attach_with_config_path(self, workspace: Path, tmp_path: Path):
        """支持配置目录路径"""
        # 先创建配置
        config = EnvManager(tmp_path / "config")
        config.index()

        # 用路径字符串 attach
        aep = AEP.attach(workspace=workspace, config=str(tmp_path / "config"))

        assert aep.config is not None


class TestAEPCreateSession:
    """测试 create_session 方法"""

    @pytest.fixture
    def aep(self, tmp_path: Path) -> AEP:
        """创建 AEP 实例"""
        config = EnvManager(tmp_path / "config")
        config.index()

        workspace = tmp_path / "workspace"
        workspace.mkdir()

        return AEP.attach(workspace=workspace, config=config)

    def test_create_session_returns_session(self, aep: AEP):
        """create_session 返回 AEPSession"""
        from aep import AEPSession

        session = aep.create_session()

        assert isinstance(session, AEPSession)

    def test_session_has_workspace(self, aep: AEP):
        """session 有正确的 workspace"""
        session = aep.create_session()

        assert session.workspace == aep.workspace

    def test_session_has_config(self, aep: AEP):
        """session 有正确的 config"""
        session = aep.create_session()

        assert session.config == aep.config


class TestAEPDetach:
    """测试 detach 方法"""

    @pytest.fixture
    def attached_aep(self, tmp_path: Path) -> AEP:
        """创建已 attach 的 AEP"""
        config = EnvManager(tmp_path / "config")
        config.index()

        workspace = tmp_path / "workspace"
        workspace.mkdir()

        return AEP.attach(workspace=workspace, config=config)

    def test_detach_removes_symlinks(self, attached_aep: AEP):
        """detach 移除符号链接"""
        workspace = attached_aep.workspace
        assert workspace is not None

        attached_aep.detach()

        agent_dir = workspace / ".agent"
        # 符号链接应该被移除
        assert not (agent_dir / "tools").exists()
        assert not (agent_dir / "skills").exists()
        assert not (agent_dir / "library").exists()
