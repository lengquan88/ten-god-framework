#!/usr/bin/env python3
"""
api_server.py — 十神架构 · REST API 服务 v1.0.0

FastAPI-based HTTP REST API，将全部六阶段能力服务化。

端点分组：
  /api/health          — 健康检查
  /api/stats           — 系统统计
  /api/bazi/calc       — 八字排盘
  /api/bazi/shensha    — 神煞推算
  /api/bazi/geju       — 格局判断
  /api/bazi/yongshen   — 喜用神分析
  /api/bazi/tiaohou    — 调候分析
  /api/bazi/full       — 综合八字分析（全部）
  /api/bazi/report     — 生成命理报告
  /api/knowledge/search   — 语义搜索
  /api/knowledge/recommend — 知识关联推荐
  /api/knowledge/wuxing/{element} — 五行查询
  /api/knowledge/bagua/{trigram}  — 八卦查询
  /api/knowledge/shigan           — 十神推演
  /api/knowledge/dizhi            — 地支分析

用法:
    python -m tengod.api_server                          # 启动 (默认 8000)
    python -m tengod.api_server --port 8080              # 指定端口
    python -m tengod.api_server --host 0.0.0.0 --port 80 # 公网
    python -m tengod.api_server --api-key my-secret      # 启用鉴权

API 文档:
    http://127.0.0.1:8000/docs     (Swagger UI)
    http://127.0.0.1:8000/redoc    (ReDoc)
"""

from __future__ import annotations

import json
import os
import sys
import time
import logging
import hashlib
import secrets
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Dict, List, Optional, Union

from fastapi import FastAPI, HTTPException, Request, Depends, Query, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel, Field, field_validator
import uvicorn

# ============================================================================
# 日志配置
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("tengod-api")

# ============================================================================
# 全局状态
# ============================================================================

_api_key: Optional[str] = None
_request_counts: Dict[str, List[float]] = defaultdict(list)
_server_started_at: str = datetime.now(timezone.utc).isoformat()
_total_requests: int = 0
_total_errors: int = 0

# ============================================================================
# 鉴权中间件
# ============================================================================

from starlette.middleware.base import BaseHTTPMiddleware

PUBLIC_PATHS = {"/api/health", "/api/stats", "/docs", "/redoc", "/openapi.json"}


class AuthMiddleware(BaseHTTPMiddleware):
    """API Key 鉴权中间件（从环境变量 TENGOD_API_KEY 读取）"""

    async def dispatch(self, request: Request, call_next):
        api_key = os.environ.get("TENGOD_API_KEY")
        if api_key and request.url.path not in PUBLIC_PATHS:
            if request.url.path.startswith("/api/"):
                x_api_key = request.headers.get("X-API-Key")
                if x_api_key is None:
                    return JSONResponse(
                        status_code=401,
                        content={"error": "Missing X-API-Key header", "status_code": 401,
                                 "timestamp": datetime.now(timezone.utc).isoformat()},
                    )
                if not secrets.compare_digest(x_api_key, api_key):
                    return JSONResponse(
                        status_code=403,
                        content={"error": "Invalid API key", "status_code": 403,
                                 "timestamp": datetime.now(timezone.utc).isoformat()},
                    )
        return await call_next(request)


# ============================================================================
# 请求日志 + 限流中间件
# ============================================================================

RATE_LIMITS: Dict[str, int] = {
    "/api/bazi/report": 15,
    "/api/bazi/full": 20,
    "/api/bazi/": 30,
    "/api/knowledge/": 60,
    "/api/health": 120,
    "/api/stats": 60,
}


