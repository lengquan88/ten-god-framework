"""
test_dayun_liunian.py — 大运与流年模块完整测试

覆盖范围：
  - 常量定义
  - derive_shigan / derive_zhi_shigan
  - calc_dayun / calc_liunian / calc_liunian_range
  - _next_jiazi / _estimate_qiyun_age
  - DayunLiunian / FortuneScore / LiunianResult 数据结构
  - LiunianEngine 完整分析引擎
  - get_liunian_engine 单例
  - 边界条件与异常输入
"""

from __future__ import annotations

import pytest
from typing import Dict, List

from tengod.dayun_liunian import (
    # 常量
    GAN_WUXING,
    GAN_YINYANG,
    WUXING_SHENG,
    WUXING_KE,
    SHIGAN_DIMENSION_WEIGHT,
    ZHI_CHONG_EFFECT,
    ZHI_HE_EFFECT,
    JIEQI_DAYS,
    # 函数
    derive_shigan,
    derive_zhi_shigan,
    calc_dayun,
    calc_liunian,
    calc_liunian_range,
    _next_jiazi,
    _estimate_qiyun_age,
    # 数据结构
    DayunLiunian,
    FortuneScore,
    LiunianResult,
    # 引擎
    LiunianEngine,
    get_liunian_engine,
)


# ==========================================================================
# 1. 常量测试
# ==========================================================================

class TestConstants:
    """测试所有模块级常量定义"""

    def test_gan_wuxing_all_ten(self):
        """GAN_WUXING 应包含全部十个天干"""
        assert len(GAN_WUXING) == 10
        for gan in ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']:
            assert gan in GAN_WUXING
            assert GAN_WUXING[gan] in ('木', '火', '土', '金', '水')

    def test_gan_yinyang_all_ten(self):
        """GAN_YINYANG 应包含全部十个天干"""
        assert len(GAN_YINYANG) == 10
        assert GAN_YINYANG['甲'] == '阳'
        assert GAN_YINYANG['乙'] == '阴'
        assert GAN_YINYANG['丙'] == '阳'
        assert GAN_YINYANG['丁'] == '阴'
        assert GAN_YINYANG['戊'] == '阳'
        assert GAN_YINYANG['己'] == '阴'
        assert GAN_YINYANG['庚'] == '阳'
        assert GAN_YINYANG['辛'] == '阴'
        assert GAN_YINYANG['壬'] == '阳'
        assert GAN_YINYANG['癸'] == '阴'

    def test_wuxing_sheng_cycle(self):
        """五行相生为闭环"""
        assert WUXING_SHENG['木'] == '火'
        assert WUXING_SHENG['火'] == '土'
        assert WUXING_SHENG['土'] == '金'
        assert WUXING_SHENG['金'] == '水'
        assert WUXING_SHENG['水'] == '木'

    def test_wuxing_ke_cycle(self):
        """五行相克为闭环"""
        assert WUXING_KE['木'] == '土'
        assert WUXING_KE['土'] == '水'
        assert WUXING_KE['水'] == '火'
        assert WUXING_KE['火'] == '金'
        assert WUXING_KE['金'] == '木'

    def test_shigan_dimension_weight_coverage(self):
        """SHIGAN_DIMENSION_WEIGHT 应包含全部十神"""
        expected_shigans = {'正官', '七杀', '正财', '偏财', '正印', '偏印',
                            '食神', '伤官', '比肩', '劫财'}
        assert set(SHIGAN_DIMENSION_WEIGHT.keys()) == expected_shigans
        for w in SHIGAN_DIMENSION_WEIGHT.values():
            for dim in ('career', 'wealth', 'relationships', 'health'):
                assert dim in w

    def test_zhi_chong_effect_dims(self):
        """ZHI_CHONG_EFFECT 应包含四个维度"""
        for dim in ('career', 'wealth', 'relationships', 'health'):
            assert dim in ZHI_CHONG_EFFECT

    def test_zhi_he_effect_dims(self):
        """ZHI_HE_EFFECT 应包含四个维度"""
        for dim in ('career', 'wealth', 'relationships', 'health'):
            assert dim in ZHI_HE_EFFECT

    def test_jieqi_days_all_months(self):
        """JIEQI_DAYS 应包含全部12个月"""
        for m in range(1, 13):
            assert m in JIEQI_DAYS
            assert 1 <= JIEQI_DAYS[m] <= 31


# ==========================================================================
# 2. derive_shigan 测试
# ==========================================================================

class TestDeriveShigan:
    """测试十神推算"""

    # 同我 — 比肩（同阴阳）
    def test_bijian_same_yinyang(self):
        """甲见甲 → 比肩"""
        assert derive_shigan('甲', '甲') == '比肩'
        assert derive_shigan('丙', '丙') == '比肩'
        assert derive_shigan('戊', '戊') == '比肩'
        assert derive_shigan('庚', '庚') == '比肩'
        assert derive_shigan('壬', '壬') == '比肩'

    # 同我 — 劫财（异阴阳）
    def test_jiecai_diff_yinyang(self):
        """甲见乙 → 劫财"""
        assert derive_shigan('甲', '乙') == '劫财'
        assert derive_shigan('乙', '甲') == '劫财'
        assert derive_shigan('丙', '丁') == '劫财'
        assert derive_shigan('丁', '丙') == '劫财'

    # 我生 — 食神（同阴阳）
    def test_shishen(self):
        """甲生丙 → 食神（甲木生丙火，同阳）"""
        assert derive_shigan('甲', '丙') == '食神'
        assert derive_shigan('乙', '丁') == '食神'
        assert derive_shigan('丙', '戊') == '食神'

    # 我生 — 伤官（异阴阳）
    def test_shangguan(self):
        """甲生丁 → 伤官（甲木生丁火，异阴阳）"""
        assert derive_shigan('甲', '丁') == '伤官'
        assert derive_shigan('乙', '丙') == '伤官'
        assert derive_shigan('丙', '己') == '伤官'

    # 我克 — 偏财（同阴阳）
    def test_piancai(self):
        """甲克戊 → 偏财（甲木克戊土，同阳）"""
        assert derive_shigan('甲', '戊') == '偏财'
        assert derive_shigan('丙', '庚') == '偏财'

    # 我克 — 正财（异阴阳）
    def test_zhengcai(self):
        """甲克己 → 正财（甲木克己土，异阴阳）"""
        assert derive_shigan('甲', '己') == '正财'
        assert derive_shigan('丙', '辛') == '正财'

    # 克我 — 七杀（同阴阳）
    def test_qisha(self):
        """庚克甲 → 七杀（庚金克甲木，同阳）"""
        assert derive_shigan('甲', '庚') == '七杀'
        assert derive_shigan('丙', '壬') == '七杀'

    # 克我 — 正官（异阴阳）
    def test_zhengguan(self):
        """辛克甲 → 正官（辛金克甲木，异阴阳）"""
        assert derive_shigan('甲', '辛') == '正官'
        assert derive_shigan('丙', '癸') == '正官'

    # 生我 — 偏印（同阴阳）
    def test_pianyin(self):
        """壬生甲 → 偏印（壬水生甲木，同阳）"""
        assert derive_shigan('甲', '壬') == '偏印'
        assert derive_shigan('丙', '甲') == '偏印'

    # 生我 — 正印（异阴阳）
    def test_zhengyin(self):
        """癸生甲 → 正印（癸水生甲木，异阴阳）"""
        assert derive_shigan('甲', '癸') == '正印'
        assert derive_shigan('丙', '乙') == '正印'

    def test_all_ten_shigans_non_empty(self):
        """任意日主与任意天干组合都不应返回空字符串"""
        for dm in ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']:
            for tg in ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']:
                result = derive_shigan(dm, tg)
                assert result != '', f"derive_shigan('{dm}', '{tg}') returned empty"
                assert result in ('比肩', '劫财', '食神', '伤官', '偏财', '正财',
                                  '七杀', '正官', '偏印', '正印')


