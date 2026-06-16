"""mcp_server.py — 十神 MCP Server v2.2.0

Model Context Protocol 服务端实现，让 Claude 等 AI 可直接调用十神能力。

支持的工具（基础 + 玄学扩展）:
[基础工具]
- tengod_oracle: 咨询十神 Oracle
- tengod_knowledge_search: 知识库搜索
- tengod_generate: 内容生成
- tengod_evaluate: 代码评估
- tengod_list_components: 列出组件
- tengod_get_status: 获取系统状态

[玄学扩展工具 · 阶段二新增]
- tengod_wuxing_query: 五行查询（生克/方位/脏腑）
- tengod_bagua_query: 八卦查询（先天/后天/64卦）
- tengod_shigan_derive: 十神推演（日干+天干→十神）
- tengod_dizhi_analyze: 地支分析（藏干/六合/三合/六冲/六害/六破/相刑）
- tengod_bazi_calc: 八字排盘（年月日时→四柱+大运+流年+分析）

[玄学扩展工具 · 阶段四新增]
- tengod_shensha_calc: 神煞推算（40+神煞，含天德/月德/桃花/华盖/魁罡等）
- tengod_geju_judge: 格局判断（从旺格/官杀格/财格/食伤格/印绶格/比劫格）
- tengod_yongshen: 喜用神分析（旺衰/调候/忌神/五行平衡）

[玄学扩展工具 · 阶段五新增]
- tengod_semantic_search: 语义搜索（自然语言查询知识图谱，支持类型过滤）
- tengod_knowledge_recommend: 知识关联推荐（节点关系推荐 + 生克推断）

用法:
    python -m tengod.mcp_server
    python -m tengod.mcp_server --transport stdio
    # 本地测试（非 stdio）：
    python demo_project/tengod/mcp_server.py --test
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
            # ============ 阶段二：玄学扩展工具 ============
            "tengod_wuxing_query": {
                "name": "tengod_wuxing_query",
                "description": "五行查询 — 金木水火土的生克关系/方位/脏腑/天干地支对应/颜色/季节/数字。"
                             "可输入五行名（如'木'或'mu'）或两个五行名来查生克关系。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "element": {
                            "type": "string",
                            "description": "查询的五行元素：木/火/土/金/水（或英文 Wood/Fire/Earth/Metal/Water）",
                        },
                        "other_element": {
                            "type": "string",
                            "description": "可选第二个五行元素，用于查询两者的生克关系",
                        },
                        "relation_mode": {
                            "type": "string",
                            "description": "查询模式：info（基本信息）/ shengke（生克分析）/ cycle（完整循环）",
                            "enum": ["info", "shengke", "cycle"],
                            "default": "info",
                        },
                    },
                    "required": ["element"],
                },
            },
            "tengod_bagua_query": {
                "name": "tengod_bagua_query",
                "description": "八卦查询 — 先天八卦/后天八卦方位、卦辞、卦象、五行、象征、六十四卦推演。"
                             "可输入单卦名（如'乾'）或两个卦名（如'乾','坤'）推演六十四卦。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "trigram": {
                            "type": "string",
                            "description": "查询的单卦：乾/兑/离/震/巽/坎/艮/坤",
                        },
                        "upper_trigram": {
                            "type": "string",
                            "description": "上卦（用于推演六十四卦）",
                        },
                        "lower_trigram": {
                            "type": "string",
                            "description": "下卦（用于推演六十四卦）",
                        },
                        "query_type": {
                            "type": "string",
                            "description": "查询类型：xiantian（先天八卦方位）/ houtian（后天八卦方位）/ info（基本信息）/ hexagram（六十四卦推演）",
                            "enum": ["xiantian", "houtian", "info", "hexagram"],
                            "default": "info",
                        },
                    },
                    "required": ["trigram"],
                },
            },
            "tengod_shigan_derive": {
                "name": "tengod_shigan_derive",
                "description": "十神推演 — 给定日主天干和其他天干，推导出对应的十神"
                             "（比肩/劫财/食神/伤官/正财/偏财/正官/七杀/正印/偏印）。"
                             "同时支持查询十神分类（善神/凶神）和关系描述。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "day_master": {
                            "type": "string",
                            "description": "日主天干：甲/乙/丙/丁/戊/己/庚/辛/壬/癸",
                        },
                        "gan": {
                            "type": "string",
                            "description": "要推演的天干（或天干列表用逗号分隔，如'甲,乙,丙,丁'）",
                        },
                        "detail_level": {
                            "type": "string",
                            "description": "详细程度：basic（仅十神名）/ full（含描述+分类）",
                            "enum": ["basic", "full"],
                            "default": "full",
                        },
                    },
                    "required": ["day_master", "gan"],
                },
            },
            "tengod_dizhi_analyze": {
                "name": "tengod_dizhi_analyze",
                "description": "地支分析 — 给定一个或多个地支，分析其藏干、六合、三合、三会、六冲、六害、六破、相刑关系。"
                             "例如输入 '子午' 可查六冲，输入 '子丑' 可查六合。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "branches": {
                            "type": "string",
                            "description": "地支（支持单地支或多个地支，如 '子' 或 '子,丑,寅' 或 '子午卯酉'）",
                        },
                        "analysis_type": {
                            "type": "string",
                            "description": "分析类型：canggan（藏干）/ liuhe（六合）/ sanhe（三合）/ sanhui（三会）/ "
                                          "liuchong（六冲）/ liuhai（六害）/ liupo（六破）/ xiangxing（相刑）/ all（全部）",
                            "enum": ["canggan", "liuhe", "sanhe", "sanhui", "liuchong", "liuhai", "liupo", "xiangxing", "all"],
                            "default": "all",
                        },
                    },
                    "required": ["branches"],
                },
            },
            "tengod_bazi_calc": {
                "name": "tengod_bazi_calc",
                "description": "八字排盘 — 给定出生日期（年月日时），输出完整八字命盘，"
                             "包括四柱干支、日主五行、真太阳时修正、大运（10步）、流年、五行分布、十神分布、地支关系、分析结论。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "year": {
                            "type": "integer",
                            "description": "出生年份（公历）",
                            "minimum": 1900,
                            "maximum": 2100,
                        },
                        "month": {
                            "type": "integer",
                            "description": "出生月份（1-12）",
                            "minimum": 1,
                            "maximum": 12,
                        },
                        "day": {
                            "type": "integer",
                            "description": "出生日（1-31）",
                            "minimum": 1,
                            "maximum": 31,
                        },
                        "hour": {
                            "type": "integer",
                            "description": "出生小时（0-23），北京时间",
                            "minimum": 0,
                            "maximum": 23,
                            "default": 12,
                        },
                        "minute": {
                            "type": "integer",
                            "description": "出生分钟（0-59）",
                            "minimum": 0,
                            "maximum": 59,
                            "default": 0,
                        },
                        "gender": {
                            "type": "string",
                            "description": "性别（影响大运顺逆）",
                            "enum": ["male", "female"],
                            "default": "male",
                        },
                        "longitude": {
                            "type": "number",
                            "description": "经度（用于真太阳时修正，默认116.4即北京时区中心）",
                            "default": 116.4,
                        },
                        "latitude": {
                            "type": "number",
                            "description": "纬度",
                            "default": 39.9,
                        },
                        "output_level": {
                            "type": "string",
                            "description": "输出级别：pillars_only（仅四柱）/ standard（标准输出）/ full（含所有分析）",
                            "enum": ["pillars_only", "standard", "full"],
                            "default": "standard",
                        },
                    },
                    "required": ["year", "month", "day"],
                },
            },
            # ============ 阶段二工具结束 ============
            # ============ 阶段四工具：神煞 + 格局 + 喜用神 ============
            "tengod_shensha_calc": {
                "name": "tengod_shensha_calc",
                "description": "神煞推算 — 给定四柱，输出全部神煞（吉神/凶神/中性），包括天德、月德、桃花、驿马、华盖、劫煞等40+神煞",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "pillars": {
                            "type": "object",
                            "description": "四柱字典，格式 {\"year\": \"庚午\", \"month\": \"壬午\", \"day\": \"辛亥\", \"hour\": \"癸巳\"}",
                            "properties": {
                                "year": {"type": "string", "description": "年柱，如'庚午'"},
                                "month": {"type": "string", "description": "月柱，如'壬午'"},
                                "day": {"type": "string", "description": "日柱，如'辛亥'"},
                                "hour": {"type": "string", "description": "时柱，如'癸巳'"},
                            },
                            "required": ["year", "month", "day", "hour"],
                        },
                        "detail_level": {
                            "type": "string",
                            "description": "输出级别：basic（摘要）/ full（完整报告）",
                            "enum": ["basic", "full"],
                            "default": "basic",
                        },
                    },
                    "required": ["pillars"],
                },
            },
            "tengod_geju_judge": {
                "name": "tengod_geju_judge",
                "description": "格局判断 — 推算八字格局（从旺格、官杀格、财格、食伤格、印绶格、比劫格等）及忌神分析",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "pillars": {
                            "type": "object",
                            "description": "四柱字典",
                            "properties": {
                                "year": {"type": "string"},
                                "month": {"type": "string"},
                                "day": {"type": "string"},
                                "hour": {"type": "string"},
                            },
                            "required": ["year", "month", "day", "hour"],
                        },
                        "detail_level": {
                            "type": "string",
                            "enum": ["basic", "full"],
                            "default": "basic",
                        },
                    },
                    "required": ["pillars"],
                },
            },
            "tengod_yongshen": {
                "name": "tengod_yongshen",
                "description": "喜用神分析 — 综合旺衰判断、调候分析、格局喜忌，推算喜神、忌神，并生成五行平衡报告",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "pillars": {
                            "type": "object",
                            "description": "四柱字典",
                            "properties": {
                                "year": {"type": "string"},
                                "month": {"type": "string"},
                                "day": {"type": "string"},
                                "hour": {"type": "string"},
                            },
                            "required": ["year", "month", "day", "hour"],
                        },
                        "detail_level": {
                            "type": "string",
                            "enum": ["basic", "full"],
                            "default": "basic",
                        },
                    },
                    "required": ["pillars"],
                },
            },
            # ============ 阶段四工具结束 ============
            # ============ 阶段五工具：向量检索 ============
            "tengod_semantic_search": {
                "name": "tengod_semantic_search",
                "description": "语义搜索 — 自然语言查询知识图谱，支持中文语义理解和类型过滤。示例：\"找所有属木的概念\"、\"与火相关的知识\"、\"东方方位\"",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "自然语言查询语句",
                        },
                        "top_k": {
                            "type": "integer",
                            "description": "返回结果数（默认10）",
                            "default": 10,
                        },
                        "type_filter": {
                            "type": "string",
                            "description": "类型过滤（可选），如 \"五行\"、\"八卦\"、\"天干\"、\"地支\"、\"十神\"、\"河图洛书\"、\"六十四卦\"",
                        },
                    },
                    "required": ["query"],
                },
            },
            "tengod_knowledge_recommend": {
                "name": "tengod_knowledge_recommend",
                "description": "知识关联推荐 — 给定一个知识节点名称，推荐语义相关的其他节点，并推断生克关系",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "node_name": {
                            "type": "string",
                            "description": "知识节点名称，如 \"木\"、\"乾\"、\"甲\"、\"子\"、\"正官\"、\"河图\"",
                        },
                        "top_k": {
                            "type": "integer",
                            "description": "返回结果数（默认5）",
                            "default": 5,
                        },
                    },
                    "required": ["node_name"],
                },
            },
            # ============ 阶段五工具结束 ============
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

        # ============ 阶段二：玄学扩展工具处理 ============
        elif tool_name == "tengod_wuxing_query":
            return self._tool_wuxing_query(arguments)
        elif tool_name == "tengod_bagua_query":
            return self._tool_bagua_query(arguments)
        elif tool_name == "tengod_shigan_derive":
            return self._tool_shigan_derive(arguments)
        elif tool_name == "tengod_dizhi_analyze":
            return self._tool_dizhi_analyze(arguments)
        elif tool_name == "tengod_bazi_calc":
            return self._tool_bazi_calc(arguments)

        # ============ 阶段四：神煞 + 格局 + 喜用神 ============
        elif tool_name == "tengod_shensha_calc":
            return self._tool_shensha_calc(arguments)
        elif tool_name == "tengod_geju_judge":
            return self._tool_geju_judge(arguments)
        elif tool_name == "tengod_yongshen":
            return self._tool_yongshen(arguments)

        # ============ 阶段五：向量检索 ============
        elif tool_name == "tengod_semantic_search":
            return self._tool_semantic_search(arguments)
        elif tool_name == "tengod_knowledge_recommend":
            return self._tool_knowledge_recommend(arguments)

        return {"error": f"Unknown tool: {tool_name}"}

    # ============ 阶段二：玄学工具实现 ============

    def _tool_wuxing_query(self, arguments: Dict) -> Any:
        """五行查询工具"""
        try:
            from tengod.knowledge_graph import KnowledgeGraph
            from tengod.divination_engine import WuxingEngine
            kg = KnowledgeGraph()
        except Exception as e:
            return {"error": f"KnowledgeGraph unavailable: {e}"}

        element = str(arguments.get("element", "")).strip()
        other = str(arguments.get("other_element", "")).strip()
        mode = str(arguments.get("relation_mode", "info"))

        # 输入规范化 (English -> 中文)
        en2cn = {"wood": "木", "fire": "火", "earth": "土", "metal": "金", "water": "水"}
        if element.lower() in en2cn:
            element = en2cn[element.lower()]
        if other.lower() in en2cn:
            other = en2cn[other.lower()]

        valid_elements = ["木", "火", "土", "金", "水"]
        if element not in valid_elements:
            return {"error": f"无效的五行元素 '{element}'，有效值：{', '.join(valid_elements)}"}

        # info 模式: 基本信息 + 生克关系
        if mode == "info":
            try:
                entity = kg.get_element(element)
            except Exception as e:
                entity = f"详情不可用: {e}"
            # 生克关系（使用 WuxingEngine.generate/restrict）
            sheng_ke_detail = {}
            for other_e in valid_elements:
                if other_e == element:
                    continue
                relation = "无直接关系"
                try:
                    gen = WuxingEngine.generate(element, other_e)
                    if gen and not (isinstance(gen, dict) and "error" in str(gen)):
                        relation = f"{element} 生 {other_e}"
                    else:
                        # 尝试反向
                        gen_rev = WuxingEngine.generate(other_e, element)
                        if gen_rev and not (isinstance(gen_rev, dict) and "error" in str(gen_rev)):
                            relation = f"{other_e} 生 {element}"
                        else:
                            # 尝试克
                            rst = WuxingEngine.restrict(element, other_e)
                            if rst and not (isinstance(rst, dict) and "error" in str(rst)):
                                relation = f"{element} 克 {other_e}"
                            else:
                                rst_rev = WuxingEngine.restrict(other_e, element)
                                if rst_rev and not (isinstance(rst_rev, dict) and "error" in str(rst_rev)):
                                    relation = f"{other_e} 克 {element}"
                except Exception:
                    pass
                sheng_ke_detail[other_e] = relation
            return {
                "element": element,
                "entity": entity,
                "relations": sheng_ke_detail,
                "note": "五行相生：木→火→土→金→水→木；五行相克：木→土→水→火→金→木",
            }

        # shengke 模式: 两元素关系
        if mode == "shengke" and other:
            if other not in valid_elements:
                return {"error": f"无效的五行元素 '{other}'，有效值：{', '.join(valid_elements)}"}
            try:
                gen = WuxingEngine.generate(element, other)
                if gen and not (isinstance(gen, dict) and "error" in str(gen)):
                    return {"element_a": element, "element_b": other, "relation": "相生",
                            "detail": f"{element}生{other}", "type": "sheng"}
            except Exception:
                pass
            try:
                gen = WuxingEngine.generate(other, element)
                if gen and not (isinstance(gen, dict) and "error" in str(gen)):
                    return {"element_a": element, "element_b": other, "relation": "相生",
                            "detail": f"{other}生{element}", "type": "sheng"}
            except Exception:
                pass
            try:
                rst = WuxingEngine.restrict(element, other)
                if rst and not (isinstance(rst, dict) and "error" in str(rst)):
                    return {"element_a": element, "element_b": other, "relation": "相克",
                            "detail": f"{element}克{other}", "type": "ke"}
            except Exception:
                pass
            try:
                rst = WuxingEngine.restrict(other, element)
                if rst and not (isinstance(rst, dict) and "error" in str(rst)):
                    return {"element_a": element, "element_b": other, "relation": "相克",
                            "detail": f"{other}克{element}", "type": "ke"}
            except Exception:
                pass
            return {"element_a": element, "element_b": other, "relation": "无直接生克", "type": "none"}

        # cycle 模式
        if mode == "cycle":
            return {
                "mode": "cycle",
                "sheng_cycle": "木→火→土→金→水→木",
                "ke_cycle": "木→土→水→火→金→木",
                "notes": "五行相生: 木生火, 火生土, 土生金, 金生水, 水生木；五行相克: 木克土, 土克水, 水克火, 火克金, 金克木",
            }

        return {"element": element, "available_modes": ["info", "shengke", "cycle"]}

    def _tool_bagua_query(self, arguments: Dict) -> Any:
        """八卦查询工具"""
        try:
            from tengod.knowledge_graph import KnowledgeGraph
            kg = KnowledgeGraph()
        except Exception as e:
            return {"error": f"KnowledgeGraph unavailable: {e}"}

        trigram = str(arguments.get("trigram", "")).strip()
        upper = str(arguments.get("upper_trigram", "")).strip()
        lower = str(arguments.get("lower_trigram", "")).strip()
        query_type = str(arguments.get("query_type", "info"))

        valid_trigrams = ["乾", "兑", "离", "震", "巽", "坎", "艮", "坤"]
        if trigram and trigram not in valid_trigrams:
            return {"error": f"无效的八卦名 '{trigram}'，有效值：{', '.join(valid_trigrams)}"}

        # 六十四卦推演
        if query_type == "hexagram":
            if not (upper and lower):
                return {"error": "hexagram 模式需要 upper_trigram 和 lower_trigram"}
            if upper not in valid_trigrams or lower not in valid_trigrams:
                return {"error": f"无效的八卦名，有效值：{', '.join(valid_trigrams)}"}
            try:
                hexagram = kg.get_liushisi_gua()
                # 简单查找匹配
                key = upper + lower
                matched = {}
                if isinstance(hexagram, dict):
                    for k, v in hexagram.items():
                        if key in k or k in key:
                            matched[k] = v
                            break
                return {
                    "upper_trigram": upper,
                    "lower_trigram": lower,
                    "hexagram_name": key,
                    "search_result": matched or "简化版引擎中未预加载此64卦详情（请参考周易原典）",
                    "note": "六十四卦共64种组合，完整卦辞请参考《周易》",
                }
            except Exception as e:
                return {"error": str(e), "hexagram_name": upper + lower}

        # 先天/后天方位
        if query_type in ("xiantian", "houtian"):
            hetu = kg.get_hetu() if query_type == "xiantian" else kg.get_luoshu()
            entity = kg.get_trigram(trigram)
            return {
                "mode": "先天八卦" if query_type == "xiantian" else "后天八卦",
                "trigram": trigram,
                "info": entity,
                "diagram_reference": "先天八卦：乾南坤北，离东坎西，震东北，巽西南，艮西北，兑东南；后天八卦：离南坎北，震东兑西，巽东南，乾西北，坤西南，艮东北",
                "diagram": hetu,
            }

        # info 模式
        entity = kg.get_trigram(trigram)
        return {"trigram": trigram, "info": entity}

    def _tool_shigan_derive(self, arguments: Dict) -> Any:
        """十神推演工具"""
        try:
            from tengod.divination_engine import ShiganEngine
            from tengod.knowledge_graph import KnowledgeGraph
            kg = KnowledgeGraph()
        except Exception as e:
            return {"error": f"Engine unavailable: {e}"}

        day_master = str(arguments.get("day_master", "")).strip()
        gan_str = str(arguments.get("gan", "")).strip()
        detail = str(arguments.get("detail_level", "full"))

        valid_gans = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
        if day_master not in valid_gans:
            return {"error": f"无效的日干 '{day_master}'，有效值：{', '.join(valid_gans)}"}

        # 支持逗号分隔或单字列表
        if "," in gan_str:
            gans = [g.strip() for g in gan_str.split(",") if g.strip()]
        elif len(gan_str) > 1 and all(g in valid_gans for g in gan_str):
            gans = list(gan_str)
        else:
            gans = [gan_str] if gan_str else []

        if not gans:
            return {"error": "未指定要推演的天干"}

        results = []
        for g in gans:
            if g not in valid_gans:
                results.append({"gan": g, "error": f"无效天干"})
                continue
            try:
                r = ShiganEngine.compute(day_master, g)
                shigan_name = r.shigan.value if hasattr(r.shigan, "value") else str(r.shigan)
                item = {
                    "gan": g,
                    "shigan": shigan_name,
                }
                if detail == "full":
                    try:
                        entity = kg.get_shigan(shigan_name)
                        item["classification"] = entity.get("classification", "")
                        item["description"] = entity.get("description", "")
                    except Exception:
                        pass
                results.append(item)
            except Exception as e:
                results.append({"gan": g, "error": str(e)})

        return {
            "day_master": day_master,
            "day_master_info": f"{day_master}（日主）",
            "derivations": results,
            "total_derived": len(results),
        }

    def _tool_dizhi_analyze(self, arguments: Dict) -> Any:
        """地支分析工具"""
        try:
            from tengod.divination_engine import DizhiEngine
        except Exception as e:
            return {"error": f"Engine unavailable: {e}"}

        branches_str = str(arguments.get("branches", "")).strip()
        analysis_type = str(arguments.get("analysis_type", "all"))

        valid_branches = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

        # 解析输入（支持逗号分隔、中文顿号分隔、或直接单字列表）
        # 规则：先按分隔符切分；如果切分后的某一项是多字且所有字都是有效地支，则再拆成单字
        if "," in branches_str or "、" in branches_str:
            import re
            parts = [p.strip() for p in re.split(r'[,，]', branches_str) if p.strip()]
        else:
            parts = [branches_str] if branches_str else []

        branches = []
        for part in parts:
            if not part:
                continue
            # 单个字的项
            if len(part) == 1:
                if part in valid_branches:
                    branches.append(part)
                continue
            # 多字的项：全是有效地支字就拆成单字；否则尝试每个字
            all_valid = all(c in valid_branches for c in part)
            if all_valid:
                branches.extend(list(part))
            else:
                # 尝试：每2字是一个地支？
                for c in part:
                    if c in valid_branches:
                        branches.append(c)

        branches = [b for b in branches if b in valid_branches]
        if not branches:
            return {"error": f"未找到有效的地支（支持：{', '.join(valid_branches)}）"}

        # 藏干分析
        def _canggan(b):
            try:
                result = DizhiEngine.canggan(b)
                if isinstance(result, dict):
                    return {
                        "main": result.get("main", ""),
                        "mid": result.get("mid", ""),
                        "residual": result.get("residual", ""),
                        "list": result.get("list", []),
                    }
                return {"raw": str(result)}
            except Exception as e:
                return {"error": str(e)}

        if analysis_type == "canggan":
            return {
                "input_branches": branches,
                "analysis_type": "藏干",
                "results": {b: _canggan(b) for b in branches},
            }

        # 六合、三合、三会、六冲、六害、六破、相刑
        def _find_pair(branches: list, engine_method: str, pairs_map: list) -> list:
            """通用查找地支关系"""
            found = []
            visited = set()
            for i, b1 in enumerate(branches):
                for j, b2 in enumerate(branches):
                    if i >= j: continue
                    key = tuple(sorted([b1, b2]))
                    if key in visited: continue
                    for pair in pairs_map:
                        if set(pair) == {b1, b2}:
                            try:
                                method = getattr(DizhiEngine, engine_method, None)
                                if method:
                                    r = method(b1)
                                    result = {"pair": "+".join(pair), "detail": str(r)}
                                else:
                                    result = {"pair": "+".join(pair)}
                                found.append(result)
                                visited.add(key)
                            except Exception:
                                found.append({"pair": "+".join(pair)})
                                visited.add(key)
                            break
            return found

        def _find_triple(branches: list, triples_map: list) -> list:
            """查找三合/三会关系"""
            found = []
            for tri in triples_map:
                if set(tri).issubset(set(branches)):
                    found.append({"triple": "+".join(tri), "note": "成立"})
            return found

        # 六合定义
        liuhe_pairs = [("子", "丑"), ("寅", "亥"), ("卯", "戌"), ("辰", "酉"), ("巳", "申"), ("午", "未")]
        # 三合
        sanhe_triples = [("申", "子", "辰"), ("亥", "卯", "未"), ("寅", "午", "戌"), ("巳", "酉", "丑")]
        # 三会
        sanhui_triples = [("寅", "卯", "辰"), ("巳", "午", "未"), ("申", "酉", "戌"), ("亥", "子", "丑")]
        # 六冲
        liuchong_pairs = [("子", "午"), ("丑", "未"), ("寅", "申"), ("卯", "酉"), ("辰", "戌"), ("巳", "亥")]
        # 六害
        liuhai_pairs = [("子", "未"), ("丑", "午"), ("寅", "巳"), ("卯", "辰"), ("申", "亥"), ("酉", "戌")]
        # 六破（简化）
        liupo_pairs = [("子", "酉"), ("午", "亥"), ("寅", "午"), ("卯", "子"), ("巳", "申"), ("未", "戌")]
        # 相刑（简化）
        xing_pairs = [("子", "卯"), ("寅", "巳"), ("巳", "申"), ("丑", "戌"), ("戌", "未")]

        result = {
            "input_branches": branches,
            "analysis_type": analysis_type,
        }

        if analysis_type in ("liuhe", "all"):
            result["liuhe_六合"] = _find_pair(branches, "liuhe", liuhe_pairs)
        if analysis_type in ("sanhe", "all"):
            result["sanhe_三合"] = _find_triple(branches, sanhe_triples)
        if analysis_type in ("sanhui", "all"):
            result["sanhui_三会"] = _find_triple(branches, sanhui_triples)
        if analysis_type in ("liuchong", "all"):
            result["liuchong_六冲"] = _find_pair(branches, "liuchong", liuchong_pairs)
        if analysis_type in ("liuhai", "all"):
            result["liuhai_六害"] = _find_pair(branches, "liuhai", liuhai_pairs)
        if analysis_type in ("liupo", "all"):
            result["liupo_六破"] = _find_pair(branches, "liupo", liupo_pairs)
        if analysis_type in ("xiangxing", "all"):
            result["xiangxing_相刑"] = _find_pair(branches, "xiangxing", xing_pairs)
        if analysis_type in ("canggan", "all"):
            result["canggan_藏干"] = {b: _canggan(b) for b in branches}

        # 汇总说明
        total_relations = sum(
            len(v) for k, v in result.items()
            if isinstance(v, list) and k != "input_branches"
        )
        result["summary"] = f"在 {len(branches)} 个地支中发现 {total_relations} 个关系"
        return result

    def _tool_bazi_calc(self, arguments: Dict) -> Any:
        """八字排盘工具"""
        try:
            from tengod.bazi_calculator import BaziChart
            from tengod.bazi_analyzer import BaziAnalyzer
            from tengod.dayun_liunian import DayunLiunian, derive_shigan, GAN_WUXING, GAN_YINYANG
        except Exception as e:
            return {"error": f"Calculation engine unavailable: {e}"}

        try:
            year = int(arguments.get("year"))
            month = int(arguments.get("month"))
            day = int(arguments.get("day"))
            hour = int(arguments.get("hour", 12))
            minute = int(arguments.get("minute", 0))
            gender = str(arguments.get("gender", "male"))
            lon = float(arguments.get("longitude", 116.4))
            lat = float(arguments.get("latitude", 39.9))
            output_level = str(arguments.get("output_level", "standard"))
        except (ValueError, TypeError) as e:
            return {"error": f"参数解析失败: {e}"}

        is_male = gender == "male"

        # 基础四柱
        chart = BaziChart(year, month, day, hour, minute, lon, lat)
        pillars = chart.pillars
        day_master = pillars["day"][0]

        result = {
            "input": {
                "solar": f"{year}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}",
                "longitude": lon,
                "latitude": lat,
                "gender": "男" if is_male else "女",
                "true_solar_time": f"{chart.true_hour:02d}:{chart.true_minute:02d}",
            },
            "pillars": {
                "year": pillars["year"],
                "month": pillars["month"],
                "day": pillars["day"],
                "hour": pillars["hour"],
            },
            "day_master": f"{day_master}（{GAN_YINYANG.get(day_master, '')}{GAN_WUXING.get(day_master, '')}）",
        }

        if output_level == "pillars_only":
            return result

        # 十神分布（四柱天干）
        shigan_map = {}
        for key, pillar in pillars.items():
            gan = pillar[0]
            if key == "day":
                shigan_map[key] = f"{gan}（日主）"
            else:
                try:
                    sh = derive_shigan(day_master, gan)
                    shigan_map[key] = f"{gan}（{sh}）"
                except Exception:
                    shigan_map[key] = gan

        # 大运（内联计算，阳男阴女顺排，阴男阳女逆排）
        dayuns = []
        try:
            # 简化版大运：以月柱为基准，每10年推进1个甲子
            # 真正的起运年龄需要节气精确计算，这里简化为0岁起运
            from tengod.bazi_calculator import BAZI_GAN, BAZI_ZHI  # 使用简写
        except Exception:
            pass
        try:
            # 使用本地天干地支列表
            tiangan = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
            dizhi = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
            y_gan = pillars["year"][0]
            y_yinyang = (tiangan.index(y_gan) % 2 == 0)  # 阳干索引偶数: 甲丙戊庚壬=0,2,4,6,8
            forward = (is_male and y_yinyang) or (not is_male and not y_yinyang)
            m_gan_idx = tiangan.index(pillars["month"][0])
            m_zhi_idx = dizhi.index(pillars["month"][1])
            for i in range(1, 11):
                if forward:
                    gi = (m_gan_idx + i) % 10
                    zi = (m_zhi_idx + i) % 12
                else:
                    gi = (m_gan_idx - i) % 10
                    zi = (m_zhi_idx - i) % 12
                pillar = tiangan[gi] + dizhi[zi]
                sh = derive_shigan(day_master, pillar[0])
                dayuns.append({
                    "age": f"{(i-1)*10}-{(i-1)*10+9}岁",
                    "start_year": year + (i-1)*10,
                    "pillar": pillar,
                    "shigan": sh,
                    "direction": "顺" if forward else "逆",
                })
        except Exception as e:
            dayuns = [{"note": f"大运计算异常: {e}"}]

        result.update({
            "shigan_map": shigan_map,
            "dayuns": dayuns,
        })

        # full 级别：加入综合分析
        if output_level == "full":
            try:
                analyzer = BaziAnalyzer(year, month, day, hour, minute, is_male, lon, lat)
                analysis = analyzer.analysis
                result.update({
                    "wuxing_distribution": analysis.get("wuxing", {}),
                    "wuxing_score": analysis.get("wuxing_score", {}),
                    "shigan_distribution": analysis.get("shigan_count", {}),
                    "branch_relations": analysis.get("branch_relations", {}),
                    "conclusion": analysis.get("conclusion", ""),
                })
            except Exception as e:
                result["analysis_error"] = str(e)

            # 近期流年
            try:
                liunians = []
                for i in range(-3, 11):
                    y = year + i
                    liunian_pillar = BaziChart(y, 6, 15, 12, 0, lon, lat).pillars["year"]
                    sh = derive_shigan(day_master, liunian_pillar[0])
                    liunians.append({"year": y, "pillar": liunian_pillar, "shigan": sh})
                result["liunians"] = liunians
            except Exception as e:
                result["liunian_error"] = str(e)

        return result

    # ============ 阶段二工具方法结束 ============

    # ============ 阶段四：神煞 + 格局 + 喜用神 ============

    def _tool_shensha_calc(self, arguments: Dict) -> Any:
        """神煞推算工具"""
        try:
            from tengod.shensha_engine import calc_all_shensha
        except Exception as e:
            return {"error": f"shensha_engine unavailable: {e}"}

        pillars = arguments.get("pillars", {})
        detail_level = arguments.get("detail_level", "basic")

        # 验证四柱
        required_keys = ["year", "month", "day", "hour"]
        for k in required_keys:
            if k not in pillars or not pillars[k]:
                return {"error": f"缺少必要字段: {k}"}
        if len(pillars.get("year", "")) < 2:
            return {"error": f"年柱格式错误: {pillars.get('year', '')}"}

        try:
            result = calc_all_shensha(pillars)
            if detail_level == "full":
                return result.json_report()
            return {
                "pillars": pillars,
                "day_master": pillars["day"][0],
                "total_shensha": len(result.all_shensha),
                "summary": result.summary,
                "year_shens": {k: v["name"] for k, v in result.year_shens.items()},
                "month_shens": {k: v["name"] for k, v in result.month_shens.items()},
                "day_shens": {k: v["name"] for k, v in result.day_shens.items()},
                "hour_shens": {k: v["name"] for k, v in result.hour_shens.items()},
                "top_jixiong": result.summary.get("top_jixiong", []),
            }
        except Exception as e:
            return {"error": f"神煞计算异常: {e}"}

    def _tool_geju_judge(self, arguments: Dict) -> Any:
        """格局判断工具"""
        try:
            from tengod.geju_engine import GejuEngine
        except Exception as e:
            return {"error": f"geju_engine unavailable: {e}"}

        pillars = arguments.get("pillars", {})
        detail_level = arguments.get("detail_level", "basic")

        for k in ["year", "month", "day", "hour"]:
            if k not in pillars:
                return {"error": f"缺少必要字段: {k}"}

        try:
            engine = GejuEngine()
            result = engine.judge(pillars, detail=detail_level)
            return result
        except Exception as e:
            return {"error": f"格局判断异常: {e}"}

    def _tool_yongshen(self, arguments: Dict) -> Any:
        """喜用神分析工具"""
        try:
            from tengod.geju_engine import YongshenEngine
            from tengod.geju_engine import analyze_bazi_comprehensive
        except Exception as e:
            return {"error": f"geju_engine unavailable: {e}"}

        pillars = arguments.get("pillars", {})
        detail_level = arguments.get("detail_level", "basic")

        for k in ["year", "month", "day", "hour"]:
            if k not in pillars:
                return {"error": f"缺少必要字段: {k}"}

        try:
            engine = YongshenEngine()
            result = engine.analyze(pillars, detail=detail_level)
            return result
        except Exception as e:
            return {"error": f"喜用神分析异常: {e}"}

    # ============ 阶段四工具方法结束 ============

    # ============ 阶段五：向量检索工具方法 ============

    def _tool_semantic_search(self, arguments: Dict) -> Any:
        """语义搜索工具"""
        try:
            from tengod.vector_store import get_vector_store
        except Exception as e:
            return {"error": f"vector_store unavailable: {e}"}

        query = arguments.get("query", "").strip()
        if not query:
            return {"error": "query 参数不能为空"}

        top_k = int(arguments.get("top_k", 10))
        type_filter = arguments.get("type_filter", None)

        try:
            store = get_vector_store()
            result = store.search_json(query, top_k=top_k, type_filter=type_filter)
            return result
        except Exception as e:
            return {"error": f"语义搜索异常: {e}"}

    def _tool_knowledge_recommend(self, arguments: Dict) -> Any:
        """知识关联推荐工具"""
        try:
            from tengod.vector_store import get_vector_store
        except Exception as e:
            return {"error": f"vector_store unavailable: {e}"}

        node_name = arguments.get("node_name", "").strip()
        if not node_name:
            return {"error": "node_name 参数不能为空"}

        top_k = int(arguments.get("top_k", 5))

        try:
            store = get_vector_store()
            recs = store.recommend_related(node_name, top_k=top_k)
            return {
                "node_name": node_name,
                "total_indexed": store._stats["total_nodes"],
                "recommendations": recs,
            }
        except Exception as e:
            return {"error": f"知识关联推荐异常: {e}"}

    # ============ 阶段五工具方法结束 ============

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
    import sys
    # --test 模式: 本地运行所有玄学工具，验证它们是否正常
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        print("=" * 60)
        print("MCP Server v2.2.0 - 本地自检模式 (test)")
        print("=" * 60)
        server = MCPServer()

        # 列出所有已注册工具
        tools = list(server._tools.keys())
        print(f"\n已注册工具: {len(tools)} 个")
        for t in tools:
            print(f"  - {t}")

        # 运行阶段二工具的基本测试
        test_cases = [
            ("tengod_wuxing_query", {"element": "木", "relation_mode": "info"}),
            ("tengod_wuxing_query", {"element": "木", "other_element": "火", "relation_mode": "shengke"}),
            ("tengod_wuxing_query", {"element": "木", "relation_mode": "cycle"}),
            ("tengod_bagua_query", {"trigram": "乾", "query_type": "info"}),
            ("tengod_shigan_derive", {"day_master": "甲", "gan": "乙,丙,丁,戊,己,庚,辛,壬,癸", "detail_level": "basic"}),
            ("tengod_dizhi_analyze", {"branches": "子,丑,寅,午", "analysis_type": "all"}),
            ("tengod_bazi_calc", {"year": 1990, "month": 6, "day": 15, "hour": 10, "minute": 30,
                                   "gender": "male", "output_level": "standard"}),
        ]

        print("\n[阶段二扩展工具测试]")
        passed = failed = 0
        for tool_name, args in test_cases:
            try:
                r = server._execute_tool(tool_name, args)
                has_error = isinstance(r, dict) and "error" in r
                status = "✅" if not has_error else "⚠️"
                print(f"  {status} {tool_name}({args})")
                # 打印结果摘要
                if isinstance(r, dict):
                    keys = list(r.keys())[:5]
                    print(f"       -> keys: {keys}")
                else:
                    print(f"       -> {str(r)[:60]}")
                if has_error:
                    failed += 1
                else:
                    passed += 1
            except Exception as e:
                print(f"  ❌ {tool_name}: {e}")
                failed += 1

        print(f"\n测试结果: {passed} 通过, {failed} 问题/警告")
        print("注: 部分 warning 级 (⚠️) 可能是正常的边界情况")

        # 阶段四工具测试
        stage4_cases = [
            ("tengod_shensha_calc", {
                "pillars": {"year": "庚午", "month": "壬午", "day": "辛亥", "hour": "癸巳"},
                "detail_level": "basic",
            }),
            ("tengod_geju_judge", {
                "pillars": {"year": "庚午", "month": "壬午", "day": "辛亥", "hour": "癸巳"},
                "detail_level": "basic",
            }),
            ("tengod_yongshen", {
                "pillars": {"year": "庚午", "month": "壬午", "day": "辛亥", "hour": "癸巳"},
                "detail_level": "basic",
            }),
            ("tengod_shensha_calc", {
                "pillars": {"year": "甲辰", "month": "丁卯", "day": "庚子", "hour": "丙子"},
                "detail_level": "full",
            }),
        ]
        print("\n[阶段四扩展工具测试]")
        passed4 = failed4 = 0
        for tool_name, args in stage4_cases:
            try:
                r = server._execute_tool(tool_name, args)
                has_error = isinstance(r, dict) and "error" in r
                status = "✅" if not has_error else "⚠️"
                print(f"  {status} {tool_name}")
                if isinstance(r, dict):
                    keys = list(r.keys())[:6]
                    print(f"       -> keys: {keys}")
                    if not has_error:
                        if tool_name == "tengod_shensha_calc":
                            print(f"       -> 神煞数: {r.get('total_shensha', 'N/A')}, 汇总: {r.get('summary', {})}")
                        elif tool_name == "tengod_geju_judge":
                            print(f"       -> 格局: {r.get('geju_name', 'N/A')}, 月干十神: {r.get('month_shishen', 'N/A')}")
                        elif tool_name == "tengod_yongshen":
                            print(f"       -> 旺衰: {r.get('wang_shuai', 'N/A')}, 喜神: {r.get('yong_shen', [])[:2]}")
                else:
                    print(f"       -> {str(r)[:80]}")
                if has_error:
                    failed4 += 1
                else:
                    passed4 += 1
            except Exception as e:
                print(f"  ❌ {tool_name}: {e}")
                failed4 += 1

        print(f"\n阶段四测试结果: {passed4} 通过, {failed4} 问题")

        # 阶段五工具测试
        stage5_cases = [
            ("tengod_semantic_search", {"query": "找所有属木的概念", "top_k": 3}),
            ("tengod_semantic_search", {"query": "方位东方", "type_filter": "天干", "top_k": 3}),
            ("tengod_knowledge_recommend", {"node_name": "木", "top_k": 5}),
            ("tengod_knowledge_recommend", {"node_name": "乾", "top_k": 3}),
        ]
        print("\n[阶段五扩展工具测试]")
        passed5 = failed5 = 0
        for tool_name, args in stage5_cases:
            try:
                r = server._execute_tool(tool_name, args)
                has_error = isinstance(r, dict) and "error" in r
                status = "✅" if not has_error else "⚠️"
                print(f"  {status} {tool_name}({args})")
                if isinstance(r, dict) and not has_error:
                    if tool_name == "tengod_semantic_search":
                        print(f"       -> 结果数: {r.get('result_count', 'N/A')}, 耗时: {r.get('search_time_ms', 'N/A')}ms")
                        for res in r.get("results", [])[:2]:
                            print(f"          [{res['type']}] {res['name']} (相似度:{res['similarity']})")
                    elif tool_name == "tengod_knowledge_recommend":
                        recs = r.get("recommendations", [])
                        print(f"       -> 推荐数: {len(recs)}")
                        for rec in recs[:2]:
                            print(f"          [{rec['type']}] {rec['name']} → {rec['relation']}")
                if has_error:
                    failed5 += 1
                else:
                    passed5 += 1
            except Exception as e:
                print(f"  ❌ {tool_name}: {e}")
                failed5 += 1

        print(f"\n阶段五测试结果: {passed5} 通过, {failed5} 问题")

        # 尝试完整的 JSON-RPC 测试
        print("\n[JSON-RPC 协议测试]")
        try:
            req = {"jsonrpc": "2.0", "method": "tools/list", "id": 1}
            resp = server._handle_request(req)
            tool_count = len(resp.get("result", {}).get("tools", [])) if "result" in resp else 0
            print(f"  ✅ tools/list -> {tool_count} 个工具")

            req2 = {"jsonrpc": "2.0", "method": "tools/call",
                    "params": {"name": "tengod_shigan_derive",
                               "arguments": {"day_master": "辛", "gan": "乙"}}, "id": 2}
            resp2 = server._handle_request(req2)
            r2 = resp2.get("result", {})
            if isinstance(r2, dict) and not r2.get("error"):
                print(f"  ✅ tools/call(tengod_shigan_derive) -> OK")
            else:
                print(f"  ⚠️ tools/call(tengod_shigan_derive) -> {r2}")
        except Exception as e:
            print(f"  ❌ JSON-RPC 协议异常: {e}")

        print("\n" + "=" * 60)
        print("MCP Server 自检完成。运行 'python -m tengod.mcp_server' 启动 stdio 模式。")
        print("=" * 60)
        return

    # 默认模式: stdio
    server = MCPServer()
    server.run()


if __name__ == "__main__":
    main()