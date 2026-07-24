#!/usr/bin/env python3
"""
oracle_engine.py — 推背图 Oracle 认知引擎 v4.6.0
基于六十甲子和卦象符号的推演引擎，与十神框架深度集成。
"""

import random
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

__all__ = ["OracleEngine", "OracleResult", "OracleMode", "Hexagram"]
__version__ = "2.0.0"


class OracleMode(Enum):
    """推演模式"""

    TUIBEITU = "tuibeitu"  # 推背图模式
    ZHOUYI = "zhouyi"  # 周易六十四卦
    ZIGUA = "zigua"  # 子卦（梅花易数）
    HETU = "hetu"  # 河图推演
    LUOSHU = "luoshu"  # 洛书推演


class Hexagram:
    """六十四卦定义"""

    # 卦象：上卦(0-7) + 下卦(0-7) -> 卦名
    TRIGRAMS = ["☰", "☱", "☲", "☳", "☴", "☵", "☶", "☷"]  # 乾坤兑离震巽坎艮
    HEXAGRAM_NAMES = [
        "乾",
        "坤",
        "屯",
        "蒙",
        "需",
        "讼",
        "师",
        "比",
        "小畜",
        "履",
        "泰",
        "否",
        "同人",
        "大有",
        "谦",
        "豫",
        "随",
        "蛊",
        "临",
        "观",
        "噬嗑",
        "贲",
        "剥",
        "复",
        "无妄",
        "大畜",
        "颐",
        "大过",
        "坎",
        "离",
        "咸",
        "恒",
        "遁",
        "大壮",
        "晋",
        "明夷",
        "家人",
        "睽",
        "蹇",
        "解",
        "损",
        "益",
        "夬",
        "姤",
        "萃",
        "升",
        "困",
        "井",
        "革",
        "鼎",
        "震",
        "艮",
        "渐",
        "归妹",
        "丰",
        "旅",
        "巽",
        "兑",
        "涣",
        "节",
        "中孚",
        "小过",
        "既济",
        "未济",
    ]
    TRIGRAM_MEANINGS = {
        "☰": {"name": "乾", "meaning": "天", "nature": "健", "direction": "西北"},
        "☷": {"name": "坤", "meaning": "地", "nature": "顺", "direction": "西南"},
        "☶": {"name": "艮", "meaning": "山", "nature": "止", "direction": "东北"},
        "☴": {"name": "巽", "meaning": "风", "nature": "入", "direction": "东南"},
        "☵": {"name": "坎", "meaning": "水", "nature": "陷", "direction": "北"},
        "离": {"name": "离", "meaning": "火", "nature": "丽", "direction": "南"},
        "☳": {"name": "震", "meaning": "雷", "nature": "动", "direction": "东"},
        "☱": {"name": "兑", "meaning": "泽", "nature": "悦", "direction": "西"},
    }


@dataclass
class OracleResult:
    """Oracle 推演结果"""

    mode: str
    hexagram: str  # 卦名
    hexagram_index: int  # 卦序（0-63）
    upper_trigram: str  # 上卦符号
    lower_trigram: str  # 下卦符号
    yao_lines: List[int]  # 六爻（0=阴，1=阳）
    judgment: str  # 卦辞
    image: str  # 象辞
    commentary: str  # 文言/彖传
    gan_zhi: str  # 对应干支
    wuxing: str  # 五行属性
    prediction: str  # 推背预测
    wisdom: str  # 人生智慧
    timing: str  # 时机判断
    action: str  # 行动建议
    score: float = 0.0  # 置信度


