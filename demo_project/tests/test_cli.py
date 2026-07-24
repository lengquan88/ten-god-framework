"""Tests for tengod CLI module.

Covers:
- main() with no arguments prints help
- main() with version subcommand outputs version string
- main() with --help flag
- Each subcommand help text is available
- Argument parsing for serve (--port, --host, --mode)
- Argument parsing for oracle (-q, -m)
- Argument parsing for generate (--prompt, --format, --provider)
- Argument parsing for knowledge (--search, --list, --stats, --limit)
- cmd_version() standalone
- cmd_serve() with mocked TenGodCore
- cmd_scan() with mocked scanner (file, directory, no scanner, results)
- cmd_oracle() with mocked oracle (full result, partial, defaults)
- cmd_status() with mocked export_state (modules, knowledge)
- cmd_generate() with mocked generator (with/without generator)
- cmd_knowledge() with mocked kb (search, list, stats, no kb, no args)
- cmd_mcp() with mocked MCPServer
- Edge cases: invalid subcommand, invalid mode choices, missing args
- Edge cases: missing keys in scan results, scan_file with non-existent path
- Edge cases: cmd_generate with all format/provider choices
- Edge cases: cmd_knowledge with empty stats, empty paginated result
- Edge cases: cmd_oracle with hexagram missing fields
- Edge cases: __name__ == "__main__" guard
"""

import sys
from unittest.mock import MagicMock, patch

import pytest

from tengod.cli import (
    cmd_version,
    cmd_serve,
    cmd_scan,
    cmd_oracle,
    cmd_status,
    cmd_generate,
    cmd_knowledge,
    cmd_mcp,
    main,
)


# ── Helpers ────────────────────────────────────────────────────────────


def _make_args(**kwargs):
    """Create a simple namespace object for command args."""
    ns = type("Args", (), {})()
    for k, v in kwargs.items():
        setattr(ns, k, v)
    return ns


def _install_mock_core(mock_core_inst=None):
    """Install a mock 'core' module with TenGodCore into sys.modules.

    Returns (mock_core_inst, mock_core_class).
    """
    if mock_core_inst is None:
        mock_core_inst = MagicMock()
    mock_core_class = MagicMock(return_value=mock_core_inst)
    mock_mod = MagicMock()
    mock_mod.TenGodCore = mock_core_class
    sys.modules["core"] = mock_mod
    return mock_core_inst, mock_core_class


def _install_mock_mcp_server(mock_server_inst=None):
    """Install a mock 'mcp_server' module with MCPServer into sys.modules.

    Returns mock_server_inst.
    """
    if mock_server_inst is None:
        mock_server_inst = MagicMock()
    mock_server_class = MagicMock(return_value=mock_server_inst)
    mock_mod = MagicMock()
    mock_mod.MCPServer = mock_server_class
    sys.modules["mcp_server"] = mock_mod
    return mock_server_inst


def _install_mock_shishen():
    """Install a mock '食神_创生输出' module into sys.modules."""
    mock_gen_config = MagicMock()
    mock_llm_provider = MagicMock()
    mock_output_format = MagicMock()
    mock_mod = MagicMock()
    mock_mod.GenerationConfig = mock_gen_config
    mock_mod.LLMProvider = mock_llm_provider
    mock_mod.OutputFormat = mock_output_format
    sys.modules["食神_创生输出"] = mock_mod
    return mock_gen_config, mock_llm_provider, mock_output_format


def _cleanup_mock_modules():
    """Remove mock modules from sys.modules to avoid cross-test pollution."""
    for mod_name in ("core", "mcp_server", "食神_创生输出"):
        sys.modules.pop(mod_name, None)


# ── main() top-level tests ──────────────────────────────────────────────


def test_main_no_args_prints_help(capsys):
    """main() with no subcommand prints usage/help text."""
    with patch.object(sys, "argv", ["tengod"]):
        main()
    captured = capsys.readouterr()
    assert "usage:" in captured.out.lower() or "tengod" in captured.out


def test_main_version_outputs_version_string(capsys):
    """main() with 'version' subcommand prints version info."""
    with patch.object(sys, "argv", ["tengod", "version"]):
        main()
    captured = capsys.readouterr()
    assert "v2.1.0" in captured.out
    assert "十神架构" in captured.out


def test_main_help_flag(capsys):
    """main() with --help flag prints help and exits."""
    with patch.object(sys, "argv", ["tengod", "--help"]):
        with pytest.raises(SystemExit) as exc_info:
            main()
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "usage:" in captured.out.lower() or "tengod" in captured.out


# ── Subcommand help text availability ──────────────────────────────────


@pytest.mark.parametrize("subcmd", [
    "serve",
    "scan",
    "oracle",
    "status",
    "generate",
    "knowledge",
    "mcp",
    "version",
])
def test_subcommand_help_text_available(subcmd, capsys):
    """Each subcommand's --help prints help text and exits 0."""
    with patch.object(sys, "argv", ["tengod", subcmd, "--help"]):
        with pytest.raises(SystemExit) as exc_info:
            main()
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert subcmd in captured.out


# ── serve argument parsing ─────────────────────────────────────────────


def test_serve_arg_parsing_defaults(capsys):
    """serve subcommand defaults are parsed correctly."""
    with patch.object(sys, "argv", ["tengod", "serve"]):
        with patch("tengod.cli.cmd_serve") as mock_cmd:
            main()
    mock_cmd.assert_called_once()
    args = mock_cmd.call_args[0][0]
    assert args.port == 8000
    assert args.host == "0.0.0.0"
    assert args.mode == "simple"


