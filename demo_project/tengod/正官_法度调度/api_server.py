#!/usr/bin/env python3
"""
api_server.py — 十神架构 HTTP API 服务
正官主理法度，对外暴露 RESTful 接口，对内调度十神模块。

支持两种运行模式：
  1. FastAPI + Uvicorn（生产模式，需 pip install fastapi uvicorn）
  2. 内置简易 WSGI（降级模式，零依赖，兼容所有环境）

用法：
    # 方式 A：uvicorn 启动
    python -m uvicorn tengod.正官_法度调度.api_server:app --host 0.0.0.0 --port 8000 --reload

    # 方式 B：直接脚本启动（自动检测 FastAPI 是否可用）
    python demo_project/tengod/正官_法度调度/api_server.py --port 8000

    # 方式 C：编程式启动
    from tengod.正官_法度调度.api_server import create_app, run_server
    app = create_app(core=my_core)
    run_server(app, host="0.0.0.0", port=8000)
"""

import json
import sys
import os
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict

# 处理路径，确保可在各种情况下导入兄弟模块
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_TENGOD_ROOT = os.path.dirname(_THIS_DIR)
if _TENGOD_ROOT not in sys.path:
    sys.path.insert(0, _TENGOD_ROOT)
if os.path.dirname(_TENGOD_ROOT) not in sys.path:
    sys.path.insert(0, os.path.dirname(_TENGOD_ROOT))


# -------- 数据结构 --------

@dataclass
class ApiResponse:
    """统一 API 响应格式"""
    code: int
    message: str
    data: Any = None

    def to_dict(self) -> Dict[str, Any]:
        return {"code": self.code, "message": self.message, "data": self.data}


# -------- FastAPI 模式检测 --------

_FASTAPI_AVAILABLE = False
_FASTAPI_ERROR = ""
app = None  # 供 uvicorn: APP_MODULE 使用

try:
    from fastapi import FastAPI, Body, HTTPException
    from fastapi.responses import JSONResponse, StreamingResponse
    from pydantic import BaseModel, Field
    _FASTAPI_AVAILABLE = True

    # Pydantic 请求模型（供 FastAPI 文档与校验使用）
    class _GenerateRequest(BaseModel):
        prompt: str = Field(..., description="提示词")
        format: str = Field("text", description="输出格式：text/markdown/json/html")
        provider: str = Field("mock", description="LLM 提供商：mock/openai/claude/local")
        model: str = Field("", description="模型名，如 gpt-3.5-turbo")
        temperature: float = 0.7
        stream: bool = False

    class _KnowledgeNodeRequest(BaseModel):
        name: str
        node_type: str = "default"
        properties: Dict[str, Any] = Field(default_factory=dict)

    class _SearchRequest(BaseModel):
        query: str
        top_k: int = 5
        node_type: Optional[str] = None

    class _TaskRequest(BaseModel):
        items: Dict[str, float]
        weights: Optional[Dict[str, float]] = None

except Exception as _e:
    _FASTAPI_AVAILABLE = False
    _FASTAPI_ERROR = str(_e)


def _build_generation_config(data: Dict[str, Any]):
    """根据字典构造 GenerationConfig（统一给 FastAPI / SimpleHttp 使用）"""
    from 食神_创生输出 import GenerationConfig, LLMProvider, OutputFormat
    fmt = data.get("format", "text")
    provider = data.get("provider", "mock")
    fmt_map = {"text": OutputFormat.TEXT, "markdown": OutputFormat.MARKDOWN,
               "json": OutputFormat.JSON, "html": OutputFormat.HTML, "code": OutputFormat.CODE}
    provider_map = {"mock": LLMProvider.MOCK, "openai": LLMProvider.OPENAI,
                    "claude": LLMProvider.CLAUDE, "local": LLMProvider.LOCAL}
    return GenerationConfig(
        format=fmt_map.get(fmt, OutputFormat.TEXT),
        provider=provider_map.get(provider, LLMProvider.MOCK),
        model=data.get("model", ""),
        temperature=float(data.get("temperature", 0.7)),
    )