async def rate_limit_middleware(request: Request, call_next):
    """简易滑动窗口限流中间件"""
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()

    # 确定限流阈值
    max_rpm = 60  # 默认
    for path_prefix, limit in RATE_LIMITS.items():
        if request.url.path.startswith(path_prefix):
            max_rpm = limit
            break

    window = [t for t in _request_counts[client_ip] if now - t < 60]
    if len(window) >= max_rpm:
        return JSONResponse(
            status_code=429,
            content={"error": f"Rate limit exceeded ({max_rpm} req/min)", "status_code": 429,
                     "timestamp": datetime.now(timezone.utc).isoformat()},
        )
    window.append(now)
    _request_counts[client_ip] = window

    return await call_next(request)

async def log_middleware(request: Request, call_next):
    """记录所有请求"""
    global _total_requests, _total_errors
    _total_requests += 1
    start = time.time()
    try:
        response = await call_next(request)
        elapsed = (time.time() - start) * 1000
        if response.status_code >= 400:
            _total_errors += 1
        logger.info(
            f"{request.method} {request.url.path} "
            f"→ {response.status_code} ({elapsed:.1f}ms)"
        )
        return response
    except Exception as e:
        _total_errors += 1
        elapsed = (time.time() - start) * 1000
        logger.error(f"{request.method} {request.url.path} → ERROR: {e} ({elapsed:.1f}ms)")
        raise


# ============================================================================
# Pydantic 模型
# ============================================================================

class BaziInput(BaseModel):
    """八字排盘输入"""
    year: int = Field(..., ge=1900, le=2100, description="出生年份")
    month: int = Field(..., ge=1, le=12, description="出生月份")
    day: int = Field(..., ge=1, le=31, description="出生日期")
    hour: int = Field(default=12, ge=0, le=23, description="出生小时 (0-23)")
    minute: int = Field(default=0, ge=0, le=59, description="出生分钟")
    gender: str = Field(default="male", description="性别: male/female")
    longitude: float = Field(default=116.4, description="出生地经度")
    latitude: float = Field(default=39.9, description="出生地纬度")

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, v: str) -> str:
        v = v.lower().strip()
        if v not in ("male", "female", "男", "女"):
            raise ValueError("gender must be 'male'/'female' or '男'/'女'")
        return "male" if v in ("male", "男") else "female"


class PillarsInput(BaseModel):
    """四柱输入（用于神煞/格局/喜用神）"""
    year: str = Field(..., min_length=2, max_length=2, description="年柱，如 '庚午'")
    month: str = Field(..., min_length=2, max_length=2, description="月柱")
    day: str = Field(..., min_length=2, max_length=2, description="日柱")
    hour: str = Field(..., min_length=2, max_length=2, description="时柱")

    def to_dict(self) -> Dict[str, str]:
        return {"year": self.year, "month": self.month, "day": self.day, "hour": self.hour}


class SearchQuery(BaseModel):
    """语义搜索查询"""
    query: str = Field(..., min_length=1, description="搜索关键词")
    top_k: int = Field(default=10, ge=1, le=50, description="返回结果数量")
    type_filter: Optional[str] = Field(default=None, description="类型过滤: 五行/八卦/天干/地支/十神")


class RecommendQuery(BaseModel):
    """知识关联推荐查询"""
    node_name: str = Field(..., min_length=1, description="节点名称")
    top_k: int = Field(default=5, ge=1, le=50, description="返回结果数量")


class ShiganQuery(BaseModel):
    """十神推演查询"""
    day_master: str = Field(..., min_length=1, max_length=1, description="日主天干, 如 '甲'")
    gan: str = Field(default="", description="目标天干, 逗号分隔, 如 '乙,丙,丁'")
    detail_level: str = Field(default="basic", description="basic/full")


class DizhiQuery(BaseModel):
    """地支分析查询"""
    branches: str = Field(..., min_length=1, description="地支字符串, 逗号分隔, 如 '子,丑,寅,午'")
    analysis_type: str = Field(default="all", description="分析类型: all/liuhe/sanhe/chong/hai/po/xing")

    @field_validator("branches")
    @classmethod
    def validate_branches(cls, v: str) -> str:
        valid = set("子丑寅卯辰巳午未申酉戌亥")
        parts = [p.strip() for p in v.replace(",", " ").split() if p.strip()]
        for p in parts:
            if p not in valid:
                raise ValueError(f"无效地支: '{p}'")
        return ",".join(parts)


