"""
cache_manager.py 综合测试
覆盖：MemoryCacheManager、EngineCacheStats、工具函数、装饰器、工厂函数、边缘情况
"""

import asyncio
import json
import os
import sys
import time
import uuid
from unittest.mock import MagicMock, patch

import pytest

from tengod.cache_manager import (
    CACHE_PREFIX,
    COMPONENT_BAZI,
    COMPONENT_GENERIC,
    ENGINE_TTL,
    CacheManager,
    EngineCacheStats,
    MemoryCacheManager,
    _engine_cache_stats,
    _hash_args,
    _make_key,
    _rate_limit_key,
    cached_bazi,
    cached_engine,
    cached_fengshui,
    cached_fusion,
    cached_qimen,
    cached_ziwei,
    get_cache_manager,
    get_engine_cache_stats,
)


# ═══════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def cm():
    """每个测试使用全新的 MemoryCacheManager 实例。"""
    return MemoryCacheManager()


@pytest.fixture
def fresh_stats():
    """每个测试使用全新的 EngineCacheStats 实例。"""
    s = EngineCacheStats()
    yield s
    s.reset()


# ═══════════════════════════════════════════════════════════════════════════
# _make_key
# ═══════════════════════════════════════════════════════════════════════════

class TestMakeKey:
    """测试 _make_key 辅助函数。"""

    def test_basic(self):
        assert _make_key("cache", "mykey") == "tengod:cache:mykey"

    def test_with_component_bazi(self):
        assert _make_key(COMPONENT_BAZI, "hash123") == "tengod:bazi:hash123"

    def test_with_empty_key(self):
        assert _make_key("comp", "") == "tengod:comp:"

    def test_with_special_chars(self):
        key = _make_key("rl", "user:中文:*/test")
        assert key.startswith("tengod:rl:")
        assert "中文" in key

    def test_with_numeric_key(self):
        assert _make_key("cache", "42") == "tengod:cache:42"

    def test_with_none_component(self):
        """None 组件应被转为字符串。"""
        result = _make_key(None, "key")  # type: ignore[arg-type]
        assert "None" in result

    def test_prefix_always_tengod(self):
        for comp in ["a", "b", "cache", "session"]:
            assert _make_key(comp, "k").startswith("tengod:")


# ═══════════════════════════════════════════════════════════════════════════
# _hash_args
# ═══════════════════════════════════════════════════════════════════════════

class TestHashArgs:
    """测试 _hash_args 辅助函数。"""

    def test_basic(self):
        h = _hash_args("hello", 42)
        assert isinstance(h, str)
        assert len(h) == 64  # SHA256 hex digest

    def test_deterministic(self):
        h1 = _hash_args("a", "b", c=3)
        h2 = _hash_args("a", "b", c=3)
        assert h1 == h2

    def test_different_args_different_hash(self):
        h1 = _hash_args(1, 2)
        h2 = _hash_args(1, 3)
        assert h1 != h2

    def test_different_kwargs_different_hash(self):
        h1 = _hash_args(x=1)
        h2 = _hash_args(x=2)
        assert h1 != h2

    def test_order_invariant_for_kwargs(self):
        h1 = _hash_args(a=1, b=2)
        h2 = _hash_args(b=2, a=1)
        assert h1 == h2

    def test_with_nested_structures(self):
        h = _hash_args({"a": [1, 2, 3]}, ["x", "y"])
        assert isinstance(h, str)
        assert len(h) == 64

    def test_with_none(self):
        h = _hash_args(None)
        assert isinstance(h, str)
        assert len(h) == 64

    def test_with_empty(self):
        h = _hash_args()
        assert isinstance(h, str)
        assert len(h) == 64

    def test_with_chinese(self):
        h1 = _hash_args("中文测试")
        h2 = _hash_args("中文测试")
        h3 = _hash_args("英文测试")
        assert h1 == h2
        assert h1 != h3

    def test_with_mixed_types(self):
        h = _hash_args(1, "hello", 3.14, True, None, [1, 2], {"k": "v"})
        assert isinstance(h, str)
        assert len(h) == 64


# ═══════════════════════════════════════════════════════════════════════════
# _rate_limit_key
# ═══════════════════════════════════════════════════════════════════════════

class TestRateLimitKey:
    """测试 _rate_limit_key 辅助函数。"""

    def test_basic(self):
        key = _rate_limit_key("user123", "/api/test")
        assert key.startswith("tengod:rl:")
        assert len(key) > len("tengod:rl:")

    def test_consistent(self):
        k1 = _rate_limit_key("user1", "/api/a")
        k2 = _rate_limit_key("user1", "/api/a")
        assert k1 == k2

    def test_different_users_different_keys(self):
        k1 = _rate_limit_key("user1", "/api/test")
        k2 = _rate_limit_key("user2", "/api/test")
        assert k1 != k2

    def test_different_endpoints_different_keys(self):
        k1 = _rate_limit_key("user1", "/api/a")
        k2 = _rate_limit_key("user1", "/api/b")
        assert k1 != k2

    def test_hashes_to_avoid_special_chars(self):
        """确保限流键经过哈希，不含原始特殊字符。"""
        key = _rate_limit_key("user:with:colons", "/api/*/wildcard")
        assert ":" not in key[len("tengod:rl:"):]  # 哈希部分不应含冒号


# ═══════════════════════════════════════════════════════════════════════════
# MemoryCacheManager —— 基础操作
# ═══════════════════════════════════════════════════════════════════════════

