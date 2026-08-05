"""
test_七杀_test_runner.py — TestRunner 回归测试

覆盖七杀_品质裁决.test_runner 的核心行为：
  1. TestStatus / TestCase / TestResult 数据类的基本属性
  2. TestRunner.add_case 注册与执行
  3. 四种状态：PASS / FAIL / ERROR / SKIP
  4. 断言错误转为 FAIL，其他异常转为 ERROR，且 ERROR 包含 traceback
  5. skip=True 的用例应标记 SKIP 且不执行
  6. summary 汇总（总数、通过数、通过率、空集边界）
  7. verbose=False 不应产生标准输出
  8. run() 多次调用结果应可重放
"""

from __future__ import annotations

import io
import sys
import traceback
from unittest.mock import patch

import pytest

from tengod.七杀_品质裁决.test_runner import (  # type: ignore[attr-defined]
    TestCase,
    TestResult,
    TestRunner,
    TestStatus,
)


# ---------------------------------------------------------------------------
# TestStatus
# ---------------------------------------------------------------------------

class TestTestStatus:
    def test_values(self):
        assert TestStatus.PASS.value == "pass"
        assert TestStatus.FAIL.value == "fail"
        assert TestStatus.ERROR.value == "error"
        assert TestStatus.SKIP.value == "skip"

    def test_members(self):
        members = set(TestStatus)
        assert len(members) == 4


# ---------------------------------------------------------------------------
# TestCase / TestResult
# ---------------------------------------------------------------------------

class TestDataClasses:
    def test_test_case_defaults(self):
        tc = TestCase("n", lambda: None)
        assert tc.name == "n"
        assert tc.description == ""
        assert tc.skip is False

    def test_test_result_defaults(self):
        tr = TestResult("n", TestStatus.PASS, 0.5)
        assert tr.case_name == "n"
        assert tr.status is TestStatus.PASS
        assert tr.duration == 0.5
        assert tr.message == ""
        assert tr.traceback == ""


# ---------------------------------------------------------------------------
# TestRunner: PASS 路径
# ---------------------------------------------------------------------------

class TestTestRunnerPass:
    def test_pass_case_marks_pass(self):
        runner = TestRunner(verbose=False)
        runner.add_case("ok", lambda: None)
        results = runner.run()
        assert len(results) == 1
        assert results[0].status is TestStatus.PASS
        assert results[0].duration >= 0.0

    def test_multiple_cases(self):
        runner = TestRunner(verbose=False)
        runner.add_case("a", lambda: None)
        runner.add_case("b", lambda: None)
        results = runner.run()
        assert len(results) == 2
        assert all(r.status is TestStatus.PASS for r in results)


# ---------------------------------------------------------------------------
# TestRunner: FAIL / ERROR 分流
# ---------------------------------------------------------------------------

class TestTestRunnerFailError:
    def test_assertion_error_is_fail(self):
        def fail_case():
            assert 1 == 2

        runner = TestRunner(verbose=False)
        runner.add_case("assert_fails", fail_case)
        results = runner.run()

        assert len(results) == 1
        r = results[0]
        assert r.status is TestStatus.FAIL
        assert "1 == 2" in r.message
        assert r.traceback == ""

    def test_generic_exception_is_error(self):
        def err_case():
            raise RuntimeError("boom")

        runner = TestRunner(verbose=False)
        runner.add_case("runtime_err", err_case)
        results = runner.run()

        assert len(results) == 1
        r = results[0]
        assert r.status is TestStatus.ERROR
        assert r.message == "boom"
        # traceback 应由 traceback.format_exc() 填充
        assert "RuntimeError" in r.traceback

    def test_value_error_is_error(self):
        def err_case():
            int("not-a-number")

        runner = TestRunner(verbose=False)
        runner.add_case("value_err", err_case)
        results = runner.run()
        assert results[0].status is TestStatus.ERROR
        assert "invalid literal" in results[0].message.lower()


