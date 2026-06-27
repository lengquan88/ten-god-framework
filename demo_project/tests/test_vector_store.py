"""test_vector_store.py — 向量存储与语义检索引擎测试 v1.0.0

覆盖 ChineseEmbedder、SemanticSearchResult、VectorStore 及模块级便捷函数。
"""

import json
import os
import sys
import tempfile
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# 确保项目路径在 sys.path 中
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from tengod.vector_store import (
    ChineseEmbedder,
    SemanticSearchResult,
    VectorStore,
    build_knowledge_vectors,
    get_vector_store,
    recommend_related,
    search_similar,
    _WUXING_ONEHOT,
    _YINYANG_ONEHOT,
    _DIRECTION_ONEHOT,
    _SEASON_ONEHOT,
    _TIANGAN_INDEX,
    _DIZHI_INDEX,
    _BAGUA_SYMBOLS,
    _SHIGAN_CATEGORIES,
)


# Mock FAISS module (not installed in test environment)
if "faiss" not in sys.modules:
    _mock_faiss = MagicMock()
    _mock_index = MagicMock()
    _mock_faiss.IndexFlatIP = MagicMock(return_value=_mock_index)
    _mock_faiss.write_index = MagicMock()
    _mock_faiss.read_index = MagicMock(return_value=_mock_index)
    sys.modules["faiss"] = _mock_faiss


# ============================================================================
# Mock 辅助函数
# ============================================================================

def _make_mock_kg():
    """创建一个模拟的知识图谱对象，包含所有必需的属性。"""
    kg = MagicMock()
    kg._elements = {
        "木": {"color": "青", "direction": "东", "season": "春", "organ": "肝", "description": "木曰曲直"},
        "火": {"color": "赤", "direction": "南", "season": "夏", "organ": "心", "description": "火曰炎上"},
        "土": {"color": "黄", "direction": "中", "season": "长夏", "organ": "脾", "description": "土爰稼穑"},
        "金": {"color": "白", "direction": "西", "season": "秋", "organ": "肺", "description": "金曰从革"},
        "水": {"color": "黑", "direction": "北", "season": "冬", "organ": "肾", "description": "水曰润下"},
    }
    kg._trigrams = {
        "乾": {"nature": "天", "family_role": "父", "element": "金", "direction": "西北", "body_part": "头"},
        "坤": {"nature": "地", "family_role": "母", "element": "土", "direction": "西南", "body_part": "腹"},
    }
    kg._tiangan = {
        "甲": {"wuxing": "木", "yinyang": "阳", "direction": "东"},
        "乙": {"wuxing": "木", "yinyang": "阴", "direction": "东"},
    }
    kg._dizhi = {
        "子": {"wuxing": "水", "yinyang": "阳", "zodiac": "鼠", "hour": "23-1", "direction": "北", "hidden_stems": "癸"},
        "丑": {"wuxing": "土", "yinyang": "阴", "zodiac": "牛", "hour": "1-3", "direction": "东北", "hidden_stems": "己癸辛"},
    }
    kg._shigan = {
        "正官": {"category": "克我阴阳异性", "description": "正官格"},
        "七杀": {"category": "克我阴阳同性", "description": "七杀格"},
    }
    kg.get_liushisi_gua.return_value = [
        {"name": "乾为天", "upper_trigram": "乾", "lower_trigram": "乾"},
        {"name": "坤为地", "upper_trigram": "坤", "lower_trigram": "坤"},
    ]
    return kg


def _make_mock_faiss_index():
    """创建一个模拟的 FAISS index，返回预设的搜索结果。"""
    mock_index = MagicMock()
    mock_index.search.return_value = (
        np.array([[0.95, 0.85, 0.75, 0.65, 0.55]], dtype=np.float32),
        np.array([[0, 1, 2, 3, 4]], dtype=np.int64),
    )
    return mock_index


