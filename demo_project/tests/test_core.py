#!/usr/bin/env python3
"""
test_core.py — 十神核心调度器集成测试
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_core_init():
    """核心初始化测试"""
    from tengod import get_core
    core = get_core()
    assert core.name is not None
    assert core.judge is not None
    assert core.scheduler is not None
    assert core.guard is not None
    assert core.config is not None


def test_core_evaluate():
    """质量裁决测试"""
    from tengod import get_core
    core = get_core()

    result = core.evaluate(
        {"功能": 90, "质量": 85, "测试": 80},
        weights={"功能": 0.5, "质量": 0.3, "测试": 0.2},
    )
    assert result["total"] > 80
    assert result["grade"] in ("A", "S")


def test_core_generate():
    """内容生成测试"""
    from tengod import get_core
    core = get_core()
    md = core.generate("测试", format="markdown")
    assert "测试" in md


def test_core_innovate():
    """创新器测试"""
    from tengod import get_core
    core = get_core()
    report = core.innovate("combine", "AI", "区块链")
    assert report["total"] >= 1


def test_core_search():
    """搜索器测试"""
    from tengod import get_core
    core = get_core()
    result = core.search(
        {"x": [1, 2, 3]},
        lambda p: -((p["x"] - 2) ** 2),
        n_trials=3,
    )
    assert result["best_params"]["x"] in (1, 2, 3)


def test_core_export_state():
    """状态导出测试"""
    from tengod import get_core
    core = get_core()
    state = core.export_state()
    assert "name" in state
    assert "scheduler" in state
    assert "judge" in state
    assert "config" in state


if __name__ == "__main__":
    tests = [
        test_core_init,
        test_core_evaluate,
        test_core_generate,
        test_core_innovate,
        test_core_search,
        test_core_export_state,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            print(f"✅ {test.__name__}")
            passed += 1
        except Exception as e:
            print(f"❌ {test.__name__}: {e}")
            failed += 1

    print(f"\n总计: {passed} 通过, {failed} 失败")
    sys.exit(0 if failed == 0 else 1)
