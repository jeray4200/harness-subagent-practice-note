#!/usr/bin/env bash
# 一键跑通多 Harness 编排 demo
set -e
cd "$(dirname "$0")"
python3 orchestrator.py
