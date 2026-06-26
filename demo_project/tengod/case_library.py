#!/usr/bin/env python3
"""
case_library.py — 阶段十八 · 命例案例库 v1.0.0

基于 BaziRecord 扩展的命例案例库，支持：
  - 案例分类（富贵/贫贱/吉凶/寿夭/婚姻/事业/疾病/灾厄 等）
  - 结构化标签管理
  - 多维度搜索（分类/标签/格局/神煞/五行/日主/关键词）
  - 案例导入导出（JSON/CSV）
  - 相似案例推荐（基于格局/日主/五行相似度）
  - 案例关联（同格局/同日主/对比案例）

设计原则：
  - 复用 data_store.py 的 Base 和 BaziRecord
  - Case 表通过 record_id 关联 BaziRecord（一对一）
  - 不破坏现有 /api/records 端点

用法：
  >>> from tengod.case_library import CaseLibrary
  >>> lib = CaseLibrary()
  >>> case_id = lib.create_case(record_id=1, category="事业", title="某企业家命例")
  >>> cases = lib.search_cases(category="事业", geju="伤官格")
"""
from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Column, Integer, String, Float, Text, DateTime, ForeignKey,
    Index, func, Boolean,
)
from sqlalchemy.orm import Session

from .data_store import Base, DataStore, BaziRecord, get_data_store


# ============================================================================
# 案例库 ORM 模型
# ============================================================================

