"""
social.py — 阶段二十七：社交协作
===============================
功能:
  1. UserProfile      — 用户档案管理
  2. ContentPost      — 用户内容分享
  3. SocialGraph      — 关注/好友关系
  4. EngagementService — 点赞/评论/分享
  5. CollaborationSession — 八字图表协同分析会话
  6. FeedGenerator    — 个性化内容流
"""

from __future__ import annotations

import hashlib
import html
import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# 简单的内存存储（生产中应替换为数据库）
# ---------------------------------------------------------------------------

_STORE: Dict[str, Dict[str, Any]] = {
    "profiles": {},
    "posts": {},
    "follows": {},        # (follower_id, following_id) -> True
    "likes": {},          # post_id -> set of user_id
    "comments": {},       # comment_id -> comment dict
    "shares": {},         # share_id -> share dict
    "sessions": {},       # session_id -> session dict
    "annotations": {},    # session_id -> [annotation, ...]
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat() + "Z"


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# ---------------------------------------------------------------------------
# 1. UserProfile
# ---------------------------------------------------------------------------


class UserProfile:
    """用户档案管理"""

    @classmethod
    def get(cls, user_id: str) -> Optional[Dict[str, Any]]:
        return _STORE["profiles"].get(user_id)

    @classmethod
    def update(
        cls,
        user_id: str,
        display_name: Optional[str] = None,
        avatar: Optional[str] = None,
        bio: Optional[str] = None,
        preferences: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        existing = _STORE["profiles"].get(user_id)
        if existing is None:
            existing = {
                "user_id": user_id,
                "display_name": user_id,
                "avatar_url": "",
                "bio": "",
                "preferences": {
                    "theme": "light",
                    "notifications": True,
                    "language": "zh-CN",
                },
                "join_date": _now_iso(),
                "stats": {
                    "calculations_count": 0,
                    "shares_count": 0,
                    "likes_received": 0,
                },
            }
            _STORE["profiles"][user_id] = existing

        if display_name is not None:
            existing["display_name"] = display_name
        if avatar is not None:
            existing["avatar_url"] = avatar
        if bio is not None:
            existing["bio"] = bio
        if preferences is not None:
            existing["preferences"].update(preferences)
        existing["updated_at"] = _now_iso()
        return existing

    @classmethod
    def get_public(cls, user_id: str) -> Optional[Dict[str, Any]]:
        p = _STORE["profiles"].get(user_id)
        if p is None:
            return None
        return {
            "user_id": p["user_id"],
            "display_name": p["display_name"],
            "avatar_url": p["avatar_url"],
            "bio": p["bio"],
            "join_date": p["join_date"],
            "stats": dict(p["stats"]),
        }

    @classmethod
    def increment_stat(cls, user_id: str, stat_key: str, by: int = 1) -> None:
        p = _STORE["profiles"].get(user_id)
        if p is None:
            return
        if stat_key in p["stats"]:
            p["stats"][stat_key] += by


# ---------------------------------------------------------------------------
# 2. ContentPost
# ---------------------------------------------------------------------------


VALID_CONTENT_TYPES = {
    "bazi_share", "ziwei_share", "liuyao_share",
    "analysis_note", "question", "discussion",
}
VALID_VISIBILITY = {"public", "followers", "private"}


class ContentPost:
    """用户生成内容分享"""

    @classmethod
    def create(
        cls,
        user_id: str,
        record_id: Optional[str] = None,
        content_type: str = "discussion",
        title: str = "",
        body: str = "",
        tags: Optional[List[str]] = None,
        visibility: str = "public",
    ) -> Dict[str, Any]:
        if content_type not in VALID_CONTENT_TYPES:
            raise ValueError(f"Invalid content_type: {content_type}")
        if visibility not in VALID_VISIBILITY:
            raise ValueError(f"Invalid visibility: {visibility}")

        post = {
            "post_id": _new_id("post"),
            "user_id": user_id,
            "record_id": record_id,
            "content_type": content_type,
            "title": sanitize_content(title),
            "body": sanitize_content(body),
            "tags": list(tags or []),
            "visibility": visibility,
            "created_at": _now_iso(),
            "likes_count": 0,
            "comments_count": 0,
            "shares_count": 0,
            "views_count": 1,
        }
        _STORE["posts"][post["post_id"]] = post
        UserProfile.increment_stat(user_id, "calculations_count", 1)
        return post

    @classmethod
    def get(cls, post_id: str) -> Optional[Dict[str, Any]]:
        return _STORE["posts"].get(post_id)

    @classmethod
    def list_by_user(cls, user_id: str, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        items = [p for p in _STORE["posts"].values() if p["user_id"] == user_id]
        items.sort(key=lambda x: x["created_at"], reverse=True)
        return items[offset:offset + limit]

    @classmethod
    def list_feed(cls, user_id: str, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        following = SocialGraph.get_following(user_id)
        items = []
        for p in _STORE["posts"].values():
            if p["visibility"] == "private" and p["user_id"] != user_id:
                continue
            if p["visibility"] == "followers" and p["user_id"] not in following and p["user_id"] != user_id:
                continue
            # public 或自己的 followers/private 或正在关注的人内容
            if p["visibility"] == "public" or p["user_id"] in following or p["user_id"] == user_id:
                items.append(p)
        items.sort(key=lambda x: x["created_at"], reverse=True)
        return items[offset:offset + limit]

    @classmethod
    def list_popular(cls, category: Optional[str] = None, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        items = [p for p in _STORE["posts"].values() if p["visibility"] == "public"]
        if category:
            items = [p for p in items if p["content_type"] == category]
        items.sort(key=lambda x: (x["likes_count"] + x["comments_count"] * 2 + x["shares_count"] * 3), reverse=True)
        return items[offset:offset + limit]

    @classmethod
    def delete(cls, user_id: str, post_id: str) -> bool:
        p = _STORE["posts"].get(post_id)
        if p is None or p["user_id"] != user_id:
            return False
        del _STORE["posts"][post_id]
        return True


# ---------------------------------------------------------------------------
# 3. SocialGraph
# ---------------------------------------------------------------------------


class SocialGraph:
    """关注/好友关系"""

    @classmethod
    def follow(cls, follower_id: str, following_id: str) -> bool:
        if follower_id == following_id:
            return False
        key = (follower_id, following_id)
        _STORE["follows"][key] = True
        return True

    @classmethod
    def unfollow(cls, follower_id: str, following_id: str) -> bool:
        key = (follower_id, following_id)
        if key in _STORE["follows"]:
            del _STORE["follows"][key]
            return True
        return False

    @classmethod
    def get_followers(cls, user_id: str) -> List[str]:
        return [a for (a, b) in _STORE["follows"].keys() if b == user_id]

    @classmethod
    def get_following(cls, user_id: str) -> List[str]:
        return [b for (a, b) in _STORE["follows"].keys() if a == user_id]

    @classmethod
    def is_following(cls, a: str, b: str) -> bool:
        return (a, b) in _STORE["follows"]

    @classmethod
    def get_social_score(cls, user_id: str) -> float:
        followers = len(cls.get_followers(user_id))
        profile = UserProfile.get(user_id)
        likes = 0
        shares = 0
        if profile is not None:
            likes = profile["stats"].get("likes_received", 0)
            shares = profile["stats"].get("shares_count", 0)
        return float(followers * 10 + likes * 2 + shares * 5)


# ---------------------------------------------------------------------------
# 4. EngagementService
# ---------------------------------------------------------------------------


class EngagementService:
    """点赞/评论/分享"""

    @classmethod
    def like(cls, user_id: str, post_id: str) -> bool:
        post = _STORE["posts"].get(post_id)
        if post is None:
            return False
        liked = _STORE["likes"].setdefault(post_id, set())
        if user_id in liked:
            liked.discard(user_id)
            post["likes_count"] = max(0, post["likes_count"] - 1)
            return False
        liked.add(user_id)
        post["likes_count"] += 1
        UserProfile.increment_stat(post["user_id"], "likes_received", 1)
        return True

    @classmethod
    def unlike(cls, user_id: str, post_id: str) -> bool:
        post = _STORE["posts"].get(post_id)
        if post is None:
            return False
        liked = _STORE["likes"].setdefault(post_id, set())
        if user_id in liked:
            liked.discard(user_id)
            post["likes_count"] = max(0, post["likes_count"] - 1)
            return True
        return False

    @classmethod
    def comment(
        cls,
        user_id: str,
        post_id: str,
        text: str,
        parent_comment_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        post = _STORE["posts"].get(post_id)
        if post is None:
            raise ValueError(f"Post {post_id} not found")
        cid = _new_id("cmt")
        comment = {
            "comment_id": cid,
            "user_id": user_id,
            "post_id": post_id,
            "text": sanitize_content(text),
            "parent_comment_id": parent_comment_id,
            "created_at": _now_iso(),
        }
        _STORE["comments"][cid] = comment
        post["comments_count"] += 1
        return comment

    @classmethod
    def list_comments(cls, post_id: str, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        items = [c for c in _STORE["comments"].values() if c["post_id"] == post_id]
        items.sort(key=lambda x: x["created_at"])
        return items[offset:offset + limit]

    @classmethod
    def delete_comment(cls, user_id: str, comment_id: str) -> bool:
        c = _STORE["comments"].get(comment_id)
        if c is None or c["user_id"] != user_id:
            return False
        post = _STORE["posts"].get(c["post_id"])
        if post is not None and post["comments_count"] > 0:
            post["comments_count"] -= 1
        del _STORE["comments"][comment_id]
        return True

    @classmethod
    def share(cls, user_id: str, post_id: str, target_platform: str = "wechat_moments") -> Dict[str, Any]:
        post = _STORE["posts"].get(post_id)
        if post is None:
            raise ValueError(f"Post {post_id} not found")
        sid = _new_id("shr")
        share = {
            "share_id": sid,
            "user_id": user_id,
            "post_id": post_id,
            "platform": target_platform,
            "share_url": generate_share_url(post_id, target_platform),
            "created_at": _now_iso(),
        }
        _STORE["shares"][sid] = share
        post["shares_count"] += 1
        UserProfile.increment_stat(post["user_id"], "shares_count", 1)
        return share

    @classmethod
    def get_post_stats(cls, post_id: str) -> Dict[str, int]:
        post = _STORE["posts"].get(post_id)
        if post is None:
            return {"likes_count": 0, "comments_count": 0, "shares_count": 0, "views_count": 0}
        return {
            "likes_count": post["likes_count"],
            "comments_count": post["comments_count"],
            "shares_count": post["shares_count"],
            "views_count": post["views_count"],
        }


# ---------------------------------------------------------------------------
# 5. CollaborationSession
# ---------------------------------------------------------------------------


class CollaborationSession:
    """八字图表协同分析会话"""

    @classmethod
    def create_session(
        cls,
        owner_id: str,
        record_id: str,
        title: str,
        description: str = "",
        invited_user_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        session = {
            "session_id": _new_id("sess"),
            "owner_id": owner_id,
            "record_id": record_id,
            "title": title,
            "description": description,
            "collaborators": set([owner_id] + list(invited_user_ids or [])),
            "analyses": [],
            "created_at": _now_iso(),
        }
        _STORE["sessions"][session["session_id"]] = session
        _STORE["annotations"][session["session_id"]] = []
        return session

    @classmethod
    def get_session(cls, session_id: str) -> Optional[Dict[str, Any]]:
        s = _STORE["sessions"].get(session_id)
        if s is None:
            return None
        # 转换 collaborators 为可序列化 list
        return {**s, "collaborators": sorted(list(s["collaborators"]))}

    @classmethod
    def add_annotation(
        cls,
        session_id: str,
        user_id: str,
        pillar_index: int,
        annotation_text: str,
        color_hex: str = "#ffcc00",
        x_pos: float = 0.0,
        y_pos: float = 0.0,
    ) -> Dict[str, Any]:
        if session_id not in _STORE["sessions"]:
            raise ValueError(f"Session {session_id} not found")
        ann = {
            "annotation_id": _new_id("ann"),
            "session_id": session_id,
            "user_id": user_id,
            "pillar_index": pillar_index,
            "text": sanitize_content(annotation_text),
            "color_hex": color_hex,
            "x_pos": x_pos,
            "y_pos": y_pos,
            "created_at": _now_iso(),
        }
        _STORE["annotations"][session_id].append(ann)
        return ann

    @classmethod
    def list_annotations(cls, session_id: str) -> List[Dict[str, Any]]:
        return list(_STORE["annotations"].get(session_id, []))

    @classmethod
    def add_collaborator(cls, session_id: str, user_id: str) -> bool:
        s = _STORE["sessions"].get(session_id)
        if s is None:
            return False
        s["collaborators"].add(user_id)
        return True

    @classmethod
    def list_sessions_for_user(cls, user_id: str) -> List[Dict[str, Any]]:
        result = []
        for s in _STORE["sessions"].values():
            if user_id in s["collaborators"]:
                result.append({**s, "collaborators": sorted(list(s["collaborators"]))})
        result.sort(key=lambda x: x["created_at"], reverse=True)
        return result

    @classmethod
    def submit_analysis(cls, session_id: str, user_id: str, content: str) -> Dict[str, Any]:
        s = _STORE["sessions"].get(session_id)
        if s is None:
            raise ValueError(f"Session {session_id} not found")
        entry = {
            "analysis_id": _new_id("an"),
            "user_id": user_id,
            "content": sanitize_content(content),
            "created_at": _now_iso(),
        }
        s["analyses"].append(entry)
        return entry

    @classmethod
    def export_session(cls, session_id: str, format: str = "json") -> str:
        s = cls.get_session(session_id)
        if s is None:
            raise ValueError(f"Session {session_id} not found")
        payload = {
            "session": s,
            "annotations": cls.list_annotations(session_id),
            "exported_at": _now_iso(),
        }
        if format == "json":
            return json.dumps(payload, ensure_ascii=False, indent=2)
        if format == "html":
            # 简易 HTML 导出
            rows = []
            for ann in payload["annotations"]:
                rows.append(
                    f"<li>柱#{ann['pillar_index']}: {html.escape(ann['text'])} "
                    f"<span style='color:{ann['color_hex']}'>●</span></li>"
                )
            return (
                "<!DOCTYPE html><html><head><meta charset='utf-8'>"
                f"<title>{html.escape(s['title'])}</title></head><body>"
                f"<h1>{html.escape(s['title'])}</h1>"
                f"<p>{html.escape(s['description'])}</p>"
                f"<ul>{''.join(rows)}</ul>"
                "</body></html>"
            )
        raise ValueError(f"Unsupported format: {format}")


# ---------------------------------------------------------------------------
# 6. FeedGenerator
# ---------------------------------------------------------------------------


class FeedGenerator:
    """个性化内容流"""

    @classmethod
    def generate_feed(cls, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        followed = ContentPost.list_feed(user_id, limit=limit)
        if len(followed) >= limit:
            return followed
        # 用流行内容填充
        popular = ContentPost.list_popular(limit=limit)
        seen_ids = {p["post_id"] for p in followed}
        for p in popular:
            if p["post_id"] in seen_ids:
                continue
            followed.append(p)
            if len(followed) >= limit:
                break
        return followed[:limit]

    @classmethod
    def get_trending(cls, time_window_days: int = 7) -> List[Dict[str, Any]]:
        items = ContentPost.list_popular(limit=50)
        # 简单起见只按 engagement 排序；时间窗口过滤可在真实实现中添加
        return items

    @classmethod
    def get_recommended_for_user(cls, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        # 简易推荐：基于用户统计返回的内容
        items = ContentPost.list_popular(limit=limit * 2)
        # 去除用户自己的内容
        items = [p for p in items if p["user_id"] != user_id]
        return items[:limit]


# ---------------------------------------------------------------------------
# 7. Helper 函数
# ---------------------------------------------------------------------------


def sanitize_content(text: str) -> str:
    """基础内容消毒 — 去 HTML 标签和多余空白"""
    if text is None:
        return ""
    # 去除危险 HTML
    safe = html.escape(str(text))
    # 压缩空白
    safe = " ".join(safe.split())
    return safe


def generate_share_url(post_id: str, platform: str = "wechat_moments") -> str:
    """根据平台生成分享链接"""
    base = f"https://tengod.example.com/share/{post_id}"
    sig = hashlib.sha1(f"{post_id}|{platform}|secret".encode("utf-8")).hexdigest()[:8]
    return f"{base}?p={platform}&s={sig}"
