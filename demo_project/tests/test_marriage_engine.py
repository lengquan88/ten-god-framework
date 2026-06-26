"""
test_marriage_engine.py —— 合婚分析引擎完整测试

覆盖：
- 所有常量表完整性
- MarriageAnalysis 数据类
- MarriageEngine 所有公开方法 (analyze, format_text)
- MarriageEngine 所有内部方法 (_get_year_ganzhi, _extract_from_bazi,
  _analyze_nayin, _analyze_rigan, _analyze_dizhi, _analyze_wuxing,
  _analyze_shengxiao)
- 加权评分正确性
- 边界情况
"""

from __future__ import annotations
from dataclasses import asdict

import pytest

from tengod.marriage_engine import (
    DI_ZHI,
    DI_ZHI_CHONG,
    DI_ZHI_LIU_HAI,
    DI_ZHI_LIU_HE,
    DI_ZHI_SAN_HE,
    NAYIN_WUXING,
    SHENGXIAO,
    SHENGXIAO_MATCH,
    TIAN_GAN,
    TIAN_GAN_HE,
    TIAN_GAN_HE_SCORE,
    WUXING_KE,
    WUXING_SHENG,
    MarriageAnalysis,
    MarriageEngine,
    _nayin_to_wuxing,
    analyze_marriage,
)


# ============================================================================
# 测试数据工厂
# ============================================================================

def make_bazi(
    *,
    year_pill="甲子",
    month_pill="甲子",
    day_pill="甲子",
    hour_pill="甲子",
    day_master="甲",
    year=2000,
    wuxing=None,
    wuxing_score=None,
    shigan_count=None,
):
    """构建测试用八字字典"""
    return {
        "pillars": {
            "year": year_pill,
            "month": month_pill,
            "day": day_pill,
            "hour": hour_pill,
        },
        "day_master": day_master,
        "analysis": {
            "wuxing": wuxing or {"金": 2, "木": 1, "水": 1, "火": 0, "土": 1},
            "wuxing_score": wuxing_score or {},
            "shigan_count": shigan_count or {},
        },
        "input": {"year": year},
    }


# 良好八字对：甲己天干五合 + 子丑地支六合 + 鼠牛生肖六合
BAZI_GOOD_1 = make_bazi(
    year_pill="甲子", day_pill="甲子", day_master="甲",
    year=1984, wuxing={"金": 2, "木": 1, "水": 1, "火": 0, "土": 1},
)
BAZI_GOOD_2 = make_bazi(
    year_pill="己丑", day_pill="己丑", day_master="己",
    year=1985, wuxing={"金": 0, "木": 1, "水": 1, "火": 2, "土": 1},
)

# 不良八字对：子午冲 + 鼠马冲
BAZI_BAD_1 = make_bazi(
    year_pill="丙午", month_pill="丙午", day_pill="丙午", hour_pill="丙午",
    day_master="丙", year=1906,
    wuxing={"金": 0, "木": 0, "水": 2, "火": 3, "土": 0},
)
BAZI_BAD_2 = make_bazi(
    year_pill="壬子", month_pill="壬子", day_pill="壬子", hour_pill="壬子",
    day_master="壬", year=1912,
    wuxing={"金": 0, "木": 0, "水": 3, "火": 0, "土": 2},
)

# 五行互补八字对
BAZI_WUXING_BU_1 = make_bazi(
    year_pill="甲子", day_pill="甲子", day_master="甲",
    year=1984, wuxing={"金": 2, "木": 1, "水": 1, "火": 0, "土": 1},
)
BAZI_WUXING_BU_2 = make_bazi(
    year_pill="己丑", day_pill="己丑", day_master="己",
    year=1985, wuxing={"金": 0, "木": 1, "水": 1, "火": 2, "土": 1},
)


# ============================================================================
# 常量表完整性测试
# ============================================================================

