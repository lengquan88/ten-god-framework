#!/usr/bin/env python3
"""
test_graph_engine.py — 知识图谱引擎单元测试
覆盖：节点/边管理、索引、查询（邻居/路径/子图/模式匹配/搜索）、统计导出
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from tengod.graph_engine import (
    GraphEdge,
    GraphNode,
    KnowledgeGraphDB,
    get_graph_db,
)

# ════════════════════════════════════════
# 1. 数据类
# ════════════════════════════════════════

class TestDataClasses:
    """GraphNode / GraphEdge 数据类"""

    def test_graph_node_creation(self):
        n = GraphNode(id="test_1", label="测试", name="节点1")
        assert n.id == "test_1"
        assert n.label == "测试"
        assert n.name == "节点1"
        assert n.properties == {}

    def test_graph_node_with_properties(self):
        n = GraphNode(id="t", label="L", name="N", properties={"k": "v"})
        assert n.properties["k"] == "v"

    def test_graph_node_to_dict(self):
        n = GraphNode(id="t", label="L", name="N", properties={"k": "v"})
        d = n.to_dict()
        assert d["id"] == "t"
        assert d["label"] == "L"
        assert d["name"] == "N"
        assert d["properties"] == {"k": "v"}

    def test_graph_edge_creation(self):
        e = GraphEdge(source="a", target="b", relation="r")
        assert e.source == "a"
        assert e.target == "b"
        assert e.relation == "r"
        assert e.weight == 1.0

    def test_graph_edge_to_dict(self):
        e = GraphEdge(source="a", target="b", relation="r", weight=0.5)
        d = e.to_dict()
        assert d["source"] == "a"
        assert d["target"] == "b"
        assert d["relation"] == "r"
        assert d["weight"] == 0.5


# ════════════════════════════════════════
# 2. 节点管理
# ════════════════════════════════════════

class TestNodeManagement:
    """节点增删查"""

    def setup_method(self):
        self.db = KnowledgeGraphDB()

    def test_add_node(self):
        n = self.db.add_node("n1", "五行", "金")
        assert n.id == "n1"
        assert n.name == "金"

    def test_add_node_duplicate_update(self):
        """重复添加同ID节点应更新属性"""
        self.db.add_node("n1", "五行", "金", properties={"color": "白"})
        self.db.add_node("n1", "五行", "金", properties={"number": 9})
        n = self.db.get_node("n1")
        assert n.properties["color"] == "白"
        assert n.properties["number"] == 9

    def test_get_node(self):
        self.db.add_node("n1", "五行", "金")
        n = self.db.get_node("n1")
        assert n is not None
        assert n.name == "金"

    def test_get_node_not_found(self):
        assert self.db.get_node("nonexistent") is None

    def test_find_node_by_name(self):
        self.db.add_node("n1", "五行", "金")
        n = self.db.find_node_by_name("金")
        assert n is not None
        assert n.id == "n1"

    def test_find_node_by_alias(self):
        self.db.add_node("n1", "五行", "金", aliases=["庚辛"])
        n = self.db.find_node_by_name("庚辛")
        assert n is not None
        assert n.id == "n1"

    def test_get_nodes_by_label(self):
        self.db.add_node("n1", "五行", "金")
        self.db.add_node("n2", "五行", "木")
        self.db.add_node("n3", "天干", "甲")
        nodes = self.db.get_nodes_by_label("五行")
        assert len(nodes) == 2


# ════════════════════════════════════════
# 3. 边管理
# ════════════════════════════════════════

class TestEdgeManagement:
    """边增删查"""

    def setup_method(self):
        self.db = KnowledgeGraphDB()
        self.db.add_node("a", "五行", "金")
        self.db.add_node("b", "五行", "水")

    def test_add_edge(self):
        e = self.db.add_edge("a", "b", "相生")
        assert e.source == "a"
        assert e.target == "b"
        assert e.relation == "相生"

    def test_add_edge_undirected(self):
        """无向边双向添加"""
        self.db.add_edge_undirected("a", "b", "相关")
        out_a = self.db.neighbors("a")
        out_b = self.db.neighbors("b")
        assert any(n.id == "b" for n in out_a)
        assert any(n.id == "a" for n in out_b)

    def test_neighbor_edges(self):
        self.db.add_edge("a", "b", "相生")
        edges = self.db.neighbor_edges("a")
        assert len(edges) >= 1


# ════════════════════════════════════════
# 4. 图查询
# ════════════════════════════════════════

class TestGraphQueries:
    """图查询算法"""

    def setup_method(self):
        self.db = KnowledgeGraphDB()
        # 构建测试图：a→b→c→d, a→c
        for nid, name in [("a", "甲"), ("b", "乙"), ("c", "丙"), ("d", "丁")]:
            self.db.add_node(nid, "天干", name)
        self.db.add_edge("a", "b", "相生")
        self.db.add_edge("b", "c", "相生")
        self.db.add_edge("c", "d", "相生")
        self.db.add_edge("a", "c", "相克")

    def test_neighbors(self):
        nb = self.db.neighbors("a")
        nb_ids = [n.id for n in nb]
        assert "b" in nb_ids
        assert "c" in nb_ids

    def test_shortest_path_direct(self):
        """a→b 直接相连"""
        path = self.db.shortest_path("a", "b")
        assert path is not None
        assert path == ["a", "b"]

    def test_shortest_path_indirect(self):
        """a→d 最短路径 a→c→d（2跳）而非 a→b→c→d（3跳）"""
        path = self.db.shortest_path("a", "d")
        assert path is not None
        assert path[0] == "a"
        assert path[-1] == "d"
        assert len(path) <= 3  # a→c→d

    def test_shortest_path_not_found(self):
        """不可达返回 None"""
        self.db.add_node("e", "天干", "戊")
        path = self.db.shortest_path("a", "e")
        assert path is None

    def test_shortest_path_with_edges(self):
        result = self.db.shortest_path_with_edges("a", "d")
        assert result is not None
        assert "path" in result
        assert "edges" in result
        assert "length" in result
        assert len(result["edges"]) == len(result["path"]) - 1

    def test_subgraph(self):
        """子图提取"""
        result = self.db.subgraph(["a", "b"], hops=1)
        assert "nodes" in result
        assert "edges" in result
        # a的1跳邻居包含b和c
        node_ids = [n["id"] for n in result["nodes"]]
        assert "a" in node_ids
        assert "b" in node_ids

    def test_match_relation(self):
        """关系模式匹配"""
        edges = self.db.match_relation(relation="相生")
        assert len(edges) >= 3  # a→b, b→c, c→d

    def test_match_pattern(self):
        """标签+属性模式匹配"""
        nodes = self.db.match_pattern(label="天干")
        assert len(nodes) >= 4  # 甲乙丙丁

    def test_search(self):
        """全文搜索"""
        result = self.db.search("甲", limit=5)
        assert isinstance(result, list)
        assert len(result) >= 1


# ════════════════════════════════════════
# 5. 统计与导出
# ════════════════════════════════════════

class TestStatsExport:
    """统计与导出"""

    def setup_method(self):
        self.db = KnowledgeGraphDB()
        self.db.add_node("a", "五行", "金")
        self.db.add_node("b", "五行", "水")
        self.db.add_node("c", "天干", "甲")
        self.db.add_edge("a", "b", "相生")
        self.db.add_edge("a", "c", "属五行")

    def test_stats(self):
        s = self.db.stats()
        assert s["total_nodes"] == 3
        assert s["total_edges"] == 2
        assert "五行" in s["labels"]
        assert "相生" in s["relations"]

    def test_export_graph(self):
        """导出整个图"""
        data = self.db.export_graph()
        assert "nodes" in data
        assert "edges" in data
        assert len(data["nodes"]) == 3
        assert len(data["edges"]) == 2

    def test_export_subgraph_by_label(self):
        """按标签导出子图"""
        data = self.db.export_subgraph_by_label(["五行"])
        assert len(data["nodes"]) == 2
        # 只包含五行节点
        for n in data["nodes"]:
            assert n["label"] == "五行"


# ════════════════════════════════════════
# 6. 命理知识库初始化
# ════════════════════════════════════════

class TestKnowledgeInitialization:
    """命理知识库初始化验证"""

    def test_get_graph_db_singleton(self):
        """get_graph_db 返回单例"""
        db1 = get_graph_db()
        db2 = get_graph_db()
        assert db1 is db2

    def test_initialized_db_has_nodes(self):
        """初始化后的图库应有节点"""
        db = get_graph_db()
        assert len(db._nodes) > 100  # 131节点

    def test_initialized_db_has_edges(self):
        """初始化后的图库应有边"""
        db = get_graph_db()
        assert len(db._edges) > 200  # 269边

    def test_initialized_db_labels(self):
        """初始化后包含8种标签"""
        db = get_graph_db()
        stats = db.stats()
        expected_labels = {"五行", "天干", "地支", "八卦", "十神", "神煞", "格局", "六十四卦"}
        assert set(stats["labels"].keys()) == expected_labels

    def test_initialized_db_relations(self):
        """初始化后包含14种关系"""
        db = get_graph_db()
        stats = db.stats()
        # 至少包含核心关系
        core_relations = {"相生", "相克", "相冲", "六合", "三合"}
        assert core_relations.issubset(set(stats["relations"].keys()))

    def test_wuxing_shengke_exists(self):
        """五行相生相克关系存在"""
        db = get_graph_db()
        # 金生水
        jin = db.find_node_by_name("金")
        shui = db.find_node_by_name("水")
        assert jin is not None and shui is not None
        nb = db.neighbors(jin.id)
        nb_names = [n.name for n in nb]
        assert "水" in nb_names

    def test_tiangan_chong_exists(self):
        """天干相冲关系存在（甲庚相冲）"""
        db = get_graph_db()
        jia = db.find_node_by_name("甲")
        geng = db.find_node_by_name("庚")
        assert jia is not None and geng is not None
        # 甲的邻居应包含庚
        nb = db.neighbors(jia.id)
        nb_ids = [n.id for n in nb]
        assert geng.id in nb_ids

    def test_64gua_count(self):
        """64卦节点数量为64"""
        db = get_graph_db()
        gua_nodes = db.get_nodes_by_label("六十四卦")
        assert len(gua_nodes) == 64