class TestMemoryCacheManagerBasic:
    """MemoryCacheManager get / set / delete 基础操作。"""

    def test_set_and_get_simple(self, cm):
        assert cm.set("key1", "value1") is True
        assert cm.get("key1") == "value1"

    def test_set_and_get_dict(self, cm):
        data = {"name": "张三", "age": 30, "tags": ["命理", "八字"]}
        cm.set("user", data)
        assert cm.get("user") == data

    def test_set_and_get_list(self, cm):
        cm.set("ids", [1, 2, 3, 4, 5])
        assert cm.get("ids") == [1, 2, 3, 4, 5]

    def test_set_and_get_int(self, cm):
        cm.set("count", 42)
        assert cm.get("count") == 42

    def test_set_and_get_float(self, cm):
        cm.set("pi", 3.14159)
        assert cm.get("pi") == 3.14159

    def test_set_and_get_bool(self, cm):
        cm.set("flag", True)
        assert cm.get("flag") is True
        cm.set("flag2", False)
        assert cm.get("flag2") is False

    def test_set_and_get_none(self, cm):
        """None 值可以被缓存和读取。"""
        cm.set("nothing", None)
        assert cm.get("nothing") is None

    def test_get_nonexistent(self, cm):
        """不存在的键应返回 None。"""
        assert cm.get("does_not_exist") is None

    def test_get_empty_string_key(self, cm):
        cm.set("", "empty_key_value")
        assert cm.get("") == "empty_key_value"

    def test_delete_existing(self, cm):
        cm.set("to_delete", "value")
        assert cm.delete("to_delete") is True
        assert cm.get("to_delete") is None

    def test_delete_nonexistent(self, cm):
        """删除不存在的键应返回 True（幂等）。"""
        assert cm.delete("never_set") is True

    def test_delete_twice(self, cm):
        cm.set("x", 1)
        cm.delete("x")
        assert cm.delete("x") is True  # 第二次删除也成功

    def test_overwrite(self, cm):
        cm.set("key", "old")
        cm.set("key", "new")
        assert cm.get("key") == "new"

    def test_set_with_custom_ttl(self, cm):
        cm.set("key", "value", ttl=99999)
        assert cm.get("key") == "value"

    def test_set_with_zero_ttl(self, cm):
        """TTL=0 表示永不过期。"""
        cm.set("eternal", "forever", ttl=0)
        assert cm.get("eternal") == "forever"

    def test_set_with_negative_ttl(self, cm):
        """负 TTL 也视为永不过期。"""
        cm.set("neg", "value", ttl=-1)
        assert cm.get("neg") == "value"

    def test_chinese_characters_in_key(self, cm):
        cm.set("中文键", "中文值")
        assert cm.get("中文键") == "中文值"

    def test_special_characters_in_key(self, cm):
        cm.set("key:with:colons", "v")
        assert cm.get("key:with:colons") == "v"
        cm.set("key*with*stars", "v2")
        assert cm.get("key*with*stars") == "v2"

    def test_large_value(self, cm):
        large = {"data": list(range(10000))}
        cm.set("large", large)
        assert cm.get("large") == large

    def test_type_mixing(self, cm):
        """同一缓存可以存储不同类型值。"""
        cm.set("k1", 42)
        cm.set("k2", "string")
        cm.set("k3", [1, 2, 3])
        cm.set("k4", {"a": 1})
        assert cm.get("k1") == 42
        assert cm.get("k2") == "string"
        assert cm.get("k3") == [1, 2, 3]
        assert cm.get("k4") == {"a": 1}


# ═══════════════════════════════════════════════════════════════════════════
# MemoryCacheManager —— TTL 过期
# ═══════════════════════════════════════════════════════════════════════════

class TestMemoryCacheManagerTTL:
    """MemoryCacheManager TTL 过期测试。"""

    def test_ttl_expires(self, cm):
        cm.set("short", {"x": 1}, ttl=1)
        assert cm.get("short") == {"x": 1}
        time.sleep(1.1)
        assert cm.get("short") is None

    def test_ttl_not_expired(self, cm):
        cm.set("long", "value", ttl=60)
        time.sleep(0.1)
        assert cm.get("long") == "value"

    def test_ttl_zero_never_expires(self, cm):
        cm.set("eternal", "forever", ttl=0)
        time.sleep(0.2)
        assert cm.get("eternal") == "forever"

    def test_ttl_negative_never_expires(self, cm):
        cm.set("neg", "v", ttl=-5)
        time.sleep(0.2)
        assert cm.get("neg") == "v"

    def test_multiple_ttl_values(self, cm):
        cm.set("s1", 1, ttl=1)
        cm.set("s2", 2, ttl=60)
        time.sleep(1.1)
        assert cm.get("s1") is None
        assert cm.get("s2") == 2

    @pytest.mark.asyncio
    async def test_ttl_with_asyncio_sleep(self, cm):
        """使用 asyncio.sleep 测试 TTL 过期。"""
        cm.set("async_short", "val", ttl=1)
        assert cm.get("async_short") == "val"
        await asyncio.sleep(1.1)
        assert cm.get("async_short") is None


# ═══════════════════════════════════════════════════════════════════════════
# MemoryCacheManager —— delete_pattern
# ═══════════════════════════════════════════════════════════════════════════

class TestMemoryCacheManagerDeletePattern:
    """MemoryCacheManager delete_pattern 测试。"""

    def test_delete_wildcard(self, cm):
        for i in range(5):
            cm.set(f"batch_{i}", i)
        removed = cm.delete_pattern("batch_*")
        assert removed == 5
        for i in range(5):
            assert cm.get(f"batch_{i}") is None

    def test_delete_partial_match(self, cm):
        cm.set("user_1", 1)
        cm.set("user_2", 2)
        cm.set("other", 3)
        removed = cm.delete_pattern("user_*")
        assert removed == 2
        assert cm.get("user_1") is None
        assert cm.get("user_2") is None
        assert cm.get("other") == 3

    def test_delete_no_match(self, cm):
        cm.set("a", 1)
        cm.set("b", 2)
        removed = cm.delete_pattern("z_*")
        assert removed == 0
        assert cm.get("a") == 1
        assert cm.get("b") == 2

    def test_delete_exact_pattern(self, cm):
        cm.set("exact_key", "value")
        removed = cm.delete_pattern("exact_key")
        assert removed == 1
        assert cm.get("exact_key") is None

    def test_delete_pattern_with_question_mark(self, cm):
        cm.set("ab1", 1)
        cm.set("ab2", 2)
        cm.set("abc", 3)
        # fnmatch 中 "ab?" 匹配 ab + 任意单字符（含 ab1, ab2, abc），
        # 使用 "ab[12]" 精确匹配数字
        removed = cm.delete_pattern("ab[12]")
        assert removed == 2
        assert cm.get("ab1") is None
        assert cm.get("ab2") is None
        assert cm.get("abc") == 3

    def test_delete_pattern_empty_store(self, cm):
        removed = cm.delete_pattern("*")
        assert removed == 0

    def test_delete_pattern_all(self, cm):
        cm.set("x", 1)
        cm.set("y", 2)
        cm.set("z", 3)
        removed = cm.delete_pattern("*")
        assert removed == 3
        assert cm.get("x") is None


# ═══════════════════════════════════════════════════════════════════════════
# MemoryCacheManager —— cached 装饰器
# ═══════════════════════════════════════════════════════════════════════════

