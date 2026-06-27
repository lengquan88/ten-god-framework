"""test_knowledge_base.py — 知识库模块完整测试

覆盖：StorageBackend, KnowledgeNode, KnowledgeEdge, KnowledgeBase (Memory 后端为主)
"""

from __future__ import annotations

import json
import time
from unittest.mock import MagicMock, mock_open, patch

import pytest

from tengod.正财_知识固化.knowledge_base import (
    KnowledgeBase,
    KnowledgeEdge,
    KnowledgeNode,
    StorageBackend,
)


# ============================================================
# StorageBackend
# ============================================================
class TestStorageBackend:
    """StorageBackend 枚举测试"""

    def test_all_values(self):
        """所有枚举值"""
        assert StorageBackend.MEMORY.value == "memory"
        assert StorageBackend.SQLITE.value == "sqlite"
        assert StorageBackend.POSTGRES.value == "postgres"
        assert StorageBackend.JSON.value == "json"

    def test_members(self):
        """四个成员"""
        members = list(StorageBackend)
        assert len(members) == 4
        values = {m.value for m in members}
        assert values == {"memory", "sqlite", "postgres", "json"}


# ============================================================
# KnowledgeNode
# ============================================================
class TestKnowledgeNode:
    """KnowledgeNode dataclass 测试"""

    def test_create_with_required_fields(self):
        """仅必填字段创建"""
        node = KnowledgeNode(id="n1", name="测试", node_type="concept")
        assert node.id == "n1"
        assert node.name == "测试"
        assert node.node_type == "concept"
        assert node.properties == {}
        assert isinstance(node.created_at, float)

    def test_create_with_all_fields(self):
        """全部字段创建"""
        node = KnowledgeNode(
            id="n2",
            name="深度神经网络",
            node_type="tech",
            properties={"层数": 128, "激活函数": "ReLU"},
            created_at=1000000.0,
        )
        assert node.id == "n2"
        assert node.name == "深度神经网络"
        assert node.node_type == "tech"
        assert node.properties == {"层数": 128, "激活函数": "ReLU"}
        assert node.created_at == 1000000.0

    def test_default_created_at_is_float(self):
        """默认 created_at 是 float"""
        node = KnowledgeNode(id="n3", name="测试", node_type="default")
        assert isinstance(node.created_at, float)
        # 应该是近期时间戳
        assert abs(node.created_at - time.time()) < 5.0

    def test_default_properties_is_empty_dict(self):
        """默认 properties 是空字典"""
        node = KnowledgeNode(id="n4", name="测试", node_type="default")
        assert isinstance(node.properties, dict)
        assert node.properties == {}

    def test_properties_not_shared(self):
        """properties 默认值不会跨实例共享"""
        n1 = KnowledgeNode(id="a", name="A", node_type="t")
        n2 = KnowledgeNode(id="b", name="B", node_type="t")
        n1.properties["key"] = "val"
        assert n2.properties == {}


# ============================================================
# KnowledgeEdge
# ============================================================
class TestKnowledgeEdge:
    """KnowledgeEdge dataclass 测试"""

    def test_create_with_all_fields(self):
        """全部字段创建"""
        edge = KnowledgeEdge(
            source="src_id", target="tgt_id", relation="depends_on", weight=0.75
        )
        assert edge.source == "src_id"
        assert edge.target == "tgt_id"
        assert edge.relation == "depends_on"
        assert edge.weight == 0.75

    def test_default_weight(self):
        """默认 weight 是 1.0"""
        edge = KnowledgeEdge(source="s", target="t", relation="related")
        assert edge.weight == 1.0