def test_serve_arg_parsing_custom(capsys):
    """serve subcommand with custom args is parsed correctly."""
    with patch.object(sys, "argv", [
        "tengod", "serve", "--port", "9000", "--host", "127.0.0.1", "--mode", "fastapi"
    ]):
        with patch("tengod.cli.cmd_serve") as mock_cmd:
            main()
    mock_cmd.assert_called_once()
    args = mock_cmd.call_args[0][0]
    assert args.port == 9000
    assert args.host == "127.0.0.1"
    assert args.mode == "fastapi"


def test_serve_invalid_mode(capsys):
    """serve --mode with invalid choice exits with error."""
    with patch.object(sys, "argv", ["tengod", "serve", "--mode", "invalid"]):
        with pytest.raises(SystemExit) as exc_info:
            main()
    assert exc_info.value.code != 0


# ── oracle argument parsing ────────────────────────────────────────────


def test_oracle_arg_parsing_defaults(capsys):
    """oracle subcommand defaults: question=None, mode='auto'."""
    with patch.object(sys, "argv", ["tengod", "oracle"]):
        with patch("tengod.cli.cmd_oracle") as mock_cmd:
            main()
    mock_cmd.assert_called_once()
    args = mock_cmd.call_args[0][0]
    assert args.question is None
    assert args.mode == "auto"


def test_oracle_arg_parsing_short_flags(capsys):
    """oracle subcommand with -q and -m short flags."""
    with patch.object(sys, "argv", [
        "tengod", "oracle", "-q", "今日运势如何", "-m", "yijing"
    ]):
        with patch("tengod.cli.cmd_oracle") as mock_cmd:
            main()
    mock_cmd.assert_called_once()
    args = mock_cmd.call_args[0][0]
    assert args.question == "今日运势如何"
    assert args.mode == "yijing"


def test_oracle_arg_parsing_long_flags(capsys):
    """oracle subcommand with --question and --mode long flags."""
    with patch.object(sys, "argv", [
        "tengod", "oracle", "--question", "Test?", "--mode", "bagua"
    ]):
        with patch("tengod.cli.cmd_oracle") as mock_cmd:
            main()
    mock_cmd.assert_called_once()
    args = mock_cmd.call_args[0][0]
    assert args.question == "Test?"
    assert args.mode == "bagua"


def test_oracle_invalid_mode(capsys):
    """oracle --mode with invalid choice exits with error."""
    with patch.object(sys, "argv", ["tengod", "oracle", "--mode", "invalid"]):
        with pytest.raises(SystemExit) as exc_info:
            main()
    assert exc_info.value.code != 0


# ── generate argument parsing ──────────────────────────────────────────


def test_generate_arg_parsing_defaults(capsys):
    """generate subcommand defaults: prompt=None, format='text', provider='mock'."""
    with patch.object(sys, "argv", ["tengod", "generate"]):
        with patch("tengod.cli.cmd_generate") as mock_cmd:
            main()
    mock_cmd.assert_called_once()
    args = mock_cmd.call_args[0][0]
    assert args.prompt is None
    assert args.format == "text"
    assert args.provider == "mock"


def test_generate_arg_parsing_custom(capsys):
    """generate subcommand with all custom args."""
    with patch.object(sys, "argv", [
        "tengod", "generate",
        "--prompt", "写一首诗",
        "--format", "markdown",
        "--provider", "openai",
    ]):
        with patch("tengod.cli.cmd_generate") as mock_cmd:
            main()
    mock_cmd.assert_called_once()
    args = mock_cmd.call_args[0][0]
    assert args.prompt == "写一首诗"
    assert args.format == "markdown"
    assert args.provider == "openai"


def test_generate_invalid_format(capsys):
    """generate --format with invalid choice exits with error."""
    with patch.object(sys, "argv", ["tengod", "generate", "--format", "invalid"]):
        with pytest.raises(SystemExit) as exc_info:
            main()
    assert exc_info.value.code != 0


def test_generate_invalid_provider(capsys):
    """generate --provider with invalid choice exits with error."""
    with patch.object(sys, "argv", ["tengod", "generate", "--provider", "invalid"]):
        with pytest.raises(SystemExit) as exc_info:
            main()
    assert exc_info.value.code != 0


# ── knowledge argument parsing ─────────────────────────────────────────


def test_knowledge_arg_parsing_defaults(capsys):
    """knowledge subcommand defaults: search=None, list=False, stats=False, limit=10."""
    with patch.object(sys, "argv", ["tengod", "knowledge"]):
        with patch("tengod.cli.cmd_knowledge") as mock_cmd:
            main()
    mock_cmd.assert_called_once()
    args = mock_cmd.call_args[0][0]
    assert args.search is None
    assert args.list is False
    assert args.stats is False
    assert args.limit == 10


def test_knowledge_arg_parsing_search(capsys):
    """knowledge --search sets the search query."""
    with patch.object(sys, "argv", [
        "tengod", "knowledge", "--search", "儒家"
    ]):
        with patch("tengod.cli.cmd_knowledge") as mock_cmd:
            main()
    mock_cmd.assert_called_once()
    args = mock_cmd.call_args[0][0]
    assert args.search == "儒家"
    assert args.list is False
    assert args.stats is False


def test_knowledge_arg_parsing_list(capsys):
    """knowledge --list is a boolean flag."""
    with patch.object(sys, "argv", ["tengod", "knowledge", "--list"]):
        with patch("tengod.cli.cmd_knowledge") as mock_cmd:
            main()
    mock_cmd.assert_called_once()
    args = mock_cmd.call_args[0][0]
    assert args.list is True


def test_knowledge_arg_parsing_stats(capsys):
    """knowledge --stats is a boolean flag."""
    with patch.object(sys, "argv", ["tengod", "knowledge", "--stats"]):
        with patch("tengod.cli.cmd_knowledge") as mock_cmd:
            main()
    mock_cmd.assert_called_once()
    args = mock_cmd.call_args[0][0]
    assert args.stats is True


