#!/usr/bin/env python3
"""
test_core_supplement.py — 十神核心调度器补充测试
覆盖 test_core.py 未覆盖的边界条件和分支
"""

import pytest
from tengod.core import Core, TenGodCore, generate_request_id, _Judge, _Scheduler, _Guard, create_app
from fastapi.testclient import TestClient


# ═══════════════════════════════════════════════════════════════════════
# 1. Core.evaluate() 补充测试
# ═══════════════════════════════════════════════════════════════════════

class TestCoreEvaluate:
    """Core.evaluate() 边界条件与分支覆盖"""

    def test_normal_scores_equal_weights(self):
        """正常打分 + 等权重"""
        core = Core()
        result = core.evaluate({"a": 80, "b": 90})
        assert result["total"] == 85.0
        assert result["grade"] == "A"
        assert result["details"]["a"]["weight"] == 0.5
        assert result["details"]["b"]["weight"] == 0.5

    def test_custom_weights(self):
        """自定义权重"""
        core = Core()
        result = core.evaluate({"a": 100, "b": 50}, weights={"a": 0.7, "b": 0.3})
        assert result["total"] == 85.0
        assert result["grade"] == "A"

    def test_empty_scores_returns_f(self):
        """空 scores 返回 F"""
        core = Core()
        result = core.evaluate({})
        assert result["total"] == 0.0
        assert result["grade"] == "F"
        assert result["details"] == {}

    def test_none_weights_auto_calculates(self):
        """weights=None 时自动均分"""
        core = Core()
        result = core.evaluate({"a": 100, "b": 50, "c": 30}, weights=None)
        # 均分权重: 1/3 each
        expected = (100 + 50 + 30) / 3
        assert result["total"] == round(expected, 2)
        for k in ("a", "b", "c"):
            assert result["details"][k]["weight"] == pytest.approx(1.0 / 3)

    def test_grade_s(self):
        """S 级 (>=90)"""
        core = Core()
        result = core.evaluate({"x": 95})
        assert result["grade"] == "S"

    def test_grade_a(self):
        """A 级 (>=80)"""
        core = Core()
        result = core.evaluate({"x": 85})
        assert result["grade"] == "A"

    def test_grade_b(self):
        """B 级 (>=70)"""
        core = Core()
        result = core.evaluate({"x": 75})
        assert result["grade"] == "B"

    def test_grade_c(self):
        """C 级 (>=60)"""
        core = Core()
        result = core.evaluate({"x": 65})
        assert result["grade"] == "C"

    def test_grade_f(self):
        """F 级 (<60)"""
        core = Core()
        result = core.evaluate({"x": 55})
        assert result["grade"] == "F"

    def test_grade_boundary_s(self):
        """S 级边界 90"""
        core = Core()
        result = core.evaluate({"x": 90})
        assert result["grade"] == "S"

    def test_grade_boundary_a(self):
        """A 级边界 80"""
        core = Core()
        result = core.evaluate({"x": 80})
        assert result["grade"] == "A"

    def test_grade_boundary_b(self):
        """B 级边界 70"""
        core = Core()
        result = core.evaluate({"x": 70})
        assert result["grade"] == "B"

    def test_grade_boundary_c(self):
        """C 级边界 60"""
        core = Core()
        result = core.evaluate({"x": 60})
        assert result["grade"] == "C"

    def test_weight_normalization(self):
        """权重和不等于 1 时归一化"""
        core = Core()
        result = core.evaluate({"a": 100, "b": 0}, weights={"a": 2, "b": 2})
        # 归一化后各 0.5，总分 = 50
        assert result["total"] == 50.0
        assert result["details"]["a"]["weight"] == 0.5
        assert result["details"]["b"]["weight"] == 0.5

    def test_missing_keys_in_weights(self):
        """weights 中缺少某些 key"""
        core = Core()
        result = core.evaluate({"a": 100, "b": 50}, weights={"a": 0.8})
        # b 不在 weights 里，normalized.get("b", 0) = 0
        # 归一化: {"a": 1.0}，total = 100*1.0 + 50*0 = 100
        assert result["total"] == 100.0
        assert result["details"]["b"]["weight"] == 0.0

    def test_extra_keys_in_weights(self):
        """weights 中有多余的 key（不在 scores 中）"""
        core = Core()
        # 多余 key 在归一化后权重会被分配，但不影响总分（scores 不包含它）
        result = core.evaluate({"a": 100}, weights={"a": 1, "b": 1})
        # 归一化: a=0.5, b=0.5; total = 100*0.5 = 50
        assert result["total"] == 50.0


