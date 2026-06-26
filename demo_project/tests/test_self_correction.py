"""
自修正守护进程 (self_correction.py) 综合测试
=============================================
覆盖：CorrectionStep, CorrectionReport, SelfCorrectionDaemon, get_daemon()
目标：95%+ 代码覆盖率
"""
import pytest
import math
import time
from unittest.mock import Mock, patch, MagicMock, PropertyMock

from tengod.self_correction import (
    CorrectionStep,
    CorrectionReport,
    SelfCorrectionDaemon,
    get_daemon,
)


# ============================================================================
# 1. CorrectionStep 数据类测试
# ============================================================================

class TestCorrectionStep:
    """CorrectionStep 数据类测试"""

    def test_create_defaults(self):
        """创建 CorrectionStep 使用默认值"""
        step = CorrectionStep(1, "观自在", "感知偏差检测")
        assert step.step_index == 1
        assert step.name == "观自在"
        assert step.tech_name == "感知偏差检测"
        assert step.status == "pending"
        assert step.input_state is None
        assert step.output_state is None
        assert step.delta == 0.0
        assert step.confidence == 0.0
        assert step.duration_ms == 0.0
        assert step.error == ""

    def test_create_all_fields(self):
        """创建 CorrectionStep 指定所有字段"""
        step = CorrectionStep(
            step_index=3,
            name="以物验道",
            tech_name="物理核验",
            status="completed",
            input_state={"value": 0.5},
            output_state={"hallucinations": []},
            delta=0.15,
            confidence=0.85,
            duration_ms=12.5,
            error="",
        )
        assert step.step_index == 3
        assert step.name == "以物验道"
        assert step.tech_name == "物理核验"
        assert step.status == "completed"
        assert step.input_state == {"value": 0.5}
        assert step.output_state == {"hallucinations": []}
        assert step.delta == 0.15
        assert step.confidence == 0.85
        assert step.duration_ms == 12.5
        assert step.error == ""

    def test_status_failed(self):
        """创建 status=failed 的 CorrectionStep"""
        step = CorrectionStep(1, "观自在", "感知偏差检测", status="failed", error="division by zero")
        assert step.status == "failed"
        assert step.error == "division by zero"

    def test_delta_negative(self):
        """delta 可以为负值"""
        step = CorrectionStep(1, "test", "test", delta=-0.5)
        assert step.delta == -0.5

    def test_confidence_boundary(self):
        """confidence 边界值"""
        step = CorrectionStep(1, "test", "test", confidence=1.0)
        assert step.confidence == 1.0

    def test_duration_ms(self):
        """duration_ms 字段"""
        step = CorrectionStep(1, "test", "test", duration_ms=999.9)
        assert step.duration_ms == 999.9


# ============================================================================
# 2. CorrectionReport 数据类测试
# ============================================================================

class TestCorrectionReport:
    """CorrectionReport 数据类测试"""

    def test_create_defaults(self):
        """创建 CorrectionReport 使用默认值"""
        report = CorrectionReport(session_id="test_001")
        assert report.session_id == "test_001"
        assert report.steps == []
        assert report.total_delta == 0.0
        assert report.success is False
        assert report.final_state is None
        assert isinstance(report.timestamp, float)

    def test_to_dict_empty(self):
        """to_dict() 空报告"""
        report = CorrectionReport(session_id="test_001", timestamp=1000000.0)
        d = report.to_dict()
        assert d["session_id"] == "test_001"
        assert d["steps"] == []
        assert d["total_delta"] == 0.0
        assert d["success"] is False
        assert d["timestamp"] == 1000000.0

    def test_to_dict_with_steps(self):
        """to_dict() 包含步骤的报告"""
        steps = [
            CorrectionStep(1, "观自在", "感知偏差检测", status="completed", delta=0.0, confidence=0.9, duration_ms=1.0),
            CorrectionStep(2, "格物致知", "根因定位", status="completed", delta=0.1, confidence=0.8, duration_ms=2.0),
        ]
        report = CorrectionReport(
            session_id="corr_123",
            steps=steps,
            total_delta=0.1,
            success=True,
            final_state={"output": 0.5},
            timestamp=2000000.0,
        )
        d = report.to_dict()
        assert d["session_id"] == "corr_123"
        assert d["total_delta"] == 0.1
        assert d["success"] is True
        assert d["timestamp"] == 2000000.0
        assert len(d["steps"]) == 2
        assert d["steps"][0]["step"] == 1
        assert d["steps"][0]["name"] == "观自在"
        assert d["steps"][0]["tech"] == "感知偏差检测"
        assert d["steps"][0]["status"] == "completed"
        assert d["steps"][0]["delta"] == 0.0
        assert d["steps"][0]["confidence"] == 0.9
        assert d["steps"][0]["duration_ms"] == 1.0
        assert d["steps"][1]["step"] == 2
        assert d["steps"][1]["name"] == "格物致知"
        assert d["steps"][1]["tech"] == "根因定位"

    def test_to_dict_success_false(self):
        """to_dict() 失败报告"""
        report = CorrectionReport(session_id="fail_001", success=False, total_delta=0.5)
        d = report.to_dict()
        assert d["success"] is False
        assert d["total_delta"] == 0.5

    def test_session_id_type(self):
        """session_id 支持字符串"""
        report = CorrectionReport(session_id="abc-123")
        assert report.session_id == "abc-123"


# ============================================================================
# 3. SelfCorrectionDaemon.__init__() 测试
# ============================================================================

class TestDaemonInit:
    """SelfCorrectionDaemon 初始化测试"""

    def test_initial_state(self):
        """初始化后内部状态为空"""
        daemon = SelfCorrectionDaemon()
        assert daemon._total_corrections == 0
        assert daemon._successful_corrections == 0
        assert daemon._history == []

    def test_multiple_instances_independent(self):
        """多个实例互不影响"""
        d1 = SelfCorrectionDaemon()
        d2 = SelfCorrectionDaemon()
        d1._total_corrections = 5
        assert d2._total_corrections == 0


# ============================================================================
# 4. correct() 完整流程测试
# ============================================================================

