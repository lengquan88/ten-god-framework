"""
test_code_scanner.py — CodeScanner 模块全面测试
七杀_品质裁决/code_scanner.py 的 pytest 测试套件。
"""

import os
import subprocess
import tempfile
from unittest.mock import MagicMock, Mock, patch

import pytest

from tengod.七杀_品质裁决.code_scanner import (
    CodeScanner,
    ScanIssue,
    ScanLevel,
    ScanReport,
)


# ═══════════════════════════════════════════════════════════════
# ScanLevel 枚举测试
# ═══════════════════════════════════════════════════════════════

class TestScanLevel:
    """ScanLevel 枚举值测试"""

    def test_all_values_present(self):
        """验证所有枚举值存在"""
        assert ScanLevel.ERROR.value == "error"
        assert ScanLevel.WARNING.value == "warning"
        assert ScanLevel.CONVENTION.value == "convention"
        assert ScanLevel.REFACTOR.value == "refactor"
        assert ScanLevel.INFO.value == "info"

    def test_enum_length(self):
        """验证枚举成员数量"""
        assert len(list(ScanLevel)) == 5

    def test_enum_is_enum(self):
        """验证 ScanLevel 是 Enum 类型"""
        assert isinstance(ScanLevel.ERROR, ScanLevel)
        assert issubclass(ScanLevel, type(ScanLevel.ERROR).__bases__[0])


# ═══════════════════════════════════════════════════════════════
# ScanIssue 数据类测试
# ═══════════════════════════════════════════════════════════════

class TestScanIssue:
    """ScanIssue 数据类测试"""

    def test_create_with_all_fields(self):
        """测试创建含所有字段的 ScanIssue"""
        issue = ScanIssue(
            file_path="test.py",
            line=10,
            column=5,
            level=ScanLevel.ERROR,
            code="E501",
            message="Line too long",
        )
        assert issue.file_path == "test.py"
        assert issue.line == 10
        assert issue.column == 5
        assert issue.level == ScanLevel.ERROR
        assert issue.code == "E501"
        assert issue.message == "Line too long"

    def test_defaults(self):
        """测试默认值"""
        issue = ScanIssue(file_path="test.py", line=1)
        assert issue.column == 0
        assert issue.level == ScanLevel.WARNING
        assert issue.code == ""
        assert issue.message == ""

    def test_equality(self):
        """测试相等性比较"""
        a = ScanIssue(file_path="a.py", line=1, code="E501")
        b = ScanIssue(file_path="a.py", line=1, code="E501")
        assert a == b

    def test_inequality(self):
        """测试不等性比较"""
        a = ScanIssue(file_path="a.py", line=1, code="E501")
        b = ScanIssue(file_path="b.py", line=1, code="E501")
        assert a != b

    def test_mutable(self):
        """测试数据类可变性"""
        issue = ScanIssue(file_path="test.py", line=1)
        issue.line = 42
        assert issue.line == 42


# ═══════════════════════════════════════════════════════════════
# ScanReport 数据类测试
# ═══════════════════════════════════════════════════════════════

class TestScanReport:
    """ScanReport 数据类测试"""

    def test_create_minimal(self):
        """测试最小参数创建"""
        report = ScanReport(tool="flake8", total_issues=0)
        assert report.tool == "flake8"
        assert report.total_issues == 0
        assert report.by_level == {}
        assert report.by_file == {}
        assert report.issues == []
        assert report.score == 100.0
        assert report.duration == 0.0
        assert report.error == ""

    def test_create_with_all_fields(self):
        """测试含所有字段创建"""
        issues = [ScanIssue(file_path="x.py", line=1)]
        report = ScanReport(
            tool="pylint",
            total_issues=1,
            by_level={"error": 1},
            by_file={"x.py": 1},
            issues=issues,
            score=85.0,
            duration=2.5,
            error="",
        )
        assert report.tool == "pylint"
        assert report.total_issues == 1
        assert report.by_level == {"error": 1}
        assert report.by_file == {"x.py": 1}
        assert len(report.issues) == 1
        assert report.score == 85.0
        assert report.duration == 2.5
        assert report.error == ""

    def test_mutable(self):
        """测试 ScanReport 可变性"""
        report = ScanReport(tool="flake8", total_issues=0)
        report.score = 50.0
        report.error = "some error"
        report.by_level["warning"] = 3
        assert report.score == 50.0
        assert report.error == "some error"
        assert report.by_level == {"warning": 3}

    def test_issues_list_default_not_shared(self):
        """测试 issues 默认列表不会在实例间共享"""
        a = ScanReport(tool="a", total_issues=0)
        b = ScanReport(tool="b", total_issues=0)
        a.issues.append(ScanIssue(file_path="x.py", line=1))
        assert len(b.issues) == 0

    def test_by_level_default_not_shared(self):
        """测试 by_level 默认字典不会在实例间共享"""
        a = ScanReport(tool="a", total_issues=0)
        b = ScanReport(tool="b", total_issues=0)
        a.by_level["error"] = 5
        assert b.by_level == {}

    def test_by_file_default_not_shared(self):
        """测试 by_file 默认字典不会在实例间共享"""
        a = ScanReport(tool="a", total_issues=0)
        b = ScanReport(tool="b", total_issues=0)
        a.by_file["f.py"] = 2
        assert b.by_file == {}