# ============================================================
# KnowledgeBase __init__
# ============================================================
class TestKnowledgeBaseInit:
    """KnowledgeBase 初始化测试"""

    def test_default_backend_is_memory(self):
        """默认后端是 MEMORY"""
        kb = KnowledgeBase()
        assert kb._backend == StorageBackend.MEMORY
        assert kb._nodes == {}
        assert kb._edges == []

    def test_init_with_sqlite_mock(self):
        """SQLite 后端初始化（mock sqlite3）"""
        mock_conn = MagicMock()
        mock_sqlite3 = MagicMock()
        mock_sqlite3.connect.return_value = mock_conn

        with patch.dict("sys.modules", {"sqlite3": mock_sqlite3}):
            import sqlite3 as orig
            import sys
            try:
                sys.modules["sqlite3"] = mock_sqlite3
                kb = KnowledgeBase(backend=StorageBackend.SQLITE, db_path="test.db")
                mock_sqlite3.connect.assert_called_once_with(
                    "test.db", check_same_thread=False
                )
                assert kb._backend == StorageBackend.SQLITE
                kb.close()
            finally:
                sys.modules["sqlite3"] = orig

    def test_init_with_json_backend(self):
        """JSON 后端初始化"""
        json_path = "/tmp/test_kb_init.json"
        kb = KnowledgeBase(backend=StorageBackend.JSON, db_path=json_path)
        assert kb._backend == StorageBackend.JSON
        assert kb._nodes == {}
        assert kb._edges == []

    def test_init_with_postgres_mock(self):
        """PostgreSQL 后端初始化（mock psycopg2）"""
        mock_conn = MagicMock()
        mock_psycopg2 = MagicMock()
        mock_psycopg2.connect.return_value = mock_conn

        with patch.dict("sys.modules", {"psycopg2": mock_psycopg2}):
            import sys
            try:
                sys.modules["psycopg2"] = mock_psycopg2
                kb = KnowledgeBase(
                    backend=StorageBackend.POSTGRES,
                    connection_string="host=localhost",
                )
                mock_psycopg2.connect.assert_called_once_with("host=localhost")
                assert kb._backend == StorageBackend.POSTGRES
                kb.close()
            finally:
                sys.modules["psycopg2"] = None


# ============================================================
# add_node
# ============================================================
class TestAddNode:
    """add_node 测试"""

    @pytest.fixture
    def kb(self):
        return KnowledgeBase()

    def test_basic_add_with_name(self, kb):
        """基本添加（仅名称）"""
        node = kb.add_node("测试节点")
        assert node.name == "测试节点"
        assert node.node_type == "default"
        assert node.properties == {}
        assert isinstance(node.id, str)
        assert len(node.id) > 0
        assert kb._nodes[node.id] is node

    def test_add_with_node_type(self, kb):
        """带 node_type 添加"""
        node = kb.add_node("AI", node_type="concept")
        assert node.node_type == "concept"

    def test_add_with_properties(self, kb):
        """带 properties 添加"""
        node = kb.add_node("儒家", properties={"代表": "孔子", "年代": "春秋"})
        assert node.properties == {"代表": "孔子", "年代": "春秋"}

    def test_add_with_custom_node_id(self, kb):
        """带自定义 node_id 添加"""
        node = kb.add_node("自定义", node_id="my-custom-id")
        assert node.id == "my-custom-id"

    def test_returns_knowledge_node(self, kb):
        """返回 KnowledgeNode 实例"""
        node = kb.add_node("节点")
        assert isinstance(node, KnowledgeNode)


# ============================================================
# add_edge
# ============================================================
class TestAddEdge:
    """add_edge 测试"""

    @pytest.fixture
    def kb(self):
        kb = KnowledgeBase()
        kb.add_node("A", node_id="a")
        kb.add_node("B", node_id="b")
        return kb

    def test_add_edge_between_existing_nodes(self, kb):
        """存在节点之间添加边"""
        edge = kb.add_edge("a", "b", "related")
        assert edge is not None
        assert edge.source == "a"
        assert edge.target == "b"
        assert edge.relation == "related"

    def test_add_edge_nonexistent_source(self, kb):
        """不存在的 source → None"""
        edge = kb.add_edge("x", "b", "related")
        assert edge is None

    def test_add_edge_nonexistent_target(self, kb):
        """不存在的 target → None"""
        edge = kb.add_edge("a", "x", "related")
        assert edge is None

    def test_add_edge_with_weight(self, kb):
        """带 weight 添加边"""
        edge = kb.add_edge("a", "b", "depends_on", weight=0.5)
        assert edge is not None
        assert edge.weight == 0.5

    def test_add_edge_with_relation(self, kb):
        """带不同 relation 添加边"""
        edge = kb.add_edge("a", "b", "contradicts")
        assert edge.relation == "contradicts"


