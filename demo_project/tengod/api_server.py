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
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
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

PUBLIC_PATHS = {"/api/health", "/api/health/full", "/api/stats", "/metrics", "/api/metrics", "/docs", "/redoc", "/openapi.json"}


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


class RecordLabel(BaseModel):
    """记录标签更新"""
    label: Optional[str] = Field(default=None, description="记录标签")
    tags: Optional[str] = Field(default=None, description="标签")
    notes: Optional[str] = Field(default=None, description="备注")


class RecordSearch(BaseModel):
    """记录搜索"""
    year: Optional[int] = Field(default=None, ge=1900, le=2100)
    month: Optional[int] = Field(default=None, ge=1, le=12)
    day_master: Optional[str] = Field(default=None)
    gender: Optional[str] = Field(default=None)
    tag: Optional[str] = Field(default=None)
    limit: int = Field(default=50, ge=1, le=200)


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

# 鉴权（API Key）
app.add_middleware(AuthMiddleware)
# 阶段十三：JWT 用户认证中间件
from tengod.auth import auth_middleware
app.middleware("http")(auth_middleware)
# 请求日志
app.middleware("http")(log_middleware)
# 限流
app.middleware("http")(rate_limit_middleware)

# 静态文件（3D 可视化等）
_static_dir = os.path.join(os.path.dirname(__file__), "..", "..", "deploy_frontend")
if os.path.isdir(_static_dir):
    app.mount("/static", StaticFiles(directory=_static_dir), name="static")


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
# 根路由 → 前端 SPA
# ============================================================================

@app.get("/", response_class=RedirectResponse, include_in_schema=False)
async def root():
    """重定向到前端 SPA"""
    return RedirectResponse(url="/static/index.html")


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


@app.get("/api/health/full", tags=["系统"])
async def health_check_full():
    """全面健康检查（含数据库、Redis、向量存储、系统资源）"""
    from tengod.metrics_collector import HealthChecker
    return HealthChecker.check_all()


@app.get("/metrics", tags=["系统"])
async def prometheus_metrics():
    """Prometheus 指标端点"""
    from tengod.metrics_collector import metrics
    from fastapi import Response
    return Response(content=metrics.to_prometheus(), media_type="text/plain")


@app.get("/api/metrics", tags=["系统"])
async def api_metrics():
    """JSON 格式监控指标"""
    from tengod.metrics_collector import metrics
    return metrics.get_snapshot()


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
    from tengod.auth import authorize
    authorize(request, "bazi:calc")
    try:
        from tengod.metrics_collector import metrics
        metrics.record_bazi_calc()
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
    from tengod.auth import authorize
    authorize(request, "bazi:calc")
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
    from tengod.auth import authorize
    authorize(request, "bazi:calc")
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
    from tengod.auth import authorize
    authorize(request, "bazi:calc")
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
    from tengod.auth import authorize
    authorize(request, "bazi:calc")
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
    from tengod.auth import authorize
    authorize(request, "bazi:full")
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
    from tengod.auth import authorize
    authorize(request, "bazi:report")
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
    from tengod.auth import authorize
    authorize(request, "knowledge:search")
    try:
        from tengod.metrics_collector import metrics
        metrics.record_knowledge_search()
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
    from tengod.auth import authorize
    authorize(request, "knowledge:search")
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
async def wuxing_query(element: str, request: Request,
                       relation_mode: str = Query("info", description="info/relations"),
                       ):
    """五行查询：生克/方位/脏腑/颜色"""
    from tengod.auth import authorize
    authorize(request, "knowledge:wuxing")
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
async def bagua_query(trigram: str, request: Request,
                      query_type: str = Query("info", description="info/relations"),
                      ):
    """八卦查询：卦象信息/方位/五行属性"""
    from tengod.auth import authorize
    authorize(request, "knowledge:wuxing")
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
    from tengod.auth import authorize
    authorize(request, "knowledge:search")
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
    from tengod.auth import authorize
    authorize(request, "knowledge:search")
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
# 数据持久化 API
# ============================================================================

def _get_store() -> "DataStore":
    from tengod.data_store import get_data_store
    return get_data_store()


def _get_data_store() -> "DataStore":
    """获取数据存储实例（别名，兼容认证端点）"""
    from tengod.data_store import get_data_store
    return get_data_store()