class TestMemoryCacheManagerCached:
    """MemoryCacheManager cached 装饰器测试。"""

    def test_cached_basic(self, cm):
        call_count = {"n": 0}

        @cm.cached("expensive", ttl=3600)
        def expensive(x: int):
            call_count["n"] += 1
            return {"x": x, "square": x * x}

        r1 = expensive(5)
        r2 = expensive(5)
        r3 = expensive(3)
        assert r1 == r2 == {"x": 5, "square": 25}
        assert r3 == {"x": 3, "square": 9}
        assert call_count["n"] == 2

    def test_cached_with_kwargs(self, cm):
        call_count = {"n": 0}

        @cm.cached("kw", ttl=60)
        def fn(a, b=0):
            call_count["n"] += 1
            return a + b

        r1 = fn(5, b=3)
        r2 = fn(5, b=3)
        r3 = fn(5, b=4)
        assert r1 == r2 == 8
        assert r3 == 9
        assert call_count["n"] == 2

    def test_cached_with_none_result(self, cm):
        """返回 None 的函数结果不应被缓存。"""
        call_count = {"n": 0}

        @cm.cached("none_test", ttl=60)
        def returns_none():
            call_count["n"] += 1
            return None

        r1 = returns_none()
        r2 = returns_none()
        assert r1 is None
        assert r2 is None
        assert call_count["n"] == 2  # None 不被缓存，每次都会调用

    def test_cached_different_prefixes(self, cm):
        call_count = {"n": 0}

        @cm.cached("prefix_a", ttl=60)
        def fn_a(x):
            call_count["n"] += 1
            return f"a:{x}"

        @cm.cached("prefix_b", ttl=60)
        def fn_b(x):
            call_count["n"] += 1
            return f"b:{x}"

        assert fn_a(1) == "a:1"
        assert fn_b(1) == "b:1"
        assert fn_a(1) == "a:1"  # 缓存命中
        assert call_count["n"] == 2  # 不同前缀不共享缓存

    def test_cached_chinese_args(self, cm):
        call_count = {"n": 0}

        @cm.cached("chinese", ttl=60)
        def fn(name):
            call_count["n"] += 1
            return f"你好, {name}"

        r1 = fn("张三")
        r2 = fn("张三")
        assert r1 == r2 == "你好, 张三"
        assert call_count["n"] == 1


# ═══════════════════════════════════════════════════════════════════════════
# MemoryCacheManager —— 案例统计缓存
# ═══════════════════════════════════════════════════════════════════════════

class TestMemoryCacheManagerCaseStats:
    """MemoryCacheManager case_stats 测试。"""

    def test_cache_and_get_case_stats(self, cm):
        stats = {"total": 99, "tags": ["命理", "八字", "紫微"]}
        assert cm.cache_case_stats(stats, ttl=3600) is True
        loaded = cm.get_case_stats()
        assert loaded == stats

    def test_get_case_stats_empty(self, cm):
        assert cm.get_case_stats() is None

    def test_case_stats_overwrite(self, cm):
        cm.cache_case_stats({"total": 10}, ttl=3600)
        cm.cache_case_stats({"total": 20}, ttl=3600)
        assert cm.get_case_stats() == {"total": 20}


# ═══════════════════════════════════════════════════════════════════════════
# MemoryCacheManager —— 八字缓存
# ═══════════════════════════════════════════════════════════════════════════

class TestMemoryCacheManagerBazi:
    """MemoryCacheManager bazi_result 测试。"""

    def test_cache_and_get_bazi_result(self, cm):
        import hashlib
        input_hash = hashlib.sha256(b"2000-01-01-12:00").hexdigest()
        result = {"day_master": "甲木", "score": 99}
        assert cm.cache_bazi_result(input_hash, result, ttl=3600) is True
        loaded = cm.get_bazi_result(input_hash)
        assert loaded == result

    def test_get_bazi_result_nonexistent(self, cm):
        assert cm.get_bazi_result("nonexistent_hash") is None


# ═══════════════════════════════════════════════════════════════════════════
# MemoryCacheManager —— 限流
# ═══════════════════════════════════════════════════════════════════════════

class TestMemoryCacheManagerRateLimit:
    """MemoryCacheManager rate_limit 测试。"""

    def test_rate_limit_basic(self, cm):
        uid = f"user_{uuid.uuid4().hex[:8]}"
        limit, window = 3, 10
        results = [cm.rate_limit(uid, "/api/test", limit, window) for _ in range(5)]
        assert results[:3] == [True, True, True]
        assert results[3] is False
        assert results[4] is False

    def test_rate_limit_different_users(self, cm):
        """不同用户有独立配额。"""
        limit, window = 2, 10
        r1 = [cm.rate_limit("user_a", "/api/test", limit, window) for _ in range(3)]
        r2 = [cm.rate_limit("user_b", "/api/test", limit, window) for _ in range(3)]
        assert r1 == [True, True, False]
        assert r2 == [True, True, False]

    def test_rate_limit_different_endpoints(self, cm):
        """不同端点有独立配额。"""
        uid = "user1"
        limit, window = 2, 10
        r1 = [cm.rate_limit(uid, "/api/a", limit, window) for _ in range(3)]
        r2 = [cm.rate_limit(uid, "/api/b", limit, window) for _ in range(3)]
        assert r1 == [True, True, False]
        assert r2 == [True, True, False]

    def test_get_rate_limit_remaining(self, cm):
        uid = "user_rem"
        limit, window = 5, 10
        cm.rate_limit(uid, "/api/test", limit, window)
        cm.rate_limit(uid, "/api/test", limit, window)
        remaining = cm.get_rate_limit_remaining(uid, "/api/test", limit, window)
        assert remaining == 3

    def test_get_rate_limit_remaining_zero(self, cm):
        uid = "user_full"
        limit, window = 1, 10
        cm.rate_limit(uid, "/api/test", limit, window)
        remaining = cm.get_rate_limit_remaining(uid, "/api/test", limit, window)
        assert remaining == 0

    def test_get_rate_limit_remaining_nonexistent(self, cm):
        remaining = cm.get_rate_limit_remaining("new_user", "/api/test", 5, 10)
        assert remaining == 5


# ═══════════════════════════════════════════════════════════════════════════
# MemoryCacheManager —— Session
# ═══════════════════════════════════════════════════════════════════════════

class TestMemoryCacheManagerSession:
    """MemoryCacheManager session 测试。"""

    def test_cache_get_delete_session(self, cm):
        sid = f"session-{uuid.uuid4().hex}"
        data = {"user_id": 123, "name": "测试用户", "role": "admin"}
        assert cm.cache_session(sid, data, ttl=3600) is True
        assert cm.get_session(sid) == data
        cm.delete_session(sid)
        assert cm.get_session(sid) is None

    def test_get_session_nonexistent(self, cm):
        assert cm.get_session("no_such_session") is None

    def test_cache_session_overwrite(self, cm):
        sid = "session_overwrite"
        cm.cache_session(sid, {"v": 1}, ttl=3600)
        cm.cache_session(sid, {"v": 2}, ttl=3600)
        assert cm.get_session(sid) == {"v": 2}


# ═══════════════════════════════════════════════════════════════════════════
# MemoryCacheManager —— 健康检查
# ═══════════════════════════════════════════════════════════════════════════

class TestMemoryCacheManagerHealthCheck:
    """MemoryCacheManager health_check 测试。"""

    def test_health_check_returns_true(self, cm):
        assert cm.health_check() is True

    def test_health_check_always_true(self, cm):
        """内存缓存始终健康。"""
        for _ in range(10):
            assert cm.health_check() is True


