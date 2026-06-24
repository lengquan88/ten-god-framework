"""
knowledge_evolution.py — 知识进化系统 v2.9
=============================================
反馈闭环 → 置信度动态调整 → 知识图谱自动补全

核心能力：
  - 用户反馈收集与分析（满意度/准确度/有用性三维度）
  - 置信度动态调整（贝叶斯式持续更新）
  - 知识图谱自动补全（规则推理 + 关联发现）
  - 进化统计与审计追踪

用法：
  >>> from tengod.knowledge_evolution import KnowledgeEvolution
  >>> ke = KnowledgeEvolution()
  >>> ke.collect_feedback(session_id, {"accuracy": 4, "satisfaction": 5})
  >>> ke.evolve()
  >>> stats = ke.get_evolution_stats()
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Set, Tuple
from collections import defaultdict
import json
import time


# ============================================================================
# 常量定义
# ============================================================================

# 五行生克关系
WUXING_SHENG = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
WUXING_KE = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}

# 知识领域定义
KNOWLEDGE_DOMAINS = [
    "bazi",        # 八字命理
    "ziwei",       # 紫微斗数
    "qimen",       # 奇门遁甲
    "liuyao",      # 六爻占卜
    "fengshui",    # 风水
    "name",        # 姓名学
    "marriage",    # 合婚
    "fusion",      # 融合分析
    "oracle",      # 推背图
]

# 十二地支
DIZHI = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

# 地支六合
DIZHI_HE = {
    "子": "丑", "丑": "子", "寅": "亥", "亥": "寅",
    "卯": "戌", "戌": "卯", "辰": "酉", "酉": "辰",
    "巳": "申", "申": "巳", "午": "未", "未": "午",
}

# 地支三合
DIZHI_SANHE = [
    {"申", "子", "辰"},  # 水局
    {"亥", "卯", "未"},  # 木局
    {"寅", "午", "戌"},  # 火局
    {"巳", "酉", "丑"},  # 金局
]

# 十神关系
SHIGAN_NAMES = ["比肩", "劫财", "食神", "伤官", "偏财", "正财", "七杀", "正官", "偏印", "正印"]


# ============================================================================
# 数据结构
# ============================================================================

@dataclass
class FeedbackRecord:
    """用户反馈记录"""
    session_id: str
    timestamp: float = field(default_factory=time.time)
    domain: str = "general"               # 知识领域
    accuracy: int = 3                      # 准确度评分 1-5
    satisfaction: int = 3                  # 满意度评分 1-5
    usefulness: int = 3                    # 有用性评分 1-5
    comment: str = ""                      # 文字反馈
    analysis_type: str = ""                # 分析类型（bazi/ziwei/...）
    corrections: List[Dict[str, str]] = field(default_factory=list)  # 用户纠正
    tags: List[str] = field(default_factory=list)

    def overall_score(self) -> float:
        """综合反馈评分"""
        return (self.accuracy + self.satisfaction + self.usefulness) / 3.0

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class ConfidenceProfile:
    """置信度配置"""
    domain: str
    base_confidence: float = 0.5           # 基础置信度
    current_confidence: float = 0.5        # 当前置信度
    feedback_count: int = 0                # 反馈次数
    positive_count: int = 0                # 正面反馈次数
    last_updated: float = field(default_factory=time.time)
    adjustments: List[Dict] = field(default_factory=list)  # 调整历史

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class KnowledgeNode:
    """知识图谱节点"""
    id: str
    domain: str
    concept: str
    confidence: float = 0.5
    properties: Dict[str, Any] = field(default_factory=dict)
    sources: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class KnowledgeEdge:
    """知识图谱边"""
    source_id: str
    target_id: str
    relation: str                         # 关系类型：correlates/causes/contradicts/supports
    weight: float = 0.5                   # 边权重
    confidence: float = 0.5
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class EvolutionResult:
    """进化结果"""
    domain: str
    action: str                           # adjusted/completed/discovered
    before_confidence: float
    after_confidence: float
    new_nodes: List[str] = field(default_factory=list)
    new_edges: List[Tuple[str, str, str]] = field(default_factory=list)
    description: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict:
        return {
            "domain": self.domain,
            "action": self.action,
            "before_confidence": self.before_confidence,
            "after_confidence": self.after_confidence,
            "new_nodes": self.new_nodes,
            "new_edges": [{"source": s, "target": t, "relation": r} for s, t, r in self.new_edges],
            "description": self.description,
            "timestamp": self.timestamp,
        }


# ============================================================================
# 知识进化引擎
# ============================================================================

class KnowledgeEvolution:
    """知识进化引擎

    核心循环：
    1. 收集反馈 → 分析满意度/准确度模式
    2. 调整置信度 → 贝叶斯式更新各领域置信度
    3. 自动补全 → 基于规则推理发现新知识关联
    4. 进化审计 → 记录所有变更，支持回滚
    """

    def __init__(self):
        # 反馈存储
        self._feedbacks: List[FeedbackRecord] = []

        # 置信度配置
        self._confidence_profiles: Dict[str, ConfidenceProfile] = {
            domain: ConfidenceProfile(domain=domain)
            for domain in KNOWLEDGE_DOMAINS
        }

        # 知识图谱
        self._nodes: Dict[str, KnowledgeNode] = {}
        self._edges: List[KnowledgeEdge] = []

        # 进化历史
        self._evolution_history: List[EvolutionResult] = []

        # 初始化种子知识图谱
        self._init_seed_knowledge()

    # ── 种子知识图谱 ──────────────────────────────────────────────────────

    def _init_seed_knowledge(self) -> None:
        """初始化种子知识节点"""
        seeds = [
            # 八字基础节点
            ("bazi_gan", "bazi", "十天干", {"values": ["甲","乙","丙","丁","戊","己","庚","辛","壬","癸"]}),
            ("bazi_zhi", "bazi", "十二地支", {"values": DIZHI}),
            ("bazi_wuxing", "bazi", "五行", {"values": list(WUXING_SHENG.keys())}),
            ("bazi_shigan", "bazi", "十神", {"values": SHIGAN_NAMES}),
            ("bazi_shengke", "bazi", "生克关系", {"sheng": WUXING_SHENG, "ke": WUXING_KE}),
            # 紫微基础节点
            ("zw_stars", "ziwei", "紫微星曜", {"main": ["紫微","天机","太阳","武曲","天同","廉贞","天府","太阴","贪狼","巨门","天相","天梁","七杀","破军"]}),
            ("zw_palaces", "ziwei", "十二宫位", {"values": ["命宫","兄弟","夫妻","子女","财帛","疾厄","迁移","交友","事业","田宅","福德","父母"]}),
            ("zw_sihua", "ziwei", "四化", {"values": ["化禄","化权","化科","化忌"]}),
            # 奇门基础节点
            ("qm_men", "qimen", "八门", {"values": ["休","生","伤","杜","景","死","惊","开"]}),
            ("qm_stars", "qimen", "九星", {"values": ["天蓬","天芮","天冲","天辅","天禽","天心","天柱","天任","天英"]}),
            ("qm_shen", "qimen", "八神", {"values": ["值符","腾蛇","太阴","六合","白虎","玄武","九地","九天"]}),
            # 六爻基础节点
            ("ly_bagua", "liuyao", "八卦", {"values": ["乾","坤","震","巽","坎","离","艮","兑"]}),
            ("ly_liuqin", "liuyao", "六亲", {"values": ["父母","兄弟","妻财","官鬼","子孙"]}),
            ("ly_liushen", "liuyao", "六神", {"values": ["青龙","朱雀","勾陈","腾蛇","白虎","玄武"]}),
            # 风水基础节点
            ("fs_directions", "fengshui", "二十四山", {}),
            ("fs_feixing", "fengshui", "玄空飞星", {}),
            # 融合节点
            ("fusion_cross", "fusion", "交叉验证", {"systems": ["bazi","ziwei","qimen"]}),
            ("fusion_weights", "fusion", "体系权重", {"bazi": 0.45, "ziwei": 0.35, "qimen": 0.20}),
        ]

        for node_id, domain, concept, props in seeds:
            self._nodes[node_id] = KnowledgeNode(
                id=node_id, domain=domain, concept=concept,
                confidence=0.8, properties=props,
            )

        # 种子边
        seed_edges = [
            ("bazi_gan", "bazi_wuxing", "belongs_to", 0.9),
            ("bazi_zhi", "bazi_wuxing", "belongs_to", 0.9),
            ("bazi_wuxing", "bazi_shengke", "governs", 0.9),
            ("bazi_shigan", "bazi_gan", "derived_from", 0.8),
            ("zw_stars", "bazi_wuxing", "correlates", 0.6),
            ("qm_men", "bazi_wuxing", "correlates", 0.5),
            ("ly_bagua", "bazi_wuxing", "correlates", 0.7),
            ("fusion_cross", "bazi_wuxing", "supports", 0.8),
            ("fusion_cross", "zw_stars", "supports", 0.7),
            ("fusion_cross", "qm_men", "supports", 0.6),
        ]

        for src, tgt, rel, w in seed_edges:
            self._edges.append(KnowledgeEdge(
                source_id=src, target_id=tgt, relation=rel, weight=w, confidence=0.8,
            ))

    # ── 反馈收集 ──────────────────────────────────────────────────────────

    def collect_feedback(
        self,
        session_id: str,
        ratings: Dict[str, Any],
        domain: str = "general",
        comment: str = "",
        analysis_type: str = "",
        corrections: Optional[List[Dict[str, str]]] = None,
    ) -> FeedbackRecord:
        """收集用户反馈

        Args:
            session_id: 会话ID
            ratings: 评分字典，包含 accuracy/satisfaction/usefulness
            domain: 知识领域
            comment: 文字反馈
            analysis_type: 分析类型
            corrections: 用户纠正列表

        Returns:
            FeedbackRecord
        """
        record = FeedbackRecord(
            session_id=session_id,
            domain=domain,
            accuracy=ratings.get("accuracy", 3),
            satisfaction=ratings.get("satisfaction", 3),
            usefulness=ratings.get("usefulness", 3),
            comment=comment,
            analysis_type=analysis_type,
            corrections=corrections or [],
            tags=self._extract_tags(comment),
        )

        self._feedbacks.append(record)

        # 实时调整置信度
        self._update_confidence_from_feedback(record)

        return record

    def _extract_tags(self, comment: str) -> List[str]:
        """从文字反馈中提取标签"""
        tags = []
        keywords = {
            "准确": "accurate", "准": "accurate", "很对": "accurate",
            "不准": "inaccurate", "错误": "inaccurate", "不对": "inaccurate",
            "有用": "useful", "很有帮助": "useful",
            "没用": "useless", "无用": "useless",
            "太复杂": "too_complex", "难懂": "hard_to_understand",
            "简单": "simple", "清晰": "clear",
        }
        for kw, tag in keywords.items():
            if kw in comment:
                tags.append(tag)
        return tags

    # ── 置信度调整 ────────────────────────────────────────────────────────

    def _update_confidence_from_feedback(self, feedback: FeedbackRecord) -> None:
        """根据反馈实时更新置信度"""
        domain = feedback.domain if feedback.domain in self._confidence_profiles else "general"
        if domain not in self._confidence_profiles:
            return

        profile = self._confidence_profiles[domain]
        score = feedback.overall_score()

        # 贝叶斯式更新
        alpha = 0.1  # 学习率
        target = score / 5.0  # 归一化到 [0, 1]

        old_conf = profile.current_confidence
        new_conf = old_conf * (1 - alpha) + target * alpha

        profile.current_confidence = round(new_conf, 4)
        profile.feedback_count += 1
        if score >= 3.5:
            profile.positive_count += 1
        profile.last_updated = time.time()
        profile.adjustments.append({
            "timestamp": feedback.timestamp,
            "score": score,
            "old_confidence": old_conf,
            "new_confidence": new_conf,
            "session_id": feedback.session_id,
        })

    def adjust_confidence(
        self,
        domain: str,
        adjustment: float,
        reason: str = "",
    ) -> ConfidenceProfile:
        """手动调整置信度

        Args:
            domain: 知识领域
            adjustment: 调整量 [-1.0, 1.0]
            reason: 调整原因

        Returns:
            更新后的 ConfidenceProfile
        """
        if domain not in self._confidence_profiles:
            self._confidence_profiles[domain] = ConfidenceProfile(domain=domain)

        profile = self._confidence_profiles[domain]
        old_conf = profile.current_confidence
        new_conf = max(0.0, min(1.0, old_conf + adjustment))
        profile.current_confidence = round(new_conf, 4)
        profile.last_updated = time.time()
        profile.adjustments.append({
            "timestamp": time.time(),
            "manual": True,
            "adjustment": adjustment,
            "reason": reason,
            "old_confidence": old_conf,
            "new_confidence": new_conf,
        })

        return profile

    def get_confidence(self, domain: str) -> float:
        """获取领域置信度"""
        profile = self._confidence_profiles.get(domain)
        return profile.current_confidence if profile else 0.5

    def get_all_confidences(self) -> Dict[str, float]:
        """获取所有领域置信度"""
        return {d: p.current_confidence for d, p in self._confidence_profiles.items()}

    # ── 知识图谱操作 ──────────────────────────────────────────────────────

    def add_node(
        self,
        node_id: str,
        domain: str,
        concept: str,
        confidence: float = 0.5,
        properties: Optional[Dict] = None,
    ) -> KnowledgeNode:
        """添加知识节点"""
        node = KnowledgeNode(
            id=node_id, domain=domain, concept=concept,
            confidence=confidence, properties=properties or {},
        )
        self._nodes[node_id] = node
        return node

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        relation: str,
        weight: float = 0.5,
        confidence: float = 0.5,
    ) -> Optional[KnowledgeEdge]:
        """添加知识边"""
        if source_id not in self._nodes or target_id not in self._nodes:
            return None

        edge = KnowledgeEdge(
            source_id=source_id, target_id=target_id,
            relation=relation, weight=weight, confidence=confidence,
        )
        self._edges.append(edge)
        return edge

    def get_node(self, node_id: str) -> Optional[KnowledgeNode]:
        """获取节点"""
        return self._nodes.get(node_id)

    def get_neighbors(self, node_id: str) -> List[Tuple[KnowledgeNode, KnowledgeEdge]]:
        """获取节点的所有邻居"""
        neighbors = []
        for edge in self._edges:
            if edge.source_id == node_id:
                target = self._nodes.get(edge.target_id)
                if target:
                    neighbors.append((target, edge))
            elif edge.target_id == node_id:
                source = self._nodes.get(edge.source_id)
                if source:
                    neighbors.append((source, edge))
        return neighbors

    # ── 知识图谱自动补全 ──────────────────────────────────────────────────

    def auto_complete_knowledge(self) -> List[EvolutionResult]:
        """知识图谱自动补全

        基于规则推理发现新知识关联：
        1. 传递推理：A→B 且 B→C → A→C
        2. 对称推理：已知 A correlates B → B correlates A
        3. 跨域推理：同一五行不同领域节点关联
        """
        results = []

        # 1. 传递推理
        trans_results = self._transitive_inference()
        results.extend(trans_results)

        # 2. 跨域关联
        cross_results = self._cross_domain_inference()
        results.extend(cross_results)

        # 3. 对称补全
        sym_results = self._symmetry_completion()
        results.extend(sym_results)

        self._evolution_history.extend(results)
        return results

    def _transitive_inference(self) -> List[EvolutionResult]:
        """传递推理：A→B ∧ B→C ⇒ A→C"""
        results = []

        edge_map: Dict[str, List[KnowledgeEdge]] = defaultdict(list)
        for edge in self._edges:
            edge_map[edge.source_id].append(edge)

        new_edges = []
        for edge in self._edges:
            for next_edge in edge_map.get(edge.target_id, []):
                # 避免自环
                if edge.source_id == next_edge.target_id:
                    continue
                # 检查是否已存在
                exists = any(
                    e.source_id == edge.source_id
                    and e.target_id == next_edge.target_id
                    for e in self._edges + new_edges
                )
                if not exists:
                    derived_weight = edge.weight * next_edge.weight * 0.7
                    derived_conf = edge.confidence * next_edge.confidence * 0.6
                    if derived_weight >= 0.2:
                        new_edge = KnowledgeEdge(
                            source_id=edge.source_id,
                            target_id=next_edge.target_id,
                            relation="inferred",
                            weight=round(derived_weight, 3),
                            confidence=round(derived_conf, 3),
                        )
                        new_edges.append(new_edge)

        for ne in new_edges:
            self._edges.append(ne)
            results.append(EvolutionResult(
                domain="fusion",
                action="discovered",
                before_confidence=0,
                after_confidence=ne.confidence,
                new_edges=[(ne.source_id, ne.target_id, ne.relation)],
                description=f"传递推理发现：{ne.source_id} → {ne.target_id}",
            ))

        return results

    def _cross_domain_inference(self) -> List[EvolutionResult]:
        """跨域关联推理"""
        results = []

        # 按五行分组
        wuxing_groups: Dict[str, List[str]] = defaultdict(list)
        for node_id, node in self._nodes.items():
            props = node.properties
            for key in ["wuxing", "values"]:
                if key in props:
                    vals = props[key]
                    if isinstance(vals, list):
                        for v in vals:
                            if v in WUXING_SHENG:
                                wuxing_groups[v].append(node_id)

        # 同五行不同域节点建立关联
        for wx, node_ids in wuxing_groups.items():
            domains = set()
            for nid in node_ids:
                node = self._nodes.get(nid)
                if node:
                    domains.add(node.domain)

            if len(domains) >= 2:
                for i, nid1 in enumerate(node_ids):
                    for nid2 in node_ids[i + 1:]:
                        n1 = self._nodes[nid1]
                        n2 = self._nodes[nid2]
                        if n1.domain != n2.domain:
                            exists = any(
                                (e.source_id == nid1 and e.target_id == nid2)
                                or (e.source_id == nid2 and e.target_id == nid1)
                                for e in self._edges
                            )
                            if not exists:
                                edge = KnowledgeEdge(
                                    source_id=nid1, target_id=nid2,
                                    relation="wuxing_correlates",
                                    weight=0.5, confidence=0.5,
                                )
                                self._edges.append(edge)
                                results.append(EvolutionResult(
                                    domain="fusion",
                                    action="discovered",
                                    before_confidence=0,
                                    after_confidence=0.5,
                                    new_edges=[(nid1, nid2, "wuxing_correlates")],
                                    description=f"跨域五行关联：{nid1} ↔ {nid2}（{wx}）",
                                ))

        return results

    def _symmetry_completion(self) -> List[EvolutionResult]:
        """对称补全"""
        results = []

        existing_pairs = set()
        for edge in self._edges:
            existing_pairs.add((edge.source_id, edge.target_id))

        symmetric_relations = {"correlates", "wuxing_correlates", "belongs_to"}

        new_edges = []
        for edge in self._edges:
            if edge.relation not in symmetric_relations:
                continue
            reverse = (edge.target_id, edge.source_id)
            if reverse not in existing_pairs:
                new_edge = KnowledgeEdge(
                    source_id=edge.target_id,
                    target_id=edge.source_id,
                    relation=edge.relation,
                    weight=edge.weight,
                    confidence=edge.confidence,
                )
                new_edges.append(new_edge)
                existing_pairs.add(reverse)

        for ne in new_edges:
            self._edges.append(ne)
            results.append(EvolutionResult(
                domain="fusion",
                action="discovered",
                before_confidence=0,
                after_confidence=ne.confidence,
                new_edges=[(ne.source_id, ne.target_id, ne.relation)],
                description=f"对称补全：{ne.source_id} ↔ {ne.target_id}",
            ))

        return results

    # ── 进化主循环 ────────────────────────────────────────────────────────

    def evolve(self) -> List[EvolutionResult]:
        """执行知识进化主循环

        1. 分析反馈趋势
        2. 调整置信度
        3. 自动补全知识图谱

        Returns:
            本轮进化结果列表
        """
        results = []

        # 1. 分析反馈趋势，批量调整置信度
        if self._feedbacks:
            domain_feedbacks: Dict[str, List[FeedbackRecord]] = defaultdict(list)
            for fb in self._feedbacks[-100:]:  # 最近 100 条
                domain_feedbacks[fb.domain].append(fb)

            for domain, fbs in domain_feedbacks.items():
                if domain in self._confidence_profiles:
                    avg_score = sum(fb.overall_score() for fb in fbs) / len(fbs)
                    target = avg_score / 5.0
                    profile = self._confidence_profiles[domain]
                    old_conf = profile.current_confidence
                    # 批量调整：学习率随反馈量增大
                    lr = min(0.3, 0.05 + len(fbs) * 0.01)
                    new_conf = old_conf * (1 - lr) + target * lr
                    profile.current_confidence = round(new_conf, 4)
                    profile.last_updated = time.time()

                    results.append(EvolutionResult(
                        domain=domain,
                        action="adjusted",
                        before_confidence=old_conf,
                        after_confidence=new_conf,
                        description=f"基于{len(fbs)}条反馈调整置信度：{old_conf:.3f} → {new_conf:.3f}",
                    ))

        # 2. 自动补全知识图谱
        auto_results = self.auto_complete_knowledge()
        results.extend(auto_results)

        self._evolution_history.extend(results)
        return results

    # ── 统计与查询 ────────────────────────────────────────────────────────

    def get_evolution_stats(self) -> Dict[str, Any]:
        """获取进化统计"""
        total_feedback = len(self._feedbacks)
        avg_score = 0.0
        if total_feedback > 0:
            avg_score = sum(fb.overall_score() for fb in self._feedbacks) / total_feedback

        domain_stats = {}
        for domain, profile in self._confidence_profiles.items():
            domain_fbs = [fb for fb in self._feedbacks if fb.domain == domain]
            domain_stats[domain] = {
                "confidence": profile.current_confidence,
                "base_confidence": profile.base_confidence,
                "feedback_count": len(domain_fbs),
                "positive_rate": (
                    profile.positive_count / profile.feedback_count
                    if profile.feedback_count > 0 else 0
                ),
                "adjustments": len(profile.adjustments),
            }

        return {
            "total_feedback": total_feedback,
            "average_score": round(avg_score, 2),
            "total_nodes": len(self._nodes),
            "total_edges": len(self._edges),
            "total_evolutions": len(self._evolution_history),
            "domains": domain_stats,
            "recent_evolutions": [
                ev.to_dict() for ev in self._evolution_history[-5:]
            ],
        }

    def get_feedback_trend(self, domain: str = "", limit: int = 20) -> List[Dict]:
        """获取反馈趋势"""
        fbs = self._feedbacks
        if domain:
            fbs = [fb for fb in fbs if fb.domain == domain]
        return [
            {
                "timestamp": fb.timestamp,
                "score": round(fb.overall_score(), 2),
                "accuracy": fb.accuracy,
                "satisfaction": fb.satisfaction,
                "usefulness": fb.usefulness,
                "domain": fb.domain,
            }
            for fb in fbs[-limit:]
        ]

    def get_knowledge_graph_stats(self) -> Dict[str, Any]:
        """获取知识图谱统计"""
        domain_nodes: Dict[str, int] = defaultdict(int)
        for node in self._nodes.values():
            domain_nodes[node.domain] += 1

        relation_types: Dict[str, int] = defaultdict(int)
        for edge in self._edges:
            relation_types[edge.relation] += 1

        return {
            "total_nodes": len(self._nodes),
            "total_edges": len(self._edges),
            "nodes_by_domain": dict(domain_nodes),
            "edges_by_relation": dict(relation_types),
            "avg_confidence": (
                sum(n.confidence for n in self._nodes.values()) / len(self._nodes)
                if self._nodes else 0
            ),
        }

    def reset(self) -> None:
        """重置进化引擎"""
        self._feedbacks.clear()
        self._confidence_profiles = {
            domain: ConfidenceProfile(domain=domain)
            for domain in KNOWLEDGE_DOMAINS
        }
        self._nodes.clear()
        self._edges.clear()
        self._evolution_history.clear()
        self._init_seed_knowledge()


# ============================================================================
# 便捷函数
# ============================================================================

_evolution_engine: Optional[KnowledgeEvolution] = None


def get_evolution_engine() -> KnowledgeEvolution:
    """获取全局知识进化引擎"""
    global _evolution_engine
    if _evolution_engine is None:
        _evolution_engine = KnowledgeEvolution()
    return _evolution_engine


def quick_feedback(
    session_id: str,
    ratings: Dict[str, Any],
    domain: str = "general",
    comment: str = "",
) -> FeedbackRecord:
    """快速提交反馈"""
    return get_evolution_engine().collect_feedback(
        session_id, ratings, domain=domain, comment=comment,
    )


def quick_evolve() -> List[EvolutionResult]:
    """快速进化"""
    return get_evolution_engine().evolve()


__all__ = [
    "KnowledgeEvolution",
    "FeedbackRecord",
    "ConfidenceProfile",
    "KnowledgeNode",
    "KnowledgeEdge",
    "EvolutionResult",
    "get_evolution_engine",
    "quick_feedback",
    "quick_evolve",
    "KNOWLEDGE_DOMAINS",
]