class ReportQuery(BaseModel):
    """报告生成查询"""
    bazi: BaziInput = Field(..., description="八字输入")
    format: str = Field(default="text", description="输出格式: text/markdown/json/html")
    include_shensha: bool = Field(default=True)
    include_geju: bool = Field(default=True)
    include_yongshen: bool = Field(default=True)


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str = "ok"
    version: str
    uptime_seconds: float
    total_requests: int
    total_errors: int


class ErrorResponse(BaseModel):
    """错误响应"""
    error: str
    detail: Optional[str] = None
    timestamp: str


# ============================================================================
# 应用初始化
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期"""
    logger.info("十神 API Server 启动中...")
    # 预热向量存储
    try:
        from tengod.vector_store import get_vector_store
        store = get_vector_store()
        logger.info(f"向量存储已预热: {len(store._nodes)} 节点")
    except Exception as e:
        logger.warning(f"向量存储预热失败: {e}")
    logger.info("十神 API Server 已就绪")
    yield
    logger.info("十神 API Server 关闭")


app = FastAPI(
    title="十神架构 · API Server",
    description="""
## 中华文明数字永生体 · REST API

提供八字排盘、神煞推算、格局判断、喜用神分析、调候分析、
语义搜索、知识关联推荐等全部能力。

### 功能分组
- **/api/bazi/*** — 八字排盘与命理分析
- **/api/knowledge/*** — 知识查询与语义搜索
- **/api/health** — 服务健康检查

