#!/usr/bin/env python3
"""
test_phase22.py — 阶段二十二：多体系综合分析引擎测试
阶段二十三：测试与前端整合

覆盖：
  - 数据结构（SystemResult / CrossValidation / ConsensusFortune / ComprehensiveResult）
  - ComprehensiveAnalyzer 核心方法
  - 多体系交叉验证逻辑
  - 共识运势评分
  - /api/prediction/comprehensive 接口（若 fastapi 可用）
  - 多样本稳定性
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
os.environ.pop("TENGOD_API_KEY", None)
os.environ["TENGOD_LLM_BACKEND"] = "mock"


# ════════════════════════════════════════
# 1. 数据结构
# ════════════════════════════════════════

class TestDataStructures:
    def test_system_result_to_dict(self):
        from tengod.multi_system_engine import SystemResult
        sr = SystemResult(system="八字", available=True, data={"wuxing": {}},
                          summary="测试总结")
        d = sr.to_dict()
        assert d["system"] == "八字"
        assert d["available"] is True
        assert "summary" in d

    def test_cross_validation_structure(self):
        from tengod.multi_system_engine import CrossValidation
        cv = CrossValidation(score=80, level="基本一致",
                             agreements=["八字", "紫微"], conflicts=["奇门"],
                             interpretations=["多数系统支持正印格局"])
        d = cv.to_dict()
        assert d["score"] == 80
        assert d["level"] == "基本一致"
        assert "八字" in d["agreements"]
        assert "奇门" in d["conflicts"]

    def test_consensus_fortune_structure(self):
        from tengod.multi_system_engine import ConsensusFortune
        cf = ConsensusFortune(overall="中吉", score=75,
                              key_strengths=["正印护身", "食神生财"],
                              key_risks=["伤官见官"],
                              best_timing=["寅卯月"], weak_timing=["申酉月"],
                              career="事业稳固", wealth="财运中等",
                              relationships="感情和睦", health="注意脾胃")
        d = cf.to_dict()
        assert d["overall"] == "中吉"
        assert d["score"] == 75
        assert isinstance(d["key_strengths"], list)
        assert "正印护身" in d["key_strengths"]

    def test_comprehensive_result_to_dict(self):
        from tengod.multi_system_engine import (
            ComprehensiveResult, SystemResult, CrossValidation, ConsensusFortune,
        )
        systems = {"八字": SystemResult(system="八字", summary="ok")}
        cr = ComprehensiveResult(
            birth_info={"year": 1990, "gender": "male"},
            systems=systems,
            cross_validation=CrossValidation(agreements=["八字"]),
            consensus=ConsensusFortune(overall="平", score=70),
            comprehensive_report="综合报告",
        )
        d = cr.to_dict()
        assert d["birth_info"]["year"] == 1990
        assert "八字" in d["systems"]
        assert d["comprehensive_report"] == "综合报告"


# ════════════════════════════════════════
# 2. ComprehensiveAnalyzer 基础功能
# ════════════════════════════════════════

class TestAnalyzerBasics:
    def test_analyzer_init(self):
        from tengod.multi_system_engine import ComprehensiveAnalyzer
        analyzer = ComprehensiveAnalyzer()
        assert hasattr(analyzer, "_engines")
        assert isinstance(analyzer._engines, dict)

    def test_safe_import_missing(self):
        from tengod.multi_system_engine import _safe_import
        assert _safe_import("this_module_does_not_exist_123", "X") is None

    def test_extract_yongshen_bazi(self):
        from tengod.multi_system_engine import ComprehensiveAnalyzer
        data = {"yongshen": ["木", "金"]}
        yong, ji = ComprehensiveAnalyzer._extract_yongshen("bazi", data)
        assert "木" in yong

    def test_extract_yongshen_ziwei(self):
        from tengod.multi_system_engine import ComprehensiveAnalyzer
        data = {"ming_zhu": "天同星入命"}
        yong, ji = ComprehensiveAnalyzer._extract_yongshen("ziwei", data)
        assert "水" in yong

    def test_extract_yongshen_empty(self):
        from tengod.multi_system_engine import ComprehensiveAnalyzer
        yong, ji = ComprehensiveAnalyzer._extract_yongshen("other", None)
        assert yong == []
        assert ji == []

    def test_analyzer_full_analysis(self):
        from tengod.multi_system_engine import ComprehensiveAnalyzer
        analyzer = ComprehensiveAnalyzer()
        result = analyzer.full_analysis(
            birth_date=(1990, 6, 15),
            birth_time=(10, 30),
            gender="male",
            target_year=2026,
        )
        assert result is not None
        assert isinstance(result.birth_info, dict)
        assert isinstance(result.systems, dict)
        d = result.to_dict()
        assert "cross_validation" in d
        assert "consensus" in d
        assert len(result.comprehensive_report) > 0

    def test_analyzer_full_analysis_with_pillars(self):
        from tengod.multi_system_engine import ComprehensiveAnalyzer
        analyzer = ComprehensiveAnalyzer()
        result = analyzer.full_analysis(
            birth_date=(1990, 6, 15),
            birth_time=(10, 0),
            gender="male",
            target_year=2026,
            pillars={"year": "庚午", "month": "壬午", "day": "辛亥", "hour": "癸巳"},
            sitting="北",
            facing="南",
            lunar_month=5,
            lunar_day=23,
        )
        assert result is not None
        d = result.to_dict()
        assert "systems" in d

    def test_consensus_score_range(self):
        from tengod.multi_system_engine import ComprehensiveAnalyzer
        analyzer = ComprehensiveAnalyzer()
        result = analyzer.full_analysis(
            birth_date=(1988, 3, 12),
            birth_time=(8, 0),
            gender="female",
            target_year=2026,
        )
        # 评分应在 0-100 之间
        score = result.consensus.score
        assert 0 <= score <= 100
        # overall 应为字符串（如 大吉/吉/平/凶 等）
        assert isinstance(result.consensus.overall, str)
        assert len(result.consensus.overall) > 0


# ════════════════════════════════════════
# 3. 交叉验证与共识
# ════════════════════════════════════════

class TestCrossValidation:
    def test_cross_score_is_numeric(self):
        from tengod.multi_system_engine import ComprehensiveAnalyzer
        analyzer = ComprehensiveAnalyzer()
        result = analyzer.full_analysis(
            birth_date=(1995, 10, 5),
            birth_time=(14, 30),
            gender="male",
            target_year=2026,
        )
        assert isinstance(result.cross_validation.score, (int, float))
        assert 0 <= result.cross_validation.score <= 100

    def test_agreements_conflicts_lists(self):
        from tengod.multi_system_engine import ComprehensiveAnalyzer
        analyzer = ComprehensiveAnalyzer()
        result = analyzer.full_analysis(
            birth_date=(1980, 1, 1),
            birth_time=(0, 0),
            gender="male",
            target_year=2026,
        )
        assert isinstance(result.cross_validation.agreements, list)
        assert isinstance(result.cross_validation.conflicts, list)

    def test_consensus_has_sections(self):
        from tengod.multi_system_engine import ComprehensiveAnalyzer
        analyzer = ComprehensiveAnalyzer()
        result = analyzer.full_analysis(
            birth_date=(2000, 7, 20),
            birth_time=(20, 15),
            gender="female",
            target_year=2026,
        )
        # 共识结果包含四大分项
        for field in ("career", "wealth", "relationships", "health"):
            assert hasattr(result.consensus, field)


# ════════════════════════════════════════
# 4. API 接口测试（若无 fastapi 则自动跳过）
# ════════════════════════════════════════

try:
    from fastapi.testclient import TestClient
    from tengod.api_server import app
    from tengod.auth import JWTManager
    HAS_FASTAPI = True
except Exception:
    HAS_FASTAPI = False


@pytest.mark.skipif(not HAS_FASTAPI, reason="fastapi / tengod.api_server 不可用")
class TestComprehensiveAPI:
    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.fixture
    def user_headers(self):
        token = JWTManager.create_access_token(1, "testuser", "user")
        return {"Authorization": f"Bearer {token}"}

    def test_api_comprehensive_success(self, client, user_headers):
        resp = client.post("/api/prediction/comprehensive", headers=user_headers, json={
            "birth_year": 1990, "birth_month": 6, "birth_day": 15,
            "birth_hour": 10, "birth_minute": 30,
            "gender": "male", "target_year": 2026,
            "sitting": "北", "facing": "南",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "birth_info" in data
        assert "systems" in data
        assert "cross_validation" in data
        assert "consensus" in data
        assert "comprehensive_report" in data
        assert isinstance(data["consensus"]["score"], (int, float))

    def test_api_comprehensive_validation(self, client, user_headers):
        # 必填字段缺失
        resp = client.post("/api/prediction/comprehensive", headers=user_headers, json={
            "birth_year": 1990,
        })
        assert resp.status_code == 422

    def test_api_comprehensive_with_pillars(self, client, user_headers):
        resp = client.post("/api/prediction/comprehensive", headers=user_headers, json={
            "birth_year": 1985, "birth_month": 3, "birth_day": 20,
            "birth_hour": 14, "birth_minute": 0, "gender": "female",
            "target_year": 2026,
            "pillars": {"year": "乙丑", "month": "己卯", "day": "甲寅", "hour": "辛未"},
            "lunar_month": 2, "lunar_day": 15,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["consensus"]["score"], (int, float))


# ════════════════════════════════════════
# 5. 多样本稳定性测试
# ════════════════════════════════════════

class TestMultiSampleStability:
    @pytest.mark.parametrize("year,month,day,hour,minute,gender", [
        (1970, 5, 5, 5, 5, "male"),
        (1985, 8, 15, 12, 0, "female"),
        (1995, 11, 25, 18, 30, "male"),
        (2005, 2, 10, 23, 45, "female"),
    ])
    def test_multiple_profiles(self, year, month, day, hour, minute, gender):
        """多种不同命理配置应均能产生有效结果"""
        from tengod.multi_system_engine import ComprehensiveAnalyzer
        analyzer = ComprehensiveAnalyzer()
        result = analyzer.full_analysis(
            birth_date=(year, month, day),
            birth_time=(hour, minute),
            gender=gender,
            target_year=2026,
        )
        assert result is not None
        assert 0 <= result.consensus.score <= 100
        assert len(result.systems) > 0
        assert len(result.comprehensive_report) > 10


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))