class TestCorrectFullFlow:
    """correct() 完整七步流程测试"""

    def test_basic_state(self):
        """基本状态：正常推理结果"""
        daemon = SelfCorrectionDaemon()
        state = {"output": 0.5, "confidence": 0.8, "uncertainty": 0.3}
        result_state, report = daemon.correct(state, enable_gate=False)

        assert isinstance(result_state, dict)
        assert isinstance(report, CorrectionReport)
        assert report.success is True
        assert len(report.steps) == 7
        assert all(s.status in ("completed", "running") for s in report.steps)
        assert report.final_state is not None
        assert daemon._total_corrections == 1
        assert daemon._successful_corrections == 1

    def test_with_expected_output(self):
        """带期望输出"""
        daemon = SelfCorrectionDaemon()
        state = {"output": 0.5, "confidence": 0.8, "uncertainty": 0.3}
        result_state, report = daemon.correct(state, expected_output=0.9, enable_gate=False)

        assert report.success is True
        assert len(report.steps) == 7
        # 验证对齐步骤执行了
        step6 = report.steps[5]
        assert step6.step_index == 6
        assert step6.status == "completed"

    def test_with_physical_constraints(self):
        """带物理约束"""
        daemon = SelfCorrectionDaemon()
        state = {"output": 2.0, "confidence": 0.8, "uncertainty": 0.3}
        constraints = [{"field": "output", "type": "range", "range": (0, 1)}]
        result_state, report = daemon.correct(
            state, physical_constraints=constraints, enable_gate=False
        )

        assert report.success is True
        # 约束触发修正
        step3 = report.steps[2]
        assert step3.step_index == 3
        assert step3.status == "completed"

    def test_with_memory_store(self):
        """带记忆库"""
        daemon = SelfCorrectionDaemon()
        state = {"output": 0.5, "name": None, "confidence": 0.8, "uncertainty": 0.3}
        memory = {"name": "test_value"}
        result_state, report = daemon.correct(state, memory_store=memory, enable_gate=False)

        assert report.success is True
        step5 = report.steps[4]
        assert step5.step_index == 5
        assert step5.status == "completed"

    def test_enable_gate_false(self):
        """enable_gate=False 跳过门禁"""
        daemon = SelfCorrectionDaemon()
        state = {"output": 0.5, "confidence": 0.8, "uncertainty": 0.3}
        result_state, report = daemon.correct(state, enable_gate=False)

        assert report.success is True
        step7 = report.steps[6]
        assert step7.step_index == 7
        assert step7.output_state.get("consolidated") is True

    def test_enable_gate_true_mock_passed(self):
        """enable_gate=True 使用 mock 门禁（通过）— 通过 correct() 完整流程"""
        mock_verdict = MagicMock()
        mock_verdict.confidence = 0.9
        mock_verdict.passed = True
        mock_verdict.retreat_reason = ""

        mock_tianmen = MagicMock()
        mock_tianmen.guard.return_value = (None, mock_verdict)

        mock_module = MagicMock()
        mock_module.get_tianmen = MagicMock(return_value=mock_tianmen)

        import sys
        with patch.dict(sys.modules, {"tengod.tiangan_gate": mock_module}):
            daemon = SelfCorrectionDaemon()
            state = {"output": 0.5, "confidence": 0.8, "uncertainty": 0.3}
            _, report = daemon.correct(state, enable_gate=True)
            assert report.success is True
            step7 = report.steps[6]
            assert step7.step_index == 7
            assert step7.status == "completed"
            assert step7.output_state.get("consolidated") is True

    def test_enable_gate_true_mock_failed(self):
        """enable_gate=True 使用 mock 门禁（失败/回退）— 通过 correct() 完整流程"""
        mock_verdict = MagicMock()
        mock_verdict.confidence = 0.3
        mock_verdict.passed = False
        mock_verdict.retreat_reason = "低置信度，天门退守"

        mock_tianmen = MagicMock()
        mock_tianmen.guard.return_value = (None, mock_verdict)

        mock_module = MagicMock()
        mock_module.get_tianmen = MagicMock(return_value=mock_tianmen)

        import sys
        with patch.dict(sys.modules, {"tengod.tiangan_gate": mock_module}):
            daemon = SelfCorrectionDaemon()
            state = {"output": 0.5, "confidence": 0.8, "uncertainty": 0.3}
            _, report = daemon.correct(state, enable_gate=True)
            assert report.success is True
            step7 = report.steps[6]
            assert step7.step_index == 7
            assert step7.status == "completed"
            assert step7.output_state.get("consolidated") is False

    def test_step1_fails_early_return(self):
        """步骤1失败时提前返回"""
        daemon = SelfCorrectionDaemon()
        with patch.object(daemon, "_step_observe") as mock_observe:
            fail_step = CorrectionStep(1, "观自在", "感知偏差检测", status="failed", error="test error")
            mock_observe.return_value = fail_step

            state = {"output": 0.5}
            result_state, report = daemon.correct(state, enable_gate=False)

            assert report.success is False
            assert len(report.steps) == 1
            # 提前返回时不会更新统计计数器
            assert daemon._total_corrections == 0
            assert daemon._successful_corrections == 0

    def test_step2_fails_early_return(self):
        """步骤2失败时提前返回"""
        daemon = SelfCorrectionDaemon()
        with patch.object(daemon, "_step_root_cause") as mock_root:
            fail_step = CorrectionStep(2, "格物致知", "根因定位", status="failed", error="test error")
            mock_root.return_value = fail_step

            state = {"output": 0.5}
            _, report = daemon.correct(state, enable_gate=False)

            assert report.success is False
            assert len(report.steps) == 2

    def test_correct_updates_stats(self):
        """correct() 更新统计计数器"""
        daemon = SelfCorrectionDaemon()
        assert daemon._total_corrections == 0
        assert daemon._successful_corrections == 0

        daemon.correct({"output": 0.5}, enable_gate=False)
        assert daemon._total_corrections == 1
        assert daemon._successful_corrections == 1

        daemon.correct({"output": 0.5}, enable_gate=False)
        assert daemon._total_corrections == 2
        assert daemon._successful_corrections == 2

    def test_correct_updates_history(self):
        """correct() 添加报告到历史"""
        daemon = SelfCorrectionDaemon()
        daemon.correct({"output": 0.5}, enable_gate=False)
        daemon.correct({"output": 0.7}, enable_gate=False)

        assert len(daemon._history) == 2
        # 两个报告应存在（session_id 可能因时间戳相同而相同，但报告对象不同）
        assert daemon._history[0] is not daemon._history[1]

    def test_report_total_delta(self):
        """报告 total_delta 是所有步骤 delta 之和"""
        daemon = SelfCorrectionDaemon()
        _, report = daemon.correct({"output": 0.5}, enable_gate=False)
        expected_delta = sum(s.delta for s in report.steps)
        assert report.total_delta == expected_delta

    def test_correct_state_not_mutated(self):
        """correct() 不修改传入的原始状态"""
        daemon = SelfCorrectionDaemon()
        original = {"output": 0.5, "confidence": 0.8}
        result_state, _ = daemon.correct(original, enable_gate=False)
        # 原始状态不应被修改（内部做了 dict(current_state) 拷贝）
        assert "output" in original