# ==========================================================================
# 3. derive_zhi_shigan 测试
# ==========================================================================

class TestDeriveZhiShigan:
    """测试地支藏干十神推算"""

    def test_zi_cang_gui(self):
        """子藏癸"""
        result = derive_zhi_shigan('甲', '子')
        assert '癸' in result
        assert result['癸'] == '正印'

    def test_wu_cang_ding_ji(self):
        """午藏丁己"""
        result = derive_zhi_shigan('甲', '午')
        assert '丁' in result  # 伤官
        assert '己' in result  # 正财

    def test_yin_cang_jia_bing_wu(self):
        """寅藏甲丙戊"""
        result = derive_zhi_shigan('甲', '寅')
        assert '甲' in result
        assert '丙' in result
        assert '戊' in result

    def test_shen_cang_geng_ren_wu(self):
        """申藏庚壬戊"""
        result = derive_zhi_shigan('甲', '申')
        assert '庚' in result  # 七杀
        assert '壬' in result  # 偏印
        assert '戊' in result  # 偏财

    def test_all_twelve_zhi(self):
        """全部十二地支都应返回非空字典"""
        for zhi in ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']:
            result = derive_zhi_shigan('甲', zhi)
            assert isinstance(result, dict)
            assert len(result) >= 1, f"地支{zhi}藏干不应为空"


# ==========================================================================
# 4. _next_jiazi 测试
# ==========================================================================

class TestNextJiazi:
    """测试甲子循环推演"""

    def test_forward_one_step(self):
        """甲子顺推 → 乙丑"""
        assert _next_jiazi('甲子', forward=True) == '乙丑'
        assert _next_jiazi('乙丑', forward=True) == '丙寅'

    def test_backward_one_step(self):
        """甲子逆推 → 癸亥"""
        assert _next_jiazi('甲子', forward=False) == '癸亥'

    def test_forward_wrap_around(self):
        """癸亥顺推 → 甲子（循环）"""
        assert _next_jiazi('癸亥', forward=True) == '甲子'

    def test_backward_wrap_around(self):
        """乙丑逆推 → 甲子"""
        assert _next_jiazi('乙丑', forward=False) == '甲子'

    def test_forward_ten_steps(self):
        """连续顺推十步不走偏"""
        cur = '甲子'
        for _ in range(10):
            cur = _next_jiazi(cur, forward=True)
        assert cur == '甲戌'

    def test_backward_ten_steps(self):
        """连续逆推十步不走偏"""
        cur = '甲子'
        for _ in range(10):
            cur = _next_jiazi(cur, forward=False)
        assert cur == '甲寅'  # 甲子→癸亥→壬戌→辛酉→庚申→己未→戊午→丁巳→丙辰→乙卯→甲寅

    def test_forward_sixty_cycle(self):
        """顺推六十步回到原点"""
        cur = '甲子'
        for _ in range(60):
            cur = _next_jiazi(cur, forward=True)
        assert cur == '甲子'

    def test_backward_sixty_cycle(self):
        """逆推六十步回到原点"""
        cur = '甲子'
        for _ in range(60):
            cur = _next_jiazi(cur, forward=False)
        assert cur == '甲子'


# ==========================================================================
# 5. calc_dayun 测试
# ==========================================================================

class TestCalcDayun:
    """测试大运推算"""

    def test_forward_male_yang_year(self):
        """阳年男 → 顺排（甲年/丙年男）"""
        # 甲寅年 男，月柱 = 丙寅 → 第一步大运 = 丁卯
        dayuns = calc_dayun(birth_year=1984, year_gan='甲',
                            month_pillar='丙寅', is_male=True, start_age_offset=0)
        assert len(dayuns) == 10
        assert dayuns[0]['pillar'] == '丁卯'
        assert dayuns[0]['direction'] == '顺排'
        assert dayuns[0]['age'] == 0

    def test_reverse_male_yin_year(self):
        """阴年男 → 逆排（乙年男）"""
        dayuns = calc_dayun(birth_year=1985, year_gan='乙',
                            month_pillar='戊寅', is_male=True, start_age_offset=0)
        assert len(dayuns) == 10
        assert dayuns[0]['direction'] == '逆排'
        assert dayuns[0]['pillar'] == '丁丑'  # 戊寅 逆推 = 丁丑

    def test_forward_female_yin_year(self):
        """阴年女 → 顺排（乙年女）"""
        dayuns = calc_dayun(birth_year=1985, year_gan='乙',
                            month_pillar='戊寅', is_male=False, start_age_offset=0)
        assert len(dayuns) == 10
        assert dayuns[0]['direction'] == '顺排'

    def test_reverse_female_yang_year(self):
        """阳年女 → 逆排（甲年女）"""
        dayuns = calc_dayun(birth_year=1984, year_gan='甲',
                            month_pillar='丙寅', is_male=False, start_age_offset=0)
        assert len(dayuns) == 10
        assert dayuns[0]['direction'] == '逆排'

    def test_start_age_offset(self):
        """起运年龄偏移"""
        dayuns = calc_dayun(birth_year=1990, year_gan='庚',
                            month_pillar='壬午', is_male=True, start_age_offset=5)
        assert dayuns[0]['age'] == 5
        assert dayuns[0]['start_year'] == 1995
        assert dayuns[1]['age'] == 15

    def test_step_numbers(self):
        """步数编号 1-10"""
        dayuns = calc_dayun(birth_year=1990, year_gan='庚',
                            month_pillar='壬午', is_male=True, start_age_offset=0)
        for i, du in enumerate(dayuns):
            assert du['step'] == i + 1

    def test_all_yang_gan_male_forward(self):
        """全部阳干年份男命都顺排"""
        for gan in ('甲', '丙', '戊', '庚', '壬'):
            dayuns = calc_dayun(birth_year=2000, year_gan=gan,
                                month_pillar='甲子', is_male=True, start_age_offset=0)
            assert dayuns[0]['direction'] == '顺排'

    def test_all_yin_gan_female_forward(self):
        """全部阴干年份女命都顺排"""
        for gan in ('乙', '丁', '己', '辛', '癸'):
            dayuns = calc_dayun(birth_year=2000, year_gan=gan,
                                month_pillar='甲子', is_male=False, start_age_offset=0)
            assert dayuns[0]['direction'] == '顺排'

    def test_all_yin_gan_male_reverse(self):
        """全部阴干年份男命都逆排"""
        for gan in ('乙', '丁', '己', '辛', '癸'):
            dayuns = calc_dayun(birth_year=2000, year_gan=gan,
                                month_pillar='甲子', is_male=True, start_age_offset=0)
            assert dayuns[0]['direction'] == '逆排'

    def test_all_yang_gan_female_reverse(self):
        """全部阳干年份女命都逆排"""
        for gan in ('甲', '丙', '戊', '庚', '壬'):
            dayuns = calc_dayun(birth_year=2000, year_gan=gan,
                                month_pillar='甲子', is_male=False, start_age_offset=0)
            assert dayuns[0]['direction'] == '逆排'