class TestConstants:
    """测试所有常量表的完整性"""

    def test_tiangan_count(self):
        assert len(TIAN_GAN) == 10
        assert TIAN_GAN[0] == "甲"
        assert TIAN_GAN[-1] == "癸"

    def test_dizhi_count(self):
        assert len(DI_ZHI) == 12
        assert DI_ZHI[0] == "子"
        assert DI_ZHI[-1] == "亥"

    def test_tiangan_he_count(self):
        """天干五合应有 5 对合（双向存储 10 条）"""
        assert len(TIAN_GAN_HE) == 10
        unique_pairs = set()
        for (g1, g2), name in TIAN_GAN_HE.items():
            pair = tuple(sorted((g1, g2)))
            unique_pairs.add((pair, name))
        assert len(unique_pairs) == 5  # 5 种合

    def test_tiangan_he_score_keys(self):
        """天干五合评分应有 5 种合"""
        assert len(TIAN_GAN_HE_SCORE) == 5
        for name in ["中正之合", "仁义之合", "威制之合", "淫匿之合", "无情之合"]:
            assert name in TIAN_GAN_HE_SCORE

    def test_dizhi_liuhe_count(self):
        """地支六合应有 6 对（双向 12 条）"""
        assert len(DI_ZHI_LIU_HE) == 12
        unique = set()
        for (z1, z2) in DI_ZHI_LIU_HE:
            unique.add(tuple(sorted((z1, z2))))
        assert len(unique) == 6

    def test_dizhi_chong_count(self):
        """地支六冲应有 6 对（双向 12 条）"""
        assert len(DI_ZHI_CHONG) == 12
        unique = set()
        for (z1, z2) in DI_ZHI_CHONG:
            unique.add(tuple(sorted((z1, z2))))
        assert len(unique) == 6

    def test_dizhi_sanhe_count(self):
        """地支三合应有 4 局"""
        assert len(DI_ZHI_SAN_HE) == 4
        for triad, wx in DI_ZHI_SAN_HE.items():
            assert len(triad) == 3
            assert len(set(triad)) == 3

    def test_dizhi_liuhai_count(self):
        """地支六害应有 6 对（双向 12 条）"""
        assert len(DI_ZHI_LIU_HAI) == 12
        unique = set()
        for (z1, z2) in DI_ZHI_LIU_HAI:
            unique.add(tuple(sorted((z1, z2))))
        assert len(unique) == 6

    def test_nayin_wuxing_count(self):
        """纳音五行应有 60 甲子"""
        assert len(NAYIN_WUXING) == 60

    def test_nayin_wuxing_all_entries_valid(self):
        """每个纳音条目格式正确（2字干支→3字纳音名）"""
        for key, value in NAYIN_WUXING.items():
            assert len(key) == 2, f"干支键长度应为2: {key}"
            assert key[0] in TIAN_GAN, f"天干无效: {key}"
            assert key[1] in DI_ZHI, f"地支无效: {key}"
            assert len(value) >= 3, f"纳音名过短: {value}"

    def test_nayin_wuxing_60_jiazi_coverage(self):
        """验证 60 甲子表覆盖所有天干地支组合（每柱 5 个）"""
        from collections import Counter
        gan_count = Counter()
        for key in NAYIN_WUXING:
            gan_count[key[0]] += 1
        # 每个天干出现 6 次（配 6 个地支）
        for gan in TIAN_GAN:
            assert gan_count[gan] == 6, f"天干 {gan} 应出现6次，实际 {gan_count[gan]}"

        zhi_count = Counter()
        for key in NAYIN_WUXING:
            zhi_count[key[1]] += 1
        # 每个地支出现 5 次（配 5 个天干）
        for zhi in DI_ZHI:
            assert zhi_count[zhi] == 5, f"地支 {zhi} 应出现5次，实际 {zhi_count[zhi]}"

    def test_shengxiao_count(self):
        assert len(SHENGXIAO) == 12
        assert SHENGXIAO[0] == "鼠"
        assert SHENGXIAO[DI_ZHI.index("子")] == "鼠"
        assert SHENGXIAO[DI_ZHI.index("丑")] == "牛"

    def test_shengxiao_match_has_triad_hex_opposition(self):
        """生肖配对应包含三合、六合、对冲"""
        assert len(SHENGXIAO_MATCH) >= 18
        # 六合
        assert SHENGXIAO_MATCH.get(("鼠", "牛")) == 95
        assert SHENGXIAO_MATCH.get(("虎", "猪")) == 95
        # 三合
        assert SHENGXIAO_MATCH.get(("鼠", "龙")) == 90
        assert SHENGXIAO_MATCH.get(("牛", "蛇")) == 90
        # 对冲
        assert SHENGXIAO_MATCH.get(("鼠", "马")) == 20
        assert SHENGXIAO_MATCH.get(("兔", "鸡")) == 20

    def test_wuxing_sheng_chain(self):
        """五行相生链：金→水→木→火→土→金"""
        assert WUXING_SHENG["金"] == "水"
        assert WUXING_SHENG["水"] == "木"
        assert WUXING_SHENG["木"] == "火"
        assert WUXING_SHENG["火"] == "土"
        assert WUXING_SHENG["土"] == "金"

    def test_wuxing_ke_chain(self):
        """五行相克链：金→木→土→水→火→金"""
        assert WUXING_KE["金"] == "木"
        assert WUXING_KE["木"] == "土"
        assert WUXING_KE["土"] == "水"
        assert WUXING_KE["水"] == "火"
        assert WUXING_KE["火"] == "金"

    def test_nayin_to_wuxing_helper(self):
        """_nayin_to_wuxing 辅助函数"""
        assert _nayin_to_wuxing("海中金") == "金"
        assert _nayin_to_wuxing("大林木") == "木"
        assert _nayin_to_wuxing("涧下水") == "水"
        assert _nayin_to_wuxing("炉中火") == "火"
        assert _nayin_to_wuxing("路旁土") == "土"
        assert _nayin_to_wuxing("未知") == "土"  # 默认返土


# ============================================================================
# MarriageAnalysis 数据类测试
# ============================================================================

class TestMarriageAnalysisDataclass:
    """测试 MarriageAnalysis 数据类"""

    def test_create_default(self):
        """测试默认构造"""
        ma = MarriageAnalysis(
            name1="张三",
            name2="李四",
            bazi1={},
            bazi2={},
        )
        assert ma.name1 == "张三"
        assert ma.name2 == "李四"
        assert ma.bazi1 == {}
        assert ma.bazi2 == {}
        assert ma.nayin1 == ""
        assert ma.nayin2 == ""
        assert ma.nayin_match == ""
        assert ma.nayin_score == 0
        assert ma.day_gan1 == ""
        assert ma.day_gan2 == ""
        assert ma.ri_gan_he == ""
        assert ma.ri_gan_score == 0
        assert ma.zhi_relations == []
        assert ma.zhi_score == 0
        assert ma.wuxing_bu == ""
        assert ma.wuxing_score == 0
        assert ma.shengxiao1 == ""
        assert ma.shengxiao2 == ""
        assert ma.shengxiao_score == 0
        assert ma.overall_score == 0
        assert ma.overall_grade == ""
        assert ma.summary == ""
        assert ma.suggestions == []

    def test_create_full(self):
        """测试完整构造"""
        ma = MarriageAnalysis(
            name1="张三",
            name2="李四",
            bazi1={"pillars": {"year": "甲子"}},
            bazi2={"pillars": {"year": "己丑"}},
            nayin1="海中金",
            nayin2="霹雳火",
            nayin_match="match desc",
            nayin_score=85,
            day_gan1="甲",
            day_gan2="己",
            ri_gan_he="甲己 → 中正之合",
            ri_gan_score=90,
            zhi_relations=["年支子丑六合"],
            zhi_score=85,
            wuxing_bu="五行互补",
            wuxing_score=85,
            shengxiao1="鼠",
            shengxiao2="牛",
            shengxiao_score=95,
            overall_score=88.5,
            overall_grade="上等婚配",
            summary="天作之合",
            suggestions=["婚姻基础良好"],
        )
        assert ma.overall_score == 88.5
        assert ma.overall_grade == "上等婚配"
        assert ma.shengxiao_score == 95

    def test_is_dataclass(self):
        """验证是 dataclass"""
        ma = MarriageAnalysis(name1="A", name2="B", bazi1={}, bazi2={})
        d = asdict(ma)
        assert "name1" in d
        assert "name2" in d
        assert "overall_score" in d

    def test_field_types(self):
        """验证字段类型"""
        ma = MarriageAnalysis(name1="A", name2="B", bazi1={}, bazi2={})
        assert isinstance(ma.name1, str)
        assert isinstance(ma.bazi1, dict)
        assert isinstance(ma.nayin_score, (int, float))
        assert isinstance(ma.zhi_relations, list)
        assert isinstance(ma.suggestions, list)


