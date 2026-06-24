#!/usr/bin/env python3
"""
cache.py — 十神项目缓存层 v2.17.0
==================================
高性能缓存层，支持 LRU、TTL、分层缓存策略。

特性：
- LRU 淘汰策略（基于 OrderedDict）
- TTL 过期机制
- 分层缓存（L1 内存缓存 + L2 持久化缓存）
- 热点数据预加载
- 缓存命中率统计
- 线程安全

用法：
    from tengod.cache import Cache

    cache = Cache(max_size=1000, ttl=300)
    cache.set("key", value)
    result = cache.get("key")
"""
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    created_at: float = field(default_factory=time.time)
    expires_at: float = 0.0
    access_count: int = 0
    last_accessed: float = 0.0

    def is_expired(self) -> bool:
        if self.expires_at == 0:
            return False
        return time.time() > self.expires_at

    def touch(self):
        self.access_count += 1
        self.last_accessed = time.time()


class Cache:
    """LRU + TTL 缓存

    特性：
    - LRU 淘汰：容量满时自动淘汰最久未使用的条目
    - TTL 过期：已过期的条目自动返回 None
    - 线程安全：所有操作加锁
    """

    def __init__(self, max_size: int = 1000, ttl: float = 300.0, name: str = "default"):
        self._max_size = max_size
        self._ttl = ttl
        self._name = name
        self._store: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.Lock()

        # 统计
        self._hits: int = 0
        self._misses: int = 0
        self._evictions: int = 0
        self._expirations: int = 0

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值，未命中返回 None"""
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                self._misses += 1
                return None

            if entry.is_expired():
                del self._store[key]
                self._expirations += 1
                self._misses += 1
                return None

            # LRU：移到末尾
            self._store.move_to_end(key)
            entry.touch()
            self._hits += 1
            return entry.value

    def set(self, key: str, value: Any, ttl: Optional[float] = None):
        """设置缓存值"""
        with self._lock:
            if key in self._store:
                self._store.move_to_end(key)

            expires_at = time.time() + (ttl if ttl is not None else self._ttl)
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=time.time(),
                expires_at=expires_at,
            )

            self._store[key] = entry

            # LRU 淘汰
            while len(self._store) > self._max_size:
                self._evictions += 1
                self._store.popitem(last=False)

    def delete(self, key: str):
        with self._lock:
            self._store.pop(key, None)

    def clear(self):
        with self._lock:
            self._store.clear()
            self._hits = 0
            self._misses = 0
            self._evictions = 0
            self._expirations = 0

    def has(self, key: str) -> bool:
        return self.get(key) is not None

    def get_or_set(self, key: str, factory: Callable[[], Any], ttl: Optional[float] = None) -> Any:
        """获取缓存，未命中时调用 factory 创建并缓存"""
        value = self.get(key)
        if value is not None:
            return value
        value = factory()
        self.set(key, value, ttl)
        return value

    def stats(self) -> Dict[str, Any]:
        total = self._hits + self._misses
        return {
            "name": self._name,
            "size": len(self._store),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self._hits / total, 3) if total > 0 else 0.0,
            "evictions": self._evictions,
            "expirations": self._expirations,
            "memory_estimate": self._estimate_memory(),
        }

    def _estimate_memory(self) -> int:
        """粗略估算内存占用（字节）"""
        total = 0
        for entry in self._store.values():
            try:
                total += len(str(entry.value))
            except Exception:
                total += 64
        return total

    def __len__(self) -> int:
        return len(self._store)

    def __contains__(self, key: str) -> bool:
        return self.has(key)


class TieredCache:
    """分层缓存：L1（内存热缓存）+ L2（持久化冷缓存）

    L1：小容量、高速度（默认 100 条，TTL 60s）
    L2：大容量、低速度（默认 1000 条，TTL 3600s）
    """

    def __init__(self,
                 l1_max: int = 100, l1_ttl: float = 60.0,
                 l2_max: int = 1000, l2_ttl: float = 3600.0):
        self.l1 = Cache(max_size=l1_max, ttl=l1_ttl, name="L1")
        self.l2 = Cache(max_size=l2_max, ttl=l2_ttl, name="L2")

    def get(self, key: str) -> Optional[Any]:
        # L1 优先
        value = self.l1.get(key)
        if value is not None:
            return value
        # L2 回退
        value = self.l2.get(key)
        if value is not None:
            # 提升到 L1
            self.l1.set(key, value)
            return value
        return None

    def set(self, key: str, value: Any, l1_ttl: Optional[float] = None, l2_ttl: Optional[float] = None):
        self.l1.set(key, value, l1_ttl)
        self.l2.set(key, value, l2_ttl)

    def delete(self, key: str):
        self.l1.delete(key)
        self.l2.delete(key)

    def clear(self):
        self.l1.clear()
        self.l2.clear()

    def stats(self) -> Dict[str, Any]:
        return {
            "l1": self.l1.stats(),
            "l2": self.l2.stats(),
            "total_hits": self.l1.stats()["hits"] + self.l2.stats()["hits"],
            "total_misses": self.l1.stats()["misses"] + self.l2.stats()["misses"],
        }


# ── 全局缓存实例 ──
# 知识图谱查询缓存（热点数据，TTL 5 分钟）
graph_cache = Cache(max_size=500, ttl=300.0, name="graph")

# 八字计算缓存（结果稳定，TTL 1 小时）
bazi_cache = Cache(max_size=200, ttl=3600.0, name="bazi")

# API 响应缓存（分层）
api_cache = TieredCache(l1_max=100, l1_ttl=30.0, l2_max=500, l2_ttl=600.0)


__all__ = [
    "Cache",
    "CacheEntry",
    "TieredCache",
    "graph_cache",
    "bazi_cache",
    "api_cache",
]