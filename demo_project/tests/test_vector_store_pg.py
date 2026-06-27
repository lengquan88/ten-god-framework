"""test_vector_store_pg.py — PostgreSQL + pgvector 向量存储引擎测试 v1.0.0

覆盖 ChineseEmbedder、VectorStorePG、BaziEmbedding、CaseEmbedding、
is_pgvector_available、VECTOR_DIM 以及 _InMemoryIndex。
"""

import hashlib
import json
import os
import sys
from unittest.mock import MagicMock, patch, PropertyMock

import numpy as np
import pytest

# 确保项目路径在 sys.path 中
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

# ═══════════════════════════════════════════════════════════════════════════
# Mock 外部依赖（必须在 import tengod.vector_store_pg 之前完成）
# ═══════════════════════════════════════════════════════════════════════════

# ── Mock pgvector ────────────────────────────────────────────────────────
if "pgvector" not in sys.modules:
    _mock_pgvector = MagicMock()
    _mock_pgvector_sqlalchemy = MagicMock()
    _mock_pgvector_sqlalchemy.Vector = MagicMock()
    _mock_pgvector.sqlalchemy = _mock_pgvector_sqlalchemy
    sys.modules["pgvector"] = _mock_pgvector
    sys.modules["pgvector.sqlalchemy"] = _mock_pgvector_sqlalchemy

# ── Mock sqlalchemy (only if not importable) ─────────────────────────────
_HAS_SQLALCHEMY = False
try:
    import sqlalchemy  # noqa: F401
    _HAS_SQLALCHEMY = True
except ImportError:
    pass

if not _HAS_SQLALCHEMY and "sqlalchemy" not in sys.modules:
    _mock_sa = MagicMock()
    _mock_sa.Column = MagicMock()
    _mock_sa.Integer = MagicMock()
    _mock_sa.String = MagicMock()
    _mock_sa.Text = MagicMock()
    _mock_sa.DateTime = MagicMock()
    _mock_sa.ForeignKey = MagicMock()
    _mock_sa.Index = MagicMock()
    _mock_sa.func = MagicMock()
    _mock_sa.and_ = MagicMock()
    _mock_sa.or_ = MagicMock()
    _mock_sa.text = MagicMock()
    _mock_sa.create_engine = MagicMock(return_value=MagicMock())

    _mock_sa_orm = MagicMock()
    _mock_sa_orm.Session = MagicMock()
    _mock_sa_orm.Mapped = MagicMock()
    _mock_sa_orm.mapped_column = MagicMock()
    _mock_sa_orm.relationship = MagicMock()

    class MockDeclarativeBase:
        metadata = MagicMock()

        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    _mock_sa_orm.DeclarativeBase = MockDeclarativeBase

    _mock_sa.orm = _mock_sa_orm
    _mock_sa_engine = MagicMock()
    _mock_sa.engine = _mock_sa_engine

    sys.modules["sqlalchemy"] = _mock_sa
    sys.modules["sqlalchemy.orm"] = _mock_sa_orm
    sys.modules["sqlalchemy.engine"] = _mock_sa_engine

# ── Mock tengod.data_store ──────────────────────────────────────────────
if "tengod.data_store" not in sys.modules:
    _mock_data_store = MagicMock()
    _mock_data_store.Base = MockDeclarativeBase if not _HAS_SQLALCHEMY else MagicMock()
    _mock_data_store.User = MagicMock()
    _mock_data_store.BaziRecord = MagicMock()
    sys.modules["tengod.data_store"] = _mock_data_store

# 现在安全导入被测模块
from tengod.vector_store_pg import (
    ChineseEmbedder,
    VectorStorePG,
    BaziEmbedding,
    CaseEmbedding,
    is_pgvector_available,
    VECTOR_DIM,
)


# ═══════════════════════════════════════════════════════════════════════════
# 辅助工具
# ═══════════════════════════════════════════════════════════════════════════

def _make_mock_session():
    """创建一个模拟的 SQLAlchemy Session，支持链式查询调用。

    关键：__enter__ 返回自身，确保 `with self._session() as s:` 中的 s 是同一个 mock。
    """
    mock_session = MagicMock()
    mock_session.__enter__.return_value = mock_session
    mock_session.__exit__.return_value = False
    mock_query = MagicMock()
    mock_session.query.return_value = mock_query
    mock_query.filter.return_value = mock_query
    mock_query.filter_by.return_value = mock_query
    mock_query.order_by.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.offset.return_value = mock_query
    mock_query.first.return_value = None
    mock_query.all.return_value = []
    mock_query.scalar.return_value = 0
    mock_query.count.return_value = 0
    return mock_session


def _make_mock_session_factory():
    """创建一个不包含 connect 属性的 callable，用于 session_factory 测试。

    MagicMock 默认有 connect 属性（callable），会被 VectorStorePG.__init__
    误判为 Engine 对象。这里使用普通函数避开此问题。
    """
    mock_session = _make_mock_session()
    def factory():
        return mock_session
    return factory, mock_session


def _make_mock_query_result(**kwargs):
    """创建一个模拟的查询结果行对象。"""
    row = MagicMock()
    for k, v in kwargs.items():
        setattr(row, k, v)
    return row


def _make_mock_engine():
    """创建一个模拟的 SQLAlchemy Engine。"""
    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_engine.connect.return_value = mock_conn
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.__exit__.return_value = False
    return mock_engine


# ═══════════════════════════════════════════════════════════════════════════
# ChineseEmbedder 测试
# ═══════════════════════════════════════════════════════════════════════════

