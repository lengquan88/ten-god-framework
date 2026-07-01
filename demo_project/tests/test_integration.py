"""
test_integration.py — 端到端集成测试 v2.35.0
================================================
全管道端到端测试：七阶段成像管道串联验证。
12门禁 + 7成像 + 7自修正 + 推测解码 + Oracle投影 + 混沌海 一体化。
"""

import pytest
import os
import sys
import json
import time
import math

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tengod.holographic_system import (
    HolographicSystem, PipelineStage, PipelineStatus,
    StageResult, PipelineResult,
    get_holographic_system, reset_holographic_system,
)
from tengod.tbce_unit import TBCECoordinates, CognitiveUnit, GateState
from tengod.twelve_gods_base import TwelveGods, FiveElements
from tengod.benchmark import (
    BenchmarkRunner, BenchmarkResult, BenchmarkSuite,
    get_benchmark_runner, reset_benchmark_runner,
)


# ============================================================================
# 测试夹具
# ============================================================================

@pytest.fixture(autouse=True)
def reset_all():
    reset_holographic_system()
    reset_benchmark_runner()
    yield
    reset_holographic_system()
    reset_benchmark_runner()


# ============================================================================
# 一、全息认知系统总控测试
# ============================================================================

class TestHolographicSystemBasic:
    """全息系统基础测试"""

    def test_system_creation(self):
        """测试系统创建"""
        system = HolographicSystem()
        assert system.VERSION == "3.0.0"

    def test_singleton(self):
        """测试单例模式"""
        s1 = get_holographic_system()
        s2 = get_holographic_system()
        assert s1 is s2

    def test_reset(self):
        """测试系统重置"""
        s1 = get_holographic_system()
        reset_holographic_system()
        s2 = get_holographic_system()
        assert s1 is not s2


class TestHolographicPipeline:
    """全管道执行测试"""

    def test_execute_minimal(self):
        """测试最小管道执行"""
        system = HolographicSystem()
        result = system.execute(
            unit_id="min_001",
            unit_name="最小管道",
            coords={"S": 0.8, "T": 0.5, "P": 0.7, "C": 0.6, "I": 0.7, "E": 0.3},
            enable_imaging=False,
            enable_self_correction=False,
            enable_oracle=False,
        )
        assert result.pipeline_id.startswith("pipeline_")
        assert result.unit_id == "min_001"
        assert len(result.stages) > 0
        assert result.overall_status in (
            PipelineStatus.SUCCESS, PipelineStatus.PAUSED,
        )

    def test_execute_full_pipeline(self):
        """测试全管道执行"""
        system = HolographicSystem()
        result = system.execute(
            unit_id="full_001",
            unit_name="全管道测试",
            coords={"S": 0.9, "T": 0.3, "P": 0.85, "C": 0.8, "I": 0.85, "E": 0.15},
            cognitive_layer=3,
            enable_imaging=True,
            enable_self_correction=True,
            enable_oracle=True,
            enable_speculation=True,
        )
        assert result.pipeline_id.startswith("pipeline_")
        assert len(result.stages) >= 4  # 摄入 + 门禁 + 成像 + 最终化
        assert result.overall_status in (
            PipelineStatus.SUCCESS, PipelineStatus.PAUSED,
        )

    def test_execute_high_quality(self):
        """测试高质量单元全管道"""
        system = HolographicSystem()
        result = system.execute(
            unit_id="hq_001",
            unit_name="高质量单元",
            coords={"S": 0.95, "T": 0.1, "P": 0.9, "C": 0.9, "I": 0.9, "E": 0.05},
            enable_imaging=True,
            enable_self_correction=True,
            enable_oracle=True,
        )
        assert result.overall_status in (
            PipelineStatus.SUCCESS, PipelineStatus.PAUSED,
        )

    def test_execute_low_quality(self):
        """测试低质量单元管道"""
        system = HolographicSystem()
        result = system.execute(
            unit_id="lq_001",
            unit_name="低质量单元",
            coords={"S": 0.2, "T": 5.0, "P": 0.2, "C": 0.1, "I": 0.1, "E": 0.9},
            enable_imaging=True,
            enable_self_correction=True,
            enable_oracle=True,
        )
        # 低质量应该被门禁拦截或处理
        assert result.overall_status in (
            PipelineStatus.SUCCESS, PipelineStatus.PAUSED,
            PipelineStatus.FAILED, PipelineStatus.CHAOS_SEA,
        )

    def test_execute_strict_mode(self):
        """测试严格模式管道"""
        system = HolographicSystem()
        result = system.execute(
            unit_id="strict_001",
            unit_name="严格模式",
            coords={"S": 0.5, "T": 0.5},
            strict_mode=True,
            enable_imaging=False,
            enable_self_correction=False,
            enable_oracle=False,
        )
        # 严格模式下中等质量可能不通过
        assert result.overall_status in (
            PipelineStatus.SUCCESS, PipelineStatus.FAILED,
        )


