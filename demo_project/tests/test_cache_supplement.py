#!/usr/bin/env python3
"""
test_cache_supplement.py — 缓存层补充测试 v4.6.0
==================================================
针对 cache.py 中高风险边界条件的补充测试：
- 过期计数与淘汰计数的精确性
- get_or_set 异常传播
- 内存估算边缘情况
- dunder 方法 (__len__, __contains__)
- 零 TTL 即时过期
- 连续淘汰行为
- TieredCache 统计一致性
- 空缓存 stats
- 覆盖写入的 LRU 顺序
"""

import time

import pytest

from tengod.cache import Cache, TieredCache, CacheEntry


# ============================================================================
# 一、Cache — 计数精确性
# ============================================================================

class TestCacheCounters:
    """缓存计数器精确性测试"""

    def test_miss_counter(self):
        """未命中计数正确"""
        cache = Cache(max_size=10, ttl=60)
        cache.get("a")
        cache.get("b")
        stats = cache.stats()
        assert stats["misses"] == 2
        assert stats["hits"] == 0

    def test_hit_counter(self):
        """命中计数正确"""
        cache = Cache(max_size=10, ttl=60)
        cache.set("a", 1)
        cache.get("a")
        cache.get("a")
        stats = cache.stats()
        assert stats["hits"] == 2
        assert stats["misses"] == 0

    def test_hit_rate_zero_total(self):
        """零请求时命中率为 0，不除零"""
        cache = Cache(max_size=10, ttl=60)
        stats = cache.stats()
        assert stats["hit_rate"] == 0.0

    def test_hit_rate_calculation(self):
        """命中率计算正确"""
        cache = Cache(max_size=10, ttl=60)
        cache.set("a", 1)
        cache.get("a")  # hit
        cache.get("a")  # hit
        cache.get("b")  # miss
        stats = cache.stats()
        assert stats["hit_rate"] == pytest.approx(2 / 3, abs=0.01)

    def test_eviction_counter(self):
        """淘汰计数正确"""
        cache = Cache(max_size=3, ttl=600)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        cache.set("d", 4)  # evict a
        cache.set("e", 5)  # evict b
        stats = cache.stats()
        assert stats["evictions"] == 2

    def test_expiration_counter(self):
        """过期计数正确"""
        cache = Cache(max_size=10, ttl=0.01)
        cache.set("a", 1)
        cache.set("b", 2)
        time.sleep(0.02)
        cache.get("a")  # expired → miss + expirations++
        cache.get("b")  # expired → miss + expirations++
        stats = cache.stats()
        assert stats["expirations"] == 2
        assert stats["misses"] == 2

    def test_clear_resets_all_counters(self):
        """clear 重置所有计数器"""
        cache = Cache(max_size=10, ttl=60)
        cache.set("a", 1)
        cache.get("a")
        cache.get("missing")
        cache.clear()
        stats = cache.stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["evictions"] == 0
        assert stats["expirations"] == 0
        assert stats["size"] == 0


# ============================================================================
# 二、Cache — 边界条件
# ============================================================================

class TestCacheEdgeCases:
    """缓存边界条件测试"""

    def test_zero_ttl_expires_immediately(self):
        """TTL 为 0 时立即过期（因为 expires_at = time.time() + 0 = now）"""
        cache = Cache(max_size=10, ttl=0)
        cache.set("a", 1)
        # 由于 set 和 get 之间有微小时间差，应该已过期
        # 但如果执行太快可能返回值。我们用自定义 TTL=0 测试
        cache.set("b", 2, ttl=0)
        # 等一小段确保过期
        time.sleep(0.001)
        result = cache.get("b")
        assert result is None

    def test_very_long_ttl(self):
        """非常长的 TTL 不会溢出"""
        cache = Cache(max_size=10, ttl=1e9)
        cache.set("a", "value")
        assert cache.get("a") == "value"

    def test_max_size_one(self):
        """max_size=1 的极端情况"""
        cache = Cache(max_size=1, ttl=60)
        cache.set("a", 1)
        assert cache.get("a") == 1
        cache.set("b", 2)  # should evict a
        assert cache.get("a") is None
        assert cache.get("b") == 2
        assert len(cache) == 1

    def test_max_size_zero_behavior(self):
        """max_size=0 时，set 后立即被淘汰"""
        cache = Cache(max_size=0, ttl=60)
        cache.set("a", 1)
        # 设置后立即淘汰，因为 len > 0
        assert len(cache) == 0
        assert cache.get("a") is None

    def test_overwrite_existing_key(self):
        """覆盖已存在的 key 不增加 size，但更新 LRU 顺序"""
        cache = Cache(max_size=3, ttl=600)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        # 覆盖 a（应移到末尾，b 变成最老）
        cache.set("a", 10)
        # 新增 d，应淘汰 b（最久未使用）
        cache.set("d", 4)
        assert cache.get("a") == 10
        assert cache.get("b") is None
        assert cache.get("c") == 3
        assert cache.get("d") == 4

    def test_delete_nonexistent_key(self):
        """删除不存在的 key 不报错"""
        cache = Cache(max_size=10, ttl=60)
        cache.delete("nonexistent")  # should not raise

    def test_has_method(self):
        """has 方法正确性"""
        cache = Cache(max_size=10, ttl=60)
        assert cache.has("a") is False
        cache.set("a", 1)
        assert cache.has("a") is True

    def test_contains_dunder(self):
        """__contains__ 魔法方法"""
        cache = Cache(max_size=10, ttl=60)
        assert ("a" in cache) is False
        cache.set("a", 1)
        assert ("a" in cache) is True

    def test_len_dunder(self):
        """__len__ 魔法方法"""
        cache = Cache(max_size=10, ttl=60)
        assert len(cache) == 0
        cache.set("a", 1)
        cache.set("b", 2)
        assert len(cache) == 2

    def test_none_value(self):
        """value 为 None 时的行为"""
        cache = Cache(max_size=10, ttl=60)
        cache.set("key", None)
        # has / __contains__ 使用 get is not None 判断，所以 None 值会被认为不存在
        # 这是一个已知的行为特征
        assert cache.get("key") is None
        assert cache.has("key") is False
        assert ("key" in cache) is False