@pytest.fixture
def mock_faiss():
    """Mock FAISS 模块，替换 sys.modules 中的 faiss。"""
    mock_faiss_mod = MagicMock()
    mock_index = MagicMock()
    # 默认 search 返回有效结果（懒初始化 / 搜索 / 推荐测试需要）
    mock_index.search.return_value = (
        np.array([[0.95, 0.85, 0.75, 0.65, 0.55]], dtype=np.float32),
        np.array([[0, 1, 2, 3, 4]], dtype=np.int64),
    )
    mock_faiss_mod.IndexFlatIP = MagicMock(return_value=mock_index)

    # write_index 需要实际创建文件（save 测试需要断言文件存在）
    def _write_index(index, path):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "wb") as f:
            f.write(b"mock_index")

    mock_faiss_mod.write_index = MagicMock(side_effect=_write_index)

    # read_index 返回一个 MagicMock（load 测试需要）
    mock_faiss_mod.read_index = MagicMock(return_value=MagicMock())

    with patch.dict("sys.modules", {"faiss": mock_faiss_mod}):
        yield mock_faiss_mod


# ============================================================================
# ChineseEmbedder 测试
# ============================================================================

class TestChineseEmbedder:
    """测试中文文本嵌入器"""

    # ── 基础嵌入 ──────────────────────────────────────────────────────

    def test_embed_empty_text(self):
        """空字符串返回零向量"""
        emb = ChineseEmbedder()
        vec = emb.embed("")
        assert vec.shape == (256,)
        assert np.allclose(vec, 0.0)

    def test_embed_whitespace_only(self):
        """纯空白文本返回零向量"""
        emb = ChineseEmbedder()
        vec = emb.embed("   \t\n  ")
        assert vec.shape == (256,)
        assert np.allclose(vec, 0.0)

    def test_embed_returns_correct_dimension(self):
        """嵌入向量维度为 256"""
        emb = ChineseEmbedder()
        vec = emb.embed("天地玄黄宇宙洪荒")
        assert vec.shape == (256,)
        assert vec.dtype == np.float32

    def test_embed_is_l2_normalized(self):
        """嵌入向量经过 L2 归一化"""
        emb = ChineseEmbedder()
        vec = emb.embed("道可道非常道名可名非常名")
        norm = np.linalg.norm(vec)
        assert np.isclose(norm, 1.0, atol=1e-6)

    def test_embed_deterministic(self):
        """相同文本产生相同向量"""
        emb = ChineseEmbedder()
        text = "易经八卦乾坤"
        v1 = emb.embed(text)
        v2 = emb.embed(text)
        assert np.array_equal(v1, v2)

    def test_embed_different_texts_different(self):
        """不同文本产生不同向量"""
        emb = ChineseEmbedder()
        v1 = emb.embed("甲乙丙丁")
        v2 = emb.embed("子丑寅卯")
        assert not np.allclose(v1, v2)

    def test_embed_single_chinese_char(self):
        """单个中文字符"""
        emb = ChineseEmbedder()
        vec = emb.embed("木")
        assert vec.shape == (256,)
        assert np.linalg.norm(vec) > 0

    def test_embed_no_chinese_characters(self):
        """无中文字符的文本"""
        emb = ChineseEmbedder()
        vec = emb.embed("hello world 123")
        assert vec.shape == (256,)

    def test_embed_long_text(self):
        """长文本嵌入"""
        emb = ChineseEmbedder()
        text = "天地玄黄宇宙洪荒日月盈昃辰宿列张" * 10
        vec = emb.embed(text)
        assert vec.shape == (256,)

    # ── 缓存 ────────────────────────────────────────────────────────

    def test_embed_cache_returns_same_object(self):
        """缓存命中返回相同对象（引用相同）"""
        emb = ChineseEmbedder()
        text = "河图洛书"
        v1 = emb.embed(text)
        v2 = emb.embed(text)
        assert v1 is v2

    def test_clear_cache(self):
        """清除缓存后重新计算"""
        emb = ChineseEmbedder()
        text = "五行八卦"
        v1 = emb.embed(text)
        emb.clear_cache()
        v2 = emb.embed(text)
        assert v1 is not v2
        assert np.array_equal(v1, v2)

    # ── 批量嵌入 ────────────────────────────────────────────────────

    def test_embed_batch(self):
        """批量嵌入返回正确形状"""
        emb = ChineseEmbedder()
        texts = ["木火土金水", "乾坤震巽", "甲乙丙丁"]
        vecs = emb.embed_batch(texts)
        assert vecs.shape == (3, 256)
        assert vecs.dtype == np.float32

    def test_embed_batch_single(self):
        """批量嵌入单个文本"""
        emb = ChineseEmbedder()
        vecs = emb.embed_batch(["天地"])
        assert vecs.shape == (1, 256)

    def test_embed_batch_empty_list(self):
        """批量嵌入空列表"""
        emb = ChineseEmbedder()
        vecs = emb.embed_batch([])
        # np.array([]) -> shape (0,)
        assert vecs.shape == (0,)

    # ── 领域语义 ────────────────────────────────────────────────────

    def test_embed_with_wuxing_terms(self):
        emb = ChineseEmbedder()
        vec = emb.embed("木火土金水")
        assert vec.shape == (256,)

    def test_embed_with_yinyang_terms(self):
        emb = ChineseEmbedder()
        vec = emb.embed("阴阳调和")
        assert vec.shape == (256,)

    def test_embed_with_direction_terms(self):
        emb = ChineseEmbedder()
        vec = emb.embed("东南西北中")
        assert vec.shape == (256,)

    def test_embed_with_season_terms(self):
        emb = ChineseEmbedder()
        vec = emb.embed("春夏秋冬")
        assert vec.shape == (256,)

    def test_embed_with_tiangan_terms(self):
        emb = ChineseEmbedder()
        vec = emb.embed("甲乙丙丁戊己庚辛壬癸")
        assert vec.shape == (256,)

    def test_embed_with_dizhi_terms(self):
        emb = ChineseEmbedder()
        vec = emb.embed("子丑寅卯辰巳午未申酉戌亥")
        assert vec.shape == (256,)

    def test_embed_with_bagua_terms(self):
        emb = ChineseEmbedder()
        vec = emb.embed("乾坤震巽坎离艮兑")
        assert vec.shape == (256,)

    def test_embed_with_bagua_symbols(self):
        emb = ChineseEmbedder()
        vec = emb.embed("☰☷☳☴")
        assert vec.shape == (256,)

    def test_embed_with_shigan_terms(self):
        emb = ChineseEmbedder()
        vec = emb.embed("正官七杀正印偏印")
        assert vec.shape == (256,)

    # ── 静态方法 ────────────────────────────────────────────────────

    def test_hash_char(self):
        h1 = ChineseEmbedder._hash_char("木")
        h2 = ChineseEmbedder._hash_char("木")
        assert h1 == h2
        assert isinstance(h1, int)

    def test_hash_char_different(self):
        h1 = ChineseEmbedder._hash_char("木")
        h2 = ChineseEmbedder._hash_char("火")
        assert h1 != h2

    def test_hash_string(self):
        h = ChineseEmbedder._hash_string("乾坤")
        assert isinstance(h, int)
        assert h >= 0

    def test_hash_string_deterministic(self):
        h1 = ChineseEmbedder._hash_string("八卦")
        h2 = ChineseEmbedder._hash_string("八卦")
        assert h1 == h2

    def test_l2_normalize_unit_vector(self):
        vec = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        result = ChineseEmbedder._l2_normalize(vec)
        assert np.allclose(result, vec)

    def test_l2_normalize_arbitrary_vector(self):
        vec = np.array([3.0, 4.0], dtype=np.float32)
        result = ChineseEmbedder._l2_normalize(vec)
        assert np.isclose(np.linalg.norm(result), 1.0)
        assert np.isclose(result[0], 0.6)
        assert np.isclose(result[1], 0.8)

    def test_l2_normalize_zero_vector(self):
        vec = np.zeros(5, dtype=np.float32)
        result = ChineseEmbedder._l2_normalize(vec)
        assert np.allclose(result, 0.0)

    def test_class_constants(self):
        assert ChineseEmbedder.VECTOR_DIM == 256
        assert ChineseEmbedder.NGRAM_DIM == 128
        assert ChineseEmbedder.SEMANTIC_DIM == 64
        assert ChineseEmbedder.STRUCT_DIM == 64