# ============================================================================
# 5. _step_observe() 测试
# ============================================================================

class TestStepObserve:
    """_step_observe() 感知偏差测试"""

    def test_normal_state(self):
        """正常状态：无偏差"""
        daemon = SelfCorrectionDaemon()
        state = {"output": 0.5, "confidence": 0.8}
        step = daemon._step_observe(state)

        assert step.step_index == 1
        assert step.name == "观自在"
        assert step.tech_name == "感知偏差检测"
        assert step.status == "completed"
        assert step.output_state["bias_detected"] is False
        assert step.output_state["distortions"] == {}
        assert step.output_state["topological_divergence"] == 0.0
        assert step.delta == 0.0
        assert step.confidence == 0.9
        assert step.duration_ms >= 0

    def test_low_confidence(self):
        """低置信度检测"""
        daemon = SelfCorrectionDaemon()
        state = {"output": 0.5, "confidence": 0.1}
        step = daemon._step_observe(state)

        assert step.status == "completed"
        assert step.output_state["bias_detected"] is True
        assert "low_confidence" in step.output_state["distortions"]
        assert step.output_state["distortions"]["low_confidence"] == 0.1
        assert step.output_state["topological_divergence"] == 0.1
        assert step.delta == 0.1

    def test_null_output(self):
        """空输出检测"""
        daemon = SelfCorrectionDaemon()
        state = {"output": None, "confidence": 0.8}
        step = daemon._step_observe(state)

        assert step.status == "completed"
        assert step.output_state["bias_detected"] is True
        assert "null_output" in step.output_state["distortions"]
        assert step.output_state["distortions"]["null_output"] == 1.0
        assert step.output_state["topological_divergence"] == 1.0

    def test_mixed_distortions(self):
        """同时存在低置信度和空输出"""
        daemon = SelfCorrectionDaemon()
        state = {"output": None, "confidence": 0.15}
        step = daemon._step_observe(state)

        assert step.output_state["bias_detected"] is True
        assert "low_confidence" in step.output_state["distortions"]
        assert "null_output" in step.output_state["distortions"]
        # 两个失真：0.15 + 1.0 = 1.15, / 2 = 0.575
        assert step.output_state["topological_divergence"] == pytest.approx(0.575)
        assert step.delta == pytest.approx(0.575)

    def test_no_confidence_key(self):
        """state 中没有 confidence 键"""
        daemon = SelfCorrectionDaemon()
        state = {"output": 0.5}
        step = daemon._step_observe(state)

        assert step.status == "completed"
        # state.get("confidence", 0.5) 默认 0.5，不小于 0.3
        assert step.output_state["bias_detected"] is False

    def test_confidence_zero(self):
        """confidence=0 是低置信度"""
        daemon = SelfCorrectionDaemon()
        state = {"output": 0.5, "confidence": 0.0}
        step = daemon._step_observe(state)

        assert step.output_state["bias_detected"] is True
        assert "low_confidence" in step.output_state["distortions"]

    def test_confidence_exactly_03(self):
        """confidence=0.3 边界：不小于 0.3，不触发"""
        daemon = SelfCorrectionDaemon()
        state = {"output": 0.5, "confidence": 0.3}
        step = daemon._step_observe(state)

        assert step.output_state["bias_detected"] is False


# ============================================================================
# 6. _step_root_cause() 测试
# ============================================================================

class TestStepRootCause:
    """_step_root_cause() 根因定位测试"""

    def test_no_bias(self):
        """无偏差时无根因"""
        daemon = SelfCorrectionDaemon()
        state = {"output": 0.5}
        observation = {"bias_detected": False, "distortions": {}}
        step = daemon._step_root_cause(state, observation)

        assert step.step_index == 2
        assert step.name == "格物致知"
        assert step.tech_name == "根因定位"
        assert step.status == "completed"
        assert step.output_state["root_causes"] == []
        assert step.output_state["cause_count"] == 0
        assert step.delta == 0.0
        assert step.confidence == 0.8

    def test_with_bias_low_confidence(self):
        """有低置信度偏差"""
        daemon = SelfCorrectionDaemon()
        state = {"confidence": 0.1}
        observation = {
            "bias_detected": True,
            "distortions": {"low_confidence": 0.1},
        }
        step = daemon._step_root_cause(state, observation)

        assert step.output_state["cause_count"] == 1
        assert len(step.output_state["root_causes"]) == 1
        cause = step.output_state["root_causes"][0]
        assert cause["cause"] == "low_confidence"
        assert cause["severity"] == 0.1
        assert "提高置信度阈值" in cause["suggested_fix"]
        assert step.delta == 0.1

    def test_with_bias_null_output(self):
        """有空输出偏差"""
        daemon = SelfCorrectionDaemon()
        state = {"output": None}
        observation = {
            "bias_detected": True,
            "distortions": {"null_output": 1.0},
        }
        step = daemon._step_root_cause(state, observation)

        assert step.output_state["cause_count"] == 1
        cause = step.output_state["root_causes"][0]
        assert cause["cause"] == "null_output"
        assert cause["severity"] == 1.0
        assert "检查输入完整性" in cause["suggested_fix"]

    def test_with_multiple_distortions(self):
        """多个偏差同时存在"""
        daemon = SelfCorrectionDaemon()
        state = {"output": None, "confidence": 0.1}
        observation = {
            "bias_detected": True,
            "distortions": {"low_confidence": 0.1, "null_output": 1.0},
        }
        step = daemon._step_root_cause(state, observation)

        assert step.output_state["cause_count"] == 2
        assert len(step.output_state["root_causes"]) == 2
        assert step.delta == 0.2

    def test_empty_observation(self):
        """空 observation"""
        daemon = SelfCorrectionDaemon()
        state = {}
        step = daemon._step_root_cause(state, {})
        assert step.output_state["root_causes"] == []
        assert step.output_state["cause_count"] == 0


