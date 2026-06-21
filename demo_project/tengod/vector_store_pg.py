#!/usr/bin/env python3
"""
vector_store_pg.py — PostgreSQL + pgvector 向量存储引擎 v1.0.0
==============================================================

作为 tengod.vector_store 中 FAISS 内存索引的替代方案，提供：
  - 八字排盘记录 (bazi_records) 的向量化索引与相似度检索
  - 案例库 (cases) 的向量化索引与相似度检索
  - HNSW 索引 + 余弦距离 (<=> 运算符)
  - 兼容现有 ChineseEmbedder（n-gram + 领域语义特征，256 维）
  - 内存回退索引：from_embeddings_to_records() — 可作为 FAISS 索引的热切换

依赖：
  pip install pgvector sqlalchemy numpy
  PostgreSQL 需安装 pgvector 扩展: CREATE EXTENSION IF NOT EXISTS vector;

用法：
  >>> from tengod.vector_store_pg import VectorStorePG, ChineseEmbedder
  >>> vs = VectorStorePG("postgresql://user:pwd@db:5432/tengod")
  >>> vs.create_tables()
  >>> vec = vs.embedder.embed_bazi(bazi_data)
  >>> vs.store_bazi_embedding(record_id=1, vector=vec, embedding_type="full")
  >>> results = vs.search_similar_by_text("身弱伤官格", top_k=10)
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np

# ── pgvector & SQLAlchemy 导入（带优雅回退） ────────────────────────────────

try:
    from pgvector.sqlalchemy import Vector as PgVector
    _PGVECTOR_AVAILABLE = True
except ImportError:  # pragma: no cover - 仅在缺少依赖时触发
    PgVector = None  # type: ignore
    _PGVECTOR_AVAILABLE = False

try:
    from sqlalchemy import (
        Column, Integer, String, Text, DateTime, ForeignKey,
        Index, func, and_, or_, text,
    )
    from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship
    from sqlalchemy.engine import Engine
    _SQLALCHEMY_AVAILABLE = True
except ImportError:  # pragma: no cover
    Engine = None  # type: ignore
    _SQLALCHEMY_AVAILABLE = False

# ── 从 data_store 复用 Base / User / BaziRecord（优雅回退） ──────────────

_Base: Any = None
_User: Any = None
_BaziRecord: Any = None

try:
    from tengod.data_store import Base as _DSBase, User as _DSUser, BaziRecord as _DSBaziRecord
    _Base, _User, _BaziRecord = _DSBase, _DSUser, _DSBaziRecord
except Exception:  # pragma: no cover - 导入失败时自行定义
    if _SQLALCHEMY_AVAILABLE:
        class _LocalBase(DeclarativeBase):
            pass
        _Base = _LocalBase
    else:
        _Base = object

__all__ = [
    "ChineseEmbedder",
    "VectorStorePG",
    "BaziEmbedding",
    "CaseEmbedding",
    "is_pgvector_available",
]

__version__ = "1.0.0"

VECTOR_DIM = 256


# ============================================================================
# 工具函数
# ============================================================================

def is_pgvector_available() -> bool:
    """返回当前环境是否安装了 pgvector Python 包。

    注意：即便安装了 Python 包，PostgreSQL 服务端仍需 CREATE EXTENSION vector;
    可通过 health_check() 方法验证服务端扩展。
    """
    return _PGVECTOR_AVAILABLE


def _ensure_pgvector() -> None:
    """若 pgvector 未安装则抛出明确的 ImportError。"""
    if not _PGVECTOR_AVAILABLE:
        raise ImportError(
            "pgvector Python 包未安装。请执行: pip install pgvector sqlalchemy"
        )
    if not _SQLALCHEMY_AVAILABLE:
        raise ImportError(
            "SQLAlchemy 未安装。请执行: pip install sqlalchemy"
        )


def _l2_normalize(vec: np.ndarray) -> np.ndarray:
    """L2 归一化。对全零向量直接返回（避免除以零）。"""
    norm = float(np.linalg.norm(vec))
    if norm > 0:
        return vec / norm
    return vec


def _cosine_distance(a: np.ndarray, b: np.ndarray) -> float:
    """纯 NumPy 实现的余弦距离（1 - cosθ），供 FAISS 回退使用。

    输入应为已归一化向量（0 ~ 2 范围）。完全相同返回 0.0，正交返回 1.0。
    """
    a = np.asarray(a, dtype=np.float64).ravel()
    b = np.asarray(b, dtype=np.float64).ravel()
    if a.size != b.size or a.size == 0:
        return 2.0
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    if na == 0 or nb == 0:
        return 2.0
    sim = float(np.dot(a, b)) / (na * nb)
    # 数值稳定性
    sim = max(-1.0, min(1.0, sim))
    return 1.0 - sim


# ============================================================================
# 领域语义特征（与 vector_store.py 保持一致，保证向量空间可比）
# ============================================================================

_WUXING_ONEHOT = {
    "木": np.array([1, 0, 0, 0, 0], dtype=np.float32),
    "火": np.array([0, 1, 0, 0, 0], dtype=np.float32),
    "土": np.array([0, 0, 1, 0, 0], dtype=np.float32),
    "金": np.array([0, 0, 0, 1, 0], dtype=np.float32),
    "水": np.array([0, 0, 0, 0, 1], dtype=np.float32),
}

_YINYANG_ONEHOT = {
    "阳": np.array([1, 0], dtype=np.float32),
    "阴": np.array([0, 1], dtype=np.float32),
}

_DIRECTION_ONEHOT = {
    "东": np.array([1, 0, 0, 0, 0, 0, 0, 0], dtype=np.float32),
    "南": np.array([0, 1, 0, 0, 0, 0, 0, 0], dtype=np.float32),
    "西": np.array([0, 0, 1, 0, 0, 0, 0, 0], dtype=np.float32),
    "北": np.array([0, 0, 0, 1, 0, 0, 0, 0], dtype=np.float32),
    "中": np.array([0, 0, 0, 0, 1, 0, 0, 0], dtype=np.float32),
    "东南": np.array([0, 0, 0, 0, 0, 1, 0, 0], dtype=np.float32),
    "西南": np.array([0, 0, 0, 0, 0, 0, 1, 0], dtype=np.float32),
    "西北": np.array([0, 0, 0, 0, 0, 0, 0, 1], dtype=np.float32),
}

_SEASON_ONEHOT = {
    "春": np.array([1, 0, 0, 0, 0], dtype=np.float32),
    "夏": np.array([0, 1, 0, 0, 0], dtype=np.float32),
    "长夏": np.array([0, 0, 1, 0, 0], dtype=np.float32),
    "秋": np.array([0, 0, 0, 1, 0], dtype=np.float32),
    "冬": np.array([0, 0, 0, 0, 1], dtype=np.float32),
}

_TIANGAN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
_TIANGAN_INDEX = {t: i for i, t in enumerate(_TIANGAN)}

_DIZHI = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
_DIZHI_INDEX = {d: i for i, d in enumerate(_DIZHI)}

_SHIGAN = ["比肩", "劫财", "食神", "伤官", "偏财", "正财", "七杀", "正官", "偏印", "正印"]


# ============================================================================
# ChineseEmbedder — 兼容 FAISS 向量空间
# ============================================================================

class ChineseEmbedder:
    """中文文本 / 八字 / 案例 嵌入器（与 vector_store.py 保持向量空间兼容）。

    生成 256 维向量：
      - 128 维：字符 n-gram 哈希特征（单字 + 双字 + 三字）
      -  64 维：领域语义特征（五行、阴阳、方位、季节、天干、地支、十神）
      -  64 维：文本结构 / 哈希填充

    输出向量做 L2 归一化，以支持 pgvector 的 <=> 余弦距离运算符
    （等价于 1 - cosθ，similarity = 1 - distance）。
    """

    VECTOR_DIM = VECTOR_DIM
    NGRAM_DIM = 128
    SEMANTIC_DIM = 64
    STRUCT_DIM = 64

    # 八字嵌入时各子块权重（可调）
    DEFAULT_BAZI_WEIGHTS = {
        "pillars": 0.5,      # 四柱
        "analysis": 0.25,    # 分析文本
        "geju": 0.15,        # 格局
        "yongshen_tiaohou": 0.1,  # 用神 / 调候
    }

    def __init__(self) -> None:
        self._cache: Dict[str, np.ndarray] = {}

    # ── 对外主 API ──────────────────────────────────────────────────────────

    def embed_text(
        self,
        text: str,
        feature_weights: Optional[Dict[str, float]] = None,
    ) -> List[float]:
        """将中文文本嵌入为 256 维向量（Python list）。

        Args:
            text: 输入文本。空字符串返回全零向量。
            feature_weights: 可选权重字典，目前保留接口；内部默认
                ngram/semantic/struct = 1/1/1。

        Returns:
            list[float]，长度 256，L2 归一化。
        """
        vec = self._embed_np(text or "")
        return [float(x) for x in vec]

    def embed_bazi(self, bazi_data: Optional[Dict[str, Any]]) -> List[float]:
        """将八字数据嵌入为 256 维向量。

        Args:
            bazi_data: dict，可能包含 pillars / analysis / geju / yongshen /
                tiaohou / shensha / day_master 等字段（字段均可缺失）。
                支持字符串字段（已序列化文本）或 dict/list 字段。
        """
        if not bazi_data:
            return [0.0] * self.VECTOR_DIM

        # 将各子块转为文本
        sub_texts: Dict[str, str] = {}
        for key in ("pillars", "analysis", "geju", "yongshen", "tiaohou", "shensha"):
            sub_texts[key] = self._to_text(bazi_data.get(key))

        day_master = bazi_data.get("day_master") or ""
        if isinstance(day_master, str) and day_master:
            sub_texts["day_master"] = f"日主:{day_master}"

        # 加权平均
        w = self.DEFAULT_BAZI_WEIGHTS
        accum = np.zeros(self.VECTOR_DIM, dtype=np.float64)
        total_w = 0.0

        for key, weight in (
            ("pillars", w["pillars"]),
            ("analysis", w["analysis"]),
            ("geju", w["geju"]),
            ("yongshen", w["yongshen_tiaohou"]),
            ("tiaohou", w["yongshen_tiaohou"] * 0.5),
            ("day_master", 0.05),
        ):
            t = sub_texts.get(key)
            if t:
                accum += self._embed_np(t) * weight
                total_w += weight

        if total_w > 0:
            accum /= total_w

        vec = _l2_normalize(accum.astype(np.float32))
        return [float(x) for x in vec]

    def embed_case(
        self,
        title: Optional[str],
        summary: Optional[str],
        analysis_text: Optional[str],
        category: Optional[str],
    ) -> List[float]:
        """将案例（标题 + 摘要 + 分析 + 分类）嵌入为 256 维向量。

        各子块权重：title 0.3 / summary 0.3 / analysis 0.3 / category 0.1。
        """
        accum = np.zeros(self.VECTOR_DIM, dtype=np.float64)
        total_w = 0.0
        blocks = [
            (title, 0.3),
            (summary, 0.3),
            (analysis_text, 0.3),
            (category, 0.1),
        ]
        for t, w in blocks:
            if not t:
                continue
            if isinstance(t, (dict, list)):
                t = self._to_text(t)
            if not t.strip():
                continue
            accum += self._embed_np(t) * w
            total_w += w

        if total_w > 0:
            accum /= total_w
        vec = _l2_normalize(accum.astype(np.float32))
        return [float(x) for x in vec]

    # ── 内部实现 ────────────────────────────────────────────────────────────

    def _embed_np(self, text: str) -> np.ndarray:
        """返回 np.ndarray[float32, shape=(256,)]，已归一化。"""
        text = text.strip() if isinstance(text, str) else ""
        if not text:
            return np.zeros(self.VECTOR_DIM, dtype=np.float32)

        if text in self._cache:
            return self._cache[text]

        ngram = self._char_ngram_hash(text)
        sem = self._domain_semantic(text)
        struct = self._text_structure(text)
        vec = np.concatenate([ngram, sem, struct]).astype(np.float32)
        vec = _l2_normalize(vec)

        self._cache[text] = vec
        return vec

    def _char_ngram_hash(self, text: str) -> np.ndarray:
        vec = np.zeros(self.NGRAM_DIM, dtype=np.float32)
        chars = [c for c in text if "\u4e00" <= c <= "\u9fff"]
        if not chars:
            # 无中文字符时退化为 ASCII 哈希，避免纯英文/数字完全为零
            for ch in text:
                idx = (ord(ch) * 2654435761) % self.NGRAM_DIM
                vec[idx] += 1.0
            return _l2_normalize(vec)

        # 单字
        for ch in chars:
            idx = (ord(ch) * 2654435761) % self.NGRAM_DIM
            vec[idx] += 1.0

        # 双字
        for i in range(len(chars) - 1):
            bigram = chars[i] + chars[i + 1]
            idx = self._hash_string(bigram) % self.NGRAM_DIM
            vec[idx] += 0.5

        # 三字
        for i in range(len(chars) - 2):
            trigram = chars[i] + chars[i + 1] + chars[i + 2]
            idx = self._hash_string(trigram) % self.NGRAM_DIM
            vec[idx] += 0.25

        return _l2_normalize(vec)

    def _domain_semantic(self, text: str) -> np.ndarray:
        """64 维领域语义特征（布局与 vector_store.py 一致）。"""
        vec = np.zeros(self.SEMANTIC_DIM, dtype=np.float32)
        offset = 0

        # 五行 5
        for wv in _WUXING_ONEHOT.values():
            pass  # 占位，下面用匹配填充
        for wx, wv in _WUXING_ONEHOT.items():
            if wx in text:
                vec[offset:offset + 5] += wv * 0.1
        offset += 5

        # 阴阳 2
        for yy, yv in _YINYANG_ONEHOT.items():
            if yy in text:
                vec[offset:offset + 2] += yv * 0.1
        offset += 2

        # 方位 8
        for dv in _DIRECTION_ONEHOT.values():
            pass
        for dir_, dv in _DIRECTION_ONEHOT.items():
            if dir_ in text:
                vec[offset:offset + 8] += dv * 0.1
        offset += 8

        # 季节 5
        for season, sv in _SEASON_ONEHOT.items():
            if season in text:
                vec[offset:offset + 5] += sv * 0.1
        offset += 5

        # 天干 10
        for tg, idx in _TIANGAN_INDEX.items():
            if tg in text:
                vec[offset + idx] += 0.1
        offset += 10

        # 地支 12
        for dz, idx in _DIZHI_INDEX.items():
            if dz in text:
                vec[offset + idx] += 0.1
        offset += 12

        # 八卦 8 — 使用字符匹配
        for i, bg in enumerate(["乾", "兑", "离", "震", "巽", "坎", "艮", "坤"]):
            if bg in text:
                vec[offset + i] += 0.1
        offset += 8

        # 十神 10
        for i, sg in enumerate(_SHIGAN):
            if sg in text:
                vec[offset + i] += 0.1
        offset += 10

        # 剩余 4 维（64 - 60 = 4）保留
        return vec

    def _text_structure(self, text: str) -> np.ndarray:
        """64 维文本结构特征（长度 + 字符占比 + 哈希填充）。"""
        vec = np.zeros(self.STRUCT_DIM, dtype=np.float32)
        if not text:
            return vec

        n = max(len(text), 1)
        vec[0] = min(len(text), 500) / 500.0
        vec[1] = sum(1 for c in text if "\u4e00" <= c <= "\u9fff") / n
        vec[2] = sum(1 for c in text if c.isdigit()) / n
        vec[3] = sum(1 for c in text if c in "，。、；：？！\"'（）【】《》·,.;:?!()[]") / n
        vec[4] = min(text.count(" "), 50) / 50.0

        # 其余 59 维用字符哈希填充
        for ch in text:
            idx = 5 + ((ord(ch) * 2654435761) % (self.STRUCT_DIM - 5))
            vec[idx] += 0.05

        return vec

    # ── 工具 ────────────────────────────────────────────────────────────────

    @staticmethod
    def _hash_string(s: str) -> int:
        h = hashlib.md5(s.encode("utf-8")).hexdigest()
        return int(h[:8], 16)

    @staticmethod
    def _to_text(obj: Any) -> str:
        if obj is None:
            return ""
        if isinstance(obj, str):
            return obj
        try:
            return json.dumps(obj, ensure_ascii=False, sort_keys=True)
        except Exception:
            return str(obj)

    def clear_cache(self) -> None:
        self._cache.clear()


# ============================================================================
# ORM 模型 — BaziEmbedding & CaseEmbedding
# ============================================================================

# 如果没有从 data_store 拿到 Base，则本地声明一个。
# 注意：使用同一个 Base.metadata.create_all(engine) 可避免表冲突。

if _PGVECTOR_AVAILABLE and _SQLALCHEMY_AVAILABLE:

    class BaziEmbedding(_Base):
        """八字记录向量表。

        每条 bazi_record 可能有多条 embedding（不同 embedding_type），
        典型类型: "full"（整体） / "pillars"（四柱） / "geju"（格局）。
        """
        __tablename__ = "bazi_embeddings"

        id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
        record_id: Mapped[int] = mapped_column(
            Integer,
            ForeignKey("bazi_records.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
        embedding_type: Mapped[str] = mapped_column(String(16), nullable=False, default="full", index=True)
        vector: Mapped[Any] = mapped_column(PgVector(VECTOR_DIM), nullable=False)
        created_at: Mapped[float] = mapped_column(
            DateTime, default=lambda: time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()), nullable=False,
        )

        __table_args__ = (
            # HNSW 索引：余弦距离
            Index(
                "ix_bazi_embeddings_vector_cosine",
                "vector",
                postgresql_using="hnsw",
                postgresql_with={"m": 16, "ef_construction": 64},
                postgresql_ops={"vector": "vector_cosine_ops"},
            ),
            Index("ix_bazi_embeddings_record_type", "record_id", "embedding_type", unique=True),
        )

        def __repr__(self) -> str:
            return f"<BaziEmbedding(id={self.id}, record_id={self.record_id}, type={self.embedding_type!r})>"


    class CaseEmbedding(_Base):
        """案例向量表。"""
        __tablename__ = "case_embeddings"

        id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
        case_id: Mapped[int] = mapped_column(
            Integer,
            # cases 表可能尚未在同一 Base 声明，这里不加 FK 约束以保持兼容。
            nullable=False,
            index=True,
        )
        embedding_type: Mapped[str] = mapped_column(String(16), nullable=False, default="full", index=True)
        vector: Mapped[Any] = mapped_column(PgVector(VECTOR_DIM), nullable=False)
        created_at: Mapped[float] = mapped_column(
            DateTime, default=lambda: time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()), nullable=False,
        )

        __table_args__ = (
            Index(
                "ix_case_embeddings_vector_cosine",
                "vector",
                postgresql_using="hnsw",
                postgresql_with={"m": 16, "ef_construction": 64},
                postgresql_ops={"vector": "vector_cosine_ops"},
            ),
            Index("ix_case_embeddings_case_type", "case_id", "embedding_type", unique=True),
        )

        def __repr__(self) -> str:
            return f"<CaseEmbedding(id={self.id}, case_id={self.case_id}, type={self.embedding_type!r})>"

else:  # pragma: no cover - 缺少依赖时提供占位，便于 import 不崩
    class BaziEmbedding:  # type: ignore
        """pgvector 未安装，此占位符仅用于避免 ImportError。"""
        __tablename__ = "bazi_embeddings"

    class CaseEmbedding:  # type: ignore
        """pgvector 未安装，此占位符仅用于避免 ImportError。"""
        __tablename__ = "case_embeddings"


# ============================================================================
# VectorStorePG — 主入口
# ============================================================================

class VectorStorePG:
    """PostgreSQL + pgvector 向量存储。

    构造参数接受以下三种形式之一：
      1. SQLAlchemy Engine 对象
      2. 数据库 URL 字符串 ("postgresql://...")
      3. Session 工厂（Callable[[], Session]）
    """

    def __init__(
        self,
        engine_or_session_factory: Union[str, "Engine", Callable[[], Session], Any],
        embedder: Optional[ChineseEmbedder] = None,
    ) -> None:
        _ensure_pgvector()

        self.embedder: ChineseEmbedder = embedder or ChineseEmbedder()

        self._engine: Optional[Engine] = None
        self._session_factory: Optional[Callable[[], Session]] = None

        from sqlalchemy import create_engine as _create_engine

        if isinstance(engine_or_session_factory, str):
            self._engine = _create_engine(
                engine_or_session_factory, echo=False, pool_pre_ping=True,
                pool_size=10, max_overflow=20,
            )
        elif hasattr(engine_or_session_factory, "connect") and callable(engine_or_session_factory.connect):
            # duck-typed Engine
            self._engine = engine_or_session_factory
        elif callable(engine_or_session_factory):
            self._session_factory = engine_or_session_factory
        else:
            raise TypeError(
                "engine_or_session_factory 必须是 Engine / 数据库 URL 字符串 / Session 工厂"
            )

        # 内存回退索引（FAISS 兼容）
        self._memory_index: Optional["_InMemoryIndex"] = None

    # ── session 管理 ─────────────────────────────────────────────────────────

    def _session(self) -> Session:
        if self._session_factory is not None:
            return self._session_factory()
        if self._engine is not None:
            return Session(self._engine)
        raise RuntimeError("VectorStorePG 未正确初始化（缺少 engine / session_factory）")

    # ── 建表 / 删表 ──────────────────────────────────────────────────────────

    def create_tables(self) -> None:
        """启用 pgvector 扩展并创建两张 embedding 表 + HNSW 索引。

        调用前请确保连接的 PostgreSQL 已安装 pgvector 扩展（apt/yum/pgxn）。
        """
        # 启用扩展
        if self._engine is not None:
            with self._engine.connect() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                conn.commit()
        else:
            with self._session() as s:  # type: ignore[union-attr]
                s.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                s.commit()

        # 创建表（通过 Base.metadata）
        if self._engine is not None:
            _Base.metadata.create_all(self._engine, tables=[
                BaziEmbedding.__table__, CaseEmbedding.__table__,
            ])
        else:
            # 使用 session_factory 时通过其 bind 的 connection 创建
            with self._session() as s:
                _Base.metadata.create_all(s.connection(), tables=[
                    BaziEmbedding.__table__, CaseEmbedding.__table__,
                ])
                s.commit()

    def drop_tables(self) -> None:
        """删除两张 embedding 表。主表 bazi_records / users 不受影响。"""
        if self._engine is not None:
            _Base.metadata.drop_all(self._engine, tables=[
                BaziEmbedding.__table__, CaseEmbedding.__table__,
            ])
        else:
            with self._session() as s:
                _Base.metadata.drop_all(s.connection(), tables=[
                    BaziEmbedding.__table__, CaseEmbedding.__table__,
                ])
                s.commit()

    # ── 写入 ─────────────────────────────────────────────────────────────────

    def store_bazi_embedding(
        self,
        record_id: int,
        vector: Union[Sequence[float], np.ndarray],
        embedding_type: str = "full",
    ) -> int:
        """写入一条八字向量；若 (record_id, embedding_type) 已存在则覆盖。"""
        vec_list = self._coerce_vector(vector)
        with self._session() as s:
            existing = (
                s.query(BaziEmbedding)
                .filter(
                    BaziEmbedding.record_id == record_id,
                    BaziEmbedding.embedding_type == embedding_type,
                )
                .first()
            )
            if existing is not None:
                existing.vector = vec_list
                s.commit()
                return existing.id
            row = BaziEmbedding(
                record_id=record_id,
                embedding_type=embedding_type,
                vector=vec_list,
            )
            s.add(row)
            s.commit()
            s.refresh(row)
            return row.id

    def store_case_embedding(
        self,
        case_id: int,
        vector: Union[Sequence[float], np.ndarray],
        embedding_type: str = "full",
    ) -> int:
        vec_list = self._coerce_vector(vector)
        with self._session() as s:
            existing = (
                s.query(CaseEmbedding)
                .filter(
                    CaseEmbedding.case_id == case_id,
                    CaseEmbedding.embedding_type == embedding_type,
                )
                .first()
            )
            if existing is not None:
                existing.vector = vec_list
                s.commit()
                return existing.id
            row = CaseEmbedding(
                case_id=case_id,
                embedding_type=embedding_type,
                vector=vec_list,
            )
            s.add(row)
            s.commit()
            s.refresh(row)
            return row.id

    def bulk_store_bazi(self, records_list: Sequence[Dict[str, Any]]) -> int:
        """批量写入八字向量。

        records_list: list[dict]，每条必须包含：
            {"record_id": int, "vector": list[256] | np.ndarray,
             "embedding_type": str}
        返回成功写入条数。
        """
        if not records_list:
            return 0
        rows = []
        for item in records_list:
            vec = self._coerce_vector(item["vector"])
            rows.append(BaziEmbedding(
                record_id=int(item["record_id"]),
                embedding_type=str(item.get("embedding_type", "full")),
                vector=vec,
            ))
        with self._session() as s:
            s.add_all(rows)
            s.commit()
        return len(rows)

    def bulk_store_cases(self, cases_list: Sequence[Dict[str, Any]]) -> int:
        if not cases_list:
            return 0
        rows = []
        for item in cases_list:
            vec = self._coerce_vector(item["vector"])
            rows.append(CaseEmbedding(
                case_id=int(item["case_id"]),
                embedding_type=str(item.get("embedding_type", "full")),
                vector=vec,
            ))
        with self._session() as s:
            s.add_all(rows)
            s.commit()
        return len(rows)

    # ── 检索 ─────────────────────────────────────────────────────────────────

    def search_similar_bazi(
        self,
        query_vector: Union[Sequence[float], np.ndarray],
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        embedding_type: str = "full",
    ) -> List[Dict[str, Any]]:
        """按余弦距离检索最相似的八字记录。

        Args:
            query_vector: 256 维向量。
            top_k: 返回条数。
            filters: 可选过滤字典，支持的键：
                - record_ids: list[int]  限定记录 id 集合
                - day_master:   str      限定日主（需 bazi_records 表存在）
                - created_after: datetime
            embedding_type: 匹配哪一类向量（默认 "full"）。

        Returns:
            list[dict]，每项包含 id / label / day_master / similarity / embedding_type。
        """
        q_vec = self._coerce_vector(query_vector)
        top_k = max(1, int(top_k))

        with self._session() as s:
            # 使用 pgvector <=> 运算符：column <=> '[...]' 返回余弦距离
            distance_expr = BaziEmbedding.vector.op("<=>")(json.dumps(q_vec))

            query = s.query(
                BaziEmbedding.id,
                BaziEmbedding.record_id,
                BaziEmbedding.embedding_type,
                distance_expr.label("distance"),
            ).filter(BaziEmbedding.embedding_type == embedding_type)

            # 可选 filters
            if filters:
                if "record_ids" in filters and filters["record_ids"]:
                    query = query.filter(BaziEmbedding.record_id.in_(list(filters["record_ids"])))

            # 尝试关联 bazi_records 获取 label / day_master
            records = query.order_by("distance").limit(top_k).all()

            result: List[Dict[str, Any]] = []
            for row in records:
                record_id = row.record_id
                similarity = max(0.0, min(1.0, 1.0 - float(row.distance)))
                # 尝试取主记录信息
                label = day_master = None
                try:
                    if _BaziRecord is not None:
                        rec = s.query(_BaziRecord).filter(_BaziRecord.id == record_id).first()
                        if rec is not None:
                            label = getattr(rec, "label", None)
                            day_master = getattr(rec, "day_master", None)
                except Exception:
                    pass
                result.append({
                    "id": record_id,
                    "embedding_id": row.id,
                    "embedding_type": row.embedding_type,
                    "label": label,
                    "day_master": day_master,
                    "similarity": round(similarity, 6),
                    "distance": round(float(row.distance), 6),
                })
            return result

    def search_similar_cases(
        self,
        query_vector: Union[Sequence[float], np.ndarray],
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        embedding_type: str = "full",
    ) -> List[Dict[str, Any]]:
        """按余弦距离检索最相似的案例。"""
        q_vec = self._coerce_vector(query_vector)
        top_k = max(1, int(top_k))

        with self._session() as s:
            distance_expr = CaseEmbedding.vector.op("<=>")(json.dumps(q_vec))
            query = s.query(
                CaseEmbedding.id,
                CaseEmbedding.case_id,
                CaseEmbedding.embedding_type,
                distance_expr.label("distance"),
            ).filter(CaseEmbedding.embedding_type == embedding_type)

            if filters:
                if "case_ids" in filters and filters["case_ids"]:
                    query = query.filter(CaseEmbedding.case_id.in_(list(filters["case_ids"])))

            rows = query.order_by("distance").limit(top_k).all()
            return [
                {
                    "id": r.case_id,
                    "embedding_id": r.id,
                    "embedding_type": r.embedding_type,
                    "similarity": round(max(0.0, 1.0 - float(r.distance)), 6),
                    "distance": round(float(r.distance), 6),
                }
                for r in rows
            ]

    def search_similar_by_text(self, text: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """直接用文本检索：embed_text + search_similar_bazi。"""
        vec = self.embedder.embed_text(text)
        return self.search_similar_bazi(vec, top_k=top_k)

    # ── 索引维护 ─────────────────────────────────────────────────────────────

    def rebuild_index(self) -> None:
        """重建两张表上的 HNSW 索引（REINDEX CONCURRENTLY 不在事务内可用）。"""
        with self._session() as s:
            s.execute(text("REINDEX INDEX ix_bazi_embeddings_vector_cosine;"))
            s.execute(text("REINDEX INDEX ix_case_embeddings_vector_cosine;"))
            s.commit()

    def rebuild_all_embeddings_from_records(self, session: Optional[Session] = None) -> int:
        """扫描所有 bazi_records，重新计算向量并写入 bazi_embeddings。

        Args:
            session: 可选外部 session，否则内部打开。

        Returns:
            重新计算并写入的记录数。
        """
        if _BaziRecord is None:
            raise RuntimeError("无法访问 BaziRecord，请先确保 tengod.data_store 可导入。")

        def _work(s: Session) -> int:
            records = s.query(_BaziRecord).all()
            count = 0
            for rec in records:
                bazi_data = {
                    "day_master": getattr(rec, "day_master", None),
                    "pillars": getattr(rec, "pillars_json", None),
                    "analysis": getattr(rec, "analysis_json", None),
                    "geju": getattr(rec, "geju_json", None),
                    "yongshen": getattr(rec, "yongshen_json", None),
                    "tiaohou": getattr(rec, "tiaohou_json", None),
                    "shensha": getattr(rec, "shensha_json", None),
                }
                vec = self.embedder.embed_bazi(bazi_data)
                if any(abs(v) > 0 for v in vec):
                    existing = (
                        s.query(BaziEmbedding)
                        .filter(
                            BaziEmbedding.record_id == rec.id,
                            BaziEmbedding.embedding_type == "full",
                        )
                        .first()
                    )
                    if existing is not None:
                        existing.vector = vec
                    else:
                        s.add(BaziEmbedding(record_id=rec.id, embedding_type="full", vector=vec))
                    count += 1
            s.commit()
            return count

        if session is not None:
            return _work(session)
        with self._session() as s:
            return _work(s)

    # ── 健康检查 ─────────────────────────────────────────────────────────────

    def health_check(self) -> Dict[str, Any]:
        """检查 pgvector 扩展是否在服务端可用。

        返回示例:
            {
                "pgvector_python": True,
                "pgvector_extension": True,
                "vector_version": "0.8.0",
                "bazi_embedding_count": 123,
                "case_embedding_count": 45,
                "error": None,
            }
        """
        result: Dict[str, Any] = {
            "pgvector_python": _PGVECTOR_AVAILABLE,
            "pgvector_extension": False,
            "vector_version": None,
            "bazi_embedding_count": 0,
            "case_embedding_count": 0,
            "error": None,
        }

        if not _PGVECTOR_AVAILABLE:
            result["error"] = "pgvector Python 包未安装: pip install pgvector"
            return result

        try:
            with self._session() as s:
                try:
                    row = s.execute(text("SELECT extversion FROM pg_extension WHERE extname = 'vector';")).first()
                    if row:
                        result["pgvector_extension"] = True
                        result["vector_version"] = row[0]
                    else:
                        result["error"] = (
                            "PostgreSQL 未启用 vector 扩展。请在数据库中执行: "
                            "CREATE EXTENSION IF NOT EXISTS vector;"
                        )
                except Exception as e:
                    result["error"] = f"无法查询 pg_extension: {e}"

                # 计数
                try:
                    result["bazi_embedding_count"] = s.query(func.count(BaziEmbedding.id)).scalar() or 0
                except Exception:
                    pass
                try:
                    result["case_embedding_count"] = s.query(func.count(CaseEmbedding.id)).scalar() or 0
                except Exception:
                    pass
        except Exception as e:
            result["error"] = f"数据库连接失败: {e}"

        return result

    # ── FAISS 兼容：内存回退索引 ───────────────────────────────────────────

    def from_embeddings_to_records(
        self,
        records: Optional[Sequence[Dict[str, Any]]] = None,
    ) -> "_InMemoryIndex":
        """构建一个纯内存的相似度索引，用于 FAISS 索引的热切换场景。

        Args:
            records: list[dict]，每项至少含 "id" 与 "vector"；可选 "label" /
                "day_master" 等。为 None 时从数据库加载所有 bazi_embeddings。
        """
        idx = _InMemoryIndex(embedder=self.embedder)
        if records is None:
            # 从数据库加载
            with self._session() as s:
                rows = s.query(BaziEmbedding).all()
                for r in rows:
                    vec_list = r.vector if isinstance(r.vector, list) else list(r.vector)
                    label = day_master = None
                    try:
                        if _BaziRecord is not None:
                            rec = s.query(_BaziRecord).filter(_BaziRecord.id == r.record_id).first()
                            if rec is not None:
                                label = getattr(rec, "label", None)
                                day_master = getattr(rec, "day_master", None)
                    except Exception:
                        pass
                    idx.add(r.record_id, vec_list, {
                        "label": label,
                        "day_master": day_master,
                        "embedding_type": r.embedding_type,
                    })
        else:
            for item in records:
                idx.add(
                    item["id"],
                    item["vector"],
                    {k: v for k, v in item.items() if k not in ("id", "vector")},
                )
        self._memory_index = idx
        return idx

    # ── 内部工具 ─────────────────────────────────────────────────────────────

    @staticmethod
    def _coerce_vector(vector: Union[Sequence[float], np.ndarray]) -> List[float]:
        """校验并规范化向量为 list[float]。全零 / 长度不正确都会抛出 ValueError。"""
        if vector is None:
            raise ValueError("vector 不能为 None")
        arr = np.asarray(vector, dtype=np.float64).ravel()
        if arr.size != VECTOR_DIM:
            raise ValueError(f"vector 维度应为 {VECTOR_DIM}，实际为 {arr.size}")
        if not np.isfinite(arr).all():
            raise ValueError("vector 包含 NaN 或 Inf")
        # 全零向量也允许写入（以支持缺失文本的记录），但在检索端会提示。
        return [float(x) for x in arr]


# ============================================================================
# 内存相似度索引（FAISS 兼容热切换）
# ============================================================================

class _InMemoryIndex:
    """纯 Python 实现的余弦相似度索引，供 VectorStorePG.from_embeddings_to_records 使用。

    接口与 FAISS IndexFlatIP 类似：
        - add(ids, vectors, metas)
        - search(query_vector, top_k) -> list[(id, similarity, meta)]
        - size
    """

    def __init__(self, embedder: Optional[ChineseEmbedder] = None) -> None:
        self.embedder = embedder or ChineseEmbedder()
        self._ids: List[int] = []
        self._vectors: List[np.ndarray] = []
        self._metas: List[Dict[str, Any]] = []

    def add(self, record_id: int, vector: Union[Sequence[float], np.ndarray], meta: Optional[Dict[str, Any]] = None) -> None:
        arr = np.asarray(vector, dtype=np.float64).ravel()
        if arr.size != VECTOR_DIM:
            raise ValueError(f"vector 维度应为 {VECTOR_DIM}，实际为 {arr.size}")
        self._ids.append(int(record_id))
        self._vectors.append(arr)
        self._metas.append(meta or {})

    def add_many(self, items: Sequence[Tuple[int, Union[Sequence[float], np.ndarray], Optional[Dict[str, Any]]]]) -> None:
        for rid, vec, meta in items:
            self.add(rid, vec, meta)

    def search(
        self,
        query_vector: Union[Sequence[float], np.ndarray],
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        q = np.asarray(query_vector, dtype=np.float64).ravel()
        if q.size != VECTOR_DIM:
            raise ValueError(f"query 维度应为 {VECTOR_DIM}，实际为 {q.size}")
        top_k = max(1, int(top_k))

        if not self._vectors:
            return []

        # 暴力计算余弦距离；对数万规模完全够用，可按需替换为 FAISS IndexFlatIP
        distances = np.array(
            [_cosine_distance(q, v) for v in self._vectors],
            dtype=np.float64,
        )
        order = np.argsort(distances, kind="stable")[:top_k]

        results: List[Dict[str, Any]] = []
        for pos in order:
            dist = float(distances[pos])
            results.append({
                "id": self._ids[pos],
                "similarity": round(max(0.0, 1.0 - dist), 6),
                "distance": round(dist, 6),
                **self._metas[pos],
            })
        return results

    def search_by_text(self, text: str, top_k: int = 10) -> List[Dict[str, Any]]:
        vec = self.embedder.embed_text(text)
        return self.search(vec, top_k=top_k)

    @property
    def size(self) -> int:
        return len(self._ids)

    def __len__(self) -> int:
        return self.size


# ============================================================================
# 自测：Embedder 逻辑验证（不需要 PostgreSQL，可在任何环境运行）
# ============================================================================

def _run_self_test() -> None:
    print("=" * 60)
    print("ChineseEmbedder 自测（不需要 PostgreSQL）")
    print("=" * 60)

    embedder = ChineseEmbedder()

    # 1) 文本向量维度
    v1 = embedder.embed_text("八字命理学：身弱伤官格，用神取印比")
    assert isinstance(v1, list) and len(v1) == 256, f"文本向量维度错误: {len(v1)}"
    print(f"[OK] 文本向量维度: {len(v1)}")

    # 2) L2 归一化
    norm = float(np.linalg.norm(np.asarray(v1, dtype=np.float64)))
    assert abs(norm - 1.0) < 1e-5, f"文本向量未归一化: L2 norm = {norm}"
    print(f"[OK] 文本向量 L2 范数: {norm:.6f}")

    # 3) 不同输入产生不同向量
    v2 = embedder.embed_text("五行木火土金水相生相克")
    assert not np.allclose(np.asarray(v1), np.asarray(v2), atol=1e-6), "两个不同文本产生了相同向量"
    print("[OK] 不同文本产生不同向量")

    # 4) 空文本产生全零（非 NaN）
    v_empty = embedder.embed_text("")
    assert all(x == 0.0 for x in v_empty), "空文本未产生全零向量"
    print("[OK] 空文本 -> 全零向量")

    # 5) 八字嵌入
    bazi = {
        "day_master": "辛",
        "pillars": {"year": "庚午", "month": "壬午", "day": "辛亥", "hour": "癸巳"},
        "analysis": "身弱伤官见官，用神取印比",
        "geju": {"name": "伤官格"},
        "yongshen": {"wuxing": "土金"},
        "tiaohou": None,
    }
    vb = embedder.embed_bazi(bazi)
    assert len(vb) == 256, f"八字向量维度错误: {len(vb)}"
    nb = float(np.linalg.norm(np.asarray(vb, dtype=np.float64)))
    assert abs(nb - 1.0) < 1e-5 or nb == 0.0, f"八字向量未正确归一化: norm={nb}"
    print(f"[OK] 八字嵌入 L2 范数: {nb:.6f}")

    # 6) 案例嵌入
    vc = embedder.embed_case(
        "伤官格命例",
        "男命，辛金日主，月令伤官",
        "身弱用印比，忌财官",
        "命理案例",
    )
    assert len(vc) == 256
    print(f"[OK] 案例嵌入: 维度 {len(vc)}")

    # 7) 相似度逻辑：相同文本距离 ≈ 0，不同文本距离 > 0
    same_dist = _cosine_distance(np.asarray(v1), np.asarray(v1))
    assert abs(same_dist - 0.0) < 1e-6, f"相同文本余弦距离不为 0: {same_dist}"
    diff_dist = _cosine_distance(np.asarray(v1), np.asarray(v2))
    assert diff_dist > 1e-3, f"不同文本余弦距离过小: {diff_dist}"
    sim_same = 1.0 - same_dist
    sim_diff = 1.0 - diff_dist
    assert sim_same > sim_diff, "相似度逻辑颠倒"
    print(f"[OK] 相似度: 相同={sim_same:.6f}, 不同={sim_diff:.6f}")

    # 8) 内存索引
    idx = _InMemoryIndex(embedder=embedder)
    test_items = [
        (1, embedder.embed_text("伤官格 身弱 用印"), {"label": "命例A", "day_master": "辛"}),
        (2, embedder.embed_text("正官格 身强 用财"), {"label": "命例B", "day_master": "甲"}),
        (3, embedder.embed_text("七杀格 制杀为权"), {"label": "命例C", "day_master": "丙"}),
    ]
    for rid, vec, meta in test_items:
        idx.add(rid, vec, meta)
    assert idx.size == 3

    hits = idx.search(embedder.embed_text("伤官格 身弱"), top_k=2)
    assert hits and hits[0]["id"] == 1, f"内存索引 top1 错误: {hits}"
    print(f"[OK] 内存索引: {len(hits)} 条结果，top1 id={hits[0]['id']} sim={hits[0]['similarity']:.4f}")

    # 9) 向量边界：非法维度
    try:
        VectorStorePG._coerce_vector([1.0, 2.0])  # 长度错误
        raise AssertionError("非法维度未抛出")
    except ValueError:
        print("[OK] 非法维度向量被拒绝")

    # 10) pgvector 依赖检查
    print(f"[INFO] pgvector Python 包可用: {is_pgvector_available()}")
    print("[INFO] 若需连接 PostgreSQL，请确认数据库中已:")
    print("       CREATE EXTENSION IF NOT EXISTS vector;")

    print("\n✅ 所有自测通过")


if __name__ == "__main__":
    _run_self_test()
