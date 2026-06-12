#!/usr/bin/env python3
"""
tengod_scan.py — 十神全域扫描 (由 init_tengod.py 为 DemoApp 生成)

用法: python tengod_scan.py [--html] [--json]
"""

import json, os, sys
from collections import defaultdict
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

GODS = {
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
      "settings"
    ]
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
      "access"
    ]
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
      "email"
    ]
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
      "research"
    ]
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
      "data"
    ]
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
      "explore"
    ]
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
      "workflow"
    ]
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
      "score"
    ]
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
      "provision"
    ]
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
      "client"
    ]
  },
  "未归类": {
    "element": "?",
    "keywords": []
  }
}

def scan():
    """扫描项目 .py 文件并归类"""
    result = defaultdict(list)
    for root, dirs, files in os.walk(PROJECT_ROOT):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in
                   ('__pycache__', 'node_modules', '.git', 'venv', 'tengod')]
        for fname in files:
            if not fname.endswith('.py') or fname.startswith('_'):
                continue
            rel = os.path.relpath(os.path.join(root, fname), PROJECT_ROOT)
            matched = False
            for god, info in GODS.items():
                for kw in info.get('keywords', []):
                    if kw.lower() in fname.lower():
                        result[god].append(rel)
                        matched = True
                        break
                if matched:
                    break
            if not matched:
                result['未归类'].append(rel)
    return dict(result)

def print_report():
    scan_result = scan()
    total = sum(len(v) for v in scan_result.values())
    classified = total - len(scan_result.get('未归类', []))
    print(f"十神扫描: {classified}/{total} 已归类 ({round(classified/max(total,1)*100,1)}%)")
    for god, files in sorted(scan_result.items(), key=lambda x: -len(x[1])):
        if god != '未归类':
            print(f"  {god}: {len(files)} 模块")

if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--json', action='store_true')
    p.add_argument('--html', action='store_true')
    args = p.parse_args()
    if args.json:
        json.dump(scan(), open('tengod_scan_report.json','w'), ensure_ascii=False, indent=2)
    else:
        print_report()