def test_knowledge_arg_parsing_search_with_limit(capsys):
    """knowledge --search with custom --limit."""
    with patch.object(sys, "argv", [
        "tengod", "knowledge", "--search", "道家", "--limit", "5"
    ]):
        with patch("tengod.cli.cmd_knowledge") as mock_cmd:
            main()
    mock_cmd.assert_called_once()
    args = mock_cmd.call_args[0][0]
    assert args.search == "道家"
    assert args.limit == 5


# ── scan argument parsing ──────────────────────────────────────────────


def test_scan_arg_parsing_defaults(capsys):
    """scan subcommand default: path=None."""
    with patch.object(sys, "argv", ["tengod", "scan"]):
        with patch("tengod.cli.cmd_scan") as mock_cmd:
            main()
    mock_cmd.assert_called_once()
    args = mock_cmd.call_args[0][0]
    assert args.path is None


def test_scan_arg_parsing_with_path(capsys):
    """scan subcommand with --path."""
    with patch.object(sys, "argv", ["tengod", "scan", "--path", "./src"]):
        with patch("tengod.cli.cmd_scan") as mock_cmd:
            main()
    mock_cmd.assert_called_once()
    args = mock_cmd.call_args[0][0]
    assert args.path == "./src"


# ── cmd_version() standalone ───────────────────────────────────────────


def test_cmd_version_standalone(capsys):
    """cmd_version() prints version info when called directly."""
    cmd_version(None)
    captured = capsys.readouterr()
    assert "v2.1.0" in captured.out
    assert "十神架构" in captured.out
    assert "十二神模块" in captured.out


# ── Edge cases: main() ─────────────────────────────────────────────────


def test_main_invalid_subcommand(capsys):
    """main() with an unknown subcommand exits with non-zero code."""
    with patch.object(sys, "argv", ["tengod", "nonexistent"]):
        with pytest.raises(SystemExit) as exc_info:
            main()
    assert exc_info.value.code != 0


# ── cmd_serve() tests ──────────────────────────────────────────────────


class TestCmdServe:
    """Tests for cmd_serve()."""

    def test_serve_calls_core_run(self, capsys):
        """cmd_serve calls TenGodCore().run() with correct args."""
        core_inst, core_cls = _install_mock_core()
        try:
            args = _make_args(host="127.0.0.1", port=9999, mode="fastapi")
            cmd_serve(args)

            core_cls.assert_called_once()
            core_inst.run.assert_called_once_with(
                serve=True, host="127.0.0.1", port=9999, mode="fastapi"
            )
            captured = capsys.readouterr()
            assert "启动中" in captured.out
        finally:
            _cleanup_mock_modules()

    def test_serve_defaults(self, capsys):
        """cmd_serve with default args."""
        core_inst, core_cls = _install_mock_core()
        try:
            args = _make_args(host="0.0.0.0", port=8000, mode="simple")
            cmd_serve(args)

            core_inst.run.assert_called_once_with(
                serve=True, host="0.0.0.0", port=8000, mode="simple"
            )
        finally:
            _cleanup_mock_modules()

    def test_serve_mode_auto(self, capsys):
        """cmd_serve with mode='auto'."""
        core_inst, core_cls = _install_mock_core()
        try:
            args = _make_args(host="0.0.0.0", port=3000, mode="auto")
            cmd_serve(args)

            core_inst.run.assert_called_once_with(
                serve=True, host="0.0.0.0", port=3000, mode="auto"
            )
        finally:
            _cleanup_mock_modules()


# ── cmd_scan() tests ───────────────────────────────────────────────────


