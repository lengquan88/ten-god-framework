"""
gate_cognitive_api.py — 门禁认知引擎 REST API v4.6.0
=========================================================
正官主理法度，对外暴露门禁认知引擎 REST 接口。

支持：
  - POST /v1/cognitive/process → 处理用户查询（三链合一：意图消解+门禁预过滤+检索+生成）
  - POST /v1/cognitive/embedding → 获取文本嵌入
  - GET  /v1/cognitive/status → 获取引擎状态
  - GET  /v1/cognitive/health → 健康检查

对接现有架构：
  - JWTAuth (复用 api_server.py)
  - 依赖: gate_torch, open_source_bridge, local_embedding
  - 路由: 与正官_法度调度/api_router 对齐
"""

import os
import sys
import json
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

# 路径处理
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_TENGOD_ROOT = os.path.dirname(_THIS_DIR)
if _TENGOD_ROOT not in sys.path:
    sys.path.insert(0, _TENGOD_ROOT)
if os.path.dirname(_TENGOD_ROOT) not in sys.path:
    sys.path.insert(0, os.path.dirname(_TENGOD_ROOT))

# 复用 api_server.py 的 JWT 认证
from .正官_法度调度.api_server import JWTAuth

# 导入门禁认知核心
from .open_source_bridge import GateCognitiveEngine, ThreeFSClient
from .local_embedding import LocalEmbedder, create_embedder

# FastAPI 检测（降级模式）
_HAS_FASTAPI = False
app = None

try:
    from fastapi import FastAPI, HTTPException, Depends, Query
    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
    from pydantic import BaseModel
    _HAS_FASTAPI = True
except ImportError:
    pass

# ============================================================================
# Pydantic 模型（FastAPI 模式）
# ============================================================================

if _HAS_FASTAPI:

    class ProcessRequest(BaseModel):
        """处理请求"""
        query: str
        history: Optional[List[str]] = None
        system_load: float = 0.5
        session_id: Optional[str] = None

    class EmbeddingRequest(BaseModel):
        """嵌入请求"""
        text: str
        text_list: Optional[List[str]] = None

    class CognitiveStatus(BaseModel):
        """引擎状态"""
        version: str = "4.1.0"
        torch_available: bool
        sentence_transformer_available: bool
        embedding_mode: str
        active_sessions: int
        storage_stats: Dict[str, Any]

    class ProcessResponse(BaseModel):
        """处理响应"""
        session_id: str
        action: str  # clarify | reject | pending | generate
        message: Optional[str] = None
        candidates: Optional[List[Dict[str, Any]]] = None
        intent: Optional[Dict[str, Any]] = None
        gate_details: Optional[Dict[str, Any]] = None
        retrieved_count: int = 0
        retrieved: Optional[List[Tuple[str, float]]] = None
        tau: Optional[int] = None
        causal_acceptance: Optional[float] = None
        prompt: Optional[str] = None
        session_stats: Optional[Dict[str, Any]] = None

    class EmbeddingResponse(BaseModel):
        """嵌入响应"""
        embedding: Optional[List[float]] = None
        embeddings: Optional[List[List[float]]] = None
        dim: int
        mode: str

    class HealthResponse(BaseModel):
        """健康检查"""
        status: str = "ok"
        timestamp: int

# ============================================================================
# 引擎实例
# ============================================================================

_engine: Optional[GateCognitiveEngine] = None


def get_engine() -> GateCognitiveEngine:
    """获取单例引擎实例"""
    global _engine
    if _engine is None:
        embed_dim = int(os.environ.get("COGNITIVE_EMBED_DIM", "384"))
        fs_endpoint = os.environ.get("THREEFS_ENDPOINT", "http://3fs-cluster:8080")
        deepseek_api_key = os.environ.get("DEEPSEEK_API_KEY", "")
        _engine = GateCognitiveEngine(
            embed_dim=embed_dim,
            fs_endpoint=fs_endpoint,
            deepseek_api_key=deepseek_api_key,
        )
    return _engine


# ============================================================================
# FastAPI 应用构建
# ============================================================================

