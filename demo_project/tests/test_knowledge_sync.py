"""Tests for tengod.正财_知识固化.knowledge_sync.

Focus:
  * Sync orchestration (wikipedia / baike / classics / all) with and without KB
  * Edge paths: empty responses, network failures, missing topics
  * History tracking
"""

from __future__ import annotations

import json
import sys
from typing import Any, Dict, List, Optional
from unittest.mock import patch

import pytest

sys.path.insert(0, "..")

from tengod.正财_知识固化.knowledge_sync import KnowledgeSyncPlugin


# ---------------------------------------------------------------------------
# Test double for a knowledge base (only needs add_node)
# ---------------------------------------------------------------------------


class FakeKB:
    def __init__(self, fail_on_add: bool = False):
        self.nodes: List[Dict[str, Any]] = []
        self.fail_on_add = fail_on_add

    def add_node(self, name: str, node_type: str = "", properties: Optional[Dict] = None):
        if self.fail_on_add:
            raise RuntimeError("KB is broken")
        self.nodes.append(
            {"name": name, "node_type": node_type, "properties": properties or {}}
        )
        return True


# ---------------------------------------------------------------------------
# Wikipedia sync
# ---------------------------------------------------------------------------


class TestWikipediaSync:
    def test_empty_wikipedia_response_recorded_as_empty(self):
        plugin = KnowledgeSyncPlugin(kb=FakeKB())
        with patch.object(plugin, "_fetch_wikipedia", return_value=(None, None)):
            res = plugin.sync_from_wikipedia(["儒家"])
        assert res["synced"] == 0
        assert res["failed"] == 1
        assert res["details"][0]["status"] == "empty"

    def test_fetch_error_recorded_as_failed(self):
        plugin = KnowledgeSyncPlugin(kb=FakeKB())

        def boom(topic, lang):
            raise RuntimeError("network")

        with patch.object(plugin, "_fetch_wikipedia", side_effect=boom):
            res = plugin.sync_from_wikipedia(["儒家", "道家"])
        assert res["synced"] == 0
        assert res["failed"] == 2
        assert all(d["status"] != "ok" for d in res["details"])

    def test_successful_sync_adds_node(self):
        kb = FakeKB()
        plugin = KnowledgeSyncPlugin(kb=kb)
        with patch.object(
            plugin,
            "_fetch_wikipedia",
            return_value=("儒家", "儒家思想介绍……" * 10),
        ):
            res = plugin.sync_from_wikipedia(["儒家"])
        assert res["synced"] == 1
        assert len(kb.nodes) == 1
        node = kb.nodes[0]
        assert node["name"] == "Wikipedia:儒家"
        assert node["node_type"] == "wikipedia"
        assert node["properties"]["language"] == "zh"
        assert node["properties"]["source"] == "Wikipedia"

    def test_summary_truncated_to_500_chars(self):
        kb = FakeKB()
        plugin = KnowledgeSyncPlugin(kb=kb)
        long_summary = "文" * 1000
        with patch.object(
            plugin, "_fetch_wikipedia", return_value=("儒家", long_summary)
        ):
            plugin.sync_from_wikipedia(["儒家"])
        assert len(kb.nodes[0]["properties"]["summary"]) == 500

    def test_no_kb_returns_empty_results_but_no_crash(self):
        plugin = KnowledgeSyncPlugin(kb=None)
        with patch.object(
            plugin,
            "_fetch_wikipedia",
            return_value=("儒家", "summary"),
        ):
            res = plugin.sync_from_wikipedia(["儒家"])
        # With no KB, fetch is still attempted but no node is added
        assert res["synced"] == 0
        assert res["failed"] == 1

    def test_multiple_topics_partial_success(self):
        kb = FakeKB()
        plugin = KnowledgeSyncPlugin(kb=kb)
        responses = iter(
            [
                ("儒家", "summary"),
                (None, None),  # empty result
                ("法家", "summary2"),
            ]
        )
        with patch.object(plugin, "_fetch_wikipedia", side_effect=lambda *a, **k: next(responses)):
            res = plugin.sync_from_wikipedia(["儒家", "道家", "法家"])
        assert res["synced"] == 2
        assert res["failed"] == 1

    def test_history_recorded_after_sync(self):
        plugin = KnowledgeSyncPlugin(kb=FakeKB())
        with patch.object(plugin, "_fetch_wikipedia", return_value=("X", "y")):
            plugin.sync_from_wikipedia(["X"])
        history = plugin.get_history()
        assert len(history) == 1
        assert history[0]["source"] == "wikipedia"
        assert "results" in history[0]


# ---------------------------------------------------------------------------
# _fetch_wikipedia: real API response parsing
# ---------------------------------------------------------------------------


