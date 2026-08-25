#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""子代理 Codex —— 正确性与资金安全视角。

模拟 harness-subagent 中 codex backend 的「实现/审查」角色，
从逻辑正确性、事务安全、边界校验角度分析同一份代码。
"""
import sys
import re
import os


def extract_code(text: str) -> str:
    m = re.search(r"```(?:python)?\s*(.*?)```", text, re.DOTALL)
    return m.group(1).strip() if m else text


def analyze(code: str):
    findings = []
    low = code.lower()
    # 无事务的余额操作
    if "set_balance" in low and "transfer" in low:
        findings.append((
            "高", "无事务保护",
            "transfer 中两次 set_balance 之间若进程崩溃会丢钱；且两次写操作非原子，"
            "并发请求下会产生竞态导致资金错误。应包在数据库事务中。",
        ))
    # 金额未校验
    if "amount" in low and not re.search(r'amount\s*[<>=]', low):
        findings.append(("中", "金额未校验", "未检查 amount <= 0，可能通过负值转账套利。"))
    # SQL 拼接（与 claude 交叉验证同一问题）
    if re.search(r'query\(.*\+', code):
        findings.append((
            "严重", "SQL 注入",
            "直接拼接 user_id 进查询，结合登录逻辑可越权读取他人数据。",
        ))
    # 缺少异常处理
    if "try" not in low:
        findings.append((
            "中", "缺异常处理",
            "数据库调用无 try/except，连接失败会抛出未捕获异常导致服务 500。",
        ))
    return findings


def main():
    brief, out = sys.argv[1], sys.argv[2]
    with open(brief, encoding="utf-8") as f:
        text = f.read()
    code = extract_code(text)
    findings = analyze(code)
    lines = [
        "# Codex 正确性与资金安全报告",
        "",
        f"- 输入代码行数：{len(code.splitlines())}",
        f"- 发现逻辑风险：{len(findings)} 项",
        "",
    ]
    if not findings:
        lines.append("✅ 未检测到明显逻辑风险。")
    for sev, name, desc in findings:
        lines.append(f"## [{sev}] {name}")
        lines.append(desc)
        lines.append("")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[codex] 正确性视角完成，输出 {len(findings)} 项发现 -> {out}")


if __name__ == "__main__":
    main()
