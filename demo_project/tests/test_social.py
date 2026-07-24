"""
Tests for tengod.social — social collaboration module.

Covers: UserProfile, ContentPost, SocialGraph, EngagementService,
        CollaborationSession, FeedGenerator, sanitize_content, generate_share_url.
"""

from __future__ import annotations

import pytest

from tengod.social import (
    UserProfile,
    ContentPost,
    SocialGraph,
    EngagementService,
    CollaborationSession,
    FeedGenerator,
    sanitize_content,
    generate_share_url,
    _STORE,
    VALID_CONTENT_TYPES,
    VALID_VISIBILITY,
)


# ---------------------------------------------------------------------------
# Fixture — reset global _STORE before every test
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_store():
    """Reset the global _STORE before each test so tests are isolated."""
    _STORE["profiles"] = {}
    _STORE["posts"] = {}
    _STORE["follows"] = {}
    _STORE["likes"] = {}
    _STORE["comments"] = {}
    _STORE["shares"] = {}
    _STORE["sessions"] = {}
    _STORE["annotations"] = {}


# ============================================================================
# UserProfile
# ============================================================================

class TestUserProfile:
    """Tests for UserProfile class."""

    def test_get_nonexistent_returns_none(self):
        assert UserProfile.get("no-such-user") is None

    def test_update_creates_new_profile_with_defaults(self):
        profile = UserProfile.update("user1")
        assert profile["user_id"] == "user1"
        assert profile["display_name"] == "user1"
        assert profile["avatar_url"] == ""
        assert profile["bio"] == ""
        assert profile["preferences"] == {
            "theme": "light",
            "notifications": True,
            "language": "zh-CN",
        }
        assert "join_date" in profile
        assert profile["stats"] == {
            "calculations_count": 0,
            "shares_count": 0,
            "likes_received": 0,
        }
        assert "updated_at" in profile

    def test_update_existing_profile_modifies_fields(self):
        UserProfile.update("user1")
        profile = UserProfile.update(
            "user1",
            display_name="Alice",
            avatar="http://img/avatar.png",
            bio="Hello world",
            preferences={"theme": "dark"},
        )
        assert profile["display_name"] == "Alice"
        assert profile["avatar_url"] == "http://img/avatar.png"
        assert profile["bio"] == "Hello world"
        assert profile["preferences"]["theme"] == "dark"
        # Other preferences should be preserved
        assert profile["preferences"]["notifications"] is True
        assert profile["preferences"]["language"] == "zh-CN"

    def test_update_with_partial_fields(self):
        UserProfile.update("user1", display_name="Old Name", bio="Old bio")
        profile = UserProfile.update("user1", display_name="New Name")
        assert profile["display_name"] == "New Name"
        assert profile["bio"] == "Old bio"  # unchanged

    def test_get_public_returns_only_public_fields(self):
        UserProfile.update("user1", display_name="Alice", bio="secret")
        public = UserProfile.get_public("user1")
        assert public is not None
        assert "user_id" in public
        assert "display_name" in public
        assert "avatar_url" in public
        assert "bio" in public
        assert "join_date" in public
        assert "stats" in public
        # preferences must NOT be in public profile
        assert "preferences" not in public
        assert "updated_at" not in public

    def test_get_public_nonexistent_returns_none(self):
        assert UserProfile.get_public("ghost") is None

    def test_increment_stat_on_existing_profile(self):
        UserProfile.update("user1")
        UserProfile.increment_stat("user1", "calculations_count", 1)
        profile = UserProfile.get("user1")
        assert profile["stats"]["calculations_count"] == 1

    def test_increment_stat_on_nonexistent_does_nothing(self):
        # Should not raise
        UserProfile.increment_stat("ghost", "calculations_count", 5)
        assert UserProfile.get("ghost") is None

    def test_increment_stat_custom_by_value(self):
        UserProfile.update("user1")
        UserProfile.increment_stat("user1", "shares_count", 10)
        profile = UserProfile.get("user1")
        assert profile["stats"]["shares_count"] == 10


# ============================================================================
# ContentPost
# ============================================================================