# ============================================================
# get_node
# ============================================================
class TestGetNode:
    """get_node 测试"""

    @pytest.fixture
    def kb(self):
        kb = KnowledgeBase()
        kb.add_node("存在的节点", node_id="exist")
        return kb

    def test_get_existing_node(self, kb):
        """获取存在的节点"""
        node = kb.get_node("exist")
        assert node is not None
        assert node.name == "存在的节点"

    def test_get_nonexistent_returns_none(self, kb):
        """获取不存在的节点 → None"""
        assert kb.get_node("nonexistent") is None


# ============================================================
# find_by_name
# ============================================================
class TestFindByName:
    """find_by_name 测试"""

    @pytest.fixture
    def kb(self):
        kb = KnowledgeBase()
        kb.add_node("孔子", node_type="person")
        kb.add_node("孔子", node_type="concept")
        kb.add_node("孟子", node_type="person")
        return kb

    def test_find_existing_by_name(self, kb):
        """按名称查找存在的节点"""
        results = kb.find_by_name("孔子")
        assert len(results) == 2
        assert all(n.name == "孔子" for n in results)

    def test_find_nonexistent_returns_empty(self, kb):
        """不存在的名称 → 空列表"""
        results = kb.find_by_name("不存在")
        assert results == []

    def test_multiple_nodes_with_same_name(self, kb):
        """同名节点全部返回"""
        results = kb.find_by_name("孔子")
        types = {n.node_type for n in results}
        assert types == {"person", "concept"}


# ============================================================
# find_by_type
# ============================================================
class TestFindByType:
    """find_by_type 测试"""

    @pytest.fixture
    def kb(self):
        kb = KnowledgeBase()
        kb.add_node("A", node_type="type1")
        kb.add_node("B", node_type="type1")
        kb.add_node("C", node_type="type2")
        return kb

    def test_find_by_type(self, kb):
        """按类型查找"""
        results = kb.find_by_type("type1")
        assert len(results) == 2
        assert all(n.node_type == "type1" for n in results)

    def test_filter_works_correctly(self, kb):
        """过滤正确"""
        results = kb.find_by_type("type2")
        assert len(results) == 1
        assert results[0].name == "C"

    def test_no_match_returns_empty(self, kb):
        """无匹配 → 空列表"""
        assert kb.find_by_type("no-such-type") == []


# ============================================================
# neighbors
# ============================================================
class TestNeighbors:
    """neighbors 测试"""

    @pytest.fixture
    def kb(self):
        kb = KnowledgeBase()
        kb.add_node("A", node_id="a")
        kb.add_node("B", node_id="b")
        kb.add_node("C", node_id="c")
        kb.add_node("D", node_id="d")  # isolated
        kb.add_edge("a", "b", "friend")
        kb.add_edge("a", "c", "enemy")
        return kb

    def test_get_neighbors_of_node_with_edges(self, kb):
        """有边节点的邻居"""
        neighbors = kb.neighbors("a")
        assert len(neighbors) == 2
        names = {n.name for n in neighbors}
        assert names == {"B", "C"}

    def test_neighbors_with_relation_filter(self, kb):
        """带 relation 过滤"""
        neighbors = kb.neighbors("a", relation="friend")
        assert len(neighbors) == 1
        assert neighbors[0].name == "B"

    def test_neighbors_for_nonexistent_node(self, kb):
        """不存在的节点 → []"""
        assert kb.neighbors("x") == []

    def test_neighbors_for_isolated_node(self, kb):
        """孤立节点 → []"""
        assert kb.neighbors("d") == []


# ============================================================
# delete_node
# ============================================================
class TestDeleteNode:
    """delete_node 测试"""

    @pytest.fixture
    def kb(self):
        kb = KnowledgeBase()
        kb.add_node("A", node_id="a")
        kb.add_node("B", node_id="b")
        kb.add_edge("a", "b", "related")
        return kb

    def test_delete_existing_node(self, kb):
        """删除存在的节点"""
        assert kb.delete_node("a") is True
        assert kb.get_node("a") is None

    def test_delete_nonexistent_returns_false(self, kb):
        """删除不存在的节点 → False"""
        assert kb.delete_node("x") is False

    def test_delete_node_removes_associated_edges(self, kb):
        """删除节点同时移除关联的边"""
        assert len(kb._edges) == 1
        kb.delete_node("a")
        assert len(kb._edges) == 0


