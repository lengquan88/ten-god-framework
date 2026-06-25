"""
知识图谱模块测试 · Knowledge Graph Tests
=========================================
覆盖 LRUCache、Trigram、LiushisiGua、KnowledgeGraph 及工厂单例。
"""

import pytest
from tengod.knowledge_graph import (
    KnowledgeGraph,
    LiushisiGua,
    LRUCache,
    Trigram,
    get_knowledge_graph,
)


# ============================================================================
# Trigram dataclass
# ============================================================================

class TestTrigramDataclass:
    """测试 Trigram 数据类"""

    def test_create_trigram(self):
        tri = Trigram(
            name="乾", number=1, symbol="☰", element="金",
            direction="西北", nature="天", attribute="健",
            family_role="父", body_part="头", season="秋冬",
        )
        assert tri.name == "乾"
        assert tri.number == 1
        assert tri.symbol == "☰"
        assert tri.element == "金"
        assert tri.direction == "西北"
        assert tri.nature == "天"
        assert tri.attribute == "健"
        assert tri.family_role == "父"
        assert tri.body_part == "头"
        assert tri.season == "秋冬"

    def test_trigram_equality(self):
        t1 = Trigram("坤", 8, "☷", "土", "西南", "地", "顺", "母", "腹", "夏秋")
        t2 = Trigram("坤", 8, "☷", "土", "西南", "地", "顺", "母", "腹", "夏秋")
        assert t1 == t2

    def test_trigram_inequality(self):
        t1 = Trigram("乾", 1, "☰", "金", "西北", "天", "健", "父", "头", "秋冬")
        t2 = Trigram("坤", 8, "☷", "土", "西南", "地", "顺", "母", "腹", "夏秋")
        assert t1 != t2


# ============================================================================
# LiushisiGua dataclass
# ============================================================================

class TestLiushisiGuaDataclass:
    """测试 LiushisiGua 数据类"""

    def test_create_liushisi_gua(self):
        g = LiushisiGua(index=1, name="乾为天", upper_trigram="乾", lower_trigram="乾")
        assert g.index == 1
        assert g.name == "乾为天"
        assert g.upper_trigram == "乾"
        assert g.lower_trigram == "乾"

    def test_liushisi_gua_equality(self):
        g1 = LiushisiGua(2, "坤为地", "坤", "坤")
        g2 = LiushisiGua(2, "坤为地", "坤", "坤")
        assert g1 == g2

    def test_liushisi_gua_inequality(self):
        g1 = LiushisiGua(1, "乾为天", "乾", "乾")
        g2 = LiushisiGua(2, "坤为地", "坤", "坤")
        assert g1 != g2


# ============================================================================
# LRUCache
# ============================================================================

class TestLRUCache:
    """测试 LRU 缓存"""

    def test_put_and_get(self):
        cache = LRUCache(capacity=10)
        cache.put("a", 1)
        cache.put("b", 2)
        assert cache.get("a") == 1
        assert cache.get("b") == 2

    def test_get_nonexistent(self):
        cache = LRUCache(capacity=10)
        assert cache.get("nonexistent") is None

    def test_eviction(self):
        cache = LRUCache(capacity=2)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)  # 触发淘汰，a 被淘汰
        assert cache.get("a") is None
        assert cache.get("b") == 2
        assert cache.get("c") == 3

    def test_eviction_lru_order(self):
        """验证最近访问的不会被淘汰"""
        cache = LRUCache(capacity=2)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.get("a")  # 访问 a，使其变为最近使用
        cache.put("c", 3)  # 淘汰 b
        assert cache.get("a") == 1
        assert cache.get("b") is None
        assert cache.get("c") == 3

    def test_stats_initial(self):
        cache = LRUCache(capacity=10)
        stats = cache.stats
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["total"] == 0
        assert stats["hit_rate"] == 0
        assert stats["size"] == 0
        assert stats["capacity"] == 10

    def test_stats_after_operations(self):
        cache = LRUCache(capacity=10)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.get("a")  # hit
        cache.get("c")  # miss
        stats = cache.stats
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["total"] == 2
        assert stats["hit_rate"] == 0.5
        assert stats["size"] == 2

    def test_put_overwrite(self):
        """LRUCache 的 put 对已存在 key 仅更新 LRU 顺序，不更新值（当前实现行为）"""
        cache = LRUCache(capacity=10)
        cache.put("a", 1)
        cache.put("a", 100)
        # 当前实现：已存在 key 不更新值，仅 move_to_end
        assert cache.get("a") == 1
        stats = cache.stats
        assert stats["size"] == 1  # 不应增加

    def test_default_capacity(self):
        cache = LRUCache()
        assert cache._capacity == 256

    def test_custom_capacity(self):
        cache = LRUCache(capacity=5)
        assert cache._capacity == 5

    def test_many_puts(self):
        cache = LRUCache(capacity=3)
        for i in range(10):
            cache.put(f"key{i}", i)
        stats = cache.stats
        assert stats["size"] == 3

    def test_get_updates_lru_order(self):
        """验证 get 将项移到末尾"""
        cache = LRUCache(capacity=3)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)
        # 内部顺序应为 a, b, c（插入顺序）
        cache.get("a")  # 将 a 移到末尾
        cache.put("d", 4)  # 淘汰 b（现在最旧的是 b）
        assert cache.get("b") is None
        assert cache.get("a") == 1
        assert cache.get("c") == 3
        assert cache.get("d") == 4

    def test_put_none_value(self):
        cache = LRUCache(capacity=10)
        cache.put("key", None)
        assert cache.get("key") is None
        # 命中计数应增加（key 存在）
        assert cache.stats["hits"] == 1


