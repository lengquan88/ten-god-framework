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
"""

import sys
from unittest.mock import patch

import pytest

from tengod.cli import cmd_version, main


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
    # Subcommand help should mention the subcommand name
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


# ── cmd_version() standalone ───────────────────────────────────────────


def test_cmd_version_standalone(capsys):
    """cmd_version() prints version info when called directly."""
    cmd_version(None)
    captured = capsys.readouterr()
    assert "v2.1.0" in captured.out
    assert "十神架构" in captured.out
    assert "十二神模块" in captured.out


# ── Edge cases ─────────────────────────────────────────────────────────


def test_main_invalid_subcommand(capsys):
    """main() with an unknown subcommand prints error and exits."""
    with patch.object(sys, "argv", ["tengod", "nonexistent"]):
        with pytest.raises(SystemExit) as exc_info:
            main()
    assert exc_info.value.code != 0