# ============================================================================
# SemanticSearchResult 测试
# ============================================================================

class TestSemanticSearchResult:
    """测试语义搜索结果数据类"""

    def test_creation(self):
        result = SemanticSearchResult(
            query="测试查询",
            results=[{"type": "五行", "name": "木", "name_cn": "青", "similarity": 0.95}],
            total_indexed=100,
            search_time_ms=1.5,
        )
        assert result.query == "测试查询"
        assert result.total_indexed == 100
        assert result.search_time_ms == 1.5
        assert len(result.results) == 1

    def test_text_summary(self):
        result = SemanticSearchResult(
            query="木",
            results=[
                {"type": "五行", "name": "木", "name_cn": "青", "similarity": 0.98},
                {"type": "天干", "name": "甲", "name_cn": "阳木", "similarity": 0.85},
            ],
            total_indexed=50,
            search_time_ms=2.3,
        )
        lines = result.text_summary()
        assert len(lines) >= 1
        assert "木" in lines[0]
        assert "50" in lines[0]
        assert "五行" in lines[1]
        assert "甲" in lines[2]

    def test_text_summary_empty_results(self):
        result = SemanticSearchResult(
            query="不存在",
            results=[],
            total_indexed=50,
            search_time_ms=0.5,
        )
        lines = result.text_summary()
        assert len(lines) == 1
        assert "不存在" in lines[0]
        assert "0 个结果" in lines[0]

    def test_text_summary_truncates_at_10(self):
        results = [
            {"type": "五行", "name": f"节点{i}", "name_cn": f"别名{i}", "similarity": 0.9 - i * 0.05}
            for i in range(15)
        ]
        result = SemanticSearchResult(
            query="测试",
            results=results,
            total_indexed=100,
            search_time_ms=1.0,
        )
        lines = result.text_summary()
        assert len(lines) <= 11

    def test_text_summary_with_zero_similarity(self):
        result = SemanticSearchResult(
            query="测试",
            results=[{"type": "五行", "name": "火", "name_cn": "赤", "similarity": 0.0}],
            total_indexed=10,
            search_time_ms=0.1,
        )
        lines = result.text_summary()
        assert "0.000" in lines[1]