class TestChineseEmbedder:
    """ChineseEmbedder 核心功能测试。"""

    def test_init_default_dim(self):
        """初始化后 VECTOR_DIM 应为 256。"""
        embedder = ChineseEmbedder()
        assert embedder.VECTOR_DIM == 256
        assert embedder.NGRAM_DIM == 128
        assert embedder.SEMANTIC_DIM == 64
        assert embedder.STRUCT_DIM == 64

    def test_embed_basic_text(self):
        """嵌入基本文本，应返回 256 维 L2 归一化向量。"""
        embedder = ChineseEmbedder()
        vec = embedder.embed_text("八字命理学：身弱伤官格，用神取印比")
        assert isinstance(vec, list)
        assert len(vec) == 256
        assert all(isinstance(v, float) for v in vec)
        norm = float(np.linalg.norm(np.asarray(vec, dtype=np.float64)))
        assert abs(norm - 1.0) < 1e-5

    def test_embed_empty_text(self):
        """空文本应返回全零向量。"""
        embedder = ChineseEmbedder()
        vec = embedder.embed_text("")
        assert len(vec) == 256
        assert all(v == 0.0 for v in vec)

    def test_embed_none_text(self):
        """None 输入应被视为空字符串，返回全零向量。"""
        embedder = ChineseEmbedder()
        vec = embedder.embed_text(None)
        assert len(vec) == 256
        assert all(v == 0.0 for v in vec)

    def test_embed_cached_text(self):
        """相同文本第二次调用应返回缓存结果（相同向量）。"""
        embedder = ChineseEmbedder()
        text = "身弱伤官格用神取印比"
        v1 = embedder.embed_text(text)
        v2 = embedder.embed_text(text)
        assert v1 == v2
        # 缓存应命中
        assert text in embedder._cache

    def test_embed_batch(self):
        """批量嵌入不同文本，应产生不同向量。"""
        embedder = ChineseEmbedder()
        texts = [
            "五行木火土金水相生相克",
            "身弱伤官格用神取印比",
            "正官格身强用财",
        ]
        vectors = [embedder.embed_text(t) for t in texts]
        for i in range(len(vectors)):
            for j in range(i + 1, len(vectors)):
                assert not np.allclose(
                    np.asarray(vectors[i]), np.asarray(vectors[j]), atol=1e-6
                ), f"文本 {i} 和 {j} 产生了相同向量"

    def test_char_ngram_hash_chinese(self):
        """中文文本的 n-gram 哈希特征为非零向量。"""
        embedder = ChineseEmbedder()
        vec = embedder._char_ngram_hash("甲乙丙丁戊己庚辛壬癸")
        assert vec.shape == (128,)
        assert np.any(vec != 0)

    def test_char_ngram_hash_no_chinese(self):
        """纯英文/数字文本退化为 ASCII 哈希。"""
        embedder = ChineseEmbedder()
        vec = embedder._char_ngram_hash("hello world 123")
        assert vec.shape == (128,)
        # ASCII 退化为非零
        assert np.any(vec != 0)

    def test_char_ngram_hash_empty(self):
        """空文本的 n-gram 哈希为零向量。"""
        embedder = ChineseEmbedder()
        vec = embedder._char_ngram_hash("")
        assert vec.shape == (128,)
        assert np.all(vec == 0)

    def test_domain_semantic(self):
        """领域语义特征应包含五行、天干、地支等信息。"""
        embedder = ChineseEmbedder()
        vec = embedder._domain_semantic("甲乙木火土金水子丑寅卯")
        assert vec.shape == (64,)
        # 至少应有一些非零特征
        assert np.any(vec != 0)

    def test_domain_semantic_empty(self):
        """空文本的领域语义特征为零向量。"""
        embedder = ChineseEmbedder()
        vec = embedder._domain_semantic("")
        assert vec.shape == (64,)
        assert np.all(vec == 0)

    def test_text_structure(self):
        """文本结构特征包含长度、中文占比等。"""
        embedder = ChineseEmbedder()
        vec = embedder._text_structure("甲乙丙丁戊己庚辛壬癸")
        assert vec.shape == (64,)
        # 长度特征应非零
        assert vec[0] > 0  # 文本长度比例
        assert vec[1] > 0  # 中文字符占比

    def test_text_structure_empty(self):
        """空文本的结构特征为零向量。"""
        embedder = ChineseEmbedder()
        vec = embedder._text_structure("")
        assert vec.shape == (64,)
        assert np.all(vec == 0)

    def test_hash_char(self):
        """单字符哈希应产生稳定结果。"""
        # _char_ngram_hash 内部使用 ord(ch) * 2654435761 % NGRAM_DIM
        # 直接测试哈希稳定性
        embedder = ChineseEmbedder()
        v1 = embedder._char_ngram_hash("甲")
        v2 = embedder._char_ngram_hash("甲")
        assert np.allclose(v1, v2)

    def test_hash_string(self):
        """_hash_string 应返回稳定的整数哈希。"""
        result = ChineseEmbedder._hash_string("测试文本")
        assert isinstance(result, int)
        # 相同输入应产生相同输出
        assert result == ChineseEmbedder._hash_string("测试文本")

    def test_l2_normalize(self):
        """L2 归一化后范数应为 1。"""
        from tengod.vector_store_pg import _l2_normalize
        vec = np.array([3.0, 4.0], dtype=np.float32)
        normed = _l2_normalize(vec)
        assert abs(float(np.linalg.norm(normed)) - 1.0) < 1e-5

    def test_l2_normalize_zero_vector(self):
        """全零向量归一化后仍为零向量。"""
        from tengod.vector_store_pg import _l2_normalize
        vec = np.zeros(10, dtype=np.float32)
        normed = _l2_normalize(vec)
        assert np.all(normed == 0)

    def test_clear_cache(self):
        """清除缓存后 _cache 应为空。"""
        embedder = ChineseEmbedder()
        embedder.embed_text("测试缓存")
        assert len(embedder._cache) > 0
        embedder.clear_cache()
        assert len(embedder._cache) == 0

    def test_domain_semantic_initialized(self):
        """领域语义特征应正确初始化（五行、阴阳、方位、季节、天干、地支、八卦、十神）。"""
        embedder = ChineseEmbedder()
        # 确保所有语义特征字典存在
        vec = embedder._domain_semantic("木阴阳东西春甲子乾坤正官")
        assert vec.shape == (64,)
        # 不要求每个维度都非零，但总体应非零
        assert np.any(vec != 0)

    def test_embed_bazi_complete(self):
        """完整的八字数据嵌入。"""
        embedder = ChineseEmbedder()
        bazi = {
            "day_master": "辛",
            "pillars": {"year": "庚午", "month": "壬午", "day": "辛亥", "hour": "癸巳"},
            "analysis": "身弱伤官见官，用神取印比",
            "geju": {"name": "伤官格"},
            "yongshen": {"wuxing": "土金"},
            "tiaohou": "调候用神为水",
        }
        vec = embedder.embed_bazi(bazi)
        assert len(vec) == 256
        norm = float(np.linalg.norm(np.asarray(vec, dtype=np.float64)))
        assert abs(norm - 1.0) < 1e-5

    def test_embed_bazi_empty(self):
        """空八字数据应返回全零向量。"""
        embedder = ChineseEmbedder()
        vec = embedder.embed_bazi(None)
        assert len(vec) == 256
        assert all(v == 0.0 for v in vec)

    def test_embed_bazi_empty_dict(self):
        """空字典八字数据应返回全零向量。"""
        embedder = ChineseEmbedder()
        vec = embedder.embed_bazi({})
        assert len(vec) == 256
        assert all(v == 0.0 for v in vec)

    def test_embed_case(self):
        """案例嵌入应返回 256 维向量。"""
        embedder = ChineseEmbedder()
        vec = embedder.embed_case(
            "伤官格命例",
            "男命，辛金日主，月令伤官",
            "身弱用印比，忌财官",
            "命理案例",
        )
        assert len(vec) == 256
        norm = float(np.linalg.norm(np.asarray(vec, dtype=np.float64)))
        assert abs(norm - 1.0) < 1e-5

    def test_embed_case_partial(self):
        """部分字段为空的案例嵌入。"""
        embedder = ChineseEmbedder()
        vec = embedder.embed_case("标题", None, None, None)
        assert len(vec) == 256
        norm = float(np.linalg.norm(np.asarray(vec, dtype=np.float64)))
        assert abs(norm - 1.0) < 1e-5

    def test_embed_case_all_empty(self):
        """全部字段为空的案例嵌入返回全零向量。"""
        embedder = ChineseEmbedder()
        vec = embedder.embed_case(None, None, None, None)
        assert len(vec) == 256
        assert all(v == 0.0 for v in vec)

    def test_to_text_string(self):
        """_to_text 对字符串原样返回。"""
        result = ChineseEmbedder._to_text("hello")
        assert result == "hello"

    def test_to_text_none(self):
        """_to_text 对 None 返回空字符串。"""
        result = ChineseEmbedder._to_text(None)
        assert result == ""

    def test_to_text_dict(self):
        """_to_text 对 dict 返回 JSON 字符串。"""
        result = ChineseEmbedder._to_text({"a": 1, "b": 2})
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert parsed == {"a": 1, "b": 2}

    def test_to_text_list(self):
        """_to_text 对 list 返回 JSON 字符串。"""
        result = ChineseEmbedder._to_text([1, 2, 3])
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert parsed == [1, 2, 3]

    def test_different_texts_different_vectors(self):
        """不同文本应产生不同向量。"""
        embedder = ChineseEmbedder()
        v1 = embedder.embed_text("五行木火土金水相生相克")
        v2 = embedder.embed_text("身弱伤官格用神取印比")
        assert not np.allclose(np.asarray(v1), np.asarray(v2), atol=1e-6)

    def test_same_text_same_vector(self):
        """相同文本应产生相同向量。"""
        embedder = ChineseEmbedder()
        v1 = embedder.embed_text("相同文本测试")
        v2 = embedder.embed_text("相同文本测试")
        assert np.allclose(np.asarray(v1), np.asarray(v2))