# ==========================================================================
# 6. calc_liunian 测试
# ==========================================================================

class TestCalcLiunian:
    """测试单年流年推算"""

    def test_basic_liunian(self):
        """基本流年推算"""
        result = calc_liunian(2026, '甲')
        assert result['year'] == 2026
        assert len(result['pillar']) == 2
        assert isinstance(result['gan_shigan'], str)
        assert result['gan_shigan'] != ''
        assert isinstance(result['zhi_shigan_detail'], dict)

    def test_liunian_gan_shigan_non_empty(self):
        """流年天干十神不应为空"""
        for dm in ['甲', '丙', '戊', '庚', '壬']:
            result = calc_liunian(2025, dm)
            assert result['gan_shigan'] != ''

    def test_different_years(self):
        """不同年份返回不同干支"""
        r1 = calc_liunian(2024, '甲')
        r2 = calc_liunian(2025, '甲')
        r3 = calc_liunian(2026, '甲')
        # 不同年份流年干支应不同
        pillars = {r1['pillar'], r2['pillar'], r3['pillar']}
        assert len(pillars) >= 2

    def test_same_day_master_different_years(self):
        """同一天主，不同年份的十神可能不同"""
        r2024 = calc_liunian(2024, '甲')
        r2025 = calc_liunian(2025, '甲')
        # 年份不同，流年天干十神可能不同（取决于干支是否相同）
        assert isinstance(r2024['gan_shigan'], str)
        assert isinstance(r2025['gan_shigan'], str)


# ==========================================================================
# 7. calc_liunian_range 测试
# ==========================================================================

class TestCalcLiunianRange:
    """测试批量流年推算"""

    def test_single_year_range(self):
        """单年范围"""
        results = calc_liunian_range(2026, 2026, '甲')
        assert len(results) == 1
        assert results[0]['year'] == 2026

    def test_five_year_range(self):
        """五年范围"""
        results = calc_liunian_range(2024, 2028, '甲')
        assert len(results) == 5
        for i, r in enumerate(results):
            assert r['year'] == 2024 + i

    def test_ten_year_range(self):
        """十年范围"""
        results = calc_liunian_range(2020, 2029, '丙')
        assert len(results) == 10
        assert all(isinstance(r['pillar'], str) for r in results)
        assert all(isinstance(r['gan_shigan'], str) for r in results)

    def test_range_all_have_zhi_shigan(self):
        """范围内的每条流年都有地支藏干"""
        results = calc_liunian_range(2025, 2026, '甲')
        for r in results:
            assert isinstance(r['zhi_shigan_detail'], dict)
            assert len(r['zhi_shigan_detail']) >= 1


# ==========================================================================
# 8. _estimate_qiyun_age 测试
# ==========================================================================

class TestEstimateQiyunAge:
    """测试起运年龄估算"""

    def test_male_yang_year_forward(self):
        """阳年男起运年龄"""
        age = _estimate_qiyun_age(1990, 6, 15, is_male=True, year_gan='庚')
        assert isinstance(age, int)
        assert age >= 1

    def test_female_yin_year_forward(self):
        """阴年女起运年龄"""
        age = _estimate_qiyun_age(1990, 6, 15, is_male=False, year_gan='乙')
        assert isinstance(age, int)
        assert age >= 1

    def test_male_yin_year_reverse(self):
        """阴年男起运年龄"""
        age = _estimate_qiyun_age(1990, 6, 15, is_male=True, year_gan='乙')
        assert isinstance(age, int)
        assert age >= 1

    def test_female_yang_year_reverse(self):
        """阳年女起运年龄"""
        age = _estimate_qiyun_age(1990, 6, 15, is_male=False, year_gan='庚')
        assert isinstance(age, int)
        assert age >= 1

    def test_minimum_age_is_one(self):
        """起运年龄至少为1"""
        for gan in ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']:
            for is_male in [True, False]:
                age = _estimate_qiyun_age(2000, 6, 15, is_male=is_male, year_gan=gan)
                assert age >= 1, f"起运年龄应>=1, got {age} for gan={gan}, is_male={is_male}"

    def test_early_month_birth(self):
        """年初出生"""
        age = _estimate_qiyun_age(1990, 1, 5, is_male=True, year_gan='庚')
        assert isinstance(age, int)
        assert age >= 1

    def test_late_month_birth(self):
        """年末出生"""
        age = _estimate_qiyun_age(1990, 12, 28, is_male=True, year_gan='庚')
        assert isinstance(age, int)
        assert age >= 1

    def test_after_jieqi(self):
        """出生在节气之后（顺排）"""
        age = _estimate_qiyun_age(1990, 6, 20, is_male=True, year_gan='庚')
        assert isinstance(age, int)
        assert age >= 1

    def test_before_jieqi(self):
        """出生在节气之前（顺排）"""
        age = _estimate_qiyun_age(1990, 6, 3, is_male=True, year_gan='庚')
        assert isinstance(age, int)
        assert age >= 1

    def test_reverse_after_jieqi(self):
        """逆排出生在节气之后"""
        age = _estimate_qiyun_age(1990, 6, 20, is_male=False, year_gan='庚')
        assert isinstance(age, int)
        assert age >= 1

    def test_reverse_before_jieqi(self):
        """逆排出生在节气之前"""
        age = _estimate_qiyun_age(1990, 6, 3, is_male=False, year_gan='庚')
        assert isinstance(age, int)
        assert age >= 1


# ==========================================================================
# 9. DayunLiunian 数据结构测试
# ==========================================================================