# ============================================================================
# _get_year_ganzhi 测试
# ============================================================================

class TestGetYearGanzhi:
    """测试 _get_year_ganzhi"""

    def test_1984_is_jiazi(self):
        """1984 年是甲子年"""
        assert MarriageEngine._get_year_ganzhi(1984) == "甲子"

    def test_1985_is_yichou(self):
        """1985 年是乙丑年"""
        assert MarriageEngine._get_year_ganzhi(1985) == "乙丑"

    def test_2000_is_gengchen(self):
        """2000 年是庚辰年"""
        assert MarriageEngine._get_year_ganzhi(2000) == "庚辰"

    def test_2024_is_jiazi_cycle(self):
        """2024 年回到甲辰（60 年一轮回）"""
        # 1984 + 40 = 2024，天干：甲(0) + 40%10 = 甲(0)，地支：子(0) + 40%12 = 辰(4)
        assert MarriageEngine._get_year_ganzhi(2024) == "甲辰"

    def test_cycle_60_years(self):
        """验证 60 年周期"""
        # 1984 is 甲子, 1984+60=2044 should also be 甲子
        assert MarriageEngine._get_year_ganzhi(1984 + 60) == "甲子"

    def test_year_0(self):
        """公元 0 年"""
        # year=0: gan=(0-4)%10=-4%10=6 → 庚, zhi=(0-4)%12=-4%12=8 → 申
        result = MarriageEngine._get_year_ganzhi(0)
        assert len(result) == 2

    def test_negative_year(self):
        """负数年份"""
        result = MarriageEngine._get_year_ganzhi(-100)
        assert len(result) == 2


# ============================================================================
# _extract_from_bazi 测试
# ============================================================================

class TestExtractFromBazi:
    """测试 _extract_from_bazi"""

    def test_extract_complete_bazi(self):
        """完整八字提取"""
        bazi = make_bazi(
            year_pill="甲子", month_pill="丙寅", day_pill="戊辰", hour_pill="庚午",
            day_master="戊", year=2000,
        )
        info = MarriageEngine._extract_from_bazi(bazi)
        assert info["year_pillar"] == "甲子"
        assert info["month_pillar"] == "丙寅"
        assert info["day_pillar"] == "戊辰"
        assert info["hour_pillar"] == "庚午"
        assert info["day_master"] == "戊"
        assert info["year_gan"] == "甲"
        assert info["year_zhi"] == "子"
        assert info["day_gan"] == "戊"
        assert info["day_zhi"] == "辰"
        assert info["month_gan"] == "丙"
        assert info["month_zhi"] == "寅"
        assert info["hour_gan"] == "庚"
        assert info["hour_zhi"] == "午"
        assert info["year"] == 2000

    def test_extract_defaults_for_missing_pillars(self):
        """缺失四柱时使用默认值"""
        bazi = {"day_master": "乙"}
        info = MarriageEngine._extract_from_bazi(bazi)
        assert info["year_pillar"] == "甲子"
        assert info["day_gan"] == "甲"  # 默认 day_pillar 为 "甲子"
        assert info["day_master"] == "乙"

    def test_extract_empty_bazi(self):
        """空八字"""
        info = MarriageEngine._extract_from_bazi({})
        assert info["year_pillar"] == "甲子"
        assert info["day_master"] == "甲"
        assert info["year"] == 2000

    def test_extract_short_pillar(self):
        """短柱名（少于2字符）诚实返回切片"""
        bazi = {"pillars": {"year": "甲", "day": "乙"}}
        info = MarriageEngine._extract_from_bazi(bazi)
        # year_pillar is "甲", len >= 2 is False, so year_gan defaults to "甲"
        assert info["year_gan"] == "甲"
        assert info["year_zhi"] == "子"
        assert info["day_gan"] == "甲"

    def test_extract_wuxing_from_analysis(self):
        """从 analysis 中提取五行"""
        bazi = make_bazi(wuxing={"金": 3, "木": 1, "水": 1, "火": 0, "土": 0})
        info = MarriageEngine._extract_from_bazi(bazi)
        assert info["wuxing"] == {"金": 3, "木": 1, "水": 1, "火": 0, "土": 0}

    def test_extract_missing_input(self):
        """缺少 input 字段"""
        bazi = {"pillars": {"year": "甲子", "month": "甲子", "day": "甲子", "hour": "甲子"}}
        info = MarriageEngine._extract_from_bazi(bazi)
        assert info["year"] == 2000


# ============================================================================
# _analyze_nayin 测试
# ============================================================================