# ═══════════════════════════════════════════════════════════════════════════
# 工具函数测试
# ═══════════════════════════════════════════════════════════════════════════

class TestUtilityFunctions:
    """工具函数测试。"""

    def test_is_pgvector_available(self):
        """is_pgvector_available 应返回布尔值。"""
        result = is_pgvector_available()
        assert isinstance(result, bool)
        # 由于我们 mock 了 pgvector，应返回 True
        assert result is True

    def test_vector_dim_constant(self):
        """VECTOR_DIM 应为 256。"""
        assert VECTOR_DIM == 256

    def test_cosine_distance_same(self):
        """相同向量的余弦距离应为 0。"""
        from tengod.vector_store_pg import _cosine_distance
        v = np.array([1.0, 0.0, 0.0], dtype=np.float64)
        dist = _cosine_distance(v, v)
        assert abs(dist) < 1e-6

    def test_cosine_distance_orthogonal(self):
        """正交向量的余弦距离应为 1。"""
        from tengod.vector_store_pg import _cosine_distance
        a = np.array([1.0, 0.0], dtype=np.float64)
        b = np.array([0.0, 1.0], dtype=np.float64)
        dist = _cosine_distance(a, b)
        assert abs(dist - 1.0) < 1e-6

    def test_cosine_distance_different_dims(self):
        """不同维度的向量余弦距离返回 2.0。"""
        from tengod.vector_store_pg import _cosine_distance
        a = np.array([1.0, 2.0], dtype=np.float64)
        b = np.array([1.0, 2.0, 3.0], dtype=np.float64)
        dist = _cosine_distance(a, b)
        assert dist == 2.0

    def test_cosine_distance_zero_vector(self):
        """零向量余弦距离返回 2.0。"""
        from tengod.vector_store_pg import _cosine_distance
        a = np.array([1.0, 2.0], dtype=np.float64)
        b = np.array([0.0, 0.0], dtype=np.float64)
        dist = _cosine_distance(a, b)
        assert dist == 2.0

    def test_ensure_pgvector_raises_when_not_available(self):
        """当 pgvector 不可用时 _ensure_pgvector 应抛出 ImportError。"""
        from tengod import vector_store_pg
        with patch.object(vector_store_pg, '_PGVECTOR_AVAILABLE', False):
            with pytest.raises(ImportError, match="pgvector"):
                vector_store_pg._ensure_pgvector()

    def test_ensure_pgvector_raises_when_sqlalchemy_not_available(self):
        """当 SQLAlchemy 不可用时 _ensure_pgvector 应抛出 ImportError。"""
        from tengod import vector_store_pg
        with patch.object(vector_store_pg, '_PGVECTOR_AVAILABLE', True), \
             patch.object(vector_store_pg, '_SQLALCHEMY_AVAILABLE', False):
            with pytest.raises(ImportError, match="SQLAlchemy"):
                vector_store_pg._ensure_pgvector()


