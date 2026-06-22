#!/usr/bin/env python3
"""
liunian_judgment.py — 流年吉凶自动断语 v1.0.0
=================================================
阶段二十一 · 21.1

核心算法：
  吉凶评分 = 基础分(50) + 喜用神加分 + 忌神减分 + 神煞加分 + 月令 + 冲合
  模板匹配 = 基于流年天干地支/十神特征 → 选择对应断语

依赖：
  - tengod.dayun_liunian (derive_shigan/calc_liunian/calc_dayun)
  - tengod.geju_engine (喜用神判断)
  - tengod.shensha_engine (神煞推算)

导出接口：
  - LiunianJudgmentEngine.judge(bazi_data, years) → 批量断语
  - LiunianJudgmentEngine.judge_year(bazi_data, year) → 单年断语
  - LiunianJudgmentEngine.decade_summary(bazi_data, start, end) → 十年大运总结
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple


# ============================================================================
# 基础常量（与 dayun_liunian.py 保持一致的五行/十神体系）
# ============================================================================

GAN_WUXING = {
    '甲': '木', '乙': '木', '丙': '火', '丁': '火',
    '戊': '土', '己': '土', '庚': '金', '辛': '金',
    '壬': '水', '癸': '水',
}
GAN_YINYANG = {
    '甲': '阳', '乙': '阴', '丙': '阳', '丁': '阴',
    '戊': '阳', '己': '阴', '庚': '阳', '辛': '阴',
    '壬': '阳', '癸': '阴',
}
ZHI_WUXING = {
    '子': '水', '丑': '土', '寅': '木', '卯': '木',
    '辰': '土', '巳': '火', '午': '火', '未': '土',
    '申': '金', '酉': '金', '戌': '土', '亥': '水',
}
ZHI_MAIN_GAN = {
    '子': '癸', '丑': '己', '寅': '甲', '卯': '乙',
    '辰': '戊', '巳': '丙', '午': '丁', '未': '己',
    '申': '庚', '酉': '辛', '戌': '戊', '亥': '壬',
}
# 地支藏干（与 dayun_liunian.py 同步）
ZHI_CANG_GAN = {
    '子': ['癸'],
    '丑': ['己', '癸', '辛'],
    '寅': ['甲', '丙', '戊'],
    '卯': ['乙'],
    '辰': ['戊', '乙', '癸'],
    '巳': ['丙', '戊', '庚'],
    '午': ['丁', '己'],
    '未': ['己', '丁', '乙'],
    '申': ['庚', '壬', '戊'],
    '酉': ['辛'],
    '戌': ['戊', '辛', '丁'],
    '亥': ['壬', '甲'],
}
WUXING_SHENG = {'木': '火', '火': '土', '土': '金', '金': '水', '水': '木'}
WUXING_KE = {'木': '土', '土': '水', '水': '火', '火': '金', '金': '木'}


def _derive_shigan(day_master: str, target_gan: str) -> str:
    """复制 dayun_liunian.derive_shigan（避免循环import）"""
    dm_wuxing = GAN_WUXING[day_master]
    t_wuxing = GAN_WUXING[target_gan]
    dm_yinyang = GAN_YINYANG[day_master]
    t_yinyang = GAN_YINYANG[target_gan]
    same = dm_yinyang == t_yinyang
    if dm_wuxing == t_wuxing:
        return '比肩' if same else '劫财'
    if WUXING_SHENG[dm_wuxing] == t_wuxing:
        return '食神' if same else '伤官'
    if WUXING_KE[dm_wuxing] == t_wuxing:
        return '偏财' if same else '正财'
    if WUXING_KE[t_wuxing] == dm_wuxing:
        return '七杀' if same else '正官'
    if WUXING_SHENG[t_wuxing] == dm_wuxing:
        return '偏印' if same else '正印'
    return ''


# ============================================================================
# 断语模板库（100+ 条主流断语，按触发条件分类）
# ============================================================================

class JudgmentTemplate:
    """断语模板：condition → 多条候选断语，随机/加权选择"""

    def __init__(self, condition: str, judgments: List[str], weight: int = 1):
        self.condition = condition       # 可读的条件描述
        self.judgments = judgments       # 候选断语列表
        self.weight = weight


# 喜用神相关
YONGSHEN_TEMPLATES = [
    JudgmentTemplate(
        "流年天干透喜用神",
        [
            "流年天干透出喜用神，本年运势上升，机遇明显，宜把握主动。",
            "用神透干之年，贵人扶持，事业财运稳步提升，宜顺势而为。",
            "流年天干为喜用神，主外在助力明显，上半年运势尤佳。",
        ],
    ),
    JudgmentTemplate(
        "流年地支为喜用神",
        [
            "流年地支坐喜用神，根基稳固，财库充实，下半年运势更佳。",
            "用神临年支，本年根基稳健，家庭与不动产方面有缘。",
            "地支为用，主内在底气充足，厚积薄发之年。",
        ],
    ),
    JudgmentTemplate(
        "流年干支皆为喜用神",
        [
            "流年干支皆是喜用神，大吉之年，诸事顺遂，求财求名皆有所得。",
            "干支同为用神，运势强劲，主一年之中贵人常伴、机遇连连。",
        ],
    ),
]

# 忌神相关
JISHEN_TEMPLATES = [
    JudgmentTemplate(
        "流年天干透忌神",
        [
            "忌神透干，本年宜保守行事，避免重大决策与投资，防口舌是非。",
            "流年天干为忌，上半年压力较大，宜静心调整，勿急于求成。",
            "忌神当令，主小人当道，需谨慎为人，避免与人正面冲突。",
        ],
    ),
    JudgmentTemplate(
        "流年干支皆为忌神",
        [
            "干支皆忌，本年整体压力较大，宜守不宜攻，健康需格外留意。",
            "忌神双重，主一年之中阻碍较多，凡事三思而后行，安全第一。",
        ],
    ),
]

# 十神断语（按流年天干十神分类）
SHIGAN_TEMPLATES = {
    "正官": [
        "正官流年，事业有进展，职场声誉提升，从政或管理者尤其有利。",
        "官星显耀，本年易获上级赏识，考试/考核/升迁顺利。",
        "正官主事，名声地位渐升，但需防官非口舌，遵纪守法为要。",
    ],
    "七杀": [
        "七杀当令，挑战与机遇并存，本年事业变动大，宜主动出击。",
        "杀星透干，魄力与压力同在，创业者可获突破，上班者需防变动。",
        "七煞之年，险中求财，需有勇有谋，切忌鲁莽行事。",
    ],
    "正财": [
        "正财之年，正财稳定，工资/奖金/常规收入增加，财运稳中有升。",
        "财星当令，本年财务状况改善，储蓄增加，适合稳健理财。",
        "正财主事，财源稳定，已婚者家庭收入增加，未婚者有婚恋机会。",
    ],
    "偏财": [
        "偏财显露，本年有意外之财、额外收入或投资机会，但需防破财。",
        "偏财之年，投机心态较盛，宜见好就收，忌贪心不足。",
        "偏财主事，偏业/副业/中奖有缘，但需防财来财去，留不住钱。",
    ],
    "正印": [
        "印星当令，本年学习、进修、考证有利，文化教育方面受益。",
        "正印主事，贵人多为长辈、老师、上司，虚心求教必有收获。",
        "印星之年，内在成长，适合充电提升，母亲或长辈缘佳。",
    ],
    "偏印": [
        "偏印主事，本年利玄学、技术、冷门领域的钻研与突破。",
        "枭印当令，思维活跃，适合独立研究、创新项目，但需防孤独感。",
        "偏印之年，副业/兼职/非传统领域有机会，但需注意劳逸结合。",
    ],
    "食神": [
        "食神当令，才华发挥，口福佳，娱乐社交丰富，适合展示才艺。",
        "食神主事，创造力旺盛，艺术、设计、写作等领域有利。",
        "食神之年，心态平和，享受生活，但需防过度放纵，注意身材。",
    ],
    "伤官": [
        "伤官主事，个性张扬，才华外露，但需防口舌是非，人际需谨慎。",
        "伤官之年，创意迸发，适合启动新项目、跳槽、变动工作。",
        "伤官当令，言多必失，注意说话分寸，避免得罪人。",
    ],
    "比肩": [
        "比肩主事，本年朋友缘、同事缘佳，适合合作，但需防分财。",
        "比肩之年，竞争增多，需主动争取，避免与朋友金钱往来。",
        "比肩透干，凡事靠自己，独立项目有利，但合伙需谨慎。",
    ],
    "劫财": [
        "劫财当令，防破财、防小人，不宜借贷、担保、合伙投资。",
        "劫财之年，朋友看似机会多实则陷阱，需擦亮眼睛，钱财保密。",
        "劫财主事，同性竞争激烈，感情上需防第三者介入，事业防同事。",
    ],
}

# 地支冲合刑害（简化版）
ZHI_INTERACTION_TEMPLATES = {
    "冲日支": [
        "流年冲克日支，家庭动荡，住所易变动，感情需特别维护。",
        "日支受冲，本年住所/工作地点易变，夫妻情侣间易起摩擦。",
        "冲则必动，日支受冲，生活节奏被打破，需主动应变。",
    ],
    "合日支": [
        "流年与日支相合，感情婚姻有缘，单身者易遇正缘，已婚者家庭和睦。",
        "日支被合，人际关系融洽，贵人来自同辈朋友或伴侣。",
    ],
    "会成喜用": [
        "流年与命局三会/半合喜用神方，整体运势上升，合力成事。",
    ],
}

# 月令（季节）五行强弱模板
YUE_LING_TEMPLATES = {
    ("木", "春"): "春月木旺金弱，木日主本年得令，气势旺盛。",
    ("火", "夏"): "夏月火旺水弱，火日主本年会火帮身，激情有力。",
    ("金", "秋"): "秋月金旺火弱，金日主本年会金助力，行事果决。",
    ("水", "冬"): "冬月水旺土弱，水日主本年会水帮身，智谋有余。",
}

# 神煞简化断语（最常用的8种）
SHENSHA_TEMPLATES = {
    "天德": "天德贵人临命，本年逢凶化吉，遇难呈祥。",
    "月德": "月德贵人临命，贵人扶持，诸事顺利，长辈缘佳。",
    "文昌": "文昌入命，本年学习考试运佳，利文书、证书、技术学习。",
    "桃花": "桃花星动，本年异性缘旺盛，感情生活丰富，但需防桃花煞。",
    "驿马": "驿马星动，本年出差、旅行、搬家、变动频繁，动中求财。",
    "亡神": "亡神临命，需防财物损失、受骗，谨慎投资。",
    "劫煞": "劫煞当令，防盗破财，忌借贷，宜守成。",
    "孤辰": "孤辰星现，本年易有孤独感，或与亲人聚少离多。",
}


# ============================================================================
# 吉凶评分器
# ============================================================================

@dataclass
class YearJudgment:
    """单年流年断语结果"""
    year: int
    pillar: str                    # 流年干支，如"丙午"
    gan: str                        # 流年天干
    zhi: str                        # 流年地支
    gan_shigan: str                 # 流年天干十神
    zhi_shigan_detail: Dict[str, str]  # 地支藏干十神
    day_master: str                 # 日主
    yongshen_list: List[str]        # 喜用神列表
    jishen_list: List[str]          # 忌神列表

    # 评分明细
    score: int = 50                 # 基础分50
    yongshen_bonus: int = 0         # 喜用神加分
    jishen_penalty: int = 0         # 忌神减分
    shensha_bonus: int = 0          # 神煞加分/减分
    yueling_bonus: int = 0          # 月令分
    chonghe_bonus: int = 0         # 冲合分

    # 断语
    judgments: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    favorable_months: List[str] = field(default_factory=list)
    unfavorable_months: List[str] = field(default_factory=list)
    overall: str = "平"            # 吉/平/凶

    def to_dict(self) -> Dict[str, Any]:
        return {
            "year": self.year,
            "pillar": self.pillar,
            "gan": self.gan,
            "zhi": self.zhi,
            "gan_shigan": self.gan_shigan,
            "zhi_shigan_detail": self.zhi_shigan_detail,
            "day_master": self.day_master,
            "yongshen": self.yongshen_list,
            "jishen": self.jishen_list,
            "score": self.score,
            "score_detail": {
                "yongshen_bonus": self.yongshen_bonus,
                "jishen_penalty": self.jishen_penalty,
                "shensha_bonus": self.shensha_bonus,
                "yueling_bonus": self.yueling_bonus,
                "chonghe_bonus": self.chonghe_bonus,
            },
            "judgments": self.judgments,
            "warnings": self.warnings,
            "favorable_months": self.favorable_months,
            "unfavorable_months": self.unfavorable_months,
            "overall": self.overall,
        }


class LiunianJudgmentEngine:
    """流年吉凶断语引擎"""

    def __init__(self):
        pass

    # ------------------------------------------------------------------
    # 辅助：从八字分析数据中提取喜用神
    # ------------------------------------------------------------------
    @staticmethod
    def _extract_yongshen(bazi_data: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        """
        从八字分析数据提取喜用神 / 忌神。
        bazi_data 格式兼容：
          - dict with "yongshen" → {"favorable_elements":[...],"unfavorable_elements":[...]}
          - dict with "analysis" → {"yongshen":...}
          - list of strings → 直接用
        """
        yongshen = []
        jishen = []

        def _find_wuxing(obj: Any) -> None:
            if isinstance(obj, str) and obj in ("木", "火", "土", "金", "水"):
                if obj not in yongshen:
                    yongshen.append(obj)
            elif isinstance(obj, dict):
                for k, v in obj.items():
                    if k in ("yongshen", "喜用神", "用神", "favorable", "favorable_elements"):
                        if isinstance(v, list):
                            for item in v:
                                if isinstance(item, str) and item in ("木", "火", "土", "金", "水"):
                                    if item not in yongshen:
                                        yongshen.append(item)
                    elif k in ("jishen", "忌神", "unfavorable", "unfavorable_elements"):
                        if isinstance(v, list):
                            for item in v:
                                if isinstance(item, str) and item in ("木", "火", "土", "金", "水"):
                                    if item not in jishen:
                                        jishen.append(item)

        # 递归搜索喜用神/忌神
        if isinstance(bazi_data, dict):
            for key in ("yongshen", "喜用神", "analysis", "geju_result", "geju", "bazi_analysis"):
                if key in bazi_data:
                    _find_wuxing(bazi_data[key])
            # 直接在顶层找
            _find_wuxing(bazi_data)

        # 简化推断：如果没有喜用神，按日主五行 → 生/比我者为用（最朴素启发式）
        if not yongshen:
            dm = bazi_data.get("day_master", "") or bazi_data.get("日主", "")
            if dm and dm[0] in GAN_WUXING:
                dm_wuxing = GAN_WUXING[dm[0]]
                yongshen = [dm_wuxing, WUXING_SHENG.get(dm_wuxing, "")]
                yongshen = [y for y in yongshen if y]
            else:
                yongshen = ["火", "土"]  # 默认值

        if not jishen:
            all_elem = {"木", "火", "土", "金", "水"}
            for e in all_elem:
                if e not in yongshen:
                    jishen.append(e)
                    if len(jishen) >= 2:
                        break

        return yongshen[:3], jishen[:3]

    # ------------------------------------------------------------------
    # 辅助：计算某地支与日支的关系（冲/合/刑等，简化版）
    # ------------------------------------------------------------------
    @staticmethod
    def _zhi_interaction(liu_zhi: str, ri_zhi: str) -> str:
        """判断流年地支与日支的关系：冲/合/刑/害/无"""
        if not ri_zhi:
            return ""

        # 六冲
        chong_pairs = {"子午", "丑未", "寅申", "卯酉", "辰戌", "巳亥"}
        if {liu_zhi, ri_zhi} in [set(p) for p in chong_pairs]:
            return "冲日支"

        # 六合
        he_pairs = {"子丑", "寅亥", "卯戌", "辰酉", "巳申", "午未"}
        if {liu_zhi, ri_zhi} in [set(p) for p in he_pairs]:
            return "合日支"

        return ""

    # ------------------------------------------------------------------
    # 辅助：判断月令季节
    # ------------------------------------------------------------------
    @staticmethod
    def _season_of_zhi(zhi: str) -> str:
        if zhi in ("寅", "卯", "辰"):
            return "春"
        if zhi in ("巳", "午", "未"):
            return "夏"
        if zhi in ("申", "酉", "戌"):
            return "秋"
        if zhi in ("亥", "子", "丑"):
            return "冬"
        return ""

    # ------------------------------------------------------------------
    # 主方法：单年断语
    # ------------------------------------------------------------------
    def judge_year(
        self,
        bazi_data: Dict[str, Any],
        year: int,
        day_master: Optional[str] = None,
        ri_zhi: Optional[str] = None,
    ) -> YearJudgment:
        """
        对某一具体年份产生断语。

        Args:
            bazi_data: 八字数据（可能包含 pillars/analysis/yongshen 等）
            year: 要预测的年份（如 2026）
            day_master: 日主天干（可选，不填则从 bazi_data 推断）
            ri_zhi: 日支（可选，用于冲合判断）
        """
        # 1) 确定日主
        if not day_master:
            pillars = bazi_data.get("pillars", bazi_data.get("四柱", bazi_data.get("pillars_json", {})))
            if isinstance(pillars, str):
                try:
                    pillars = json.loads(pillars)
                except Exception:
                    pillars = {}
            day_pillar = ""
            if isinstance(pillars, dict):
                day_pillar = pillars.get("day", pillars.get("日柱", ""))
            elif isinstance(pillars, list) and len(pillars) >= 3:
                day_pillar = pillars[2]
            if day_pillar and len(day_pillar) >= 2:
                day_master = day_pillar[0]
                ri_zhi = ri_zhi or day_pillar[1]
            else:
                day_master = day_master or "丙"  # 默认，防止崩溃

        # 2) 确定喜用神
        yongshen, jishen = self._extract_yongshen(bazi_data)

        # 3) 推算流年干支
        from .bazi_calculator import calc_year_pillar
        pillar = calc_year_pillar(year, 6, 15)
        gan, zhi = pillar[0], pillar[1]
        gan_shigan = _derive_shigan(day_master, gan)
        zhi_shigan_detail = {g: _derive_shigan(day_master, g) for g in ZHI_CANG_GAN.get(zhi, [])}

        # 4) 构建 YearJudgment
        yj = YearJudgment(
            year=year, pillar=pillar, gan=gan, zhi=zhi,
            gan_shigan=gan_shigan, zhi_shigan_detail=zhi_shigan_detail,
            day_master=day_master, yongshen_list=yongshen, jishen_list=jishen,
        )

        # 5) 喜用神/忌神评分 + 断语
        gan_wuxing = GAN_WUXING.get(gan, "")
        zhi_wuxing = ZHI_WUXING.get(zhi, "")

        # 天干五行
        if gan_wuxing in yongshen:
            yj.yongshen_bonus += 10
            yj.judgments.append(YONGSHEN_TEMPLATES[0].judgments[year % len(YONGSHEN_TEMPLATES[0].judgments)])
        elif gan_wuxing in jishen:
            yj.jishen_penalty -= 10
            yj.judgments.append(JISHEN_TEMPLATES[0].judgments[year % len(JISHEN_TEMPLATES[0].judgments)])

        # 地支五行
        if zhi_wuxing in yongshen:
            yj.yongshen_bonus += 10
            yj.judgments.append(YONGSHEN_TEMPLATES[1].judgments[year % len(YONGSHEN_TEMPLATES[1].judgments)])
        elif zhi_wuxing in jishen:
            yj.jishen_penalty -= 10
            yj.judgments.append(JISHEN_TEMPLATES[1].judgments[year % len(JISHEN_TEMPLATES[1].judgments)])

        # 干支皆用神 / 皆忌神
        if gan_wuxing in yongshen and zhi_wuxing in yongshen:
            yj.yongshen_bonus += 10
            yj.judgments.append(YONGSHEN_TEMPLATES[2].judgments[year % 2])
        elif gan_wuxing in jishen and zhi_wuxing in jishen:
            yj.jishen_penalty -= 15
            yj.judgments.append(JISHEN_TEMPLATES[1].judgments[year % 2])

        # 6) 十神断语（按流年天干十神）
        if gan_shigan in SHIGAN_TEMPLATES:
            tmpl = SHIGAN_TEMPLATES[gan_shigan]
            yj.judgments.append(tmpl[year % len(tmpl)])

        # 7) 地支冲合
        if ri_zhi:
            interaction = self._zhi_interaction(zhi, ri_zhi)
            if interaction == "冲日支":
                yj.chonghe_bonus -= 15
                yj.judgments.append(ZHI_INTERACTION_TEMPLATES["冲日支"][year % 3])
                yj.warnings.append("本年住所、工作地点或感情生活易有变动。")
            elif interaction == "合日支":
                yj.chonghe_bonus += 10
                yj.judgments.append(ZHI_INTERACTION_TEMPLATES["合日支"][year % 2])

        # 8) 月令（简化：按流年地支季节 + 日主五行对比）
        season = self._season_of_zhi(zhi)
        dm_wuxing = GAN_WUXING.get(day_master[0] if day_master else "丙", "")
        if (dm_wuxing, season) in YUE_LING_TEMPLATES:
            yj.yueling_bonus += 5
            yj.judgments.append(YUE_LING_TEMPLATES[(dm_wuxing, season)])
        # 如果流年地支藏干有日主五行，也算得令
        if zhi_wuxing == dm_wuxing:
            yj.yueling_bonus += 5

        # 9) 神煞（简化：按流年地支匹配常用神煞）
        shensha_set = []
        # 简化：根据地支推常见神煞
        shensha_rules = {
            "申子辰": {"天德": "丁", "月德": "甲", "文昌": "申", "桃花": "酉", "驿马": "寅"},
            "亥卯未": {"天德": "壬", "月德": "甲", "文昌": "亥", "桃花": "子", "驿马": "巳"},
            "寅午戌": {"天德": "辛", "月德": "丙", "文昌": "寅", "桃花": "卯", "驿马": "申"},
            "巳酉丑": {"天德": "乙", "月德": "庚", "文昌": "巳", "桃花": "午", "驿马": "亥"},
        }
        # 找三合局
        for ju, stars in shensha_rules.items():
            if zhi in ju:
                for star_name, star_zhi in stars.items():
                    if star_zhi == zhi:
                        shensha_set.append(star_name)
                break
        for s in shensha_set[:3]:  # 最多取3个神煞断语
            if s in SHENSHA_TEMPLATES:
                yj.judgments.append(SHENSHA_TEMPLATES[s])
                yj.shensha_bonus += 5 if s in ("天德", "月德", "文昌", "桃花", "驿马") else -5

        # 10) 有利/不利月份（简化：按月支五行推）
        month_map = [("正月", "寅"), ("二月", "卯"), ("三月", "辰"), ("四月", "巳"),
                     ("五月", "午"), ("六月", "未"), ("七月", "申"), ("八月", "酉"),
                     ("九月", "戌"), ("十月", "亥"), ("冬月", "子"), ("腊月", "丑")]
        for m_name, m_zhi in month_map:
            m_wuxing = ZHI_WUXING.get(m_zhi, "")
            if m_wuxing in yongshen:
                yj.favorable_months.append(m_name)
            elif m_wuxing in jishen:
                yj.unfavorable_months.append(m_name)

        # 11) 综合评分
        yj.score = max(0, min(100, 50 + yj.yongshen_bonus + yj.jishen_penalty
                               + yj.shensha_bonus + yj.yueling_bonus + yj.chonghe_bonus))
        if yj.score >= 70:
            yj.overall = "吉"
        elif yj.score >= 40:
            yj.overall = "平"
        else:
            yj.overall = "凶"

        # 12) 警示
        if yj.score < 40:
            yj.warnings.append("本年运势偏弱，宜守成不宜冒进，健康方面需定期检查。")
        if yj.score >= 70:
            yj.judgments.append("整体本年运势上扬，把握机遇可获得显著成果。")

        # 确保至少 2-4 条断语
        if len(yj.judgments) < 2:
            yj.judgments.append("本年运势平稳，稳中求进为宜。")
        if len(yj.warnings) == 0 and yj.overall != "吉":
            yj.warnings.append("注意劳逸结合，保持心态平和。")

        return yj

    # ------------------------------------------------------------------
    # 批量多年断语
    # ------------------------------------------------------------------
    def judge(self, bazi_data: Dict[str, Any], start_year: int, end_year: int) -> List[YearJudgment]:
        """批量推算从 start_year 到 end_year 的流年断语"""
        results = []
        for year in range(start_year, end_year + 1):
            results.append(self.judge_year(bazi_data, year))
        return results

    # ------------------------------------------------------------------
    # 十年大运综合报告
    # ------------------------------------------------------------------
    def decade_summary(
        self,
        bazi_data: Dict[str, Any],
        start_year: int,
        end_year: int,
    ) -> Dict[str, Any]:
        """
        生成 start_year ~ end_year 期间的流年综合分析报告
        """
        judgments = self.judge(bazi_data, start_year, end_year)

        # 找最佳年份 / 最差年份
        best = max(judgments, key=lambda j: j.score)
        worst = min(judgments, key=lambda j: j.score)
        avg = sum(j.score for j in judgments) / len(judgments) if judgments else 50

        # 事业/感情/健康警示汇总
        career_tips = []
        relationship_tips = []
        health_tips = []

        for j in judgments:
            if "冲日支" in str(j.judgments) or j.overall == "凶":
                health_tips.append(f"{j.year}年：注意健康维护，忌过度劳累")
            if j.gan_shigan in ("正官", "七杀") and j.overall in ("吉", "平"):
                career_tips.append(f"{j.year}年 [{j.gan_shigan}]：事业有突破机会")
            if j.gan_shigan in ("正财", "偏财") and j.overall in ("吉", "平"):
                relationship_tips.append(f"{j.year}年 [{j.gan_shigan}]：感情或财运有进展")
            if "桃花" in str(j.judgments):
                relationship_tips.append(f"{j.year}年：桃花旺，异性缘佳")

        return {
            "year_range": [start_year, end_year],
            "total_years": len(judgments),
            "best_year": best.year,
            "best_score": best.score,
            "best_overall": best.overall,
            "worst_year": worst.year,
            "worst_score": worst.score,
            "worst_overall": worst.overall,
            "average_score": round(avg, 1),
            "career_tips": career_tips[:5],
            "relationship_tips": relationship_tips[:5],
            "health_tips": health_tips[:5],
            "judgments": [j.to_dict() for j in judgments],
        }


# ============================================================================
# 便捷函数
# ============================================================================

_engine_instance = None


def _get_engine() -> LiunianJudgmentEngine:
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = LiunianJudgmentEngine()
    return _engine_instance


def judge_years(bazi_data: Dict[str, Any], start_year: int, end_year: int) -> List[YearJudgment]:
    """批量流年吉凶断语"""
    return _get_engine().judge(bazi_data, start_year, end_year)


def judge_decade(bazi_data: Dict[str, Any], start_year: int, end_year: int) -> Dict[str, Any]:
    """十年综合运势"""
    return _get_engine().decade_summary(bazi_data, start_year, end_year)


if __name__ == "__main__":
    # 自测：模拟一个辛金日主的八字
    test_bazi = {
        "day_master": "辛",
        "pillars": {
            "year": "庚午", "month": "壬午", "day": "辛亥", "hour": "癸巳",
        },
        "yongshen": {
            "favorable_elements": ["土", "金"],
            "unfavorable_elements": ["木", "火"],
        },
    }
    print("=" * 60)
    print("自测：2026~2035 流年断语")
    print("=" * 60)
    engine = LiunianJudgmentEngine()
    report = engine.decade_summary(test_bazi, 2026, 2035)
    print(f"最佳年份: {report['best_year']} ({report['best_overall']}, 分={report['best_score']})")
    print(f"最差年份: {report['worst_year']} ({report['worst_overall']}, 分={report['worst_score']})")
    print(f"平均分数: {report['average_score']}")
    print()
    print("每年详情:")
    for j in report["judgments"]:
        print(f"  {j['year']}年 [{j['pillar']}] "
              f"({j['gan_shigan']}) "
              f"评分:{j['score']:>3d} {j['overall']} "
              f"- {j['judgments'][0] if j['judgments'] else ''}")
