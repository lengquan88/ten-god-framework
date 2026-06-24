#!/usr/bin/env python3
"""
test_v21_performance.py — v2.1 新模块性能测试
覆盖：真太阳时计算、五行旺衰、可视化生成、八字排盘 性能基准
"""
import os
import sys
import time
import statistics
from datetime import datetime

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from tengod.bazi_calculator import BaziChart, calc_bazi
from tengod.solar_time import (
    SolarTimeCalculator,
    JieqiCalculator,
    WuxingStrengthCalculator,
    calculate_solar_time,
    calculate_wuxing_strength,
)
from tengod.chart_visualizer import BaziChartVisualizer, visualize_bazi


# ════════════════════════════════════════
# 性能测试工具
# ════════════════════════════════════════

def measure_time(func, runs=100):
    """测量函数执行时间"""
    times = []
    for _ in range(runs):
        start = time.perf_counter()
        func()
        end = time.perf_counter()
        times.append((end - start) * 1000)  # ms
    return {
        "mean": statistics.mean(times),
        "median": statistics.median(times),
        "p95": sorted(times)[int(len(times) * 0.95)],
        "max": max(times),
        "min": min(times),
    }


# ════════════════════════════════════════
# 1. 八字排盘性能
# ════════════════════════════════════════

class TestBaziPerformance:
    """八字排盘性能测试"""

    def test_single_bazi_calculation_speed(self):
        """单次八字排盘应 < 5ms"""
        def calc():
            BaziChart(1990, 6, 15, 10, 30, longitude=116.4)

        stats = measure_time(calc, runs=100)
        assert stats["mean"] < 5.0, f"八字排盘平均耗时 {stats['mean']:.2f}ms 超过 5ms"
        assert stats["p95"] < 10.0, f"八字排盘 P95 耗时 {stats['p95']:.2f}ms 超过 10ms"

    def test_batch_bazi_calculation(self):
        """批量八字排盘 1000 次应 < 5s"""
        start = time.perf_counter()
        for i in range(1000):
            BaziChart(1990 + i % 30, (i % 12) + 1, (i % 28) + 1, i % 24, i % 60)
        elapsed = time.perf_counter() - start
        assert elapsed < 5.0, f"批量排盘 1000 次耗时 {elapsed:.2f}s 超过 5s"

    def test_calc_bazi_function_speed(self):
        """便捷函数 calc_bazi 应 < 5ms"""
        def calc():
            calc_bazi(1990, 6, 15, 10, 30)

        stats = measure_time(calc, runs=100)
        assert stats["mean"] < 5.0


# ════════════════════════════════════════
# 2. 真太阳时计算性能
# ════════════════════════════════════════

class TestSolarTimePerformance:
    """真太阳时计算性能"""

    def test_solar_time_calculation_speed(self):
        """单次真太阳时计算应 < 1ms"""
        calc = SolarTimeCalculator(longitude=116.4)
        local = datetime(1990, 6, 15, 10, 30)

        def calc_once():
            calc.calculate(local)

        stats = measure_time(calc_once, runs=1000)
        assert stats["mean"] < 1.0, f"真太阳时计算平均耗时 {stats['mean']:.3f}ms 超过 1ms"

    def test_equation_of_time_speed(self):
        """均时差计算应 < 0.5ms"""
        calc = SolarTimeCalculator()

        def calc_eot():
            for day in range(1, 366):
                calc._calculate_equation_of_time(day)

        stats = measure_time(calc_eot, runs=100)
        # 365 次计算应 < 50ms
        assert stats["mean"] < 50.0, f"365次均时差计算耗时 {stats['mean']:.2f}ms 超过 50ms"


# ════════════════════════════════════════
# 3. 节气查询性能
# ════════════════════════════════════════

class TestJieqiPerformance:
    """节气查询性能"""

    def test_jieqi_query_speed(self):
        """单次节气查询应 < 1ms"""
        calc = JieqiCalculator()

        def query():
            calc.get_jieqi(2026, 6, 22)

        stats = measure_time(query, runs=1000)
        assert stats["mean"] < 1.0, f"节气查询平均耗时 {stats['mean']:.3f}ms 超过 1ms"

    def test_is_jieqi_day_speed(self):
        """节气日判断应 < 0.5ms"""
        calc = JieqiCalculator()

        def check():
            calc.is_jieqi_day(2, 4)

        stats = measure_time(check, runs=1000)
        assert stats["mean"] < 0.5


