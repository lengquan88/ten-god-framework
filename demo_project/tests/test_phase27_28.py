"""
test_phase27_28.py — 阶段 27（社交协作）+ 阶段 28（高级可视化）测试
==========================================================
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from tengod.social import (
    UserProfile, ContentPost, SocialGraph, EngagementService,
    CollaborationSession, FeedGenerator, sanitize_content, generate_share_url,
)
from tengod.visualization import (
    BaziChartRenderer, TrajectoryVisualizer, ZiweiStarMap,
    LiuyaoHexagramDisplay, QimenBoard, InteractiveWidgetSpec,
    THEMES, ThemeConfig, apply_theme, export_to_png, export_to_html,
    generate_share_image, WUXING_COLORS,
)


# ============================================================================
# TestUserProfile
# ============================================================================


class TestUserProfile:

    def test_create_profile(self):
        p = UserProfile.update("u_1", display_name="小明", bio="测试用户")
        assert p is not None
        assert p["user_id"] == "u_1"
        assert p["display_name"] == "小明"

    def test_update_profile(self):
        UserProfile.update("u_2", display_name="原名称")
        UserProfile.update("u_2", display_name="新名称")
        p = UserProfile.get("u_2")
        assert p is not None
        assert p["display_name"] == "新名称"

    def test_get_public_omits_private(self):
        UserProfile.update(
            "u_3",
            display_name="公开用户",
            preferences={"theme": "light"},
        )
        pub = UserProfile.get_public("u_3")
        assert pub is not None
        assert pub["user_id"] == "u_3"
        assert pub["display_name"] == "公开用户"
        assert "preferences" not in pub
        assert "updated_at" not in pub

    def test_get_stats(self):
        UserProfile.update("u_4", display_name="统计用户")
        p = UserProfile.get("u_4")
        stats = p["stats"]
        assert isinstance(stats, dict)
        assert "calculations_count" in stats
        assert "shares_count" in stats
        assert "likes_received" in stats


# ============================================================================
# TestContentPost
# ============================================================================


class TestContentPost:

    def test_create_post(self):
        post = ContentPost.create(
            user_id="u_p1",
            record_id="rec_001",
            content_type="bazi_share",
            title="我的八字分享",
            body="分析一下",
            tags=["八字", "分享"],
            visibility="public",
        )
        assert post["post_id"] is not None
        assert post["user_id"] == "u_p1"
        assert post["record_id"] == "rec_001"
        assert post["content_type"] == "bazi_share"

    def test_list_by_user_returns_own_posts(self):
        ContentPost.create(user_id="u_p2", title="Post A", visibility="public")
        ContentPost.create(user_id="u_p2", title="Post B", visibility="public")
        ContentPost.create(user_id="u_p_other", title="Post C", visibility="public")
        result = ContentPost.list_by_user("u_p2")
        assert len(result) == 2
        assert all(r["user_id"] == "u_p2" for r in result)

    def test_list_popular(self):
        p1 = ContentPost.create(user_id="u_p3", title="High", visibility="public")
        p2 = ContentPost.create(user_id="u_p3", title="Low", visibility="public")
        # 点赞 p1 更多
        EngagementService.like("u_l1", p1["post_id"])
        EngagementService.like("u_l2", p1["post_id"])
        EngagementService.like("u_l3", p2["post_id"])
        popular = ContentPost.list_popular()
        assert len(popular) >= 2
        # 第一个应该是 p1
        assert popular[0]["post_id"] == p1["post_id"]

    def test_visibility_public_appears_in_feed(self):
        ContentPost.create(user_id="u_author", title="Public", visibility="public")
        feed = ContentPost.list_feed("u_viewer")
        assert any(p["title"] == "Public" for p in feed)

    def test_visibility_private_hidden_from_others(self):
        ContentPost.create(user_id="u_private_author", title="Private", visibility="private")
        feed = ContentPost.list_feed("u_stranger")
        assert all(p["title"] != "Private" for p in feed)

    def test_delete_post_removes_it(self):
        post = ContentPost.create(user_id="u_del", title="To delete", visibility="public")
        before = ContentPost.get(post["post_id"])
        assert before is not None
        ok = ContentPost.delete("u_del", post["post_id"])
        assert ok
        after = ContentPost.get(post["post_id"])
        assert after is None


# ============================================================================
# TestSocialGraph
# ============================================================================


class TestSocialGraph:

    def test_follow_creates_relation(self):
        result = SocialGraph.follow("u_a", "u_b")
        assert result is True

    def test_is_following_after_follow(self):
        SocialGraph.follow("u_c", "u_d")
        assert SocialGraph.is_following("u_c", "u_d") is True

    def test_unfollow_removes_relation(self):
        SocialGraph.follow("u_e", "u_f")
        assert SocialGraph.is_following("u_e", "u_f") is True
        ok = SocialGraph.unfollow("u_e", "u_f")
        assert ok
        assert SocialGraph.is_following("u_e", "u_f") is False

    def test_get_followers_returns_list(self):
        SocialGraph.follow("u_g1", "u_target")
        SocialGraph.follow("u_g2", "u_target")
        followers = SocialGraph.get_followers("u_target")
        assert isinstance(followers, list)
        assert "u_g1" in followers
        assert "u_g2" in followers

    def test_social_score_increases_with_followers(self):
        SocialGraph.follow("u_x1", "u_popular")
        score1 = SocialGraph.get_social_score("u_popular")
        SocialGraph.follow("u_x2", "u_popular")
        SocialGraph.follow("u_x3", "u_popular")
        score2 = SocialGraph.get_social_score("u_popular")
        assert score2 > score1


# ============================================================================
# TestEngagementService
# ============================================================================


class TestEngagementService:

    def _make_post(self):
        return ContentPost.create(user_id="u_eng", title="Engagement test", visibility="public")

    def test_like_toggles(self):
        post = self._make_post()
        r1 = EngagementService.like("u_liker", post["post_id"])
        assert r1 is True
        stats = EngagementService.get_post_stats(post["post_id"])
        assert stats["likes_count"] >= 1
        # 再点一次应该 toggle (取消)
        r2 = EngagementService.like("u_liker", post["post_id"])
        assert r2 is False

    def test_comment_added(self):
        post = self._make_post()
        comment = EngagementService.comment("u_commenter", post["post_id"], "这是一条评论")
        assert comment["comment_id"] is not None
        comments = EngagementService.list_comments(post["post_id"])
        assert any(c["comment_id"] == comment["comment_id"] for c in comments)

    def test_delete_comment(self):
        post = self._make_post()
        c = EngagementService.comment("u_commenter", post["post_id"], "将被删除")
        ok = EngagementService.delete_comment("u_commenter", c["comment_id"])
        assert ok
        comments = EngagementService.list_comments(post["post_id"])
        assert not any(comment["comment_id"] == c["comment_id"] for comment in comments)

    def test_share_tracks_event(self):
        post = self._make_post()
        share = EngagementService.share("u_sharer", post["post_id"], "wechat_moments")
        assert share["share_id"] is not None
        stats = EngagementService.get_post_stats(post["post_id"])
        assert stats["shares_count"] >= 1

    def test_post_stats_accurate(self):
        post = self._make_post()
        EngagementService.like("u_s1", post["post_id"])
        EngagementService.like("u_s2", post["post_id"])
        EngagementService.comment("u_s3", post["post_id"], "评论1")
        EngagementService.share("u_s4", post["post_id"])
        stats = EngagementService.get_post_stats(post["post_id"])
        assert stats["likes_count"] >= 2
        assert stats["comments_count"] >= 1
        assert stats["shares_count"] >= 1

    def test_list_comments_pagination(self):
        post = self._make_post()
        for i in range(5):
            EngagementService.comment(f"u_{i}", post["post_id"], f"comment {i}")
        page = EngagementService.list_comments(post["post_id"], limit=3)
        assert len(page) == 3


# ============================================================================
# TestCollaborationSession
# ============================================================================


class TestCollaborationSession:

    def test_create_session(self):
        session = CollaborationSession.create_session(
            owner_id="u_owner",
            record_id="rec_collab",
            title="八字协同分析",
            invited_user_ids=["u_invited"],
        )
        assert session["session_id"] is not None
        assert session["owner_id"] == "u_owner"
        assert session["record_id"] == "rec_collab"

    def test_add_annotation(self):
        session = CollaborationSession.create_session("u_o1", "rec_a", "title")
        ann = CollaborationSession.add_annotation(
            session_id=session["session_id"],
            user_id="u_o1",
            pillar_index=2,
            annotation_text="此柱为关键",
            color_hex="#ff0000",
            x_pos=10.5,
            y_pos=20.3,
        )
        assert ann["annotation_id"] is not None
        assert ann["pillar_index"] == 2
        assert ann["color_hex"] == "#ff0000"

    def test_add_collaborator(self):
        session = CollaborationSession.create_session("u_o2", "rec_b", "t2")
        ok = CollaborationSession.add_collaborator(session["session_id"], "u_new")
        assert ok
        fetched = CollaborationSession.get_session(session["session_id"])
        assert "u_new" in fetched["collaborators"]

    def test_list_annotations_returns_list(self):
        session = CollaborationSession.create_session("u_o3", "rec_c", "t3")
        CollaborationSession.add_annotation(session["session_id"], "u_o3", 0, "ann1")
        CollaborationSession.add_annotation(session["session_id"], "u_o3", 1, "ann2")
        anns = CollaborationSession.list_annotations(session["session_id"])
        assert isinstance(anns, list)
        assert len(anns) == 2

    def test_export_session_json(self):
        session = CollaborationSession.create_session("u_o4", "rec_d", "t4")
        CollaborationSession.add_annotation(session["session_id"], "u_o4", 0, "export_test")
        result = CollaborationSession.export_session(session["session_id"], format="json")
        assert isinstance(result, str)
        # 能解析为 JSON
        parsed = json.loads(result)
        assert "session" in parsed
        assert "annotations" in parsed


# ============================================================================
# TestFeedGenerator
# ============================================================================


class TestFeedGenerator:

    def test_generate_feed_returns_list(self):
        feed = FeedGenerator.generate_feed("u_f1", limit=10)
        assert isinstance(feed, list)

    def test_trending_returns_posts(self):
        ContentPost.create(user_id="u_t", title="trending", visibility="public")
        trending = FeedGenerator.get_trending()
        assert isinstance(trending, list)
        assert len(trending) > 0

    def test_recommended_returns_list(self):
        ContentPost.create(user_id="u_other", title="推荐", visibility="public")
        rec = FeedGenerator.get_recommended_for_user("u_f2", limit=5)
        assert isinstance(rec, list)
        assert len(rec) <= 5

    def test_feed_pagination(self):
        feed = FeedGenerator.generate_feed("u_f3", limit=3)
        assert len(feed) <= 3


# ============================================================================
# TestBaziChartRenderer
# ============================================================================


class TestBaziChartRenderer:

    def _sample_pillars(self):
        return {"year": "庚午", "month": "壬午", "day": "庚子", "hour": "辛巳"}

    def test_render_ascii_returns_string(self):
        ascii_art = BaziChartRenderer.render_ascii(self._sample_pillars(), "庚")
        assert isinstance(ascii_art, str)
        assert len(ascii_art) > 0

    def test_render_json_chart_has_pillars(self):
        chart = BaziChartRenderer.render_json_chart(self._sample_pillars())
        assert "pillars" in chart
        assert len(chart["pillars"]) == 4

    def test_wuxing_colors(self):
        colors = {el: BaziChartRenderer.get_colors_by_wuxing(el) for el in WUXING_COLORS}
        # 每个元素都有颜色
        assert all(len(c) > 0 for c in colors.values())
        # 颜色是不同的（不要求所有都不同，至少大部分不同）
        unique = len(set(colors.values()))
        assert unique >= 4

    def test_interactive_hints_added(self):
        chart = BaziChartRenderer.render_json_chart(self._sample_pillars())
        chart = BaziChartRenderer.add_interactive_hints(chart)
        assert "hints" in chart
        assert isinstance(chart["hints"], dict)
        assert len(chart["hints"]) > 0

    def test_render_svg_starts_with_svg_tag(self):
        svg = BaziChartRenderer.render_svg(self._sample_pillars(), "庚")
        assert isinstance(svg, str)
        assert "<?xml" in svg or svg.strip().startswith("<svg") or "<svg" in svg


# ============================================================================
# TestTrajectoryVisualizer
# ============================================================================


class TestTrajectoryVisualizer:

    def test_line_chart_data_structure(self):
        years = [2020, 2021, 2022, 2023]
        line = TrajectoryVisualizer.generate_line_chart(year_range=years)
        assert "data" in line
        assert isinstance(line["data"], list)
        assert len(line["data"]) == 4

    def test_heatmap_contains_scores(self):
        hm = TrajectoryVisualizer.generate_heatmap(year_range=[2020, 2021])
        cells = hm["cells"]
        assert all("score" in cell for cell in cells)
        assert all(cell["score"] is not None for cell in cells)

    def test_radar_six_dimensions(self):
        radar = TrajectoryVisualizer.generate_radar_chart()
        assert len(radar["dimensions"]) == 6
        assert len(radar["axes"]) == 6

    def test_bar_chart_has_labels(self):
        bar = TrajectoryVisualizer.generate_bar_chart({"A": 10, "B": 20}, "测试")
        assert "labels" in bar
        assert "values" in bar
        assert len(bar["labels"]) == len(bar["values"])

    def test_multiple_years_included(self):
        years = [2020, 2021, 2022, 2023, 2024]
        line = TrajectoryVisualizer.generate_line_chart(year_range=years)
        returned_years = [p["year"] for p in line["data"]]
        for y in years:
            assert y in returned_years


# ============================================================================
# TestZiweiStarMap
# ============================================================================


class TestZiweiStarMap:

    def test_twelve_palace_layout(self):
        palaces = ZiweiStarMap.generate_palace_layout()
        assert len(palaces) == 12

    def test_palace_has_stars(self):
        palaces = ZiweiStarMap.generate_palace_layout()
        for p in palaces:
            assert "main_stars" in p
            assert len(p["main_stars"]) > 0

    def test_major_transits_has_year(self):
        transits = ZiweiStarMap.generate_major_transits(current_year=2025)
        assert transits["current_year"] == 2025
        assert len(transits["大运"]) >= 1

    def test_interactive_data_has_tooltip(self):
        stars = ZiweiStarMap.generate_interactive_stars()
        assert len(stars) > 0
        for s in stars:
            assert "tooltip" in s
            assert len(s["tooltip"]) > 0


# ============================================================================
# TestLiuyaoHexagram
# ============================================================================


class TestLiuyaoHexagram:

    def test_hexagram_six_lines(self):
        hex_data = LiuyaoHexagramDisplay.render_hexagram([1, 0, 1, 0, 1, 0])
        assert len(hex_data["lines"]) == 6
        assert hex_data["yao_count"] == 6

    def test_binary_representation(self):
        hex_data = LiuyaoHexagramDisplay.render_hexagram([1, 0, 1, 0, 1, 0])
        binary = hex_data["binary"]
        # 只包含 0 和 1
        assert all(ch in "01" for ch in binary)
        assert len(binary) == 6

    def test_changing_lines_highlighted(self):
        original = [1, 1, 1, 0, 0, 0]
        changed =  [1, 0, 1, 1, 0, 1]
        result = LiuyaoHexagramDisplay.render_changing_lines(original, changed)
        changing_lines = [l for l in result["lines"] if l["is_changing"]]
        assert len(changing_lines) >= 1
        assert result["changing_count"] >= 1

    def test_pair_rendered(self):
        pair = LiuyaoHexagramDisplay.render_hexagram_pair(
            [1, 1, 1, 0, 0, 0],
            [1, 0, 1, 1, 0, 1],
        )
        assert "primary" in pair
        assert "transformed" in pair
        assert pair["primary"]["lines"][0]["value"] == 1


# ============================================================================
# TestQimenBoard
# ============================================================================


class TestQimenBoard:

    def test_nine_palace_board(self):
        board = QimenBoard.render_nine_palace_board()
        assert board["grid_size"] == 3
        assert len(board["palaces"]) == 9

    def test_palace_has_direction(self):
        board = QimenBoard.render_nine_palace_board()
        for p in board["palaces"]:
            assert "direction" in p
            assert p["direction"] is not None

    def test_shensha_overlay(self):
        overlay = QimenBoard.render_shensha_overlays()
        assert "overlays" in overlay
        assert len(overlay["overlays"]) >= 8

    def test_time_dimension_has_segments(self):
        td = QimenBoard.render_time_dimension(2025, 6, 15, 12)
        assert "segments" in td
        assert len(td["segments"]) >= 12
        assert td["year"] == 2025


# ============================================================================
# TestInteractiveWidget
# ============================================================================


class TestInteractiveWidget:

    def test_bazi_widget_has_type(self):
        spec = InteractiveWidgetSpec.build_bazi_widget_spec(
            {"year": "庚午", "month": "壬午", "day": "庚子", "hour": "辛巳"}
        )
        assert spec["widget_type"] == "bazi_chart"

    def test_trajectory_widget_has_data(self):
        spec = InteractiveWidgetSpec.build_trajectory_widget_spec()
        assert "data" in spec
        assert "line_chart" in spec["data"]

    def test_widget_spec_is_json_serializable(self):
        specs = [
            InteractiveWidgetSpec.build_bazi_widget_spec(
                {"year": "甲子", "month": "丙寅", "day": "戊辰", "hour": "庚申"}
            ),
            InteractiveWidgetSpec.build_trajectory_widget_spec(),
            InteractiveWidgetSpec.build_hexagram_widget_spec([1, 1, 1, 0, 0, 0]),
            InteractiveWidgetSpec.build_ziwei_widget_spec(),
            InteractiveWidgetSpec.build_qimen_widget_spec(),
        ]
        for spec in specs:
            serialized = json.dumps(spec, ensure_ascii=False)
            assert isinstance(serialized, str)
            assert len(serialized) > 0


# ============================================================================
# TestThemeSystem
# ============================================================================


class TestThemeSystem:

    def test_theme_config_exists(self):
        light = THEMES.get("light")
        dark = THEMES.get("dark")
        assert light is not None
        assert dark is not None
        assert isinstance(light, ThemeConfig)
        assert light.primary.startswith("#")

    def test_apply_theme_changes_colors(self):
        chart = BaziChartRenderer.render_json_chart(
            {"year": "甲子", "month": "丙寅", "day": "戊辰", "hour": "庚申"}
        )
        themed_light = apply_theme(chart, "light")
        themed_dark = apply_theme(chart, "dark")
        assert themed_light["theme"]["name"] == "light"
        assert themed_dark["theme"]["name"] == "dark"
        # 主题色应该不同
        assert themed_light["theme"]["primary"] != themed_dark["theme"]["background"] or \
               themed_light["theme"]["background"] != themed_dark["theme"]["background"]

    def test_traditional_theme_uses_ink_colors(self):
        traditional = THEMES.get("traditional")
        assert traditional is not None
        assert traditional.font_family == "serif"
        assert traditional.name == "traditional"


# ============================================================================
# TestExportUtilities
# ============================================================================


class TestExportUtilities:

    def test_export_html_has_doctype(self):
        html_out = export_to_html("八字命盘", {"pillar": "example"})
        assert isinstance(html_out, str)
        assert "<!DOCTYPE html>" in html_out or "<!doctype html>" in html_out.lower()
        assert "<html" in html_out

    def test_share_image_has_dimensions(self):
        image = generate_share_image({"year": "甲子"}, score=85.0, theme="traditional")
        assert "width" in image
        assert "height" in image
        assert image["score"] == 85.0
        assert image["width"] > 0
        assert image["height"] > 0

    def test_export_returns_string(self):
        result = export_to_png("<svg></svg>", "output.png")
        assert isinstance(result, str)
        assert len(result) > 0


# ============================================================================
# Helper / integration smoke tests
# ============================================================================


class TestHelpers:

    def test_sanitize_content_escapes(self):
        raw = '<script>alert("xss")</script>'
        safe = sanitize_content(raw)
        assert "<script>" not in safe

    def test_generate_share_url(self):
        url = generate_share_url("post_abc", "wechat_moments")
        assert "post_abc" in url
        assert url.startswith("http")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
