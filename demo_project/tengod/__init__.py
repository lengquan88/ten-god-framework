#!/usr/bin/env python3
"""
tengod/__init__.py — 十神包体系 (由 init_tengod.py 自动生成)

项目: DemoApp
初始化时间: 2026-06-11T18:50:46.742013
模块总数: 10
"""

import sys
import os

# 先注入子模块路径到 sys.path
_TENGOD_ROOT = os.path.dirname(os.path.abspath(__file__))
# 把 tengod 目录自身也加入 path
if _TENGOD_ROOT not in sys.path:
    sys.path.insert(0, _TENGOD_ROOT)
for _subdir in os.listdir(_TENGOD_ROOT):
    _full = os.path.join(_TENGOD_ROOT, _subdir)
    if os.path.isdir(_full) and not _subdir.startswith('.') and not _subdir.startswith('_'):
        if _full not in sys.path:
            sys.path.insert(0, _full)

PROJECT_ROOT = os.path.dirname(_TENGOD_ROOT)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

GOD_NAMES = {
    "比肩": "架构协同 — 十神子包",
    "劫财": "攻防边界 — 十神子包",
    "食神": "创生输出 — 十神子包",
    "伤官": "破界创新 — 十神子包",
    "正财": "知识固化 — 十神子包",
    "偏财": "奇招演化 — 十神子包",
    "正官": "法度调度 — 十神子包",
    "七杀": "品质裁决 — 十神子包",
    "正印": "滋养守护 — 十神子包",
    "偏印": "桥接通变 — 十神子包"
}

__version__ = "1.0.0"


def __getattr__(name):
    """懒加载子模块和 core"""
    if name == "TenGodCore" or name == "get_core":
        from . import core
        return getattr(core, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# 显式预导入常用符号（避免懒加载开销）
# 注意：先暴露 GOD_NAMES 等基础符号，子模块和 core 通过懒加载按需获取
__all__ = [
    "TenGodCore",
    "get_core",
    "GOD_NAMES",
]