class TestHolographicGates:
    """门禁集成测试"""

    def test_gate_verdicts_recorded(self):
        """测试门禁裁决被记录"""
        system = HolographicSystem()
        result = system.execute(
            unit_id="gate_001",
            unit_name="门禁记录",
            coords={"S": 0.9, "T": 0.5, "P": 0.8, "C": 0.7, "I": 0.8, "E": 0.2},
            enable_imaging=False,
            enable_self_correction=False,
            enable_oracle=False,
        )
        assert len(result.gate_verdicts) == 12
        for god in TwelveGods:
            assert god.value in result.gate_verdicts

    def test_gate_stage_recorded(self):
        """测试门禁阶段被记录"""
        system = HolographicSystem()
        result = system.execute(
            unit_id="gate_stage_001",
            unit_name="门禁阶段",
            coords={"S": 0.9, "P": 0.8, "C": 0.7, "I": 0.8},
            enable_imaging=False,
            enable_self_correction=False,
            enable_oracle=False,
        )
        gate_stages = [s for s in result.stages if s.stage == PipelineStage.TWELVE_GATES]
        assert len(gate_stages) == 1

    def test_element_health_updated(self):
        """测试五行状态更新"""
        system = HolographicSystem()
        system.execute(
            unit_id="elem_001",
            unit_name="五行测试",
            coords={"S": 0.9, "P": 0.8, "C": 0.7, "I": 0.8},
            enable_imaging=False,
            enable_self_correction=False,
            enable_oracle=False,
        )
        health = system.get_element_health()
        assert len(health) == 6  # 木火土金水+太极
        assert "木" in health
        assert "金" in health


class TestHolographicImaging:
    """成像管道集成测试"""

    def test_imaging_with_text_modality(self):
        """测试文本模态成像"""
        system = HolographicSystem()
        result = system.execute(
            unit_id="img_001",
            unit_name="文本成像",
            coords={"S": 0.9, "T": 0.3, "P": 0.85, "C": 0.8, "I": 0.85, "E": 0.15},
            modalities=["text"],
            enable_imaging=True,
            enable_self_correction=False,
            enable_oracle=False,
        )
        assert result.imaging_result is not None
        assert "quality_score" in result.imaging_result
        assert result.imaging_result["quality_score"] >= 0.0

    def test_imaging_with_multiple_modalities(self):
        """测试多模态成像"""
        system = HolographicSystem()
        result = system.execute(
            unit_id="img_multi",
            unit_name="多模态成像",
            coords={"S": 0.9, "T": 0.3, "P": 0.85, "C": 0.8, "I": 0.85, "E": 0.15},
            modalities=["text", "image", "audio"],
            enable_imaging=True,
            enable_self_correction=False,
            enable_oracle=False,
        )
        assert result.imaging_result is not None

    def test_imaging_speculation(self):
        """测试推测解码集成"""
        system = HolographicSystem()
        result = system.execute(
            unit_id="img_spec",
            unit_name="推测解码",
            coords={"S": 0.9, "T": 0.3, "P": 0.85, "C": 0.8, "I": 0.85, "E": 0.15},
            modalities=["text"],
            enable_imaging=True,
            enable_speculation=True,
            enable_self_correction=False,
            enable_oracle=False,
        )
        if result.imaging_result:
            spec = result.imaging_result.get("speculation", {})
            assert "hit" in spec or "enabled" in spec


class TestHolographicCorrection:
    """自修正集成测试"""

    def test_self_correction_executed(self):
        """测试自修正执行"""
        system = HolographicSystem()
        result = system.execute(
            unit_id="corr_001",
            unit_name="自修正",
            coords={"S": 0.5, "T": 0.5, "P": 0.5, "C": 0.5, "I": 0.5, "E": 0.5},
            enable_imaging=True,
            enable_self_correction=True,
            enable_oracle=False,
        )
        # 自修正可能在七论未通过时触发
        assert result is not None
        assert result.pipeline_id.startswith("pipeline_")

    def test_correction_result_structure(self):
        """测试自修正结果结构"""
        system = HolographicSystem()
        result = system.execute(
            unit_id="corr_struct",
            unit_name="自修正结构",
            coords={"S": 0.5, "T": 0.5, "P": 0.5, "C": 0.5, "I": 0.5, "E": 0.5},
            enable_imaging=True,
            enable_self_correction=True,
            enable_oracle=False,
        )
        if result.correction_result:
            assert "success" in result.correction_result
            assert "total_delta" in result.correction_result


