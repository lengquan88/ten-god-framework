"""
test_cognitive_metrics.py — 认知指标采集器测试 v2.32.0
===========================================================
测试覆盖：
- TBCEDriftRecord: 创建/告警级别/序列化
- GatePassRecord: 创建/序列化
- CognitiveSnapshot: 创建/序列化
- CognitiveMetricsCollector 单例模式
- TBCE坐标漂移: 记录/统计/告警检测
- 门禁通过率: 记录/统计/趋势
- 推理统计: 延迟分布/百分位
- 自修正统计: 成功率/混沌海计数
- 认知层覆盖: 更新/查询
- 认知快照: 采集/历史/最新
- 认知健康: 健康分数/状态/仪表盘
- 并发安全: 多线程指标采集
"""

import pytest
import threading
import math
from unittest.mock import MagicMock

from tengod.cognitive_metrics import (
    TBCEDriftRecord,
    GatePassRecord,
    CognitiveSnapshot,
    CognitiveMetricsCollector,
    get_cognitive_metrics,
    reset_cognitive_metrics,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(autouse=True)
def reset_collector():
    """每个测试前重置采集器状态。"""
    reset_cognitive_metrics()
    cm = CognitiveMetricsCollector()
    cm.reset()
    yield
    cm.reset()
    reset_cognitive_metrics()


@pytest.fixture
def cm():
    """获取采集器实例。"""
    return CognitiveMetricsCollector()


# ============================================================================
# TBCEDriftRecord 测试
# ============================================================================

class TestTBCEDriftRecord:
    def test_create_drift_record(self):
        """创建漂移记录"""
        record = TBCEDriftRecord(
            unit_id="unit_001",
            unit_name="测试单元",
            coords_before=[0.5, 0.5, 0.5, 0.5, 0.5, 0.5],
            coords_after=[0.6, 0.6, 0.6, 0.6, 0.6, 0.6],
            drift_distance=math.sqrt(6 * 0.01),
            drift_per_dimension=[0.1] * 6,
            trigger="gate_judge",
        )
        assert record.unit_id == "unit_001"
        assert record.unit_name == "测试单元"
        assert len(record.coords_before) == 6
        assert len(record.coords_after) == 6
        assert record.trigger == "gate_judge"

    def test_is_warning_below_threshold(self):
        """漂移低于警告阈值"""
        record = TBCEDriftRecord(
            unit_id="u1", unit_name="u",
            coords_before=[0.0], coords_after=[0.1],
            drift_distance=0.1, drift_per_dimension=[0.1],
        )
        assert record.is_warning is False
        assert record.is_critical is False

    def test_is_warning_at_threshold(self):
        """漂移刚好达到警告阈值"""
        record = TBCEDriftRecord(
            unit_id="u1", unit_name="u",
            coords_before=[0.0], coords_after=[0.3],
            drift_distance=0.3, drift_per_dimension=[0.3],
        )
        assert record.is_warning is False
        assert record.is_critical is False

    def test_is_warning_above_threshold(self):
        """漂移超过警告阈值"""
        record = TBCEDriftRecord(
            unit_id="u1", unit_name="u",
            coords_before=[0.0], coords_after=[0.4],
            drift_distance=0.4, drift_per_dimension=[0.4],
        )
        assert record.is_warning is True
        assert record.is_critical is False

    def test_is_critical_above_threshold(self):
        """漂移超过严重阈值"""
        record = TBCEDriftRecord(
            unit_id="u1", unit_name="u",
            coords_before=[0.0], coords_after=[0.6],
            drift_distance=0.6, drift_per_dimension=[0.6],
        )
        assert record.is_warning is True
        assert record.is_critical is True

    def test_to_dict(self):
        """漂移记录序列化"""
        record = TBCEDriftRecord(
            unit_id="u1", unit_name="test",
            coords_before=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6],
            coords_after=[0.2, 0.3, 0.4, 0.5, 0.6, 0.7],
            drift_distance=0.245,
            drift_per_dimension=[0.1] * 6,
            trigger="self_correction",
        )
        d = record.to_dict()
        assert d["unit_id"] == "u1"
        assert d["unit_name"] == "test"
        assert len(d["coords_before"]) == 6
        assert len(d["coords_after"]) == 6
        assert d["drift_distance"] == round(0.245, 4)
        assert d["is_warning"] is False
        assert d["is_critical"] is False
        assert d["trigger"] == "self_correction"
        assert "drift_per_dim" in d