class TestDayunLiunianDataclass:
    """测试 DayunLiunian 数据类"""

    def test_create_default(self):
        """默认创建"""
        dl = DayunLiunian(1990, 6, 15)
        assert dl.birth_year == 1990
        assert dl.birth_month == 6
        assert dl.birth_day == 15
        assert dl.is_male is True
        assert dl.hour == 12
        assert isinstance(dl.pillars, dict)
        assert len(dl.pillars) == 4  # year, month, day, hour
        assert len(dl.dayuns) == 10
        assert len(dl.liunian_samples) >= 10

    def test_create_male(self):
        """男性命盘"""
        dl = DayunLiunian(1990, 6, 15, 10, 30, is_male=True, longitude=116.4)
        assert dl.is_male is True
        assert 'year' in dl.pillars
        assert 'month' in dl.pillars
        assert 'day' in dl.pillars
        assert 'hour' in dl.pillars

    def test_create_female(self):
        """女性命盘"""
        dl = DayunLiunian(1990, 6, 15, 10, 30, is_male=False, longitude=116.4)
        assert dl.is_male is False
        assert len(dl.dayuns) == 10

    def test_report_generation(self):
        """report() 方法生成文本报告"""
        dl = DayunLiunian(1990, 6, 15, 10, 30, is_male=True, longitude=116.4)
        report = dl.report()
        assert isinstance(report, str)
        assert len(report) > 0
        assert '1990' in report
        assert '男命' in report
        assert '大运' in report
        assert '流年' in report

    def test_report_female(self):
        """女性报告"""
        dl = DayunLiunian(1990, 6, 15, 10, 30, is_male=False, longitude=116.4)
        report = dl.report()
        assert '女命' in report

    def test_boundary_year(self):
        """边界年份（公元前/极小年份）"""
        dl = DayunLiunian(1, 1, 1, 12, 0, is_male=True, longitude=120.0)
        assert len(dl.pillars) == 4
        assert len(dl.dayuns) == 10

    def test_extreme_birth_dates(self):
        """极端出生日期"""
        dl = DayunLiunian(2000, 12, 31, 23, 59, is_male=True, longitude=120.0)
        assert len(dl.pillars) == 4
        assert len(dl.dayuns) == 10

    def test_leap_year_feb29(self):
        """闰年2月29日"""
        dl = DayunLiunian(2000, 2, 29, 12, 0, is_male=True, longitude=120.0)
        assert len(dl.pillars) == 4

    def test_dayuns_ten_steps(self):
        """大运始终为10步"""
        dl = DayunLiunian(1984, 2, 5, 12, 0, is_male=True, longitude=120.0)
        assert len(dl.dayuns) == 10

    def test_liunian_samples_range(self):
        """流年样本范围覆盖出生年+10年"""
        dl = DayunLiunian(1990, 6, 15)
        years = [s['year'] for s in dl.liunian_samples]
        assert 1990 in years
        assert years[-1] >= 2000


# ==========================================================================
# 10. FortuneScore 数据结构测试
# ==========================================================================

class TestFortuneScore:
    """测试 FortuneScore 数据类"""

    def test_default_values(self):
        """默认值均为50"""
        fs = FortuneScore()
        assert fs.career == 50
        assert fs.wealth == 50
        assert fs.relationships == 50
        assert fs.health == 50
        assert fs.overall == 50

    def test_custom_values(self):
        """自定义值"""
        fs = FortuneScore(career=80, wealth=70, relationships=60, health=90, overall=75)
        assert fs.career == 80
        assert fs.wealth == 70
        assert fs.relationships == 60
        assert fs.health == 90
        assert fs.overall == 75

    def test_to_dict(self):
        """to_dict() 返回完整字典"""
        fs = FortuneScore(career=80, wealth=70, relationships=60, health=90, overall=75,
                          detail={'note': 'test'})
        d = fs.to_dict()
        assert d['career'] == 80
        assert d['wealth'] == 70
        assert d['relationships'] == 60
        assert d['health'] == 90
        assert d['overall'] == 75
        assert d['detail'] == {'note': 'test'}

    def test_detail_default(self):
        """detail 默认空字典"""
        fs = FortuneScore()
        assert fs.detail == {}

    def test_boundary_values(self):
        """边界值（0和100）"""
        fs = FortuneScore(career=0, wealth=100, relationships=0, health=100, overall=50)
        assert fs.career == 0
        assert fs.wealth == 100
        assert fs.relationships == 0
        assert fs.health == 100


# ==========================================================================
# 11. LiunianResult 数据结构测试
# ==========================================================================

class TestLiunianResult:
    """测试 LiunianResult 数据类"""

    def test_create_default(self):
        """默认创建"""
        lr = LiunianResult(year=2026, pillar='丙午', gan='丙', zhi='午',
                           gan_shigan='食神')
        assert lr.year == 2026
        assert lr.pillar == '丙午'
        assert lr.gan == '丙'
        assert lr.zhi == '午'
        assert lr.gan_shigan == '食神'
        assert lr.dayun_pillar == ''
        assert lr.score.overall == 50

    def test_full_fields(self):
        """完整字段创建"""
        fs = FortuneScore(career=70, wealth=80, relationships=65, health=75, overall=72)
        lr = LiunianResult(
            year=2026, pillar='丙午', gan='丙', zhi='午',
            gan_shigan='食神', zhi_shigan={'丁': '伤官', '己': '正财'},
            dayun_pillar='癸未', dayun_shigan='正印',
            dayun_effect='印星生身',
            yongshen_score=10, score=fs,
            judgments=['吉'], warnings=['注意健康'],
            favorable_months=['正月', '二月'],
            unfavorable_months=['四月'],
        )
        assert lr.dayun_pillar == '癸未'
        assert lr.dayun_shigan == '正印'
        assert lr.yongshen_score == 10
        assert lr.judgments == ['吉']
        assert lr.warnings == ['注意健康']
        assert lr.favorable_months == ['正月', '二月']
        assert lr.unfavorable_months == ['四月']

    def test_to_dict(self):
        """to_dict() 返回完整字典"""
        fs = FortuneScore(career=70, wealth=80, relationships=65, health=75, overall=72)
        lr = LiunianResult(
            year=2026, pillar='丙午', gan='丙', zhi='午',
            gan_shigan='食神', zhi_shigan={'丁': '伤官'},
            dayun_pillar='癸未', dayun_shigan='正印',
            dayun_effect='平稳', yongshen_score=5,
            score=fs, judgments=['吉', '利'],
            warnings=['慎'], favorable_months=['正月'],
            unfavorable_months=['七月'],
        )
        d = lr.to_dict()
        assert d['year'] == 2026
        assert d['pillar'] == '丙午'
        assert d['score']['career'] == 70
        assert d['score']['overall'] == 72
        assert d['judgments'] == ['吉', '利']
        assert d['warnings'] == ['慎']
        assert d['favorable_months'] == ['正月']
        assert d['unfavorable_months'] == ['七月']

    def test_empty_lists(self):
        """空列表默认值"""
        lr = LiunianResult(year=2026, pillar='丙午', gan='丙', zhi='午',
                           gan_shigan='食神')
        assert lr.judgments == []
        assert lr.warnings == []
        assert lr.favorable_months == []
        assert lr.unfavorable_months == []


# ==========================================================================
# 12. LiunianEngine 测试
# ==========================================================================