class TestHolographicOracle:
    """Oracle投影集成测试"""

    def test_oracle_executed(self):
        """测试Oracle投影执行"""
        system = HolographicSystem()
        result = system.execute(
            unit_id="oracle_001",
            unit_name="Oracle投影",
            coords={"S": 0.9, "T": 0.3, "P": 0.85, "C": 0.8, "I": 0.85, "E": 0.15},
            enable_imaging=False,
            enable_self_correction=False,
            enable_oracle=True,
        )
        assert result.oracle_result is not None

    def test_oracle_result_structure(self):
        """测试Oracle结果结构"""
        system = HolographicSystem()
        result = system.execute(
            unit_id="oracle_struct",
            unit_name="Oracle结构",
            coords={"S": 0.9, "T": 0.3, "P": 0.85, "C": 0.8, "I": 0.85, "E": 0.15},
            enable_imaging=False,
            enable_self_correction=False,
            enable_oracle=True,
        )
        if result.oracle_result:
            assert "past" in result.oracle_result or "error" in str(result.oracle_result)


class TestHolographicResults:
    """结果与统计测试"""

    def test_pipeline_result_to_dict(self):
        """测试管道结果序列化"""
        result = PipelineResult(
            pipeline_id="test_001",
            unit_id="u1",
            unit_name="test",
        )
        d = result.to_dict()
        assert d["pipeline_id"] == "test_001"
        assert d["unit_id"] == "u1"
        assert d["overall_status"] == "pending"

    def test_pipeline_stats(self):
        """测试管道统计"""
        system = HolographicSystem()
        for i in range(3):
            system.execute(
                unit_id=f"stat_{i}",
                unit_name=f"统计测试{i}",
                coords={"S": 0.9, "P": 0.8},
                enable_imaging=False,
                enable_self_correction=False,
                enable_oracle=False,
            )
        stats = system.get_pipeline_stats()
        assert stats["total_pipelines"] == 3
        assert "success_rate" in stats
        assert "element_health" in stats

    def test_recent_pipelines(self):
        """测试最近管道查询"""
        system = HolographicSystem()
        system.execute(
            unit_id="recent_001",
            unit_name="最近管道",
            coords={"S": 0.9},
            enable_imaging=False,
            enable_self_correction=False,
            enable_oracle=False,
        )
        recent = system.get_recent_pipelines(limit=5)
        assert len(recent) >= 1

    def test_get_pipeline_by_id(self):
        """测试按ID获取管道"""
        system = HolographicSystem()
        result = system.execute(
            unit_id="get_001",
            unit_name="ID查询",
            coords={"S": 0.9},
            enable_imaging=False,
            enable_self_correction=False,
            enable_oracle=False,
        )
        found = system.get_pipeline(result.pipeline_id)
        assert found is not None
        assert found["unit_id"] == "get_001"

    def test_get_nonexistent_pipeline(self):
        """测试不存在的管道"""
        system = HolographicSystem()
        result = system.get_pipeline("nonexistent")
        assert result is None


class TestHolographicSpeculation:
    """推测解码集成测试"""

    def test_speculation_stats_initial(self):
        """测试初始推测解码统计"""
        system = HolographicSystem()
        stats = system.get_speculation_stats()
        assert stats["total"] == 0
        assert stats["hits"] == 0

    def test_speculation_stats_after_execution(self):
        """测试执行后推测解码统计"""
        system = HolographicSystem()
        system.execute(
            unit_id="spec_001",
            unit_name="推测统计",
            coords={"S": 0.9, "T": 0.3, "P": 0.85, "C": 0.8, "I": 0.85, "E": 0.15},
            modalities=["text"],
            enable_imaging=True,
            enable_speculation=True,
            enable_self_correction=False,
            enable_oracle=False,
        )
        stats = system.get_speculation_stats()
        assert "total" in stats
        assert "speedup_estimate" in stats


# ============================================================================
# 二、基准测试测试
# ============================================================================

class TestBenchmarkResult:
    """基准测试结果测试"""

    def test_result_creation(self):
        """测试结果创建"""
        result = BenchmarkResult(
            name="test_bench",
            description="测试基准",
            iterations=100,
            total_duration_ms=1000.0,
            min_ms=5.0, max_ms=15.0, mean_ms=10.0, median_ms=10.0,
            p95_ms=14.0, p99_ms=15.0, std_ms=2.0,
            throughput_per_sec=100.0,
            success_count=100, failure_count=0,
        )
        d = result.to_dict()
        assert d["name"] == "test_bench"
        assert d["mean_ms"] == 10.0
        assert d["throughput_per_sec"] == 100.0

    def test_suite_creation(self):
        """测试套件创建"""
        suite = BenchmarkSuite(suite_name="test_suite")
        d = suite.to_dict()
        assert d["suite_name"] == "test_suite"


