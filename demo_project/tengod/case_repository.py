"""
case_repository.py — 案例仓库 v2.11
====================================
持久化案例管理，支持搜索、导入导出、分页。

特性：
  - 基于 database.py 的案例持久化存储
  - 全文搜索（名称 + 八字数据）
  - JSON 导入导出
  - 种子数据从 case_comparator 迁移
  - 向后兼容：内存模式回退

用法：
  >>> from tengod.case_repository import CaseRepository, get_repository
  >>> repo = get_repository()
  >>> repo.add_case({"name": "张三", "bazi": {...}})
  >>> results = repo.search("财运")
  >>> repo.export_to_json("cases.json")
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional

from tengod.database import get_db, is_persistent


# ============================================================================
# 种子案例数据
# ============================================================================

SEED_CASES = [
    {
        "name": "案例001：财旺身弱",
        "bazi_data": {"year": "庚午", "month": "壬午", "day": "辛亥", "hour": "癸巳",
                       "day_master": "辛金", "gender": "male"},
        "analysis": {"geju": "财旺身弱", "yongshen": "土金", "summary": "日主辛金，生于午月，火旺克金..."},
        "tags": ["八字", "财运", "身弱"],
        "category": "bazi",
        "metadata": {"source": "seed", "confidence": 0.85},
    },
    {
        "name": "案例002：食神生财",
        "bazi_data": {"year": "甲子", "month": "丙寅", "day": "戊辰", "hour": "庚申",
                       "day_master": "戊土", "gender": "female"},
        "analysis": {"geju": "食神生财", "yongshen": "火土", "summary": "日主戊土，食神庚金生财..."},
        "tags": ["八字", "财运", "食神"],
        "category": "bazi",
        "metadata": {"source": "seed", "confidence": 0.80},
    },
    {
        "name": "案例003：官印相生",
        "bazi_data": {"year": "壬申", "month": "庚戌", "day": "丙子", "hour": "甲午",
                       "day_master": "丙火", "gender": "male"},
        "analysis": {"geju": "官印相生", "yongshen": "木火", "summary": "日主丙火，官印相生..."},
        "tags": ["八字", "事业", "官印"],
        "category": "bazi",
        "metadata": {"source": "seed", "confidence": 0.82},
    },
    {
        "name": "案例004：伤官配印",
        "bazi_data": {"year": "乙卯", "month": "己丑", "day": "壬午", "hour": "辛亥",
                       "day_master": "壬水", "gender": "female"},
        "analysis": {"geju": "伤官配印", "yongshen": "金水", "summary": "日主壬水，伤官配印..."},
        "tags": ["八字", "才华", "伤官"],
        "category": "bazi",
        "metadata": {"source": "seed", "confidence": 0.78},
    },
    {
        "name": "案例005：杀印相生",
        "bazi_data": {"year": "癸亥", "month": "甲寅", "day": "庚辰", "hour": "丙戌",
                       "day_master": "庚金", "gender": "male"},
        "analysis": {"geju": "杀印相生", "yongshen": "土金", "summary": "日主庚金，七杀丙火制..."},
        "tags": ["八字", "权贵", "七杀"],
        "category": "bazi",
        "metadata": {"source": "seed", "confidence": 0.83},
    },
]


# ============================================================================
# 案例仓库
# ============================================================================

class CaseRepository:
    """案例仓库

    提供案例的增删改查、搜索、导入导出。
    """

    def __init__(self):
        self._seeded = False

    # ── 初始化 ──────────────────────────────────────────────────────────

    def seed(self) -> int:
        """播种初始案例数据，返回播种数量"""
        if self._seeded:
            return 0

        if is_persistent():
            db = get_db()
            count = db.count_cases()
            if count > 0:
                self._seeded = True
                return 0

            for case in SEED_CASES:
                db.insert_case(case)

        self._seeded = True
        return len(SEED_CASES)

    # ── 案例 CRUD ────────────────────────────────────────────────────────

    def add_case(self, case: Dict[str, Any]) -> Dict[str, Any]:
        """添加案例，返回完整案例对象"""
        if is_persistent():
            db = get_db()
            case_id = db.insert_case(case)
            return db.get_case(case_id)
        # 内存模式：返回带 ID 的数据
        case["id"] = int(time.time() * 1000)
        return dict(case)

    def get_case(self, case_id: int) -> Optional[Dict[str, Any]]:
        """获取案例"""
        if is_persistent():
            return get_db().get_case(case_id)
        return None

    def update_case(self, case_id: int, data: Dict[str, Any]) -> bool:
        """更新案例"""
        if is_persistent():
            return get_db().update_case(case_id, data)
        return False

    def delete_case(self, case_id: int) -> bool:
        """删除案例"""
        if is_persistent():
            return get_db().delete_case(case_id)
        return False

    def list_cases(
        self,
        page: int = 1,
        page_size: int = 20,
        category: str = "",
        tag: str = "",
        search: str = "",
    ) -> Dict[str, Any]:
        """分页列出案例

        Args:
            page: 页码（从 1 开始）
            page_size: 每页数量
            category: 分类过滤
            tag: 标签过滤
            search: 搜索关键词

        Returns:
            {"items": [...], "total": N, "page": P, "page_size": S, "total_pages": TP}
        """
        if not is_persistent():
            return {"items": [], "total": 0, "page": page, "page_size": page_size, "total_pages": 0}

        db = get_db()
        offset = (page - 1) * page_size

        items = db.list_cases(limit=page_size, offset=offset, category=category, search=search)
        total = db.count_cases(category=category, search=search)

        # 标签过滤（内存中）
        if tag and items:
            items = [c for c in items if tag in c.get("tags", [])]

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": max(1, (total + page_size - 1) // page_size),
        }

    def search(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """搜索案例"""
        if not is_persistent():
            return []
        return get_db().list_cases(limit=limit, search=query)

    def count(self, category: str = "") -> int:
        """统计案例数"""
        if is_persistent():
            return get_db().count_cases(category=category)
        return 0

    # ── 导入导出 ──────────────────────────────────────────────────────────

    def export_to_json(self, filepath: str) -> int:
        """导出案例到 JSON 文件，返回导出数量"""
        result = self.list_cases(page=1, page_size=10000)
        items = result["items"]
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump({
                "version": "2.11.0",
                "exported_at": time.time(),
                "count": len(items),
                "cases": items,
            }, f, ensure_ascii=False, indent=2)
        return len(items)

    def import_from_json(self, filepath: str) -> int:
        """从 JSON 文件导入案例，返回导入数量"""
        if not os.path.exists(filepath):
            return 0

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        cases = data.get("cases", [])
        count = 0
        for case in cases:
            clean_case = {
                "name": case.get("name", ""),
                "bazi_data": case.get("bazi_data", {}),
                "analysis": case.get("analysis", {}),
                "tags": case.get("tags", []),
                "category": case.get("category", "general"),
                "metadata": case.get("metadata", {}),
            }
            self.add_case(clean_case)
            count += 1

        return count

    def bulk_import(self, cases: List[Dict[str, Any]]) -> int:
        """批量导入案例，返回导入数量"""
        count = 0
        for case in cases:
            self.add_case(case)
            count += 1
        return count

    # ── 统计 ──────────────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        """获取案例库统计"""
        if not is_persistent():
            return {"total": 0, "by_category": {}, "by_tag": {}, "source": "memory"}

        db = get_db()
        total = db.count_cases()
        all_cases = db.list_cases(limit=10000)

        by_category: Dict[str, int] = {}
        by_tag: Dict[str, int] = {}
        for c in all_cases:
            cat = c["category"]
            by_category[cat] = by_category.get(cat, 0) + 1
            for t in c.get("tags", []):
                by_tag[t] = by_tag.get(t, 0) + 1

        return {
            "total": total,
            "by_category": by_category,
            "by_tag": by_tag,
            "source": "sqlite",
            "db_path": db._db_path,
        }

    def get_similar_cases(self, bazi_data: Dict[str, Any], limit: int = 5) -> List[Dict[str, Any]]:
        """查找相似案例（基于八字数据关键词匹配）"""
        if not is_persistent():
            return []

        db = get_db()
        # 提取关键词
        keywords = []
        if "day_master" in bazi_data:
            keywords.append(bazi_data["day_master"])
        if "geju" in bazi_data:
            keywords.append(bazi_data["geju"])

        all_cases = db.list_cases(limit=100)
        results = []
        for case in all_cases:
            case_bazi = case.get("bazi_data", {})
            score = 0
            if case_bazi.get("day_master") == bazi_data.get("day_master"):
                score += 3
            if case_bazi.get("gender") == bazi_data.get("gender"):
                score += 1
            # 相同标签加分
            common_tags = set(case.get("tags", [])) & set(keywords)
            score += len(common_tags)

            if score > 0:
                results.append({"case": case, "score": score})

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]


# ============================================================================
# 全局实例
# ============================================================================

_repository: Optional[CaseRepository] = None


def get_repository() -> CaseRepository:
    """获取全局案例仓库"""
    global _repository
    if _repository is None:
        _repository = CaseRepository()
        _repository.seed()
    return _repository


def reset_repository() -> None:
    """重置仓库（测试用）"""
    global _repository
    _repository = None


__all__ = [
    "CaseRepository",
    "get_repository",
    "reset_repository",
    "SEED_CASES",
]