# ============================================================================
# GatePassRecord 测试
# ============================================================================

class TestGatePassRecord:
    def test_create_gate_record(self):
        """创建门禁记录"""
        record = GatePassRecord(
            gate_name="比肩·劫财",
            god_name="BIJIAN",
            element="木",
            passed=True,
            score=0.85,
            element_boost=0.1,
            reason="架构健康",
            unit_id="unit_001",
        )
        assert record.gate_name == "比肩·劫财"
        assert record.god_name == "BIJIAN"
        assert record.element == "木"
        assert record.passed is True
        assert record.score == 0.85
        assert record.element_boost == 0.1

    def test_to_dict(self):
        """门禁记录序列化"""
        record = GatePassRecord(
            gate_name="七杀·品质裁决",
            god_name="QISHA",
            element="金",
            passed=False,
            score=0.4,
            element_boost=-0.05,
            reason="品质不达标" * 10,
            unit_id="u2",
        )
        d = record.to_dict()
        assert d["gate_name"] == "七杀·品质裁决"
        assert d["passed"] is False
        assert d["score"] == 0.4
        assert len(d["reason"]) <= 100
        assert "element_boost" in d


# ============================================================================
# CognitiveSnapshot 测试
# ============================================================================

class TestCognitiveSnapshot:
    def test_create_snapshot(self):
        """创建认知快照"""
        snap = CognitiveSnapshot()
        assert snap.tbce_unit_count == 0
        assert snap.drift_count == 0
        assert snap.gate_total == 0
        assert snap.gate_pass_rate == 0.0
        assert snap.inference_count == 0
        assert len(snap.tbce_mean) == 6
        assert len(snap.tbce_std) == 6

    def test_to_dict(self):
        """快照序列化"""
        snap = CognitiveSnapshot()
        snap.tbce_mean = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
        snap.gate_total = 100
        snap.gate_passed = 85
        snap.gate_pass_rate = 0.85
        d = snap.to_dict()
        assert "tbce" in d
        assert "drift" in d
        assert "gates" in d
        assert "inference" in d
        assert "correction" in d
        assert d["gates"]["total"] == 100
        assert d["gates"]["pass_rate"] == 0.85
        assert len(d["tbce"]["mean"]) == 6


# ============================================================================
# CognitiveMetricsCollector 单例测试
# ============================================================================

class TestCognitiveMetricsCollectorSingleton:
    def test_singleton_instance(self, cm):
        """采集器是单例"""
        cm2 = CognitiveMetricsCollector()
        assert cm is cm2

    def test_reset_clears_all_state(self, cm):
        """reset 清空所有状态"""
        cm.record_tbce_drift("u1", "u1", [0.5] * 6, [0.6] * 6)
        cm.record_gate_pass("g1", "g1", "木", True, 0.8)
        cm.record_inference(100.0)
        cm.record_speculation(True)
        cm.record_correction(True)
        cm.take_snapshot()

        cm.reset()

        assert len(cm._drift_records) == 0
        assert len(cm._gate_records) == 0
        assert len(cm._inference_durations) == 0
        assert cm._speculation_total == 0
        assert cm._correction_total_count == 0
        assert len(cm._snapshots) == 0

    def test_global_get_cognitive_metrics(self):
        """全局 get_cognitive_metrics 函数"""
        reset_cognitive_metrics()
        cm1 = get_cognitive_metrics()
        cm2 = get_cognitive_metrics()
        assert cm1 is cm2
        assert isinstance(cm1, CognitiveMetricsCollector)

    def test_reset_cognitive_metrics(self):
        """全局重置函数"""
        cm1 = get_cognitive_metrics()
        reset_cognitive_metrics()
        cm2 = get_cognitive_metrics()
        assert cm1 is not cm2


# ============================================================================
# TBCE 漂移记录与统计测试
# ============================================================================