# ═══════════════════════════════════════════════════════════════════════
# 2. Core.generate() 补充测试
# ═══════════════════════════════════════════════════════════════════════

class TestCoreGenerate:
    """Core.generate() 各格式分支"""

    def test_format_text(self):
        """format=text 原样返回"""
        core = Core()
        result = core.generate("hello", format="text")
        assert result == "hello"

    def test_format_markdown(self):
        """format=markdown"""
        core = Core()
        result = core.generate("hello", format="markdown")
        assert result == "# hello\n"

    def test_format_html(self):
        """format=html"""
        core = Core()
        result = core.generate("hello", format="html")
        assert result == "<div>hello</div>"

    def test_unknown_format_treated_as_text(self):
        """未知格式按 text 处理"""
        core = Core()
        result = core.generate("hello", format="json")
        assert result == "hello"

    def test_default_format_is_text(self):
        """默认 format=text"""
        core = Core()
        result = core.generate("hello")
        assert result == "hello"


# ═══════════════════════════════════════════════════════════════════════
# 3. Core.innovate() 补充测试
# ═══════════════════════════════════════════════════════════════════════

class TestCoreInnovate:
    """Core.innovate() 各种模式"""

    def test_combine_with_two_args(self):
        """mode=combine + 2 个参数"""
        core = Core()
        result = core.innovate("combine", "AI", "区块链")
        assert result["total"] == 1
        assert result["mode"] == "combine"
        assert result["inputs"] == ["AI", "区块链"]
        assert "融合方案" in result["ideas"][0]

    def test_combine_with_many_args(self):
        """mode=combine + 3+ 个参数"""
        core = Core()
        result = core.innovate("combine", "A", "B", "C")
        assert result["total"] == 1
        assert "A + B" in result["ideas"][0]

    def test_derive_with_one_arg(self):
        """mode=derive + 1 个参数"""
        core = Core()
        result = core.innovate("derive", "AI")
        assert result["total"] == 1
        assert result["mode"] == "derive"
        assert "派生方案" in result["ideas"][0]

    def test_derive_with_multiple_args(self):
        """mode=derive + 多个参数"""
        core = Core()
        result = core.innovate("derive", "A", "B", "C")
        assert result["total"] == 1
        assert "派生方案" in result["ideas"][0]

    def test_unknown_mode_falls_back(self):
        """未知模式回退"""
        core = Core()
        result = core.innovate("unknown", "X", "Y")
        assert result["total"] == 1
        assert result["mode"] == "unknown"
        assert "unknown 模式创新结果" in result["ideas"][0]

    def test_combine_single_arg_falls_back(self):
        """combine 模式只有 1 个参数时回退"""
        core = Core()
        result = core.innovate("combine", "single")
        assert result["total"] == 1
        assert result["mode"] == "combine"
        assert "combine 模式创新结果" in result["ideas"][0]

    def test_empty_args(self):
        """无参数"""
        core = Core()
        result = core.innovate("combine")
        assert result["total"] == 1
        assert result["inputs"] == []
        assert "combine 模式创新结果" in result["ideas"][0]

    def test_derive_no_args(self):
        """derive 模式无参数"""
        core = Core()
        result = core.innovate("derive")
        assert result["total"] == 1
        assert result["inputs"] == []
        assert "derive 模式创新结果" in result["ideas"][0]


