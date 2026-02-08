"""
AEP - Agent Environment Protocol

为 AI Agent 提供统一的能力发现和调用接口。

核心概念:
- EnvManager: 能力配置 (工具、技能、资料库)
- AEP: 主类，通过 attach() 将配置挂载到工作区
- AEPSession: 会话，通过 exec() 执行命令

Example:
    >>> from aep import EnvManager, AEP
    >>>
    >>> # 配置阶段
    >>> config = EnvManager("./capabilities")
    >>> config.add_tool("./tools/grep.py")
    >>> config.add_skill("./skills/web-scraper/")
    >>> config.add_library("./docs/api.md")
    >>> config.index()
    >>>
    >>> # 挂载阶段
    >>> aep = AEP.attach(workspace="./my_project", config=config)
    >>>
    >>> # 运行时
    >>> session = aep.create_session()
    >>> result = session.exec("tools list")
    >>> result = session.exec("tools run \"tools.grep.search('TODO', '.')\"")
    >>> result = session.exec("ls .agent/library/")
"""

from aep.core import AEP, EnvManager, AEPSession, ExecResult

__version__ = "0.1.0"
__all__ = ["AEP", "EnvManager", "AEPSession", "ExecResult"]