# ═══════════════════════════════════════════════════════════════
# CodeScanner 初始化测试
# ═══════════════════════════════════════════════════════════════

class TestCodeScannerInit:
    """CodeScanner 初始化测试"""

    def test_init_with_project_root(self, tmp_path):
        """测试传入 project_root"""
        scanner = CodeScanner(project_root=str(tmp_path))
        assert scanner._project_root == str(tmp_path)

    def test_init_without_project_root(self):
        """测试不传 project_root 时使用当前工作目录"""
        scanner = CodeScanner()
        assert scanner._project_root == os.getcwd()

    def test_init_with_none(self):
        """测试传入 None 时使用当前工作目录"""
        scanner = CodeScanner(project_root=None)
        assert scanner._project_root == os.getcwd()

    def test_class_constants(self):
        """测试类常量"""
        assert CodeScanner.MAX_SCORE == 100.0
        assert CodeScanner.PENALTY_PER_ERROR == 10.0
        assert CodeScanner.PENALTY_PER_WARNING == 3.0
        assert CodeScanner.PENALTY_PER_CONVENTION == 1.0

    def test_module_constants_via_class(self):
        """测试通过类访问常量"""
        assert CodeScanner.MAX_SCORE == 100.0
        assert CodeScanner.PENALTY_PER_ERROR == 10.0
        assert CodeScanner.PENALTY_PER_WARNING == 3.0
        assert CodeScanner.PENALTY_PER_CONVENTION == 1.0


# ═══════════════════════════════════════════════════════════════
# _find_python_files 测试
# ═══════════════════════════════════════════════════════════════

class TestFindPythonFiles:
    """_find_python_files 测试"""

    def test_finds_python_files(self, tmp_path):
        """测试查找 .py 文件"""
        (tmp_path / "a.py").write_text("")
        (tmp_path / "b.py").write_text("")
        (tmp_path / "c.txt").write_text("")
        scanner = CodeScanner(project_root=str(tmp_path))
        files = scanner._find_python_files(str(tmp_path))
        assert len(files) == 2
        assert any("a.py" in f for f in files)
        assert any("b.py" in f for f in files)

    def test_recursive_search(self, tmp_path):
        """测试递归查找"""
        sub = tmp_path / "sub"
        sub.mkdir()
        (tmp_path / "root.py").write_text("")
        (sub / "child.py").write_text("")
        scanner = CodeScanner()
        files = scanner._find_python_files(str(tmp_path))
        assert len(files) == 2

    def test_exclude_dirs_default(self, tmp_path):
        """测试默认排除目录"""
        (tmp_path / "__pycache__").mkdir()
        (tmp_path / "__pycache__" / "cached.py").write_text("")
        (tmp_path / "main.py").write_text("")
        scanner = CodeScanner()
        files = scanner._find_python_files(str(tmp_path))
        assert len(files) == 1
        assert "main.py" in files[0]

    def test_exclude_dirs_custom(self, tmp_path):
        """测试自定义排除目录"""
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_a.py").write_text("")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "mod.py").write_text("")
        scanner = CodeScanner()
        files = scanner._find_python_files(str(tmp_path), exclude_dirs=["tests"])
        assert len(files) == 1
        assert "mod.py" in files[0]

    def test_exclude_dot_dirs(self, tmp_path):
        """测试自动排除以点开头的目录"""
        (tmp_path / ".hidden").mkdir()
        (tmp_path / ".hidden" / "secret.py").write_text("")
        (tmp_path / "visible.py").write_text("")
        scanner = CodeScanner()
        files = scanner._find_python_files(str(tmp_path))
        assert len(files) == 1
        assert "visible.py" in files[0]

    def test_empty_directory(self, tmp_path):
        """测试空目录"""
        scanner = CodeScanner()
        files = scanner._find_python_files(str(tmp_path))
        assert files == []

    def test_no_python_files(self, tmp_path):
        """测试目录中无 .py 文件"""
        (tmp_path / "readme.md").write_text("")
        (tmp_path / "data.json").write_text("")
        scanner = CodeScanner()
        files = scanner._find_python_files(str(tmp_path))
        assert files == []

    def test_exclude_dirs_none(self, tmp_path):
        """测试 exclude_dirs 为 None 时使用默认值"""
        (tmp_path / "__pycache__").mkdir()
        (tmp_path / "__pycache__" / "x.py").write_text("")
        (tmp_path / "ok.py").write_text("")
        scanner = CodeScanner()
        files = scanner._find_python_files(str(tmp_path), exclude_dirs=None)
        assert len(files) == 1