# ============================================================================
# 三、Cache — get_or_set 细节
# ============================================================================

class TestCacheGetOrSet:
    """get_or_set 方法细节测试"""

    def test_get_or_set_miss_calls_factory(self):
        """未命中时调用 factory"""
        cache = Cache(max_size=10, ttl=60)
        call_count = [0]

        def factory():
            call_count[0] += 1
            return "created"

        result = cache.get_or_set("k", factory)
        assert result == "created"
        assert call_count[0] == 1

    def test_get_or_set_hit_skips_factory(self):
        """命中时不调用 factory"""
        cache = Cache(max_size=10, ttl=60)
        cache.set("k", "existing")
        call_count = [0]

        def factory():
            call_count[0] += 1
            return "new"

        result = cache.get_or_set("k", factory)
        assert result == "existing"
        assert call_count[0] == 0

    def test_get_or_set_with_custom_ttl(self):
        """get_or_set 支持自定义 TTL"""
        cache = Cache(max_size=10, ttl=60)
        call_count = [0]

        def factory():
            call_count[0] += 1
            return "val"

        result = cache.get_or_set("k", factory, ttl=0.01)
        assert result == "val"
        time.sleep(0.02)
        # 过期后应再次调用 factory
        result2 = cache.get_or_set("k", factory, ttl=0.01)
        assert result2 == "val"
        assert call_count[0] == 2

    def test_get_or_set_factory_raises(self):
        """factory 抛出异常时，异常传播且不缓存"""
        cache = Cache(max_size=10, ttl=60)

        def failing_factory():
            raise ValueError("factory failed")

        with pytest.raises(ValueError, match="factory failed"):
            cache.get_or_set("k", failing_factory)

        # 未缓存任何内容
        assert cache.get("k") is None
        assert len(cache) == 0


# ============================================================================
# 四、CacheEntry — 细节
# ============================================================================

class TestCacheEntryDetails:
    """CacheEntry 细节测试"""

    def test_zero_expires_means_never_expires(self):
        """expires_at=0 表示永不过期"""
        entry = CacheEntry(key="k", value="v", expires_at=0.0)
        assert entry.is_expired() is False

    def test_touch_increments_access_count(self):
        """touch 增加访问计数"""
        entry = CacheEntry(key="k", value="v")
        assert entry.access_count == 0
        entry.touch()
        assert entry.access_count == 1
        entry.touch()
        assert entry.access_count == 2

    def test_touch_updates_last_accessed(self):
        """touch 更新最后访问时间"""
        entry = CacheEntry(key="k", value="v")
        first = entry.last_accessed
        time.sleep(0.001)
        entry.touch()
        assert entry.last_accessed > first


# ============================================================================
# 五、Cache — 内存估算
# ============================================================================