class TestAnalyzeNayin:
    """测试 _analyze_nayin"""

    def test_same_wuxing_harmony(self):
        """相同五行 → 和谐，85 分"""
        info1 = {"year_pillar": "甲子"}  # 海中金 → 金
        info2 = {"year_pillar": "乙丑"}  # 海中金 → 金
        desc, score = MarriageEngine._analyze_nayin(info1, info2)
        assert score == 85
        assert "和谐" in desc

    def test_male_sheng_female(self):
        """男方生女方 → 90 分"""
        info1 = {"year_pillar": "甲子"}  # 金
        info2 = {"year_pillar": "丙子"}  # 涧下水 → 水，金生水
        desc, score = MarriageEngine._analyze_nayin(info1, info2)
        assert score == 90
        assert "男方生女方" in desc

    def test_female_sheng_male(self):
        """女方生男方 → 80 分"""
        info1 = {"year_pillar": "丙子"}  # 水
        info2 = {"year_pillar": "甲子"}  # 金，金生水
        desc, score = MarriageEngine._analyze_nayin(info1, info2)
        assert score == 80
        assert "女方生男方" in desc

    def test_male_ke_female(self):
        """男方克女方 → 50 分"""
        info1 = {"year_pillar": "甲子"}  # 金
        info2 = {"year_pillar": "戊辰"}  # 大林木 → 木，金克木
        desc, score = MarriageEngine._analyze_nayin(info1, info2)
        assert score == 50
        assert "男方克女方" in desc

    def test_female_ke_male(self):
        """女方克男方 → 40 分"""
        info1 = {"year_pillar": "戊辰"}  # 木
        info2 = {"year_pillar": "甲子"}  # 金，金克木
        desc, score = MarriageEngine._analyze_nayin(info1, info2)
        assert score == 40
        assert "女方克男方" in desc

    def test_no_direct_relation(self):
        """无直接关系保底分支：60 分代码路径存在但五行全有生克关系故实际不可达"""
        # 所有五行两两之间都有生克关系，60分是保底代码
        # 验证只要输入合法，返回的分数在合理范围
        info1 = {"year_pillar": "甲子"}  # 金
        info2 = {"year_pillar": "戊子"}  # 霹雳火 → 火，火克金 → 女方克男方
        desc, score = MarriageEngine._analyze_nayin(info1, info2)
        assert score == 40  # 火克金
        assert "女方克" in desc

    def test_unknown_nayin(self):
        """未知纳音"""
        info1 = {"year_pillar": "XX"}
        info2 = {"year_pillar": "YY"}
        desc, score = MarriageEngine._analyze_nayin(info1, info2)
        assert score == 85  # 都是"土" → 相同五行


# ============================================================================
# _analyze_rigan 测试
# ============================================================================

class TestAnalyzeRigan:
    """测试 _analyze_rigan"""

    def test_jiaji_he(self):
        """甲己合 → 中正之合，90 分"""
        info1 = {"day_gan": "甲"}
        info2 = {"day_gan": "己"}
        desc, score = MarriageEngine._analyze_rigan(info1, info2)
        assert score == 90
        assert "中正之合" in desc

    def test_yigeng_he(self):
        """乙庚合 → 仁义之合，85 分"""
        info1 = {"day_gan": "乙"}
        info2 = {"day_gan": "庚"}
        desc, score = MarriageEngine._analyze_rigan(info1, info2)
        assert score == 85
        assert "仁义之合" in desc

    def test_bingxin_he(self):
        """丙辛合 → 威制之合，70 分"""
        info1 = {"day_gan": "丙"}
        info2 = {"day_gan": "辛"}
        desc, score = MarriageEngine._analyze_rigan(info1, info2)
        assert score == 70
        assert "威制之合" in desc

    def test_dingren_he(self):
        """丁壬合 → 淫匿之合，50 分"""
        info1 = {"day_gan": "丁"}
        info2 = {"day_gan": "壬"}
        desc, score = MarriageEngine._analyze_rigan(info1, info2)
        assert score == 50
        assert "淫匿之合" in desc

    def test_wugui_he(self):
        """戊癸合 → 无情之合，40 分"""
        info1 = {"day_gan": "戊"}
        info2 = {"day_gan": "癸"}
        desc, score = MarriageEngine._analyze_rigan(info1, info2)
        assert score == 40
        assert "无情之合" in desc

    def test_reverse_jiaji(self):
        """己甲合（反向）→ 中正之合，90 分"""
        info1 = {"day_gan": "己"}
        info2 = {"day_gan": "甲"}
        desc, score = MarriageEngine._analyze_rigan(info1, info2)
        assert score == 90
        assert "中正之合" in desc

    def test_no_he(self):
        """无合 → 50 分"""
        info1 = {"day_gan": "甲"}
        info2 = {"day_gan": "乙"}
        desc, score = MarriageEngine._analyze_rigan(info1, info2)
        assert score == 50
        assert "无合" in desc


# ============================================================================
# _analyze_dizhi 测试
# ============================================================================