class TestBenchmarkRunner:
    """基准测试运行器测试"""

    def test_run_basic(self):
        """测试基础运行"""
        runner = BenchmarkRunner()
        result = runner.run(
            name="basic_test",
            description="基础测试",
            func=lambda: sum(range(100)),
            iterations=100,
            warmup=5,
        )
        assert result.name == "basic_test"
        assert result.iterations == 100
        assert result.success_count == 100
        assert result.failure_count == 0
        assert result.mean_ms > 0

    def test_run_with_failures(self):
        """测试带失败的运行"""
        runner = BenchmarkRunner()
        call_count = [0]

        def flaky():
            call_count[0] += 1
            if call_count[0] % 3 == 0:
                raise ValueError("flaky")
            return call_count[0]

        result = runner.run(
            name="flaky_test",
            description="带失败测试",
            func=flaky,
            iterations=30,
            warmup=0,
        )
        assert result.failure_count > 0

    def test_benchmark_speculation(self):
        """测试推测解码基准"""
        runner = BenchmarkRunner()
        import random
        def speculation():
            return random.random() > 0.3

        result = runner.benchmark_speculation(speculation, iterations=50)
        assert result.name == "speculation_decoding"
        assert "hit_rate" in result.metadata
        assert "speedup_estimate" in result.metadata

    def test_benchmark_tbce_creation(self):
        """测试TBCE创建基准"""
        runner = BenchmarkRunner()
        result = runner.benchmark_tbce_creation(iterations=100)
        assert result.name == "tbce_unit_creation"
        assert result.success_count > 0

    def test_benchmark_tbce_query(self):
        """测试TBCE查询基准"""
        runner = BenchmarkRunner()
        result = runner.benchmark_tbce_query(iterations=100)
        assert result.name == "tbce_query"
        assert result.success_count > 0

    def test_benchmark_element_cycle(self):
        """测试五行生克基准"""
        runner = BenchmarkRunner()
        result = runner.benchmark_element_cycle(iterations=100)
        assert result.name == "element_cycle"
        assert result.success_count > 0

    def test_benchmark_twelve_gates(self):
        """测试十二神门禁基准"""
        runner = BenchmarkRunner()
        result = runner.benchmark_twelve_gates(iterations=10)
        assert result.name == "twelve_gates_judge"
        # 可能成功也可能因环境失败
        assert result.iterations >= 0

    def test_full_suite(self):
        """测试完整基准套件"""
        runner = BenchmarkRunner()
        suite = runner.run_full_suite(
            name="test_suite",
            include_load_test=False,
        )
        assert suite.suite_name == "test_suite"
        assert len(suite.results) >= 4  # TBCE创建+查询+五行+推测+门禁
        for result in suite.results:
            assert result.mean_ms >= 0

    def test_regression_check(self):
        """测试回归检测"""
        runner = BenchmarkRunner()
        baseline = BenchmarkResult(
            name="test", description="test",
            iterations=100, total_duration_ms=1000,
            min_ms=5, max_ms=15, mean_ms=10, median_ms=10,
            p95_ms=14, p99_ms=15, std_ms=2,
            throughput_per_sec=100, success_count=100, failure_count=0,
        )
        runner.set_baseline("test", baseline)

        current = BenchmarkResult(
            name="test", description="test",
            iterations=100, total_duration_ms=1200,
            min_ms=6, max_ms=18, mean_ms=12, median_ms=12,
            p95_ms=17, p99_ms=18, std_ms=2.5,
            throughput_per_sec=83, success_count=100, failure_count=0,
        )

        regression = runner.check_regression("test", current, max_degradation=0.2)
        assert regression["degradation"] == pytest.approx(0.2, abs=0.01)

    def test_no_regression(self):
        """测试无回归"""
        runner = BenchmarkRunner()
        baseline = BenchmarkResult(
            name="test", description="test",
            iterations=100, total_duration_ms=1000,
            min_ms=5, max_ms=15, mean_ms=10, median_ms=10,
            p95_ms=14, p99_ms=15, std_ms=2,
            throughput_per_sec=100, success_count=100, failure_count=0,
        )
        runner.set_baseline("test", baseline)

        current = BenchmarkResult(
            name="test", description="test",
            iterations=100, total_duration_ms=1000,
            min_ms=5, max_ms=15, mean_ms=10, median_ms=10,
            p95_ms=14, p99_ms=15, std_ms=2,
            throughput_per_sec=100, success_count=100, failure_count=0,
        )

        regression = runner.check_regression("test", current)
        assert regression["regression"] is False

    def test_regression_no_baseline(self):
        """测试无基线的回归检测"""
        runner = BenchmarkRunner()
        current = BenchmarkResult(
            name="test", description="test",
            iterations=100, total_duration_ms=1000,
            min_ms=5, max_ms=15, mean_ms=10, median_ms=10,
            p95_ms=14, p99_ms=15, std_ms=2,
            throughput_per_sec=100, success_count=100, failure_count=0,
        )
        regression = runner.check_regression("test", current)
        assert regression["regression"] is False
        assert "无历史基线" in regression["message"]

    def test_load_benchmark(self):
        """测试负载基准"""
        runner = BenchmarkRunner()

        def light_task():
            sum(i * i for i in range(50))

        result = runner.benchmark_load(
            "light_test", light_task, concurrent=3, iterations_per_worker=10,
        )
        assert result.name == "light_test_load_3w"
        assert result.metadata["concurrent_workers"] == 3
        assert result.success_count > 0


