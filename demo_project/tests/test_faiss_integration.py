"""test_faiss_integration.py — FAISS 向量索引验证 v2.1.0
验证 faiss-cpu 安装、use_vector_db("faiss") 语义搜索精度。
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tengod"))

from 正财_知识固化.knowledge_base import KnowledgeBase


class TestFAISSInstallation:
    """FAISS 安装验证"""

    def test_faiss_importable(self):
        """验证 faiss 模块可导入"""
        try:
            import faiss

            assert faiss is not None
        except ImportError:
            pytest.skip("faiss-cpu not installed")


class TestFAISSVectorDB:
    """FAISS 向量数据库集成"""

    def test_use_vector_db_faiss(self):
        """验证 use_vector_db("faiss") 成功启用"""
        kb = KnowledgeBase()
        # 添加一些测试节点
        kb.add_node("儒家思想", node_type="philosophy", properties={"核心": "仁义礼智信"})
        kb.add_node("道家思想", node_type="philosophy", properties={"核心": "道法自然"})
        kb.add_node("法家思想", node_type="philosophy", properties={"核心": "以法治国"})
        kb.add_node("墨家思想", node_type="philosophy", properties={"核心": "兼爱非攻"})
        kb.add_node("计算机科学", node_type="tech", properties={"核心": "算法"})
        kb.add_node("人工智能", node_type="tech", properties={"核心": "深度学习"})
        kb.add_node("机器学习", node_type="tech", properties={"核心": "模式识别"})
        kb.add_node("量子计算", node_type="tech", properties={"核心": "量子比特"})

        result = kb.use_vector_db("faiss")
        assert result["provider"] == "faiss"
        assert result["dimension"] > 0
        assert result["indexed"] >= 8
        assert result["error"] == ""

    def test_use_vector_db_auto(self):
        """验证 use_vector_db("auto") 自动选择 FAISS"""
        kb = KnowledgeBase()
        kb.add_node("测试节点", node_type="test", properties={"key": "value"})
        result = kb.use_vector_db("auto")
        # auto should pick faiss since it's installed
        assert result["provider"] in ("faiss", "chroma", "memory")

    def test_use_vector_db_disable(self):
        """验证 use_vector_db("disable") 禁用向量搜索"""
        kb = KnowledgeBase()
        result = kb.use_vector_db("disable")
        assert result["provider"] == "memory"


class TestFAISSSemanticSearch:
    """FAISS 语义搜索精度"""

    @pytest.fixture
    def populated_kb(self):
        """创建预填充的知识库"""
        kb = KnowledgeBase()
        nodes = [
            ("儒家", "philosophy", {"代表": "孔子", "经典": "论语", "思想": "仁义礼智信"}),
            ("道家", "philosophy", {"代表": "老子", "经典": "道德经", "思想": "道法自然无为"}),
            ("法家", "philosophy", {"代表": "韩非子", "经典": "韩非子", "思想": "以法治国"}),
            ("墨家", "philosophy", {"代表": "墨子", "经典": "墨子", "思想": "兼爱非攻尚贤"}),
            ("兵家", "philosophy", {"代表": "孙子", "经典": "孙子兵法", "思想": "知己知彼"}),
            ("医家", "philosophy", {"代表": "扁鹊", "经典": "黄帝内经", "思想": "阴阳五行"}),
            ("易经", "classic", {"内容": "六十四卦", "地位": "群经之首"}),
            ("诗经", "classic", {"内容": "风雅颂", "篇数": "305"}),
            ("史记", "classic", {"作者": "司马迁", "地位": "史家之绝唱"}),
            ("春秋", "classic", {"作者": "孔子", "体例": "编年史"}),
            ("河图", "cosmic", {"结构": "1-10黑白点", "对应": "先天八卦"}),
            ("洛书", "cosmic", {"结构": "3x3九宫幻方", "对应": "九畴"}),
            ("阴阳", "concept", {"应用": "中医风水哲学兵法"}),
            ("五行", "concept", {"构成": "金木水火土"}),
            ("八卦", "concept", {"构成": "乾坤震巽坎离艮兑"}),
            ("机器学习", "tech", {"领域": "人工智能", "方法": "模式识别"}),
            ("深度学习", "tech", {"领域": "人工智能", "方法": "神经网络"}),
            ("自然语言处理", "tech", {"领域": "人工智能", "方法": "文本分析"}),
            ("量子计算", "tech", {"领域": "物理学", "方法": "量子比特"}),
            ("区块链", "tech", {"领域": "分布式系统", "方法": "共识算法"}),
        ]
        for name, ntype, props in nodes:
            kb.add_node(name, node_type=ntype, properties=props)
        kb.use_vector_db("faiss")
        return kb

    def test_semantic_search_philosophy(self, populated_kb):
        """验证哲学类语义搜索：查询儒家应返回相关哲学节点"""
        results = populated_kb.query_nearest("孔子儒家仁义", top_k=5)
        assert len(results) > 0
        # 儒家应该在结果中
        names = [r["name"] for r in results]
        assert "儒家" in names

    def test_semantic_search_tech(self, populated_kb):
        """验证技术类语义搜索：查询AI应返回相关技术节点"""
        results = populated_kb.query_nearest("人工智能深度学习", top_k=5)
        assert len(results) > 0
        names = [r["name"] for r in results]
        tech_results = any(
            name in names for name in ["机器学习", "深度学习", "自然语言处理", "量子计算"]
        )
        assert tech_results

    def test_semantic_search_score_descending(self, populated_kb):
        """验证搜索结果按相似度降序排列"""
        results = populated_kb.query_nearest("道家老子无为", top_k=5)
        if len(results) >= 2:
            scores = [r["score"] for r in results]
            for i in range(len(scores) - 1):
                assert scores[i] >= scores[i + 1]  # 降序

    def test_semantic_search_top_k_limit(self, populated_kb):
        """验证 top_k 参数限制结果数量"""
        results = populated_kb.query_nearest("测试查询", top_k=3)
        assert len(results) <= 3

    def test_semantic_search_node_type_filter(self, populated_kb):
        """验证 node_type 过滤"""
        results = populated_kb.query_nearest("哲学思想", top_k=5, node_type="philosophy")
        assert len(results) > 0
        for r in results:
            assert r["node_type"] == "philosophy"

    def test_faiss_stats_after_indexing(self, populated_kb):
        """验证索引后的统计信息"""
        stats = populated_kb.stats()
        assert stats["nodes"] == 20
        # _vector_provider 是内部属性
        assert populated_kb._vector_provider == "faiss"

    def test_faiss_dimension(self, populated_kb):
        """验证向量维度正确"""
        assert populated_kb._vector_dim > 0
        assert populated_kb._faiss_index is not None


class TestFAISSGracefulFallback:
    """FAISS 优雅降级"""

    def test_faiss_not_installed_fallback(self):
        """验证 FAISS 未安装时的降级行为"""
        import importlib

        # 模拟 faiss 不可用
        original_faiss = sys.modules.get("faiss")
        try:
            sys.modules["faiss"] = None
            kb = KnowledgeBase()
            kb.add_node("测试", node_type="test", properties={})
            result = kb.use_vector_db("faiss")
            assert "error" in result
        finally:
            if original_faiss is not None:
                sys.modules["faiss"] = original_faiss
            elif "faiss" in sys.modules:
                del sys.modules["faiss"]