# ============================================================
# stats
# ============================================================
class TestStats:
    """stats 测试"""

    def test_empty_stats(self):
        """空知识库统计"""
        kb = KnowledgeBase()
        s = kb.stats()
        assert s == {
            "nodes": 0,
            "edges": 0,
            "node_types": 0,
            "backend": "memory",
        }

    def test_stats_with_nodes_and_edges(self):
        """有节点和边的统计"""
        kb = KnowledgeBase()
        kb.add_node("A", node_type="t1")
        kb.add_node("B", node_type="t1")
        kb.add_node("C", node_type="t2")
        nodes = kb.find_by_name("A")
        nodes2 = kb.find_by_name("B")
        kb.add_edge(nodes[0].id, nodes2[0].id, "related")
        s = kb.stats()
        assert s["nodes"] == 3
        assert s["edges"] == 1
        assert s["node_types"] == 2
        assert s["backend"] == "memory"

    def test_verify_structure(self):
        """验证 stats 结构"""
        kb = KnowledgeBase()
        s = kb.stats()
        assert set(s.keys()) == {"nodes", "edges", "node_types", "backend"}


# ============================================================
# export
# ============================================================
class TestExport:
    """export 测试"""

    def test_empty_export(self):
        """空导出"""
        kb = KnowledgeBase()
        data = kb.export()
        assert data == {"nodes": [], "edges": []}

    def test_export_with_nodes_and_edges(self):
        """有节点和边的导出"""
        kb = KnowledgeBase()
        kb.add_node("A", node_type="t1", properties={"k": "v"})
        nodes = kb.find_by_name("A")
        nid = nodes[0].id
        kb.add_node("B", node_type="t2", node_id="b")
        kb.add_edge(nid, "b", "related", weight=0.5)
        data = kb.export()
        assert len(data["nodes"]) == 2
        assert len(data["edges"]) == 1
        assert data["edges"][0]["weight"] == 0.5

    def test_verify_export_structure(self):
        """验证导出结构"""
        kb = KnowledgeBase()
        kb.add_node("测试", node_type="test", properties={"x": 1})
        data = kb.export()
        node = data["nodes"][0]
        assert set(node.keys()) == {"id", "name", "type", "properties", "created_at"}
        assert node["type"] == "test"
        assert node["properties"] == {"x": 1}


# ============================================================
# close
# ============================================================
class TestClose:
    """close 测试"""

    def test_close_with_memory_backend(self):
        """Memory 后端 close 无异常"""
        kb = KnowledgeBase()
        kb.close()  # 不应抛异常


# ============================================================
# query_nearest
# ============================================================
class TestQueryNearest:
    """query_nearest 测试（零外部依赖）"""

    @pytest.fixture
    def kb(self):
        kb = KnowledgeBase()
        kb.add_node("深度学习", node_type="concept", properties={"领域": "AI"})
        kb.add_node("神经网络", node_type="concept", properties={"领域": "AI"})
        kb.add_node("炒菜", node_type="life", properties={"领域": "生活"})
        return kb

    def test_empty_query_returns_empty(self, kb):
        """空查询 → []"""
        assert kb.query_nearest("") == []

    def test_empty_nodes_returns_empty(self):
        """空节点 → []"""
        kb = KnowledgeBase()
        assert kb.query_nearest("测试") == []

    def test_basic_query_with_node_type_filter(self, kb):
        """带 node_type 过滤"""
        results = kb.query_nearest("深度学习", node_type="concept")
        assert len(results) > 0
        for r in results:
            assert r["node_type"] == "concept"

    def test_basic_query_with_top_k(self, kb):
        """带 top_k 限制"""
        results = kb.query_nearest("深度学习", top_k=1)
        assert len(results) <= 1

    def test_basic_query_with_min_score(self, kb):
        """带 min_score 过滤"""
        results = kb.query_nearest("深度学习", min_score=0.5)
        for r in results:
            assert r["score"] >= 0.5

    def test_results_sorted_by_score_descending(self, kb):
        """结果按分数降序排列"""
        results = kb.query_nearest("深度学习 神经网络", top_k=10)
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True)