# ═══════════════════════════════════════════════════════════════════════════
# get_cache_manager 工厂函数
# ═══════════════════════════════════════════════════════════════════════════

class TestGetCacheManager:
    """get_cache_manager() 工厂函数测试。"""

    def test_returns_memory_cache_manager(self):
        """无 Redis 环境变量时应返回 MemoryCacheManager。"""
        cm = get_cache_manager()
        assert isinstance(cm, MemoryCacheManager)

    def test_singleton_behavior(self):
        """多次调用返回同一实例。"""
        cm1 = get_cache_manager()
        cm2 = get_cache_manager()
        assert cm1 is cm2

    def test_get_set_works(self):
        cm = get_cache_manager()
        key = f"factory_test_{uuid.uuid4().hex}"
        cm.set(key, {"ok": True})
        assert cm.get(key) == {"ok": True}
        cm.delete(key)

    def test_health_check_works(self):
        cm = get_cache_manager()
        assert cm.health_check() is True


# ═══════════════════════════════════════════════════════════════════════════
# EngineCacheStats
# ═══════════════════════════════════════════════════════════════════════════

class TestEngineCacheStats:
    """EngineCacheStats 数据类测试。"""

    def test_initial_stats_empty(self, fresh_stats):
        stats = fresh_stats.get_stats()
        assert stats == {}

    def test_record_hit(self, fresh_stats):
        fresh_stats.record_hit("bazi")
        stats = fresh_stats.get_stats()
        assert stats["bazi"]["hits"] == 1
        assert stats["bazi"]["misses"] == 0
        assert stats["bazi"]["total"] == 1
        assert stats["bazi"]["hit_rate"] == 1.0

    def test_record_miss(self, fresh_stats):
        fresh_stats.record_miss("bazi")
        stats = fresh_stats.get_stats()
        assert stats["bazi"]["hits"] == 0
        assert stats["bazi"]["misses"] == 1
        assert stats["bazi"]["total"] == 1
        assert stats["bazi"]["hit_rate"] == 0.0

    def test_hit_rate_calculation(self, fresh_stats):
        fresh_stats.record_hit("ziwei")
        fresh_stats.record_hit("ziwei")
        fresh_stats.record_miss("ziwei")
        stats = fresh_stats.get_stats()
        assert stats["ziwei"]["hits"] == 2
        assert stats["ziwei"]["misses"] == 1
        assert stats["ziwei"]["total"] == 3
        assert stats["ziwei"]["hit_rate"] == round(2 / 3, 3)

    def test_multiple_engines(self, fresh_stats):
        fresh_stats.record_hit("bazi")
        fresh_stats.record_hit("bazi")
        fresh_stats.record_miss("bazi")
        fresh_stats.record_hit("ziwei")
        fresh_stats.record_miss("ziwei")
        stats = fresh_stats.get_stats()
        assert "bazi" in stats
        assert "ziwei" in stats
        assert stats["bazi"]["hits"] == 2
        assert stats["bazi"]["misses"] == 1
        assert stats["ziwei"]["hits"] == 1
        assert stats["ziwei"]["misses"] == 1

    def test_zero_total_hit_rate(self, fresh_stats):
        """没有记录时 hit_rate 为 0.0。"""
        # 通过 get_stats 内部计算，无记录的引擎不会被列出
        # 但如果有记录但全是 0，hit_rate = 0.0
        stats = fresh_stats.get_stats()
        assert stats == {}

    def test_reset(self, fresh_stats):
        fresh_stats.record_hit("bazi")
        fresh_stats.record_miss("bazi")
        fresh_stats.reset()
        assert fresh_stats.get_stats() == {}

    def test_hit_rate_rounding(self, fresh_stats):
        """hit_rate 保留 3 位小数。"""
        fresh_stats.record_hit("test")
        fresh_stats.record_hit("test")
        fresh_stats.record_miss("test")
        # 2/3 ≈ 0.666666..., rounded to 0.667
        stats = fresh_stats.get_stats()
        assert stats["test"]["hit_rate"] == 0.667

    def test_all_hits(self, fresh_stats):
        for _ in range(10):
            fresh_stats.record_hit("perfect")
        stats = fresh_stats.get_stats()
        assert stats["perfect"]["hit_rate"] == 1.0

    def test_all_misses(self, fresh_stats):
        for _ in range(5):
            fresh_stats.record_miss("fail")
        stats = fresh_stats.get_stats()
        assert stats["fail"]["hit_rate"] == 0.0


# ═══════════════════════════════════════════════════════════════════════════
# get_engine_cache_stats 模块级函数
# ═══════════════════════════════════════════════════════════════════════════

class TestGetEngineCacheStats:
    """get_engine_cache_stats() 模块级函数测试。"""

    def test_returns_dict(self):
        _engine_cache_stats.reset()
        result = get_engine_cache_stats()
        assert isinstance(result, dict)

    def test_tracks_hits_and_misses(self):
        _engine_cache_stats.reset()
        _engine_cache_stats.record_hit("bazi")
        _engine_cache_stats.record_miss("bazi")
        stats = get_engine_cache_stats()
        assert stats["bazi"]["hits"] == 1
        assert stats["bazi"]["misses"] == 1
        _engine_cache_stats.reset()


# ═══════════════════════════════════════════════════════════════════════════
# cached_engine 装饰器
# ═══════════════════════════════════════════════════════════════════════════