class Case(Base):
    """命例案例表 — 扩展 BaziRecord 的案例信息"""
    __tablename__ = "cases"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    record_id: int = Column(
        Integer, ForeignKey("bazi_records.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True,
    )
    title: str = Column(String(256), nullable=False)
    category: str = Column(String(64), nullable=True, index=True)  # 富贵/贫贱/吉凶/寿夭/婚姻/事业/疾病/灾厄
    source: str = Column(String(128), nullable=True)  # 案例来源（如《滴天髓》《子平真诠》）
    credibility: float = Column(Float, default=0.8)  # 可信度 0-1
    is_public: bool = Column(Boolean, default=True)
    is_featured: bool = Column(Boolean, default=False)  # 是否精选案例

    # 案例分析
    summary: str = Column(Text, nullable=True)  # 案例摘要
    analysis_text: str = Column(Text, nullable=True)  # 详细分析
    conclusion: str = Column(Text, nullable=True)  # 结论

    # 互动数据
    view_count: int = Column(Integer, default=0)
    favorite_count: int = Column(Integer, default=0)
    like_count: int = Column(Integer, default=0)

    # 元数据
    tags: str = Column(String(512), nullable=True)  # 逗号分隔标签
    created_at: datetime = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    updated_at: datetime = Column(
        DateTime, default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc), nullable=False,
    )

    __table_args__ = (
        Index("idx_case_category", "category"),
        Index("idx_case_public_featured", "is_public", "is_featured"),
    )

    def to_dict(self, include_record: bool = False) -> Dict[str, Any]:
        result = {
            "id": self.id,
            "record_id": self.record_id,
            "title": self.title,
            "category": self.category,
            "source": self.source,
            "credibility": self.credibility,
            "is_public": self.is_public,
            "is_featured": self.is_featured,
            "summary": self.summary,
            "analysis_text": self.analysis_text,
            "conclusion": self.conclusion,
            "view_count": self.view_count,
            "favorite_count": self.favorite_count,
            "like_count": self.like_count,
            "tags": self.tags.split(",") if self.tags else [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_record and hasattr(self, "_record_data"):
            result["record"] = self._record_data
        return result


class CaseRelation(Base):
    """案例关联表 — 案例间的关系（相似/对比/引用/同格局/同日主）"""
    __tablename__ = "case_relations"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    case_a_id: int = Column(
        Integer, ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    case_b_id: int = Column(
        Integer, ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    relation_type: str = Column(String(32), nullable=False)  # similar/contrast/cite/same_geju/same_dm
    similarity_score: float = Column(Float, default=0.0)  # 相似度 0-1
    note: str = Column(String(256), nullable=True)
    created_at: datetime = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False,
    )

    __table_args__ = (
        Index("idx_relation_ab", "case_a_id", "case_b_id"),
        Index("idx_relation_type", "relation_type"),
    )


# ============================================================================
# 预定义分类
# ============================================================================

DEFAULT_CATEGORIES = [
    "富贵", "贫贱", "吉凶", "寿夭",
    "婚姻", "事业", "疾病", "灾厄",
    "学业", "子女", "财运", "官运",
    "其他",
]


# ============================================================================
# CaseLibrary 核心类
# ============================================================================

class CaseLibrary:
    """命例案例库管理器"""

    def __init__(self, store: Optional[DataStore] = None):
        self.store = store or get_data_store()
        # 确保新表已创建（checkfirst=True 避免重复创建报错）
        Base.metadata.create_all(self.store._engine, checkfirst=True)

    def _session(self) -> Session:
        return self.store._session()

    # ── 案例 CRUD ──────────────────────────────────────────────────────────

    def create_case(
        self,
        record_id: int,
        title: str,
        category: Optional[str] = None,
        source: Optional[str] = None,
        credibility: float = 0.8,
        is_public: bool = True,
        is_featured: bool = False,
        summary: Optional[str] = None,
        analysis_text: Optional[str] = None,
        conclusion: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> int:
        """创建案例，返回案例 ID"""
        with self._session() as s:
            # 验证 record 存在
            record = s.query(BaziRecord).filter(BaziRecord.id == record_id).first()
            if record is None:
                raise ValueError(f"BaziRecord {record_id} 不存在")

            case = Case(
                record_id=record_id,
                title=title,
                category=category,
                source=source,
                credibility=credibility,
                is_public=is_public,
                is_featured=is_featured,
                summary=summary,
                analysis_text=analysis_text,
                conclusion=conclusion,
                tags=",".join(tags) if tags else None,
            )
            s.add(case)
            s.commit()
            s.refresh(case)
            return case.id

    def get_case(self, case_id: int, increment_view: bool = False) -> Optional[Dict[str, Any]]:
        """获取案例详情"""
        with self._session() as s:
            case = s.query(Case).filter(Case.id == case_id).first()
            if case is None:
                return None

            if increment_view:
                case.view_count = (case.view_count or 0) + 1
                s.commit()

            result = case.to_dict(include_record=False)
            # 附带关联的 BaziRecord 信息
            record = s.query(BaziRecord).filter(BaziRecord.id == case.record_id).first()
            if record:
                result["record"] = record.to_dict()
            return result

    def list_cases(
        self,
        category: Optional[str] = None,
        is_public: Optional[bool] = None,
        is_featured: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0,
        order_by: str = "created_desc",  # created_desc/created_asc/views/favorites
    ) -> Dict[str, Any]:
        """列出案例（支持分页、筛选、排序）"""
        with self._session() as s:
            q = s.query(Case)
            if category is not None:
                q = q.filter(Case.category == category)
            if is_public is not None:
                q = q.filter(Case.is_public == is_public)
            if is_featured is not None:
                q = q.filter(Case.is_featured == is_featured)

            total = q.count()

            if order_by == "created_asc":
                q = q.order_by(Case.created_at.asc())
            elif order_by == "views":
                q = q.order_by(Case.view_count.desc())
            elif order_by == "favorites":
                q = q.order_by(Case.favorite_count.desc())
            else:  # created_desc
                q = q.order_by(Case.created_at.desc())

            cases = q.offset(offset).limit(limit).all()
            return {
                "total": total,
                "limit": limit,
                "offset": offset,
                "cases": [c.to_dict() for c in cases],
            }

    def update_case(self, case_id: int, **kwargs) -> bool:
        """更新案例"""
        with self._session() as s:
            case = s.query(Case).filter(Case.id == case_id).first()
            if case is None:
                return False
            for key, value in kwargs.items():
                if key == "tags" and isinstance(value, list):
                    value = ",".join(value)
                if hasattr(case, key):
                    setattr(case, key, value)
            case.updated_at = datetime.now(timezone.utc)
            s.commit()
            return True

    def delete_case(self, case_id: int) -> bool:
        """删除案例"""
        with self._session() as s:
            case = s.query(Case).filter(Case.id == case_id).first()
            if case is None:
                return False
            s.delete(case)
            s.commit()
            return True

    # ── 多维度搜索 ─────────────────────────────────────────────────────────

    def search_cases(
        self,
        keyword: Optional[str] = None,
        category: Optional[str] = None,
        tag: Optional[str] = None,
        day_master: Optional[str] = None,
        geju: Optional[str] = None,
        gender: Optional[str] = None,
        source: Optional[str] = None,
        is_public: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """多维度搜索案例

        支持按关键词（标题/摘要/分析）、分类、标签、日主、格局、性别、来源搜索。
        """
        with self._session() as s:
            q = s.query(Case).join(BaziRecord, Case.record_id == BaziRecord.id)

            if keyword:
                kw = f"%{keyword}%"
                q = q.filter(
                    (Case.title.like(kw)) |
                    (Case.summary.like(kw)) |
                    (Case.analysis_text.like(kw)) |
                    (Case.conclusion.like(kw))
                )
            if category:
                q = q.filter(Case.category == category)
            if tag:
                q = q.filter(Case.tags.contains(tag))
            if day_master:
                q = q.filter(BaziRecord.day_master == day_master)
            if gender:
                q = q.filter(BaziRecord.gender == gender)
            if source:
                q = q.filter(Case.source.contains(source))
            if is_public is not None:
                q = q.filter(Case.is_public == is_public)

            # 格局搜索（需解析 geju_json）
            if geju:
                q = q.filter(BaziRecord.geju_json.contains(f'"geju_name": "{geju}"'))

            total = q.count()
            cases = q.order_by(Case.created_at.desc()).offset(offset).limit(limit).all()

            return {
                "total": total,
                "limit": limit,
                "offset": offset,
                "cases": [c.to_dict() for c in cases],
            }

    # ── 分类与标签 ─────────────────────────────────────────────────────────

    def list_categories(self) -> List[Dict[str, Any]]:
        """列出所有分类及其案例数"""
        with self._session() as s:
            rows = (
                s.query(Case.category, func.count(Case.id))
                .filter(Case.category.isnot(None))
                .group_by(Case.category)
                .order_by(func.count(Case.id).desc())
                .all()
            )
            return [{"name": r[0], "count": r[1]} for r in rows]

    def list_tags(self) -> List[Dict[str, Any]]:
        """列出所有标签及其使用次数"""
        with self._session() as s:
            cases = s.query(Case.tags).filter(Case.tags.isnot(None)).all()
            tag_count: Dict[str, int] = {}
            for (tags_str,) in cases:
                for t in tags_str.split(","):
                    t = t.strip()
                    if t:
                        tag_count[t] = tag_count.get(t, 0) + 1
            return sorted(
                [{"name": k, "count": v} for k, v in tag_count.items()],
                key=lambda x: -x["count"],
            )

    # ── 互动 ──────────────────────────────────────────────────────────────

    def increment_view(self, case_id: int) -> bool:
        with self._session() as s:
            case = s.query(Case).filter(Case.id == case_id).first()
            if case is None:
                return False
            case.view_count = (case.view_count or 0) + 1
            s.commit()
            return True

    def toggle_favorite(self, case_id: int) -> Optional[int]:
        """切换收藏状态，返回新的收藏数"""
        with self._session() as s:
            case = s.query(Case).filter(Case.id == case_id).first()
            if case is None:
                return None
            case.favorite_count = max(0, (case.favorite_count or 0) + 1)
            s.commit()
            return case.favorite_count

    def toggle_like(self, case_id: int) -> Optional[int]:
        """切换点赞状态，返回新的点赞数"""
        with self._session() as s:
            case = s.query(Case).filter(Case.id == case_id).first()
            if case is None:
                return None
            case.like_count = max(0, (case.like_count or 0) + 1)
            s.commit()
            return case.like_count

    # ── 案例关联 ──────────────────────────────────────────────────────────

    def link_cases(
        self,
        case_a_id: int,
        case_b_id: int,
        relation_type: str = "similar",
        similarity_score: float = 0.0,
        note: Optional[str] = None,
    ) -> int:
        """建立案例关联，返回关联 ID"""
        if case_a_id == case_b_id:
            raise ValueError("不能关联自己")
        with self._session() as s:
            rel = CaseRelation(
                case_a_id=case_a_id,
                case_b_id=case_b_id,
                relation_type=relation_type,
                similarity_score=similarity_score,
                note=note,
            )
            s.add(rel)
            s.commit()
            s.refresh(rel)
            return rel.id

    def get_relations(self, case_id: int, relation_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取案例的关联案例"""
        with self._session() as s:
            q = s.query(CaseRelation).filter(
                (CaseRelation.case_a_id == case_id) |
                (CaseRelation.case_b_id == case_id)
            )
            if relation_type:
                q = q.filter(CaseRelation.relation_type == relation_type)
            rels = q.all()
            result = []
            for rel in rels:
                other_id = rel.case_b_id if rel.case_a_id == case_id else rel.case_a_id
                other_case = s.query(Case).filter(Case.id == other_id).first()
                if other_case:
                    result.append({
                        "relation_id": rel.id,
                        "other_case_id": other_id,
                        "other_title": other_case.title,
                        "other_category": other_case.category,
                        "relation_type": rel.relation_type,
                        "similarity_score": rel.similarity_score,
                        "note": rel.note,
                    })
            return result

    # ── 相似案例推荐 ──────────────────────────────────────────────────────

    def find_similar_cases(
        self,
        case_id: int,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """基于格局/日主/五行相似度推荐相似案例

        相似度计算：
          - 同日主 +30%
          - 同格局 +40%
          - 五行分布相似度 +30%
        """
        with self._session() as s:
            target_case = s.query(Case).filter(Case.id == case_id).first()
            if target_case is None:
                return []

            target_record = s.query(BaziRecord).filter(
                BaziRecord.id == target_case.record_id
            ).first()
            if target_record is None:
                return []

            target_dm = target_record.day_master
            target_geju = self._extract_geju_name(target_record)
            target_wuxing = self._extract_wuxing(target_record)

            # 获取所有其他案例
            other_cases = (
                s.query(Case, BaziRecord)
                .join(BaziRecord, Case.record_id == BaziRecord.id)
                .filter(Case.id != case_id)
                .filter(Case.is_public == True)  # noqa: E712
                .limit(200)
                .all()
            )

            scored = []
            for case, record in other_cases:
                score = 0.0
                # 同日主
                if target_dm and record.day_master == target_dm:
                    score += 0.3
                # 同格局
                other_geju = self._extract_geju_name(record)
                if target_geju and other_geju and target_geju == other_geju:
                    score += 0.4
                # 五行相似度
                other_wuxing = self._extract_wuxing(record)
                if target_wuxing and other_wuxing:
                    wuxing_sim = self._wuxing_similarity(target_wuxing, other_wuxing)
                    score += 0.3 * wuxing_sim

                if score > 0:
                    scored.append({
                        "case_id": case.id,
                        "title": case.title,
                        "category": case.category,
                        "day_master": record.day_master,
                        "similarity_score": round(score, 3),
                    })

            scored.sort(key=lambda x: -x["similarity_score"])
            return scored[:limit]

    def _extract_geju_name(self, record: BaziRecord) -> Optional[str]:
        """从记录中提取格局名称"""
        if not record.geju_json:
            return None
        try:
            data = json.loads(record.geju_json)
            return data.get("geju_name")
        except (json.JSONDecodeError, TypeError):
            return None

    def _extract_wuxing(self, record: BaziRecord) -> Optional[Dict[str, int]]:
        """从记录中提取五行分布"""
        if not record.analysis_json:
            return None
        try:
            data = json.loads(record.analysis_json)
            return data.get("wuxing")
        except (json.JSONDecodeError, TypeError):
            return None

    @staticmethod
    def _wuxing_similarity(w1: Dict[str, int], w2: Dict[str, int]) -> float:
        """计算两个五行分布的相似度（余弦相似度）"""
        import math
        elements = ["木", "火", "土", "金", "水"]
        v1 = [w1.get(e, 0) for e in elements]
        v2 = [w2.get(e, 0) for e in elements]
        dot = sum(a * b for a, b in zip(v1, v2))
        mag1 = math.sqrt(sum(a * a for a in v1))
        mag2 = math.sqrt(sum(b * b for b in v2))
        if mag1 == 0 or mag2 == 0:
            return 0.0
        return dot / (mag1 * mag2)

    # ── 导入导出 ──────────────────────────────────────────────────────────

    def export_cases(
        self,
        case_ids: Optional[List[int]] = None,
        format: str = "json",  # json/csv
    ) -> str:
        """导出案例

        Args:
            case_ids: 指定案例ID列表（None=全部）
            format: json 或 csv

        Returns:
            导出内容字符串
        """
        with self._session() as s:
            q = s.query(Case).join(BaziRecord, Case.record_id == BaziRecord.id)
            if case_ids:
                q = q.filter(Case.id.in_(case_ids))
            rows = q.all()

            if format == "csv":
                return self._export_csv(rows, s)
            else:
                return self._export_json(rows, s)

    def _export_json(self, cases: List[Case], session: Session) -> str:
        result = []
        for case in cases:
            record = session.query(BaziRecord).filter(
                BaziRecord.id == case.record_id
            ).first()
            item = case.to_dict()
            if record:
                item["record"] = {
                    "year": record.year, "month": record.month, "day": record.day,
                    "hour": record.hour, "minute": record.minute,
                    "gender": record.gender,
                    "day_master": record.day_master,
                    "pillars": json.loads(record.pillars_json) if record.pillars_json else None,
                    "geju": json.loads(record.geju_json) if record.geju_json else None,
                }
            result.append(item)
        return json.dumps({"cases": result, "exported_at": datetime.now(timezone.utc).isoformat()},
                         ensure_ascii=False, indent=2, default=str)

    def _export_csv(self, cases: List[Case], session: Session) -> str:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "id", "title", "category", "source", "credibility",
            "is_public", "is_featured", "view_count", "favorite_count",
            "tags", "summary", "conclusion",
            "year", "month", "day", "hour", "gender", "day_master",
            "created_at",
        ])
        for case in cases:
            record = session.query(BaziRecord).filter(
                BaziRecord.id == case.record_id
            ).first()
            writer.writerow([
                case.id, case.title, case.category or "", case.source or "",
                case.credibility, case.is_public, case.is_featured,
                case.view_count, case.favorite_count,
                case.tags or "", case.summary or "", case.conclusion or "",
                record.year if record else "", record.month if record else "",
                record.day if record else "", record.hour if record else "",
                record.gender if record else "", record.day_master if record else "",
                case.created_at.isoformat() if case.created_at else "",
            ])
        return output.getvalue()

    def import_cases(self, data: str, format: str = "json") -> Dict[str, int]:
        """导入案例

        Args:
            data: JSON 或 CSV 字符串
            format: json 或 csv

        Returns:
            {"imported": N, "skipped": M}
        """
        imported = 0
        skipped = 0

        if format == "json":
            parsed = json.loads(data)
            for item in parsed.get("cases", []):
                try:
                    # 需要先有对应的 BaziRecord
                    record_data = item.get("record", {})
                    if not record_data:
                        skipped += 1
                        continue

                    with self._session() as s:
                        # 查找或创建 BaziRecord
                        record = s.query(BaziRecord).filter(
                            BaziRecord.year == record_data.get("year"),
                            BaziRecord.month == record_data.get("month"),
                            BaziRecord.day == record_data.get("day"),
                            BaziRecord.hour == record_data.get("hour"),
                        ).first()

                        if record is None:
                            skipped += 1
                            continue

                        # 检查案例是否已存在
                        existing = s.query(Case).filter(
                            Case.record_id == record.id,
                            Case.title == item.get("title"),
                        ).first()
                        if existing:
                            skipped += 1
                            continue

                        case = Case(
                            record_id=record.id,
                            title=item["title"],
                            category=item.get("category"),
                            source=item.get("source"),
                            credibility=item.get("credibility", 0.8),
                            is_public=item.get("is_public", True),
                            is_featured=item.get("is_featured", False),
                            summary=item.get("summary"),
                            analysis_text=item.get("analysis_text"),
                            conclusion=item.get("conclusion"),
                            tags=",".join(item.get("tags", [])) if item.get("tags") else None,
                        )
                        s.add(case)
                        s.commit()
                        imported += 1
                except Exception:
                    skipped += 1
                    continue

        return {"imported": imported, "skipped": skipped}

    # ── 统计 ──────────────────────────────────────────────────────────────

    def stats(self) -> Dict[str, Any]:
        """案例库统计"""
        with self._session() as s:
            total = s.query(func.count(Case.id)).scalar() or 0
            public = s.query(func.count(Case.id)).filter(Case.is_public == True).scalar() or 0  # noqa: E712
            featured = s.query(func.count(Case.id)).filter(Case.is_featured == True).scalar() or 0  # noqa: E712
            total_views = s.query(func.sum(Case.view_count)).scalar() or 0
            total_favorites = s.query(func.sum(Case.favorite_count)).scalar() or 0
            categories = self.list_categories()
            top_tags = self.list_tags()[:10]

            return {
                "total_cases": total,
                "public_cases": public,
                "featured_cases": featured,
                "total_views": total_views,
                "total_favorites": total_favorites,
                "categories": categories,
                "top_tags": top_tags,
            }


# ============================================================================
# 模块级单例
# ============================================================================

_library: Optional[CaseLibrary] = None


def get_case_library(store: Optional[DataStore] = None) -> CaseLibrary:
    """获取全局 CaseLibrary 实例"""
    global _library
    if _library is None:
        _library = CaseLibrary(store)
    return _library


# ============================================================================
# 自测
# ============================================================================

def _self_test():
    """自测"""
    import tempfile
    import os

    print("=== Case Library 自测 ===\n")

    # 使用临时数据库
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        store = DataStore(db_path=db_path)
        lib = CaseLibrary(store)

        # 创建用户和记录
        user = store.get_or_create_user("test_user")
        record_id = store.save_bazi_record(
            year=1990, month=6, day=15, hour=10,
            gender="male", user_id=user.id,
            day_master="辛",
            pillars={"year": "庚午", "month": "壬午", "day": "辛亥", "hour": "癸巳"},
            analysis={"wuxing": {"金": 2, "水": 2, "火": 3, "土": 1}},
            geju={"geju_name": "伤官格"},
            tags="测试",
        )
        print(f"创建记录: id={record_id}")

        # 创建案例
        case_id = lib.create_case(
            record_id=record_id,
            title="某企业家命例",
            category="事业",
            summary="辛金日主，伤官格，适合创业",
            tags=["企业家", "创业"],
        )
        print(f"创建案例: id={case_id}")

        # 获取案例
        case = lib.get_case(case_id, increment_view=True)
        print(f"案例标题: {case['title']}")
        print(f"案例分类: {case['category']}")
        print(f"浏览数: {case['view_count']}")

        # 搜索
        results = lib.search_cases(category="事业")
        print(f"搜索结果: {results['total']} 条")

        # 分类列表
        cats = lib.list_categories()
        print(f"分类: {cats}")

        # 标签列表
        tags = lib.list_tags()
        print(f"标签: {tags}")

        # 导出
        exported = lib.export_cases(format="json")
        print(f"导出JSON长度: {len(exported)}")

        # 统计
        stats = lib.stats()
        print(f"统计: {stats}")

        print("\n所有测试通过!")
    finally:
        os.unlink(db_path)


if __name__ == "__main__":
    _self_test()