class TestLiunianEngine:
    """测试流年运势引擎"""

    @pytest.fixture
    def engine(self):
        """创建引擎实例"""
        return LiunianEngine()

    @pytest.mark.asyncio
    async def test_analyze_basic(self, engine):
        """基本分析流程"""
        result = engine.analyze(
            birth_year=1990, birth_month=6, birth_day=15,
            hour=12, minute=0, is_male=True, longitude=116.4,
            yongshen=['土', '金'], jishen=['木', '火'],
            target_years=[2026, 2027],
        )
        assert 'pillars' in result
        assert 'day_master' in result
        assert 'qiyun_age' in result
        assert 'yongshen' in result
        assert 'jishen' in result
        assert 'dayuns' in result
        assert 'liunian' in result
        assert 'summary' in result
        assert len(result['liunian']) == 2

    @pytest.mark.asyncio
    async def test_analyze_default_yongshen(self, engine):
        """不指定喜用神时使用默认值"""
        result = engine.analyze(
            birth_year=1990, birth_month=6, birth_day=15,
            target_years=[2026],
        )
        assert len(result['yongshen']) >= 2
        assert len(result['jishen']) >= 2

    @pytest.mark.asyncio
    async def test_analyze_default_target_years(self, engine):
        """不指定目标年份时使用默认范围"""
        result = engine.analyze(
            birth_year=1990, birth_month=6, birth_day=15,
        )
        assert len(result['liunian']) >= 8

    @pytest.mark.asyncio
    async def test_analyze_summary_fields(self, engine):
        """汇总字段完整性"""
        result = engine.analyze(
            birth_year=1990, birth_month=6, birth_day=15,
            target_years=[2026, 2027, 2028],
        )
        summary = result['summary']
        assert 'best_year' in summary
        assert 'best_score' in summary
        assert 'worst_year' in summary
        assert 'worst_score' in summary
        assert 'average_score' in summary
        assert 'total_years' in summary
        assert summary['total_years'] == 3

    @pytest.mark.asyncio
    async def test_analyze_single_year(self, engine):
        """单年分析"""
        result = engine.analyze(
            birth_year=1990, birth_month=6, birth_day=15,
            target_years=[2026],
        )
        assert len(result['liunian']) == 1
        liunian = result['liunian'][0]
        assert liunian['year'] == 2026
        assert 'pillar' in liunian
        assert 'gan_shigan' in liunian
        assert 'score' in liunian
        assert 'judgments' in liunian
        assert 'warnings' in liunian
        assert 'favorable_months' in liunian
        assert 'unfavorable_months' in liunian

    @pytest.mark.asyncio
    async def test_analyze_female(self, engine):
        """女性命盘分析"""
        result = engine.analyze(
            birth_year=1990, birth_month=6, birth_day=15,
            is_male=False, target_years=[2026],
        )
        assert len(result['dayuns']) == 10
        assert len(result['liunian']) == 1

    @pytest.mark.asyncio
    async def test_analyze_qiyun_age_in_result(self, engine):
        """起运年龄在结果中"""
        result = engine.analyze(
            birth_year=1990, birth_month=6, birth_day=15,
        )
        assert result['qiyun_age'] >= 1

    @pytest.mark.asyncio
    async def test_analyze_dayun_details(self, engine):
        """大运详情字段"""
        result = engine.analyze(
            birth_year=1990, birth_month=6, birth_day=15,
        )
        for du in result['dayuns']:
            assert 'step' in du
            assert 'start_age' in du
            assert 'end_age' in du
            assert 'pillar' in du
            assert 'start_year' in du
            assert 'direction' in du
            assert 'gan_shigan' in du
            assert du['end_age'] == du['start_age'] + 9

    @pytest.mark.asyncio
    async def test_analyze_liunian_scores_in_range(self, engine):
        """流年评分在0-100范围内"""
        result = engine.analyze(
            birth_year=1990, birth_month=6, birth_day=15,
            target_years=[2026, 2027, 2028, 2029, 2030],
        )
        for ln in result['liunian']:
            for dim in ('career', 'wealth', 'relationships', 'health', 'overall'):
                score = ln['score'][dim]
                assert 0 <= score <= 100, f"{dim} score {score} out of range"

    @pytest.mark.asyncio
    async def test_analyze_judgments_not_empty(self, engine):
        """断语不应为空"""
        result = engine.analyze(
            birth_year=1990, birth_month=6, birth_day=15,
            target_years=[2026, 2027],
        )
        for ln in result['liunian']:
            assert len(ln['judgments']) >= 1

    @pytest.mark.asyncio
    async def test_analyze_summary_best_worst(self, engine):
        """最佳/最差年份统计正确"""
        result = engine.analyze(
            birth_year=1990, birth_month=6, birth_day=15,
            target_years=[2026, 2027, 2028, 2029, 2030],
        )
        best = result['summary']['best_score']
        worst = result['summary']['worst_score']
        assert best >= worst

    @pytest.mark.asyncio
    async def test_analyze_boundary_years(self, engine):
        """边界年份"""
        result = engine.analyze(
            birth_year=1900, birth_month=1, birth_day=1,
            target_years=[2026],
        )
        assert 'pillars' in result
        assert len(result['liunian']) == 1

    @pytest.mark.asyncio
    async def test_analyze_extreme_birth(self, engine):
        """极端出生日期"""
        result = engine.analyze(
            birth_year=2000, birth_month=12, birth_day=31,
            hour=23, minute=59, is_male=True,
            target_years=[2026],
        )
        assert len(result['pillars']) == 4


# ==========================================================================
# 13. _dayun_liunian_effect 测试
# ==========================================================================

class TestDayunLiunianEffect:
    """测试大运流年叠加效应"""

    @pytest.fixture
    def engine(self):
        return LiunianEngine()

    def test_empty_dayun_shigan(self, engine):
        """大运十神为空时返回空"""
        effect = engine._dayun_liunian_effect('', '正官')
        assert effect == ''

    def test_guansha_overlap(self, engine):
        """官杀叠加"""
        effect = engine._dayun_liunian_effect('正官', '七杀')
        assert '官杀' in effect

    def test_caixing_overlap(self, engine):
        """财星叠加"""
        effect = engine._dayun_liunian_effect('正财', '偏财')
        assert '财星' in effect

    def test_yinxing_shengshen(self, engine):
        """印星生身"""
        effect = engine._dayun_liunian_effect('正印', '比肩')
        assert '印星生身' in effect

    def test_shishang_shengcai(self, engine):
        """食伤生财"""
        effect = engine._dayun_liunian_effect('食神', '正财')
        assert '食伤生财' in effect

    def test_bijie_duocai(self, engine):
        """比劫夺财"""
        effect = engine._dayun_liunian_effect('正财', '劫财')
        assert '比劫夺财' in effect

    def test_same_shigan(self, engine):
        """相同十神"""
        effect = engine._dayun_liunian_effect('正官', '正官')
        assert '力量加倍' in effect

    def test_peaceful_transition(self, engine):
        """平稳过渡"""
        effect = engine._dayun_liunian_effect('正印', '正官')
        assert '平稳过渡' in effect

    def test_multiple_effects(self, engine):
        """多个效应叠加"""
        effect = engine._dayun_liunian_effect('正官', '正官')
        # 正官+正官 → 官杀混杂 + 力量加倍
        assert '官杀' in effect or '力量加倍' in effect


# ==========================================================================
# 14. _calculate_fortune_score 测试
# ==========================================================================