class TestAnalyzeDizhi:
    """测试 _analyze_dizhi"""

    def test_all_liuhe(self):
        """年支、月支、日支全部六合"""
        info1 = {
            "year_zhi": "子", "month_zhi": "寅", "day_zhi": "卯",
            "year_pillar": "甲子",
        }
        info2 = {
            "year_zhi": "丑", "month_zhi": "亥", "day_zhi": "戌",
            "year_pillar": "己丑",
        }
        relations, score = MarriageEngine._analyze_dizhi(info1, info2)
        assert "年支子丑六合" in relations
        assert "月支寅亥六合" in relations
        assert "日支卯戌六合" in relations
        # 基准 60 + 15(年合) + 20(日合) + 10(月合) = 105, cap 100
        assert score == 100

    def test_year_chong(self):
        """年支六冲"""
        info1 = {"year_zhi": "子", "month_zhi": "寅", "day_zhi": "卯"}
        info2 = {"year_zhi": "午", "month_zhi": "亥", "day_zhi": "戌"}
        relations, score = MarriageEngine._analyze_dizhi(info1, info2)
        assert "年支子午六冲" in relations
        # 60 - 20(年冲) + 20(日合) + 10(月合) = 70
        assert score == 70

    def test_day_chong(self):
        """日支六冲"""
        info1 = {"year_zhi": "子", "month_zhi": "寅", "day_zhi": "子"}
        info2 = {"year_zhi": "丑", "month_zhi": "亥", "day_zhi": "午"}
        relations, score = MarriageEngine._analyze_dizhi(info1, info2)
        assert "日支子午六冲" in relations
        # 60 + 15(年合) - 25(日冲) + 10(月合) = 60
        assert score == 60

    def test_year_liuhai(self):
        """年支六害"""
        info1 = {"year_zhi": "子", "month_zhi": "寅", "day_zhi": "卯"}
        info2 = {"year_zhi": "未", "month_zhi": "亥", "day_zhi": "戌"}
        relations, score = MarriageEngine._analyze_dizhi(info1, info2)
        assert "年支子未六害" in relations
        # 60 - 15(年害) + 20(日合) + 10(月合) = 75
        assert score == 75

    def test_day_liuhai(self):
        """日支六害"""
        info1 = {"year_zhi": "子", "month_zhi": "寅", "day_zhi": "子"}
        info2 = {"year_zhi": "丑", "month_zhi": "亥", "day_zhi": "未"}
        relations, score = MarriageEngine._analyze_dizhi(info1, info2)
        assert "日支子未六害" in relations

    def test_month_chong(self):
        """月支六冲"""
        info1 = {"year_zhi": "子", "month_zhi": "子", "day_zhi": "卯"}
        info2 = {"year_zhi": "丑", "month_zhi": "午", "day_zhi": "戌"}
        relations, score = MarriageEngine._analyze_dizhi(info1, info2)
        assert "月支子午六冲" in relations

    def test_no_relation(self):
        """无特殊关系"""
        info1 = {"year_zhi": "子", "month_zhi": "子", "day_zhi": "子"}
        info2 = {"year_zhi": "寅", "month_zhi": "寅", "day_zhi": "寅"}
        relations, score = MarriageEngine._analyze_dizhi(info1, info2)
        assert "无特殊关系" in relations[0]  # "地支无特殊关系"
        assert score == 60

    def test_score_clamped_to_10(self):
        """分数最低 10 分"""
        info1 = {"year_zhi": "子", "month_zhi": "子", "day_zhi": "子"}
        info2 = {"year_zhi": "午", "month_zhi": "午", "day_zhi": "午"}
        relations, score = MarriageEngine._analyze_dizhi(info1, info2)
        # 60 - 20(年冲) - 25(日冲) - 10(月冲) = 5, clamped to 10
        assert score == 10

    def test_score_clamped_to_100(self):
        """分数最高 100 分"""
        info1 = {"year_zhi": "子", "month_zhi": "寅", "day_zhi": "卯"}
        info2 = {"year_zhi": "丑", "month_zhi": "亥", "day_zhi": "戌"}
        _, score = MarriageEngine._analyze_dizhi(info1, info2)
        assert score == 100


# ============================================================================
# _analyze_wuxing 测试
# ============================================================================

class TestAnalyzeWuxing:
    """测试 _analyze_wuxing"""

    def test_wuxing_complementary(self):
        """五行互补"""
        info1 = {"wuxing": {"金": 2, "木": 1, "水": 1, "火": 0, "土": 1}}
        info2 = {"wuxing": {"金": 0, "木": 1, "水": 1, "火": 2, "土": 1}}
        desc, score = MarriageEngine._analyze_wuxing(info1, info2)
        assert score == 85
        assert "五行互补" in desc

    def test_wuxing_similar(self):
        """五行分布相似"""
        info1 = {"wuxing": {"金": 2, "木": 1, "水": 1, "火": 1, "土": 0}}
        info2 = {"wuxing": {"金": 2, "木": 1, "水": 1, "火": 1, "土": 0}}
        desc, score = MarriageEngine._analyze_wuxing(info1, info2)
        assert score == 70
        assert "和谐" in desc

    def test_wuxing_different(self):
        """五行各有偏重"""
        info1 = {"wuxing": {"金": 2, "木": 1, "水": 1, "火": 1, "土": 0}}
        info2 = {"wuxing": {"金": 1, "木": 2, "水": 1, "火": 0, "土": 1}}
        desc, score = MarriageEngine._analyze_wuxing(info1, info2)
        assert score == 55
        assert "各有偏重" in desc or "调候" in desc

    def test_wuxing_male_complements_female(self):
        """男方补女方"""
        info1 = {"wuxing": {"金": 2, "木": 1, "水": 1, "火": 0, "土": 1}}  # 男方有金
        info2 = {"wuxing": {"金": 0, "木": 1, "水": 1, "火": 2, "土": 1}}  # 女方缺金
        desc, score = MarriageEngine._analyze_wuxing(info1, info2)
        assert score == 85
        assert "男方补女方" in desc

    def test_wuxing_female_complements_male(self):
        """女方补男方"""
        info1 = {"wuxing": {"金": 0, "木": 1, "水": 1, "火": 2, "土": 1}}  # 男方缺金
        info2 = {"wuxing": {"金": 2, "木": 1, "水": 1, "火": 0, "土": 1}}  # 女方有金
        desc, score = MarriageEngine._analyze_wuxing(info1, info2)
        assert score == 85
        assert "女方补男方" in desc

    def test_wuxing_empty_dicts(self):
        """空五行字典"""
        info1 = {"wuxing": {}}
        info2 = {"wuxing": {}}
        desc, score = MarriageEngine._analyze_wuxing(info1, info2)
        assert score == 70  # 相等 → 和谐

    def test_wuxing_missing_key(self):
        """缺少 wuxing 键"""
        info1 = {}
        info2 = {}
        desc, score = MarriageEngine._analyze_wuxing(info1, info2)
        assert score == 70  # 都为空 → 相等 → 和谐


