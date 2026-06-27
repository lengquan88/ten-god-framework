import pytest
from unittest.mock import patch
from tengod.七杀_品质裁决.quality_judge import QualityJudge, Score, Grade


class TestGrade:
    def test_enum_values(self):
        assert Grade.S.value == "S"
        assert Grade.A.value == "A"
        assert Grade.B.value == "B"
        assert Grade.C.value == "C"
        assert Grade.D.value == "D"

    def test_enum_members(self):
        members = set(Grade)
        assert Grade.S in members
        assert Grade.A in members
        assert Grade.B in members
        assert Grade.C in members
        assert Grade.D in members


class TestScore:
    def test_score_creation_and_weighted_property(self):
        score = Score(name="Test", value=80, weight=2.0)
        assert score.name == "Test"
        assert score.value == 80
        assert score.weight == 2.0
        assert score.weighted == 160.0

    def test_score_with_default_weight(self):
        score = Score(name="Test", value=75)
        assert score.weight == 1.0
        assert score.weighted == 75.0

    def test_score_with_custom_weight(self):
        score = Score(name="Test", value=50, weight=3.0)
        assert score.weighted == 150.0

    def test_score_with_comment(self):
        score = Score(name="Test", value=90, comment="Excellent work")
        assert score.comment == "Excellent work"

    def test_score_weighted_with_zero_weight(self):
        score = Score(name="Test", value=100, weight=0.0)
        assert score.weighted == 0.0


class TestQualityJudgeInit:
    def test_init_with_empty_scores(self):
        judge = QualityJudge()
        assert judge._scores == []


class TestAddScore:
    def test_add_score_returns_score(self):
        judge = QualityJudge()
        score = judge.add_score("code_quality", 85)
        assert isinstance(score, Score)
        assert score.name == "code_quality"
        assert score.value == 85
        assert score.weight == 1.0
        assert score.comment == ""

    def test_add_score_with_all_params(self):
        judge = QualityJudge()
        score = judge.add_score("security", 95, weight=2.0, comment="No vulnerabilities")
        assert score.name == "security"
        assert score.value == 95
        assert score.weight == 2.0
        assert score.comment == "No vulnerabilities"

    def test_multiple_add_score_calls(self):
        judge = QualityJudge()
        judge.add_score("a", 80)
        judge.add_score("b", 90)
        assert len(judge._scores) == 2


class TestTotalWeighted:
    def test_total_weighted_with_no_scores_returns_zero(self):
        judge = QualityJudge()
        assert judge.total_weighted() == 0.0

    def test_total_weighted_with_single_score(self):
        judge = QualityJudge()
        judge.add_score("test", 80, weight=2.0)
        assert judge.total_weighted() == 80.0

    def test_total_weighted_with_multiple_scores(self):
        judge = QualityJudge()
        judge.add_score("a", 80, weight=1.0)
        judge.add_score("b", 90, weight=1.0)
        assert judge.total_weighted() == 85.0

    def test_total_weighted_with_varied_weights(self):
        judge = QualityJudge()
        judge.add_score("a", 100, weight=3.0)
        judge.add_score("b", 50, weight=1.0)
        # (100*3 + 50*1) / (3+1) = 350/4 = 87.5
        assert judge.total_weighted() == 87.5

    def test_total_weighted_with_zero_total_weight(self):
        judge = QualityJudge()
        judge.add_score("a", 80, weight=0.0)
        judge.add_score("b", 90, weight=0.0)
        assert judge.total_weighted() == 0.0


