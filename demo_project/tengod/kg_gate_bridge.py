"""
kg_gate_bridge.py — 知识图谱门禁桥接 v4.6.0
===============================================
道曰："道生一，一生二，二生三，三生万物。"

知识图谱实体关系 ↔ 门禁系数映射：
  - 十神 → 五行 → 九宫格 → 门禁系数
  - 星曜 → 宫位 → 四化 → 门禁权重
  - 六爻世应 → 用神 → 因果链

支持：
  - 门禁系数查询：给定实体 → 返回对应的九宫格门禁系数
  - 关系链推理：实体 A → 关系 → 实体 B → 门禁调整
  - 五行生克门禁：生克关系 → 门禁系数动态调制

用法：
    bridge = KGGateBridge()
    coeffs = bridge.get_gate_coefficients("正官")
    # → {"kan_1": 0.8, "li_9": 1.2, ...}
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


# ============================================================================
# 实体 → 门禁系数映射
# ============================================================================

# 十神 → 五行 → 九宫位 → 门禁系数（6维调制）
SHISHEN_GATE_MAP = {
    # 正官（金）→ 乾六兑七
    "正官": {"palace": 6, "element": "金", "gate_mod": [1.0, 0.7, 1.0, 1.0, 1.0, 1.0]},
    "七杀": {"palace": 7, "element": "金", "gate_mod": [1.0, 1.0, 1.0, 1.0, 1.0, 0.7]},
    # 正印（水）→ 坎一
    "正印": {"palace": 1, "element": "水", "gate_mod": [0.7, 1.0, 1.0, 1.0, 1.0, 1.0]},
    "偏印": {"palace": 1, "element": "水", "gate_mod": [0.8, 0.8, 1.0, 1.0, 1.0, 1.0]},
    # 正财（土）→ 坤二艮八
    "正财": {"palace": 2, "element": "土", "gate_mod": [1.0, 1.0, 1.0, 0.7, 1.0, 1.0]},
    "偏财": {"palace": 8, "element": "土", "gate_mod": [0.7, 1.0, 1.0, 1.0, 1.0, 0.7]},
    # 食神（火）→ 离九
    "食神": {"palace": 9, "element": "火", "gate_mod": [1.0, 1.0, 0.7, 0.7, 1.0, 1.0]},
    "伤官": {"palace": 9, "element": "火", "gate_mod": [1.0, 1.0, 0.8, 0.8, 1.0, 1.0]},
    # 比肩（木）→ 震三巽四
    "比肩": {"palace": 3, "element": "木", "gate_mod": [1.0, 1.0, 1.0, 1.0, 0.7, 1.0]},
    "劫财": {"palace": 4, "element": "木", "gate_mod": [1.0, 1.0, 0.7, 1.0, 1.0, 1.0]},
}

# 紫微主星 → 宫位 → 门禁系数
ZIWEI_STAR_MAP = {
    "紫微": {"palace": 5, "gate_mod": [1.0, 1.0, 1.0, 1.0, 1.0, 1.0]},  # 中五帝星
    "天机": {"palace": 3, "gate_mod": [1.0, 1.0, 1.0, 1.0, 0.8, 1.0]},  # 震三木
    "太阳": {"palace": 9, "gate_mod": [1.0, 1.0, 0.8, 0.8, 1.0, 1.0]},  # 离九火
    "武曲": {"palace": 6, "gate_mod": [1.0, 0.8, 1.0, 1.0, 1.0, 1.0]},  # 乾六金
    "天同": {"palace": 1, "gate_mod": [0.8, 1.0, 1.0, 1.0, 1.0, 1.0]},  # 坎一水
    "廉贞": {"palace": 9, "gate_mod": [1.0, 1.0, 0.7, 0.7, 1.0, 1.0]},  # 离九火
    "天府": {"palace": 2, "gate_mod": [1.0, 1.0, 1.0, 0.8, 1.0, 1.0]},  # 坤二土
    "太阴": {"palace": 1, "gate_mod": [0.8, 0.8, 1.0, 1.0, 1.0, 1.0]},  # 坎一水
    "贪狼": {"palace": 3, "gate_mod": [1.0, 1.0, 1.0, 1.0, 0.7, 1.0]},  # 震三木
    "巨门": {"palace": 2, "gate_mod": [1.0, 1.0, 1.0, 0.7, 1.0, 1.0]},  # 坤二土
    "天相": {"palace": 1, "gate_mod": [0.9, 0.9, 1.0, 1.0, 1.0, 1.0]},  # 坎一水
    "天梁": {"palace": 8, "gate_mod": [0.8, 1.0, 1.0, 1.0, 1.0, 0.9]},  # 艮八土
    "七杀": {"palace": 7, "gate_mod": [1.0, 1.0, 1.0, 1.0, 1.0, 0.7]},  # 兑七金
    "破军": {"palace": 1, "gate_mod": [0.7, 0.7, 1.0, 1.0, 1.0, 1.0]},  # 坎一水
}

# 五行生克关系 → 门禁调制
WUXING_SHENGKE = {
    # (me, other): is_healthy (True=生, False=克)
    ("木", "火"): 1.0,   # 木生火 → 正常
    ("木", "土"): 0.7,   # 木克土 → 调制
    ("火", "土"): 1.0,   # 火生土
    ("火", "金"): 0.7,   # 火克金
    ("土", "金"): 1.0,   # 土生金
    ("土", "水"): 0.7,   # 土克水
    ("金", "水"): 1.0,   # 金生水
    ("金", "木"): 0.7,   # 金克木
    ("水", "木"): 1.0,   # 水生木
    ("水", "火"): 0.7,   # 水克火
}

# 六爻六亲 → 门禁系数
LIUYAO_QIN_MAP = {
    "父母": {"gate_mod": [0.8, 0.8, 1.0, 1.0, 1.0, 1.0]},  # 坎水
    "兄弟": {"gate_mod": [1.0, 1.0, 1.0, 1.0, 0.8, 1.0]},  # 震木
    "妻财": {"gate_mod": [1.0, 1.0, 1.0, 0.8, 1.0, 1.0]},  # 坤土
    "官鬼": {"gate_mod": [1.0, 0.8, 0.8, 1.0, 1.0, 1.0]},  # 乾金
    "子孙": {"gate_mod": [1.0, 1.0, 0.8, 0.8, 1.0, 1.0]},  # 离火
}


class KGGateBridge:
    """知识图谱门禁桥接 v3.8.0

    将领域实体（十神、星曜、六亲等）映射为门禁系数，
    实现 "知识 → 门禁" 的语义级调整。
    """

    def __init__(self):
        self._entity_map = self._build_entity_map()

    def _build_entity_map(self) -> Dict[str, Dict[str, Any]]:
        """合并所有实体映射"""
        entity_map: Dict[str, Dict[str, Any]] = {}
        for d in [SHISHEN_GATE_MAP, ZIWEI_STAR_MAP, LIUYAO_QIN_MAP]:
            entity_map.update(d)
        return entity_map

    def get_gate_coefficients(self, entity: str) -> Optional[Dict[str, Any]]:
        """获取实体的门禁系数

        Args:
            entity: 实体名称（如 "正官", "紫微", "父母"）

        Returns:
            {
                "palace": 6,
                "element": "金",
                "gate_mod": [1.0, 0.7, 1.0, 1.0, 1.0, 1.0],
            }
        """
        return self._entity_map.get(entity)

    def get_gate_mod(self, entity: str) -> Optional[List[float]]:
        """获取门禁调制向量"""
        info = self._entity_map.get(entity)
        return info["gate_mod"] if info else None

    def get_palace(self, entity: str) -> Optional[int]:
        """获取实体对应的九宫格编号"""
        info = self._entity_map.get(entity)
        return info["palace"] if info else None

    def get_element(self, entity: str) -> Optional[str]:
        """获取实体对应的五行"""
        info = self._entity_map.get(entity)
        return info.get("element") if info else None

    def apply_wuxing_shengke(
        self,
        base_mod: List[float],
        me_element: str,
        other_element: str,
    ) -> List[float]:
        """五行生克调制门禁系数

        Args:
            base_mod: 基础门禁调制向量
            me_element: 主体五行
            other_element: 客体五行

        Returns:
            调制后的门禁系数
        """
        if me_element == other_element:
            # 同五行 → 比和，不调制
            return base_mod

        # 生克关系
        sheng = WUXING_SHENGKE.get((me_element, other_element), 1.0)
        ke = WUXING_SHENGKE.get((other_element, me_element), 1.0)

        # 生克因子
        factor = min(sheng, ke)

        return [c * factor for c in base_mod]

    def resolve_chain(
        self,
        entities: List[str],
    ) -> Dict[str, Any]:
        """解析实体链，计算综合门禁系数

        例：用户查询 "正官格取用神" → entities=["正官", "用神"]
        → 正官(金) → 用神(取决于日主) → 综合门禁系数

        Args:
            entities: 实体链列表

        Returns:
            {
                "chain": [...],
                "composite_gate_mod": [...],
                "palace_sequence": [...],
                "element_chain": [...],
            }
        """
        chain = []
        component_mods = []

        for entity in entities:
            info = self.get_gate_coefficients(entity)
            chain.append({
                "entity": entity,
                "found": info is not None,
                "palace": info["palace"] if info else None,
                "element": info.get("element") if info else None,
            })
            if info and "gate_mod" in info:
                component_mods.append(info["gate_mod"])

        # 综合门禁系数：各分量加权平均
        if component_mods:
            composite = [0.0] * 6
            for mod in component_mods:
                for i in range(6):
                    composite[i] += mod[i]
            composite = [c / len(component_mods) for c in composite]
        else:
            composite = [1.0] * 6

        return {
            "chain": chain,
            "composite_gate_mod": composite,
            "palace_sequence": [c["palace"] for c in chain if c["palace"]],
            "element_chain": [c["element"] for c in chain if c["element"]],
        }

    def get_all_entities(self) -> List[str]:
        """获取所有已知实体"""
        return list(self._entity_map.keys())

    def search_entities(self, text: str, max_results: int = 5) -> List[str]:
        """从文本中搜索已知实体（v4.3.0）

        Args:
            text: 查询文本
            max_results: 最多返回实体数

        Returns:
            匹配到的实体名称列表，按匹配长度降序
        """
        found = []
        for entity in self._entity_map:
            if entity in text:
                found.append((len(entity), entity))
        found.sort(reverse=True)  # 长实体优先
        return [e for _, e in found[:max_results]]

    def get_stats(self) -> Dict[str, Any]:
        """获取桥接统计"""
        categories = {}
        for entity, info in self._entity_map.items():
            elem = info.get("element", "未知")
            if elem not in categories:
                categories[elem] = []
            categories[elem].append(entity)
        return {
            "total_entities": len(self._entity_map),
            "by_element": {k: len(v) for k, v in categories.items()},
            "unique_palaces": len(set(info["palace"] for info in self._entity_map.values())),
        }


# ============================================================================
# 自检
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  知识图谱门禁桥接 v3.8.0")
    print("=" * 60)

    bridge = KGGateBridge()
    stats = bridge.get_stats()
    print(f"\n  实体总数: {stats['total_entities']}")
    print(f"  五行分布: {stats['by_element']}")

    # 单实体查询
    print("\n  单实体查询:")
    for entity in ["正官", "紫微", "食神", "父母"]:
        info = bridge.get_gate_coefficients(entity)
        if info:
            print(f"    {entity}: palace={info['palace']}, element={info['element']}, mod={info['gate_mod']}")

    # 实体链解析
    print("\n  实体链解析: '正官' → '用神'")
    result = bridge.resolve_chain(["正官", "用神"])
    print(f"    chain: {result['chain']}")
    print(f"    composite_mod: {result['composite_gate_mod']}")

    # 五行生克
    print("\n  五行生克调制:")
    base = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
    print(f"    木克土: {bridge.apply_wuxing_shengke(base, '木', '土')}")
    print(f"    木生火: {bridge.apply_wuxing_shengke(base, '木', '火')}")

    print("\n" + "=" * 60)
    print("  自检完成")
    print("=" * 60)