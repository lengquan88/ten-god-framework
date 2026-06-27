"""tests/test_knowledge_sync.py — 知识库同步插件测试

测试覆盖：
- 初始化（有/无 kb）
- set_knowledge_base()
- 网络同步方法（Wikipedia / 百度百科）在离线环境下的优雅降级
- 古籍同步（内置数据）
- sync_all() / get_history()
- 经典数据完整性
"""
import json
from unittest.mock import patch, MagicMock
import urllib.request

import pytest
from tengod.正财_知识固化.knowledge_sync import KnowledgeSyncPlugin


# ── Mock KnowledgeBase ──────────────────────────────────────────────────────

class MockKB:
    """模拟知识库对象，记录 add_node 调用"""

    def __init__(self):
        self.nodes: list[dict] = []

    def add_node(self, node_id: str, node_type: str, properties: dict):
        self.nodes.append({
            "node_id": node_id,
            "node_type": node_type,
            "properties": properties,
        })


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_kb():
    return MockKB()


@pytest.fixture
def plugin_with_kb(mock_kb):
    return KnowledgeSyncPlugin(kb=mock_kb)


@pytest.fixture
def plugin_without_kb():
    return KnowledgeSyncPlugin(kb=None)


# ── 初始化 / set_knowledge_base ─────────────────────────────────────────────

class TestInit:
    """测试初始化相关"""

    def test_init_with_kb(self):
        """初始化时传入 kb"""
        kb = MockKB()
        plugin = KnowledgeSyncPlugin(kb=kb)
        assert plugin._kb is kb
        assert plugin.get_history() == []

    def test_init_without_kb(self):
        """初始化时不传 kb"""
        plugin = KnowledgeSyncPlugin()
        assert plugin._kb is None
        assert plugin.get_history() == []

    def test_set_knowledge_base(self):
        """set_knowledge_base 更新内部 kb 引用"""
        kb1 = MockKB()
        kb2 = MockKB()
        plugin = KnowledgeSyncPlugin(kb=kb1)
        assert plugin._kb is kb1
        plugin.set_knowledge_base(kb2)
        assert plugin._kb is kb2


# ── Wikipedia 同步 ──────────────────────────────────────────────────────────

class TestSyncWikipedia:
    """测试 Wikipedia 同步（离线环境，网络请求会失败）"""

    def test_sync_without_kb_handles_gracefully(self, plugin_without_kb):
        """没有 kb 时，Wikipedia 同步应优雅处理（返回 failed count）"""
        result = plugin_without_kb.sync_from_wikipedia(["儒家", "道家"])
        assert "synced" in result
        assert "failed" in result
        assert "details" in result
        assert result["synced"] == 0
        assert result["failed"] == 2  # 两个 topic 都获取失败
        assert len(result["details"]) == 2

    def test_sync_with_kb_handles_network_failure(self, plugin_with_kb, mock_kb):
        """有 kb 但网络不可达时，Wikipedia 同步应优雅降级"""
        result = plugin_with_kb.sync_from_wikipedia(["儒家"])
        assert result["synced"] == 0
        assert result["failed"] == 1
        assert mock_kb.nodes == []  # 没有成功添加到 kb

    def test_sync_returns_correct_structure(self, plugin_without_kb):
        """返回结果结构正确"""
        result = plugin_without_kb.sync_from_wikipedia(["易经", "阴阳", "五行"])
        assert isinstance(result, dict)
        assert set(result.keys()) == {"synced", "failed", "details"}
        assert result["synced"] + result["failed"] == 3

    def test_sync_records_history(self, plugin_without_kb):
        """同步后应记录到历史"""
        plugin_without_kb.sync_from_wikipedia(["道家"])
        history = plugin_without_kb.get_history()
        assert len(history) == 1
        assert history[0]["source"] == "wikipedia"
        assert "time" in history[0]
        assert "results" in history[0]


# ── 百度百科同步 ────────────────────────────────────────────────────────────