# ============================================================
# _char_ngrams
# ============================================================
class TestCharNGrams:
    """_char_ngrams 测试"""

    def test_basic_text(self):
        """基本文本"""
        kb = KnowledgeBase()
        grams = kb._char_ngrams("hello", n=2)
        assert "he" in grams
        assert "ll" in grams
        assert "lo" in grams

    def test_short_text_less_than_n(self):
        """短文本（长度 < n）"""
        kb = KnowledgeBase()
        grams = kb._char_ngrams("a", n=3)
        assert grams == {"a": 1}

    def test_empty_text(self):
        """空文本"""
        kb = KnowledgeBase()
        grams = kb._char_ngrams("", n=2)
        # 空字符串经过 lower 和正则后仍为空，长度 < n
        assert grams == {"": 1}

    def test_non_ascii_text_chinese(self):
        """中文（非 ASCII）文本"""
        kb = KnowledgeBase()
        grams = kb._char_ngrams("深度学习", n=2)
        assert "深度" in grams
        assert "学习" in grams
        assert "度学" in grams


# ============================================================
# _cosine
# ============================================================
class TestCosine:
    """_cosine 测试"""

    @staticmethod
    def _call(kb, a, b):
        return KnowledgeBase._cosine(kb, a, b)

    def test_identical_vectors(self):
        """相同向量 → 1.0"""
        kb = KnowledgeBase()
        result = self._call(kb, {"a": 1, "b": 2}, {"a": 1, "b": 2})
        assert result == pytest.approx(1.0)

    def test_orthogonal_vectors(self):
        """正交向量 → 0.0"""
        kb = KnowledgeBase()
        result = self._call(kb, {"a": 1}, {"b": 1})
        assert result == 0.0

    def test_empty_vectors(self):
        """空向量 → 0.0"""
        kb = KnowledgeBase()
        assert self._call(kb, {}, {"a": 1}) == 0.0
        assert self._call(kb, {"a": 1}, {}) == 0.0

    def test_single_element_vectors(self):
        """单元素向量"""
        kb = KnowledgeBase()
        result = self._call(kb, {"x": 3}, {"x": 3})
        assert result == pytest.approx(1.0)


# ============================================================
# _node_text
# ============================================================
class TestNodeText:
    """_node_text 测试"""

    def test_includes_name_type_properties(self):
        """包含名称、类型、属性"""
        kb = KnowledgeBase()
        node = KnowledgeNode(
            id="n1", name="深度学习", node_type="concept",
            properties={"领域": "AI", "层数": 128},
        )
        text = kb._node_text(node)
        assert "深度学习" in text
        assert "concept" in text
        assert "领域" in text
        assert "AI" in text
        assert "层数" in text
        assert "128" in text


# ============================================================
# bulk_add
# ============================================================
class TestBulkAdd:
    """bulk_add 测试"""

    @pytest.fixture
    def kb(self):
        return KnowledgeBase()

    def test_basic_bulk_add(self, kb):
        """基本批量添加"""
        records = [
            {"name": "节点1", "node_type": "t1", "properties": {"x": 1}},
            {"name": "节点2", "node_type": "t2"},
        ]
        nodes = kb.bulk_add(records)
        assert len(nodes) == 2
        assert nodes[0].name == "节点1"
        assert nodes[1].name == "节点2"
        assert kb.stats()["nodes"] == 2

    def test_empty_list(self, kb):
        """空列表"""
        nodes = kb.bulk_add([])
        assert nodes == []

    def test_with_custom_ids(self, kb):
        """带自定义 ID"""
        records = [
            {"name": "A", "id": "id-a"},
            {"name": "B", "id": "id-b"},
        ]
        nodes = kb.bulk_add(records)
        assert nodes[0].id == "id-a"
        assert nodes[1].id == "id-b"


