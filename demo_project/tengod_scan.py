#!/usr/bin/env python3
"""
tengod_scan.py — 十神全域扫描 (由 init_tengod.py 为 DemoApp 生成)
v1.1 — 性能优化版（预编译正则 + 缓存）

用法: python tengod_scan.py [--html] [--json] [--stats]
"""

import argparse
import json
import os
import re
from collections import defaultdict
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# 性能优化：预编译正则一次，避免每次扫描时重复编译
COMPILED_KEYWORDS = {}

GODS_RAW = {
    "比肩": {
        "element": "木",
        "keywords": [
            "main",
            "app",
            "core",
            "orchestrat",
            "run",
            "server",
            "init",
            "startup",
            "bootstrap",
            "entry",
            "config",
            "settings",
        ],
    },
    "劫财": {
        "element": "木",
        "keywords": [
            "auth",
            "security",
            "guard",
            "defend",
            "protect",
            "firewall",
            "validate",
            "sanitize",
            "rate_limit",
            "permission",
            "access",
        ],
    },
    "食神": {
        "element": "火",
        "keywords": [
            "generate",
            "output",
            "export",
            "render",
            "report",
            "template",
            "llm",
            "ai",
            "nlp",
            "chat",
            "message",
            "notify",
            "email",
        ],
    },
    "伤官": {
        "element": "火",
        "keywords": [
            "analyze",
            "causal",
            "reason",
            "infer",
            "predict",
            "model",
            "train",
            "learn",
            "innovate",
            "experiment",
            "research",
        ],
    },
    "正财": {
        "element": "土",
        "keywords": [
            "store",
            "database",
            "db",
            "repository",
            "model",
            "entity",
            "schema",
            "migration",
            "cache",
            "knowledge",
            "graph",
            "data",
        ],
    },
    "偏财": {
        "element": "土",
        "keywords": [
            "search",
            "optimize",
            "tune",
            "algorithm",
            "recommend",
            "rank",
            "sort",
            "filter",
            "query",
            "find",
            "explore",
        ],
    },
    "正官": {
        "element": "金",
        "keywords": [
            "api",
            "router",
            "handler",
            "controller",
            "endpoint",
            "service",
            "pipeline",
            "queue",
            "schedule",
            "task",
            "job",
            "workflow",
        ],
    },
    "七杀": {
        "element": "金",
        "keywords": [
            "test",
            "eval",
            "quality",
            "benchmark",
            "monitor",
            "metric",
            "check",
            "audit",
            "review",
            "inspect",
            "assert",
            "score",
        ],
    },
    "正印": {
        "element": "水",
        "keywords": [
            "config",
            "env",
            "setup",
            "install",
            "init",
            "bootstrap",
            "console",
            "cli",
            "admin",
            "dashboard",
            "provision",
        ],
    },
    "偏印": {
        "element": "水",
        "keywords": [
            "bridge",
            "adapter",
            "connector",
            "integrate",
            "proxy",
            "gateway",
            "transform",
            "convert",
            "mapper",
            "translate",
            "sync",
            "client",
        ],
    },
    "未归类": {
        "element": "?",
        "keywords": [],
    },
}


def _build_compiled():
    """构建预编译的正则表达式"""
    for god, info in GODS_RAW.items():
        keywords = info.get("keywords", [])
        if keywords:
            # 把所有关键词合并到一个正则中，单次扫描匹配
            pattern = re.compile(
                "|".join(re.escape(k) for k in keywords),
                re.IGNORECASE,
            )
            COMPILED_KEYWORDS[god] = pattern
        else:
            COMPILED_KEYWORDS[god] = None
    return COMPILED_KEYWORDS


def _scan_tengod_subdirs():
    """扫描 tengod 子目录的 Python 文件数与代码行数"""
    tengod_root = os.path.join(PROJECT_ROOT, "tengod")
    stats = {}
    if not os.path.isdir(tengod_root):
        return stats
    for sub in os.listdir(tengod_root):
        full = os.path.join(tengod_root, sub)
        if not os.path.isdir(full) or sub.startswith((".", "_")):
            continue
        file_count = 0
        line_count = 0
        for r, _, files in os.walk(full):
            for f in files:
                if f.endswith(".py") and not f.startswith("_"):
                    file_count += 1
                    try:
                        with open(os.path.join(r, f), "r", encoding="utf-8") as fp:
                            line_count += sum(1 for _ in fp)
                    except IOError:
                        pass
        stats[sub] = {"files": file_count, "lines": line_count}
    return stats


def scan():
    """扫描项目 .py 文件并归类（高性能版）"""
    _build_compiled()
    result = defaultdict(list)
    file_count = 0
    line_count = 0

    for root, dirs, files in os.walk(PROJECT_ROOT):
        # 优化：原地修改 dirs 列表，os.walk 不会下钻排除的目录
        dirs[:] = [
            d
            for d in dirs
            if not d.startswith(".")
            and d not in ("__pycache__", "node_modules", ".git", "venv", "tengod")
        ]
        for fname in files:
            if not fname.endswith(".py") or fname.startswith("_"):
                continue
            file_count += 1
            full_path = os.path.join(root, fname)
            try:
                with open(full_path, "r", encoding="utf-8") as fp:
                    line_count += sum(1 for _ in fp)
            except IOError:
                pass

            rel = os.path.relpath(full_path, PROJECT_ROOT)
            fname_lower = fname.lower()
            matched = False
            # 单次正则匹配所有关键词
            for god, pattern in COMPILED_KEYWORDS.items():
                if god == "未归类":
                    continue
                if pattern and pattern.search(fname_lower):
                    result[god].append(rel)
                    matched = True
                    break
            if not matched:
                result["未归类"].append(rel)

    return {
        "classification": dict(result),
        "tengod_submodules": _scan_tengod_subdirs(),
        "file_count": file_count,
        "line_count": line_count,
        "scanned_at": datetime.now().isoformat(),
    }


def print_report():
    """打印报告"""
    data = scan()
    classification = data["classification"]
    total = sum(len(v) for v in classification.values())
    classified = total - len(classification.get("未归类", []))
    pct = round(classified / max(total, 1) * 100, 1)

    print("\n=== 十神全域扫描报告 ===")
    print(f"扫描时间: {data['scanned_at']}")
    print(f"项目文件: {data['file_count']} 个 .py 文件, {data['line_count']} 行代码")
    print(f"十神归类: {classified}/{total} 已归类 ({pct}%)")
    print()
    for god, files in sorted(classification.items(), key=lambda x: -len(x[1])):
        if god != "未归类":
            print(f"  {god}: {len(files)} 模块")

    # tengod 子模块统计
    submodules = data.get("tengod_submodules", {})
    if submodules:
        print("\n=== tengod 子模块统计 ===")
        for name, info in sorted(submodules.items()):
            print(f"  {name}: {info['files']} 文件 / {info['lines']} 行")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="输出 JSON 报告")
    parser.add_argument("--html", action="store_true", help="输出 HTML 报告")
    parser.add_argument("--stats", action="store_true", help="只输出统计信息")
    args = parser.parse_args()

    if args.json:
        json.dump(
            scan(), open("tengod_scan_report.json", "w"), ensure_ascii=False, indent=2
        )
        print("报告已写入 tengod_scan_report.json")
    else:
        print_report()
