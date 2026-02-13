"""
AEPSession - 会话管理

管理 Agent 与环境的交互会话，维护状态（cwd, env）。
执行逻辑委托给专门的 Executor 组件。
"""

import os
import shlex
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

from aep.core.executor import ExecResult, SkillExecutor, ToolExecutor

if TYPE_CHECKING:
    from aep.core.config import EnvManager


class AEPSession:
    """
    AEP 会话

    管理 Agent 与环境的交互，维护会话状态。
    exec() 是唯一对外接口，执行逻辑委托给 Executor 组件。

    职责:
    - 命令解析与路由
    - 会话状态管理 (cwd, env)
    - 上下文获取

    注意:
    - MCP 服务器在配置阶段通过 add_mcp_server() 自动转换为 tool stub
    - Agent 通过 `tools run "tools.<mcp_name>.<method>(...)"` 统一调用
    """

    def __init__(self, workspace: Path, config: "EnvManager"):
        """
        初始化会话

        Args:
            workspace: 工作区目录
            config: 能力配置
        """
        self.workspace = workspace
        self.config = config
        self.cwd = workspace  # 当前工作目录
        self.env: dict[str, str] = {}  # 自定义环境变量

        # 初始化执行器
        self.tool_executor = ToolExecutor(config)
        self.skill_executor = SkillExecutor(config)

        logger.debug(f"Session 创建: workspace={workspace}")

    def exec(self, command: str) -> ExecResult:
        """
        执行命令 (唯一对外接口)

        根据命令前缀路由到不同处理器：
        - tools ... -> _handle_tools()
        - skills ... -> _handle_skills()
        - cd -> _handle_cd()
        - export -> _handle_export()
        - 其他 -> _shell_passthrough()

        Args:
            command: 要执行的命令

        Returns:
            ExecResult 包含 stdout, stderr, return_code
        """
        command = command.strip()
        if not command:
            return ExecResult()

        logger.debug(f"exec: {command}")

        # 特殊处理: tools run "..." 支持多行代码
        # shlex.split 会把换行符当作分隔符，导致多行代码被错误拆分
        if command.startswith("tools run "):
            return self._handle_tools_run(command[10:])  # 跳过 "tools run "

        try:
            parts = shlex.split(command)
        except ValueError as e:
            return ExecResult(stderr=f"命令解析错误: {e}", return_code=1)

        if not parts:
            return ExecResult()

        cmd = parts[0]
        args = parts[1:]

        # 命令路由
        if cmd == "tools":
            return self._handle_tools(args)
        elif cmd == "skills":
            return self._handle_skills(args)
        elif cmd == "cd":
            return self._handle_cd(args)
        elif cmd == "export":
            return self._handle_export(args)
        else:
            return self._shell_passthrough(command)

    # ==================== Tools ====================

    def _handle_tools(self, args: list[str]) -> ExecResult:
        """处理 tools 命令"""
        if not args:
            return ExecResult(
                stderr="Usage: tools <list|info|run> [args]\n"
                "  tools list             - 列出所有工具\n"
                "  tools info <name>      - 查看工具详情\n"
                '  tools run "<code>"     - 执行 Python 代码',
                return_code=1,
            )

        subcmd = args[0]

        if subcmd == "list":
            index_file = self.config.tools_dir / "index.md"
            if index_file.exists():
                return ExecResult(stdout=index_file.read_text(encoding="utf-8"))
            return ExecResult(stdout="_暂无工具_\n")

        elif subcmd == "info":
            if len(args) < 2:
                return ExecResult(stderr="Usage: tools info <name>", return_code=1)
            name = args[1]
            return self._tools_info(name)

        elif subcmd == "run":
            if len(args) < 2:
                return ExecResult(
                    stderr='Usage: tools run "<python_code>"', return_code=1
                )
            code = args[1]
            return self.tool_executor.run(
                code=code,
                cwd=self.cwd,
                workspace=self.workspace,
            )

        else:
            return ExecResult(stderr=f"未知子命令: {subcmd}", return_code=1)

    def _handle_tools_run(self, code_arg: str) -> ExecResult:
        """
        处理 tools run 命令（支持多行代码）

        支持的格式:
        - tools run "code"
        - tools run 'code'
        - tools run \"\"\"multiline code\"\"\"
        - tools run '''multiline code'''

        Args:
            code_arg: "tools run " 之后的部分
        """
        code_arg = code_arg.strip()

        if not code_arg:
            return ExecResult(stderr='Usage: tools run "<python_code>"', return_code=1)

        # 提取代码内容（去除引号包裹）
        code = self._extract_quoted_code(code_arg)

        if code is None:
            return ExecResult(
                stderr="代码必须用引号包裹: tools run \"code\" 或 tools run '''code'''",
                return_code=1,
            )

        return self.tool_executor.run(
            code=code,
            cwd=self.cwd,
            workspace=self.workspace,
        )

    def _extract_quoted_code(self, s: str) -> str | None:
        """
        从引号包裹的字符串中提取代码

        支持:
        - "..." 双引号
        - '...' 单引号
        - \"\"\"...\"\"\" 三双引号
        - '''...''' 三单引号

        Returns:
            提取的代码，如果格式不正确则返回 None
        """
        # 三引号优先
        if s.startswith('"""') and s.endswith('"""') and len(s) >= 6:
            return s[3:-3]
        if s.startswith("'''") and s.endswith("'''") and len(s) >= 6:
            return s[3:-3]

        # 单/双引号
        if s.startswith('"') and s.endswith('"') and len(s) >= 2:
            return s[1:-1]
        if s.startswith("'") and s.endswith("'") and len(s) >= 2:
            return s[1:-1]

        return None

    def _tools_info(self, name: str) -> ExecResult:
        """获取工具详情"""
        # 查找 .md 文档
        doc_file = self.config.tools_dir / f"{name}.md"
        if doc_file.exists():
            return ExecResult(stdout=doc_file.read_text(encoding="utf-8"))

        # 没有文档，尝试读取 py 文件的 docstring
        py_file = self.config.tools_dir / f"{name}.py"
        if py_file.exists():
            content = py_file.read_text(encoding="utf-8")
            # 简单提取顶层 docstring
            if content.startswith('"""'):
                end = content.find('"""', 3)
                if end > 0:
                    return ExecResult(stdout=content[3:end].strip())
            return ExecResult(stdout=f"工具 {name} 存在，但无文档。")

        return ExecResult(stderr=f"工具不存在: {name}", return_code=1)

    # ==================== Skills ====================

    def _handle_skills(self, args: list[str]) -> ExecResult:
        """处理 skills 命令"""
        if not args:
            return ExecResult(
                stderr="Usage: skills <list|info|run> [args]\n"
                "  skills list                  - 列出所有技能\n"
                "  skills info <name>           - 查看技能详情\n"
                "  skills run <path.py> [args]  - 执行技能脚本",
                return_code=1,
            )

        subcmd = args[0]

        if subcmd == "list":
            index_file = self.config.skills_dir / "index.md"
            if index_file.exists():
                return ExecResult(stdout=index_file.read_text(encoding="utf-8"))
            return ExecResult(stdout="_暂无技能_\n")

        elif subcmd == "info":
            if len(args) < 2:
                return ExecResult(stderr="Usage: skills info <name>", return_code=1)
            name = args[1]
            return self._skills_info(name)

        elif subcmd == "run":
            if len(args) < 2:
                return ExecResult(
                    stderr="Usage: skills run <path.py> [args]", return_code=1
                )
            script_path = args[1]
            script_args = args[2:]
            return self.skill_executor.run(script_path, script_args)

        else:
            return ExecResult(stderr=f"未知子命令: {subcmd}", return_code=1)

    def _skills_info(self, name: str) -> ExecResult:
        """获取技能详情"""
        skill_dir = self.config.skills_dir / name
        if not skill_dir.is_dir():
            return ExecResult(stderr=f"技能不存在: {name}", return_code=1)

        # 查找 SKILL.md 或 README.md
        for doc_name in ["SKILL.md", "README.md"]:
            doc_file = skill_dir / doc_name
            if doc_file.exists():
                return ExecResult(stdout=doc_file.read_text(encoding="utf-8"))

        return ExecResult(stdout=f"技能 {name} 存在，但无文档。")

    # ==================== 内置命令 ====================

    def _handle_cd(self, args: list[str]) -> ExecResult:
        """处理 cd 命令"""
        if not args:
            # cd 无参数，回到 workspace
            self.cwd = self.workspace
            return ExecResult(stdout=str(self.cwd))

        target = args[0]

        if target.startswith("/") or (len(target) > 1 and target[1] == ":"):
            # 绝对路径
            new_path = Path(target)
        else:
            # 相对路径
            new_path = self.cwd / target

        new_path = new_path.resolve()

        if not new_path.exists():
            return ExecResult(stderr=f"目录不存在: {new_path}", return_code=1)
        if not new_path.is_dir():
            return ExecResult(stderr=f"不是目录: {new_path}", return_code=1)

        self.cwd = new_path
        return ExecResult(stdout=str(self.cwd))

    def _handle_export(self, args: list[str]) -> ExecResult:
        """处理 export 命令"""
        if not args:
            # 列出当前环境变量
            output = "\n".join(f"{k}={v}" for k, v in self.env.items())
            return ExecResult(stdout=output or "(无自定义环境变量)")

        for arg in args:
            if "=" in arg:
                key, value = arg.split("=", 1)
                self.env[key] = value
            else:
                return ExecResult(
                    stderr=f"无效格式: {arg}，应为 KEY=VALUE", return_code=1
                )

        return ExecResult()

    # ==================== Shell 透传 ====================

    def _shell_passthrough(self, command: str) -> ExecResult:
        """透传给系统 shell"""
        env = {**os.environ, **self.env}

        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=str(self.cwd),
                env=env,
                capture_output=True,
                text=True,
                timeout=60,
            )
            return ExecResult(
                stdout=result.stdout,
                stderr=result.stderr,
                return_code=result.returncode,
            )
        except subprocess.TimeoutExpired:
            return ExecResult(stderr="执行超时 (60s)", return_code=124)
        except Exception as e:
            return ExecResult(stderr=f"执行错误: {e}", return_code=1)

    # ==================== 上下文 ====================

    def get_context(self) -> str:
        """
        获取 L0 上下文 (注入 System Prompt)

        Returns:
            包含可用能力概览的字符串
        """
        parts = []

        # 工具索引 (包含 MCP 工具)
        tools_index = self.config.tools_dir / "index.md"
        if tools_index.exists():
            parts.append(tools_index.read_text(encoding="utf-8"))

        # 技能索引
        skills_index = self.config.skills_dir / "index.md"
        if skills_index.exists():
            parts.append(skills_index.read_text(encoding="utf-8"))

        # 资料索引
        library_index = self.config.library_dir / "index.md"
        if library_index.exists():
            parts.append(library_index.read_text(encoding="utf-8"))

        return "\n\n".join(parts)