# ════════════════════════════════════════
# 4. 五行旺衰性能
# ════════════════════════════════════════

class TestWuxingStrengthPerformance:
    """五行旺衰计算性能"""

    def test_single_wuxing_calculation(self):
        """单次五行旺衰计算应 < 1ms"""
        calc = WuxingStrengthCalculator()

        def calc_once():
            calc.calculate_strength("木", 3)

        stats = measure_time(calc_once, runs=1000)
        assert stats["mean"] < 1.0

    def test_calculate_all_speed(self):
        """计算所有五行旺衰应 < 2ms"""
        calc = WuxingStrengthCalculator()

        def calc_all():
            calc.calculate_all(6)

        stats = measure_time(calc_all, runs=1000)
        assert stats["mean"] < 2.0


# ════════════════════════════════════════
# 5. 可视化生成性能
# ════════════════════════════════════════

class TestVisualizationPerformance:
    """可视化生成性能"""

    def test_html_generation_speed(self):
        """HTML 生成应 < 10ms"""
        viz = BaziChartVisualizer()
        data = {
            "pillars": {"year": "甲子", "month": "丙寅", "day": "戊午", "hour": "庚申"},
            "wuxing": {"木": 2, "火": 1, "土": 1, "金": 1, "水": 3},
            "geju": "正官格",
            "shensha": ["天乙贵人", "文昌"]
        }

        def generate():
            viz.generate_html(data)

        stats = measure_time(generate, runs=100)
        assert stats["mean"] < 10.0, f"HTML生成平均耗时 {stats['mean']:.2f}ms 超过 10ms"

    def test_json_generation_speed(self):
        """JSON 生成应 < 2ms"""
        viz = BaziChartVisualizer()
        data = {"pillars": {"year": "甲子"}, "wuxing": {"木": 1}}

        def generate():
            viz.generate_json(data)

        stats = measure_time(generate, runs=1000)
        assert stats["mean"] < 2.0

    def test_batch_html_generation(self):
        """批量 HTML 生成 100 次应 < 1s"""
        viz = BaziChartVisualizer()
        data = {
            "pillars": {"year": "甲子", "month": "丙寅", "day": "戊午", "hour": "庚申"},
            "wuxing": {"木": 2, "火": 1, "土": 1, "金": 1, "水": 3}
        }

        start = time.perf_counter()
        for _ in range(100):
            viz.generate_html(data)
        elapsed = time.perf_counter() - start
        assert elapsed < 1.0, f"批量HTML生成 100 次耗时 {elapsed:.2f}s 超过 1s"


# ════════════════════════════════════════
# 6. 端到端性能
# ════════════════════════════════════════

class TestEndToEndPerformance:
    """端到端性能测试"""

    def test_full_bazi_pipeline_speed(self):
        """完整八字流程（排盘+真太阳时+五行+可视化）应 < 20ms"""
        def pipeline():
            # 1. 排盘
            chart = BaziChart(1990, 6, 15, 10, 30, longitude=116.4)
            # 2. 真太阳时
            calc = SolarTimeCalculator(longitude=116.4)
            calc.calculate(datetime(1990, 6, 15, 10, 30))
            # 3. 五行旺衰
            calculate_wuxing_strength(6)
            # 4. 可视化
            data = {
                "pillars": chart.pillars,
                "wuxing": {"木": 1, "火": 1, "土": 1, "金": 1, "水": 1}
            }
            visualize_bazi(data)

        stats = measure_time(pipeline, runs=100)
        assert stats["mean"] < 20.0, f"完整流程平均耗时 {stats['mean']:.2f}ms 超过 20ms"
        assert stats["p95"] < 50.0, f"完整流程 P95 耗时 {stats['p95']:.2f}ms 超过 50ms"

    def test_concurrent_bazi_calculation(self):
        """模拟并发排盘 500 次应 < 3s"""
        start = time.perf_counter()
        results = []
        for i in range(500):
            chart = BaziChart(
                1990 + (i % 30),
                (i % 12) + 1,
                (i % 28) + 1,
                i % 24,
                i % 60
            )
            results.append(chart.pillars)

        elapsed = time.perf_counter() - start
        assert elapsed < 3.0, f"并发排盘 500 次耗时 {elapsed:.2f}s 超过 3s"
        assert len(results) == 500
        # 验证结果多样性
        unique = set(tuple(r.values()) for r in results)
        assert len(unique) > 100, "排盘结果多样性不足"
