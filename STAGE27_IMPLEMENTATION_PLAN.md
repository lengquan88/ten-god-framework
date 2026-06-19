# 阶段二十七：社交协作 — 技术实现方案

> 目标：激活用户互动，提升平台粘性（命盘分享/案例对比公开/社区评论/收藏关注）
> 依赖：现有 `auth.py`（用户认证）、`data_store.py`（PostgreSQL）
> 预计工作量：2-3 人/周

---

## 27.0 架构总览

```
         用户
          │
    ┌─────┴─────┐
    ▼           ▼
  分享命盘     案例对比公开
 (加密链接)     (匿名化页面)
    │           │
    ▼           ▼
  收藏/关注     社区评论
(个人收藏夹)  (点赞/举报)
    │           │
    └─────┬─────┘
          ▼
     /api/share/*
    /api/social/*
    (auth.py: JWT 认证)
          │
          ▼
    PostgreSQL
  share_links / case_comments / user_follows / favorites
```

---

## 27.1 命盘分享（1天）

### 数据库模型

```python
# 新增表: share_links
class ShareLink(Base):
    __tablename__ = "share_links"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)  # 随机 token，URL 安全
    share_type: Mapped[str] = mapped_column(String(16))  # "bazi_record" / "case" / "comparison"
    target_id: Mapped[int] = mapped_column(Integer, index=True)  # 对应的 record_id / case_id
    owner_id: Mapped[int] = mapped_column(Integer, index=True)  # 创建者 user_id

    # 访问控制
    is_public: Mapped[bool] = mapped_column(default=True)  # 任何人可访问
    requires_password: Mapped[bool] = mapped_column(default=False)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=True)  # PBKDF2

    # 元数据
    view_count: Mapped[int] = mapped_column(default=0)
    expires_at: Mapped[datetime] = mapped_column(nullable=True)  # None = 永久
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    # 展示配置（隐私控制）
    show_pillars: Mapped[bool] = mapped_column(default=True)  # 显示四柱
    show_wuxing: Mapped[bool] = mapped_column(default=True)  # 显示五行
    show_dayun: Mapped[bool] = mapped_column(default=True)  # 显示大运
    show_personal_info: Mapped[bool] = mapped_column(default=False)  # 不显示姓名/生日
```

### API 端点

```
POST   /api/share/create            {share_type, target_id, is_public, password, expires_days, display_config}
       → 返回 {share_url, token}

GET    /api/share/{token}           （公开端点，无需登录）
       → 返回 {share_type, display_config, content_data, expires_at}

POST   /api/share/{token}/view      记录访问（+1 view_count，IP 去重）

DELETE /api/share/{token}           仅 owner 可删除

GET    /api/share/my/list           我的分享列表（分页）
```

### 分享页面

`web_console/share-view.html`:
```
访问 URL: https://域名/share/{token}
页面内容:
  ┌─ 十神架构 [logo]
  │  命盘分享（匿名显示，根据 display_config 展示）
  │
  │  四柱展示（无姓名/生日，除非 share 允许）
  │  五行分布
  │  格局判断
  │  大运流年
  │
  └─ [复制分享链接] [点赞]
     浏览次数: 1234
     分享者: 用户匿名ID or 不显示
```

### Token 生成策略

```python
import secrets, base64
def generate_share_token():
    """生成 URL 安全的 32 字符 token"""
    raw = secrets.token_bytes(24)
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()
```

---

## 27.2 案例对比公开页（0.5天）

### 数据库模型

```python
# 复用 share_links 表，share_type="comparison"
# target_id 存第一个 case_id，通过额外表存对比关系
class ComparisonShare(Base):
    __tablename__ = "comparison_shares"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    share_link_id: Mapped[int] = mapped_column(Integer, index=True)
    case_a_id: Mapped[int]
    case_b_id: Mapped[int]
    notes: Mapped[str] = mapped_column(Text, nullable=True)  # 对比说明文字
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
```

### API 端点

```
POST   /api/share/comparison        {case_a_id, case_b_id, notes, display_config}
       → 返回 {share_url, token}

GET    /api/share/comparison/{token}  （公开）
       → 返回 {case_a, case_b, notes, similarity_score, wuxing_diff}

GET    /api/compare/{case_a_id}/{case_b_id} （已登录用户，内部对比视图）
       → 返回两份命盘的结构化对比数据
```

### 对比页面设计

```
URL: /compare/{case_a_token}/{case_b_token}

┌─ 案例 A ─────────────┐  ┌─ 案例 B ─────────────┐
│ 标题: 企业家命盘       │  │ 标题: 运动员命盘      │
│ 日主: 辛金             │  │ 日主: 甲木            │
│ 格局: 伤官格           │  │ 格局: 正官格          │
│ 五行: 金旺 水相 火次   │  │ 五行: 木旺 金缺 土次  │
│                       │  │                       │
└──────────────────────┘  └──────────────────────┘

━ 五行相似度: 72% ◀━━━━━━━━━━━━━━━▅

━ 相似点 ▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁
  · 日主均得月令
  · 天干有合化

━ 差异点 ▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁
  · A 伤官格 vs B 正官格
  · A 金旺 vs B 木旺

  [分享此对比]  [收藏对比]
```

---

## 27.3 收藏与关注（0.5天）

### 数据库模型