# ============================================================================
# VectorStore 测试（使用 mock_faiss fixture）
# ============================================================================

class TestVectorStoreInit:
    """测试 VectorStore 初始化"""

    def test_init_default(self):
        store = VectorStore()
        assert store.dim == 256
        assert store.is_initialized is False
        assert isinstance(store.embedder, ChineseEmbedder)

    def test_init_custom_dim(self):
        store = VectorStore(dim=128)
        assert store.dim == 128

    def test_stats_property(self):
        store = VectorStore()
        s = store.stats
        assert s["total_nodes"] == 0
        assert s["total_vectors"] == 0
        assert s["search_count"] == 0
        assert s["avg_search_ms"] == 0.0

    def test_is_initialized(self):
        store = VectorStore()
        assert store.is_initialized is False


class TestVectorStoreBuildIndex:
    """测试索引构建"""

    def test_build_from_knowledge_graph(self, mock_faiss):
        mock_kg = _make_mock_kg()
        store = VectorStore()
        count = store.build_from_knowledge_graph(kg=mock_kg)
        assert count > 0
        assert store.is_initialized is True
        assert store._stats["total_nodes"] == count
        assert store._stats["total_vectors"] == count

    def test_build_from_knowledge_graph_none(self, mock_faiss):
        mock_kg = _make_mock_kg()
        with patch("tengod.knowledge_graph.get_knowledge_graph", return_value=mock_kg):
            store = VectorStore()
            count = store.build_from_knowledge_graph(kg=None)
        assert count > 0
        assert store.is_initialized is True

    def test_extract_nodes(self):
        mock_kg = _make_mock_kg()
        store = VectorStore()
        nodes = store._extract_nodes(mock_kg)
        assert len(nodes) > 0
        for node in nodes:
            assert "id" in node
            assert "type" in node
            assert "name" in node
            assert "name_cn" in node
            assert "text" in node

    def test_format_element(self):
        info = {"color": "青", "direction": "东", "season": "春", "description": "木曰曲直"}
        text = VectorStore._format_element("木", info)
        assert "五行" in text
        assert "木" in text
        assert "color:青" in text

    def test_build_index_initializes_nodes(self, mock_faiss):
        store = VectorStore()
        vectors = np.random.randn(5, 256).astype(np.float32)
        nodes = [{"id": f"node:{i}", "type": "测试", "name": f"节点{i}", "name_cn": "", "text": f"文本{i}"} for i in range(5)]
        store._build_index(vectors, nodes)
        assert store.is_initialized is True
        assert store._stats["total_nodes"] == 5
        assert store._stats["total_vectors"] == 5
        assert len(store._nodes) == 5