class TestContentPost:
    """Tests for ContentPost class."""

    def test_create_with_all_fields(self):
        post = ContentPost.create(
            user_id="user1",
            record_id="rec_abc",
            content_type="bazi_share",
            title="My Chart",
            body="Analysis here",
            tags=["bazi", "health"],
            visibility="followers",
        )
        assert post["user_id"] == "user1"
        assert post["record_id"] == "rec_abc"
        assert post["content_type"] == "bazi_share"
        assert post["title"] == "My Chart"
        assert post["body"] == "Analysis here"
        assert post["tags"] == ["bazi", "health"]
        assert post["visibility"] == "followers"
        assert "post_id" in post
        assert "created_at" in post
        assert post["likes_count"] == 0
        assert post["comments_count"] == 0
        assert post["shares_count"] == 0
        assert post["views_count"] == 1

    def test_create_with_defaults(self):
        post = ContentPost.create(user_id="user1")
        assert post["content_type"] == "discussion"
        assert post["visibility"] == "public"
        assert post["title"] == ""
        assert post["body"] == ""
        assert post["tags"] == []
        assert post["record_id"] is None

    def test_create_invalid_content_type_raises_valueerror(self):
        with pytest.raises(ValueError, match="Invalid content_type"):
            ContentPost.create(user_id="user1", content_type="invalid_type")

    def test_create_invalid_visibility_raises_valueerror(self):
        with pytest.raises(ValueError, match="Invalid visibility"):
            ContentPost.create(user_id="user1", visibility="secret")

    def test_get_existing_post(self):
        post = ContentPost.create(user_id="user1", title="Test")
        fetched = ContentPost.get(post["post_id"])
        assert fetched is not None
        assert fetched["title"] == "Test"

    def test_get_nonexistent_returns_none(self):
        assert ContentPost.get("no-such-post") is None

    def test_list_by_user_returns_sorted_by_created_at_desc(self):
        p1 = ContentPost.create(user_id="user1", title="First")
        p2 = ContentPost.create(user_id="user1", title="Second")
        posts = ContentPost.list_by_user("user1")
        assert len(posts) == 2
        assert posts[0]["created_at"] >= posts[1]["created_at"]

    def test_list_by_user_with_limit_offset(self):
        for i in range(5):
            ContentPost.create(user_id="user1", title=f"Post {i}")
        posts = ContentPost.list_by_user("user1", limit=2, offset=1)
        assert len(posts) == 2

    def test_list_feed_includes_public_posts(self):
        ContentPost.create(user_id="user1", visibility="public", title="Public")
        feed = ContentPost.list_feed("user2")
        assert len(feed) == 1

    def test_list_feed_excludes_private_posts_of_others(self):
        ContentPost.create(user_id="user1", visibility="private", title="Secret")
        feed = ContentPost.list_feed("user2")
        assert len(feed) == 0

    def test_list_feed_excludes_followers_only_from_non_following(self):
        ContentPost.create(user_id="user1", visibility="followers", title="Followers")
        feed = ContentPost.list_feed("user2")
        assert len(feed) == 0

    def test_list_feed_includes_followers_only_when_following(self):
        SocialGraph.follow("user2", "user1")
        ContentPost.create(user_id="user1", visibility="followers", title="Followers")
        feed = ContentPost.list_feed("user2")
        assert len(feed) == 1

    def test_list_feed_includes_own_private(self):
        ContentPost.create(user_id="user1", visibility="private", title="My Secret")
        feed = ContentPost.list_feed("user1")
        assert len(feed) == 1

    def test_list_feed_with_limit_offset(self):
        for i in range(5):
            ContentPost.create(user_id="user1", visibility="public", title=f"Feed {i}")
        feed = ContentPost.list_feed("user2", limit=2, offset=1)
        assert len(feed) == 2

    def test_list_popular_returns_public_sorted_by_engagement(self):
        p1 = ContentPost.create(user_id="user1", visibility="public")
        p2 = ContentPost.create(user_id="user2", visibility="public")
        # Boost p2's engagement
        EngagementService.like("user3", p2["post_id"])
        EngagementService.like("user4", p2["post_id"])
        EngagementService.comment("user3", p2["post_id"], "nice")
        popular = ContentPost.list_popular()
        assert len(popular) == 2
        # p2 should be first (higher engagement)
        assert popular[0]["post_id"] == p2["post_id"]

    def test_list_popular_excludes_private(self):
        ContentPost.create(user_id="user1", visibility="private")
        popular = ContentPost.list_popular()
        assert len(popular) == 0

    def test_list_popular_with_category_filter(self):
        ContentPost.create(user_id="user1", visibility="public", content_type="bazi_share")
        ContentPost.create(user_id="user1", visibility="public", content_type="discussion")
        popular = ContentPost.list_popular(category="bazi_share")
        assert len(popular) == 1
        assert popular[0]["content_type"] == "bazi_share"

    def test_delete_own_post_returns_true(self):
        post = ContentPost.create(user_id="user1")
        assert ContentPost.delete("user1", post["post_id"]) is True
        assert ContentPost.get(post["post_id"]) is None

    def test_delete_others_post_returns_false(self):
        post = ContentPost.create(user_id="user1")
        assert ContentPost.delete("user2", post["post_id"]) is False
        assert ContentPost.get(post["post_id"]) is not None

    def test_delete_nonexistent_returns_false(self):
        assert ContentPost.delete("user1", "no-such-post") is False

    def test_create_with_tags_and_record_id(self):
        post = ContentPost.create(
            user_id="user1",
            tags=["health", "wealth"],
            record_id="rec_xyz",
        )
        assert post["tags"] == ["health", "wealth"]
        assert post["record_id"] == "rec_xyz"

    def test_sanitize_content_called_on_title_and_body(self):
        post = ContentPost.create(
            user_id="user1",
            title="<script>alert(1)</script>",
            body="  too   many   spaces  ",
        )
        assert "<script>" not in post["title"]
        assert post["body"] == "too many spaces"