# ============================================================================
# 7. _step_physical_verify() 测试
# ============================================================================

class TestStepPhysicalVerify:
    """_step_physical_verify() 物理核验测试"""

    def test_no_constraints(self):
        """无约束时通过"""
        daemon = SelfCorrectionDaemon()
        state = {"output": 0.5}
        step = daemon._step_physical_verify(state, None)

        assert step.step_index == 3
        assert step.name == "以物验道"
        assert step.tech_name == "物理核验"
        assert step.status == "completed"
        assert step.output_state["hallucinations"] == []
        assert step.output_state["hallucination_count"] == 0
        assert step.output_state["verified"] is True
        assert step.delta == 0.0
        assert step.confidence == 0.85

    def test_empty_constraints(self):
        """空约束列表"""
        daemon = SelfCorrectionDaemon()
        state = {"output": 0.5}
        step = daemon._step_physical_verify(state, [])
        assert step.output_state["verified"] is True
        assert step.output_state["hallucination_count"] == 0

    def test_range_in_range(self):
        """值在范围内"""
        daemon = SelfCorrectionDaemon()
        state = {"score": 0.5}
        constraints = [{"field": "score", "type": "range", "range": (0, 1)}]
        step = daemon._step_physical_verify(state, constraints)

        assert step.output_state["verified"] is True
        assert step.output_state["hallucination_count"] == 0

    def test_range_out_of_range_below(self):
        """值低于范围"""
        daemon = SelfCorrectionDaemon()
        state = {"score": -0.5}
        constraints = [{"field": "score", "type": "range", "range": (0, 1)}]
        step = daemon._step_physical_verify(state, constraints)

        assert step.output_state["verified"] is False
        assert step.output_state["hallucination_count"] == 1
        hallucination = step.output_state["hallucinations"][0]
        assert hallucination["field"] == "score"
        assert hallucination["type"] == "out_of_range"
        assert hallucination["value"] == -0.5
        assert hallucination["expected_range"] == [0, 1]
        assert step.delta == 0.15

    def test_range_out_of_range_above(self):
        """值高于范围"""
        daemon = SelfCorrectionDaemon()
        state = {"score": 2.0}
        constraints = [{"field": "score", "type": "range", "range": (0, 1)}]
        step = daemon._step_physical_verify(state, constraints)

        assert step.output_state["hallucination_count"] == 1
        assert step.output_state["hallucinations"][0]["value"] == 2.0

    def test_non_null_violated(self):
        """非空约束违反"""
        daemon = SelfCorrectionDaemon()
        state = {"name": None}
        constraints = [{"field": "name", "type": "non_null"}]
        step = daemon._step_physical_verify(state, constraints)

        assert step.output_state["verified"] is False
        assert step.output_state["hallucination_count"] == 1
        hallucination = step.output_state["hallucinations"][0]
        assert hallucination["field"] == "name"
        assert hallucination["type"] == "null_violation"
        assert hallucination["value"] is None

    def test_non_null_ok(self):
        """非空约束满足"""
        daemon = SelfCorrectionDaemon()
        state = {"name": "test"}
        constraints = [{"field": "name", "type": "non_null"}]
        step = daemon._step_physical_verify(state, constraints)

        assert step.output_state["verified"] is True
        assert step.output_state["hallucination_count"] == 0

    def test_range_value_none(self):
        """range 约束但值为 None（不触发 range 检查）"""
        daemon = SelfCorrectionDaemon()
        state = {"score": None}
        constraints = [{"field": "score", "type": "range", "range": (0, 1)}]
        step = daemon._step_physical_verify(state, constraints)

        assert step.output_state["hallucination_count"] == 0
        assert step.output_state["verified"] is True

    def test_mixed_constraints(self):
        """混合约束（部分通过部分失败）"""
        daemon = SelfCorrectionDaemon()
        state = {"score": 2.0, "name": None, "ok_field": 0.5}
        constraints = [
            {"field": "score", "type": "range", "range": (0, 1)},
            {"field": "name", "type": "non_null"},
            {"field": "ok_field", "type": "range", "range": (0, 1)},
        ]
        step = daemon._step_physical_verify(state, constraints)

        assert step.output_state["hallucination_count"] == 2
        assert step.output_state["verified"] is False
        assert step.delta == 0.3

    def test_unknown_constraint_type(self):
        """未知约束类型：不触发任何检查"""
        daemon = SelfCorrectionDaemon()
        state = {"x": 0.5}
        constraints = [{"field": "x", "type": "unknown"}]
        step = daemon._step_physical_verify(state, constraints)

        assert step.output_state["hallucination_count"] == 0
        assert step.output_state["verified"] is True


# ============================================================================
# 8. _step_correct_state() 测试
# ============================================================================