# ═══════════════════════════════════════════════════════════════════════
# 4. Core.search() 补充测试
# ═══════════════════════════════════════════════════════════════════════

class TestCoreSearch:
    """Core.search() 各种场景"""

    def test_simple_param_space(self):
        """简单参数空间网格搜索"""
        core = Core()
        result = core.search(
            {"x": [1, 2, 3]},
            lambda p: p["x"] * 10,
            n_trials=10,
        )
        assert result["best_params"]["x"] == 3
        assert result["best_score"] == 30
        assert len(result["trials"]) == 3

    def test_single_parameter(self):
        """单参数网格搜索"""
        core = Core()
        result = core.search(
            {"a": [5, 10, 15]},
            lambda p: p["a"],
            n_trials=10,
        )
        assert result["best_params"]["a"] == 15
        assert result["best_score"] == 15

    def test_n_trials_limits_search(self):
        """n_trials 限制搜索次数"""
        core = Core()
        result = core.search(
            {"x": [1, 2, 3, 4, 5]},
            lambda p: p["x"],
            n_trials=3,
        )
        assert len(result["trials"]) == 3
        assert result["best_params"]["x"] == 3

    def test_objective_raises_exception(self):
        """objective 抛异常时跳过"""
        core = Core()
        def bad_objective(params):
            if params["x"] == 2:
                raise ValueError("bad")
            return params["x"]

        result = core.search(
            {"x": [1, 2, 3]},
            bad_objective,
            n_trials=10,
        )
        assert result["best_params"]["x"] == 3
        assert result["best_score"] == 3
        # 第 2 个 trial 的 score 应为 -inf
        scores = [t["score"] for t in result["trials"]]
        assert scores[1] == float("-inf")

    def test_empty_param_space(self):
        """空参数空间 — itertools.product([]) 产生一个空 tuple，迭代一次"""
        core = Core()
        result = core.search({}, lambda p: 1, n_trials=10)
        # product([]) → [()], 所以迭代一次，params={}, objective({}) → 1
        assert result["best_params"] == {}
        assert result["best_score"] == 1
        assert len(result["trials"]) == 1

    def test_scalar_values(self):
        """非列表值（标量）"""
        core = Core()
        result = core.search(
            {"x": 42, "y": [1, 2]},
            lambda p: p["x"] + p["y"],
            n_trials=10,
        )
        assert result["best_params"]["x"] == 42
        assert result["best_params"]["y"] == 2
        assert result["best_score"] == 44

    def test_maximize_search(self):
        """最大化搜索（默认行为）"""
        core = Core()
        result = core.search(
            {"x": [1, 2, 3]},
            lambda p: p["x"],
            n_trials=10,
        )
        assert result["best_score"] == 3

    def test_multi_param_combinatorial(self):
        """多参数组合搜索"""
        core = Core()
        result = core.search(
            {"x": [1, 2], "y": [10, 20]},
            lambda p: p["x"] * p["y"],
            n_trials=10,
        )
        assert result["best_params"] == {"x": 2, "y": 20}
        assert result["best_score"] == 40
        assert len(result["trials"]) == 4

    def test_all_objectives_raise_exception(self):
        """所有 objective 都抛异常 — 触发 fallback 分支"""
        core = Core()
        result = core.search(
            {"x": [1, 2, 3]},
            lambda p: 1 / 0,  # always raises
            n_trials=10,
        )
        # fallback: best_params = {k: first_value}, best_score = 0.0
        assert result["best_params"] == {"x": 1}
        assert result["best_score"] == 0.0
        assert len(result["trials"]) == 3
        for t in result["trials"]:
            assert t["score"] == float("-inf")


# ═══════════════════════════════════════════════════════════════════════
# 5. Core.export_state() 补充测试
# ═══════════════════════════════════════════════════════════════════════