if _HAS_FASTAPI:

    app = FastAPI(
        title="门禁认知引擎 API",
        description="三链合一：意图消解 + 门禁预过滤 + 测地线检索 + 坐忘澄清",
        version="3.2.0",
    )

    security = HTTPBearer()
    jwt_auth = JWTAuth()

    @app.get("/v1/cognitive/health", response_model=HealthResponse, tags=["健康检查"])
    async def health():
        """健康检查"""
        return HealthResponse(
            status="ok",
            timestamp=int(time.time()),
        )

    @app.get("/v1/cognitive/status", response_model=CognitiveStatus, tags=["状态"])
    async def status(credentials: HTTPAuthorizationCredentials = Depends(security)):
        """获取引擎状态"""
        # 验证 token
        try:
            token = credentials.credentials
            jwt_auth.decode(token)
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid token")

        engine = get_engine()
        stats = engine.get_stats()
        return CognitiveStatus(
            version="4.6.0",
            torch_available=stats["torch_available"],
            sentence_transformer_available=stats["threefs_available"],
            embedding_mode=engine._embedder.get_mode(),
            active_sessions=len(engine._sessions),
            storage_stats=stats["storage_stats"],
        )

    @app.post("/v1/cognitive/process", response_model=ProcessResponse, tags=["认知处理"])
    async def process(
        request: ProcessRequest,
        credentials: HTTPAuthorizationCredentials = Depends(security),
    ):
        """认知处理入口

        三链合一完整管道：
          1. 多轮意图消解（坐忘门禁 + 歧义判断）
          2. 三道门禁预过滤（权限 + 资源 + 因果）
          3. 六维投影 + 测地线检索
          4. DeepSeek R1 因果验证
          5. 结构化 Prompt 生成
        """
        # 验证 token
        try:
            token = credentials.credentials
            jwt_auth.decode(token)
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid token")

        engine = get_engine()

        # 请求计数（v4.9.0）
        import time as _time
        t_start = _time.time()

        result = engine.process(
            query=request.query,
            history=request.history or [],
            system_load=request.system_load,
            session_id=request.session_id,
        )

        # 更新指标
        _request_count += 1
        _total_latency_ms += (_time.time() - t_start) * 1000

        return ProcessResponse(**result)

    @app.post("/v1/cognitive/embedding", response_model=EmbeddingResponse, tags=["嵌入"])
    async def embedding(
        request: EmbeddingRequest,
        credentials: HTTPAuthorizationCredentials = Depends(security),
    ):
        """获取文本语义嵌入

        单文本或批量，返回 384 维归一化向量。
        """
        # 验证 token
        try:
            token = credentials.credentials
            jwt_auth.decode(token)
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid token")

        engine = get_engine()
        embedder = engine._embedder

        if request.text_list is not None:
            # 批量
            emb_batch = embedder.encode_batch(request.text_list)
            return EmbeddingResponse(
                embeddings=[emb.tolist() for emb in emb_batch],
                dim=embedder.get_dim(),
                mode=embedder.get_mode(),
            )
        else:
            # 单文本
            emb = embedder.encode(request.text)
            return EmbeddingResponse(
                embedding=emb.tolist(),
                dim=embedder.get_dim(),
                mode=embedder.get_mode(),
            )

    @app.get("/v1/cognitive/gate_coefficients", tags=["门禁"])
    async def gate_coefficients(
        entity: str = Query(..., description="意图实体名称（如 八字/紫微/六爻/风水/姓名学）"),
        credentials: HTTPAuthorizationCredentials = Depends(security),
    ):
        """获取知识图谱门禁系数（v4.3.0）

        查询指定实体对应的五行→九宫格→门禁系数映射。
        """
        try:
            token = credentials.credentials
            jwt_auth.decode(token)
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid token")

        engine = get_engine()
        kg = engine.kg_bridge

        if not kg:
            return {"error": "KG bridge not initialized", "entity": entity}

        coefficients = kg.get_gate_coefficients(entity)
        if not coefficients:
            return {"error": "Entity not found", "entity": entity}

        return {
            "entity": entity,
            "coefficients": coefficients,
            "gate_coefficient": coefficients.get("gate_coefficient", 0.0),
            "element": coefficients.get("element", ""),
            "palace": coefficients.get("palace", ""),
            "gate_mod": coefficients.get("gate_mod", []),
        }

# ── Prometheus 指标（v4.5.0）─────────────────────────────────────────

    # 请求计数器
    import time as _time
    _request_count = 0
    _error_count = 0
    _total_latency_ms = 0.0
    _start_time = _time.time()

    @app.get("/metrics")
    async def metrics():
        """Prometheus 指标端点（v4.5.0）"""
        uptime = _time.time() - _start_time
        lines = [
            "# HELP tengod_cognitive_requests_total Total cognitive requests",
            "# TYPE tengod_cognitive_requests_total counter",
            f"tengod_cognitive_requests_total {_request_count}",
            "# HELP tengod_cognitive_errors_total Total cognitive errors",
            "# TYPE tengod_cognitive_errors_total counter",
            f"tengod_cognitive_errors_total {_error_count}",
            "# HELP tengod_cognitive_latency_ms_avg Average latency ms",
            "# TYPE tengod_cognitive_latency_ms_avg gauge",
            f"tengod_cognitive_latency_ms_avg {_total_latency_ms / max(_request_count, 1):.3f}",
            "# HELP tengod_cognitive_uptime_seconds Engine uptime",
            "# TYPE tengod_cognitive_uptime_seconds gauge",
            f"tengod_cognitive_uptime_seconds {uptime:.1f}",
            "# HELP tengod_cognitive_active_sessions Active sessions",
            "# TYPE tengod_cognitive_active_sessions gauge",
            f"tengod_cognitive_active_sessions {len(get_engine()._sessions)}",
        ]
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse("\n".join(lines) + "\n")

    # 请求计数中间件（注入到 process 端点）
    _original_process = None

    # ── 降级模式 ──────────────────────────────────────────────────────

# ============================================================================
# 降级模式：直接打印路由说明
# ============================================================================

else:
    print("=" * 60)
    print("  门禁认知引擎 API")
    print("  降级模式：FastAPI / Uvicorn 未安装")
    print("=" * 60)
    print()
    print("请安装依赖启用完整功能：")
    print("  pip install fastapi uvicorn python-multipart")
    print()
    print("API 端点：")
    print("  GET  /v1/cognitive/health")
    print("  GET  /v1/cognitive/status  (需 JWT)")
    print("  POST /v1/cognitive/process  (需 JWT)")
    print("  POST /v1/cognitive/embedding  (需 JWT)")
    print()


# ============================================================================
# 启动入口
# ============================================================================

if __name__ == "__main__" and _HAS_FASTAPI:
    import uvicorn
    port = int(os.environ.get("PORT", "8001"))
    host = os.environ.get("HOST", "0.0.0.0")
    print(f"Starting Gate Cognitive API on {host}:{port}")
    uvicorn.run(app, host=host, port=port)