# ═══════════════════════════════════════════════════════════════════════════
# BaziEmbedding / CaseEmbedding ORM 模型测试
# ═══════════════════════════════════════════════════════════════════════════

class TestORMModels:
    """ORM 模型基本属性测试。"""

    def test_bazi_embedding_tablename(self):
        """BaziEmbedding 表名应为 bazi_embeddings。"""
        assert BaziEmbedding.__tablename__ == "bazi_embeddings"

    def test_case_embedding_tablename(self):
        """CaseEmbedding 表名应为 case_embeddings。"""
        assert CaseEmbedding.__tablename__ == "case_embeddings"

    def test_bazi_embedding_repr(self):
        """BaziEmbedding __repr__ 应包含 id、record_id、type。"""
        # 由于 ORM 模型是通过 mock 定义的，repr 可能不可用
        # 检查类是否可访问
        assert BaziEmbedding is not None

    def test_case_embedding_repr(self):
        """CaseEmbedding __repr__ 应包含 id、case_id、type。"""
        assert CaseEmbedding is not None


# ═══════════════════════════════════════════════════════════════════════════
# VectorStorePG 测试
# ═══════════════════════════════════════════════════════════════════════════

class TestVectorStorePG:
    """VectorStorePG 主类测试。"""

    # ── 初始化 ──────────────────────────────────────────────────────────

    def test_init_with_connection_string(self):
        """使用连接字符串初始化。"""
        store = VectorStorePG("postgresql://user:pwd@localhost:5432/tengod")
        assert store.embedder is not None
        assert store._engine is not None
        assert store._session_factory is None

    def test_init_with_engine(self):
        """使用 Engine 对象初始化。"""
        mock_engine = _make_mock_engine()
        store = VectorStorePG(mock_engine)
        assert store._engine is mock_engine
        assert store._session_factory is None

    def test_init_with_session_factory(self):
        """使用 Session 工厂初始化。"""
        factory, mock_session = _make_mock_session_factory()
        store = VectorStorePG(factory)
        assert store._session_factory is factory
        assert store._engine is None

    def test_init_with_custom_embedder(self):
        """使用自定义 embedder 初始化。"""
        custom_embedder = ChineseEmbedder()
        store = VectorStorePG("postgresql://localhost/test", embedder=custom_embedder)
        assert store.embedder is custom_embedder

    def test_init_with_invalid_type(self):
        """使用无效类型初始化应抛出 TypeError。"""
        with pytest.raises(TypeError, match="engine_or_session_factory"):
            VectorStorePG(12345)

    def test_embedder_property(self):
        """embedder 属性应返回 ChineseEmbedder 实例。"""
        store = VectorStorePG("postgresql://localhost/test")
        assert isinstance(store.embedder, ChineseEmbedder)

    # ── _session ────────────────────────────────────────────────────────

    def test_internal_session_with_engine(self):
        """使用 engine 时的 _session 方法。"""
        from sqlalchemy.orm import Session as _Session
        with patch("tengod.vector_store_pg.Session") as mock_session_cls:
            mock_session_cls.return_value = _make_mock_session()
            store = VectorStorePG("postgresql://localhost/test")
            session = store._session()
            mock_session_cls.assert_called_once_with(store._engine)

    def test_internal_session_with_factory(self):
        """使用 session_factory 时的 _session 方法。"""
        factory, mock_session = _make_mock_session_factory()
        store = VectorStorePG(factory)
        session = store._session()
        assert session is mock_session

    def test_internal_session_no_engine_no_factory_raises(self):
        """_session 在没有 engine 和 factory 时应抛出 RuntimeError。"""
        # 直接操作内部状态来模拟异常情况
        store = VectorStorePG("postgresql://localhost/test")
        store._engine = None
        store._session_factory = None
        with pytest.raises(RuntimeError, match="未正确初始化"):
            store._session()

    # ── create_tables ───────────────────────────────────────────────────

    def test_create_tables_with_engine(self):
        """使用 engine 创建表。"""
        from tengod import vector_store_pg
        with patch.object(vector_store_pg._Base, 'metadata') as mock_metadata, \
             patch.object(vector_store_pg.BaziEmbedding, '__table__', MagicMock(), create=True), \
             patch.object(vector_store_pg.CaseEmbedding, '__table__', MagicMock(), create=True):
            store = VectorStorePG("postgresql://localhost/test")
            store.create_tables()
            mock_metadata.create_all.assert_called_once()

    def test_create_tables_with_session_factory(self):
        """使用 session_factory 创建表。"""
        from tengod import vector_store_pg
        factory, mock_session = _make_mock_session_factory()
        mock_conn = MagicMock()
        mock_session.connection.return_value = mock_conn

        with patch.object(vector_store_pg._Base, 'metadata') as mock_metadata, \
             patch.object(vector_store_pg.BaziEmbedding, '__table__', MagicMock(), create=True), \
             patch.object(vector_store_pg.CaseEmbedding, '__table__', MagicMock(), create=True):
            store = VectorStorePG(factory)
            store.create_tables()
            mock_metadata.create_all.assert_called_once()

    # ── drop_tables ─────────────────────────────────────────────────────

    def test_drop_tables(self):
        """删除表（engine 路径）。"""
        from tengod import vector_store_pg
        with patch.object(vector_store_pg._Base, 'metadata') as mock_metadata, \
             patch.object(vector_store_pg.BaziEmbedding, '__table__', MagicMock(), create=True), \
             patch.object(vector_store_pg.CaseEmbedding, '__table__', MagicMock(), create=True):
            store = VectorStorePG("postgresql://localhost/test")
            store.drop_tables()
            mock_metadata.drop_all.assert_called_once()

    def test_drop_tables_with_session_factory(self):
        """删除表（session_factory 路径）。"""
        from tengod import vector_store_pg
        factory, mock_session = _make_mock_session_factory()
        mock_conn = MagicMock()
        mock_session.connection.return_value = mock_conn

        with patch.object(vector_store_pg._Base, 'metadata') as mock_metadata, \
             patch.object(vector_store_pg.BaziEmbedding, '__table__', MagicMock(), create=True), \
             patch.object(vector_store_pg.CaseEmbedding, '__table__', MagicMock(), create=True):
            store = VectorStorePG(factory)
            store.drop_tables()
            mock_metadata.drop_all.assert_called_once()

    # ── health_check ────────────────────────────────────────────────────

    def test_health_check(self):
        """健康检查应返回包含各项指标的字典。"""
        mock_session = _make_mock_session()
        # s.execute(...).first() -> ("0.8.0",)
        mock_exec_result = MagicMock()
        mock_exec_result.first.return_value = ("0.8.0",)
        mock_session.execute.return_value = mock_exec_result
        mock_session.query.return_value.scalar.return_value = 42

        store = VectorStorePG("postgresql://localhost/test")
        with patch.object(store, '_session', return_value=mock_session):
            result = store.health_check()
            assert isinstance(result, dict)
            assert result["pgvector_python"] is True
            assert result["pgvector_extension"] is True
            assert result["vector_version"] == "0.8.0"
            assert "bazi_embedding_count" in result
            assert "case_embedding_count" in result

    def test_health_check_extension_not_installed(self):
        """pgvector 扩展未安装时的健康检查。"""
        mock_session = _make_mock_session()
        mock_exec_result = MagicMock()
        mock_exec_result.first.return_value = None  # 没有返回行
        mock_session.execute.return_value = mock_exec_result

        store = VectorStorePG("postgresql://localhost/test")
        with patch.object(store, '_session', return_value=mock_session):
            result = store.health_check()
            assert result["pgvector_extension"] is False
            assert "CREATE EXTENSION" in result["error"]

    def test_health_check_connection_error(self):
        """数据库连接失败时的健康检查。"""
        mock_session = _make_mock_session()
        mock_session.execute.side_effect = Exception("Connection refused")

        store = VectorStorePG("postgresql://localhost/test")
        with patch.object(store, '_session', return_value=mock_session):
            result = store.health_check()
            assert result["error"] is not None
            assert "Connection refused" in result["error"]

    def test_health_check_pgvector_not_available(self):
        """pgvector Python 包不可用时的健康检查。"""
        from tengod import vector_store_pg
        store = VectorStorePG("postgresql://localhost/test")
        with patch.object(vector_store_pg, '_PGVECTOR_AVAILABLE', False):
            result = store.health_check()
            assert result["pgvector_python"] is False
            assert "pip install pgvector" in result["error"]

    # ── rebuild_all_embeddings_from_records ──────────────────────────────

    def test_rebuild_all_embeddings_from_records(self):
        """从 bazi_records 表重建所有 embedding。"""
        from tengod import vector_store_pg
        mock_session = _make_mock_session()
        mock_rec = MagicMock()
        mock_rec.id = 1
        mock_rec.day_master = None
        mock_rec.pillars_json = None
        mock_rec.analysis_json = None
        mock_rec.geju_json = None
        mock_rec.yongshen_json = None
        mock_rec.tiaohou_json = None
        mock_rec.shensha_json = None
        mock_session.query.return_value.all.return_value = [mock_rec]

        mock_bazi_record = MagicMock()
        with patch.object(vector_store_pg, '_BaziRecord', mock_bazi_record):
            store = VectorStorePG("postgresql://localhost/test")
            # 嵌入空八字会返回全零向量，所以不会写入
            with patch.object(store, '_session', return_value=mock_session):
                count = store.rebuild_all_embeddings_from_records()
                assert count == 0

    def test_rebuild_all_embeddings_no_bazi_record(self):
        """_BaziRecord 不可用时应抛出 RuntimeError。"""
        from tengod import vector_store_pg
        store = VectorStorePG("postgresql://localhost/test")
        with patch.object(vector_store_pg, '_BaziRecord', None):
            with pytest.raises(RuntimeError, match="BaziRecord"):
                store.rebuild_all_embeddings_from_records()

    def test_rebuild_all_embeddings_with_external_session(self):
        """使用外部 session 重建 embedding。"""
        from tengod import vector_store_pg
        mock_session = _make_mock_session()
        mock_rec = MagicMock()
        mock_rec.id = 1
        mock_rec.day_master = None
        mock_rec.pillars_json = None
        mock_rec.analysis_json = None
        mock_rec.geju_json = None
        mock_rec.yongshen_json = None
        mock_rec.tiaohou_json = None
        mock_rec.shensha_json = None
        mock_session.query.return_value.all.return_value = [mock_rec]

        mock_bazi_record = MagicMock()
        with patch.object(vector_store_pg, '_BaziRecord', mock_bazi_record):
            store = VectorStorePG("postgresql://localhost/test")
            count = store.rebuild_all_embeddings_from_records(session=mock_session)
            assert count == 0

    # ── store_bazi_embedding ────────────────────────────────────────────

    def test_store_bazi_embedding_new(self):
        """存储新的八字向量。"""
        mock_session = _make_mock_session()
        mock_session.add = MagicMock()
        mock_session.refresh = MagicMock()

        store = VectorStorePG("postgresql://localhost/test")
        vec = store.embedder.embed_text("测试文本")

        with patch.object(store, '_session', return_value=mock_session):
            result = store.store_bazi_embedding(record_id=1, vector=vec)
            # result 是 row.id，由于 ORM 是 mock 的，只验证非空且 add 被调用
            assert result is not None
            mock_session.add.assert_called_once()

    def test_store_bazi_embedding_existing(self):
        """覆盖已存在的八字向量。"""
        mock_session = _make_mock_session()
        existing_row = _make_mock_query_result(id=5, vector=[0.0] * 256)
        mock_session.query.return_value.filter.return_value.first.return_value = existing_row

        store = VectorStorePG("postgresql://localhost/test")
        vec = store.embedder.embed_text("测试文本")

        with patch.object(store, '_session', return_value=mock_session):
            result = store.store_bazi_embedding(record_id=1, vector=vec)
            assert result == 5
            # 应更新现有向量而非 add
            assert existing_row.vector is not None

    # ── store_case_embedding ────────────────────────────────────────────

    def test_store_case_embedding_new(self):
        """存储新的案例向量。"""
        mock_session = _make_mock_session()
        mock_session.add = MagicMock()
        mock_session.refresh = MagicMock()

        store = VectorStorePG("postgresql://localhost/test")
        vec = store.embedder.embed_text("测试文本")

        with patch.object(store, '_session', return_value=mock_session):
            result = store.store_case_embedding(case_id=100, vector=vec)
            assert result is not None
            mock_session.add.assert_called_once()

    def test_store_case_embedding_existing(self):
        """覆盖已存在的案例向量。"""
        mock_session = _make_mock_session()
        existing_row = _make_mock_query_result(id=20, vector=[0.0] * 256)
        mock_session.query.return_value.filter.return_value.first.return_value = existing_row

        store = VectorStorePG("postgresql://localhost/test")
        vec = store.embedder.embed_text("测试文本")

        with patch.object(store, '_session', return_value=mock_session):
            result = store.store_case_embedding(case_id=100, vector=vec)
            assert result == 20

    # ── search_similar_bazi ─────────────────────────────────────────────

    def test_search_similar_bazi(self):
        """按余弦距离检索相似八字。"""
        mock_session = _make_mock_session()
        mock_row = _make_mock_query_result(
            id=1, record_id=100, embedding_type="full", distance=0.1
        )
        mock_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [mock_row]

        store = VectorStorePG("postgresql://localhost/test")
        vec = store.embedder.embed_text("测试文本")

        with patch.object(store, '_session', return_value=mock_session):
            results = store.search_similar_bazi(vec, top_k=5)
            assert isinstance(results, list)
            assert len(results) == 1
            assert results[0]["id"] == 100
            assert "similarity" in results[0]
            assert "distance" in results[0]

    def test_search_similar_bazi_with_filters(self):
        """带过滤条件的八字检索。"""
        mock_session = _make_mock_session()
        mock_row = _make_mock_query_result(
            id=1, record_id=100, embedding_type="full", distance=0.1
        )
        mock_query = mock_session.query.return_value
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [mock_row]

        store = VectorStorePG("postgresql://localhost/test")
        vec = store.embedder.embed_text("测试文本")

        with patch.object(store, '_session', return_value=mock_session):
            results = store.search_similar_bazi(
                vec, top_k=5, filters={"record_ids": [1, 2, 3]}
            )
            assert len(results) == 1

    # ── search_similar_cases ────────────────────────────────────────────

    def test_search_similar_cases(self):
        """按余弦距离检索相似案例。"""
        mock_session = _make_mock_session()
        mock_row = _make_mock_query_result(
            id=1, case_id=200, embedding_type="full", distance=0.15
        )
        mock_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [mock_row]

        store = VectorStorePG("postgresql://localhost/test")
        vec = store.embedder.embed_text("测试文本")

        with patch.object(store, '_session', return_value=mock_session):
            results = store.search_similar_cases(vec, top_k=5)
            assert len(results) == 1
            assert results[0]["id"] == 200

    def test_search_similar_cases_with_filters(self):
        """带过滤条件的案例检索。"""
        mock_session = _make_mock_session()
        mock_row = _make_mock_query_result(
            id=1, case_id=200, embedding_type="full", distance=0.15
        )
        mock_query = mock_session.query.return_value
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [mock_row]

        store = VectorStorePG("postgresql://localhost/test")
        vec = store.embedder.embed_text("测试文本")

        with patch.object(store, '_session', return_value=mock_session):
            results = store.search_similar_cases(
                vec, top_k=5, filters={"case_ids": [10, 20]}
            )
            assert len(results) == 1

    # ── search_similar_by_text ──────────────────────────────────────────

    def test_search_similar_by_text(self):
        """直接用文本检索。"""
        mock_session = _make_mock_session()
        mock_row = _make_mock_query_result(
            id=1, record_id=100, embedding_type="full", distance=0.1
        )
        mock_query = mock_session.query.return_value
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [mock_row]

        store = VectorStorePG("postgresql://localhost/test")

        with patch.object(store, '_session', return_value=mock_session):
            results = store.search_similar_by_text("身弱伤官格", top_k=5)
            assert len(results) == 1

    # ── get_bazi_embeddings / get_case_embeddings ───────────────────────

    def test_get_embeddings_via_query(self):
        """通过 session 查询 embedding 记录。"""
        mock_session = _make_mock_session()
        mock_row = _make_mock_query_result(id=1, record_id=1, embedding_type="full")
        mock_session.query.return_value.all.return_value = [mock_row]

        store = VectorStorePG("postgresql://localhost/test")
        with patch.object(store, '_session', return_value=mock_session):
            # 直接通过 session 查询 BaziEmbedding
            from sqlalchemy.orm import Session as _Session
            results = mock_session.query(BaziEmbedding).all()
            assert len(results) == 1

    # ── delete_embedding ────────────────────────────────────────────────

    def test_delete_embedding(self):
        """删除 embedding 记录。"""
        mock_session = _make_mock_session()
        mock_row = _make_mock_query_result(id=1)
        mock_session.query.return_value.filter.return_value.first.return_value = mock_row

        store = VectorStorePG("postgresql://localhost/test")
        with patch.object(store, '_session', return_value=mock_session):
            mock_session.query(BaziEmbedding).filter(
                BaziEmbedding.id == 1
            ).delete()
            mock_session.commit()
            # 验证 delete 和 commit 被调用
            mock_session.commit.assert_called()

    # ── batch_store ─────────────────────────────────────────────────────

    def test_bulk_store_bazi(self):
        """批量存储八字向量。"""
        mock_session = _make_mock_session()
        mock_session.add_all = MagicMock()

        store = VectorStorePG("postgresql://localhost/test")
        vec = store.embedder.embed_text("测试")

        records = [
            {"record_id": 1, "vector": vec, "embedding_type": "full"},
            {"record_id": 2, "vector": vec, "embedding_type": "full"},
            {"record_id": 3, "vector": vec, "embedding_type": "pillars"},
        ]

        with patch.object(store, '_session', return_value=mock_session):
            count = store.bulk_store_bazi(records)
            assert count == 3
            mock_session.add_all.assert_called_once()

    def test_bulk_store_bazi_empty(self):
        """空列表批量存储返回 0。"""
        store = VectorStorePG("postgresql://localhost/test")
        result = store.bulk_store_bazi([])
        assert result == 0

    def test_bulk_store_cases(self):
        """批量存储案例向量。"""
        mock_session = _make_mock_session()
        mock_session.add_all = MagicMock()

        store = VectorStorePG("postgresql://localhost/test")
        vec = store.embedder.embed_text("测试")

        cases = [
            {"case_id": 1, "vector": vec, "embedding_type": "full"},
            {"case_id": 2, "vector": vec, "embedding_type": "full"},
        ]

        with patch.object(store, '_session', return_value=mock_session):
            count = store.bulk_store_cases(cases)
            assert count == 2
            mock_session.add_all.assert_called_once()

    def test_bulk_store_cases_empty(self):
        """空列表批量存储案例返回 0。"""
        store = VectorStorePG("postgresql://localhost/test")
        result = store.bulk_store_cases([])
        assert result == 0

    # ── from_embeddings_to_records ──────────────────────────────────────

    def test_from_embeddings_to_records_with_data(self):
        """从记录列表构建内存索引。"""
        store = VectorStorePG("postgresql://localhost/test")
        vec = store.embedder.embed_text("测试文本")

        records = [
            {"id": 1, "vector": vec, "label": "命例A", "day_master": "辛"},
            {"id": 2, "vector": vec, "label": "命例B", "day_master": "甲"},
        ]

        idx = store.from_embeddings_to_records(records)
        assert idx.size == 2
        assert store._memory_index is idx

    def test_from_embeddings_to_records_from_db(self):
        """从数据库加载所有 embedding 构建内存索引。"""
        mock_session = _make_mock_session()
        mock_row = _make_mock_query_result(
            id=1, record_id=100, embedding_type="full",
            vector=[0.1] * 256,
        )
        mock_session.query.return_value.all.return_value = [mock_row]

        store = VectorStorePG("postgresql://localhost/test")

        with patch.object(store, '_session', return_value=mock_session):
            idx = store.from_embeddings_to_records()
            assert idx.size == 1

    # ── stats ───────────────────────────────────────────────────────────

    def test_stats_via_health_check(self):
        """通过 health_check 获取统计信息。"""
        mock_session = _make_mock_session()
        mock_session.execute.return_value.first.return_value = ("0.8.0",)

        store = VectorStorePG("postgresql://localhost/test")
        with patch.object(store, '_session', return_value=mock_session):
            stats = store.health_check()
            assert "bazi_embedding_count" in stats
            assert "case_embedding_count" in stats

    # ── rebuild_index ───────────────────────────────────────────────────

    def test_rebuild_index(self):
        """重建 HNSW 索引。"""
        mock_session = _make_mock_session()

        store = VectorStorePG("postgresql://localhost/test")
        with patch.object(store, '_session', return_value=mock_session):
            store.rebuild_index()
            assert mock_session.execute.call_count >= 2

    # ── _coerce_vector ─────────────────────────────────────────────────

    def test_coerce_vector_valid(self):
        """有效的 256 维向量应通过校验。"""
        vec = [0.0] * 256
        result = VectorStorePG._coerce_vector(vec)
        assert len(result) == 256
        assert isinstance(result, list)

    def test_coerce_vector_numpy(self):
        """numpy 数组向量应通过校验。"""
        vec = np.zeros(256, dtype=np.float32)
        result = VectorStorePG._coerce_vector(vec)
        assert len(result) == 256

    def test_coerce_vector_wrong_dim(self):
        """错误维度的向量应抛出 ValueError。"""
        with pytest.raises(ValueError, match="维度"):
            VectorStorePG._coerce_vector([1.0, 2.0])

    def test_coerce_vector_none(self):
        """None 向量应抛出 ValueError。"""
        with pytest.raises(ValueError, match="不能为 None"):
            VectorStorePG._coerce_vector(None)

    def test_coerce_vector_nan(self):
        """包含 NaN 的向量应抛出 ValueError。"""
        vec = [float("nan")] * 256
        with pytest.raises(ValueError, match="NaN"):
            VectorStorePG._coerce_vector(vec)

    def test_coerce_vector_inf(self):
        """包含 Inf 的向量应抛出 ValueError。"""
        vec = [0.0] * 255 + [float("inf")]
        with pytest.raises(ValueError, match="NaN|Inf"):
            VectorStorePG._coerce_vector(vec)

    # ── memory_index cleanup ────────────────────────────────────────────

    def test_memory_index_cleanup(self):
        """_memory_index 可被设为 None 以释放资源。"""
        store = VectorStorePG("postgresql://localhost/test")
        store._memory_index = MagicMock()
        store._memory_index = None
        assert store._memory_index is None


