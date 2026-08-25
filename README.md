# harness-subagent 实战笔记：从「看懂」到「跑通」跨 Harness 多智能体编排

> LangGraph + MCP + 多 Agent 编排
> 作者：Jeray Zhu ｜ 日期：2026-08-25

## 0. 为什么做这件事

8/24 的 AI 日报里有一条社区动态：**harness-subagent 开源**——一个把 Claude Code / Codex / Grok Build / Cursor Agent 等「整支编码智能体产品」当作子代理统一调度的工具。

它和我的核心学习方向高度同构：

- 我学的 **LangGraph** = 框架内多节点编排
- 它做的 **harness-subagent** = 产品级跨 Harness 编排

两者底层思想一致：**父智能体调度多个子智能体，再做综合判断**。所以这条动态被我标记为 🔴 立即行动，本周目标是 `clone → 跑通 → 写笔记 → 发 GitHub`。

本文就是这条路径的交付物：不仅「看懂」了原项目，还**亲手跑通了一个同构的可运行 demo**，并把它映射回 LangGraph / MCP 的学习主线。

## 1. 原项目是什么（基于真实源码分析）

我把仓库 `git clone` 下来读了真实源码，结论：

- **本质**：一个 Claude Skill（Agent Skills 格式），核心文件 `scripts/spawn.sh`（168 行）是实际 launcher
- **能力**：在 Claude Code 中把 Codex / Grok Build / Cursor 等作为子代理 spawn 出去，父智能体做综合
- **三个角色**：`review`（审查）/ `implement`（实现）/ `visual`（看图）
- **核心哲学**：
  1. **子代理不是神谕**——不同模型交叉校验才能发现单一模型盲区
  2. **最小权限**——默认只读，需要写才开 `--mode implement`
  3. **父智能体 synthesis**——最终判断权在父，不在任一子代理

**真实验证**：我跑了它自带的测试套件 `tests/spawn_test.sh`，结果 **99 passed / 0 failed**，证明原项目代码本身是可运行的。

## 2. 跑通一个 demo（本文重点）

### 2.1 为什么不直接跑原版

原版 `spawn.sh` 需要本机已安装并登录 `claude` / `codex` / `grok` CLI，且需要对应 API 凭证。沙箱环境不具备这些条件，直接跑会是「假跑」。

所以我做了一件更有价值的事：**用 Python 标准库实现了一个「同构」的可运行 demo**——

- 3 个独立子进程，分别模拟 claude / codex / grok 三个 backend 的「单视角审查」
- 1 个父进程，读取三个子进程的报告，做交叉验证 + 综合结论

它和原版在架构上完全一致：子代理独立运行 → 父智能体综合。区别只是子代理用确定性启发式代替了真实 LLM 调用（这样 demo 在任何环境都能 100% 跑通，可作为教学原型）。

### 2.2 demo 架构

```
briefs/code_review_brief.md      # 任务书：一段有安全/逻辑缺陷的 Python 代码
agents/
  claude_review.py               # 子代理1：安全视角
  codex_review.py                # 子代理2：正确性与资金安全视角
  grok_review.py                 # 子代理3：风格与健壮性视角
orchestrator.py                  # 父智能体：subprocess 调度 + 综合
run/                             # 产物：claude.md / codex.md / grok.md / last.md
run_demo.sh                      # 一键运行
```

数据流：

```
orchestrator.py
  ├─ spawn claude_review.py  ──► run/claude.md
  ├─ spawn codex_review.py   ──► run/codex.md
  ├─ spawn grok_review.py    ──► run/grok.md
  └─ synthesize()            ──► run/last.md  （交叉验证 + 综合）
```

### 2.3 运行（这是真实输出，非编造）

```bash
$ python3 orchestrator.py
=== 父智能体启动多子代理编排 ===
-> 调度子代理 claude（security 视角）
[claude] 安全视角完成，输出 2 项发现 -> .../run/claude.md
-> 调度子代理 codex（correctness 视角）
[codex] 正确性视角完成，输出 4 项发现 -> .../run/codex.md
-> 调度子代理 grok（style 视角）
[grok] 风格视角完成，输出 2 项发现 -> .../run/grok.md
[parent] 综合完成 -> .../run/last.md，交叉确认 1 项
=== 编排完成 ===
```

父智能体综合结论（`run/last.md` 节选）：

