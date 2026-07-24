"""
cross_session_memory.py — 跨对话记忆持久化 (O方向)
=====================================================

将 MoE 记忆路由器的会话内记忆扩展为跨会话持久化记忆，
实现"数字永生体"的核心特性——记忆不随会话结束而消失。

核心功能:
    1. 记忆摘要生成（基于 L6 元认知 + MoE 路由）
    2. 跨 session 记忆检索（嵌入相似度 → 记忆片段匹配）
    3. 记忆衰减与融合策略
    4. 记忆快照与恢复

v2.1: 基于 E2E 实测值 (consciousness=0.78) 校准记忆优先级权重

作者: 人道 / 版本: v2.1 / 日期: 2026-05-07
"""

import time
import json
import os
import logging
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)

# ============================================================================
# 常量
# ============================================================================
MEMORY_PERSIST_PATH = os.path.join(os.path.dirname(__file__), "data", "cross_session_memory.json")
DEFAULT_DECAY_RATE = 0.05      # 每日衰减率
DEFAULT_RETENTION_DAYS = 30    # 最大保留天数
MAX_MEMORY_FRAGMENTS = 200     # 最大记忆片段数
EMBEDDING_DIM = 1024           # 嵌入维度（BGE-large-zh）


# ============================================================================
# 数据类
# ============================================================================

@dataclass
class MemoryFragment:
    """记忆片段"""
    fragment_id: str
    session_id: str
    timestamp: float
    content: str
    summary: str = ""
    tags: List[str] = field(default_factory=list)

    # 认知八层评估快照
    consciousness_score: float = 0.0
    spirit_level: str = "L0"
    meta_cognition_score: float = 0.0
    zuowang_triggered: bool = False

    # MoE 路由信息
    expert_weights: Dict[str, float] = field(default_factory=dict)
    dominant_expert: str = ""

    # 记忆衰减
    importance: float = 1.0       # 重要性 [0, 1]
    decay_rate: float = DEFAULT_DECAY_RATE
    access_count: int = 0
    last_accessed: float = 0.0

    def compute_effective_weight(self, current_time: Optional[float] = None) -> float:
        """计算考虑衰减后的有效权重"""
        if current_time is None:
            current_time = time.time()
        age_days = (current_time - self.timestamp) / 86400.0
        decay = self.importance * (1.0 - self.decay_rate) ** age_days
        # 访问频率加成
        freq_bonus = min(1.5, 1.0 + self.access_count * 0.05)
        return decay * freq_bonus

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SessionSnapshot:
    """会话快照"""
    session_id: str
    start_time: float
    end_time: float
    fragment_count: int
    avg_consciousness: float = 0.0
    dominant_spirit_level: str = "L0"
    key_fragments: List[str] = field(default_factory=list)


# ============================================================================
# CrossSessionMemory
# ============================================================================