class TestCmdScan:
    """Tests for cmd_scan()."""

    def test_scan_no_scanner(self, capsys):
        """cmd_scan when scanner is None prints unavailable message."""
        core_inst = MagicMock()
        core_inst.scanner = None
        _install_mock_core(core_inst)
        try:
            args = _make_args(path=None)
            with patch("tengod.cli.os.getcwd", return_value="/fake/cwd"):
                cmd_scan(args)

            captured = capsys.readouterr()
            assert "扫描器不可用" in captured.out
        finally:
            _cleanup_mock_modules()

    def test_scan_no_results(self, capsys):
        """cmd_scan with scanner returning empty results."""
        core_inst = MagicMock()
        core_inst.scanner = MagicMock()
        core_inst.scanner.scan_code.return_value = []
        _install_mock_core(core_inst)
        try:
            args = _make_args(path=None)
            with patch("tengod.cli.os.getcwd", return_value="/fake/cwd"):
                cmd_scan(args)

            captured = capsys.readouterr()
            assert "未发现问题" in captured.out
        finally:
            _cleanup_mock_modules()

    def test_scan_with_results(self, capsys):
        """cmd_scan with scanner returning issues."""
        core_inst = MagicMock()
        core_inst.scanner = MagicMock()
        core_inst.scanner.scan_code.return_value = [
            {"severity": "error", "line": 10, "col": 5, "message": "bad code"},
            {"severity": "warn", "line": 20, "col": 0, "message": "style issue"},
            {"severity": "info", "line": 30, "col": 1, "message": "note"},
        ]
        _install_mock_core(core_inst)
        try:
            args = _make_args(path=None)
            with patch("tengod.cli.os.getcwd", return_value="/fake/cwd"):
                cmd_scan(args)

            captured = capsys.readouterr()
            assert "发现 3 个问题" in captured.out
            assert "[ERROR] L10:5 - bad code" in captured.out
            assert "[WARN] L20:0 - style issue" in captured.out
            assert "[INFO] L30:1 - note" in captured.out
        finally:
            _cleanup_mock_modules()

    def test_scan_with_results_missing_keys(self, capsys):
        """cmd_scan handles results with missing keys (uses defaults)."""
        core_inst = MagicMock()
        core_inst.scanner = MagicMock()
        core_inst.scanner.scan_code.return_value = [
            {"message": "no severity key"},
            {"severity": "warn"},
            {},
        ]
        _install_mock_core(core_inst)
        try:
            args = _make_args(path=None)
            with patch("tengod.cli.os.getcwd", return_value="/fake/cwd"):
                cmd_scan(args)

            captured = capsys.readouterr()
            assert "发现 3 个问题" in captured.out
            # Default severity is "info"
            assert "[INFO] L?:0 - no severity key" in captured.out
            # Default line is "?", default col is 0, default message is ""
            assert "[WARN] L?:0 - " in captured.out
            assert "[INFO] L?:0 - " in captured.out
        finally:
            _cleanup_mock_modules()

    def test_scan_with_file_path(self, capsys, tmp_path):
        """cmd_scan with a file path reads and scans the file."""
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')")

        core_inst = MagicMock()
        core_inst.scanner = MagicMock()
        core_inst.scanner.scan_code.return_value = [
            {"severity": "warn", "line": 1, "col": 0, "message": "ok"}
        ]
        _install_mock_core(core_inst)
        try:
            args = _make_args(path=str(test_file))
            cmd_scan(args)

            core_inst.scanner.scan_code.assert_called_once_with("print('hello')")
            captured = capsys.readouterr()
            assert "发现 1 个问题" in captured.out
        finally:
            _cleanup_mock_modules()

    def test_scan_with_directory_path(self, capsys):
        """cmd_scan with a directory path passes empty string to scanner."""
        core_inst = MagicMock()
        core_inst.scanner = MagicMock()
        core_inst.scanner.scan_code.return_value = []
        _install_mock_core(core_inst)
        try:
            args = _make_args(path="/some/dir")
            with patch("tengod.cli.os.path.isfile", return_value=False):
                cmd_scan(args)

            core_inst.scanner.scan_code.assert_called_once_with("")
        finally:
            _cleanup_mock_modules()

    def test_scan_default_path_uses_cwd(self, capsys):
        """cmd_scan with path=None uses os.getcwd()."""
        core_inst = MagicMock()
        core_inst.scanner = MagicMock()
        core_inst.scanner.scan_code.return_value = []
        _install_mock_core(core_inst)
        try:
            args = _make_args(path=None)
            with patch("tengod.cli.os.getcwd", return_value="/my/project"):
                with patch("tengod.cli.os.path.isfile", return_value=False):
                    cmd_scan(args)

            core_inst.scanner.scan_code.assert_called_once_with("")
            captured = capsys.readouterr()
            assert "扫描路径: /my/project" in captured.out
        finally:
            _cleanup_mock_modules()

    def test_scan_truncates_results_at_20(self, capsys):
        """cmd_scan only prints first 20 issues."""
        core_inst = MagicMock()
        core_inst.scanner = MagicMock()
        core_inst.scanner.scan_code.return_value = [
            {"severity": "info", "line": i, "col": 0, "message": f"issue {i}"}
            for i in range(25)
        ]
        _install_mock_core(core_inst)
        try:
            args = _make_args(path=None)
            with patch("tengod.cli.os.getcwd", return_value="/fake"):
                cmd_scan(args)

            captured = capsys.readouterr()
            assert "发现 25 个问题" in captured.out
            assert "issue 19" in captured.out
            assert "issue 20" not in captured.out
        finally:
            _cleanup_mock_modules()

    def test_scan_file_not_found(self, capsys):
        """cmd_scan with a non-existent file path raises FileNotFoundError."""
        core_inst = MagicMock()
        core_inst.scanner = MagicMock()
        _install_mock_core(core_inst)
        try:
            args = _make_args(path="/nonexistent/file.py")
            # os.path.isfile must return True to trigger the open() call
            with patch("tengod.cli.os.path.isfile", return_value=True):
                with pytest.raises(FileNotFoundError):
                    cmd_scan(args)
        finally:
            _cleanup_mock_modules()


# ── cmd_oracle() tests ─────────────────────────────────────────────────