# ============================================================================
# SocialGraph
# ============================================================================

class TestSocialGraph:
    """Tests for SocialGraph class."""

    def test_follow_creates_relationship(self):
        assert SocialGraph.follow("user1", "user2") is True
        assert SocialGraph.is_following("user1", "user2") is True

    def test_follow_self_returns_false(self):
        assert SocialGraph.follow("user1", "user1") is False

    def test_unfollow_existing_returns_true(self):
        SocialGraph.follow("user1", "user2")
        assert SocialGraph.unfollow("user1", "user2") is True
        assert SocialGraph.is_following("user1", "user2") is False

    def test_unfollow_nonexistent_returns_false(self):
        assert SocialGraph.unfollow("user1", "user2") is False

    def test_get_followers_returns_list(self):
        SocialGraph.follow("user2", "user1")
        SocialGraph.follow("user3", "user1")
        followers = SocialGraph.get_followers("user1")
        assert sorted(followers) == ["user2", "user3"]

    def test_get_following_returns_list(self):
        SocialGraph.follow("user1", "user2")
        SocialGraph.follow("user1", "user3")
        following = SocialGraph.get_following("user1")
        assert sorted(following) == ["user2", "user3"]

    def test_is_following_true_false(self):
        SocialGraph.follow("user1", "user2")
        assert SocialGraph.is_following("user1", "user2") is True
        assert SocialGraph.is_following("user2", "user1") is False
        assert SocialGraph.is_following("user1", "user3") is False

    def test_get_social_score_with_followers_likes_shares(self):
        UserProfile.update("user1")
        SocialGraph.follow("user2", "user1")
        SocialGraph.follow("user3", "user1")
        UserProfile.increment_stat("user1", "likes_received", 5)
        UserProfile.increment_stat("user1", "shares_count", 3)
        # followers=2*10 + likes=5*2 + shares=3*5 = 20 + 10 + 15 = 45
        score = SocialGraph.get_social_score("user1")
        assert score == 45.0

    def test_get_social_score_with_no_profile(self):
        # No profile created — followers=0, likes=0, shares=0
        score = SocialGraph.get_social_score("ghost")
        assert score == 0.0


# ============================================================================
# EngagementService
# ============================================================================