class TestVectorStoreSearch:
    """测试语义搜索"""

    def test_search_basic(self, mock_faiss):
        mock_kg = _make_mock_kg()
        store = VectorStore()
        store.build_from_knowledge_graph(kg=mock_kg)
        mock_index = _make_mock_faiss_index()
        store._index = mock_index

        result = store.search("木", top_k=5)
        assert isinstance(result, SemanticSearchResult)
        assert result.query == "木"
        assert len(result.results) > 0
        for r in result.results:
            assert "similarity" in r
            assert "type" in r
            assert "name" in r

    def test_search_with_type_filter(self, mock_faiss):
        mock_kg = _make_mock_kg()
        store = VectorStore()
        store.build_from_knowledge_graph(kg=mock_kg)
        mock_index = _make_mock_faiss_index()
        store._index = mock_index

        result = store.search("木", top_k=5, type_filter="五行")
        assert isinstance(result, SemanticSearchResult)
        for r in result.results:
            assert r["type"] == "五行"

    def test_search_top_k_limit(self, mock_faiss):
        mock_kg = _make_mock_kg()
        store = VectorStore()
        store.build_from_knowledge_graph(kg=mock_kg)
        mock_index = _make_mock_faiss_index()
        store._index = mock_index

        result = store.search("测试", top_k=3)
        assert len(result.results) <= 3

    def test_search_with_negative_indices(self, mock_faiss):
        mock_kg = _make_mock_kg()
        store = VectorStore()
        store.build_from_knowledge_graph(kg=mock_kg)
        mock_index = MagicMock()
        mock_index.search.return_value = (
            np.array([[0.9, 0.8, 0.7]], dtype=np.float32),
            np.array([[-1, 0, 1]], dtype=np.int64),
        )
        store._index = mock_index

        result = store.search("测试", top_k=5)
        assert len(result.results) == 2

    def test_search_out_of_bounds_indices(self, mock_faiss):
        mock_kg = _make_mock_kg()
        store = VectorStore()
        store.build_from_knowledge_graph(kg=mock_kg)
        mock_index = MagicMock()
        mock_index.search.return_value = (
            np.array([[0.9, 0.8, 0.7]], dtype=np.float32),
            np.array([[0, 999, 1]], dtype=np.int64),
        )
        store._index = mock_index

        result = store.search("测试", top_k=5)
        assert len(result.results) == 2

    def test_search_updates_stats(self, mock_faiss):
        mock_kg = _make_mock_kg()
        store = VectorStore()
        store.build_from_knowledge_graph(kg=mock_kg)
        mock_index = _make_mock_faiss_index()
        store._index = mock_index

        store.search("测试", top_k=5)
        assert store._stats["search_count"] == 1
        assert store._stats["avg_search_ms"] > 0

    def test_search_json(self, mock_faiss):
        mock_kg = _make_mock_kg()
        store = VectorStore()
        store.build_from_knowledge_graph(kg=mock_kg)
        mock_index = _make_mock_faiss_index()
        store._index = mock_index

        result = store.search_json("木", top_k=3)
        assert isinstance(result, dict)
        assert result["query"] == "木"
        assert "result_count" in result
        assert "results" in result
        assert "search_time_ms" in result
        for r in result["results"]:
            assert "rank" in r
            assert "similarity" in r

    def test_search_json_with_type_filter(self, mock_faiss):
        mock_kg = _make_mock_kg()
        store = VectorStore()
        store.build_from_knowledge_graph(kg=mock_kg)
        mock_index = _make_mock_faiss_index()
        store._index = mock_index

        result = store.search_json("天干", top_k=5, type_filter="天干")
        assert isinstance(result, dict)


