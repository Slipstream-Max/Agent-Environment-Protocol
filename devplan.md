# AEP 开发计划

> 增量交付，每个阶段结束都有可测试的产出。
> 核心理念：AEP 是一个基于文件系统的能力环境，通过 Schema 暴露给 LLM，支持代码编排。

---

## Phase 0: 环境基础 (Phase 0 & 1 合并) ✅

**目标**: `AgentEnvironment` 目录结构 + 基础文件操作

| 任务 | 产出 | 状态 |
|------|------|------|
| uv 初始化 | `pyproject.toml` | ✅ Done |
| AgentEnvironment | `aep/core/enviroment.py` (自包含目录) | ✅ Done |
| AEP 主类 | `aep/core/aep.py` (代理层) | ✅ Done |
| 文件操作 | `ls`, `cat`, `grep` (纯文件系统实现) | ✅ Done |
| 日志集成 | Loguru 集成 | ✅ Done |

---

## Phase 1: Tools 系统 - Python (Next)

**目标**: 支持添加 Python 本地工具，并生成 **渐进式披露文档 (L0/L1)**

| 任务 | 产出 | 验证 |
|------|------|------|
| add_tool(py) | 复制 Python 文件到 `tools/` | 文件存在 + 索引更新 |
| AST 解析 | 解析函数签名、文档字符串 | 解析准确性测试 |
| **L0 Index 生成** | `tools/index.md` (所有工具一句话摘要) | ls tools/ 显示摘要 |
| **L1 Doc 生成** | `tools/{name}/TOOL.md` (详细参数说明) | cat 显示完整文档 |

---

## Phase 2: Tools 系统 - MCP 集成

**目标**: 支持 MCP Server，自动转换为本地工具结构 (L0/L1)

| 任务 | 产出 | 验证 |
|------|------|------|
| MCP Client | 连接 MCP Server 获取 capabilities | 连接测试 |
| 存根生成 | 为每个 MCP Tool 生成 `stub.py` | 代码生成测试 |
| 自动转换 | `ListTools` -> `TOOL.md` + 更新 `index.md` | 转换准确性 |

---

## Phase 3: 执行引擎 (aep_tools)

**目标**: 实现 `aep_tools`，支持在环境内执行 Python 代码编排工具

| 任务 | 产出 | 验证 |
|------|------|------|
| 命名空间加载 | 动态加载 `tools/` 下的工具到 `tools.xxx` | 导入测试 |
| 安全执行环境 | 限制性的 Python 执行器 | 安全性测试 |
| 上下文注入 | 注入 `tools` 对象供代码调用 | 编排脚本执行 |

---

## Phase 4: Skills 系统

**目标**: 复杂的、多文件的能力包 + 渐进式披露

| 任务 | 产出 | 验证 |
|------|------|------|
| add_skill | 复制整个文件夹到 `skills/` | 目录完整性 |
| L0 Index | `skills/index.md` (技能列表) | ls skills/ |
| L1 Doc | `skills/{name}/README.md` (技能说明) | cat 技能文档 |
| 环境隔离 | 为每个 Skill 管理独立的 venv (uv) | 环境隔离测试 |
| aep_skills | 执行 Skill 入口脚本 | 脚本传参测试 |

---

## Phase 5: Library 系统

**目标**: 静态知识库 + 索引

| 任务 | 产出 | 验证 |
|------|------|------|
| add_library | 复制文档到 `library/` | 文件存在 |
| L0 Index | `library/index.md` (文档列表) | ls library/ |

---

## Phase 6: Agent 集成接口

**目标**: 完善 `as_tools()` schema 和 **`get_context()` 上下文加载**

| 任务 | 产出 | 验证 |
|------|------|------|
| **L0 Context 接口** | `aep.get_context()` 返回 standard intro | 输出内容检查 |
| Schema 完善 | 包含所有工具、参数的详细描述 | OpenAI 格式校验 |
| 错误处理 | 统一的错误返回格式 | 异常捕获测试 |

**get_context() 接口**:
AEP 提供标准接口，返回 "L0 开场白"，Agent 可将其注入 System Prompt 或 User Message。

```python
def get_context(self) -> str:
    """获取 L0 上下文 (开场白)"""
    return f"""
Current Environment:
{self.cat('tools/index.md')}
{self.cat('skills/index.md')}
{self.cat('library/index.md')}
"""
```