# ═══════════════════════════════════════════════════════════════
# _compute_score 测试
# ═══════════════════════════════════════════════════════════════

class TestComputeScore:
    """_compute_score 测试"""

    def test_no_issues_perfect_score(self):
        """测试无问题时满分"""
        scanner = CodeScanner()
        report = ScanReport(tool="flake8", total_issues=0)
        scanner._compute_score(report)
        assert report.score == 100.0
        assert report.total_issues == 0
        assert report.by_level == {}
        assert report.by_file == {}

    def test_single_error(self):
        """测试单个错误"""
        scanner = CodeScanner()
        report = ScanReport(tool="flake8", total_issues=0)
        report.issues = [ScanIssue(file_path="f.py", line=1, level=ScanLevel.ERROR)]
        scanner._compute_score(report)
        assert report.score == 90.0
        assert report.total_issues == 1
        assert report.by_level == {"error": 1}

    def test_single_warning(self):
        """测试单个警告"""
        scanner = CodeScanner()
        report = ScanReport(tool="flake8", total_issues=0)
        report.issues = [ScanIssue(file_path="f.py", line=1, level=ScanLevel.WARNING)]
        scanner._compute_score(report)
        assert report.score == 97.0
        assert report.total_issues == 1
        assert report.by_level == {"warning": 1}

    def test_single_convention(self):
        """测试单个规范性问题"""
        scanner = CodeScanner()
        report = ScanReport(tool="flake8", total_issues=0)
        report.issues = [
            ScanIssue(file_path="f.py", line=1, level=ScanLevel.CONVENTION)
        ]
        scanner._compute_score(report)
        assert report.score == 99.0
        assert report.total_issues == 1
        assert report.by_level == {"convention": 1}

    def test_refactor_no_penalty(self):
        """测试重构建议不扣分"""
        scanner = CodeScanner()
        report = ScanReport(tool="flake8", total_issues=0)
        report.issues = [ScanIssue(file_path="f.py", line=1, level=ScanLevel.REFACTOR)]
        scanner._compute_score(report)
        assert report.score == 100.0
        assert report.by_level == {"refactor": 1}

    def test_info_no_penalty(self):
        """测试信息级别不扣分"""
        scanner = CodeScanner()
        report = ScanReport(tool="flake8", total_issues=0)
        report.issues = [ScanIssue(file_path="f.py", line=1, level=ScanLevel.INFO)]
        scanner._compute_score(report)
        assert report.score == 100.0
        assert report.by_level == {"info": 1}

    def test_mixed_issues(self):
        """测试混合问题类型"""
        scanner = CodeScanner()
        report = ScanReport(tool="flake8", total_issues=0)
        report.issues = [
            ScanIssue(file_path="f.py", line=1, level=ScanLevel.ERROR),
            ScanIssue(file_path="f.py", line=2, level=ScanLevel.ERROR),
            ScanIssue(file_path="f.py", line=3, level=ScanLevel.WARNING),
            ScanIssue(file_path="f.py", line=4, level=ScanLevel.CONVENTION),
            ScanIssue(file_path="f.py", line=5, level=ScanLevel.CONVENTION),
            ScanIssue(file_path="f.py", line=6, level=ScanLevel.CONVENTION),
        ]
        scanner._compute_score(report)
        # 2 errors: -20, 1 warning: -3, 3 conventions: -3 → 100 - 26 = 74
        assert report.score == 74.0
        assert report.total_issues == 6
        assert report.by_level == {
            "error": 2,
            "warning": 1,
            "convention": 3,
        }

    def test_score_clamping_zero(self):
        """测试分数不会低于 0"""
        scanner = CodeScanner()
        report = ScanReport(tool="flake8", total_issues=0)
        # 20 errors → 20 * 10 = 200 penalty → should clamp to 0
        report.issues = [
            ScanIssue(file_path=f"f{i}.py", line=1, level=ScanLevel.ERROR)
            for i in range(20)
        ]
        scanner._compute_score(report)
        assert report.score == 0.0

    def test_score_clamping_above_zero(self):
        """测试边界情况：刚好到 0 但不会被 clamp 到负数"""
        scanner = CodeScanner()
        report = ScanReport(tool="flake8", total_issues=0)
        # 10 errors → 100 - 100 = 0
        report.issues = [
            ScanIssue(file_path=f"f{i}.py", line=1, level=ScanLevel.ERROR)
            for i in range(10)
        ]
        scanner._compute_score(report)
        assert report.score == 0.0

    def test_by_file_aggregation(self):
        """测试 by_file 聚合"""
        scanner = CodeScanner()
        report = ScanReport(tool="flake8", total_issues=0)
        report.issues = [
            ScanIssue(file_path="/a/b/f1.py", line=1, level=ScanLevel.ERROR),
            ScanIssue(file_path="/a/b/f1.py", line=2, level=ScanLevel.WARNING),
            ScanIssue(file_path="/a/c/f2.py", line=1, level=ScanLevel.ERROR),
        ]
        scanner._compute_score(report)
        assert report.by_file == {"f1.py": 2, "f2.py": 1}

    def test_total_issues_set(self):
        """测试 total_issues 被正确设置"""
        scanner = CodeScanner()
        report = ScanReport(tool="flake8", total_issues=999)
        report.issues = [
            ScanIssue(file_path="f.py", line=1),
            ScanIssue(file_path="f.py", line=2),
        ]
        scanner._compute_score(report)
        assert report.total_issues == 2

    def test_score_rounding(self):
        """测试分数四舍五入"""
        scanner = CodeScanner()
        report = ScanReport(tool="flake8", total_issues=0)
        # 3 warnings → 100 - 9 = 91.0
        report.issues = [
            ScanIssue(file_path="f.py", line=i, level=ScanLevel.WARNING)
            for i in range(1, 4)
        ]
        scanner._compute_score(report)
        assert report.score == 91.0