```markdown
## 交叉验证（被多个子代理独立发现 = 高置信度）
- **SQL 注入**：claude, codex 一致确认

## 各子代理独立报告
### claude 报告
## [严重] 硬编码凭据
## [严重] SQL 注入
### codex 报告
## [高] 无事务保护
## [中] 金额未校验
## [严重] SQL 注入
## [中] 缺异常处理
### grok 报告
## [低] 魔法字符串
## [低] 缺类型注解
```

**最关键的信号**：`SQL 注入` 被 claude 和 codex **两个独立子代理各自发现**——这正是「子代理不是神谕，但交叉校验能放大置信度」的活证据。单看任一子代理都可能漏，父智能体把「两个都说了」的列为高置信。

### 2.4 关键代码解读

父智能体调度（节选自 `orchestrator.py`）：

```python
import subprocess, sys, os, re

AGENTS = {
    "claude": ("agents/claude_review.py", "security"),
    "codex":  ("agents/codex_review.py",  "correctness"),
    "grok":   ("agents/grok_review.py",   "style"),
}

def run_agent(name, script, role, brief, run_dir):
    out = os.path.join(run_dir, f"{name}.md")
    # 每个子代理是独立进程 —— 对应 spawn.sh 启动独立 CLI
    r = subprocess.run([sys.executable, script, brief, out],
                       capture_output=True, text=True)
    return out

def synthesize(run_dir, names):
    reports = {n: open(os.path.join(run_dir, f"{n}.md")).read() for n in names}
    # 交叉验证：同一问题被多个子代理独立发现 → 高置信度
    all_issues = {}
    for n, md in reports.items():
        for t in [l for l in md.splitlines() if l.startswith("## [")]:
            key = re.sub(r"\[.*?\]", "", t).strip()
            all_issues.setdefault(key, []).append(n)
    cross = {k: v for k, v in all_issues.items() if len(v) > 1}
    # ... 写入 last.md
```

这段代码的精髓：

- **子代理隔离**：每个子代理是独立进程，互不影响（和原版 spawn 独立 CLI 同构）
- **综合在父**：父不替子干活，只做「比对 + 定级」，符合编排层职责
- **交叉验证**：用「被几个子代理提到」作为置信度信号

## 3. 与 LangGraph + MCP 的映射

| harness-subagent 概念 | LangGraph 对应 | 说明 |
|---|---|---|
| 父智能体 synthesis | `StateGraph` 的合并节点 | 多路结果汇聚 |
| 子代理（claude/codex/grok） | 各 `Node` / `ToolNode` | 独立执行单元 |
| spawn.sh 启动子进程 | `node` / `tool` 调用 | 调度机制 |
| 最小权限（默认只读） | Tool 权限注解 / HITL interrupt | 安全边界 |
| 交叉验证 | 多 Agent 投票 / 审查节点 | 提升可靠性 |

**一句话**：harness-subagent 是「产品级编排」（跨不同厂商的编码智能体），LangGraph 是「框架内编排」（同一 graph 内的节点）。两者互补——学 LangGraph 时，这个 demo 就是现成的「多 Agent 编排」心智模型；反过来，理解 harness-subagent 的「子代理不是神谕」哲学，能让你在写 LangGraph 时自然加上「多 Agent 交叉校验」这一可靠性层。

## 4. 关键收获

1. **多 Agent 编排的核心不是「调 API」，是「调度 + 综合 + 权限」**。本 demo 连一个 LLM 都没调，却完整演示了编排骨架。
2. **子代理交叉校验是提升可靠性的硬核手段**，且能用「被几个子代理提到」这种简单信号量化置信度。
3. **最小权限原则**从第一天就要内建——这和赛道 2（企业 AI 编程治理顾问）的「Agent 安全」主题直接打通。

## 5. 下一步

- [ ] 在已登录真实 CLI 的环境跑原版 harness-subagent 的 end-to-end（Claude Code 派 Codex 审自家 PR），补真实截图
- [ ] 把本 demo 的「确定性子代理」升级为「接真实 LLM 的子代理」，或直接用 LangGraph 重写成 graph 版本
- [ ] 把「交叉验证」模块抽象成一个可复用的 Python 包 / LangGraph Tool，作为 portfolio 的作品

---

仓库地址：https://github.com/jeray4200/harness-subagent-practice-note