class TestCmdOracle:
    """Tests for cmd_oracle()."""

    def test_oracle_full_result(self, capsys):
        """cmd_oracle prints full oracle result."""
        core_inst = MagicMock()
        core_inst.consult_oracle.return_value = {
            "hexagram": {
                "name": "乾为天",
                "symbol": "☰☰",
                "upper": "乾",
                "lower": "乾",
                "changing_lines": [3],
            },
            "interpretation": "大吉大利",
            "advice": "积极进取",
        }
        _install_mock_core(core_inst)
        try:
            args = _make_args(question="今日运势", mode="yijing")
            cmd_oracle(args)

            core_inst.consult_oracle.assert_called_once_with("今日运势", "yijing")
            captured = capsys.readouterr()
            assert "咨询 Oracle" in captured.out
            assert "卦象: 乾为天 (☰☰)" in captured.out
            assert "上卦: 乾  下卦: 乾" in captured.out
            assert "变爻: [3]" in captured.out
            assert "大吉大利" in captured.out
            assert "积极进取" in captured.out
        finally:
            _cleanup_mock_modules()

    def test_oracle_hexagram_missing_fields(self, capsys):
        """cmd_oracle handles hexagram with missing symbol/upper/lower/changing_lines."""
        core_inst = MagicMock()
        core_inst.consult_oracle.return_value = {
            "hexagram": {
                "name": "坤为地",
            },
            "interpretation": "厚德载物",
        }
        _install_mock_core(core_inst)
        try:
            args = _make_args(question="test", mode="bagua")
            cmd_oracle(args)

            captured = capsys.readouterr()
            assert "卦象: 坤为地 (?)" in captured.out
            assert "上卦: ?  下卦: ?" in captured.out
            assert "变爻: []" in captured.out
            assert "厚德载物" in captured.out
        finally:
            _cleanup_mock_modules()

    def test_oracle_partial_result_no_hexagram(self, capsys):
        """cmd_oracle handles result without hexagram."""
        core_inst = MagicMock()
        core_inst.consult_oracle.return_value = {
            "interpretation": "顺其自然",
            "advice": "保持冷静",
        }
        _install_mock_core(core_inst)
        try:
            args = _make_args(question="test", mode="auto")
            cmd_oracle(args)

            captured = capsys.readouterr()
            assert "顺其自然" in captured.out
            assert "保持冷静" in captured.out
            assert "卦象" not in captured.out
        finally:
            _cleanup_mock_modules()

    def test_oracle_partial_result_only_interpretation(self, capsys):
        """cmd_oracle handles result with only interpretation."""
        core_inst = MagicMock()
        core_inst.consult_oracle.return_value = {
            "interpretation": "平平无奇",
        }
        _install_mock_core(core_inst)
        try:
            args = _make_args(question="test", mode="auto")
            cmd_oracle(args)

            captured = capsys.readouterr()
            assert "平平无奇" in captured.out
            assert "建议" not in captured.out
        finally:
            _cleanup_mock_modules()

    def test_oracle_default_question(self, capsys):
        """cmd_oracle uses default question when args.question is None."""
        core_inst = MagicMock()
        core_inst.consult_oracle.return_value = {}
        _install_mock_core(core_inst)
        try:
            args = _make_args(question=None, mode=None)
            cmd_oracle(args)

            core_inst.consult_oracle.assert_called_once_with("当前运势如何", "auto")
        finally:
            _cleanup_mock_modules()

    def test_oracle_default_mode(self, capsys):
        """cmd_oracle uses 'auto' mode when args.mode is None."""
        core_inst = MagicMock()
        core_inst.consult_oracle.return_value = {}
        _install_mock_core(core_inst)
        try:
            args = _make_args(question="test", mode=None)
            cmd_oracle(args)

            core_inst.consult_oracle.assert_called_once_with("test", "auto")
        finally:
            _cleanup_mock_modules()

    def test_oracle_empty_result(self, capsys):
        """cmd_oracle handles empty result dict."""
        core_inst = MagicMock()
        core_inst.consult_oracle.return_value = {}
        _install_mock_core(core_inst)
        try:
            args = _make_args(question="test", mode="wuxing")
            cmd_oracle(args)

            captured = capsys.readouterr()
            assert "咨询 Oracle" in captured.out
        finally:
            _cleanup_mock_modules()

    def test_oracle_mode_wuxing(self, capsys):
        """cmd_oracle with wuxing mode."""
        core_inst = MagicMock()
        core_inst.consult_oracle.return_value = {
            "hexagram": {
                "name": "水火既济",
                "symbol": "☵☲",
                "upper": "坎",
                "lower": "离",
                "changing_lines": [],
            },
            "interpretation": "五行调和",
            "advice": "顺势而为",
        }
        _install_mock_core(core_inst)
        try:
            args = _make_args(question="五行运势", mode="wuxing")
            cmd_oracle(args)

            core_inst.consult_oracle.assert_called_once_with("五行运势", "wuxing")
            captured = capsys.readouterr()
            assert "模式: wuxing" in captured.out
            assert "卦象: 水火既济 (☵☲)" in captured.out
        finally:
            _cleanup_mock_modules()


# ── cmd_status() tests ─────────────────────────────────────────────────


class TestCmdStatus:
    """Tests for cmd_status()."""

    def test_status_with_modules(self, capsys):
        """cmd_status prints module statuses."""
        core_inst = MagicMock()
        core_inst.export_state.return_value = {
            "version": "2.0.0",
            "modules": {
                "scanner": True,
                "oracle": False,
                "kb": True,
            },
            "knowledge": {},
        }
        _install_mock_core(core_inst)
        try:
            args = _make_args()
            cmd_status(args)

            captured = capsys.readouterr()
            assert "v2.0.0" in captured.out
            assert "模块状态" in captured.out
            assert "✓ scanner" in captured.out
            assert "✗ oracle" in captured.out
            assert "✓ kb" in captured.out
        finally:
            _cleanup_mock_modules()

    def test_status_with_knowledge(self, capsys):
        """cmd_status prints knowledge stats."""
        core_inst = MagicMock()
        core_inst.export_state.return_value = {
            "version": "1.0",
            "modules": {},
            "knowledge": {"nodes": 42, "edges": 99},
        }
        _install_mock_core(core_inst)
        try:
            args = _make_args()
            cmd_status(args)

            captured = capsys.readouterr()
            assert "42 节点" in captured.out
            assert "99 边" in captured.out
        finally:
            _cleanup_mock_modules()

    def test_status_no_modules_no_knowledge(self, capsys):
        """cmd_status with empty state."""
        core_inst = MagicMock()
        core_inst.export_state.return_value = {
            "version": "1.0",
        }
        _install_mock_core(core_inst)
        try:
            args = _make_args()
            cmd_status(args)

            captured = capsys.readouterr()
            assert "v1.0" in captured.out
            assert "模块状态" not in captured.out
            assert "知识库" not in captured.out
        finally:
            _cleanup_mock_modules()

    def test_status_empty_modules(self, capsys):
        """cmd_status with empty modules dict."""
        core_inst = MagicMock()
        core_inst.export_state.return_value = {
            "version": "1.0",
            "modules": {},
            "knowledge": {},
        }
        _install_mock_core(core_inst)
        try:
            args = _make_args()
            cmd_status(args)

            captured = capsys.readouterr()
            assert "模块状态" not in captured.out
            assert "知识库" not in captured.out
        finally:
            _cleanup_mock_modules()

    def test_status_missing_version(self, capsys):
        """cmd_status with state missing version key."""
        core_inst = MagicMock()
        core_inst.export_state.return_value = {
            "modules": {"scanner": True},
        }
        _install_mock_core(core_inst)
        try:
            args = _make_args()
            cmd_status(args)

            captured = capsys.readouterr()
            assert "v?" in captured.out
        finally:
            _cleanup_mock_modules()