class TestFetchWikipedia:
    def test_valid_page_parsed(self):
        plugin = KnowledgeSyncPlugin()
        payload = {
            "query": {
                "pages": {
                    "123": {
                        "pageid": 123,
                        "title": "儒家",
                        "extract": "儒家思想",
                    }
                }
            }
        }
        with patch(
            "urllib.request.urlopen",
        ) as mock_open:
            import io
            mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(payload).encode("utf-8")
            title, summary = plugin._fetch_wikipedia("儒家")
        assert title == "儒家"
        assert summary == "儒家思想"

    def test_missing_page_id_minus_one(self):
        plugin = KnowledgeSyncPlugin()
        payload = {"query": {"pages": {"-1": {"title": "Not Found"}}}}
        with patch("urllib.request.urlopen") as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(payload).encode()
            title, summary = plugin._fetch_wikipedia("儒家")
        assert title is None
        assert summary is None

    def test_network_error_handled(self):
        plugin = KnowledgeSyncPlugin()
        with patch("urllib.request.urlopen", side_effect=ConnectionError("boom")):
            title, summary = plugin._fetch_wikipedia("儒家")
        assert title is None
        assert summary is None


# ---------------------------------------------------------------------------
# Baidu Baike sync
# ---------------------------------------------------------------------------


class TestBaiduBaikeSync:
    def test_empty_fetch_recorded_as_failed(self):
        plugin = KnowledgeSyncPlugin(kb=FakeKB())
        with patch.object(plugin, "_fetch_baidu_baike", return_value=None):
            res = plugin.sync_from_baidu_baike(["儒家"])
        assert res["failed"] == 1
        assert res["synced"] == 0

    def test_successful_fetch_adds_node(self):
        kb = FakeKB()
        plugin = KnowledgeSyncPlugin(kb=kb)
        entry = {"abstract": "百科摘要……", "url": "http://baike/foo"}
        with patch.object(plugin, "_fetch_baidu_baike", return_value=entry):
            res = plugin.sync_from_baidu_baike(["儒家"])
        assert res["synced"] == 1
        assert len(kb.nodes) == 1
        assert kb.nodes[0]["name"] == "百度百科:儒家"

    def test_fetch_exception_recorded(self):
        plugin = KnowledgeSyncPlugin(kb=FakeKB())
        with patch.object(
            plugin, "_fetch_baidu_baike", side_effect=RuntimeError("net")
        ):
            res = plugin.sync_from_baidu_baike(["儒家"])
        assert res["failed"] == 1

    def test_network_error_in_fetch(self):
        plugin = KnowledgeSyncPlugin()
        with patch("urllib.request.urlopen", side_effect=ConnectionError()):
            entry = plugin._fetch_baidu_baike("儒家")
        assert entry is None


# ---------------------------------------------------------------------------
# Classics sync
# ---------------------------------------------------------------------------


class TestClassicsSync:
    def test_default_classics_synced(self):
        kb = FakeKB()
        plugin = KnowledgeSyncPlugin(kb=kb)
        res = plugin.sync_from_classics()
        assert res["synced"] == 7
        assert res["failed"] == 0
        assert len(kb.nodes) == 7
        titles = {n["properties"]["title"] for n in kb.nodes}
        assert "易经" in titles
        assert "道德经" in titles

    def test_missing_classic_recorded_as_failed(self):
        kb = FakeKB()
        plugin = KnowledgeSyncPlugin(kb=kb)
        res = plugin.sync_from_classics(["易经", "不存在的经典"])
        assert res["synced"] == 1
        assert res["failed"] == 1
        assert any(d["classic"] == "不存在的经典" and d["status"] == "not found" for d in res["details"])

    def test_classics_without_kb_still_recorded(self):
        plugin = KnowledgeSyncPlugin(kb=None)
        res = plugin.sync_from_classics(["易经"])
        # Without KB, "synced" cannot happen because node creation is gated
        # on self._kb. The classic is skipped silently (neither synced nor
        # failed), matching the implementation's current behavior.
        assert res["synced"] == 0
        assert res["failed"] == 0
        assert res["details"] == []

    def test_classic_data_metadata(self):
        plugin = KnowledgeSyncPlugin()
        data = plugin._get_classic_data()
        assert "author" in data["易经"]
        assert "summary" in data["论语"]

    def test_set_knowledge_base_swapped(self):
        plugin = KnowledgeSyncPlugin()
        assert plugin._kb is None
        kb = FakeKB()
        plugin.set_knowledge_base(kb)
        assert plugin._kb is kb


# ---------------------------------------------------------------------------
# sync_all orchestration
# ---------------------------------------------------------------------------


class TestSyncAll:
    def test_sync_all_invokes_all_sources(self):
        plugin = KnowledgeSyncPlugin(kb=FakeKB())
        with patch.object(plugin, "sync_from_wikipedia", return_value={"synced": 0, "failed": 0, "details": []}), \
             patch.object(plugin, "sync_from_baidu_baike", return_value={"synced": 0, "failed": 0, "details": []}), \
             patch.object(plugin, "sync_from_classics", return_value={"synced": 0, "failed": 0, "details": []}):
            res = plugin.sync_all()
        assert "wikipedia" in res
        assert "baidu_baike" in res
        assert "classics" in res