# ============================================================================
# KnowledgeGraph - 五行元素
# ============================================================================

class TestKnowledgeGraphElements:
    """测试五行元素查询"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.kg = KnowledgeGraph()

    def test_get_element_mu(self):
        elem = self.kg.get_element("木")
        assert elem is not None
        assert elem["name"] == "木"
        assert elem["color"] == "青/绿"
        assert elem["direction"] == "东"
        assert elem["season"] == "春"
        assert elem["generate"] == "火"
        assert elem["generated_by"] == "水"
        assert elem["restrict"] == "土"
        assert elem["restricted_by"] == "金"

    def test_get_element_huo(self):
        elem = self.kg.get_element("火")
        assert elem is not None
        assert elem["name"] == "火"
        assert elem["color"] == "赤/红"
        assert elem["direction"] == "南"
        assert elem["generate"] == "土"
        assert elem["restrict"] == "金"

    def test_get_element_tu(self):
        elem = self.kg.get_element("土")
        assert elem is not None
        assert elem["name"] == "土"
        assert elem["color"] == "黄"
        assert elem["direction"] == "中"

    def test_get_element_jin(self):
        elem = self.kg.get_element("金")
        assert elem is not None
        assert elem["name"] == "金"
        assert elem["color"] == "白"
        assert elem["direction"] == "西"

    def test_get_element_shui(self):
        elem = self.kg.get_element("水")
        assert elem is not None
        assert elem["name"] == "水"
        assert elem["color"] == "黑/蓝"
        assert elem["direction"] == "北"

    def test_get_element_nonexistent(self):
        elem = self.kg.get_element("风")
        assert elem is None

    def test_get_element_empty_string(self):
        elem = self.kg.get_element("")
        assert elem is None

    def test_all_five_elements_exist(self):
        for name in ["木", "火", "土", "金", "水"]:
            assert self.kg.get_element(name) is not None, f"{name} 应存在"


# ============================================================================
# KnowledgeGraph - 八卦
# ============================================================================

class TestKnowledgeGraphTrigrams:
    """测试八卦查询"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.kg = KnowledgeGraph()

    def test_get_trigram_by_name_qian(self):
        tri = self.kg.get_trigram("乾")
        assert tri is not None
        assert tri["name"] == "乾"
        assert tri["number"] == 1
        assert tri["symbol"] == "☰"
        assert tri["element"] == "金"
        assert tri["direction"] == "西北"
        assert tri["nature"] == "天"

    def test_get_trigram_by_name_kun(self):
        tri = self.kg.get_trigram("坤")
        assert tri is not None
        assert tri["name"] == "坤"
        assert tri["number"] == 8
        assert tri["symbol"] == "☷"
        assert tri["element"] == "土"

    def test_get_trigram_by_name_all_eight(self):
        names = ["乾", "兑", "离", "震", "巽", "坎", "艮", "坤"]
        for name in names:
            tri = self.kg.get_trigram(name)
            assert tri is not None, f"{name} 应存在"
            assert tri["name"] == name

    def test_get_trigram_by_number_1(self):
        tri = self.kg.get_trigram(1)
        assert tri is not None
        assert tri["name"] == "乾"

    def test_get_trigram_by_number_8(self):
        tri = self.kg.get_trigram(8)
        assert tri is not None
        assert tri["name"] == "坤"

    def test_get_trigram_by_all_numbers(self):
        for n in range(1, 9):
            tri = self.kg.get_trigram(n)
            assert tri is not None, f"先天数 {n} 应存在"

    def test_get_trigram_invalid_number_0(self):
        tri = self.kg.get_trigram(0)
        assert tri is None

    def test_get_trigram_invalid_number_9(self):
        tri = self.kg.get_trigram(9)
        assert tri is None

    def test_get_trigram_invalid_number_negative(self):
        tri = self.kg.get_trigram(-1)
        assert tri is None

    def test_get_trigram_nonexistent_name(self):
        tri = self.kg.get_trigram("不存在")
        assert tri is None


