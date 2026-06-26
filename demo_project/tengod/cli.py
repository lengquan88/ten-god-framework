#!/usr/bin/env python3
"""tengod — 十神架构 CLI 工具 v2.1.0

命令:
    tengod serve         启动 HTTP 服务
    tengod scan          代码扫描
    tengod oracle        咨询 Oracle
    tengod status        查看系统状态
    tengod generate      内容生成
    tengod knowledge     知识库管理
    tengod version       显示版本
    tengod mcp           启动 MCP Server

用法:
    tengod serve --port 8000 --host 0.0.0.0
    tengod oracle -q "今日运势如何"
    tengod scan --path ./src
    tengod knowledge --search "儒家"
    tengod generate --prompt "写一首诗" --format markdown
"""
import argparse
import os
import sys


def cmd_serve(args):
    """启动 HTTP 服务"""
    print("十神架构服务启动中...")
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

    from core import TenGodCore

    core = TenGodCore()
    core.run(
        serve=True,
        host=args.host,
        port=args.port,
        mode=args.mode,
    )


def cmd_scan(args):
    """代码扫描"""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

    scan_path = args.path or os.getcwd()
    print(f"扫描路径: {scan_path}")

    from core import TenGodCore

    core = TenGodCore()
    core.run(serve=False)

    if core.scanner:
        results = core.scanner.scan_code(open(scan_path).read() if os.path.isfile(scan_path) else "")
        if results:
            print(f"\n发现 {len(results)} 个问题:")
            for issue in results[:20]:
                sev = issue.get("severity", "info")
                line = issue.get("line", "?")
                msg = issue.get("message", "")
                col = issue.get("col", 0)
                print(f"  [{sev.upper()}] L{line}:{col} - {msg}")
        else:
            print("未发现问题。")
    else:
        print("扫描器不可用。")


def cmd_oracle(args):
    """咨询 Oracle"""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

    from core import TenGodCore

    core = TenGodCore()
    core.run(serve=False)

    question = args.question or "当前运势如何"
    mode = args.mode or "auto"

    print(f"\n{'='*50}")
    print("  咨询 Oracle")
    print(f"  问题: {question}")
    print(f"  模式: {mode}")
    print(f"{'='*50}\n")

    result = core.consult_oracle(question, mode)

    hexagram = result.get("hexagram", {})
    if hexagram:
        print(f"  卦象: {hexagram.get('name', '?')} ({hexagram.get('symbol', '?')})")
        print(f"  上卦: {hexagram.get('upper', '?')}  下卦: {hexagram.get('lower', '?')}")
        print(f"  变爻: {hexagram.get('changing_lines', [])}")

    interpretation = result.get("interpretation", "")
    if interpretation:
        print(f"\n  解读:\n  {interpretation}")

    advice = result.get("advice", "")
    if advice:
        print(f"\n  建议:\n  {advice}")

    print(f"\n{'='*50}\n")


def cmd_status(args):
    """查看系统状态"""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

    from core import TenGodCore

    core = TenGodCore()
    core.run(serve=False)

    state = core.export_state()
    print(f"\n{'='*50}")
    print(f"  十神架构 v{state.get('version', '?')} 状态")
    print(f"{'='*50}")

    modules = state.get("modules", {})
    if modules:
        print("\n  模块状态:")
        for name, status in modules.items():
            icon = "✓" if status else "✗"
            print(f"    {icon} {name}")

    knowledge = state.get("knowledge", {})
    if knowledge:
        print(f"\n  知识库: {knowledge.get('nodes', 0)} 节点, {knowledge.get('edges', 0)} 边")

    print(f"\n{'='*50}\n")


def cmd_generate(args):
    """内容生成"""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

    from core import TenGodCore
    from 食神_创生输出 import GenerationConfig, LLMProvider, OutputFormat

    core = TenGodCore()
    core.run(serve=False)

    prompt = args.prompt or "你好"
    fmt = args.format or "text"
    provider = args.provider or "mock"

    print(f"生成中... (格式: {fmt}, 提供商: {provider})")

    if core.generator:
        cfg = GenerationConfig(
            format=OutputFormat(fmt),
            provider=LLMProvider(provider),
        )
        result = core.generator.generate(prompt, cfg)
        print(f"\n{'='*50}")
        print(result)
        print(f"{'='*50}\n")
    else:
        print("生成器不可用。")