class TestMemoryEstimate:
    """内存估算测试"""

    def test_estimate_memory_basic(self):
        """基本内存估算"""
        cache = Cache(max_size=10, ttl=60)
        cache.set("a", "hello")
        cache.set("b", "world")
        stats = cache.stats()
        assert "memory_estimate" in stats
        assert stats["memory_estimate"] > 0

    def test_estimate_memory_empty(self):
        """空缓存内存估算为 0"""
        cache = Cache(max_size=10, ttl=60)
        assert cache.stats()["memory_estimate"] == 0

    def test_estimate_memory_with_numeric(self):
        """数值类型的内存估算"""
        cache = Cache(max_size=10, ttl=60)
        cache.set("a", 42)
        stats = cache.stats()
        assert stats["memory_estimate"] > 0

    def test_estimate_memory_with_dict(self):
        """字典值的内存估算"""
        cache = Cache(max_size=10, ttl=60)
        cache.set("a", {"key": "value", "nested": {"x": 1}})
        stats = cache.stats()
        assert stats["memory_estimate"] > 0

    def test_estimate_memory_exception_fallback(self):
        """当 str(value) 抛异常时使用默认 64 字节"""
        class BadStr:
            def __str__(self):
                raise RuntimeError("can't str")

        cache = Cache(max_size=10, ttl=60)
        cache.set("a", BadStr())
        stats = cache.stats()
        # 使用默认 64 字节回退
        assert stats["memory_estimate"] == 64


# ============================================================================
# 六、TieredCache — 补充测试
# ============================================================================

class TestTieredCacheSupplement:
    """分层缓存补充测试"""

    def test_stats_total_counts(self):
        """stats 中 total_hits 和 total_misses 是 L1+L2 之和"""
        tc = TieredCache(l1_max=5, l1_ttl=60, l2_max=10, l2_ttl=600)
        tc.set("a", 1)
        tc.set("b", 2)
        tc.get("a")  # L1 hit
        tc.l1.clear()
        tc.get("a")  # L2 hit (promoted to L1)
        tc.get("c")  # miss both

        stats = tc.stats()
        assert stats["total_hits"] == stats["l1"]["hits"] + stats["l2"]["hits"]
        assert stats["total_misses"] == stats["l1"]["misses"] + stats["l2"]["misses"]

    def test_delete_removes_from_both_tiers(self):
        """delete 从两层都删除"""
        tc = TieredCache(l1_max=5, l1_ttl=60, l2_max=10, l2_ttl=600)
        tc.set("a", 1)
        tc.delete("a")
        assert tc.l1.get("a") is None
        assert tc.l2.get("a") is None
        assert tc.get("a") is None

    def test_clear_clears_both_tiers(self):
        """clear 清空两层"""
        tc = TieredCache(l1_max=5, l1_ttl=60, l2_max=10, l2_ttl=600)
        tc.set("a", 1)
        tc.set("b", 2)
        tc.clear()
        assert tc.get("a") is None
        assert tc.get("b") is None
        assert len(tc.l1) == 0
        assert len(tc.l2) == 0

    def test_l2_promotion_to_l1(self):
        """L2 命中后提升到 L1"""
        tc = TieredCache(l1_max=5, l1_ttl=60, l2_max=10, l2_ttl=600)
        tc.set("a", 1)
        # 清空 L1，保留 L2
        tc.l1.clear()
        assert tc.l1.get("a") is None
        assert tc.l2.get("a") == 1

        # 通过 TieredCache get，应从 L2 提升到 L1
        result = tc.get("a")
        assert result == 1
        assert tc.l1.get("a") == 1  # 已提升

    def test_l1_eviction_independent_of_l2(self):
        """L1 淘汰不影响 L2"""
        tc = TieredCache(l1_max=2, l1_ttl=60, l2_max=10, l2_ttl=600)
        tc.set("a", 1)
        tc.set("b", 2)
        tc.set("c", 3)  # L1 evicts a, but L2 still has all three
        # L1 只保留最近 2 个
        assert len(tc.l1) == 2
        # L2 保留全部 3 个
        assert len(tc.l2) == 3
        assert tc.l2.get("a") == 1


# ============================================================================
# 七、全局缓存实例
# ============================================================================

class TestGlobalCacheInstances:
    """全局缓存实例测试"""

    def test_graph_cache_is_cache_instance(self):
        from tengod.cache import graph_cache
        assert isinstance(graph_cache, Cache)
        assert graph_cache._name == "graph"

    def test_bazi_cache_is_cache_instance(self):
        from tengod.cache import bazi_cache
        assert isinstance(bazi_cache, Cache)
        assert bazi_cache._name == "bazi"

    def test_api_cache_is_tiered(self):
        from tengod.cache import api_cache
        assert isinstance(api_cache, TieredCache)

    def test_global_caches_are_independent(self):
        """全局缓存实例相互独立"""
        from tengod.cache import graph_cache, bazi_cache
        graph_cache.set("test_key", "graph_val")
        bazi_cache.set("test_key", "bazi_val")
        assert graph_cache.get("test_key") == "graph_val"
        assert bazi_cache.get("test_key") == "bazi_val"
        # 清理
        graph_cache.delete("test_key")
        bazi_cache.delete("test_key")