class TestGrade:
    def test_grade_returns_S_at_90_plus(self):
        judge = QualityJudge()
        judge.add_score("test", 95)
        assert judge.grade() == Grade.S

    def test_grade_returns_A_at_80_to_89(self):
        judge = QualityJudge()
        judge.add_score("test", 85)
        assert judge.grade() == Grade.A

    def test_grade_returns_B_at_70_to_79(self):
        judge = QualityJudge()
        judge.add_score("test", 75)
        assert judge.grade() == Grade.B

    def test_grade_returns_C_at_60_to_69(self):
        judge = QualityJudge()
        judge.add_score("test", 65)
        assert judge.grade() == Grade.C

    def test_grade_returns_D_below_60(self):
        judge = QualityJudge()
        judge.add_score("test", 55)
        assert judge.grade() == Grade.D

    def test_grade_boundary_exactly_90(self):
        judge = QualityJudge()
        judge.add_score("test", 90)
        assert judge.grade() == Grade.S

    def test_grade_boundary_exactly_80(self):
        judge = QualityJudge()
        judge.add_score("test", 80)
        assert judge.grade() == Grade.A

    def test_grade_boundary_exactly_70(self):
        judge = QualityJudge()
        judge.add_score("test", 70)
        assert judge.grade() == Grade.B

    def test_grade_boundary_exactly_60(self):
        judge = QualityJudge()
        judge.add_score("test", 60)
        assert judge.grade() == Grade.C

    def test_grade_with_no_scores(self):
        judge = QualityJudge()
        # total_weighted returns 0, which is >= 0, so Grade.D
        assert judge.grade() == Grade.D


class TestReport:
    def test_report_structure(self):
        judge = QualityJudge()
        judge.add_score("code", 85, comment="Good code")
        report = judge.report()

        assert "total" in report
        assert "grade" in report
        assert "items" in report
        assert report["total"] == 85.0
        assert report["grade"] == "A"
        assert len(report["items"]) == 1
        assert report["items"][0]["name"] == "code"
        assert report["items"][0]["value"] == 85
        assert report["items"][0]["weight"] == 1.0
        assert report["items"][0]["weighted"] == 85.0
        assert report["items"][0]["comment"] == "Good code"

    def test_report_with_multiple_items(self):
        judge = QualityJudge()
        judge.add_score("security", 90, weight=2.0)
        judge.add_score("performance", 70, weight=1.0)
        report = judge.report()

        assert len(report["items"]) == 2
        assert report["items"][0]["name"] == "security"
        assert report["items"][1]["name"] == "performance"
        # (90*2 + 70*1) / (2+1) = 250/3 ≈ 83.33
        assert report["total"] == round(250 / 3, 2)
        assert report["grade"] == "A"

    def test_report_with_no_items(self):
        judge = QualityJudge()
        report = judge.report()

        assert report["total"] == 0.0
        assert report["grade"] == "D"
        assert report["items"] == []


class TestReset:
    def test_reset_clears_scores(self):
        judge = QualityJudge()
        judge.add_score("test", 80)
        judge.reset()
        assert judge._scores == []

    def test_reset_then_add_score_works(self):
        judge = QualityJudge()
        judge.add_score("old", 50)
        judge.reset()
        judge.add_score("new", 90)
        assert judge.total_weighted() == 90.0
        assert judge.grade() == Grade.S


class TestGradeThresholds:
    def test_grade_thresholds_structure(self):
        assert QualityJudge.GRADE_THRESHOLDS == {
            Grade.S: 90,
            Grade.A: 80,
            Grade.B: 70,
            Grade.C: 60,
            Grade.D: 0,
        }

    def test_grade_thresholds_keys(self):
        assert Grade.S in QualityJudge.GRADE_THRESHOLDS
        assert Grade.A in QualityJudge.GRADE_THRESHOLDS
        assert Grade.B in QualityJudge.GRADE_THRESHOLDS
        assert Grade.C in QualityJudge.GRADE_THRESHOLDS
        assert Grade.D in QualityJudge.GRADE_THRESHOLDS


class TestEdgeCases:
    def test_value_at_100(self):
        judge = QualityJudge()
        judge.add_score("perfect", 100)
        assert judge.total_weighted() == 100.0
        assert judge.grade() == Grade.S

    def test_value_at_0(self):
        judge = QualityJudge()
        judge.add_score("terrible", 0)
        assert judge.total_weighted() == 0.0
        assert judge.grade() == Grade.D

    def test_value_just_above_89(self):
        judge = QualityJudge()
        judge.add_score("test", 89.5)
        assert judge.grade() == Grade.A

    def test_value_just_below_90(self):
        judge = QualityJudge()
        judge.add_score("test", 89.9)
        assert judge.grade() == Grade.A

    def test_grade_fallback_to_D_when_no_threshold_match(self):
        judge = QualityJudge()
        judge.add_score("test", 100)
        with patch.object(QualityJudge, "GRADE_THRESHOLDS", {}):
            assert judge.grade() == Grade.D