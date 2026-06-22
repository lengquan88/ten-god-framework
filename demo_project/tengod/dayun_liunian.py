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
    _gan_index, _zhi_index, _jiazi_name,
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


if __name__ == '__main__':
    # 自测
    chart = DayunLiunian(1990, 6, 15, 10, 30, is_male=True, longitude=116.4)
    print(chart.report())

    print()
    chart2 = DayunLiunian(1990, 6, 15, 10, 30, is_male=False, longitude=116.4)
    print(chart2.report())