# ============================================================
# update_node
# ============================================================
class TestUpdateNode:
    """update_node 测试"""

    @pytest.fixture
    def kb(self):
        kb = KnowledgeBase()
        kb.add_node("原始", node_type="raw", properties={"old": "val"}, node_id="n1")
        return kb

    def test_update_existing_node_name(self, kb):
        """更新名称"""
        updated = kb.update_node("n1", name="新名称")
        assert updated.name == "新名称"
        assert updated.node_type == "raw"  # 不变
        assert updated.properties == {"old": "val"}  # 不变

    def test_update_existing_node_type(self, kb):
        """更新类型"""
        updated = kb.update_node("n1", node_type="new_type")
        assert updated.node_type == "new_type"

    def test_update_existing_node_properties(self, kb):
        """更新属性"""
        updated = kb.update_node("n1", properties={"new": "data"})
        assert updated.properties == {"new": "data"}

    def test_update_nonexistent_returns_none(self, kb):
        """不存在的节点 → None"""
        assert kb.update_node("x", name="x") is None


# ============================================================
# delete_nodes
# ============================================================
class TestDeleteNodesBatch:
    """delete_nodes 批量删除测试"""

    @pytest.fixture
    def kb(self):
        kb = KnowledgeBase()
        kb.add_node("A", node_id="a")
        kb.add_node("B", node_id="b")
        kb.add_node("C", node_id="c")
        return kb

    def test_batch_delete(self, kb):
        """批量删除"""
        count = kb.delete_nodes(["a", "b"])
        assert count == 2
        assert kb.stats()["nodes"] == 1

    def test_mixed_existing_nonexistent(self, kb):
        """混合存在/不存在"""
        count = kb.delete_nodes(["a", "x", "y"])
        assert count == 1

    def test_returns_count(self, kb):
        """返回删除数量"""
        count = kb.delete_nodes(["a", "b", "c"])
        assert count == 3
        assert kb.stats()["nodes"] == 0


# ============================================================
# upsert_node
# ============================================================
class TestUpsertNode:
    """upsert_node 测试"""

    @pytest.fixture
    def kb(self):
        kb = KnowledgeBase()
        kb.add_node("存在", node_type="type_a", properties={"old": "prop"})
        return kb

    def test_create_new_returns_created_true(self, kb):
        """创建新节点 → created=True"""
        node, created = kb.upsert_node("新节点", node_type="new_type")
        assert created is True
        assert node.name == "新节点"
        assert node.node_type == "new_type"

    def test_update_existing_returns_created_false(self, kb):
        """更新已有节点 → created=False"""
        node, created = kb.upsert_node("存在", node_type="type_a", properties={"new": "prop"})
        assert created is False
        assert node.properties == {"new": "prop"}

    def test_same_name_different_type_creates_new(self, kb):
        """同名不同类型 → 创建新节点"""
        node, created = kb.upsert_node("存在", node_type="type_b")
        assert created is True
        assert node.node_type == "type_b"
        # 两个节点都存在
        assert kb.stats()["nodes"] == 2


# ============================================================
# query_by_prefix
# ============================================================
class TestQueryByPrefix:
    """query_by_prefix 测试"""

    @pytest.fixture
    def kb(self):
        kb = KnowledgeBase()
        kb.add_node("深度学习")
        kb.add_node("深度神经网络")
        kb.add_node("机器学习")
        kb.add_node("深度强化学习")
        return kb

    def test_match_by_prefix(self, kb):
        """前缀匹配"""
        results = kb.query_by_prefix("深度")
        assert len(results) == 3
        for r in results:
            assert r.name.startswith("深度")

    def test_no_match_returns_empty(self, kb):
        """无匹配 → []"""
        results = kb.query_by_prefix("不存在")
        assert results == []

    def test_respects_limit(self, kb):
        """遵守 limit 参数"""
        results = kb.query_by_prefix("深度", limit=1)
        assert len(results) == 1