class TestSyncBaiduBaike:
    """测试百度百科同步（离线环境，网络请求会失败）"""

    def test_sync_without_kb_handles_gracefully(self, plugin_without_kb):
        """没有 kb 时，百度百科同步应优雅处理"""
        result = plugin_without_kb.sync_from_baidu_baike(["儒家", "道家"])
        assert result["synced"] == 0
        assert result["failed"] == 2
        assert len(result["details"]) == 2

    def test_sync_with_kb_handles_network_failure(self, plugin_with_kb, mock_kb):
        """有 kb 但网络不可达时，百度百科同步应优雅降级"""
        result = plugin_with_kb.sync_from_baidu_baike(["论语"])
        assert result["synced"] == 0
        assert result["failed"] == 1
        assert mock_kb.nodes == []

    def test_sync_records_history(self, plugin_without_kb):
        """同步后应记录到历史"""
        plugin_without_kb.sync_from_baidu_baike(["孙子兵法"])
        history = plugin_without_kb.get_history()
        assert len(history) == 1
        assert history[0]["source"] == "baidu_baike"


# ── 古籍同步 ────────────────────────────────────────────────────────────────

class TestSyncClassics:
    """测试古籍同步（使用内置数据，不依赖网络）"""

    def test_sync_without_kb(self, plugin_without_kb):
        """没有 kb 时，能找到经典但不同步（不会报错）"""
        result = plugin_without_kb.sync_from_classics()
        assert result["synced"] == 0
        assert result["failed"] == 0
        assert result["details"] == []

    def test_sync_with_kb_all_default(self, plugin_with_kb, mock_kb):
        """有 kb 时，同步全部 7 部默认经典"""
        result = plugin_with_kb.sync_from_classics()
        assert result["synced"] == 7
        assert result["failed"] == 0
        assert len(mock_kb.nodes) == 7
        # 验证 node 结构
        for node in mock_kb.nodes:
            assert node["node_type"] == "classic"
            assert "author" in node["properties"]
            assert "dynasty" in node["properties"]
            assert "category" in node["properties"]
            assert "summary" in node["properties"]

    def test_sync_with_specific_classics(self, plugin_with_kb, mock_kb):
        """同步指定经典列表"""
        result = plugin_with_kb.sync_from_classics(["易经", "道德经", "论语"])
        assert result["synced"] == 3
        assert result["failed"] == 0
        assert len(mock_kb.nodes) == 3
        node_ids = [n["node_id"] for n in mock_kb.nodes]
        assert "古籍:易经" in node_ids
        assert "古籍:道德经" in node_ids
        assert "古籍:论语" in node_ids

    def test_sync_with_unknown_classic(self, plugin_with_kb, mock_kb):
        """同步未知经典应计入 failed"""
        result = plugin_with_kb.sync_from_classics(["易经", "不存在的经典"])
        assert result["synced"] == 1
        assert result["failed"] == 1
        assert len(mock_kb.nodes) == 1
        assert result["details"][1]["status"] == "not found"

    def test_sync_records_history(self, plugin_with_kb):
        """同步后应记录历史"""
        plugin_with_kb.sync_from_classics(["易经"])
        history = plugin_with_kb.get_history()
        assert len(history) == 1
        assert history[0]["source"] == "classics"
        assert history[0]["results"]["synced"] == 1


# ── sync_all / get_history ──────────────────────────────────────────────────

class TestSyncAllAndHistory:
    """测试 sync_all 和 get_history"""

    def test_sync_all_returns_dict_with_3_keys(self, plugin_without_kb):
        """sync_all() 返回包含 3 个 key 的字典"""
        result = plugin_without_kb.sync_all()
        assert isinstance(result, dict)
        assert set(result.keys()) == {"wikipedia", "baidu_baike", "classics"}

    def test_sync_all_records_3_history_entries(self, plugin_without_kb):
        """sync_all 应记录 3 条历史"""
        plugin_without_kb.sync_all()
        history = plugin_without_kb.get_history()
        assert len(history) == 3
        sources = {h["source"] for h in history}
        assert sources == {"wikipedia", "baidu_baike", "classics"}

    def test_get_history_initially_empty(self, plugin_without_kb):
        """初始状态历史为空"""
        assert plugin_without_kb.get_history() == []

    def test_get_history_after_multiple_syncs(self, plugin_without_kb):
        """多次同步后历史累积正确"""
        plugin_without_kb.sync_from_wikipedia(["儒家"])
        plugin_without_kb.sync_from_baidu_baike(["道家"])
        plugin_without_kb.sync_from_classics(["易经"])
        history = plugin_without_kb.get_history()
        assert len(history) == 3
        assert history[0]["source"] == "wikipedia"
        assert history[1]["source"] == "baidu_baike"
        assert history[2]["source"] == "classics"


# ── 经典数据完整性 ──────────────────────────────────────────────────────────

