#!/usr/bin/env python3
"""
cache_manager.py — Redis 缓存层与降级方案 v1.0.0

阶段：公共基础设施
功能：
  1. CacheManager —— 基于 Redis 的通用缓存
        - 通用 JSON 缓存（get/set/delete/delete_pattern）
        - 函数结果装饰器（cached）
        - 案例统计缓存（cache_case_stats / get_case_stats）
        - 八字计算缓存（cache_bazi_result / get_bazi_result）
        - 滑动窗口限流（rate_limit / get_rate_limit_remaining）
        - Session 缓存（cache_session / get_session / delete_session）
        - 健康检查（health_check）
  2. MemoryCacheManager —— 无 Redis 时的内存降级实现，接口完全一致
  3. get_cache_manager() —— 工厂函数，单例 + 自动降级

缓存键命名规范：tengod:{component}:{key}
"""

from __future__ import annotations

import functools
import hashlib
import json
import logging
import os
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("tengod.cache_manager")


# ============================================================================
# 常量与工具函数
# ============================================================================

CACHE_PREFIX = "tengod"
COMPONENT_GENERIC = "cache"
COMPONENT_CASE_STATS = "case_stats"
COMPONENT_BAZI = "bazi"
COMPONENT_RL = "rl"
COMPONENT_SESSION = "session"


def _make_key(component: str, key: str) -> str:
    """拼接命名空间后的 Redis 键。"""
    return f"{CACHE_PREFIX}:{component}:{key}"


