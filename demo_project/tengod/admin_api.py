#!/usr/bin/env python3
"""
admin_api.py — 管理后台 API 模块 v1.0.0
阶段二十六（Stage 26）：Admin Backend

提供八字记录、案例、用户的管理端点，并集成 AdvancedAnalyzer
实现命例对比、批量排盘、命运轨迹推演等高级分析功能。

模块结构：
  1. Pydantic 数据模型（可独立使用）
  2. AdminService 业务逻辑（不依赖 FastAPI）
  3. create_admin_app() FastAPI 应用工厂
  4. 独立运行入口与自测

用法：
    # 核心服务（不依赖 FastAPI）
    from tengod.admin_api import AdminService
    service = AdminService(db_path="/tmp/test.db")
    record = service.create_record({"year": 1990, ...})
    traj = service.get_trajectory(record["id"], 1990, 2030)

    # FastAPI 方式
    from tengod.admin_api import create_admin_app
    app = create_admin_app()
    # uvicorn main:app --reload
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ============================================================================
# 1. Pydantic 数据模型
# ============================================================================

try:
    from pydantic import BaseModel, Field
    _HAS_PYDANTIC = True
except Exception:  # pragma: no cover - 优雅降级
    _HAS_PYDANTIC = False

    class BaseModel:  # type: ignore
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

        def model_dump(self):
            return self.__dict__.copy()

        def dict(self):
            return self.__dict__.copy()


if _HAS_PYDANTIC:

    class BaziRecordInput(BaseModel):
        year: int = Field(..., ge=1900, le=2100, description="出生年份")
        month: int = Field(..., ge=1, le=12, description="出生月份")
        day: int = Field(..., ge=1, le=31, description="出生日期")
        hour: int = Field(..., ge=0, le=23, description="出生时辰（24 小时制）")
        minute: Optional[int] = Field(0, ge=0, le=59, description="出生分钟")
        gender: str = Field("male", pattern="^(male|female)$", description="性别")
        longitude: Optional[float] = Field(116.4, description="经度")
        latitude: Optional[float] = Field(39.9, description="纬度")
        user_id: Optional[int] = Field(None, description="关联用户ID")
        label: Optional[str] = Field(None, max_length=128, description="标签/备注")
        notes: Optional[str] = Field(None, description="详细备注")
        tags: Optional[str] = Field(None, max_length=256, description="逗号分隔的标签")

    class BaziRecordUpdate(BaseModel):
        year: Optional[int] = Field(None, ge=1900, le=2100)
        month: Optional[int] = Field(None, ge=1, le=12)
        day: Optional[int] = Field(None, ge=1, le=31)
        hour: Optional[int] = Field(None, ge=0, le=23)
        minute: Optional[int] = Field(None, ge=0, le=59)
        gender: Optional[str] = Field(None)
        longitude: Optional[float] = None
        latitude: Optional[float] = None
        user_id: Optional[int] = None
        label: Optional[str] = None
        notes: Optional[str] = None
        tags: Optional[str] = None

    class CaseInput(BaseModel):
        title: str = Field(..., min_length=1, max_length=256)
        summary: Optional[str] = None
        analysis_text: Optional[str] = None
        category: Optional[str] = Field(None, max_length=64)
        is_public: bool = True
        is_featured: bool = False
        bazi_record_id: Optional[int] = None
        user_id: Optional[int] = None
        tags: Optional[str] = None

    class CaseUpdate(BaseModel):
        title: Optional[str] = None
        summary: Optional[str] = None
        analysis_text: Optional[str] = None
        category: Optional[str] = None
        is_public: Optional[bool] = None
        is_featured: Optional[bool] = None
        bazi_record_id: Optional[int] = None
        user_id: Optional[int] = None
        tags: Optional[str] = None

    class UserCreate(BaseModel):
        username: str = Field(..., min_length=3, max_length=64)
        display_name: Optional[str] = None
        email: Optional[str] = Field(None, max_length=128)
        role: str = Field("user", pattern="^(user|admin|guest)$")
        api_quota_daily: int = Field(100, ge=0)

    class UserUpdate(BaseModel):
        display_name: Optional[str] = None
        email: Optional[str] = None
        role: Optional[str] = None
        is_active: Optional[bool] = None
        api_quota_daily: Optional[int] = None

    class TrajectoryQuery(BaseModel):
        bazi_record_id: Optional[int] = None
        year: Optional[int] = None
        month: Optional[int] = None
        day: Optional[int] = None
        hour: Optional[int] = None
        gender: Optional[str] = None
        start_year: int = Field(1900, ge=1900, le=2200)
        end_year: int = Field(2030, ge=1900, le=2200)

    class BatchBaziQuery(BaseModel):
        records: List[Dict[str, Any]] = Field(
            ..., description="BaziRecordInput 字典列表，最多 50 条"
        )

    class CompareQuery(BaseModel):
        record_a_id: int
        record_b_id: int

    class ConfigUpdate(BaseModel):
        key: str
        value: Any

else:  # pragma: no cover
    BaziRecordInput = BaziRecordUpdate = CaseInput = CaseUpdate = object  # type: ignore
    UserCreate = UserUpdate = TrajectoryQuery = BatchBaziQuery = object  # type: ignore
    CompareQuery = ConfigUpdate = object  # type: ignore


__all__ = [
    "AdminService",
    "create_admin_app",
    "BaziRecordInput",
    "BaziRecordUpdate",
    "CaseInput",
    "CaseUpdate",
    "UserCreate",
    "UserUpdate",
    "TrajectoryQuery",
    "BatchBaziQuery",
    "CompareQuery",
    "ConfigUpdate",
]
__version__ = "1.0.0"


# ============================================================================
# 2. AdminService 业务逻辑
# ============================================================================

class AdminService:
    """
    后台管理核心服务（纯 Python，不依赖 FastAPI）

    封装：
      - 八字记录 CRUD
      - 案例 CRUD
      - 用户管理（查询/更新角色/切换活跃状态）
      - 命运轨迹推演
      - 批量排盘
      - 命例对比
      - 系统统计信息
    """

    def __init__(self, store=None, db_path: Optional[str] = None, analyzer=None):
        """
        Args:
            store: 可选，自定义 DataStore 实例
            db_path: 可选，SQLite 数据库路径
            analyzer: 可选，自定义 AdvancedAnalyzer 实例
        """
        from .data_store import DataStore  # lazy import

        self._store = store or DataStore(db_path=db_path)
        self._analyzer = analyzer

        # 简易配置缓存（进程内 kv store）
        self._config: Dict[str, Any] = {}

    # ── 便捷属性 ───────────────────────────────────────────────
    @property
    def store(self):
        return self._store

    @property
    def analyzer(self):
        if self._analyzer is None:
            from .advanced_analysis import AdvancedAnalyzer
            self._analyzer = AdvancedAnalyzer(store=self._store)
        return self._analyzer

    # ── 八字记录 ───────────────────────────────────────────────

    def get_records_paginated(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """分页获取八字记录列表。"""
        try:
            records = self._store.list_bazi_records(
                limit=max(1, int(limit)), offset=max(0, int(offset))
            )
            return [r.to_dict() for r in records]
        except Exception as e:
            return []

    def get_record(self, record_id: int) -> Optional[Dict[str, Any]]:
        """获取单条八字记录。"""
        try:
            record = self._store.get_bazi_record(int(record_id))
            return record.to_dict() if record is not None else None
        except Exception:
            return None

    def create_record(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建新的八字记录，返回 dict（包含 id）。"""
        try:
            # 允许传入 BaziRecordInput 或 dict
            data = _to_dict(input_data)

            required = ["year", "month", "day", "hour"]
            for k in required:
                if k not in data or data[k] is None:
                    raise ValueError(f"缺少必填字段: {k}")

            rid = self._store.save_bazi_record(
                year=int(data["year"]),
                month=int(data["month"]),
                day=int(data["day"]),
                hour=int(data["hour"]),
                minute=int(data.get("minute", 0) or 0),
                gender=str(data.get("gender", "male")),
                longitude=float(data.get("longitude", 116.4) or 116.4),
                latitude=float(data.get("latitude", 39.9) or 39.9),
                user_id=data.get("user_id"),
                label=data.get("label"),
                tags=data.get("tags"),
                notes=data.get("notes"),
            )
            record = self._store.get_bazi_record(rid)
            if record is None:
                return {"id": rid, "error": "创建后无法读取记录"}
            return record.to_dict()
        except Exception as e:
            return {"error": f"create_record failed: {e}"}

    def update_record(self, record_id: int, update_data: Dict[str, Any]) -> bool:
        """更新八字记录字段。"""
        try:
            data = _to_dict(update_data)
            # 仅保留允许更新的字段
            allowed = {
                "year", "month", "day", "hour", "minute", "gender",
                "longitude", "latitude", "user_id", "label", "notes", "tags",
            }
            clean = {k: v for k, v in data.items() if k in allowed and v is not None}
            if not clean:
                return False
            return bool(self._store.update_bazi_record(int(record_id), **clean))
        except Exception:
            return False

    def delete_record(self, record_id: int) -> bool:
        """删除八字记录。"""
        try:
            return bool(self._store.delete_bazi_record(int(record_id)))
        except Exception:
            return False

    # ── 案例管理 ───────────────────────────────────────────────

    def get_cases_paginated(
        self, limit: int = 50, offset: int = 0,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """分页获取案例列表（可选按 category 过滤）。"""
        try:
            cases = self._store.list_cases(
                limit=max(1, int(limit)),
                offset=max(0, int(offset)),
                category=category if category else None,
            )
            return [c.to_dict() for c in cases]
        except Exception:
            return []

    def create_case(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """创建案例。"""
        try:
            d = _to_dict(data)
            if "title" not in d or not str(d.get("title", "")).strip():
                raise ValueError("title 为必填字段")
            cid = self._store.save_case(
                title=str(d["title"]),
                summary=d.get("summary"),
                analysis_text=d.get("analysis_text"),
                category=d.get("category"),
                is_public=bool(d.get("is_public", True)),
                is_featured=bool(d.get("is_featured", False)),
                bazi_record_id=d.get("bazi_record_id"),
                user_id=d.get("user_id"),
                tags=d.get("tags"),
            )
            case = self._store.get_case(cid)
            return case.to_dict() if case is not None else {"id": cid}
        except Exception as e:
            return {"error": f"create_case failed: {e}"}

    def update_case(self, case_id: int, data: Dict[str, Any]) -> bool:
        """更新案例字段。"""
        try:
            d = _to_dict(data)
            allowed = {
                "title", "summary", "analysis_text", "category",
                "is_public", "is_featured", "bazi_record_id", "user_id", "tags",
            }
            clean = {k: v for k, v in d.items() if k in allowed and v is not None}
            if not clean:
                return False
            return bool(self._store.update_case(int(case_id), **clean))
        except Exception:
            return False

    def delete_case(self, case_id: int) -> bool:
        """删除案例。"""
        try:
            return bool(self._store.delete_case(int(case_id)))
        except Exception:
            return False

    # ── 用户管理 ───────────────────────────────────────────────

    def get_users(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取用户列表。"""
        try:
            users = self._store.list_users(limit=max(1, int(limit)))
            return [self._user_to_dict(u) for u in users]
        except Exception:
            return []

    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """获取单个用户。"""
        try:
            user = self._store.get_user(int(user_id))
            return self._user_to_dict(user) if user is not None else None
        except Exception:
            return None

    def create_user(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """创建用户（简单实现，主要用于测试）。"""
        try:
            d = _to_dict(data)
            if not d.get("username"):
                raise ValueError("username 为必填字段")
            with self._store._session() as s:
                from .data_store import User as UserModel
                existing = s.query(UserModel).filter(
                    UserModel.username == str(d["username"])
                ).first()
                if existing is not None:
                    return {"error": "username 已存在"}
                user = UserModel(
                    username=str(d["username"]),
                    display_name=d.get("display_name") or d["username"],
                    email=d.get("email"),
                    role=str(d.get("role", "user")),
                    is_active=1 if d.get("is_active", True) else 0,
                    api_quota_daily=int(d.get("api_quota_daily", 100)),
                    last_login_at=datetime.now(timezone.utc),
                )
                s.add(user)
                s.commit()
                s.refresh(user)
                return self._user_to_dict(user)
        except Exception as e:
            return {"error": f"create_user failed: {e}"}

    def update_user(self, user_id: int, data: Dict[str, Any]) -> bool:
        """更新用户字段。"""
        try:
            d = _to_dict(data)
            allowed = {
                "display_name", "email", "role", "api_quota_daily",
            }
            clean = {k: v for k, v in d.items() if k in allowed and v is not None}

            # is_active 需要特殊处理（数据库中是 int）
            set_active = d.get("is_active")
            if set_active is not None:
                clean["is_active"] = 1 if bool(set_active) else 0

            if not clean:
                return False

            with self._store._session() as s:
                from .data_store import User as UserModel
                user = s.query(UserModel).filter(UserModel.id == int(user_id)).first()
                if user is None:
                    return False
                for k, v in clean.items():
                    if hasattr(user, k):
                        setattr(user, k, v)
                s.commit()
                return True
        except Exception:
            return False

    def toggle_user_active(self, user_id: int) -> bool:
        """切换用户 is_active 状态。"""
        try:
            with self._store._session() as s:
                from .data_store import User as UserModel
                user = s.query(UserModel).filter(UserModel.id == int(user_id)).first()
                if user is None:
                    return False
                user.is_active = 0 if int(user.is_active or 0) == 1 else 1
                s.commit()
                return True
        except Exception:
            return False

    # ── 高级分析（委托给 AdvancedAnalyzer） ───────────────

    def get_trajectory(
        self, bazi_record_id: int, start_year: int, end_year: int,
    ) -> Dict[str, Any]:
        """基于已存储的八字记录进行命运轨迹推演。"""
        try:
            record = self._store.get_bazi_record(int(bazi_record_id))
            if record is None:
                return {"error": f"bazi_record_id={bazi_record_id} 不存在"}

            start_year = int(start_year)
            end_year = int(end_year)
            # 校验年份范围，无效范围返回空但不报错
            if end_year < start_year or end_year <= record.year:
                return {
                    "birth": {"year": record.year, "month": record.month,
                              "day": record.day, "hour": record.hour,
                              "gender": record.gender},
                    "dayun": [], "liunian": [], "life_stages": [],
                    "summary": "年份范围无效",
                }

            start_age = max(0, start_year - record.year)
            end_age = max(start_age, end_year - record.year)
            return self.analyzer.destiny_trajectory(
                year=record.year, month=record.month, day=record.day,
                hour=record.hour, minute=getattr(record, "minute", 0) or 0,
                gender=record.gender or "male",
                start_age=start_age, end_age=end_age,
            )
        except Exception as e:
            return {"error": f"get_trajectory failed: {e}"}

    def get_trajectory_from_bazi(
        self, bazi_input: Dict[str, Any], start_year: int, end_year: int,
    ) -> Dict[str, Any]:
        """基于内联八字数据进行命运轨迹推演（先保存记录，再推演）。"""
        try:
            record = self.create_record(bazi_input)
            if not record or "error" in record or "id" not in record:
                return {"error": f"无法创建八字记录: {record.get('error', '未知错误')}"}
            return self.get_trajectory(int(record["id"]), start_year, end_year)
        except Exception as e:
            return {"error": f"get_trajectory_from_bazi failed: {e}"}

    def batch_bazi(self, inputs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """批量排盘分析。"""
        try:
            if not inputs:
                return {"results": [], "stats": {
                    "total": 0, "success": 0, "failed": 0,
                    "day_masters": {}, "gejus": {},
                    "wuxing_totals": {"金": 0, "木": 0, "水": 0, "火": 0, "土": 0},
                }}
            # 限制最多 50 条
            inputs = list(inputs)[:50]
            result = self.analyzer.batch_bazi(inputs)
            # 确保返回结构可序列化
            return self._ensure_serializable(result)
        except Exception as e:
            return {"error": f"batch_bazi failed: {e}", "results": [], "stats": {}}

    def compare_cases(self, record_a_id: int, record_b_id: int) -> Dict[str, Any]:
        """对比两个命例。"""
        try:
            if record_a_id == record_b_id:
                # 相同记录 — 给出 100% 相似度的结果
                record = self._store.get_bazi_record(int(record_a_id))
                if record is None:
                    return {"error": f"record_id={record_a_id} 不存在"}
                return {
                    "record_a": {"id": record_a_id, "year": record.year,
                                 "month": record.month, "day": record.day,
                                 "hour": record.hour, "gender": record.gender},
                    "record_b": {"id": record_b_id, "year": record.year,
                                 "month": record.month, "day": record.day,
                                 "hour": record.hour, "gender": record.gender},
                    "similarity_score": 100.0,
                    "summary": "对比的是同一条命例，相似度 100%",
                    "day_master_same": True,
                    "geju_same": True,
                }
            return self.analyzer.compare_cases(int(record_a_id), int(record_b_id))
        except Exception as e:
            return {"error": f"compare_cases failed: {e}"}

    # ── 系统统计 ───────────────────────────────────────────────

    def get_system_stats(self) -> Dict[str, Any]:
        """获取系统统计信息。返回值保证可 JSON 序列化。"""
        try:
            base = self._store.stats() or {}
            # 添加用户数 & 简单缓存统计
            try:
                with self._store._session() as s:
                    from .data_store import User as UserModel, ReportCache
                    total_users = s.query(UserModel).count() or 0
                    active_users = (
                        s.query(UserModel).filter(UserModel.is_active == 1).count() or 0
                    )
                    cached_reports = s.query(ReportCache).count() or 0
            except Exception:
                total_users = 0
                active_users = 0
                cached_reports = 0

            # 清理 base 中不可序列化的值（如 lambda）
            top_day_masters = []
            if isinstance(base.get("top_day_masters"), list):
                for item in base["top_day_masters"]:
                    try:
                        if isinstance(item, dict):
                            top_day_masters.append({
                                "dm": str(item.get("dm", "")),
                                "count": int(item.get("count", 0)),
                            })
                        else:
                            top_day_masters.append({"dm": str(item), "count": 0})
                    except Exception:
                        continue

            recent_activity_raw = base.get("recent_activity", "")
            # 如果 recent_activity 是 function/lambda，则替换为当前时间字符串
            if callable(recent_activity_raw):
                try:
                    recent_activity_raw = recent_activity_raw()
                except Exception:
                    recent_activity_raw = None
            if isinstance(recent_activity_raw, (int, float)):
                recent_activity = str(recent_activity_raw)
            elif recent_activity_raw is None:
                recent_activity = ""
            else:
                recent_activity = str(recent_activity_raw)

            return {
                "total_users": int(total_users),
                "active_users": int(active_users),
                "total_records": int(base.get("total_records", 0)),
                "total_cases": int(base.get("total_cases", 0)),
                "total_cached_reports": int(cached_reports),
                "top_day_masters": top_day_masters,
                "cache_entries": int(len(self._config)),
                "db_path": str(base.get("db_path", "")) if base.get("db_path") else "",
                "db_size_mb": float(base.get("db_size_mb", 0) or 0),
                "recent_activity": recent_activity,
            }
        except Exception as e:
            return {
                "error": f"get_system_stats failed: {e}",
                "total_users": 0,
                "active_users": 0,
                "total_records": 0,
                "total_cases": 0,
                "total_cached_reports": 0,
                "top_day_masters": [],
                "cache_entries": 0,
                "db_path": "",
                "db_size_mb": 0.0,
                "recent_activity": "",
            }

    # ── 配置管理（简易 KV） ─────────────────────────────

    def set_config(self, key: str, value: Any) -> bool:
        """设置一个配置项。"""
        try:
            self._config[str(key)] = value
            return True
        except Exception:
            return False

    def get_config(self, key: str, default: Any = None) -> Any:
        """读取一个配置项。"""
        return self._config.get(key, default)

    def list_config(self) -> Dict[str, Any]:
        """列出所有配置项。"""
        return dict(self._config)

    # ── 内部工具 ───────────────────────────────────────────────

    @staticmethod
    def _user_to_dict(user) -> Dict[str, Any]:
        return {
            "id": getattr(user, "id", None),
            "username": getattr(user, "username", None),
            "display_name": getattr(user, "display_name", None),
            "email": getattr(user, "email", None),
            "role": getattr(user, "role", "user"),
            "is_active": bool(int(getattr(user, "is_active", 1) or 0)),
            "api_quota_daily": int(getattr(user, "api_quota_daily", 100) or 0),
            "last_login_at": (
                user.last_login_at.isoformat()
                if getattr(user, "last_login_at", None) else None
            ),
            "created_at": (
                user.created_at.isoformat()
                if getattr(user, "created_at", None) else None
            ),
        }

    @classmethod
    def _ensure_serializable(cls, obj: Any) -> Any:
        """递归确保返回对象可 JSON 序列化。"""
        if isinstance(obj, dict):
            return {str(k): cls._ensure_serializable(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [cls._ensure_serializable(v) for v in obj]
        if isinstance(obj, (datetime,)):
            return obj.isoformat()
        if isinstance(obj, (str, int, float, bool)) or obj is None:
            return obj
        # 其他类型尝试 str()
        try:
            json.dumps(obj)
            return obj
        except Exception:
            return str(obj)


# ============================================================================
# 工具函数：统一处理 pydantic 对象 / dict 输入
# ============================================================================

def _to_dict(obj: Any) -> Dict[str, Any]:
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "model_dump") and callable(obj.model_dump):
        try:
            return obj.model_dump(exclude_none=True)
        except Exception:
            pass
    if hasattr(obj, "dict") and callable(obj.dict):
        try:
            return obj.dict(exclude_none=True)
        except Exception:
            pass
    # 回退：__dict__
    if hasattr(obj, "__dict__"):
        return {k: v for k, v in obj.__dict__.items() if not k.startswith("_")}
    return {}


# ============================================================================
# 3. FastAPI 应用工厂
# ============================================================================

def create_admin_app(
    service: Optional[AdminService] = None,
    title: str = "Tengod Admin API",
) -> Any:
    """创建并返回 FastAPI 应用实例（若 fastapi 未安装则抛出清晰异常）。

    Args:
        service: 可选 AdminService 实例；若未提供将基于默认数据存储创建。
        title: 应用标题。
    """
    try:
        from fastapi import FastAPI, HTTPException, Query, Body, status
        from fastapi.responses import JSONResponse
    except Exception as e:
        raise ImportError(
            f"create_admin_app 需要 fastapi: {e}\n"
            "请执行: pip install fastapi uvicorn"
        ) from e

    # 校验 Pydantic — 若不可用则同样降级
    if not _HAS_PYDANTIC:
        raise ImportError("create_admin_app 需要 pydantic")

    admin_service = service or AdminService()

    app = FastAPI(title=title, version=__version__)

    # ── 健康检查 ─────────────────────────────────────────────
    @app.get("/api/admin/health", tags=["系统"])
    async def health():
        return {"status": "ok", "component": "admin", "version": __version__}

    # ── 统计信息 ───────────────────────────────────────────
    @app.get("/api/admin/stats", tags=["系统"])
    async def get_stats():
        try:
            return admin_service.get_system_stats()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    # ── 八字记录 CRUD ─────────────────────────────────────
    @app.get("/api/admin/records", tags=["八字记录"])
    async def list_records(
        limit: int = Query(50, ge=1, le=500),
        offset: int = Query(0, ge=0),
    ):
        return admin_service.get_records_paginated(limit=limit, offset=offset)

    @app.post("/api/admin/records", tags=["八字记录"], status_code=201)
    async def create_record_endpoint(payload: BaziRecordInput):
        result = admin_service.create_record(payload)
        if result is None or isinstance(result, dict) and result.get("error"):
            raise HTTPException(
                status_code=400,
                detail=(result or {}).get("error", "创建失败"),
            )
        return result

    @app.get("/api/admin/records/{record_id}", tags=["八字记录"])
    async def get_record_endpoint(record_id: int):
        result = admin_service.get_record(record_id)
        if result is None:
            raise HTTPException(status_code=404, detail=f"记录 {record_id} 不存在")
        return result

    @app.patch("/api/admin/records/{record_id}", tags=["八字记录"])
    async def update_record_endpoint(record_id: int, payload: BaziRecordUpdate):
        ok = admin_service.update_record(record_id, payload)
        if not ok:
            raise HTTPException(status_code=404, detail=f"记录 {record_id} 不存在或无可更新字段")
        return {"ok": True, "id": record_id}

    @app.delete("/api/admin/records/{record_id}", tags=["八字记录"])
    async def delete_record_endpoint(record_id: int):
        ok = admin_service.delete_record(record_id)
        if not ok:
            raise HTTPException(status_code=404, detail=f"记录 {record_id} 不存在")
        return {"ok": True, "id": record_id}

    # ── 案例管理 ───────────────────────────────────────────
    @app.get("/api/admin/cases", tags=["案例管理"])
    async def list_cases(
        limit: int = Query(50, ge=1, le=500),
        offset: int = Query(0, ge=0),
        category: Optional[str] = Query(None),
    ):
        return admin_service.get_cases_paginated(
            limit=limit, offset=offset, category=category,
        )

    @app.post("/api/admin/cases", tags=["案例管理"], status_code=201)
    async def create_case_endpoint(payload: CaseInput):
        result = admin_service.create_case(payload)
        if isinstance(result, dict) and result.get("error"):
            raise HTTPException(status_code=400, detail=result["error"])
        return result

    @app.patch("/api/admin/cases/{case_id}", tags=["案例管理"])
    async def update_case_endpoint(case_id: int, payload: CaseUpdate):
        ok = admin_service.update_case(case_id, payload)
        if not ok:
            raise HTTPException(status_code=404, detail=f"案例 {case_id} 不存在")
        return {"ok": True, "id": case_id}

    @app.delete("/api/admin/cases/{case_id}", tags=["案例管理"])
    async def delete_case_endpoint(case_id: int):
        ok = admin_service.delete_case(case_id)
        if not ok:
            raise HTTPException(status_code=404, detail=f"案例 {case_id} 不存在")
        return {"ok": True, "id": case_id}

    # ── 用户管理 ───────────────────────────────────────────
    @app.get("/api/admin/users", tags=["用户管理"])
    async def list_users_endpoint(limit: int = Query(50, ge=1, le=500)):
        return admin_service.get_users(limit=limit)

    @app.get("/api/admin/users/{user_id}", tags=["用户管理"])
    async def get_user_endpoint(user_id: int):
        result = admin_service.get_user(user_id)
        if result is None:
            raise HTTPException(status_code=404, detail=f"用户 {user_id} 不存在")
        return result

    @app.patch("/api/admin/users/{user_id}", tags=["用户管理"])
    async def update_user_endpoint(user_id: int, payload: UserUpdate):
        ok = admin_service.update_user(user_id, payload)
        if not ok:
            raise HTTPException(status_code=404, detail=f"用户 {user_id} 不存在")
        return {"ok": True, "id": user_id}

    # ── 高级分析 ───────────────────────────────────────────
    @app.post("/api/admin/analysis/trajectory", tags=["高级分析"])
    async def trajectory_endpoint(query: TrajectoryQuery):
        q = query.model_dump(exclude_none=True)
        if q.get("bazi_record_id"):
            result = admin_service.get_trajectory(
                int(q["bazi_record_id"]),
                int(q.get("start_year", 1900)),
                int(q.get("end_year", 2030)),
            )
        elif all(k in q for k in ("year", "month", "day", "hour")):
            result = admin_service.get_trajectory_from_bazi(
                q,
                int(q.get("start_year", 1900)),
                int(q.get("end_year", 2030)),
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="需提供 bazi_record_id 或内联的 year/month/day/hour",
            )
        if isinstance(result, dict) and result.get("error"):
            raise HTTPException(status_code=400, detail=result["error"])
        return result

    @app.post("/api/admin/analysis/batch", tags=["高级分析"])
    async def batch_endpoint(query: BatchBaziQuery):
        result = admin_service.batch_bazi(query.records)
        if isinstance(result, dict) and result.get("error"):
            raise HTTPException(status_code=400, detail=result["error"])
        return result

    @app.post("/api/admin/analysis/compare", tags=["高级分析"])
    async def compare_endpoint(query: CompareQuery):
        result = admin_service.compare_cases(query.record_a_id, query.record_b_id)
        if isinstance(result, dict) and result.get("error"):
            raise HTTPException(status_code=400, detail=result["error"])
        return result

    # ── 配置管理 ───────────────────────────────────────────
    @app.post("/api/admin/config", tags=["系统"])
    async def set_config_endpoint(payload: ConfigUpdate):
        ok = admin_service.set_config(payload.key, payload.value)
        if not ok:
            raise HTTPException(status_code=400, detail="写入失败")
        return {"key": payload.key, "value": payload.value, "ok": True}

    @app.get("/api/admin/config", tags=["系统"])
    async def list_config_endpoint():
        return admin_service.list_config()

    return app


# ============================================================================
# 4. 独立运行入口与自测
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Tengod Admin API 自测 v" + __version__)
    print("=" * 60)

    # 4.1 创建 AdminService（使用临时 SQLite）
    db_path = os.path.join(tempfile.gettempdir(), "tengod_admin_selftest.db")
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except Exception:
            pass

    service = AdminService(db_path=db_path)
    print(f"[OK] AdminService 初始化成功 (db: {db_path})")

    # 4.2 创建测试记录
    record = service.create_record({
        "year": 1990, "month": 6, "day": 15, "hour": 10, "minute": 30,
        "gender": "male", "label": "自测试八字",
    })
    if isinstance(record, dict) and "id" in record and "error" not in record:
        print(f"[OK] 创建八字记录 id={record['id']}（日主字段: {record.get('day_master')}）")
    else:
        print(f"[!] 创建八字记录: {record}")

    # 4.3 调用 get_trajectory
    rid = record["id"] if isinstance(record, dict) and record.get("id") else 1
    trajectory = service.get_trajectory(rid, 1990, 2030)
    if isinstance(trajectory, dict) and "error" not in trajectory:
        dayun = trajectory.get("dayun", [])
        liunian = trajectory.get("liunian", [])
        print(f"[OK] 命运轨迹推演完成：大运 {len(dayun)} 步，流年 {len(liunian)} 条")
        print(f"     summary: {trajectory.get('summary', '')[:60]}")
    else:
        print(f"[!] 轨迹推演异常: {trajectory.get('error', 'unknown')}")

    # 4.4 系统统计
    stats = service.get_system_stats()
    print(f"[OK] 系统统计 — users: {stats.get('total_users')}, "
          f"records: {stats.get('total_records')}")

    # 4.5 FastAPI 路由信息
    try:
        app = create_admin_app(service=service)
        routes = [getattr(r, "path", None) for r in getattr(app, "routes", [])
                  if getattr(r, "path", None)]
        print(f"[OK] FastAPI 应用已创建，共 {len(routes)} 个路由")
        for r in sorted(set(routes))[:8]:
            print(f"     - {r}")
    except Exception as e:
        print(f"[!] FastAPI 不可用（{type(e).__name__}: {e}），但 AdminService 可正常工作")

    # 4.6 清理
    try:
        os.remove(db_path)
    except Exception:
        pass

    print("\n自测完成。")