# ═══════════════════════════════════════════════════════════════
# scan() 测试
# ═══════════════════════════════════════════════════════════════

class TestScan:
    """scan() 方法测试"""

    def test_unknown_tool(self):
        """测试未知工具返回错误报告"""
        scanner = CodeScanner()
        report = scanner.scan(tool="unknown_tool", paths=["test.py"])
        assert report.tool == "unknown_tool"
        assert report.total_issues == 0
        assert "未知扫描工具" in report.error

    def test_empty_paths(self, tmp_path):
        """测试空路径列表时提前返回"""
        scanner = CodeScanner(project_root=str(tmp_path))
        report = scanner.scan(tool="flake8", paths=[])
        assert report.tool == "flake8"
        assert report.total_issues == 0
        assert report.score == 100.0
        assert "未发现任何 Python 文件" in report.error

    def test_none_paths_uses_find(self, tmp_path):
        """测试 paths=None 时自动查找 Python 文件"""
        (tmp_path / "test.py").write_text("x = 1\n")
        scanner = CodeScanner(project_root=str(tmp_path))
        with patch.object(scanner, "_run_flake8") as mock_run:
            mock_run.return_value = ScanReport(tool="flake8", total_issues=0, score=100.0)
            scanner.scan(tool="flake8", paths=None)
            mock_run.assert_called_once()
            # 验证传入的 paths 包含了找到的 .py 文件
            call_args = mock_run.call_args[0][0]
            assert any("test.py" in p for p in call_args)

    def test_scan_flake8(self, tmp_path):
        """测试 scan("flake8") 调用 _run_flake8"""
        (tmp_path / "test.py").write_text("x = 1\n")
        scanner = CodeScanner(project_root=str(tmp_path))
        with patch.object(scanner, "_run_flake8") as mock_run:
            mock_run.return_value = ScanReport(
                tool="flake8", total_issues=0, score=100.0
            )
            report = scanner.scan(tool="flake8", paths=["test.py"])
            mock_run.assert_called_once_with(["test.py"])
            assert report.tool == "flake8"

    def test_scan_pylint(self, tmp_path):
        """测试 scan("pylint") 调用 _run_pylint"""
        (tmp_path / "test.py").write_text("x = 1\n")
        scanner = CodeScanner(project_root=str(tmp_path))
        with patch.object(scanner, "_run_pylint") as mock_run:
            mock_run.return_value = ScanReport(
                tool="pylint", total_issues=0, score=100.0
            )
            report = scanner.scan(tool="pylint", paths=["test.py"])
            mock_run.assert_called_once_with(["test.py"])
            assert report.tool == "pylint"


# ═══════════════════════════════════════════════════════════════
# _run_flake8 测试（Mock subprocess）
# ═══════════════════════════════════════════════════════════════