class TestTBCEDrift:
    def test_record_drift(self, cm):
        """记录 TBCE 漂移"""
        record = cm.record_tbce_drift(
            unit_id="unit_001",
            unit_name="测试单元",
            coords_before=[0.5, 0.5, 0.5, 0.5, 0.5, 0.5],
            coords_after=[0.6, 0.6, 0.6, 0.6, 0.6, 0.6],
            trigger="gate_judge",
        )
        assert record.unit_id == "unit_001"
        assert record.drift_distance > 0
        assert len(record.drift_per_dimension) == 6
        assert len(cm._drift_records) == 1

    def test_drift_distance_calculation(self, cm):
        """漂移距离计算正确（欧几里得距离）"""
        record = cm.record_tbce_drift(
            "u1", "u1",
            [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        )
        assert abs(record.drift_distance - 1.0) < 0.001

    def test_drift_drift_per_dimension(self, cm):
        """每维度漂移计算正确"""
        record = cm.record_tbce_drift(
            "u1", "u1",
            [0.1, 0.2, 0.3, 0.4, 0.5, 0.6],
            [0.2, 0.4, 0.6, 0.8, 1.0, 1.2],
        )
        expected = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
        for i in range(6):
            assert abs(record.drift_per_dimension[i] - expected[i]) < 0.001

    def test_drift_ring_buffer(self, cm):
        """漂移记录环形缓冲区"""
        cm._max_drift_records = 5
        for i in range(10):
            cm.record_tbce_drift(
                f"u{i}", f"u{i}",
                [0.0] * 6, [0.1] * 6,
            )
        assert len(cm._drift_records) == 5

    def test_get_drift_stats_empty(self, cm):
        """无漂移记录时的统计"""
        stats = cm.get_drift_stats()
        assert stats["total"] == 0

    def test_get_drift_stats(self, cm):
        """漂移统计正确（精确控制 6 维下的总欧几里得距离）"""
        import math
        # 正常漂移（总距离 = 0.2 < 0.3）3 次
        d_normal = 0.2 / math.sqrt(6)
        for i in range(3):
            cm.record_tbce_drift(f"u{i}", f"u{i}", [0.0]*6, [d_normal]*6)
        # 警告漂移（总距离 = 0.4 > 0.3 但 < 0.5）2 次
        d_warning = 0.4 / math.sqrt(6)
        for i in range(2):
            cm.record_tbce_drift(f"w{i}", f"w{i}", [0.0]*6, [d_warning]*6)
        # 严重漂移（总距离 = 0.6 > 0.5）1 次
        d_critical = 0.6 / math.sqrt(6)
        cm.record_tbce_drift("c1", "c1", [0.0]*6, [d_critical]*6)

        stats = cm.get_drift_stats()
        assert stats["total"] == 6
        assert stats["warnings"] == 3
        assert stats["critical"] == 1
        assert "warning_rate" in stats
        assert "critical_rate" in stats
        assert "mean_drift" in stats
        assert "max_drift" in stats
        assert "by_dimension" in stats
        assert len(stats["by_dimension"]) == 6


# ============================================================================
# TBCE 漂移告警测试
# ============================================================================

class TestDriftAlerts:
    def test_no_alerts_when_clean(self, cm):
        """无漂移时无告警"""
        alerts = cm.check_drift_alerts()
        assert isinstance(alerts, list)
        assert len(alerts) == 0

    def test_critical_drift_alert(self, cm):
        """严重漂移触发告警"""
        for i in range(5):
            cm.record_tbce_drift(
                f"u{i}", f"unit_{i}",
                [0.0] * 6, [0.6] * 6,
            )
        alerts = cm.check_drift_alerts()
        critical_alerts = [a for a in alerts if a["level"] == "critical"]
        assert len(critical_alerts) > 0
        assert critical_alerts[0]["type"] == "tbce_drift"

    def test_warning_trend_alert(self, cm):
        """大量警告漂移触发趋势告警"""
        for i in range(30):
            cm.record_tbce_drift(
                f"u{i}", f"unit_{i}",
                [0.0] * 6, [0.4] * 6,
            )
        alerts = cm.check_drift_alerts()
        warning_alerts = [a for a in alerts if a["type"] == "tbce_drift_trend"]
        assert len(warning_alerts) > 0

    def test_dimension_drift_alert(self, cm):
        """单维度漂移告警"""
        for i in range(10):
            coords_before = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
            coords_after = [0.3, 0.0, 0.0, 0.0, 0.0, 0.0]
            cm.record_tbce_drift(f"u{i}", f"u{i}", coords_before, coords_after)
        alerts = cm.check_drift_alerts()
        dim_alerts = [a for a in alerts if a["type"] == "dimension_drift"]
        assert len(dim_alerts) > 0


# ============================================================================
# 门禁通过率统计测试
# ============================================================================

class TestGateStats:
    def test_record_gate_pass(self, cm):
        """记录门禁通过"""
        record = cm.record_gate_pass(
            gate_name="比肩·劫财",
            god_name="BIJIAN",
            element="木",
            passed=True,
            score=0.85,
            element_boost=0.1,
            reason="架构健康",
            unit_id="u1",
        )
        assert record.passed is True
        assert len(cm._gate_records) == 1

    def test_record_gate_fail(self, cm):
        """记录门禁失败"""
        record = cm.record_gate_pass(
            "七杀·品质裁决", "QISHA", "金",
            False, 0.4, -0.05, "品质低", "u2",
        )
        assert record.passed is False

    def test_gate_ring_buffer(self, cm):
        """门禁记录环形缓冲区"""
        cm._max_gate_records = 10
        for i in range(20):
            cm.record_gate_pass(f"g{i}", f"g{i}", "木", True, 0.8)
        assert len(cm._gate_records) == 10

    def test_get_gate_stats_empty(self, cm):
        """无门禁记录时的统计"""
        stats = cm.get_gate_stats()
        assert stats["total"] == 0

    def test_get_gate_stats_overall(self, cm):
        """门禁总体统计"""
        for i in range(7):
            cm.record_gate_pass(f"g{i}", f"g{i}", "木", True, 0.8)
        for i in range(3):
            cm.record_gate_pass(f"f{i}", f"f{i}", "金", False, 0.3)

        stats = cm.get_gate_stats()
        assert stats["total"] == 10
        assert stats["passed"] == 7
        assert stats["failed"] == 3
        assert stats["overall_pass_rate"] == 0.7

    def test_get_gate_stats_by_gate(self, cm):
        """按门禁分组统计"""
        for i in range(5):
            cm.record_gate_pass("gate_a", "GA", "木", True, 0.8 + i * 0.02)
        for i in range(3):
            cm.record_gate_pass("gate_a", "GA", "木", False, 0.3)

        stats = cm.get_gate_stats()
        assert "gate_a" in stats["by_gate"]
        gate_a = stats["by_gate"]["gate_a"]
        assert gate_a["total"] == 8
        assert gate_a["passed"] == 5
        assert gate_a["pass_rate"] == 5 / 8
        assert "avg_score" in gate_a
        assert "min_score" in gate_a
        assert "max_score" in gate_a
        assert "avg_element_boost" in gate_a

    def test_get_gate_stats_by_element(self, cm):
        """按五行分组统计"""
        cm.record_gate_pass("g1", "g1", "木", True, 0.8)
        cm.record_gate_pass("g2", "g2", "木", False, 0.4)
        cm.record_gate_pass("g3", "g3", "金", True, 0.7)

        stats = cm.get_gate_stats()
        assert "木" in stats["by_element"]
        assert stats["by_element"]["木"]["total"] == 2
        assert stats["by_element"]["金"]["total"] == 1

    def test_record_gate_verdict_from_object(self, cm):
        """从裁决对象记录门禁"""
        mock_verdict = MagicMock()
        mock_verdict.gate_name = "test_gate"
        mock_verdict.god_name = "TG"
        mock_verdict.element = "水"
        mock_verdict.passed = True
        mock_verdict.score = 0.75
        mock_verdict.element_boost = 0.05
        mock_verdict.reason = "ok"

        record = cm.record_gate_verdict(mock_verdict, unit_id="u1")
        assert record.gate_name == "test_gate"
        assert record.passed is True
        assert record.unit_id == "u1"

    def test_record_gate_verdict_fallback(self, cm):
        """裁决对象异常时回退"""
        class BadVerdict:
            def __getattr__(self, name):
                raise RuntimeError("fail")

        record = cm.record_gate_verdict(BadVerdict())
        assert record.gate_name == "unknown"
        assert record.passed is False

    def test_get_gate_trend(self, cm):
        """门禁通过率趋势"""
        for i in range(30):
            passed = i < 25
            cm.record_gate_pass("gate_a", "GA", "木", passed, 0.7)

        trends = cm.get_gate_trend(window_size=10)
        assert "gate_a" in trends
        assert len(trends["gate_a"]) > 0

    def test_get_gate_trend_insufficient_data(self, cm):
        """数据不足时趋势为空"""
        for i in range(5):
            cm.record_gate_pass("g", "g", "木", True, 0.8)
        trends = cm.get_gate_trend(window_size=20)
        assert trends == {}


# ============================================================================
# 推理统计测试
# ============================================================================

class TestInferenceStats:
    def test_record_inference(self, cm):
        """记录推理耗时"""
        cm.record_inference(100.0)
        cm.record_inference(200.0)
        assert len(cm._inference_durations) == 2

    def test_inference_ring_buffer(self, cm):
        """推理记录环形缓冲区"""
        cm._max_inference_records = 5
        for i in range(10):
            cm.record_inference(100.0)
        assert len(cm._inference_durations) == 5

    def test_get_inference_stats_empty(self, cm):
        """无推理记录时的统计"""
        stats = cm.get_inference_stats()
        assert stats["count"] == 0

    def test_get_inference_stats(self, cm):
        """推理统计正确"""
        durations = [50, 100, 150, 200, 250, 300, 350, 400, 450, 500]
        for d in durations:
            cm.record_inference(float(d))

        stats = cm.get_inference_stats()
        assert stats["count"] == 10
        assert stats["mean_ms"] == 275.0
        assert stats["min_ms"] == 50.0
        assert stats["max_ms"] == 500.0
        assert "std_ms" in stats
        assert "p50_ms" in stats
        assert "p95_ms" in stats
        assert "p99_ms" in stats


# ============================================================================
# 推测解码统计测试
# ============================================================================

class TestSpeculationStats:
    def test_record_speculation_hit(self, cm):
        """记录推测命中"""
        cm.record_speculation(True)
        cm.record_speculation(True)
        cm.record_speculation(False)
        assert cm._speculation_total == 3
        assert cm._speculation_hits == 2

    def test_get_speculation_stats(self, cm):
        """推测解码统计"""
        for i in range(7):
            cm.record_speculation(True)
        for i in range(3):
            cm.record_speculation(False)

        stats = cm.get_speculation_stats()
        assert stats["total"] == 10
        assert stats["hits"] == 7
        assert abs(stats["hit_rate"] - 0.7) < 0.001
        assert "speedup_estimate" in stats

    def test_get_speculation_stats_empty(self, cm):
        """无推测时的统计"""
        stats = cm.get_speculation_stats()
        assert stats["total"] == 0
        assert stats["hits"] == 0
        assert stats["hit_rate"] == 0.0


# ============================================================================
# 自修正统计测试
# ============================================================================

class TestCorrectionStats:
    def test_record_correction_success(self, cm):
        """记录成功修正"""
        cm.record_correction(True)
        cm.record_correction(True)
        cm.record_correction(False)
        assert cm._correction_total_count == 3
        assert cm._correction_success_count == 2

    def test_record_chaos_sea_entry(self, cm):
        """记录混沌海存疑"""
        cm.record_chaos_sea_entry()
        cm.record_chaos_sea_entry()
        assert cm._chaos_sea_entry_count == 2

    def test_get_correction_stats(self, cm):
        """自修正统计"""
        for i in range(8):
            cm.record_correction(True)
        for i in range(2):
            cm.record_correction(False)
        cm.record_chaos_sea_entry()

        stats = cm.get_correction_stats()
        assert stats["total"] == 10
        assert stats["success"] == 8
        assert abs(stats["success_rate"] - 0.8) < 0.001
        assert stats["chaos_sea_entries"] == 1


# ============================================================================
# 认知层覆盖测试
# ============================================================================

class TestLayerCoverage:
    def test_update_layer_coverage(self, cm):
        """更新认知层覆盖"""
        coverage = {1: 10, 2: 20, 3: 15, 4: 5}
        cm.update_layer_coverage(coverage)
        result = cm.get_layer_coverage()
        assert result == coverage

    def test_get_layer_coverage_empty(self, cm):
        """初始为空"""
        assert cm.get_layer_coverage() == {}


# ============================================================================
# 认知快照测试
# ============================================================================

class TestCognitiveSnapshotFeature:
    def test_take_snapshot_empty(self, cm):
        """空状态快照"""
        snap = cm.take_snapshot()
        assert snap.tbce_unit_count == 0
        assert snap.drift_count == 0
        assert snap.gate_total == 0
        assert snap.inference_count == 0
        assert len(cm._snapshots) == 1

    def test_take_snapshot_with_data(self, cm):
        """带数据的快照"""
        cm.record_tbce_drift("u1", "u1", [0.5]*6, [0.6]*6)
        cm.record_gate_pass("g1", "g1", "木", True, 0.8)
        cm.record_gate_pass("g2", "g2", "金", False, 0.4)
        cm.record_inference(100.0)
        cm.record_speculation(True)
        cm.record_correction(True)

        snap = cm.take_snapshot()
        assert snap.drift_count == 1
        assert snap.gate_total == 2
        assert snap.gate_passed == 1
        assert snap.inference_count == 1
        assert snap.speculation_hit_rate > 0
        assert snap.correction_count == 1

    def test_get_latest_snapshot(self, cm):
        """获取最新快照"""
        assert cm.get_latest_snapshot() is None
        cm.take_snapshot()
        latest = cm.get_latest_snapshot()
        assert latest is not None
        assert "tbce" in latest

    def test_get_snapshot_history(self, cm):
        """获取快照历史"""
        for i in range(5):
            cm.take_snapshot()
        history = cm.get_snapshot_history(limit=3)
        assert len(history) == 3

    def test_snapshot_ring_buffer(self, cm):
        """快照环形缓冲区"""
        cm._max_snapshots = 3
        for i in range(10):
            cm.take_snapshot()
        assert len(cm._snapshots) == 3


# ============================================================================
# 认知健康测试
# ============================================================================

class TestCognitiveHealth:
    def test_compute_health_score_empty(self, cm):
        """无数据时健康分为 1.0"""
        score = cm._compute_health_score()
        assert score == 1.0

    def test_compute_health_score_with_data(self, cm):
        """带数据的健康分计算"""
        for i in range(8):
            cm.record_gate_pass("g", "g", "木", True, 0.8)
        for i in range(2):
            cm.record_gate_pass("g", "g", "木", False, 0.3)
        for i in range(10):
            cm.record_tbce_drift(f"u{i}", f"u{i}", [0.0]*6, [0.1]*6)
        for i in range(7):
            cm.record_correction(True)
        for i in range(3):
            cm.record_correction(False)
        for i in range(6):
            cm.record_speculation(True)
        for i in range(4):
            cm.record_speculation(False)
        for i in range(10):
            cm.record_inference(100.0)

        score = cm._compute_health_score()
        assert 0.0 <= score <= 1.0

    def test_get_health_status_healthy(self, cm):
        """健康状态 - healthy"""
        for i in range(9):
            cm.record_gate_pass("g", "g", "木", True, 0.9)
        cm.record_gate_pass("g", "g", "木", False, 0.3)
        for i in range(10):
            cm.record_tbce_drift(f"u{i}", f"u{i}", [0.0]*6, [0.05]*6)

        status = cm.get_health_status()
        assert "status" in status
        assert "score" in status
        assert "gates" in status
        assert "drift" in status
        assert "alerts" in status

    def test_get_dashboard_data(self, cm):
        """仪表盘数据"""
        cm.record_gate_pass("g1", "g1", "木", True, 0.8)
        cm.record_tbce_drift("u1", "u1", [0.5]*6, [0.6]*6)

        data = cm.get_dashboard_data()
        assert "timestamp" in data
        assert "overall_health" in data
        assert "snapshot" in data
        assert "gates" in data
        assert "drift" in data
        assert "inference" in data
        assert "correction" in data
        assert "speculation" in data
        assert "alerts" in data
        assert "layer_coverage" in data
        assert 0.0 <= data["overall_health"] <= 1.0


# ============================================================================
# 并发安全测试
# ============================================================================

class TestConcurrencySafety:
    def test_concurrent_drift_recording(self, cm):
        """并发记录漂移"""
        errors = []

        def record_drifts(n, offset):
            try:
                for i in range(n):
                    cm.record_tbce_drift(
                        f"u{offset + i}", f"u{offset + i}",
                        [0.0] * 6, [0.1] * 6,
                    )
            except Exception as e:
                errors.append(e)

        threads = []
        for i in range(5):
            t = threading.Thread(target=record_drifts, args=(20, i * 20))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(cm._drift_records) == 100

    def test_concurrent_gate_recording(self, cm):
        """并发记录门禁"""
        errors = []

        def record_gates(n, offset):
            try:
                for i in range(n):
                    passed = i % 2 == 0
                    cm.record_gate_pass(
                        f"gate_{offset + i}",
                        f"G{offset + i}",
                        "木",
                        passed,
                        0.7,
                    )
            except Exception as e:
                errors.append(e)

        threads = []
        for i in range(5):
            t = threading.Thread(target=record_gates, args=(20, i * 20))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(cm._gate_records) == 100