class TestClassicData:
    """测试 _get_classic_data() 内置数据"""

    EXPECTED_CLASSICS = ["易经", "道德经", "论语", "孙子兵法", "黄帝内经", "诗经", "史记"]

    def test_returns_7_classics(self):
        """_get_classic_data() 返回 7 部经典"""
        plugin = KnowledgeSyncPlugin()
        data = plugin._get_classic_data()
        assert len(data) == 7
        assert set(data.keys()) == set(self.EXPECTED_CLASSICS)

    def test_yijing_has_correct_attributes(self):
        """易经具有正确的属性"""
        plugin = KnowledgeSyncPlugin()
        data = plugin._get_classic_data()
        yijing = data["易经"]
        assert yijing["author"] == "周文王/孔子"
        assert yijing["dynasty"] == "周"
        assert yijing["category"] == "哲学/占卜"
        assert "阴阳变化" in yijing["summary"]
        assert "六十四卦" in yijing["summary"]

    def test_each_classic_has_required_attributes(self):
        """每部经典都包含 author, dynasty, category, summary"""
        plugin = KnowledgeSyncPlugin()
        data = plugin._get_classic_data()
        for classic_name in self.EXPECTED_CLASSICS:
            info = data[classic_name]
            assert "author" in info, f"{classic_name} missing author"
            assert "dynasty" in info, f"{classic_name} missing dynasty"
            assert "category" in info, f"{classic_name} missing category"
            assert "summary" in info, f"{classic_name} missing summary"
            assert isinstance(info["summary"], str)
            assert len(info["summary"]) > 0

    def test_shiji_has_correct_attributes(self):
        """史记具有正确的属性"""
        plugin = KnowledgeSyncPlugin()
        data = plugin._get_classic_data()
        shiji = data["史记"]
        assert shiji["author"] == "司马迁"
        assert shiji["dynasty"] == "汉"
        assert shiji["category"] == "历史"
        assert "纪传体" in shiji["summary"]

    def test_sync_classics_preserves_node_properties(self, plugin_with_kb, mock_kb):
        """同步经典时节点属性完整保留"""
        plugin_with_kb.sync_from_classics(["道德经"])
        node = mock_kb.nodes[0]
        assert node["node_id"] == "古籍:道德经"
        assert node["node_type"] == "classic"
        assert node["properties"]["author"] == "老子"
        assert node["properties"]["dynasty"] == "春秋"
        assert node["properties"]["category"] == "哲学"
        assert node["properties"]["source"] == "中华经典古籍库"
        assert "synced_at" in node["properties"]


# ── _fetch_wikipedia ────────────────────────────────────────────────────────

class TestFetchWikipedia:
    """测试 _fetch_wikipedia 内部方法"""

    def test_fetch_wikipedia_success(self, plugin_without_kb):
        """_fetch_wikipedia — mock 返回有效 Wikipedia API JSON"""
        mock_resp = MagicMock()
        mock_resp.__enter__.return_value = mock_resp
        mock_resp.read.return_value = json.dumps({
            "query": {
                "pages": {
                    "12345": {
                        "title": "儒家",
                        "extract": "儒家是中国古代主流思想流派。",
                    }
                }
            }
        }).encode("utf-8")

        with patch.object(urllib.request, "urlopen", return_value=mock_resp):
            title, summary = plugin_without_kb._fetch_wikipedia("儒家", "zh")
        assert title == "儒家"
        assert summary == "儒家是中国古代主流思想流派。"

    def test_fetch_wikipedia_no_page(self, plugin_without_kb):
        """_fetch_wikipedia — page_id 为 -1 时返回 (None, None)"""
        mock_resp = MagicMock()
        mock_resp.__enter__.return_value = mock_resp
        mock_resp.read.return_value = json.dumps({
            "query": {
                "pages": {
                    "-1": {"title": "不存在", "extract": ""},
                }
            }
        }).encode("utf-8")

        with patch.object(urllib.request, "urlopen", return_value=mock_resp):
            title, summary = plugin_without_kb._fetch_wikipedia("不存在", "zh")
        assert title is None
        assert summary is None

    def test_fetch_wikipedia_network_error(self, plugin_without_kb):
        """_fetch_wikipedia — URLError 时返回 (None, None)"""
        with patch.object(urllib.request, "urlopen", side_effect=Exception("network error")):
            title, summary = plugin_without_kb._fetch_wikipedia("儒家", "zh")
        assert title is None
        assert summary is None

    def test_fetch_wikipedia_json_decode_error(self, plugin_without_kb):
        """_fetch_wikipedia — 无效 JSON 时返回 (None, None)"""
        mock_resp = MagicMock()
        mock_resp.__enter__.return_value = mock_resp
        mock_resp.read.return_value = b"not valid json {{{"

        with patch.object(urllib.request, "urlopen", return_value=mock_resp):
            title, summary = plugin_without_kb._fetch_wikipedia("儒家", "zh")
        assert title is None
        assert summary is None


