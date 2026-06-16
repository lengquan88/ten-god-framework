#!/usr/bin/env python3
"""
vector_store.py — 向量存储与语义检索引擎 v1.0.0
==============================================
为中华传统文化知识图谱提供向量化存储与语义搜索能力。

技术方案：
  - 嵌入层：字符级 n-gram 哈希 + 领域语义特征（256维）
  - 存储层：FAISS IndexFlatIP（余弦相似度）
  - 搜索层：语义相似搜索 + 知识关联推荐

依赖：faiss-cpu, numpy（已安装）
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np

__all__ = [
    "VectorStore",
    "ChineseEmbedder",
    "SemanticSearchResult",
    "build_knowledge_vectors",
    "search_similar",
    "recommend_related",
]
__version__ = "1.0.0"

# ============================================================================
# 领域语义特征映射（五行、阴阳、方位等）
# ============================================================================

# 核心领域词汇及其语义特征向量（64维）
_DOMAIN_SEMANTIC: Dict[str, np.ndarray] = {}

# 五行映射（独热编码基）
_WUXING_ONEHOT = {
    "木": np.array([1, 0, 0, 0, 0], dtype=np.float32),
    "火": np.array([0, 1, 0, 0, 0], dtype=np.float32),
    "土": np.array([0, 0, 1, 0, 0], dtype=np.float32),
    "金": np.array([0, 0, 0, 1, 0], dtype=np.float32),
    "水": np.array([0, 0, 0, 0, 1], dtype=np.float32),
}

# 阴阳映射
_YINYANG_ONEHOT = {
    "阳": np.array([1, 0], dtype=np.float32),
    "阴": np.array([0, 1], dtype=np.float32),
}

# 方位映射（8方位独热）
_DIRECTION_ONEHOT = {
    "东": np.array([1, 0, 0, 0, 0, 0, 0, 0], dtype=np.float32),
    "南": np.array([0, 1, 0, 0, 0, 0, 0, 0], dtype=np.float32),
    "西": np.array([0, 0, 1, 0, 0, 0, 0, 0], dtype=np.float32),
    "北": np.array([0, 0, 0, 1, 0, 0, 0, 0], dtype=np.float32),
    "中": np.array([0, 0, 0, 0, 1, 0, 0, 0], dtype=np.float32),
    "东南": np.array([0, 0, 0, 0, 0, 1, 0, 0], dtype=np.float32),
    "西南": np.array([0, 0, 0, 0, 0, 0, 1, 0], dtype=np.float32),
    "西北": np.array([0, 0, 0, 0, 0, 0, 0, 1], dtype=np.float32),
    "东北": np.array([0.5, 0, 0, 0.5, 0, 0.5, 0, 0.5], dtype=np.float32),  # 复合
}

# 季节映射
_SEASON_ONEHOT = {
    "春": np.array([1, 0, 0, 0, 0], dtype=np.float32),
    "夏": np.array([0, 1, 0, 0, 0], dtype=np.float32),
    "长夏": np.array([0, 0, 1, 0, 0], dtype=np.float32),
    "秋": np.array([0, 0, 0, 1, 0], dtype=np.float32),
    "冬": np.array([0, 0, 0, 0, 1], dtype=np.float32),
}

# 天干地支索引
_TIANGAN_INDEX = {t: i for i, t in enumerate(["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"])}
_DIZHI_INDEX = {d: i for i, d in enumerate(["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"])}

# 八卦符号
_BAGUA_SYMBOLS = {
    "乾": "☰", "兑": "☱", "离": "☲", "震": "☳",
    "巽": "☴", "坎": "☵", "艮": "☶", "坤": "☷",
}

# 十神分类
_SHIGAN_CATEGORIES = {
    "正官": "克我阴阳异性", "七杀": "克我阴阳同性",
    "正印": "生我阴阳异性", "偏印": "生我阴阳同性",
    "正财": "我克阴阳异性", "偏财": "我克阴阳同性",
    "比肩": "同我阴阳同性", "劫财": "同我阴阳异性",
    "食神": "我生阴阳同性", "伤官": "我生阴阳异性",
}


# ============================================================================
# 中文嵌入器
# ============================================================================

class ChineseEmbedder:
    """中文文本嵌入器 — 字符级 n-gram + 领域语义特征

    生成 256 维向量：
      - 128 维：字符 n-gram 哈希特征
      - 64 维：领域语义特征（五行、阴阳、方位等）
      - 64 维：补充特征（文本结构）

    无需预训练模型，纯 Python + NumPy 实现。
    """

    VECTOR_DIM = 256
    NGRAM_DIM = 128
    SEMANTIC_DIM = 64
    STRUCT_DIM = 64

    def __init__(self):
        self._cache: Dict[str, np.ndarray] = {}

    def embed(self, text: str) -> np.ndarray:
        """将文本嵌入为向量"""
        text = text.strip()
        if not text:
            return np.zeros(self.VECTOR_DIM, dtype=np.float32)

        if text in self._cache:
            return self._cache[text]

        # 1. 字符 n-gram 哈希特征
        ngram_vec = self._char_ngram_hash(text)

        # 2. 领域语义特征
        semantic_vec = self._domain_semantic(text)

        # 3. 文本结构特征
        struct_vec = self._text_structure(text)

        # 拼接并归一化
        vec = np.concatenate([ngram_vec, semantic_vec, struct_vec])
        vec = self._l2_normalize(vec)

        self._cache[text] = vec
        return vec

    def embed_batch(self, texts: List[str]) -> np.ndarray:
        """批量嵌入"""
        return np.array([self.embed(t) for t in texts], dtype=np.float32)

    def _char_ngram_hash(self, text: str) -> np.ndarray:
        """字符级 n-gram 哈希特征（128维）"""
        vec = np.zeros(self.NGRAM_DIM, dtype=np.float32)

        # 提取中文字符
        chars = [c for c in text if '\u4e00' <= c <= '\u9fff']
        if not chars:
            return vec

        # 单字特征
        for ch in chars:
            idx = self._hash_char(ch) % self.NGRAM_DIM
            vec[idx] += 1.0

        # 双字特征（bigram）
        for i in range(len(chars) - 1):
            bigram = chars[i] + chars[i + 1]
            idx = self._hash_string(bigram) % self.NGRAM_DIM
            vec[idx] += 0.5

        # 三字特征（trigram）
        for i in range(len(chars) - 2):
            trigram = chars[i] + chars[i + 1] + chars[i + 2]
            idx = self._hash_string(trigram) % self.NGRAM_DIM
            vec[idx] += 0.25

        # 归一化
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm
        return vec

    def _domain_semantic(self, text: str) -> np.ndarray:
        """领域语义特征（64维）"""
        vec = np.zeros(self.SEMANTIC_DIM, dtype=np.float32)
        offset = 0

        # 五行特征 (5维)
        for wx, wv in _WUXING_ONEHOT.items():
            if wx in text:
                vec[offset:offset + 5] += wv * 0.1
        offset += 5

        # 阴阳特征 (2维)
        for yy, yv in _YINYANG_ONEHOT.items():
            if yy in text:
                vec[offset:offset + 2] += yv * 0.1
        offset += 2

        # 方位特征 (8维)
        for dir_, dv in _DIRECTION_ONEHOT.items():
            if dir_ in text:
                vec[offset:offset + 8] += dv * 0.1
        offset += 8

        # 季节特征 (5维)
        for season, sv in _SEASON_ONEHOT.items():
            if season in text:
                vec[offset:offset + 5] += sv * 0.1
        offset += 5

        # 天干特征 (10维)
        for tg, idx in _TIANGAN_INDEX.items():
            if tg in text:
                vec[offset + idx] += 0.1
        offset += 10

        # 地支特征 (12维)
        for dz, idx in _DIZHI_INDEX.items():
            if dz in text:
                vec[offset + idx] += 0.1
        offset += 12

        # 八卦特征 (8维)
        for bg, sym in _BAGUA_SYMBOLS.items():
            if bg in text or sym in text:
                idx = list(_BAGUA_SYMBOLS.keys()).index(bg)
                vec[offset + idx] += 0.1
        offset += 8

        # 十神特征 (10维)
        for sg, _ in _SHIGAN_CATEGORIES.items():
            if sg in text:
                idx = list(_SHIGAN_CATEGORIES.keys()).index(sg)
                vec[offset + idx] += 0.1
        offset += 10

        # 剩余维度 (4维) 留给其他语义特征
        # 留空

        return vec

    def _text_structure(self, text: str) -> np.ndarray:
        """文本结构特征（64维）"""
        vec = np.zeros(self.STRUCT_DIM, dtype=np.float32)

        chars = list(text)
        if not chars:
            return vec

        # 长度特征
        vec[0] = min(len(text), 100) / 100.0

        # 中文占比
        chinese_chars = sum(1 for c in chars if '\u4e00' <= c <= '\u9fff')
        vec[1] = chinese_chars / max(len(chars), 1)

        # 数字占比
        digit_chars = sum(1 for c in chars if c.isdigit())
        vec[2] = digit_chars / max(len(chars), 1)

        # 符号占比
        punct_chars = sum(1 for c in chars if c in '，。、；：？！""''（）【】《》')
        vec[3] = punct_chars / max(len(chars), 1)

        # 词数特征（用字符数近似）
        vec[4] = min(chinese_chars, 20) / 20.0

        # 剩余维度用哈希填充
        for i, ch in enumerate(chars):
            if i >= 59:
                break
            if '\u4e00' <= ch <= '\u9fff':
                idx = 5 + (self._hash_char(ch) % 59)
                vec[idx] += 0.05

        return vec

    @staticmethod
    def _hash_char(ch: str) -> int:
        """单字哈希"""
        return ord(ch) * 2654435761 & 0xFFFFFFFF

    @staticmethod
    def _hash_string(s: str) -> int:
        """字符串哈希"""
        h = hashlib.md5(s.encode('utf-8')).hexdigest()
        return int(h[:8], 16)

    @staticmethod
    def _l2_normalize(vec: np.ndarray) -> np.ndarray:
        """L2 归一化"""
        norm = np.linalg.norm(vec)
        if norm > 0:
            return vec / norm
        return vec

    def clear_cache(self):
        self._cache.clear()


# ============================================================================
# FAISS 向量存储
# ============================================================================

@dataclass
class SemanticSearchResult:
    """语义搜索结果"""
    query: str
    results: List[Dict[str, Any]]
    total_indexed: int
    search_time_ms: float

    def text_summary(self) -> List[str]:
        """生成文本摘要"""
        lines = [f"搜索: \"{self.query}\" → {len(self.results)} 个结果 ({self.total_indexed} 个节点, {self.search_time_ms:.1f}ms)"]
        for i, r in enumerate(self.results[:10]):
            dist = r.get("similarity", 0)
            bar = "█" * int(dist * 20) + "░" * (20 - int(dist * 20))
            lines.append(f"  {i+1}. [{r['type']}] {r['name']} ({r['name_cn']}) {bar} {dist:.3f}")
        return lines


class VectorStore:
    """向量存储 — 基于 FAISS 的语义搜索引擎

    核心功能：
      - 构建向量索引（FAISS IndexFlatIP）
      - 语义搜索（余弦相似度）
      - 知识关联推荐
      - 索引持久化
    """

    def __init__(self, dim: int = 256):
        self.embedder = ChineseEmbedder()
        self.dim = dim
        self._index = None          # FAISS 索引
        self._nodes: List[Dict] = []  # 节点元数据
        self._initialized = False
        self._stats = {
            "total_nodes": 0,
            "total_vectors": 0,
            "search_count": 0,
            "avg_search_ms": 0.0,
        }

    # ── 索引构建 ──────────────────────────────────────────────────────────

    def build_from_knowledge_graph(self, kg: Any = None) -> int:
        """从知识图谱构建向量索引

        Args:
            kg: KnowledgeGraph 实例（None 则自动导入）

        Returns:
            索引的节点数量
        """
        if kg is None:
            from tengod.knowledge_graph import get_knowledge_graph
            kg = get_knowledge_graph()

        nodes = self._extract_nodes(kg)
        texts = [n["text"] for n in nodes]
        vectors = self.embedder.embed_batch(texts)

        self._build_index(vectors, nodes)
        return len(nodes)

    def _extract_nodes(self, kg: Any) -> List[Dict[str, Any]]:
        """从知识图谱提取所有节点为可嵌入文本"""
        nodes = []

        def _safe_get(obj, key, default=""):
            """安全获取属性，兼容 dict 和 dataclass"""
            if isinstance(obj, dict):
                return obj.get(key, default)
            return getattr(obj, key, default)

        # 五行元素
        for name, info in kg._elements.items():
            text = self._format_element(name, info)
            nodes.append({
                "id": f"element:{name}", "type": "五行", "name": name,
                "name_cn": _safe_get(info, "color", ""), "text": text,
                "data": info if isinstance(info, dict) else {},
            })

        # 八卦
        for name, info in kg._trigrams.items():
            sym = _BAGUA_SYMBOLS.get(name, "")
            text = (f"八卦 {name}{sym} "
                    f"自然:{_safe_get(info,'nature')} "
                    f"家人:{_safe_get(info,'family_role')} "
                    f"五行:{_safe_get(info,'element')} "
                    f"方位:{_safe_get(info,'direction')} "
                    f"身体:{_safe_get(info,'body_part')}")
            nodes.append({
                "id": f"trigram:{name}", "type": "八卦", "name": name,
                "name_cn": sym, "text": text,
                "data": {"nature": _safe_get(info, "nature"),
                         "element": _safe_get(info, "element")},
            })

        # 天干
        for name, info in kg._tiangan.items():
            text = f"天干 {name} 五行:{info.get('wuxing','')} 阴阳:{info.get('yinyang','')} 方位:{info.get('direction','')}"
            nodes.append({
                "id": f"tiangan:{name}", "type": "天干", "name": name,
                "name_cn": f"{info.get('yinyang','')}{info.get('wuxing','')}", "text": text, "data": info,
            })

        # 地支
        for name, info in kg._dizhi.items():
            text = f"地支 {name} 五行:{info.get('wuxing','')} 阴阳:{info.get('yinyang','')} 生肖:{info.get('zodiac','')} 时辰:{info.get('hour','')} 方位:{info.get('direction','')} 藏干:{info.get('hidden_stems','')}"
            nodes.append({
                "id": f"dizhi:{name}", "type": "地支", "name": name,
                "name_cn": info.get("zodiac", ""), "text": text, "data": info,
            })

        # 十神
        for name, info in kg._shigan.items():
            category = _SHIGAN_CATEGORIES.get(name, "")
            text = f"十神 {name} 分类:{info.get('category','')} 规则:{category} 描述:{info.get('description','')}"
            nodes.append({
                "id": f"shigan:{name}", "type": "十神", "name": name,
                "name_cn": info.get("category", ""), "text": text, "data": info,
            })

        # 河图洛书
        hetu_info = {"name": "河图", "description": "天一生水，地六成之；地二生火，天七成之；天三生木，地八成之；地四生金，天九成之；天五生土，地十成之"}
        luoshu_info = {"name": "洛书", "description": "戴九履一，左三右七，二四为肩，六八为足，五居中央"}
        nodes.append({
            "id": "diagram:河图", "type": "河图洛书", "name": "河图",
            "name_cn": "天地生成数", "text": f"河图 {hetu_info['description']}", "data": hetu_info,
        })
        nodes.append({
            "id": "diagram:洛书", "type": "河图洛书", "name": "洛书",
            "name_cn": "九宫格", "text": f"洛书 {luoshu_info['description']}", "data": luoshu_info,
        })

        # 六十四卦（取代表性的）
        try:
            gua_list = kg.get_liushisi_gua()
            for g in gua_list[:64]:  # 最多64个
                text = f"六十四卦 {g['name']} 上卦:{g['upper_trigram']} 下卦:{g['lower_trigram']}"
                nodes.append({
                    "id": f"gua64:{g['name']}", "type": "六十四卦", "name": g['name'],
                    "name_cn": f"{g['upper_trigram']}+{g['lower_trigram']}", "text": text, "data": g,
                })
        except Exception:
            pass

        return nodes

    @staticmethod
    def _format_element(name: str, info: Dict) -> str:
        """格式化五行元素为文本"""
        parts = [f"五行 {name}"]
        for key in ["color", "direction", "season", "flavor", "organ", "sensory", "emotion", "sound", "description"]:
            if key in info:
                parts.append(f"{key}:{info[key]}")
        return " ".join(parts)

    def _build_index(self, vectors: np.ndarray, nodes: List[Dict]):
        """构建 FAISS 索引"""
        import faiss
        vectors = vectors.astype(np.float32)
        self._index = faiss.IndexFlatIP(self.dim)  # 内积 = 余弦相似度（归一化后）
        self._index.add(vectors)
        self._nodes = nodes
        self._initialized = True
        self._stats["total_nodes"] = len(nodes)
        self._stats["total_vectors"] = vectors.shape[0]

    # ── 语义搜索 ──────────────────────────────────────────────────────────

    def search(self, query: str, top_k: int = 10,
               type_filter: Optional[str] = None) -> SemanticSearchResult:
        """语义搜索

        Args:
            query: 搜索查询（自然语言）
            top_k: 返回结果数
            type_filter: 类型过滤（可选），如 "五行"、"八卦"、"天干" 等

        Returns:
            SemanticSearchResult
        """
        import time
        t0 = time.time()

        if not self._initialized:
            self._lazy_init()

        query_vec = self.embedder.embed(query).reshape(1, -1).astype(np.float32)
        k = min(top_k * 3, len(self._nodes))  # 多取一些做过滤
        distances, indices = self._index.search(query_vec, k)

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < 0 or idx >= len(self._nodes):
                continue
            node = self._nodes[idx]
            if type_filter and node.get("type") != type_filter:
                continue
            results.append({
                **node,
                "similarity": float(dist),
                "rank": len(results) + 1,
            })
            if len(results) >= top_k:
                break

        elapsed = (time.time() - t0) * 1000
        self._stats["search_count"] += 1
        avg = self._stats["avg_search_ms"]
        n = self._stats["search_count"]
        self._stats["avg_search_ms"] = avg + (elapsed - avg) / n

        return SemanticSearchResult(
            query=query,
            results=results,
            total_indexed=len(self._nodes),
            search_time_ms=elapsed,
        )

    def search_json(self, query: str, top_k: int = 10,
                    type_filter: Optional[str] = None) -> Dict[str, Any]:
        """语义搜索（JSON 格式）"""
        result = self.search(query, top_k, type_filter)
        return {
            "query": query,
            "total_indexed": result.total_indexed,
            "search_time_ms": round(result.search_time_ms, 2),
            "result_count": len(result.results),
            "results": [
                {
                    "rank": r["rank"],
                    "type": r["type"],
                    "name": r["name"],
                    "name_cn": r.get("name_cn", ""),
                    "similarity": round(r["similarity"], 4),
                    "text": r["text"][:200],
                }
                for r in result.results
            ],
        }

    # ── 知识关联推荐 ──────────────────────────────────────────────────────

    def recommend_related(self, node_name: str, top_k: int = 5,
                          exclude_self: bool = True) -> List[Dict[str, Any]]:
        """推荐相关知识节点

        Args:
            node_name: 节点名称（如 "木"、"乾"、"甲" 等）
            top_k: 返回结果数
            exclude_self: 是否排除自身

        Returns:
            相关节点列表
        """
        if not self._initialized:
            self._lazy_init()

        # 找到目标节点
        target_text = None
        target_type = None
        for node in self._nodes:
            if node["name"] == node_name:
                target_text = node["text"]
                target_type = node["type"]
                break

        if target_text is None:
            # 模糊匹配
            for node in self._nodes:
                if node_name in node["name"] or node_name in node.get("name_cn", ""):
                    target_text = node["text"]
                    target_type = node["type"]
                    break

        if target_text is None:
            return []

        result = self.search(target_text, top_k=top_k + 1, type_filter=None)
        recommendations = []
        for r in result.results:
            if exclude_self and r["name"] == node_name:
                continue
            recommendations.append({
                "type": r["type"],
                "name": r["name"],
                "name_cn": r.get("name_cn", ""),
                "similarity": round(r["similarity"], 4),
                "relation": self._infer_relation(node_name, r["name"]),
            })
            if len(recommendations) >= top_k:
                break

        return recommendations

    def _infer_relation(self, source: str, target: str) -> str:
        """推断两个知识节点之间的关系"""
        # 简单规则推断
        if source in _WUXING_ONEHOT and target in _WUXING_ONEHOT:
            # 五行生克
            sheng_order = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
            ke_order = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}
            if sheng_order.get(source) == target:
                return f"{source}生{target}（相生）"
            if sheng_order.get(target) == source:
                return f"{target}生{source}（被生）"
            if ke_order.get(source) == target:
                return f"{source}克{target}（相克）"
            if ke_order.get(target) == source:
                return f"{target}克{source}（被克）"
            return "同类"
        return "语义关联"

    # ── 索引管理 ──────────────────────────────────────────────────────────

    def _lazy_init(self):
        """懒初始化：自动从知识图谱构建"""
        self.build_from_knowledge_graph()

    def save(self, path: str):
        """保存索引到文件"""
        import faiss
        if not self._initialized:
            self._lazy_init()
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        faiss.write_index(self._index, path + ".index")
        with open(path + ".meta.json", "w", encoding="utf-8") as f:
            json.dump(self._nodes, f, ensure_ascii=False, indent=2)
        with open(path + ".stats.json", "w", encoding="utf-8") as f:
            json.dump(self._stats, f, ensure_ascii=False, indent=2)

    def load(self, path: str):
        """从文件加载索引"""
        import faiss
        self._index = faiss.read_index(path + ".index")
        with open(path + ".meta.json", "r", encoding="utf-8") as f:
            self._nodes = json.load(f)
        try:
            with open(path + ".stats.json", "r", encoding="utf-8") as f:
                self._stats = json.load(f)
        except FileNotFoundError:
            pass
        self._initialized = True

    @property
    def stats(self) -> Dict[str, Any]:
        return dict(self._stats)

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    def node_types(self) -> Dict[str, int]:
        """获取节点类型分布"""
        if not self._initialized:
            self._lazy_init()
        types = Counter(n["type"] for n in self._nodes)
        return dict(types)


# ============================================================================
# 全局单例
# ============================================================================

_vector_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """获取全局向量存储单例"""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
        _vector_store.build_from_knowledge_graph()
    return _vector_store


# ============================================================================
# 便捷函数
# ============================================================================

def build_knowledge_vectors() -> VectorStore:
    """构建知识向量索引"""
    store = VectorStore()
    count = store.build_from_knowledge_graph()
    print(f"✅ 向量索引构建完成: {count} 个节点, {store.dim} 维")
    return store


def search_similar(query: str, top_k: int = 10) -> Dict[str, Any]:
    """语义搜索便捷函数"""
    store = get_vector_store()
    return store.search_json(query, top_k)


def recommend_related(node_name: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """知识关联推荐便捷函数"""
    store = get_vector_store()
    return store.recommend_related(node_name, top_k)


# ============================================================================
# CLI 测试
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("向量存储与语义检索引擎 v1.0.0")
    print("=" * 60)

    # 构建索引
    store = build_knowledge_vectors()
    print(f"\n节点类型分布: {store.node_types()}")

    # 语义搜索测试
    test_queries = [
        "找所有属木的概念",
        "与火相关的知识",
        "东方方位",
        "生克关系",
        "春天",
        "阴阳",
        "天干地支",
        "身体部位",
        "八卦中的乾",
        "水元素的特性",
        "地支三合",
        "十神中的正官",
    ]

    print("\n" + "=" * 60)
    print("语义搜索测试")
    print("=" * 60)
    for query in test_queries:
        result = store.search(query, top_k=3)
        print(f"\n🔍 \"{query}\"")
        for r in result.results:
            bar = "█" * int(r["similarity"] * 20) + "░" * (20 - int(r["similarity"] * 20))
            print(f"  [{r['type']}] {r['name']} ({r['name_cn']}) {bar} {r['similarity']:.3f}")

    # 知识关联推荐测试
    print("\n" + "=" * 60)
    print("知识关联推荐测试")
    print("=" * 60)
    for node in ["木", "乾", "甲", "子", "正官", "河图"]:
        recs = store.recommend_related(node, top_k=5)
        print(f"\n📎 \"{node}\" 相关推荐:")
        for r in recs:
            print(f"  [{r['type']}] {r['name']} ({r['name_cn']}) → {r['relation']} (相似度:{r['similarity']:.3f})")

    print(f"\n{store._stats}")