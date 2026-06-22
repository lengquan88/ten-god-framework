#!/usr/bin/env python3
"""
advanced_analysis.py — 十神架构高级分析模块 v1.0.0
=====================================================
阶段二十 20.3：功能深化

功能：
  1. 命例对比分析（compare_cases）— 对比两个命例的五行/格局/十神差异
  2. 批量排盘（batch_bazi）— 一次排多个八字，返回汇总统计
  3. 命运轨迹推演（destiny_trajectory）— 基于大运流年推演人生轨迹

用法：
    from tengod.advanced_analysis import AdvancedAnalyzer
    analyzer = AdvancedAnalyzer()

    # 命例对比
    result = analyzer.compare_cases(record_a_id, record_b_id)

    # 批量排盘
    result = analyzer.batch_bazi([
        {"year": 1990, "month": 6, "day": 15, "hour": 10, "gender": "male"},
        {"year": 1985, "month": 3, "day": 20, "hour": 14, "gender": "female"},
    ])

    # 命运轨迹推演
    result = analyzer.destiny_trajectory(year=1990, month=6, day=15, hour=10, gender="male")
"""

from typing import Any, Dict, List, Optional

from .bazi_analyzer import BaziAnalyzer
from .data_store import get_data_store

__all__ = ["AdvancedAnalyzer"]
__version__ = "1.0.0"