def _hash_args(*args, **kwargs) -> str:
    """将 args / kwargs 哈希成稳定字符串，用于生成缓存键。"""
    raw = json.dumps(
        {"args": [repr(a) for a in args], "kwargs": sorted(kwargs.items())},
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _rate_limit_key(user_id: str, endpoint: str) -> str:
    """限流器的稳定键（对 user_id + endpoint 做哈希，避免非法字符）。"""
    digest = hashlib.sha256(f"{user_id}:{endpoint}".encode("utf-8")).hexdigest()
    return _make_key(COMPONENT_RL, digest)


# ============================================================================
# CacheManager —— Redis 实现
# ============================================================================

class CacheManager:
    """基于 Redis 的通用缓存管理器，支持 JSON 序列化与 TTL。"""

    def __init__(self, redis_url: str):
        """
        初始化 Redis 客户端。

        :param redis_url: Redis 连接 URL，如 redis://localhost:6379/0
        """
        self.redis_url = redis_url
        try:
            import redis  # type: ignore
            self._redis = redis.from_url(redis_url)
        except Exception as e:  # pragma: no cover - 取决于运行环境
            logger.warning("CacheManager 初始化失败: %s", e)
            self._redis = None

    # ------------------------------------------------------------------
    # 基础 JSON 缓存
    # ------------------------------------------------------------------

    def get(self, key: str) -> Optional[Any]:
        """获取缓存的 JSON 值；未命中或出错返回 None。"""
        if self._redis is None:
            return None
        try:
            raw = self._redis.get(_make_key(COMPONENT_GENERIC, key))
            if raw is None:
                return None
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            return json.loads(raw)
        except Exception as e:
            logger.warning("CacheManager.get(%s) 失败: %s", key, e)
            return None

    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """
        写入 JSON 值，带 TTL（秒）。

        :param key: 业务键
        :param value: 可 JSON 序列化的对象
        :param ttl: 过期时间（秒），默认 5 分钟
        :return: 成功返回 True
        """
        if self._redis is None:
            return False
        try:
            data = json.dumps(value, ensure_ascii=False, default=str)
            self._redis.set(_make_key(COMPONENT_GENERIC, key), data, ex=ttl)
            return True
        except Exception as e:
            logger.warning("CacheManager.set(%s) 失败: %s", key, e)
            return False

    def delete(self, key: str) -> bool:
        """删除单个键。"""
        if self._redis is None:
            return False
        try:
            self._redis.delete(_make_key(COMPONENT_GENERIC, key))
            return True
        except Exception as e:
            logger.warning("CacheManager.delete(%s) 失败: %s", key, e)
            return False

    def delete_pattern(self, pattern: str) -> int:
        """
        按通配模式删除键（pattern 不需要包含 tengod:cache: 前缀）。

        :param pattern: 业务层通配符，例如 "user:*:profile"
        :return: 被删除的键数量（失败时返回 0）
        """
        if self._redis is None:
            return 0
        full_pattern = _make_key(COMPONENT_GENERIC, pattern)
        try:
            keys: List[bytes | str] = list(self._redis.scan_iter(match=full_pattern))
            if not keys:
                return 0
            return int(self._redis.delete(*keys) or 0)
        except Exception as e:
            logger.warning("CacheManager.delete_pattern(%s) 失败: %s", pattern, e)
            return 0

    # ------------------------------------------------------------------
    # 装饰器：缓存函数结果
    # ------------------------------------------------------------------

    def cached(self, key_prefix: str, ttl: int = 300) -> Callable:
        """
        装饰器：将函数返回值以 JSON 方式缓存。

        缓存键 = tengod:cache:{key_prefix}:{sha256(args, kwargs)}

        用法:
            @cache_manager.cached("bazi:calc", ttl=3600)
            def calc_bazi(birth):
                ...
        """

        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                digest = _hash_args(*args, **kwargs)
                cache_key = f"{key_prefix}:{digest}"
                hit = self.get(cache_key)
                if hit is not None:
                    return hit
                result = func(*args, **kwargs)
                if result is not None:
                    self.set(cache_key, result, ttl=ttl)
                return result

            return wrapper

        return decorator

    # ------------------------------------------------------------------
    # 案例统计
    # ------------------------------------------------------------------

    def cache_case_stats(self, stats: Dict[str, Any], ttl: int = 3600) -> bool:
        """缓存案例统计摘要（全量覆盖）。"""
        if self._redis is None:
            return False
        try:
            data = json.dumps(stats, ensure_ascii=False, default=str)
            self._redis.set(_make_key(COMPONENT_CASE_STATS, "summary"), data, ex=ttl)
            return True
        except Exception as e:
            logger.warning("CacheManager.cache_case_stats 失败: %s", e)
            return False

    def get_case_stats(self) -> Optional[Dict[str, Any]]:
        """获取案例统计摘要。"""
        if self._redis is None:
            return None
        try:
            raw = self._redis.get(_make_key(COMPONENT_CASE_STATS, "summary"))
            if raw is None:
                return None
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            return json.loads(raw)
        except Exception as e:
            logger.warning("CacheManager.get_case_stats 失败: %s", e)
            return None

    # ------------------------------------------------------------------
    # 八字计算缓存
    # ------------------------------------------------------------------

    def cache_bazi_result(self, input_hash: str, result: Dict[str, Any],
                          ttl: int = 86400) -> bool:
        """根据输入哈希缓存八字计算结果，默认 TTL 1 天。"""
        if self._redis is None:
            return False
        try:
            data = json.dumps(result, ensure_ascii=False, default=str)
            self._redis.set(_make_key(COMPONENT_BAZI, input_hash), data, ex=ttl)
            return True
        except Exception as e:
            logger.warning("CacheManager.cache_bazi_result(%s) 失败: %s", input_hash, e)
            return False

    def get_bazi_result(self, input_hash: str) -> Optional[Dict[str, Any]]:
        """获取已缓存的八字计算结果。"""
        if self._redis is None:
            return None
        try:
            raw = self._redis.get(_make_key(COMPONENT_BAZI, input_hash))
            if raw is None:
                return None
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            return json.loads(raw)
        except Exception as e:
            logger.warning("CacheManager.get_bazi_result(%s) 失败: %s", input_hash, e)
            return None

    # ------------------------------------------------------------------
    # 滑动窗口限流（Redis sorted set）
    # ------------------------------------------------------------------

    def rate_limit(self, user_id: str, endpoint: str,
                   limit: int, window_seconds: int) -> bool:
        """
        滑动窗口限流：在 window_seconds 窗口内最多允许 limit 次请求。

        :return: True 表示允许，False 表示被限流
        """
        if self._redis is None:
            return True
        try:
            now = time.time()
            key = _rate_limit_key(user_id, endpoint)
            member = f"{now:.6f}:{os.urandom(4).hex()}"

            pipe = self._redis.pipeline()
            pipe.zremrangebyscore(key, 0, now - window_seconds)
            pipe.zadd(key, {member: now})
            pipe.zcard(key)
            pipe.expire(key, window_seconds + 1)
            _, _, card, _ = pipe.execute()

            return int(card) <= limit
        except Exception as e:
            logger.warning("CacheManager.rate_limit(%s, %s) 失败: %s", user_id, endpoint, e)
            return True

    def get_rate_limit_remaining(self, user_id: str, endpoint: str,
                                 limit: int, window_seconds: int) -> int:
        """返回剩余配额（窗口内还能请求多少次）。"""
        if self._redis is None:
            return max(0, limit)
        try:
            now = time.time()
            key = _rate_limit_key(user_id, endpoint)
            self._redis.zremrangebyscore(key, 0, now - window_seconds)
            card = int(self._redis.zcard(key) or 0)
            return max(0, limit - card)
        except Exception as e:
            logger.warning("CacheManager.get_rate_limit_remaining(%s, %s) 失败: %s",
                           user_id, endpoint, e)
            return max(0, limit)

    # ------------------------------------------------------------------
    # Session 缓存
    # ------------------------------------------------------------------

    def cache_session(self, session_id: str, data: Dict[str, Any],
                      ttl: int = 86400) -> bool:
        """缓存 Session 数据。"""
        if self._redis is None:
            return False
        try:
            payload = json.dumps(data, ensure_ascii=False, default=str)
            self._redis.set(_make_key(COMPONENT_SESSION, session_id), payload, ex=ttl)
            return True
        except Exception as e:
            logger.warning("CacheManager.cache_session(%s) 失败: %s", session_id, e)
            return False

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """读取 Session。"""
        if self._redis is None:
            return None
        try:
            raw = self._redis.get(_make_key(COMPONENT_SESSION, session_id))
            if raw is None:
                return None
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            return json.loads(raw)
        except Exception as e:
            logger.warning("CacheManager.get_session(%s) 失败: %s", session_id, e)
            return None

    def delete_session(self, session_id: str) -> bool:
        """删除 Session。"""
        if self._redis is None:
            return False
        try:
            self._redis.delete(_make_key(COMPONENT_SESSION, session_id))
            return True
        except Exception as e:
            logger.warning("CacheManager.delete_session(%s) 失败: %s", session_id, e)
            return False

    # ------------------------------------------------------------------
    # 健康检查
    # ------------------------------------------------------------------

    def health_check(self) -> bool:
        """检查 Redis 连接是否可用。"""
        if self._redis is None:
            return False
        try:
            return bool(self._redis.ping())
        except Exception as e:
            logger.warning("CacheManager.health_check 失败: %s", e)
            return False


# ============================================================================
# MemoryCacheManager —— 内存降级实现
# ============================================================================

class MemoryCacheManager:
    """
    内存版缓存管理器，在无 Redis 时作为降级方案。
    所有键/值存放在字典中，TTL 通过 (value, expire_at) 元组实现。
    """

    def __init__(self) -> None:
        self._store: Dict[str, Tuple[Any, float]] = {}
        self._lock = threading.RLock()

    # ---------- 内部工具 ----------

    def _now(self) -> float:
        return time.time()

    def _expired(self, expire_at: float) -> bool:
        return expire_at is not None and expire_at < self._now()

    def _get_raw(self, full_key: str) -> Optional[Any]:
        with self._lock:
            item = self._store.get(full_key)
            if item is None:
                return None
            value, expire_at = item
            if self._expired(expire_at):
                self._store.pop(full_key, None)
                return None
            return value

    def _set_raw(self, full_key: str, value: Any, ttl: int) -> None:
        with self._lock:
            expire_at = self._now() + ttl if ttl and ttl > 0 else float("inf")
            self._store[full_key] = (value, expire_at)
            self._purge_expired_locked()

    def _purge_expired_locked(self) -> None:
        # 简单惰性清理：仅当条目数超过阈值时扫描
        if len(self._store) < 5000:
            return
        now = self._now()
        expired_keys = [k for k, (_, exp) in self._store.items()
                        if exp is not None and exp < now]
        for k in expired_keys:
            self._store.pop(k, None)

    # ---------- 基础 JSON 缓存 ----------

    def get(self, key: str) -> Optional[Any]:
        return self._get_raw(_make_key(COMPONENT_GENERIC, key))

    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        self._set_raw(_make_key(COMPONENT_GENERIC, key), value, ttl)
        return True

    def delete(self, key: str) -> bool:
        with self._lock:
            self._store.pop(_make_key(COMPONENT_GENERIC, key), None)
            return True

    def delete_pattern(self, pattern: str) -> int:
        import fnmatch
        full_pattern = _make_key(COMPONENT_GENERIC, pattern)
        with self._lock:
            matched = [k for k in self._store.keys()
                       if fnmatch.fnmatchcase(k, full_pattern)]
            for k in matched:
                self._store.pop(k, None)
            return len(matched)

    # ---------- 装饰器 ----------

    def cached(self, key_prefix: str, ttl: int = 300) -> Callable:
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                digest = _hash_args(*args, **kwargs)
                cache_key = f"{key_prefix}:{digest}"
                hit = self.get(cache_key)
                if hit is not None:
                    return hit
                result = func(*args, **kwargs)
                if result is not None:
                    self.set(cache_key, result, ttl=ttl)
                return result

            return wrapper

        return decorator

    # ---------- 案例统计 ----------

    def cache_case_stats(self, stats: Dict[str, Any], ttl: int = 3600) -> bool:
        self._set_raw(_make_key(COMPONENT_CASE_STATS, "summary"), stats, ttl)
        return True

    def get_case_stats(self) -> Optional[Dict[str, Any]]:
        return self._get_raw(_make_key(COMPONENT_CASE_STATS, "summary"))

    # ---------- 八字缓存 ----------

    def cache_bazi_result(self, input_hash: str, result: Dict[str, Any],
                          ttl: int = 86400) -> bool:
        self._set_raw(_make_key(COMPONENT_BAZI, input_hash), result, ttl)
        return True

    def get_bazi_result(self, input_hash: str) -> Optional[Dict[str, Any]]:
        return self._get_raw(_make_key(COMPONENT_BAZI, input_hash))

    # ---------- 滑动窗口限流 ----------

    def rate_limit(self, user_id: str, endpoint: str,
                   limit: int, window_seconds: int) -> bool:
        now = self._now()
        key = _rate_limit_key(user_id, endpoint)
        member = f"{now:.6f}:{os.urandom(4).hex()}"
        with self._lock:
            # 存储结构：{ key: List[timestamp] }
            timeline: List[float] = self._timeline_store.get(key, [])
            cutoff = now - window_seconds
            timeline = [ts for ts in timeline if ts >= cutoff]
            if len(timeline) >= limit:
                self._timeline_store[key] = timeline
                return False
            timeline.append(now)
            self._timeline_store[key] = timeline
            _ = member  # 保留与 Redis 版本相同的随机成员语义（无实际作用）
            return True

    def get_rate_limit_remaining(self, user_id: str, endpoint: str,
                                 limit: int, window_seconds: int) -> int:
        now = self._now()
        key = _rate_limit_key(user_id, endpoint)
        with self._lock:
            timeline: List[float] = self._timeline_store.get(key, [])
            cutoff = now - window_seconds
            timeline = [ts for ts in timeline if ts >= cutoff]
            self._timeline_store[key] = timeline
            return max(0, limit - len(timeline))

    # ---------- Session ----------

    def cache_session(self, session_id: str, data: Dict[str, Any],
                      ttl: int = 86400) -> bool:
        self._set_raw(_make_key(COMPONENT_SESSION, session_id), data, ttl)
        return True

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        return self._get_raw(_make_key(COMPONENT_SESSION, session_id))

    def delete_session(self, session_id: str) -> bool:
        with self._lock:
            self._store.pop(_make_key(COMPONENT_SESSION, session_id), None)
            return True

    # ---------- 健康检查 ----------

    def health_check(self) -> bool:
        return True


# 将限流器的时间线存放在独立字典中，避免与普通缓存冲突
MemoryCacheManager._timeline_store: Dict[str, List[float]] = {}


# ============================================================================
# 工厂函数：单例 + 自动降级
# ============================================================================

_cache_manager_instance: Optional[CacheManager | MemoryCacheManager] = None
_cache_manager_lock = threading.Lock()


def get_cache_manager() -> CacheManager | MemoryCacheManager:
    """
    获取全局缓存管理器（单例）。

    优先级：
      1. 若存在 TENGOD_REDIS_URL 环境变量，尝试使用 CacheManager(Redis)
         - 连接成功 → 返回 Redis 版
         - 连接失败 → 降级到 MemoryCacheManager
      2. 否则 → 返回 MemoryCacheManager

    :return: CacheManager 或 MemoryCacheManager 实例
    """
    global _cache_manager_instance
    if _cache_manager_instance is not None:
        return _cache_manager_instance

    with _cache_manager_lock:
        if _cache_manager_instance is not None:
            return _cache_manager_instance

        redis_url = os.environ.get("TENGOD_REDIS_URL", "").strip()
        if redis_url:
            try:
                manager = CacheManager(redis_url)
                if manager.health_check():
                    logger.info("使用 Redis 缓存管理器: %s",
                                redis_url.replace("://", "://***@"))
                    _cache_manager_instance = manager
                    return _cache_manager_instance
                logger.warning("Redis 健康检查失败，降级到内存缓存")
            except Exception as e:
                logger.warning("Redis 初始化异常: %s，降级到内存缓存", e)

        logger.info("使用内存缓存管理器（MemoryCacheManager）")
        _cache_manager_instance = MemoryCacheManager()
        return _cache_manager_instance


# ============================================================================
# v2.6: 引擎级缓存工具
# ============================================================================

# 引擎缓存 TTL（秒）
ENGINE_TTL = {
    "bazi": 86400,       # 八字：24小时
    "ziwei": 86400,      # 紫微：24小时
    "qimen": 3600,       # 奇门：1小时
    "fengshui": 3600,    # 风水：1小时
    "liuyao": 3600,      # 六爻：1小时
    "fusion": 1800,      # 融合分析：30分钟
    "report": 600,       # 报告：10分钟
    "default": 300,      # 默认：5分钟
}


class EngineCacheStats:
    """引擎缓存统计 v2.6"""

    def __init__(self):
        self._lock = threading.Lock()
        self._hits: Dict[str, int] = {}
        self._misses: Dict[str, int] = {}

    def record_hit(self, engine: str) -> None:
        with self._lock:
            self._hits[engine] = self._hits.get(engine, 0) + 1

    def record_miss(self, engine: str) -> None:
        with self._lock:
            self._misses[engine] = self._misses.get(engine, 0) + 1

    def get_stats(self) -> Dict[str, Dict[str, Any]]:
        """获取各引擎缓存命中率"""
        with self._lock:
            stats = {}
            all_engines = set(list(self._hits.keys()) + list(self._misses.keys()))
            for engine in all_engines:
                h = self._hits.get(engine, 0)
                m = self._misses.get(engine, 0)
                total = h + m
                stats[engine] = {
                    "hits": h,
                    "misses": m,
                    "total": total,
                    "hit_rate": round(h / total, 3) if total > 0 else 0.0,
                }
            return stats

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()
            self._misses.clear()


_engine_cache_stats = EngineCacheStats()


def get_engine_cache_stats() -> Dict[str, Dict[str, Any]]:
    """获取引擎缓存命中率统计"""
    return _engine_cache_stats.get_stats()


def cached_engine(engine: str, ttl: Optional[int] = None):
    """引擎级缓存装饰器 v2.6

    自动选择 TTL，追踪命中率。

    Args:
        engine: 引擎名（bazi/ziwei/qimen/fengshui/liuyao/fusion/report）
        ttl: 自定义 TTL（秒），None 则使用默认值

    Usage:
        @cached_engine("bazi")
        def calculate_bazi(birth_date, birth_time):
            ...
    """
    actual_ttl = ttl or ENGINE_TTL.get(engine, ENGINE_TTL["default"])

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            cm = get_cache_manager()
            key = f"{engine}:{_hash_args(*args, **kwargs)}"
            result = cm.get(key)
            if result is not None:
                _engine_cache_stats.record_hit(engine)
                return result
            _engine_cache_stats.record_miss(engine)
            result = func(*args, **kwargs)
            cm.set(key, result, ttl=actual_ttl)
            return result
        return wrapper
    return decorator


def cached_bazi(ttl: Optional[int] = None):
    """八字引擎缓存装饰器"""
    return cached_engine("bazi", ttl)


def cached_ziwei(ttl: Optional[int] = None):
    """紫微引擎缓存装饰器"""
    return cached_engine("ziwei", ttl)


def cached_qimen(ttl: Optional[int] = None):
    """奇门引擎缓存装饰器"""
    return cached_engine("qimen", ttl)


def cached_fengshui(ttl: Optional[int] = None):
    """风水引擎缓存装饰器"""
    return cached_engine("fengshui", ttl)


def cached_fusion(ttl: Optional[int] = None):
    """融合分析缓存装饰器"""
    return cached_engine("fusion", ttl)


# ============================================================================
# 自测：仅在直接执行此文件时运行
# ============================================================================

def _self_test() -> int:
    """在 MemoryCacheManager 上进行一次完整的自测。"""
    print("=" * 60)
    print("tengod.cache_manager 自测（使用 MemoryCacheManager）")
    print("=" * 60)

    cm = MemoryCacheManager()
    passed = 0
    total = 0

    # 1. 基础 get / set
    total += 1
    cm.set("foo", {"value": "中文支持 ✓", "n": 42}, ttl=60)
    got = cm.get("foo")
    if got == {"value": "中文支持 ✓", "n": 42}:
        print("[PASS] 1. set / get 基本写入读取")
        passed += 1
    else:
        print(f"[FAIL] 1. 期望 {{'value': '中文支持 ✓', 'n': 42}}, 得到 {got!r}")

    # 2. 未命中
    total += 1
    if cm.get("not_exist") is None:
        print("[PASS] 2. 未命中返回 None")
        passed += 1
    else:
        print("[FAIL] 2. 未命中应返回 None")

    # 3. delete
    total += 1
    cm.set("to_delete", [1, 2, 3], ttl=60)
    cm.delete("to_delete")
    if cm.get("to_delete") is None:
        print("[PASS] 3. delete 能够移除键")
        passed += 1
    else:
        print("[FAIL] 3. delete 未能移除键")

    # 4. delete_pattern
    total += 1
    for i in range(5):
        cm.set(f"batch_{i}", i, ttl=60)
    removed = cm.delete_pattern("batch_*")
    if removed == 5 and cm.get("batch_0") is None:
        print("[PASS] 4. delete_pattern 按通配符批量删除")
        passed += 1
    else:
        print(f"[FAIL] 4. 期望 5, got={removed}, batch_0={cm.get('batch_0')!r}")

    # 5. TTL 过期
    total += 1
    cm.set("short", {"a": 1}, ttl=1)
    time.sleep(1.1)
    if cm.get("short") is None:
        print("[PASS] 5. TTL 过期后 get 返回 None")
        passed += 1
    else:
        print("[FAIL] 5. TTL 应过期但仍可读")

    # 6. @cached 装饰器
    total += 1
    call_counter = {"n": 0}

    @cm.cached("expensive", ttl=60)
    def expensive(x: int) -> Dict[str, Any]:
        call_counter["n"] += 1
        return {"x": x, "square": x * x, "msg": "中文"}

    r1 = expensive(5)
    r2 = expensive(5)
    r3 = expensive(3)
    if (r1 == r2 == {"x": 5, "square": 25, "msg": "中文"}
            and r3 == {"x": 3, "square": 9, "msg": "中文"}
            and call_counter["n"] == 2):
        print("[PASS] 6. @cached 装饰器正确缓存（相同参数命中，不同参数分别缓存）")
        passed += 1
    else:
        print(f"[FAIL] 6. r1={r1}, r3={r3}, calls={call_counter['n']}")

    # 7. case_stats
    total += 1
    cm.cache_case_stats({"total": 99, "tags": ["命理", "八字"]}, ttl=3600)
    stats = cm.get_case_stats()
    if stats and stats.get("total") == 99:
        print("[PASS] 7. cache_case_stats / get_case_stats")
        passed += 1
    else:
        print(f"[FAIL] 7. stats={stats!r}")

    # 8. bazi_result
    total += 1
    input_hash = hashlib.sha256(b"2000-01-01-12:00").hexdigest()
    cm.cache_bazi_result(input_hash, {"day_master": "甲木", "score": 99}, ttl=3600)
    br = cm.get_bazi_result(input_hash)
    if br and br.get("day_master") == "甲木":
        print("[PASS] 8. cache_bazi_result / get_bazi_result")
        passed += 1
    else:
        print(f"[FAIL] 8. bazi_result={br!r}")

    # 9. rate_limit
    total += 1
    uid = "test_user"
    endpoint = "/api/test"
    limit, window = 3, 5
    results = [cm.rate_limit(uid, endpoint, limit, window) for _ in range(5)]
    remaining = cm.get_rate_limit_remaining(uid, endpoint, limit, window)
    if results[:3] == [True, True, True] and results[3:] == [False, False] and remaining == 0:
        print("[PASS] 9. rate_limit 滑动窗口：前 3 通过，后 2 被拒绝；remaining=0")
        passed += 1
    else:
        print(f"[FAIL] 9. results={results}, remaining={remaining}")

    # 10. session
    total += 1
    sid = "session-abc-123"
    cm.cache_session(sid, {"user_id": 1, "name": "测试用户"}, ttl=3600)
    sess = cm.get_session(sid)
    cm.delete_session(sid)
    after_delete = cm.get_session(sid)
    if sess and sess.get("name") == "测试用户" and after_delete is None:
        print("[PASS] 10. cache_session / get_session / delete_session")
        passed += 1
    else:
        print(f"[FAIL] 10. sess={sess!r}, after_delete={after_delete!r}")

    # 11. health_check
    total += 1
    if cm.health_check():
        print("[PASS] 11. health_check 返回 True")
        passed += 1
    else:
        print("[FAIL] 11. health_check 应为 True")

    print("-" * 60)
    print(f"结果: {passed}/{total} 通过")
    print("=" * 60)
    return 0 if passed == total else 1


if __name__ == "__main__":
    import sys
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    sys.exit(_self_test())
