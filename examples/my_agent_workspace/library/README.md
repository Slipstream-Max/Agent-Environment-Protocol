# Agent Environment Protocol (AEP)

> 一种基于文件系统的 Agent 管理协议，让 AI Agent 通过命令行探索和使用能力。

Version: 1.2.2

---

## 核心哲学（Core Philosophy）

> Terminal as Interface
> Filesystem as Context
> Git as Memory

AEP 不试图重新发明操作系统，也不将 Agent 视为特殊存在。

在 AEP 中：
- **Agent** 是一个会使用终端的操作者
- **Runtime** 是执行、约束与记录的系统
- **文件系统** 是唯一真实上下文
- **Git** 是唯一持久记忆

> Agent 不拥有状态，状态属于 Agent Enviroment。

---

## 1. 设计目标（Design Goals）

AEP 的目标是定义一种以文件系统为中心，聚合tools skills library的Agent运行时协议。同时添加tools skills运行时机制，支持以python代码的方式调用tools，支持以skills开头的命令调用skills。

---

## 2. 安装与快速开始

### 安装

```python
from aep import AEP
from openai import OpenAI

aep=AEP("./my-workspace")

client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="not-needed",
)

client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello, how are you?"},
    ],
    tools=aep.as_tools(),
    tool_choice="auto",
)


```

### 快速开始



---

## 3. 设计详情（Design Details）

### 3.1 Agent Enviroment 模型

Agent Enviroment 是 AEP 中的最小执行与回滚单元。
每次 Agent 运行绑定到一个 Agent Enviroment，对 Agent 而言是“整个世界”。

#### 目录结构
```
.agent / workspace
├── tools/      # 注入型工具（只读）
├── skills/     # 可执行技能（只读）
├── library/    # 规则 / 人设 / 文档（只读）
└── .           # Agent 工作区（读写）
```

> Runtime 可以通过 Git worktree 并行创建多个 Agent Enviroment。

### 3.2 权限与安全模型

AEP 完全依赖 Linux 原生权限机制。

| 路径 | 用户 | 权限 | 语义 |
| :--- | :--- | :--- | :--- |
| tools/ | root | 555 | 系统工具，不可修改 |
| skills/ | root | 555 | 系统技能，不可修改 |
| library/ | root | 444 | 文档与规则 |

---

## 4. 架构设计

详见 [arch.md](arch.md) 完整架构设计。
