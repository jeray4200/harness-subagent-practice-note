#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""子代理 Grok —— 代码风格与健壮性视角。

模拟 harness-subagent 中 grok backend 的「实现（implement）」角色，
从可维护性、输入校验、类型安全角度分析同一份代码。
"""
import sys
import re
import os


def extract_code(text: str) -> str:
    m = re.search(r"```(?:python)?\s*(.*?)```", text, re.DOTALL)
    return m.group(1).strip() if m else text


def analyze(code: str):
    findings = []
    # 魔法字符串
    if re.search(r'==\s*["\']admin', code):
        findings.append((
            "低", "魔法字符串",
            '"admin" 硬编码在逻辑中，应提取为常量或配置，便于多角色扩展。',
        ))
    # 缺类型注解
    if re.search(r'def \w+\([^)]*\)\s*:', code) and "->" not in code:
        findings.append((
            "低", "缺类型注解",
            "函数无返回类型注解，降低可读性与静态检查能力。",
        ))
    # 输入校验（session/user_id 合法性）
    body_after_def = code.split("def", 1)[1]
    head = body_after_def[:300]
    if re.search(r'def .*session', code) and "if" not in head:
        findings.append((
            "中", "缺输入校验",
            "函数未校验 session/user_id 的合法性与归属，易产生越权调用。",
        ))
    return findings


def main():
    brief, out = sys.argv[1], sys.argv[2]
    with open(brief, encoding="utf-8") as f:
        text = f.read()
    code = extract_code(text)
    findings = analyze(code)
    lines = [
        "# Grok 风格与健壮性报告",
        "",
        f"- 输入代码行数：{len(code.splitlines())}",
        f"- 发现可维护性问题：{len(findings)} 项",
        "",
    ]
    if not findings:
        lines.append("✅ 代码风格良好。")
    for sev, name, desc in findings:
        lines.append(f"## [{sev}] {name}")
        lines.append(desc)
        lines.append("")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[grok] 风格视角完成，输出 {len(findings)} 项发现 -> {out}")


if __name__ == "__main__":
    main()