# ── cmd_generate() tests ───────────────────────────────────────────────


class TestCmdGenerate:
    """Tests for cmd_generate()."""

    def test_generate_with_generator(self, capsys):
        """cmd_generate with generator available."""
        core_inst = MagicMock()
        core_inst.generator = MagicMock()
        core_inst.generator.generate.return_value = "生成的内容"
        _install_mock_core(core_inst)
        gen_cfg, llm_prov, out_fmt = _install_mock_shishen()
        try:
            args = _make_args(prompt="写一首诗", format="markdown", provider="openai")
            cmd_generate(args)

            out_fmt.assert_called_once_with("markdown")
            llm_prov.assert_called_once_with("openai")
            gen_cfg.assert_called_once()
            core_inst.generator.generate.assert_called_once_with("写一首诗", gen_cfg.return_value)

            captured = capsys.readouterr()
            assert "生成中" in captured.out
            assert "生成的内容" in captured.out
        finally:
            _cleanup_mock_modules()

    def test_generate_no_generator(self, capsys):
        """cmd_generate when generator is None."""
        core_inst = MagicMock()
        core_inst.generator = None
        _install_mock_core(core_inst)
        _install_mock_shishen()
        try:
            args = _make_args(prompt="test", format="text", provider="mock")
            cmd_generate(args)

            captured = capsys.readouterr()
            assert "生成器不可用" in captured.out
        finally:
            _cleanup_mock_modules()

    def test_generate_defaults(self, capsys):
        """cmd_generate with default prompt/format/provider."""
        core_inst = MagicMock()
        core_inst.generator = MagicMock()
        core_inst.generator.generate.return_value = "默认内容"
        _install_mock_core(core_inst)
        _install_mock_shishen()
        try:
            args = _make_args(prompt=None, format=None, provider=None)
            cmd_generate(args)

            core_inst.generator.generate.assert_called_once()
            call_args = core_inst.generator.generate.call_args[0]
            assert call_args[0] == "你好"

            captured = capsys.readouterr()
            assert "默认内容" in captured.out
        finally:
            _cleanup_mock_modules()

    def test_generate_format_json(self, capsys):
        """cmd_generate with format='json'."""
        core_inst = MagicMock()
        core_inst.generator = MagicMock()
        core_inst.generator.generate.return_value = '{"result": "ok"}'
        _install_mock_core(core_inst)
        out_fmt = _install_mock_shishen()[2]
        try:
            args = _make_args(prompt="test", format="json", provider="mock")
            cmd_generate(args)

            out_fmt.assert_called_once_with("json")
            captured = capsys.readouterr()
            assert '{"result": "ok"}' in captured.out
        finally:
            _cleanup_mock_modules()

    def test_generate_format_html(self, capsys):
        """cmd_generate with format='html'."""
        core_inst = MagicMock()
        core_inst.generator = MagicMock()
        core_inst.generator.generate.return_value = "<p>hello</p>"
        _install_mock_core(core_inst)
        out_fmt = _install_mock_shishen()[2]
        try:
            args = _make_args(prompt="test", format="html", provider="mock")
            cmd_generate(args)

            out_fmt.assert_called_once_with("html")
            captured = capsys.readouterr()
            assert "<p>hello</p>" in captured.out
        finally:
            _cleanup_mock_modules()

    def test_generate_format_code(self, capsys):
        """cmd_generate with format='code'."""
        core_inst = MagicMock()
        core_inst.generator = MagicMock()
        core_inst.generator.generate.return_value = "def foo(): pass"
        _install_mock_core(core_inst)
        out_fmt = _install_mock_shishen()[2]
        try:
            args = _make_args(prompt="test", format="code", provider="mock")
            cmd_generate(args)

            out_fmt.assert_called_once_with("code")
            captured = capsys.readouterr()
            assert "def foo(): pass" in captured.out
        finally:
            _cleanup_mock_modules()

    def test_generate_provider_claude(self, capsys):
        """cmd_generate with provider='claude'."""
        core_inst = MagicMock()
        core_inst.generator = MagicMock()
        core_inst.generator.generate.return_value = "claude output"
        _install_mock_core(core_inst)
        llm_prov = _install_mock_shishen()[1]
        try:
            args = _make_args(prompt="test", format="text", provider="claude")
            cmd_generate(args)

            llm_prov.assert_called_once_with("claude")
            captured = capsys.readouterr()
            assert "claude output" in captured.out
        finally:
            _cleanup_mock_modules()


# ── cmd_knowledge() tests ──────────────────────────────────────────────


