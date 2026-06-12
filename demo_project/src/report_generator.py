#!/usr/bin/env python3
"""report_generator.py — 报告生成 (食神·创生输出)"""

from typing import List, Dict
from datetime import datetime

def generate_report(records: List[Dict]) -> str:
    """生成文本报告"""
    now = datetime.now().isoformat()
    lines = [f"Report @ {now}", "=" * 40]
    for i, r in enumerate(records, 1):
        lines.append(f"{i}. {r.get('user', '?')}: {r.get('action', '?')} [{r.get('status', '?')}]")
    lines.append(f"\nTotal: {len(records)} records")
    return "\n".join(lines)