class TestCachedEngine:
    """cached_engine 装饰器测试。"""

    def setup_method(self):
        _engine_cache_stats.reset()
        # 清除单例缓存，避免跨测试泄漏
        cm = get_cache_manager()
        cm.delete_pattern("*")

    def teardown_method(self):
        _engine_cache_stats.reset()
        cm = get_cache_manager()
        cm.delete_pattern("*")

    def test_cached_engine_basic(self):
        call_count = {"n": 0}

        @cached_engine("bazi")
        def calc_bazi(birth_date):
            call_count["n"] += 1
            return {"birth": birth_date, "day_master": "甲木"}

        r1 = calc_bazi("2000-01-01")
        r2 = calc_bazi("2000-01-01")
        r3 = calc_bazi("2000-06-15")

        assert r1 == r2 == {"birth": "2000-01-01", "day_master": "甲木"}
        assert r3 == {"birth": "2000-06-15", "day_master": "甲木"}
        assert call_count["n"] == 2  # 第二次命中缓存

    def test_cached_engine_tracks_stats(self):
        @cached_engine("ziwei")
        def calc_ziwei(data):
            return {"data": data, "palace": "命宫"}

        calc_ziwei("birth_data")
        calc_ziwei("birth_data")  # 缓存命中

        stats = get_engine_cache_stats()
        assert stats["ziwei"]["hits"] == 1
        assert stats["ziwei"]["misses"] == 1
        assert stats["ziwei"]["total"] == 2

    def test_cached_engine_custom_ttl(self):
        @cached_engine("qimen", ttl=1)
        def calc_qimen(data):
            return {"data": data}

        calc_qimen("test")
        assert calc_qimen("test") == {"data": "test"}  # 缓存命中

        time.sleep(1.1)
        # TTL 过期后重新计算
        result = calc_qimen("test")
        assert result == {"data": "test"}

    def test_cached_engine_default_ttl(self):
        """使用默认 TTL（来自 ENGINE_TTL）。"""
        assert ENGINE_TTL["bazi"] == 86400

        @cached_engine("bazi")
        def calc(data):
            return {"data": data}

        calc("test")
        assert calc("test") == {"data": "test"}

    def test_cached_engine_unknown_engine(self):
        """未知引擎使用 default TTL。"""
        @cached_engine("unknown_engine")
        def calc(data):
            return {"data": data}

        calc("test")
        assert calc("test") == {"data": "test"}

    @pytest.mark.asyncio
    async def test_cached_engine_with_async_caller(self):
        """cached_engine 是同步装饰器，但在异步上下文中也可调用。"""
        @cached_engine("fengshui")
        def calc_fs(data):
            return {"data": data, "direction": "坐北朝南"}

        # 在 async 上下文中调用同步函数
        result = calc_fs("house_data")
        assert result["direction"] == "坐北朝南"


# ═══════════════════════════════════════════════════════════════════════════
# 便捷函数：cached_bazi, cached_ziwei, cached_qimen, cached_fengshui, cached_fusion
# ═══════════════════════════════════════════════════════════════════════════

class TestCachedConvenience:
    """cached_bazi / cached_ziwei / cached_qimen / cached_fengshui / cached_fusion 测试。"""

    def setup_method(self):
        _engine_cache_stats.reset()
        # 清除单例缓存，避免跨测试泄漏
        cm = get_cache_manager()
        cm.delete_pattern("*")

    def teardown_method(self):
        _engine_cache_stats.reset()
        cm = get_cache_manager()
        cm.delete_pattern("*")

    def test_cached_bazi(self):
        call_count = {"n": 0}

        @cached_bazi()
        def calc(birth):
            call_count["n"] += 1
            return {"bz": birth}

        r1 = calc("2000-01-01")
        r2 = calc("2000-01-01")
        assert r1 == r2 == {"bz": "2000-01-01"}
        assert call_count["n"] == 1

    def test_cached_bazi_custom_ttl(self):
        @cached_bazi(ttl=1)
        def calc(birth):
            return {"bz": birth}

        calc("test")
        assert calc("test") == {"bz": "test"}
        time.sleep(1.1)
        # 过期后返回新结果
        assert calc("test") == {"bz": "test"}

    def test_cached_ziwei(self):
        call_count = {"n": 0}

        @cached_ziwei()
        def calc(data):
            call_count["n"] += 1
            return {"zw": data}

        r1 = calc("birth")
        r2 = calc("birth")
        assert r1 == r2 == {"zw": "birth"}
        assert call_count["n"] == 1

    def test_cached_qimen(self):
        call_count = {"n": 0}

        @cached_qimen()
        def calc(data):
            call_count["n"] += 1
            return {"qm": data}

        r1 = calc("time_data")
        r2 = calc("time_data")
        assert r1 == r2 == {"qm": "time_data"}
        assert call_count["n"] == 1

    def test_cached_fengshui(self):
        call_count = {"n": 0}

        @cached_fengshui()
        def calc(data):
            call_count["n"] += 1
            return {"fs": data}

        r1 = calc("direction")
        r2 = calc("direction")
        assert r1 == r2 == {"fs": "direction"}
        assert call_count["n"] == 1

    def test_cached_fusion(self):
        call_count = {"n": 0}

        @cached_fusion()
        def calc(data):
            call_count["n"] += 1
            return {"fu": data}

        r1 = calc("multi_system")
        r2 = calc("multi_system")
        assert r1 == r2 == {"fu": "multi_system"}
        assert call_count["n"] == 1

    def test_convenience_functions_track_stats(self):
        @cached_bazi()
        def fn_bz(data):
            return {"engine": "bazi", "data": data}

        @cached_ziwei()
        def fn_zw(data):
            return {"engine": "ziwei", "data": data}

        fn_bz("b1")
        fn_bz("b1")  # hit
        fn_zw("z1")
        fn_zw("z1")  # hit

        stats = get_engine_cache_stats()
        assert stats["bazi"]["hits"] == 1
        assert stats["bazi"]["misses"] == 1
        assert stats["ziwei"]["hits"] == 1
        assert stats["ziwei"]["misses"] == 1