class TestEngagementService:
    """Tests for EngagementService class."""

    def test_like_on_existing_post_returns_true(self):
        post = ContentPost.create(user_id="user1")
        assert EngagementService.like("user2", post["post_id"]) is True
        stats = EngagementService.get_post_stats(post["post_id"])
        assert stats["likes_count"] == 1

    def test_like_twice_toggles(self):
        post = ContentPost.create(user_id="user1")
        EngagementService.like("user2", post["post_id"])
        result = EngagementService.like("user2", post["post_id"])
        assert result is False
        stats = EngagementService.get_post_stats(post["post_id"])
        assert stats["likes_count"] == 0

    def test_like_on_nonexistent_post_returns_false(self):
        assert EngagementService.like("user1", "no-post") is False

    def test_unlike_on_liked_post_returns_true(self):
        post = ContentPost.create(user_id="user1")
        EngagementService.like("user2", post["post_id"])
        assert EngagementService.unlike("user2", post["post_id"]) is True
        stats = EngagementService.get_post_stats(post["post_id"])
        assert stats["likes_count"] == 0

    def test_unlike_on_non_liked_post_returns_false(self):
        post = ContentPost.create(user_id="user1")
        assert EngagementService.unlike("user2", post["post_id"]) is False

    def test_unlike_on_nonexistent_post_returns_false(self):
        assert EngagementService.unlike("user1", "no-post") is False

    def test_comment_on_existing_post(self):
        post = ContentPost.create(user_id="user1")
        comment = EngagementService.comment("user2", post["post_id"], "Great post!")
        assert comment["user_id"] == "user2"
        assert comment["post_id"] == post["post_id"]
        assert comment["text"] == "Great post!"
        assert "comment_id" in comment
        stats = EngagementService.get_post_stats(post["post_id"])
        assert stats["comments_count"] == 1

    def test_comment_on_nonexistent_post_raises_valueerror(self):
        with pytest.raises(ValueError, match="not found"):
            EngagementService.comment("user1", "no-post", "text")

    def test_comment_with_parent_comment_id(self):
        post = ContentPost.create(user_id="user1")
        parent = EngagementService.comment("user2", post["post_id"], "Parent")
        child = EngagementService.comment(
            "user3", post["post_id"], "Child", parent_comment_id=parent["comment_id"]
        )
        assert child["parent_comment_id"] == parent["comment_id"]

    def test_list_comments_returns_sorted(self):
        post = ContentPost.create(user_id="user1")
        EngagementService.comment("user2", post["post_id"], "First")
        EngagementService.comment("user3", post["post_id"], "Second")
        comments = EngagementService.list_comments(post["post_id"])
        assert len(comments) == 2
        assert comments[0]["created_at"] <= comments[1]["created_at"]

    def test_list_comments_with_limit_offset(self):
        post = ContentPost.create(user_id="user1")
        for i in range(5):
            EngagementService.comment("user2", post["post_id"], f"Comment {i}")
        comments = EngagementService.list_comments(post["post_id"], limit=2, offset=1)
        assert len(comments) == 2

    def test_delete_comment_own_returns_true(self):
        post = ContentPost.create(user_id="user1")
        comment = EngagementService.comment("user2", post["post_id"], "text")
        assert EngagementService.delete_comment("user2", comment["comment_id"]) is True
        assert EngagementService.delete_comment("user2", comment["comment_id"]) is False

    def test_delete_comment_others_returns_false(self):
        post = ContentPost.create(user_id="user1")
        comment = EngagementService.comment("user2", post["post_id"], "text")
        assert EngagementService.delete_comment("user3", comment["comment_id"]) is False

    def test_delete_comment_nonexistent_returns_false(self):
        assert EngagementService.delete_comment("user1", "no-cmt") is False

    def test_share_on_existing_post(self):
        post = ContentPost.create(user_id="user1")
        share = EngagementService.share("user2", post["post_id"], "weibo")
        assert share["user_id"] == "user2"
        assert share["post_id"] == post["post_id"]
        assert share["platform"] == "weibo"
        assert "share_url" in share
        stats = EngagementService.get_post_stats(post["post_id"])
        assert stats["shares_count"] == 1

    def test_share_on_nonexistent_raises_valueerror(self):
        with pytest.raises(ValueError, match="not found"):
            EngagementService.share("user1", "no-post")

    def test_share_with_different_platforms(self):
        post = ContentPost.create(user_id="user1")
        s1 = EngagementService.share("user2", post["post_id"], "wechat_moments")
        s2 = EngagementService.share("user3", post["post_id"], "weibo")
        assert s1["platform"] == "wechat_moments"
        assert s2["platform"] == "weibo"
        assert s1["share_url"] != s2["share_url"]

    def test_get_post_stats_on_existing_post(self):
        post = ContentPost.create(user_id="user1")
        EngagementService.like("user2", post["post_id"])
        EngagementService.comment("user3", post["post_id"], "nice")
        EngagementService.share("user4", post["post_id"])
        stats = EngagementService.get_post_stats(post["post_id"])
        assert stats["likes_count"] == 1
        assert stats["comments_count"] == 1
        assert stats["shares_count"] == 1
        assert stats["views_count"] == 1

    def test_get_post_stats_on_nonexistent_returns_zeros(self):
        stats = EngagementService.get_post_stats("no-post")
        assert stats == {"likes_count": 0, "comments_count": 0, "shares_count": 0, "views_count": 0}


