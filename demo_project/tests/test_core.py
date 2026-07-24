#!/usr/bin/env python3
"""
test_core.py — 十神核心调度器集成测试
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# fastapi 可选依赖
try:
    import fastapi
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False


# ==============================================================================
# 辅助函数
# ==============================================================================

def test_generate_request_id():
    """独立函数：generate_request_id"""
    from tengod.core import generate_request_id

    rid = generate_request_id()
    assert rid.startswith("tgd_")
    assert len(rid) == 16  # "tgd_" + 12 hex chars


# ==============================================================================
# 内部组件类
# ==============================================================================

def test_internal_classes():
    """内部组件 _Judge / _Scheduler / _Guard"""
    from tengod.core import _Judge, _Scheduler, _Guard

    j = _Judge()
    assert j.status == "ready"

    s = _Scheduler()
    assert s.status == "ready"

    g = _Guard()
    assert g.status == "ready"


# ==============================================================================
# Core 初始化与信息
# ==============================================================================

def test_core_init():
    """核心初始化测试"""
    from tengod import get_core

    core = get_core()
    assert core.name is not None
    assert core.judge is not None
    assert core.scheduler is not None
    assert core.guard is not None
    assert core.config is not None


def test_core_get_info():
    """get_info 测试"""
    from tengod import get_core

    core = get_core()
    info = core.get_info()
    assert info["version"] == "1.5.0"
    assert info["build"] == "20250622"
    assert info["author"] == "TenGod Team"
    assert "initialized" in info
    assert "request_count" in info


def test_core_initialize():
    """initialize 测试"""
    from tengod.core import Core

    core = Core()
    assert core._initialized is False

    core.initialize()
    assert core._initialized is True

    # 重复初始化不应报错
    core.initialize()
    assert core._initialized is True


def test_core_run():
    """run 测试"""
    from tengod.core import Core

    core = Core()
    result = core.run()
    assert result["version"] == "1.5.0"
    assert result["status"] == "running"
    assert result["init_steps"] == [
        "core_initialized",
        "modules_loaded",
        "api_ready",
    ]


def test_core_process():
    """process 测试"""
    from tengod.core import Core

    core = Core()
    result = core.process("req-001", {"key": "value"})
    assert result["request_id"] == "req-001"
    assert result["status"] == "processed"
    assert result["data"] == {"key": "value"}
    assert "timestamp" in result

    # 请求计数递增
    assert core._request_count == 1
    core.process("req-002", {})
    assert core._request_count == 2


# ==============================================================================
# evaluate —— 质量裁决（全边界）
# ==============================================================================

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


def test_core_evaluate_empty_scores():
    """evaluate：空 scores"""
    from tengod.core import Core

    core = Core()
    result = core.evaluate({})
    assert result["total"] == 0.0
    assert result["grade"] == "F"
    assert result["details"] == {}


def test_core_evaluate_no_weights():
    """evaluate：不传 weights（均分）"""
    from tengod.core import Core

    core = Core()
    result = core.evaluate({"a": 60, "b": 80})
    # 均分 = 70 — grade B
    assert result["total"] == 70.0
    assert result["grade"] == "B"
    assert "a" in result["details"]
    assert "b" in result["details"]


def test_core_evaluate_grade_s():
    """evaluate：grade S (>=90)"""
    from tengod.core import Core

    core = Core()
    result = core.evaluate({"x": 95})
    assert result["grade"] == "S"
    assert result["total"] == 95.0


def test_core_evaluate_grade_a():
    """evaluate：grade A (>=80)"""
    from tengod.core import Core

    core = Core()
    result = core.evaluate({"x": 85})
    assert result["grade"] == "A"


def test_core_evaluate_grade_c():
    """evaluate：grade C (>=60)"""
    from tengod.core import Core

    core = Core()
    result = core.evaluate({"x": 65})
    assert result["grade"] == "C"


def test_core_evaluate_grade_f():
    """evaluate：grade F (<60)"""
    from tengod.core import Core

    core = Core()
    result = core.evaluate({"x": 30})
    assert result["grade"] == "F"


# ==============================================================================
# generate —— 内容生成
# ==============================================================================

def test_core_generate():
    """内容生成测试"""
    from tengod import get_core

    core = get_core()
    md = core.generate("测试", format="markdown")
    assert "测试" in md


def test_core_generate_html():
    """generate：html 格式"""
    from tengod.core import Core

    core = Core()
    result = core.generate("Hello", format="html")
    assert result == "<div>Hello</div>"


def test_core_generate_text_default():
    """generate：默认 text 格式"""
    from tengod.core import Core

    core = Core()
    result = core.generate("Hello")
    assert result == "Hello"


# ==============================================================================
# innovate —— 创新器
# ==============================================================================

def test_core_innovate():
    """创新器测试"""
    from tengod import get_core

    core = get_core()
    report = core.innovate("combine", "AI", "区块链")
    assert report["total"] >= 1


def test_core_innovate_derive():
    """innovate：derive 模式"""
    from tengod.core import Core

    core = Core()
    report = core.innovate("derive", "太极")
    assert report["mode"] == "derive"
    assert report["total"] >= 1
    assert "太极" in report["ideas"][0]


def test_core_innovate_unknown_mode():
    """innovate：未知模式"""
    from tengod.core import Core

    core = Core()
    report = core.innovate("unknown", "A", "B")
    assert report["mode"] == "unknown"
    assert report["ideas"][0] == "unknown 模式创新结果"


def test_core_innovate_combine_single_arg():
    """innovate：combine 模式但只有一个参数"""
    from tengod.core import Core

    core = Core()
    report = core.innovate("combine", "A")
    # 只有一个参数，不满足 len>=2，走 else 分支
    assert report["mode"] == "combine"
    assert report["inputs"] == ["A"]
    assert report["total"] == 1


def test_core_innovate_derive_no_args():
    """innovate：derive 模式但无参数"""
    from tengod.core import Core

    core = Core()
    report = core.innovate("derive")
    assert report["mode"] == "derive"
    assert report["inputs"] == []
    assert report["total"] == 1


# ==============================================================================
# search —— 搜索器
# ==============================================================================

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


def test_core_search_exception_in_objective():
    """search：目标函数抛出异常 —— 触发 fallback 分支"""
    from tengod.core import Core

    core = Core()
    result = core.search(
        {"x": [1, 2]},
        lambda p: (_ for _ in ()).throw(ValueError("boom")),
        n_trials=10,
    )
    # 所有 trial 的 score 都是 -inf，best_params 为 None，触发 fallback:
    # best_params = {k: param_space[k][0]}, best_score = 0.0
    assert "best_params" in result
    assert result["best_score"] == 0.0
    assert result["best_params"] == {"x": 1}


def test_core_search_empty_param_space():
    """search：空参数空间"""
    from tengod.core import Core

    core = Core()
    result = core.search({}, lambda p: 1.0, n_trials=10)
    # itertools.product(*[]) → [()]，循环一次，params={}, score=1.0
    assert result["best_params"] == {}
    assert result["best_score"] == 1.0
    assert len(result["trials"]) == 1


def test_core_search_n_trials_limit():
    """search：n_trials 限制"""
    from tengod.core import Core

    core = Core()
    result = core.search(
        {"x": [1, 2, 3, 4, 5]},
        lambda p: p["x"],
        n_trials=2,
    )
    assert len(result["trials"]) == 2


def test_core_search_non_list_value():
    """search：参数空间包含非列表值"""
    from tengod.core import Core

    core = Core()
    result = core.search(
        {"x": 42, "y": [1, 2]},
        lambda p: p["x"] + p["y"],
        n_trials=10,
    )
    assert len(result["trials"]) == 2  # 1 * 2 = 2 combinations
    assert result["best_params"] is not None


# ==============================================================================
# export_state
# ==============================================================================

def test_core_export_state():
    """状态导出测试"""
    from tengod import get_core

    core = get_core()
    state = core.export_state()
    assert "name" in state
    assert "scheduler" in state
    assert "judge" in state
    assert "config" in state


def test_core_export_state_before_init():
    """export_state：初始化前"""
    from tengod.core import Core

    core = Core()
    state = core.export_state()
    assert state["initialized"] is False
    assert state["scheduler"]["status"] == "pending"
    assert state["judge"]["status"] == "pending"
    assert state["guard"]["status"] == "pending"


def test_core_export_state_after_init():
    """export_state：初始化后"""
    from tengod.core import Core

    core = Core()
    core.initialize()
    state = core.export_state()
    assert state["initialized"] is True
    assert state["scheduler"]["status"] == "ready"
    assert state["judge"]["status"] == "ready"
    assert state["guard"]["status"] == "ready"


# ==============================================================================
# get_core 单例
# ==============================================================================

def test_get_core_singleton():
    """get_core：单例行为"""
    from tengod.core import get_core, Core

    # 重置单例
    import tengod.core as tc
    tc._core_instance = None

    c1 = get_core()
    c2 = get_core()
    assert c1 is c2


def test_core_direct_constructor():
    """Core 直接构造（非单例）"""
    from tengod.core import Core

    c1 = Core()
    c2 = Core()
    assert c1 is not c2
    # 类属性不变
    assert c1.VERSION == "1.5.0"
    assert c1.BUILD == "20250622"
    assert c1.AUTHOR == "TenGod Team"


# ==============================================================================
# create_app
# ==============================================================================

@pytest.mark.skipif(not HAS_FASTAPI, reason="fastapi not installed")
def test_create_app_no_config():
    """create_app：无 config"""
    from tengod.core import create_app

    app = create_app()
    assert app.title == "TenGod API"
    assert app.version == "1.5.0"


@pytest.mark.skipif(not HAS_FASTAPI, reason="fastapi not installed")
def test_create_app_with_cors():
    """create_app：带 CORS config"""
    from tengod.core import create_app

    class Config:
        enable_cors = True
        cors_origins = ["https://example.com"]

    app = create_app(Config())
    assert app.title == "TenGod API"


@pytest.mark.skipif(not HAS_FASTAPI, reason="fastapi not installed")
def test_create_app_with_cors_default_origins():
    """create_app：CORS 开启但无 cors_origins 属性"""
    from tengod.core import create_app

    class Config:
        enable_cors = True

    app = create_app(Config())
    assert app.title == "TenGod API"


@pytest.mark.skipif(not HAS_FASTAPI, reason="fastapi not installed")
def test_create_app_cors_disabled():
    """create_app：CORS 关闭"""
    from tengod.core import create_app

    class Config:
        enable_cors = False

    app = create_app(Config())
    assert app.title == "TenGod API"


@pytest.mark.skipif(not HAS_FASTAPI, reason="fastapi not installed")
def test_create_app_endpoints():
    """create_app：端点存在性"""
    from tengod.core import create_app
    from fastapi.testclient import TestClient

    app = create_app()
    client = TestClient(app)

    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"

    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json()["name"] == "TenGod API"

    resp = client.get("/api/v1/version")
    assert resp.status_code == 200
    assert resp.json()["version"] == "1.5.0"


# ==============================================================================
# 兼容性别名
# ==============================================================================

def test_tengod_core_alias():
    """TenGodCore 别名"""
    from tengod.core import TenGodCore, Core

    assert TenGodCore is Core


# ==============================================================================
# evaluate 补充：权重归一化
# ==============================================================================

def test_core_evaluate_weight_normalization():
    """evaluate：权重非归一化时自动归一"""
    from tengod.core import Core

    core = Core()
    # 权重和为 2，会自动归一化
    result = core.evaluate({"a": 100}, weights={"a": 2.0})
    assert result["total"] == 100.0
    assert result["grade"] == "S"


# ==============================================================================
# 运行入口
# ==============================================================================

if __name__ == "__main__":
    tests = [
        test_generate_request_id,
        test_internal_classes,
        test_core_init,
        test_core_get_info,
        test_core_initialize,
        test_core_run,
        test_core_process,
        test_core_evaluate,
        test_core_evaluate_empty_scores,
        test_core_evaluate_no_weights,
        test_core_evaluate_grade_s,
        test_core_evaluate_grade_a,
        test_core_evaluate_grade_c,
        test_core_evaluate_grade_f,
        test_core_generate,
        test_core_generate_html,
        test_core_generate_text_default,
        test_core_innovate,
        test_core_innovate_derive,
        test_core_innovate_unknown_mode,
        test_core_innovate_combine_single_arg,
        test_core_innovate_derive_no_args,
        test_core_search,
        test_core_search_exception_in_objective,
        test_core_search_empty_param_space,
        test_core_search_n_trials_limit,
        test_core_search_non_list_value,
        test_core_export_state,
        test_core_export_state_before_init,
        test_core_export_state_after_init,
        test_get_core_singleton,
        test_core_direct_constructor,
        test_create_app_no_config,
        test_create_app_with_cors,
        test_create_app_with_cors_default_origins,
        test_create_app_cors_disabled,
        test_create_app_endpoints,
        test_tengod_core_alias,
        test_core_evaluate_weight_normalization,
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
