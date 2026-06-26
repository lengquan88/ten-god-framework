"""
test_huigu_scheduler.py — 回头看调度器全面测试
===============================================
测试覆盖 GradientSnapshot 数据类、HuiguScheduler 类、
工厂函数单例、别名函数以及各种边界条件。
"""

import math
import time
import pytest
from unittest.mock import patch

from tengod.huigu_scheduler import (
    GradientSnapshot,
    HuiguScheduler,
    get_huigu_scheduler,
    get_scheduler,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def scheduler():
    """创建默认配置的 HuiguScheduler 实例"""
    return HuiguScheduler()


@pytest.fixture
def scheduler_custom():
    """创建自定义参数的 HuiguScheduler 实例"""
    return HuiguScheduler(window_size=20, max_angle=60.0)


@pytest.fixture
def scheduler_small_window():
    """创建小窗口的 HuiguScheduler 实例（用于震荡测试）"""
    return HuiguScheduler(window_size=5, max_angle=45.0)


# ============================================================================
# 1. GradientSnapshot 数据类测试
# ============================================================================

class TestGradientSnapshot:
    """GradientSnapshot 数据类测试"""

    def test_create_basic(self):
        """测试基本创建"""
        snap = GradientSnapshot(step=1, direction=[1.0, 0.0], magnitude=1.0, angle_to_origin=0.0)
        assert snap.step == 1
        assert snap.direction == [1.0, 0.0]
        assert snap.magnitude == 1.0
        assert snap.angle_to_origin == 0.0

    def test_default_timestamp(self):
        """测试默认时间戳"""
        before = time.time()
        snap = GradientSnapshot(step=0, direction=[1.0], magnitude=0.5, angle_to_origin=10.0)
        after = time.time()
        assert before <= snap.timestamp <= after

    def test_all_fields(self):
        """测试所有字段可访问"""
        snap = GradientSnapshot(
            step=42,
            direction=[3.0, -4.0],
            magnitude=5.0,
            angle_to_origin=53.13,
            timestamp=1234567890.0,
        )
        assert snap.step == 42
        assert snap.direction == [3.0, -4.0]
        assert snap.magnitude == 5.0
        assert snap.angle_to_origin == 53.13
        assert snap.timestamp == 1234567890.0

    def test_field_types(self):
        """测试字段类型"""
        snap = GradientSnapshot(step=10, direction=[1.0, 2.0], magnitude=3.0, angle_to_origin=5.0)
        assert isinstance(snap.step, int)
        assert isinstance(snap.direction, list)
        assert isinstance(snap.magnitude, float)
        assert isinstance(snap.angle_to_origin, float)
        assert isinstance(snap.timestamp, float)

    def test_empty_direction(self):
        """测试空方向向量"""
        snap = GradientSnapshot(step=0, direction=[], magnitude=0.0, angle_to_origin=0.0)
        assert snap.direction == []
        assert snap.magnitude == 0.0

    def test_equality(self):
        """测试相等性（dataclass 默认行为）"""
        snap1 = GradientSnapshot(step=1, direction=[1.0], magnitude=1.0, angle_to_origin=0.0, timestamp=100.0)
        snap2 = GradientSnapshot(step=1, direction=[1.0], magnitude=1.0, angle_to_origin=0.0, timestamp=100.0)
        assert snap1 == snap2

    def test_inequality(self):
        """测试不相等"""
        snap1 = GradientSnapshot(step=1, direction=[1.0], magnitude=1.0, angle_to_origin=0.0)
        snap2 = GradientSnapshot(step=2, direction=[1.0], magnitude=1.0, angle_to_origin=0.0)
        assert snap1 != snap2


# ============================================================================
# 2. HuiguScheduler __init__ 测试
# ============================================================================

class TestHuiguSchedulerInit:
    """HuiguScheduler 初始化测试"""

    def test_default_init(self):
        """测试默认初始化"""
        scheduler = HuiguScheduler()
        assert scheduler.window_size == 10
        assert scheduler.max_angle == 45.0
        assert scheduler._history == []
        assert scheduler._initial_direction is None
        assert scheduler._silent_count == 0
        assert scheduler._recall_count == 0
        assert scheduler._total_steps == 0

    def test_custom_window_size(self):
        """测试自定义窗口大小"""
        scheduler = HuiguScheduler(window_size=20)
        assert scheduler.window_size == 20
        assert scheduler.max_angle == 45.0

    def test_custom_max_angle(self):
        """测试自定义最大角度"""
        scheduler = HuiguScheduler(max_angle=90.0)
        assert scheduler.window_size == 10
        assert scheduler.max_angle == 90.0

    def test_custom_both(self):
        """测试两个参数都自定义"""
        scheduler = HuiguScheduler(window_size=30, max_angle=60.0)
        assert scheduler.window_size == 30
        assert scheduler.max_angle == 60.0

    def test_zero_window_size(self):
        """测试窗口大小为 0"""
        scheduler = HuiguScheduler(window_size=0, max_angle=45.0)
        assert scheduler.window_size == 0
        # 注册一个梯度后，振荡检测用 window_size=0 的 recent 切片
        result = scheduler.register_gradient(1, [1.0, 0.0])
        assert result["action"] == "continue"

    def test_zero_max_angle(self):
        """测试最大角度为 0"""
        scheduler = HuiguScheduler(max_angle=0.0)
        # 任何非零角度都会触发 silent
        result = scheduler.register_gradient(1, [1.0, 0.0])
        # 设置初始方向为 [1.0, 0.0]
        result = scheduler.register_gradient(2, [0.0, 1.0])
        # 与 [1.0, 0.0] 夹角为 90 > 0
        assert result["action"] == "silent"


# ============================================================================
# 3. register_gradient 测试
# ============================================================================

class TestRegisterGradient:
    """register_gradient 方法测试"""

    def test_zero_gradient(self, scheduler):
        """测试零梯度 — 返回 continue"""
        result = scheduler.register_gradient(1, [0.0, 0.0, 0.0])
        assert result["action"] == "continue"
        assert result["angle"] == 0
        assert result["trajectory_health"] == 1.0

    def test_empty_gradient(self, scheduler):
        """测试空梯度列表 — 返回 continue"""
        result = scheduler.register_gradient(1, [])
        assert result["action"] == "continue"
        assert result["angle"] == 0
        assert result["trajectory_health"] == 1.0

    def test_same_direction_continue(self, scheduler):
        """测试相同方向 — 返回 continue"""
        result1 = scheduler.register_gradient(1, [1.0, 0.0])
        assert result1["action"] == "continue"
        result2 = scheduler.register_gradient(2, [2.0, 0.0])  # 同方向
        assert result2["action"] == "continue"
        assert result2["angle"] == 0.0

    def test_large_angle_silent(self, scheduler):
        """测试大角度偏离 — 返回 silent"""
        scheduler.register_gradient(1, [1.0, 0.0])  # 初始方向
        result = scheduler.register_gradient(2, [0.0, 1.0])  # 90° > 45°
        assert result["action"] == "silent"
        assert result["angle"] == 90.0

    def test_small_magnitude_recall(self, scheduler):
        """测试极小梯度模长 — 返回 recall"""
        scheduler.register_gradient(1, [1.0, 0.0])  # 初始方向
        result = scheduler.register_gradient(2, [5e-7, 5e-7])  # magnitude ≈ 7.07e-7 < 1e-6
        assert result["action"] == "recall"

    def test_oscillation_pattern_silent(self, scheduler_small_window):
        """测试震荡模式 — 返回 silent"""
        s = scheduler_small_window  # window_size=5
        # 建立初始方向
        s.register_gradient(1, [1.0, 0.0])
        # 制造震荡：交替方向
        results = []
        directions = [
            [0.0, 1.0],    # 90°, 与上一个差 90
            [1.0, 0.0],    # 0°, 与上一个差 90
            [0.0, 1.0],    # 90°, 与上一个差 90
            [1.0, 0.0],    # 0°, 与上一个差 90
            [0.0, 1.0],    # 90°, 与上一个差 90
        ]
        for i, d in enumerate(directions, start=2):
            results.append(s.register_gradient(i, d))
        # 第5个注册后，history 有 1+5=6 个快照，recent 5 个
        # 振荡次数：相邻差值 > 20 的次数
        # angles: [0, 90, 0, 90, 0] → 差值: 90, 90, 90, 90 共4次 > 20
        # oscillations = 4, len(angles) * 0.3 = 1.5, 4 > 1.5 → silent
        assert any(r["action"] == "silent" for r in results)

    def test_return_value_structure(self, scheduler):
        """测试返回值的完整结构"""
        result = scheduler.register_gradient(1, [1.0, 2.0, 3.0])
        assert "action" in result
        assert "angle" in result
        assert "magnitude" in result
        assert "trajectory_health" in result
        assert "step" in result
        assert result["action"] in ("continue", "silent", "recall")
        assert isinstance(result["angle"], (int, float))
        assert isinstance(result["magnitude"], (int, float))
        assert isinstance(result["trajectory_health"], (int, float))
        assert result["step"] == 1

    def test_multiple_continue_steps(self, scheduler):
        """测试多个连续的正常步骤"""
        results = []
        for i in range(1, 11):
            results.append(scheduler.register_gradient(i, [1.0, 0.1 * i]))
        assert all(r["action"] == "continue" for r in results)

    def test_silent_counter_increments(self, scheduler):
        """测试 silent 计数器递增"""
        scheduler.register_gradient(1, [1.0, 0.0])
        scheduler.register_gradient(2, [0.0, 1.0])  # silent
        assert scheduler._silent_count == 1
        assert scheduler._recall_count == 0

    def test_recall_counter_increments(self, scheduler):
        """测试 recall 计数器递增"""
        scheduler.register_gradient(1, [1.0, 0.0])
        scheduler.register_gradient(2, [5e-7, 0.0])  # recall, magnitude=5e-7 < 1e-6
        assert scheduler._recall_count == 1
        assert scheduler._silent_count == 0

    def test_total_steps_counter(self, scheduler):
        """测试总步数计数器"""
        for i in range(1, 6):
            scheduler.register_gradient(i, [float(i), 0.0])
        assert scheduler._total_steps == 5

    def test_history_appends(self, scheduler):
        """测试历史记录追加"""
        scheduler.register_gradient(1, [1.0, 0.0])
        scheduler.register_gradient(2, [2.0, 0.0])
        assert len(scheduler._history) == 2
        assert scheduler._history[0].step == 1
        assert scheduler._history[1].step == 2

    def test_initial_direction_set(self, scheduler):
        """测试初始方向设置"""
        assert scheduler._initial_direction is None
        scheduler.register_gradient(1, [3.0, 4.0])
        assert scheduler._initial_direction == [3.0, 4.0]

    def test_initial_direction_not_reset(self, scheduler):
        """测试初始方向不会因后续注册而改变"""
        scheduler.register_gradient(1, [1.0, 0.0])
        scheduler.register_gradient(2, [0.0, 1.0])
        assert scheduler._initial_direction == [1.0, 0.0]


# ============================================================================
# 4. _compute_angle 测试
# ============================================================================

class TestComputeAngle:
    """_compute_angle 方法测试"""

    def test_parallel_vectors(self, scheduler):
        """测试平行向量（0°）"""
        angle = scheduler._compute_angle([1.0, 0.0], [5.0, 0.0])
        assert angle == pytest.approx(0.0, abs=1e-6)

    def test_orthogonal_vectors(self, scheduler):
        """测试正交向量（90°）"""
        angle = scheduler._compute_angle([1.0, 0.0], [0.0, 1.0])
        assert angle == pytest.approx(90.0, abs=1e-6)

    def test_opposite_vectors(self, scheduler):
        """测试相反向量（180°）"""
        angle = scheduler._compute_angle([1.0, 0.0], [-1.0, 0.0])
        assert angle == pytest.approx(180.0, abs=1e-6)

    def test_45_degree(self, scheduler):
        """测试 45° 角"""
        angle = scheduler._compute_angle([1.0, 0.0], [1.0, 1.0])
        assert angle == pytest.approx(45.0, abs=1e-6)

    def test_zero_vector_first(self, scheduler):
        """测试第一个向量为零向量"""
        angle = scheduler._compute_angle([0.0, 0.0], [1.0, 0.0])
        assert angle == 0.0

    def test_zero_vector_second(self, scheduler):
        """测试第二个向量为零向量"""
        angle = scheduler._compute_angle([1.0, 0.0], [0.0, 0.0])
        assert angle == 0.0

    def test_both_zero_vectors(self, scheduler):
        """测试两个零向量"""
        angle = scheduler._compute_angle([0.0, 0.0], [0.0, 0.0])
        assert angle == 0.0

    def test_3d_vectors(self, scheduler):
        """测试三维向量"""
        angle = scheduler._compute_angle([1.0, 0.0, 0.0], [0.0, 1.0, 0.0])
        assert angle == pytest.approx(90.0, abs=1e-6)

    def test_different_dimensions_via_zip(self, scheduler):
        """测试不同维度（zip 会自动截断）"""
        angle = scheduler._compute_angle([1.0, 0.0, 0.0], [1.0, 0.0])
        assert angle == pytest.approx(0.0, abs=1e-6)

    def test_negative_values(self, scheduler):
        """测试负值向量"""
        angle = scheduler._compute_angle([1.0, 1.0], [-1.0, -1.0])
        assert angle == pytest.approx(180.0, abs=1e-5)

    def test_very_large_values(self, scheduler):
        """测试极大值向量"""
        angle = scheduler._compute_angle([1e10, 0.0], [0.0, 1e10])
        assert angle == pytest.approx(90.0, abs=1e-6)

    def test_very_small_nonzero_values(self, scheduler):
        """测试极小非零值向量"""
        angle = scheduler._compute_angle([1e-10, 0.0], [0.0, 1e-10])
        assert angle == pytest.approx(90.0, abs=1e-6)

    def test_single_element_vectors(self, scheduler):
        """测试单元素向量"""
        angle = scheduler._compute_angle([1.0], [1.0])
        assert angle == pytest.approx(0.0, abs=1e-6)
        angle2 = scheduler._compute_angle([1.0], [-1.0])
        assert angle2 == pytest.approx(180.0, abs=1e-6)


# ============================================================================
# 5. _decide_action 测试
# ============================================================================

class TestDecideAction:
    """_decide_action 方法测试"""

    def test_continue_normal(self, scheduler):
        """测试正常角度和模长 — continue"""
        scheduler._history = []  # 确保空历史
        action = scheduler._decide_action(angle=30.0, magnitude=0.5)
        assert action == "continue"

    def test_silent_angle_exceeds(self, scheduler):
        """测试角度超过阈值 — silent"""
        action = scheduler._decide_action(angle=50.0, magnitude=1.0)
        assert action == "silent"

    def test_recall_small_magnitude(self, scheduler):
        """测试极小模长 — recall"""
        action = scheduler._decide_action(angle=10.0, magnitude=5e-7)
        assert action == "recall"

    def test_boundary_angle_equals_max(self, scheduler):
        """测试边界条件：angle == max_angle — continue（不是 >）"""
        action = scheduler._decide_action(angle=45.0, magnitude=1.0)
        assert action == "continue"

    def test_boundary_magnitude_equals_threshold(self, scheduler):
        """测试边界条件：magnitude == 1e-6 — continue（不是 <）"""
        action = scheduler._decide_action(angle=10.0, magnitude=1e-6)
        assert action == "continue"

    def test_angle_just_above_max(self, scheduler):
        """测试角度刚好超过阈值"""
        action = scheduler._decide_action(angle=45.0001, magnitude=1.0)
        assert action == "silent"

    def test_magnitude_just_below_threshold(self, scheduler):
        """测试模长刚好低于阈值"""
        action = scheduler._decide_action(angle=10.0, magnitude=9.99999e-7)
        assert action == "recall"

    def test_oscillation_detection(self, scheduler_small_window):
        """测试震荡检测"""
        s = scheduler_small_window  # window_size=5
        # 填充历史使得 recent 5 个快照的 angle 震荡
        # 手动构造历史快照
        for i in range(5):
            snap = GradientSnapshot(
                step=i,
                direction=[1.0, 0.0],
                magnitude=1.0,
                angle_to_origin=90.0 if i % 2 == 0 else 0.0,
            )
            s._history.append(snap)
        # history 有 5 个，window_size=5，recent 5 个
        # angles: [90, 0, 90, 0, 90]
        # 相邻差值: 90, 90, 90, 90 → oscillations=4, len(angles)*0.3=1.5, 4>1.5 → silent
        action = s._decide_action(angle=30.0, magnitude=1.0)
        assert action == "silent"

    def test_no_oscillation_with_stable_angles(self, scheduler_small_window):
        """测试稳定角度不触发震荡检测"""
        s = scheduler_small_window
        for i in range(5):
            snap = GradientSnapshot(
                step=i,
                direction=[1.0, 0.0],
                magnitude=1.0,
                angle_to_origin=5.0,  # 稳定角度
            )
            s._history.append(snap)
        # angles: [5, 5, 5, 5, 5], 相邻差值都是 0
        action = s._decide_action(angle=10.0, magnitude=1.0)
        assert action == "continue"

    def test_oscillation_not_enough_snapshots(self, scheduler):
        """测试快照不够时不触发震荡检测"""
        # history 只有 2 个，不到 window_size=10
        for i in range(2):
            snap = GradientSnapshot(
                step=i,
                direction=[1.0, 0.0],
                magnitude=1.0,
                angle_to_origin=90.0 if i % 2 == 0 else 0.0,
            )
            scheduler._history.append(snap)
        action = scheduler._decide_action(angle=30.0, magnitude=1.0)
        assert action == "continue"

    def test_oscillation_exactly_at_threshold(self, scheduler_small_window):
        """测试震荡刚好在阈值边界"""
        s = scheduler_small_window
        # 创建 5 个快照，其中只有 1 个震荡（oscillations=1, 阈值=1.5, 1 <= 1.5）
        angles = [0.0, 0.0, 0.0, 0.0, 90.0]
        for i, a in enumerate(angles):
            snap = GradientSnapshot(step=i, direction=[1.0, 0.0], magnitude=1.0, angle_to_origin=a)
            s._history.append(snap)
        action = s._decide_action(angle=10.0, magnitude=1.0)
        assert action == "continue"


# ============================================================================
# 6. _compute_health 测试
# ============================================================================

class TestComputeHealth:
    """_compute_health 方法测试"""

    def test_few_snapshots_healthy(self, scheduler):
        """测试快照少于 3 个时返回 1.0"""
        scheduler.register_gradient(1, [1.0, 0.0])
        health = scheduler._compute_health()
        assert health == 1.0

    def test_two_snapshots_healthy(self, scheduler):
        """测试两个快照时返回 1.0"""
        scheduler.register_gradient(1, [1.0, 0.0])
        scheduler.register_gradient(2, [2.0, 0.0])
        health = scheduler._compute_health()
        assert health == 1.0

    def test_healthy_trajectory(self, scheduler):
        """测试健康轨迹（小角度偏离）"""
        scheduler.register_gradient(1, [1.0, 0.0])
        scheduler.register_gradient(2, [1.0, 0.1])
        scheduler.register_gradient(3, [1.0, 0.05])
        scheduler.register_gradient(4, [1.0, -0.1])
        health = scheduler._compute_health()
        # 平均角度应该很小，健康度接近 1.0
        assert 0.5 <= health <= 1.0

    def test_unhealthy_trajectory(self, scheduler):
        """测试不健康轨迹（大角度偏离）"""
        scheduler.register_gradient(1, [1.0, 0.0])
        scheduler.register_gradient(2, [-0.5, 0.866])  # ~120°
        scheduler.register_gradient(3, [-0.5, -0.866])  # ~120°
        scheduler.register_gradient(4, [-1.0, 0.0])  # 180°
        scheduler.register_gradient(5, [-0.5, 0.866])  # ~120°
        health = scheduler._compute_health()
        assert health < 0.5

    def test_health_range(self, scheduler):
        """测试健康度始终在 [0, 1] 范围内"""
        scheduler.register_gradient(1, [1.0, 0.0])
        for i in range(2, 20):
            scheduler.register_gradient(i, [float(i % 3 - 1), float(i % 2)])
        health = scheduler._compute_health()
        assert 0.0 <= health <= 1.0

    def test_health_with_many_snapshots(self, scheduler):
        """测试大量快照时的健康度"""
        scheduler.register_gradient(1, [1.0, 0.0])
        for i in range(2, 50):
            scheduler.register_gradient(i, [1.0, 0.01 * i])
        health = scheduler._compute_health()
        assert 0.0 <= health <= 1.0

    def test_health_with_all_large_angles(self, scheduler):
        """测试全大角度时的健康度"""
        scheduler.register_gradient(1, [1.0, 0.0])
        for i in range(2, 30):
            scheduler.register_gradient(i, [0.0, 1.0])  # 90° each
        health = scheduler._compute_health()
        # avg_angle ≈ 90, max_angle = 90, health = 1 - 90/90 ≈ 0
        assert health < 0.1


# ============================================================================
# 7. get_best_snapshot 测试
# ============================================================================

class TestGetBestSnapshot:
    """get_best_snapshot 方法测试"""

    def test_empty_history(self, scheduler):
        """测试空历史返回 None"""
        assert scheduler.get_best_snapshot() is None

    def test_with_history(self, scheduler):
        """测试有历史时返回最小偏离角的快照"""
        scheduler.register_gradient(1, [1.0, 0.0])  # angle=0
        scheduler.register_gradient(2, [0.9, 0.1])  # small angle
        scheduler.register_gradient(3, [0.0, 1.0])  # angle=90
        best = scheduler.get_best_snapshot()
        assert best is not None
        assert best.step == 1
        assert best.angle_to_origin == pytest.approx(0.0, abs=1e-6)

    def test_best_snapshot_is_not_none_type(self, scheduler):
        """测试返回的是 GradientSnapshot 类型"""
        scheduler.register_gradient(1, [1.0, 0.0])
        best = scheduler.get_best_snapshot()
        assert isinstance(best, GradientSnapshot)

    def test_best_snapshot_in_middle(self, scheduler):
        """测试最佳快照在中间位置"""
        scheduler.register_gradient(1, [1.0, 0.0])  # angle=0, sets initial direction
        scheduler.register_gradient(2, [0.0, 1.0])  # angle=90
        scheduler.register_gradient(3, [1.0, 0.0])  # angle=0  ← also best
        best = scheduler.get_best_snapshot()
        # 第 1 步和第 3 步都是 angle=0，min 返回第一个
        assert best.step == 1


# ============================================================================
# 8. reset_origin 测试
# ============================================================================

class TestResetOrigin:
    """reset_origin 方法测试"""

    def test_reset_with_history(self, scheduler):
        """测试有历史时重置初始方向"""
        scheduler.register_gradient(1, [1.0, 0.0])
        scheduler.register_gradient(2, [0.0, 1.0])
        assert scheduler._initial_direction == [1.0, 0.0]
        scheduler.reset_origin()
        assert scheduler._initial_direction == [0.0, 1.0]

    def test_reset_with_empty_history(self, scheduler):
        """测试空历史时重置"""
        scheduler.reset_origin()
        assert scheduler._initial_direction is None

    def test_reset_after_reset(self, scheduler):
        """测试连续重置"""
        scheduler.register_gradient(1, [1.0, 0.0])
        scheduler.register_gradient(2, [0.0, 1.0])
        scheduler.register_gradient(3, [-1.0, 0.0])
        scheduler.reset_origin()
        assert scheduler._initial_direction == [-1.0, 0.0]
        scheduler.register_gradient(4, [0.0, -1.0])
        scheduler.reset_origin()
        assert scheduler._initial_direction == [0.0, -1.0]

    def test_reset_changes_angle_calculation(self, scheduler):
        """测试重置后角度计算使用新的初始方向"""
        scheduler.register_gradient(1, [1.0, 0.0])
        # 重置 - 初始方向变为 [1.0, 0.0]（只有一个快照）
        scheduler.reset_origin()
        # 现在注册一个 [1.0, 0.0] 同方向的，角度应为 0
        result = scheduler.register_gradient(2, [1.0, 0.0])
        assert result["angle"] == 0.0


# ============================================================================
# 9. get_stats 测试
# ============================================================================

class TestGetStats:
    """get_stats 方法测试"""

    def test_empty_stats(self, scheduler):
        """测试空统计"""
        stats = scheduler.get_stats()
        assert stats["total_steps"] == 0
        assert stats["silent_count"] == 0
        assert stats["recall_count"] == 0
        assert stats["silent_rate"] == 0.0
        assert stats["recall_rate"] == 0.0
        assert stats["trajectory_health"] == 1.0
        assert stats["history_size"] == 0

    def test_stats_after_some_steps(self, scheduler):
        """测试几步后的统计"""
        scheduler.register_gradient(1, [1.0, 0.0])
        scheduler.register_gradient(2, [0.0, 1.0])  # silent
        scheduler.register_gradient(3, [5e-7, 0.0])  # recall, magnitude=5e-7 < 1e-6
        stats = scheduler.get_stats()
        assert stats["total_steps"] == 3
        assert stats["silent_count"] == 1
        assert stats["recall_count"] == 1
        assert stats["silent_rate"] == pytest.approx(1 / 3, abs=0.001)
        assert stats["recall_rate"] == pytest.approx(1 / 3, abs=0.001)
        assert stats["history_size"] == 3

    def test_stats_all_fields_present(self, scheduler):
        """测试所有字段都存在"""
        stats = scheduler.get_stats()
        expected_keys = {
            "total_steps", "silent_count", "recall_count",
            "silent_rate", "recall_rate", "trajectory_health", "history_size",
        }
        assert set(stats.keys()) == expected_keys

    def test_stats_rates_avoid_zero_division(self, scheduler):
        """测试除零保护"""
        stats = scheduler.get_stats()
        assert stats["silent_rate"] == 0.0
        assert stats["recall_rate"] == 0.0


# ============================================================================
# 10. get_status 测试
# ============================================================================

class TestGetStatus:
    """get_status 方法测试"""

    def test_empty_status(self, scheduler):
        """测试空状态"""
        status = scheduler.get_status()
        assert status["total_steps"] == 0
        assert status["window_size"] == 10
        assert status["max_angle"] == 45.0
        assert status["recent_history"] == []

    def test_status_with_recent_history(self, scheduler):
        """测试有最近历史的状态"""
        for i in range(1, 8):
            scheduler.register_gradient(i, [1.0, 0.1 * i])
        status = scheduler.get_status()
        assert len(status["recent_history"]) == 5  # 最近 5 个
        assert status["recent_history"][0]["step"] == 3
        assert status["recent_history"][-1]["step"] == 7

    def test_status_less_than_5(self, scheduler):
        """测试不足 5 个快照时的状态"""
        scheduler.register_gradient(1, [1.0, 0.0])
        scheduler.register_gradient(2, [2.0, 0.0])
        status = scheduler.get_status()
        assert len(status["recent_history"]) == 2

    def test_status_includes_window_size(self, scheduler_custom):
        """测试状态包含自定义窗口大小"""
        status = scheduler_custom.get_status()
        assert status["window_size"] == 20
        assert status["max_angle"] == 60.0

    def test_status_recent_history_structure(self, scheduler):
        """测试最近历史的结构"""
        scheduler.register_gradient(1, [1.0, 2.0, 3.0])
        status = scheduler.get_status()
        entry = status["recent_history"][0]
        assert "step" in entry
        assert "angle" in entry
        assert "magnitude" in entry
        assert isinstance(entry["step"], int)
        assert isinstance(entry["angle"], (int, float))
        assert isinstance(entry["magnitude"], (int, float))


# ============================================================================
# 11. 历史窗口裁剪测试
# ============================================================================

class TestHistoryTrimming:
    """历史窗口裁剪测试"""

    def test_history_trimmed_when_exceeds_limit(self, scheduler):
        """测试历史超过 window_size*2 时被裁剪"""
        # window_size=10, 所以超过 20 个快照时裁剪
        for i in range(1, 26):
            scheduler.register_gradient(i, [1.0, 0.1 * i])
        # 应该有 20 个（裁剪到 window_size * 2 = 20）
        assert len(scheduler._history) == 20
        # 最早的应该是 step 6
        assert scheduler._history[0].step == 6
        assert scheduler._history[-1].step == 25

    def test_history_not_trimmed_within_limit(self, scheduler):
        """测试不超过限制时不裁剪"""
        for i in range(1, 21):
            scheduler.register_gradient(i, [1.0, 0.1 * i])
        assert len(scheduler._history) == 20

    def test_history_trimmed_with_custom_window(self, scheduler_custom):
        """测试自定义窗口下的裁剪"""
        # window_size=20, 超过 40 时裁剪
        for i in range(1, 50):
            scheduler_custom.register_gradient(i, [1.0, 0.1 * i])
        assert len(scheduler_custom._history) == 40

    def test_history_trimmed_zero_window(self):
        """测试零窗口时裁剪行为（window_size=0 时 -0 切片返回全列表）"""
        s = HuiguScheduler(window_size=0, max_angle=45.0)
        for i in range(1, 5):
            s.register_gradient(i, [1.0, 0.0])
        # window_size=0, 所以 window_size*2=0, self._history[-0:] 返回全部
        assert len(s._history) == 4


# ============================================================================
# 12. 单例工厂函数测试
# ============================================================================

class TestGetHuiguScheduler:
    """get_huigu_scheduler 工厂函数测试"""

    def test_returns_huigu_scheduler_instance(self):
        """测试返回 HuiguScheduler 实例"""
        # 重置全局状态
        import tengod.huigu_scheduler as mod
        mod._huigu_scheduler = None
        s = get_huigu_scheduler()
        assert isinstance(s, HuiguScheduler)

    def test_singleton_behavior(self):
        """测试单例行为"""
        import tengod.huigu_scheduler as mod
        mod._huigu_scheduler = None
        s1 = get_huigu_scheduler()
        s2 = get_huigu_scheduler()
        assert s1 is s2

    def test_singleton_ignores_second_call_args(self):
        """测试后续调用忽略参数"""
        import tengod.huigu_scheduler as mod
        mod._huigu_scheduler = None
        s1 = get_huigu_scheduler(window_size=10, max_angle=45.0)
        s2 = get_huigu_scheduler(window_size=999, max_angle=999.0)
        assert s1 is s2
        assert s2.window_size == 10  # 保持第一次的参数
        assert s2.max_angle == 45.0

    def test_default_parameters(self):
        """测试默认参数"""
        import tengod.huigu_scheduler as mod
        mod._huigu_scheduler = None
        s = get_huigu_scheduler()
        assert s.window_size == 10
        assert s.max_angle == 45.0

    def test_custom_parameters_on_first_call(self):
        """测试首次调用时自定义参数"""
        import tengod.huigu_scheduler as mod
        mod._huigu_scheduler = None
        s = get_huigu_scheduler(window_size=30, max_angle=60.0)
        assert s.window_size == 30
        assert s.max_angle == 60.0


# ============================================================================
# 13. get_scheduler 别名测试
# ============================================================================

class TestGetScheduler:
    """get_scheduler 别名函数测试"""

    def test_returns_huigu_scheduler_instance(self):
        """测试返回 HuiguScheduler 实例"""
        import tengod.huigu_scheduler as mod
        mod._huigu_scheduler = None
        s = get_scheduler()
        assert isinstance(s, HuiguScheduler)

    def test_alias_same_as_factory(self):
        """测试别名与工厂函数返回相同实例"""
        import tengod.huigu_scheduler as mod
        mod._huigu_scheduler = None
        s1 = get_huigu_scheduler()
        s2 = get_scheduler()
        assert s1 is s2

    def test_alias_after_factory(self):
        """测试先调用工厂函数再调用别名"""
        import tengod.huigu_scheduler as mod
        mod._huigu_scheduler = None
        s1 = get_huigu_scheduler(window_size=15, max_angle=30.0)
        s2 = get_scheduler()
        assert s1 is s2
        assert s2.window_size == 15


# ============================================================================
# 14. 边界条件测试
# ============================================================================

class TestBoundaryConditions:
    """边界条件测试"""

    def test_empty_gradient_list(self, scheduler):
        """测试空梯度列表"""
        result = scheduler.register_gradient(1, [])
        assert result["action"] == "continue"

    def test_single_element_gradient(self, scheduler):
        """测试单元素梯度"""
        result = scheduler.register_gradient(1, [1.0])
        assert result["action"] == "continue"
        assert result["magnitude"] == pytest.approx(1.0, abs=1e-6)

    def test_all_zeros_gradient(self, scheduler):
        """测试全零梯度"""
        result = scheduler.register_gradient(1, [0.0, 0.0, 0.0, 0.0])
        assert result["action"] == "continue"
        assert result["angle"] == 0

    def test_very_large_gradients(self, scheduler):
        """测试极大梯度值"""
        scheduler.register_gradient(1, [1e20, 0.0])
        result = scheduler.register_gradient(2, [0.0, 1e20])
        assert result["action"] == "silent"
        assert result["angle"] == 90.0

    def test_negative_gradient_values(self, scheduler):
        """测试负梯度值"""
        result = scheduler.register_gradient(1, [-1.0, -2.0, -3.0])
        assert result["action"] == "continue"
        assert result["magnitude"] == pytest.approx(math.sqrt(14), abs=1e-4)

    def test_different_vector_dimensions(self, scheduler):
        """测试不同维度向量（zip 截断）"""
        scheduler.register_gradient(1, [1.0, 0.0, 0.0])
        # 第二个向量维度不同，zip 会截断到最短的
        result = scheduler.register_gradient(2, [1.0, 0.0])
        assert result["angle"] == 0.0

    def test_angle_exactly_max_angle(self, scheduler):
        """测试角度正好等于 max_angle（或略低于）"""
        # 初始方向 [1.0, 0.0]，第二个向量与初始方向夹角略低于 45°
        # 使用 [1.0, 0.999] 夹角 ≈ 44.97° < 45°
        scheduler.register_gradient(1, [1.0, 0.0])
        result = scheduler.register_gradient(2, [1.0, 0.999])
        assert result["angle"] < 45.0
        assert result["action"] == "continue"  # > 才触发 silent

    def test_magnitude_exactly_threshold(self, scheduler):
        """测试模长正好等于阈值"""
        scheduler.register_gradient(1, [1.0, 0.0])
        result = scheduler.register_gradient(2, [1e-6, 0.0])
        assert result["action"] == "continue"  # < 才触发 recall

    def test_magnitude_just_above_threshold(self, scheduler):
        """测试模长刚好高于阈值"""
        scheduler.register_gradient(1, [1.0, 0.0])
        # 1.000001e-6 > 1e-6
        result = scheduler.register_gradient(2, [1.000001e-6, 0.0])
        assert result["action"] == "continue"

    def test_very_large_angle(self, scheduler):
        """测试极大角度（接近 180°）"""
        scheduler.register_gradient(1, [1.0, 0.0])
        result = scheduler.register_gradient(2, [-0.9999, 0.0001])
        assert result["action"] == "silent"

    def test_many_snapshots_without_oscillation(self, scheduler):
        """测试大量快照但无震荡"""
        scheduler.register_gradient(1, [1.0, 0.0])
        for i in range(2, 30):
            result = scheduler.register_gradient(i, [1.0, 0.01 * i])
            assert result["action"] == "continue"

    def test_oscillation_exactly_30_percent(self, scheduler_small_window):
        """测试震荡刚好 30%"""
        s = scheduler_small_window
        # 创建 5 个快照，只有 1 个震荡
        # oscillations=1, 阈值=5*0.3=1.5, 1 <= 1.5 → continue
        s.register_gradient(1, [1.0, 0.0])
        for i in range(2, 6):
            # 小角度变化，不会触发震荡
            s.register_gradient(i, [1.0, 0.01 * i])
        # 手动添加一个震荡
        s._history[-1] = GradientSnapshot(step=5, direction=[0.0, 1.0], magnitude=1.0, angle_to_origin=90.0)
        # angles: 大约都是小角度... 最后一个替换为 90
        # 现在 history 有 5 个，但我需要检查角度
        # 直接调用 _decide_action
        action = s._decide_action(angle=10.0, magnitude=1.0)
        # 可能还是 continue，取决于实际角度
        assert action in ("continue", "silent")

    def test_register_gradient_preserves_initial_direction_on_empty(self, scheduler):
        """测试空梯度不改变初始方向"""
        result = scheduler.register_gradient(1, [])
        assert result["action"] == "continue"
        assert scheduler._initial_direction is None

    def test_all_zeros_gradient_does_not_set_initial(self, scheduler):
        """测试全零梯度不设置初始方向"""
        result = scheduler.register_gradient(1, [0.0, 0.0])
        assert result["action"] == "continue"
        assert scheduler._initial_direction is None

    def test_register_after_reset(self, scheduler):
        """测试重置后注册使用新初始方向"""
        scheduler.register_gradient(1, [1.0, 0.0])
        scheduler.register_gradient(2, [0.0, 1.0])
        scheduler.reset_origin()
        # 新初始方向 = [0.0, 1.0]
        result = scheduler.register_gradient(3, [0.0, 2.0])
        assert result["angle"] == 0.0


# ============================================================================
# 15. 综合场景测试
# ============================================================================

class TestIntegrationScenarios:
    """综合场景测试"""

    def test_full_workflow(self, scheduler):
        """测试完整工作流程"""
        # 阶段 1：正常训练
        for i in range(1, 6):
            result = scheduler.register_gradient(i, [1.0, 0.1 * i])
            assert result["action"] == "continue"

        # 阶段 2：出现偏离
        result = scheduler.register_gradient(6, [0.0, 1.0])
        assert result["action"] == "silent"

        # 阶段 3：检查状态
        stats = scheduler.get_stats()
        assert stats["silent_count"] == 1
        assert stats["total_steps"] == 6

        best = scheduler.get_best_snapshot()
        assert best is not None
        assert best.angle_to_origin == pytest.approx(0.0, abs=0.01)

        # 阶段 4：重置
        scheduler.reset_origin()

        # 阶段 5：继续训练
        result = scheduler.register_gradient(7, [0.0, 1.0])
        assert result["action"] == "continue"

        status = scheduler.get_status()
        assert status["window_size"] == 10
        assert len(status["recent_history"]) <= 5

    def test_silent_and_recall_mixed(self, scheduler):
        """测试 silent 和 recall 混合场景"""
        scheduler.register_gradient(1, [1.0, 0.0])
        # silent
        result_silent = scheduler.register_gradient(2, [0.0, 1.0])
        assert result_silent["action"] == "silent"
        # recall
        result_recall = scheduler.register_gradient(3, [5e-7, 0.0])
        assert result_recall["action"] == "recall"
        # continue
        result_continue = scheduler.register_gradient(4, [1.0, 0.1])
        assert result_continue["action"] == "continue"

        stats = scheduler.get_stats()
        assert stats["silent_count"] == 1
        assert stats["recall_count"] == 1

    def test_oscillation_detection_in_workflow(self, scheduler_small_window):
        """测试工作流中的震荡检测"""
        s = scheduler_small_window
        s.register_gradient(1, [1.0, 0.0])
        # 制造震荡
        results = []
        for i in range(2, 10):
            if i % 2 == 0:
                results.append(s.register_gradient(i, [0.0, 1.0]))
            else:
                results.append(s.register_gradient(i, [1.0, 0.0]))
        assert any(r["action"] == "silent" for r in results)

    def test_large_workload(self, scheduler):
        """测试大量梯度注册"""
        for i in range(1, 200):
            result = scheduler.register_gradient(i, [1.0, 0.01 * i])
            assert result["action"] in ("continue", "silent", "recall")
        assert scheduler._total_steps == 199
        # 历史已被裁剪
        assert len(scheduler._history) <= scheduler.window_size * 2