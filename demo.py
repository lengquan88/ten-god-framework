#!/usr/bin/env python3
"""
demo.py — 十神框架自动化演示脚本
=================================

创建一个空项目 → 初始化十神框架 → 展示效果。
运行: python demo.py
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

FRAMEWORK_ROOT = os.path.dirname(os.path.abspath(__file__))

# ═══════════════════════════════════════════════════════════
# 演示场景
# ═══════════════════════════════════════════════════════════

def print_step(n: int, title: str):
    print(f'\n{"=" * 60}')
    print(f'  Step {n}: {title}')
    print(f'{"=" * 60}')

def demo():
    print('\n' + '=' * 60)
    print('  十神架构框架 — 自动化演示')
    print('  ten-god-framework demo v1.0')
    print('=' * 60)

    # ── Step 1: 创建项目 ─────────────────────────────
    print_step(1, '创建一个"混乱"的新项目')

    demo_dir = os.path.join(FRAMEWORK_ROOT, 'demo_project')
    if not os.path.exists(demo_dir):
        print('  demo_project/ 已存在，使用现有文件')
    else:
        print('  项目文件:')
        for root, dirs, files in os.walk(demo_dir):
            for f in files:
                if f.endswith('.py'):
                    rel = os.path.relpath(os.path.join(root, f), demo_dir)
                    print(f'    {rel}')

    # ── Step 2: 初始化十神 ───────────────────────────
    print_step(2, '一键初始化十神框架')

    init_script = os.path.join(FRAMEWORK_ROOT, 'init_tengod.py')
    if os.path.exists(init_script):
        result = subprocess.run(
            [sys.executable, init_script, demo_dir, '--name', 'DemoApp', '--scan'],
            capture_output=True, text=True, timeout=30, cwd=FRAMEWORK_ROOT)
        print(result.stdout[-800:] if result.stdout else '(no output)')
        if result.stderr:
            print(f'  [stderr]: {result.stderr[:200]}')
    else:
        print(f'  [!] init_tengod.py 未找到，使用已初始化的项目')

    # ── Step 3: 展示目录结构 ─────────────────────────
    print_step(3, '查看十神目录结构')

    tengod_dir = os.path.join(demo_dir, 'tengod')
    if os.path.exists(tengod_dir):
        for item in sorted(os.listdir(tengod_dir)):
            item_path = os.path.join(tengod_dir, item)
            if os.path.isdir(item_path) and not item.startswith('_'):
                py_count = len([f for f in os.listdir(item_path) if f.endswith('.py')])
                if py_count > 0:
                    print(f'  {item}/ ({py_count} .py)')
    else:
        print('  (运行 init_tengod.py 以生成)')

    # ── Step 4: 运行扫描 ─────────────────────────────
    print_step(4, '运行十神扫描')

    scan_script = os.path.join(demo_dir, 'tengod_scan.py')
    if os.path.exists(scan_script):
        result = subprocess.run(
            [sys.executable, scan_script],
            capture_output=True, text=True, timeout=30, cwd=demo_dir)
        print(result.stdout[:600] if result.stdout else '(no output)')
    else:
        print('  (运行 init_tengod.py --scan 以生成扫描器)')

    # ── Step 5: 展示报表 ─────────────────────────────
    print_step(5, '查看初始化报告')

    report_path = os.path.join(demo_dir, 'tengod_init_report.json')
    if os.path.exists(report_path):
        with open(report_path, 'r', encoding='utf-8') as f:
            report = json.load(f)
        print(f'  项目: {report.get("project", "?")}')
        print(f'  模块总数: {report.get("total_modules", 0)}')
        print(f'  已归类: {report.get("classified", 0)}')
        print(f'  十神分布:')
        for god, data in report.get('gods', {}).items():
            count = data.get('count', 0)
            if count > 0:
                print(f'    {god}: {count} 模块')

    # ── 总结 ─────────────────────────────────────────
    print_step(6, '演示完成')

    print(f'''
  你的项目现在拥有:
    - 十神分类目录结构
    - 自动扫描引擎 (tengod_scan.py)
    - 初始化报告 (tengod_init_report.json)

  下一步:
    cd {demo_dir}
    python tengod_scan.py --json    # 导出JSON报告
    # 复制进阶引擎:
    cp ../core/*.py .               # 核心引擎
    cp ../advanced/*.py .           # 进阶引擎
''')

    print('=' * 60)
    print('  演示结束 — 十神框架已就绪')
    print('=' * 60)


if __name__ == '__main__':
    demo()
