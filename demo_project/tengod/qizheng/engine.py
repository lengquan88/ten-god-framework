"""
tengod.qizheng — 阶段二十一 · 21.3 七政四余星象排盘

七政四余 = 七政（日月金木水火土） + 四余（罗睺/计都/月孛/紫气）

简化版算法（不依赖 swiss ephemeris，基于平均轨道周期推算）：
  1. 儒略日计算（简化）
  2. 行星黄经 = 基础黄经 + 平均速度 × 时间差
  3. 入宫判断：黄经/30 取整 = 十二宫
  4. 庙旺利陷：根据行星所在宫位判断

十二宫（黄道十二宫，简化为地支对应）：
  子宫: 330~360 度 + 0~30度
  丑宫: 30~60
  寅宫: 60~90
  卯宫: 90~120
  辰宫: 120~150
  巳宫: 150~180
  午宫: 180~210
  未宫: 210~240
  申宫: 240~270
  酉宫: 270~300
  戌宫: 300~330
  亥宫: 330~360

实际应用中，需要更精确的天文计算；本实现作为命理学演示用途，
追求的是"趋势正确"而非"天文精度"。
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ============================================================================
# 基础数据
# ============================================================================

# 七政基本参数（平均轨道周期，儒略世纪相对于J2000）
# 平均运动速度(度/日) - 简化版
SEVEN_PLANETS = {
    "日": {"name_cn": "日", "period_days": 365.24, "base_longitude": 280.0, "wuxing": "火", "type": "吉星"},
    "月": {"name_cn": "月", "period_days": 27.32,  "base_longitude": 240.0, "wuxing": "水", "type": "吉星"},
    "木": {"name_cn": "木星", "period_days": 4332.59, "base_longitude": 30.0,  "wuxing": "木", "type": "吉星"},
    "火": {"name_cn": "火星", "period_days": 686.97, "base_longitude": 120.0, "wuxing": "火", "type": "凶星"},
    "土": {"name_cn": "土星", "period_days": 10759.2, "base_longitude": 150.0, "wuxing": "土", "type": "凶星"},
    "金": {"name_cn": "金星", "period_days": 224.70, "base_longitude": 45.0,  "wuxing": "金", "type": "吉星"},
    "水": {"name_cn": "水星", "period_days": 87.97,  "base_longitude": 260.0, "wuxing": "水", "type": "中性"},
}

# 四余（与七政相关）
FOUR_PLANETS = {
    "罗睺": {"wuxing": "火", "type": "凶星", "influence": "主是非争斗"},
    "计都": {"wuxing": "土", "type": "凶星", "influence": "主阴险阻碍"},
    "月孛": {"wuxing": "水", "type": "中性", "influence": "主妖邪波折"},
    "紫气": {"wuxing": "木", "type": "吉星", "influence": "主贵人祥瑞"},
}

# 十二宫（对应地支 + 度数）
TWELVE_PALACES = [
    ("子", 0, 30), ("丑", 30, 60), ("寅", 60, 90),
    ("卯", 90, 120), ("辰", 120, 150), ("巳", 150, 180),
    ("午", 180, 210), ("未", 210, 240), ("申", 240, 270),
    ("酉", 270, 300), ("戌", 300, 330), ("亥", 330, 360),
]

# 庙旺利陷（简化版）
MIAO_WANG = {
    ("日", "午"): "庙", ("月", "未"): "庙",
    ("木", "亥"): "庙", ("火", "寅"): "庙", ("火", "午"): "庙",
    ("土", "丑"): "庙", ("土", "辰"): "庙", ("土", "未"): "庙", ("土", "戌"): "庙",
    ("金", "酉"): "庙", ("水", "申"): "庙", ("水", "子"): "庙",
    ("日", "卯"): "旺", ("月", "酉"): "旺",
    ("木", "未"): "旺", ("火", "戌"): "旺",
    ("土", "午"): "旺", ("金", "辰"): "旺", ("水", "巳"): "旺",
}


# ============================================================================
# 核心计算（简化版）
# ============================================================================

def _julian_day(year: int, month: int, day: int, hour: float = 12.0) -> float:
    """简化版儒略日计算（适用于1900~2100）"""
    a = (14 - month) // 12
    y = year + 4800 - a
    m = month + 12 * a - 3
    jdn = day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045
    return jdn + (hour - 12.0) / 24.0


def _days_from_j2000(jd: float) -> float:
    """距离J2000 (2000-01-01 12:00 UT) 天数"""
    return jd - 2451545.0


def _planet_longitude(planet_key: str, days_from_j2000: float) -> float:
    """
    简化版：根据基础黄经 + 平均速度 × 天数，计算行星黄经(0~360度)。

    实际天文计算需考虑：轨道离心率、摄动、平近点角等。
    此处简化用于命理演示。
    """
    info = SEVEN_PLANETS.get(planet_key, {"period_days": 365.24, "base_longitude": 0.0})
    speed = 360.0 / info["period_days"]  # 平均每日运动度数
    longitude = (info["base_longitude"] + speed * days_from_j2000) % 360.0
    return longitude


def _zhi_from_longitude(longitude: float) -> str:
    """根据黄经确定地支（子宫0~30度）"""
    idx = int(longitude // 30) % 12
    return TWELVE_PALACES[idx][0]


def _get_miao_wang(planet: str, zhi: str) -> str:
    """判断庙旺利陷"""
    if (planet, zhi) in MIAO_WANG:
        return MIAO_WANG[(planet, zhi)]
    return "得"  # 默认


# ============================================================================
# 排盘引擎
# ============================================================================

@dataclass
class PlanetPosition:
    """单颗行星位置"""
    name: str          # 七政/四余名称
    longitude: float   # 黄经度
    zhi: str           # 入宫地支
    palace: str        # 宫位（命宫/财帛等，由外部分配）
    miao_wang: str     # 庙/旺/得/利/陷
    wuxing: str        # 五行
    type: str          # 吉/凶/中

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "longitude_deg": round(self.longitude, 2),
            "zhi": self.zhi,
            "palace": self.palace,
            "miao_wang": self.miao_wang,
            "wuxing": self.wuxing,
            "type": self.type,
        }


@dataclass
class QizhengResult:
    """七政四余星象排盘结果"""
    birth_datetime: str
    julian_day: float
    seven_planets: Dict[str, PlanetPosition]
    four_remainders: Dict[str, PlanetPosition]
    analysis: Dict[str, Any] = field(default_factory=dict)
    judgments: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "birth_datetime": self.birth_datetime,
            "julian_day": round(self.julian_day, 2),
            "seven_planets": {k: v.to_dict() for k, v in self.seven_planets.items()},
            "four_remainders": {k: v.to_dict() for k, v in self.four_remainders.items()},
            "analysis": self.analysis,
            "judgments": self.judgments,
        }


class QizhengEngine:
    """七政四余简化排盘引擎"""

    # 简化版宫位分配：将命宫定义为出生时刻的"日支"
    def __init__(self):
        pass

    def compute(self, year: int, month: int, day: int,
                hour: int = 12, minute: int = 0) -> QizhengResult:
        """
        根据出生年月日时排盘

        Args:
            year: 公历年（如1990）
            month: 月（1~12）
            day: 日（1~31）
            hour: 时（0~23）
            minute: 分（0~59）
        """
        # 1) 儒略日
        jd = _julian_day(year, month, day, hour + minute / 60.0)
        days = _days_from_j2000(jd)

        # 2) 计算七政位置
        seven = {}
        for key, info in SEVEN_PLANETS.items():
            lon = _planet_longitude(key, days)
            zhi = _zhi_from_longitude(lon)
            seven[key] = PlanetPosition(
                name=info["name_cn"],
                longitude=lon,
                zhi=zhi,
                palace=self._assign_palace(zhi),
                miao_wang=_get_miao_wang(key, zhi),
                wuxing=info["wuxing"],
                type=info["type"],
            )

        # 3) 四余位置（简化：罗睺与月亮相关，计都对冲罗睺，月孛=月远地点，紫气=月行最慢点）
        four = {}
        moon_lon = seven["月"].longitude

        # 罗睺: 月亮升交点 - 简化为月球经度 + 180（简化值）
        luohou_lon = (moon_lon + 90.0) % 360.0
        four["罗睺"] = PlanetPosition(
            name="罗睺", longitude=luohou_lon, zhi=_zhi_from_longitude(luohou_lon),
            palace=self._assign_palace(_zhi_from_longitude(luohou_lon)),
            miao_wang=_get_miao_wang("火", _zhi_from_longitude(luohou_lon)),
            wuxing="火", type="凶星"
        )

        # 计都: 罗睺对冲 + 180 度
        jidu_lon = (luohou_lon + 180.0) % 360.0
        four["计都"] = PlanetPosition(
            name="计都", longitude=jidu_lon, zhi=_zhi_from_longitude(jidu_lon),
            palace=self._assign_palace(_zhi_from_longitude(jidu_lon)),
            miao_wang="陷", wuxing="土", type="凶星"
        )

        # 月孛: 月球远地点（简化=月经度 + 90）
        yuebo_lon = (moon_lon + 270.0) % 360.0
        four["月孛"] = PlanetPosition(
            name="月孛", longitude=yuebo_lon, zhi=_zhi_from_longitude(yuebo_lon),
            palace=self._assign_palace(_zhi_from_longitude(yuebo_lon)),
            miao_wang="陷", wuxing="水", type="中性"
        )

        # 紫气: 简化为月经度 + 45
        ziqi_lon = (moon_lon + 45.0) % 360.0
        four["紫气"] = PlanetPosition(
            name="紫气", longitude=ziqi_lon, zhi=_zhi_from_longitude(ziqi_lon),
            palace=self._assign_palace(_zhi_from_longitude(ziqi_lon)),
            miao_wang="庙", wuxing="木", type="吉星"
        )

        # 4) 组装
        dt_str = f"{year:04d}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}"
        result = QizhengResult(
            birth_datetime=dt_str,
            julian_day=jd,
            seven_planets=seven,
            four_remainders=four,
        )

        # 5) 分析
        self._analyze(result)
        return result

    def _assign_palace(self, zhi: str) -> str:
        """根据地支简化分配宫位（传统紫微12宫）"""
        mapping = {
            "子": "命宫", "丑": "兄弟宫", "寅": "夫妻宫",
            "卯": "子女宫", "辰": "财帛宫", "巳": "奴仆宫",
            "午": "疾厄宫", "未": "迁移宫", "申": "官禄宫",
            "酉": "福德宫", "戌": "田宅宫", "亥": "父母宫",
        }
        return mapping.get(zhi, "命宫")

    def _analyze(self, result: QizhengResult) -> None:
        """简化分析：根据七政四余入宫分布 + 庙旺判断运势"""
        # 吉位统计
        miao_count = 0
        wang_count = 0
        xian_count = 0
        jixing = []
        for name, pos in result.seven_planets.items():
            if pos.miao_wang == "庙":
                miao_count += 1
            elif pos.miao_wang == "旺":
                wang_count += 1
            elif pos.miao_wang == "陷":
                xian_count += 1
            if pos.type == "吉星":
                jixing.append(f"{name}入{pos.palace}({pos.zhi})")

        # 四余分析
        siyu_analysis = []
        for name, pos in result.four_remainders.items():
            if pos.type == "吉星":
                siyu_analysis.append(f"{name}入{pos.palace}，{FOUR_PLANETS.get(name, {}).get('influence', '')}")
            elif pos.type == "凶星":
                siyu_analysis.append(f"{name}入{pos.palace}，{FOUR_PLANETS.get(name, {}).get('influence', '')}")

        result.analysis = {
            "庙旺总数": miao_count + wang_count,
            "陷数": xian_count,
            "主星庙旺": jixing,
            "四余分布": siyu_analysis,
        }

        # 生成断语（简化）
        if miao_count >= 2:
            result.judgments.append(f"命盘庙旺数多（{miao_count}庙{wang_count}旺），整体格局偏吉。")
        elif xian_count >= 3:
            result.judgments.append(f"命盘陷数较多（{xian_count}个），部分领域需特别注意。")
        else:
            result.judgments.append("命盘格局平衡，整体平稳渐进。")

        # 吉星入命宫
        for name, pos in result.seven_planets.items():
            if pos.palace == "命宫" and pos.type == "吉星":
                result.judgments.append(f"{name}入命宫，{pos.wuxing}星耀命，基础运势不俗。")
            if pos.palace == "财帛宫" and pos.type == "吉星":
                result.judgments.append(f"{name}入财帛宫，财源稳定，理财能力强。")
            if pos.palace == "官禄宫" and pos.type == "吉星":
                result.judgments.append(f"{name}入官禄宫，事业有贵人扶助，仕途有望。")

        # 四余警示
        for name, pos in result.four_remainders.items():
            if pos.type == "凶星" and pos.palace in ("命宫", "疾厄宫"):
                result.judgments.append(f"{name}临{pos.palace}，需特别提防精神/健康方面的波动。")


# ============================================================================
# 便捷函数
# ============================================================================

def compute_qizheng(year: int, month: int, day: int,
                    hour: int = 12, minute: int = 0) -> QizhengResult:
    return QizhengEngine().compute(year=year, month=month, day=day, hour=hour, minute=minute)


if __name__ == "__main__":
    # 自测：2026年6月19日 12:00
    print("=" * 60)
    print("七政四余自测：2026-06-19 12:00")
    print("=" * 60)
    result = compute_qizheng(2026, 6, 19, 12, 0)
    print(f"出生时间: {result.birth_datetime}")
    print(f"儒略日: {result.julian_day:.2f}")
    print()
    print("七政位置:")
    for key, pos in result.seven_planets.items():
        print(f"  {key} ({pos.name}): {pos.longitude:.2f}° → {pos.zhi}宫({pos.palace}) "
              f"{pos.miao_wang} {pos.wuxing} {pos.type}")
    print()
    print("四余位置:")
    for key, pos in result.four_remainders.items():
        print(f"  {key}: {pos.longitude:.2f}° → {pos.zhi}宫({pos.palace}) {pos.miao_wang}")
    print()
    print("分析:")
    for k, v in result.analysis.items():
        if isinstance(v, list):
            print(f"  {k}:")
            for item in v:
                print(f"    · {item}")
        else:
            print(f"  {k}: {v}")
    print()
    print("断语:")
    for j in result.judgments:
        print(f"  · {j}")
