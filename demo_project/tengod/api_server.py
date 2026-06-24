#!/usr/bin/env python3
"""
api_server.py — 十神架构 · REST API 服务 v2.10.0

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
  
  v2.2 新增端点:
  /api/v2/solar-time   — 真太阳时计算
  /api/v2/jieqi        — 节气查询
  /api/v2/wuxing/strength — 五行旺衰量化
  /api/v2/chart/bazi   — 八字命盘 HTML 可视化
  /api/v2/ai/analyze   — Deepseek AI 智能分析
  /api/v2/ai/stream    — AI 流式响应
        
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
import threading
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
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse, Response
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
## 中华文明数字永生体 · REST API v2.2

提供八字排盘、神煞推算、格局判断、喜用神分析、调候分析、
语义搜索、知识关联推荐、真太阳时、五行旺衰、AI 智能分析等全部能力。

### 功能分组
- **/api/bazi/*** — 八字排盘与命理分析
- **/api/knowledge/*** — 知识查询与语义搜索
- **/api/v2/** — v2.2 新增：真太阳时、节气、五行旺衰、命盘可视化、Deepseek AI
- **/api/health** — 服务健康检查

### 鉴权
通过 `X-API-Key` 请求头传递 API Key（若启动时启用了鉴权）。
""",
    version="2.2.0",
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

# Gzip 压缩（移动端流量优化 v2.3）
app.add_middleware(GZipMiddleware, minimum_size=1024)

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

# 阶段十九：PWA Web 控制台挂载
_web_console_dir = os.path.join(os.path.dirname(__file__), "..", "web_console")
if os.path.isdir(_web_console_dir):
    app.mount("/app", StaticFiles(directory=_web_console_dir, html=True), name="web_console")


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
    # 阶段十九：优先重定向到 PWA 控制台
    _web_console_dir = os.path.join(os.path.dirname(__file__), "..", "web_console")
    if os.path.isdir(_web_console_dir):
        return RedirectResponse(url="/app/index.html")
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
        gen = BaziReportGenerator(analyzer, lang=getattr(query, 'lang', 'zh-CN'))

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
# 阶段十八：命例案例库 API 端点
# ============================================================================

class CaseCreateRequest(BaseModel):
    """创建案例请求"""
    record_id: int = Field(..., description="关联的八字记录ID")
    title: str = Field(..., min_length=1, max_length=256, description="案例标题")
    category: Optional[str] = Field(default=None, description="案例分类")
    source: Optional[str] = Field(default=None, description="案例来源")
    credibility: float = Field(default=0.8, ge=0, le=1, description="可信度")
    is_public: bool = Field(default=True, description="是否公开")
    is_featured: bool = Field(default=False, description="是否精选")
    summary: Optional[str] = Field(default=None, description="案例摘要")
    analysis_text: Optional[str] = Field(default=None, description="详细分析")
    conclusion: Optional[str] = Field(default=None, description="结论")
    tags: Optional[List[str]] = Field(default=None, description="标签列表")


class CaseUpdateRequest(BaseModel):
    """更新案例请求"""
    title: Optional[str] = Field(default=None, max_length=256)
    category: Optional[str] = None
    source: Optional[str] = None
    credibility: Optional[float] = Field(default=None, ge=0, le=1)
    is_public: Optional[bool] = None
    is_featured: Optional[bool] = None
    summary: Optional[str] = None
    analysis_text: Optional[str] = None
    conclusion: Optional[str] = None
    tags: Optional[List[str]] = None


class CaseSearchRequest(BaseModel):
    """案例搜索请求"""
    keyword: Optional[str] = None
    category: Optional[str] = None
    tag: Optional[str] = None
    day_master: Optional[str] = None
    geju: Optional[str] = None
    gender: Optional[str] = None
    source: Optional[str] = None
    is_public: Optional[bool] = None
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)


class CaseLinkRequest(BaseModel):
    """案例关联请求"""
    case_b_id: int = Field(..., description="目标案例ID")
    relation_type: str = Field(default="similar", description="关联类型")
    similarity_score: float = Field(default=0.0, ge=0, le=1)
    note: Optional[str] = None


# ─── 阶段二十：Webhook 请求模型 ──────────────────────────

class WebhookSubscribeRequest(BaseModel):
    """Webhook 订阅请求"""
    url: str = Field(..., min_length=1, max_length=512, description="回调 URL")
    events: List[str] = Field(..., min_length=1, description="订阅事件列表，支持 * 通配")
    secret: Optional[str] = Field(default="", max_length=256, description="HMAC 签名密钥")
    description: Optional[str] = Field(default="", max_length=256)


class WebhookUpdateRequest(BaseModel):
    """Webhook 更新请求"""
    url: Optional[str] = Field(default=None, max_length=512)
    events: Optional[List[str]] = None
    secret: Optional[str] = None
    is_active: Optional[bool] = None
    description: Optional[str] = None


class WebhookTriggerRequest(BaseModel):
    """Webhook 手动触发（管理员）"""
    event_type: str = Field(..., max_length=64)
    payload: dict = Field(default_factory=dict)


