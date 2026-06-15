"""lru_cache.py — 知识库缓存层 (v2.1.0)

LRU 缓存 + TTL，加速高频查询。
"""
import time
import threading
from collections import OrderedDict
from typing import Any, Dict, Optional, Tuple


class LRUCache:
    """LRU 缓存 — 最近最少使用淘汰 + TTL 过期

    用法：
        cache = LRUCache(max_size=1000, default_ttl=300)
        cache.set("key", value)
        value = cache.get("key")
        cache.set("key", value, ttl=60)  # 自定义 TTL
    """

    def __init__(self, max_size: int = 1000, default_ttl: float = 300.0):
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._store: OrderedDict = OrderedDict()
        self._lock = threading.RLock()

    def get(self, key: str) -> Tuple[Optional[Any], bool]:
        """获取缓存值，返回 (value, hit)"""
        with self._lock:
            if key not in self._store:
                return None, False

            value, expires_at = self._store[key]
            if time.time() > expires_at:
                del self._store[key]
                return None, False

            # 移动到末尾（最近使用）
            self._store.move_to_end(key)
            return value, True

    def set(self, key: str, value: Any, ttl: Optional[float] = None):
        """设置缓存值"""
        with self._lock:
            if key in self._store:
                self._store.move_to_end(key)

            expires_at = time.time() + (ttl if ttl is not None else self._default_ttl)
            self._store[key] = (value, expires_at)

            # 淘汰最久未使用的
            while len(self._store) > self._max_size:
                self._store.popitem(last=False)

    def delete(self, key: str) -> bool:
        """删除缓存键"""
        with self._lock:
            if key in self._store:
                del self._store[key]
                return True
            return False

    def clear(self):
        """清空缓存"""
        with self._lock:
            self._store.clear()

    def contains(self, key: str) -> bool:
        """检查键是否存在且未过期"""
        with self._lock:
            if key not in self._store:
                return False
            _, expires_at = self._store[key]
            if time.time() > expires_at:
                return False
            return True

    def size(self) -> int:
        """当前缓存条目数"""
        with self._lock:
            return len(self._store)

    def stats(self) -> Dict[str, Any]:
        """缓存统计"""
        with self._lock:
            now = time.time()
            expired = sum(1 for _, exp in self._store.values() if now > exp)
            return {
                "size": len(self._store),
                "max_size": self._max_size,
                "default_ttl": self._default_ttl,
                "expired": expired,
            }


class KnowledgeCache:
    """知识库缓存 — 封装 LRU 缓存，面向知识库查询场景

    支持：
        - 按节点名缓存
        - 按搜索查询缓存
        - 按类型过滤缓存
        - 缓存失效策略
    """

    def __init__(self, max_size: int = 1000, default_ttl: float = 300.0):
        self._node_cache = LRUCache(max_size=max_size, default_ttl=default_ttl)
        self._query_cache = LRUCache(max_size=max_size // 2, default_ttl=default_ttl)
        self._type_cache = LRUCache(max_size=100, default_ttl=default_ttl * 2)
        self._hits = 0
        self._misses = 0

    def get_node(self, node_id: str) -> Tuple[Optional[Any], bool]:
        """获取节点缓存"""
        key = f"node:{node_id}"
        value, hit = self._node_cache.get(key)
        if hit:
            self._hits += 1
        else:
            self._misses += 1
        return value, hit

    def set_node(self, node_id: str, node_data: Any, ttl: Optional[float] = None):
        """设置节点缓存"""
        key = f"node:{node_id}"
        self._node_cache.set(key, node_data, ttl)

    def get_query(self, query: str, filters: Optional[Dict] = None) -> Tuple[Optional[Any], bool]:
        """获取搜索查询缓存"""
        key = self._make_query_key(query, filters)
        value, hit = self._query_cache.get(key)
        if hit:
            self._hits += 1
        else:
            self._misses += 1
        return value, hit

    def set_query(self, query: str, result: Any, filters: Optional[Dict] = None, ttl: Optional[float] = None):
        """设置搜索查询缓存"""
        key = self._make_query_key(query, filters)
        self._query_cache.set(key, result, ttl)

    def get_by_type(self, node_type: str) -> Tuple[Optional[Any], bool]:
        """获取按类型查询缓存"""
        key = f"type:{node_type}"
        value, hit = self._type_cache.get(key)
        if hit:
            self._hits += 1
        else:
            self._misses += 1
        return value, hit

    def set_by_type(self, node_type: str, nodes: Any, ttl: Optional[float] = None):
        """设置按类型查询缓存"""
        key = f"type:{node_type}"
        self._type_cache.set(key, nodes, ttl)

    def invalidate_node(self, node_id: str):
        """使特定节点缓存失效"""
        self._node_cache.delete(f"node:{node_id}")

    def invalidate_all(self):
        """使所有缓存失效"""
        self._node_cache.clear()
        self._query_cache.clear()
        self._type_cache.clear()

    def _make_query_key(self, query: str, filters: Optional[Dict] = None) -> str:
        """生成查询缓存键"""
        if filters:
            filter_str = "|".join(f"{k}={v}" for k, v in sorted(filters.items()))
            return f"query:{query}:{filter_str}"
        return f"query:{query}"

    def stats(self) -> Dict[str, Any]:
        """缓存统计"""
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0.0
        return {
            "node_cache": self._node_cache.stats(),
            "query_cache": self._query_cache.stats(),
            "type_cache": self._type_cache.stats(),
            "hits": self._hits,
            "misses": self._misses,
            "total_requests": total,
            "hit_rate": round(hit_rate, 4),
        }