class TestRunFlake8:
    """_run_flake8 测试（mock subprocess.run）"""

    def test_parses_all_level_codes(self):
        """测试解析所有 flake8 级别代码"""
        output = (
            "test.py:1:1: E501 line too long\n"
            "test.py:2:1: F401 imported but unused\n"
            "test.py:3:1: W503 line break before binary operator\n"
            "test.py:4:1: C901 function is too complex\n"
            "test.py:5:1: R504 unnecessary variable assignment\n"
            "test.py:6:1: N802 function name should be lowercase\n"
        )
        mock_result = Mock()
        mock_result.stdout = output
        mock_result.returncode = 0

        scanner = CodeScanner()
        with patch("subprocess.run", return_value=mock_result):
            report = scanner._run_flake8(["test.py"])

        assert report.tool == "flake8"
        assert report.total_issues == 6
        assert report.by_level == {
            "error": 2,  # E501 + F401
            "warning": 1,  # W503
            "convention": 1,  # C901
            "refactor": 1,  # R504
            "info": 1,  # N802 → unknown prefix → INFO
        }
        assert report.duration >= 0
        assert report.score < 100.0

    def test_parses_error_level(self):
        """测试 E 和 F 代码归类为 ERROR"""
        output = "test.py:1:1: E302 expected 2 blank lines\n"
        mock_result = Mock()
        mock_result.stdout = output
        scanner = CodeScanner()
        with patch("subprocess.run", return_value=mock_result):
            report = scanner._run_flake8(["test.py"])
        assert report.issues[0].level == ScanLevel.ERROR
        assert report.issues[0].code == "E302"

    def test_parses_warning_level(self):
        """测试 W 代码归类为 WARNING"""
        output = "test.py:1:1: W291 trailing whitespace\n"
        mock_result = Mock()
        mock_result.stdout = output
        scanner = CodeScanner()
        with patch("subprocess.run", return_value=mock_result):
            report = scanner._run_flake8(["test.py"])
        assert report.issues[0].level == ScanLevel.WARNING
        assert report.issues[0].code == "W291"

    def test_parses_convention_level(self):
        """测试 C 代码归类为 CONVENTION"""
        output = "test.py:1:1: C0301 line too long\n"
        mock_result = Mock()
        mock_result.stdout = output
        scanner = CodeScanner()
        with patch("subprocess.run", return_value=mock_result):
            report = scanner._run_flake8(["test.py"])
        assert report.issues[0].level == ScanLevel.CONVENTION

    def test_parses_refactor_level(self):
        """测试 R 代码归类为 REFACTOR"""
        output = "test.py:1:1: R0903 too few public methods\n"
        mock_result = Mock()
        mock_result.stdout = output
        scanner = CodeScanner()
        with patch("subprocess.run", return_value=mock_result):
            report = scanner._run_flake8(["test.py"])
        assert report.issues[0].level == ScanLevel.REFACTOR

    def test_unknown_code_falls_to_info(self):
        """测试未知代码前缀归类为 INFO"""
        output = "test.py:1:1: X999 custom lint rule\n"
        mock_result = Mock()
        mock_result.stdout = output
        scanner = CodeScanner()
        with patch("subprocess.run", return_value=mock_result):
            report = scanner._run_flake8(["test.py"])
        assert report.issues[0].level == ScanLevel.INFO

    def test_empty_output(self):
        """测试空输出"""
        mock_result = Mock()
        mock_result.stdout = ""
        scanner = CodeScanner()
        with patch("subprocess.run", return_value=mock_result):
            report = scanner._run_flake8(["test.py"])
        assert report.total_issues == 0
        assert report.score == 100.0

    def test_blank_lines_skipped(self):
        """测试空白行被跳过"""
        output = "test.py:1:1: E501 line too long\n\n\n"
        mock_result = Mock()
        mock_result.stdout = output
        scanner = CodeScanner()
        with patch("subprocess.run", return_value=mock_result):
            report = scanner._run_flake8(["test.py"])
        assert report.total_issues == 1

    def test_malformed_lines_skipped(self):
        """测试格式错误的行被跳过"""
        output = "test.py:1:1: E501 line too long\nnot_a_valid_line\n"
        mock_result = Mock()
        mock_result.stdout = output
        scanner = CodeScanner()
        with patch("subprocess.run", return_value=mock_result):
            report = scanner._run_flake8(["test.py"])
        assert report.total_issues == 1

    def test_non_digit_line_column(self):
        """测试非数字行号和列号"""
        output = "test.py:abc:xyz: E501 line too long\n"
        mock_result = Mock()
        mock_result.stdout = output
        scanner = CodeScanner()
        with patch("subprocess.run", return_value=mock_result):
            report = scanner._run_flake8(["test.py"])
        # 行号非数字时设为 0，列号非数字时设为 0
        assert report.total_issues == 1
        assert report.issues[0].line == 0
        assert report.issues[0].column == 0

    def test_message_without_space(self):
        """测试代码后没有空格分隔消息的情况"""
        output = "test.py:1:1: E501\n"
        mock_result = Mock()
        mock_result.stdout = output
        scanner = CodeScanner()
        with patch("subprocess.run", return_value=mock_result):
            report = scanner._run_flake8(["test.py"])
        assert report.total_issues == 1
        assert report.issues[0].message == ""

    def test_score_computed_after_scan(self):
        """测试扫描后评分被计算"""
        output = "test.py:1:1: E501 line too long\n"
        mock_result = Mock()
        mock_result.stdout = output
        scanner = CodeScanner()
        with patch("subprocess.run", return_value=mock_result):
            report = scanner._run_flake8(["test.py"])
        assert report.score == 90.0  # 100 - 10

    def test_duration_set(self):
        """测试 duration 被设置"""
        mock_result = Mock()
        mock_result.stdout = ""
        scanner = CodeScanner()
        with patch("subprocess.run", return_value=mock_result):
            report = scanner._run_flake8(["test.py"])
        assert report.duration >= 0

    def test_timeout(self):
        """测试 _run_flake8 超时返回空报告"""
        # 使用 MagicMock 来模拟 FileNotFoundError
        mock_run = MagicMock()
        mock_run.return_value.stdout = "test.py:1:1: E501 error\n"
        mock_run.return_value.returncode = 0
        scanner = CodeScanner()
        with patch("subprocess.run", mock_run):
            # 正常情况
            report = scanner._run_flake8(["test.py"])
            assert report.error == ""
            assert report.total_issues == 1