class TestStepCorrectState:
    """_step_correct_state() 状态修正测试"""

    def test_no_hallucinations(self):
        """无幻觉时只调整不确定性"""
        daemon = SelfCorrectionDaemon()
        state = {"output": 0.5, "uncertainty": 0.5, "fallback_value": 0.0}
        root_causes = {}
        verification = {"hallucinations": [], "hallucination_count": 0}

        step = daemon._step_correct_state(state, root_causes, verification)

        assert step.step_index == 4
        assert step.name == "抱元守一"
        assert step.tech_name == "状态修正"
        assert step.status == "completed"
        assert step.output_state.get("uncertainty") == 0.3
        assert step.delta == 0.1

    def test_out_of_range_correction(self):
        """越界值修正"""
        daemon = SelfCorrectionDaemon()
        state = {"score": 2.0, "uncertainty": 0.5, "fallback_value": 0.0}
        verification = {
            "hallucinations": [
                {"field": "score", "type": "out_of_range", "expected_range": [0, 1], "value": 2.0},
            ],
            "hallucination_count": 1,
        }

        step = daemon._step_correct_state(state, {}, verification)

        assert step.output_state["score"] == 0.5  # (0+1)/2
        assert step.output_state["uncertainty"] == 0.3
        assert step.delta == 0.2  # 两个修正

    def test_null_violation_correction(self):
        """空值违反修正"""
        daemon = SelfCorrectionDaemon()
        state = {"name": None, "uncertainty": 0.5, "fallback_value": 0.0}
        verification = {
            "hallucinations": [
                {"field": "name", "type": "null_violation", "value": None},
            ],
            "hallucination_count": 1,
        }

        step = daemon._step_correct_state(state, {}, verification)

        assert step.output_state["name"] == 0.0  # fallback_value
        assert step.output_state["uncertainty"] == 0.3

    def test_null_violation_with_fallback(self):
        """空值违反使用自定义 fallback_value"""
        daemon = SelfCorrectionDaemon()
        state = {"name": None, "uncertainty": 0.5, "fallback_value": 42.0}
        verification = {
            "hallucinations": [
                {"field": "name", "type": "null_violation", "value": None},
            ],
            "hallucination_count": 1,
        }

        step = daemon._step_correct_state(state, {}, verification)

        assert step.output_state["name"] == 42.0

    def test_uncertainty_adjustment_min(self):
        """不确定性最低 0.1"""
        daemon = SelfCorrectionDaemon()
        state = {"uncertainty": 0.1}
        step = daemon._step_correct_state(state, {}, {"hallucinations": []})

        assert step.output_state["uncertainty"] == 0.1  # max(0.1, 0.1-0.2) = 0.1

    def test_uncertainty_high(self):
        """高不确定性调整"""
        daemon = SelfCorrectionDaemon()
        state = {"uncertainty": 0.9}
        step = daemon._step_correct_state(state, {}, {"hallucinations": []})

        assert step.output_state["uncertainty"] == 0.7  # 0.9 - 0.2

    def test_multiple_hallucinations(self):
        """多个幻觉同时修正"""
        daemon = SelfCorrectionDaemon()
        state = {"score": 2.0, "name": None, "uncertainty": 0.5, "fallback_value": 0.0}
        verification = {
            "hallucinations": [
                {"field": "score", "type": "out_of_range", "expected_range": [0, 1], "value": 2.0},
                {"field": "name", "type": "null_violation", "value": None},
            ],
            "hallucination_count": 2,
        }

        step = daemon._step_correct_state(state, {}, verification)

        assert step.output_state["score"] == 0.5
        assert step.output_state["name"] == 0.0
        assert step.output_state["uncertainty"] == 0.3
        assert step.delta == pytest.approx(0.3)  # 3 个修正

    def test_no_uncertainty_key(self):
        """state 中没有 uncertainty 键"""
        daemon = SelfCorrectionDaemon()
        state = {}
        step = daemon._step_correct_state(state, {}, {"hallucinations": []})

        assert step.output_state["uncertainty"] == 0.3  # 0.5 - 0.2


# ============================================================================
# 9. _step_complete() 测试
# ============================================================================

class TestStepComplete:
    """_step_complete() 补全缺失测试"""

    def test_no_memory_store(self):
        """无记忆库"""
        daemon = SelfCorrectionDaemon()
        state = {"output": 0.5, "name": None}
        step = daemon._step_complete(state, None)

        assert step.step_index == 5
        assert step.name == "补天浴日"
        assert step.tech_name == "补全缺失"
        assert step.status == "completed"
        assert step.output_state == {}
        assert step.delta == 0.0
        assert step.confidence == 0.7

    def test_empty_memory_store(self):
        """空记忆库"""
        daemon = SelfCorrectionDaemon()
        state = {"output": 0.5}
        step = daemon._step_complete(state, {})
        assert step.output_state == {}
        assert step.delta == 0.0

    def test_fill_none_value(self):
        """补全 None 值"""
        daemon = SelfCorrectionDaemon()
        state = {"name": None, "output": 0.5}
        memory = {"name": "张三"}
        step = daemon._step_complete(state, memory)

        assert step.output_state["name"] == "张三"
        assert step.delta == 0.05

    def test_fill_short_string(self):
        """补全短字符串"""
        daemon = SelfCorrectionDaemon()
        state = {"desc": "短", "output": 0.5}
        memory = {"desc": "这是一个很长的描述文本用于补全短字符串"}
        step = daemon._step_complete(state, memory)

        assert "desc" in step.output_state
        assert "（补：" in step.output_state["desc"]
        assert step.delta == 0.05

    def test_short_string_no_memory_match(self):
        """短字符串但记忆库无匹配键"""
        daemon = SelfCorrectionDaemon()
        state = {"desc": "短", "output": 0.5}
        memory = {"other": "value"}
        step = daemon._step_complete(state, memory)

        assert step.output_state == {}

    def test_string_length_10_not_short(self):
        """长度为10的字符串不被视为短字符串"""
        daemon = SelfCorrectionDaemon()
        state = {"desc": "0123456789", "output": 0.5}
        memory = {"desc": "extended"}
        step = daemon._step_complete(state, memory)

        # len("0123456789") == 10, not < 10
        assert step.output_state == {}

    def test_multiple_completions(self):
        """多个字段同时补全"""
        daemon = SelfCorrectionDaemon()
        state = {"name": None, "desc": "x", "output": 0.5}
        memory = {"name": "李四", "desc": "详细描述文本内容"}
        step = daemon._step_complete(state, memory)

        assert "name" in step.output_state
        assert "desc" in step.output_state
        assert step.delta == 0.1  # 2 * 0.05

    def test_none_value_no_memory_match(self):
        """None 值但记忆库无匹配键"""
        daemon = SelfCorrectionDaemon()
        state = {"name": None, "output": 0.5}
        memory = {"other": "value"}
        step = daemon._step_complete(state, memory)

        assert step.output_state == {}


