# 阶段二十六：管理后台 — 技术实现方案

> 目标：为运营团队提供数据管理与运营工具（用户管理/案例审核/数据统计/系统配置）
> 依赖：现有 `auth.py`（admin 角色）、`data_store.py`（PostgreSQL 数据）
> 预计工作量：2-3 人/周

---

## 26.0 架构总览

```
       运营人员 / 管理员
              │
     ┌────────▼─────────┐
     │   管理后台 Web UI   │ (独立页面，admin only，JWT 保护)
     │  菜单:用户/审核/统计/配置 │
     └────────┬──────────┘
              ▼
        /api/admin/*
       (auth.py: admin_only)
              │
     ┌────────┼────────┬────────┬────────┐
     ▼        ▼        ▼        ▼        ▼
   用户管理  案例审核  数据统计  系统配置  日志审计
    (CRUD)    (队列)    (报表)   (开关)   (只读查看)
     │         │        │         │         │
     └─────────┴────────┴─────────┴─────────┘
              ▼
         PostgreSQL
   users / cases / admin_action_logs / feature_flags / announcements
```

---

## 26.1 管理后台 Web UI（1.5天）

### 项目结构：`web_console/admin/`

```
web_console/admin/
├── index.html         # 管理后台入口（JWT 验证 + 菜单 + 内容区）
├── admin.js           # 管理后台全部逻辑（页面切换 / API 调用 / 渲染）
└── style.css          # 管理后台样式（简洁专业风格）
```

**页面布局（单页应用）：**
```
┌─ 顶部导航栏 ─────────────────────────────────────┐
│ [Logo:十神架构管理后台]  用户:admin  [退出]      │
├─ 左侧菜单 ─────────────┬─────────────────────────┤
│ 👥 用户管理             │ 右侧内容区（根据菜单切换）       │
│ 📋 案例审核队列         │   [表格/图表/表单]             │
│ 📊 数据统计面板         │                           │
│ 🔧 系统配置             │                           │
│ 🔌 Webhook 管理         │                           │
│ 🧩 插件管理             │                           │
│ 📜 操作日志             │                           │
└────────────────────────┴─────────────────────────┘
```

**7 个页面的功能清单：**

| 页面 | 功能 |
|------|------|
| 用户管理 | 用户列表表格（分页/搜索/筛选）+ 编辑角色/配额/禁用/启用 |
| 案例审核 | 待审核列表（pending）+ 查看详情 + 通过/驳回（附理由）+ 精选/取消精选 |
| 数据统计 | 卡片概览（总用户/今日新增/总案例/排盘次数）+ 折线图/饼图 + CSV 导出 |
| 系统配置 | 功能开关（案例库/AI解读/插件市场）+ 公告管理（创建/列表/启用/禁用）+ 角色配额 |
| Webhook 管理 | 订阅列表 + 推送记录 + 手动测试推送 |
| 插件管理 | 插件列表 + 审核通过/下架 + 调用日志 |
| 操作日志 | 操作人/时间/类型/IP/详情（只读，过滤搜索） |

---

## 26.2 后端 API 端点（1天）

### API 清单

```
【用户管理】
GET     /api/admin/users?keyword=&role=&status=&limit=20&offset=0
GET     /api/admin/users/{user_id}
PUT     /api/admin/users/{user_id}    {role, api_quota_daily, display_name, email, is_active}
POST    /api/admin/users/{user_id}/disable
POST    /api/admin/users/{user_id}/enable

【案例审核】
GET     /api/admin/cases/pending?limit=20&offset=0
GET     /api/admin/cases?review_status=&limit=20&offset=0
POST    /api/admin/cases/{case_id}/review    {approved, reason}
POST    /api/admin/cases/{case_id}/feature
POST    /api/admin/cases/{case_id}/unfeature

【数据统计】
GET     /api/admin/stats/dashboard            {total_users, new_today, total_cases, total_records, active_users_7d}
GET     /api/admin/stats/users/daily?days=30
GET     /api/admin/stats/records/daily?days=30
GET     /api/admin/stats/export/csv?type=users|cases|records

【系统配置】
GET     /api/admin/config/features            {case_library_enabled, ai_enabled, plugins_enabled...}
PUT     /api/admin/config/features            {feature_key: true/false}
POST    /api/admin/config/announcement        {title, content, link_url, start_at, end_at, is_active}
GET     /api/admin/config/announcements

【日志审计】
GET     /api/admin/logs/actions?user_id=&action_type=&start_date=&end_date=&limit=50
```