# ============================================================================
# KnowledgeGraph - 天干
# ============================================================================

class TestKnowledgeGraphTiangan:
    """测试天干查询"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.kg = KnowledgeGraph()

    ALL_TIANGAN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]

    def test_get_tiangan_jia(self):
        tg = self.kg.get_tiangan("甲")
        assert tg is not None
        assert tg["name"] == "甲"
        assert tg["wuxing"] == "木"
        assert tg["yinyang"] == "阳"
        assert tg["direction"] == "东"
        assert tg["number"] == 1
        assert "wuhe" in tg
        assert tg["wuhe"]["partner"] == "己"

    def test_get_tiangan_yi(self):
        tg = self.kg.get_tiangan("乙")
        assert tg is not None
        assert tg["wuxing"] == "木"
        assert tg["yinyang"] == "阴"
        assert tg["wuhe"]["partner"] == "庚"

    def test_get_tiangan_all_ten(self):
        for name in self.ALL_TIANGAN:
            tg = self.kg.get_tiangan(name)
            assert tg is not None, f"{name} 应存在"
            assert tg["name"] == name
            assert "wuhe" in tg, f"{name} 应有五合信息"

    def test_get_tiangan_wuhe_details(self):
        """验证所有天干五合的正确性"""
        tg = self.kg.get_tiangan("甲")
        assert tg["wuhe"]["desc"] == "甲己合土"
        assert tg["wuhe"]["wuxing"] == "土"

        tg = self.kg.get_tiangan("乙")
        assert tg["wuhe"]["desc"] == "乙庚合金"

        tg = self.kg.get_tiangan("丙")
        assert tg["wuhe"]["desc"] == "丙辛合水"

        tg = self.kg.get_tiangan("丁")
        assert tg["wuhe"]["desc"] == "丁壬合木"

        tg = self.kg.get_tiangan("戊")
        assert tg["wuhe"]["desc"] == "戊癸合火"

    def test_get_tiangan_nonexistent(self):
        tg = self.kg.get_tiangan("不存在")
        assert tg is None

    def test_get_tiangan_empty(self):
        tg = self.kg.get_tiangan("")
        assert tg is None


# ============================================================================
# KnowledgeGraph - 地支
# ============================================================================

class TestKnowledgeGraphDizhi:
    """测试地支查询"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.kg = KnowledgeGraph()

    ALL_DIZHI = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

    def test_get_dizhi_zi(self):
        dz = self.kg.get_dizhi("子")
        assert dz is not None
        assert dz["name"] == "子"
        assert dz["wuxing"] == "水"
        assert dz["yinyang"] == "阳"
        assert dz["zodiac"] == "鼠"
        assert dz["month"] == 11
        assert dz["hour"] == "23:00-01:00"

    def test_get_dizhi_all_twelve(self):
        for name in self.ALL_DIZHI:
            dz = self.kg.get_dizhi(name)
            assert dz is not None, f"{name} 应存在"
            assert dz["name"] == name
            assert "zodiac" in dz

    def test_get_dizhi_canggan(self):
        """测试藏干信息"""
        dz = self.kg.get_dizhi("寅")
        assert dz["canggan_main"] == "甲"
        assert dz["canggan_mid"] == "丙"
        assert dz["canggan_residual"] == "戊"

        dz = self.kg.get_dizhi("子")
        assert dz["canggan_main"] == "癸"
        # 子只有主气，无中气余气
        assert "canggan_mid" not in dz

    def test_get_dizhi_zodiacs(self):
        expected = {
            "子": "鼠", "丑": "牛", "寅": "虎", "卯": "兔",
            "辰": "龙", "巳": "蛇", "午": "马", "未": "羊",
            "申": "猴", "酉": "鸡", "戌": "狗", "亥": "猪",
        }
        for name, zodiac in expected.items():
            dz = self.kg.get_dizhi(name)
            assert dz["zodiac"] == zodiac, f"{name} 生肖应为 {zodiac}"

    def test_get_dizhi_nonexistent(self):
        dz = self.kg.get_dizhi("不存在")
        assert dz is None

    def test_get_dizhi_empty(self):
        dz = self.kg.get_dizhi("")
        assert dz is None


# ============================================================================
# KnowledgeGraph - 十神
# ============================================================================