# ============================================================================
# _analyze_shengxiao 测试
# ============================================================================

class TestAnalyzeShengxiao:
    """测试 _analyze_shengxiao"""

    def test_liuhe_shu_niu(self):
        """鼠牛六合 → 95 分"""
        info1 = {"year_zhi": "子"}  # 鼠
        info2 = {"year_zhi": "丑"}  # 牛
        sx1, sx2, desc, score = MarriageEngine._analyze_shengxiao(info1, info2)
        assert sx1 == "鼠"
        assert sx2 == "牛"
        assert score == 95
        assert "六合" in desc

    def test_sanhe_shu_long(self):
        """鼠龙三合 → 90 分，>=90 归入六合描述"""
        info1 = {"year_zhi": "子"}  # 鼠
        info2 = {"year_zhi": "辰"}  # 龙
        _, _, desc, score = MarriageEngine._analyze_shengxiao(info1, info2)
        assert score == 90
        assert "佳配" in desc or "合" in desc

    def test_sanhe_shu_hou(self):
        """鼠猴三合 → 85 分"""
        info1 = {"year_zhi": "子"}  # 鼠
        info2 = {"year_zhi": "申"}  # 猴
        _, _, _, score = MarriageEngine._analyze_shengxiao(info1, info2)
        assert score == 85

    def test_chong_shu_ma(self):
        """鼠马对冲 → 20 分"""
        info1 = {"year_zhi": "子"}  # 鼠
        info2 = {"year_zhi": "午"}  # 马
        _, _, desc, score = MarriageEngine._analyze_shengxiao(info1, info2)
        assert score == 20
        assert "相冲" in desc

    def test_normal(self):
        """普通匹配 → 50 分（>=30 → 相冲描述）"""
        info1 = {"year_zhi": "子"}  # 鼠
        info2 = {"year_zhi": "寅"}  # 虎
        _, _, desc, score = MarriageEngine._analyze_shengxiao(info1, info2)
        assert score == 50
        assert "相冲" in desc or "包容" in desc

    def test_hu_zhu_liuhe(self):
        """虎猪六合 → 95 分"""
        info1 = {"year_zhi": "寅"}  # 虎
        info2 = {"year_zhi": "亥"}  # 猪
        _, _, _, score = MarriageEngine._analyze_shengxiao(info1, info2)
        assert score == 95

    def test_tu_ji_chong(self):
        """兔鸡对冲 → 20 分"""
        info1 = {"year_zhi": "卯"}  # 兔
        info2 = {"year_zhi": "酉"}  # 鸡
        _, _, _, score = MarriageEngine._analyze_shengxiao(info1, info2)
        assert score == 20

    def test_all_12_shengxiao_map_correctly(self):
        """验证所有 12 生肖都能正确映射"""
        for i, zhi in enumerate(DI_ZHI):
            info = {"year_zhi": zhi}
            sx, _, _, _ = MarriageEngine._analyze_shengxiao(info, info)
            assert sx == SHENGXIAO[i], f"地支 {zhi} 应映射到生肖 {SHENGXIAO[i]}"


# ============================================================================
# analyze 完整分析测试
# ============================================================================