def cmd_knowledge(args):
    """知识库管理"""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

    from core import TenGodCore

    core = TenGodCore()
    core.run(serve=False)

    if args.search:
        if core.kb:
            results = core.kb.query_nearest(args.search, top_k=args.limit or 10)
            print(f"\n搜索: {args.search}")
            print(f"结果数: {len(results)}")
            for r in results:
                print(f"  [{r['node_type']}] {r['name']} (相似度: {r['score']:.4f})")
        else:
            print("知识库不可用。")
    elif args.list:
        if core.kb:
            nodes = core.kb.query_paginated(page=1, page_size=100)
            print(f"\n节点总数: {nodes.get('total', 0)}")
            for n in nodes.get("items", [])[:20]:
                print(f"  [{n.node_type}] {n.name}")
        else:
            print("知识库不可用。")
    elif args.stats:
        if core.kb:
            stats = core.kb.stats()
            print("\n知识库统计:")
            print(f"  节点: {stats.get('nodes', 0)}")
            print(f"  边: {stats.get('edges', 0)}")
            print(f"  类型分布: {stats.get('type_distribution', {})}")
            print(f"  后端: {stats.get('backend', 'unknown')}")
        else:
            print("知识库不可用。")
    else:
        print("请指定 --search, --list, 或 --stats")


def cmd_mcp(args):
    """启动 MCP Server"""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

    from mcp_server import MCPServer

    server = MCPServer()
    print("十神 MCP Server 启动 (stdio)", file=sys.stderr)
    server.run()


def cmd_version(args):
    """显示版本"""
    print("十神架构 CLI v2.1.0")
    print("十二神模块 | 30+ API | 100+ 知识节点")
    print("MCP Server | CLI Tools | Multi-SDK")


def main():
    parser = argparse.ArgumentParser(
        description="十神架构 CLI 工具",
        prog="tengod",
    )
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # serve
    serve_parser = subparsers.add_parser("serve", help="启动 HTTP 服务")
    serve_parser.add_argument("--port", type=int, default=8000)
    serve_parser.add_argument("--host", default="0.0.0.0")
    serve_parser.add_argument("--mode", default="simple", choices=["simple", "fastapi", "auto"])

    # scan
    scan_parser = subparsers.add_parser("scan", help="代码扫描")
    scan_parser.add_argument("--path", default=None)

    # oracle
    oracle_parser = subparsers.add_parser("oracle", help="咨询 Oracle")
    oracle_parser.add_argument("-q", "--question", default=None)
    oracle_parser.add_argument("-m", "--mode", default="auto", choices=["auto", "yijing", "wuxing", "bagua"])

    # status
    subparsers.add_parser("status", help="查看系统状态")

    # generate
    gen_parser = subparsers.add_parser("generate", help="内容生成")
    gen_parser.add_argument("--prompt", default=None)
    gen_parser.add_argument("--format", default="text", choices=["text", "markdown", "json", "html", "code"])
    gen_parser.add_argument("--provider", default="mock", choices=["mock", "openai", "claude"])

    # knowledge
    know_parser = subparsers.add_parser("knowledge", help="知识库管理")
    know_parser.add_argument("--search", default=None)
    know_parser.add_argument("--list", action="store_true")
    know_parser.add_argument("--stats", action="store_true")
    know_parser.add_argument("--limit", type=int, default=10)

    # mcp
    subparsers.add_parser("mcp", help="启动 MCP Server")

    # version
    subparsers.add_parser("version", help="显示版本")

    args = parser.parse_args()

    if args.command == "serve":
        cmd_serve(args)
    elif args.command == "scan":
        cmd_scan(args)
    elif args.command == "oracle":
        cmd_oracle(args)
    elif args.command == "status":
        cmd_status(args)
    elif args.command == "generate":
        cmd_generate(args)
    elif args.command == "knowledge":
        cmd_knowledge(args)
    elif args.command == "mcp":
        cmd_mcp(args)
    elif args.command == "version":
        cmd_version(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()