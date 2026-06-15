#!/usr/bin/env python3
"""
test_runner.py — 简易测试运行器
七杀主理裁决，提供轻量级测试执行与结果收集。
"""

import time
import traceback
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List


class TestStatus(Enum):
    """测试状态"""

    PASS = "pass"
    FAIL = "fail"
    ERROR = "error"
    SKIP = "skip"


@dataclass
class TestCase:
    """测试用例"""

    name: str
    func: Callable
    description: str = ""
    skip: bool = False


@dataclass
class TestResult:
    """测试结果"""

    case_name: str
    status: TestStatus
    duration: float
    message: str = ""
    traceback: str = ""


class TestRunner:
    """测试运行器 — 裁决之衡

    执行测试用例并收集结果，输出汇总报告。
    """

    def __init__(self, verbose: bool = True):
        self._cases: List[TestCase] = []
        self._results: List[TestResult] = []
        self._verbose = verbose

    def add_case(self, name: str, func: Callable, description: str = "") -> TestCase:
        """添加测试用例"""
        case = TestCase(name=name, func=func, description=description)
        self._cases.append(case)
        return case

    def run(self) -> List[TestResult]:
        """运行所有测试"""
        self._results.clear()
        for case in self._cases:
            if case.skip:
                result = TestResult(
                    case_name=case.name,
                    status=TestStatus.SKIP,
                    duration=0.0,
                    message="Test skipped",
                )
                self._results.append(result)
                continue

            start = time.time()
            try:
                case.func()
                result = TestResult(
                    case_name=case.name,
                    status=TestStatus.PASS,
                    duration=time.time() - start,
                )
            except AssertionError as e:
                result = TestResult(
                    case_name=case.name,
                    status=TestStatus.FAIL,
                    duration=time.time() - start,
                    message=str(e),
                )
            except Exception as e:
                result = TestResult(
                    case_name=case.name,
                    status=TestStatus.ERROR,
                    duration=time.time() - start,
                    message=str(e),
                    traceback=traceback.format_exc(),
                )

            self._results.append(result)
            if self._verbose:
                self._print_result(result)

        return self._results

    def _print_result(self, result: TestResult) -> None:
        """打印单个结果"""
        symbol = {
            TestStatus.PASS: "✅",
            TestStatus.FAIL: "❌",
            TestStatus.ERROR: "⚠️ ",
            TestStatus.SKIP: "⏭️ ",
        }.get(result.status, "·")
        duration_ms = result.duration * 1000
        print(f"{symbol} {result.case_name} ({duration_ms:.1f}ms)")
        if result.message and result.status != TestStatus.PASS:
            print(f"   {result.message}")

    def summary(self) -> Dict[str, Any]:
        """生成汇总报告"""
        status_count = {s.value: 0 for s in TestStatus}
        total_duration = 0.0
        for r in self._results:
            status_count[r.status.value] += 1
            total_duration += r.duration

        return {
            "total": len(self._results),
            "passed": status_count[TestStatus.PASS.value],
            "failed": status_count[TestStatus.FAIL.value],
            "errors": status_count[TestStatus.ERROR.value],
            "skipped": status_count[TestStatus.SKIP.value],
            "duration": round(total_duration, 3),
            "pass_rate": (
                round(status_count[TestStatus.PASS.value] / len(self._results) * 100, 2)
                if self._results
                else 0.0
            ),
        }