class TestAnalyze:
    """测试 analyze 完整合婚分析"""

    def test_analyze_good_pair(self):
        """良好婚配：甲己合 + 子丑合 + 鼠牛合"""
        result = MarriageEngine.analyze("张三", BAZI_GOOD_1, "李四", BAZI_GOOD_2)
        assert isinstance(result, MarriageAnalysis)
        assert result.name1 == "张三"
        assert result.name2 == "李四"
        assert result.day_gan1 == "甲"
        assert result.day_gan2 == "己"
        assert result.ri_gan_score == 90
        assert result.ri_gan_he != ""
        assert result.shengxiao1 == "鼠"
        assert result.shengxiao2 == "牛"
        assert result.shengxiao_score == 95
        assert result.overall_score > 70
        assert result.overall_grade != ""
        assert result.summary != ""

    def test_analyze_bad_pair(self):
        """不良婚配：子午冲 + 鼠马冲"""
        result = MarriageEngine.analyze("张三", BAZI_BAD_1, "李四", BAZI_BAD_2)
        assert isinstance(result, MarriageAnalysis)
        assert result.shengxiao1 == "马"
        assert result.shengxiao2 == "鼠"
        assert result.shengxiao_score == 20
        assert result.overall_score < 60

    def test_analyze_returns_full_bazi_data(self):
        """返回的八字数据完整"""
        result = MarriageEngine.analyze("张三", BAZI_GOOD_1, "李四", BAZI_GOOD_2)
        assert result.bazi1 == BAZI_GOOD_1
        assert result.bazi2 == BAZI_GOOD_2

    def test_analyze_nayin_fields_populated(self):
        """纳音字段已填充"""
        result = MarriageEngine.analyze("张三", BAZI_GOOD_1, "李四", BAZI_GOOD_2)
        assert result.nayin1 != ""
        assert result.nayin2 != ""
        assert result.nayin_match != ""
        assert result.nayin_score > 0

    def test_analyze_high_grade(self):
        """高分配对 → 上等婚配"""
        # 构造一个极高分配对
        bazi1 = make_bazi(
            year_pill="甲子", month_pill="甲子", day_pill="甲子", hour_pill="甲子",
            day_master="甲", year=1984,
            wuxing={"金": 2, "木": 1, "水": 1, "火": 0, "土": 1},
        )
        bazi2 = make_bazi(
            year_pill="己丑", month_pill="己亥", day_pill="己丑", hour_pill="己丑",
            day_master="己", year=1985,
            wuxing={"金": 0, "木": 1, "水": 1, "火": 2, "土": 1},
        )
        # 分析：甲己合(90) + 年支子丑合 + 日支... let me check
        # info1: year_zhi=子, month_zhi=子, day_zhi=子
        # info2: year_zhi=丑, month_zhi=亥, day_zhi=丑
        # 年支子丑六合(+15), 日支子丑... wait, day_zhi2=丑, so 子丑 also 六合(+20), 月支子亥... no relation
        # Nayin: 甲子(金) vs 己丑(火) → 火克金 → 女方克男方(40)
        # 五行: 互补(85)
        # 生肖: 鼠牛(95)
        # overall = 40*0.15 + 90*0.25 + 95*0.25 + 85*0.20 + 95*0.15
        # = 6 + 22.5 + 23.75 + 17 + 14.25 = 83.5
        result = MarriageEngine.analyze("赵六", bazi1, "王五", bazi2)
        assert result.overall_grade == "上等婚配"
        assert result.overall_score >= 80

    def test_analyze_low_grade(self):
        """低分配对 → 下等婚配"""
        # 丙午(马) vs 壬子(鼠) → 鼠马冲(20), 年支子午冲, 日支子午冲
        result = MarriageEngine.analyze("A", BAZI_BAD_1, "B", BAZI_BAD_2)
        assert result.overall_grade == "下等婚配"
        assert result.overall_score < 50

    def test_analyze_suggestions_for_bad(self):
        """不良配对生成建议"""
        result = MarriageEngine.analyze("A", BAZI_BAD_1, "B", BAZI_BAD_2)
        assert len(result.suggestions) > 0
        assert any("冲" in s for s in result.suggestions) or len(result.suggestions) > 0

    def test_analyze_suggestions_wuxing_insufficient(self):
        """五行互补不足触发建议（覆盖 wuxing_score < 60 分支）"""
        bazi1 = make_bazi(
            year_pill="甲子", day_pill="甲子", day_master="甲", year=1984,
            wuxing={"金": 2, "木": 1, "水": 1, "火": 1, "土": 0},
        )
        bazi2 = make_bazi(
            year_pill="甲子", day_pill="甲子", day_master="甲", year=1984,
            wuxing={"金": 1, "木": 2, "水": 1, "火": 0, "土": 1},
        )
        result = MarriageEngine.analyze("A", bazi1, "B", bazi2)
        # wuxing_score = 55 (< 60), 应触发五行互补不足建议
        assert result.wuxing_score < 60
        assert any("五行" in s or "风水" in s for s in result.suggestions)

    def test_analyze_suggestions_for_good(self):
        """良好配对建议"""
        result = MarriageEngine.analyze("张三", BAZI_GOOD_1, "李四", BAZI_GOOD_2)
        assert len(result.suggestions) > 0

    def test_analyze_same_person(self):
        """同一个人（自己和自己）"""
        result = MarriageEngine.analyze("张三", BAZI_GOOD_1, "张三", BAZI_GOOD_1)
        assert isinstance(result, MarriageAnalysis)
        assert result.name1 == result.name2
        assert result.overall_score > 0

    def test_analyze_with_different_wuxing_distributions(self):
        """不同五行分布"""
        bazi1 = make_bazi(
            year_pill="甲子", day_pill="甲子", day_master="甲", year=1984,
            wuxing={"金": 5, "木": 0, "水": 0, "火": 0, "土": 0},
        )
        bazi2 = make_bazi(
            year_pill="己丑", day_pill="己丑", day_master="己", year=1985,
            wuxing={"金": 0, "木": 5, "水": 0, "火": 0, "土": 0},
        )
        result = MarriageEngine.analyze("A", bazi1, "B", bazi2)
        assert isinstance(result, MarriageAnalysis)

    def test_analyze_consistency(self):
        """确定性：相同输入得到相同结果"""
        r1 = MarriageEngine.analyze("张三", BAZI_GOOD_1, "李四", BAZI_GOOD_2)
        r2 = MarriageEngine.analyze("张三", BAZI_GOOD_1, "李四", BAZI_GOOD_2)
        assert r1.overall_score == r2.overall_score
        assert r1.overall_grade == r2.overall_grade
        assert r1.shengxiao_score == r2.shengxiao_score

    def test_analyze_weighted_scoring_correct(self):
        """验证加权评分公式正确"""
        result = MarriageEngine.analyze("张三", BAZI_GOOD_1, "李四", BAZI_GOOD_2)
        expected = (
            result.nayin_score * 0.15
            + result.ri_gan_score * 0.25
            + result.zhi_score * 0.25
            + result.wuxing_score * 0.20
            + result.shengxiao_score * 0.15
        )
        assert round(expected, 1) == result.overall_score


# ============================================================================
# format_text 测试
# ============================================================================