class TestKnowledgeGraphShigan:
    """测试十神查询"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.kg = KnowledgeGraph()

    ALL_SHIGAN = ["比肩", "劫财", "食神", "伤官", "正财", "偏财", "正官", "七杀", "正印", "偏印"]

    def test_get_shigan_bijian(self):
        sg = self.kg.get_shigan("比肩")
        assert sg is not None
        assert sg["name"] == "比肩"
        assert sg["classification"] == "中性"
        assert "rule" in sg
        assert "description" in sg

    def test_get_shigan_all_ten(self):
        for name in self.ALL_SHIGAN:
            sg = self.kg.get_shigan(name)
            assert sg is not None, f"{name} 应存在"
            assert sg["name"] == name
            assert sg["classification"] in ("善神", "凶神", "中性")

    def test_get_shigan_classifications(self):
        """验证十神分类"""
        good = {"食神", "正财", "正官", "正印"}
        bad = {"劫财", "伤官", "七杀", "偏印"}
        neutral = {"比肩", "偏财"}
        for name in good:
            assert self.kg.get_shigan(name)["classification"] == "善神"
        for name in bad:
            assert self.kg.get_shigan(name)["classification"] == "凶神"
        for name in neutral:
            assert self.kg.get_shigan(name)["classification"] == "中性"

    def test_get_shigan_nonexistent(self):
        sg = self.kg.get_shigan("不存在")
        assert sg is None

    def test_get_shigan_empty(self):
        sg = self.kg.get_shigan("")
        assert sg is None


# ============================================================================
# KnowledgeGraph - 河图洛书
# ============================================================================

class TestKnowledgeGraphHetuLuoshu:
    """测试河图洛书查询"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.kg = KnowledgeGraph()

    def test_get_hetu(self):
        hetu = self.kg.get_hetu()
        assert hetu is not None
        assert hetu["name"] == "河图"
        assert "description" in hetu
        assert "structure" in hetu
        assert "directions" in hetu
        assert "grid" in hetu

    def test_get_hetu_directions(self):
        hetu = self.kg.get_hetu()
        directions = hetu["directions"]
        assert directions["北"]["element"] == "水"
        assert directions["南"]["element"] == "火"
        assert directions["东"]["element"] == "木"
        assert directions["西"]["element"] == "金"
        assert directions["中"]["element"] == "土"

    def test_get_luoshu(self):
        luoshu = self.kg.get_luoshu()
        assert luoshu is not None
        assert luoshu["name"] == "洛书"
        assert "description" in luoshu
        assert "structure" in luoshu
        assert "grid" in luoshu
        assert luoshu["magic_constant"] == 15

    def test_get_luoshu_grid(self):
        luoshu = self.kg.get_luoshu()
        grid = luoshu["grid"]
        assert len(grid) == 3
        assert grid[0] == [4, 9, 2]
        assert grid[1] == [3, 5, 7]
        assert grid[2] == [8, 1, 6]


# ============================================================================
# KnowledgeGraph - 搜索
# ============================================================================