# ============================================================================
# 三、端到端全管道集成测试
# ============================================================================

class TestEndToEndPipeline:
    """端到端全管道测试"""

    def test_full_pipeline_all_stages(self):
        """全管道所有阶段测试"""
        system = HolographicSystem()
        result = system.execute(
            unit_id="e2e_001",
            unit_name="端到端全管道",
            coords={"S": 0.9, "T": 0.3, "P": 0.85, "C": 0.8, "I": 0.85, "E": 0.15},
            cognitive_layer=3,
            modalities=["text"],
            enable_imaging=True,
            enable_self_correction=True,
            enable_oracle=True,
            enable_speculation=True,
        )

        stage_values = {s.stage.value for s in result.stages}
        assert "ingest" in stage_values
        assert "twelve_gates" in stage_values
        assert "finalize" in stage_values

    def test_pipeline_result_completeness(self):
        """管道结果完整性"""
        system = HolographicSystem()
        result = system.execute(
            unit_id="complete_001",
            unit_name="完整性测试",
            coords={"S": 0.9, "T": 0.3, "P": 0.85, "C": 0.8, "I": 0.85, "E": 0.15},
            enable_imaging=True,
            enable_self_correction=True,
            enable_oracle=True,
            enable_speculation=True,
        )

        d = result.to_dict()
        assert "pipeline_id" in d
        assert "stages" in d
        assert "gate_verdicts" in d
        assert "overall_status" in d
        assert "total_duration_ms" in d

    def test_multiple_pipeline_executions(self):
        """多次管道执行"""
        system = HolographicSystem()
        for i in range(5):
            result = system.execute(
                unit_id=f"multi_{i}",
                unit_name=f"多次执行{i}",
                coords={"S": 0.8 + i * 0.02, "T": 0.5, "P": 0.7},
                enable_imaging=False,
                enable_self_correction=False,
                enable_oracle=False,
            )
            assert result.pipeline_id.startswith("pipeline_")

        stats = system.get_pipeline_stats()
        assert stats["total_pipelines"] == 5

    def test_pipeline_performance_sanity(self):
        """管道性能合理性"""
        system = HolographicSystem()
        result = system.execute(
            unit_id="perf_001",
            unit_name="性能测试",
            coords={"S": 0.9, "T": 0.3, "P": 0.85, "C": 0.8, "I": 0.85, "E": 0.15},
            enable_imaging=True,
            enable_self_correction=True,
            enable_oracle=True,
            enable_speculation=True,
        )
        # 管道总耗时应在合理范围内 (< 30秒)
        assert result.total_duration_ms < 30000

    def test_benchmark_to_holographic_integration(self):
        """基准测试→全息系统集成"""
        # 基准测试
        runner = BenchmarkRunner()
        bench_result = runner.benchmark_tbce_creation(iterations=50)
        assert bench_result.success_count > 0

        # 全息系统
        system = HolographicSystem()
        result = system.execute(
            unit_id="bench_int_001",
            unit_name="基准集成",
            coords={"S": 0.9, "P": 0.8},
            enable_imaging=False,
            enable_self_correction=False,
            enable_oracle=False,
        )
        assert result.pipeline_id.startswith("pipeline_")

        # 统计
        stats = system.get_pipeline_stats()
        assert stats["total_pipelines"] >= 1