### 辅助函数

```python
def _log_admin_action(request, action_type, detail):
    """记录管理员操作（用于审计追踪）"""
    claims = _extract_jwt_claims(request)
    admin_id = claims.get("user_id", 0)
    from tengod.data_store import get_default_store
    get_default_store().admin_log_action(
        admin_id=admin_id, action_type=action_type,
        detail=detail, client_ip=request.client.host if request.client else ""
    )
```

---

## 26.3 数据库扩展（0.5天）

### 新增 3 张表 + 1 组字段

```python
# 1. cases 表新增审核字段（在 Case 模型中添加）
review_status: Mapped[str] = mapped_column(String(16), default="approved")  # pending/approved/rejected
reviewed_by: Mapped[int] = mapped_column(Integer, nullable=True)
review_reason: Mapped[str] = mapped_column(String(512), nullable=True)
reviewed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

# 2. admin_action_logs（管理员操作日志）
class AdminActionLog(Base):
    __tablename__ = "admin_action_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    admin_id: Mapped[int] = mapped_column(Integer, index=True)
    action_type: Mapped[str] = mapped_column(String(64), index=True)
    detail: Mapped[str] = mapped_column(String(1024), nullable=True)
    client_ip: Mapped[str] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

# 3. feature_flags（功能开关）
class FeatureFlag(Base):
    __tablename__ = "feature_flags"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    flag_key: Mapped[str] = mapped_column(String(64), unique=True, index=True)  # "case_library_enabled"
    flag_value: Mapped[str] = mapped_column(String(256))
    description: Mapped[str] = mapped_column(String(256), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, onupdate=lambda: datetime.now(timezone.utc))

# 4. announcements（公告表）
class Announcement(Base):
    __tablename__ = "announcements"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=True)
    link_url: Mapped[str] = mapped_column(String(512), nullable=True)
    start_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    end_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_by: Mapped[int] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
```

---

## 26.4 DataStore 新增方法

