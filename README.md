# Agent-Environment-Protocol

## 1. 简介 (Introduction)

**Agent Environment Protocol (AEP)** 是一种定义 AI Agent 与其运行环境交互方式的标准协议。AEP 的核心理念是 **"Filesystem as Interface"** 与 **"Index-First Discovery" (索引优先发现)**。

旨在解决以下核心挑战：

* **上下文效率**：通过分层索引替代全量 Context 注入，解决 Token 挤占问题。
* **依赖隔离**：通过模块化容器与代理执行模式，解决复合技能的依赖冲突问题。
* **能力持久化**：将 Agent 的临时代码固化为文件系统中的可复用资产。

AEP 将环境抽象为四个标准域：**原子工具 (Tools)**、**复合技能 (Skills)**、**静态知识 (Library)** 和 **工作空间 (Workspace)**。

---

## 2. 核心组件 (Component Architecture)

### 2.1 原子工具域 (Tools / The Body)

* **定义**：预置的、无状态的系统级能力接口。通常为 MCP (Model Context Protocol) Server 的客户端存根 (Stubs)。
* **权限**：`ReadOnly` (只读)。Agent 无法修改底层工具逻辑。
* **交互**：通过 `_manifest.md` 暴露元数据。

### 2.2 复合技能域 (Skills / The Muscle Memory)

* **定义**：用户或 Agent 定义的高级工作流。包含完整的业务逻辑代码、依赖定义和描述文档。
* **权限**：`ReadWrite` (读写)。支持持久化存储。
* **运行时**：**隔离执行**。每个技能拥有独立的虚拟环境，通过代理模式调用。

### 2.3 静态知识域 (Library / The Memory)

* **定义**：非结构化的参考资料库（文档、日志、规范）。
* **权限**：`ReadWrite` (主要由 Librarian Agent 维护)。
* **机制**：**分形索引 (Fractal Indexing)**。采用层级化的 `_index.md` 引导 Agent 进行树状检索，避免向量搜索的幻觉。

### 2.4 动态工作域 (Workspace / The Desktop)

* **定义**：当前任务的执行现场。
* **权限**：`ReadWrite` (完全控制)。
* **隔离**：作为 CWD (Current Working Directory) 挂载，与系统层物理隔离，任务结束后可独立归档或销毁。

---

## 3. 文件系统结构 (Filesystem Structure)

AEP 协议强制要求以下目录拓扑结构：

```text
/aep_root
│
├── /tools (Mount: Read-Only)
│   ├── _manifest.md           # [Level 1] 全局工具索引
│   ├── /browser               # 工具包
│   │   ├── _manifest.md       # [Level 2] 包内功能索引
│   │   ├── open.py            # 执行入口
│   │   └── ...
│   └── /system
│
├── /skills (Mount: Read-Write, Persistent)
│   ├── _index.md              # 技能发现索引 (由 Watcher 自动维护)
│   └── /data_cleaner_pro      # [Skill Package]
│       ├── .venv/             # [Runtime] 隔离的虚拟环境 (uv managed)
│       ├── pyproject.toml     # [Config] 依赖声明文件
│       ├── script.py          # [Logic] 核心逻辑
│       └── description.md     # [Meta] 技能描述与参数定义
│
├── /library (Mount: Read-Write)
│   ├── _index.md              # 全局知识地图
│   └── /specifications
│       ├── _index.md          # 子目录摘要
│       ├── api_v1.pdf
│       └── api_v1.pdf.meta.md # [Shadow File] 大文件内容摘要
│
└── /workspace (Mount: Read-Write)
    ├── main.py
        └── data.csv

```

---

## 4. 运行时与隔离机制 (Runtime & Isolation)

AEP v1.1 引入 **"Proxy Execution Pattern" (代理执行模式)** 以解决依赖地狱。

### 4.1 技能隔离 (Per-Skill Isolation)

* 每个 `/skills` 子目录必须包含标准的依赖描述文件 (如 `pyproject.toml` 或 `requirements.txt`)。
* 环境不共享：Skill A 的依赖安装在 `/skills/A/.venv`，Skill B 安装在 `/skills/B/.venv`。
* **持久性**：由于 `/skills` 是挂载卷，`.venv` 随物理文件系统持久化，重启容器无需重装。

### 4.2 代理调用 (The Proxy Shim)

Agent 在主 REPL 环境中不直接 `import` 技能代码，而是通过系统内核提供的 **Proxy Object** 进行调用。

* **调用流**：
1. Agent 执行: `skills.data_cleaner.run(input="file.csv")`
2. Kernel 拦截: 识别为技能调用。
3. **CLI 桥接**: Kernel 构造子进程命令 `uv run script.py --args '...'`。
4. **隔离执行**: 代码在 `/skills/data_cleaner/.venv` 中运行。
5. **结果回传**: `stdout/stderr` 被捕获并返回给 Agent。

### 4.3 错误反馈回路 (Error Feedback Loop)

* 若依赖缺失或环境损坏，`uv` 或子进程会返回非零状态码。
* Kernel 将错误封装为 Python `RuntimeError` 抛出给 Agent。
* **Agent 自愈**：Agent 捕获异常 -> 读取 `pyproject.toml` -> 修正依赖 -> 再次调用 (触发自动重装)。

---

## 5. 生命周期与维护 (Lifecycle & Maintenance)

### 5.1 Watcher (守护进程)

系统后台运行一个文件系统监听器 (Sidecar Process)。

* **职责**：监听 `/tools`, `/skills`, `/library` 的 `CREATE`, `MODIFY`, `DELETE` 事件。
* **去抖动**：合并短时间内的多次修改。

### 5.2 Indexer (索引编制者)

由 Watcher 唤醒的轻量级 Sub-agent。

* **Tool/Skill 变更**：自动更新父目录的 `_manifest.md` 或 `_index.md`。
* **Library 变更**：自动读取新文件，生成摘要 (Summary) 和关键词 (Keywords)，更新索引文件。

### 5.3 Refactor Agent (重构代理)

响应 `/save_skill` 指令的专用 Agent。

* **输入**：会话历史代码、上下文变量。
* **输出**：在 `/skills` 中创建新目录，生成 `script.py` (参数化重构)、`description.md` 和 `pyproject.toml` (依赖推断)。

---

## 6. 部署技术栈推荐 (Recommended Stack)

* **容器化**：Docker / Podman (提供基础的文件系统隔离)。
* **包管理**：`uv` (极速 Python 包管理器，负责 Skill 的环境构建与运行)。
* **内核语言**：Python 3.10+ (作为 Host REPL)。
* **IPC**：Standard I/O (用于 REPL 与 Subprocess 通信)。

---

**附录：Agent 交互示例**

```python
    # 1. 探索
    print(open("/tools/_manifest.md").read()) 
    # -> 返回工具列表

    # 2. 调用原子工具 (In-Process)
    tools.web.search.run("Python AEP protocol")

    # 3. 调用复合技能 (Cross-Process via Proxy)
    # 这一步会自动检查并使用 /skills/report_gen/.venv
    skills.report_gen.run(topic="AEP") 

    # 4. 查阅资料 (Index-First)
    print(open("/library/_index.md").read())
    # -> 发现 /library/specs
    print(open("/library/specs/_index.md").read())
    # -> 找到目标文件
```