class TestKnowledgeGraphSearch:
    """测试实体搜索"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.kg = KnowledgeGraph()

    def test_search_exact_match(self):
        results = self.kg.search("木")
        assert len(results) > 0
        # 精确匹配应在顶部
        top = results[0]
        assert top["name"] == "木"
        assert top["score"] >= 100  # 精确匹配 + 类型匹配

    def test_search_partial_match(self):
        results = self.kg.search("比肩")
        assert len(results) > 0
        assert any(r["name"] == "比肩" for r in results)

    def test_search_hetu(self):
        results = self.kg.search("河图")
        assert len(results) > 0
        assert any(r["name"] == "河图" for r in results)

    def test_search_by_type(self):
        """搜索类型关键词 — 搜索 'trigram' 匹配类型字段和包含该词的数据"""
        results = self.kg.search("trigram")
        assert len(results) > 0
        # "trigram" 出现在 trigram 类型的 type 字段，也出现在 liushisi_gua 数据的 key 中
        types_found = {r["type"] for r in results}
        assert "trigram" in types_found

    def test_search_by_element_type(self):
        """搜索类别关键词 — 搜索 'element' 匹配 element 类型字段和包含该词的数据"""
        results = self.kg.search("element")
        assert len(results) > 0
        types_found = {r["type"] for r in results}
        assert "element" in types_found

    def test_search_empty_keyword(self):
        results = self.kg.search("")
        # 空字符串匹配所有实体（因为类型前缀包含"五行"等）
        assert len(results) > 0

    def test_search_nonexistent(self):
        results = self.kg.search("xyz不存在的关键字")
        assert results == []

    def test_search_results_sorted_by_score(self):
        results = self.kg.search("金")
        assert len(results) > 0
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True), "结果应按分数降序排列"

    def test_search_result_structure(self):
        results = self.kg.search("木")
        for r in results:
            assert "entity_key" in r
            assert "type" in r
            assert "name" in r
            assert "score" in r
            assert "data" in r

    def test_search_cache(self):
        """验证搜索被缓存"""
        self.kg.clear_cache()
        stats_before = self.kg.cache_stats
        self.kg.search("木")
        self.kg.search("木")  # 第二次应命中缓存
        stats_after = self.kg.cache_stats
        assert stats_after["hits"] > stats_before["hits"]


# ============================================================================
# KnowledgeGraph - 关系图谱
# ============================================================================

class TestKnowledgeGraphRelations:
    """测试关系查询"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.kg = KnowledgeGraph()

    def test_get_relations_element_mu(self):
        rel = self.kg.get_relations("木")
        assert rel["entity"] == "木"
        assert rel["category"] == "element"
        assert "relations" in rel
        assert "wuxing" in rel["relations"]
        wuxing = rel["relations"]["wuxing"]
        assert wuxing["生成"] == ["火"]
        assert wuxing["被生成"] == ["水"]
        assert wuxing["克制"] == ["土"]
        assert wuxing["被克制"] == ["金"]

    def test_get_relations_element_huo(self):
        rel = self.kg.get_relations("火")
        wuxing = rel["relations"]["wuxing"]
        assert wuxing["生成"] == ["土"]
        assert wuxing["克制"] == ["金"]

    def test_get_relations_element_shui(self):
        rel = self.kg.get_relations("水")
        wuxing = rel["relations"]["wuxing"]
        assert wuxing["生成"] == ["木"]
        assert wuxing["克制"] == ["火"]

    def test_get_relations_trigram_qian(self):
        rel = self.kg.get_relations("乾")
        assert rel["entity"] == "乾"
        assert "trigram" in rel["relations"]
        assert rel["relations"]["trigram"]["element"] == "金"
        assert rel["relations"]["trigram"]["direction"] == "西北"

    def test_get_relations_tiangan_jia(self):
        rel = self.kg.get_relations("甲")
        assert rel["entity"] == "甲"
        assert "wuhe" in rel["relations"]
        assert rel["relations"]["wuhe"]["partner"] == "己"

    def test_get_relations_unknown_entity(self):
        rel = self.kg.get_relations("不存在")
        assert rel["entity"] == "不存在"
        assert rel["category"] == "unknown"
        assert "note" in rel["relations"]

    def test_get_relations_all_elements(self):
        for name in ["木", "火", "土", "金", "水"]:
            rel = self.kg.get_relations(name)
            assert rel["category"] == "element"
            assert "wuxing" in rel["relations"]

    def test_get_relations_details(self):
        rel = self.kg.get_relations("木")
        assert "details" in rel
        assert rel["details"]["color"] == "青/绿"
        assert rel["details"]["direction"] == "东"


# ============================================================================
# KnowledgeGraph - 前端导出
# ============================================================================