```python
def admin_list_users(self, keyword: str = "", role: str = "", status: str = "",
                     limit: int = 20, offset: int = 0) -> dict:
    """分页 + 搜索的用户列表"""
    with self.Session() as s:
        q = s.query(User)
        if keyword:
            q = q.filter(User.username.like(f"%{keyword}%") | (User.display_name or "").like(f"%{keyword}%"))
        if role:
            q = q.filter(User.role == role)
        if status == "active":
            q = q.filter(User.is_active == 1)
        elif status == "disabled":
            q = q.filter(User.is_active == 0)
        total = q.count()
        users = q.order_by(User.created_at.desc()).offset(offset).limit(limit).all()
        return {"total": total, "items": [self._user_to_dict(u) for u in users], "limit": limit, "offset": offset}

def admin_get_user(self, user_id: int) -> Optional[dict]:
    with self.Session() as s:
        u = s.get(User, user_id)
        return self._user_to_dict(u) if u else None

def admin_update_user(self, user_id: int, **updates) -> Optional[dict]:
    with self.Session() as s:
        u = s.get(User, user_id)
        if not u: return None
        for k, v in updates.items():
            if hasattr(u, k) and v is not None:
                setattr(u, k, v)
        s.commit()
        return self._user_to_dict(u)

def admin_toggle_user_active(self, user_id: int, is_active: bool):
    with self.Session() as s:
        u = s.get(User, user_id)
        if u:
            u.is_active = 1 if is_active else 0
            s.commit()

def admin_list_cases(self, review_status: str = "", limit: int = 20, offset: int = 0) -> dict:
    with self.Session() as s:
        q = s.query(Case)
        if review_status:
            q = q.filter(Case.review_status == review_status)
        total = q.count()
        cases = q.order_by(Case.created_at.desc()).offset(offset).limit(limit).all()
        return {"total": total, "items": [c.to_dict() for c in cases]}

def admin_review_case(self, case_id: int, approved: bool, reason: str = None):
    with self.Session() as s:
        c = s.get(Case, case_id)
        if c:
            c.review_status = "approved" if approved else "rejected"
            c.review_reason = reason
            c.reviewed_at = datetime.now(timezone.utc)
            s.commit()

def admin_toggle_case_featured(self, case_id: int, featured: bool):
    with self.Session() as s:
        c = s.get(Case, case_id)
        if c:
            c.is_featured = featured
            s.commit()

def admin_get_dashboard_stats(self) -> dict:
    with self.Session() as s:
        total_users = s.query(func.count(User.id)).scalar()
        today = datetime.now(timezone.utc).date()
        today_start = datetime.combine(today, datetime.min.time()).replace(tzinfo=timezone.utc)
        new_today = s.query(func.count(User.id)).filter(User.created_at >= today_start).scalar()
        total_cases = s.query(func.count(Case.id)).scalar()
        total_records = s.query(func.count(BaziRecord.id)).scalar()
        # 7天活跃用户
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        active_users_7d = s.query(func.count(User.id)).filter(User.last_login_at >= week_ago).scalar()
        return {
            "total_users": int(total_users or 0),
            "new_today": int(new_today or 0),
            "total_cases": int(total_cases or 0),
            "total_records": int(total_records or 0),
            "active_users_7d": int(active_users_7d or 0),
        }

def admin_get_user_daily(self, days: int = 30) -> dict:
    with self.Session() as s:
        start = datetime.now(timezone.utc).date() - timedelta(days=days)
        rows = s.query(
            func.date(User.created_at), func.count(User.id)
        ).filter(User.created_at >= datetime.combine(start, datetime.min.time()).replace(tzinfo=timezone.utc)
        ).group_by(func.date(User.created_at)).order_by(func.date(User.created_at)).all()
        return {"days": days, "data": [{"date": str(r[0]), "count": int(r[1])} for r in rows]}

def admin_get_record_daily(self, days: int = 30) -> dict:
    # 类似上面，基于 BaziRecord.created_at 统计
    pass

def admin_export_csv(self, type: str) -> str:
    """导出 CSV（users/cases/records 三选一）"""
    if type == "users":
        with self.Session() as s:
            users = s.query(User).all()
            lines = ["id,username,display_name,role,email,is_active,api_quota_daily,created_at"]
            for u in users:
                lines.append(f"{u.id},{u.username},{u.display_name or ''},{u.role},{u.email or ''},{u.is_active},{u.api_quota_daily},{u.created_at}")
            return "\n".join(lines)
    # cases / records 类似
    return ""

def admin_get_feature_flags(self) -> dict:
    with self.Session() as s:
        flags = s.query(FeatureFlag).all()
        result = {}
        for f in flags:
            v = f.flag_value
            result[f.flag_key] = v.lower() in ("true", "1", "yes") if v in ("true", "false", "1", "0", "yes", "no") else v
        # 返回默认值（未设置的 flag）
        defaults = {"case_library_enabled": True, "ai_interpreter_enabled": True,
                    "plugin_market_enabled": False, "miniapp_enabled": True}
        for k, v in defaults.items():
            if k not in result:
                result[k] = v
        return result

def admin_set_feature_flags(self, **kwargs):
    with self.Session() as s:
        for key, value in kwargs.items():
            existing = s.query(FeatureFlag).filter(FeatureFlag.flag_key == key).first()
            str_value = str(value).lower() if isinstance(value, bool) else str(value)
            if existing:
                existing.flag_value = str_value
            else:
                s.add(FeatureFlag(flag_key=key, flag_value=str_value))
        s.commit()

def admin_create_announcement(self, **kwargs) -> dict:
    with self.Session() as s:
        a = Announcement(**{k: v for k, v in kwargs.items() if v is not None})
        s.add(a); s.commit(); s.refresh(a)
        return {"id": a.id, "title": a.title, "is_active": a.is_active}

def admin_list_announcements(self) -> list:
    with self.Session() as s:
        items = s.query(Announcement).order_by(Announcement.created_at.desc()).all()
        return [{"id": a.id, "title": a.title, "content": a.content, "link_url": a.link_url,
                 "is_active": a.is_active, "created_at": a.created_at.isoformat() if a.created_at else None} for a in items]

def admin_log_action(self, admin_id: int, action_type: str, detail: str, client_ip: str = ""):
    with self.Session() as s:
        log = AdminActionLog(admin_id=admin_id, action_type=action_type, detail=detail, client_ip=client_ip)
        s.add(log); s.commit()

def admin_list_action_logs(self, user_id: int = None, action_type: str = "",
                           start_date: str = "", end_date: str = "", limit: int = 50, offset: int = 0) -> dict:
    with self.Session() as s:
        q = s.query(AdminActionLog)
        if user_id:
            q = q.filter(AdminActionLog.admin_id == user_id)
        if action_type:
            q = q.filter(AdminActionLog.action_type == action_type)
        if start_date:
            q = q.filter(AdminActionLog.created_at >= datetime.fromisoformat(start_date))
        if end_date:
            q = q.filter(AdminActionLog.created_at <= datetime.fromisoformat(end_date))
        total = q.count()
        logs = q.order_by(AdminActionLog.created_at.desc()).offset(offset).limit(limit).all()
        return {"total": total, "items": [
            {"id": l.id, "admin_id": l.admin_id, "action_type": l.action_type,
             "detail": l.detail, "client_ip": l.client_ip,
             "created_at": l.created_at.isoformat() if l.created_at else None}
            for l in logs]}

def _user_to_dict(self, u: User) -> dict:
    return {
        "id": u.id, "username": u.username, "display_name": u.display_name,
        "role": u.role, "email": u.email, "is_active": bool(u.is_active),
        "api_quota_daily": u.api_quota_daily,
        "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
        "created_at": u.created_at.isoformat() if u.created_at else None,
    }
```