# ── sync_from_wikipedia 成功路径 ──────────────────────────────────────────────

class TestSyncWikipediaSuccess:
    """测试 sync_from_wikipedia 成功路径（mock 网络）"""

    def test_sync_from_wikipedia_success(self, plugin_with_kb, mock_kb):
        """sync_from_wikipedia — mock _fetch_wikipedia，验证 add_node 被调用"""
        with patch.object(plugin_with_kb, "_fetch_wikipedia",
                          return_value=("儒家", "儒家思想摘要")):
            result = plugin_with_kb.sync_from_wikipedia(["儒家"])
        assert result["synced"] == 1
        assert result["failed"] == 0
        assert result["details"][0]["status"] == "ok"
        assert result["details"][0]["title"] == "儒家"
        assert len(mock_kb.nodes) == 1
        assert mock_kb.nodes[0]["node_id"] == "Wikipedia:儒家"
        assert mock_kb.nodes[0]["node_type"] == "wikipedia"
        assert mock_kb.nodes[0]["properties"]["source"] == "Wikipedia"

    def test_sync_from_wikipedia_empty_title(self, plugin_with_kb, mock_kb):
        """sync_from_wikipedia — _fetch_wikipedia 返回 (None, None) 时计为 failed"""
        with patch.object(plugin_with_kb, "_fetch_wikipedia",
                          return_value=(None, None)):
            result = plugin_with_kb.sync_from_wikipedia(["儒家"])
        assert result["synced"] == 0
        assert result["failed"] == 1
        assert result["details"][0]["status"] == "empty"
        assert mock_kb.nodes == []

    def test_sync_from_wikipedia_empty_summary(self, plugin_with_kb, mock_kb):
        """sync_from_wikipedia — _fetch_wikipedia 返回 title 但 summary 为 None"""
        with patch.object(plugin_with_kb, "_fetch_wikipedia",
                          return_value=("儒家", None)):
            result = plugin_with_kb.sync_from_wikipedia(["儒家"])
        assert result["synced"] == 0
        assert result["failed"] == 1
        assert mock_kb.nodes == []

    def test_sync_from_wikipedia_custom_language(self, plugin_with_kb, mock_kb):
        """sync_from_wikipedia — 自定义 language='en' 时 URL 使用 en.wikipedia.org"""
        with patch.object(plugin_with_kb, "_fetch_wikipedia") as mock_fetch:
            mock_fetch.return_value = ("Confucianism", "Confucianism summary...")
            plugin_with_kb.sync_from_wikipedia(["Confucianism"], language="en")
            mock_fetch.assert_called_once_with("Confucianism", "en")

    def test_sync_from_wikipedia_empty_topics(self, plugin_with_kb):
        """sync_from_wikipedia — 空 topics 列表返回 0,0"""
        result = plugin_with_kb.sync_from_wikipedia([])
        assert result["synced"] == 0
        assert result["failed"] == 0
        assert result["details"] == []


# ── _fetch_baidu_baike ──────────────────────────────────────────────────────

class TestFetchBaiduBaike:
    """测试 _fetch_baidu_baike 内部方法"""

    def test_fetch_baidu_baike_success(self, plugin_without_kb):
        """_fetch_baidu_baike — mock 返回有效 JSON"""
        mock_resp = MagicMock()
        mock_resp.__enter__.return_value = mock_resp
        mock_resp.read.return_value = json.dumps({
            "abstract": "儒家思想核心内容...",
            "url": "https://baike.baidu.com/item/儒家",
        }).encode("utf-8")

        with patch.object(urllib.request, "urlopen", return_value=mock_resp):
            entry = plugin_without_kb._fetch_baidu_baike("儒家")
        assert entry is not None
        assert entry["abstract"] == "儒家思想核心内容..."
        assert entry["url"] == "https://baike.baidu.com/item/儒家"

    def test_fetch_baidu_baike_network_error(self, plugin_without_kb):
        """_fetch_baidu_baike — URLError 时返回 None"""
        with patch.object(urllib.request, "urlopen", side_effect=Exception("network error")):
            entry = plugin_without_kb._fetch_baidu_baike("儒家")
        assert entry is None