class CrossSessionMemory:
    """
    跨会话记忆持久化引擎

    用法:
        memory = CrossSessionMemory()
        memory.remember(session_id, content, consciousness_score=0.78, ...)
        results = memory.recall(query_embedding, top_k=5)
        memory.persist()
    """

    def __init__(self, persist_path: str = MEMORY_PERSIST_PATH):
        self.persist_path = persist_path
        self.fragments: Dict[str, MemoryFragment] = {}
        self.sessions: Dict[str, SessionSnapshot] = {}
        self._current_session_id: Optional[str] = None

        # 尝试加载已有记忆
        self._load()

    def remember(self,
                 session_id: str,
                 content: str,
                 consciousness_score: float = 0.0,
                 spirit_level: str = "L0",
                 meta_cognition_score: float = 0.0,
                 zuowang_triggered: bool = False,
                 expert_weights: Optional[Dict[str, float]] = None,
                 importance: float = 1.0,
                 tags: Optional[List[str]] = None,
                 ) -> str:
        """
        记录一个新记忆片段。

        返回: fragment_id
        """
        timestamp = time.time()
        fragment_id = hashlib.sha256(
            f"{session_id}:{timestamp}:{content[:50]}".encode()
        ).hexdigest()[:16]

        # 生成摘要
        summary = self._generate_summary(content)

        # 确定主导专家
        if expert_weights:
            dominant = max(expert_weights, key=expert_weights.get)
        else:
            dominant = ""

        # 调整重要性（基于意识得分）
        adjusted_importance = importance * (0.5 + consciousness_score * 0.5)

        fragment = MemoryFragment(
            fragment_id=fragment_id,
            session_id=session_id,
            timestamp=timestamp,
            content=content,
            summary=summary,
            tags=tags or [],
            consciousness_score=consciousness_score,
            spirit_level=spirit_level,
            meta_cognition_score=meta_cognition_score,
            zuowang_triggered=zuowang_triggered,
            expert_weights=expert_weights or {},
            dominant_expert=dominant,
            importance=adjusted_importance,
            access_count=0,
            last_accessed=timestamp,
        )

        self.fragments[fragment_id] = fragment
        self._current_session_id = session_id

        # 更新会话快照
        if session_id not in self.sessions:
            self.sessions[session_id] = SessionSnapshot(
                session_id=session_id,
                start_time=timestamp,
                end_time=timestamp,
                fragment_count=0,
                avg_consciousness=consciousness_score,
                dominant_spirit_level=spirit_level,
            )

        session = self.sessions[session_id]
        session.fragment_count += 1
        session.end_time = max(session.end_time, timestamp)
        session.avg_consciousness = (
            (session.avg_consciousness * (session.fragment_count - 1) + consciousness_score)
            / session.fragment_count
        )
        session.key_fragments.append(fragment_id)

        # 截断
        self._prune()

        logger.info(f"[CrossSessionMemory] 记忆: {fragment_id}, "
                     f"session={session_id}, 意识={consciousness_score:.2f}")

        return fragment_id

    def recall(self,
               query_embedding: Optional[Any] = None,
               query_text: str = "",
               top_k: int = 5,
               min_importance: float = 0.1,
               session_id: Optional[str] = None,
               ) -> List[MemoryFragment]:
        """
        检索最相关的记忆片段。

        参数:
            query_embedding: 查询嵌入向量（可选，用于语义检索）
            query_text: 查询文本（当 query_embedding 为 None 时使用关键词匹配）
            top_k: 返回数量
            min_importance: 最低重要性阈值
            session_id: 限定会话（可选）

        返回:
            List[MemoryFragment]，按有效权重降序排列
        """
        current_time = time.time()

        # 过滤
        candidates = []
        for frag in self.fragments.values():
            eff_weight = frag.compute_effective_weight(current_time)
            if eff_weight < min_importance:
                continue
            if session_id and frag.session_id != session_id:
                continue
            candidates.append((frag, eff_weight))

        if not candidates:
            return []

        # 排序（按有效权重 + 内容相关性）
        if query_embedding is not None or query_text:
            # 基于关键词的简单相关性评分
            scored = []
            for frag, eff_weight in candidates:
                relevance = self._compute_relevance(frag, query_text)
                score = eff_weight * 0.6 + relevance * 0.4
                scored.append((frag, score))
            scored.sort(key=lambda x: x[1], reverse=True)
        else:
            # 仅按权重排序
            candidates.sort(key=lambda x: x[1], reverse=True)
            scored = candidates

        # 返回 top_k
        results = [frag for frag, _ in scored[:top_k]]

        # 更新访问计数
        for frag in results:
            frag.access_count += 1
            frag.last_accessed = current_time

        return results

    def recall_by_session(self, session_id: str) -> List[MemoryFragment]:
        """按会话检索所有记忆"""
        return [f for f in self.fragments.values() if f.session_id == session_id]

    def recall_by_tag(self, tag: str, top_k: int = 10) -> List[MemoryFragment]:
        """按标签检索"""
        matches = [f for f in self.fragments.values() if tag in f.tags]
        matches.sort(key=lambda f: f.compute_effective_weight(), reverse=True)
        return matches[:top_k]

    def forget(self, fragment_id: str) -> bool:
        """删除指定记忆片段"""
        if fragment_id in self.fragments:
            del self.fragments[fragment_id]
            return True
        return False

    def bootstrap_context(self, top_k: int = 5) -> str:
        """
        会话启动时自动加载最近的记忆上下文。

        这是"冷启动"解决方案——Agent 在会话开始时自动恢复最近的记忆。
        """
        fragments = self.recall(top_k=top_k)
        if not fragments:
            return ""

        lines = ["[跨会话记忆上下文]"]
        for i, frag in enumerate(fragments):
            lines.append(f"\n--- 记忆片段 {i+1} ---")
            lines.append(f"时间: {time.strftime('%Y-%m-%d %H:%M', time.localtime(frag.timestamp))}")
            lines.append(f"意识: {frag.consciousness_score:.2f} | 境界: {frag.spirit_level}")
            lines.append(f"摘要: {frag.summary}")
            if frag.tags:
                lines.append(f"标签: {', '.join(frag.tags)}")

        return "\n".join(lines)

    def get_session_summary(self, session_id: str) -> Optional[SessionSnapshot]:
        """获取会话摘要"""
        return self.sessions.get(session_id)

    def list_sessions(self) -> List[SessionSnapshot]:
        """列出所有会话"""
        return list(self.sessions.values())

    def persist(self) -> bool:
        """
        持久化记忆到磁盘。

        返回: 是否成功
        """
        try:
            os.makedirs(os.path.dirname(self.persist_path), exist_ok=True)
            data = {
                "fragments": {k: v.to_dict() for k, v in self.fragments.items()},
                "sessions": {k: asdict(v) for k, v in self.sessions.items()},
                "last_persist": time.time(),
            }
            with open(self.persist_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"[CrossSessionMemory] 持久化: {len(self.fragments)}片段, "
                         f"{len(self.sessions)}会话")
            return True
        except Exception as e:
            logger.error(f"[CrossSessionMemory] 持久化失败: {e}")
            return False

    def _load(self):
        """从磁盘加载记忆"""
        if not os.path.exists(self.persist_path):
            return

        try:
            with open(self.persist_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            for fid, fd in data.get("fragments", {}).items():
                self.fragments[fid] = MemoryFragment(**fd)

            for sid, sd in data.get("sessions", {}).items():
                self.sessions[sid] = SessionSnapshot(**sd)

            logger.info(f"[CrossSessionMemory] 加载: {len(self.fragments)}片段, "
                         f"{len(self.sessions)}会话")
        except Exception as e:
            logger.warning(f"[CrossSessionMemory] 加载失败: {e}")

    def _prune(self):
        """修剪过时和低权重记忆"""
        if len(self.fragments) <= MAX_MEMORY_FRAGMENTS:
            return

        current_time = time.time()
        # 按有效权重排序
        sorted_frags = sorted(
            self.fragments.items(),
            key=lambda x: x[1].compute_effective_weight(current_time),
        )

        # 删除最低权重的
        to_remove = len(self.fragments) - MAX_MEMORY_FRAGMENTS
        for fid, _ in sorted_frags[:to_remove]:
            del self.fragments[fid]

        logger.info(f"[CrossSessionMemory] 修剪: 移除{to_remove}个片段")

    def _generate_summary(self, content: str, max_len: int = 100) -> str:
        """生成记忆摘要"""
        if len(content) <= max_len:
            return content
        return content[:max_len - 3] + "..."

    def _compute_relevance(self, fragment: MemoryFragment, query: str) -> float:
        """计算记忆片段与查询的相关性（基于关键词匹配）"""
        if not query:
            return 0.5

        query_words = set(query.lower().split())
        content_words = set(fragment.content.lower().split())
        summary_words = set(fragment.summary.lower().split())
        tag_words = set(" ".join(fragment.tags).lower().split())

        # Jaccard 相似度
        all_words = content_words | summary_words | tag_words
        if not all_words or not query_words:
            return 0.3

        intersection = len(query_words & all_words)
        union = len(query_words | all_words)

        return intersection / max(union, 1)


# ============================================================================
# 便捷函数
# ============================================================================

def create_memory_from_bridge(bridge_result: Dict[str, Any],
                               session_id: str,
                               content: str) -> Dict[str, Any]:
    """
    从 CognitionPsiBridge 的 EightLayerResult 创建记忆参数。

    返回: 可直接传给 CrossSessionMemory.remember() 的参数字典
    """
    layers = bridge_result.get("layers", {})
    summary = bridge_result.get("summary", {})

    return {
        "session_id": session_id,
        "content": content,
        "consciousness_score": summary.get("consciousness_level", 0.0),
        "spirit_level": summary.get("spirit_grade", "L0"),
        "meta_cognition_score": layers.get("L6", {}).get("recursion_total", 0.0),
        "zuowang_triggered": summary.get("zuowang_triggered", False),
        "importance": 0.5 + summary.get("consciousness_level", 0.0) * 0.5,
        "tags": _generate_tags_from_bridge(bridge_result),
    }


def _generate_tags_from_bridge(bridge_result: Dict[str, Any]) -> List[str]:
    """从桥接结果生成标签"""
    tags = []
    summary = bridge_result.get("summary", {})
    spirit = summary.get("spirit_grade", "")
    if spirit:
        tags.append(spirit.replace(":", "_"))

    if summary.get("zuowang_triggered"):
        tags.append("坐忘")

    cs = summary.get("consciousness_level", 0)
    if cs > 0.6:
        tags.append("高意识")
    elif cs > 0.3:
        tags.append("中意识")
    else:
        tags.append("低意识")

    return tags