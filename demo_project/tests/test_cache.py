#!/usr/bin/env python3
"""
test_cache.py — 缓存层测试 v2.17.0
==================================
测试 LRU/TTL 缓存和分层缓存的所有功能。

用法：
    pytest tests/test_cache.py -v
"""
import time

import pytest

from tengod.cache import Cache, TieredCache, CacheEntry, graph_cache, bazi_cache, api_cache


class TestCacheEntry:
    """缓存条目"""

    def test_entry_creation(self):
        entry = CacheEntry(key="test", value=42)
        assert entry.key == "test"
        assert entry.value == 42
        assert entry.created_at > 0
        assert entry.access_count == 0

    def test_entry_expired(self):
        entry = CacheEntry(key="test", value=42, expires_at=time.time() - 10)
        assert entry.is_expired()

    def test_entry_not_expired(self):
        entry = CacheEntry(key="test", value=42, expires_at=time.time() + 3600)
        assert not entry.is_expired()

    def test_entry_touch(self):
        entry = CacheEntry(key="test", value=42)
        entry.touch()
        assert entry.access_count == 1
        assert entry.last_accessed > 0


class TestCache:
    """LRU + TTL 缓存"""

    @pytest.fixture
    def cache(self):
        return Cache(max_size=10, ttl=60.0, name="test")

    def test_set_get(self, cache):
        cache.set("key", "value")
        assert cache.get("key") == "value"

    def test_get_miss(self, cache):
        assert cache.get("nonexistent") is None

    def test_has(self, cache):
        cache.set("key", "value")
        assert cache.has("key")
        assert "key" in cache
        assert not cache.has("missing")

    def test_delete(self, cache):
        cache.set("key", "value")
        cache.delete("key")
        assert cache.get("key") is None

    def test_clear(self, cache):
        cache.set("a", 1)
        cache.set("b", 2)
        cache.clear()
        assert len(cache) == 0
        assert cache.stats()["hits"] == 0

    def test_ttl_expiry(self, cache):
        cache = Cache(max_size=10, ttl=0.01, name="test")  # 10ms TTL
        cache.set("key", "value")
        time.sleep(0.02)
        assert cache.get("key") is None

    def test_custom_ttl(self, cache):
        cache.set("key", "value", ttl=0.01)
        time.sleep(0.02)
        assert cache.get("key") is None

    def test_lru_eviction(self):
        cache = Cache(max_size=3, ttl=600)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        cache.set("d", 4)  # 应淘汰 a
        assert cache.get("a") is None
        assert cache.get("b") == 2
        assert cache.get("c") == 3
        assert cache.get("d") == 4

    def test_lru_access_updates_order(self):
        cache = Cache(max_size=3, ttl=600)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        cache.get("a")  # 访问 a，将其移到末尾
        cache.set("d", 4)  # 应淘汰 b（最久未使用）
        assert cache.get("a") == 1
        assert cache.get("b") is None
        assert cache.get("c") == 3
        assert cache.get("d") == 4

    def test_get_or_set(self, cache):
        call_count = [0]

        def factory():
            call_count[0] += 1
            return "created"

        cache = Cache(max_size=10, ttl=600, name="test")
        result = cache.get_or_set("key", factory)
        assert result == "created"
        assert call_count[0] == 1

        # 第二次调用应命中缓存
        result = cache.get_or_set("key", factory)
        assert result == "created"
        assert call_count[0] == 1  # factory 未再调用

    def test_stats(self, cache):
        cache.set("a", 1)
        cache.set("b", 2)
        cache.get("a")
        cache.get("a")
        cache.get("missing")

        stats = cache.stats()
        assert stats["name"] == "test"
        assert stats["size"] == 2
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["hit_rate"] == pytest.approx(2 / 3, abs=0.01)

    def test_thread_safety(self):
        import threading
        cache = Cache(max_size=100, ttl=600)
        results = []

        def worker(start, end):
            for i in range(start, end):
                cache.set(f"key{i}", i)
                results.append(cache.get(f"key{i}"))

        threads = [
            threading.Thread(target=worker, args=(0, 20)),
            threading.Thread(target=worker, args=(20, 40)),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(cache) == 40
        assert len(results) == 40

    def test_global_graph_cache(self):
        graph_cache.set("五行", {"name": "五行"})
        assert graph_cache.get("五行") is not None
        graph_cache.clear()

    def test_global_bazi_cache(self):
        bazi_cache.set("test", "data")
        assert bazi_cache.get("test") == "data"
        bazi_cache.clear()


class TestTieredCache:
    """分层缓存"""

    @pytest.fixture
    def cache(self):
        return TieredCache(l1_max=5, l1_ttl=60.0, l2_max=10, l2_ttl=600.0)

    def test_set_get(self, cache):
        cache.set("key", "value")
        assert cache.get("key") == "value"

    def test_l1_hit(self, cache):
        cache.set("key", "value")
        cache.get("key")  # L1 命中
        assert cache.l1.stats()["hits"] >= 1

    def test_l2_fallback(self, cache):
        cache.set("key", "value")
        cache.l1.clear()  # 清空 L1
        assert cache.get("key") == "value"  # L2 回退
        assert cache.l2.stats()["hits"] >= 1

    def test_l1_promotion(self, cache):
        cache.set("key", "value")
        cache.l1.clear()
        cache.get("key")  # L2 命中，提升到 L1
        assert cache.l1.get("key") == "value"

    def test_delete(self, cache):
        cache.set("key", "value")
        cache.delete("key")
        assert cache.get("key") is None

    def test_clear(self, cache):
        cache.set("a", 1)
        cache.set("b", 2)
        cache.clear()
        assert cache.get("a") is None
        assert cache.get("b") is None

    def test_stats(self, cache):
        cache.set("a", 1)
        cache.set("b", 2)
        cache.get("a")
        stats = cache.stats()
        assert "l1" in stats
        assert "l2" in stats
        assert stats["total_hits"] >= 0

    def test_global_api_cache(self):
        api_cache.set("test", "data")
        assert api_cache.get("test") == "data"
        api_cache.clear()