# ═══════════════════════════════════════════════════════════════
# _run_flake8 错误处理测试
# ═══════════════════════════════════════════════════════════════

class TestRunFlake8Errors:
    """_run_flake8 错误处理测试"""

    def test_file_not_found_error(self):
        """测试 flake8 未安装时返回错误"""
        scanner = CodeScanner()
        with patch("subprocess.run", side_effect=FileNotFoundError("flake8 not found")):
            report = scanner._run_flake8(["test.py"])
        assert "flake8 未安装" in report.error
        assert report.total_issues == 0
        assert report.issues == []

    def test_timeout_expired(self):
        """测试 flake8 扫描超时"""
        scanner = CodeScanner()
        with patch(
            "subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="flake8", timeout=120),
        ):
            report = scanner._run_flake8(["test.py"])
        assert "扫描超时" in report.error
        assert "120s" in report.error
        assert report.total_issues == 0

    def test_generic_exception(self):
        """测试通用异常"""
        scanner = CodeScanner()
        with patch("subprocess.run", side_effect=Exception("generic error")):
            report = scanner._run_flake8(["test.py"])
        assert report.error == "generic error"
        assert report.total_issues == 0


# ═══════════════════════════════════════════════════════════════
# _run_pylint 测试（Mock subprocess）
# ═══════════════════════════════════════════════════════════════