# ============================================================
# query_paginated
# ============================================================
class TestQueryPaginated:
    """query_paginated 测试"""

    @pytest.fixture
    def kb(self):
        kb = KnowledgeBase()
        # 创建 30 个节点：20 个 type_a + 10 个 type_b
        for i in range(20):
            kb.add_node(f"节点_a_{i:02d}", node_type="type_a")
        for i in range(10):
            kb.add_node(f"节点_b_{i:02d}", node_type="type_b")
        return kb

    def test_basic_pagination(self, kb):
        """基本分页"""
        result = kb.query_paginated()
        assert result["total"] == 30
        assert result["page"] == 1
        assert result["page_size"] == 20
        assert len(result["items"]) == 20
        assert result["pages"] == 2

    def test_page_1(self, kb):
        """第 1 页"""
        result = kb.query_paginated(page=1, page_size=10)
        assert result["page"] == 1
        assert len(result["items"]) == 10

    def test_page_2(self, kb):
        """第 2 页"""
        result = kb.query_paginated(page=2, page_size=10)
        assert result["page"] == 2
        assert len(result["items"]) == 10

    def test_with_node_type_filter(self, kb):
        """带 node_type 过滤"""
        result = kb.query_paginated(node_type="type_b")
        assert result["total"] == 10
        assert len(result["items"]) == 10
        for item in result["items"]:
            assert item.node_type == "type_b"

    def test_sort_by_name(self, kb):
        """按名称排序"""
        result = kb.query_paginated(sort_by="name", page_size=30)
        names = [n.name for n in result["items"]]
        assert names == sorted(names)

    def test_sort_by_created_at(self, kb):
        """按 created_at 排序"""
        result = kb.query_paginated(sort_by="created_at", page_size=5)
        assert len(result["items"]) == 5
        # 默认升序（descending=False）
        times = [n.created_at for n in result["items"]]
        assert times == sorted(times)

    def test_descending_order(self, kb):
        """降序排列"""
        result = kb.query_paginated(sort_by="name", descending=True, page_size=30)
        names = [n.name for n in result["items"]]
        assert names == sorted(names, reverse=True)

    def test_verify_pages_calculation(self, kb):
        """验证 pages 计算"""
        result = kb.query_paginated(page_size=7)
        assert result["pages"] == (30 + 7 - 1) // 7  # 5


# ============================================================
# stats_enhanced
# ============================================================
class TestStatsEnhanced:
    """stats_enhanced 测试"""

    def test_includes_sqlalchemy_available(self):
        """包含 sqlalchemy_available 字段"""
        kb = KnowledgeBase()
        kb.add_node("A", node_type="t1")
        stats = kb.stats_enhanced()
        assert "sqlalchemy_available" in stats
        assert isinstance(stats["sqlalchemy_available"], bool)

    def test_includes_type_distribution(self):
        """包含 type_distribution"""
        kb = KnowledgeBase()
        kb.add_node("A", node_type="t1")
        kb.add_node("B", node_type="t1")
        kb.add_node("C", node_type="t2")
        stats = kb.stats_enhanced()
        assert "type_distribution" in stats
        assert stats["type_distribution"] == {"t1": 2, "t2": 1}


# ============================================================
# import_from_json
# ============================================================
class TestImportFromJSON:
    """import_from_json 测试"""

    def test_mock_file_read_with_valid_json(self):
        """mock 文件读取：有效 JSON"""
        kb = KnowledgeBase()
        valid_json = json.dumps([
            {"name": "节点A", "node_type": "ta", "properties": {"x": 1}},
            {"name": "节点B", "node_type": "tb"},
        ])
        with patch("builtins.open", mock_open(read_data=valid_json)):
            result = kb.import_from_json("fake.json")
        assert result["added"] == 2
        assert result["skipped"] == 0
        assert result["errors"] == []
        assert kb.stats()["nodes"] == 2

    def test_mock_file_read_with_invalid_json(self):
        """mock 文件读取：无效 JSON"""
        kb = KnowledgeBase()
        with patch("builtins.open", mock_open(read_data="not valid json {{{")):
            result = kb.import_from_json("fake.json")
        assert result["added"] == 0
        assert len(result["errors"]) > 0

    def test_mock_file_read_error(self):
        """mock 文件读取错误"""
        kb = KnowledgeBase()
        m = mock_open()
        m.side_effect = IOError("file not found")
        with patch("builtins.open", m):
            result = kb.import_from_json("fake.json")
        assert result["added"] == 0
        assert len(result["errors"]) == 1
        assert "file not found" in result["errors"][0]


