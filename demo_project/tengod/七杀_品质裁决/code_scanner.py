#!/usr/bin/env python3
"""
code_scanner.py — 代码质量自动扫描器 v1.5.0
七杀主理裁决，集成 flake8 / pylint 自动扫描 Python 代码质量并生成评分报告。
"""

import os
import subprocess
import sys
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum


class ScanLevel(Enum):
    """扫描严重级别"""
    ERROR = "error"
    WARNING = "warning"
    CONVENTION = "convention"
    REFACTOR = "refactor"
    INFO = "info"


@dataclass
class ScanIssue:
    """扫描发现的问题"""
    file_path: str
    line: int
    column: int = 0
    level: ScanLevel = ScanLevel.WARNING
    code: str = ""
    message: str = ""


@dataclass
class ScanReport:
    """扫描报告"""
    tool: str
    total_issues: int
    by_level: Dict[str, int] = field(default_factory=dict)
    by_file: Dict[str, int] = field(default_factory=dict)
    issues: List[ScanIssue] = field(default_factory=list)
    score: float = 100.0
    duration: float = 0.0
    error: str = ""


class CodeScanner:
    """代码质量扫描器 — 裁决之镜

    集成 flake8 / pylint 自动扫描项目代码，
    输出质量评分报告，可与 QualityJudge 联动。
    """

    MAX_SCORE = 100.0
    PENALTY_PER_ERROR = 10.0
    PENALTY_PER_WARNING = 3.0
    PENALTY_PER_CONVENTION = 1.0

    def __init__(self, project_root: Optional[str] = None):
        self._project_root = project_root or os.getcwd()

    def _find_python_files(self, root: str, exclude_dirs: Optional[List[str]] = None) -> List[str]:
        """递归查找所有 .py 文件"""
        exclude = set(exclude_dirs or [".git", "__pycache__", ".venv", "venv", "node_modules"])
        py_files: List[str] = []
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in exclude and not d.startswith(".")]
            for f in filenames:
                if f.endswith(".py"):
                    py_files.append(os.path.join(dirpath, f))
        return py_files

    def _run_flake8(self, paths: List[str]) -> ScanReport:
        """运行 flake8 扫描"""
        import time
        start = time.time()
        report = ScanReport(tool="flake8", total_issues=0)

        try:
            result = subprocess.run(
                [sys.executable, "-m", "flake8", "--format=default", "--exit-zero"] + paths,
                capture_output=True, text=True, timeout=120,
                cwd=self._project_root,
            )
            lines = result.stdout.strip().split("\n")
            for line in lines:
                if not line:
                    continue
                # flake8 格式：path:line:col: CODE message
                parts = line.split(":", 3)
                if len(parts) < 4:
                    continue
                fpath, lineno, col, rest = parts
                code_msg = rest.strip().split(" ", 1)
                code = code_msg[0]
                msg = code_msg[1] if len(code_msg) > 1 else ""

                # 根据 code 首字母判断级别
                if code.startswith("E") or code.startswith("F"):
                    level = ScanLevel.ERROR
                elif code.startswith("W"):
                    level = ScanLevel.WARNING
                elif code.startswith("C"):
                    level = ScanLevel.CONVENTION
                elif code.startswith("R"):
                    level = ScanLevel.REFACTOR
                else:
                    level = ScanLevel.INFO

                issue = ScanIssue(
                    file_path=fpath,
                    line=int(lineno) if lineno.isdigit() else 0,
                    column=int(col) if col.isdigit() else 0,
                    level=level,
                    code=code,
                    message=msg,
                )
                report.issues.append(issue)

        except FileNotFoundError:
            report.error = "flake8 未安装。运行: pip install flake8"
        except subprocess.TimeoutExpired:
            report.error = "flake8 扫描超时（120s）"
        except Exception as e:
            report.error = str(e)

        self._compute_score(report)
        report.duration = round(time.time() - start, 2)
        return report

    def _run_pylint(self, paths: List[str]) -> ScanReport:
        """运行 pylint 扫描"""
        import time
        start = time.time()
        report = ScanReport(tool="pylint", total_issues=0)

        try:
            result = subprocess.run(
                [sys.executable, "-m", "pylint", "--output-format=text", "--exit-zero"] + paths,
                capture_output=True, text=True, timeout=120,
                cwd=self._project_root,
            )
            lines = result.stdout.strip().split("\n")
            for line in lines:
                if not line or line.startswith("--") or "lines evaluated" in line:
                    continue
                # pylint 格式：path:line:col: CODE: message
                parts = line.split(":", 3)
                if len(parts) < 4:
                    continue
                fpath, lineno, col, rest = parts
                if not fpath or not lineno.isdigit():
                    continue
                code_msg = rest.strip().split(":", 1)
                code = code_msg[0].strip()
                msg = code_msg[1].strip() if len(code_msg) > 1 else ""

                if code.startswith("E") or code.startswith("F"):
                    level = ScanLevel.ERROR
                elif code.startswith("W"):
                    level = ScanLevel.WARNING
                elif code.startswith("R"):
                    level = ScanLevel.REFACTOR
                elif code.startswith("C"):
                    level = ScanLevel.CONVENTION
                else:
                    level = ScanLevel.INFO

                issue = ScanIssue(
                    file_path=fpath,
                    line=int(lineno),
                    column=int(col) if col.isdigit() else 0,
                    level=level,
                    code=code,
                    message=msg,
                )
                report.issues.append(issue)

        except FileNotFoundError:
            report.error = "pylint 未安装。运行: pip install pylint"
        except subprocess.TimeoutExpired:
            report.error = "pylint 扫描超时（120s）"
        except Exception as e:
            report.error = str(e)

        self._compute_score(report)
        report.duration = round(time.time() - start, 2)
        return report

    def _compute_score(self, report: ScanReport) -> None:
        """计算质量评分（100分制）"""
        score = self.MAX_SCORE
        by_level: Dict[str, int] = {}
        by_file: Dict[str, int] = {}

        for issue in report.issues:
            lvl = issue.level.value
            by_level[lvl] = by_level.get(lvl, 0) + 1
            fname = os.path.basename(issue.file_path)
            by_file[fname] = by_file.get(fname, 0) + 1

            if issue.level == ScanLevel.ERROR:
                score -= self.PENALTY_PER_ERROR
            elif issue.level == ScanLevel.WARNING:
                score -= self.PENALTY_PER_WARNING
            elif issue.level == ScanLevel.CONVENTION:
                score -= self.PENALTY_PER_CONVENTION

        report.total_issues = len(report.issues)
        report.by_level = by_level
        report.by_file = by_file
        report.score = max(0.0, round(score, 1))

    def scan(self, tool: str = "flake8", paths: Optional[List[str]] = None) -> ScanReport:
        """执行代码扫描。

        Args:
            tool: "flake8" 或 "pylint"
            paths: 要扫描的文件/目录列表，默认扫描整个项目

        Returns:
            ScanReport 包含所有问题和质量评分
        """
        if paths is None:
            paths = self._find_python_files(self._project_root)

        if not paths:
            report = ScanReport(tool=tool, total_issues=0, score=100.0)
            report.error = "未发现任何 Python 文件"
            return report

        if tool == "flake8":
            return self._run_flake8(paths)
        elif tool == "pylint":
            return self._run_pylint(paths)
        else:
            report = ScanReport(tool=tool, total_issues=0)
            report.error = f"未知扫描工具: {tool}，支持: flake8, pylint"
            return report

    def scan_both(self, paths: Optional[List[str]] = None) -> Dict[str, ScanReport]:
        """同时运行 flake8 和 pylint 扫描"""
        return {
            "flake8": self.scan("flake8", paths),
            "pylint": self.scan("pylint", paths),
        }

    def scan_to_judge(self, quality_judge,
                      paths: Optional[List[str]] = None) -> Dict[str, Any]:
        """运行扫描并写入 QualityJudge，返回综合评分报告。

        将 flake8 和 pylint 的扫描结果分别作为评分项添加到 QualityJudge：
        - flake8_score / pylint_score: 各工具评分（权重各0.5）
        - 最终得分 = 两个工具的加权平均
        """
        results = self.scan_both(paths)
        quality_judge.reset()

        for tool, report in results.items():
            if report.error:
                quality_judge.add_score(
                    f"{tool}_error", 0,
                    weight=0.5,
                    comment=f"{tool} 扫描失败: {report.error}",
                )
            else:
                quality_judge.add_score(
                    f"{tool}_score", report.score,
                    weight=0.5,
                    comment=f"{tool} 发现 {report.total_issues} 个问题",
                )

        judge_report = quality_judge.report()
        return {
            "judge": judge_report,
            "flake8": {
                "score": results["flake8"].score,
                "issues": results["flake8"].total_issues,
                "error": results["flake8"].error,
            },
            "pylint": {
                "score": results["pylint"].score,
                "issues": results["pylint"].total_issues,
                "error": results["pylint"].error,
            },
        }


__all__ = ["CodeScanner", "ScanReport", "ScanIssue", "ScanLevel"]
__version__ = "1.5.0"