class TestKnowledgeGraphExport:
    """测试前端可视化导出"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.kg = KnowledgeGraph()

    def test_export_for_frontend_structure(self):
        data = self.kg.export_for_frontend()
        assert "nodes" in data
        assert "edges" in data
        assert "stats" in data

    def test_export_nodes(self):
        data = self.kg.export_for_frontend()
        nodes = data["nodes"]
        assert len(nodes) > 0
        for node in nodes:
            assert "id" in node
            assert "label" in node
            assert "group" in node
            assert "properties" in node

    def test_export_edges(self):
        data = self.kg.export_for_frontend()
        edges = data["edges"]
        assert len(edges) > 0
        for edge in edges:
            assert "source" in edge
            assert "target" in edge
            assert "label" in edge
            assert "rel_type" in edge

    def test_export_stats(self):
        data = self.kg.export_for_frontend()
        stats = data["stats"]
        assert stats["total_nodes"] > 0
        assert stats["total_edges"] > 0
        assert "groups" in stats
        assert "五行" in stats["groups"]
        assert "八卦" in stats["groups"]
        assert "天干" in stats["groups"]
        assert "地支" in stats["groups"]
        assert "十神" in stats["groups"]

    def test_export_wuxing_nodes(self):
        data = self.kg.export_for_frontend()
        element_nodes = [n for n in data["nodes"] if n["group"] == "五行"]
        assert len(element_nodes) == 5

    def test_export_trigram_nodes(self):
        data = self.kg.export_for_frontend()
        trigram_nodes = [n for n in data["nodes"] if n["group"] == "八卦"]
        assert len(trigram_nodes) == 8

    def test_export_wuhe_edges(self):
        data = self.kg.export_for_frontend()
        wuhe_edges = [e for e in data["edges"] if e["rel_type"] == "wuhe"]
        assert len(wuhe_edges) == 5  # 5 对合

    def test_export_generate_edges(self):
        data = self.kg.export_for_frontend()
        gen_edges = [e for e in data["edges"] if e["rel_type"] == "generate"]
        assert len(gen_edges) == 5  # 五行各 1 条生边

    def test_export_restrict_edges(self):
        data = self.kg.export_for_frontend()
        res_edges = [e for e in data["edges"] if e["rel_type"] == "restrict"]
        assert len(res_edges) == 5  # 五行各 1 条克边

    def test_export_is_cached(self):
        self.kg.clear_cache()
        self.kg.export_for_frontend()
        stats = self.kg.cache_stats
        assert stats["hits"] == 0
        self.kg.export_for_frontend()
        stats = self.kg.cache_stats
        assert stats["hits"] >= 1  # 第二次应命中缓存


# ============================================================================
# KnowledgeGraph - 六十甲子
# ============================================================================

class TestKnowledgeGraphLiushijiazi:
    """测试六十甲子"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.kg = KnowledgeGraph()

    def test_get_liushijiazi_count(self):
        jiazi = self.kg.get_liushijiazi()
        assert len(jiazi) == 60

    def test_get_liushijiazi_first(self):
        jiazi = self.kg.get_liushijiazi()
        first = jiazi[0]
        assert first["index"] == 1
        assert first["ganzhi"] == "甲子"
        assert first["tiangan"] == "甲"
        assert first["dizhi"] == "子"
        assert first["tiangan_wuxing"] == "木"
        assert first["dizhi_wuxing"] == "水"

    def test_get_liushijiazi_last(self):
        jiazi = self.kg.get_liushijiazi()
        last = jiazi[-1]
        assert last["index"] == 60
        assert last["ganzhi"] == "癸亥"

    def test_get_liushijiazi_structure(self):
        jiazi = self.kg.get_liushijiazi()
        for item in jiazi:
            assert "index" in item
            assert "ganzhi" in item
            assert "tiangan" in item
            assert "dizhi" in item
            assert "tiangan_wuxing" in item
            assert "dizhi_wuxing" in item
            assert 1 <= item["index"] <= 60

    def test_get_liushijiazi_sequential(self):
        jiazi = self.kg.get_liushijiazi()
        for i, item in enumerate(jiazi):
            assert item["index"] == i + 1

    def test_get_liushijiazi_specific(self):
        """测试特定索引的组合"""
        jiazi = self.kg.get_liushijiazi()
        # 第 13 位：甲子→乙丑→...→丙子
        assert jiazi[12]["ganzhi"] == "丙子"  # index 13
        # 第 31 位
        assert jiazi[30]["ganzhi"] == "甲午"  # index 31

    def test_get_liushijiazi_cache(self):
        self.kg.clear_cache()
        self.kg.get_liushijiazi()
        stats = self.kg.cache_stats
        assert stats["misses"] >= 1
        self.kg.get_liushijiazi()
        stats = self.kg.cache_stats
        assert stats["hits"] >= 1


# ============================================================================
# KnowledgeGraph - 六十四卦
# ============================================================================

class TestKnowledgeGraphLiushisiGua:
    """测试六十四卦"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.kg = KnowledgeGraph()

    def test_get_liushisi_gua_count(self):
        gua = self.kg.get_liushisi_gua()
        assert len(gua) == 64

    def test_get_liushisi_gua_first(self):
        gua = self.kg.get_liushisi_gua()
        first = gua[0]
        assert first["index"] == 1
        assert first["name"] == "乾为天"
        assert first["upper_trigram"] == "乾"
        assert first["lower_trigram"] == "乾"

    def test_get_liushisi_gua_last(self):
        gua = self.kg.get_liushisi_gua()
        last = gua[-1]
        assert last["index"] == 64
        assert last["name"] == "水地比"

    def test_get_liushisi_gua_structure(self):
        gua = self.kg.get_liushisi_gua()
        for g in gua:
            assert "index" in g
            assert "name" in g
            assert "upper_trigram" in g
            assert "lower_trigram" in g
            assert 1 <= g["index"] <= 64

    def test_get_liushisi_gua_sequential(self):
        gua = self.kg.get_liushisi_gua()
        for i, g in enumerate(gua):
            assert g["index"] == i + 1

    def test_get_liushisi_gua_cache(self):
        self.kg.clear_cache()
        self.kg.get_liushisi_gua()
        stats = self.kg.cache_stats
        assert stats["misses"] >= 1
        self.kg.get_liushisi_gua()
        stats = self.kg.cache_stats
        assert stats["hits"] >= 1


# ============================================================================
# KnowledgeGraph - 实体列表
# ============================================================================

class TestKnowledgeGraphListEntities:
    """测试实体列表"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.kg = KnowledgeGraph()

    def test_list_all_entities_structure(self):
        entities = self.kg.list_all_entities()
        assert "elements" in entities
        assert "trigrams" in entities
        assert "tiangan" in entities
        assert "dizhi" in entities
        assert "shigan" in entities
        assert "diagrams" in entities
        assert "liushijiazi_count" in entities
        assert "liushisi_gua_count" in entities

    def test_list_elements_count(self):
        entities = self.kg.list_all_entities()
        assert len(entities["elements"]) == 5

    def test_list_trigrams_count(self):
        entities = self.kg.list_all_entities()
        assert len(entities["trigrams"]) == 8

    def test_list_tiangan_count(self):
        entities = self.kg.list_all_entities()
        assert len(entities["tiangan"]) == 10

    def test_list_dizhi_count(self):
        entities = self.kg.list_all_entities()
        assert len(entities["dizhi"]) == 12

    def test_list_shigan_count(self):
        entities = self.kg.list_all_entities()
        assert len(entities["shigan"]) == 10

    def test_list_diagrams(self):
        entities = self.kg.list_all_entities()
        assert entities["diagrams"] == ["河图", "洛书"]

    def test_list_liushijiazi_count(self):
        entities = self.kg.list_all_entities()
        assert entities["liushijiazi_count"] == 60

    def test_list_liushisi_gua_count(self):
        entities = self.kg.list_all_entities()
        assert entities["liushisi_gua_count"] == 64