class TestVectorStoreRecommend:
    """测试知识关联推荐"""

    def test_recommend_related_exact_match(self, mock_faiss):
        mock_kg = _make_mock_kg()
        store = VectorStore()
        store.build_from_knowledge_graph(kg=mock_kg)
        mock_index = _make_mock_faiss_index()
        store._index = mock_index

        recs = store.recommend_related("木", top_k=5)
        assert isinstance(recs, list)
        for r in recs:
            assert "type" in r
            assert "name" in r
            assert "similarity" in r
            assert "relation" in r

    def test_recommend_related_exclude_self(self, mock_faiss):
        mock_kg = _make_mock_kg()
        store = VectorStore()
        store.build_from_knowledge_graph(kg=mock_kg)
        mock_index = _make_mock_faiss_index()
        store._index = mock_index

        recs = store.recommend_related("木", top_k=5, exclude_self=True)
        names = [r["name"] for r in recs]
        assert "木" not in names

    def test_recommend_related_include_self(self, mock_faiss):
        mock_kg = _make_mock_kg()
        store = VectorStore()
        store.build_from_knowledge_graph(kg=mock_kg)
        mock_index = _make_mock_faiss_index()
        store._index = mock_index

        recs = store.recommend_related("木", top_k=5, exclude_self=False)
        names = [r["name"] for r in recs]
        assert "木" in names

    def test_recommend_related_not_found(self, mock_faiss):
        mock_kg = _make_mock_kg()
        store = VectorStore()
        store.build_from_knowledge_graph(kg=mock_kg)

        recs = store.recommend_related("不存在的节点", top_k=5)
        assert recs == []

    def test_recommend_related_fuzzy_match(self, mock_faiss):
        mock_kg = _make_mock_kg()
        store = VectorStore()
        store.build_from_knowledge_graph(kg=mock_kg)
        mock_index = _make_mock_faiss_index()
        store._index = mock_index

        recs = store.recommend_related("青", top_k=5)
        assert isinstance(recs, list)

    def test_recommend_related_top_k(self, mock_faiss):
        mock_kg = _make_mock_kg()
        store = VectorStore()
        store.build_from_knowledge_graph(kg=mock_kg)
        mock_index = _make_mock_faiss_index()
        store._index = mock_index

        recs = store.recommend_related("木", top_k=3)
        assert len(recs) <= 3


class TestVectorStoreInferRelation:
    """测试关系推断"""

    def test_infer_relation_wuxing_sheng(self, mock_faiss):
        mock_kg = _make_mock_kg()
        store = VectorStore()
        store.build_from_knowledge_graph(kg=mock_kg)
        rel = store._infer_relation("木", "火")
        assert "生" in rel

    def test_infer_relation_wuxing_ke(self, mock_faiss):
        mock_kg = _make_mock_kg()
        store = VectorStore()
        store.build_from_knowledge_graph(kg=mock_kg)
        rel = store._infer_relation("木", "土")
        assert "克" in rel

    def test_infer_relation_wuxing_same(self, mock_faiss):
        mock_kg = _make_mock_kg()
        store = VectorStore()
        store.build_from_knowledge_graph(kg=mock_kg)
        rel = store._infer_relation("木", "木")
        assert rel == "同类"

    def test_infer_relation_non_wuxing(self):
        store = VectorStore()
        rel = store._infer_relation("乾", "坤")
        assert rel == "语义关联"


class TestVectorStoreIO:
    """测试索引持久化"""

    def test_save(self, mock_faiss):
        mock_kg = _make_mock_kg()
        store = VectorStore()
        store.build_from_knowledge_graph(kg=mock_kg)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test_model")
            store.save(path)

            assert os.path.exists(path + ".index")
            assert os.path.exists(path + ".meta.json")
            assert os.path.exists(path + ".stats.json")

            with open(path + ".meta.json", "r", encoding="utf-8") as f:
                meta = json.load(f)
            assert len(meta) > 0

            with open(path + ".stats.json", "r", encoding="utf-8") as f:
                stats = json.load(f)
            assert "total_nodes" in stats

    def test_load(self, mock_faiss):
        mock_kg = _make_mock_kg()
        store = VectorStore()
        store.build_from_knowledge_graph(kg=mock_kg)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test_model")
            store.save(path)

            store2 = VectorStore()
            store2.load(path)

            assert store2.is_initialized is True
            assert len(store2._nodes) == len(store._nodes)
            assert store2._stats["total_nodes"] == store._stats["total_nodes"]

    def test_load_without_stats(self, mock_faiss):
        mock_kg = _make_mock_kg()
        store = VectorStore()
        store.build_from_knowledge_graph(kg=mock_kg)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test_model")
            mock_faiss.write_index(store._index, path + ".index")
            with open(path + ".meta.json", "w", encoding="utf-8") as f:
                json.dump(store._nodes, f, ensure_ascii=False)

            store2 = VectorStore()
            store2.load(path)
            assert store2.is_initialized is True
            assert len(store2._nodes) == len(store._nodes)

    def test_save_creates_directories(self, mock_faiss):
        mock_kg = _make_mock_kg()
        store = VectorStore()
        store.build_from_knowledge_graph(kg=mock_kg)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "subdir", "nested", "model")
            store.save(path)
            assert os.path.exists(path + ".index")
            assert os.path.exists(path + ".meta.json")

    def test_save_lazy_init(self, mock_faiss):
        mock_kg = _make_mock_kg()
        with patch("tengod.knowledge_graph.get_knowledge_graph", return_value=mock_kg):
            store = VectorStore()
            assert store.is_initialized is False
            with tempfile.TemporaryDirectory() as tmpdir:
                path = os.path.join(tmpdir, "test_model")
                store.save(path)
                assert os.path.exists(path + ".index")