# ═══════════════════════════════════════════════════════════════════════════
# 边缘情况综合测试
# ═══════════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    """边缘情况与综合测试。"""

    def test_thread_safety_basic(self, cm):
        """基本并发写入测试（多线程同时 set/get）。"""
        import threading

        errors = []
        results = {}

        def worker(idx):
            try:
                cm.set(f"thread_{idx}", idx)
                val = cm.get(f"thread_{idx}")
                results[idx] = val
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        for i in range(20):
            assert results.get(i) == i

    def test_many_keys(self, cm):
        """大量键的读写。"""
        N = 500
        for i in range(N):
            cm.set(f"key_{i}", i)
        for i in range(N):
            assert cm.get(f"key_{i}") == i
        # 删除部分
        removed = cm.delete_pattern("key_1*")
        assert removed >= 10  # key_10 ~ key_199 中匹配 key_1*
        # 未删除的仍存在
        assert cm.get("key_0") == 0
        assert cm.get("key_200") == 200

    def test_set_then_immediate_get(self, cm):
        """写入后立即读取应命中。"""
        for i in range(100):
            cm.set(f"fast_{i}", i)
            assert cm.get(f"fast_{i}") == i

    def test_cache_manager_import(self):
        """CacheManager 类可以被导入。"""
        assert CacheManager is not None

    def test_cache_manager_init_no_redis(self):
        """CacheManager 无 Redis 时初始化不崩溃。"""
        c = CacheManager("redis://nonexistent:6379/0")
        assert c.get("any") is None
        assert c.set("any", "value") is False
        assert c.delete("any") is False
        assert c.delete_pattern("*") == 0
        assert c.health_check() is False
        assert c.cache_case_stats({}) is False
        assert c.get_case_stats() is None
        assert c.cache_bazi_result("h", {}) is False
        assert c.get_bazi_result("h") is None
        assert c.rate_limit("u", "/api", 10, 60) is True  # 降级允许
        assert c.get_rate_limit_remaining("u", "/api", 10, 60) == 10
        assert c.cache_session("s", {}) is False
        assert c.get_session("s") is None
        assert c.delete_session("s") is False

    def test_memory_cache_manager_attributes(self, cm):
        """验证 MemoryCacheManager 具有所有必要属性。"""
        assert hasattr(cm, "_store")
        assert hasattr(cm, "_lock")
        assert isinstance(cm._store, dict)

    def test_engine_ttl_constants(self):
        """验证 ENGINE_TTL 常量。"""
        assert ENGINE_TTL["bazi"] == 86400
        assert ENGINE_TTL["ziwei"] == 86400
        assert ENGINE_TTL["qimen"] == 3600
        assert ENGINE_TTL["fengshui"] == 3600
        assert ENGINE_TTL["liuyao"] == 3600
        assert ENGINE_TTL["fusion"] == 1800
        assert ENGINE_TTL["report"] == 600
        assert ENGINE_TTL["default"] == 300

    def test_cache_prefix_constant(self):
        assert CACHE_PREFIX == "tengod"

    def test_set_with_empty_dict(self, cm):
        cm.set("empty_dict", {})
        assert cm.get("empty_dict") == {}

    def test_set_with_empty_list(self, cm):
        cm.set("empty_list", [])
        assert cm.get("empty_list") == []

    def test_set_with_zero(self, cm):
        cm.set("zero", 0)
        assert cm.get("zero") == 0

    def test_set_with_false(self, cm):
        cm.set("false_val", False)
        assert cm.get("false_val") is False

    def test_delete_pattern_single_char(self, cm):
        cm.set("a", 1)
        cm.set("b", 2)
        removed = cm.delete_pattern("a")
        assert removed == 1
        assert cm.get("a") is None
        assert cm.get("b") == 2

    def test_cached_engine_with_complex_args(self, cm):
        _engine_cache_stats.reset()

        @cached_engine("fusion")
        def complex_fn(a, b, c=3):
            return {"sum": a + b + c}

        r1 = complex_fn(1, 2, c=3)
        r2 = complex_fn(1, 2, c=3)
        r3 = complex_fn(1, 2, c=4)
        assert r1 == r2 == {"sum": 6}
        assert r3 == {"sum": 7}

        _engine_cache_stats.reset()

    def test_cached_engine_preserves_function_metadata(self):
        @cached_engine("bazi")
        def my_func(data):
            """我的函数文档。"""
            return data

        assert my_func.__name__ == "my_func"
        assert my_func.__doc__ == "我的函数文档。"

    def test_memory_cached_preserves_function_metadata(self, cm):
        @cm.cached("test", ttl=60)
        def my_func(data):
            """装饰器保留元数据。"""
            return data

        assert my_func.__name__ == "my_func"
        assert my_func.__doc__ == "装饰器保留元数据。"

    @pytest.mark.asyncio
    async def test_async_ttl_expiration(self, cm):
        """异步 TTL 过期测试。"""
        cm.set("async_key", "value", ttl=1)
        assert cm.get("async_key") == "value"
        await asyncio.sleep(1.1)
        assert cm.get("async_key") is None


# ═══════════════════════════════════════════════════════════════════════════
# CacheManager —— Mock Redis 覆盖 Redis 路径
# ═══════════════════════════════════════════════════════════════════════════

def _make_mock_redis():
    """创建模拟 Redis 客户端。"""
    mock_r = MagicMock()
    mock_r.ping.return_value = True
    return mock_r


def _make_cache_manager_with_mock(mock_redis=None):
    """创建一个带有模拟 Redis 的 CacheManager。"""
    if mock_redis is None:
        mock_redis = _make_mock_redis()

    mock_redis_module = MagicMock()
    mock_redis_module.from_url.return_value = mock_redis

    with patch.dict(sys.modules, {"redis": mock_redis_module}):
        cm = CacheManager("redis://localhost:6379/0")
    return cm, mock_redis