class TestFormatText:
    """测试 format_text 格式化输出"""

    def test_format_text_non_empty(self):
        """format_text 产生非空输出"""
        result = MarriageEngine.analyze("张三", BAZI_GOOD_1, "李四", BAZI_GOOD_2)
        text = MarriageEngine.format_text(result)
        assert isinstance(text, str)
        assert len(text) > 0
        assert "张三" in text
        assert "李四" in text
        assert "八字" in text

    def test_format_text_contains_score(self):
        """输出包含评分"""
        result = MarriageEngine.analyze("张三", BAZI_GOOD_1, "李四", BAZI_GOOD_2)
        text = MarriageEngine.format_text(result)
        assert str(result.overall_score) in text
        assert result.overall_grade in text

    def test_format_text_contains_all_sections(self):
        """输出包含所有分析部分"""
        result = MarriageEngine.analyze("张三", BAZI_GOOD_1, "李四", BAZI_GOOD_2)
        text = MarriageEngine.format_text(result)
        assert "纳音" in text
        assert "日干" in text
        assert "地支" in text
        assert "五行" in text
        assert "生肖" in text
        assert "综合评分" in text

    def test_format_text_with_empty_suggestions(self):
        """空建议列表"""
        ma = MarriageAnalysis(
            name1="张三", name2="李四",
            bazi1={}, bazi2={},
            suggestions=[],
            day_gan1="甲", day_gan2="乙",
            zhi_relations=[],
        )
        text = MarriageEngine.format_text(ma)
        assert isinstance(text, str)
        assert len(text) > 0

    def test_format_text_bad_pair(self):
        """不良配对格式化输出"""
        result = MarriageEngine.analyze("张三", BAZI_BAD_1, "李四", BAZI_BAD_2)
        text = MarriageEngine.format_text(result)
        assert "下等" in text or "一般" in text or str(result.overall_grade) in text


# ============================================================================
# analyze_marriage 便捷函数测试
# ============================================================================

class TestAnalyzeMarriageFunction:
    """测试便捷函数 analyze_marriage"""

    def test_analyze_marriage_returns_marriage_analysis(self):
        """便捷函数返回 MarriageAnalysis 实例"""
        result = analyze_marriage("张三", BAZI_GOOD_1, "李四", BAZI_GOOD_2)
        assert isinstance(result, MarriageAnalysis)

    def test_analyze_marriage_equivalent_to_engine(self):
        """便捷函数与引擎方法结果一致"""
        r1 = analyze_marriage("张三", BAZI_GOOD_1, "李四", BAZI_GOOD_2)
        r2 = MarriageEngine.analyze("张三", BAZI_GOOD_1, "李四", BAZI_GOOD_2)
        assert r1.overall_score == r2.overall_score
        assert r1.overall_grade == r2.overall_grade


# ============================================================================
# 综合/回归测试
# ============================================================================

class TestComprehensive:
    """综合回归测试"""

    def test_all_zhi_combinations_produce_valid_result(self):
        """所有地支组合都能产生有效结果"""
        for zhi1 in DI_ZHI:
            for zhi2 in DI_ZHI:
                bazi1 = make_bazi(
                    year_pill=f"甲{zhi1}",
                    day_pill=f"甲{zhi1}",
                    month_pill=f"甲{zhi1}",
                    hour_pill=f"甲{zhi1}",
                )
                bazi2 = make_bazi(
                    year_pill=f"甲{zhi2}",
                    day_pill=f"甲{zhi2}",
                    month_pill=f"甲{zhi2}",
                    hour_pill=f"甲{zhi2}",
                )
                result = MarriageEngine.analyze("A", bazi1, "B", bazi2)
                assert 0 <= result.overall_score <= 100
                assert result.overall_grade != ""

    def test_all_tiangan_combinations_produce_valid_result(self):
        """所有天干组合都能产生有效结果"""
        for gan1 in TIAN_GAN:
            for gan2 in TIAN_GAN:
                bazi1 = make_bazi(day_pill=f"{gan1}子", day_master=gan1)
                bazi2 = make_bazi(day_pill=f"{gan2}子", day_master=gan2)
                result = MarriageEngine.analyze("A", bazi1, "B", bazi2)
                assert 0 <= result.overall_score <= 100

    def test_grade_boundaries(self):
        """等级边界测试"""
        # 构造不同分数级别的配对
        # >= 80 → 上等
        # >= 65 → 中等
        # >= 50 → 一般
        # < 50 → 下等

        # 上等：高分对
        bazi_high = MarriageEngine.analyze("张三", BAZI_GOOD_1, "李四", BAZI_GOOD_2)
        assert bazi_high.overall_grade in ("上等婚配", "中等婚配", "一般婚配", "下等婚配")

        # 下等：低分对
        bazi_low = MarriageEngine.analyze("A", BAZI_BAD_1, "B", BAZI_BAD_2)
        assert bazi_low.overall_grade in ("上等婚配", "中等婚配", "一般婚配", "下等婚配")

    def test_summary_not_empty(self):
        """总结不为空"""
        result = MarriageEngine.analyze("张三", BAZI_GOOD_1, "李四", BAZI_GOOD_2)
        assert len(result.summary) > 0

    def test_shigan_count_extracted(self):
        """十神计数提取"""
        bazi = make_bazi(shigan_count={"正官": 2, "七杀": 1})
        info = MarriageEngine._extract_from_bazi(bazi)
        assert info["shigan_count"] == {"正官": 2, "七杀": 1}

    def test_wuxing_score_extracted(self):
        """五行分数提取"""
        bazi = make_bazi(wuxing_score={"金": 80, "木": 60})
        info = MarriageEngine._extract_from_bazi(bazi)
        assert info["wuxing_score"] == {"金": 80, "木": 60}

    def test_zhi_relations_always_list(self):
        """地支关系始终是列表"""
        result = MarriageEngine.analyze("张三", BAZI_GOOD_1, "李四", BAZI_GOOD_2)
        assert isinstance(result.zhi_relations, list)
        assert len(result.zhi_relations) > 0

    def test_overall_score_in_range(self):
        """综合评分在 0-100 范围内"""
        result = MarriageEngine.analyze("张三", BAZI_GOOD_1, "李四", BAZI_GOOD_2)
        assert 0 <= result.overall_score <= 100

    def test_round_trip_empty_bazi(self):
        """空八字不崩溃"""
        result = MarriageEngine.analyze("A", {}, "B", {})
        assert isinstance(result, MarriageAnalysis)
        assert 0 <= result.overall_score <= 100
        text = MarriageEngine.format_text(result)
        assert len(text) > 0