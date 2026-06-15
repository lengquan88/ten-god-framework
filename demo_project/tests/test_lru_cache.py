"""test_lru_cache.py — 知识库缓存层测试 v2.1.0"""
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tengod"))

from 正财_知识固化.lru_cache import LRUCache, KnowledgeCache


class TestLRUCacheBasic:
    def test_set_and_get(self):
        cache = LRUCache(max_size=10)
        cache.set("key1", "value1")
        value, hit = cache.get("key1")
        assert value == "value1"
        assert hit is True

    def test_get_miss(self):
        cache = LRUCache(max_size=10)
        value, hit = cache.get("nonexistent")
        assert value is None
        assert hit is False

    def test_contains(self):
        cache = LRUCache(max_size=10)
        cache.set("a", 1)
        assert cache.contains("a") is True
        assert cache.contains("b") is False

    def test_delete(self):
        cache = LRUCache(max_size=10)
        cache.set("a", 1)
        assert cache.delete("a") is True
        assert cache.contains("a") is False
        assert cache.delete("a") is False

    def test_clear(self):
        cache = LRUCache(max_size=10)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.clear()
        assert cache.size() == 0

    def test_size(self):
        cache = LRUCache(max_size=10)
        assert cache.size() == 0
        cache.set("a", 1)
        cache.set("b", 2)
        assert cache.size() == 2


class TestLRUCacheTTL:
    def test_ttl_expiry(self):
        cache = LRUCache(max_size=10, default_ttl=0.1)
        cache.set("a", 1)
        assert cache.contains("a") is True
        time.sleep(0.15)
        assert cache.contains("a") is False
        value, hit = cache.get("a")
        assert value is None
        assert hit is False

    def test_custom_ttl(self):
        cache = LRUCache(max_size=10, default_ttl=300)
        cache.set("short", "v", ttl=0.1)
        cache.set("long", "v", ttl=300)
        time.sleep(0.15)
        assert cache.contains("short") is False
        assert cache.contains("long") is True

    def test_ttl_not_expired(self):
        cache = LRUCache(max_size=10, default_ttl=300)
        cache.set("a", 1)
        value, hit = cache.get("a")
        assert value == 1
        assert hit is True


class TestLRUCacheEviction:
    def test_lru_eviction(self):
        cache = LRUCache(max_size=3)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        cache.set("d", 4)  # 应淘汰 a
        assert cache.contains("a") is False
        assert cache.contains("b") is True
        assert cache.contains("c") is True
        assert cache.contains("d") is True

    def test_lru_access_bumps(self):
        cache = LRUCache(max_size=3)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        cache.get("a")  # 访问 a，提升到最近使用
        cache.set("d", 4)  # 应淘汰 b（最久未使用）
        assert cache.contains("a") is True
        assert cache.contains("b") is False
        assert cache.contains("c") is True
        assert cache.contains("d") is True


class TestLRUCacheStats:
    def test_stats(self):
        cache = LRUCache(max_size=100, default_ttl=300)
        cache.set("a", 1)
        cache.set("b", 2)
        s = cache.stats()
        assert s["size"] == 2
        assert s["max_size"] == 100
        assert s["default_ttl"] == 300


class TestLRUCacheThreadSafety:
    def test_concurrent_access(self):
        import threading

        cache = LRUCache(max_size=1000)
        errors = []

        def worker(start: int):
            try:
                for i in range(start, start + 100):
                    cache.set(f"key{i}", i)
                    cache.get(f"key{i}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i * 100,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        # 可能有少量被淘汰，但至少大部分应该还在
        assert cache.size() > 0


class TestKnowledgeCache:
    def test_node_cache(self):
        cache = KnowledgeCache()
        cache.set_node("n1", {"name": "test"})
        value, hit = cache.get_node("n1")
        assert value == {"name": "test"}
        assert hit is True

    def test_node_cache_miss(self):
        cache = KnowledgeCache()
        value, hit = cache.get_node("n99")
        assert value is None
        assert hit is False

    def test_query_cache(self):
        cache = KnowledgeCache()
        cache.set_query("search term", [{"id": 1}])
        value, hit = cache.get_query("search term")
        assert value == [{"id": 1}]
        assert hit is True

    def test_query_cache_with_filters(self):
        cache = KnowledgeCache()
        cache.set_query("search", ["r1"], filters={"type": "philosophy"})
        value, hit = cache.get_query("search", filters={"type": "philosophy"})
        assert value == ["r1"]
        assert hit is True

        # 不同过滤条件应不同
        value2, hit2 = cache.get_query("search", filters={"type": "tech"})
        assert hit2 is False

    def test_type_cache(self):
        cache = KnowledgeCache()
        cache.set_by_type("philosophy", ["儒家", "道家"])
        value, hit = cache.get_by_type("philosophy")
        assert value == ["儒家", "道家"]
        assert hit is True

    def test_invalidate_node(self):
        cache = KnowledgeCache()
        cache.set_node("n1", {"data": 1})
        cache.invalidate_node("n1")
        value, hit = cache.get_node("n1")
        assert value is None
        assert hit is False

    def test_invalidate_all(self):
        cache = KnowledgeCache()
        cache.set_node("n1", {})
        cache.set_node("n2", {})
        cache.set_query("q", [])
        cache.invalidate_all()
        assert cache.get_node("n1") == (None, False)
        assert cache.get_node("n2") == (None, False)
        assert cache.get_query("q") == (None, False)

    def test_stats(self):
        cache = KnowledgeCache()
        cache.set_node("n1", {})
        cache.get_node("n1")  # hit
        cache.get_node("n2")  # miss
        s = cache.stats()
        assert s["hits"] == 1
        assert s["misses"] == 1
        assert s["total_requests"] == 2
        assert s["hit_rate"] == 0.5