class TestCacheManagerWithMockRedis:
    """CacheManager 使用 Mock Redis 的完整测试。"""

    def test_get_with_redis_hit(self):
        cm, mock_r = _make_cache_manager_with_mock()
        mock_r.get.return_value = b'{"key": "value"}'
        result = cm.get("test_key")
        assert result == {"key": "value"}
        mock_r.get.assert_called_once()

    def test_get_with_redis_miss(self):
        cm, mock_r = _make_cache_manager_with_mock()
        mock_r.get.return_value = None
        result = cm.get("missing_key")
        assert result is None

    def test_get_with_redis_string(self):
        """Redis 返回字符串（非 bytes）的 get 操作。"""
        cm, mock_r = _make_cache_manager_with_mock()
        mock_r.get.return_value = '{"key": "value"}'
        result = cm.get("test_key")
        assert result == {"key": "value"}

    def test_set_with_redis(self):
        cm, mock_r = _make_cache_manager_with_mock()
        result = cm.set("key", {"data": "test"}, ttl=600)
        assert result is True
        mock_r.set.assert_called_once()

    def test_delete_with_redis(self):
        cm, mock_r = _make_cache_manager_with_mock()
        result = cm.delete("key")
        assert result is True
        mock_r.delete.assert_called_once()

    def test_delete_pattern_with_redis(self):
        cm, mock_r = _make_cache_manager_with_mock()
        mock_r.scan_iter.return_value = [b"tengod:cache:user:1", b"tengod:cache:user:2"]
        mock_r.delete.return_value = 2
        result = cm.delete_pattern("user:*")
        assert result == 2

    def test_delete_pattern_with_redis_no_match(self):
        cm, mock_r = _make_cache_manager_with_mock()
        mock_r.scan_iter.return_value = []
        result = cm.delete_pattern("nonexistent:*")
        assert result == 0

    def test_cached_decorator_with_redis(self):
        cm, mock_r = _make_cache_manager_with_mock()
        mock_r.get.return_value = None  # 首次未命中

        call_count = {"n": 0}

        @cm.cached("test", ttl=60)
        def fn(x):
            call_count["n"] += 1
            return {"result": x}

        r = fn(42)
        assert r == {"result": 42}
        assert call_count["n"] == 1
        # 验证 set 被调用
        mock_r.set.assert_called_once()

    def test_cached_decorator_with_redis_hit(self):
        cm, mock_r = _make_cache_manager_with_mock()
        mock_r.get.return_value = b'{"cached": true}'

        call_count = {"n": 0}

        @cm.cached("test", ttl=60)
        def fn(x):
            call_count["n"] += 1
            return {"result": x}

        r = fn(42)
        assert r == {"cached": True}
        assert call_count["n"] == 0  # 缓存命中，不调用原函数

    def test_cache_case_stats_with_redis(self):
        cm, mock_r = _make_cache_manager_with_mock()
        result = cm.cache_case_stats({"total": 100}, ttl=3600)
        assert result is True
        mock_r.set.assert_called_once()

    def test_get_case_stats_with_redis(self):
        cm, mock_r = _make_cache_manager_with_mock()
        mock_r.get.return_value = json.dumps({"total": 100, "tags": ["命理"]}).encode()
        result = cm.get_case_stats()
        assert result == {"total": 100, "tags": ["命理"]}

    def test_get_case_stats_with_redis_none(self):
        cm, mock_r = _make_cache_manager_with_mock()
        mock_r.get.return_value = None
        result = cm.get_case_stats()
        assert result is None

    def test_cache_bazi_result_with_redis(self):
        cm, mock_r = _make_cache_manager_with_mock()
        result = cm.cache_bazi_result("hash123", {"day_master": "甲木"}, ttl=86400)
        assert result is True
        mock_r.set.assert_called_once()

    def test_get_bazi_result_with_redis(self):
        cm, mock_r = _make_cache_manager_with_mock()
        mock_r.get.return_value = json.dumps({"day_master": "甲木", "score": 99}).encode()
        result = cm.get_bazi_result("hash123")
        assert result == {"day_master": "甲木", "score": 99}

    def test_get_bazi_result_with_redis_none(self):
        cm, mock_r = _make_cache_manager_with_mock()
        mock_r.get.return_value = None
        result = cm.get_bazi_result("no_hash")
        assert result is None

    def test_rate_limit_with_redis_allow(self):
        cm, mock_r = _make_cache_manager_with_mock()
        # 模拟 pipeline
        mock_pipe = MagicMock()
        mock_pipe.execute.return_value = (0, 0, 1, 1)  # zcard = 1, limit = 10
        mock_r.pipeline.return_value = mock_pipe

        result = cm.rate_limit("user1", "/api/test", 10, 60)
        assert result is True

    def test_rate_limit_with_redis_deny(self):
        cm, mock_r = _make_cache_manager_with_mock()
        mock_pipe = MagicMock()
        mock_pipe.execute.return_value = (0, 0, 11, 1)  # zcard = 11, limit = 10
        mock_r.pipeline.return_value = mock_pipe

        result = cm.rate_limit("user1", "/api/test", 10, 60)
        assert result is False

    def test_get_rate_limit_remaining_with_redis(self):
        cm, mock_r = _make_cache_manager_with_mock()
        mock_r.zcard.return_value = 3  # 已使用 3 次

        result = cm.get_rate_limit_remaining("user1", "/api/test", 10, 60)
        assert result == 7

    def test_cache_session_with_redis(self):
        cm, mock_r = _make_cache_manager_with_mock()
        result = cm.cache_session("sess123", {"user_id": 1}, ttl=86400)
        assert result is True
        mock_r.set.assert_called_once()

    def test_get_session_with_redis(self):
        cm, mock_r = _make_cache_manager_with_mock()
        mock_r.get.return_value = b'{"user_id": 1, "name": "test"}'
        result = cm.get_session("sess123")
        assert result == {"user_id": 1, "name": "test"}

    def test_get_session_with_redis_none(self):
        cm, mock_r = _make_cache_manager_with_mock()
        mock_r.get.return_value = None
        result = cm.get_session("no_sess")
        assert result is None

    def test_delete_session_with_redis(self):
        cm, mock_r = _make_cache_manager_with_mock()
        result = cm.delete_session("sess123")
        assert result is True
        mock_r.delete.assert_called_once()

    def test_health_check_with_redis_true(self):
        cm, mock_r = _make_cache_manager_with_mock()
        mock_r.ping.return_value = True
        result = cm.health_check()
        assert result is True

    def test_health_check_with_redis_exception(self):
        cm, mock_r = _make_cache_manager_with_mock()
        mock_r.ping.side_effect = Exception("connection lost")
        result = cm.health_check()
        assert result is False

    def test_get_with_redis_exception(self):
        cm, mock_r = _make_cache_manager_with_mock()
        mock_r.get.side_effect = Exception("connection error")
        result = cm.get("any")
        assert result is None

    def test_set_with_redis_exception(self):
        cm, mock_r = _make_cache_manager_with_mock()
        mock_r.set.side_effect = Exception("connection error")
        result = cm.set("any", "value")
        assert result is False

    def test_delete_with_redis_exception(self):
        cm, mock_r = _make_cache_manager_with_mock()
        mock_r.delete.side_effect = Exception("connection error")
        result = cm.delete("any")
        assert result is False

    def test_delete_pattern_with_redis_exception(self):
        cm, mock_r = _make_cache_manager_with_mock()
        mock_r.scan_iter.side_effect = Exception("scan error")
        result = cm.delete_pattern("*")
        assert result == 0

    def test_cache_case_stats_with_redis_exception(self):
        cm, mock_r = _make_cache_manager_with_mock()
        mock_r.set.side_effect = Exception("set error")
        result = cm.cache_case_stats({"total": 1})
        assert result is False

    def test_get_case_stats_with_redis_exception(self):
        cm, mock_r = _make_cache_manager_with_mock()
        mock_r.get.side_effect = Exception("get error")
        result = cm.get_case_stats()
        assert result is None

    def test_cache_bazi_result_with_redis_exception(self):
        cm, mock_r = _make_cache_manager_with_mock()
        mock_r.set.side_effect = Exception("set error")
        result = cm.cache_bazi_result("h", {})
        assert result is False

    def test_get_bazi_result_with_redis_exception(self):
        cm, mock_r = _make_cache_manager_with_mock()
        mock_r.get.side_effect = Exception("get error")
        result = cm.get_bazi_result("h")
        assert result is None

    def test_rate_limit_with_redis_exception(self):
        cm, mock_r = _make_cache_manager_with_mock()
        mock_r.pipeline.side_effect = Exception("pipeline error")
        result = cm.rate_limit("u", "/api", 10, 60)
        assert result is True  # 异常时降级允许

    def test_get_rate_limit_remaining_with_redis_exception(self):
        cm, mock_r = _make_cache_manager_with_mock()
        mock_r.zcard.side_effect = Exception("zcard error")
        result = cm.get_rate_limit_remaining("u", "/api", 10, 60)
        assert result == 10  # 异常时返回最大值

    def test_cache_session_with_redis_exception(self):
        cm, mock_r = _make_cache_manager_with_mock()
        mock_r.set.side_effect = Exception("set error")
        result = cm.cache_session("s", {})
        assert result is False

    def test_get_session_with_redis_exception(self):
        cm, mock_r = _make_cache_manager_with_mock()
        mock_r.get.side_effect = Exception("get error")
        result = cm.get_session("s")
        assert result is None

    def test_delete_session_with_redis_exception(self):
        cm, mock_r = _make_cache_manager_with_mock()
        mock_r.delete.side_effect = Exception("delete error")
        result = cm.delete_session("s")
        assert result is False