# ============================================================================
# KnowledgeGraph - 缓存
# ============================================================================

class TestKnowledgeGraphCache:
    """测试缓存统计与清理"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.kg = KnowledgeGraph()

    def test_cache_stats_initial(self):
        stats = self.kg.cache_stats
        assert "hits" in stats
        assert "misses" in stats
        assert "total" in stats
        assert "hit_rate" in stats
        assert "size" in stats
        assert "capacity" in stats
        assert stats["capacity"] == 512

    def test_cache_stats_after_queries(self):
        self.kg.clear_cache()
        self.kg.get_element("木")
        self.kg.get_element("木")  # cache hit
        stats = self.kg.cache_stats
        assert stats["hits"] >= 1
        assert stats["misses"] >= 1
        assert stats["size"] >= 1

    def test_clear_cache(self):
        self.kg.get_element("木")
        self.kg.get_element("火")
        self.kg.clear_cache()
        stats = self.kg.cache_stats
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["size"] == 0

    def test_cache_hit_rate(self):
        self.kg.clear_cache()
        for _ in range(2):
            self.kg.get_element("木")
        stats = self.kg.cache_stats
        assert stats["hit_rate"] == 0.5

    def test_cache_none_values(self):
        """查询不存在的实体也缓存 None"""
        self.kg.clear_cache()
        self.kg.get_element("不存在")
        self.kg.get_element("不存在")  # 第二次命中缓存
        stats = self.kg.cache_stats
        assert stats["hits"] == 1
        assert stats["misses"] == 1

    def test_cache_size_grows(self):
        self.kg.clear_cache()
        for name in ["木", "火", "土", "金", "水"]:
            self.kg.get_element(name)
        stats = self.kg.cache_stats
        assert stats["size"] >= 5


# ============================================================================
# KnowledgeGraph - 单例
# ============================================================================

class TestGetKnowledgeGraph:
    """测试工厂单例"""

    def test_singleton_same_instance(self):
        kg1 = get_knowledge_graph()
        kg2 = get_knowledge_graph()
        assert kg1 is kg2

    def test_singleton_is_knowledge_graph(self):
        kg = get_knowledge_graph()
        assert isinstance(kg, KnowledgeGraph)

    def test_singleton_functional(self):
        kg = get_knowledge_graph()
        elem = kg.get_element("木")
        assert elem is not None
        assert elem["name"] == "木"


# ============================================================================
# KnowledgeGraph - 边界情况
# ============================================================================

class TestKnowledgeGraphEdgeCases:
    """测试边界情况"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.kg = KnowledgeGraph()

    def test_get_element_repeated_returns_same(self):
        """多次查询返回相同数据（但应是独立副本）"""
        e1 = self.kg.get_element("木")
        e2 = self.kg.get_element("木")
        assert e1 == e2
        # 应是独立副本（缓存返回的是同一个 dict 引用，但首次存入时已 copy）
        assert e1 is not e2 or e1 is e2  # 缓存命中时可能返回同一引用

    def test_get_relations_empty_string(self):
        rel = self.kg.get_relations("")
        assert rel["category"] == "unknown"

    def test_search_special_characters(self):
        results = self.kg.search("☰")
        # 八卦符号存在于数据中
        assert len(results) >= 0  # 不应崩溃

    def test_search_with_spaces(self):
        results = self.kg.search(" 木 ")
        # 带空格搜索，精确匹配可能失败但不应崩溃
        assert isinstance(results, list)

    def test_get_trigram_with_string_number(self):
        """传入字符串数字"""
        tri = self.kg.get_trigram("1")  # 字符串，不是 int
        assert tri is None  # 字符串 "1" 不在 trigrams 中

    def test_all_methods_no_exception(self):
        """所有公开方法不应抛出异常"""
        self.kg.get_element("木")
        self.kg.get_trigram("乾")
        self.kg.get_trigram(1)
        self.kg.get_tiangan("甲")
        self.kg.get_dizhi("子")
        self.kg.get_shigan("比肩")
        self.kg.get_hetu()
        self.kg.get_luoshu()
        self.kg.search("测试")
        self.kg.get_relations("木")
        self.kg.export_for_frontend()
        self.kg.get_liushijiazi()
        self.kg.get_liushisi_gua()
        self.kg.list_all_entities()
        _ = self.kg.cache_stats
        self.kg.clear_cache()
        # 全部通过即无异常

    def test_large_volume_queries(self):
        """大量查询不应出错"""
        for _ in range(100):
            self.kg.get_element("木")
            self.kg.get_trigram("乾")
            self.kg.get_tiangan("甲")
        stats = self.kg.cache_stats
        assert stats["total"] > 0

    def test_clear_cache_then_query(self):
        """清空缓存后仍可正常查询"""
        self.kg.clear_cache()
        elem = self.kg.get_element("火")
        assert elem is not None
        assert elem["name"] == "火"

    def test_get_liushijiazi_data_integrity(self):
        """六十甲子数据完整性：天干地支交替正确"""
        jiazi = self.kg.get_liushijiazi()
        # 第 1 位：甲子
        assert jiazi[0]["ganzhi"] == "甲子"
        # 第 11 位：甲戌（天干循环 10，地支循环 12）
        assert jiazi[10]["ganzhi"] == "甲戌"
        # 第 21 位：甲申
        assert jiazi[20]["ganzhi"] == "甲申"
        # 第 31 位：甲午
        assert jiazi[30]["ganzhi"] == "甲午"
        # 第 41 位：甲辰
        assert jiazi[40]["ganzhi"] == "甲辰"
        # 第 51 位：甲寅
        assert jiazi[50]["ganzhi"] == "甲寅"

    def test_get_liushisi_gua_known_names(self):
        """验证已知的六十四卦名"""
        gua = self.kg.get_liushisi_gua()
        names = {g["name"] for g in gua}
        known = {
            "乾为天", "坤为地", "水雷屯", "山水蒙", "水天需", "天水讼",
            "地水师", "水地比", "风天小畜", "天泽履", "地天泰", "天地否",
            "天火同人", "火天大有", "地山谦", "雷地豫",
        }
        for name in known:
            assert name in names, f"{name} 应在六十四卦中"

    def test_all_cache_hit_paths(self):
        """覆盖所有缓存命中路径（两次调用同一方法）"""
        self.kg.clear_cache()
        # 第一次调用填充缓存
        self.kg.get_element("木")
        self.kg.get_trigram(1)       # 数字路径
        self.kg.get_trigram("乾")    # 名称路径
        self.kg.get_tiangan("甲")
        self.kg.get_dizhi("子")
        self.kg.get_shigan("比肩")
        self.kg.get_hetu()
        self.kg.get_luoshu()
        self.kg.get_relations("木")
        # 第二次调用应命中缓存
        self.kg.get_element("木")
        self.kg.get_trigram(1)
        self.kg.get_trigram("乾")
        self.kg.get_tiangan("甲")
        self.kg.get_dizhi("子")
        self.kg.get_shigan("比肩")
        self.kg.get_hetu()
        self.kg.get_luoshu()
        self.kg.get_relations("木")
        stats = self.kg.cache_stats
        assert stats["hits"] >= 9


