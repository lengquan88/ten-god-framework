"""
multi_system_engine.py — 阶段二十二 · 多体系综合分析引擎 v1.0.0
================================================================

整合所有术数体系（八字/紫微/奇门/六爻/七政四余/流年/风水/高级术数），
提供交叉验证、共识判断与综合报告。
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import random

# ============================================================================
# 辅助：安全导入各引擎
# ============================================================================

def _safe_import(module_name: str, class_name: str):
    try:
        mod = __import__(module_name, fromlist=[class_name])
        cls = getattr(mod, class_name, None)
        return cls
    except Exception:
        return None


# ============================================================================
# 数据结构
# ============================================================================

WUXING_SIGNS = ["木", "火", "土", "金", "水"]


@dataclass
class SystemResult:
    system: str
    available: bool = True
    data: Optional[Dict] = None
    error: Optional[str] = None
    summary: str = ""

    def to_dict(self) -> Dict:
        return {
            "system": self.system, "available": self.available,
            "data": self.data, "error": self.error, "summary": self.summary,
        }


@dataclass
class CrossValidation:
    score: int = 50
    level: str = "待观察"
    agreements: List[str] = field(default_factory=list)
    conflicts: List[str] = field(default_factory=list)
    interpretations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class ConsensusFortune:
    overall: str = "平"
    score: int = 50
    key_strengths: List[str] = field(default_factory=list)
    key_risks: List[str] = field(default_factory=list)
    best_timing: List[str] = field(default_factory=list)
    weak_timing: List[str] = field(default_factory=list)
    career: str = ""
    wealth: str = ""
    relationships: str = ""
    health: str = ""

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class ComprehensiveResult:
    birth_info: Dict[str, Any]
    systems: Dict[str, SystemResult]
    cross_validation: CrossValidation
    consensus: ConsensusFortune
    comprehensive_report: str

    def to_dict(self) -> Dict:
        return {
            "birth_info": self.birth_info,
            "systems": {k: v.to_dict() for k, v in self.systems.items()},
            "cross_validation": self.cross_validation.to_dict(),
            "consensus": self.consensus.to_dict(),
            "comprehensive_report": self.comprehensive_report,
        }


# ============================================================================
# 综合分析引擎
# ============================================================================

class ComprehensiveAnalyzer:
    """
    多体系综合分析引擎

    整合体系：八字、紫微斗数、奇门遁甲、六爻卦、流年断语、
              玄空风水、七政四余、高级术数
    """

    def __init__(self):
        self._engines: Dict[str, Any] = {}
        self._init_engines()

    def _init_engines(self):
        for name, (mod, cls) in {
            "bazi": ("tengod.bazi_analyzer", "BaziAnalyzer"),
            "ziwei": ("tengod.ziwei_engine", "ZiweiEngine"),
            "qimen": ("tengod.qimen_engine", "QimenEngine"),
            "liuyao": ("tengod.liuyao_engine", "LiuyaoEngine"),
            "liunian": ("tengod.liunian_judgment", "LiunianJudgmentEngine"),
            "fengshui": ("tengod.fengshui.xuankong", "XuankongEngine"),
            "qizheng": ("tengod.qizheng.engine", "QizhengEngine"),
            "shushu": ("tengod.advanced_shushu", "AdvancedShuShuEngine"),
            "marriage": ("tengod.marriage_engine", "MarriageEngine"),
            "name": ("tengod.name_engine", "NameEngine"),
        }.items():
            cls_obj = _safe_import(mod, cls)
            if cls_obj:
                try:
                    self._engines[name] = cls_obj()
                except Exception:
                    pass

    @staticmethod
    def _extract_yongshen(system: str, data: Any) -> Tuple[List[str], List[str]]:
        yong, ji = [], []
        if not data or not isinstance(data, dict):
            return yong, ji

        if system == "bazi":
            yong_raw = data.get("yongshen", data.get("喜用神", []))
            if isinstance(yong_raw, list):
                yong = [e for e in yong_raw if e in WUXING_SIGNS]

        elif system == "ziwei":
            ming_zhu = data.get("ming_zhu", "")
            if any(s in ming_zhu for s in ["天同", "天梁", "天府", "太阴"]):
                yong = ["水", "金"]
            elif any(s in ming_zhu for s in ["紫微", "武曲", "贪狼"]):
                yong = ["土", "金"]
            elif any(s in ming_zhu for s in ["太阳", "巨门"]):
                yong = ["木", "水"]

        elif system == "liunian":
            if "yongshen" in data and isinstance(data["yongshen"], list):
                yong = [e for e in data["yongshen"] if e in WUXING_SIGNS]

        elif system == "shushu":
            tb = data.get("tieban", {})
            tian_pan = str(tb.get("tian_pan", ""))
            wuxing_map = {"乾": "金", "兑": "金", "离": "火", "震": "木",
                          "巽": "木", "坎": "水", "艮": "土", "坤": "土"}
            for bg, wx in wuxing_map.items():
                if bg in tian_pan:
                    yong.append(wx)
                    break

        return yong[:3], ji[:3]

    def _calc_bazi(self, year, month, day, hour, minute, gender) -> SystemResult:
        try:
            eng_class = _safe_import("tengod.bazi_analyzer", "BaziAnalyzer")
            if not eng_class:
                return SystemResult("八字", False, error="引擎未加载")
            is_male = (gender.lower() in ("male", "m", "男"))
            analyzer = eng_class(year, month, day, hour, minute, is_male)
            chart = analyzer.chart
            data = {
                "pillars": chart.pillars,
                "day_master": chart.day_master,
                "ganzhi_list": chart.ganzhi_list,
                "analysis": analyzer.analysis,
            }
            day_master = chart.day_master or ""
            conclusion = data.get("analysis", {}).get("conclusion", "") or ""
            conclusion = conclusion.split("\n")[0][:30]
            summary = f"日主{day_master}，{conclusion}"
            return SystemResult("八字", True, data=data, summary=summary)
        except Exception as e:
            return SystemResult("八字", False, error=str(e))

    def _calc_ziwei(self, year, month, day, hour, minute, gender) -> SystemResult:
        try:
            eng = self._engines.get("ziwei")
            if not eng:
                return SystemResult("紫微斗数", False, error="引擎未加载")
            result = eng.calc_chart(year, month, day, hour, minute, gender)
            data = result.__dict__ if hasattr(result, "__dict__") else {}
            ming_zhu = data.get("ming_zhu", "")
            summary = f"命主星：{ming_zhu}"
            return SystemResult("紫微斗数", True, data=data, summary=summary)
        except Exception as e:
            return SystemResult("紫微斗数", False, error=str(e))

    def _calc_qimen(self, year, month, day, hour, minute) -> SystemResult:
        try:
            eng = self._engines.get("qimen")
            if not eng:
                return SystemResult("奇门遁甲", False, error="引擎未加载")
            result = eng.calc_chart(year, month, day, hour, minute)
            data = result.__dict__ if hasattr(result, "__dict__") else {}
            summary = str(data.get("pan_type", data.get("type", "奇门")))[:30]
            return SystemResult("奇门遁甲", True, data=data, summary=summary)
        except Exception as e:
            return SystemResult("奇门遁甲", False, error=str(e))

    def _calc_liuyao(self, year, month, day, hour, minute) -> SystemResult:
        try:
            eng = self._engines.get("liuyao")
            if not eng:
                return SystemResult("六爻卦", False, error="引擎未加载")
            yao_types = eng.shake_coins()
            result = eng.calc_gua(yao_types=yao_types, day_ganzhi=None)
            data = result.__dict__ if hasattr(result, "__dict__") else {}
            summary = f"本卦：{data.get('ben_gua_name', '')}"
            return SystemResult("六爻卦", True, data=data, summary=summary)
        except Exception as e:
            return SystemResult("六爻卦", False, error=str(e))

    def _calc_liunian(self, pillars, target_year) -> SystemResult:
        try:
            eng = self._engines.get("liunian")
            if not eng:
                return SystemResult("流年断语", False, error="引擎未加载")
            result = eng.judge_year(pillars, target_year)
            data = asdict(result) if hasattr(result, "__dataclass_fields__") else {}
            score = data.get("score", 0)
            overall = data.get("overall", "平")
            return SystemResult("流年断语", True, data=data,
                              summary=f"评分{score}分，整体{overall}")
        except Exception as e:
            return SystemResult("流年断语", False, error=str(e))

    def _calc_fengshui(self, sitting, facing, year) -> SystemResult:
        try:
            eng = self._engines.get("fengshui")
            if not eng:
                return SystemResult("玄空风水", False, error="引擎未加载")
            result = eng.compute(sitting=sitting, facing=facing, year=year)
            data = asdict(result) if hasattr(result, "__dataclass_fields__") else {}
            best = data.get("analysis", {}).get("overall_best", "")
            summary = f"最佳方位：{best}"
            return SystemResult("玄空风水", True, data=data, summary=summary)
        except Exception as e:
            return SystemResult("玄空风水", False, error=str(e))

    def _calc_qizheng(self, year, month, day, hour, minute) -> SystemResult:
        try:
            eng = self._engines.get("qizheng")
            if not eng:
                return SystemResult("七政四余", False, error="引擎未加载")
            result = eng.compute(year, month, day, hour, minute)
            data = asdict(result) if hasattr(result, "__dataclass_fields__") else {}
            seven_count = len(data.get("seven_planets", {}))
            four_count = len(data.get("four_remainders", {}))
            return SystemResult("七政四余", True, data=data,
                              summary=f"七政{seven_count}星，四余{four_count}星")
        except Exception as e:
            return SystemResult("七政四余", False, error=str(e))

    def _calc_shushu(self, pillars, lunar_month, lunar_day) -> SystemResult:
        try:
            eng = self._engines.get("shushu")
            if not eng:
                return SystemResult("高级术数", False, error="引擎未加载")
            result = eng.compute_all(
                pillars=pillars,
                lunar_month=lunar_month,
                lunar_day=lunar_day,
            )
            methods = list(result.keys())
            return SystemResult("高级术数", True, data=result,
                              summary="包含：" + "、".join(methods))
        except Exception as e:
            return SystemResult("高级术数", False, error=str(e))

    def _calc_name(self, surname: str, given_name: str) -> SystemResult:
        """姓名学分析 — 阶段二十五新增"""
        try:
            from tengod.name_engine import NameEngine
            result = NameEngine.analyze(surname, given_name)
            data = {
                "surname": result.surname,
                "given_name": result.given_name,
                "wuge": {
                    "tian": result.wuge.tian_ge,
                    "ren": result.wuge.ren_ge,
                    "di": result.wuge.di_ge,
                    "wai": result.wuge.wai_ge,
                    "zong": result.wuge.zong_ge,
                },
                "sancai": list(result.sancai),
                "sancai_ji": result.sancai_ji,
                "sancai_desc": result.sancai_desc,
                "overall_score": result.overall_score,
                "overall_grade": result.overall_grade,
                "suggestions": result.suggestions,
            }
            summary = f"五格评分 {result.overall_score}分，{result.overall_grade}；三才{'·'.join(result.sancai)}"
            return SystemResult("姓名学", True, data=data, summary=summary)
        except Exception as e:
            return SystemResult("姓名学", False, error=str(e))

    def _calc_marriage(self, name1: str, bazi1: dict,
                       name2: str, bazi2: dict) -> SystemResult:
        """合婚分析 — 阶段二十五新增"""
        try:
            from tengod.marriage_engine import MarriageEngine
            result = MarriageEngine.analyze(name1, bazi1, name2, bazi2)
            data = {
                "name1": result.name1,
                "name2": result.name2,
                "day_gan1": result.day_gan1,
                "day_gan2": result.day_gan2,
                "nayin": {
                    "nayin1": result.nayin1,
                    "nayin2": result.nayin2,
                    "match": result.nayin_match,
                    "score": result.nayin_score,
                },
                "ri_gan": {
                    "relation": result.ri_gan_he,
                    "score": result.ri_gan_score,
                },
                "dizhi": {
                    "relations": result.zhi_relations,
                    "score": result.zhi_score,
                },
                "wuxing": {
                    "analysis": result.wuxing_bu,
                    "score": result.wuxing_score,
                },
                "shengxiao": {
                    "shengxiao1": result.shengxiao1,
                    "shengxiao2": result.shengxiao2,
                    "score": result.shengxiao_score,
                },
                "overall_score": result.overall_score,
                "overall_grade": result.overall_grade,
                "summary": result.summary,
                "suggestions": result.suggestions,
            }
            summary = f"合婚评分 {result.overall_score}分，{result.overall_grade}"
            return SystemResult("合婚分析", True, data=data, summary=summary)
        except Exception as e:
            return SystemResult("合婚分析", False, error=str(e))

    def _cross_validate(self, systems: Dict[str, SystemResult]) -> CrossValidation:
        agreements: List[str] = []
        conflicts: List[str] = []

        # 喜用神一致性
        yong_collections: Dict[str, List[str]] = {}
        for name, sr in systems.items():
            if sr.available and sr.data:
                yong, _ = self._extract_yongshen(name, sr.data)
                if yong:
                    yong_collections[name] = yong

        if len(yong_collections) >= 2:
            yong_sets = [set(y) for y in yong_collections.values()]
            common = yong_sets[0].intersection(*yong_sets[1:])
            if common:
                agreements.append(f"共识喜用神：{'、'.join(common)}")
            elif len(yong_collections) == 2:
                conflicts.append("喜用神判断不一致（不同体系算法差异，正常现象）")

        # 流年与六爻一致性
        ln = systems.get("流年断语")
        ly = systems.get("六爻卦")
        if ln and ln.available and ly and ly.available:
            ln_ov = ln.data.get("overall", "平") if isinstance(ln.data, dict) else "平"
            ly_gua = ly.data.get("ben_gua_name", "") if isinstance(ly.data, dict) else ""
            good_gua = ["乾为天", "坤为地", "地天泰", "水地比", "风火家人"]
            bad_gua = ["天地否", "坎为水", "火水未济"]
            ly_ov = "吉" if any(g in ly_gua for g in good_gua) else ("凶" if any(g in ly_gua for g in bad_gua) else "平")
            if ln_ov == ly_ov:
                agreements.append(f"流年({ln_ov})与六爻({ly_ov})判断一致")
            else:
                conflicts.append(f"流年({ln_ov})与六爻({ly_ov})判断有差异")

        score = min(100, 50 + len(agreements) * 15 - len(conflicts) * 10)
        level = "一致" if len(agreements) >= 2 else ("矛盾" if len(conflicts) > 2 else "待观察")
        interp = []
        if agreements:
            interp.append("多体系分析一致性较高，可信度强")
        if conflicts:
            interp.append("部分体系判断有差异，建议综合参考")

        return CrossValidation(
            score=max(0, score), level=level,
            agreements=agreements[:5], conflicts=conflicts[:3],
            interpretations=interp[:3],
        )

    def _build_consensus(self, systems: Dict[str, SystemResult],
                         cross: CrossValidation) -> ConsensusFortune:
        scores: List[int] = []

        ln = systems.get("流年断语")
        if ln and ln.available:
            s = ln.data.get("score", 50) if isinstance(ln.data, dict) else 50
            scores.append(s)

        ss = systems.get("高级术数")
        if ss and ss.available:
            shaozi = ss.data.get("shaozi", {}) if isinstance(ss.data, dict) else {}
            s = shaozi.get("total_score", 70) if isinstance(shaozi, dict) else 70
            scores.append(s)

        avg = round(sum(scores) / len(scores)) if scores else 65

        overall_map = {range(80, 101): "大吉", range(65, 80): "吉",
                       range(50, 65): "平", range(35, 50): "凶"}
        overall = next((v for r, v in overall_map.items() if avg in r), "平")

        strengths, risks = [], []
        if ln and ln.available:
            jgmnts = ln.data.get("judgments", []) if isinstance(ln.data, dict) else []
            if jgmnts:
                strengths.append(f"流年：{jgmnts[0][:35]}")
        if ss and ss.available:
            tb = ss.data.get("tieban", {}) if isinstance(ss.data, dict) else {}
            summary = tb.get("summary", "") if isinstance(tb, dict) else ""
            if summary:
                strengths.append(f"铁板：{summary[:35]}")

        best_timing, weak_timing = [], []
        if ln and ln.available:
            best_timing = (ln.data.get("favorable_months", []) if isinstance(ln.data, dict) else [])[:3]
            weak_timing = (ln.data.get("unfavorable_months", []) if isinstance(ln.data, dict) else [])[:3]

        return ConsensusFortune(
            overall=overall, score=avg,
            key_strengths=strengths[:3],
            key_risks=risks[:3],
            best_timing=best_timing,
            weak_timing=weak_timing,
            career="事业稳定发展，宜稳中求进",
            wealth="财运平稳，正财为主",
            relationships="感情关系需要用心经营",
            health="健康良好，注意劳逸结合",
        )

    def _generate_report(self, birth_info: Dict, systems: Dict[str, SystemResult],
                          cross: CrossValidation, consensus: ConsensusFortune) -> str:
        lines = [
            "=" * 56,
            "         中华命理综合分析报告",
            "=" * 56, "",
            "【基础信息】",
            f"  出生：{birth_info.get('year','')}年{birth_info.get('month','')}月"
            f"{birth_info.get('day','')}日 {birth_info.get('hour',0)}:"
            f"{birth_info.get('minute',0):02d}时",
            f"  性别：{birth_info.get('gender','未知')}", "",
            "【各体系分析】",
        ]
        for name, sr in systems.items():
            status = sr.summary if sr.available else f"暂不可用（{sr.error}）"
            lines.append(f"  ▶ {name}：{status}")

        lines.extend(["", "【交叉验证】",
                      f"  一致性：{cross.score}分（{cross.level}）"])
        for a in cross.agreements:
            lines.append(f"  ✓ {a}")
        for c in cross.conflicts:
            lines.append(f"  ✗ {c}")

        lines.extend(["", "【共识运势】",
                      f"  整体：{consensus.overall}（{consensus.score}分）",
                      f"  事业：{consensus.career}",
                      f"  财运：{consensus.wealth}",
                      f"  感情：{consensus.relationships}",
                      f"  健康：{consensus.health}"])

        if consensus.key_strengths:
            lines.append("")
            lines.append("【核心优势】")
            for s in consensus.key_strengths:
                lines.append(f"  ★ {s}")

        if consensus.best_timing:
            lines.append(f"\n【最佳时机】{'、'.join(consensus.best_timing)}")
        if consensus.weak_timing:
            lines.append(f"【需谨慎】{'、'.join(consensus.weak_timing)}")

        lines.extend(["", "=" * 56,
                      "  本报告由 AI 综合多体系算法生成，仅供参考。",
                      "  命运把握在自己手中，祝您前程似锦！",
                      "=" * 56])
        return "\n".join(lines)

    def full_analysis(
        self,
        birth_date: Tuple[int, int, int],
        birth_time: Tuple[int, int],
        gender: str = "male",
        target_year: int = 2026,
        pillars: Optional[Dict[str, str]] = None,
        sitting: str = "北",
        facing: str = "南",
        lunar_month: Optional[int] = None,
        lunar_day: Optional[int] = None,
        name_surname: Optional[str] = None,
        name_given: Optional[str] = None,
        partner_info: Optional[Dict[str, Any]] = None,
    ) -> ComprehensiveResult:
        year, month, day = birth_date
        hour, minute = birth_time

        birth_info = {
            "year": year, "month": month, "day": day,
            "hour": hour, "minute": minute, "gender": gender,
        }

        systems: Dict[str, SystemResult] = {}

        # 八字
        systems["八字"] = self._calc_bazi(year, month, day, hour, minute, gender)

        # 提取四柱
        if pillars is None:
            bd = systems["八字"].data
            p = (bd.get("pillars", {}) or {}) if bd else {}
            pillars = {
                "year": p.get("year", ""),
                "month": p.get("month", ""),
                "day": p.get("day", ""),
                "hour": p.get("hour", ""),
            }

        systems["紫微斗数"] = self._calc_ziwei(year, month, day, hour, minute, gender)
        systems["奇门遁甲"] = self._calc_qimen(year, month, day, hour, minute)
        systems["六爻卦"] = self._calc_liuyao(year, month, day, hour, minute)
        systems["流年断语"] = self._calc_liunian(pillars, target_year)
        systems["玄空风水"] = self._calc_fengshui(sitting, facing, target_year)
        systems["七政四余"] = self._calc_qizheng(year, month, day, hour, minute)
        systems["高级术数"] = self._calc_shushu(
            pillars, lunar_month or month, lunar_day or day)

        # 阶段二十五新增：姓名学分析（若提供姓名参数）
        if name_surname and name_given:
            systems["姓名学"] = self._calc_name(name_surname, name_given)

        # 阶段二十五新增：合婚分析（若提供 partner_info）
        if partner_info:
            # 提取自己的八字信息供合婚使用
            bazi_self = {}
            if systems.get("八字", None) and systems["八字"].data:
                bazi_self = systems["八字"].data or {}
            bazi_partner = partner_info.get("bazi", {}) or {}
            p_name1 = partner_info.get("name1", "本人") or "本人"
            p_name2 = partner_info.get("name2", "对方") or "对方"
            systems["合婚分析"] = self._calc_marriage(
                p_name1, bazi_self, p_name2, bazi_partner
            )

        cross = self._cross_validate(systems)
        consensus = self._build_consensus(systems, cross)
        report = self._generate_report(birth_info, systems, cross, consensus)

        return ComprehensiveResult(
            birth_info=birth_info,
            systems=systems,
            cross_validation=cross,
            consensus=consensus,
            comprehensive_report=report,
        )