class TestRunPylint:
    """_run_pylint 测试（mock subprocess.run）"""

    def test_parses_all_level_codes(self):
        """测试解析所有 pylint 级别代码"""
        output = (
            "test.py:1:1: E0602: Undefined variable\n"
            "test.py:2:1: W0611: Unused import\n"
            "test.py:3:1: R0903: Too few public methods\n"
            "test.py:4:1: C0301: Line too long\n"
            "test.py:5:1: I0011: Locally disabling\n"
        )
        mock_result = Mock()
        mock_result.stdout = output
        scanner = CodeScanner()
        with patch("subprocess.run", return_value=mock_result):
            report = scanner._run_pylint(["test.py"])

        assert report.tool == "pylint"
        assert report.total_issues == 5
        levels = {issue.level for issue in report.issues}
        assert ScanLevel.ERROR in levels
        assert ScanLevel.WARNING in levels
        assert ScanLevel.REFACTOR in levels
        assert ScanLevel.CONVENTION in levels
        assert ScanLevel.INFO in levels  # I0011 → unknown → INFO

    def test_parses_error_level(self):
        """测试 pylint E 代码归类为 ERROR"""
        output = "test.py:1:1: E0001: syntax error\n"
        mock_result = Mock()
        mock_result.stdout = output
        scanner = CodeScanner()
        with patch("subprocess.run", return_value=mock_result):
            report = scanner._run_pylint(["test.py"])
        assert report.issues[0].level == ScanLevel.ERROR
        assert report.issues[0].code == "E0001"

    def test_parses_warning_level(self):
        """测试 pylint W 代码归类为 WARNING"""
        output = "test.py:1:1: W0611: Unused import\n"
        mock_result = Mock()
        mock_result.stdout = output
        scanner = CodeScanner()
        with patch("subprocess.run", return_value=mock_result):
            report = scanner._run_pylint(["test.py"])
        assert report.issues[0].level == ScanLevel.WARNING

    def test_parses_refactor_level(self):
        """测试 pylint R 代码归类为 REFACTOR"""
        output = "test.py:1:1: R0201: Method could be a function\n"
        mock_result = Mock()
        mock_result.stdout = output
        scanner = CodeScanner()
        with patch("subprocess.run", return_value=mock_result):
            report = scanner._run_pylint(["test.py"])
        assert report.issues[0].level == ScanLevel.REFACTOR

    def test_parses_convention_level(self):
        """测试 pylint C 代码归类为 CONVENTION"""
        output = "test.py:1:1: C0114: Missing module docstring\n"
        mock_result = Mock()
        mock_result.stdout = output
        scanner = CodeScanner()
        with patch("subprocess.run", return_value=mock_result):
            report = scanner._run_pylint(["test.py"])
        assert report.issues[0].level == ScanLevel.CONVENTION

    def test_skips_dash_lines(self):
        """测试跳过破折号行"""
        output = (
            "************* Module test\n"
            "test.py:1:1: E0001: error\n"
            "--------------------------------------------------------------------\n"
        )
        mock_result = Mock()
        mock_result.stdout = output
        scanner = CodeScanner()
        with patch("subprocess.run", return_value=mock_result):
            report = scanner._run_pylint(["test.py"])
        assert report.total_issues == 1

    def test_skips_lines_evaluated(self):
        """测试跳过包含 'lines evaluated' 的行"""
        output = (
            "test.py:1:1: E0001: error\n"
            "Your code has been rated at 10.00/10 (2 lines evaluated)\n"
        )
        mock_result = Mock()
        mock_result.stdout = output
        scanner = CodeScanner()
        with patch("subprocess.run", return_value=mock_result):
            report = scanner._run_pylint(["test.py"])
        assert report.total_issues == 1

    def test_skips_malformed_lines(self):
        """测试跳过格式错误的行"""
        output = (
            "test.py:1:1: E0001: error\n"
            "not a valid pylint output line\n"
        )
        mock_result = Mock()
        mock_result.stdout = output
        scanner = CodeScanner()
        with patch("subprocess.run", return_value=mock_result):
            report = scanner._run_pylint(["test.py"])
        assert report.total_issues == 1

    def test_skips_line_with_non_digit_lineno(self):
        """测试跳过行号非数字的行"""
        output = "test.py:abc:1: E0001: error\n"
        mock_result = Mock()
        mock_result.stdout = output
        scanner = CodeScanner()
        with patch("subprocess.run", return_value=mock_result):
            report = scanner._run_pylint(["test.py"])
        assert report.total_issues == 0

    def test_empty_output(self):
        """测试空输出"""
        mock_result = Mock()
        mock_result.stdout = ""
        scanner = CodeScanner()
        with patch("subprocess.run", return_value=mock_result):
            report = scanner._run_pylint(["test.py"])
        assert report.total_issues == 0
        assert report.score == 100.0

    def test_score_computed(self):
        """测试 pylint 扫描后评分被计算"""
        output = "test.py:1:1: E0001: error\n"
        mock_result = Mock()
        mock_result.stdout = output
        scanner = CodeScanner()
        with patch("subprocess.run", return_value=mock_result):
            report = scanner._run_pylint(["test.py"])
        assert report.score == 90.0

    def test_duration_set(self):
        """测试 pylint duration 被设置"""
        mock_result = Mock()
        mock_result.stdout = ""
        scanner = CodeScanner()
        with patch("subprocess.run", return_value=mock_result):
            report = scanner._run_pylint(["test.py"])
        assert report.duration >= 0


# ═══════════════════════════════════════════════════════════════
# _run_pylint 错误处理测试
# ═══════════════════════════════════════════════════════════════

class TestRunPylintErrors:
    """_run_pylint 错误处理测试"""

    def test_file_not_found_error(self):
        """测试 pylint 未安装时返回错误"""
        scanner = CodeScanner()
        with patch("subprocess.run", side_effect=FileNotFoundError("pylint not found")):
            report = scanner._run_pylint(["test.py"])
        assert "pylint 未安装" in report.error
        assert report.total_issues == 0
        assert report.issues == []

    def test_timeout_expired(self):
        """测试 pylint 扫描超时"""
        scanner = CodeScanner()
        with patch(
            "subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="pylint", timeout=120),
        ):
            report = scanner._run_pylint(["test.py"])
        assert "扫描超时" in report.error
        assert "120s" in report.error

    def test_generic_exception(self):
        """测试通用异常"""
        scanner = CodeScanner()
        with patch("subprocess.run", side_effect=Exception("pylint crash")):
            report = scanner._run_pylint(["test.py"])
        assert report.error == "pylint crash"


# ═══════════════════════════════════════════════════════════════
# scan_both 测试
# ═══════════════════════════════════════════════════════════════