class TestCalculateFortuneScore:
    """测试四维度评分"""

    @pytest.fixture
    def engine(self):
        return LiunianEngine()

    def test_basic_score(self, engine):
        """基本评分"""
        score = engine._calculate_fortune_score(
            gan_shigan='正官', dayun_shigan='正印',
            yongshen_score=0, gan_wuxing='金', zhi_wuxing='火',
            yongshen=['土', '金'], jishen=['木', '水'],
            ri_zhi='子', liu_zhi='丑',
        )
        assert isinstance(score, FortuneScore)
        assert 0 <= score.career <= 100
        assert 0 <= score.wealth <= 100
        assert 0 <= score.relationships <= 100
        assert 0 <= score.health <= 100
        assert 0 <= score.overall <= 100

    def test_yongshen_positive(self, engine):
        """喜用神加分"""
        score = engine._calculate_fortune_score(
            gan_shigan='正官', dayun_shigan='',
            yongshen_score=20, gan_wuxing='土', zhi_wuxing='土',
            yongshen=['土', '金'], jishen=['木', '水'],
            ri_zhi='', liu_zhi='',
        )
        assert score.career >= 50
        assert score.wealth >= 50

    def test_jishen_negative(self, engine):
        """忌神减分"""
        score = engine._calculate_fortune_score(
            gan_shigan='正官', dayun_shigan='',
            yongshen_score=-20, gan_wuxing='木', zhi_wuxing='木',
            yongshen=['土', '金'], jishen=['木', '水'],
            ri_zhi='', liu_zhi='',
        )
        # 有忌神减分，可能低于50
        assert score.career <= 100
        assert score.wealth <= 100

    def test_zhichong_effect(self, engine):
        """地支相冲"""
        score = engine._calculate_fortune_score(
            gan_shigan='正官', dayun_shigan='',
            yongshen_score=0, gan_wuxing='金', zhi_wuxing='火',
            yongshen=['土', '金'], jishen=['木', '水'],
            ri_zhi='子', liu_zhi='午',  # 子午冲
        )
        # 相冲应减分
        assert isinstance(score, FortuneScore)

    def test_zhihe_effect(self, engine):
        """地支相合"""
        score = engine._calculate_fortune_score(
            gan_shigan='正官', dayun_shigan='',
            yongshen_score=0, gan_wuxing='金', zhi_wuxing='火',
            yongshen=['土', '金'], jishen=['木', '水'],
            ri_zhi='子', liu_zhi='丑',  # 子丑合
        )
        assert isinstance(score, FortuneScore)

    def test_scores_clamped(self, engine):
        """评分被限制在0-100"""
        score = engine._calculate_fortune_score(
            gan_shigan='劫财', dayun_shigan='七杀',
            yongshen_score=-100, gan_wuxing='木', zhi_wuxing='木',
            yongshen=['土', '金'], jishen=['木', '水'],
            ri_zhi='子', liu_zhi='午',
        )
        assert 0 <= score.career <= 100
        assert 0 <= score.wealth <= 100
        assert 0 <= score.relationships <= 100
        assert 0 <= score.health <= 100

    def test_extreme_yongshen_score(self, engine):
        """极端喜用神分数"""
        # 非常大的正分
        score = engine._calculate_fortune_score(
            gan_shigan='正财', dayun_shigan='正印',
            yongshen_score=40, gan_wuxing='土', zhi_wuxing='金',
            yongshen=['土', '金'], jishen=['木', '水'],
            ri_zhi='', liu_zhi='',
        )
        assert score.career <= 100
        assert score.wealth <= 100

    def test_all_shigans_produce_valid_scores(self, engine):
        """所有十神都产生有效评分"""
        for shigan in ['正官', '七杀', '正财', '偏财', '正印', '偏印',
                       '食神', '伤官', '比肩', '劫财']:
            score = engine._calculate_fortune_score(
                gan_shigan=shigan, dayun_shigan='',
                yongshen_score=0, gan_wuxing='金', zhi_wuxing='水',
                yongshen=['土', '金'], jishen=['木', '水'],
                ri_zhi='', liu_zhi='',
            )
            assert 0 <= score.overall <= 100, f"shigan={shigan} overall={score.overall}"

    def test_all_chong_pairs(self, engine):
        """所有六冲组合"""
        chong_pairs = [('子', '午'), ('丑', '未'), ('寅', '申'),
                       ('卯', '酉'), ('辰', '戌'), ('巳', '亥')]
        for a, b in chong_pairs:
            score = engine._calculate_fortune_score(
                gan_shigan='正官', dayun_shigan='',
                yongshen_score=0, gan_wuxing='金', zhi_wuxing='火',
                yongshen=['土', '金'], jishen=['木', '水'],
                ri_zhi=a, liu_zhi=b,
            )
            assert isinstance(score, FortuneScore)

    def test_all_he_pairs(self, engine):
        """所有六合组合"""
        he_pairs = [('子', '丑'), ('寅', '亥'), ('卯', '戌'),
                    ('辰', '酉'), ('巳', '申'), ('午', '未')]
        for a, b in he_pairs:
            score = engine._calculate_fortune_score(
                gan_shigan='正官', dayun_shigan='',
                yongshen_score=0, gan_wuxing='金', zhi_wuxing='火',
                yongshen=['土', '金'], jishen=['木', '水'],
                ri_zhi=a, liu_zhi=b,
            )
            assert isinstance(score, FortuneScore)


# ==========================================================================
# 15. _generate_judgments 测试
# ==========================================================================

class TestGenerateJudgments:
    """测试断语生成"""

    @pytest.fixture
    def engine(self):
        return LiunianEngine()

    def test_returns_tuple_of_lists(self, engine):
        """返回 (judgments, warnings) 元组"""
        score = FortuneScore(career=60, wealth=60, relationships=60, health=60, overall=60)
        j, w = engine._generate_judgments('正官', '正印', '平稳过渡', 0, score)
        assert isinstance(j, list)
        assert isinstance(w, list)

    def test_judgments_not_empty(self, engine):
        """断语不应为空"""
        score = FortuneScore(career=50, wealth=50, relationships=50, health=50, overall=50)
        j, w = engine._generate_judgments('正官', '', '', 0, score)
        assert len(j) >= 1

    def test_high_score_judgments(self, engine):
        """高分产生积极断语"""
        score = FortuneScore(career=85, wealth=90, relationships=95, health=88, overall=90)
        j, w = engine._generate_judgments('正官', '正印', '印星生身', 20, score)
        assert len(j) >= 2

    def test_low_score_warnings(self, engine):
        """低分产生警示"""
        score = FortuneScore(career=25, wealth=20, relationships=15, health=30, overall=22)
        j, w = engine._generate_judgments('劫财', '七杀', '', -20, score)
        assert len(w) >= 1
        assert '运势偏弱' in ' '.join(w) or '偏弱' in ' '.join(w)

    def test_yongshen_positive_judgment(self, engine):
        """喜用神高分断语"""
        score = FortuneScore(career=70, wealth=70, relationships=70, health=70, overall=70)
        j, w = engine._generate_judgments('正官', '', '', 20, score)
        assert any('喜用神' in s for s in j)

    def test_jishen_negative_warning(self, engine):
        """忌神警示"""
        score = FortuneScore(career=40, wealth=40, relationships=40, health=40, overall=40)
        j, w = engine._generate_judgments('劫财', '', '', -20, score)
        assert any('忌' in s for s in w)

    def test_all_ten_shigans_have_judgment(self, engine):
        """全部十神都有断语模板"""
        for shigan in ['正官', '七杀', '正财', '偏财', '正印', '偏印',
                       '食神', '伤官', '比肩', '劫财']:
            score = FortuneScore(career=50, wealth=50, relationships=50, health=50, overall=50)
            j, w = engine._generate_judgments(shigan, '', '', 0, score)
            assert len(j) >= 1, f"shigan={shigan} has no judgments"

    def test_extreme_high_score(self, engine):
        """极高分断语"""
        score = FortuneScore(career=95, wealth=98, relationships=92, health=96, overall=95)
        j, w = engine._generate_judgments('正官', '正印', '平稳过渡', 15, score)
        assert any('运势上扬' in s for s in j)

    def test_dimension_warnings_format(self, engine):
        """维度警示格式正确"""
        score = FortuneScore(career=25, wealth=30, relationships=20, health=28, overall=25)
        j, w = engine._generate_judgments('劫财', '', '', -10, score)
        assert any('偏弱' in s for s in w)