### 鉴权
通过 `X-API-Key` 请求头传递 API Key（若启动时启用了鉴权）。
""",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 鉴权
app.add_middleware(AuthMiddleware)
# 请求日志
app.middleware("http")(log_middleware)
# 限流
app.middleware("http")(rate_limit_middleware)


# ============================================================================
# 辅助函数
# ============================================================================

def _build_pillars(bazi: BaziInput) -> Dict[str, str]:
    """从 BaziInput 构建四柱"""
    from tengod.bazi_calculator import BaziChart
    chart = BaziChart(bazi.year, bazi.month, bazi.day,
                      bazi.hour, bazi.minute, bazi.longitude, bazi.latitude)
    return chart.pillars


def _bazi_to_analyzer(bazi: BaziInput):
    """从 BaziInput 创建 BaziAnalyzer"""
    from tengod.bazi_analyzer import BaziAnalyzer
    is_male = bazi.gender == "male"
    return BaziAnalyzer(bazi.year, bazi.month, bazi.day,
                        bazi.hour, bazi.minute, is_male=is_male,
                        longitude=bazi.longitude, latitude=bazi.latitude)


# ============================================================================
# 健康检查
# ============================================================================

@app.get("/api/health", response_model=HealthResponse, tags=["系统"])
async def health_check():
    """服务健康检查"""
    uptime = (datetime.now(timezone.utc) - datetime.fromisoformat(_server_started_at)).total_seconds()
    return {
        "status": "ok",
        "version": "1.0.0",
        "uptime_seconds": round(uptime, 1),
        "total_requests": _total_requests,
        "total_errors": _total_errors,
    }


@app.get("/api/stats", tags=["系统"])
async def system_stats():
    """系统统计信息"""
    from tengod.vector_store import get_vector_store
    try:
        store = get_vector_store()
        vs_stats = store._stats
    except Exception:
        vs_stats = {}

    return {
        "version": "1.0.0",
        "started_at": _server_started_at,
        "total_requests": _total_requests,
        "total_errors": _total_errors,
        "vector_store": {
            "total_nodes": vs_stats.get("total_nodes", 0),
            "total_vectors": vs_stats.get("total_vectors", 0),
            "search_count": vs_stats.get("search_count", 0),
        },
        "active_clients": len(_request_counts),
    }


# ============================================================================
# 八字排盘 API
# ============================================================================

@app.post("/api/bazi/calc", tags=["八字排盘"])
async def bazi_calc(bazi: BaziInput, request: Request):
    """八字排盘：计算四柱 + 大运 + 流年 + 十神 + 五行分析"""
    try:
        analyzer = _bazi_to_analyzer(bazi)
        a = analyzer.analysis
        chart = analyzer.chart

        return {
            "input": {
                "solar": f"{bazi.year}-{bazi.month:02d}-{bazi.day:02d} {bazi.hour:02d}:{bazi.minute:02d}",
                "gender": "男" if bazi.gender == "male" else "女",
                "longitude": bazi.longitude,
                "true_solar_time": f"{chart.true_hour:02d}:{chart.true_minute:02d}",
            },
            "pillars": a["pillars"],
            "day_master": a["day_master"],
            "day_master_info": a.get("day_master_info", ""),
            "shigan_map": a["shigan_map"],
            "shigan_count": a["shigan_count"],
            "wuxing": a["wuxing"],
            "wuxing_score": a["wuxing_score"],
            "branch_relations": a["branch_relations"],
            "dayuns": a["dayuns"][:5],
            "liunians": a["liunians"][:6],
            "conclusion": a["conclusion"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"八字排盘失败: {e}")


@app.post("/api/bazi/shensha", tags=["八字排盘"])
async def bazi_shensha(bazi: BaziInput, request: Request):
    """神煞推算：40+ 神煞分析"""
    try:
        from tengod.shensha_engine import calc_all_shensha
        pillars = _build_pillars(bazi)
        result = calc_all_shensha(pillars)
        return {
            "pillars": pillars,
            "day_master": pillars["day"][0],
            "total_shensha": len(result.all_shensha),
            "summary": result.summary,
            "year_shensha": {k: {"name": v["name"], "cat": v["cat"], "desc": v["desc"]}
                             for k, v in result.year_shens.items()},
            "month_shensha": {k: {"name": v["name"], "cat": v["cat"], "desc": v["desc"]}
                              for k, v in result.month_shens.items()},
            "day_shensha": {k: {"name": v["name"], "cat": v["cat"], "desc": v["desc"]}
                            for k, v in result.day_shens.items()},
            "hour_shensha": {k: {"name": v["name"], "cat": v["cat"], "desc": v["desc"]}
                             for k, v in result.hour_shens.items()},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"神煞推算失败: {e}")


@app.post("/api/bazi/geju", tags=["八字排盘"])
async def bazi_geju(bazi: BaziInput, request: Request):
    """格局判断"""
    try:
        from tengod.geju_engine import calc_geju
        pillars = _build_pillars(bazi)
        result = calc_geju(pillars)
        return {
            "pillars": pillars,
            "geju_name": result.geju_name,
            "geju_type": result.geju_type,
            "geju_desc": result.geju_desc,
            "score": result.score,
            "is_cong": result.is_cong,
            "is_huaqi": result.is_huaqi,
            "shiyongshen": result.shiyongshen,
            "jishen": result.jishen,
            "fujia_shens": result.fujia_shens,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"格局判断失败: {e}")


@app.post("/api/bazi/yongshen", tags=["八字排盘"])
async def bazi_yongshen(bazi: BaziInput, request: Request,
                        ):
    """喜用神分析"""
    try:
        from tengod.geju_engine import calc_yongshen
        pillars = _build_pillars(bazi)
        result = calc_yongshen(pillars)
        return {
            "pillars": pillars,
            "day_master": pillars["day"][0],
            "wang_shuai": result.wang_shuai,
            "wang_shuai_level": result.wang_shuai_level,
            "yong_shen": result.yong_shen,
            "ji_shen": result.ji_shen,
            "yongshen_desc": result.yongshen_desc,
            "wuxing_balance": result.wuxing_balance,
            "tiaohou_needed": result.tiaohou_needed,
            "tiaohou_shens": result.tiaohou_shens,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"喜用神分析失败: {e}")


@app.post("/api/bazi/tiaohou", tags=["八字排盘"])
async def bazi_tiaohou(bazi: BaziInput, request: Request,
                       ):
    """调候分析"""
    try:
        from tengod.geju_engine import calc_tiaohou
        pillars = _build_pillars(bazi)
        result = calc_tiaohou(pillars)
        return {
            "pillars": pillars,
            "required_tiaohou": result.required_tiaohou,
            "tiaohou_shens": result.tiaohou_shens,
            "season": result.season,
            "desc": result.desc,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"调候分析失败: {e}")


@app.post("/api/bazi/full", tags=["八字排盘"])
async def bazi_full(bazi: BaziInput, request: Request):
    """综合八字分析：排盘 + 神煞 + 格局 + 喜用神 + 调候（一次性返回全部）"""
    try:
        from tengod.bazi_analyzer import BaziAnalyzer
        from tengod.shensha_engine import calc_all_shensha
        from tengod.geju_engine import calc_geju, calc_yongshen, calc_tiaohou

        is_male = bazi.gender == "male"
        analyzer = BaziAnalyzer(bazi.year, bazi.month, bazi.day,
                                bazi.hour, bazi.minute, is_male=is_male,
                                longitude=bazi.longitude, latitude=bazi.latitude)
        a = analyzer.analysis
        chart = analyzer.chart
        pillars = a["pillars"]

        # 神煞
        shensha = calc_all_shensha(pillars)
        # 格局
        geju = calc_geju(pillars)
        # 喜用神
        yongshen = calc_yongshen(pillars)
        # 调候
        tiaohou = calc_tiaohou(pillars)

        return {
            "input": {
                "solar": f"{bazi.year}-{bazi.month:02d}-{bazi.day:02d} {bazi.hour:02d}:{bazi.minute:02d}",
                "gender": "男" if bazi.gender == "male" else "女",
                "longitude": bazi.longitude,
                "true_solar_time": f"{chart.true_hour:02d}:{chart.true_minute:02d}",
            },
            "bazi": {
                "pillars": pillars,
                "day_master": a["day_master"],
                "day_master_info": a.get("day_master_info", ""),
                "shigan_map": a["shigan_map"],
                "shigan_count": a["shigan_count"],
                "wuxing": a["wuxing"],
                "wuxing_score": a["wuxing_score"],
                "branch_relations": a["branch_relations"],
                "conclusion": a["conclusion"],
            },
            "shensha": {
                "total": len(shensha.all_shensha),
                "summary": shensha.summary,
                "detail": {k: {"name": v["name"], "cat": v["cat"], "pillar": v["pillar"], "desc": v["desc"]}
                           for k, v in shensha.all_shensha.items()},
            },
            "geju": {
                "name": geju.geju_name,
                "type": geju.geju_type,
                "desc": geju.geju_desc,
                "score": geju.score,
                "is_cong": geju.is_cong,
                "is_huaqi": geju.is_huaqi,
                "shiyongshen": geju.shiyongshen,
                "jishen": geju.jishen,
            },
            "yongshen": {
                "wang_shuai": yongshen.wang_shuai,
                "wang_shuai_level": yongshen.wang_shuai_level,
                "yong_shen": yongshen.yong_shen,
                "ji_shen": yongshen.ji_shen,
                "desc": yongshen.yongshen_desc,
                "wuxing_balance": yongshen.wuxing_balance,
            },
            "tiaohou": {
                "required": tiaohou.required_tiaohou,
                "tiaohou_shens": tiaohou.tiaohou_shens,
                "season": tiaohou.season,
                "desc": tiaohou.desc,
            },
            "dayun": a["dayuns"][:5],
            "liunian": a["liunians"][:6],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"综合八字分析失败: {e}")


@app.post("/api/bazi/report", tags=["八字排盘"])
async def bazi_report(query: ReportQuery, request: Request,
                      ):
    """生成命理报告（文本/Markdown/JSON/HTML）"""
    try:
        from tengod.bazi_analyzer import BaziAnalyzer
        from tengod.shensha_engine import calc_all_shensha
        from tengod.geju_engine import calc_geju, calc_yongshen, calc_tiaohou
        from tengod.report_generator import BaziReportGenerator

        is_male = query.bazi.gender == "male"
        analyzer = BaziAnalyzer(query.bazi.year, query.bazi.month, query.bazi.day,
                                query.bazi.hour, query.bazi.minute, is_male=is_male,
                                longitude=query.bazi.longitude, latitude=query.bazi.latitude)
        gen = BaziReportGenerator(analyzer)

        pillars = analyzer.analysis["pillars"]
        if query.include_shensha:
            gen.set_shensha(calc_all_shensha(pillars))
        if query.include_geju:
            gen.set_geju(calc_geju(pillars))
        if query.include_yongshen:
            gen.set_yongshen(calc_yongshen(pillars))
            gen.set_tiaohou(calc_tiaohou(pillars))

        fmt = query.format.lower()
        if fmt == "text":
            return {"format": "text", "report": gen.text_report()}
        elif fmt == "markdown":
            return {"format": "markdown", "report": gen.markdown_report()}
        elif fmt == "json":
            return {"format": "json", "report": gen.json_report()}
        elif fmt == "html":
            return HTMLResponse(content=gen.html_report())
        else:
            raise HTTPException(status_code=400, detail=f"不支持的格式: {fmt}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"报告生成失败: {e}")


# ============================================================================
# 知识查询 API
# ============================================================================

@app.post("/api/knowledge/search", tags=["知识查询"])
async def knowledge_search(query: SearchQuery, request: Request,
                           ):
    """语义搜索：基于 FAISS 向量的知识检索"""
    try:
        from tengod.vector_store import get_vector_store
        store = get_vector_store()
        result = store.search_json(query.query, top_k=query.top_k, type_filter=query.type_filter)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"语义搜索失败: {e}")


@app.post("/api/knowledge/recommend", tags=["知识查询"])
async def knowledge_recommend(query: RecommendQuery, request: Request,
                              ):
    """知识关联推荐：基于知识图谱的节点关联推荐"""
    try:
        from tengod.vector_store import get_vector_store
        store = get_vector_store()
        recs = store.recommend_related(query.node_name, top_k=query.top_k)
        return {
            "node_name": query.node_name,
            "total_indexed": store._stats["total_nodes"],
            "recommendations": recs,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"知识关联推荐失败: {e}")


@app.get("/api/knowledge/wuxing/{element}", tags=["知识查询"])
async def wuxing_query(element: str, relation_mode: str = Query("info", description="info/relations"),
                       ):
    """五行查询：生克/方位/脏腑/颜色"""
    try:
        from tengod.knowledge_graph import get_knowledge_graph
        kg = get_knowledge_graph()
        elem = kg.get_element(element)
        if elem is None:
            raise HTTPException(status_code=404, detail=f"未知五行: {element}")

        result = {"element": element, "info": elem}
        if relation_mode in ("relations", "all"):
            rels = kg.get_relations(element)
            result["relations"] = rels
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"五行查询失败: {e}")


@app.get("/api/knowledge/bagua/{trigram}", tags=["知识查询"])
async def bagua_query(trigram: str, query_type: str = Query("info", description="info/relations"),
                      ):
    """八卦查询：卦象信息/方位/五行属性"""
    try:
        from tengod.knowledge_graph import get_knowledge_graph
        kg = get_knowledge_graph()
        tri = kg.get_trigram(trigram)
        if tri is None:
            raise HTTPException(status_code=404, detail=f"未知八卦: {trigram}")

        result = {"trigram": trigram, "info": tri}
        if query_type in ("relations", "all"):
            rels = kg.get_relations(trigram)
            result["relations"] = rels
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"八卦查询失败: {e}")


@app.post("/api/knowledge/shigan", tags=["知识查询"])
async def shigan_derive(query: ShiganQuery, request: Request,
                        ):
    """十神推演：日主天干与目标天干的关系推演"""
    try:
        from tengod.divination_engine import ShiganEngine, TianganEngine
        dm = query.day_master
        gans = [g.strip() for g in query.gan.replace(",", " ").split() if g.strip()] if query.gan else list(TianganEngine.TIANGAN)

        derivations = []
        for g in gans:
            sr = ShiganEngine.compute(dm, g)
            derivations.append({
                "gan": g,
                "shigan": sr.shigan.value,
                "category": ShiganEngine.classify(sr.shigan),
                "description": sr.description,
            })

        return {
            "day_master": dm,
            "derivations": derivations,
            "total_derived": len(derivations),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"十神推演失败: {e}")


@app.post("/api/knowledge/dizhi", tags=["知识查询"])
async def dizhi_analyze(query: DizhiQuery, request: Request,
                        ):
    """地支分析：藏干/六合/三合/六冲/六害/六破/相刑"""
    try:
        from tengod.divination_engine import DizhiEngine, find_interactions
        branches = query.branches.split(",")

        # 地支基本信息
        info = {}
        for b in branches:
            di = DizhiEngine._INFO.get(b)
            if di:
                info[b] = {
                    "name": b,
                    "wuxing": di.wuxing,
                    "yinyang": di.yinyang.value if hasattr(di.yinyang, 'value') else str(di.yinyang),
                    "direction": di.direction,
                    "month": di.month_name,
                    "hour": di.hour_name,
                    "animal": di.zodiac,
                    "canggan": di.canggan_main,
                }

        # 互动关系
        interactions = find_interactions(branches)

        result = {
            "input_branches": branches,
            "analysis_type": query.analysis_type,
            "info": info,
        }

        if query.analysis_type in ("all", "liuhe"):
            if interactions.get("he"):
                result["liuhe_六合"] = interactions["he"]
        if query.analysis_type in ("all", "sanhe"):
            if interactions.get("sanhe"):
                result["sanhe_三合"] = interactions["sanhe"]
        if query.analysis_type in ("all", "chong"):
            if interactions.get("chong"):
                result["chong_六冲"] = interactions["chong"]
        if query.analysis_type in ("all", "hai"):
            if interactions.get("hai"):
                result["hai_六害"] = interactions["hai"]
        if query.analysis_type in ("all", "po"):
            if interactions.get("po"):
                result["po_六破"] = interactions["po"]
        if query.analysis_type in ("all", "xing"):
            if interactions.get("xing"):
                result["xing_相刑"] = interactions["xing"]

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"地支分析失败: {e}")


# ============================================================================
# 全局异常处理
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": str(exc.detail),
            "status_code": exc.status_code,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.exception(f"未处理的异常: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


# ============================================================================
# 启动入口
# ============================================================================

def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description="十神架构 REST API Server")
    parser.add_argument("--host", default="127.0.0.1", help="监听地址 (默认: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="监听端口 (默认: 8000)")
    parser.add_argument("--api-key", default=None, help="API Key (启用鉴权)")
    parser.add_argument("--reload", action="store_true", help="开发模式热重载")
    args = parser.parse_args()

    if args.api_key:
        os.environ["TENGOD_API_KEY"] = args.api_key
        logger.info(f"API Key 鉴权已启用")

    logger.info(f"启动 API Server: http://{args.host}:{args.port}")
    logger.info(f"Swagger 文档: http://{args.host}:{args.port}/docs")

    uvicorn.run(
        "tengod.api_server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )


if __name__ == "__main__":
    main()