# ============================================================
# import_from_csv
# ============================================================
class TestImportFromCSV:
    """import_from_csv 测试"""

    def test_mock_file_read_with_valid_csv(self):
        """mock 文件读取：有效 CSV"""
        kb = KnowledgeBase()
        csv_content = "name,node_type,field1,field2\nCSV节点1,type_a,val1,val2\nCSV节点2,type_b,val3,val4\n"
        with patch("builtins.open", mock_open(read_data=csv_content)):
            result = kb.import_from_csv("fake.csv")
        assert result["added"] == 2
        assert result["skipped"] == 0
        assert result["errors"] == []
        assert kb.stats()["nodes"] == 2

    def test_mock_file_read_error(self):
        """mock 文件读取错误"""
        kb = KnowledgeBase()
        m = mock_open()
        m.side_effect = IOError("file not found")
        with patch("builtins.open", m):
            result = kb.import_from_csv("fake.csv")
        assert result["added"] == 0
        assert len(result["errors"]) == 1
        assert "file not found" in result["errors"][0]


# ============================================================
# import_from_yaml
# ============================================================
class TestImportFromYAML:
    """import_from_yaml 测试"""

    def test_mock_open_with_regex_fallback_format(self):
        """mock open: 正则回退格式（无 PyYAML）"""
        kb = KnowledgeBase()
        yaml_content = (
            "- name: 儒家\n  node_type: school\n  properties:\n    代表: 孔子\n"
            "- name: 道家\n  node_type: school\n"
        )
        # 确保 PyYAML 不可用，走正则回退
        with patch.dict("sys.modules", {"yaml": None}):
            import sys
            try:
                sys.modules["yaml"] = None
                with patch("builtins.open", mock_open(read_data=yaml_content)):
                    result = kb.import_from_yaml("fake.yaml")
                assert result["added"] == 2
                assert result["errors"] == []
                assert kb.stats()["nodes"] == 2
            finally:
                sys.modules["yaml"] = None

    def test_mock_file_read_error(self):
        """mock 文件读取错误"""
        kb = KnowledgeBase()
        m = mock_open()
        m.side_effect = IOError("file not found")
        with patch.dict("sys.modules", {"yaml": None}):
            import sys
            try:
                sys.modules["yaml"] = None
                with patch("builtins.open", m):
                    result = kb.import_from_yaml("fake.yaml")
                assert result["added"] == 0
                assert len(result["errors"]) == 1
                assert "file not found" in result["errors"][0]
            finally:
                sys.modules["yaml"] = None


# ============================================================
# use_sqlalchemy
# ============================================================
class TestUseSqlalchemy:
    """use_sqlalchemy 测试"""

    def test_when_sqlalchemy_not_available_returns_false(self):
        """SQLAlchemy 不可用时返回 False"""
        kb = KnowledgeBase()
        # Mock _SQLALCHEMY_AVAILABLE 为 False
        with patch(
            "tengod.正财_知识固化.knowledge_base._SQLALCHEMY_AVAILABLE", False
        ):
            result = kb.use_sqlalchemy()
        assert result is False


# ============================================================
# use_vector_db
# ============================================================
class TestUseVectorDB:
    """use_vector_db 测试"""

    def test_provider_disable_returns_memory(self):
        """provider="disable" → memory"""
        kb = KnowledgeBase()
        result = kb.use_vector_db("disable")
        assert result["provider"] == "memory"
        assert result["dimension"] == 0
        assert result["indexed"] == 0

    def test_provider_auto_when_faiss_chroma_not_available(self):
        """provider="auto" 且 faiss/chroma 不可用 → 降级为 memory"""
        kb = KnowledgeBase()
        # 确保 faiss 和 chromadb 都不可用
        with patch.dict("sys.modules", {"faiss": None, "chromadb": None}):
            import sys
            try:
                sys.modules["faiss"] = None
                sys.modules["chromadb"] = None
                result = kb.use_vector_db("auto")
                assert result["provider"] == "memory"
            finally:
                sys.modules["faiss"] = None
                sys.modules["chromadb"] = None


# ============================================================
# vector_search
# ============================================================
class TestVectorSearch:
    """vector_search 测试"""

    def test_when_no_vector_provider_falls_back_to_query_nearest(self):
        """没有向量 provider → 回退到 query_nearest"""
        kb = KnowledgeBase()
        kb.add_node("深度学习", node_type="concept", properties={"领域": "AI"})
        # 不调用 use_vector_db，没有 _vector_provider 属性
        results = kb.vector_search("深度学习")
        assert len(results) > 0
        assert "score" in results[0]