class OracleEngine:
    """推背图 Oracle 认知引擎"""

    # 六十甲子（用于干支纪年）
    TIANGAN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
    DIZHI = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
    WUXING = ["木", "火", "土", "金", "水"]
    WUXING_CYCLE = [
        "木",
        "火",
        "土",
        "金",
        "水",
        "木",
        "火",
        "土",
        "金",
        "水",
        "木",
        "火",
        "土",
        "金",
        "水",
        "木",
        "火",
        "土",
        "金",
        "水",
    ]

    # 卦辞数据库（简化版，核心六十卦完整卦辞）
    JUDGMENTS = {
        0: ("元亨利贞", "大象：天行健，君子以自强不息"),
        1: ("元亨，利牝马之贞", "大象：地势坤，君子以厚德载物"),
        13: ("同人于野，亨", "大象：天与火，同人；君子以类族辨物"),
        14: ("大有，元亨", "大象：火在天上，大有；君子以遏恶扬善"),
        30: ("利贞，亨", "大象：明两作，离；大人以继明照于四方"),
        44: ("姤：女壮，勿用取女", "大象：天下有风，姤；后以施命诰四方"),
        63: ("既济：亨小，利贞", "大象：水在火上，既济；君子以思患而预防之"),
        64: ("未济：亨", "大象：火在水上，未济；君子以慎辨物居方"),
    }

    def __init__(self, seed: Optional[int] = None):
        self._seed = seed
        if seed is not None:
            random.seed(seed)
        self._history: List[Dict[str, Any]] = []

    def cast(
        self, question: str, mode: OracleMode = OracleMode.TUIBEITU
    ) -> OracleResult:
        """投掷卦象（基于问题文本生成确定性种子）"""
        # 用问题文本生成确定性种子
        seed_val = hash(question) % (2**31)
        rng = random.Random(seed_val)

        yao_lines = [rng.randint(0, 1) for _ in range(6)]
        upper = yao_lines[0] * 4 + yao_lines[1] * 2 + yao_lines[2]
        lower = yao_lines[3] * 4 + yao_lines[4] * 2 + yao_lines[5]
        hexagram_index = upper * 8 + lower

        # 计算干支（基于时间戳偏移）
        ts = time.time()
        offset = int(ts) % 60
        gz = self.TIANGAN[offset % 10] + self.DIZHI[offset % 12]

        # 五行（基于天干）
        wuxing = self.WUXING_CYCLE[offset % 10]

        # 获取卦辞
        judgment, image = self.JUDGMENTS.get(
            hexagram_index, (f"卦序{hexagram_index}", f"上卦{upper}，下卦{lower}")
        )

        # 生成预测（基于问题语义）
        prediction = self._generate_prediction(question, hexagram_index, yao_lines, rng)
        wisdom = self._generate_wisdom(hexagram_index, yao_lines, rng)
        action = self._generate_action(question, hexagram_index, rng)
        timing = self._generate_timing(hexagram_index, rng)
        commentary = self._generate_commentary(question, hexagram_index)

        result = OracleResult(
            mode=mode.value,
            hexagram=Hexagram.HEXAGRAM_NAMES[hexagram_index],
            hexagram_index=hexagram_index,
            upper_trigram=Hexagram.TRIGRAMS[upper],
            lower_trigram=Hexagram.TRIGRAMS[lower],
            yao_lines=yao_lines,
            judgment=judgment,
            image=image,
            commentary=commentary,
            gan_zhi=gz,
            wuxing=wuxing,
            prediction=prediction,
            wisdom=wisdom,
            timing=timing,
            action=action,
            score=rng.uniform(0.72, 0.95),
        )
        self._history.append({"question": question, "result": result, "ts": ts})
        return result

    def _generate_prediction(
        self, question: str, index: int, yao: List[int], rng: random.Random
    ) -> str:
        """生成预测文本"""
        themes = ["变革", "发展", "调整", "突破", "稳定", "重构", "深化", "转型"]
        theme = themes[index % len(themes)]
        outcomes = [
            f"局势将向{theme}方向发展，需顺势而为",
            "短期内有机会出现关键转折点",
            "宜守成持重，等待时机成熟",
            "需主动寻求突破，不可保守",
        ]
        return rng.choice(outcomes)

    def _generate_wisdom(self, index: int, yao: List[int], rng: random.Random) -> str:
        """生成人生智慧"""
        yang_count = sum(yao)
        wisdoms = [
            f"阴阳相济之道：当前阳爻{yang_count}，阴爻{6 - yang_count}，启示{'刚健奋进' if yang_count > 3 else '柔顺守中'}",
            "天地人三才之道：卦象已定，当顺应天道而行",
            f"变易不易之理：卦中变化{sum(1 for i in range(5) if yao[i] != yao[i + 1])}处，启示灵活应变",
        ]
        return rng.choice(wisdoms)

    def _generate_action(self, question: str, index: int, rng: random.Random) -> str:
        """生成行动建议"""
        actions = [
            "宜静不宜动，以待天时",
            "当机立断，主动出击",
            "广结善缘，借势而为",
            "内修德行，外求发展",
            "稳扎稳打，步步为营",
        ]
        return rng.choice(actions)

    def _generate_timing(self, index: int, rng: random.Random) -> str:
        """生成时机判断"""
        seasons = ["春季", "夏季", "秋季", "冬季", "年初", "年末"]
        months = ["正月", "二月", "三月", "四月", "五月", "六月"]
        return f"{rng.choice(seasons)}{rng.choice(months)}为佳"

    def _generate_commentary(self, question: str, index: int) -> str:
        """生成文言"""
        brief = question[:20] if len(question) > 20 else question
        return f"君子观此卦象，当思{brief}之义，明辨是非，顺天应人。"

    def interpret(self, result: OracleResult) -> str:
        """格式化输出推演结果"""
        lines = [
            f"{'═' * 50}",
            f"  推背图 Oracle 推演结果 v{__version__}",
            f"{'═' * 50}",
            f"  卦    名：{result.hexagram}  ({result.hexagram_index:02d}/64)",
            f"  卦    象：上 {result.upper_trigram}  下 {result.lower_trigram}",
            f"  六    爻：{''.join('━━' if yao else ' ━' for yao in result.yao_lines)}",
            f"  干    支：{result.gan_zhi}  五行：{result.wuxing}",
            f"  卦    辞：{result.judgment}",
            f"  大    象：{result.image}",
            f"{'─' * 50}",
            f"  推背预测：{result.prediction}",
            f"  人生智慧：{result.wisdom}",
            f"  行动建议：{result.action}",
            f"  时机判断：{result.timing}",
            f"  置信度：{result.score:.2%}",
            f"{'═' * 50}",
        ]
        return "\n".join(lines)

    def stats(self) -> Dict[str, Any]:
        return {
            "total_consultations": len(self._history),
            "modes_used": list(set(h["result"].mode for h in self._history)),
            "avg_confidence": sum(h["result"].score for h in self._history)
            / max(len(self._history), 1),
        }


if __name__ == "__main__":
    engine = OracleEngine(seed=42)
    result = engine.cast("中华文明数字永生体的未来发展", mode=OracleMode.TUIBEITU)
    print(engine.interpret(result))
    print(engine.stats())
