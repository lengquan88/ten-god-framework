"""test_classics_search.py — 古籍全文检索模块测试"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tengod"))

from 正财_知识固化.classics_search import ClassicsSearchEngine, SikuQuanshuConnector


# ═══════════════════════════════════════════════════════════════════
# ClassicsSearchEngine 测试
# ═══════════════════════════════════════════════════════════════════


class TestClassicsSearchEngineInit:
    """ClassicsSearchEngine 初始化测试"""

    def test_init_builds_index(self):
        """初始化后 _classics_index 包含 12 部经典"""
        engine = ClassicsSearchEngine()
        assert len(engine._classics_index) == 12
        assert "易经" in engine._classics_index
        assert "道德经" in engine._classics_index
        assert "论语" in engine._classics_index

    def test_init_empty_history(self):
        """初始化后 _search_history 为空列表"""
        engine = ClassicsSearchEngine()
        assert engine._search_history == []


class TestClassicsSearchEngineSearch:
    """ClassicsSearchEngine.search() 测试"""

    def test_search_exact_title_match(self):
        """精确标题匹配返回高分结果"""
        engine = ClassicsSearchEngine()
        result = engine.search("易经")
        assert result["query"] == "易经"
        assert result["total"] >= 1
        assert result["results"][0]["title"] == "易经"
        assert result["results"][0]["score"] >= 10.0

    def test_search_title_match_ranks_higher(self):
        """标题匹配的评分高于仅文本匹配"""
        engine = ClassicsSearchEngine()
        result = engine.search("易经")
        title_match_score = result["results"][0]["score"]
        # "易经" 在标题中应获得 10.0 + 字符匹配加分
        assert title_match_score >= 10.0

    def test_search_text_content_match(self):
        """搜索文本内容能找到匹配"""
        engine = ClassicsSearchEngine()
        result = engine.search("君子")
        assert result["total"] >= 1
        titles = [r["title"] for r in result["results"]]
        # "君子" 出现在论语和诗经中
        assert "论语" in titles or "诗经" in titles

    def test_search_with_category_filter(self):
        """category 过滤只返回指定分类结果"""
        engine = ClassicsSearchEngine()
        result = engine.search("道", category="子部")
        assert result["total"] >= 1
        for r in result["results"]:
            assert r["category"] == "子部"

    def test_search_with_category_filter_all_四部(self):
        """四个分类各自过滤正确"""
        engine = ClassicsSearchEngine()
        for cat in ["经部", "史部", "子部", "集部"]:
            result = engine.search("之", category=cat)
            for r in result["results"]:
                assert r["category"] == cat, f"期望 {cat}，实际 {r['category']}"

    def test_search_with_limit(self):
        """limit 参数限制返回结果数量"""
        engine = ClassicsSearchEngine()
        result = engine.search("之", limit=3)
        assert result["total"] <= 3
        assert len(result["results"]) <= 3

    def test_search_with_limit_one(self):
        """limit=1 只返回一个结果"""
        engine = ClassicsSearchEngine()
        result = engine.search("道", limit=1)
        assert result["total"] <= 1
        assert len(result["results"]) <= 1

    def test_search_no_results(self):
        """搜索无匹配词返回空结果"""
        engine = ClassicsSearchEngine()
        result = engine.search("zzzqqq")
        assert result["total"] == 0
        assert result["results"] == []

    def test_search_updates_history(self):
        """搜索后历史记录被更新"""
        engine = ClassicsSearchEngine()
        engine.search("易经")
        history = engine.get_history()
        assert len(history) == 1
        assert history[0]["query"] == "易经"
        assert "time" in history[0]
        assert "result_count" in history[0]

    def test_search_result_structure(self):
        """搜索结果包含完整字段"""
        engine = ClassicsSearchEngine()
        result = engine.search("易经")
        assert "query" in result
        assert "total" in result
        assert "results" in result
        r = result["results"][0]
        assert "title" in r
        assert "category" in r
        assert "score" in r
        assert "snippet" in r
        assert "chapters" in r

    def test_search_results_sorted_by_score_desc(self):
        """搜索结果按评分降序排列"""
        engine = ClassicsSearchEngine()
        result = engine.search("道")
        scores = [r["score"] for r in result["results"]]
        assert scores == sorted(scores, reverse=True)


class TestClassicsSearchEngineGetByCategory:
    """ClassicsSearchEngine.get_by_category() 测试"""

    def test_get_by_category_经部(self):
        """经部应包含易经、论语、大学、中庸、孟子"""
        engine = ClassicsSearchEngine()
        jing = engine.get_by_category("经部")
        titles = {item["title"] for item in jing}
        assert titles == {"易经", "论语", "大学", "中庸", "孟子"}

    def test_get_by_category_史部(self):
        """史部应包含史记"""
        engine = ClassicsSearchEngine()
        shi = engine.get_by_category("史部")
        titles = {item["title"] for item in shi}
        assert titles == {"史记"}

    def test_get_by_category_子部(self):
        """子部应包含道德经、庄子、孙子兵法、黄帝内经"""
        engine = ClassicsSearchEngine()
        zi = engine.get_by_category("子部")
        titles = {item["title"] for item in zi}
        assert titles == {"道德经", "庄子", "孙子兵法", "黄帝内经"}

    def test_get_by_category_集部(self):
        """集部应包含诗经、楚辞"""
        engine = ClassicsSearchEngine()
        ji = engine.get_by_category("集部")
        titles = {item["title"] for item in ji}
        assert titles == {"诗经", "楚辞"}

    def test_get_by_category_unknown(self):
        """未知分类返回空列表"""
        engine = ClassicsSearchEngine()
        result = engine.get_by_category("不存在的分类")
        assert result == []


class TestClassicsSearchEngineList:
    """ClassicsSearchEngine list_categories / list_all_titles 测试"""

    def test_list_categories(self):
        """list_categories 返回四部分类"""
        engine = ClassicsSearchEngine()
        assert engine.list_categories() == ["经部", "史部", "子部", "集部"]

    def test_list_all_titles(self):
        """list_all_titles 返回全部 12 部典籍标题"""
        engine = ClassicsSearchEngine()
        titles = engine.list_all_titles()
        assert len(titles) == 12
        expected = {"易经", "道德经", "论语", "大学", "中庸", "孟子",
                     "庄子", "孙子兵法", "史记", "诗经", "楚辞", "黄帝内经"}
        assert set(titles) == expected


class TestClassicsSearchEngineHistory:
    """ClassicsSearchEngine.get_history() 测试"""

    def test_get_history_empty_initially(self):
        """初始化后历史为空"""
        engine = ClassicsSearchEngine()
        assert engine.get_history() == []

    def test_get_history_after_multiple_searches(self):
        """多次搜索后历史累加"""
        engine = ClassicsSearchEngine()
        engine.search("易经")
        engine.search("论语", category="经部")
        engine.search("zzzqqq")
        history = engine.get_history()
        assert len(history) == 3
        assert history[0]["query"] == "易经"
        assert history[1]["query"] == "论语"
        assert history[1]["category"] == "经部"
        assert history[2]["query"] == "zzzqqq"
        assert history[2]["result_count"] == 0


class TestClassicsSearchEngineScore:
    """ClassicsSearchEngine._score() 测试"""

    def test_score_title_match(self):
        """查询词在标题中匹配得 10.0 基础分"""
        engine = ClassicsSearchEngine()
        score = engine._score("易经", "易经", "乾元亨利贞")
        assert score >= 10.0

    def test_score_text_match(self):
        """查询词仅在文本中匹配得 5.0 基础分"""
        engine = ClassicsSearchEngine()
        score = engine._score("乾元", "易经", "乾元亨利贞")
        assert score >= 5.0
        assert score < 10.0  # 标题中不包含完整查询词

    def test_score_char_match_in_title(self):
        """逐字匹配：标题中每个字 +1.0"""
        engine = ClassicsSearchEngine()
        # "易" 在 "易经" 标题中
        score = engine._score("易", "易经", "乾元亨利贞")
        assert score >= 10.0 + 1.0  # 标题完整匹配 + 单字在标题中

    def test_score_char_match_in_text(self):
        """逐字匹配：文本中每个字 +0.5"""
        engine = ClassicsSearchEngine()
        # "乾" 不在标题"易经"中，但在文本"乾元亨利贞"中
        score = engine._score("乾", "易经", "乾元亨利贞")
        assert score >= 5.0  # 文本完整匹配
        assert score >= 5.0 + 0.5  # 单字在文本中

    def test_score_no_match(self):
        """完全不匹配返回 0.0"""
        engine = ClassicsSearchEngine()
        score = engine._score("xyz", "易经", "乾元亨利贞")
        assert score == 0.0


class TestClassicsSearchEngineExtractSnippet:
    """ClassicsSearchEngine._extract_snippet() 测试"""

    def test_extract_snippet_query_found(self):
        """查询词在文本中找到时，返回包含该词的片段"""
        engine = ClassicsSearchEngine()
        snippet = engine._extract_snippet("乾元亨利贞。", "亨利", 60)
        assert "亨利" in snippet

    def test_extract_snippet_query_not_found_returns_prefix(self):
        """查询词完全不在文本中时，返回前 max_len 字符"""
        engine = ClassicsSearchEngine()
        snippet = engine._extract_snippet("乾元亨利贞", "xyz", 10)
        assert snippet == "乾元亨利贞"

    def test_extract_snippet_char_found(self):
        """逐字查找时，返回包含该字的片段"""
        engine = ClassicsSearchEngine()
        snippet = engine._extract_snippet("乾元亨利贞", "利", 20)
        assert "利" in snippet

    def test_extract_snippet_with_ellipsis_start(self):
        """片段不从开头开始时，前面加 ..."""
        engine = ClassicsSearchEngine()
        long_text = "前" * 50 + "查询词" + "后" * 50
        snippet = engine._extract_snippet(long_text, "查询词", 20)
        assert snippet.startswith("...")

    def test_extract_snippet_with_ellipsis_end(self):
        """片段不到结尾时，后面加 ..."""
        engine = ClassicsSearchEngine()
        long_text = "前" * 50 + "查询词" + "后" * 50
        snippet = engine._extract_snippet(long_text, "查询词", 20)
        assert snippet.endswith("...")


# ═══════════════════════════════════════════════════════════════════
# SikuQuanshuConnector 测试
# ═══════════════════════════════════════════════════════════════════


class TestSikuQuanshuConnector:
    """SikuQuanshuConnector 测试"""

    def test_connector_init_with_api_key(self):
        """初始化时传入 api_key 被保存"""
        connector = SikuQuanshuConnector(api_key="test-key-123")
        assert connector._api_key == "test-key-123"

    def test_connector_init_without_api_key(self):
        """初始化时不传 api_key，_api_key 为 None"""
        connector = SikuQuanshuConnector()
        assert connector._api_key is None

    def test_connector_search_returns_placeholder(self):
        """search() 返回占位结构"""
        connector = SikuQuanshuConnector()
        result = connector.search("论语", volume="jing")
        assert result["source"] == "四库全书"
        assert result["query"] == "论语"
        assert result["volume"] == "jing"
        assert result["status"] == "connector_ready"
        assert "note" in result

    def test_connector_search_without_volume(self):
        """search() 不传 volume 时 volume 为 None"""
        connector = SikuQuanshuConnector()
        result = connector.search("论语")
        assert result["volume"] is None

    def test_connector_get_volume_list(self):
        """get_volume_list() 返回 4 个卷目"""
        connector = SikuQuanshuConnector()
        volumes = connector.get_volume_list()
        assert len(volumes) == 4
        ids = [v["id"] for v in volumes]
        assert ids == ["jing", "shi", "zi", "ji"]
        for v in volumes:
            assert "id" in v
            assert "name" in v
            assert "count" in v