@app.post("/api/records", tags=["数据持久化"])
async def save_record(bazi: BaziInput, request: Request,
                      label: str = Query(None, description="记录标签"),
                      username: str = Query(None, description="用户名（已废弃，自动使用当前登录用户）")):
    """保存八字排盘记录（自动计算排盘+神煞+格局+喜用神）

    阶段十三：记录自动关联到当前登录用户（多租户隔离）
    """
    from tengod.auth import authorize
    auth_user = authorize(request, "records:write")
    try:
        from tengod.bazi_analyzer import BaziAnalyzer
        from tengod.shensha_engine import calc_all_shensha
        from tengod.geju_engine import calc_geju, calc_yongshen, calc_tiaohou

        is_male = bazi.gender == "male"
        analyzer = BaziAnalyzer(bazi.year, bazi.month, bazi.day,
                                bazi.hour, bazi.minute, is_male=is_male,
                                longitude=bazi.longitude, latitude=bazi.latitude)
        a = analyzer.analysis
        pillars = a["pillars"]

        store = _get_store()
        # 阶段十三：使用当前登录用户 ID（多租户隔离）
        record_id = store.save_bazi_record(
            year=bazi.year, month=bazi.month, day=bazi.day,
            hour=bazi.hour, minute=bazi.minute,
            gender=bazi.gender,
            longitude=bazi.longitude, latitude=bazi.latitude,
            user_id=auth_user.id, label=label,
            day_master=a["day_master"],
            pillars=pillars,
            analysis=a,
            shensha={"total": len(calc_all_shensha(pillars).all_shensha),
                     "summary": calc_all_shensha(pillars).summary},
            geju={
                "name": calc_geju(pillars).geju_name,
                "type": calc_geju(pillars).geju_type,
                "desc": calc_geju(pillars).geju_desc,
                "score": calc_geju(pillars).score,
            },
            yongshen={
                "wang_shuai": calc_yongshen(pillars).wang_shuai,
                "yong_shen": calc_yongshen(pillars).yong_shen,
                "ji_shen": calc_yongshen(pillars).ji_shen,
            },
            tiaohou={
                "required": calc_tiaohou(pillars).required_tiaohou,
                "tiaohou_shens": calc_tiaohou(pillars).tiaohou_shens,
            },
        )

        return {
            "id": record_id,
            "user_id": auth_user.id,
            "username": auth_user.username,
            "day_master": a["day_master"],
            "pillars": pillars,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存记录失败: {e}")


@app.get("/api/records", tags=["数据持久化"])
async def list_records(
    request: Request,
    user_id: int = Query(None, description="用户 ID（仅管理员可指定）"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """列出八字排盘记录

    阶段十三：普通用户只能查看自己的记录，管理员可查看所有或指定用户
    """
    from tengod.auth import authorize
    auth_user = authorize(request, "records:read", consume_quota=False)
    # 多租户隔离：非管理员强制只看自己的记录
    if not auth_user.is_admin:
        user_id = auth_user.id
    try:
        store = _get_store()
        records = store.list_bazi_records(user_id=user_id, limit=limit, offset=offset)
        return {
            "total": store.count_bazi_records(user_id=user_id),
            "limit": limit,
            "offset": offset,
            "records": [
                {
                    "id": r.id, "user_id": r.user_id, "label": r.label,
                    "year": r.year, "month": r.month, "day": r.day,
                    "hour": r.hour, "gender": r.gender,
                    "day_master": r.day_master,
                    "tags": r.tags,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in records
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"列出记录失败: {e}")


@app.get("/api/records/{record_id}", tags=["数据持久化"])
async def get_record(record_id: int, request: Request):
    """获取单条八字排盘记录（含完整分析结果）

    阶段十三：普通用户只能查看自己的记录
    """
    from tengod.auth import authorize
    auth_user = authorize(request, "records:read", consume_quota=False)
    try:
        store = _get_store()
        record = store.get_bazi_record(record_id)
        if record is None:
            raise HTTPException(status_code=404, detail=f"记录不存在: {record_id}")
        # 多租户隔离
        if not auth_user.is_admin and record.user_id != auth_user.id:
            raise HTTPException(status_code=403, detail="无权访问此记录")
        return record.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取记录失败: {e}")


@app.put("/api/records/{record_id}", tags=["数据持久化"])
async def update_record(record_id: int, update: RecordLabel, request: Request):
    """更新记录标签/备注

    阶段十三：普通用户只能更新自己的记录
    """
    from tengod.auth import authorize
    auth_user = authorize(request, "records:write", consume_quota=False)
    try:
        store = _get_store()
        record = store.get_bazi_record(record_id)
        if record is None:
            raise HTTPException(status_code=404, detail=f"记录不存在: {record_id}")
        if not auth_user.is_admin and record.user_id != auth_user.id:
            raise HTTPException(status_code=403, detail="无权修改此记录")
        kwargs = {}
        if update.label is not None:
            kwargs["label"] = update.label
        if update.tags is not None:
            kwargs["tags"] = update.tags
        if update.notes is not None:
            kwargs["notes"] = update.notes
        if not kwargs:
            raise HTTPException(status_code=400, detail="No update fields provided")
        ok = store.update_bazi_record(record_id, **kwargs)
        if not ok:
            raise HTTPException(status_code=404, detail=f"记录不存在: {record_id}")
        return {"id": record_id, "updated": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新记录失败: {e}")


@app.delete("/api/records/{record_id}", tags=["数据持久化"])
async def delete_record(record_id: int, request: Request):
    """删除八字排盘记录

    阶段十三：普通用户只能删除自己的记录
    """
    from tengod.auth import authorize
    auth_user = authorize(request, "records:delete", consume_quota=False)
    try:
        store = _get_store()
        record = store.get_bazi_record(record_id)
        if record is None:
            raise HTTPException(status_code=404, detail=f"记录不存在: {record_id}")
        if not auth_user.is_admin and record.user_id != auth_user.id:
            raise HTTPException(status_code=403, detail="无权删除此记录")
        ok = store.delete_bazi_record(record_id)
        if not ok:
            raise HTTPException(status_code=404, detail=f"记录不存在: {record_id}")
        return {"id": record_id, "deleted": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除记录失败: {e}")


@app.post("/api/records/search", tags=["数据持久化"])
async def search_records(search: RecordSearch, request: Request):
    """搜索八字排盘记录"""
    from tengod.auth import authorize
    authorize(request, "records:read")
    try:
        store = _get_store()
        records = store.search_bazi_records(
            year=search.year, month=search.month,
            day_master=search.day_master,
            gender=search.gender,
            tag=search.tag,
            limit=search.limit,
        )
        return {
            "count": len(records),
            "records": [
                {
                    "id": r.id, "user_id": r.user_id, "label": r.label,
                    "year": r.year, "month": r.month, "day": r.day,
                    "hour": r.hour, "gender": r.gender,
                    "day_master": r.day_master,
                    "tags": r.tags,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in records
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索记录失败: {e}")


@app.get("/api/users", tags=["数据持久化"])
async def list_users(limit: int = Query(50, ge=1, le=200)):
    """列出用户"""
    try:
        store = _get_store()
        users = store.list_users(limit=limit)
        return {
            "count": len(users),
            "users": [
                {"id": u.id, "username": u.username, "display_name": u.display_name,
                 "created_at": u.created_at.isoformat() if u.created_at else None}
                for u in users
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"列出用户失败: {e}")


# ============================================================================
# 增强 stats 端点（含数据库统计）
# ============================================================================

@app.get("/api/stats/db", tags=["系统"])
async def db_stats():
    """数据库统计信息"""
    try:
        store = _get_store()
        return store.stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"数据库统计失败: {e}")


# ============================================================================
# 阶段十三：用户认证 API 模型
# ============================================================================

class RegisterRequest(BaseModel):
    """注册请求"""
    username: str = Field(..., min_length=3, max_length=64, description="用户名")
    password: str = Field(..., min_length=6, max_length=128, description="密码")
    display_name: Optional[str] = Field(default=None, max_length=128, description="显示名")
    email: Optional[str] = Field(default=None, max_length=128, description="邮箱")


class LoginRequest(BaseModel):
    """登录请求"""
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class RefreshRequest(BaseModel):
    """刷新令牌请求"""
    refresh_token: str = Field(..., description="刷新令牌")


class ChangePasswordRequest(BaseModel):
    """修改密码请求"""
    old_password: str = Field(..., description="旧密码")
    new_password: str = Field(..., min_length=6, max_length=128, description="新密码")


class UpdateUserRequest(BaseModel):
    """更新用户信息请求"""
    display_name: Optional[str] = Field(default=None, max_length=128)
    email: Optional[str] = Field(default=None, max_length=128)


# ============================================================================
# 阶段十一：高级术数 API 模型
# ============================================================================

class ZiweiQuery(BaseModel):
    """紫微斗数排盘查询"""
    year: int = Field(..., ge=1900, le=2100, description="公历年")
    month: int = Field(..., ge=1, le=12, description="公历月")
    day: int = Field(..., ge=1, le=31, description="公历日")
    hour: int = Field(default=0, ge=0, le=23, description="小时")
    minute: int = Field(default=0, ge=0, le=59, description="分钟")
    gender: str = Field(default="male", description="性别 (male/female)")


class LiuyaoQuery(BaseModel):
    """六爻摇卦查询"""
    yao_str: Optional[str] = Field(default=None, description="六爻字符串 (1=少阳,0=少阴,3=老阳,2=老阴)")
    day_ganzhi: Optional[str] = Field(default=None, description="日干支")


class QimenQuery(BaseModel):
    """奇门遁甲排盘查询"""
    year: int = Field(..., ge=1900, le=2100, description="公历年")
    month: int = Field(..., ge=1, le=12, description="公历月")
    day: int = Field(..., ge=1, le=31, description="公历日")
    hour: int = Field(default=0, ge=0, le=23, description="小时")
    minute: int = Field(default=0, ge=0, le=59, description="分钟")


class NameQuery(BaseModel):
    """姓名学分析查询"""
    surname: str = Field(..., min_length=1, max_length=2, description="姓氏")
    given_name: str = Field(..., min_length=1, max_length=2, description="名字")


class MarriageQuery(BaseModel):
    """合婚分析查询"""
    bazi1: Dict[str, Any] = Field(..., description="男方八字数据")
    bazi2: Dict[str, Any] = Field(..., description="女方八字数据")
    name1: str = Field(default="男方", description="男方姓名")
    name2: str = Field(default="女方", description="女方姓名")


# ============================================================================
# LLM 大模型 API
# ============================================================================

class ChatQuery(BaseModel):
    """AI 对话查询"""
    question: str = Field(..., min_length=1, description="用户问题")
    bazi_json: Optional[Dict[str, Any]] = Field(default=None, description="八字上下文（可选）")
    use_rag: bool = Field(default=True, description="是否启用 RAG 增强")
    stream: bool = Field(default=False, description="是否流式输出")


class ChatResponse(BaseModel):
    """AI 对话响应"""
    question: str
    answer: str
    model: str
    backend: str
    rag_used: bool
    usage: Dict[str, int] = {}


@app.post("/api/chat", tags=["AI 对话"])
async def ai_chat(query: ChatQuery, request: Request):
    """AI 命理对话（支持 RAG 增强）"""
    from tengod.auth import authorize
    authorize(request, "chat:send")
    from tengod.metrics_collector import metrics
    metrics.record_ai_chat()
    from tengod.llm_adapter import get_llm, chat, chat_stream, ChatMessage

    llm = get_llm()

    # 构建八字上下文
    bazi_context = None
    if query.bazi_json:
        bazi = query.bazi_json
        bazi_context = (
            f"八字：{bazi.get('pillars', {}).get('year', '')} "
            f"{bazi.get('pillars', {}).get('month', '')} "
            f"{bazi.get('pillars', {}).get('day', '')} "
            f"{bazi.get('pillars', {}).get('hour', '')}\n"
            f"日主：{bazi.get('day_master', '')}\n"
            f"性别：{bazi.get('input', {}).get('gender', '')}"
        )

    # 流式输出
    if query.stream:
        from fastapi.responses import StreamingResponse

        async def generate():
            async for chunk in chat_stream(
                query.question, bazi_context, llm, use_rag=query.use_rag
            ):
                yield f"data: {json.dumps({'chunk': chunk}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={"X-Backend": llm.model_name},
        )

    # 非流式
    answer = await chat(query.question, bazi_context, llm, use_rag=query.use_rag)
    return ChatResponse(
        question=query.question,
        answer=answer,
        model=llm.model_name,
        backend=os.environ.get("TENGOD_LLM_BACKEND", "mock"),
        rag_used=query.use_rag,
    )


@app.post("/api/chat/report", tags=["AI 对话"])
async def ai_report(bazi: BaziInput, request: Request,
                    use_rag: bool = Query(True, description="是否启用 RAG")):
    """AI 生成命理报告"""
    from tengod.auth import authorize
    authorize(request, "chat:report")
    from tengod.llm_adapter import get_llm, generate_report
    from tengod.bazi_analyzer import BaziAnalyzer
    from tengod.report_generator import BaziReportGenerator

    try:
        analyzer = BaziAnalyzer(
            bazi.year, bazi.month, bazi.day,
            bazi.hour, bazi.minute,
            is_male=(bazi.gender == "male"),
            longitude=bazi.longitude, latitude=bazi.latitude,
        )
        gen = BaziReportGenerator(analyzer)
        report_text = gen.text_report()

        llm = get_llm()
        enhanced = await generate_report(report_text, llm, use_rag=use_rag)

        return {
            "original": report_text[:500],
            "enhanced": enhanced,
            "model": llm.model_name,
            "rag_used": use_rag,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 报告生成失败: {e}")


# ============================================================================
# 阶段十七：AI 智能解读 API 端点
# ============================================================================

class AIInterpretRequest(BaseModel):
    """AI 解读请求"""
    question: str = Field(default="", description="可选：用户关注的具体问题")


@app.post("/api/ai/interpret/bazi", tags=["AI 智能解读"])
async def ai_interpret_bazi(bazi: BaziInput, request: Request,
                            use_rag: bool = Query(False, description="是否启用RAG增强"),
                            question: str = Query("", description="可选关注问题"),
                            stream: bool = Query(False, description="是否流式输出")):
    """八字深度 AI 解读（四柱+神煞+格局+喜用神+调候+大运）"""
    from tengod.auth import authorize
    authorize(request, "ai:interpret" if not stream else "ai:interpret:stream")
    from tengod.metrics_collector import metrics
    metrics.record_ai_chat()

    from tengod.ai_interpreter import (
        build_bazi_context, interpret_bazi, interpret_bazi_stream,
    )
    from tengod.bazi_analyzer import BaziAnalyzer
    from tengod.shensha_engine import calc_all_shensha
    from tengod.geju_engine import analyze_bazi_comprehensive
    from tengod.llm_adapter import get_llm

    try:
        # 1. 排盘 + 综合分析
        analyzer = BaziAnalyzer(
            bazi.year, bazi.month, bazi.day, bazi.hour, bazi.minute,
            is_male=(bazi.gender == "male"),
            longitude=bazi.longitude, latitude=bazi.latitude,
        )
        analysis = analyzer.analysis

        # 2. 神煞推算
        shensha_result = calc_all_shensha(analysis["pillars"])

        # 3. 格局/喜用神/调候综合分析
        comprehensive = analyze_bazi_comprehensive(analysis["pillars"])

        # 4. 构建结构化上下文
        from tengod.ai_interpreter import _to_dict
        shensha_dict = _to_dict(shensha_result)
        comp_dict = _to_dict(comprehensive)
        context = build_bazi_context(
            pillars=analysis["pillars"],
            day_master=analysis["day_master"],
            gender=bazi.gender,
            wuxing=analysis.get("wuxing"),
            shigan_map=analysis.get("shigan_map"),
            shensha=shensha_dict,
            geju=comp_dict.get("geju"),
            yongshen=comp_dict.get("yongshen"),
            tiaohou=comp_dict.get("tiaohou"),
            dayuns=analysis.get("dayuns"),
            branch_relations=analysis.get("branch_relations"),
        )

        llm = get_llm()

        # 5. 流式或非流式输出
        if stream:
            from fastapi.responses import StreamingResponse

            async def generate():
                async for chunk in interpret_bazi_stream(
                    context, llm=llm, use_rag=use_rag, question=question
                ):
                    yield f"data: {json.dumps({'chunk': chunk}, ensure_ascii=False)}\n\n"
                yield "data: [DONE]\n\n"

            return StreamingResponse(
                generate(),
                media_type="text/event-stream",
                headers={"X-Backend": llm.model_name},
            )

        report = await interpret_bazi(context, llm=llm, use_rag=use_rag, question=question)
        return {
            "interpretation": report,
            "model": llm.model_name,
            "backend": os.environ.get("TENGOD_LLM_BACKEND", "mock"),
            "rag_used": use_rag,
            "context_preview": context[:200],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 八字解读失败: {e}")


@app.post("/api/ai/interpret/ziwei", tags=["AI 智能解读"])
async def ai_interpret_ziwei(bazi: BaziInput, request: Request,
                             question: str = Query("", description="可选关注问题")):
    """紫微斗数 AI 解读"""
    from tengod.auth import authorize
    authorize(request, "ai:interpret")
    from tengod.ai_interpreter import build_ziwei_context, interpret_ziwei
    from tengod.ziwei_engine import calc_ziwei, ziwei_to_dict
    from tengod.llm_adapter import get_llm

    try:
        chart = calc_ziwei(bazi.year, bazi.month, bazi.day, bazi.hour,
                          bazi.minute, bazi.gender)
        chart_dict = ziwei_to_dict(chart)
        context = build_ziwei_context(chart_dict)

        llm = get_llm()
        report = await interpret_ziwei(context, llm=llm, question=question)
        return {
            "interpretation": report,
            "model": llm.model_name,
            "backend": os.environ.get("TENGOD_LLM_BACKEND", "mock"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 紫微解读失败: {e}")


@app.post("/api/ai/interpret/liuyao", tags=["AI 智能解读"])
async def ai_interpret_liuyao(request: Request,
                              question: str = Query(..., description="所占之事")):
    """六爻 AI 解读"""
    from tengod.auth import authorize
    authorize(request, "ai:interpret")
    from tengod.ai_interpreter import build_liuyao_context, interpret_liuyao
    from tengod.liuyao_engine import shake_and_calc
    from tengod.ai_interpreter import _to_dict
    from tengod.llm_adapter import get_llm

    try:
        result = shake_and_calc()
        result_dict = _to_dict(result)
        context = build_liuyao_context(result_dict)

        llm = get_llm()
        report = await interpret_liuyao(context, question=question, llm=llm)
        return {
            "interpretation": report,
            "model": llm.model_name,
            "backend": os.environ.get("TENGOD_LLM_BACKEND", "mock"),
            "gua_name": result_dict.get("ben_gua_name", ""),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 六爻解读失败: {e}")


@app.post("/api/ai/interpret/name", tags=["AI 智能解读"])
async def ai_interpret_name(request: Request,
                            surname: str = Query(..., description="姓氏"),
                            given_name: str = Query(..., description="名字")):
    """姓名学 AI 解读"""
    from tengod.auth import authorize
    authorize(request, "ai:interpret")
    from tengod.ai_interpreter import build_name_context, interpret_name
    from tengod.name_engine import analyze_name
    from tengod.ai_interpreter import _to_dict
    from tengod.llm_adapter import get_llm

    try:
        result = analyze_name(surname, given_name)
        result_dict = _to_dict(result)
        context = build_name_context(result_dict)

        llm = get_llm()
        report = await interpret_name(context, llm=llm)
        return {
            "interpretation": report,
            "model": llm.model_name,
            "backend": os.environ.get("TENGOD_LLM_BACKEND", "mock"),
            "score": result_dict.get("score", 0),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 姓名解读失败: {e}")


class MarriageInterpretRequest(BaseModel):
    """合婚 AI 解读请求"""
    name1: str = Field(..., description="甲方姓名")
    name2: str = Field(..., description="乙方姓名")
    bazi1: Dict[str, Any] = Field(..., description="甲方八字数据")
    bazi2: Dict[str, Any] = Field(..., description="乙方八字数据")


@app.post("/api/ai/interpret/marriage", tags=["AI 智能解读"])
async def ai_interpret_marriage(req: MarriageInterpretRequest, request: Request):
    """合婚 AI 解读"""
    from tengod.auth import authorize
    authorize(request, "ai:interpret")
    from tengod.ai_interpreter import build_marriage_context, interpret_marriage
    from tengod.marriage_engine import analyze_marriage
    from tengod.ai_interpreter import _to_dict
    from tengod.llm_adapter import get_llm

    try:
        result = analyze_marriage(req.name1, req.bazi1, req.name2, req.bazi2)
        result_dict = _to_dict(result)
        context = build_marriage_context(result_dict)

        llm = get_llm()
        report = await interpret_marriage(context, llm=llm)
        return {
            "interpretation": report,
            "model": llm.model_name,
            "backend": os.environ.get("TENGOD_LLM_BACKEND", "mock"),
            "total_score": result_dict.get("total_score", 0),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 合婚解读失败: {e}")


@app.post("/api/ai/interpret/oracle", tags=["AI 智能解读"])
async def ai_interpret_oracle(request: Request,
                              question: str = Query(..., description="所占之事"),
                              mode: str = Query("tuibeitu", description="占卜模式")):
    """Oracle 推背图 AI 深度解读"""
    from tengod.auth import authorize
    authorize(request, "ai:interpret")
    from tengod.ai_interpreter import build_oracle_context, interpret_oracle
    from tengod.伤官_破界创新.oracle_engine import OracleEngine, OracleMode
    from tengod.ai_interpreter import _to_dict
    from tengod.llm_adapter import get_llm

    try:
        mode_map = {
            "tuibeitu": OracleMode.TUIBEITU,
            "zhouyi": OracleMode.ZHOUYI,
            "zigua": OracleMode.ZIGUA,
        }
        oracle_mode = mode_map.get(mode.lower(), OracleMode.TUIBEITU)
        engine = OracleEngine()
        result = engine.cast(question, mode=oracle_mode)
        result_dict = _to_dict(result)
        context = build_oracle_context(result_dict)

        llm = get_llm()
        report = await interpret_oracle(context, question=question, llm=llm)
        return {
            "interpretation": report,
            "model": llm.model_name,
            "backend": os.environ.get("TENGOD_LLM_BACKEND", "mock"),
            "hexagram": result_dict.get("hexagram", ""),
            "hexagram_name": result_dict.get("hexagram", ""),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Oracle 解读失败: {e}")


# ============================================================================
# 阶段十三：用户认证 API 端点
# ============================================================================

@app.post("/api/auth/register", tags=["用户认证"])
async def register(req: RegisterRequest):
    """用户注册"""
    from tengod.auth import PasswordHasher
    from tengod.data_store import DataStore, User as UserModel

    store = _get_data_store()
    with store._session() as s:
        # 检查用户名是否已存在
        existing = s.query(UserModel).filter(UserModel.username == req.username).first()
        if existing:
            raise HTTPException(status_code=409, detail="用户名已存在")

        # 创建用户
        user = UserModel(
            username=req.username,
            display_name=req.display_name or req.username,
            email=req.email,
            password_hash=PasswordHasher.hash(req.password),
            role="user",
            is_active=1,
        )
        s.add(user)
        s.commit()
        s.refresh(user)

    return {
        "message": "注册成功",
        "user": {
            "id": user.id,
            "username": user.username,
            "display_name": user.display_name,
            "role": user.role,
        },
    }


@app.post("/api/auth/login", tags=["用户认证"])
async def login(req: LoginRequest):
    """用户登录"""
    from tengod.auth import PasswordHasher, JWTManager, create_token_pair
    from tengod.data_store import DataStore, User as UserModel

    store = _get_data_store()
    with store._session() as s:
        user = s.query(UserModel).filter(UserModel.username == req.username).first()
        if user is None:
            raise HTTPException(status_code=401, detail="用户名或密码错误")
        if not user.is_active:
            raise HTTPException(status_code=403, detail="账号已被禁用")
        if not user.password_hash:
            raise HTTPException(status_code=401, detail="账号未设置密码")

        if not PasswordHasher.verify(req.password, user.password_hash):
            raise HTTPException(status_code=401, detail="用户名或密码错误")

        # 更新最后登录时间
        user.last_login_at = datetime.now(timezone.utc)
        s.commit()

        tokens = create_token_pair(user.id, user.username, user.role)

    return {
        "message": "登录成功",
        "user": {
            "id": user.id,
            "username": user.username,
            "display_name": user.display_name,
            "role": user.role,
        },
        **tokens,
    }


@app.post("/api/auth/refresh", tags=["用户认证"])
async def refresh_token(req: RefreshRequest):
    """刷新访问令牌"""
    from tengod.auth import JWTManager, create_token_pair

    payload = JWTManager.verify_token(req.refresh_token)
    if payload is None:
        raise HTTPException(status_code=401, detail="刷新令牌无效或已过期")
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="令牌类型错误")

    tokens = create_token_pair(
        int(payload["sub"]),
        payload["username"],
        payload["role"],
    )
    return {"message": "刷新成功", **tokens}


@app.get("/api/auth/me", tags=["用户认证"])
async def get_me(request: Request):
    """获取当前用户信息"""
    from tengod.auth import CurrentUser

    user: Optional[CurrentUser] = getattr(request.state, "current_user", None)
    if user is None or not user.is_authenticated:
        raise HTTPException(status_code=401, detail="未登录")

    from tengod.auth import QuotaManager, ROLE_PERMISSIONS
    quota = ROLE_PERMISSIONS.get(user.role, {}).get("quota_daily", 100)
    allowed, used, remaining = QuotaManager.check(user.id, quota)

    return {
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "role_name": ROLE_PERMISSIONS.get(user.role, {}).get("name", "未知"),
        "permissions": user.permissions,
        "quota": {
            "daily_limit": quota,
            "used_today": used,
            "remaining": remaining,
        },
    }


@app.post("/api/auth/change-password", tags=["用户认证"])
async def change_password(req: ChangePasswordRequest, request: Request):
    """修改密码"""
    from tengod.auth import CurrentUser, PasswordHasher
    from tengod.data_store import DataStore, User as UserModel

    user: Optional[CurrentUser] = getattr(request.state, "current_user", None)
    if user is None or not user.is_authenticated:
        raise HTTPException(status_code=401, detail="未登录")

    store = _get_data_store()
    with store._session() as s:
        db_user = s.query(UserModel).filter(UserModel.id == user.id).first()
        if db_user is None:
            raise HTTPException(status_code=404, detail="用户不存在")

        if not PasswordHasher.verify(req.old_password, db_user.password_hash):
            raise HTTPException(status_code=400, detail="旧密码错误")

        db_user.password_hash = PasswordHasher.hash(req.new_password)
        s.commit()

    return {"message": "密码修改成功"}


@app.put("/api/auth/profile", tags=["用户认证"])
async def update_profile(req: UpdateUserRequest, request: Request):
    """更新用户资料"""
    from tengod.auth import CurrentUser
    from tengod.data_store import DataStore, User as UserModel

    user: Optional[CurrentUser] = getattr(request.state, "current_user", None)
    if user is None or not user.is_authenticated:
        raise HTTPException(status_code=401, detail="未登录")

    store = _get_data_store()
    with store._session() as s:
        db_user = s.query(UserModel).filter(UserModel.id == user.id).first()
        if db_user is None:
            raise HTTPException(status_code=404, detail="用户不存在")

        if req.display_name is not None:
            db_user.display_name = req.display_name
        if req.email is not None:
            db_user.email = req.email
        s.commit()
        result = {
            "id": db_user.id,
            "username": db_user.username,
            "display_name": db_user.display_name,
            "email": db_user.email,
            "role": db_user.role,
        }

    return {"message": "资料更新成功", "user": result}


# ── 管理员端点 ──────────────────────────────────────────────────────

@app.get("/api/admin/users", tags=["管理员"])
async def list_users(request: Request):
    """列出所有用户（仅管理员）"""
    from tengod.auth import CurrentUser
    from tengod.data_store import DataStore, User as UserModel

    user: Optional[CurrentUser] = getattr(request.state, "current_user", None)
    if user is None or user.role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")

    store = _get_data_store()
    with store._session() as s:
        users = s.query(UserModel).order_by(UserModel.created_at.desc()).all()
        return {
            "total": len(users),
            "users": [
                {
                    "id": u.id,
                    "username": u.username,
                    "display_name": u.display_name,
                    "email": u.email,
                    "role": u.role,
                    "is_active": bool(u.is_active),
                    "created_at": str(u.created_at) if u.created_at else None,
                    "last_login_at": str(u.last_login_at) if u.last_login_at else None,
                }
                for u in users
            ],
        }


@app.put("/api/admin/users/{user_id}/role", tags=["管理员"])
async def update_user_role(user_id: int, role: str, request: Request):
    """更新用户角色（仅管理员）"""
    from tengod.auth import CurrentUser, ROLE_PERMISSIONS
    from tengod.data_store import DataStore, User as UserModel

    current: Optional[CurrentUser] = getattr(request.state, "current_user", None)
    if current is None or current.role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")

    if role not in ROLE_PERMISSIONS:
        raise HTTPException(status_code=400, detail=f"无效角色: {role}")

    store = _get_data_store()
    with store._session() as s:
        user = s.query(UserModel).filter(UserModel.id == user_id).first()
        if user is None:
            raise HTTPException(status_code=404, detail="用户不存在")
        user.role = role
        s.commit()
        username = user.username

    return {"message": f"用户 {username} 角色已更新为 {role}"}


@app.put("/api/admin/users/{user_id}/status", tags=["管理员"])
async def toggle_user_status(user_id: int, request: Request):
    """启用/禁用用户（仅管理员）"""
    from tengod.auth import CurrentUser
    from tengod.data_store import DataStore, User as UserModel

    current: Optional[CurrentUser] = getattr(request.state, "current_user", None)
    if current is None or current.role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")

    store = _get_data_store()
    with store._session() as s:
        user = s.query(UserModel).filter(UserModel.id == user_id).first()
        if user is None:
            raise HTTPException(status_code=404, detail="用户不存在")
        user.is_active = 0 if user.is_active else 1
        s.commit()
        username = user.username
        is_active = bool(user.is_active)

    status_text = "启用" if is_active else "禁用"
    return {"message": f"用户 {username} 已{status_text}"}


# ============================================================================
# 阶段十一：高级术数 API 端点
# ============================================================================

@app.post("/api/ziwei/calc", tags=["高级术数"])
async def ziwei_calc(query: ZiweiQuery, request: Request):
    """紫微斗数排盘"""
    from tengod.auth import authorize
    authorize(request, "ziwei:calc")
    try:
        from tengod.metrics_collector import metrics
        metrics.record_ziwei_calc()
        from tengod.ziwei_engine import ZiweiEngine
        chart = ZiweiEngine.calc_chart(
            query.year, query.month, query.day,
            query.hour, query.minute, query.gender
        )
        return ZiweiEngine.to_dict(chart)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"紫微斗数排盘失败: {e}")


@app.post("/api/liuyao/shake", tags=["高级术数"])
async def liuyao_shake(query: LiuyaoQuery, request: Request):
    """六爻摇卦"""
    from tengod.auth import authorize
    authorize(request, "liuyao:shake")
    try:
        from tengod.metrics_collector import metrics
        metrics.record_liuyao_calc()
        from tengod.liuyao_engine import LiuyaoEngine, calc_from_yao
        if query.yao_str:
            result = calc_from_yao(query.yao_str, query.day_ganzhi)
        else:
            result = LiuyaoEngine.calc_gua(day_ganzhi=query.day_ganzhi)
        return {
            "ben_gua": result.ben_gua_name,
            "bian_gua": result.bian_gua_name,
            "hu_gua": result.hu_gua_name,
            "ben_symbol": result.ben_gua_symbol,
            "bian_symbol": result.bian_gua_symbol,
            "gua_gong": result.gua_gong,
            "shang_gua": result.shang_gua,
            "xia_gua": result.xia_gua,
            "dong_yao": result.dong_yao_positions,
            "yaos": [
                {
                    "position": y.position,
                    "symbol": LiuyaoEngine._yao_to_symbol(y.value, y.is_dong),
                    "liuqin": y.liuqin,
                    "zhi": y.zhi,
                    "liushen": y.liushen,
                    "shi": y.shi,
                    "ying": y.ying,
                    "is_dong": y.is_dong,
                }
                for y in result.yaos
            ],
            "duanci": result.ben_gua_duanci,
            "judgment": result.overall_judgment,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"六爻摇卦失败: {e}")


@app.post("/api/qimen/calc", tags=["高级术数"])
async def qimen_calc(query: QimenQuery, request: Request):
    """奇门遁甲排盘"""
    from tengod.auth import authorize
    authorize(request, "qimen:calc")
    try:
        from tengod.metrics_collector import metrics
        metrics.record_qimen_calc()
        from tengod.qimen_engine import QimenEngine
        chart = QimenEngine.calc_chart(
            query.year, query.month, query.day,
            query.hour, query.minute
        )
        return QimenEngine.to_dict(chart)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"奇门遁甲排盘失败: {e}")


@app.post("/api/name/analyze", tags=["高级术数"])
async def name_analyze(query: NameQuery, request: Request):
    """姓名学分析"""
    from tengod.auth import authorize
    authorize(request, "name:analyze")
    try:
        from tengod.metrics_collector import metrics
        metrics.record_name_analysis()
        from tengod.name_engine import NameEngine
        result = NameEngine.analyze(query.surname, query.given_name)
        return {
            "surname": result.surname,
            "given_name": result.given_name,
            "surname_strokes": result.surname_strokes,
            "given_strokes": result.given_strokes,
            "wuge": {
                "tian": {"value": result.wuge.tian_ge, "ji": result.wuge.tian_ge_ji},
                "ren": {"value": result.wuge.ren_ge, "ji": result.wuge.ren_ge_ji},
                "di": {"value": result.wuge.di_ge, "ji": result.wuge.di_ge_ji},
                "wai": {"value": result.wuge.wai_ge, "ji": result.wuge.wai_ge_ji},
                "zong": {"value": result.wuge.zong_ge, "ji": result.wuge.zong_ge_ji},
            },
            "sancai": "·".join(result.sancai),
            "sancai_ji": result.sancai_ji,
            "sancai_desc": result.sancai_desc,
            "overall_score": result.overall_score,
            "overall_grade": result.overall_grade,
            "suggestions": result.suggestions,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"姓名学分析失败: {e}")


@app.post("/api/marriage/analyze", tags=["高级术数"])
async def marriage_analyze(query: MarriageQuery, request: Request):
    """合婚分析"""
    from tengod.auth import authorize
    authorize(request, "marriage:analyze")
    try:
        from tengod.metrics_collector import metrics
        metrics.record_marriage_analysis()
        from tengod.marriage_engine import MarriageEngine
        result = MarriageEngine.analyze(
            query.name1, query.bazi1,
            query.name2, query.bazi2
        )
        return {
            "name1": result.name1,
            "name2": result.name2,
            "day_gan1": result.day_gan1,
            "day_gan2": result.day_gan2,
            "nayin": {"nayin1": result.nayin1, "nayin2": result.nayin2, "match": result.nayin_match, "score": result.nayin_score},
            "ri_gan": {"relation": result.ri_gan_he, "score": result.ri_gan_score},
            "dizhi": {"relations": result.zhi_relations, "score": result.zhi_score},
            "wuxing": {"analysis": result.wuxing_bu, "score": result.wuxing_score},
            "shengxiao": {"shengxiao1": result.shengxiao1, "shengxiao2": result.shengxiao2, "score": result.shengxiao_score},
            "overall_score": result.overall_score,
            "overall_grade": result.overall_grade,
            "summary": result.summary,
            "suggestions": result.suggestions,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"合婚分析失败: {e}")


# ============================================================================
# 阶段十四：命理知识图谱 API 端点
# ============================================================================

@app.get("/api/graph/stats", tags=["知识图谱"])
async def graph_stats(request: Request):
    """知识图谱统计信息"""
    from tengod.auth import authorize
    authorize(request, "knowledge:search", consume_quota=False)
    from tengod.graph_engine import get_graph_db
    return get_graph_db().stats()


@app.get("/api/graph/search", tags=["知识图谱"])
async def graph_search(request: Request,
                       keyword: str = Query(..., description="搜索关键词"),
                       limit: int = Query(20, ge=1, le=100)):
    """搜索图谱节点"""
    from tengod.auth import authorize
    authorize(request, "knowledge:search")
    from tengod.graph_engine import get_graph_db
    db = get_graph_db()
    nodes = db.search(keyword, limit=limit)
    return {
        "keyword": keyword,
        "total": len(nodes),
        "nodes": [n.to_dict() for n in nodes],
    }


@app.get("/api/graph/node/{node_name}", tags=["知识图谱"])
async def graph_get_node(node_name: str, request: Request):
    """按名称获取节点详情"""
    from tengod.auth import authorize
    authorize(request, "knowledge:search", consume_quota=False)
    from tengod.graph_engine import get_graph_db
    db = get_graph_db()
    node = db.find_node_by_name(node_name)
    if node is None:
        raise HTTPException(status_code=404, detail=f"未找到节点: {node_name}")
    return node.to_dict()


@app.get("/api/graph/node/{node_name}/neighbors", tags=["知识图谱"])
async def graph_neighbors(node_name: str, request: Request,
                          direction: str = Query("both", description="out/in/both"),
                          relation: str = Query(None, description="关系类型过滤"),
                          limit: int = Query(50, ge=1, le=200)):
    """获取节点邻居"""
    from tengod.auth import authorize
    authorize(request, "knowledge:search")
    from tengod.graph_engine import get_graph_db
    db = get_graph_db()
    node = db.find_node_by_name(node_name)
    if node is None:
        raise HTTPException(status_code=404, detail=f"未找到节点: {node_name}")

    neighbors = db.neighbors(node.id, direction=direction, relation=relation, limit=limit)
    edges = db.neighbor_edges(node.id, direction=direction, relation=relation)
    return {
        "node": node.to_dict(),
        "neighbors": [n.to_dict() for n in neighbors],
        "edges": [e.to_dict() for e in edges],
        "total": len(neighbors),
    }


@app.get("/api/graph/path", tags=["知识图谱"])
async def graph_path(request: Request,
                     source: str = Query(..., description="起点节点名"),
                     target: str = Query(..., description="终点节点名"),
                     max_depth: int = Query(10, ge=1, le=20)):
    """最短路径查询"""
    from tengod.auth import authorize
    authorize(request, "knowledge:search")
    from tengod.graph_engine import get_graph_db
    db = get_graph_db()

    src = db.find_node_by_name(source)
    tgt = db.find_node_by_name(target)
    if src is None:
        raise HTTPException(status_code=404, detail=f"未找到起点: {source}")
    if tgt is None:
        raise HTTPException(status_code=404, detail=f"未找到终点: {target}")

    result = db.shortest_path_with_edges(src.id, tgt.id, max_depth=max_depth)
    if result is None:
        return {
            "source": source,
            "target": target,
            "reachable": False,
            "message": f"在 {max_depth} 跳内不可达",
        }
    return {"source": source, "target": target, "reachable": True, **result}


@app.get("/api/graph/subgraph", tags=["知识图谱"])
async def graph_subgraph(request: Request,
                         node_names: str = Query(..., description="中心节点名（逗号分隔）"),
                         hops: int = Query(1, ge=1, le=5)):
    """提取子图"""
    from tengod.auth import authorize
    authorize(request, "knowledge:search")
    from tengod.graph_engine import get_graph_db
    db = get_graph_db()

    names = [n.strip() for n in node_names.split(",") if n.strip()]
    node_ids = []
    missing = []
    for name in names:
        node = db.find_node_by_name(name)
        if node:
            node_ids.append(node.id)
        else:
            missing.append(name)

    if not node_ids:
        raise HTTPException(status_code=404, detail=f"未找到任何节点: {names}")

    sub = db.subgraph(node_ids, hops=hops)
    return {"centers": names, "missing": missing, **sub}


@app.get("/api/graph/label/{label}", tags=["知识图谱"])
async def graph_by_label(label: str, request: Request,
                         limit: int = Query(100, ge=1, le=500)):
    """按标签获取所有节点"""
    from tengod.auth import authorize
    authorize(request, "knowledge:search", consume_quota=False)
    from tengod.graph_engine import get_graph_db
    db = get_graph_db()
    nodes = db.get_nodes_by_label(label)[:limit]
    return {
        "label": label,
        "total": len(nodes),
        "nodes": [n.to_dict() for n in nodes],
    }


@app.get("/api/graph/match", tags=["知识图谱"])
async def graph_match(request: Request,
                      label: str = Query(None, description="节点标签"),
                      relation: str = Query(None, description="关系类型"),
                      target_label: str = Query(None, description="目标节点标签"),
                      limit: int = Query(50, ge=1, le=200)):
    """模式匹配查询"""
    from tengod.auth import authorize
    authorize(request, "knowledge:search")
    from tengod.graph_engine import get_graph_db
    db = get_graph_db()

    if relation:
        # 关系匹配
        edges = db.match_relation(source_label=label, relation=relation,
                                  target_label=target_label, limit=limit)
        return {
            "query": {"label": label, "relation": relation, "target_label": target_label},
            "total": len(edges),
            "edges": [e.to_dict() for e in edges],
            "nodes": [
                {"source": db.get_node(e.source).to_dict() if db.get_node(e.source) else None,
                 "target": db.get_node(e.target).to_dict() if db.get_node(e.target) else None}
                for e in edges
            ],
        }
    else:
        # 节点匹配
        nodes = db.match_pattern(label=label, limit=limit)
        return {
            "query": {"label": label},
            "total": len(nodes),
            "nodes": [n.to_dict() for n in nodes],
        }


@app.get("/api/graph/export", tags=["知识图谱"])
async def graph_export(request: Request,
                       labels: str = Query(None, description="标签过滤（逗号分隔）"),
                       limit: int = Query(300, ge=1, le=1000)):
    """导出图谱数据（前端可视化用）"""
    from tengod.auth import authorize
    authorize(request, "knowledge:search", consume_quota=False)
    from tengod.graph_engine import get_graph_db
    db = get_graph_db()

    if labels:
        label_list = [l.strip() for l in labels.split(",") if l.strip()]
        return db.export_subgraph_by_label(label_list, max_nodes=limit)
    else:
        return db.export_graph(limit=limit)


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