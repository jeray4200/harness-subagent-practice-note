#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""父智能体（parent）：调度多个子代理（独立进程），读取各自报告，综合成 last.md。

对应 harness-subagent 的 spawn.sh（按 backend 启动子进程）+ 父智能体的
synthesis（综合判断）阶段。核心思想：子代理不是神谕，多个模型交叉校验才能
发现单一模型的盲区。

运行：python3 orchestrator.py
"""
import subprocess
import os
import sys
import re

# 子代理注册表：(脚本, 视角角色)
AGENTS = {
    "claude": ("agents/claude_review.py", "security"),
    "codex": ("agents/codex_review.py", "correctness"),
    "grok": ("agents/grok_review.py", "style"),
}


def run_agent(name: str, script: str, role: str, brief: str, run_dir: str):
    out = os.path.join(run_dir, f"{name}.md")
    r = subprocess.run(
        [sys.executable, script, brief, out],
        capture_output=True, text=True,
    )
    print(r.stdout.strip())
    if r.returncode != 0:
        print(r.stderr)
    return out


def extract_titles(md: str):
    return [l.strip() for l in md.splitlines() if l.startswith("## [")]


def synthesize(run_dir: str, names):
    reports = {}
    for n in names:
        with open(os.path.join(run_dir, f"{n}.md"), encoding="utf-8") as f:
            reports[n] = f.read()

    # 交叉验证：哪些问题被多个子代理独立发现 -> 高置信度
    all_issues = {}
    for n, md in reports.items():
        for t in extract_titles(md):
            key = re.sub(r"\[.*?\]", "", t).strip()
            all_issues.setdefault(key, []).append(n)
    cross = {k: v for k, v in all_issues.items() if len(v) > 1}

    lines = [
        "# 父智能体综合结论（last.md）",
        "",
        "## 交叉验证（被多个子代理独立发现 = 高置信度）",
        "",
    ]
    if cross:
        for k, v in cross.items():
            lines.append(f"- **{k}**：{', '.join(v)} 一致确认")
    else:
        lines.append("- 无跨代理一致项")
    lines += ["", "## 各子代理独立报告", ""]
    for n, md in reports.items():
        lines.append(f"### {n} 报告")
        lines.append(md)
        lines.append("")

    out = os.path.join(run_dir, "last.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[parent] 综合完成 -> {out}，交叉确认 {len(cross)} 项")


def main():
    base = os.path.dirname(os.path.abspath(__file__))
    brief = os.path.join(base, "briefs", "code_review_brief.md")
    run_dir = os.path.join(base, "run")
    os.makedirs(run_dir, exist_ok=True)

    print("=== 父智能体启动多子代理编排 ===")
    for name, (script, role) in AGENTS.items():
        print(f"-> 调度子代理 {name}（{role} 视角）")
        run_agent(name, os.path.join(base, script), role, brief, run_dir)
    synthesize(run_dir, list(AGENTS.keys()))
    print("=== 编排完成 ===")


if __name__ == "__main__":
    main()
