"""
AEP - Agent Environment Protocol 主类

提供 attach() 方法将配置挂载到工作区。
"""

from pathlib import Path
from typing import Optional

from loguru import logger

from aep.core.config import EnvManager
from aep.core.session import AEPSession


class AEP:
    """
    Agent Environment Protocol 主类

    使用 attach() 将配置挂载到工作区，然后 create_session() 创建会话。

    Example:
        >>> config = EnvManager("./capabilities")
        >>> config.add_tool("./tools/grep.py")
        >>> config.index()
        >>>
        >>> aep = AEP.attach(workspace="./my_project", config=config)
        >>> session = aep.create_session()
        >>> result = session.exec("tools list")
    """

    def __init__(
        self, workspace: Optional[str | Path] = None, agent_dir: str = ".agents"
    ):
        self.workspace: Optional[Path] = (
            Path(workspace).resolve() if workspace else None
        )
        self.agent_dir_name = agent_dir
        self.agent_dir: Optional[Path] = (
            self.workspace / agent_dir if self.workspace else None
        )
        self.config: Optional[EnvManager] = None

    @classmethod
    def attach(
        cls,
        workspace: str | Path,
        config: EnvManager | str | Path,
        agent_dir: str = ".agents",
    ) -> "AEP":
        """
        将配置挂载到工作区

        在工作区创建协议目录（默认 .agents/），内部使用符号链接指向配置目录。

        Args:
            workspace: 工作区目录路径
            config: EnvManager 实例或配置目录路径
            agent_dir: 协议目录名称，默认为 ".agents"

        Returns:
            AEP 实例
        """
        instance = cls(workspace, agent_dir)

        # 处理config
        if isinstance(config, (str, Path)):
            config = EnvManager(config)
        instance.config = config

        # 创建 agent_dir
        if instance.agent_dir.exists():
            logger.info(f"{instance.agent_dir_name}/ 目录已存在，将尝试更新链接")
        else:
            instance.agent_dir.mkdir(parents=True)

        # 创建链接
        instance._create_symlinks()

        logger.info(f"AEP 挂载完成: {instance.workspace} <- {config.config_dir}")
        return instance

    def _create_symlinks(self) -> None:
        """创建链接"""
        if self.config is None or self.agent_dir is None:
            return

        links = [
            ("tools", self.config.tools_dir),
            ("skills", self.config.skills_dir),
            ("library", self.config.library_dir),
        ]

        for name, target in links:
            link = self.agent_dir / name

            # 如果存在且不是符号链接，直接报错保护用户目录
            if link.exists() and not link.is_symlink():
                raise RuntimeError(
                    f"协议目录冲突: {link} 已存在且不是符号链接，请手动处理"
                )

            # 如果链接已存在，先删除
            if link.is_symlink():
                try:
                    link.unlink()
                except OSError as e:
                    logger.warning(f"删除旧链接失败: {link}, {e}")

            # 创建链接
            try:
                link.symlink_to(target, target_is_directory=True)
                logger.debug(f"创建链接: {link} -> {target}")
            except OSError as e:
                logger.error(f"创建链接失败: {e}")
                raise

    def create_session(self) -> AEPSession:
        """
        创建会话

        Returns:
            AEPSession 实例
        """
        if self.workspace is None or self.config is None:
            raise RuntimeError("AEP 未正确初始化，请使用 AEP.attach() 创建实例")

        return AEPSession(self.workspace, self.config)

    def detach(self) -> None:
        """
        解除挂载

        删除协议目录下的符号链接
        """
        if self.workspace is None or self.agent_dir is None:
            return

        if not self.agent_dir.exists():
            return

        for name in ["tools", "skills", "library"]:
            link = self.agent_dir / name
            if link.is_symlink():
                link.unlink()
                logger.debug(f"删除符号链接: {link}")

        # 如果 agent_dir 为流浪(不再有链接或文件)，删除它
        try:
            if self.agent_dir.exists() and not any(self.agent_dir.iterdir()):
                self.agent_dir.rmdir()
                logger.debug(f"删除空的协议目录: {self.agent_dir}")
        except OSError as e:
            logger.warning(f"无法删除协议目录: {e}")

        logger.info(f"AEP 已解除挂载: {self.workspace}")

    def __repr__(self) -> str:
        return f"AEP(workspace={self.workspace}, agent_dir={self.agent_dir_name}, config={self.config})"
