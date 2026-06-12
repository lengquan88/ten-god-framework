#!/usr/bin/env python3
"""
test_tengod.py — 十神子模块单元测试
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tengod"))


def test_bijian_registry():
    """比肩_架构协同：组件注册中心测试"""
    from 比肩_架构协同 import component, get_registry

    registry = get_registry()

    @component("test_comp")
    class TestComp:
        pass

    assert registry.has("test_comp")
    comp = registry.get("test_comp")
    assert isinstance(comp, type)


def test_jiecai_guard():
    """劫财_攻防边界：权限守护器测试"""
    from 劫财_攻防边界 import Guard, Permission

    guard = Guard()
    guard.register_role("admin", {Permission.READ, Permission.WRITE, Permission.ADMIN})
    guard.register_role("viewer", {Permission.READ})

    admin = guard.create_context("u1", roles=["admin"])
    viewer = guard.create_context("u2", roles=["viewer"])

    assert guard.check(admin, Permission.DELETE) is True
    assert guard.check(viewer, Permission.WRITE) is False
    assert guard.check(admin, Permission.READ) is True


def test_shishen_generator():
    """食神_创生输出：内容生成器测试"""
    from 食神_创生输出 import ContentGenerator, GenerationConfig, OutputFormat

    gen = ContentGenerator(name="test")
    config = GenerationConfig(format=OutputFormat.MARKDOWN)

    result1 = gen.generate("Hello", config)
    result2 = gen.generate("Hello", config)

    # 缓存命中
    assert result1 == result2
    assert "Hello" in result1
    assert len(gen.get_history()) == 2


def test_shangguan_innovator():
    """伤官_破界创新：创新器测试"""
    from 伤官_破界创新 import Innovator, InnovationType

    inv = Innovator()
    idea = inv.combine(["A", "B", "C"])
    assert idea.innovation_type == InnovationType.COMBINATION
    assert 0.0 <= idea.score <= 1.0
    assert len(inv.top_ideas()) >= 1


def test_zhengcai_kb():
    """正财_知识固化：知识库测试"""
    from 正财_知识固化 import KnowledgeBase

    kb = KnowledgeBase()
    a = kb.add_node("A", node_type="concept")
    b = kb.add_node("B", node_type="concept")

    edge = kb.add_edge(a.id, b.id, "relates", weight=0.8)
    assert edge is not None

    neighbors = kb.neighbors(a.id, "relates")
    assert len(neighbors) == 1
    assert neighbors[0].id == b.id

    stats = kb.stats()
    assert stats["nodes"] == 2
    assert stats["edges"] == 1


def test_piancai_optimizer():
    """偏财_奇招演化：搜索优化器测试"""
    from 偏财_奇招演化 import SearchOptimizer, SearchSpace

    space = SearchSpace({"x": [1, 2, 3, 4, 5]})

    def obj(p):
        return -((p["x"] - 3) ** 2)

    opt = SearchOptimizer(space, mode="grid")
    result = opt.optimize(obj, n_trials=5, maximize=True)
    assert result.best_params["x"] == 3
    assert result.best_score == 0


def test_zhengguan_scheduler():
    """正官_法度调度：任务调度器测试"""
    from 正官_法度调度 import TaskScheduler, TaskPriority, TaskStatus

    scheduler = TaskScheduler(max_workers=2)

    def my_task():
        return 42

    task = scheduler.submit("t1", my_task, priority=TaskPriority.HIGH)
    assert task.priority == TaskPriority.HIGH

    scheduler.run_all()
    assert scheduler.get_status("t1") == TaskStatus.COMPLETED


def test_zhengguan_router():
    """正官_法度调度：API 路由测试"""
    from 正官_法度调度 import APIRouter

    router = APIRouter(prefix="/api")

    @router.get("/hello")
    def hello():
        return "world"

    result = router.dispatch("/hello", "GET")
    assert result == "world"
    assert any(r["path"] == "/api/hello" for r in router.list_routes())


def test_qisha_judge():
    """七杀_品质裁决：质量裁决器测试"""
    from 七杀_品质裁决 import QualityJudge, Grade

    judge = QualityJudge()
    judge.add_score("功能", 95, weight=0.5)
    judge.add_score("质量", 90, weight=0.5)
    assert judge.grade() == Grade.S
    assert judge.total_weighted() == 92.5

    judge.reset()
    judge.add_score("功能", 50, weight=1.0)
    assert judge.grade() == Grade.D


def test_qisha_runner():
    """七杀_品质裁决：测试运行器测试"""
    from 七杀_品质裁决 import TestRunner, TestStatus

    runner = TestRunner(verbose=False)

    def passing_test():
        assert 1 + 1 == 2

    def failing_test():
        assert 1 + 1 == 3

    runner.add_case("pass", passing_test)
    runner.add_case("fail", failing_test)
    runner.run()

    summary = runner.summary()
    assert summary["total"] == 2
    assert summary["passed"] == 1
    assert summary["failed"] == 1


def test_zhengyin_config():
    """正印_滋养守护：配置管理器测试"""
    from 正印_滋养守护 import ConfigManager

    cm = ConfigManager()
    cm.set_default("workers", 4)
    cm.set("workers", 8)
    assert cm.get("workers") == 8
    assert cm.get_info("workers").source.value == "override"


def test_pianyin_adapter():
    """偏印_桥接通变：协议适配器测试"""
    from 偏印_桥接通变 import Adapter, DictToJsonConverter, CamelToSnakeConverter

    json_conv = DictToJsonConverter()
    adapter = Adapter("json", json_conv)

    data = {"k": "v"}
    json_str = adapter.convert(data, direction="to")
    back = adapter.convert(json_str, direction="from")
    assert back == data

    cs = CamelToSnakeConverter()
    snake = cs.from_source({"userName": "alice"})
    assert "user_name" in snake


if __name__ == "__main__":
    tests = [
        test_bijian_registry,
        test_jiecai_guard,
        test_shishen_generator,
        test_shangguan_innovator,
        test_zhengcai_kb,
        test_piancai_optimizer,
        test_zhengguan_scheduler,
        test_zhengguan_router,
        test_qisha_judge,
        test_qisha_runner,
        test_zhengyin_config,
        test_pianyin_adapter,
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
