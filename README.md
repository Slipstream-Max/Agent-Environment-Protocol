Agent Environment Protocol (AEP)

Version: 1.2.2

---

核心哲学（Core Philosophy）

> Terminal as Interface
Filesystem as Context
Git as Memory



AEP 不试图重新发明操作系统，也不将 Agent 视为特殊存在。

在 AEP 中：

Agent 是一个会使用终端的操作者

Runtime 是执行、约束与记录的系统

文件系统是唯一真实上下文

Git 是唯一持久记忆


Agent 不拥有状态， 状态属于 Workspace。


---

1. 设计目标（Design Goals）

AEP 的目标是定义一种：

可回放（Replayable）

可回滚（Reversible）

可并行（Parallelizable）

可演化（Evolvable）


的 Agent 运行时协议。

AEP 明确反对：

隐式内存

黑箱工具调用

Agent 自主持久化



---

2. Workspace 模型（Workspace Model）

2.1 Workspace 定义

Workspace 是 AEP 中的最小执行与回滚单元。

每次 Agent 运行绑定到一个 Workspace

Workspace 对 Agent 而言是“整个世界”


2.2 目录结构（单 Workspace 实例）

/workspace
├── tools/      # 注入型工具（只读）
├── skills/     # 可执行技能（只读）
├── library/    # 规则 / 人设 / 文档（只读）
└── .           # Agent 工作区（读写）

> Runtime MAY 通过 Git worktree 并行创建多个 Workspace。




---

3. 权限与安全模型（Security Model）

AEP 完全依赖 Linux 原生权限机制。

路径	用户	权限	语义

tools/	root	555	系统工具，不可修改
skills/	root	555	系统技能，不可修改
library/	root	444	文档与规则
workspace root	agent	755	Agent 自由空间


Agent 运行身份：agent

Agent 不得：

修改 tools / skills / library

提权

绕过 Runtime Hook



---

4. 执行接口（Runtime Interfaces）

AEP 中所有能力均以命令行形式暴露。

差异仅在于：

所连接的 Runtime

是否隔离

生命周期



---

4.1 Shell（系统命令）

标准 Linux 命令：

ls
sed -i 's/foo/bar/' file.txt

规则：

仅允许非交互式命令

禁止启动 REPL（vim / nano / python 等）



---

4.2 tools —— 注入型 Python CLI

tools 是一个 命令行形式的 Python 注入执行器。

tools "print(1 + 1)"

语义：

CLI 入口

不启动新进程

将代码字符串注入到宿主 Python Runtime中执行

Runtime 已预加载 tools/* 命名空间


特点：

启动极快

共享上下文

适合 glue logic / 轻处理



---

4.3 calltool —— 结构化工具调用

calltool 是 tools Runtime 内部的规范化调用形式：

tools.web.search.run(query="AEP")

用途：

参数 schema 明确

便于 tracing / logging

限制自由拼装逻辑


calltool 不是独立通道。


---

4.4 skills —— 可执行技能 CLI

skills 是 标准 Unix 可执行程序：

skills ./skills/data_cleaner/run.py --input raw.csv --output clean.csv

语义：

独立进程

Shebang 驱动（uv / venv 等）

独立依赖


适合：

重任务

稳定、可复用能力



---

5. 文件修改原则（File Mutation Policy）

AEP 不定义专用的编辑协议。

原因：

Unix 工具链已足够完整

sed / awk / perl / python / tools 均合法


唯一约束：

修改仅发生在 Workspace 内

所有修改都会被 Runtime 记录



---

6. 启动注入（Boot Injection）

在 Session 启动时，Runtime 会：

1. 加载基础 System Prompt（终端操作者身份）


2. 自动读取：



/workspace/library/boot/*.md

3. 追加注入到 System Prompt



library/docs/ 不会自动注入，仅供按需查阅。


---

7. Turn 状态机（Turn State Machine）

每次 Agent 运行被定义为一个 Turn。

TURN START
  ├─ LLM 思考（无副作用）
  ├─ LLM 执行命令（shell / tools / skills）
  ├─ LLM 自检
TURN END

Agent 不知道 Turn 的存在。

Turn 由 Runtime 管理。


---

8. Runtime Hook 与 Checkpoint

在 TURN END 时，Runtime 必须自动执行 Hook。

Hook 行为包括：

文件系统 diff

Workspace 状态快照

Git commit（Checkpoint）


Agent 不得 主动触发或控制 checkpoint。


---

9. Checkpoint 语义

每个 Turn 对应一个 Checkpoint：

精确映射一次 Agent 行为

可回滚

可重放


示例 Commit Message：

turn: 12
status: SUCCESS
files:
- output.csv


---

10. 失败语义（Failure Semantics）

失败是 AEP 的一等状态。

以下情况视为失败：

非零退出码

tools / skills 抛出异常

Runtime 检测到违规


失败 Turn 仍必须生成 Checkpoint：

turn: 13
status: FAILED
reason: schema mismatch


---

11. 并行执行（Git Worktree）

AEP 推荐使用 Git worktree 实现并行 Workspace：

git worktree add ../ws_a branch-a
git worktree add ../ws_b branch-b

特性：

每个 Workspace 独立 HEAD

文件系统完全隔离

Agent 互不可见


整合由 Runtime 或 Builder Agent 完成。


---

12. Worker–Builder 演化模型

AEP 采用双循环演化模型。

Worker Agent（agent 用户）

执行任务

可创建临时脚本

无长期记忆


Builder Agent（root 用户）

观察 Git 历史

识别高价值脚本

内化为 skills

编写 README 与索引


Worker 不学习。

系统进化由 Builder 完成。


---

13. 不变量（Invariants）

AEP 系统必须满足：

1. 文件系统即事实


2. Git 即记忆


3. Agent 无隐式状态


4. 每个 Turn 可回放


5. 每次执行必留痕




---

14. 总结（Summary）

AEP 是一个：

极度 Unix

极度可审计

极度可控


的 Agent 运行时协议。

Agent 只是执行者。

Runtime 才是时间本身。