class TestCmdKnowledge:
    """Tests for cmd_knowledge()."""

    def test_knowledge_search(self, capsys):
        """cmd_knowledge with --search."""
        core_inst = MagicMock()
        core_inst.kb = MagicMock()
        core_inst.kb.query_nearest.return_value = [
            {"node_type": "concept", "name": "道", "score": 0.95},
            {"node_type": "entity", "name": "德", "score": 0.87},
        ]
        _install_mock_core(core_inst)
        try:
            args = _make_args(search="道家", list=False, stats=False, limit=5)
            cmd_knowledge(args)

            core_inst.kb.query_nearest.assert_called_once_with("道家", top_k=5)
            captured = capsys.readouterr()
            assert "搜索: 道家" in captured.out
            assert "结果数: 2" in captured.out
            assert "[concept] 道 (相似度: 0.9500)" in captured.out
            assert "[entity] 德 (相似度: 0.8700)" in captured.out
        finally:
            _cleanup_mock_modules()

    def test_knowledge_search_no_kb(self, capsys):
        """cmd_knowledge --search when kb is None."""
        core_inst = MagicMock()
        core_inst.kb = None
        _install_mock_core(core_inst)
        try:
            args = _make_args(search="test", list=False, stats=False, limit=10)
            cmd_knowledge(args)

            captured = capsys.readouterr()
            assert "知识库不可用" in captured.out
        finally:
            _cleanup_mock_modules()

    def test_knowledge_search_empty_results(self, capsys):
        """cmd_knowledge --search with empty results."""
        core_inst = MagicMock()
        core_inst.kb = MagicMock()
        core_inst.kb.query_nearest.return_value = []
        _install_mock_core(core_inst)
        try:
            args = _make_args(search="nonexistent", list=False, stats=False, limit=10)
            cmd_knowledge(args)

            captured = capsys.readouterr()
            assert "搜索: nonexistent" in captured.out
            assert "结果数: 0" in captured.out
        finally:
            _cleanup_mock_modules()

    def test_knowledge_list(self, capsys):
        """cmd_knowledge with --list."""
        core_inst = MagicMock()
        core_inst.kb = MagicMock()
        mock_node = MagicMock()
        mock_node.node_type = "concept"
        mock_node.name = "阴阳"
        mock_node2 = MagicMock()
        mock_node2.node_type = "entity"
        mock_node2.name = "五行"
        core_inst.kb.query_paginated.return_value = {
            "total": 2,
            "items": [mock_node, mock_node2],
        }
        _install_mock_core(core_inst)
        try:
            args = _make_args(search=None, list=True, stats=False, limit=10)
            cmd_knowledge(args)

            core_inst.kb.query_paginated.assert_called_once_with(page=1, page_size=100)
            captured = capsys.readouterr()
            assert "节点总数: 2" in captured.out
            assert "[concept] 阴阳" in captured.out
            assert "[entity] 五行" in captured.out
        finally:
            _cleanup_mock_modules()

    def test_knowledge_list_no_kb(self, capsys):
        """cmd_knowledge --list when kb is None."""
        core_inst = MagicMock()
        core_inst.kb = None
        _install_mock_core(core_inst)
        try:
            args = _make_args(search=None, list=True, stats=False, limit=10)
            cmd_knowledge(args)

            captured = capsys.readouterr()
            assert "知识库不可用" in captured.out
        finally:
            _cleanup_mock_modules()

    def test_knowledge_list_empty(self, capsys):
        """cmd_knowledge --list with empty paginated result."""
        core_inst = MagicMock()
        core_inst.kb = MagicMock()
        core_inst.kb.query_paginated.return_value = {
            "total": 0,
            "items": [],
        }
        _install_mock_core(core_inst)
        try:
            args = _make_args(search=None, list=True, stats=False, limit=10)
            cmd_knowledge(args)

            captured = capsys.readouterr()
            assert "节点总数: 0" in captured.out
        finally:
            _cleanup_mock_modules()

    def test_knowledge_list_missing_total(self, capsys):
        """cmd_knowledge --list with result missing 'total' key."""
        core_inst = MagicMock()
        core_inst.kb = MagicMock()
        core_inst.kb.query_paginated.return_value = {
            "items": [],
        }
        _install_mock_core(core_inst)
        try:
            args = _make_args(search=None, list=True, stats=False, limit=10)
            cmd_knowledge(args)

            captured = capsys.readouterr()
            assert "节点总数: 0" in captured.out
        finally:
            _cleanup_mock_modules()

    def test_knowledge_stats(self, capsys):
        """cmd_knowledge with --stats."""
        core_inst = MagicMock()
        core_inst.kb = MagicMock()
        core_inst.kb.stats.return_value = {
            "nodes": 100,
            "edges": 200,
            "type_distribution": {"concept": 60, "entity": 40},
            "backend": "faiss",
        }
        _install_mock_core(core_inst)
        try:
            args = _make_args(search=None, list=False, stats=True, limit=10)
            cmd_knowledge(args)

            core_inst.kb.stats.assert_called_once()
            captured = capsys.readouterr()
            assert "知识库统计" in captured.out
            assert "节点: 100" in captured.out
            assert "边: 200" in captured.out
            assert "类型分布:" in captured.out
            assert "后端: faiss" in captured.out
        finally:
            _cleanup_mock_modules()

    def test_knowledge_stats_no_kb(self, capsys):
        """cmd_knowledge --stats when kb is None."""
        core_inst = MagicMock()
        core_inst.kb = None
        _install_mock_core(core_inst)
        try:
            args = _make_args(search=None, list=False, stats=True, limit=10)
            cmd_knowledge(args)

            captured = capsys.readouterr()
            assert "知识库不可用" in captured.out
        finally:
            _cleanup_mock_modules()

    def test_knowledge_stats_empty(self, capsys):
        """cmd_knowledge --stats with empty stats dict."""
        core_inst = MagicMock()
        core_inst.kb = MagicMock()
        core_inst.kb.stats.return_value = {}
        _install_mock_core(core_inst)
        try:
            args = _make_args(search=None, list=False, stats=True, limit=10)
            cmd_knowledge(args)

            captured = capsys.readouterr()
            assert "知识库统计" in captured.out
            assert "节点: 0" in captured.out
            assert "边: 0" in captured.out
            assert "类型分布: {}" in captured.out
            assert "后端: unknown" in captured.out
        finally:
            _cleanup_mock_modules()

    def test_knowledge_no_args(self, capsys):
        """cmd_knowledge with no --search, --list, or --stats."""
        core_inst = MagicMock()
        core_inst.kb = MagicMock()
        _install_mock_core(core_inst)
        try:
            args = _make_args(search=None, list=False, stats=False, limit=10)
            cmd_knowledge(args)

            captured = capsys.readouterr()
            assert "请指定 --search, --list, 或 --stats" in captured.out
        finally:
            _cleanup_mock_modules()

    def test_knowledge_search_default_limit(self, capsys):
        """cmd_knowledge --search uses default limit 10 when limit is None."""
        core_inst = MagicMock()
        core_inst.kb = MagicMock()
        core_inst.kb.query_nearest.return_value = []
        _install_mock_core(core_inst)
        try:
            args = _make_args(search="test", list=False, stats=False, limit=None)
            cmd_knowledge(args)

            core_inst.kb.query_nearest.assert_called_once_with("test", top_k=10)
        finally:
            _cleanup_mock_modules()

    def test_knowledge_list_truncates_at_20(self, capsys):
        """cmd_knowledge --list only prints first 20 items."""
        core_inst = MagicMock()
        core_inst.kb = MagicMock()
        items = []
        for i in range(25):
            node = MagicMock()
            node.node_type = "concept"
            node.name = f"node_{i}"
            items.append(node)
        core_inst.kb.query_paginated.return_value = {
            "total": 25,
            "items": items,
        }
        _install_mock_core(core_inst)
        try:
            args = _make_args(search=None, list=True, stats=False, limit=10)
            cmd_knowledge(args)

            captured = capsys.readouterr()
            assert "节点总数: 25" in captured.out
            assert "node_19" in captured.out
            assert "node_20" not in captured.out
        finally:
            _cleanup_mock_modules()