class AdvancedAnalyzer:
    """高级分析器：命例对比、批量排盘、命运轨迹推演"""

    def __init__(self, store=None):
        self._store = store or get_data_store()

    # ─── 命例对比分析 ───────────────────────────────────

    def compare_cases(self, record_a_id: int, record_b_id: int) -> Dict[str, Any]:
        """对比两个命例

        Args:
            record_a_id: 命例A的记录ID
            record_b_id: 命例B的记录ID

        Returns:
            对比结果，包含五行差异、格局差异、十神差异、相似度评分
        """
        record_a = self._get_record(record_a_id)
        record_b = self._get_record(record_b_id)
        if not record_a:
            return {"error": f"命例A (record_id={record_a_id}) 不存在"}
        if not record_b:
            return {"error": f"命例B (record_id={record_b_id}) 不存在"}

        analysis_a = self._get_analysis(record_a)
        analysis_b = self._get_analysis(record_b)

        # 五行对比
        wuxing_a = analysis_a.get("wuxing", {})
        wuxing_b = analysis_b.get("wuxing", {})
        wuxing_compare = self._compare_wuxing(wuxing_a, wuxing_b)

        # 格局对比
        geju_a = self._get_geju_name(record_a)
        geju_b = self._get_geju_name(record_b)
        geju_same = geju_a == geju_b if geju_a and geju_b else False

        # 日主对比
        dm_a = analysis_a.get("day_master", "")
        dm_b = analysis_b.get("day_master", "")
        dm_same = dm_a == dm_b if dm_a and dm_b else False

        # 十神对比
        shigan_a = analysis_a.get("shigan", {})
        shigan_b = analysis_b.get("shigan", {})
        shigan_compare = self._compare_shigan(shigan_a, shigan_b)

        # 相似度评分（0-100）
        similarity = self._calc_similarity(
            wuxing_a, wuxing_b, dm_a, dm_b, geju_a, geju_b
        )

        return {
            "record_a": {
                "id": record_a_id,
                "year": record_a.year,
                "month": record_a.month,
                "day": record_a.day,
                "hour": record_a.hour,
                "gender": record_a.gender,
                "day_master": dm_a,
                "geju": geju_a,
            },
            "record_b": {
                "id": record_b_id,
                "year": record_b.year,
                "month": record_b.month,
                "day": record_b.day,
                "hour": record_b.hour,
                "gender": record_b.gender,
                "day_master": dm_b,
                "geju": geju_b,
            },
            "wuxing_compare": wuxing_compare,
            "geju_same": geju_same,
            "day_master_same": dm_same,
            "shigan_compare": shigan_compare,
            "similarity_score": round(similarity, 2),
            "summary": self._compare_summary(
                dm_a, dm_b, geju_a, geju_b, similarity
            ),
        }

    def _compare_wuxing(self, wa: Dict, wb: Dict) -> Dict[str, Any]:
        """对比五行分布"""
        all_elements = set(list(wa.keys()) + list(wb.keys()))
        diff = {}
        for elem in all_elements:
            va = wa.get(elem, 0)
            vb = wb.get(elem, 0)
            diff[elem] = {
                "a": va,
                "b": vb,
                "diff": va - vb,
            }
        return {
            "a": wa,
            "b": wb,
            "diff": diff,
            "dominant_a": max(wa, key=wa.get) if wa else None,
            "dominant_b": max(wb, key=wb.get) if wb else None,
        }

    def _compare_shigan(self, sa: Dict, sb: Dict) -> Dict[str, Any]:
        """对比十神分布"""
        all_shigan = set(list(sa.keys()) + list(sb.keys()))
        diff = {}
        for s in all_shigan:
            diff[s] = {
                "a": sa.get(s, 0),
                "b": sb.get(s, 0),
            }
        return diff

    def _calc_similarity(
        self, wa: Dict, wb: Dict, dm_a: str, dm_b: str, geju_a: str, geju_b: str
    ) -> float:
        """计算相似度评分（0-100）"""
        score = 0.0
        # 日主相同 +30
        if dm_a and dm_b and dm_a == dm_b:
            score += 30
        # 格局相同 +40
        if geju_a and geju_b and geju_a == geju_b:
            score += 40
        # 五行余弦相似度 * 30
        all_elements = ["金", "木", "水", "火", "土"]
        va = [wa.get(e, 0) for e in all_elements]
        vb = [wb.get(e, 0) for e in all_elements]
        dot = sum(a * b for a, b in zip(va, vb))
        norm_a = sum(a * a for a in va) ** 0.5
        norm_b = sum(b * b for b in vb) ** 0.5
        if norm_a > 0 and norm_b > 0:
            cosine = dot / (norm_a * norm_b)
            score += cosine * 30
        return min(score, 100.0)

    def _compare_summary(
        self, dm_a: str, dm_b: str, geju_a: str, geju_b: str, similarity: float
    ) -> str:
        """生成对比摘要"""
        parts = []
        if dm_a and dm_b:
            if dm_a == dm_b:
                parts.append(f"两命例日主同为{dm_a}")
            else:
                parts.append(f"日主分别为{dm_a}和{dm_b}")
        if geju_a and geju_b:
            if geju_a == geju_b:
                parts.append(f"格局同为{geju_a}")
            else:
                parts.append(f"格局分别为{geju_a}和{geju_b}")
        if similarity >= 70:
            parts.append("相似度较高，命理特征相近")
        elif similarity >= 40:
            parts.append("相似度中等，部分命理特征相似")
        else:
            parts.append("相似度较低，命理特征差异明显")
        return "，".join(parts) + "。"

    # ─── 批量排盘 ───────────────────────────────────────

    def batch_bazi(self, inputs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """批量排盘

        Args:
            inputs: 八字输入列表，每个元素包含 year/month/day/hour/minute/gender

        Returns:
            批量排盘结果，包含每个命例的分析和汇总统计
        """
        results = []
        for i, inp in enumerate(inputs):
            try:
                analyzer = BaziAnalyzer(
                    year=inp["year"],
                    month=inp["month"],
                    day=inp["day"],
                    hour=inp.get("hour", 12),
                    minute=inp.get("minute", 0),
                    is_male=inp.get("gender", "male") == "male",
                )
                report = analyzer.json_report()
                results.append({
                    "index": i,
                    "input": inp,
                    "pillars": analyzer.chart.pillars,
                    "day_master": analyzer.analysis.get("day_master"),
                    "geju": analyzer.analysis.get("geju", {}).get("geju_name") if isinstance(analyzer.analysis.get("geju"), dict) else analyzer.analysis.get("geju"),
                    "wuxing": analyzer.analysis.get("wuxing", {}),
                    "success": True,
                })
            except Exception as e:
                results.append({
                    "index": i,
                    "input": inp,
                    "success": False,
                    "error": str(e),
                })

        # 汇总统计
        successful = [r for r in results if r.get("success")]
        stats = {
            "total": len(inputs),
            "success": len(successful),
            "failed": len(results) - len(successful),
            "day_masters": {},
            "gejus": {},
            "wuxing_totals": {"金": 0, "木": 0, "水": 0, "火": 0, "土": 0},
        }
        for r in successful:
            dm = r.get("day_master", "未知")
            stats["day_masters"][dm] = stats["day_masters"].get(dm, 0) + 1
            geju = r.get("geju", "未知")
            stats["gejus"][geju] = stats["gejus"].get(geju, 0) + 1
            for elem, count in r.get("wuxing", {}).items():
                if elem in stats["wuxing_totals"]:
                    stats["wuxing_totals"][elem] += count

        return {
            "results": results,
            "stats": stats,
        }

    # ─── 命运轨迹推演 ───────────────────────────────────

    def destiny_trajectory(
        self,
        year: int,
        month: int,
        day: int,
        hour: int,
        minute: int = 0,
        gender: str = "male",
        start_age: int = 0,
        end_age: int = 80,
    ) -> Dict[str, Any]:
        """命运轨迹推演（基于大运流年）

        Args:
            year/month/day/hour/minute: 出生时间
            gender: 性别
            start_age: 起始年龄
            end_age: 结束年龄

        Returns:
            轨迹推演结果，包含大运列表、流年列表、人生阶段分析
        """
        analyzer = BaziAnalyzer(
            year=year, month=month, day=day, hour=hour, minute=minute,
            is_male=gender == "male",
        )
        day_master = analyzer.analysis.get("day_master", "")
        wuxing = analyzer.analysis.get("wuxing", {})

        # 生成大运（每10年一运，简化版）
        dayun_list = self._generate_dayun(day_master, wuxing, start_age, end_age, gender)

        # 生成流年（逐年）
        liunian_list = self._generate_liunian(year, start_age, end_age, day_master)

        # 人生阶段分析
        stages = self._analyze_life_stages(dayun_list, day_master)

        return {
            "birth": {
                "year": year, "month": month, "day": day, "hour": hour,
                "gender": gender,
            },
            "day_master": day_master,
            "wuxing": wuxing,
            "dayun": dayun_list,
            "liunian": liunian_list,
            "life_stages": stages,
            "summary": self._trajectory_summary(day_master, dayun_list, stages),
        }

    def _generate_dayun(
        self, day_master: str, wuxing: Dict, start_age: int, end_age: str, gender: str
    ) -> List[Dict[str, Any]]:
        """生成大运列表（简化版，基于五行循环）"""
        # 简化：根据日主五行，生成顺逆大运
        wuxing_order = ["木", "火", "土", "金", "水"]
        dm_element = self._get_dm_element(day_master)
        if dm_element not in wuxing_order:
            return []

        dm_idx = wuxing_order.index(dm_element)
        # 阳男阴女顺排，阴男阳女逆排
        is_yang = day_master in ["甲", "丙", "戊", "庚", "壬"]
        forward = (is_yang and gender == "male") or (not is_yang and gender == "female")

        dayun = []
        current_age = max(start_age, 0)
        # 大运起始年龄（简化：从 5 岁开始）
        dayun_start = 5
        age = dayun_start
        idx = 0

        while age <= end_age:
            if forward:
                elem_idx = (dm_idx + 1 + idx) % 5
            else:
                elem_idx = (dm_idx - 1 - idx) % 5
            elem = wuxing_order[elem_idx]

            # 大运天干地支（简化）
            gan_list = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
            gan = gan_list[(idx * 2) % 10]
            zhi_list = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
            zhi = zhi_list[(idx * 2) % 12]

            # 与日主的关系
            relation = self._wuxing_relation(dm_element, elem)

            dayun.append({
                "index": idx + 1,
                "age_start": age,
                "age_end": age + 9,
                "gan_zhi": gan + zhi,
                "element": elem,
                "relation": relation,
                "favorable": relation in ["比肩", "正印", "偏印", "食神", "正财"],
            })
            age += 10
            idx += 1

        return dayun

    def _generate_liunian(
        self, birth_year: int, start_age: int, end_age: int, day_master: str
    ) -> List[Dict[str, Any]]:
        """生成流年列表"""
        dm_element = self._get_dm_element(day_master)
        gan_list = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
        zhi_list = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
        wuxing_order = ["木", "火", "土", "金", "水"]

        liunian = []
        for age in range(max(start_age, 0), min(end_age + 1, 100)):
            year = birth_year + age
            gan_idx = (year - 4) % 10  # 1984年甲子
            zhi_idx = (year - 4) % 12
            gan = gan_list[gan_idx]
            zhi = zhi_list[zhi_idx]
            gan_elem = wuxing_order[gan_idx % 5]
            relation = self._wuxing_relation(dm_element, gan_elem)

            liunian.append({
                "age": age,
                "year": year,
                "gan_zhi": gan + zhi,
                "element": gan_elem,
                "relation": relation,
            })

        return liunian

    def _analyze_life_stages(self, dayun_list: List, day_master: str) -> List[Dict[str, Any]]:
        """分析人生阶段"""
        stages = []
        for du in dayun_list:
            age_start = du["age_start"]
            age_end = du["age_end"]
            # 阶段命名
            if age_start < 15:
                stage_name = "少年运"
            elif age_start < 25:
                stage_name = "青年运"
            elif age_start < 40:
                stage_name = "壮年运"
            elif age_start < 55:
                stage_name = "中年运"
            else:
                stage_name = "晚年运"

            stages.append({
                "stage": stage_name,
                "age_range": f"{age_start}-{age_end}",
                "dayun": du["gan_zhi"],
                "element": du["element"],
                "relation": du["relation"],
                "favorable": du["favorable"],
                "advice": self._stage_advice(du["relation"], du["favorable"]),
            })
        return stages

    def _stage_advice(self, relation: str, favorable: bool) -> str:
        """阶段建议"""
        if favorable:
            return f"{relation}运，顺势而为，宜进取发展"
        else:
            return f"{relation}运，宜守不宜攻，谨慎行事"

    def _trajectory_summary(
        self, day_master: str, dayun_list: List, stages: List
    ) -> str:
        """轨迹摘要"""
        if not dayun_list:
            return "无法推演命运轨迹"
        favorable_count = sum(1 for du in dayun_list if du["favorable"])
        total = len(dayun_list)
        ratio = favorable_count / total if total else 0
        if ratio >= 0.6:
            trend = "整体运势顺遂，有利大运较多"
        elif ratio >= 0.4:
            trend = "运势起伏平衡，顺逆参半"
        else:
            trend = "整体运势偏逆，需谨慎应对"
        return f"日主{day_master}，{trend}。共推演{total}步大运，其中{favorable_count}步为有利运。"

    # ─── 工具方法 ───────────────────────────────────────

    def _get_record(self, record_id: int):
        """获取八字记录"""
        with self._store._session() as s:
            from .data_store import BaziRecord
            return s.query(BaziRecord).filter_by(id=record_id).first()

    def _get_analysis(self, record) -> Dict:
        """获取记录的分析数据"""
        import json
        if record.analysis_json:
            try:
                return json.loads(record.analysis_json)
            except Exception:
                return {}
        return {}

    def _get_geju_name(self, record) -> str:
        """获取格局名"""
        import json
        if record.geju_json:
            try:
                geju = json.loads(record.geju_json)
                if isinstance(geju, dict):
                    return geju.get("geju_name", "")
                return str(geju)
            except Exception:
                return ""
        return ""

    def _get_dm_element(self, day_master: str) -> str:
        """日主天干转五行"""
        gan_wuxing = {
            "甲": "木", "乙": "木",
            "丙": "火", "丁": "火",
            "戊": "土", "己": "土",
            "庚": "金", "辛": "金",
            "壬": "水", "癸": "水",
        }
        return gan_wuxing.get(day_master, "土")

    def _wuxing_relation(self, dm_element: str, other_element: str) -> str:
        """五行关系（十神简化）"""
        if dm_element == other_element:
            return "比肩"
        relations = {
            ("木", "火"): "食神", ("木", "土"): "偏财", ("木", "金"): "七杀", ("木", "水"): "正印",
            ("火", "土"): "食神", ("火", "金"): "偏财", ("火", "木"): "正印", ("火", "水"): "七杀",
            ("土", "金"): "食神", ("土", "水"): "偏财", ("土", "火"): "正印", ("土", "木"): "七杀",
            ("金", "水"): "食神", ("金", "木"): "偏财", ("金", "土"): "正印", ("金", "火"): "七杀",
            ("水", "木"): "食神", ("水", "火"): "偏财", ("水", "金"): "正印", ("水", "土"): "七杀",
        }
        return relations.get((dm_element, other_element), "偏印")