```python
class Favorite(Base):
    """收藏夹"""
    __tablename__ = "favorites"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    item_type: Mapped[str] = mapped_column(String(16))  # "case" / "bazi_record" / "comparison"
    item_id: Mapped[int] = mapped_column(Integer)
    folder_name: Mapped[str] = mapped_column(String(64), default="默认收藏夹")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (Index("idx_fav_user_item", "user_id", "item_type", "item_id", unique=True),)

class UserFollow(Base):
    """用户关注关系（A 关注 B）"""
    __tablename__ = "user_follows"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    follower_id: Mapped[int] = mapped_column(Integer, index=True)  # 关注者 A
    following_id: Mapped[int] = mapped_column(Integer, index=True)  # 被关注者 B
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (Index("idx_follow_pair", "follower_id", "following_id", unique=True),)
```

### API 端点

```
POST   /api/social/favorite            {item_type, item_id, folder_name}
DELETE /api/social/favorite/{item_type}/{item_id}
GET    /api/social/favorites?folder_name=X&limit=20&offset=0
GET    /api/social/folders             我的收藏夹列表

POST   /api/social/follow/{user_id}    关注某人
POST   /api/social/unfollow/{user_id}  取消关注
GET    /api/social/following           我关注的人列表
GET    /api/social/followers           关注我的人列表
```

---

## 27.4 社区评论（1天）

### 数据库模型

```python
class CaseComment(Base):
    """案例评论"""
    __tablename__ = "case_comments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(Integer, index=True)
    author_id: Mapped[int] = mapped_column(Integer, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)  # 评论内容

    # 互动数据
    like_count: Mapped[int] = mapped_column(default=0)

    # 状态
    status: Mapped[str] = mapped_column(String(16), default="active")  # active/deleted/reported/hidden
    report_count: Mapped[int] = mapped_column(default=0)  # 被举报次数

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, onupdate=lambda: datetime.now(timezone.utc))

class CommentLike(Base):
    """评论点赞记录（防重复点赞）"""
    __tablename__ = "comment_likes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    comment_id: Mapped[int] = mapped_column(Integer, index=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (Index("idx_comment_like_unique", "comment_id", "user_id", unique=True),)

class CommentReport(Base):
    """评论举报"""
    __tablename__ = "comment_reports"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    comment_id: Mapped[int] = mapped_column(Integer, index=True)
    reporter_id: Mapped[int] = mapped_column(Integer, index=True)
    reason: Mapped[str] = mapped_column(String(32))  # spam/offensive/inaccurate/other
    detail: Mapped[str] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
```

### API 端点

```
POST   /api/cases/{case_id}/comments       {content}                → 发布评论
GET    /api/cases/{case_id}/comments?limit=20&offset=0              → 评论列表（按热度/时间排序）
DELETE /api/cases/comments/{comment_id}                              → 删除自己的评论
POST   /api/cases/comments/{comment_id}/like                         → 点赞/取消点赞
POST   /api/cases/comments/{comment_id}/report    {reason, detail}  → 举报
```

### 内容安全策略

```
1. 发布前校验: content 非空，长度 ≤ 2000 字符
2. 敏感词过滤: 内置敏感词表（政治/色情/辱骂），命中则标记为 "hidden"
3. 举报阈值: report_count ≥ 3 自动隐藏（需管理员二次审核）
4. 频率限制: 同一用户 5 分钟内最多发布 10 条评论
5. 管理员权限: admin 可删除任意评论
```

---

## 27.5 前端集成（0.5天）

### 修改 `web_console/index.html`

```
新增页面:
  · 分享详情页（/share/{token}）
  · 案例对比页（/compare/{a}/{b}）
  · 我的收藏（/profile/favorites）
  · 我的关注（/profile/follows）

新增交互:
  · 案例卡片增加 [分享] [收藏] [对比] 按钮
  · 评论区 UI（类似 GitHub 评论样式）
  · 点赞动画
  · 首页增加 [关注的用户新案例] 模块
```

---

## 27.6 文件结构汇总

```
新增:
  web_console/share-view.html          # 命盘分享查看页（公开）
  web_console/social.js                # 收藏/关注/评论前端逻辑

修改:
  tengod/data_store.py                 # ShareLink / ComparisonShare / Favorite / UserFollow /
                                       # CaseComment / CommentLike / CommentReport 共7张表 + 方法
  tengod/api_server.py                 # /api/share/* + /api/social/* 共约 15 个端点
  web_console/index.html               # 增加收藏/关注/对比/分享按钮与评论区

测试:
  tests/test_social_api.py
```

---

## 27.7 实施顺序

```
第1天:   分享功能（share_links 表 + API + 分享页）
第2天:   收藏/关注 + 评论系统
第3天:   对比页 + 前端集成 + 内容安全 + 测试
```

---

## 27.8 风险与缓解

| 风险 | 概率 | 影响 | 缓解方案 |
|------|------|------|---------|
| 分享链接暴露隐私数据 | 高 | 高 | 默认隐藏个人信息（姓名/生日），显式配置 display_config |
| 评论区出现攻击性内容 | 高 | 中 | 敏感词过滤 + 举报阈值 + 管理员审核 + 频率限制 |
| 刷赞/机器人互动 | 中 | 低 | 每用户每评论仅一次点赞（唯一索引约束） |
| 分享链接被滥用（SEO 垃圾） | 中 | 低 | 可配置过期时间 + 浏览次数统计，异常分享自动标记 |
| Token 碰撞（两个分享同 token） | 极低 | 高 | 数据库唯一索引 + 碰撞检测重试 |