# ── cmd_mcp() tests ────────────────────────────────────────────────────


class TestCmdMcp:
    """Tests for cmd_mcp()."""

    def test_mcp_starts_server(self, capsys):
        """cmd_mcp creates MCPServer and calls run()."""
        server_inst = _install_mock_mcp_server()
        try:
            args = _make_args()
            cmd_mcp(args)

            server_inst.run.assert_called_once()
            captured = capsys.readouterr()
            assert "MCP Server 启动" in captured.err
        finally:
            _cleanup_mock_modules()

    def test_mcp_server_instantiation(self, capsys):
        """cmd_mcp verifies MCPServer is instantiated."""
        server_inst = _install_mock_mcp_server()
        try:
            args = _make_args()
            cmd_mcp(args)

            server_inst.run.assert_called_once()
        finally:
            _cleanup_mock_modules()


# ── Integration: main() dispatches to correct cmd_* function ───────────


class TestMainDispatch:
    """Tests that main() dispatches to the correct command function."""

    def test_main_dispatches_to_cmd_scan(self, capsys):
        """main() calls cmd_scan for 'scan' subcommand."""
        with patch.object(sys, "argv", ["tengod", "scan", "--path", "/tmp"]):
            with patch("tengod.cli.cmd_scan") as mock_cmd:
                main()
        mock_cmd.assert_called_once()

    def test_main_dispatches_to_cmd_status(self, capsys):
        """main() calls cmd_status for 'status' subcommand."""
        with patch.object(sys, "argv", ["tengod", "status"]):
            with patch("tengod.cli.cmd_status") as mock_cmd:
                main()
        mock_cmd.assert_called_once()

    def test_main_dispatches_to_cmd_mcp(self, capsys):
        """main() calls cmd_mcp for 'mcp' subcommand."""
        with patch.object(sys, "argv", ["tengod", "mcp"]):
            with patch("tengod.cli.cmd_mcp") as mock_cmd:
                main()
        mock_cmd.assert_called_once()

    def test_main_dispatches_to_cmd_serve(self, capsys):
        """main() calls cmd_serve for 'serve' subcommand."""
        with patch.object(sys, "argv", ["tengod", "serve"]):
            with patch("tengod.cli.cmd_serve") as mock_cmd:
                main()
        mock_cmd.assert_called_once()

    def test_main_dispatches_to_cmd_oracle(self, capsys):
        """main() calls cmd_oracle for 'oracle' subcommand."""
        with patch.object(sys, "argv", ["tengod", "oracle"]):
            with patch("tengod.cli.cmd_oracle") as mock_cmd:
                main()
        mock_cmd.assert_called_once()

    def test_main_dispatches_to_cmd_generate(self, capsys):
        """main() calls cmd_generate for 'generate' subcommand."""
        with patch.object(sys, "argv", ["tengod", "generate"]):
            with patch("tengod.cli.cmd_generate") as mock_cmd:
                main()
        mock_cmd.assert_called_once()

    def test_main_dispatches_to_cmd_knowledge(self, capsys):
        """main() calls cmd_knowledge for 'knowledge' subcommand."""
        with patch.object(sys, "argv", ["tengod", "knowledge"]):
            with patch("tengod.cli.cmd_knowledge") as mock_cmd:
                main()
        mock_cmd.assert_called_once()

    def test_main_dispatches_to_cmd_version(self, capsys):
        """main() calls cmd_version for 'version' subcommand."""
        with patch.object(sys, "argv", ["tengod", "version"]):
            with patch("tengod.cli.cmd_version") as mock_cmd:
                main()
        mock_cmd.assert_called_once()


# ── Edge: main() with no subcommand dispatches to print_help ───────────


def test_main_no_subcommand_shows_help(capsys):
    """main() with only flags but no subcommand shows help."""
    with patch.object(sys, "argv", ["tengod"]):
        main()
    captured = capsys.readouterr()
    assert "usage:" in captured.out.lower() or "tengod" in captured.out or "十神架构" in captured.out


# ── __name__ == "__main__" guard ────────────────────────────────────────


def test_main_guard(capsys):
    """The __name__ == '__main__' guard invokes main() correctly."""
    # We simulate the guard by calling main() directly with mocked argv
    with patch.object(sys, "argv", ["tengod", "version"]):
        main()
    captured = capsys.readouterr()
    assert "v2.1.0" in captured.out