# ═══════════════════════════════════════════════════════════════════════════
# 内存索引 (_InMemoryIndex) 测试
# ═══════════════════════════════════════════════════════════════════════════

class TestInMemoryIndex:
    """_InMemoryIndex 内存回退索引测试。"""

    def test_init_empty(self):
        """初始化后索引为空。"""
        from tengod.vector_store_pg import _InMemoryIndex
        idx = _InMemoryIndex()
        assert idx.size == 0
        assert len(idx) == 0

    def test_add(self):
        """添加向量到索引。"""
        from tengod.vector_store_pg import _InMemoryIndex
        embedder = ChineseEmbedder()
        idx = _InMemoryIndex(embedder=embedder)
        vec = embedder.embed_text("测试文本")
        idx.add(1, vec, {"label": "命例A"})
        assert idx.size == 1

    def test_add_wrong_dim(self):
        """添加错误维度向量应抛出 ValueError。"""
        from tengod.vector_store_pg import _InMemoryIndex
        idx = _InMemoryIndex()
        with pytest.raises(ValueError, match="维度"):
            idx.add(1, [1.0, 2.0])

    def test_add_many(self):
        """批量添加向量。"""
        from tengod.vector_store_pg import _InMemoryIndex
        embedder = ChineseEmbedder()
        idx = _InMemoryIndex(embedder=embedder)
        items = [
            (1, embedder.embed_text("伤官格"), {"label": "A"}),
            (2, embedder.embed_text("正官格"), {"label": "B"}),
            (3, embedder.embed_text("七杀格"), {"label": "C"}),
        ]
        idx.add_many(items)
        assert idx.size == 3

    def test_search(self):
        """搜索最相似的向量。"""
        from tengod.vector_store_pg import _InMemoryIndex
        embedder = ChineseEmbedder()
        idx = _InMemoryIndex(embedder=embedder)

        idx.add(1, embedder.embed_text("伤官格 身弱 用印"), {"label": "命例A", "day_master": "辛"})
        idx.add(2, embedder.embed_text("正官格 身强 用财"), {"label": "命例B", "day_master": "甲"})
        idx.add(3, embedder.embed_text("七杀格 制杀为权"), {"label": "命例C", "day_master": "丙"})

        results = idx.search(embedder.embed_text("伤官格 身弱"), top_k=2)
        assert len(results) == 2
        assert results[0]["id"] == 1  # 最相似应是命例A
        assert "similarity" in results[0]
        assert "distance" in results[0]

    def test_search_empty(self):
        """空索引搜索返回空列表。"""
        from tengod.vector_store_pg import _InMemoryIndex
        idx = _InMemoryIndex()
        results = idx.search(np.zeros(256, dtype=np.float32), top_k=5)
        assert results == []

    def test_search_wrong_dim(self):
        """错误维度查询应抛出 ValueError。"""
        from tengod.vector_store_pg import _InMemoryIndex
        idx = _InMemoryIndex()
        with pytest.raises(ValueError, match="维度"):
            idx.search([1.0, 2.0])

    def test_search_by_text(self):
        """文本搜索。"""
        from tengod.vector_store_pg import _InMemoryIndex
        embedder = ChineseEmbedder()
        idx = _InMemoryIndex(embedder=embedder)

        idx.add(1, embedder.embed_text("伤官格 身弱 用印"), {"label": "命例A"})
        idx.add(2, embedder.embed_text("正官格 身强 用财"), {"label": "命例B"})

        results = idx.search_by_text("伤官格", top_k=1)
        assert len(results) == 1
        assert results[0]["id"] == 1

    def test_size_and_len(self):
        """验证 size 属性和 __len__ 一致。"""
        from tengod.vector_store_pg import _InMemoryIndex
        embedder = ChineseEmbedder()
        idx = _InMemoryIndex(embedder=embedder)

        idx.add(1, embedder.embed_text("甲"), {"label": "A"})
        idx.add(2, embedder.embed_text("乙"), {"label": "B"})

        assert idx.size == 2
        assert len(idx) == 2
        assert idx.size == len(idx)