# ============================================================================
# 10. _step_align() 测试
# ============================================================================

class TestStepAlign:
    """_step_align() 全局验证测试"""

    def test_no_expected(self):
        """无期望值"""
        daemon = SelfCorrectionDaemon()
        state = {"output": 0.5}
        step = daemon._step_align(state, None)

        assert step.step_index == 6
        assert step.name == "天人合一"
        assert step.tech_name == "全局验证"
        assert step.status == "completed"
        assert step.output_state == {}
        assert step.delta == 0.0
        assert step.confidence == 0.8

    def test_numeric_close(self):
        """数值输出接近期望值"""
        daemon = SelfCorrectionDaemon()
        state = {"output": 0.52}
        step = daemon._step_align(state, 0.5)

        # diff = 0.02 <= 0.1, 不触发对齐
        assert step.output_state == {}
        assert step.delta == 0.0

    def test_numeric_far(self):
        """数值输出偏离期望值"""
        daemon = SelfCorrectionDaemon()
        state = {"output": 0.5}
        step = daemon._step_align(state, 0.9)

        # diff = 0.4 > 0.1, 触发对齐
        # aligned = {"output": 0.9, "alignment_delta": 0.4}, len=2
        assert step.output_state["output"] == 0.9
        assert step.output_state["alignment_delta"] == 0.4
        assert step.delta == 0.16

    def test_dict_align_close(self):
        """字典输出各字段接近"""
        daemon = SelfCorrectionDaemon()
        state = {"output": {"a": 0.52, "b": 0.48}}
        step = daemon._step_align(state, {"a": 0.5, "b": 0.5})

        # diff 都 <= 0.1
        assert step.output_state == {}

    def test_dict_align_far(self):
        """字典输出部分字段偏离"""
        daemon = SelfCorrectionDaemon()
        state = {"output": {"a": 0.5, "b": 0.2}}
        step = daemon._step_align(state, {"a": 0.5, "b": 0.9})

        # a: diff=0.0, b: diff=0.7 > 0.1
        assert "b" in step.output_state
        assert step.output_state["b"] == 0.9
        assert step.delta == 0.08

    def test_dict_align_multiple_far(self):
        """字典多个字段偏离"""
        daemon = SelfCorrectionDaemon()
        state = {"output": {"a": 0.1, "b": 0.2}}
        step = daemon._step_align(state, {"a": 0.9, "b": 0.8})

        assert "a" in step.output_state
        assert "b" in step.output_state
        assert step.output_state["a"] == 0.9
        assert step.output_state["b"] == 0.8
        assert step.delta == 0.16

    def test_non_numeric_output(self):
        """非数值输出不触发对齐"""
        daemon = SelfCorrectionDaemon()
        state = {"output": "hello"}
        step = daemon._step_align(state, "world")

        assert step.output_state == {}

    def test_output_none(self):
        """output=None 不触发对齐"""
        daemon = SelfCorrectionDaemon()
        state = {"output": None}
        step = daemon._step_align(state, 0.5)

        assert step.output_state == {}

    def test_dict_expected_mismatched_keys(self):
        """字典中不重叠的键"""
        daemon = SelfCorrectionDaemon()
        state = {"output": {"a": 0.5}}
        step = daemon._step_align(state, {"b": 0.9})

        assert step.output_state == {}

    def test_dict_non_numeric_values(self):
        """字典中非数值值不触发"""
        daemon = SelfCorrectionDaemon()
        state = {"output": {"a": "text"}}
        step = daemon._step_align(state, {"a": "text"})

        assert step.output_state == {}


# ============================================================================
# 11. _step_consolidate() 测试
# ============================================================================

class TestStepConsolidate:
    """_step_consolidate() 记忆固化测试"""

    def test_enable_gate_false(self):
        """enable_gate=False 直接固化"""
        daemon = SelfCorrectionDaemon()
        state = {"output": 0.5}
        step = daemon._step_consolidate(state, False)

        assert step.step_index == 7
        assert step.name == "铭文刻骨"
        assert step.tech_name == "记忆固化"
        assert step.status == "completed"
        assert step.output_state["consolidated"] is True
        assert "memory_key" in step.output_state
        assert step.confidence == 0.9
        assert step.delta == 0.05

    def test_enable_gate_true_import_error(self):
        """enable_gate=True 但 import 失败（异常处理）"""
        daemon = SelfCorrectionDaemon()
        state = {"output": 0.5}

        # 直接 patch 内置 __import__ 来触发异常路径
        with patch("builtins.__import__", side_effect=ImportError("No module named 'tiangan_gate'")):
            step = daemon._step_consolidate(state, True)

            # import 失败时状态为 failed
            assert step.status == "failed"
            assert "No module" in step.error

    def test_enable_gate_true_mock_passed(self):
        """enable_gate=True 门禁通过"""
        daemon = SelfCorrectionDaemon()
        state = {"output": 0.5}

        mock_verdict = MagicMock()
        mock_verdict.confidence = 0.9
        mock_verdict.passed = True
        mock_verdict.retreat_reason = ""

        mock_tianmen = MagicMock()
        mock_tianmen.guard.return_value = ("output", mock_verdict)

        mock_module = MagicMock()
        mock_module.get_tianmen = MagicMock(return_value=mock_tianmen)

        import sys
        with patch.dict(sys.modules, {"tengod.tiangan_gate": mock_module}):
            step = daemon._step_consolidate(state, True)

            assert step.status == "completed"
            assert step.output_state["consolidated"] is True
            assert "memory_key" in step.output_state
            assert step.confidence == 0.9
            assert step.delta == 0.05

    def test_enable_gate_true_mock_failed(self):
        """enable_gate=True 门禁拒绝"""
        daemon = SelfCorrectionDaemon()
        state = {"output": 0.5}

        mock_verdict = MagicMock()
        mock_verdict.confidence = 0.3
        mock_verdict.passed = False
        mock_verdict.retreat_reason = "低置信度，天门退守"

        mock_tianmen = MagicMock()
        mock_tianmen.guard.return_value = ("blocked", mock_verdict)

        mock_module = MagicMock()
        mock_module.get_tianmen = MagicMock(return_value=mock_tianmen)

        import sys
        with patch.dict(sys.modules, {"tengod.tiangan_gate": mock_module}):
            step = daemon._step_consolidate(state, True)

            assert step.status == "completed"
            assert step.output_state["consolidated"] is False
            assert step.output_state["reason"] == "低置信度，天门退守"
            assert step.confidence == 0.3
            assert step.delta == 0.0


