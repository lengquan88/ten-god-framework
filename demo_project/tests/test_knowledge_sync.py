"""tests/test_knowledge_sync.py — 知识库同步插件测试

测试覆盖：
- 初始化（有/无 kb）
- set_knowledge_base()
- 网络同步方法（Wikipedia / 百度百科）在离线环境下的优雅降级
- 古籍同步（内置数据）
- sync_all() / get_history()
- 经典数据完整性
"""
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