# ---------------------------------------------------------------------------
# TestRunner: SKIP
# ---------------------------------------------------------------------------

class TestTestRunnerSkip:
    def test_skip_case_marks_skip_without_exec(self):
        executed = {"flag": False}

        def side_effect():
            executed["flag"] = True

        runner = TestRunner(verbose=False)
        tc = runner.add_case("s", side_effect)
        tc.skip = True

        results = runner.run()
        assert len(results) == 1
        r = results[0]
        assert r.status is TestStatus.SKIP
        assert r.message == "Test skipped"
        assert r.duration == 0.0
        # 关键：被跳过的用例不应被执行
        assert executed["flag"] is False


# ---------------------------------------------------------------------------
# summary
# ---------------------------------------------------------------------------

class TestSummary:
    def test_summary_aggregates_counts(self):
        def fail():
            assert False

        def err():
            raise RuntimeError("x")

        runner = TestRunner(verbose=False)
        runner.add_case("p1", lambda: None)
        runner.add_case("p2", lambda: None)
        runner.add_case("f1", fail)
        runner.add_case("e1", err)
        runner.add_case("s1", lambda: None).skip = True

        # 必须先 run()，summary 才会有数据
        runner.run()
        summary = runner.summary()
        assert summary["total"] == 5
        assert summary["passed"] == 2
        assert summary["failed"] == 1
        assert summary["errors"] == 1
        assert summary["skipped"] == 1
        assert summary["pass_rate"] == pytest.approx(40.0, abs=1e-6)
        assert summary["duration"] >= 0.0

    def test_summary_empty_runner(self):
        runner = TestRunner(verbose=False)
        summary = runner.summary()
        assert summary["total"] == 0
        assert summary["passed"] == 0
        assert summary["failed"] == 0
        assert summary["errors"] == 0
        assert summary["skipped"] == 0
        assert summary["pass_rate"] == 0.0

    def test_summary_resets_after_run(self):
        runner = TestRunner(verbose=False)
        runner.add_case("p", lambda: None)
        runner.run()
        assert runner.summary()["total"] == 1

        # 清空用例后再次运行（但用例列表不会被自动清空）
        runner._cases = []
        runner.run()
        # summary 仍反映上一次结果（因为 self._results 只在 run 开头清空）
        # 这是一个"重复 run 行为"的快照，记录当前设计：
        assert runner.summary()["total"] == 0


# ---------------------------------------------------------------------------
# 其他边界
# ---------------------------------------------------------------------------

class TestVerboseOutput:
    def test_verbose_true_prints(self):
        runner = TestRunner(verbose=True)
        runner.add_case("p", lambda: None)
        with patch("sys.stdout", new_callable=io.StringIO) as out:
            runner.run()
            printed = out.getvalue()
        assert "p" in printed
        assert "✅" in printed

    def test_verbose_false_prints_nothing(self):
        runner = TestRunner(verbose=False)
        runner.add_case("p", lambda: None)
        with patch("sys.stdout", new_callable=io.StringIO) as out:
            runner.run()
            printed = out.getvalue()
        assert printed == ""

    def test_run_idempotent(self):
        """run 可以被重复调用且每次返回完整最新结果。"""
        runner = TestRunner(verbose=False)
        runner.add_case("a", lambda: None)
        runner.add_case("b", lambda: None)

        r1 = runner.run()
        r2 = runner.run()
        assert len(r1) == len(r2) == 2
        # 每次 run 后 _results 都应与最新结果一致
        assert runner.summary()["total"] == 2

    def test_exception_traceback_format(self):
        """ERROR 的 traceback 字段应为字符串且非空。"""
        def raise_exc():
            raise ValueError("deep")

        runner = TestRunner(verbose=False)
        runner.add_case("exc", raise_exc)
        results = runner.run()
        tb = results[0].traceback
        assert isinstance(tb, str)
        assert tb, "traceback 不应为空字符串"
        # 必须包含异常名称
        assert "ValueError" in tb
        assert "deep" in tb