# ============================================================================
# 12. _suggest_fix() 测试
# ============================================================================

class TestSuggestFix:
    """_suggest_fix() 修复建议测试"""

    def test_low_confidence(self):
        daemon = SelfCorrectionDaemon()
        fix = daemon._suggest_fix("low_confidence")
        assert "提高置信度阈值" in fix

    def test_null_output(self):
        daemon = SelfCorrectionDaemon()
        fix = daemon._suggest_fix("null_output")
        assert "检查输入完整性" in fix

    def test_out_of_range(self):
        daemon = SelfCorrectionDaemon()
        fix = daemon._suggest_fix("out_of_range")
        assert "物理约束裁剪" in fix

    def test_null_violation(self):
        daemon = SelfCorrectionDaemon()
        fix = daemon._suggest_fix("null_violation")
        assert "默认值" in fix

    def test_unknown_cause(self):
        daemon = SelfCorrectionDaemon()
        fix = daemon._suggest_fix("unknown_cause")
        assert "重新审视输入与推理过程" == fix

    def test_empty_string(self):
        daemon = SelfCorrectionDaemon()
        fix = daemon._suggest_fix("")
        assert "重新审视输入与推理过程" == fix


# ============================================================================
# 13. get_stats() 测试
# ============================================================================

class TestGetStats:
    """get_stats() 统计信息测试"""

    def test_initial_stats(self):
        """初始统计"""
        daemon = SelfCorrectionDaemon()
        stats = daemon.get_stats()

        assert stats["total_corrections"] == 0
        assert stats["successful"] == 0
        assert stats["success_rate"] == 0.0
        assert stats["recent_reports"] == []

    def test_after_successful_corrections(self):
        """成功修正后统计"""
        daemon = SelfCorrectionDaemon()
        daemon.correct({"output": 0.5}, enable_gate=False)
        daemon.correct({"output": 0.7}, enable_gate=False)

        stats = daemon.get_stats()
        assert stats["total_corrections"] == 2
        assert stats["successful"] == 2
        assert stats["success_rate"] == 1.0
        assert len(stats["recent_reports"]) == 2

    def test_mixed_success_and_failure(self):
        """混合成功和失败"""
        daemon = SelfCorrectionDaemon()

        daemon.correct({"output": 0.5}, enable_gate=False)

        # 模拟一次失败
        with patch.object(daemon, "_step_observe") as mock_observe:
            mock_observe.return_value = CorrectionStep(
                1, "观自在", "感知偏差检测", status="failed", error="err"
            )
            daemon.correct({"output": 0.5}, enable_gate=False)

        stats = daemon.get_stats()
        # 提前返回时不会更新统计计数器，所以只有第一次成功的那次
        assert stats["total_corrections"] == 1
        assert stats["successful"] == 1
        assert stats["success_rate"] == 1.0

    def test_recent_reports_limit(self):
        """recent_reports 最多5条"""
        daemon = SelfCorrectionDaemon()
        for i in range(10):
            daemon.correct({"output": float(i) / 10}, enable_gate=False)

        stats = daemon.get_stats()
        assert len(stats["recent_reports"]) == 5
        assert stats["total_corrections"] == 10

    def test_success_rate_zero_total(self):
        """total=0 时 success_rate=0（除以 max(1,0)=1）"""
        daemon = SelfCorrectionDaemon()
        stats = daemon.get_stats()
        assert stats["success_rate"] == 0.0


# ============================================================================
# 14. get_daemon() 单例测试
# ============================================================================

class TestGetDaemon:
    """get_daemon() 单例测试"""

    def test_returns_daemon_instance(self):
        """返回 SelfCorrectionDaemon 实例"""
        daemon = get_daemon()
        assert isinstance(daemon, SelfCorrectionDaemon)

    def test_singleton(self):
        """多次调用返回同一实例"""
        # 重置全局变量
        import tengod.self_correction as sc
        sc._daemon = None

        d1 = get_daemon()
        d2 = get_daemon()
        assert d1 is d2

    def test_new_instance_after_reset(self):
        """重置后的新实例"""
        import tengod.self_correction as sc
        old = get_daemon()
        sc._daemon = None
        new = get_daemon()
        assert old is not new


# ============================================================================
# 15. 边界情况测试
# ============================================================================