@app.post("/api/cases", tags=["命例案例库"])
async def create_case(req: CaseCreateRequest, request: Request):
    """创建命例案例"""
    from tengod.auth import authorize
    authorize(request, "case:write")
    from tengod.case_library import get_case_library
    try:
        lib = get_case_library()
        case_id = lib.create_case(
            record_id=req.record_id,
            title=req.title,
            category=req.category,
            source=req.source,
            credibility=req.credibility,
            is_public=req.is_public,
            is_featured=req.is_featured,
            summary=req.summary,
            analysis_text=req.analysis_text,
            conclusion=req.conclusion,
            tags=req.tags,
        )
        return {"id": case_id, "created": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建案例失败: {e}")


@app.get("/api/cases", tags=["命例案例库"])
async def list_cases(
    request: Request,
    category: Optional[str] = Query(None),
    is_public: Optional[bool] = Query(None),
    is_featured: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    order_by: str = Query("created_desc", description="created_desc/created_asc/views/favorites"),
):
    """列出命例案例"""
    from tengod.auth import authorize
    authorize(request, "case:read", consume_quota=False)
    from tengod.case_library import get_case_library
    lib = get_case_library()
    return lib.list_cases(
        category=category, is_public=is_public, is_featured=is_featured,
        limit=limit, offset=offset, order_by=order_by,
    )


@app.get("/api/cases/{case_id}", tags=["命例案例库"])
async def get_case(case_id: int, request: Request):
    """获取案例详情（自动增加浏览数）"""
    from tengod.auth import authorize
    authorize(request, "case:read", consume_quota=False)
    from tengod.case_library import get_case_library
    lib = get_case_library()
    case = lib.get_case(case_id, increment_view=True)
    if case is None:
        raise HTTPException(status_code=404, detail="案例不存在")
    return case


@app.put("/api/cases/{case_id}", tags=["命例案例库"])
async def update_case(case_id: int, req: CaseUpdateRequest, request: Request):
    """更新案例"""
    from tengod.auth import authorize
    authorize(request, "case:write")
    from tengod.case_library import get_case_library
    lib = get_case_library()
    kwargs = {k: v for k, v in req.model_dump().items() if v is not None}
    if not kwargs:
        raise HTTPException(status_code=400, detail="未提供更新字段")
    success = lib.update_case(case_id, **kwargs)
    if not success:
        raise HTTPException(status_code=404, detail="案例不存在")
    return {"id": case_id, "updated": True}


@app.delete("/api/cases/{case_id}", tags=["命例案例库"])
async def delete_case(case_id: int, request: Request):
    """删除案例"""
    from tengod.auth import authorize
    authorize(request, "case:delete")
    from tengod.case_library import get_case_library
    lib = get_case_library()
    success = lib.delete_case(case_id)
    if not success:
        raise HTTPException(status_code=404, detail="案例不存在")
    return {"id": case_id, "deleted": True}


@app.post("/api/cases/search", tags=["命例案例库"])
async def search_cases(req: CaseSearchRequest, request: Request):
    """多维度搜索案例"""
    from tengod.auth import authorize
    authorize(request, "case:read", consume_quota=False)
    from tengod.case_library import get_case_library
    lib = get_case_library()
    return lib.search_cases(
        keyword=req.keyword, category=req.category, tag=req.tag,
        day_master=req.day_master, geju=req.geju, gender=req.gender,
        source=req.source, is_public=req.is_public,
        limit=req.limit, offset=req.offset,
    )


@app.get("/api/cases/categories/list", tags=["命例案例库"])
async def list_case_categories(request: Request):
    """列出所有案例分类"""
    from tengod.auth import authorize
    authorize(request, "case:read", consume_quota=False)
    from tengod.case_library import get_case_library, DEFAULT_CATEGORIES
    lib = get_case_library()
    used = lib.list_categories()
    # 合并预定义分类和已使用分类
    all_cats = []
    for name in DEFAULT_CATEGORIES:
        count = next((c["count"] for c in used if c["name"] == name), 0)
        all_cats.append({"name": name, "count": count})
    # 添加非预定义的分类
    for c in used:
        if c["name"] not in {cat["name"] for cat in all_cats}:
            all_cats.append(c)
    return {"categories": all_cats}


@app.get("/api/cases/tags/list", tags=["命例案例库"])
async def list_case_tags(request: Request):
    """列出所有案例标签"""
    from tengod.auth import authorize
    authorize(request, "case:read", consume_quota=False)
    from tengod.case_library import get_case_library
    lib = get_case_library()
    return {"tags": lib.list_tags()}


@app.get("/api/cases/stats/summary", tags=["命例案例库"])
async def case_stats(request: Request):
    """案例库统计"""
    from tengod.auth import authorize
    authorize(request, "case:read", consume_quota=False)
    from tengod.case_library import get_case_library
    lib = get_case_library()
    return lib.stats()


@app.get("/api/cases/export/all", tags=["命例案例库"])
async def export_cases(
    request: Request,
    format: str = Query("json", description="导出格式: json/csv"),
):
    """导出案例"""
    from tengod.auth import authorize
    authorize(request, "case:read", consume_quota=False)
    from tengod.case_library import get_case_library
    lib = get_case_library()
    content = lib.export_cases(format=format)
    if format == "csv":
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(
            content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=cases.csv"},
        )
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(
        content,
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=cases.json"},
    )


@app.post("/api/cases/import/batch", tags=["命例案例库"])
async def import_cases(
    request: Request,
    format: str = Query("json", description="导入格式: json"),
):
    """导入案例（请求体为导入内容）"""
    from tengod.auth import authorize
    authorize(request, "case:write")
    from tengod.case_library import get_case_library
    body = await request.body()
    data = body.decode("utf-8")
    lib = get_case_library()
    result = lib.import_cases(data, format=format)
    return result


@app.get("/api/cases/{case_id}/similar", tags=["命例案例库"])
async def get_similar_cases(
    case_id: int, request: Request,
    limit: int = Query(5, ge=1, le=20),
):
    """获取相似案例推荐"""
    from tengod.auth import authorize
    authorize(request, "case:read", consume_quota=False)
    from tengod.case_library import get_case_library
    lib = get_case_library()
    similar = lib.find_similar_cases(case_id, limit=limit)
    return {"case_id": case_id, "similar_cases": similar}


@app.post("/api/cases/{case_id}/links", tags=["命例案例库"])
async def link_cases(case_id: int, req: CaseLinkRequest, request: Request):
    """建立案例关联"""
    from tengod.auth import authorize
    authorize(request, "case:write")
    from tengod.case_library import get_case_library
    lib = get_case_library()
    try:
        rel_id = lib.link_cases(
            case_a_id=case_id,
            case_b_id=req.case_b_id,
            relation_type=req.relation_type,
            similarity_score=req.similarity_score,
            note=req.note,
        )
        return {"id": rel_id, "linked": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/cases/{case_id}/links", tags=["命例案例库"])
async def get_case_links(
    case_id: int, request: Request,
    relation_type: Optional[str] = Query(None),
):
    """获取案例关联"""
    from tengod.auth import authorize
    authorize(request, "case:read", consume_quota=False)
    from tengod.case_library import get_case_library
    lib = get_case_library()
    return {"case_id": case_id, "relations": lib.get_relations(case_id, relation_type)}


@app.post("/api/cases/{case_id}/favorite", tags=["命例案例库"])
async def favorite_case(case_id: int, request: Request):
    """收藏案例"""
    from tengod.auth import authorize
    authorize(request, "case:read")
    from tengod.case_library import get_case_library
    lib = get_case_library()
    count = lib.toggle_favorite(case_id)
    if count is None:
        raise HTTPException(status_code=404, detail="案例不存在")
    return {"id": case_id, "favorite_count": count}


@app.post("/api/cases/{case_id}/like", tags=["命例案例库"])
async def like_case(case_id: int, request: Request):
    """点赞案例"""
    from tengod.auth import authorize
    authorize(request, "case:read")
    from tengod.case_library import get_case_library
    lib = get_case_library()
    count = lib.toggle_like(case_id)
    if count is None:
        raise HTTPException(status_code=404, detail="案例不存在")
    return {"id": case_id, "like_count": count}


# ============================================================================
# 阶段二十 20.1：开放 API — Webhook 与插件系统
# ============================================================================

@app.get("/api/webhooks/events", tags=["Webhook"])
async def list_webhook_events(request: Request):
    """列出所有可用的事件类型"""
    from tengod.auth import authorize
    authorize(request, "webhook:read")
    from tengod.webhook import EVENT_TYPES
    return {"events": [{"type": k, "description": v} for k, v in EVENT_TYPES.items()]}


@app.post("/api/webhooks", tags=["Webhook"])
async def create_webhook(req: WebhookSubscribeRequest, request: Request):
    """创建 Webhook 订阅"""
    from tengod.auth import authorize
    authorize(request, "webhook:write")
    from tengod.webhook import get_webhook_manager
    wh = get_webhook_manager()
    return wh.subscribe(url=req.url, events=req.events, secret=req.secret or "", description=req.description or "")


@app.get("/api/webhooks", tags=["Webhook"])
async def list_webhooks(request: Request, active_only: bool = False):
    """列出 Webhook 订阅"""
    from tengod.auth import authorize
    authorize(request, "webhook:read")
    from tengod.webhook import get_webhook_manager
    wh = get_webhook_manager()
    return {"subscriptions": wh.list_subscriptions(active_only=active_only)}


@app.get("/api/webhooks/{sub_id}", tags=["Webhook"])
async def get_webhook(sub_id: int, request: Request):
    """获取 Webhook 订阅详情"""
    from tengod.auth import authorize
    authorize(request, "webhook:read")
    from tengod.webhook import get_webhook_manager
    wh = get_webhook_manager()
    sub = wh.get_subscription(sub_id)
    if not sub:
        raise HTTPException(status_code=404, detail="订阅不存在")
    return sub


@app.put("/api/webhooks/{sub_id}", tags=["Webhook"])
async def update_webhook(sub_id: int, req: WebhookUpdateRequest, request: Request):
    """更新 Webhook 订阅"""
    from tengod.auth import authorize
    authorize(request, "webhook:write")
    from tengod.webhook import get_webhook_manager
    wh = get_webhook_manager()
    sub = wh.update_subscription(
        sub_id,
        url=req.url,
        events=req.events,
        secret=req.secret,
        is_active=req.is_active,
        description=req.description,
    )
    if not sub:
        raise HTTPException(status_code=404, detail="订阅不存在")
    return sub


@app.delete("/api/webhooks/{sub_id}", tags=["Webhook"])
async def delete_webhook(sub_id: int, request: Request):
    """取消 Webhook 订阅"""
    from tengod.auth import authorize
    authorize(request, "webhook:delete")
    from tengod.webhook import get_webhook_manager
    wh = get_webhook_manager()
    ok = wh.unsubscribe(sub_id)
    if not ok:
        raise HTTPException(status_code=404, detail="订阅不存在")
    return {"deleted": True, "id": sub_id}


@app.post("/api/webhooks/{sub_id}/test", tags=["Webhook"])
async def test_webhook(sub_id: int, request: Request):
    """发送测试事件到 Webhook"""
    from tengod.auth import authorize
    authorize(request, "webhook:write")
    from tengod.webhook import get_webhook_manager
    wh = get_webhook_manager()
    result = wh.test_subscription(sub_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@app.get("/api/webhooks/{sub_id}/deliveries", tags=["Webhook"])
async def list_webhook_deliveries(sub_id: int, request: Request, limit: int = 50):
    """列出 Webhook 交付记录"""
    from tengod.auth import authorize
    authorize(request, "webhook:read")
    from tengod.webhook import get_webhook_manager
    wh = get_webhook_manager()
    return {"deliveries": wh.list_deliveries(sub_id=sub_id, limit=limit)}


@app.post("/api/webhooks/trigger", tags=["Webhook"])
async def trigger_webhook(req: WebhookTriggerRequest, request: Request):
    """手动触发事件（管理员）"""
    from tengod.auth import authorize
    authorize(request, "webhook:write")
    from tengod.webhook import get_webhook_manager
    wh = get_webhook_manager()
    count = wh.trigger(req.event_type, req.payload)
    return {"triggered": count, "event_type": req.event_type}


@app.get("/api/webhooks/stats/summary", tags=["Webhook"])
async def webhook_stats(request: Request):
    """Webhook 统计"""
    from tengod.auth import authorize
    authorize(request, "webhook:read")
    from tengod.webhook import get_webhook_manager
    wh = get_webhook_manager()
    return wh.stats()


# ─── 插件系统 API ────────────────────────────────────────

@app.get("/api/plugins", tags=["插件系统"])
async def list_plugins(request: Request, state: Optional[str] = None):
    """列出插件"""
    from tengod.auth import authorize
    authorize(request, "plugin:read")
    from tengod.比肩_架构协同.plugin_manager import PluginManager
    pm = PluginManager()
    pm.discover()
    return {"plugins": pm.list_plugins(state=state)}


@app.get("/api/plugins/stats/summary", tags=["插件系统"])
async def plugin_stats(request: Request):
    """插件统计"""
    from tengod.auth import authorize
    authorize(request, "plugin:read")
    from tengod.比肩_架构协同.plugin_manager import PluginManager
    pm = PluginManager()
    return pm.stats()


# ─── 阶段二十 20.3：高级分析 API ─────────────────────────

class BatchBaziRequest(BaseModel):
    """批量排盘请求"""
    inputs: List[Dict[str, Any]] = Field(..., min_length=1, max_length=100)


class CompareCasesRequest(BaseModel):
    """命例对比请求"""
    record_a_id: int
    record_b_id: int


class TrajectoryRequest(BaseModel):
    """命运轨迹推演请求"""
    year: int = Field(..., ge=1900, le=2100)
    month: int = Field(..., ge=1, le=12)
    day: int = Field(..., ge=1, le=31)
    hour: int = Field(..., ge=0, le=23)
    minute: int = Field(default=0, ge=0, le=59)
    gender: str = Field(default="male")
    start_age: int = Field(default=0, ge=0, le=100)
    end_age: int = Field(default=80, ge=1, le=120)


# ============================================================================
# 阶段二十一：流年/玄空/七政/高级术数 请求模型
# ============================================================================

class LiunianRequest(BaseModel):
    """流年断语请求"""
    pillars: Dict[str, str] = Field(..., description='四柱 {"year":"甲子","month":"丙寅","day":"戊辰","hour":"庚申"}')
    target_year: int = Field(default=2026, ge=1900, le=2200)
    years_range: Optional[List[int]] = Field(default=None, description='批量分析的年份列表')


class FengshuiRequest(BaseModel):
    """玄空飞星请求"""
    sitting: str = Field(default="北", description='坐向：如"北"、"南"、"东"、"西"')
    facing: str = Field(default="南", description='朝向')
    year: int = Field(default=2026, ge=1900, le=2200)
    house_info: Optional[Dict[str, str]] = Field(default=None, description='房屋信息')


class QizhengRequest(BaseModel):
    """七政四余排盘请求"""
    year: int = Field(..., ge=1900, le=2200)
    month: int = Field(..., ge=1, le=12)
    day: int = Field(..., ge=1, le=31)
    hour: int = Field(default=12, ge=0, le=23)
    minute: int = Field(default=0, ge=0, le=59)


class AdvancedShushuRequest(BaseModel):
    """高级术数（铁板神数/邵子神数/称骨算命）请求"""
    pillars: Dict[str, str] = Field(..., description='四柱 {"year":"甲子","month":"丙寅","day":"戊辰","hour":"庚申"}')
    lunar_month: Optional[int] = Field(default=None, ge=1, le=12, description='农历月（称骨用）')
    lunar_day: Optional[int] = Field(default=None, ge=1, le=31, description='农历日（称骨用）')


# ============================================================================
# 阶段二十一：流年/玄空/七政/高级术数 API 端点
# ============================================================================

@app.post("/api/prediction/liunian", tags=["流年断语"])
async def liunian_judgment(req: LiunianRequest, request: Request):
    """单年流年断语与批量运势分析"""
    from tengod.auth import authorize
    authorize(request, "bazi:full")
    from tengod.liunian_judgment import LiunianJudgmentEngine
    engine = LiunianJudgmentEngine()

    if req.years_range and len(req.years_range) > 0:
        return engine.judge(req.pillars, req.years_range)

    result = engine.judge_year(req.pillars, req.target_year)
    if hasattr(result, "to_dict"):
        return result.to_dict()
    if hasattr(result, "__dataclass_fields__"):
        from dataclasses import asdict
        return asdict(result)
    return result


@app.post("/api/prediction/fengshui", tags=["玄空风水"])
async def fengshui_analysis(req: FengshuiRequest, request: Request):
    """玄空飞星排盘与阳宅风水分析"""
    from tengod.auth import authorize
    authorize(request, "bazi:full")
    from tengod.fengshui.xuankong import XuankongEngine, YangzhaiAnalyzer
    engine = XuankongEngine()
    result = engine.compute(sitting=req.sitting, facing=req.facing, year=req.year)

    response = {}
    if hasattr(result, "__dataclass_fields__"):
        from dataclasses import asdict
        response = asdict(result)
    else:
        response = result

    if req.house_info:
        analyzer = YangzhaiAnalyzer()
        analysis = analyzer.analyze(result, req.house_info)
        if isinstance(response, dict):
            response["house_analysis"] = analysis

    return response


@app.post("/api/prediction/qizheng", tags=["七政四余"])
async def qizheng_calc(req: QizhengRequest, request: Request):
    """七政四余星象排盘"""
    from tengod.auth import authorize
    authorize(request, "bazi:full")
    from tengod.qizheng.engine import QizhengEngine
    engine = QizhengEngine()
    result = engine.compute(year=req.year, month=req.month, day=req.day,
                            hour=req.hour, minute=req.minute)
    if hasattr(result, "__dataclass_fields__"):
        from dataclasses import asdict
        return asdict(result)
    return result


# ============================================================================
# 阶段二十二：综合多体系分析
# ============================================================================

class ComprehensiveRequest(BaseModel):
    """综合分析请求（阶段二十五扩展）"""
    birth_year: int = Field(..., ge=1900, le=2100, description="出生年")
    birth_month: int = Field(..., ge=1, le=12, description="出生月")
    birth_day: int = Field(..., ge=1, le=31, description="出生日")
    birth_hour: int = Field(default=12, ge=0, le=23, description="出生时(0-23)")
    birth_minute: int = Field(default=0, ge=0, le=59, description="出生分")
    gender: str = Field(default="male", description="性别: male/female")
    target_year: int = Field(default=2026, ge=1900, le=2200, description="流年分析年份")
    pillars: Optional[Dict[str, str]] = Field(default=None, description="四柱干支(可不填，自动计算)")
    sitting: str = Field(default="北", description="风水坐向-坐")
    facing: str = Field(default="南", description="风水坐向-向")
    lunar_month: Optional[int] = Field(default=None, ge=1, le=12, description="农历月")
    lunar_day: Optional[int] = Field(default=None, ge=1, le=31, description="农历日")
    # 阶段二十五新增
    name_surname: Optional[str] = Field(default=None, max_length=4, description="姓氏（用于姓名学分析，可选）")
    name_given: Optional[str] = Field(default=None, max_length=6, description="名字（用于姓名学分析，可选）")
    partner: Optional[Dict[str, Any]] = Field(default=None, description="对方信息：{name, bazi: {day_master, pillars}}")


@app.post("/api/prediction/comprehensive", tags=["综合分析"])
async def comprehensive_analysis(req: ComprehensiveRequest, request: Request):
    """
    多体系综合分析

    整合8大术数体系：八字、紫微斗数、奇门遁甲、六爻卦、
    流年断语、玄空风水、七政四余、高级术数（铁板/邵子/称骨）

    提供交叉验证、共识判断与综合报告。
    """
    from tengod.auth import authorize
    authorize(request, "bazi:full")
    from tengod.multi_system_engine import ComprehensiveAnalyzer
    analyzer = ComprehensiveAnalyzer()
    result = analyzer.full_analysis(
        birth_date=(req.birth_year, req.birth_month, req.birth_day),
        birth_time=(req.birth_hour, req.birth_minute),
        gender=req.gender,
        target_year=req.target_year,
        pillars=req.pillars,
        sitting=req.sitting,
        facing=req.facing,
        lunar_month=req.lunar_month,
        lunar_day=req.lunar_day,
        name_surname=req.name_surname,
        name_given=req.name_given,
        partner_info=req.partner,
    )
    return result.to_dict()


# ============================================================================
# 阶段二十四：综合报告生成 + AI 解读
# ============================================================================

class ComprehensiveInterpretRequest(BaseModel):
    """综合分析 AI 解读请求"""
    birth_year: int = Field(..., ge=1900, le=2100)
    birth_month: int = Field(..., ge=1, le=12)
    birth_day: int = Field(..., ge=1, le=31)
    birth_hour: int = Field(default=12, ge=0, le=23)
    birth_minute: int = Field(default=0, ge=0, le=59)
    gender: str = Field(default="male")
    target_year: int = Field(default=2026, ge=1900, le=2200)
    pillars: Optional[Dict[str, str]] = Field(default=None)
    sitting: str = Field(default="北")
    facing: str = Field(default="南")
    lunar_month: Optional[int] = Field(default=None, ge=1, le=12)
    lunar_day: Optional[int] = Field(default=None, ge=1, le=31)
    use_rag: bool = Field(default=False)
    question: str = Field(default="")
    report_format: str = Field(default="text",
                               description="报告格式: text/markdown/html/json")
    name_surname: Optional[str] = Field(default=None, description="姓氏（用于姓名学分析）")
    name_given: Optional[str] = Field(default=None, description="名字（用于姓名学分析）")
    partner: Optional[Dict[str, Any]] = Field(default=None, description="对方信息")


@app.post("/api/prediction/comprehensive/interpret", tags=["综合分析"])
async def comprehensive_interpret(req: ComprehensiveInterpretRequest, request: Request):
    """
    多体系综合分析 + AI 智能解读 + 报告生成

    三合一接口：分析 → AI 解读 → 格式化报告一步完成。
    支持 text / markdown / html / json 格式输出。
    """
    from tengod.auth import authorize
    authorize(request, "bazi:full")
    from tengod.multi_system_engine import ComprehensiveAnalyzer
    from tengod.ai_interpreter import interpret_comprehensive
    from tengod.report_generator import ComprehensiveReportGenerator

    # 1. 多体系综合分析
    analyzer = ComprehensiveAnalyzer()
    comp_result = analyzer.full_analysis(
        birth_date=(req.birth_year, req.birth_month, req.birth_day),
        birth_time=(req.birth_hour, req.birth_minute),
        gender=req.gender,
        target_year=req.target_year,
        pillars=req.pillars,
        sitting=req.sitting,
        facing=req.facing,
        lunar_month=req.lunar_month,
        lunar_day=req.lunar_day,
        name_surname=req.name_surname,
        name_given=req.name_given,
        partner_info=req.partner,
    )
    comp_dict = comp_result.to_dict()

    # 2. AI 智能解读
    ai_report = await interpret_comprehensive(
        comp_dict,
        use_rag=req.use_rag,
        question=req.question,
    )

    # 3. 生成格式化报告
    gen = ComprehensiveReportGenerator(comp_dict)
    if req.report_format == "markdown":
        formatted = gen.markdown_report()
    elif req.report_format == "html":
        formatted = gen.html_report()
    elif req.report_format == "json":
        formatted = gen.json_report()
    else:
        formatted = gen.text_report()

    return {
        "ai_interpretation": ai_report,
        "formatted_report": formatted,
        "format": req.report_format,
        "raw_result": comp_dict,
    }


@app.post("/api/prediction/shushu", tags=["高级术数"])
async def advanced_shushu(req: AdvancedShushuRequest, request: Request):
    """铁板神数 / 邵子神数 / 称骨算命 综合分析"""
    from tengod.auth import authorize
    authorize(request, "bazi:full")
    from tengod.advanced_shushu import AdvancedShuShuEngine
    engine = AdvancedShuShuEngine()
    result = engine.compute_all(
        pillars=req.pillars,
        lunar_month=req.lunar_month,
        lunar_day=req.lunar_day,
    )
    return result


@app.post("/api/advanced/compare", tags=["高级分析"])
async def compare_cases(req: CompareCasesRequest, request: Request):
    """命例对比分析"""
    from tengod.auth import authorize
    authorize(request, "bazi:full")
    from tengod.advanced_analysis import AdvancedAnalyzer
    analyzer = AdvancedAnalyzer()
    result = analyzer.compare_cases(req.record_a_id, req.record_b_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@app.post("/api/advanced/batch-bazi", tags=["高级分析"])
async def batch_bazi(req: BatchBaziRequest, request: Request):
    """批量排盘"""
    from tengod.auth import authorize
    authorize(request, "bazi:full")
    from tengod.advanced_analysis import AdvancedAnalyzer
    analyzer = AdvancedAnalyzer()
    return analyzer.batch_bazi(req.inputs)


@app.post("/api/advanced/trajectory", tags=["高级分析"])
async def destiny_trajectory(req: TrajectoryRequest, request: Request):
    """命运轨迹推演"""
    from tengod.auth import authorize
    authorize(request, "bazi:full")
    from tengod.advanced_analysis import AdvancedAnalyzer
    analyzer = AdvancedAnalyzer()
    return analyzer.destiny_trajectory(
        year=req.year, month=req.month, day=req.day, hour=req.hour,
        minute=req.minute, gender=req.gender,
        start_age=req.start_age, end_age=req.end_age,
    )


# ─── API 版本信息 ────────────────────────────────────────

@app.get("/api/version", tags=["系统"])
async def api_version():
    """API 版本信息"""
    return {
        "api_version": "3.0.0",
        "engine_version": _get_data_store().get_version() if hasattr(_get_data_store(), "get_version") else "1.5.0",
        "sdk_versions": {
            "python": "3.0.0",
            "javascript": "3.0.0",
            "go": "1.0.0",
        },
        "pwa_version": "3.0.0",
        "features": [
            "bazi_analysis", "case_library", "knowledge_graph", "oracle",
            "ai_interpreter", "pwa", "webhook", "plugins", "rbac",
        ],
    }


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
async def list_users_admin(request: Request):
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
        label_list = [label.strip() for label in labels.split(",") if label.strip()]
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
# v2.2 新增端点：真太阳时、节气、五行旺衰、命盘可视化、Deepseek AI
# ============================================================================

# ─── v2.2 请求模型 ─────────────────────────────────────────────────────────

class SolarTimeRequest(BaseModel):
    """真太阳时计算请求"""
    year: int = Field(..., ge=1900, le=2100, description="年")
    month: int = Field(..., ge=1, le=12, description="月")
    day: int = Field(..., ge=1, le=31, description="日")
    hour: int = Field(default=12, ge=0, le=23, description="时")
    minute: int = Field(default=0, ge=0, le=59, description="分")
    longitude: float = Field(default=120.0, description="经度")


class JieqiRequest(BaseModel):
    """节气查询请求"""
    year: int = Field(..., ge=1900, le=2100, description="年")
    month: int = Field(..., ge=1, le=12, description="月")
    day: int = Field(..., ge=1, le=31, description="日")


class WuxingStrengthRequest(BaseModel):
    """五行旺衰查询请求"""
    month: int = Field(..., ge=1, le=12, description="月份")
    element: Optional[str] = Field(default=None, description="指定五行: 木/火/土/金/水")


class ChartBaziRequest(BaseModel):
    """命盘可视化请求"""
    bazi: BaziInput = Field(..., description="八字输入")
    theme: str = Field(default="classic", description="主题: classic/modern/minimal")
    format: str = Field(default="html", description="输出格式: html/json")


class AIAnalyzeRequest(BaseModel):
    """AI 智能分析请求"""
    bazi: BaziInput = Field(..., description="八字输入")
    analysis_type: str = Field(default="basic", description="分析类型: basic/career/year/marriage/full")
    focus: str = Field(default="综合", description="分析焦点")
    target_year: Optional[int] = Field(default=None, ge=1900, le=2200, description="流年分析年份")
    age: Optional[int] = Field(default=None, ge=0, le=120, description="事业分析年龄")
    partner_bazi: Optional[BaziInput] = Field(default=None, description="合婚对方八字")


class AIStreamRequest(BaseModel):
    """AI 流式分析请求"""
    bazi: BaziInput = Field(..., description="八字输入")
    question: str = Field(default="", description="用户问题")
    analysis_type: str = Field(default="basic", description="分析类型")


# ─── v2.2 API 端点 ─────────────────────────────────────────────────────────

@app.post("/api/v2/solar-time", tags=["v2.2 真太阳时"])
async def v2_solar_time(req: SolarTimeRequest, request: Request):
    """真太阳时计算：经度修正 + 均时差 + 时辰映射"""
    from tengod.auth import authorize
    authorize(request, "bazi:calc")
    try:
        from tengod.solar_time import SolarTimeCalculator
        from datetime import datetime
        calc = SolarTimeCalculator(longitude=req.longitude)
        local = datetime(req.year, req.month, req.day, req.hour, req.minute)
        result = calc.calculate(local)
        shichen = calc.get_shichen(result.true_hour)
        return {
            "input": {"datetime": f"{req.year}-{req.month:02d}-{req.day:02d} {req.hour:02d}:{req.minute:02d}",
                      "longitude": req.longitude},
            "solar_time": f"{result.true_hour:02d}:{result.true_minute:02d}",
            "time_correction_minutes": round(result.time_correction, 2),
            "shichen": shichen,
            "shichen_range": {"start": calc.get_shichen_range(shichen)[0],
                              "end": calc.get_shichen_range(shichen)[1]},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"真太阳时计算失败: {e}")


@app.post("/api/v2/jieqi", tags=["v2.2 节气"])
async def v2_jieqi(req: JieqiRequest, request: Request):
    """节气查询：当前节气 + 下一节气 + 节气日判断"""
    from tengod.auth import authorize
    authorize(request, "bazi:calc", consume_quota=False)
    try:
        from tengod.solar_time import JieqiCalculator
        calc = JieqiCalculator()
        info = calc.get_jieqi(req.year, req.month, req.day)
        is_jieqi = calc.is_jieqi_day(req.month, req.day)
        return {
            "date": f"{req.year}-{req.month:02d}-{req.day:02d}",
            "current_jieqi": info.get("current"),
            "next_jieqi": info.get("next"),
            "is_jieqi_day": is_jieqi,
            "month": info.get("month"),
            "day": info.get("day"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"节气查询失败: {e}")


@app.post("/api/v2/wuxing/strength", tags=["v2.2 五行旺衰"])
async def v2_wuxing_strength(req: WuxingStrengthRequest, request: Request):
    """五行旺衰量化：旺/相/休/囚/死 五级量化"""
    from tengod.auth import authorize
    authorize(request, "bazi:calc", consume_quota=False)
    try:
        from tengod.solar_time import WuxingStrengthCalculator
        calc = WuxingStrengthCalculator()
        if req.element:
            result = calc.calculate_strength(req.element, req.month)
            return {
                "month": req.month,
                "season": calc.get_season(req.month),
                "element": req.element,
                "status": result["status"],
                "strength": result["strength"],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        all_strengths = calc.calculate_all(req.month)
        return {
            "month": req.month,
            "season": calc.get_season(req.month),
            "strengths": all_strengths,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"五行旺衰计算失败: {e}")


@app.post("/api/v2/chart/bazi", tags=["v2.2 命盘可视化"])
async def v2_chart_bazi(req: ChartBaziRequest, request: Request):
    """八字命盘可视化：生成交互式 HTML 命盘或 JSON 数据"""
    from tengod.auth import authorize
    authorize(request, "bazi:calc")
    try:
        from tengod.chart_visualizer import BaziChartVisualizer, VisualizationConfig, visualize_bazi
        from tengod.bazi_analyzer import BaziAnalyzer
        from tengod.shensha_engine import calc_all_shensha
        from tengod.geju_engine import calc_geju

        is_male = req.bazi.gender == "male"
        analyzer = BaziAnalyzer(req.bazi.year, req.bazi.month, req.bazi.day,
                                req.bazi.hour, req.bazi.minute, is_male=is_male,
                                longitude=req.bazi.longitude, latitude=req.bazi.latitude)
        a = analyzer.analysis
        pillars = a["pillars"]

        # 统计五行
        wuxing_count = {"木": 0, "火": 0, "土": 0, "金": 0, "水": 0}
        wuxing_map = {'甲': '木', '乙': '木', '丙': '火', '丁': '火',
                       '戊': '土', '己': '土', '庚': '金', '辛': '金',
                       '壬': '水', '癸': '水'}
        for pillar in pillars.values():
            for char in pillar:
                if char in wuxing_map:
                    wuxing_count[wuxing_map[char]] += 1

        # 神煞
        shensha_result = calc_all_shensha(pillars)
        shensha_names = [v["name"] for v in shensha_result.all_shensha.values()][:10]

        geju_result = calc_geju(pillars)

        chart_data = {
            "pillars": pillars,
            "wuxing": wuxing_count,
            "geju": geju_result.geju_name,
            "shensha": shensha_names,
        }

        if req.format == "json":
            viz = BaziChartVisualizer()
            return {"json": json.loads(viz.generate_json(chart_data)),
                    "timestamp": datetime.now(timezone.utc).isoformat()}

        cfg = VisualizationConfig(theme=req.theme)
        viz = BaziChartVisualizer(cfg)
        html = viz.generate_html(chart_data)
        return HTMLResponse(content=html)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"命盘可视化生成失败: {e}")


@app.post("/api/v2/ai/analyze", tags=["v2.2 AI 分析"])
async def v2_ai_analyze(req: AIAnalyzeRequest, request: Request):
    """Deepseek AI 智能命理分析：八字解读/流年/合婚/事业/综合"""
    from tengod.auth import authorize
    authorize(request, "ai:interpret")
    from tengod.metrics_collector import metrics
    metrics.record_ai_chat()
    try:
        from tengod.intelligent_analysis import IntelligentAnalysisEngine, get_engine
        from tengod.bazi_analyzer import BaziAnalyzer
        from tengod.shensha_engine import calc_all_shensha
        from tengod.geju_engine import calc_geju

        is_male = req.bazi.gender == "male"
        analyzer = BaziAnalyzer(req.bazi.year, req.bazi.month, req.bazi.day,
                                req.bazi.hour, req.bazi.minute, is_male=is_male,
                                longitude=req.bazi.longitude, latitude=req.bazi.latitude)
        a = analyzer.analysis
        pillars = a["pillars"]

        wuxing_count = {"木": 0, "火": 0, "土": 0, "金": 0, "水": 0}
        wuxing_map = {'甲': '木', '乙': '木', '丙': '火', '丁': '火',
                       '戊': '土', '己': '土', '庚': '金', '辛': '金',
                       '壬': '水', '癸': '水'}
        for pillar in pillars.values():
            for char in pillar:
                if char in wuxing_map:
                    wuxing_count[wuxing_map[char]] += 1

        shensha_result = calc_all_shensha(pillars)
        shensha_names = [v["name"] for v in shensha_result.all_shensha.values()][:10]
        geju_result = calc_geju(pillars)

        bazi_data = {
            "pillars": pillars,
            "wuxing": wuxing_count,
            "geju": geju_result.geju_name,
            "shensha": shensha_names,
        }

        engine = get_engine()
        options = {}

        if req.analysis_type in ("career", "full"):
            options["career"] = True
            options["age"] = req.age or 30
        if req.analysis_type in ("year", "full"):
            options["year"] = req.target_year or 2026
        if req.analysis_type == "marriage" and req.partner_bazi:
            from tengod.bazi_analyzer import BaziAnalyzer as BA2
            p = req.partner_bazi
            partner_analyzer = BA2(p.year, p.month, p.day, p.hour, p.minute,
                                   is_male=(p.gender != req.bazi.gender),
                                   longitude=p.longitude, latitude=p.latitude)
            partner_pillars = partner_analyzer.analysis["pillars"]
            options["marriage"] = True
            options["partner_bazi"] = {"pillars": partner_pillars}

        result = await engine.full_analysis(bazi_data, options=options)

        response = {
            "analysis_type": req.analysis_type,
            "focus": req.focus,
            "results": {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        for key, val in result.items():
            if hasattr(val, "__dict__"):
                response["results"][key] = {
                    "title": val.title,
                    "content": val.content if len(val.content) < 500 else val.content[:500] + "...",
                    "score": val.score,
                    "tags": val.tags,
                    "recommendations": val.recommendations[:3],
                }
            else:
                response["results"][key] = str(val)[:500]

        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 智能分析失败: {e}")


@app.post("/api/v2/ai/stream", tags=["v2.2 AI 分析"])
async def v2_ai_stream(req: AIStreamRequest, request: Request):
    """Deepseek AI 流式分析：SSE 实时推送分析结果"""
    from tengod.auth import authorize
    authorize(request, "ai:interpret:stream")
    from tengod.metrics_collector import metrics
    metrics.record_ai_chat()
    try:
        from tengod.deepseek_adapter import DeepseekClient, DeepseekConfig, Message, BAZI_SYSTEM_PROMPT
        from tengod.bazi_analyzer import BaziAnalyzer
        from tengod.shensha_engine import calc_all_shensha
        from tengod.geju_engine import calc_geju
        from fastapi.responses import StreamingResponse

        is_male = req.bazi.gender == "male"
        analyzer = BaziAnalyzer(req.bazi.year, req.bazi.month, req.bazi.day,
                                req.bazi.hour, req.bazi.minute, is_male=is_male,
                                longitude=req.bazi.longitude, latitude=req.bazi.latitude)
        a = analyzer.analysis
        pillars = a["pillars"]

        shensha_result = calc_all_shensha(pillars)
        shensha_names = [v["name"] for v in shensha_result.all_shensha.values()][:10]
        geju_result = calc_geju(pillars)

        context = (
            f"八字：年柱{pillars['year']} 月柱{pillars['month']} 日柱{pillars['day']} 时柱{pillars['hour']}\n"
            f"日主：{a['day_master']}\n"
            f"格局：{geju_result.geju_name}\n"
            f"神煞：{','.join(shensha_names)}\n"
            f"五行：{a.get('wuxing', '')}\n"
            f"问题：{req.question or '请综合分析此命盘'}"
        )

        api_key = os.environ.get("DEEPSEEK_API_KEY", "")
        if not api_key:
            raise HTTPException(status_code=503, detail="DEEPSEEK_API_KEY 未配置")

        async def generate():
            client = DeepseekClient(DeepseekConfig(api_key=api_key))
            try:
                async for chunk in client.stream_chat(
                    [Message(role="user", content=context)],
                    system_prompt=BAZI_SYSTEM_PROMPT[:500],
                ):
                    yield f"data: {json.dumps({'chunk': chunk}, ensure_ascii=False)}\n\n"
                yield "data: [DONE]\n\n"
            finally:
                await client.close()

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={"X-Backend": "deepseek-chat", "X-API-Version": "2.2.0"},
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 流式分析失败: {e}")


# ============================================================================
# v2.3 新增：国际化端点
# ============================================================================

@app.get("/api/v2/i18n/languages", tags=["v2.3 国际化"])
async def v2_i18n_languages(request: Request):
    """获取可用语言列表"""
    from tengod.auth import authorize
    authorize(request, "public", consume_quota=False)
    from tengod.i18n import get_i18n_engine
    engine = get_i18n_engine()
    return {"languages": engine.get_available_langs(), "default": "zh-CN"}


@app.post("/api/v2/i18n/translate", tags=["v2.3 国际化"])
async def v2_i18n_translate(request: Request):
    """批量翻译接口：传入文本数组和目标语言，返回翻译结果"""
    from tengod.auth import authorize
    authorize(request, "public", consume_quota=False)
    try:
        body = await request.json()
        texts = body.get("texts", [])
        lang = body.get("lang", "en")
        from tengod.i18n import get_i18n_engine
        engine = get_i18n_engine()
        result = {text: engine.translate(text, lang) for text in texts}
        return {"lang": lang, "translations": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# v2.3 新增：移动端轻量端点 + 分页
# ============================================================================

@app.get("/api/v2/mobile/bazi/quick", tags=["v2.3 移动端"])
async def v2_mobile_bazi_quick(
    request: Request,
    year: int, month: int, day: int, hour: int,
    minute: int = 0, gender: str = "male",
    longitude: float = 116.4, latitude: float = 39.9,
    lang: str = "zh-CN",
):
    """移动端轻量八字排盘：只返回核心数据，减少 payload"""
    from tengod.auth import authorize
    authorize(request, "bazi:calc")
    try:
        from tengod.bazi_analyzer import BaziAnalyzer
        is_male = gender == "male"
        analyzer = BaziAnalyzer(year, month, day, hour, minute,
                                is_male=is_male, longitude=longitude, latitude=latitude)
        a = analyzer.analysis
        pillars = a["pillars"]

        # 统计五行
        wuxing_count = {"木": 0, "火": 0, "土": 0, "金": 0, "水": 0}
        wuxing_map = {'甲': '木', '乙': '木', '丙': '火', '丁': '火',
                       '戊': '土', '己': '土', '庚': '金', '辛': '金',
                       '壬': '水', '癸': '水'}
        for pillar in pillars.values():
            for char in pillar:
                if char in wuxing_map:
                    wuxing_count[wuxing_map[char]] += 1

        # 翻译
        result = {
            "p": pillars,
            "d": a["day_master"],
            "w": wuxing_count,
            "t": a.get("total_score", 0),
        }

        if lang != "zh-CN":
            from tengod.i18n import translate_bazi, translate_wuxing
            result["p"] = translate_bazi(pillars, lang=lang)
            result["w"] = translate_wuxing(wuxing_count, lang=lang)

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v2/knowledge/list", tags=["v2.3 移动端"])
async def v2_knowledge_list(
    request: Request,
    page: int = 1,
    page_size: int = 20,
    category: Optional[str] = None,
    lang: str = "zh-CN",
):
    """知识图谱列表：支持分页、分类过滤、多语言"""
    from tengod.auth import authorize
    authorize(request, "knowledge:read", consume_quota=False)
    try:
        from tengod.graph_engine import get_graph_db
        graph_db = get_graph_db()
        nodes = list(graph_db._nodes.values())

        # 分类过滤
        if category:
            nodes = [n for n in nodes if n.label == category]

        total = len(nodes)
        start = (page - 1) * page_size
        end = start + page_size
        page_nodes = nodes[start:end]

        # 翻译
        if lang != "zh-CN":
            from tengod.i18n import t as ti18n
            result_nodes = []
            for n in page_nodes:
                d = n.to_dict()
                d["name"] = ti18n(d["name"], lang)
                result_nodes.append(d)
        else:
            result_nodes = [n.to_dict() for n in page_nodes]

        return {
            "items": result_nodes,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# v2.7: 六爻卦象 API
# ============================================================================

from pydantic import BaseModel, Field

class LiuyaoCastRequest(BaseModel):
    date: Optional[str] = Field(None, description="日期 (YYYY-MM-DD)，默认今天")
    question: Optional[str] = Field(None, description="所问之事")
    method: str = Field("random", description="起卦方式: random(随机) / manual(手动)")

class LiuyaoCastResponse(BaseModel):
    ben_gua_name: str
    bian_gua_name: str = ""
    hu_gua_name: str = ""
    shang_gua: str = ""
    xia_gua: str = ""
    gua_gong: str = ""
    yaos: List[Dict[str, Any]] = []
    overall_judgment: str = ""
    day_ganzhi: str = ""


@app.post("/api/liuyao/cast", response_model=LiuyaoCastResponse, tags=["v2.7 六爻"])
async def cast_liuyao(request: LiuyaoCastRequest):
    """六爻起卦"""
    try:
        from tengod.liuyao_engine import LiuyaoEngine
        engine = LiuyaoEngine()
        result = engine.calc_gua(day_ganzhi=request.date)
        yaos = [
            {
                "position": y.position,
                "yao_type": str(y.yao_type),
                "is_dong": y.is_dong,
                "zhi": y.zhi,
                "liuqin": y.liuqin,
                "liushen": y.liushen,
                "shi": y.shi,
                "ying": y.ying,
            }
            for y in result.yaos
        ]
        return LiuyaoCastResponse(
            ben_gua_name=result.ben_gua_name,
            bian_gua_name=result.bian_gua_name,
            hu_gua_name=result.hu_gua_name,
            shang_gua=result.shang_gua,
            xia_gua=result.xia_gua,
            gua_gong=result.gua_gong,
            yaos=yaos,
            overall_judgment=result.overall_judgment,
            day_ganzhi=result.day_ganzhi,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/liuyao/chart", tags=["v2.7 六爻"])
async def liuyao_chart(date: Optional[str] = None, question: Optional[str] = None):
    """六爻卦象 HTML 可视化"""
    try:
        from tengod.liuyao_engine import LiuyaoEngine
        from tengod.chart_visualizer import visualize_liuyao
        engine = LiuyaoEngine()
        result = engine.calc_gua(day_ganzhi=date)
        html = visualize_liuyao(result)
        return HTMLResponse(content=html)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# v2.7: SSE 流式解读端点
# ============================================================================

from starlette.responses import StreamingResponse

@app.post("/api/v2/ai/stream-interpret", tags=["v2.7 AI 流式"])
async def stream_ai_interpret(request: Request):
    """SSE 流式 AI 解读"""
    try:
        body = await request.json()
    except Exception:
        body = {}

    bazi_context = body.get("bazi_context", "")
    question = body.get("question", "请分析命盘")
    system = body.get("system", "bazi")

    async def generate():
        try:
            from tengod.llm_adapter import get_llm_adapter
            llm = get_llm_adapter()

            if system == "bazi":
                from tengod.ai_interpreter import BAZI_INTERPRET_PROMPT
                prompt = BAZI_INTERPRET_PROMPT
            elif system == "liuyao":
                prompt = "你是一位精通六爻的占卜师，请根据卦象进行解读。"
            else:
                prompt = "你是一位精通命理的顾问，请进行专业分析。"

            messages = [
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"{question}\n\n{bazi_context}"},
            ]

            response = await llm.chat_stream(messages)
            async for chunk in response:
                content = getattr(chunk, "content", "") if hasattr(chunk, "content") else str(chunk)
                if content:
                    yield f"data: {json.dumps({'content': content}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


# ============================================================================
# v2.7: 异步任务端点
# ============================================================================

_task_store: Dict[str, Dict[str, Any]] = {}
_task_counter = 0
_task_lock = __import__("threading").Lock()

@app.post("/api/tasks", tags=["v2.7 异步任务"])
async def create_task(request: Request):
    """创建异步任务"""
    global _task_counter
    try:
        body = await request.json()
    except Exception:
        body = {}

    task_type = body.get("type", "generic")
    params = body.get("params", {})

    with _task_lock:
        _task_counter += 1
        task_id = f"task_{_task_counter}"
        _task_store[task_id] = {
            "id": task_id,
            "type": task_type,
            "status": "pending",
            "progress": 0,
            "result": None,
            "error": None,
            "created_at": __import__("datetime").datetime.now().isoformat(),
        }

    return {"task_id": task_id, "status": "pending"}


@app.get("/api/tasks/{task_id}", tags=["v2.7 异步任务"])
async def get_task_status(task_id: str):
    """获取任务状态"""
    task = _task_store.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


@app.post("/api/tasks/{task_id}/progress", tags=["v2.7 异步任务"])
async def update_task_progress(task_id: str, progress: int = 0, status: str = "running"):
    """更新任务进度（内部使用）"""
    task = _task_store.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    task["progress"] = progress
    task["status"] = status
    return task


# ============================================================================
# v2.8: 可观测性 + API 加固
# ============================================================================

from tengod.observability import (
    get_health_checker, health_check_response,
    get_metrics_collector, get_request_tracker,
    generate_request_id, set_request_id,
    setup_logging, get_logger,
)

# 初始化日志
setup_logging(level="INFO", fmt="json")
logger = get_logger("tengod.api")

# 注册默认健康检查
_health = get_health_checker()
_health.register("memory", lambda: {"status": "healthy", "detail": "OK"})
_health.register("python", lambda: {
    "status": "healthy",
    "detail": f"Python {sys.version[:5]}",
    "version": sys.version,
})


# ── 请求追踪中间件 ──────────────────────────────────────────────────────────

@app.middleware("http")
async def request_tracking_middleware(request: Request, call_next):
    """请求追踪中间件"""
    rid = request.headers.get("X-Request-ID", generate_request_id())
    set_request_id(rid)

    tracker = get_request_tracker()
    tracker.start_request(rid, request.method, request.url.path)

    start = time.time()
    try:
        response = await call_next(request)
        duration_ms = (time.time() - start) * 1000
        tracker.end_request(rid, response.status_code, duration_ms)
        response.headers["X-Request-ID"] = rid
        response.headers["X-Response-Time"] = f"{duration_ms:.1f}ms"
        return response
    except Exception as e:
        duration_ms = (time.time() - start) * 1000
        tracker.end_request(rid, 500, duration_ms)
        logger.error(f"Request failed: {str(e)}", extra={"request_id": rid, "path": request.url.path})
        raise


# ── 全局错误处理 ────────────────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理"""
    logger.error(f"Unhandled exception: {str(exc)}", extra={"path": request.url.path})
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": str(exc)[:200],
            "request_id": get_request_id(),
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP 异常统一格式"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "http_error",
            "message": exc.detail,
            "status_code": exc.status_code,
            "request_id": get_request_id(),
        },
    )


# ── 速率限制 ────────────────────────────────────────────────────────────────

_rate_limit_store: Dict[str, List[float]] = {}
_rate_limit_lock = threading.Lock()

def _check_rate_limit(client_ip: str, max_requests: int = 100, window: int = 60) -> bool:
    """简单的滑动窗口速率限制"""
    now = time.time()
    with _rate_limit_lock:
        if client_ip not in _rate_limit_store:
            _rate_limit_store[client_ip] = []
        timestamps = _rate_limit_store[client_ip]
        timestamps = [t for t in timestamps if now - t < window]
        _rate_limit_store[client_ip] = timestamps

        if len(timestamps) >= max_requests:
            return False

        timestamps.append(now)
        return True

    # 清理过期条目
    if len(_rate_limit_store) > 10000:
        expired = [ip for ip, ts in _rate_limit_store.items()
                    if not ts or now - ts[-1] > window * 2]
        for ip in expired:
            _rate_limit_store.pop(ip, None)


# ── 健康检查端点 ────────────────────────────────────────────────────────────

@app.get("/health", tags=["v2.8 可观测性"])
async def health_check():
    """健康检查端点"""
    return health_check_response()


@app.get("/health/ready", tags=["v2.8 可观测性"])
async def readiness_check():
    """就绪检查"""
    result = health_check_response()
    if result["status"] == "unhealthy":
        return JSONResponse(status_code=503, content=result)
    return result


@app.get("/health/live", tags=["v2.8 可观测性"])
async def liveness_check():
    """存活检查"""
    return {"status": "alive", "timestamp": datetime.now(timezone.utc).isoformat()}


# ── Prometheus 指标端点 ─────────────────────────────────────────────────────

@app.get("/metrics", tags=["v2.8 可观测性"])
async def metrics():
    """Prometheus 指标端点"""
    return Response(
        content=get_metrics_collector().get_metrics(),
        media_type="text/plain; charset=utf-8",
    )


# ── 配置端点 ────────────────────────────────────────────────────────────────

@app.get("/api/config", tags=["v2.8 配置"])
async def get_api_config():
    """获取当前配置（敏感信息脱敏）"""
    from tengod.config_manager import get_config_dict
    cfg = get_config_dict()
    # 脱敏
    if "llm" in cfg and "api_key" in cfg["llm"]:
        key = cfg["llm"]["api_key"]
        if key and len(key) > 8:
            cfg["llm"]["api_key"] = key[:4] + "****" + key[-4:]
    if "security" in cfg and "jwt_secret" in cfg["security"]:
        secret = cfg["security"]["jwt_secret"]
        if secret and len(secret) > 8:
            cfg["security"]["jwt_secret"] = secret[:4] + "****"
    return cfg


# ============================================================================
# v2.9: 智能体编排 + 知识进化 + 智能对话 API
# ============================================================================

# ── Pydantic 模型 ────────────────────────────────────────────────────────────

class AgentOrchestrateRequest(BaseModel):
    query: str = Field(..., description="用户查询/意图描述", min_length=1, max_length=2000)
    session_id: Optional[str] = Field(None, description="会话ID")
    params: Optional[Dict[str, Any]] = Field(None, description="额外参数（如出生日期）")

class AgentToolsResponse(BaseModel):
    tools: List[Dict[str, Any]]
    count: int

class AgentIntentResponse(BaseModel):
    primary: str
    intents: List[str]
    confidence: float
    suggested_tools: List[str]

class EvolutionFeedbackRequest(BaseModel):
    session_id: str = Field(..., description="会话ID")
    ratings: Dict[str, int] = Field(..., description="评分: accuracy/satisfaction/usefulness (1-5)")
    domain: str = Field("general", description="知识领域")
    comment: str = Field("", description="文字反馈")
    analysis_type: str = Field("", description="分析类型")
    corrections: Optional[List[Dict[str, str]]] = Field(None, description="纠正列表")

class EvolutionFeedbackResponse(BaseModel):
    session_id: str
    overall_score: float
    domain: str
    confidence_after: float

class EvolutionStatsResponse(BaseModel):
    total_feedback: int
    average_score: float
    total_nodes: int
    total_edges: int
    total_evolutions: int
    domains: Dict[str, Any]
    recent_evolutions: List[Dict[str, Any]]

class EvolutionConfidenceResponse(BaseModel):
    confidences: Dict[str, float]
    average: float
    highest: Dict[str, Any]
    lowest: Dict[str, Any]

class EvolutionAdjustRequest(BaseModel):
    domain: str = Field(..., description="知识领域")
    adjustment: float = Field(..., ge=-1.0, le=1.0, description="调整量 [-1.0, 1.0]")
    reason: str = Field("", description="调整原因")

class ConversationChatRequest(BaseModel):
    message: str = Field(..., description="用户消息", min_length=1, max_length=5000)
    session_id: str = Field(..., description="会话ID")
    bazi_context: str = Field("", description="八字上下文")

class ConversationChatResponse(BaseModel):
    session_id: str
    response: str
    intent: Dict[str, Any]
    suggestions: List[Dict[str, str]]
    conversation_state: str
    session_stats: Dict[str, Any]

class ConversationSessionResponse(BaseModel):
    session_id: str
    message_count: int
    topics_covered: List[str]
    intent_context: Dict[str, Any]


# ── 智能体编排端点 ───────────────────────────────────────────────────────────

@app.post("/api/v2/agent/orchestrate", tags=["v2.9 智能体"])
async def v2_agent_orchestrate(req: AgentOrchestrateRequest, request: Request):
    """智能体编排：意图识别 → 计划生成 → 执行工具链 → 返回结果"""
    from tengod.auth import authorize
    authorize(request, "agent:orchestrate")
    try:
        from tengod.agent_orchestrator import get_orchestrator
        orchestrator = get_orchestrator()
        params = req.params or {}
        result = orchestrator.orchestrate(req.query, session_id=req.session_id, params=params)
        return result.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"智能体编排失败: {e}")


@app.get("/api/v2/agent/tools", tags=["v2.9 智能体"])
async def v2_agent_tools(request: Request):
    """列出所有可用工具及其规格"""
    from tengod.auth import authorize
    authorize(request, "agent:tools", consume_quota=False)
    try:
        from tengod.agent_orchestrator import get_orchestrator
        orchestrator = get_orchestrator()
        return AgentToolsResponse(
            tools=orchestrator.get_tool_specs(),
            count=len(orchestrator.tools),
        ).model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取工具列表失败: {e}")


@app.post("/api/v2/agent/detect-intent", tags=["v2.9 智能体"])
async def v2_agent_detect_intent(request: Request):
    """意图识别：分析用户查询，返回意图分类和置信度"""
    from tengod.auth import authorize
    authorize(request, "agent:detect", consume_quota=False)
    try:
        body = await request.json()
        query = body.get("query", "")
        if not query:
            raise HTTPException(status_code=400, detail="query 不能为空")
        from tengod.agent_orchestrator import get_orchestrator
        orchestrator = get_orchestrator()
        intent = orchestrator.detect_intent(query)
        plan = orchestrator.plan_actions(query, intent)
        return AgentIntentResponse(
            primary=intent["primary"],
            intents=intent["intents"],
            confidence=intent["confidence"],
            suggested_tools=plan,
        ).model_dump()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"意图识别失败: {e}")


# ── 知识进化端点 ────────────────────────────────────────────────────────────

@app.post("/api/v2/evolution/feedback", tags=["v2.9 知识进化"])
async def v2_evolution_feedback(req: EvolutionFeedbackRequest, request: Request):
    """提交用户反馈：用于知识进化系统的置信度调整"""
    from tengod.auth import authorize
    authorize(request, "evolution:feedback")
    try:
        from tengod.knowledge_evolution import get_evolution_engine
        engine = get_evolution_engine()
        record = engine.collect_feedback(
            session_id=req.session_id,
            ratings=req.ratings,
            domain=req.domain,
            comment=req.comment,
            analysis_type=req.analysis_type,
            corrections=req.corrections,
        )
        return EvolutionFeedbackResponse(
            session_id=record.session_id,
            overall_score=round(record.overall_score(), 2),
            domain=record.domain,
            confidence_after=engine.get_confidence(req.domain),
        ).model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"提交反馈失败: {e}")


@app.get("/api/v2/evolution/stats", tags=["v2.9 知识进化"])
async def v2_evolution_stats(request: Request):
    """获取知识进化统计：总反馈数、置信度分布、进化历史"""
    from tengod.auth import authorize
    authorize(request, "evolution:read", consume_quota=False)
    try:
        from tengod.knowledge_evolution import get_evolution_engine
        engine = get_evolution_engine()
        stats = engine.get_evolution_stats()
        return EvolutionStatsResponse(**stats).model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取进化统计失败: {e}")


@app.get("/api/v2/evolution/confidence", tags=["v2.9 知识进化"])
async def v2_evolution_confidence(request: Request):
    """获取所有知识领域的置信度分布"""
    from tengod.auth import authorize
    authorize(request, "evolution:read", consume_quota=False)
    try:
        from tengod.knowledge_evolution import get_evolution_engine
        engine = get_evolution_engine()
        confs = engine.get_all_confidences()
        entries = sorted(confs.items(), key=lambda x: x[1], reverse=True)
        avg = sum(confs.values()) / len(confs) if confs else 0
        return EvolutionConfidenceResponse(
            confidences=confs,
            average=round(avg, 3),
            highest={"domain": entries[0][0], "confidence": entries[0][1]} if entries else {},
            lowest={"domain": entries[-1][0], "confidence": entries[-1][1]} if entries else {},
        ).model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取置信度失败: {e}")


@app.get("/api/v2/evolution/trend", tags=["v2.9 知识进化"])
async def v2_evolution_trend(request: Request, domain: str = "", limit: int = 20):
    """获取反馈趋势：按时间排序的反馈评分"""
    from tengod.auth import authorize
    authorize(request, "evolution:read", consume_quota=False)
    try:
        from tengod.knowledge_evolution import get_evolution_engine
        engine = get_evolution_engine()
        trend = engine.get_feedback_trend(domain=domain, limit=limit)
        return {"domain": domain or "all", "limit": limit, "data": trend, "count": len(trend)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取反馈趋势失败: {e}")


@app.get("/api/v2/evolution/graph", tags=["v2.9 知识进化"])
async def v2_evolution_graph(request: Request):
    """获取知识图谱统计：节点/边分布、关系类型"""
    from tengod.auth import authorize
    authorize(request, "evolution:read", consume_quota=False)
    try:
        from tengod.knowledge_evolution import get_evolution_engine
        engine = get_evolution_engine()
        return engine.get_knowledge_graph_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取知识图谱失败: {e}")


@app.post("/api/v2/evolution/evolve", tags=["v2.9 知识进化"])
async def v2_evolution_trigger(request: Request):
    """手动触发知识进化：分析反馈趋势 + 自动补全知识图谱"""
    from tengod.auth import authorize
    authorize(request, "evolution:evolve")
    try:
        from tengod.knowledge_evolution import get_evolution_engine
        engine = get_evolution_engine()
        results = engine.evolve()
        return {
            "evolutions": [r.to_dict() for r in results],
            "count": len(results),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"知识进化失败: {e}")


@app.post("/api/v2/evolution/confidence/adjust", tags=["v2.9 知识进化"])
async def v2_evolution_adjust(req: EvolutionAdjustRequest, request: Request):
    """手动调整知识领域置信度"""
    from tengod.auth import authorize
    authorize(request, "evolution:adjust")
    try:
        from tengod.knowledge_evolution import get_evolution_engine
        engine = get_evolution_engine()
        profile = engine.adjust_confidence(req.domain, req.adjustment, req.reason)
        return {
            "domain": req.domain,
            "confidence": profile.current_confidence,
            "adjustment": req.adjustment,
            "reason": req.reason,
            "adjustment_count": len(profile.adjustments),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"调整置信度失败: {e}")


# ── 智能对话端点 ────────────────────────────────────────────────────────────

@app.post("/api/v2/conversation/chat", tags=["v2.9 对话引擎"])
async def v2_conversation_chat(req: ConversationChatRequest, request: Request):
    """智能对话：意图追踪 + 主动建议 + 多轮记忆"""
    from tengod.auth import authorize
    authorize(request, "conversation:chat")
    try:
        from tengod.ai_interpreter import smart_chat
        result = await smart_chat(
            user_message=req.message,
            session_id=req.session_id,
            bazi_context=req.bazi_context,
        )
        return ConversationChatResponse(
            session_id=result["session_id"],
            response=result["response"],
            intent=result["intent"],
            suggestions=result["suggestions"],
            conversation_state=result["conversation_state"],
            session_stats=result["session_stats"],
        ).model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"智能对话失败: {e}")


@app.get("/api/v2/conversation/session/{session_id}", tags=["v2.9 对话引擎"])
async def v2_conversation_session(session_id: str, request: Request):
    """获取会话摘要：消息数、话题覆盖、意图上下文"""
    from tengod.auth import authorize
    authorize(request, "conversation:read", consume_quota=False)
    try:
        from tengod.ai_interpreter import get_conversation_engine
        engine = get_conversation_engine()
        summary = engine.get_session_summary(session_id)
        return ConversationSessionResponse(
            session_id=session_id,
            message_count=summary["message_count"],
            topics_covered=summary["topics_covered"],
            intent_context=summary["intent_context"],
        ).model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取会话摘要失败: {e}")


@app.delete("/api/v2/conversation/session/{session_id}", tags=["v2.9 对话引擎"])
async def v2_conversation_reset(session_id: str, request: Request):
    """重置会话：清除对话历史、意图追踪、建议记录"""
    from tengod.auth import authorize
    authorize(request, "conversation:reset")
    try:
        from tengod.ai_interpreter import get_conversation_engine
        engine = get_conversation_engine()
        engine.reset_session(session_id)
        return {"session_id": session_id, "status": "reset", "timestamp": datetime.now(timezone.utc).isoformat()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重置会话失败: {e}")


@app.get("/api/v2/conversation/suggestions/{session_id}", tags=["v2.9 对话引擎"])
async def v2_conversation_suggestions(session_id: str, request: Request):
    """获取主动建议：基于当前会话意图追踪"""
    from tengod.auth import authorize
    authorize(request, "conversation:read", consume_quota=False)
    try:
        from tengod.ai_interpreter import get_conversation_engine, ProactiveAdvisor
        engine = get_conversation_engine()
        session = engine.get_session_summary(session_id)
        advisor = ProactiveAdvisor()
        suggestions = advisor.generate_suggestions(
            session.get("intent_context", {}),
            max_suggestions=3,
        )
        return {
            "session_id": session_id,
            "suggestions": suggestions,
            "count": len(suggestions),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取建议失败: {e}")


# ============================================================================
# v2.12: 数据管理 API — 案例/对话/反馈/数据库
# ============================================================================

# ── 案例管理 ────────────────────────────────────────────────────────────────

class CaseListRequest(BaseModel):
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")
    category: str = Field("", description="分类过滤")
    tag: str = Field("", description="标签过滤")
    search: str = Field("", description="搜索关键词")

@app.get("/api/v2/cases", tags=["v2.12 数据管理"])
async def list_cases(request: Request, page: int = 1, page_size: int = 20, category: str = "", search: str = ""):
    """分页列出案例"""
    from tengod.auth import authorize
    authorize(request, "data:read", consume_quota=False)
    try:
        from tengod.case_repository import get_repository
        repo = get_repository()
        result = repo.list_cases(page=page, page_size=page_size, category=category, search=search)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取案例列表失败: {e}")


@app.get("/api/v2/cases/{case_id}", tags=["v2.12 数据管理"])
async def get_case(case_id: int, request: Request):
    """获取案例详情"""
    from tengod.auth import authorize
    authorize(request, "data:read", consume_quota=False)
    try:
        from tengod.case_repository import get_repository
        repo = get_repository()
        case = repo.get_case(case_id)
        if not case:
            raise HTTPException(status_code=404, detail="案例不存在")
        return case
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取案例失败: {e}")


@app.post("/api/v2/cases", tags=["v2.12 数据管理"])
async def create_case(request: Request):
    """创建案例"""
    from tengod.auth import authorize
    authorize(request, "data:write")
    try:
        body = await request.json()
        from tengod.case_repository import get_repository
        repo = get_repository()
        result = repo.add_case(body)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建案例失败: {e}")


@app.put("/api/v2/cases/{case_id}", tags=["v2.12 数据管理"])
async def update_case(case_id: int, request: Request):
    """更新案例"""
    from tengod.auth import authorize
    authorize(request, "data:write")
    try:
        body = await request.json()
        from tengod.case_repository import get_repository
        repo = get_repository()
        success = repo.update_case(case_id, body)
        if not success:
            raise HTTPException(status_code=404, detail="案例不存在")
        return {"success": True, "id": case_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新案例失败: {e}")


@app.delete("/api/v2/cases/{case_id}", tags=["v2.12 数据管理"])
async def delete_case(case_id: int, request: Request):
    """删除案例"""
    from tengod.auth import authorize
    authorize(request, "data:write")
    try:
        from tengod.case_repository import get_repository
        repo = get_repository()
        success = repo.delete_case(case_id)
        if not success:
            raise HTTPException(status_code=404, detail="案例不存在")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除案例失败: {e}")


@app.get("/api/v2/cases/similar", tags=["v2.12 数据管理"])
async def find_similar_cases(day_master: str = "", limit: int = 5, request: Request = None):
    """查找相似案例"""
    from tengod.auth import authorize
    authorize(request, "data:read", consume_quota=False)
    try:
        from tengod.case_repository import get_repository
        repo = get_repository()
        similar = repo.get_similar_cases({"day_master": day_master}, limit=limit)
        return {"similar": similar, "count": len(similar)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查找相似案例失败: {e}")


@app.get("/api/v2/cases/export", tags=["v2.12 数据管理"])
async def export_cases(filepath: str = "/tmp/cases_export.json", request: Request = None):
    """导出全部案例为 JSON"""
    from tengod.auth import authorize
    authorize(request, "data:admin", consume_quota=False)
    try:
        from tengod.case_repository import get_repository
        repo = get_repository()
        count = repo.export_to_json(filepath)
        return {"success": True, "count": count, "path": filepath}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导出失败: {e}")


@app.post("/api/v2/cases/import", tags=["v2.12 数据管理"])
async def import_cases(request: Request):
    """批量导入案例 JSON"""
    from tengod.auth import authorize
    authorize(request, "data:admin")
    try:
        body = await request.json()
        from tengod.case_repository import get_repository
        repo = get_repository()
        count = repo.bulk_import(body.get("cases", []))
        return {"success": True, "imported": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导入失败: {e}")


# ── 对话历史 ──────────────────────────────────────────────────────────────

@app.get("/api/v2/conversations", tags=["v2.12 数据管理"])
async def list_conversations(request: Request, limit: int = 10):
    """获取最近会话列表"""
    from tengod.auth import authorize
    authorize(request, "data:read", consume_quota=False)
    try:
        from tengod.database import is_persistent, get_db
        if not is_persistent():
            return {"conversations": [], "count": 0}
        recent = get_db().get_recent_conversations(limit=limit)
        return {"conversations": recent, "count": len(recent)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取会话列表失败: {e}")


@app.get("/api/v2/conversations/{session_id}", tags=["v2.12 数据管理"])
async def get_conversation(session_id: str, request: Request, limit: int = 100):
    """获取会话详情"""
    from tengod.auth import authorize
    authorize(request, "data:read", consume_quota=False)
    try:
        from tengod.database import is_persistent, get_db
        if not is_persistent():
            return {"messages": [], "count": 0}
        messages = get_db().get_conversation(session_id, limit=limit)
        return {"session_id": session_id, "messages": messages, "count": len(messages)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取会话详情失败: {e}")


@app.delete("/api/v2/conversations/{session_id}", tags=["v2.12 数据管理"])
async def delete_conversation(session_id: str, request: Request):
    """删除会话"""
    from tengod.auth import authorize
    authorize(request, "data:write")
    try:
        from tengod.database import is_persistent, get_db
        if not is_persistent():
            raise HTTPException(status_code=400, detail="持久化未启用")
        deleted = get_db().delete_conversation(session_id)
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除会话失败: {e}")


# ── 反馈管理 ──────────────────────────────────────────────────────────────

@app.get("/api/v2/feedback", tags=["v2.12 数据管理"])
async def list_feedback(request: Request, domain: str = "", limit: int = 20, offset: int = 0):
    """列出反馈记录"""
    from tengod.auth import authorize
    authorize(request, "data:read", consume_quota=False)
    try:
        from tengod.database import is_persistent, get_db
        if not is_persistent():
            return {"feedback": [], "count": 0}
        feedback = get_db().list_feedback(domain=domain, limit=limit, offset=offset)
        count = get_db().count_feedback(domain=domain)
        return {"feedback": feedback, "count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取反馈失败: {e}")


@app.get("/api/v2/feedback/stats", tags=["v2.12 数据管理"])
async def get_feedback_stats(request: Request):
    """获取反馈统计"""
    from tengod.auth import authorize
    authorize(request, "data:read", consume_quota=False)
    try:
        from tengod.database import is_persistent, get_db
        if not is_persistent():
            return {"total": 0}
        stats = get_db().get_feedback_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计失败: {e}")


# ── 数据库管理 ──────────────────────────────────────────────────────────────

@app.get("/api/v2/admin/db-stats", tags=["v2.12 数据管理"])
async def get_db_stats(request: Request):
    """获取数据库统计"""
    from tengod.auth import authorize
    authorize(request, "data:admin", consume_quota=False)
    try:
        from tengod.database import is_persistent, get_db
        if not is_persistent():
            return {"is_persistent": False, "stats": {}}
        stats = get_db().get_stats()
        return {"is_persistent": True, "stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计失败: {e}")


@app.post("/api/v2/admin/backup", tags=["v2.12 数据管理"])
async def backup_full(request: Request):
    """全量数据备份导出"""
    from tengod.auth import authorize
    authorize(request, "data:admin")
    try:
        from tengod.database import is_persistent, get_db
        if not is_persistent():
            raise HTTPException(status_code=400, detail="持久化未启用")
        export = get_db().export_all()
        return export
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"备份失败: {e}")


@app.post("/api/v2/admin/restore", tags=["v2.12 数据管理"])
async def restore_full(request: Request):
    """从备份恢复全量数据"""
    from tengod.auth import authorize
    authorize(request, "data:admin")
    try:
        body = await request.json()
        from tengod.database import is_persistent, get_db
        if not is_persistent():
            raise HTTPException(status_code=400, detail="持久化未启用")
        counts = get_db().import_all(body)
        return {"success": True, "counts": counts}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"恢复失败: {e}")


# ============================================================================
# v2.13: 流年运势 API
# ============================================================================

from tengod.dayun_liunian import get_liunian_engine


@app.post("/api/v2/liunian/analyze", tags=["v2.13 流年运势"])
async def liunian_analyze(request: Request):
    """流年运势综合分析（含大运+流年叠加、四维度评分）"""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="请求体须为JSON")

    birth_year = body.get("birth_year")
    birth_month = body.get("birth_month")
    birth_day = body.get("birth_day")
    if not all([birth_year, birth_month, birth_day]):
        raise HTTPException(status_code=400, detail="缺少必填字段: birth_year, birth_month, birth_day")

    engine = get_liunian_engine()
    result = engine.analyze(
        birth_year=int(birth_year),
        birth_month=int(birth_month),
        birth_day=int(birth_day),
        hour=int(body.get("hour", 12)),
        minute=int(body.get("minute", 0)),
        is_male=body.get("gender", "male") == "male",
        longitude=float(body.get("longitude", 120.0)),
        yongshen=body.get("yongshen"),
        jishen=body.get("jishen"),
        target_years=body.get("target_years"),
    )
    return result


@app.get("/api/v2/liunian/year/{year}", tags=["v2.13 流年运势"])
async def liunian_single_year(
    year: int,
    birth_year: int,
    birth_month: int,
    birth_day: int,
    hour: int = 12,
    minute: int = 0,
    gender: str = "male",
    longitude: float = 120.0,
    yongshen: str = "",
    jishen: str = "",
):
    """单年流年运势详情"""
    engine = get_liunian_engine()
    yongshen_list = [y.strip() for y in yongshen.split(",") if y.strip()] if yongshen else None
    jishen_list = [j.strip() for j in jishen.split(",") if j.strip()] if jishen else None
    result = engine.analyze(
        birth_year=birth_year, birth_month=birth_month, birth_day=birth_day,
        hour=hour, minute=minute, is_male=gender == "male",
        longitude=longitude, yongshen=yongshen_list, jishen=jishen_list,
        target_years=[year],
    )
    return result["liunian"][0] if result["liunian"] else {}


# ============================================================================
# v2.14: 天眼门禁 API
# ============================================================================

from tengod.tiangan_gate import get_tianmen
from tengod.xiuzhen_realms import get_evaluator, NINE_REALMS
from tengod.self_correction import get_daemon
from tengod.hundun_sea import get_hundun_sea
from tengod.huigu_scheduler import get_huigu_scheduler


@app.get("/api/v2/gate/stats", tags=["v2.14 天眼门禁"])
async def gate_stats():
    """天眼门禁统计"""
    tianmen = get_tianmen()
    return tianmen.get_stats()


@app.get("/api/v2/gate/verdict", tags=["v2.14 天眼门禁"])
async def gate_verdict(
    output: str = "",
    confidence: float = 0.5,
    entropy: float = 0.5,
    variance: float = 0.1,
):
    """知止判定测试"""
    tianmen = get_tianmen()
    guarded, verdict = tianmen.guard(
        output,
        confidence_scores={"overall": confidence},
        feature_entropies={"output": entropy},
    )
    return {
        "passed": verdict.passed,
        "confidence": round(verdict.confidence, 3),
        "cultivation_qi": round(verdict.cultivation_qi, 3),
        "should_retreat": verdict.should_retreat,
        "reason": verdict.retreat_reason,
        "guarded_output": guarded,
    }


@app.get("/api/v2/realms/status", tags=["v2.14 修真九境"])
async def realms_status():
    """修真九境修行状态"""
    evaluator = get_evaluator()
    return evaluator.get_realm_progress()


@app.get("/api/v2/realms/all", tags=["v2.14 修真九境"])
async def realms_all():
    """九境全览"""
    return [
        {
            "index": r.index,
            "name": r.name,
            "description": r.description,
            "threshold": r.pass_threshold,
        }
        for r in NINE_REALMS
    ]


@app.post("/api/v2/realms/evaluate", tags=["v2.14 修真九境"])
async def realms_evaluate(request: Request):
    """心魔劫评测"""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="请求体须为JSON")
    scores = body.get("scores", {})
    evaluator = get_evaluator()
    return evaluator.evaluate(scores, body.get("test_name", "心魔劫"))


@app.post("/api/v2/correct", tags=["v2.14 自修正"])
async def self_correct(request: Request):
    """七步自修正流程"""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="请求体须为JSON")
    daemon = get_daemon()
    state, report = daemon.correct(
        current_state=body.get("state", {}),
        expected_output=body.get("expected"),
        physical_constraints=body.get("constraints"),
        memory_store=body.get("memory"),
        enable_gate=body.get("enable_gate", True),
    )
    return {
        "corrected_state": state,
        "report": report.to_dict(),
    }


@app.get("/api/v2/correct/stats", tags=["v2.14 自修正"])
async def correction_stats():
    """自修正统计"""
    daemon = get_daemon()
    return daemon.get_stats()


@app.get("/api/v2/hundun/stats", tags=["v2.14 混沌海"])
async def hundun_stats():
    """混沌海统计"""
    sea = get_hundun_sea()
    return sea.get_stats()


@app.get("/api/v2/hundun/foams", tags=["v2.14 混沌海"])
async def hundun_foams(status: str = "floating"):
    """浮沫坐标列表"""
    sea = get_hundun_sea()
    if status == "verified":
        foams = sea.get_verified_foams()
    else:
        foams = sea.get_floating_foams()
    return [f.to_dict() for f in foams[:20]]


@app.get("/api/v2/huigu/stats", tags=["v2.14 回头看"])
async def huigu_stats():
    """回头看调度器统计"""
    scheduler = get_huigu_scheduler()
    return scheduler.get_stats()


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
        logger.info("API Key 鉴权已启用")

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