# ── sync_from_baidu_baike 成功路径 ────────────────────────────────────────────

class TestSyncBaiduBaikeSuccess:
    """测试 sync_from_baidu_baike 成功路径（mock 网络）"""

    def test_sync_from_baidu_baike_success(self, plugin_with_kb, mock_kb):
        """sync_from_baidu_baike — mock _fetch_baidu_baike，验证 add_node 被调用"""
        with patch.object(plugin_with_kb, "_fetch_baidu_baike",
                          return_value={"abstract": "摘要内容", "url": "http://example.com"}):
            result = plugin_with_kb.sync_from_baidu_baike(["儒家"])
        assert result["synced"] == 1
        assert result["failed"] == 0
        assert result["details"][0]["status"] == "ok"
        assert len(mock_kb.nodes) == 1
        assert mock_kb.nodes[0]["node_id"] == "百度百科:儒家"
        assert mock_kb.nodes[0]["node_type"] == "baidu_baike"
        assert mock_kb.nodes[0]["properties"]["source"] == "百度百科"

    def test_sync_from_baidu_baike_empty_topics(self, plugin_with_kb):
        """sync_from_baidu_baike — 空 topics 列表返回 0,0"""
        result = plugin_with_kb.sync_from_baidu_baike([])
        assert result["synced"] == 0
        assert result["failed"] == 0
        assert result["details"] == []


# ── sync_from_classics (kb=None) ─────────────────────────────────────────────

class TestSyncClassicsExtended:
    """测试 sync_from_classics 边界情况"""

    def test_sync_from_classics_without_kb(self, plugin_without_kb):
        """sync_from_classics — kb=None 时返回结构化结果，details 为空"""
        result = plugin_without_kb.sync_from_classics(["易经", "论语"])
        assert result["synced"] == 0
        assert result["failed"] == 0
        assert result["details"] == []


# ── sync_all with kb ─────────────────────────────────────────────────────────

class TestSyncAllWithKb:
    """测试 sync_all 带 kb 的情况"""

    def test_sync_all_with_kb(self, plugin_with_kb, mock_kb):
        """sync_all — 有 kb 时 3 个数据源都被调用"""
        with patch.object(plugin_with_kb, "sync_from_wikipedia",
                          return_value={"synced": 1, "failed": 0, "details": []}) as mock_wiki, \
             patch.object(plugin_with_kb, "sync_from_baidu_baike",
                          return_value={"synced": 1, "failed": 0, "details": []}) as mock_baidu, \
             patch.object(plugin_with_kb, "sync_from_classics",
                          return_value={"synced": 7, "failed": 0, "details": []}) as mock_classics:
            result = plugin_with_kb.sync_all()
        assert set(result.keys()) == {"wikipedia", "baidu_baike", "classics"}
        mock_wiki.assert_called_once()
        mock_baidu.assert_called_once()
        mock_classics.assert_called_once()


class TestSyncWikipediaException:
    """sync_from_wikipedia — _fetch_wikipedia 抛出异常"""

    def test_sync_from_wikipedia_exception(self, plugin_with_kb):
        """_fetch_wikipedia 抛出异常时，记录失败"""
        with patch.object(plugin_with_kb, "_fetch_wikipedia", side_effect=RuntimeError("boom")):
            result = plugin_with_kb.sync_from_wikipedia(["test"])
        assert result["synced"] == 0
        assert result["failed"] == 1
        assert result["details"][0]["status"] == "boom"


class TestSyncBaiduBaikeException:
    """sync_from_baidu_baike — _fetch_baidu_baike 抛出异常"""

    def test_sync_from_baidu_baike_exception(self, plugin_with_kb):
        """_fetch_baidu_baike 抛出异常时，记录失败"""
        with patch.object(plugin_with_kb, "_fetch_baidu_baike", side_effect=RuntimeError("boom")):
            result = plugin_with_kb.sync_from_baidu_baike(["test"])
        assert result["synced"] == 0
        assert result["failed"] == 1
        assert result["details"][0]["status"] == "boom"