---

## 26.5 修改现有 API 以支持 Feature Flag

### 在 `api_server.py` 入口增加检查

```python
# 每个 API 函数调用前检查对应的 feature flag
def _check_feature_flag(feature_key: str):
    """检查功能开关，未启用则报错"""
    from tengod.data_store import get_default_store
    flags = get_default_store().admin_get_feature_flags()
    if not flags.get(feature_key, True):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "该功能已被管理员禁用")

# 在对应 API 中使用
@app.post("/api/cases", tags=["案例库"])
async def create_case(request: Request, req: CaseCreateRequest):
    authorize(request, "case:write")
    _check_feature_flag("case_library_enabled")
    # ... 原有逻辑
```

---

## 26.6 文件结构汇总

```
新增:
  web_console/admin/index.html      # 管理后台入口 SPA
  web_console/admin/admin.js        # 管理后台逻辑（页面切换/API/渲染）
  web_console/admin/style.css       # 管理后台样式

修改:
  tengod/data_store.py              # AdminActionLog/FeatureFlag/Announcement 3 张表 + 新增方法
  tengod/api_server.py              # ~25 个 /api/admin/* 端点 + _log_admin_action + _check_feature_flag

测试:
  tests/test_admin_api.py           # 管理后台 API 测试
```

---

## 26.7 实施顺序

```
第1天:   数据库表设计 + DataStore 方法实现
第2天:   API 端点开发（用户/案例/统计/配置）
第3天:   管理后台 Web UI 开发
第4天:   日志审计 + 测试 + 权限验证
```

---

## 26.8 风险与缓解

| 风险 | 概率 | 影响 | 缓解方案 |
|------|------|------|---------|
| 管理权限被绕过 | 中 | 高 | 每个 admin 端点独立验证 role=="admin"，测试覆盖所有端点 |
| CSV 导出中文乱码 | 高 | 低 | UTF-8 BOM + Excel 兼容编码 |
| 操作日志写入失败影响主流程 | 低 | 中 | 日志写入使用 try/except，失败不阻塞主流程 |
| feature_flag 查询频繁 | 中 | 低 | Redis 缓存 flag，TTL=5min |