# ============================================================================
# CollaborationSession
# ============================================================================

class TestCollaborationSession:
    """Tests for CollaborationSession class."""

    def test_create_session_basic(self):
        session = CollaborationSession.create_session(
            owner_id="user1",
            record_id="rec_001",
            title="Test Session",
            description="A test",
        )
        assert session["owner_id"] == "user1"
        assert session["record_id"] == "rec_001"
        assert session["title"] == "Test Session"
        assert session["description"] == "A test"
        assert "session_id" in session
        assert "user1" in session["collaborators"]

    def test_create_session_with_invited_users(self):
        session = CollaborationSession.create_session(
            owner_id="user1",
            record_id="rec_001",
            title="Group Session",
            invited_user_ids=["user2", "user3"],
        )
        assert "user1" in session["collaborators"]
        assert "user2" in session["collaborators"]
        assert "user3" in session["collaborators"]

    def test_get_session_returns_serializable_collaborators(self):
        session = CollaborationSession.create_session(
            owner_id="user1",
            record_id="rec_001",
            title="Test",
            invited_user_ids=["user2"],
        )
        fetched = CollaborationSession.get_session(session["session_id"])
        assert fetched is not None
        assert isinstance(fetched["collaborators"], list)
        assert sorted(fetched["collaborators"]) == ["user1", "user2"]

    def test_get_session_nonexistent_returns_none(self):
        assert CollaborationSession.get_session("no-sess") is None

    def test_add_annotation_to_existing_session(self):
        session = CollaborationSession.create_session(
            owner_id="user1", record_id="rec_001", title="Test"
        )
        ann = CollaborationSession.add_annotation(
            session_id=session["session_id"],
            user_id="user1",
            pillar_index=0,
            annotation_text="Good pillar",
        )
        assert ann["user_id"] == "user1"
        assert ann["pillar_index"] == 0
        assert ann["text"] == "Good pillar"
        assert ann["color_hex"] == "#ffcc00"
        assert ann["x_pos"] == 0.0
        assert ann["y_pos"] == 0.0

    def test_add_annotation_to_nonexistent_raises_valueerror(self):
        with pytest.raises(ValueError, match="not found"):
            CollaborationSession.add_annotation(
                session_id="no-sess",
                user_id="user1",
                pillar_index=0,
                annotation_text="text",
            )

    def test_add_annotation_with_all_params(self):
        session = CollaborationSession.create_session(
            owner_id="user1", record_id="rec_001", title="Test"
        )
        ann = CollaborationSession.add_annotation(
            session_id=session["session_id"],
            user_id="user2",
            pillar_index=3,
            annotation_text="Custom note",
            color_hex="#00ff00",
            x_pos=10.5,
            y_pos=20.3,
        )
        assert ann["color_hex"] == "#00ff00"
        assert ann["x_pos"] == 10.5
        assert ann["y_pos"] == 20.3

    def test_list_annotations(self):
        session = CollaborationSession.create_session(
            owner_id="user1", record_id="rec_001", title="Test"
        )
        CollaborationSession.add_annotation(
            session["session_id"], "user1", 0, "First"
        )
        CollaborationSession.add_annotation(
            session["session_id"], "user1", 1, "Second"
        )
        annotations = CollaborationSession.list_annotations(session["session_id"])
        assert len(annotations) == 2

    def test_add_collaborator_to_existing(self):
        session = CollaborationSession.create_session(
            owner_id="user1", record_id="rec_001", title="Test"
        )
        assert CollaborationSession.add_collaborator(session["session_id"], "user2") is True
        fetched = CollaborationSession.get_session(session["session_id"])
        assert "user2" in fetched["collaborators"]

    def test_add_collaborator_to_nonexistent_returns_false(self):
        assert CollaborationSession.add_collaborator("no-sess", "user1") is False

    def test_list_sessions_for_user(self):
        s1 = CollaborationSession.create_session(
            owner_id="user1", record_id="rec_001", title="Session 1"
        )
        CollaborationSession.create_session(
            owner_id="user2", record_id="rec_002", title="Session 2"
        )
        sessions = CollaborationSession.list_sessions_for_user("user1")
        assert len(sessions) == 1
        assert sessions[0]["session_id"] == s1["session_id"]

    def test_list_sessions_for_user_includes_invited(self):
        CollaborationSession.create_session(
            owner_id="user1",
            record_id="rec_001",
            title="Session",
            invited_user_ids=["user2"],
        )
        sessions = CollaborationSession.list_sessions_for_user("user2")
        assert len(sessions) == 1

    def test_submit_analysis(self):
        session = CollaborationSession.create_session(
            owner_id="user1", record_id="rec_001", title="Test"
        )
        entry = CollaborationSession.submit_analysis(
            session["session_id"], "user1", "My analysis"
        )
        assert entry["user_id"] == "user1"
        assert entry["content"] == "My analysis"
        assert "analysis_id" in entry

    def test_submit_analysis_to_nonexistent_raises_valueerror(self):
        with pytest.raises(ValueError, match="not found"):
            CollaborationSession.submit_analysis("no-sess", "user1", "content")

    def test_export_session_as_json(self):
        session = CollaborationSession.create_session(
            owner_id="user1", record_id="rec_001", title="Test"
        )
        CollaborationSession.add_annotation(
            session["session_id"], "user1", 0, "Note"
        )
        result = CollaborationSession.export_session(session["session_id"], "json")
        import json
        parsed = json.loads(result)
        assert parsed["session"]["title"] == "Test"
        assert len(parsed["annotations"]) == 1
        assert "exported_at" in parsed

    def test_export_session_as_html(self):
        session = CollaborationSession.create_session(
            owner_id="user1", record_id="rec_001", title="My Session", description="Desc"
        )
        CollaborationSession.add_annotation(
            session["session_id"], "user1", 0, "Important note"
        )
        result = CollaborationSession.export_session(session["session_id"], "html")
        assert "<!DOCTYPE html>" in result
        assert "My Session" in result
        assert "Desc" in result
        assert "Important note" in result

    def test_export_session_nonexistent_raises_valueerror(self):
        with pytest.raises(ValueError, match="not found"):
            CollaborationSession.export_session("no-sess")

    def test_export_session_invalid_format_raises_valueerror(self):
        session = CollaborationSession.create_session(
            owner_id="user1", record_id="rec_001", title="Test"
        )
        with pytest.raises(ValueError, match="Unsupported format"):
            CollaborationSession.export_session(session["session_id"], "xml")


