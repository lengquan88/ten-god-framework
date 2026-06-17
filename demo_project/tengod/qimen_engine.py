#!/usr/bin/env python3
"""
qimen_engine.py — 奇门遁甲排盘引擎 v1.0.0

奇门遁甲是中国古代最高层次的预测学之一，以时间、空间、数理
三者结合，通过九宫、八门、九星、八神、三奇六仪等要素进行推演。

核心排盘流程：
  1. 排四柱（年、月、日、时柱）
  2. 定局（阴阳遁、局数）
  3. 排地盘（三奇六仪）
  4. 排天盘（九星）
  5. 排人盘（八门）
  6. 排神盘（八神）
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ============================================================================
# 常量定义
# ============================================================================

# 九宫格（洛书数序）
# 4 9 2
# 3 5 7
# 8 1 6
JIU_GONG = {
    1: {"name": "坎", "zhi": "子", "wuxing": "水", "direction": "北", "num": 1},
    2: {"name": "坤", "zhi": "未申", "wuxing": "土", "direction": "西南", "num": 2},
    3: {"name": "震", "zhi": "卯", "wuxing": "木", "direction": "东", "num": 3},
    4: {"name": "巽", "zhi": "辰巳", "wuxing": "木", "direction": "东南", "num": 4},
    5: {"name": "中", "zhi": "", "wuxing": "土", "direction": "中", "num": 5},
    6: {"name": "乾", "zhi": "戌亥", "wuxing": "金", "direction": "西北", "num": 6},
    7: {"name": "兑", "zhi": "酉", "wuxing": "金", "direction": "西", "num": 7},
    8: {"name": "艮", "zhi": "丑寅", "wuxing": "土", "direction": "东北", "num": 8},
    9: {"name": "离", "zhi": "午", "wuxing": "火", "direction": "南", "num": 9},
}

# 八门
BA_MEN = ["休", "死", "伤", "杜", "中", "开", "惊", "生", "景"]
# 八门原始宫位（休1, 死2, 伤3, 杜4, 开6, 惊7, 生8, 景9）
BA_MEN_ORIGIN = {"休": 1, "死": 2, "伤": 3, "杜": 4, "开": 6, "惊": 7, "生": 8, "景": 9}

# 九星
JIU_XING = ["天蓬", "天芮", "天冲", "天辅", "天禽", "天心", "天柱", "天任", "天英"]
# 九星原始宫位
JIU_XING_ORIGIN = {
    "天蓬": 1, "天芮": 2, "天冲": 3, "天辅": 4,
    "天禽": 5, "天心": 6, "天柱": 7, "天任": 8, "天英": 9,
}

# 八神（阳遁顺排，阴遁逆排）
BA_SHEN = ["值符", "螣蛇", "太阴", "六合", "白虎", "玄武", "九地", "九天"]

# 天干
TIAN_GAN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
DI_ZHI = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

# 三奇六仪排列
# 阳遁顺排，阴遁逆排
# 戊己庚辛壬癸丁丙乙
SAN_QI_LIU_YI = ["戊", "己", "庚", "辛", "壬", "癸", "丁", "丙", "乙"]

# 六甲旬首
LIU_JIA_XUN_SHOU = {
    "甲子": "戊", "甲戌": "己", "甲申": "庚",
    "甲午": "辛", "甲辰": "壬", "甲寅": "癸",
}

# 节气与阴阳遁局数
# 阳遁: 冬至到夏至前
# 阴遁: 夏至到冬至前
JIEQI_JU = {
    "冬至":  (1, "阳"), "小寒":  (2, "阳"), "大寒":  (3, "阳"),
    "立春":  (8, "阳"), "雨水":  (9, "阳"), "惊蛰":  (1, "阳"),
    "春分":  (3, "阳"), "清明":  (4, "阳"), "谷雨":  (5, "阳"),
    "立夏":  (4, "阳"), "小满":  (5, "阳"), "芒种":  (6, "阳"),
    "夏至":  (9, "阴"), "小暑":  (8, "阴"), "大暑":  (7, "阴"),
    "立秋":  (2, "阴"), "处暑":  (1, "阴"), "白露":  (9, "阴"),
    "秋分":  (7, "阴"), "寒露":  (6, "阴"), "霜降":  (5, "阴"),
    "立冬":  (6, "阴"), "小雪":  (5, "阴"), "大雪":  (4, "阴"),
}


# ============================================================================
# 数据模型
# ============================================================================

@dataclass
class GongPan:
    """宫位盘信息"""
    num: int             # 宫数 1-9
    name: str            # 宫名: 坎/坤/震/巽/中/乾/兑/艮/离
    wuxing: str          # 五行
    direction: str       # 方位
    di_gan: str = ""     # 地盘天干
    tian_gan: str = ""   # 天盘天干
    men: str = ""        # 八门
    xing: str = ""       # 九星
    shen: str = ""       # 八神
    tiangan_pan: str = "" # 天盘天干


@dataclass
class QimenChart:
    """奇门遁甲排盘"""
    # 时间
    year: int; month: int; day: int; hour: int; minute: int
    year_gan: str; year_zhi: str
    month_gan: str; month_zhi: str
    day_gan: str; day_zhi: str
    hour_gan: str; hour_zhi: str
    
    # 局
    yin_yang: str        # "阳" / "阴"
    ju_num: int          # 局数 1-9
    
    # 旬首
    xun_shou: str        # 如 "甲子戊"
    zhi_fu: str          # 值符星
    zhi_shi: str         # 值使门
    
    # 九宫
    gongs: Dict[int, GongPan] = field(default_factory=dict)


# ============================================================================
# 核心引擎
# ============================================================================

class QimenEngine:
    """奇门遁甲排盘引擎"""

    # ── 四柱计算 ──

    @staticmethod
    def _get_year_ganzhi(year: int) -> Tuple[str, str]:
        gan_idx = (year - 4) % 10
        zhi_idx = (year - 4) % 12
        return TIAN_GAN[gan_idx], DI_ZHI[zhi_idx]

    @staticmethod
    def _get_month_ganzhi(year: int, month: int, day: int) -> Tuple[str, str]:
        """获取月干支（简化：按节气估算）"""
        year_gan = QimenEngine._get_year_ganzhi(year)[0]
        gan_start = TIAN_GAN.index(year_gan)
        # 甲己→丙寅, 乙庚→戊寅, 丙辛→庚寅, 丁壬→壬寅, 戊癸→甲寅
        gan_offset = (gan_start % 5) * 2 + 2
        month_gan_idx = (gan_offset + month - 1) % 10
        month_zhi_idx = (2 + month - 1) % 12  # 寅月为正月
        return TIAN_GAN[month_gan_idx], DI_ZHI[month_zhi_idx]

    @staticmethod
    def _get_day_ganzhi(year: int, month: int, day: int) -> Tuple[str, str]:
        """获取日干支（简化计算）"""
        # 以2000年1月1日为甲子日基准
        # 计算距2000.1.1的天数
        days = 0
        for y in range(2000, year):
            if (y % 4 == 0 and y % 100 != 0) or (y % 400 == 0):
                days += 366
            else:
                days += 365
        
        month_days = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        if (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0):
            month_days[2] = 29
        
        for m in range(1, month):
            days += month_days[m]
        days += day - 1
        
        gan_idx = days % 10
        zhi_idx = days % 12
        return TIAN_GAN[gan_idx], DI_ZHI[zhi_idx]

    @staticmethod
    def _get_hour_ganzhi(day_gan: str, hour: int) -> Tuple[str, str]:
        """根据日干和时辰获取时干支"""
        gan_idx = TIAN_GAN.index(day_gan)
        hour_zhi_idx = (hour + 1) // 2 % 12
        # 子时天干: 甲己→甲子, 乙庚→丙子, 丙辛→戊子, 丁壬→庚子, 戊癸→壬子
        zi_gan = (gan_idx % 5) * 2
        hour_gan_idx = (zi_gan + hour_zhi_idx) % 10
        return TIAN_GAN[hour_gan_idx], DI_ZHI[hour_zhi_idx]

    # ── 定局 ──

    @classmethod
    def _get_ju(cls, month: int, day: int) -> Tuple[int, str]:
        """
        根据公历日期确定阴阳遁和局数（简化版）
        """
        # 节气近似日期（简化处理）
        jieqi_dates = [
            (1, 6, "小寒"), (1, 21, "大寒"), (2, 4, "立春"), (2, 19, "雨水"),
            (3, 6, "惊蛰"), (3, 21, "春分"), (4, 5, "清明"), (4, 20, "谷雨"),
            (5, 6, "立夏"), (5, 21, "小满"), (6, 6, "芒种"), (6, 22, "夏至"),
            (7, 7, "小暑"), (7, 23, "大暑"), (8, 8, "立秋"), (8, 23, "处暑"),
            (9, 8, "白露"), (9, 23, "秋分"), (10, 8, "寒露"), (10, 24, "霜降"),
            (11, 8, "立冬"), (11, 22, "小雪"), (12, 7, "大雪"), (12, 22, "冬至"),
        ]
        
        # 找到当前日期所属的节气区间
        date_val = month * 100 + day
        jieqi_idx = 0
        for i, (m, d, _) in enumerate(jieqi_dates):
            if date_val >= m * 100 + d:
                jieqi_idx = i
            else:
                break
        
        jieqi_name = jieqi_dates[jieqi_idx % 24][2]
        ju_num, yin_yang = JIEQI_JU.get(jieqi_name, (1, "阳"))
        return ju_num, yin_yang

    # ── 排盘 ──

    @classmethod
    def _get_xun_shou(cls, hour_zhi: str) -> str:
        """根据时支获取旬首"""
        zhi_idx = DI_ZHI.index(hour_zhi)
        # 时支在旬中的位置
        xun_start_idx = (zhi_idx // 10) * 10  # 旬首地支
        xun_zhi = DI_ZHI[xun_start_idx]
        return f"甲{xun_zhi}"

    @classmethod
    def _get_zhi_fu_xing(cls, xun_shou: str) -> str:
        """根据旬首找值符星"""
        # 六甲遁于六仪
        xun_gan = LIU_JIA_XUN_SHOU.get(xun_shou, "戊")
        # 在地盘找到该天干所在宫位
        return xun_gan

    @classmethod
    def _get_zhi_shi_men(cls, xun_shou: str) -> str:
        """根据旬首找值使门"""
        zhi = xun_shou[1]  # 取地支
        zhi_idx = DI_ZHI.index(zhi)
        # 从旬首地支所在宫数，推算值使门
        men_map = {0: "休", 1: "死", 2: "伤", 3: "杜", 4: "开", 5: "惊", 6: "生", 7: "景"}
        return men_map.get(zhi_idx % 8, "休")

    @classmethod
    def _pai_di_pan(cls, ju_num: int, yin_yang: str) -> Dict[int, str]:
        """
        排地盘（三奇六仪）
        阳遁顺排: 戊1→己2→庚3→辛4→壬5→癸6→丁7→丙8→乙9
        阴遁逆排: 戊1→乙9→丙8→丁7→癸6→壬5→辛4→庚3→己2
        """
        di_pan = {}
        if yin_yang == "阳":
            for i, gan in enumerate(SAN_QI_LIU_YI):
                gong = (ju_num - 1 + i) % 9 + 1
                di_pan[gong] = gan
        else:
            for i, gan in enumerate(SAN_QI_LIU_YI):
                gong = (ju_num - 1 - i) % 9 + 1
                di_pan[gong] = gan
        return di_pan

    @classmethod
    def _pai_tian_pan(cls, di_pan: Dict[int, str], hour_gan: str) -> Dict[int, str]:
        """
        排天盘
        时干在地盘哪一宫，该宫的天盘天干就是时干
        """
        # 找出时干在地盘的位置
        zhi_fu_gong = None
        for gong, gan in di_pan.items():
            if gan == hour_gan:
                zhi_fu_gong = gong
                break
        if zhi_fu_gong is None:
            zhi_fu_gong = 1
        
        # 天盘天干与地盘一致（简化）
        return di_pan.copy()

    @classmethod
    def _pai_men(cls, di_pan: Dict[int, str], zhi_shi: str, hour_zhi: str,
                 yin_yang: str) -> Dict[int, str]:
        """排八门"""
        # 值使门落宫
        men_order = ["休", "生", "伤", "杜", "景", "死", "惊", "开"]
        zhi_shi_idx = men_order.index(zhi_shi) if zhi_shi in men_order else 0
        
        hour_zhi_idx = DI_ZHI.index(hour_zhi)
        # 计算值使门落宫（简化）
        if yin_yang == "阳":
            zhishi_gong = (hour_zhi_idx + 1) % 9 or 9
        else:
            zhishi_gong = (9 - hour_zhi_idx) % 9 or 9
        
        men_pan = {}
        for i, men in enumerate(men_order):
            if yin_yang == "阳":
                gong = (zhishi_gong - 1 + i) % 9 + 1
            else:
                gong = (zhishi_gong - 1 - i) % 9 + 1
            men_pan[gong] = men
        
        return men_pan

    @classmethod
    def _pai_xing(cls, di_pan: Dict[int, str], hour_gan: str) -> Dict[int, str]:
        """排九星（天盘）"""
        # 值符星落宫 = 时干落宫
        zhi_fu_gong = 1
        for gong, gan in di_pan.items():
            if gan == hour_gan:
                zhi_fu_gong = gong
                break
        
        xing_order = ["天蓬", "天任", "天冲", "天辅", "天英", "天芮", "天柱", "天心"]
        xing_pan = {}
        for i, xing in enumerate(xing_order):
            gong = (zhi_fu_gong - 1 + i) % 9 + 1
            xing_pan[gong] = xing
        
        return xing_pan

    @classmethod
    def _pai_shen(cls, zhi_fu_gong: int, yin_yang: str) -> Dict[int, str]:
        """排八神"""
        shen_pan = {}
        for i, shen in enumerate(BA_SHEN):
            if yin_yang == "阳":
                gong = (zhi_fu_gong - 1 + i) % 9 + 1
            else:
                gong = (zhi_fu_gong - 1 - i) % 9 + 1
            shen_pan[gong] = shen
        return shen_pan

    # ── 公开接口 ──

    @classmethod
    def calc_chart(cls, year: int, month: int, day: int, hour: int = 0,
                   minute: int = 0) -> QimenChart:
        """完整奇门遁甲排盘"""
        # 1. 排四柱
        year_gan, year_zhi = cls._get_year_ganzhi(year)
        month_gan, month_zhi = cls._get_month_ganzhi(year, month, day)
        day_gan, day_zhi = cls._get_day_ganzhi(year, month, day)
        hour_gan, hour_zhi = cls._get_hour_ganzhi(day_gan, hour)
        
        # 2. 定局
        ju_num, yin_yang = cls._get_ju(month, day)
        
        # 3. 旬首
        xun_shou = cls._get_xun_shou(hour_zhi)
        zhi_fu = cls._get_zhi_fu_xing(xun_shou)
        zhi_shi = cls._get_zhi_shi_men(xun_shou)
        
        # 4. 排地盘
        di_pan = cls._pai_di_pan(ju_num, yin_yang)
        
        # 5. 排天盘
        tian_pan = cls._pai_tian_pan(di_pan, hour_gan)
        
        # 6. 排八门
        men_pan = cls._pai_men(di_pan, zhi_shi, hour_zhi, yin_yang)
        
        # 7. 排九星
        xing_pan = cls._pai_xing(di_pan, hour_gan)
        
        # 8. 排八神
        zhi_fu_gong = 1
        for gong, gan in di_pan.items():
            if gan == hour_gan:
                zhi_fu_gong = gong
                break
        shen_pan = cls._pai_shen(zhi_fu_gong, yin_yang)
        
        # 9. 构建宫位
        gongs = {}
        for num in range(1, 10):
            gong_info = JIU_GONG[num]
            gongs[num] = GongPan(
                num=num,
                name=gong_info["name"],
                wuxing=gong_info["wuxing"],
                direction=gong_info["direction"],
                di_gan=di_pan.get(num, ""),
                tian_gan=tian_pan.get(num, ""),
                men=men_pan.get(num, ""),
                xing=xing_pan.get(num, ""),
                shen=shen_pan.get(num, ""),
            )
        
        return QimenChart(
            year=year, month=month, day=day, hour=hour, minute=minute,
            year_gan=year_gan, year_zhi=year_zhi,
            month_gan=month_gan, month_zhi=month_zhi,
            day_gan=day_gan, day_zhi=day_zhi,
            hour_gan=hour_gan, hour_zhi=hour_zhi,
            yin_yang=yin_yang, ju_num=ju_num,
            xun_shou=xun_shou,
            zhi_fu=zhi_fu, zhi_shi=zhi_shi,
            gongs=gongs,
        )

    @classmethod
    def to_dict(cls, chart: QimenChart) -> Dict[str, Any]:
        """转为字典"""
        return {
            "input": {
                "solar": f"{chart.year}-{chart.month:02d}-{chart.day:02d} {chart.hour:02d}:{chart.minute:02d}",
            },
            "sizhu": {
                "year": f"{chart.year_gan}{chart.year_zhi}",
                "month": f"{chart.month_gan}{chart.month_zhi}",
                "day": f"{chart.day_gan}{chart.day_zhi}",
                "hour": f"{chart.hour_gan}{chart.hour_zhi}",
            },
            "ju": f"{chart.yin_yang}遁{chart.ju_num}局",
            "yin_yang": chart.yin_yang,
            "ju_num": chart.ju_num,
            "xun_shou": chart.xun_shou,
            "zhi_fu": chart.zhi_fu,
            "zhi_shi": chart.zhi_shi,
            "gongs": {
                num: {
                    "name": g.name,
                    "wuxing": g.wuxing,
                    "direction": g.direction,
                    "di_gan": g.di_gan,
                    "tian_gan": g.tian_gan,
                    "men": g.men,
                    "xing": g.xing,
                    "shen": g.shen,
                }
                for num, g in chart.gongs.items()
            },
        }

    @classmethod
    def format_text(cls, chart: QimenChart) -> str:
        """格式化文本输出"""
        d = cls.to_dict(chart)
        lines = []
        lines.append("╔══════════════════════════════════════╗")
        lines.append("║       奇 门 遁 甲 排 盘              ║")
        lines.append("╠══════════════════════════════════════╣")
        lines.append(f"║ 时间: {d['input']['solar']}")
        lines.append(f"║ 四柱: 年{d['sizhu']['year']} 月{d['sizhu']['month']} 日{d['sizhu']['day']} 时{d['sizhu']['hour']}")
        lines.append(f"║ 局: {d['ju']}  旬首: {d['xun_shou']}")
        lines.append(f"║ 值符: {d['zhi_fu']}  值使: {d['zhi_shi']}")
        lines.append("╠══════════════════════════════════════╣")
        
        # 九宫格布局
        layout = [
            (4, 9, 2),
            (3, 5, 7),
            (8, 1, 6),
        ]
        
        for row in layout:
            line_parts = []
            for num in row:
                g = d["gongs"].get(num, {})
                name = g.get("name", "?")
                dg = g.get("di_gan", "?")
                tg = g.get("tian_gan", "?")
                men = g.get("men", "?")
                xing = g.get("xing", "?")
                shen = g.get("shen", "?")
                line_parts.append(f"{name}{tg}{dg} {men[:1]}{xing[:2]}{shen[:2]}")
            lines.append("║ " + " │ ".join(f"{p:12s}" for p in line_parts) + " ║")
        
        lines.append("╚══════════════════════════════════════╝")
        return "\n".join(lines)


# ============================================================================
# 便捷函数
# ============================================================================

def calc_qimen(year: int, month: int, day: int, hour: int = 0,
               minute: int = 0) -> QimenChart:
    """快速排奇门遁甲"""
    return QimenEngine.calc_chart(year, month, day, hour, minute)


__all__ = [
    "QimenEngine", "QimenChart", "GongPan",
    "calc_qimen", "JIU_GONG", "BA_MEN", "JIU_XING", "BA_SHEN",
]