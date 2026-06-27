#!/usr/bin/env python3
"""
test_core.py — 十神核心调度器集成测试
"""

import os
import sys

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


def test_generate_request_id():
    """generate_request_id 函数测试"""
    from tengod.core import generate_request_id

    rid = generate_request_id()
    assert rid.startswith("tgd_")
    assert len(rid) == 16  # "tgd_" + 12 hex chars


def test_core_initialize():
    """初始化测试"""
    from tengod.core import Core

    core = Core()
    assert core._initialized is False
    core.initialize()
    assert core._initialized is True


def test_core_initialize_twice():
    """重复初始化测试（early return 分支）"""
    from tengod.core import Core

    core = Core()
    core.initialize()
    # 第二次调用应该走 early return 分支
    core.initialize()
    assert core._initialized is True


def test_core_run():
    """run() 方法测试"""
    from tengod.core import Core

    core = Core()
    result = core.run()
    assert result["version"] == "1.5.0"
    assert result["status"] == "running"
    assert "init_steps" in result


def test_core_get_info():
    """get_info() 方法测试"""
    from tengod import get_core

    core = get_core()
    info = core.get_info()
    assert "version" in info
    assert "initialized" in info
    assert "request_count" in info


def test_core_process():
    """process() 方法测试"""
    from tengod import get_core

    core = get_core()
    result = core.process("req_001", {"key": "value"})
    assert result["request_id"] == "req_001"
    assert result["status"] == "processed"
    assert result["data"] == {"key": "value"}


def test_core_evaluate_empty():
    """evaluate() 空输入测试"""
    from tengod import get_core

    core = get_core()
    result = core.evaluate({})
    assert result["total"] == 0.0
    assert result["grade"] == "F"
    assert result["details"] == {}


def test_core_evaluate_no_weights():
    """evaluate() 无权重测试（均分）"""
    from tengod import get_core

    core = get_core()
    result = core.evaluate({"a": 80, "b": 90})
    assert result["total"] == 85.0
    assert result["grade"] == "A"


def test_core_evaluate_grade_s():
    """evaluate() S 级测试"""
    from tengod import get_core

    core = get_core()
    result = core.evaluate({"x": 95})
    assert result["grade"] == "S"
    assert result["total"] == 95.0


def test_core_evaluate_grade_b():
    """evaluate() B 级测试"""
    from tengod import get_core

    core = get_core()
    result = core.evaluate({"x": 75})
    assert result["grade"] == "B"
    assert result["total"] == 75.0


def test_core_evaluate_grade_c():
    """evaluate() C 级测试"""
    from tengod import get_core

    core = get_core()
    result = core.evaluate({"x": 65})
    assert result["grade"] == "C"
    assert result["total"] == 65.0


def test_core_evaluate_grade_f():
    """evaluate() F 级测试"""
    from tengod import get_core

    core = get_core()
    result = core.evaluate({"x": 50})
    assert result["grade"] == "F"
    assert result["total"] == 50.0


def test_core_generate_html():
    """generate() HTML 格式测试"""
    from tengod import get_core

    core = get_core()
    result = core.generate("Hello", format="html")
    assert result == "<div>Hello</div>"


def test_core_generate_text():
    """generate() 默认格式测试"""
    from tengod import get_core

    core = get_core()
    result = core.generate("Hello", format="text")
    assert result == "Hello"


def test_core_innovate_derive():
    """innovate() derive 模式测试"""
    from tengod import get_core

    core = get_core()
    report = core.innovate("derive", "AI")
    assert report["mode"] == "derive"
    assert report["total"] >= 1
    assert "派生方案" in report["ideas"][0]


def test_core_innovate_unknown():
    """innovate() 未知模式 fallback 测试"""
    from tengod import get_core

    core = get_core()
    report = core.innovate("unknown_mode")
    assert report["mode"] == "unknown_mode"
    assert report["total"] == 1
    assert "模式创新结果" in report["ideas"][0]


def test_core_search_exception():
    """search() 目标函数异常测试（部分成功，部分异常）"""
    from tengod import get_core

    core = get_core()
    result = core.search(
        {"x": [1, 2]},
        lambda p: 1 / 0 if p["x"] == 1 else p["x"],  # x=1 抛异常，x=2 正常
        n_trials=5,
    )
    assert result["best_score"] == 2.0
    assert result["best_params"] == {"x": 2}
    assert len(result["trials"]) == 2


def test_core_search_best_params_fallback():
    """search() best_params=None 回退测试"""
    from tengod import get_core

    core = get_core()
    # 所有目标函数都抛异常，best_params 保持 None，触发 fallback
    result = core.search(
        {"x": [1]},
        lambda p: 1 / 0,
        n_trials=5,
    )
    # fallback 分支：best_params 被设为第一个值
    assert result["best_params"] == {"x": 1}
    assert result["best_score"] == 0.0


def test_core_export_state_initialized():
    """export_state() 已初始化状态测试"""
    from tengod.core import Core

    core = Core()
    core.initialize()
    state = core.export_state()
    assert state["scheduler"]["status"] == "ready"
    assert state["judge"]["status"] == "ready"
    assert state["guard"]["status"] == "ready"
    assert state["initialized"] is True


def test_create_app_basic():
    """create_app() 基础测试（mock FastAPI）"""
    from unittest.mock import patch, MagicMock

    mock_fastapi = MagicMock()
    mock_cors = MagicMock()

    with patch.dict("sys.modules", {"fastapi": MagicMock(), "fastapi.middleware.cors": MagicMock()}):
        import fastapi
        import fastapi.middleware.cors
        fastapi.FastAPI = mock_fastapi
        fastapi.middleware.cors.CORSMiddleware = mock_cors

        from tengod.core import create_app
        app = create_app()
        mock_fastapi.assert_called_once()
        # CORS 默认不启用（config 为 None）
        mock_cors.assert_not_called()


def test_create_app_with_cors():
    """create_app() 带 CORS 配置测试"""
    from unittest.mock import patch, MagicMock

    mock_fastapi = MagicMock()
    mock_app_instance = MagicMock()
    mock_fastapi.return_value = mock_app_instance
    mock_cors = MagicMock()

    class MockConfig:
        enable_cors = True
        cors_origins = ["http://example.com"]

    with patch.dict("sys.modules", {"fastapi": MagicMock(), "fastapi.middleware.cors": MagicMock()}):
        import fastapi
        import fastapi.middleware.cors
        fastapi.FastAPI = mock_fastapi
        fastapi.middleware.cors.CORSMiddleware = mock_cors

        from tengod.core import create_app
        app = create_app(config=MockConfig())
        mock_fastapi.assert_called_once()
        mock_app_instance.add_middleware.assert_called_once()


if __name__ == "__main__":
    tests = [
        test_core_init,
        test_core_evaluate,
        test_core_generate,
        test_core_innovate,
        test_core_search,
        test_core_export_state,
        test_generate_request_id,
        test_core_initialize,
        test_core_initialize_twice,
        test_core_run,
        test_core_get_info,
        test_core_process,
        test_core_evaluate_empty,
        test_core_evaluate_no_weights,
        test_core_evaluate_grade_s,
        test_core_evaluate_grade_b,
        test_core_evaluate_grade_c,
        test_core_evaluate_grade_f,
        test_core_generate_html,
        test_core_generate_text,
        test_core_innovate_derive,
        test_core_innovate_unknown,
        test_core_search_exception,
        test_core_search_best_params_fallback,
        test_core_export_state_initialized,
        test_create_app_basic,
        test_create_app_with_cors,
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
