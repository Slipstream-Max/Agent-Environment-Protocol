"""
AEP Executors - 独立的代码执行器

使用 uv 管理虚拟环境，提供更快速的依赖安装体验。

ToolExecutor: 在共享的虚拟环境中执行 Python 工具代码
SkillExecutor: 在技能专属的虚拟环境中执行脚本

注意: MCP 服务器通过 config.add_mcp_server() 自动转换为 tools
"""

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from loguru import logger

if TYPE_CHECKING:
    from aep.core.config import EnvManager


@dataclass
class ExecResult:
    """命令执行结果"""

    stdout: str = ""
    stderr: str = ""
    return_code: int = 0


def _find_uv() -> str:
    """查找 uv 可执行文件"""
    # 尝试直接调用
    if shutil.which("uv"):
        return "uv"
    # Windows: 可能在 Python Scripts 目录
    # 如果找不到，返回 uv 让系统报错
    return "uv"


def _get_python(venv_dir: Path) -> Path:
    """获取 venv 中的 Python 路径"""
    # Windows
    python = venv_dir / "Scripts" / "python.exe"
    if python.exists():
        return python
    # Linux/Mac
    python = venv_dir / "bin" / "python"
    if python.exists():
        return python
    raise RuntimeError(f"未找到 venv Python: {venv_dir}")


class ToolExecutor:
    """
    工具执行器

    所有工具共享一个虚拟环境，使用 uv 管理依赖。
    工具代码可以访问 tools 命名空间下的所有工具模块。

    目录结构:
        tools/
        ├── .venv/             # 共享的虚拟环境 (uv 风格)
        ├── requirements.txt   # 依赖清单
        ├── grep.py            # 工具模块
        └── file_edit.py
    """

    def __init__(self, config: "EnvManager"):
        self.config = config
        self.tools_dir = config.tools_dir
        self.venv_dir = self.tools_dir / ".venv"
        self._uv = _find_uv()

    def ensure_venv(self) -> Path:
        """确保虚拟环境存在，返回 Python 路径"""
        if not self.venv_dir.exists():
            raise RuntimeError("tools venv 不存在，请在配置阶段创建 (.venv)")

        return _get_python(self.venv_dir)

    def run(
        self,
        code: str,
        cwd: Optional[Path] = None,
        workspace: Optional[Path] = None,
    ) -> ExecResult:
        """
        执行 Python 代码

        代码在 tools venv 中运行，可以访问:
        - tools.xxx: 所有工具模块
        - cwd: 当前工作目录
        - workspace: 工作区根目录
        - 常用模块: json, re, os, Path

        Args:
            code: Python 代码字符串
            cwd: 当前工作目录
            workspace: 工作区根目录

        Returns:
            ExecResult
        """
        python = self.ensure_venv()

        # 构建执行脚本
        wrapper_script = self._build_wrapper_script(code, cwd, workspace)

        try:
            result = subprocess.run(
                [str(python), "-c", wrapper_script],
                cwd=str(cwd) if cwd else None,
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

    def _build_wrapper_script(
        self,
        code: str,
        cwd: Optional[Path],
        workspace: Optional[Path],
    ) -> str:
        """构建包装脚本，注入上下文"""
        tools_dir_str = str(self.tools_dir).replace("\\", "\\\\")
        cwd_str = str(cwd).replace("\\", "\\\\") if cwd else ""
        workspace_str = str(workspace).replace("\\", "\\\\") if workspace else ""

        # 转义用户代码中的特殊字符
        escaped_code = code.replace("\\", "\\\\").replace('"', '\\"')

        wrapper = f'''
import sys
import os
import json
import re
import importlib.util
from pathlib import Path

# 上下文变量
cwd = Path("{cwd_str}") if "{cwd_str}" else Path.cwd()
workspace = Path("{workspace_str}") if "{workspace_str}" else cwd
tools_dir = Path("{tools_dir_str}")

# 动态加载 tools 命名空间
class ToolsNamespace:
    pass

tools = ToolsNamespace()
for py_file in tools_dir.glob("*.py"):
    tool_name = py_file.stem
    try:
        spec = importlib.util.spec_from_file_location(tool_name, py_file)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            setattr(tools, tool_name, module)
    except Exception as e:
        print(f"Warning: Failed to load tool {{tool_name}}: {{e}}", file=sys.stderr)

# 执行用户代码
_code = """{escaped_code}"""
try:
    # 尝试 eval (表达式)
    try:
        _result = eval(_code)
        if _result is not None:
            print(_result)
    except SyntaxError:
        # 尝试 exec (语句)
        exec(_code)
except Exception as e:
    print(f"{{type(e).__name__}}: {{e}}", file=sys.stderr)
    sys.exit(1)
'''
        return wrapper


class SkillExecutor:
    """
    技能执行器

    每个技能有独立的虚拟环境，使用 uv 管理依赖。

    目录结构:
        skills/
        └── web-scraper/
            ├── .venv/             # 技能专属 venv (uv 风格)
            ├── requirements.txt   # 技能依赖
            ├── SKILL.md           # 技能文档
            └── main.py            # 入口脚本
    """

    def __init__(self, config: "EnvManager"):
        self.config = config
        self.skills_dir = config.skills_dir
        self._uv = _find_uv()

    def ensure_venv(self, skill_name: str) -> Path:
        """确保技能的虚拟环境存在，返回 Python 路径"""
        skill_dir = self.skills_dir / skill_name
        venv_dir = skill_dir / ".venv"

        if not venv_dir.exists():
            raise RuntimeError(
                f"技能 venv 不存在: {skill_dir.name}，请在配置阶段创建 (.venv)"
            )

        return _get_python(venv_dir)

    def run(
        self,
        script_path: str,
        args: list[str],
    ) -> ExecResult:
        """
        执行技能脚本

        Args:
            script_path: 脚本路径，格式为 "skill_name/script.py"
            args: 传递给脚本的参数

        Returns:
            ExecResult
        """
        # 解析路径
        parts = script_path.split("/", 1)
        skill_name = parts[0]

        skill_dir = self.skills_dir / skill_name
        if not skill_dir.is_dir():
            return ExecResult(stderr=f"技能不存在: {skill_name}", return_code=1)

        full_script = self.skills_dir / script_path
        if not full_script.exists():
            return ExecResult(stderr=f"脚本不存在: {script_path}", return_code=1)

        # 确保 venv 存在
        try:
            python = self.ensure_venv(skill_name)
        except Exception as e:
            return ExecResult(stderr=f"创建虚拟环境失败: {e}", return_code=1)

        cmd = [str(python), str(full_script)] + args

        try:
            result = subprocess.run(
                cmd,
                cwd=str(skill_dir),
                capture_output=True,
                text=True,
                timeout=300,
            )
            return ExecResult(
                stdout=result.stdout,
                stderr=result.stderr,
                return_code=result.returncode,
            )
        except subprocess.TimeoutExpired:
            return ExecResult(stderr="执行超时 (300s)", return_code=124)
        except Exception as e:
            return ExecResult(stderr=f"执行错误: {e}", return_code=1)