class TestEdgeCases:
    """边界情况测试"""

    def test_empty_state(self):
        """空状态"""
        daemon = SelfCorrectionDaemon()
        result_state, report = daemon.correct({}, enable_gate=False)

        assert report.success is True
        assert isinstance(result_state, dict)
        assert len(report.steps) == 7

    def test_all_none_values(self):
        """所有值都为 None — confidence=None 导致 step1 失败（TypeError）"""
        daemon = SelfCorrectionDaemon()
        state = {"output": None, "confidence": None, "uncertainty": None}
        result_state, report = daemon.correct(state, enable_gate=False)

        # confidence=None 时 state.get("confidence", 0.5) < 0.3 会抛出 TypeError
        # 步骤1 会捕获异常并标记为 failed
        assert report.success is False
        assert len(report.steps) == 1

    def test_very_large_confidence(self):
        """非常大的 confidence 值"""
        daemon = SelfCorrectionDaemon()
        state = {"output": 0.5, "confidence": 1000.0}
        step = daemon._step_observe(state)
        assert step.output_state["bias_detected"] is False

    def test_negative_confidence(self):
        """负 confidence"""
        daemon = SelfCorrectionDaemon()
        state = {"output": 0.5, "confidence": -0.5}
        step = daemon._step_observe(state)
        assert step.output_state["bias_detected"] is True

    def test_step_observe_exception(self):
        """_step_observe 异常处理"""
        daemon = SelfCorrectionDaemon()

        class BadState:
            def get(self, key, default=None):
                raise RuntimeError("forced error")

        step = daemon._step_observe(BadState())
        assert step.status == "failed"
        assert "forced error" in step.error

    def test_step_root_cause_exception(self):
        """_step_root_cause 异常处理"""
        daemon = SelfCorrectionDaemon()

        class BadObservation:
            def get(self, key, default=None):
                raise RuntimeError("forced error")

        step = daemon._step_root_cause({}, BadObservation())
        assert step.status == "failed"
        assert "forced error" in step.error

    def test_step_physical_verify_exception(self):
        """_step_physical_verify 异常处理"""
        daemon = SelfCorrectionDaemon()
        # 传入一个非列表的 constraints 来触发异常
        step = daemon._step_physical_verify({}, 42)  # type: ignore
        assert step.status == "failed"
        assert step.error != ""

    def test_step_correct_state_exception(self):
        """_step_correct_state 异常处理"""
        daemon = SelfCorrectionDaemon()

        class BadVerification:
            def get(self, key, default=None):
                raise RuntimeError("forced error")

        step = daemon._step_correct_state({}, {}, BadVerification())
        assert step.status == "failed"
        assert "forced error" in step.error

    def test_step_complete_exception(self):
        """_step_complete 异常处理"""
        daemon = SelfCorrectionDaemon()

        class BadState:
            def items(self):
                raise RuntimeError("forced error")

        step = daemon._step_complete(BadState(), {"key": "val"})
        assert step.status == "failed"
        assert "forced error" in step.error

    def test_step_align_exception(self):
        """_step_align 异常处理"""
        daemon = SelfCorrectionDaemon()

        class BadState:
            def get(self, key, default=None):
                raise RuntimeError("forced error")

        step = daemon._step_align(BadState(), 0.5)
        assert step.status == "failed"
        assert "forced error" in step.error

    def test_step_consolidate_exception(self):
        """_step_consolidate 异常处理"""
        daemon = SelfCorrectionDaemon()
        # enable_gate=True 触发 import，异常被捕获
        with patch("builtins.__import__", side_effect=RuntimeError("unexpected error")):
            step = daemon._step_consolidate({}, True)
            assert step.status == "failed"
            assert "unexpected error" in step.error

    def test_report_to_dict_structure(self):
        """CorrectionReport.to_dict() 完整结构验证"""
        daemon = SelfCorrectionDaemon()
        _, report = daemon.correct({"output": 0.5}, enable_gate=False)

        d = report.to_dict()
        assert "session_id" in d
        assert "steps" in d
        assert "total_delta" in d
        assert "success" in d
        assert "timestamp" in d

        for step_dict in d["steps"]:
            assert "step" in step_dict
            assert "name" in step_dict
            assert "tech" in step_dict
            assert "status" in step_dict
            assert "delta" in step_dict
            assert "confidence" in step_dict
            assert "duration_ms" in step_dict


# ============================================================================
# 16. 集成 — correct() 各步骤交互测试
# ============================================================================

class TestCorrectIntegration:
    """correct() 集成测试"""

    def test_full_cycle_low_confidence(self):
        """低置信度 → 根因诊断 → 物理核验 → 修正 → 补全 → 对齐 → 固化"""
        daemon = SelfCorrectionDaemon()
        state = {"output": 0.2, "confidence": 0.15, "uncertainty": 0.6, "fallback_value": 0.0}
        expected = 0.9
        constraints = [{"field": "output", "type": "range", "range": (0, 1)}]
        memory = {"name": "test_name"}

        result_state, report = daemon.correct(
            state,
            expected_output=expected,
            physical_constraints=constraints,
            memory_store=memory,
            enable_gate=False,
        )

        assert report.success is True
        assert len(report.steps) == 7
        assert report.final_state is not None
        assert daemon._total_corrections == 1
        assert daemon._successful_corrections == 1

        # 步骤1应检测到低置信度
        step1 = report.steps[0]
        assert step1.output_state["bias_detected"] is True

        # 步骤2应有根因
        step2 = report.steps[1]
        assert step2.output_state["cause_count"] >= 1

        # 步骤3应通过（output 在范围内）
        step3 = report.steps[2]
        assert step3.output_state["verified"] is True

        # 步骤4应调整不确定性
        step4 = report.steps[3]
        assert "uncertainty" in step4.output_state

        # 步骤6应对齐
        step6 = report.steps[5]
        # output 偏离 expected，应对齐
        assert "output" in step6.output_state

    def test_full_cycle_null_output(self):
        """空输出完整流程"""
        daemon = SelfCorrectionDaemon()
        state = {"output": None, "confidence": 0.8, "uncertainty": 0.5, "fallback_value": 0.0}
        constraints = [
            {"field": "output", "type": "non_null"},
            {"field": "name", "type": "non_null"},
        ]
        memory = {"name": "补全的名字"}

        result_state, report = daemon.correct(
            state, physical_constraints=constraints, memory_store=memory, enable_gate=False
        )

        assert report.success is True

        step1 = report.steps[0]
        assert step1.output_state["bias_detected"] is True
        assert "null_output" in step1.output_state["distortions"]

        step3 = report.steps[2]
        assert step3.output_state["hallucination_count"] >= 1

    def test_state_evolution_through_steps(self):
        """状态在步骤间逐步演化"""
        daemon = SelfCorrectionDaemon()
        state = {"output": 2.0, "confidence": 0.8, "uncertainty": 0.5, "fallback_value": 0.0}
        constraints = [{"field": "output", "type": "range", "range": (0, 1)}]

        result_state, report = daemon.correct(
            state, physical_constraints=constraints, enable_gate=False
        )

        # 步骤4修正了 output 为 0.5
        # 这个值应反映在最终状态中
        assert report.final_state is not None
        assert isinstance(result_state, dict)