class TestVectorStoreLazyInit:
    """测试懒初始化"""

    def test_lazy_init_on_search(self, mock_faiss):
        mock_kg = _make_mock_kg()
        with patch("tengod.knowledge_graph.get_knowledge_graph", return_value=mock_kg):
            store = VectorStore()
            assert store.is_initialized is False
            result = store.search("测试", top_k=3)
            assert store.is_initialized is True
            assert isinstance(result, SemanticSearchResult)

    def test_node_types(self, mock_faiss):
        mock_kg = _make_mock_kg()
        store = VectorStore()
        store.build_from_knowledge_graph(kg=mock_kg)

        types = store.node_types()
        assert isinstance(types, dict)
        assert len(types) > 0
        for count in types.values():
            assert count > 0

    def test_node_types_lazy_init(self, mock_faiss):
        mock_kg = _make_mock_kg()
        with patch("tengod.knowledge_graph.get_knowledge_graph", return_value=mock_kg):
            store = VectorStore()
            assert store.is_initialized is False
            types = store.node_types()
            assert store.is_initialized is True
            assert len(types) > 0


# ============================================================================
# 模块级函数测试
# ============================================================================

class TestModuleFunctions:
    """测试模块级便捷函数"""

    def test_build_knowledge_vectors(self, mock_faiss):
        mock_kg = _make_mock_kg()
        with patch("tengod.knowledge_graph.get_knowledge_graph", return_value=mock_kg):
            store = build_knowledge_vectors()
            assert isinstance(store, VectorStore)
            assert store.is_initialized is True

    def test_get_vector_store_singleton(self, mock_faiss):
        import tengod.vector_store as vs_module
        vs_module._vector_store = None

        mock_kg = _make_mock_kg()
        with patch("tengod.knowledge_graph.get_knowledge_graph", return_value=mock_kg):
            store1 = get_vector_store()
            store2 = get_vector_store()
            assert store1 is store2

    def test_search_similar(self, mock_faiss):
        mock_kg = _make_mock_kg()
        import tengod.vector_store as vs_module
        vs_module._vector_store = None

        with patch("tengod.knowledge_graph.get_knowledge_graph", return_value=mock_kg):
            result = search_similar("木", top_k=3)
            assert isinstance(result, dict)
            assert result["query"] == "木"

    def test_recommend_related_func(self, mock_faiss):
        mock_kg = _make_mock_kg()
        import tengod.vector_store as vs_module
        vs_module._vector_store = None

        with patch("tengod.knowledge_graph.get_knowledge_graph", return_value=mock_kg):
            result = recommend_related("木", top_k=3)
            assert isinstance(result, list)


# ============================================================================
# 边缘情况测试
# ============================================================================