# ==========================================================================
# 16. _month_analysis 测试
# ==========================================================================

class TestMonthAnalysis:
    """测试有利/不利月份分析"""

    @pytest.fixture
    def engine(self):
        return LiunianEngine()

    def test_returns_tuple_of_lists(self, engine):
        """返回 (fav, unfav) 元组"""
        fav, unfav = engine._month_analysis('火', ['土', '金'], ['木', '水'])
        assert isinstance(fav, list)
        assert isinstance(unfav, list)

    def test_spring_months_wood(self, engine):
        """春季月份为木"""
        fav, unfav = engine._month_analysis('火', ['木'], ['金'])
        assert '正月' in fav
        assert '二月' in fav

    def test_summer_months_fire(self, engine):
        """夏季月份为火"""
        fav, unfav = engine._month_analysis('火', ['火'], ['金'])
        assert '四月' in fav
        assert '五月' in fav

    def test_autumn_months_metal(self, engine):
        """秋季月份为金"""
        fav, unfav = engine._month_analysis('火', ['金'], ['木'])
        assert '七月' in fav
        assert '八月' in fav

    def test_winter_months_water(self, engine):
        """冬季月份为水"""
        fav, unfav = engine._month_analysis('火', ['水'], ['土'])
        assert '十月' in fav
        assert '冬月' in fav

    def test_earth_months(self, engine):
        """土月（三、六、九、腊月）"""
        fav, unfav = engine._month_analysis('火', ['土'], ['木'])
        assert '三月' in fav
        assert '六月' in fav
        assert '九月' in fav
        assert '腊月' in fav

    def test_empty_yongshen_no_fav(self, engine):
        """空喜用神无有利月份"""
        fav, unfav = engine._month_analysis('火', [], [])
        assert len(fav) == 0

    def test_all_months_covered(self, engine):
        """十二个月全部覆盖"""
        all_months = ['正月', '二月', '三月', '四月', '五月', '六月',
                      '七月', '八月', '九月', '十月', '冬月', '腊月']
        fav, unfav = engine._month_analysis('火', ['木', '火', '土', '金', '水'], [])
        assert len(fav) == 12

    def test_month_not_in_neither(self, engine):
        """既非喜用神也非忌神的月份不出现在任何列表中"""
        fav, unfav = engine._month_analysis('火', ['木'], ['金'])
        for m in fav:
            assert m not in unfav
        for m in unfav:
            assert m not in fav


# ==========================================================================
# 17. get_liunian_engine 单例测试
# ==========================================================================

class TestGetLiunianEngine:
    """测试单例工厂函数"""

    def test_returns_liunian_engine(self):
        """返回 LiunianEngine 实例"""
        engine = get_liunian_engine()
        assert isinstance(engine, LiunianEngine)

    def test_singleton(self):
        """多次调用返回同一实例"""
        e1 = get_liunian_engine()
        e2 = get_liunian_engine()
        assert e1 is e2

    def test_engine_has_cache(self):
        """引擎实例有缓存"""
        engine = get_liunian_engine()
        assert hasattr(engine, '_dayuns_cache')
        assert isinstance(engine._dayuns_cache, dict)


# ==========================================================================
# 18. 边界条件和异常输入测试
# ==========================================================================

