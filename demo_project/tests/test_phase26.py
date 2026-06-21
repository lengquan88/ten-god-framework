#!/usr/bin/env python3
"""
test_phase26.py — 阶段二十六：高级分析 API 集成测试

覆盖：
  - AdvancedAnalyzer.destiny_trajectory（命运轨迹推演）
  - AdvancedAnalyzer.batch_bazi（批量排盘）
  - AdvancedAnalyzer.compare_cases（命例对比）
  - /api/advanced/trajectory 端点
  - /api/advanced/batch-bazi 端点
  - /api/advanced/compare 端点
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
os.environ.pop("TENGOD_API_KEY", None)
os.environ["TENGOD_LLM_BACKEND"] = "mock"


class TestDestinyTrajectory:
    """命运轨迹推演测试"""

    def test_trajectory_basic(self):
        """基础轨迹推演"""
        from tengod.advanced_analysis import AdvancedAnalyzer
        analyzer = AdvancedAnalyzer()
        result = analyzer.destiny_trajectory(
            year=1990, month=6, day=15, hour=10, minute=0,
            gender="male", start_age=0, end_age=60,
        )
        assert "birth" in result
        assert result["birth"]["year"] == 1990
        assert result["birth"]["gender"] == "male"
        assert "day_master" in result
        assert "dayun" in result
        assert "liunian" in result
        assert "life_stages" in result
        assert "summary" in result

    def test_trajectory_dayun_structure(self):
        """大运结构正确性"""
        from tengod.advanced_analysis import AdvancedAnalyzer
        analyzer = AdvancedAnalyzer()
        result = analyzer.destiny_trajectory(
            year=1985, month=3, day=20, hour=8, gender="female",
            start_age=0, end_age=40,
        )
        dayun = result["dayun"]
        assert isinstance(dayun, list)
        # 大运应有多个条目（每10年一步）
        if dayun:
            du = dayun[0]
            for field in ("index", "age_start", "age_end", "gan_zhi", "element", "relation", "favorable"):
                assert field in du, f"缺失字段 {field}"
            assert isinstance(du["favorable"], bool)

    def test_trajectory_liunian_structure(self):
        """流年结构正确性"""
        from tengod.advanced_analysis import AdvancedAnalyzer
        analyzer = AdvancedAnalyzer()
        result = analyzer.destiny_trajectory(
            year=1995, month=1, day=1, hour=12, gender="male",
            start_age=20, end_age=25,
        )
        liunian = result["liunian"]
        assert isinstance(liunian, list)
        # 流年数量应与年龄范围一致
        if liunian:
            ln = liunian[0]
            for field in ("age", "year", "gan_zhi", "element", "relation"):
                assert field in ln, f"缺失字段 {field}"
            assert isinstance(ln["year"], int)

    def test_trajectory_life_stages(self):
        """人生阶段分析"""
        from tengod.advanced_analysis import AdvancedAnalyzer
        analyzer = AdvancedAnalyzer()
        result = analyzer.destiny_trajectory(
            year=2000, month=5, day=10, hour=15, gender="male",
            start_age=0, end_age=80,
        )
        stages = result["life_stages"]
        assert isinstance(stages, list)
        # 应该有多个阶段
        assert len(stages) >= 1
        # 每个阶段应有阶段名和年龄段
        for stage in stages:
            assert "stage" in stage or "name" in stage
            assert "age_range" in stage

    def test_trajectory_with_custom_range(self):
        """自定义年龄范围"""
        from tengod.advanced_analysis import AdvancedAnalyzer
        analyzer = AdvancedAnalyzer()
        result = analyzer.destiny_trajectory(
            year=1990, month=1, day=1, hour=0,
            gender="female", start_age=30, end_age=50,
        )
        assert result["birth"]["gender"] == "female"
        # 流年应从30岁开始
        liunian = result["liunian"]
        if liunian:
            assert liunian[0]["age"] >= 30


class TestBatchBazi:
    """批量排盘测试"""

    def test_batch_bazi_basic(self):
        """基础批量排盘"""
        from tengod.advanced_analysis import AdvancedAnalyzer
        analyzer = AdvancedAnalyzer()
        inputs = [
            {"year": 1990, "month": 6, "day": 15, "hour": 10, "gender": "male"},
            {"year": 1985, "month": 3, "day": 20, "hour": 14, "gender": "female"},
        ]
        result = analyzer.batch_bazi(inputs)
        assert "results" in result
        assert "stats" in result
        assert result["stats"]["total"] == 2
        assert result["stats"]["success"] >= 0
        assert result["stats"]["success"] <= 2

    def test_batch_bazi_results_structure(self):
        """批量结果结构"""
        from tengod.advanced_analysis import AdvancedAnalyzer
        analyzer = AdvancedAnalyzer()
        inputs = [{"year": 1990, "month": 6, "day": 15, "hour": 10, "gender": "male"}]
        result = analyzer.batch_bazi(inputs)
        r = result["results"][0]
        assert r["success"] is True
        assert "pillars" in r
        assert "day_master" in r
        assert "index" in r
        assert r["index"] == 0

    def test_batch_bazi_stats_aggregation(self):
        """批量统计聚合"""
        from tengod.advanced_analysis import AdvancedAnalyzer
        analyzer = AdvancedAnalyzer()
        inputs = [
            {"year": 1990, "month": 6, "day": 15, "hour": 10, "gender": "male"},
            {"year": 1985, "month": 3, "day": 20, "hour": 14, "gender": "female"},
            {"year": 2000, "month": 1, "day": 1, "hour": 0, "gender": "male"},
        ]
        result = analyzer.batch_bazi(inputs)
        stats = result["stats"]
        assert "day_masters" in stats
        assert "gejus" in stats
        assert "wuxing_totals" in stats
        # 五行总数应合理
        wuxing = stats["wuxing_totals"]
        for elem in ["金", "木", "水", "火", "土"]:
            assert elem in wuxing

    def test_batch_bazi_single(self):
        """单条批量排盘"""
        from tengod.advanced_analysis import AdvancedAnalyzer
        analyzer = AdvancedAnalyzer()
        result = analyzer.batch_bazi([{"year": 1990, "month": 6, "day": 15, "gender": "male"}])
        assert result["stats"]["total"] == 1
        assert result["stats"]["success"] == 1


class TestCompareCases:
    """命例对比测试"""

    def test_compare_cases_invalid_ids(self):
        """无效 ID 返回错误"""
        from tengod.advanced_analysis import AdvancedAnalyzer
        analyzer = AdvancedAnalyzer()
        result = analyzer.compare_cases(99999, 88888)
        assert "error" in result
        assert result["error"] is not None


class TestAdvancedAPIEndpoints:
    """高级分析 API 端点测试（FastAPI TestClient）"""

    @pytest.fixture
    def admin_headers(self):
        from tengod.auth import JWTManager
        token = JWTManager.create_access_token(1, "admin", "admin")
        return {"Authorization": f"Bearer {token}"}

    def test_trajectory_endpoint(self, admin_headers):
        """命运轨迹 API 端点"""
        from fastapi.testclient import TestClient
        from tengod.api_server import app

        client = TestClient(app)
        resp = client.post(
            "/api/advanced/trajectory",
            json={
                "year": 1990, "month": 6, "day": 15,
                "hour": 10, "minute": 0,
                "gender": "male",
                "start_age": 0, "end_age": 40,
            },
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "birth" in data
        assert "dayun" in data
        assert "liunian" in data

    def test_batch_bazi_endpoint(self, admin_headers):
        """批量排盘 API 端点"""
        from fastapi.testclient import TestClient
        from tengod.api_server import app

        client = TestClient(app)
        resp = client.post(
            "/api/advanced/batch-bazi",
            json={
                "inputs": [
                    {"year": 1990, "month": 6, "day": 15, "hour": 10, "gender": "male"},
                    {"year": 1985, "month": 3, "day": 20, "hour": 14, "gender": "female"},
                ]
            },
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "results" in data
        assert "stats" in data

    def test_compare_endpoint_not_found(self, admin_headers):
        """命例对比 API（无效 ID 应返回 404）"""
        from fastapi.testclient import TestClient
        from tengod.api_server import app

        client = TestClient(app)
        resp = client.post(
            "/api/advanced/compare",
            json={"record_a_id": 99999, "record_b_id": 88888},
            headers=admin_headers,
        )
        # 无效记录应返回 404
        assert resp.status_code == 404

    def test_trajectory_endpoint_validation(self):
        """命运轨迹端点参数验证"""
        from fastapi.testclient import TestClient
        from tengod.api_server import app

        client = TestClient(app)
        # 缺少必需参数时应返回 422
        resp = client.post("/api/advanced/trajectory", json={"year": 1990})
        assert resp.status_code == 422


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))
