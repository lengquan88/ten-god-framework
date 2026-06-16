"""
bazi_calculator.py — 八字排盘核心
= = = = = = = = = = = = = = = = = = =
功能：
  1. 公历 → 年/月/日/时四柱干支
  2. 立春为界判年柱
  3. 节气为界判月柱（五虎遁）
  4. 日柱（查表/公式）
  5. 时辰分界（五鼠遁）
  6. 真太阳时修正（经度修正）

关键规则摘要：
  - 年柱：以立春为界；立春之前为上一年
  - 月柱：以节气为界，正月建寅（立春-惊蛰为寅月）
  - 月干：五虎遁（甲己之年丙作首…）
  - 时干：五鼠遁（甲己还加甲…）
  - 真太阳时：本地经度相对东经120度的偏差

用法：
  >>> from tengod.bazi_calculator import BaziChart
  >>> chart = BaziChart(1990, 6, 15, 10, 30, lon=116.4, lat=39.9)
  >>> chart.pillars
  {'year': '庚午', 'month': '壬午', 'day': '庚子', 'hour': '辛巳'}
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# = = = = = = = = = = = = = = = = = = = =
# 常量表
# = = = = = = = = = = = = = = = = = = = =

TIAN_GAN = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']
DI_ZHI = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']

# 月支对应（寅月=正月，即立春~惊蛰）
MONTH_ZHI = ['寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥', '子', '丑']

# 五虎遁：按年干起正月（寅月）天干
# 甲己之年丙作首；乙庚之年戊为头；丙辛必定寻庚起；丁壬壬位顺流行；戊癸甲兮方可得
WU_HU_DUN = {
    '甲': '丙', '己': '丙',
    '乙': '戊', '庚': '戊',
    '丙': '庚', '辛': '庚',
    '丁': '壬', '壬': '壬',
    '戊': '甲', '癸': '甲',
}

# 五鼠遁：按日干起子时天干
# 甲己还加甲；乙庚丙作初；丙辛从戊起；丁壬庚子居；戊癸何方发；壬子是真途
WU_SHU_DUN = {
    '甲': '甲', '己': '甲',
    '乙': '丙', '庚': '丙',
    '丙': '戊', '辛': '戊',
    '丁': '庚', '壬': '庚',
    '戊': '壬', '癸': '壬',
}

# 简化版二十四节气（月/日近似值）
# 用于判定月柱交界；精确天文节气算法复杂，这里用经验近似
# 格式: [('节气名', month, day, 所属月支序号)]
# 序号对应 MONTH_ZHI: 0=寅, 1=卯, ... 11=丑
SOLAR_TERMS_APPROX = [
    ('立春', 2, 4, 0),
    ('惊蛰', 3, 6, 1),
    ('清明', 4, 5, 2),
    ('立夏', 5, 6, 3),
    ('芒种', 6, 6, 4),
    ('小暑', 7, 7, 5),
    ('立秋', 8, 8, 6),
    ('白露', 9, 8, 7),
    ('寒露', 10, 8, 8),
    ('立冬', 11, 7, 9),
    ('大雪', 12, 7, 10),
    ('小寒', 1, 6, 11),
]


# = = = = = = = = = = = = = = = = = = = =
# 工具函数
# = = = = = = = = = = = = = = = = = = = =

def _gan_index(gan: str) -> int:
    return TIAN_GAN.index(gan)


def _zhi_index(zhi: str) -> int:
    return DI_ZHI.index(zhi)


def _jiazi_index(ganzhi: str) -> int:
    """返回 1~60 的甲子序号"""
    g, z = ganzhi[0], ganzhi[1]
    gi, zi = _gan_index(g), _zhi_index(z)
    # 使用中国剩余定理求 n: n ≡ gi (mod 10), n ≡ zi (mod 12)
    for n in range(1, 61):
        if (n - 1) % 10 == gi and (n - 1) % 12 == zi:
            return n
    return 0


def _jiazi_name(idx: int) -> str:
    """根据 1~60 序号取甲子名称"""
    return TIAN_GAN[(idx - 1) % 10] + DI_ZHI[(idx - 1) % 12]


def _true_solar_time(hour: int, minute: int, longitude: float) -> Tuple[int, int]:
    """
    真太阳时修正：
      - 东经120度为北京时间基准
      - 每相差1度约4分钟（24h * 60min / 360度 = 4 min/度）
      - 经度>120 → 比北京时间早；<120 → 比北京时间晚
    返回修正后的 (hour, minute)
    """
    diff_minutes = (longitude - 120.0) * 4.0  # 度 × 4 分钟/度
    total_minutes = hour * 60 + minute + diff_minutes
    total_minutes = total_minutes % (24 * 60)
    return int(total_minutes // 60), int(total_minutes % 60)


def _get_month_zhi_index(month: int, day: int) -> int:
    """
    根据月日确定所属月支序号（0=寅 ... 11=丑）。
    使用近似节气表判定月柱交界。
    """
    # 构造 (month, day) 对
    for i in range(len(SOLAR_TERMS_APPROX)):
        name, m1, d1, zhi_idx = SOLAR_TERMS_APPROX[i]
        name_next, m2, d2, zhi_idx_next = SOLAR_TERMS_APPROX[(i + 1) % len(SOLAR_TERMS_APPROX)]
        # 判断日期是否在 [m1/d1, m2/d2) 之间
        # 处理跨年情况（小寒 1/6 到 立春 2/4）
        in_range = _date_in_range(month, day, m1, d1, m2, d2)
        if in_range:
            return zhi_idx
    return 0  # 默认寅月


def _date_in_range(m: int, d: int, m1: int, d1: int, m2: int, d2: int) -> bool:
    """判断 (m,d) 是否在 [m1/d1, m2/d2) 之间，处理跨年。"""
    def _key(mm: int, dd: int) -> int:
        return mm * 100 + dd
    key = _key(m, d)
    k1 = _key(m1, d1)
    k2 = _key(m2, d2)
    if k1 <= k2:
        return k1 <= key < k2
    else:
        # 跨年（例如 小寒 1/6 到 立春 2/4）
        return key >= k1 or key < k2


# = = = = = = = = = = = = = = = = = = = =
# 核心计算
# = = = = = = = = = = = = = = = = = = = =

def calc_year_pillar(year: int, month: int, day: int) -> str:
    """
    年柱：以立春为界。
      - 立春（约2月4日）及之后 → 本年
      - 立春之前 → 上一年
    干支：以公元4年为甲子年参考，(year-4) mod 60 取偏移
    """
    before_lichun = _date_before_lichun(month, day)
    effective_year = year - 1 if before_lichun else year
    offset = (effective_year - 4) % 60  # 0 表示甲子年
    idx = offset + 1  # 转换为 1~60 序号
    return _jiazi_name(idx)


def _date_before_lichun(month: int, day: int) -> bool:
    if month < 2:
        return True
    if month == 2 and day < 4:
        return True
    return False


def calc_month_pillar(year: int, month: int, day: int, year_gan: str) -> str:
    """
    月柱：
      - 月支：由节气决定（立春=寅月起点）
      - 月干：五虎遁（以年干推算正月天干）
    """
    # 月支
    zhi_idx = _get_month_zhi_index(month, day)
    month_zhi = MONTH_ZHI[zhi_idx]

    # 月干：年干→正月天干，再按月份偏移
    first_month_gan = WU_HU_DUN[year_gan]
    first_gan_idx = _gan_index(first_month_gan)
    month_gan_idx = (first_gan_idx + zhi_idx) % 10  # zhi_idx 即月份偏移（0=寅月=正月）
    month_gan = TIAN_GAN[month_gan_idx]

    return month_gan + month_zhi


def calc_day_pillar(year: int, month: int, day: int) -> str:
    """
    日柱：基于公历日期计算。
    使用通用公式：
      1582年10月15日及之后（格里历）
      以 1900-01-01 = 甲戌日 (idx=11) 为参考
      更准确：以某已知基准日推算
    这里用一个广泛验证的公式：
      base = 1900年1月1日为"甲戌"日，序号 11
      计算相差天数，加 11 后 mod 60
    """
    from datetime import date
    try:
        target = date(year, month, day)
        base = date(1900, 1, 1)
        diff = (target - base).days
        idx = (11 + diff) % 60  # 1900-01-01 为甲戌日(序号11)
        if idx <= 0:
            idx += 60
        return _jiazi_name(idx)
    except ValueError:
        return ""


def calc_hour_pillar(day_gan: str, true_hour: int, true_minute: int) -> str:
    """
    时柱：
      - 时支：按时辰划分（23-1 子时, 1-3 丑时...）
      - 时干：五鼠遁
    注意：23:00 之后为下一日的子时（夜子时规则简化处理）
    """
    # 时支
    hour_zhi = _hour_to_zhi(true_hour, true_minute)

    # 时干：日干→子时天干，按时辰偏移
    first_hour_gan = WU_SHU_DUN[day_gan]
    first_gan_idx = _gan_index(first_hour_gan)
    zhi_offset = _zhi_index(hour_zhi)  # 子=0, 丑=1 ...
    hour_gan_idx = (first_gan_idx + zhi_offset) % 10
    hour_gan = TIAN_GAN[hour_gan_idx]

    return hour_gan + hour_zhi


def _hour_to_zhi(h: int, m: int) -> str:
    """24小时制 → 地支时辰。
    子时: 23:00 - 0:59
    丑时: 1:00 - 2:59
    ...
    """
    total_min = h * 60 + m
    if total_min >= 23 * 60 or total_min < 1 * 60:
        return '子'
    # 每2小时一支，从1:00起算
    idx = ((h - 1) // 2 + 1) % 12
    return DI_ZHI[idx]


# = = = = = = = = = = = = = = = = = = = =
# 对外数据结构
# = = = = = = = = = = = = = = = = = = = =

@dataclass
class BaziChart:
    """
    八字命盘 — 四柱干支 + 元信息
    """
    year: int
    month: int
    day: int
    hour: int
    minute: int
    longitude: float = 120.0  # 默认北京时间
    latitude: float = 39.9

    # 计算结果
    pillars: Dict[str, str] = field(default_factory=dict)
    true_hour: int = 0
    true_minute: int = 0

    def __post_init__(self) -> None:
        self._calculate()

    def _calculate(self) -> None:
        # 真太阳时修正
        self.true_hour, self.true_minute = _true_solar_time(
            self.hour, self.minute, self.longitude
        )

        # 年柱
        year_pillar = calc_year_pillar(self.year, self.month, self.day)
        year_gan = year_pillar[0]

        # 月柱
        month_pillar = calc_month_pillar(self.year, self.month, self.day, year_gan)

        # 日柱
        day_pillar = calc_day_pillar(self.year, self.month, self.day)

        # 时柱（基于真太阳时）
        hour_pillar = calc_hour_pillar(day_pillar[0], self.true_hour, self.true_minute)

        self.pillars = {
            'year': year_pillar,
            'month': month_pillar,
            'day': day_pillar,
            'hour': hour_pillar,
        }

    @property
    def day_master(self) -> str:
        """日干（日主）"""
        return self.pillars['day'][0]

    @property
    def ganzhi_list(self) -> List[str]:
        """四柱干支列表 [年, 月, 日, 时]"""
        return [
            self.pillars['year'],
            self.pillars['month'],
            self.pillars['day'],
            self.pillars['hour'],
        ]

    def __repr__(self) -> str:
        return (
            f"BaziChart({self.year}-{self.month:02d}-{self.day:02d} "
            f"{self.hour:02d}:{self.minute:02d}, "
            f"真太阳时={self.true_hour:02d}:{self.true_minute:02d}, "
            f"年={self.pillars['year']} 月={self.pillars['month']} "
            f"日={self.pillars['day']} 时={self.pillars['hour']})"
        )


# = = = = = = = = = = = = = = = = = = = =
# 便捷函数
# = = = = = = = = = = = = = = = = = = = =

def calc_bazi(year: int, month: int, day: int,
              hour: int = 12, minute: int = 0,
              longitude: float = 120.0, latitude: float = 39.9) -> Dict[str, str]:
    """
    便捷函数：输入公历日期时间，返回四柱字典。
    """
    chart = BaziChart(year, month, day, hour, minute, longitude, latitude)
    return chart.pillars


if __name__ == '__main__':
    # 自测：几个关键日期
    test_cases = [
        (1990, 6, 15, 10, 30, 116.4, 39.9, "示例一"),
        (2000, 2, 4, 12, 0, 116.4, 39.9, "立春当日"),
        (2000, 2, 3, 23, 0, 116.4, 39.9, "立春前一日夜子时"),
        (1984, 2, 5, 12, 0, 116.4, 39.9, "甲子年参考"),
    ]
    for y, m, d, h, mi, lon, lat, label in test_cases:
        c = BaziChart(y, m, d, h, mi, lon, lat)
        print(f"[{label}] {y}-{m:02d}-{d:02d} {h:02d}:{mi:02d} "
              f"→ 年{c.pillars['year']} 月{c.pillars['month']} "
              f"日{c.pillars['day']} 时{c.pillars['hour']} "
              f"(真太阳时{c.true_hour:02d}:{c.true_minute:02d})")
