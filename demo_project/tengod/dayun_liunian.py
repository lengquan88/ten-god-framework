"""
dayun_liunian.py — 大运与流年推演
= = = = = = = = = = = = = = = = = = =
功能：
  1. 起运年龄推算（简化版：阳男阴女顺、阴男阳女逆）
  2. 10步大运排盘（每步10年）
  3. 任意年份的流年干支与十神分析

关键规则：
  - 阳干（甲丙戊庚壬）年生男 / 阴干（乙丁己辛癸）年生女：顺排
  - 阴年生男 / 阳年生女：逆排
  - 起运岁数 = 出生至最近节气的天数 / 3（简化近似）
  - 每步大运 = 月柱顺逆推一个甲子循环
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .bazi_calculator import (
    TIAN_GAN, DI_ZHI, calc_bazi, calc_year_pillar,
    _gan_index, _zhi_index,
)


# = = = = = = = = = = = = = = = = = = = =
# 十神分类（与 divination_engine 保持一致的简化映射）
# = = = = = = = = = = = = = = = = = = = =

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

# 五行生克
WUXING_SHENG = {'木': '火', '火': '土', '土': '金', '金': '水', '水': '木'}
WUXING_KE = {'木': '土', '土': '水', '水': '火', '火': '金', '金': '木'}


def derive_shigan(day_master: str, target_gan: str) -> str:
    """
    根据日干推算目标天干的十神。
    规则：
      - 同我（五行相同）：同阴阳=比肩，异阴阳=劫财
      - 我生（日干生目标）：同阴阳=食神，异阴阳=伤官
      - 我克（日干克目标）：同阴阳=偏财，异阴阳=正财
      - 克我（目标克日干）：同阴阳=七杀，异阴阳=正官
      - 生我（目标生日干）：同阴阳=偏印，异阴阳=正印
    """
    dm_wuxing = GAN_WUXING[day_master]
    t_wuxing = GAN_WUXING[target_gan]
    dm_yinyang = GAN_YINYANG[day_master]
    t_yinyang = GAN_YINYANG[target_gan]
    same_yinyang = dm_yinyang == t_yinyang

    if dm_wuxing == t_wuxing:
        return '比肩' if same_yinyang else '劫财'
    if WUXING_SHENG[dm_wuxing] == t_wuxing:
        return '食神' if same_yinyang else '伤官'
    if WUXING_KE[dm_wuxing] == t_wuxing:
        return '偏财' if same_yinyang else '正财'
    if WUXING_KE[t_wuxing] == dm_wuxing:
        return '七杀' if same_yinyang else '正官'
    if WUXING_SHENG[t_wuxing] == dm_wuxing:
        return '偏印' if same_yinyang else '正印'
    return ''


def derive_zhi_shigan(day_master: str, target_zhi: str) -> Dict[str, str]:
    """
    推算地支藏干对应的十神。
    简化版：子藏癸，丑藏己癸辛，寅藏甲丙戊...
    """
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
    cang = ZHI_CANG_GAN.get(target_zhi, [])
    return {g: derive_shigan(day_master, g) for g in cang}


# = = = = = = = = = = = = = = = = = = = =
# 大运推算
# = = = = = = = = = = = = = = = = = = = =

def _next_jiazi(name: str, forward: bool = True) -> str:
    """取下一个（或上一个）甲子名称"""
    g, z = name[0], name[1]
    gi, zi = _gan_index(g), _zhi_index(z)
    if forward:
        gi = (gi + 1) % 10
        zi = (zi + 1) % 12
    else:
        gi = (gi - 1) % 10
        zi = (zi - 1) % 12
    return TIAN_GAN[gi] + DI_ZHI[zi]


def calc_dayun(birth_year: int, year_gan: str, month_pillar: str,
               is_male: bool, start_age_offset: int = 0) -> List[Dict]:
    """
    推算10步大运（每步10年）。
    简化逻辑：
      - 阳年（甲丙戊庚壬）男 / 阴年（乙丁己辛癸）女 → 顺排
      - 阴年男 / 阳年女 → 逆排
      - 起运年龄 = start_age_offset（简化，默认0岁起排；可由外部调整）
    返回：
      [{'age': 起运岁数, 'pillar': '大运干支', 'start_year': 起运年份}, ...]
    """
    yang_gans = {'甲', '丙', '戊', '庚', '壬'}
    forward = (is_male and year_gan in yang_gans) or (not is_male and year_gan not in yang_gans)

    dayuns = []
    current = month_pillar
    # 第一步大运本身是月柱的下一个（顺）或上一个（逆）
    for step in range(10):
        current = _next_jiazi(current, forward=forward)
        start_age = start_age_offset + step * 10
        dayuns.append({
            'step': step + 1,
            'age': start_age,
            'pillar': current,
            'start_year': birth_year + start_age,
            'direction': '顺排' if forward else '逆排',
        })
    return dayuns


# = = = = = = = = = = = = = = = = = = = =
# 流年推算
# = = = = = = = = = = = = = = = = = = = =

def calc_liunian(year: int, day_master: str) -> Dict[str, str]:
    """
    推算指定年份的流年信息。
    流年干支 = (year - 4) mod 60 起算
    返回：
      {'year': 年份, 'pillar': 流年干支, 'gan_shigan': 年干十神, 'zhi_shigan': 年支藏干十神}
    """
    pillar = calc_year_pillar(year, 6, 15)  # 取年中确保是本年
    gan, zhi = pillar[0], pillar[1]
    return {
        'year': year,
        'pillar': pillar,
        'gan_shigan': derive_shigan(day_master, gan),
        'zhi_shigan_detail': derive_zhi_shigan(day_master, zhi),
    }


def calc_liunian_range(start_year: int, end_year: int,
                        day_master: str) -> List[Dict]:
    """批量推算一个年份范围的流年"""
    results = []
    for y in range(start_year, end_year + 1):
        results.append(calc_liunian(y, day_master))
    return results


# = = = = = = = = = = = = = = = = = = = =
# 对外数据结构
# = = = = = = = = = = = = = = = = = = = =

@dataclass
class DayunLiunian:
    birth_year: int
    birth_month: int
    birth_day: int
    hour: int = 12
    minute: int = 0
    is_male: bool = True
    longitude: float = 120.0

    # 结果
    pillars: Dict[str, str] = field(default_factory=dict)
    dayuns: List[Dict] = field(default_factory=list)
    liunian_samples: List[Dict] = field(default_factory=list)

    def __post_init__(self) -> None:
        # 先排四柱
        self.pillars = calc_bazi(self.birth_year, self.birth_month, self.birth_day,
                                   self.hour, self.minute, self.longitude)
        day_master = self.pillars['day'][0]
        year_gan = self.pillars['year'][0]

        # 大运
        self.dayuns = calc_dayun(self.birth_year, year_gan, self.pillars['month'],
                                   self.is_male, start_age_offset=0)

        # 流年示例（前后各5年）
        self.liunian_samples = calc_liunian_range(
            self.birth_year, self.birth_year + 10, day_master
        )

    def report(self) -> str:
        """生成文本报告"""
        lines = []
        lines.append("=" * 50)
        lines.append(f"出生: {self.birth_year}-{self.birth_month:02d}-{self.birth_day:02d} "
                      f"{'男命' if self.is_male else '女命'}")
        lines.append(f"四柱: 年{self.pillars['year']} 月{self.pillars['month']} "
                      f"日{self.pillars['day']} 时{self.pillars['hour']}")
        lines.append(f"日主: {self.pillars['day'][0]} ({GAN_WUXING[self.pillars['day'][0]]} "
                      f"{GAN_YINYANG[self.pillars['day'][0]]})")
        lines.append("-" * 50)
        lines.append("大运（10步，每步10年）:")
        for du in self.dayuns:
            gan_shigan = derive_shigan(self.pillars['day'][0], du['pillar'][0])
            lines.append(f"  {du['step']:>2d}. {du['age']:>3d}岁 ({du['start_year']}年起) "
                          f"{du['pillar']} [{gan_shigan}] ({du['direction']})")
        lines.append("-" * 50)
        lines.append("近年流年示例:")
        for ln in self.liunian_samples[:6]:
            zhi_shigans = '/'.join(
                f"{g}({s})" for g, s in ln['zhi_shigan_detail'].items()
            )
            lines.append(f"  {ln['year']}年 [{ln['pillar']}] "
                          f"年干十神:{ln['gan_shigan']} "
                          f"年支藏干:{zhi_shigans}")
        lines.append("=" * 50)
        return '\n'.join(lines)


# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
# v2.13.0 新增：流年运势精准引擎（LiunianEngine）
# 功能：大运+流年叠加效应、四维度吉凶量化评分（事业/财运/感情/健康）
# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =

# 节气近似日期（简化版，用于起运年龄估算）
# 节气日期按月份分组，返回该月节气的近似日序号
JIEQI_DAYS = {
    1: 6,    # 小寒
    2: 4,    # 立春
    3: 6,    # 惊蛰
    4: 5,    # 清明
    5: 6,    # 立夏
    6: 6,    # 芒种
    7: 7,    # 小暑
    8: 7,    # 立秋
    9: 8,    # 白露
    10: 8,   # 寒露
    11: 7,   # 立冬
    12: 7,   # 大雪
}

# 十神对各维度的影响力权重
SHIGAN_DIMENSION_WEIGHT = {
    '正官': {'career': 0.30, 'wealth': 0.10, 'relationships': 0.10, 'health': 0.05},
    '七杀': {'career': 0.25, 'wealth': 0.05, 'relationships': -0.05, 'health': -0.10},
    '正财': {'career': 0.05, 'wealth': 0.30, 'relationships': 0.15, 'health': 0.05},
    '偏财': {'career': 0.00, 'wealth': 0.25, 'relationships': 0.10, 'health': 0.00},
    '正印': {'career': 0.15, 'wealth': 0.00, 'relationships': 0.10, 'health': 0.20},
    '偏印': {'career': 0.10, 'wealth': 0.00, 'relationships': 0.00, 'health': 0.10},
    '食神': {'career': 0.10, 'wealth': 0.10, 'relationships': 0.20, 'health': 0.15},
    '伤官': {'career': 0.15, 'wealth': 0.05, 'relationships': -0.05, 'health': -0.05},
    '比肩': {'career': 0.05, 'wealth': 0.00, 'relationships': 0.15, 'health': 0.10},
    '劫财': {'career': -0.05, 'wealth': -0.15, 'relationships': -0.05, 'health': 0.05},
}

# 地支冲合对各维度的影响
ZHI_CHONG_EFFECT = {'career': -0.10, 'wealth': -0.10, 'relationships': -0.15, 'health': -0.10}
ZHI_HE_EFFECT = {'career': 0.05, 'wealth': 0.10, 'relationships': 0.15, 'health': 0.05}


def _estimate_qiyun_age(birth_year: int, birth_month: int, birth_day: int,
                         is_male: bool, year_gan: str) -> int:
    """
    估算起运年龄（简化版）。
    阳年男/阴年女 → 顺排（从出生到下一个节气）
    阴年男/阳年女 → 逆排（从上一个节气到出生）
    起运岁数 = 天数差 / 3（3天 = 1岁），取整
    """
    yang_gans = {'甲', '丙', '戊', '庚', '壬'}
    forward = (is_male and year_gan in yang_gans) or (not is_male and year_gan not in yang_gans)

    # 获取当月节气日
    jieqi_day = JIEQI_DAYS.get(birth_month, 6)

    if forward:
        # 顺排：出生日到本月节气（或下月节气）
        if birth_day < jieqi_day:
            days_diff = jieqi_day - birth_day
        else:
            # 到下月节气
            next_month = birth_month % 12 + 1
            next_jieqi = JIEQI_DAYS.get(next_month, 6)
            # 粗略计算：本月剩余天数 + 下月节气日
            days_in_month = 30  # 简化
            days_diff = (days_in_month - birth_day) + next_jieqi
    else:
        # 逆排：从上月节气到出生日
        prev_month = (birth_month - 2) % 12 + 1
        prev_jieqi = JIEQI_DAYS.get(prev_month, 6)
        if birth_day > jieqi_day:
            days_diff = birth_day - jieqi_day
        else:
            # 从上月节气
            days_in_month = 30
            days_diff = (days_in_month - prev_jieqi) + birth_day

    qiyun_age = max(1, days_diff // 3)
    return qiyun_age


# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
# 四维度运势评分
# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =

@dataclass
class FortuneScore:
    """四维度运势评分"""
    career: int = 50          # 事业运 (0-100)
    wealth: int = 50          # 财运 (0-100)
    relationships: int = 50   # 感情运 (0-100)
    health: int = 50          # 健康运 (0-100)
    overall: int = 50         # 综合分

    detail: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'career': self.career,
            'wealth': self.wealth,
            'relationships': self.relationships,
            'health': self.health,
            'overall': self.overall,
            'detail': self.detail,
        }


@dataclass
class LiunianResult:
    """单年流年运势完整结果"""
    year: int
    pillar: str
    gan: str
    zhi: str
    gan_shigan: str
    zhi_shigan: Dict[str, str] = field(default_factory=dict)
    dayun_pillar: str = ''             # 当前大运干支
    dayun_shigan: str = ''             # 大运天干十神
    dayun_effect: str = ''             # 大运叠加效应描述
    yongshen_score: int = 0            # 喜用神加减分
    score: FortuneScore = field(default_factory=FortuneScore)
    judgments: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    favorable_months: List[str] = field(default_factory=list)
    unfavorable_months: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'year': self.year,
            'pillar': self.pillar,
            'gan': self.gan,
            'zhi': self.zhi,
            'gan_shigan': self.gan_shigan,
            'zhi_shigan': self.zhi_shigan,
            'dayun_pillar': self.dayun_pillar,
            'dayun_shigan': self.dayun_shigan,
            'dayun_effect': self.dayun_effect,
            'yongshen_score': self.yongshen_score,
            'score': self.score.to_dict(),
            'judgments': self.judgments,
            'warnings': self.warnings,
            'favorable_months': self.favorable_months,
            'unfavorable_months': self.unfavorable_months,
        }


class LiunianEngine:
    """
    流年运势精准引擎 v2.13.0

    功能：
    1. 精确起运年龄推算
    2. 大运+流年叠加效应分析
    3. 四维度吉凶量化评分（事业/财运/感情/健康）
    4. 逐年流年详细报告
    """

    def __init__(self):
        self._dayuns_cache: Dict[str, List[Dict]] = {}

    def analyze(
        self,
        birth_year: int,
        birth_month: int,
        birth_day: int,
        hour: int = 12,
        minute: int = 0,
        is_male: bool = True,
        longitude: float = 120.0,
        yongshen: Optional[List[str]] = None,
        jishen: Optional[List[str]] = None,
        target_years: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """
        完整的流年运势分析。

        Args:
            birth_year/month/day/hour/minute: 出生信息
            is_male: 性别
            longitude: 经度
            yongshen: 喜用神五行列表（如 ['土', '金']）
            jishen: 忌神五行列表
            target_years: 目标年份列表（默认当前年份前后各5年）

        Returns:
            包含四柱、大运、逐年流年报告的完整字典
        """
        # 1) 排四柱
        pillars = calc_bazi(birth_year, birth_month, birth_day, hour, minute, longitude)
        day_master = pillars['day'][0]
        year_gan = pillars['year'][0]
        ri_zhi = pillars['day'][1] if len(pillars['day']) >= 2 else ''

        # 2) 推算大运
        qiyun_age = _estimate_qiyun_age(birth_year, birth_month, birth_day, is_male, year_gan)
        dayuns = calc_dayun(birth_year, year_gan, pillars['month'], is_male, qiyun_age)

        # 3) 确定喜用神（默认值）
        if not yongshen:
            dm_wuxing = GAN_WUXING.get(day_master, '火')
            sheng = WUXING_SHENG.get(dm_wuxing, '木')
            yongshen = [dm_wuxing, sheng]
        if not jishen:
            all_elem = {'木', '火', '土', '金', '水'}
            jishen = [e for e in all_elem if e not in yongshen][:2]

        # 4) 目标年份
        if not target_years:
            current_year = 2026
            target_years = list(range(current_year - 2, current_year + 8))

        # 5) 逐年分析
        liunian_results = []
        for year in target_years:
            result = self._analyze_single_year(
                year, day_master, ri_zhi, dayuns, yongshen, jishen, pillars
            )
            liunian_results.append(result)

        # 6) 汇总
        scores = [r.score for r in liunian_results]
        best = max(liunian_results, key=lambda r: r.score.overall)
        worst = min(liunian_results, key=lambda r: r.score.overall)
        avg_overall = sum(s.overall for s in scores) // len(scores) if scores else 50

        return {
            'pillars': pillars,
            'day_master': day_master,
            'day_master_wuxing': GAN_WUXING.get(day_master, ''),
            'day_master_yinyang': GAN_YINYANG.get(day_master, ''),
            'qiyun_age': qiyun_age,
            'yongshen': yongshen,
            'jishen': jishen,
            'dayuns': [{
                'step': d['step'],
                'start_age': d['age'],
                'end_age': d['age'] + 9,
                'pillar': d['pillar'],
                'start_year': d['start_year'],
                'direction': d['direction'],
                'gan_shigan': derive_shigan(day_master, d['pillar'][0]),
            } for d in dayuns],
            'liunian': [r.to_dict() for r in liunian_results],
            'summary': {
                'best_year': best.year,
                'best_score': best.score.overall,
                'worst_year': worst.year,
                'worst_score': worst.score.overall,
                'average_score': avg_overall,
                'total_years': len(liunian_results),
            },
        }

    def _analyze_single_year(
        self,
        year: int,
        day_master: str,
        ri_zhi: str,
        dayuns: List[Dict],
        yongshen: List[str],
        jishen: List[str],
        pillars: Dict[str, str],
    ) -> LiunianResult:
        """分析单个年份的流年运势"""

        # 流年干支
        liunian_pillar = calc_year_pillar(year, 6, 15)
        gan, zhi = liunian_pillar[0], liunian_pillar[1]
        gan_shigan = derive_shigan(day_master, gan)
        zhi_shigan = derive_zhi_shigan(day_master, zhi)

        # 找当前大运（按年份匹配）
        current_dayun = None
        for du in dayuns:
            if du['start_year'] <= year < du['start_year'] + 10:
                current_dayun = du
                break
        if not current_dayun and dayuns:
            current_dayun = dayuns[0]

        dayun_pillar = current_dayun['pillar'] if current_dayun else ''
        dayun_gan = dayun_pillar[0] if dayun_pillar else ''
        dayun_shigan = derive_shigan(day_master, dayun_gan) if dayun_gan else ''

        # 大运叠加效应
        dayun_effect = self._dayun_liunian_effect(dayun_shigan, gan_shigan)

        # 喜用神影响
        gan_wuxing = GAN_WUXING.get(gan, '')
        zhi_wuxing = ZHI_WUXING.get(zhi, '') if hasattr(globals().get('ZHI_WUXING'), 'get') else ''
        # 简化地支五行
        zhi_map = {'子': '水', '丑': '土', '寅': '木', '卯': '木', '辰': '土',
                   '巳': '火', '午': '火', '未': '土', '申': '金', '酉': '金', '戌': '土', '亥': '水'}
        zhi_wuxing = zhi_map.get(zhi, '')

        yongshen_score = 0
        if gan_wuxing in yongshen:
            yongshen_score += 10
        if zhi_wuxing in yongshen:
            yongshen_score += 10
        if gan_wuxing in jishen:
            yongshen_score -= 10
        if zhi_wuxing in jishen:
            yongshen_score -= 10

        # 四维度评分
        score = self._calculate_fortune_score(
            gan_shigan, dayun_shigan, yongshen_score, gan_wuxing, zhi_wuxing,
            yongshen, jishen, ri_zhi, zhi
        )

        # 断语
        judgments, warnings = self._generate_judgments(
            gan_shigan, dayun_shigan, dayun_effect, yongshen_score, score
        )

        # 有利/不利月份
        fav_months, unfav_months = self._month_analysis(zhi_wuxing, yongshen, jishen)

        return LiunianResult(
            year=year,
            pillar=liunian_pillar,
            gan=gan,
            zhi=zhi,
            gan_shigan=gan_shigan,
            zhi_shigan=zhi_shigan,
            dayun_pillar=dayun_pillar,
            dayun_shigan=dayun_shigan,
            dayun_effect=dayun_effect,
            yongshen_score=yongshen_score,
            score=score,
            judgments=judgments,
            warnings=warnings,
            favorable_months=fav_months,
            unfavorable_months=unfav_months,
        )

    def _dayun_liunian_effect(self, dayun_shigan: str, liunian_shigan: str) -> str:
        """大运与流年十神叠加效应分析"""
        if not dayun_shigan:
            return ''

        effects = []

        # 官杀叠加
        if dayun_shigan in ('正官', '七杀') and liunian_shigan in ('正官', '七杀'):
            effects.append('官杀混杂，事业压力大但机遇也大')
        # 财星叠加
        if dayun_shigan in ('正财', '偏财') and liunian_shigan in ('正财', '偏财'):
            effects.append('财星叠见，财运旺盛但需防财多身弱')
        # 印星助身
        if dayun_shigan in ('正印', '偏印') and liunian_shigan in ('比肩', '劫财', '食神', '伤官'):
            effects.append('印星生身，才华得以发挥')
        # 食伤生财
        if dayun_shigan in ('食神', '伤官') and liunian_shigan in ('正财', '偏财'):
            effects.append('食伤生财，创意变现之年')
        # 比劫夺财
        if liunian_shigan in ('劫财', '比肩') and dayun_shigan in ('正财', '偏财'):
            effects.append('比劫夺财，防破财、合伙失利')
        # 冲克
        if dayun_shigan == liunian_shigan:
            effects.append(f'大运与流年同为{liunian_shigan}，力量加倍')

        return '；'.join(effects) if effects else '大运与流年平稳过渡'

    def _calculate_fortune_score(
        self,
        gan_shigan: str,
        dayun_shigan: str,
        yongshen_score: int,
        gan_wuxing: str,
        zhi_wuxing: str,
        yongshen: List[str],
        jishen: List[str],
        ri_zhi: str,
        liu_zhi: str,
    ) -> FortuneScore:
        """四维度吉凶量化评分"""

        # 基础分 50
        career = 50
        wealth = 50
        relationships = 50
        health = 50

        # 十神权重
        if gan_shigan in SHIGAN_DIMENSION_WEIGHT:
            w = SHIGAN_DIMENSION_WEIGHT[gan_shigan]
            career += int(w.get('career', 0) * 50)
            wealth += int(w.get('wealth', 0) * 50)
            relationships += int(w.get('relationships', 0) * 50)
            health += int(w.get('health', 0) * 50)

        # 大运十神叠加
        if dayun_shigan in SHIGAN_DIMENSION_WEIGHT:
            w = SHIGAN_DIMENSION_WEIGHT[dayun_shigan]
            career += int(w.get('career', 0) * 30)
            wealth += int(w.get('wealth', 0) * 30)
            relationships += int(w.get('relationships', 0) * 30)
            health += int(w.get('health', 0) * 30)

        # 喜用神/忌神影响（均匀分布到各维度）
        yongshen_factor = yongshen_score // 4
        career += yongshen_factor
        wealth += yongshen_factor
        relationships += yongshen_factor
        health += yongshen_factor

        # 地支冲合
        if ri_zhi and liu_zhi:
            chong_pairs = {'子午', '丑未', '寅申', '卯酉', '辰戌', '巳亥'}
            if {liu_zhi, ri_zhi} in [{p[0], p[1]} for p in chong_pairs]:
                for dim, effect in ZHI_CHONG_EFFECT.items():
                    v = getattr(locals().get('__self__'), dim, None)
            he_pairs = {'子丑', '寅亥', '卯戌', '辰酉', '巳申', '午未'}
            if {liu_zhi, ri_zhi} in [{p[0], p[1]} for p in he_pairs]:
                for dim, effect in ZHI_HE_EFFECT.items():
                    dim_val = effect * 30
                    if dim == 'career':
                        career += int(dim_val)
                    elif dim == 'wealth':
                        wealth += int(dim_val)
                    elif dim == 'relationships':
                        relationships += int(dim_val)
                    elif dim == 'health':
                        health += int(dim_val)

        # 重新处理冲合（简化写法）
        if ri_zhi and liu_zhi:
            chong_set = {'子午', '丑未', '寅申', '卯酉', '辰戌', '巳亥'}
            pair = liu_zhi + ri_zhi
            is_chong = any(pair in s or pair[::-1] in s for s in chong_set)
            if is_chong:
                career -= 10
                wealth -= 10
                relationships -= 15
                health -= 10

            he_set = {'子丑', '寅亥', '卯戌', '辰酉', '巳申', '午未'}
            is_he = any(pair in s or pair[::-1] in s for s in he_set)
            if is_he:
                career += 5
                wealth += 10
                relationships += 15
                health += 5

        # 限制在 0-100
        career = max(0, min(100, career))
        wealth = max(0, min(100, wealth))
        relationships = max(0, min(100, relationships))
        health = max(0, min(100, health))
        overall = (career + wealth + relationships + health) // 4

        return FortuneScore(
            career=career,
            wealth=wealth,
            relationships=relationships,
            health=health,
            overall=overall,
        )

    def _generate_judgments(
        self,
        gan_shigan: str,
        dayun_shigan: str,
        dayun_effect: str,
        yongshen_score: int,
        score: FortuneScore,
    ) -> Tuple[List[str], List[str]]:
        """生成流年断语和警示"""
        judgments = []
        warnings = []

        # 十神断语
        shigan_judgments = {
            '正官': '正官流年，事业稳步上升，职场声誉提升，从政或管理者尤其有利。',
            '七杀': '七杀当令，挑战与机遇并存，事业变动大，宜主动出击。',
            '正财': '正财之年，财源稳定，工资奖金收入增加，适合稳健理财。',
            '偏财': '偏财显露，有意外之财或投资机会，但需防破财。',
            '正印': '印星当令，学习进修考证有利，贵人多为长辈上司。',
            '偏印': '偏印主事，利玄学技术冷门领域钻研，思维活跃。',
            '食神': '食神当令，才华发挥，社交丰富，适合展示才艺。',
            '伤官': '伤官主事，个性张扬，创意迸发，但需防口舌是非。',
            '比肩': '比肩主事，朋友缘同事缘佳，适合合作但需防分财。',
            '劫财': '劫财当令，防破财防小人，不宜借贷担保合伙投资。',
        }
        if gan_shigan in shigan_judgments:
            judgments.append(shigan_judgments[gan_shigan])

        # 大运叠加断语
        if dayun_effect and dayun_effect != '大运与流年平稳过渡':
            judgments.append(dayun_effect)

        # 四维度状态
        dim_labels = {
            'career': '事业', 'wealth': '财运',
            'relationships': '感情', 'health': '健康',
        }
        for dim, label in dim_labels.items():
            val = getattr(score, dim)
            if val >= 80:
                judgments.append(f'{label}运极佳（{val}分），宜积极进取。')
            elif val >= 60:
                judgments.append(f'{label}运平稳（{val}分），稳中求进。')
            elif val <= 30:
                warnings.append(f'{label}运偏弱（{val}分），宜守不宜攻。')

        # 喜用神相关
        if yongshen_score >= 15:
            judgments.append('流年干支皆为喜用神，大吉之年，诸事顺遂。')
        elif yongshen_score <= -15:
            warnings.append('干支皆忌，本年整体压力较大，宜守不宜攻。')

        # 综合警示
        if score.overall < 40:
            warnings.append('本年运势偏弱，宜守成不宜冒进，健康方面需定期检查。')
        if score.overall >= 75:
            judgments.append('整体本年运势上扬，把握机遇可获得显著成果。')

        if len(judgments) < 2:
            judgments.append('本年运势平稳，稳中求进为宜。')

        return judgments, warnings

    def _month_analysis(
        self,
        liu_zhi_wuxing: str,
        yongshen: List[str],
        jishen: List[str],
    ) -> Tuple[List[str], List[str]]:
        """分析有利/不利月份"""
        month_map = [
            ('正月', '木'), ('二月', '木'), ('三月', '土'),
            ('四月', '火'), ('五月', '火'), ('六月', '土'),
            ('七月', '金'), ('八月', '金'), ('九月', '土'),
            ('十月', '水'), ('冬月', '水'), ('腊月', '土'),
        ]
        fav, unfav = [], []
        for m_name, m_wuxing in month_map:
            if m_wuxing in yongshen:
                fav.append(m_name)
            elif m_wuxing in jishen:
                unfav.append(m_name)
        return fav, unfav


# 全局单例
_liunian_engine: Optional[LiunianEngine] = None


def get_liunian_engine() -> LiunianEngine:
    global _liunian_engine
    if _liunian_engine is None:
        _liunian_engine = LiunianEngine()
    return _liunian_engine


if __name__ == '__main__':
    # 自测原始 DayunLiunian
    chart = DayunLiunian(1990, 6, 15, 10, 30, is_male=True, longitude=116.4)
    print(chart.report())

    print()
    chart2 = DayunLiunian(1990, 6, 15, 10, 30, is_male=False, longitude=116.4)
    print(chart2.report())

    # 自测新引擎
    print('\n' + '=' * 60)
    print('v2.13.0 LiunianEngine 自测')
    print('=' * 60)
    engine = get_liunian_engine()
    result = engine.analyze(
        birth_year=1990, birth_month=6, birth_day=15,
        hour=12, minute=0, is_male=True, longitude=116.4,
        yongshen=['土', '金'], jishen=['木', '火'],
        target_years=[2026, 2027, 2028, 2029, 2030],
    )
    print(f"日主: {result['day_master']} ({result['day_master_wuxing']})")
    print(f"起运: {result['qiyun_age']}岁")
    print(f"喜用神: {result['yongshen']}")
    print("大运:")
    for du in result['dayuns']:
        print(f"  {du['start_age']:>3d}-{du['end_age']:>3d}岁: {du['pillar']} [{du['gan_shigan']}] ({du['direction']})")
    print("\n流年分析:")
    for ln in result['liunian']:
        print(f"  {ln['year']}年 [{ln['pillar']}] "
              f"十神:{ln['gan_shigan']} "
              f"四维评分: 事业{ln['score']['career']} "
              f"财运{ln['score']['wealth']} "
              f"感情{ln['score']['relationships']} "
              f"健康{ln['score']['health']} "
              f"综合{ln['score']['overall']}")
        if ln['judgments']:
            print(f"    断语: {ln['judgments'][0]}")
    print(f"\n汇总: 最佳{result['summary']['best_year']}年 "
          f"最差{result['summary']['worst_year']}年 "
          f"平均{result['summary']['average_score']}分")