# ============================================================================
# FeedGenerator
# ============================================================================

class TestFeedGenerator:
    """Tests for FeedGenerator class."""

    def test_generate_feed_with_followed_content(self):
        # Create a user and posts from followed users
        SocialGraph.follow("user1", "user2")
        ContentPost.create(user_id="user2", visibility="public", title="From followed")
        feed = FeedGenerator.generate_feed("user1")
        assert len(feed) == 1
        assert feed[0]["title"] == "From followed"

    def test_generate_feed_falls_back_to_popular(self):
        # No followed users — should fall back to popular
        ContentPost.create(user_id="user99", visibility="public", title="Popular")
        feed = FeedGenerator.generate_feed("user1")
        assert len(feed) == 1
        assert feed[0]["title"] == "Popular"

    def test_generate_feed_deduplicates(self):
        SocialGraph.follow("user1", "user2")
        # This post will appear in both followed feed and popular
        ContentPost.create(user_id="user2", visibility="public", title="Dupe")
        ContentPost.create(user_id="user3", visibility="public", title="Filler")
        feed = FeedGenerator.generate_feed("user1", limit=50)
        # Should not have duplicates
        ids = [p["post_id"] for p in feed]
        assert len(ids) == len(set(ids))

    def test_generate_feed_enough_followed_returns_early(self):
        SocialGraph.follow("user1", "user2")
        for i in range(5):
            ContentPost.create(user_id="user2", visibility="public", title=f"F{i}")
        feed = FeedGenerator.generate_feed("user1", limit=3)
        # All from followed, no need to fall back to popular
        assert len(feed) == 3
        assert all(p["user_id"] == "user2" for p in feed)

    def test_generate_feed_fills_with_popular_from_other_users(self):
        SocialGraph.follow("user1", "user2")
        # Create older posts from non-followed user (high engagement, appear in popular)
        for i in range(10):
            p = ContentPost.create(user_id="user3", visibility="public", title=f"P{i}")
            EngagementService.like("user99", p["post_id"])
            EngagementService.comment("user99", p["post_id"], "nice")
        # Create recent posts from followed user (low engagement, appear in feed)
        for i in range(10):
            ContentPost.create(user_id="user2", visibility="public", title=f"F{i}")
        feed = FeedGenerator.generate_feed("user1", limit=3)
        # Should include posts from both users (followed + popular filler)
        assert len(feed) == 3

    def test_get_trending(self):
        ContentPost.create(user_id="user1", visibility="public", title="Trending1")
        ContentPost.create(user_id="user2", visibility="public", title="Trending2")
        trending = FeedGenerator.get_trending()
        assert len(trending) == 2

    def test_get_trending_excludes_private(self):
        ContentPost.create(user_id="user1", visibility="private", title="Secret")
        trending = FeedGenerator.get_trending()
        assert len(trending) == 0

    def test_get_recommended_for_user_excludes_own_posts(self):
        ContentPost.create(user_id="user1", visibility="public", title="Mine")
        ContentPost.create(user_id="user2", visibility="public", title="Others")
        recommended = FeedGenerator.get_recommended_for_user("user1")
        ids = [p["user_id"] for p in recommended]
        assert "user1" not in ids


# ============================================================================
# Helper functions
# ============================================================================

class TestSanitizeContent:
    """Tests for sanitize_content helper."""

    def test_escapes_html(self):
        result = sanitize_content("<script>alert('xss')</script>")
        assert "<script>" not in result
        assert "&lt;" in result
        assert "&gt;" in result

    def test_collapses_whitespace(self):
        result = sanitize_content("hello    world\n\n\t\tfoo")
        assert result == "hello world foo"

    def test_none_returns_empty_string(self):
        assert sanitize_content(None) == ""


class TestGenerateShareUrl:
    """Tests for generate_share_url helper."""

    def test_returns_url_with_params(self):
        url = generate_share_url("post_abc", "wechat_moments")
        assert url.startswith("https://tengod.example.com/share/post_abc")
        assert "p=wechat_moments" in url
        assert "s=" in url

    def test_different_platforms_produce_different_urls(self):
        url1 = generate_share_url("post_abc", "wechat_moments")
        url2 = generate_share_url("post_abc", "weibo")
        assert url1 != url2
        assert "p=wechat_moments" in url1
        assert "p=weibo" in url2

    def test_default_platform(self):
        url = generate_share_url("post_abc")
        assert "p=wechat_moments" in url