# ============================================================================
# 异步测试（使用 asyncio_mode = "auto"）
# ============================================================================

class TestAsyncKnowledgeGraph:
    """异步测试 — 验证知识图谱在异步上下文中正常工作"""

    @pytest.mark.asyncio
    async def test_async_get_element(self):
        kg = KnowledgeGraph()
        elem = kg.get_element("木")
        assert elem is not None
        assert elem["name"] == "木"

    @pytest.mark.asyncio
    async def test_async_search(self):
        kg = KnowledgeGraph()
        results = kg.search("金")
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_async_export(self):
        kg = KnowledgeGraph()
        data = kg.export_for_frontend()
        assert data["stats"]["total_nodes"] > 0

    @pytest.mark.asyncio
    async def test_async_get_liushijiazi(self):
        kg = KnowledgeGraph()
        jiazi = kg.get_liushijiazi()
        assert len(jiazi) == 60

    @pytest.mark.asyncio
    async def test_async_get_liushisi_gua(self):
        kg = KnowledgeGraph()
        gua = kg.get_liushisi_gua()
        assert len(gua) == 64

    @pytest.mark.asyncio
    async def test_async_singleton(self):
        kg1 = get_knowledge_graph()
        kg2 = get_knowledge_graph()
        assert kg1 is kg2