class TestCacheManagerInitNoRedis:
    """CacheManager 在 redis 库不可用时的降级行为。"""

    def test_no_redis_import_all_methods(self):
        """模拟 redis 库不可用，所有方法返回降级值。"""
        import builtins

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "redis":
                raise ImportError("No module named 'redis'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            c = CacheManager("redis://localhost:6379/0")
            assert c._redis is None
            # 基础操作
            assert c.get("any") is None
            assert c.set("any", "value") is False
            assert c.delete("any") is False
            assert c.delete_pattern("*") == 0
            # 案例统计
            assert c.cache_case_stats({}) is False
            assert c.get_case_stats() is None
            # 八字缓存
            assert c.cache_bazi_result("h", {}) is False
            assert c.get_bazi_result("h") is None
            # 限流（降级允许）
            assert c.rate_limit("u", "/api", 10, 60) is True
            assert c.get_rate_limit_remaining("u", "/api", 10, 60) == 10
            # Session
            assert c.cache_session("s", {}) is False
            assert c.get_session("s") is None
            assert c.delete_session("s") is False
            # 健康检查
            assert c.health_check() is False


# ═══════════════════════════════════════════════════════════════════════════
# get_cache_manager —— Redis 环境变量路径
# ═══════════════════════════════════════════════════════════════════════════

class TestGetCacheManagerRedisPath:
    """get_cache_manager() 的 Redis 路径测试。"""

    def test_redis_env_var_healthy(self):
        """设置 TENGOD_REDIS_URL 且 Redis 健康时返回 CacheManager。"""
        import tengod.cache_manager as cm_module

        # 重置单例
        cm_module._cache_manager_instance = None

        mock_redis = _make_mock_redis()
        mock_redis_module = MagicMock()
        mock_redis_module.from_url.return_value = mock_redis

        with patch.dict(os.environ, {"TENGOD_REDIS_URL": "redis://localhost:6379/0"}):
            with patch.dict(sys.modules, {"redis": mock_redis_module}):
                mgr = cm_module.get_cache_manager()
                assert isinstance(mgr, CacheManager)

        # 清理
        cm_module._cache_manager_instance = None

    def test_redis_env_var_unhealthy_fallback(self):
        """Redis 健康检查失败时降级到 MemoryCacheManager。"""
        import tengod.cache_manager as cm_module

        cm_module._cache_manager_instance = None

        mock_redis = _make_mock_redis()
        mock_redis.ping.return_value = False  # 健康检查失败
        mock_redis_module = MagicMock()
        mock_redis_module.from_url.return_value = mock_redis

        with patch.dict(os.environ, {"TENGOD_REDIS_URL": "redis://localhost:6379/0"}):
            with patch.dict(sys.modules, {"redis": mock_redis_module}):
                mgr = cm_module.get_cache_manager()
                assert isinstance(mgr, MemoryCacheManager)

        cm_module._cache_manager_instance = None

    def test_redis_env_var_init_exception_fallback(self):
        """Redis 初始化异常时降级到 MemoryCacheManager。"""
        import tengod.cache_manager as cm_module

        cm_module._cache_manager_instance = None

        mock_redis_module = MagicMock()
        mock_redis_module.from_url.side_effect = RuntimeError("init failed")

        with patch.dict(os.environ, {"TENGOD_REDIS_URL": "redis://localhost:6379/0"}):
            with patch.dict(sys.modules, {"redis": mock_redis_module}):
                mgr = cm_module.get_cache_manager()
                assert isinstance(mgr, MemoryCacheManager)

        cm_module._cache_manager_instance = None

    def test_double_checked_locking_second_check(self):
        """测试 get_cache_manager 的双重检查锁定路径。"""
        import tengod.cache_manager as cm_module

        cm_module._cache_manager_instance = None

        # 模拟：第一个检查通过（instance 为 None），进入锁，
        # 但第二个检查发现 instance 已被设置
        original_lock = cm_module._cache_manager_lock

        class FakeLock:
            def __enter__(self):
                # 在进入锁之前，设置 instance（模拟另一个线程抢先）
                cm_module._cache_manager_instance = MemoryCacheManager()
                return None

            def __exit__(self, *args):
                pass

        cm_module._cache_manager_lock = FakeLock()

        try:
            with patch.dict(os.environ, {}, clear=True):
                mgr = cm_module.get_cache_manager()
                assert isinstance(mgr, MemoryCacheManager)
        finally:
            cm_module._cache_manager_lock = original_lock
            cm_module._cache_manager_instance = None


# ═══════════════════════════════════════════════════════════════════════════
# _self_test 函数覆盖
# ═══════════════════════════════════════════════════════════════════════════

class TestSelfTest:
    """_self_test() 函数测试。"""

    def test_self_test_runs_all_passed(self):
        """_self_test() 应返回 0（全部通过）。"""
        from tengod.cache_manager import _self_test

        result = _self_test()
        assert result == 0


# ═══════════════════════════════════════════════════════════════════════════
# MemoryCacheManager —— _purge_expired_locked (5000+ 条目触发)
# ═══════════════════════════════════════════════════════════════════════════

class TestMemoryCacheManagerPurge:
    """MemoryCacheManager 过期清理测试（触发 _purge_expired_locked 阈值）。"""

    def test_purge_expired_triggered_at_threshold(self):
        """当条目数 >= 5000 时触发惰性清理。"""
        cm = MemoryCacheManager()
        # 添加 5000+ 条目，全部使用短 TTL 使其立即过期
        for i in range(5000):
            cm.set(f"purge_{i}", i, ttl=0)  # ttl=0 永不过期，不会触发清理

        # 添加一些已过期条目
        for i in range(10):
            cm.set(f"expired_{i}", i, ttl=1)
        time.sleep(1.1)

        # 再添加一个条目触发清理（此时 store 已有 5000+ 条目）
        cm.set("trigger", "value", ttl=60)

        # 验证过期条目已被清理
        for i in range(10):
            assert cm.get(f"expired_{i}") is None

        # 永不过期的条目仍存在
        assert cm.get("purge_0") == 0
        assert cm.get("trigger") == "value"

        # 清理
        cm.delete_pattern("purge_*")
        cm.delete_pattern("trigger")

    def test_purge_not_triggered_below_threshold(self):
        """条目数 < 5000 时不触发清理。"""
        cm = MemoryCacheManager()
        for i in range(100):
            cm.set(f"below_{i}", i, ttl=1)
        time.sleep(1.1)

        # 再添加一个条目，此时条目数 < 5000，不触发清理
        cm.set("new_one", "v", ttl=60)

        # 过期条目在 get 时惰性删除
        assert cm.get("below_0") is None
        assert cm.get("new_one") == "v"

        cm.delete_pattern("below_*")
        cm.delete_pattern("new_one")