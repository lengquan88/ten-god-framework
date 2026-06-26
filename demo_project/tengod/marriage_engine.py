#!/usr/bin/env python3
"""
marriage_engine.py — 合婚分析引擎 v1.0.0

基于八字命理学的婚配分析，涵盖：
  1. 年柱纳音匹配
  2. 日柱天干五合
  3. 地支六合/三合/六冲分析
  4. 五行互补分析
  5. 十神配比
  6. 综合婚配评分
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple


# ============================================================================
# 常量定义
# ============================================================================

TIAN_GAN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
DI_ZHI = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

# 天干五合
TIAN_GAN_HE = {
    ("甲", "己"): "中正之合", ("己", "甲"): "中正之合",
    ("乙", "庚"): "仁义之合", ("庚", "乙"): "仁义之合",
    ("丙", "辛"): "威制之合", ("辛", "丙"): "威制之合",
    ("丁", "壬"): "淫匿之合", ("壬", "丁"): "淫匿之合",
    ("戊", "癸"): "无情之合", ("癸", "戊"): "无情之合",
}

# 天干五合评分
TIAN_GAN_HE_SCORE = {
    "中正之合": 90, "仁义之合": 85, "威制之合": 70, "淫匿之合": 50, "无情之合": 40,
}

# 地支六合
DI_ZHI_LIU_HE = {
    ("子", "丑"): "土", ("丑", "子"): "土",
    ("寅", "亥"): "木", ("亥", "寅"): "木",
    ("卯", "戌"): "火", ("戌", "卯"): "火",
    ("辰", "酉"): "金", ("酉", "辰"): "金",
    ("巳", "申"): "水", ("申", "巳"): "水",
    ("午", "未"): "日月合", ("未", "午"): "日月合",
}

# 地支六冲
DI_ZHI_CHONG = {
    ("子", "午"): "水火冲", ("午", "子"): "水火冲",
    ("丑", "未"): "土土冲", ("未", "丑"): "土土冲",
    ("寅", "申"): "金木冲", ("申", "寅"): "金木冲",
    ("卯", "酉"): "金木冲", ("酉", "卯"): "金木冲",
    ("辰", "戌"): "土土冲", ("戌", "辰"): "土土冲",
    ("巳", "亥"): "水火冲", ("亥", "巳"): "水火冲",
}

# 地支三合
DI_ZHI_SAN_HE = {
    ("申", "子", "辰"): "水局",
    ("亥", "卯", "未"): "木局",
    ("寅", "午", "戌"): "火局",
    ("巳", "酉", "丑"): "金局",
}

# 地支六害
DI_ZHI_LIU_HAI = {
    ("子", "未"): True, ("未", "子"): True,
    ("丑", "午"): True, ("午", "丑"): True,
    ("寅", "巳"): True, ("巳", "寅"): True,
    ("卯", "辰"): True, ("辰", "卯"): True,
    ("申", "亥"): True, ("亥", "申"): True,
    ("酉", "戌"): True, ("戌", "酉"): True,
}

# 纳音五行（六十甲子）
NAYIN_WUXING = {
    "甲子": "海中金", "乙丑": "海中金", "丙寅": "炉中火", "丁卯": "炉中火",
    "戊辰": "大林木", "己巳": "大林木", "庚午": "路旁土", "辛未": "路旁土",
    "壬申": "剑锋金", "癸酉": "剑锋金", "甲戌": "山头火", "乙亥": "山头火",
    "丙子": "涧下水", "丁丑": "涧下水", "戊寅": "城头土", "己卯": "城头土",
    "庚辰": "白蜡金", "辛巳": "白蜡金", "壬午": "杨柳木", "癸未": "杨柳木",
    "甲申": "泉中水", "乙酉": "泉中水", "丙戌": "屋上土", "丁亥": "屋上土",
    "戊子": "霹雳火", "己丑": "霹雳火", "庚寅": "松柏木", "辛卯": "松柏木",
    "壬辰": "长流水", "癸巳": "长流水", "甲午": "沙中金", "乙未": "沙中金",
    "丙申": "山下火", "丁酉": "山下火", "戊戌": "平地木", "己亥": "平地木",
    "庚子": "壁上土", "辛丑": "壁上土", "壬寅": "金箔金", "癸卯": "金箔金",
    "甲辰": "覆灯火", "乙巳": "覆灯火", "丙午": "天河水", "丁未": "天河水",
    "戊申": "大驿土", "己酉": "大驿土", "庚戌": "钗钏金", "辛亥": "钗钏金",
    "壬子": "桑柘木", "癸丑": "桑柘木", "甲寅": "大溪水", "乙卯": "大溪水",
    "丙辰": "沙中土", "丁巳": "沙中土", "戊午": "天上火", "己未": "天上火",
    "庚申": "石榴木", "辛酉": "石榴木", "壬戌": "大海水", "癸亥": "大海水",
}

# 纳音五行提取
def _nayin_to_wuxing(nayin: str) -> str:
    for wx in ["金", "木", "水", "火", "土"]:
        if wx in nayin:
            return wx
    return "土"

# 五行生克关系
WUXING_SHENG = {"金": "水", "水": "木", "木": "火", "火": "土", "土": "金"}
WUXING_KE = {"金": "木", "木": "土", "土": "水", "水": "火", "火": "金"}

# 生肖配对
SHENGXIAO = ["鼠", "牛", "虎", "兔", "龙", "蛇", "马", "羊", "猴", "鸡", "狗", "猪"]
SHENGXIAO_MATCH = {
    # 三合生肖组
    ("鼠", "龙"): 90, ("鼠", "猴"): 85, ("龙", "猴"): 85,
    ("牛", "蛇"): 90, ("牛", "鸡"): 85, ("蛇", "鸡"): 85,
    ("虎", "马"): 90, ("虎", "狗"): 85, ("马", "狗"): 85,
    ("兔", "羊"): 90, ("兔", "猪"): 85, ("羊", "猪"): 85,
    # 六合生肖组
    ("鼠", "牛"): 95, ("虎", "猪"): 95, ("兔", "狗"): 95,
    ("龙", "鸡"): 95, ("蛇", "猴"): 95, ("马", "羊"): 95,
    # 对冲生肖
    ("鼠", "马"): 20, ("牛", "羊"): 20, ("虎", "猴"): 20,
    ("兔", "鸡"): 20, ("龙", "狗"): 20, ("蛇", "猪"): 20,
}


# ============================================================================
# 数据模型
# ============================================================================

@dataclass
class MarriageAnalysis:
    """合婚分析结果"""
    # 双方信息
    name1: str
    name2: str
    bazi1: Dict[str, Any]  # 八字数据（含 day_master, pillars, wuxing 等）
    bazi2: Dict[str, Any]
    
    # 年柱纳音
    nayin1: str = ""
    nayin2: str = ""
    nayin_match: str = ""
    nayin_score: float = 0
    
    # 日柱天干
    day_gan1: str = ""
    day_gan2: str = ""
    ri_gan_he: str = ""
    ri_gan_score: float = 0
    
    # 地支关系
    zhi_relations: List[str] = field(default_factory=list)
    zhi_score: float = 0
    
    # 五行互补
    wuxing_bu: str = ""
    wuxing_score: float = 0
    
    # 生肖配对
    shengxiao1: str = ""
    shengxiao2: str = ""
    shengxiao_score: float = 0
    
    # 综合
    overall_score: float = 0
    overall_grade: str = ""
    summary: str = ""
    suggestions: List[str] = field(default_factory=list)


# ============================================================================
# 核心引擎
# ============================================================================

class MarriageEngine:
    """合婚分析引擎"""

    @classmethod
    def _get_year_ganzhi(cls, year: int) -> str:
        gan_idx = (year - 4) % 10
        zhi_idx = (year - 4) % 12
        return f"{TIAN_GAN[gan_idx]}{DI_ZHI[zhi_idx]}"

    @classmethod
    def _extract_from_bazi(cls, bazi: Dict[str, Any]) -> Dict[str, Any]:
        """从八字数据中提取关键信息"""
        pillars = bazi.get("pillars", {})
        analysis = bazi.get("analysis", {})
        day_master = bazi.get("day_master", "甲")
        input_data = bazi.get("input", {})
        
        year_pillar = pillars.get("year", "甲子")
        month_pillar = pillars.get("month", "甲子")
        day_pillar = pillars.get("day", "甲子")
        hour_pillar = pillars.get("hour", "甲子")
        
        return {
            "year_pillar": year_pillar,
            "month_pillar": month_pillar,
            "day_pillar": day_pillar,
            "hour_pillar": hour_pillar,
            "day_master": day_master,
            "year_gan": year_pillar[0] if len(year_pillar) >= 2 else "甲",
            "year_zhi": year_pillar[1] if len(year_pillar) >= 2 else "子",
            "day_gan": day_pillar[0] if len(day_pillar) >= 2 else "甲",
            "day_zhi": day_pillar[1] if len(day_pillar) >= 2 else "子",
            "month_gan": month_pillar[0] if len(month_pillar) >= 2 else "甲",
            "month_zhi": month_pillar[1] if len(month_pillar) >= 2 else "子",
            "hour_gan": hour_pillar[0] if len(hour_pillar) >= 2 else "甲",
            "hour_zhi": hour_pillar[1] if len(hour_pillar) >= 2 else "子",
            "wuxing": analysis.get("wuxing", {}),
            "wuxing_score": analysis.get("wuxing_score", {}),
            "shigan_count": analysis.get("shigan_count", {}),
            "year": input_data.get("year", 2000),
        }

    @classmethod
    def _analyze_nayin(cls, info1: Dict, info2: Dict) -> Tuple[str, float]:
        """分析年柱纳音匹配"""
        nayin1 = NAYIN_WUXING.get(info1["year_pillar"], "未知")
        nayin2 = NAYIN_WUXING.get(info2["year_pillar"], "未知")
        wx1 = _nayin_to_wuxing(nayin1)
        wx2 = _nayin_to_wuxing(nayin2)
        
        if wx1 == wx2:
            return f"{nayin1} vs {nayin2} → 五行相同，和谐", 85
        elif WUXING_SHENG.get(wx1) == wx2:
            return f"{nayin1} vs {nayin2} → {wx1}生{wx2}，男方生女方", 90
        elif WUXING_SHENG.get(wx2) == wx1:
            return f"{nayin1} vs {nayin2} → {wx2}生{wx1}，女方生男方", 80
        elif WUXING_KE.get(wx1) == wx2:
            return f"{nayin1} vs {nayin2} → {wx1}克{wx2}，男方克女方", 50
        elif WUXING_KE.get(wx2) == wx1:
            return f"{nayin1} vs {nayin2} → {wx2}克{wx1}，女方克男方", 40
        return f"{nayin1} vs {nayin2} → 五行无直接关系", 60

    @classmethod
    def _analyze_rigan(cls, info1: Dict, info2: Dict) -> Tuple[str, float]:
        """分析日柱天干五合"""
        gan1 = info1["day_gan"]
        gan2 = info2["day_gan"]
        he = TIAN_GAN_HE.get((gan1, gan2), "")
        if he:
            score = TIAN_GAN_HE_SCORE.get(he, 60)
            return f"{gan1}{gan2} → {he}，天干五合", score
        return f"{gan1}{gan2} → 无合", 50

    @classmethod
    def _analyze_dizhi(cls, info1: Dict, info2: Dict) -> Tuple[List[str], float]:
        """分析地支关系"""
        relations = []
        total_score = 60
        
        # 检查年支关系
        zhi1 = info1["year_zhi"]
        zhi2 = info2["year_zhi"]
        
        if (zhi1, zhi2) in DI_ZHI_LIU_HE:
            r = f"年支{zhi1}{zhi2}六合"
            relations.append(r)
            total_score += 15
        elif (zhi1, zhi2) in DI_ZHI_CHONG:
            r = f"年支{zhi1}{zhi2}六冲"
            relations.append(r)
            total_score -= 20
        elif (zhi1, zhi2) in DI_ZHI_LIU_HAI:
            r = f"年支{zhi1}{zhi2}六害"
            relations.append(r)
            total_score -= 15
        
        # 检查日支关系
        dz1 = info1["day_zhi"]
        dz2 = info2["day_zhi"]
        
        if (dz1, dz2) in DI_ZHI_LIU_HE:
            r = f"日支{dz1}{dz2}六合"
            relations.append(r)
            total_score += 20
        elif (dz1, dz2) in DI_ZHI_CHONG:
            r = f"日支{dz1}{dz2}六冲"
            relations.append(r)
            total_score -= 25
        elif (dz1, dz2) in DI_ZHI_LIU_HAI:
            r = f"日支{dz1}{dz2}六害"
            relations.append(r)
            total_score -= 20
        
        # 检查月支关系
        mz1 = info1["month_zhi"]
        mz2 = info2["month_zhi"]
        if (mz1, mz2) in DI_ZHI_LIU_HE:
            relations.append(f"月支{mz1}{mz2}六合")
            total_score += 10
        elif (mz1, mz2) in DI_ZHI_CHONG:
            relations.append(f"月支{mz1}{mz2}六冲")
            total_score -= 10
        
        if not relations:
            relations.append("地支无特殊关系")
        
        return relations, max(10, min(100, total_score))

    @classmethod
    def _analyze_wuxing(cls, info1: Dict, info2: Dict) -> Tuple[str, float]:
        """分析五行互补"""
        wx1 = info1.get("wuxing", {})
        wx2 = info2.get("wuxing", {})
        
        all_wx = ["金", "木", "水", "火", "土"]
        bu_ji = []
        has_bu = False
        
        for wx in all_wx:
            c1 = wx1.get(wx, 0)
            c2 = wx2.get(wx, 0)
            if c1 == 0 and c2 >= 2:
                bu_ji.append(f"{wx}(女方补男方)")
                has_bu = True
            elif c2 == 0 and c1 >= 2:
                bu_ji.append(f"{wx}(男方补女方)")
                has_bu = True
        
        if has_bu:
            return "五行互补: " + ", ".join(bu_ji), 85
        elif wx1 == wx2:
            return "五行分布相似，较为和谐", 70
        return "五行各有偏重，需注意调候", 55

    @classmethod
    def _analyze_shengxiao(cls, info1: Dict, info2: Dict) -> Tuple[str, str, str, float]:
        """分析生肖配对"""
        zhi1 = info1["year_zhi"]
        zhi2 = info2["year_zhi"]
        sx1 = SHENGXIAO[DI_ZHI.index(zhi1)]
        sx2 = SHENGXIAO[DI_ZHI.index(zhi2)]
        
        score = SHENGXIAO_MATCH.get((sx1, sx2), 50)
        if (sx2, sx1) in SHENGXIAO_MATCH:
            score = SHENGXIAO_MATCH.get((sx2, sx1), 50)
        
        if score >= 90:
            desc = "六合佳配，天作之合"
        elif score >= 80:
            desc = "三合吉配，和谐美满"
        elif score >= 60:
            desc = "生肖一般，无冲无害"
        elif score >= 30:
            desc = "生肖相冲，需多包容"
        else:
            desc = "严重相冲，婚姻多阻"
        
        return sx1, sx2, desc, score

    @classmethod
    def analyze(cls, name1: str, bazi1: Dict[str, Any],
               name2: str, bazi2: Dict[str, Any]) -> MarriageAnalysis:
        """
        完整合婚分析
        
        参数:
            name1: 男方姓名
            bazi1: 男方八字数据
            name2: 女方姓名
            bazi2: 女方八字数据
        """
        info1 = cls._extract_from_bazi(bazi1)
        info2 = cls._extract_from_bazi(bazi2)
        
        # 纳音分析
        nayin_match, nayin_score = cls._analyze_nayin(info1, info2)
        
        # 日干五合
        ri_gan_he, ri_gan_score = cls._analyze_rigan(info1, info2)
        
        # 地支关系
        zhi_relations, zhi_score = cls._analyze_dizhi(info1, info2)
        
        # 五行互补
        wuxing_bu, wuxing_score = cls._analyze_wuxing(info1, info2)
        
        # 生肖配对
        sx1, sx2, sx_desc, sx_score = cls._analyze_shengxiao(info1, info2)
        
        # 综合评分（加权）
        overall = (
            nayin_score * 0.15 +
            ri_gan_score * 0.25 +
            zhi_score * 0.25 +
            wuxing_score * 0.20 +
            sx_score * 0.15
        )
        
        if overall >= 80:
            grade = "上等婚配"
        elif overall >= 65:
            grade = "中等婚配"
        elif overall >= 50:
            grade = "一般婚配"
        else:
            grade = "下等婚配"
        
        # 总结
        parts = []
        if ri_gan_he and "合" in ri_gan_he:
            parts.append("日柱天干相合，夫妻缘分深厚")
        if any("冲" in r for r in zhi_relations):
            parts.append("存在地支冲克，需注意沟通包容")
        if wuxing_score >= 80:
            parts.append("五行互补良好，相互扶持")
        if sx_score >= 85:
            parts.append("生肖匹配极佳")
        
        summary = "；".join(parts) if parts else "婚配一般，需双方共同努力经营"
        
        # 建议
        suggestions = []
        if zhi_score < 50:
            suggestions.append("地支冲克较重，建议婚后多沟通，培养共同兴趣")
        if wuxing_score < 60:
            suggestions.append("五行互补不足，可通过家居风水、穿衣颜色等调和")
        if sx_score < 40:
            suggestions.append("生肖相冲，可通过择吉日、风水布局化解")
        if not suggestions:
            suggestions.append("八字匹配度较高，婚姻基础良好")
        
        return MarriageAnalysis(
            name1=name1, name2=name2,
            bazi1=bazi1, bazi2=bazi2,
            nayin1=NAYIN_WUXING.get(info1["year_pillar"], ""),
            nayin2=NAYIN_WUXING.get(info2["year_pillar"], ""),
            nayin_match=nayin_match,
            nayin_score=nayin_score,
            day_gan1=info1["day_gan"],
            day_gan2=info2["day_gan"],
            ri_gan_he=ri_gan_he,
            ri_gan_score=ri_gan_score,
            zhi_relations=zhi_relations,
            zhi_score=zhi_score,
            wuxing_bu=wuxing_bu,
            wuxing_score=wuxing_score,
            shengxiao1=sx1, shengxiao2=sx2,
            shengxiao_score=sx_score,
            overall_score=round(overall, 1),
            overall_grade=grade,
            summary=summary,
            suggestions=suggestions,
        )

    @classmethod
    def format_text(cls, result: MarriageAnalysis) -> str:
        """格式化输出"""
        lines = []
        lines.append("╔══════════════════════════════════════╗")
        lines.append("║       八 字 合 婚 分 析              ║")
        lines.append("╠══════════════════════════════════════╣")
        lines.append(f"║ 男方: {result.name1}  日主: {result.day_gan1}")
        lines.append(f"║ 女方: {result.name2}  日主: {result.day_gan2}")
        lines.append("╠══════════════════════════════════════╣")
        lines.append(f"║ 年柱纳音: {result.nayin1} vs {result.nayin2}")
        lines.append(f"║ 纳音评分: {result.nayin_score}分 - {result.nayin_match}")
        lines.append(f"║ 日干关系: {result.ri_gan_he} ({result.ri_gan_score}分)")
        lines.append(f"║ 地支关系: {', '.join(result.zhi_relations)} ({result.zhi_score}分)")
        lines.append(f"║ 五行互补: {result.wuxing_bu} ({result.wuxing_score}分)")
        lines.append(f"║ 生肖: {result.shengxiao1} vs {result.shengxiao2} ({result.shengxiao_score}分)")
        lines.append("╠══════════════════════════════════════╣")
        lines.append(f"║ 综合评分: {result.overall_score}/100")
        lines.append(f"║ 婚配等级: {result.overall_grade}")
        lines.append(f"║ 总结: {result.summary}")
        lines.append(f"║ 建议: {result.suggestions[0] if result.suggestions else ''}")
        lines.append("╚══════════════════════════════════════╝")
        return "\n".join(lines)


# ============================================================================
# 便捷函数
# ============================================================================

def analyze_marriage(name1: str, bazi1: Dict[str, Any],
                     name2: str, bazi2: Dict[str, Any]) -> MarriageAnalysis:
    """快速合婚分析"""
    return MarriageEngine.analyze(name1, bazi1, name2, bazi2)


__all__ = [
    "MarriageEngine", "MarriageAnalysis",
    "analyze_marriage", "NAYIN_WUXING", "SHENGXIAO",
]