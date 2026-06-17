#!/usr/bin/env python3
"""
data_store.py — 正财·知识固化 · 数据持久化层 v1.0.0

SQLite + SQLAlchemy ORM，提供八字排盘记录、用户、报告缓存的持久化存储。

数据模型：
  - User: 用户表
  - BaziRecord: 八字排盘记录表
  - ReportCache: 报告缓存表

用法：
  >>> from tengod.data_store import DataStore
  >>> store = DataStore()
  >>> record_id = store.save_bazi_record(year=1990, month=6, day=15, ...)
  >>> records = store.list_bazi_records()
  >>> store.get_bazi_record(record_id)
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import (
    Column, Integer, String, Float, Text, DateTime, ForeignKey,
    create_engine, Index, func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship

# ============================================================================
# 数据库路径
# ============================================================================

DEFAULT_DB_PATH = os.environ.get(
    "TENGOD_DB_PATH",
    str(Path(__file__).resolve().parent.parent / "data" / "tengod.db"),
)

# 数据库 URL（优先使用环境变量，支持 PostgreSQL）
# 示例: postgresql://tengod:secret@db:5432/tengod
DATABASE_URL = os.environ.get("TENGOD_DATABASE_URL", "")


# ============================================================================
# ORM 模型
# ============================================================================

class Base(DeclarativeBase):
    pass


class User(Base):
    """用户表"""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(128), nullable=True)
    # 阶段十三：认证字段
    password_hash: Mapped[str] = mapped_column(String(256), nullable=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="user")  # admin/user/guest
    email: Mapped[str] = mapped_column(String(128), nullable=True, index=True)
    is_active: Mapped[int] = mapped_column(Integer, nullable=False, default=1)  # 1=活跃 0=禁用
    # API 配额
    api_quota_daily: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    records: Mapped[List["BaziRecord"]] = relationship(back_populates="user", lazy="select")

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username!r}, role={self.role!r})>"


class BaziRecord(Base):
    """八字排盘记录表"""
    __tablename__ = "bazi_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    label: Mapped[str] = mapped_column(String(128), nullable=True)

    # 出生时间
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    day: Mapped[int] = mapped_column(Integer, nullable=False)
    hour: Mapped[int] = mapped_column(Integer, nullable=False)
    minute: Mapped[int] = mapped_column(Integer, default=0)
    gender: Mapped[str] = mapped_column(String(8), nullable=False, default="male")
    longitude: Mapped[float] = mapped_column(Float, default=116.4)
    latitude: Mapped[float] = mapped_column(Float, default=39.9)

    # 计算结果（JSON 存储）
    day_master: Mapped[str] = mapped_column(String(8), nullable=True)
    pillars_json: Mapped[str] = mapped_column(Text, nullable=True)
    analysis_json: Mapped[str] = mapped_column(Text, nullable=True)
    shensha_json: Mapped[str] = mapped_column(Text, nullable=True)
    geju_json: Mapped[str] = mapped_column(Text, nullable=True)
    yongshen_json: Mapped[str] = mapped_column(Text, nullable=True)
    tiaohou_json: Mapped[str] = mapped_column(Text, nullable=True)

    # 元数据
    tags: Mapped[str] = mapped_column(String(256), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc), nullable=False
    )

    user: Mapped[Optional["User"]] = relationship(back_populates="records")
    report_cache: Mapped[List["ReportCache"]] = relationship(
        back_populates="bazi_record", lazy="select", cascade="all, delete-orphan"
    )

    # 复合索引
    __table_args__ = (
        Index("idx_bazi_user_created", "user_id", "created_at"),
        Index("idx_bazi_date", "year", "month", "day"),
        Index("idx_bazi_day_master", "day_master"),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "label": self.label,
            "year": self.year, "month": self.month, "day": self.day,
            "hour": self.hour, "minute": self.minute,
            "gender": self.gender,
            "longitude": self.longitude, "latitude": self.latitude,
            "day_master": self.day_master,
            "pillars": json.loads(self.pillars_json) if self.pillars_json else None,
            "analysis": json.loads(self.analysis_json) if self.analysis_json else None,
            "shensha": json.loads(self.shensha_json) if self.shensha_json else None,
            "geju": json.loads(self.geju_json) if self.geju_json else None,
            "yongshen": json.loads(self.yongshen_json) if self.yongshen_json else None,
            "tiaohou": json.loads(self.tiaohou_json) if self.tiaohou_json else None,
            "tags": self.tags,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<BaziRecord(id={self.id}, {self.year}-{self.month}-{self.day}, {self.gender})>"


class ReportCache(Base):
    """报告缓存表"""
    __tablename__ = "report_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bazi_record_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("bazi_records.id", ondelete="CASCADE"), nullable=False, index=True
    )
    format: Mapped[str] = mapped_column(String(16), nullable=False, default="text")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    bazi_record: Mapped["BaziRecord"] = relationship(back_populates="report_cache")

    __table_args__ = (
        Index("idx_report_record_format", "bazi_record_id", "format"),
    )

    def __repr__(self):
        return f"<ReportCache(id={self.id}, record={self.bazi_record_id}, format={self.format!r})>"


# ============================================================================
# DataStore 核心类
# ============================================================================

class DataStore:
    """数据持久化存储（支持 SQLite 和 PostgreSQL）"""

    def __init__(self, db_path: Optional[str] = None, db_url: Optional[str] = None):
        # 优先使用 db_url（PostgreSQL），其次 db_path（SQLite）
        url = db_url or DATABASE_URL
        if url:
            # PostgreSQL 模式
            self.db_url = url
            self.db_path = None
            self._engine = create_engine(url, echo=False, pool_pre_ping=True, pool_size=10, max_overflow=20)
        else:
            # SQLite 模式（默认）
            self.db_path = db_path or DEFAULT_DB_PATH
            self.db_url = None
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            self._engine = create_engine(
                f"sqlite:///{self.db_path}",
                echo=False,
                connect_args={"check_same_thread": False},
            )
        Base.metadata.create_all(self._engine)

    def _session(self) -> Session:
        return Session(self._engine)

    # ── 用户管理 ──────────────────────────────────────────────────────────

    def get_or_create_user(self, username: str, display_name: str = None) -> User:
        """获取或创建用户"""
        with self._session() as s:
            user = s.query(User).filter(User.username == username).first()
            if user is None:
                user = User(username=username, display_name=display_name or username)
                s.add(user)
                s.commit()
                s.refresh(user)
            return user

    def get_user(self, user_id: int) -> Optional[User]:
        with self._session() as s:
            return s.query(User).filter(User.id == user_id).first()

    def list_users(self, limit: int = 50) -> List[User]:
        with self._session() as s:
            return s.query(User).order_by(User.created_at.desc()).limit(limit).all()

    # ── 八字记录 CRUD ─────────────────────────────────────────────────────

    def save_bazi_record(
        self,
        year: int, month: int, day: int, hour: int, minute: int = 0,
        gender: str = "male", longitude: float = 116.4, latitude: float = 39.9,
        user_id: Optional[int] = None, label: str = None,
        day_master: str = None,
        pillars: Dict = None,
        analysis: Dict = None,
        shensha: Dict = None,
        geju: Dict = None,
        yongshen: Dict = None,
        tiaohou: Dict = None,
        tags: str = None, notes: str = None,
    ) -> int:
        """保存八字排盘记录，返回记录 ID"""
        with self._session() as s:
            record = BaziRecord(
                user_id=user_id, label=label,
                year=year, month=month, day=day, hour=hour, minute=minute,
                gender=gender, longitude=longitude, latitude=latitude,
                day_master=day_master,
                pillars_json=json.dumps(pillars, ensure_ascii=False) if pillars else None,
                analysis_json=json.dumps(analysis, ensure_ascii=False) if analysis else None,
                shensha_json=json.dumps(shensha, ensure_ascii=False) if shensha else None,
                geju_json=json.dumps(geju, ensure_ascii=False) if geju else None,
                yongshen_json=json.dumps(yongshen, ensure_ascii=False) if yongshen else None,
                tiaohou_json=json.dumps(tiaohou, ensure_ascii=False) if tiaohou else None,
                tags=tags, notes=notes,
            )
            s.add(record)
            s.commit()
            s.refresh(record)
            return record.id

    def get_bazi_record(self, record_id: int) -> Optional[BaziRecord]:
        """获取单条八字记录"""
        with self._session() as s:
            return s.query(BaziRecord).filter(BaziRecord.id == record_id).first()

    def list_bazi_records(
        self,
        user_id: Optional[int] = None,
        limit: int = 50,
        offset: int = 0,
        order_by: str = "created_at_desc",
    ) -> List[BaziRecord]:
        """列出八字记录（支持分页、排序）"""
        with self._session() as s:
            q = s.query(BaziRecord)
            if user_id is not None:
                q = q.filter(BaziRecord.user_id == user_id)
            if order_by == "created_at_asc":
                q = q.order_by(BaziRecord.created_at.asc())
            else:
                q = q.order_by(BaziRecord.created_at.desc())
            return q.offset(offset).limit(limit).all()

    def search_bazi_records(
        self,
        year: Optional[int] = None,
        month: Optional[int] = None,
        day_master: Optional[str] = None,
        gender: Optional[str] = None,
        tag: Optional[str] = None,
        limit: int = 50,
    ) -> List[BaziRecord]:
        """搜索八字记录"""
        with self._session() as s:
            q = s.query(BaziRecord)
            if year is not None:
                q = q.filter(BaziRecord.year == year)
            if month is not None:
                q = q.filter(BaziRecord.month == month)
            if day_master is not None:
                q = q.filter(BaziRecord.day_master == day_master)
            if gender is not None:
                q = q.filter(BaziRecord.gender == gender)
            if tag is not None:
                q = q.filter(BaziRecord.tags.contains(tag))
            return q.order_by(BaziRecord.created_at.desc()).limit(limit).all()

    def update_bazi_record(self, record_id: int, **kwargs) -> bool:
        """更新八字记录"""
        with self._session() as s:
            record = s.query(BaziRecord).filter(BaziRecord.id == record_id).first()
            if record is None:
                return False
            for key, value in kwargs.items():
                if hasattr(record, key):
                    setattr(record, key, value)
            record.updated_at = datetime.now(timezone.utc)
            s.commit()
            return True

    def delete_bazi_record(self, record_id: int) -> bool:
        """删除八字记录"""
        with self._session() as s:
            record = s.query(BaziRecord).filter(BaziRecord.id == record_id).first()
            if record is None:
                return False
            s.delete(record)
            s.commit()
            return True

    def count_bazi_records(self, user_id: Optional[int] = None) -> int:
        """统计八字记录数量"""
        with self._session() as s:
            q = s.query(func.count(BaziRecord.id))
            if user_id is not None:
                q = q.filter(BaziRecord.user_id == user_id)
            return q.scalar() or 0

    # ── 报告缓存 ──────────────────────────────────────────────────────────

    def cache_report(self, record_id: int, format: str, content: str) -> int:
        """缓存报告（按内容和格式去重，使用 SQLite 的 hash 索引）"""
        import hashlib
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        with self._session() as s:
            # 查重
            existing = (
                s.query(ReportCache)
                .filter(
                    ReportCache.bazi_record_id == record_id,
                    ReportCache.format == format,
                    ReportCache.content_hash == content_hash,
                )
                .first()
            )
            if existing:
                return existing.id

            cache = ReportCache(
                bazi_record_id=record_id,
                format=format,
                content=content,
                content_hash=content_hash,
            )
            s.add(cache)
            s.commit()
            s.refresh(cache)
            return cache.id

    def get_cached_report(self, record_id: int, format: str = "text") -> Optional[str]:
        """获取缓存的报告"""
        with self._session() as s:
            cache = (
                s.query(ReportCache)
                .filter(
                    ReportCache.bazi_record_id == record_id,
                    ReportCache.format == format,
                )
                .order_by(ReportCache.created_at.desc())
                .first()
            )
            return cache.content if cache else None

    def clear_report_cache(self, record_id: Optional[int] = None) -> int:
        """清除报告缓存"""
        with self._session() as s:
            q = s.query(ReportCache)
            if record_id is not None:
                q = q.filter(ReportCache.bazi_record_id == record_id)
            count = q.count()
            q.delete()
            s.commit()
            return count

    # ── 统计 ──────────────────────────────────────────────────────────────

    def stats(self) -> Dict[str, Any]:
        """数据库统计信息"""
        with self._session() as s:
            db_info: Dict[str, Any] = {}
            if self.db_path:
                db_info["db_path"] = self.db_path
                db_info["db_size_mb"] = round(os.path.getsize(self.db_path) / 1024 / 1024, 2) if os.path.exists(self.db_path) else 0
            else:
                db_info["db_url"] = self.db_url
                db_info["db_type"] = "postgresql"
            return {
                **db_info,
                "total_users": s.query(func.count(User.id)).scalar() or 0,
                "total_records": s.query(func.count(BaziRecord.id)).scalar() or 0,
                "total_cached_reports": s.query(func.count(ReportCache.id)).scalar() or 0,
                "top_day_masters": [
                    {"dm": r[0], "count": r[1]}
                    for r in s.query(BaziRecord.day_master, func.count(BaziRecord.id))
                    .filter(BaziRecord.day_master.isnot(None))
                    .group_by(BaziRecord.day_master)
                    .order_by(func.count(BaziRecord.id).desc())
                    .limit(5)
                    .all()
                ],
                "recent_activity": (
                    BaziRecord.created_at.default.arg if hasattr(BaziRecord.created_at.default, 'arg')
                    else str(datetime.now(timezone.utc))
                ),
            }

    # ── 备份与恢复 ──────────────────────────────────────────────────────────

    def backup(self, backup_path: Optional[str] = None) -> str:
        """备份数据库到指定路径（SQLite 模式下文件复制，PostgreSQL 模式下导出 JSON）"""
        import shutil
        if self.db_path:
            if backup_path is None:
                backup_path = f"{self.db_path}.backup.{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
            shutil.copy2(self.db_path, backup_path)
            return backup_path
        # PostgreSQL 模式：导出为 JSON
        if backup_path is None:
            backup_path = f"tengod_backup_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
        data = self._export_all()
        with open(backup_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        return backup_path

    def restore(self, backup_path: str) -> bool:
        """从备份恢复数据库"""
        if not os.path.exists(backup_path):
            return False
        if self.db_path:
            import shutil
            self.backup()
            shutil.copy2(backup_path, self.db_path)
            return True
        # PostgreSQL 模式：从 JSON 导入
        with open(backup_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return self._import_all(data)

    def _export_all(self) -> Dict[str, Any]:
        """导出所有数据为字典"""
        with self._session() as s:
            return {
                "users": [
                    {"id": u.id, "username": u.username, "display_name": u.display_name,
                     "created_at": str(u.created_at)}
                    for u in s.query(User).all()
                ],
                "records": [
                    {"id": r.id, "user_id": r.user_id, "label": r.label,
                     "year": r.year, "month": r.month, "day": r.day,
                     "hour": r.hour, "minute": r.minute, "gender": r.gender,
                     "calendar": r.calendar, "day_master": r.day_master,
                     "bazi_json": r.bazi_json, "created_at": str(r.created_at)}
                    for r in s.query(BaziRecord).all()
                ],
            }

    def _import_all(self, data: Dict[str, Any]) -> bool:
        """从字典导入数据"""
        with self._session() as s:
            for u in data.get("users", []):
                existing = s.query(User).filter(User.username == u["username"]).first()
                if not existing:
                    s.add(User(username=u["username"], display_name=u.get("display_name")))
            s.commit()
            return True

    def close(self):
        self._engine.dispose()


# ============================================================================
# 单例
# ============================================================================

_store: Optional[DataStore] = None


def get_data_store(db_path: Optional[str] = None) -> DataStore:
    """获取全局 DataStore 实例"""
    global _store
    if _store is None:
        _store = DataStore(db_path)
    return _store


# ============================================================================
# 自测
# ============================================================================

if __name__ == "__main__":
    import tempfile

    # 使用临时文件进行测试
    db_path = os.path.join(tempfile.gettempdir(), "tengod_test.db")
    if os.path.exists(db_path):
        os.remove(db_path)

    store = DataStore(db_path)
    print(f"数据库路径: {db_path}")

    # 测试用户
    user = store.get_or_create_user("test_user", "测试用户")
    print(f"创建用户: {user}")

    # 测试保存记录
    record_id = store.save_bazi_record(
        year=1990, month=6, day=15, hour=10, minute=30,
        gender="male", user_id=user.id, label="测试八字",
        day_master="辛",
        pillars={"year": "庚午", "month": "壬午", "day": "辛亥", "hour": "癸巳"},
        analysis={"conclusion": "测试分析"},
        shensha={"total": 12},
        geju={"name": "伤官格"},
        tags="测试,演示",
    )
    print(f"保存记录: id={record_id}")

    # 测试查询
    record = store.get_bazi_record(record_id)
    print(f"查询记录: {record}")
    d = record.to_dict()
    print(f"  日主: {d['day_master']}, 格局: {d['geju']['name']}")

    # 测试列表
    records = store.list_bazi_records(limit=10)
    print(f"记录列表: {len(records)} 条")

    # 测试搜索
    results = store.search_bazi_records(day_master="辛")
    print(f"搜索日主=辛: {len(results)} 条")

    # 测试报告缓存
    cache_id = store.cache_report(record_id, "text", "这是一份测试报告")
    print(f"缓存报告: id={cache_id}")
    cached = store.get_cached_report(record_id, "text")
    print(f"读取缓存: {len(cached)} 字符")

    # 测试统计
    stats = store.stats()
    print(f"统计: {stats['total_records']} 条记录, {stats['total_cached_reports']} 条缓存")

    # 测试备份
    backup_path = store.backup()
    print(f"备份: {backup_path}")

    # 清理
    store.delete_bazi_record(record_id)
    print(f"删除后: {store.count_bazi_records()} 条记录")

    # 测试恢复
    ok = store.restore(backup_path)
    print(f"恢复: {'成功' if ok else '失败'}, {store.count_bazi_records()} 条记录")

    store.close()
    os.remove(db_path)
    if os.path.exists(backup_path):
        os.remove(backup_path)

    print("\n所有测试通过!")