def create_app(core: Optional[Any] = None) -> Any:
    """创建 HTTP 应用。FastAPI 可用时返回 FastAPI 实例，否则返回 None。

    在 FastAPI 不可用的情况下，run_server 会自动回退到内置 SimpleHttpServer。
    """
    if core is None:
        from tengod import get_core
        core = get_core()

    if not _FASTAPI_AVAILABLE:
        return None

    fast_app = FastAPI(
        title="十神架构 API",
        description="中华文明数字永生体 - 十神协同架构的 RESTful 接口",
        version="1.2.0",
    )

    # -------- 健康检查 --------

    @fast_app.get("/", tags=["系统"])
    def root():
        return ApiResponse(code=0, message="十神架构服务运行中", data={
            "version": "1.2.0",
            "modules": {
                "比肩": "已就绪" if core.registry else "未启用",
                "劫财": "已就绪" if core.guard else "未启用",
                "食神": "已就绪" if core.generator else "未启用",
                "伤官": "已就绪" if core.innovator else "未启用",
                "正财": "已就绪" if core.kb else "未启用",
                "偏财": "已就绪",
                "正官": "已就绪",
                "七杀": "已就绪" if core.judge else "未启用",
                "正印": "已就绪" if core.config else "未启用",
                "偏印": "已就绪" if core.bridge else "未启用",
                "元辰": "已就绪" if getattr(core, "locator", None) else "未启用",
                "太极": "已就绪" if getattr(core, "balancer", None) else "未启用",
            },
        }).to_dict()

    @fast_app.get("/health", tags=["系统"])
    def health():
        return {"status": "ok", "timestamp": __import__("time").time()}

    @fast_app.get("/api/status", tags=["系统"])
    def api_status():
        state = core.export_state()
        return ApiResponse(code=0, message="ok", data=state).to_dict()

    # -------- 食神 · 内容生成 --------

    @fast_app.post("/api/generate", tags=["食神 · 创生输出"])
    def api_generate(req: _GenerateRequest):
        """调用食神生成内容（非流式）"""
        if not core.generator:
            raise HTTPException(status_code=503, detail="食神模块未就绪")
        cfg = _build_generation_config(req.dict())
        text = core.generator.generate(req.prompt, cfg)
        return ApiResponse(code=0, message="ok", data={
            "content": text,
            "length": len(text),
            "format": cfg.format.value,
            "provider": cfg.provider.value,
        }).to_dict()

    @fast_app.post("/api/generate/stream", tags=["食神 · 创生输出"])
    def api_generate_stream(req: _GenerateRequest):
        """流式生成内容（SSE）"""
        if not core.generator:
            raise HTTPException(status_code=503, detail="食神模块未就绪")
        cfg = _build_generation_config(req.dict())

        def _gen():
            for chunk in core.generator.generate_stream(req.prompt, cfg):
                yield f"data: {json.dumps({'chunk': chunk}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(_gen(), media_type="text/event-stream")

    # -------- 正财 · 知识库 --------

    @fast_app.post("/api/knowledge/node", tags=["正财 · 知识固化"])
    def api_add_node(req: _KnowledgeNodeRequest):
        if not core.kb:
            raise HTTPException(status_code=503, detail="正财模块未就绪")
        node = core.kb.add_node(req.name, node_type=req.node_type, properties=req.properties)
        return ApiResponse(code=0, message="ok", data={
            "id": node.id, "name": node.name, "node_type": node.node_type
        }).to_dict()

    @fast_app.get("/api/knowledge/nodes", tags=["正财 · 知识固化"])
    def api_list_nodes(node_type: Optional[str] = None):
        if not core.kb:
            raise HTTPException(status_code=503, detail="正财模块未就绪")
        nodes = core.kb.find_by_type(node_type) if node_type else list(core.kb._nodes.values())
        return ApiResponse(code=0, message="ok", data={
            "total": len(nodes),
            "items": [
                {"id": n.id, "name": n.name, "node_type": n.node_type, "properties": n.properties}
                for n in nodes
            ],
        }).to_dict()

    @fast_app.post("/api/knowledge/search", tags=["正财 · 知识固化"])
    def api_search_knowledge(req: _SearchRequest):
        """向量相似度搜索"""
        if not core.kb:
            raise HTTPException(status_code=503, detail="正财模块未就绪")
        results = core.kb.query_nearest(req.query, top_k=req.top_k, node_type=req.node_type)
        return ApiResponse(code=0, message="ok", data={
            "query": req.query,
            "total": len(results),
            "items": [
                {"id": r["id"], "name": r["name"], "node_type": r["node_type"], "score": r["score"]}
                for r in results
            ],
        }).to_dict()

    @fast_app.get("/api/knowledge/stats", tags=["正财 · 知识固化"])
    def api_kb_stats():
        if not core.kb:
            raise HTTPException(status_code=503, detail="正财模块未就绪")
        return ApiResponse(code=0, message="ok", data=core.kb.stats()).to_dict()

    # -------- 七杀 · 品质裁决 --------

    @fast_app.post("/api/evaluate", tags=["七杀 · 品质裁决"])
    def api_evaluate(req: _TaskRequest):
        if not core.judge:
            raise HTTPException(status_code=503, detail="七杀模块未就绪")
        result = core.evaluate(req.items, weights=req.weights)
        return ApiResponse(code=0, message="ok", data=result).to_dict()

    # -------- 偏财 · 参数寻优 --------

    @fast_app.post("/api/optimize/search", tags=["偏财 · 奇招演化"])
    def api_optimize_search(
        space: Dict[str, List[Any]] = Body(..., example={"lr": [0.001, 0.01, 0.1], "batch": [16, 32, 64]}),
        trials: int = 20,
    ):
        """网格/随机参数搜索"""
        try:
            from 偏财_奇招演化 import SearchOptimizer, SearchSpace
            ss = SearchSpace(space)
            def default_obj(params):
                score = 0.0
                for k, vs in space.items():
                    mid_idx = len(vs) // 2
                    val = params.get(k, vs[0])
                    if val in vs:
                        score -= abs(vs.index(val) - mid_idx)
                return score
            opt = SearchOptimizer(ss, mode="grid")
            res = opt.optimize(default_obj, n_trials=trials, maximize=True)
            return ApiResponse(code=0, message="ok", data={
                "best_params": res.best_params,
                "best_score": res.best_score,
                "iterations": res.iterations,
                "duration": res.duration,
            }).to_dict()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    # -------- 伤官 · 创新思维 --------

    @fast_app.post("/api/innovate", tags=["伤官 · 破界创新"])
    def api_innovate(items: List[str] = Body(..., example=["AI", "知识图谱", "区块链"])):
        if not core.innovator:
            raise HTTPException(status_code=503, detail="伤官模块未就绪")
        core.innovator.combine(items)
        ideas = [
            {"title": i.title, "description": i.description, "feasibility": i.feasibility,
             "impact": i.impact, "score": round(i.score, 3)}
            for i in getattr(core.innovator, "_ideas", [])[-20:]
        ]
        return ApiResponse(code=0, message="ok", data={"total": len(ideas), "ideas": ideas}).to_dict()

    # -------- 元辰 · 项目定位 --------

    @fast_app.get("/api/locate", tags=["元辰 · 本源定位"])
    def api_locate():
        locator = getattr(core, "locator", None)
        if not locator:
            raise HTTPException(status_code=503, detail="元辰模块未就绪")
        locator.locate()
        return ApiResponse(code=0, message="ok", data=locator.summary()).to_dict()

    # -------- 太极 · 阴阳调和 --------

    @fast_app.get("/api/balance", tags=["太极 · 阴阳调和"])
    def api_balance():
        balancer = getattr(core, "balancer", None)
        if not balancer:
            raise HTTPException(status_code=503, detail="太极模块未就绪")
        return ApiResponse(code=0, message="ok", data=balancer.stats()).to_dict()

    @fast_app.post("/api/balance/{state}", tags=["太极 · 阴阳调和"])
    def api_set_balance(state: str):
        """设置状态：yin / yang / balanced"""
        balancer = getattr(core, "balancer", None)
        if not balancer:
            raise HTTPException(status_code=503, detail="太极模块未就绪")
        from 太极_阴阳调和 import YinYang as YY
        state_map = {"yin": YY.YIN, "yang": YY.YANG, "balanced": YY.BALANCED}
        if state not in state_map:
            raise HTTPException(status_code=400, detail="state must be yin/yang/balanced")
        balancer.set_state(state_map[state], reason="api request")
        return ApiResponse(code=0, message="ok", data=balancer.stats()).to_dict()

    return fast_app