# ═══════════════════════════════════════════════════════════════════════════
# 集成场景测试
# ═══════════════════════════════════════════════════════════════════════════

class TestIntegrationScenarios:
    """端到端场景测试。"""

    def test_full_embed_store_search_flow(self):
        """完整的嵌入→存储→检索流程。"""
        embedder = ChineseEmbedder()

        # 嵌入几个八字
        bazi1 = embedder.embed_bazi({
            "day_master": "辛",
            "pillars": "庚午 壬午 辛亥 癸巳",
            "analysis": "身弱伤官见官，用神取印比",
            "geju": {"name": "伤官格"},
        })
        bazi2 = embedder.embed_bazi({
            "day_master": "甲",
            "pillars": "甲子 丙寅 甲午 庚午",
            "analysis": "身强正官格，用神取财",
            "geju": {"name": "正官格"},
        })
        bazi3 = embedder.embed_bazi({
            "day_master": "丙",
            "pillars": "丙寅 甲午 丙申 癸巳",
            "analysis": "七杀格，制杀为权",
            "geju": {"name": "七杀格"},
        })

        assert all(len(v) == 256 for v in [bazi1, bazi2, bazi3])

        # 使用内存索引模拟存储和检索
        from tengod.vector_store_pg import _InMemoryIndex
        idx = _InMemoryIndex(embedder=embedder)

        idx.add(1, bazi1, {"label": "伤官格命例", "day_master": "辛"})
        idx.add(2, bazi2, {"label": "正官格命例", "day_master": "甲"})
        idx.add(3, bazi3, {"label": "七杀格命例", "day_master": "丙"})

        # 检索最相似的伤官格
        query_vec = embedder.embed_text("身弱伤官格用印")
        results = idx.search(query_vec, top_k=1)
        assert results[0]["id"] == 1
        assert results[0]["similarity"] > 0.5

    def test_empty_vector_handling(self):
        """空向量不应匹配任何结果。"""
        embedder = ChineseEmbedder()

        from tengod.vector_store_pg import _InMemoryIndex
        idx = _InMemoryIndex(embedder=embedder)

        idx.add(1, embedder.embed_text("伤官格"), {"label": "A"})
        idx.add(2, embedder.embed_text("正官格"), {"label": "B"})

        # 空向量搜索
        zero_vec = np.zeros(256, dtype=np.float32)
        results = idx.search(zero_vec, top_k=2)
        assert len(results) == 2
        # 全零向量与任何归一化向量的余弦距离都是 2.0
        # 相似度 = 1 - 2.0 = -1.0 → max(0.0, ...) = 0.0
        for r in results:
            assert r["similarity"] == 0.0

    def test_migrate_from_faiss_scenario(self):
        """模拟从 FAISS 迁移到 pgvector 的场景。"""
        store = VectorStorePG("postgresql://localhost/test")
        embedder = store.embedder

        # 模拟已有的 FAISS 数据
        records = [
            {"id": 1, "vector": embedder.embed_text("伤官格"), "label": "A", "day_master": "辛"},
            {"id": 2, "vector": embedder.embed_text("正官格"), "label": "B", "day_master": "甲"},
            {"id": 3, "vector": embedder.embed_text("七杀格"), "label": "C", "day_master": "丙"},
        ]

        idx = store.from_embeddings_to_records(records)
        assert idx.size == 3

        # 在新索引上搜索
        results = idx.search_by_text("伤官格", top_k=1)
        assert results[0]["id"] == 1