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

    # v7.8.0: 实体同义词扩展 — 用于检索增强
    ENTITY_SYNONYMS: Dict[str, str] = {
        # 八字基础
        "八字": "四柱·生辰·排盘·命理",
        "命理": "八字·命运·分析",
        "天干": "十天干·天干阴阳·阳干·阴干",
        "地支": "十二地支·地支阴阳·阳支·阴支",
        "五行": "五行相生·五行相克·木生火·火生土·土生金·金生水·水生木·木克土·土克水·水克火·火克金·金克木",
        "十神": "正官·七杀·正印·偏印·正财·偏财·食神·伤官·比肩·劫财·生克关系",
        "大运": "运程·十年大运·行运·排大运",
        "流年": "太岁·岁运·流年运势·吉凶",
        "用神": "喜用神·用神·喜神·取用·旺衰",
        "格局": "正官格·七杀格·正印格·格局分析·特殊格局",
        # 紫微斗数
        "紫微斗数": "紫微斗数·命盘·十二宫·四化",
        "十二宫": "命宫·兄弟宫·夫妻宫·子女宫·财帛宫·疾厄宫·迁移宫·交友宫·官禄宫·田宅宫·福德宫·父母宫",
        "四化": "化禄·化权·化科·化忌",
        # 六爻
        "六爻": "起卦·铜钱·六爻预测·占卜",
        "世应": "世爻·应爻·世应关系",
        # 风水
        "风水": "风水术·地理·堪舆",
        "玄空": "玄空飞星·玄空风水",
        "飞星": "九星飞布·一白·二黑·三碧·四绿·五黄·六白·七赤·八白·九紫",
        "九宫": "坎一·坤二·震三·巽四·中五·乾六·兑七·艮八·离九",
        "坐向": "坐山·朝向·山向",
        "峦头": "龙脉·砂水·形势",
        "理气": "理气派·卦理·星气",
        # 姓名学
        "姓名学": "姓名学·五格·三才·数理",
        "五格": "天格·人格·地格·总格·外格",
        "三才": "天格·人格·地格·三才配置",
        "数理": "数理·81数理·吉数·凶数",
        # 通用
        "天干五合": "甲己合土·乙庚合金·丙辛合水·丁壬合木·戊癸合火",
        "地支三合": "申子辰合水·亥卯未合木·寅午戌合火·巳酉丑合金",
        "三合局": "申子辰合水·亥卯未合木·寅午戌合火·巳酉丑合金",
        "地支六合": "子丑合土·寅亥合木·卯戌合火·辰酉合金·巳申合水·午未合太阳",
        "地支六冲": "子午冲·丑未冲·寅申冲·卯酉冲·辰戌冲·巳亥冲",
        "地支六害": "子未害·丑午害·寅巳害·卯辰害·申亥害·酉戌害",
        "地支三刑": "无礼之刑·恃势之刑·无恩之刑·自刑",
        "地支藏干": "支藏人元·地支藏干表",
        "纳音": "六十甲子·纳音五行",
        "六十甲子": "甲子乙丑·丙寅丁卯·戊辰己巳·庚午辛未·壬申癸酉·六十干支",
        "十二长生": "长生·沐浴·冠带·临官·帝旺·衰·病·死·墓·绝·胎·养",
        "空亡": "旬空·空亡·六甲空亡",
        "二十四节气": "立春·雨水·惊蛰·春分·清明·谷雨·立夏·小满·芒种·夏至·小暑·大暑·立秋·处暑·白露·秋分·寒露·霜降·立冬·小雪·大雪·冬至·小寒·大寒",
        "魁罡": "魁罡格·庚戌·庚辰·壬辰·戊戌",
        "从格": "从财格·从杀格·从儿格·从势格·从强格",
        "化气格": "化气格·甲己化土·乙庚化金·丙辛化水·丁壬化木·戊癸化火",
        "驿马": "驿马星·走动·奔波·迁移",
        "桃花": "桃花星·咸池·异性缘·桃花运",
        "岁运并临": "岁运·并临·大运流年相同",
        "天克地冲": "天克地冲·流年冲克·大运冲克",
        "小运": "小运·一年一运·辅助大运",
        "命宫": "命宫·安命宫·命宫推算",
        "胎元": "胎元·受胎月份·命理胎元",
        "三方四正": "三方·四正·对宫·会照",
        "禄存": "禄存星·天禄·财星·福禄",
        "天魁": "天魁星·天乙贵人·科甲",
        "天钺": "天钺星·玉堂贵人·科名",
        "六兽": "青龙·朱雀·勾陈·螣蛇·白虎·玄武",
        "六神": "青龙·朱雀·勾陈·螣蛇·白虎·玄武",
        "月建": "月建·月令·月将·掌权",
        "日辰": "日辰·日令·当日·管辖",
        "动爻": "动爻·发动·变爻·老阳老阴",
        "变爻": "变爻·动爻变化·之卦",
        "暗动": "暗动·日冲·月冲·被动发动",
        "旬空": "旬空·空亡·日辰填空",
        "应期": "应期·应验·吉凶应验",
        "伏神": "伏神·伏藏·飞伏",
        "飞神": "飞神·压伏·飞伏关系",
        "六合卦": "六合卦·六十四卦·六合",
        "六冲卦": "六冲卦·六十四卦·六冲",
        "失物": "失物·寻找·遗失·去向",
        "三元九运": "三元九运·上元中元下元·一运至九运",
        "八宅": "八宅·东四宅·西四宅·八宅明镜",
        "四灵诀": "青龙·白虎·朱雀·玄武·四灵",
        "五黄煞": "五黄·煞气·五黄大煞·化解",
        "明堂": "明堂·内明堂·外明堂·聚气",
        "水法": "水法·来水·去水·水口",
        "阳宅": "阳宅·住宅·房屋·风水布局",
        "一白贪狼": "一白·贪狼星·文昌·桃花",
        "八白左辅": "八白·左辅星·财运·正财",
        "九紫右弼": "九紫·右弼星·喜庆·婚姻",
        "呼形喝象": "呼形喝象·形象·取象·峦头",
        "罗盘": "罗盘·罗经·天池·指南针",
        "天格": "天格·姓氏·祖先·运格",
        "人格": "人格·主运·中心·性格",
        "地格": "地格·前运·基础·子女",
        "总格": "总格·后运·晚年·结果",
        "外格": "外格·副运·社交·人际关系",
        "日柱": "日柱·日元·日主·命主",
        "寅申冲": "寅申冲·驿马冲·奔波·变动",
        "通关": "通关·通关用神·五行通关",
        "调候": "调候用神·寒暖燥湿·调候",
        "从财格": "从财格·弃命从财·财旺·富命",
        "从杀格": "从杀格·弃命从杀·官杀旺·权贵",
    }

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
        """从文本中搜索已知实体（v7.8.0）

        Args:
            text: 查询文本
            max_results: 最多返回实体数

        Returns:
            匹配到的实体名称列表，按匹配长度降序
        """
        found = []
        # 搜索 _entity_map（门禁映射实体）
        for entity in self._entity_map:
            if entity in text:
                found.append((len(entity), entity))
        # 也搜索 ENTITY_SYNONYMS（同义词扩展实体）
        for entity in self.ENTITY_SYNONYMS:
            if entity in text:
                found.append((len(entity), entity))
        # 去重（长实体优先）
        seen = set()
        unique = []
        for length, entity in sorted(found, reverse=True):
            if entity not in seen:
                seen.add(entity)
                unique.append(entity)
        return unique[:max_results]

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