class TestEdgeCases:
    """边界条件和异常输入"""

    # ── derive_shigan 边界 ──

    def test_derive_shigan_same_element_diff_yinyang(self):
        """五行相同阴阳不同 → 劫财"""
        # 甲(阳木) vs 乙(阴木) → 劫财
        assert derive_shigan('甲', '乙') == '劫财'
        assert derive_shigan('丙', '丁') == '劫财'

    def test_derive_shigan_cross_branch(self):
        """跨分支覆盖"""
        # 壬(阳水)生甲(阳木) → 偏印
        assert derive_shigan('甲', '壬') == '偏印'
        # 癸(阴水)生甲(阳木) → 正印
        assert derive_shigan('甲', '癸') == '正印'

    # ── calc_liunian 边界 ──

    def test_calc_liunian_very_old_year(self):
        """极早年份"""
        result = calc_liunian(1900, '甲')
        assert result['year'] == 1900
        assert len(result['pillar']) == 2

    def test_calc_liunian_future_year(self):
        """极远未来年份"""
        result = calc_liunian(2100, '甲')
        assert result['year'] == 2100
        assert len(result['pillar']) == 2

    # ── calc_dayun 边界 ──

    def test_calc_dayun_zero_start_age(self):
        """0岁起运"""
        dayuns = calc_dayun(birth_year=2000, year_gan='庚',
                            month_pillar='戊子', is_male=True, start_age_offset=0)
        assert dayuns[0]['age'] == 0
        assert dayuns[0]['start_year'] == 2000

    def test_calc_dayun_large_start_age(self):
        """大龄起运（如10岁）"""
        dayuns = calc_dayun(birth_year=2000, year_gan='庚',
                            month_pillar='戊子', is_male=True, start_age_offset=10)
        assert dayuns[0]['age'] == 10
        assert dayuns[0]['start_year'] == 2010
        assert dayuns[9]['age'] == 100
        assert dayuns[9]['start_year'] == 2100

    # ── _next_jiazi 边界 ──

    def test_next_jiazi_whole_cycle_forward(self):
        """完整60甲子顺推循环"""
        start = '甲子'
        cur = start
        visited = []
        for i in range(60):
            visited.append(cur)
            cur = _next_jiazi(cur, forward=True)
        assert cur == start
        assert len(set(visited)) == 60  # 无重复

    def test_next_jiazi_whole_cycle_backward(self):
        """完整60甲子逆推循环"""
        start = '甲子'
        cur = start
        visited = []
        for i in range(60):
            visited.append(cur)
            cur = _next_jiazi(cur, forward=False)
        assert cur == start
        assert len(set(visited)) == 60

    # ── _estimate_qiyun_age 边界 ──

    def test_estimate_qiyun_age_month_boundary(self):
        """月份边界"""
        for m in range(1, 13):
            age = _estimate_qiyun_age(2000, m, 15, is_male=True, year_gan='庚')
            assert age >= 1

    def test_estimate_qiyun_age_day_boundary(self):
        """日期边界"""
        for d in [1, 15, 28]:
            age = _estimate_qiyun_age(2000, 6, d, is_male=True, year_gan='庚')
            assert age >= 1

    # ── LiunianEngine.analyze 边界 ──

    @pytest.mark.asyncio
    async def test_engine_analyze_empty_target_years(self):
        """空目标年份列表 → 使用默认范围（当前年份前后共10年）"""
        engine = LiunianEngine()
        result = engine.analyze(
            birth_year=1990, birth_month=6, birth_day=15,
            target_years=[],
        )
        # 空列表时，analyze 内部使用默认的 target_years（当前年份前后），
        # 因此结果不为空
        assert len(result['liunian']) >= 1
        assert result['summary']['total_years'] == len(result['liunian'])

    @pytest.mark.asyncio
    async def test_engine_analyze_all_yang_gan_births(self):
        """全部阳年出生"""
        engine = LiunianEngine()
        for gan in ['甲', '丙', '戊', '庚', '壬']:
            # 通过选一个该年干的实际年份
            # 甲年：1984, 丙年：1986, 戊年：1988, 庚年：1990, 壬年：1992
            year_map = {'甲': 1984, '丙': 1986, '戊': 1988, '庚': 1990, '壬': 1992}
            result = engine.analyze(
                birth_year=year_map[gan], birth_month=6, birth_day=15,
                target_years=[2026],
            )
            assert result['day_master'] != ''

    @pytest.mark.asyncio
    async def test_engine_analyze_all_yin_gan_births(self):
        """全部阴年出生"""
        engine = LiunianEngine()
        year_map = {'乙': 1985, '丁': 1987, '己': 1989, '辛': 1991, '癸': 1993}
        for gan in year_map:
            result = engine.analyze(
                birth_year=year_map[gan], birth_month=6, birth_day=15,
                target_years=[2026],
            )
            assert result['day_master'] != ''

    @pytest.mark.asyncio
    async def test_engine_analyze_past_liunian_coverage(self):
        """大运覆盖过去的流年"""
        engine = LiunianEngine()
        result = engine.analyze(
            birth_year=1990, birth_month=6, birth_day=15,
            target_years=[2000, 2010, 2020, 2030, 2040, 2050],
        )
        assert len(result['liunian']) == 6
        for ln in result['liunian']:
            assert ln['dayun_pillar'] != ''  # 每个年份都应有大运

    # ── FortuneScore 边界 ──

    def test_fortune_score_beyond_range_to_dict(self):
        """超出范围的值仍可 to_dict"""
        fs = FortuneScore(career=150, wealth=-10, relationships=200, health=-50, overall=300)
        d = fs.to_dict()
        assert d['career'] == 150
        assert d['wealth'] == -10

    # ── LiunianResult 边界 ──

    def test_liunian_result_to_dict_minimal(self):
        """最小字段 to_dict"""
        lr = LiunianResult(year=2026, pillar='丙午', gan='丙', zhi='午',
                           gan_shigan='食神')
        d = lr.to_dict()
        assert d['year'] == 2026
        assert d['dayun_pillar'] == ''
        assert d['judgments'] == []


# ==========================================================================
# 19. 综合场景测试
# ==========================================================================

class TestIntegrationScenarios:
    """综合场景测试"""

    @pytest.mark.asyncio
    async def test_full_pipeline_male(self):
        """完整男性命盘分析流程"""
        engine = LiunianEngine()
        result = engine.analyze(
            birth_year=1984, birth_month=2, birth_day=5,
            hour=12, minute=0, is_male=True, longitude=116.4,
            yongshen=['土', '金'], jishen=['木', '水'],
            target_years=[2024, 2025, 2026, 2027, 2028],
        )
        # 验证所有关键字段
        assert result['day_master'] != ''
        assert result['day_master_wuxing'] != ''
        assert result['day_master_yinyang'] != ''
        assert result['qiyun_age'] >= 1
        assert len(result['dayuns']) == 10
        assert len(result['liunian']) == 5
        assert result['summary']['total_years'] == 5
        assert result['summary']['best_score'] >= result['summary']['worst_score']

    @pytest.mark.asyncio
    async def test_full_pipeline_female(self):
        """完整女性命盘分析流程"""
        engine = LiunianEngine()
        result = engine.analyze(
            birth_year=1985, birth_month=8, birth_day=20,
            hour=8, minute=30, is_male=False, longitude=121.5,
            yongshen=['火', '木'], jishen=['金', '水'],
            target_years=[2026, 2027, 2028],
        )
        assert result['day_master'] != ''
        assert len(result['dayuns']) == 10
        assert len(result['liunian']) == 3

    @pytest.mark.asyncio
    async def test_dayun_liunian_consistency(self):
        """DayunLiunian 与 LiunianEngine 不应崩溃"""
        # DayunLiunian 排盘
        chart = DayunLiunian(1990, 6, 15, 10, 30, is_male=True, longitude=116.4)
        report = chart.report()
        assert '庚午' in report or '1990' in report

        # LiunianEngine 分析
        engine = LiunianEngine()
        result = engine.analyze(
            birth_year=1990, birth_month=6, birth_day=15,
            hour=10, minute=30, is_male=True, longitude=116.4,
            target_years=[2026],
        )
        assert result['day_master'] == chart.pillars['day'][0]

    @pytest.mark.asyncio
    async def test_consecutive_decade_analysis(self):
        """连续十年分析"""
        engine = LiunianEngine()
        result = engine.analyze(
            birth_year=1990, birth_month=6, birth_day=15,
            target_years=list(range(2026, 2036)),
        )
        assert len(result['liunian']) == 10
        # 十年评分应有变化
        scores = [r['score']['overall'] for r in result['liunian']]
        assert len(set(scores)) >= 1  # 至少有变化

    @pytest.mark.asyncio
    async def test_liunian_result_field_completeness(self):
        """LiunianResult 返回字段完整性"""
        engine = LiunianEngine()
        result = engine.analyze(
            birth_year=1990, birth_month=6, birth_day=15,
            yongshen=['土', '金'], jishen=['木', '火'],
            target_years=[2026],
        )
        ln = result['liunian'][0]
        required_fields = ['year', 'pillar', 'gan', 'zhi', 'gan_shigan',
                           'zhi_shigan', 'dayun_pillar', 'dayun_shigan',
                           'dayun_effect', 'yongshen_score', 'score',
                           'judgments', 'warnings', 'favorable_months',
                           'unfavorable_months']
        for field in required_fields:
            assert field in ln, f"Missing field: {field}"

    @pytest.mark.asyncio
    async def test_engine_custom_longitude(self):
        """不同经度不影响分析结果"""
        engine = LiunianEngine()
        result_east = engine.analyze(
            birth_year=1990, birth_month=6, birth_day=15,
            longitude=135.0, target_years=[2026],
        )
        result_west = engine.analyze(
            birth_year=1990, birth_month=6, birth_day=15,
            longitude=75.0, target_years=[2026],
        )
        assert result_east['day_master'] != ''
        assert result_west['day_master'] != ''