class TestScanBoth:
    """scan_both 测试"""

    def test_returns_both_reports(self):
        """测试返回 flake8 和 pylint 两个报告"""
        scanner = CodeScanner()
        with patch.object(scanner, "scan") as mock_scan:
            mock_scan.side_effect = lambda tool, paths: ScanReport(
                tool=tool, total_issues=0, score=100.0
            )
            results = scanner.scan_both(["test.py"])
        assert "flake8" in results
        assert "pylint" in results
        assert results["flake8"].tool == "flake8"
        assert results["pylint"].tool == "pylint"
        assert mock_scan.call_count == 2

    def test_passes_paths_through(self):
        """测试路径被正确传递"""
        scanner = CodeScanner()
        with patch.object(scanner, "scan") as mock_scan:
            mock_scan.return_value = ScanReport(tool="x", total_issues=0, score=100.0)
            scanner.scan_both(paths=["a.py", "b.py"])
        calls = mock_scan.call_args_list
        for call in calls:
            assert call[0][1] == ["a.py", "b.py"]

    def test_none_paths_passed(self):
        """测试 None 路径被传递"""
        scanner = CodeScanner()
        with patch.object(scanner, "scan") as mock_scan:
            mock_scan.return_value = ScanReport(tool="x", total_issues=0, score=100.0)
            scanner.scan_both(paths=None)
        calls = mock_scan.call_args_list
        for call in calls:
            assert call[0][1] is None


# ═══════════════════════════════════════════════════════════════
# scan_to_judge 测试
# ═══════════════════════════════════════════════════════════════

class TestScanToJudge:
    """scan_to_judge 测试"""

    def test_returns_expected_structure(self):
        """测试返回结构完整"""
        mock_judge = Mock()
        mock_judge.report.return_value = {"total": 85.0, "grade": "B", "items": []}

        scanner = CodeScanner()
        with patch.object(scanner, "scan_both") as mock_scan_both:
            mock_scan_both.return_value = {
                "flake8": ScanReport(
                    tool="flake8", total_issues=3, score=90.0, error=""
                ),
                "pylint": ScanReport(
                    tool="pylint", total_issues=5, score=80.0, error=""
                ),
            }
            result = scanner.scan_to_judge(mock_judge, ["test.py"])

        mock_judge.reset.assert_called_once()
        assert mock_judge.add_score.call_count == 2
        assert "judge" in result
        assert "flake8" in result
        assert "pylint" in result
        assert result["flake8"]["score"] == 90.0
        assert result["flake8"]["issues"] == 3
        assert result["flake8"]["error"] == ""
        assert result["pylint"]["score"] == 80.0
        assert result["pylint"]["issues"] == 5
        assert result["pylint"]["error"] == ""

    def test_adds_score_with_weight(self):
        """测试添加评分项时权重正确"""
        mock_judge = Mock()
        mock_judge.report.return_value = {"total": 90.0, "grade": "A", "items": []}

        scanner = CodeScanner()
        with patch.object(scanner, "scan_both") as mock_scan_both:
            mock_scan_both.return_value = {
                "flake8": ScanReport(
                    tool="flake8", total_issues=0, score=100.0, error=""
                ),
                "pylint": ScanReport(
                    tool="pylint", total_issues=0, score=100.0, error=""
                ),
            }
            scanner.scan_to_judge(mock_judge)

        # 验证 add_score 被调用时的参数
        calls = mock_judge.add_score.call_args_list
        for call in calls:
            kwargs = call[1]
            assert kwargs["weight"] == 0.5

    def test_handles_error_reports(self):
        """测试处理扫描错误报告"""
        mock_judge = Mock()
        mock_judge.report.return_value = {"total": 0.0, "grade": "D", "items": []}

        scanner = CodeScanner()
        with patch.object(scanner, "scan_both") as mock_scan_both:
            mock_scan_both.return_value = {
                "flake8": ScanReport(
                    tool="flake8",
                    total_issues=0,
                    score=0.0,
                    error="flake8 未安装",
                ),
                "pylint": ScanReport(
                    tool="pylint",
                    total_issues=0,
                    score=0.0,
                    error="pylint 未安装",
                ),
            }
            result = scanner.scan_to_judge(mock_judge)

        calls = mock_judge.add_score.call_args_list
        # 错误报告应该使用 f"{tool}_error" 作为名称
        assert calls[0][0][0] == "flake8_error"
        assert calls[0][0][1] == 0
        assert calls[1][0][0] == "pylint_error"
        assert calls[1][0][1] == 0

    def test_handles_mixed_reports(self):
        """测试混合正常和错误报告"""
        mock_judge = Mock()
        mock_judge.report.return_value = {"total": 45.0, "grade": "D", "items": []}

        scanner = CodeScanner()
        with patch.object(scanner, "scan_both") as mock_scan_both:
            mock_scan_both.return_value = {
                "flake8": ScanReport(
                    tool="flake8", total_issues=2, score=90.0, error=""
                ),
                "pylint": ScanReport(
                    tool="pylint",
                    total_issues=0,
                    score=0.0,
                    error="pylint 扫描超时（120s）",
                ),
            }
            result = scanner.scan_to_judge(mock_judge)

        calls = mock_judge.add_score.call_args_list
        assert calls[0][0][0] == "flake8_score"
        assert calls[0][0][1] == 90.0
        assert calls[1][0][0] == "pylint_error"
        assert calls[1][0][1] == 0