class TestEdgeCases:
    """边缘情况测试"""

    def test_vector_store_empty_nodes(self, mock_faiss):
        store = VectorStore()
        vectors = np.empty((0, 256), dtype=np.float32)
        nodes = []
        store._build_index(vectors, nodes)
        assert store.is_initialized is True
        assert store._stats["total_nodes"] == 0

    def test_search_with_empty_index(self, mock_faiss):
        store = VectorStore()
        vectors = np.empty((0, 256), dtype=np.float32)
        store._build_index(vectors, [])

        mock_index = MagicMock()
        mock_index.search.return_value = (
            np.array([[]], dtype=np.float32),
            np.array([[]], dtype=np.int64),
        )
        store._index = mock_index

        result = store.search("测试", top_k=5)
        assert len(result.results) == 0

    def test_search_dimension_mismatch(self, mock_faiss):
        store = VectorStore(dim=128)
        vectors = np.random.randn(3, 128).astype(np.float32)
        nodes = [{"id": f"n:{i}", "type": "测试", "name": f"节点{i}", "name_cn": "", "text": f"文本{i}"} for i in range(3)]
        store._build_index(vectors, nodes)
        assert store.is_initialized is True

    def test_embedder_cache_consistency(self):
        emb = ChineseEmbedder()
        text = "甲乙丙丁戊己庚辛壬癸"
        v1 = emb.embed(text)
        v2 = emb.embed(text)
        v3 = emb.embed(text)
        assert v1 is v2 is v3

    def test_embed_batch_consistency(self):
        emb = ChineseEmbedder()
        texts = ["甲乙", "丙丁", "戊己"]
        batch = emb.embed_batch(texts)
        singles = np.array([emb.embed(t) for t in texts])
        assert np.allclose(batch, singles)

    def test_embed_pure_ascii(self):
        emb = ChineseEmbedder()
        vec = emb.embed("hello world 12345")
        assert vec.shape == (256,)

    def test_embed_mixed_text(self):
        emb = ChineseEmbedder()
        vec = emb.embed("五行 wuxing 123")
        assert vec.shape == (256,)

    def test_search_type_filter_no_match(self, mock_faiss):
        mock_kg = _make_mock_kg()
        store = VectorStore()
        store.build_from_knowledge_graph(kg=mock_kg)
        mock_index = _make_mock_faiss_index()
        store._index = mock_index

        result = store.search("木", top_k=5, type_filter="不存在的类型")
        assert len(result.results) == 0

    def test_recommend_related_empty_nodes(self, mock_faiss):
        store = VectorStore()
        vectors = np.empty((0, 256), dtype=np.float32)
        store._build_index(vectors, [])
        recs = store.recommend_related("木", top_k=5)
        assert recs == []

    def test_search_json_result_structure(self, mock_faiss):
        mock_kg = _make_mock_kg()
        store = VectorStore()
        store.build_from_knowledge_graph(kg=mock_kg)
        mock_index = _make_mock_faiss_index()
        store._index = mock_index

        result = store.search_json("测试", top_k=3)
        assert "query" in result
        assert "total_indexed" in result
        assert "search_time_ms" in result
        assert "result_count" in result
        assert "results" in result
        assert isinstance(result["results"], list)

    def test_embed_very_short_text(self):
        emb = ChineseEmbedder()
        vec = emb.embed("木")
        assert vec.shape == (256,)
        norm = np.linalg.norm(vec)
        assert np.isclose(norm, 1.0, atol=1e-6)

    def test_embed_special_chars(self):
        emb = ChineseEmbedder()
        vec = emb.embed("！@#￥%……&*（）")
        assert vec.shape == (256,)

    def test_result_creation_defaults(self):
        result = SemanticSearchResult(
            query="测试",
            results=[],
            total_indexed=0,
            search_time_ms=0.0,
        )
        assert result.query == "测试"
        assert result.results == []
        assert result.total_indexed == 0
        assert result.search_time_ms == 0.0


# ============================================================================
# 模块级常量测试
# ============================================================================

class TestModuleConstants:
    """测试模块级常量"""

    def test_wuxing_onehot_keys(self):
        assert set(_WUXING_ONEHOT.keys()) == {"木", "火", "土", "金", "水"}

    def test_wuxing_onehot_shape(self):
        for vec in _WUXING_ONEHOT.values():
            assert vec.shape == (5,)
            assert vec.dtype == np.float32

    def test_yinyang_onehot_keys(self):
        assert set(_YINYANG_ONEHOT.keys()) == {"阳", "阴"}

    def test_direction_onehot_keys(self):
        expected = {"东", "南", "西", "北", "中", "东南", "西南", "西北", "东北"}
        assert set(_DIRECTION_ONEHOT.keys()) == expected

    def test_season_onehot_keys(self):
        assert set(_SEASON_ONEHOT.keys()) == {"春", "夏", "长夏", "秋", "冬"}

    def test_tiangan_index_keys(self):
        assert len(_TIANGAN_INDEX) == 10
        assert "甲" in _TIANGAN_INDEX
        assert "癸" in _TIANGAN_INDEX

    def test_dizhi_index_keys(self):
        assert len(_DIZHI_INDEX) == 12
        assert "子" in _DIZHI_INDEX
        assert "亥" in _DIZHI_INDEX

    def test_bagua_symbols_keys(self):
        assert len(_BAGUA_SYMBOLS) == 8
        assert _BAGUA_SYMBOLS["乾"] == "☰"
        assert _BAGUA_SYMBOLS["坤"] == "☷"

    def test_shigan_categories_keys(self):
        assert len(_SHIGAN_CATEGORIES) == 10
        assert "正官" in _SHIGAN_CATEGORIES
        assert "伤官" in _SHIGAN_CATEGORIES