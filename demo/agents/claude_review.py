#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""子代理 Claude —— 安全视角审查。

读取 brief 中的代码，使用确定性启发式规则检测安全风险，输出 Markdown 报告。
这模拟 harness-subagent 中 claude backend 的「审查（review）」角色：
单一模型只看到自己视角，父智能体需要把多个模型的结论交叉比对。
"""
import sys
import re
import os


def extract_code(text: str) -> str:
    m = re.search(r"```(?:python)?\s*(.*?)```", text, re.DOTALL)
    return m.group(1).strip() if m else text


def analyze(code: str):
    findings = []
    # 硬编码凭据
    if re.search(r'(password|secret|api_key|token)\s*==\s*["\']', code, re.I):
        findings.append((
            "严重", "硬编码凭据",
            "代码中直接比较明文密码/密钥（如 password == \"secret123\"），"
            "应改为哈希比对，并将密钥移入密钥管理服务。",
        ))
    # SQL 拼接注入
    if re.search(r'SELECT.*FROM.*\+', code, re.I) or re.search(r'query\(.*\+', code):
        findings.append((
            "严重", "SQL 注入",
            "通过字符串拼接构造 SQL（如 \"... WHERE id = \" + user_id），"
            "攻击者可注入任意条件实现越权读取。必须使用参数化查询。",
        ))
    # 动态执行
    if re.search(r'\b(eval|exec)\s*\(', code):
        findings.append(("高", "动态执行", "使用了 eval/exec，存在代码注入风险。"))
    return findings


def main():
    brief, out = sys.argv[1], sys.argv[2]
    with open(brief, encoding="utf-8") as f:
        text = f.read()
    code = extract_code(text)
    findings = analyze(code)
    lines = [
        "# Claude 安全审查报告",
        "",
        f"- 输入代码行数：{len(code.splitlines())}",
        f"- 发现安全风险：{len(findings)} 项",
        "",
    ]
    if not findings:
        lines.append("✅ 未检测到明显安全风险。")
    for sev, name, desc in findings:
        lines.append(f"## [{sev}] {name}")
        lines.append(desc)
        lines.append("")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[claude] 安全视角完成，输出 {len(findings)} 项发现 -> {out}")


if __name__ == "__main__":
    main()
