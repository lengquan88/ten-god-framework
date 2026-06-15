"""mcp_server.py — 十神 MCP Server v2.1.0

Model Context Protocol 服务端实现，让 Claude 等 AI 可直接调用十神能力。

支持的工具:
- tengod_oracle: 咨询十神 Oracle
- tengod_knowledge_search: 知识库搜索
- tengod_generate: 内容生成
- tengod_evaluate: 代码评估
- tengod_task_submit: 提交任务
- tengod_list_components: 列出组件

用法:
    python -m tengod.mcp_server
    # 或通过 stdio 传输（标准 MCP 模式）
    python -m tengod.mcp_server --transport stdio
"""
import json
import sys
import os
import asyncio
from typing import Any, Dict, List, Optional


# ============ MCP 协议常量 ============

MCP_VERSION = "2024-11-05"
PROTOCOL_NAME = "tengod-mcp"


class MCPServer:
    """十神 MCP Server — 通过 stdio 与 AI 助手通信"""

    def __init__(self):
        self._tools: Dict[str, Dict] = {}
        self._core = None
        self._initialized = False
        self._register_tools()

    def _get_core(self):
        """延迟导入 Core"""
        if self._core is None:
            try:
                from core import TenGodCore
                self._core = TenGodCore()
                self._core.run(serve=False)
            except Exception:
                self._core = "unavailable"
        return self._core if self._core != "unavailable" else None

    def _register_tools(self):
        """注册所有 MCP 工具"""
        self._tools = {
            "tengod_oracle": {
                "name": "tengod_oracle",
                "description": "咨询十神 Oracle — 获取中华文明智慧对问题的洞察",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "question": {
                            "type": "string",
                            "description": "要咨询的问题",
                        },
                        "mode": {
                            "type": "string",
                            "description": "占卜模式：auto（自动）/ yijing（易经）/ wuxing（五行）/ bagua（八卦）",
                            "enum": ["auto", "yijing", "wuxing", "bagua"],
                            "default": "auto",
                        },
                    },
                    "required": ["question"],
                },
            },
            "tengod_knowledge_search": {
                "name": "tengod_knowledge_search",
                "description": "搜索十神知识库 — 查询中华文明知识节点",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "搜索关键词",
                        },
                        "node_type": {
                            "type": "string",
                            "description": "节点类型过滤",
                        },
                        "top_k": {
                            "type": "integer",
                            "description": "返回结果数量",
                            "default": 5,
                        },
                    },
                    "required": ["query"],
                },
            },
            "tengod_generate": {
                "name": "tengod_generate",
                "description": "使用十神食神生成内容 — 支持文本/代码/JSON/HTML/Markdown",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "prompt": {
                            "type": "string",
                            "description": "生成提示词",
                        },
                        "format": {
                            "type": "string",
                            "description": "输出格式",
                            "enum": ["text", "markdown", "json", "html", "code"],
                            "default": "text",
                        },
                        "provider": {
                            "type": "string",
                            "description": "生成提供商",
                            "enum": ["mock", "openai", "claude"],
                            "default": "mock",
                        },
                    },
                    "required": ["prompt"],
                },
            },
            "tengod_evaluate": {
                "name": "tengod_evaluate",
                "description": "使用十神七杀评估代码质量",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "要评估的代码",
                        },
                        "language": {
                            "type": "string",
                            "description": "编程语言",
                            "default": "python",
                        },
                    },
                    "required": ["code"],
                },
            },
            "tengod_list_components": {
                "name": "tengod_list_components",
                "description": "列出十神架构所有模块及其状态",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            },
            "tengod_get_status": {
                "name": "tengod_get_status",
                "description": "获取十神系统整体状态",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            },
        }

    def _handle_initialize(self, params: Dict) -> Dict:
        """处理 initialize 请求"""
        self._initialized = True
        return {
            "protocolVersion": MCP_VERSION,
            "capabilities": {
                "tools": {},
            },
            "serverInfo": {
                "name": "tengod",
                "version": "2.1.0",
            },
        }

    def _handle_list_tools(self, params: Dict) -> Dict:
        """处理 tools/list 请求"""
        return {"tools": list(self._tools.values())}

    def _handle_call_tool(self, params: Dict) -> Dict:
        """处理 tools/call 请求"""
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        if tool_name not in self._tools:
            return {
                "content": [{"type": "text", "text": f"Unknown tool: {tool_name}"}],
                "isError": True,
            }

        try:
            result = self._execute_tool(tool_name, arguments)
            return {
                "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}],
            }
        except Exception as e:
            return {
                "content": [{"type": "text", "text": f"Error: {e}"}],
                "isError": True,
            }

    def _execute_tool(self, tool_name: str, arguments: Dict) -> Any:
        """执行具体工具"""
        core = self._get_core()

        if tool_name == "tengod_oracle":
            question = arguments.get("question", "")
            mode = arguments.get("mode", "auto")
            if core:
                result = core.consult_oracle(question, mode)
                return {
                    "question": question,
                    "mode": mode,
                    "hexagram": result.get("hexagram", {}),
                    "interpretation": result.get("interpretation", ""),
                    "advice": result.get("advice", ""),
                }
            return {"question": question, "answer": "Oracle unavailable (core not loaded)"}

        elif tool_name == "tengod_knowledge_search":
            query = arguments.get("query", "")
            top_k = arguments.get("top_k", 5)
            node_type = arguments.get("node_type")
            if core and core.kb:
                results = core.kb.query_nearest(query, top_k=top_k, node_type=node_type)
                return {
                    "query": query,
                    "total": len(results),
                    "results": [
                        {"name": r["name"], "type": r["node_type"], "score": round(r["score"], 4)}
                        for r in results
                    ],
                }
            return {"query": query, "total": 0, "results": []}

        elif tool_name == "tengod_generate":
            prompt = arguments.get("prompt", "")
            fmt = arguments.get("format", "text")
            provider = arguments.get("provider", "mock")
            if core and core.generator:
                from 食神_创生输出 import GenerationConfig, LLMProvider, OutputFormat
                cfg = GenerationConfig(
                    format=OutputFormat(fmt),
                    provider=LLMProvider(provider),
                )
                text = core.generator.generate(prompt, cfg)
                return {"prompt": prompt, "format": fmt, "output": text}
            return {"prompt": prompt, "output": "Generator unavailable"}

        elif tool_name == "tengod_evaluate":
            code = arguments.get("code", "")
            language = arguments.get("language", "python")
            if core and core.scanner:
                results = core.scanner.scan_code(code)
                return {
                    "language": language,
                    "total_issues": len(results),
                    "issues": results[:20],
                }
            return {"language": language, "issues": []}

        elif tool_name == "tengod_list_components":
            if core:
                state = core.export_state()
                return {
                    "components": state.get("modules", {}),
                    "status": state.get("balancer", {}),
                }
            return {"components": {}}

        elif tool_name == "tengod_get_status":
            if core:
                state = core.export_state()
                return {
                    "version": "2.1.0",
                    "modules": state.get("modules", {}),
                    "knowledge": state.get("knowledge", {}),
                    "oracle": state.get("oracle", {}),
                    "consensus": state.get("consensus", {}),
                }
            return {"version": "2.1.0", "status": "core unavailable"}

        return {"error": f"Unknown tool: {tool_name}"}

    def _handle_request(self, request: Dict) -> Optional[Dict]:
        """处理 JSON-RPC 请求"""
        method = request.get("method", "")
        params = request.get("params", {})
        req_id = request.get("id")

        try:
            if method == "initialize":
                result = self._handle_initialize(params)
            elif method == "tools/list":
                result = self._handle_list_tools(params)
            elif method == "tools/call":
                result = self._handle_call_tool(params)
            elif method == "notifications/initialized":
                return None  # 通知不需要响应
            else:
                result = {"error": f"Unknown method: {method}"}

            return {"jsonrpc": "2.0", "id": req_id, "result": result}
        except Exception as e:
            return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32603, "message": str(e)}}

    async def run_stdio(self):
        """通过 stdio 运行 MCP Server"""
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)

        writer_transport, writer_protocol = await asyncio.get_event_loop().connect_write_pipe(
            lambda: asyncio.streams.FlowControlMixin(loop=asyncio.get_event_loop()),
            sys.stdout,
        )

        buf = bytearray()
        while True:
            chunk = await reader.read(4096)
            if not chunk:
                break
            buf.extend(chunk)

            while True:
                try:
                    data = buf.decode("utf-8")
                    request = json.loads(data)
                    buf.clear()

                    response = self._handle_request(request)
                    if response:
                        resp_str = json.dumps(response, ensure_ascii=False) + "\n"
                        sys.stdout.write(resp_str)
                        sys.stdout.flush()
                except json.JSONDecodeError:
                    break
                except Exception:
                    break

    def run(self):
        """主入口"""
        asyncio.run(self.run_stdio())


def main():
    """CLI 入口"""
    server = MCPServer()
    server.run()


if __name__ == "__main__":
    main()