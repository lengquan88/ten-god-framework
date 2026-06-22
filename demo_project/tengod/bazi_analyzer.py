"""
bazi_analyzer.py — 八字综合分析报告
= = = = = = = = = = = = = = = = = = =
整合 bazi_calculator + dayun_liunian + divination_engine
产出结构化分析报告：
  - 四柱信息
  - 五行强弱统计
  - 十神分布
  - 地支关系（合冲害破刑）
  - 大运与流年摘要
  - 自然语言分析结论
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List

from .bazi_calculator import BaziChart
from .dayun_liunian import (
    calc_dayun, calc_liunian_range,
    derive_shigan, derive_zhi_shigan, GAN_WUXING, GAN_YINYANG,
)


@dataclass
class BaziAnalyzer:
    year: int
    month: int
    day: int
    hour: int = 12
    minute: int = 0
    is_male: bool = True
    longitude: float = 120.0
    latitude: float = 39.9

    # 分析结果
    chart: BaziChart = field(default=None)  # type: ignore[assignment]
    analysis: Dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.chart = BaziChart(self.year, self.month, self.day,
                                self.hour, self.minute,
                                self.longitude, self.latitude)
        self._analyze()

    # ---- 核心分析 ----
    def _analyze(self) -> None:
        pillars = self.chart.pillars
        day_master = self.chart.day_master

        # 1. 提取每柱天干地支
        stems = [pillars[k][0] for k in ['year', 'month', 'day', 'hour']]
        branches = [pillars[k][1] for k in ['year', 'month', 'day', 'hour']]

        # 2. 五行分布（天干+地支主气）
        wuxing_counter: Counter = Counter()
        for g in stems:
            wuxing_counter[GAN_WUXING[g]] += 1
        for z in branches:
            # 简化：地支本气（第一个藏干）
            zhi_main_gan = {'子': '癸', '丑': '己', '寅': '甲', '卯': '乙',
                             '辰': '戊', '巳': '丙', '午': '丁', '未': '己',
                             '申': '庚', '酉': '辛', '戌': '戊', '亥': '壬'}
            wuxing_counter[GAN_WUXING[zhi_main_gan[z]]] += 1

        # 3. 十神分布（天干）
        shigan_map = {
            'year_gan': derive_shigan(day_master, stems[0]),
            'month_gan': derive_shigan(day_master, stems[1]),
            'day_gan': derive_shigan(day_master, stems[2]),
            'hour_gan': derive_shigan(day_master, stems[3]),
        }
        shigan_counter: Counter = Counter(shigan_map.values())

        # 4. 地支关系（合冲害破刑）
        branch_relations = self._branch_relations(branches)

        # 5. 大运
        dayuns = calc_dayun(self.year, stems[0], pillars['month'],
                              self.is_male, start_age_offset=0)

        # 6. 流年（前后各5年+当前）
        current_year = self.year
        liunians = calc_liunian_range(current_year - 3, current_year + 10, day_master)

        self.analysis = {
            'pillars': pillars,
            'day_master': day_master,
            'stems': stems,
            'branches': branches,
            'wuxing': dict(wuxing_counter),
            'wuxing_score': self._score_wuxing(wuxing_counter),
            'shigan_map': shigan_map,
            'shigan_count': dict(shigan_counter),
            'branch_relations': branch_relations,
            'dayuns': dayuns,
            'liunians': liunians,
            'conclusion': self._conclusion(day_master, wuxing_counter, shigan_counter, branch_relations),
        }

    # ---- 地支关系 ----
    def _branch_relations(self, branches: List[str]) -> Dict[str, List]:
        """
        简化版地支关系识别：
          - 六合: 子丑, 寅亥, 卯戌, 辰酉, 巳申, 午未
          - 三合局: 申子辰(合水), 亥卯未(合木), 寅午戌(合火), 巳酉丑(合金)
          - 六冲: 子午, 丑未, 寅申, 卯酉, 辰戌, 巳亥
          - 相刑: 子卯, 丑戌未(三刑), 寅巳申(三刑), 辰辰, 午午, 酉酉, 亥亥(自刑)
          - 六害: 子未, 丑午, 寅巳, 卯辰, 申亥, 酉戌
          - 六破: 子酉, 丑辰, 寅午, 卯午, 申巳, 亥未 （简化）
        """
        liu_he = [('子', '丑'), ('寅', '亥'), ('卯', '戌'), ('辰', '酉'), ('巳', '申'), ('午', '未')]
        san_he = [('申', '子', '辰'), ('亥', '卯', '未'), ('寅', '午', '戌'), ('巳', '酉', '丑')]
        liu_chong = [('子', '午'), ('丑', '未'), ('寅', '申'), ('卯', '酉'), ('辰', '戌'), ('巳', '亥')]
        liu_hai = [('子', '未'), ('丑', '午'), ('寅', '巳'), ('卯', '辰'), ('申', '亥'), ('酉', '戌')]
        liu_po = [('子', '酉'), ('丑', '辰'), ('寅', '午'), ('巳', '申'), ('午', '亥'), ('未', '戌')]
        san_xing = [('子', '卯'), ('寅', '巳'), ('巳', '申'), ('丑', '戌'), ('戌', '未')]

        branch_set = set(branches)
        relations = {
            '六合': [], '三合': [], '六冲': [], '六害': [], '六破': [], '相刑': [],
        }

        for pair in liu_he:
            if set(pair).issubset(branch_set):
                relations['六合'].append('+'.join(pair))
        for tri in san_he:
            if set(tri).issubset(branch_set):
                relations['三合'].append('+'.join(tri))
        for pair in liu_chong:
            if set(pair).issubset(branch_set):
                relations['六冲'].append('+'.join(pair))
        for pair in liu_hai:
            if set(pair).issubset(branch_set):
                relations['六害'].append('+'.join(pair))
        for pair in liu_po:
            if set(pair).issubset(branch_set):
                relations['六破'].append('+'.join(pair))
        for pair in san_xing:
            if set(pair).issubset(branch_set):
                relations['相刑'].append('+'.join(pair))
        # 自刑
        zi_xing = {'辰', '午', '酉', '亥'}
        for z in branches:
            if z in zi_xing:
                relations['相刑'].append(z + '(自刑)')

        return relations

    # ---- 五行打分 ----
    def _score_wuxing(self, counter: Counter) -> Dict[str, str]:
        total = sum(counter.values()) or 1
        scores = {}
        for wx in ['木', '火', '土', '金', '水']:
            count = counter.get(wx, 0)
            pct = count / total * 100
            level = '旺' if pct >= 30 else ('中和' if pct >= 15 else ('弱' if pct > 0 else '缺'))
            scores[wx] = f'{count}个 ({pct:.0f}%) - {level}'
        return scores

    # ---- 自然语言结论 ----
    def _conclusion(self, day_master: str, wuxing: Counter,
                     shigan: Counter, relations: Dict) -> str:
        lines = []
        # 日主概述
        lines.append(f'日主为【{day_master}】，属{GAN_YINYANG[day_master]}{GAN_WUXING[day_master]}。')

        # 五行判断
        sorted_wx = wuxing.most_common()
        if sorted_wx:
            top = sorted_wx[0][0]
            missing = [wx for wx in ['木', '火', '土', '金', '水'] if wuxing.get(wx, 0) == 0]
            lines.append(f'八字中五行【{top}】最旺。')
            if missing:
                lines.append(f'五行缺少：{"、".join(missing)}，可考虑通过喜用神调和。')

        # 十神判断
        good = shigan.get('正官', 0) + shigan.get('正印', 0) + shigan.get('正财', 0) + \
               shigan.get('比肩', 0) + shigan.get('食神', 0)
        strong = shigan.get('七杀', 0) + shigan.get('伤官', 0) + shigan.get('劫财', 0) + \
                shigan.get('偏财', 0) + shigan.get('偏印', 0)
        if good > strong:
            lines.append('十神以善神为主，整体格局温和稳固。')
        elif strong > good:
            lines.append('十神中凶神偏多，行动力与决断力较强，但需注意人际关系。')

        # 地支关系
        rel_desc = []
        for k, v in relations.items():
            if v:
                rel_desc.append(f'{k}({"、".join(v)})')
        if rel_desc:
            lines.append(f'地支关系：{"；".join(rel_desc)}。')

        return ' '.join(lines)

    # ---- 报告输出 ----
    def text_report(self) -> str:
        a = self.analysis
        lines = []
        lines.append('=' * 60)
        lines.append(f'八字综合分析报告 — {self.year}-{self.month:02d}-{self.day:02d} '
                      f'{self.hour:02d}:{self.minute:02d}')
        lines.append(f'真太阳时: {self.chart.true_hour:02d}:{self.chart.true_minute:02d} '
                      f'(经度 {self.longitude}°)')
        lines.append('-' * 60)
        lines.append('四柱:')
        lines.append(f'  年柱: {a["pillars"]["year"]} ({a["shigan_map"]["year_gan"]})')
        lines.append(f'  月柱: {a["pillars"]["month"]} ({a["shigan_map"]["month_gan"]})')
        lines.append(f'  日柱: {a["pillars"]["day"]} (日主 {a["day_master"]})')
        lines.append(f'  时柱: {a["pillars"]["hour"]} ({a["shigan_map"]["hour_gan"]})')
        lines.append('-' * 60)
        lines.append('五行分布:')
        for wx in ['木', '火', '土', '金', '水']:
            lines.append(f'  {wx}: {a["wuxing_score"][wx]}')
        lines.append('-' * 60)
        lines.append('十神分布:')
        for sg, cnt in sorted(a['shigan_count'].items(), key=lambda x: -x[1]):
            lines.append(f'  {sg}: {cnt}')
        lines.append('-' * 60)
        lines.append('地支关系:')
        has_relation = False
        for k, v in a['branch_relations'].items():
            if v:
                has_relation = True
                lines.append(f'  {k}: {", ".join(v)}')
        if not has_relation:
            lines.append('  (无显著合冲害破刑关系)')
        lines.append('-' * 60)
        lines.append('大运（每步10年，起运=0岁）:')
        for du in a['dayuns'][:5]:
            gan_shigan = derive_shigan(a['day_master'], du['pillar'][0])
            lines.append(f'  {du["age"]:>3d}-{du["age"]+9:>3d}岁 '
                          f'({du["start_year"]:>4d}-{du["start_year"]+9:>4d}) '
                          f'{du["pillar"]} [{gan_shigan}]')
        lines.append('-' * 60)
        lines.append('近期流年:')
        for ln in a['liunians'][:8]:
            lines.append(f'  {ln["year"]:>4d}年: {ln["pillar"]} '
                          f'[{ln["gan_shigan"]}]')
        lines.append('-' * 60)
        lines.append('分析结论:')
        lines.append(f'  {a["conclusion"]}')
        lines.append('=' * 60)
        return '\n'.join(lines)

    def json_report(self) -> Dict:
        return self.analysis


if __name__ == '__main__':
    a = BaziAnalyzer(1990, 6, 15, 10, 30, is_male=True, longitude=116.4)
    print(a.text_report())