class TestCoreExportState:
    """Core.export_state() 初始化/未初始化"""

    def test_when_initialized(self):
        """已初始化状态"""
        core = Core()
        core.initialize()
        state = core.export_state()
        assert state["initialized"] is True
        assert state["scheduler"]["status"] == "ready"
        assert state["judge"]["status"] == "ready"
        assert state["guard"]["status"] == "ready"

    def test_when_not_initialized(self):
        """未初始化状态"""
        core = Core()
        state = core.export_state()
        assert state["initialized"] is False
        assert state["scheduler"]["status"] == "pending"
        assert state["judge"]["status"] == "pending"
        assert state["guard"]["status"] == "pending"

    def test_contains_all_keys(self):
        """包含所有必要字段"""
        core = Core()
        state = core.export_state()
        for key in ("name", "version", "build", "initialized", "request_count",
                     "config", "scheduler", "judge", "guard"):
            assert key in state


# ═══════════════════════════════════════════════════════════════════════
# 6. create_app() 测试
# ═══════════════════════════════════════════════════════════════════════

class DummyConfig:
    """模拟配置对象"""
    def __init__(self, enable_cors=False, cors_origins=None):
        self.enable_cors = enable_cors
        self.cors_origins = cors_origins or ["*"]


class TestCreateApp:
    """create_app() FastAPI 应用创建"""

    def test_create_app_without_config(self):
        """create_app 无 config"""
        app = create_app()
        assert app is not None
        assert app.title == "TenGod API"

    def test_create_app_with_cors_enabled(self):
        """create_app enable_cors=True"""
        config = DummyConfig(enable_cors=True)
        app = create_app(config)
        assert app is not None

    def test_create_app_with_cors_disabled(self):
        """create_app enable_cors=False"""
        config = DummyConfig(enable_cors=False)
        app = create_app(config)
        assert app is not None

    def test_health_endpoint(self):
        """健康检查端点"""
        app = create_app()
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "1.5.0"
        assert "timestamp" in data

    def test_root_endpoint(self):
        """根端点"""
        app = create_app()
        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "TenGod API"
        assert data["version"] == "1.5.0"
        assert data["status"] == "running"

    def test_version_endpoint(self):
        """版本端点"""
        app = create_app()
        client = TestClient(app)
        response = client.get("/api/v1/version")
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "1.5.0"
        assert data["build"] == "20250622"
        assert data["author"] == "TenGod Team"


# ═══════════════════════════════════════════════════════════════════════
# 7. TenGodCore 别名
# ═══════════════════════════════════════════════════════════════════════

class TestTenGodCoreAlias:
    """TenGodCore 别名测试"""

    def test_tengodcore_is_core(self):
        """TenGodCore 就是 Core"""
        assert TenGodCore is Core

    def test_tengodcore_instance(self):
        """TenGodCore 实例化"""
        t = TenGodCore()
        assert isinstance(t, Core)
        assert t.name == "TenGod Core"


# ═══════════════════════════════════════════════════════════════════════
# 8. 内部类与常量
# ═══════════════════════════════════════════════════════════════════════

class TestInternalClasses:
    """内部组件 _Judge, _Scheduler, _Guard"""

    def test_judge(self):
        j = _Judge()
        assert j.status == "ready"

    def test_scheduler(self):
        s = _Scheduler()
        assert s.status == "ready"

    def test_guard(self):
        g = _Guard()
        assert g.status == "ready"


class TestCoreConstants:
    """Core 类常量"""

    def test_version(self):
        assert Core.VERSION == "1.5.0"

    def test_build(self):
        assert Core.BUILD == "20250622"

    def test_author(self):
        assert Core.AUTHOR == "TenGod Team"


# ═══════════════════════════════════════════════════════════════════════
# 9. generate_request_id 补充
# ═══════════════════════════════════════════════════════════════════════

class TestGenerateRequestId:
    """generate_request_id 补充"""

    def test_format(self):
        """格式：tgd_ 开头"""
        rid = generate_request_id()
        assert rid.startswith("tgd_")
        assert len(rid) == 4 + 12  # tgd_ + 12 hex

    def test_uniqueness(self):
        """多次调用结果不同"""
        ids = {generate_request_id() for _ in range(100)}
        assert len(ids) == 100