# 默认 app（供 uvicorn 直接使用，FastAPI 不可用时为 None）
if _FASTAPI_AVAILABLE:
    try:
        from tengod import get_core
        app = create_app(get_core())
    except Exception:
        app = None


# -------- 降级：简易内置 HTTP Server（零依赖） --------

class SimpleHttpServer:
    """无 FastAPI 时的降级方案，基于 http.server"""

    def __init__(self, core: Any, host: str = "0.0.0.0", port: int = 8000):
        self.core = core
        self.host = host
        self.port = port

    def _dispatch(self, method: str, path: str, body: str) -> (int, Dict[str, Any]):
        """根据路径分发到对应处理逻辑"""
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            data = {}

        # 健康检查
        if path in ("/", "/health") and method == "GET":
            return 200, {"status": "ok", "version": "1.2.0", "mode": "simple-http"}

        # 状态总览
        if path == "/api/status" and method == "GET":
            return 200, ApiResponse(code=0, message="ok", data=self.core.export_state()).to_dict()

        # 食神生成
        if path == "/api/generate" and method == "POST":
            from 食神_创生输出 import GenerationConfig, LLMProvider, OutputFormat
            cfg = GenerationConfig(
                format=OutputFormat(data.get("format", "text")),
                provider=LLMProvider(data.get("provider", "mock")),
                model=data.get("model", ""),
                temperature=float(data.get("temperature", 0.7)),
            )
            text = self.core.generator.generate(data.get("prompt", ""), cfg)
            return 200, ApiResponse(code=0, message="ok", data={"content": text, "length": len(text)}).to_dict()

        # 正财搜索
        if path == "/api/knowledge/search" and method == "POST":
            results = self.core.kb.query_nearest(
                data.get("query", ""),
                top_k=int(data.get("top_k", 5)),
                node_type=data.get("node_type"),
            )
            items = [{"id": r["id"], "name": r["name"], "node_type": r["node_type"], "score": r["score"]} for r in results]
            return 200, ApiResponse(code=0, message="ok", data={"total": len(items), "items": items}).to_dict()

        # 正财添加节点
        if path == "/api/knowledge/node" and method == "POST":
            node = self.core.kb.add_node(
                data.get("name", ""),
                node_type=data.get("node_type", "default"),
                properties=data.get("properties", {}),
            )
            return 200, ApiResponse(code=0, message="ok", data={"id": node.id, "name": node.name}).to_dict()

        # 正财节点列表
        if path == "/api/knowledge/nodes" and method == "GET":
            all_nodes = list(self.core.kb._nodes.values())
            items = [{"id": n.id, "name": n.name, "node_type": n.node_type} for n in all_nodes]
            return 200, ApiResponse(code=0, message="ok", data={"total": len(items), "items": items}).to_dict()

        # 七杀评估
        if path == "/api/evaluate" and method == "POST":
            result = self.core.evaluate(data.get("items", {}), weights=data.get("weights"))
            return 200, ApiResponse(code=0, message="ok", data=result).to_dict()

        # 元辰
        if path == "/api/locate" and method == "GET":
            locator = getattr(self.core, "locator", None)
            if locator:
                locator.locate()
                return 200, ApiResponse(code=0, message="ok", data=locator.summary()).to_dict()
            return 503, {"code": 503, "message": "元辰模块未就绪"}

        # 太极
        if path == "/api/balance" and method == "GET":
            balancer = getattr(self.core, "balancer", None)
            if balancer:
                return 200, ApiResponse(code=0, message="ok", data=balancer.stats()).to_dict()
            return 503, {"code": 503, "message": "太极模块未就绪"}

        return 404, {"code": 404, "message": f"Route not found: {method} {path}"}

    def serve_forever(self) -> None:
        """启动内置 HTTP 服务器"""
        from http.server import BaseHTTPRequestHandler, HTTPServer
        server_self = self

        class Handler(BaseHTTPRequestHandler):
            def _send_json(self, status: int, payload: Dict[str, Any]) -> None:
                body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                status, payload = server_self._dispatch("GET", self.path, "")
                self._send_json(status, payload)

            def do_POST(self):
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length).decode("utf-8") if length else ""
                status, payload = server_self._dispatch("POST", self.path, body)
                self._send_json(status, payload)

            def log_message(self, fmt, *args):
                print(f"[十神-API] {self.log_date_time_string()} {args[0]}")

        httpd = HTTPServer((self.host, self.port), Handler)
        print(f"✅ 十神架构 HTTP API 服务已启动（内置简易模式）")
        print(f"   访问地址: http://{self.host}:{self.port}")
        print(f"   健康检查: http://{self.host}:{self.port}/health")
        print(f"   状态总览: http://{self.host}:{self.port}/api/status")
        print(f"\n   提示: pip install fastapi uvicorn 可升级为生产模式（SSE/文档/校验）")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n正在关闭服务...")
            httpd.server_close()


# -------- 统一入口：run_server --------

def run_server(app_or_core: Any = None, host: str = "0.0.0.0", port: int = 8000) -> None:
    """启动 HTTP 服务。

    - 若传入 FastAPI app 或 fastapi 可用：用 uvicorn 启动
    - 否则用内置简易 HTTP 服务
    """
    # 优先 FastAPI 模式
    if _FASTAPI_AVAILABLE:
        try:
            import uvicorn
            if app_or_core is None:
                from tengod import get_core
                app_to_run = create_app(get_core())
            elif hasattr(app_or_core, "openapi"):
                app_to_run = app_or_core
            else:
                app_to_run = create_app(app_or_core)
            uvicorn.run(app_to_run, host=host, port=port, log_level="info")
            return
        except ImportError:
            print("[提示] fastapi 已检测到但 uvicorn 未安装，切换至内置 HTTP 服务...")

    # 内置降级模式
    if app_or_core is None or not hasattr(app_or_core, "export_state"):
        from tengod import get_core
        core = get_core()
    else:
        core = app_or_core
    SimpleHttpServer(core, host=host, port=port).serve_forever()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="十神架构 HTTP API 服务")
    parser.add_argument("--host", default="0.0.0.0", help="绑定地址")
    parser.add_argument("--port", type=int, default=8000, help="监听端口")
    args = parser.parse_args()

    run_server(host=args.host, port=args.port)


__all__ = ["create_app", "run_server", "SimpleHttpServer", "ApiResponse", "app"]
__version__ = "1.2.0"
