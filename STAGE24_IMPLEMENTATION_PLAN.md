# 阶段二十四：移动端小程序 — 技术实现方案

> 目标：覆盖微信/支付宝生态，实现轻量化排盘与社交传播（无需安装，用完即走）
> 依赖：现有 `auth.py`（JWT 认证）、`api_server.py`（八字排盘/案例 API）
> 预计工作量：3-4 人/周

---

## 24.0 架构总览

```
    微信用户                        支付宝用户
        │                               │
        ▼                               ▼
  微信小程序 WeChat               支付宝小程序 Alipay
(原生 WXML/WXSS/JS)             (原生 AXML/ACSS/JS)
        │                               │
        └───────────┬───────────────────┘
                    ▼
              HTTPS 请求（白名单域名）
                    │
          ┌─────────┴─────────┐
          ▼                   ▼
  /api/miniapp/auth     /api/miniapp/...
  (code→openid→JWT)  (排盘/历史/分享/每日运势)
          │                   │
   ┌──────┴───────────────────┴──────┐
   │     PostgreSQL + Redis + 核心业务引擎  │
   └─────────────────────────────────┘
```

---

## 24.1 技术选型

| 方案 | 优势 | 劣势 | 推荐 |
|------|------|------|------|
| **双端原生**（微信 WXML + 支付宝 AXML 分开写） | 最高性能，完美体验 | 维护成本高（2 倍代码） | ★★★ |
| **Taro 跨端**（一套代码编译到双端） | 代码复用，降低维护 | 学习成本，部分 API 差异 | ★★★★ |
| **uni-app 跨端**（Vue 语法，跨端能力强） | 生态成熟，文档全 | 依赖 Vue，团队需熟悉 | ★★★★ |

**推荐：Taro（React 语法）** — 与后端 FastAPI + React 风格一致，团队学习曲线平滑。

---

## 24.2 微信小程序实现（2天）

### 项目结构：`miniapp/wechat/`

```
miniapp/wechat/
├── app.js                    # 小程序入口，App.onLaunch 检查登录态
├── app.json                  # 全局配置（pages/window/tabBar/permission）
├── app.wxss                  # 全局样式
├── project.config.json        # 开发者工具配置（appid/es6/minified）
├── sitemap.json              # 搜索收录配置
│
├── utils/
│   ├── auth.js               # 登录逻辑：wx.login → code → /api/miniapp/auth → JWT
│   ├── api.js                # 请求封装：wx.request + JWT Header + 错误处理
│   ├── storage.js            # 本地存储：token/用户信息/排盘历史缓存
│   └── share.js              # 分享卡片生成
│
├── components/
│   ├── bazi-card/index       # 八字卡片组件
│   ├── pillar-display/       # 四柱显示（天干地支+十神+藏干）
│   ├── wuxing-bar/           # 五行分布条
│   └── star-rating/          # 评分组件
│
└── pages/
    ├── index/                # 首页：输入生辰 → 排盘 → 显示结果
    ├── calc/                 # 排盘页（生日/时间/性别输入）
    ├── result/               # 排盘结果页（四柱/五行/十神/格局）
    ├── history/              # 历史记录页
    ├── case-library/         # 案例库（调用 /api/cases）
    ├── case-detail/          # 案例详情（调用 /api/cases/{id}）
    ├── profile/              # 我的（登录状态/配额/设置）
    └── share/                # 分享页（生成精美卡片）
```

### 核心功能模块详解

**1. 登录模块（utils/auth.js）：**
```javascript
// 微信 code → 后端 openid → 生成 JWT
// 后端新增端点：POST /api/miniapp/auth
export async function ensureLogin() {
  const token = wx.getStorageSync('jwt_token');
  if (token && !isTokenExpired(token)) return token;

  return new Promise((resolve, reject) => {
    wx.login({
      success: async ({ code }) => {
        const res = await api.post('/miniapp/auth', {
          code, provider: 'wechat'
        });
        wx.setStorageSync('jwt_token', res.token);
        wx.setStorageSync('user_info', res.user);
        resolve(res.token);
      },
      fail: reject
    });
  });
}
```

**2. API 请求封装（utils/api.js）：**
```javascript
const BASE_URL = 'https://your-domain.com/api';

export async function request(path, options = {}) {
  const token = wx.getStorageSync('jwt_token');
  return new Promise((resolve, reject) => {
    wx.request({
      url: BASE_URL + path,
      method: options.method || 'GET',
      data: options.data,
      header: {
        'content-type': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {})
      },
      success: ({ statusCode, data }) => {
        if (statusCode >= 200 && statusCode < 300) resolve(data);
        else if (statusCode === 401) { wx.removeStorageSync('jwt_token'); ensureLogin(); }
        else reject(new Error(data.detail || '请求失败'));
      },
      fail: reject
    });
  });
}
export const api = { get: (p, d) => request(p, { data: d }), post: (p, d) => request(p, { method: 'POST', data: d }) };
```

**3. 排盘首页（pages/index/index.wxml + .js）：**
```
表单字段: 姓名(可选) + 性别(单选 male/female) + 出生日期(DatePicker) + 出生时间(TimePicker)
按钮: [开始排盘] → 跳 pages/calc → 确认 → pages/result
布局: 居中纵向布局，大按钮，温暖配色（米黄 + 古铜）
```

**4. 排盘结果页（pages/result/index.wxml + .js）：**
```
- 基本信息：姓名/性别/出生时间/真太阳时
- 四柱显示：年柱/月柱/日柱/时柱（天干在上，地支在下，含十神+藏干）
- 五行分布：条形图（金木水火土各自占比）
- 十神统计：比肩/劫财/食神/伤官/偏财/正财/七杀/正官/偏印/正印 计数
- 格局判断：正官格/七杀格/正印格/食神格/从财格/从杀格...
- 喜用神分析：金木水火土中哪个为喜用，哪个为忌
- 大运表：列出10步大运（起运年龄起，每步10年）
- 操作区：[保存到历史] [生成分享卡片] [查看类似案例]
```

**5. 历史记录页（pages/history/index.js）：**
```
- 列表显示最近排盘记录（分页 /api/records?limit=20&offset=X）
- 每条：日期 + 八字 + 五行概览
- 点击跳 pages/result（传入 record_id 重查详情）
- 左滑删除（调用 DELETE /api/records/{id}）
```

**6. 分享功能（pages/share/index.js）：**
```javascript
// 生成精美的命盘分享图（Canvas 绘制）
// 调用 POST /api/miniapp/share/generate 获取服务端渲染的图片 URL
// 或本地 canvas 2D 绘制 → 保存到相册 + 分享到朋友圈
Page({
  data: { shareImage: '' },

  onLoad(options) {
    const recordId = options.record_id;
    wx.request({
      url: `${BASE_URL}/miniapp/share/generate`,
      method: 'POST',
      data: { record_id: recordId },
      success: ({ data }) => this.setData({ shareImage: data.image_url })
    });
  },

  onShareAppMessage() {
    return {
      title: '我刚算了一卦八字，快来看看你的命盘',
      path: '/pages/index/index?from=share',
      imageUrl: this.data.shareImage
    };
  },

  saveToAlbum() {
    wx.saveImageToPhotosAlbum({ filePath: this.data.shareImage });
  }
});
```

**7. 每日运势（pages/fortune/index.js）：**
```
调用 GET /api/miniapp/daily-fortune
显示: 今日日期 + 运势等级(大吉/中平/小心) + 建议事项 + 幸运数字/颜色
```

---

## 24.3 支付宝小程序（1.5天）

### 项目结构：`miniapp/alipay/`

结构与微信一致，文件名后缀不同：
- `.wxml` → `.axml`
- `.wxss` → `.acss`
- `.js` → `.js`（API 前缀：`wx.` → `my.`）

**关键差异：**
```javascript
// utils/auth.js (支付宝版)
my.getAuthCode({ scopes: 'auth_user' }).then(({ authCode }) => {
  // authCode → 后端 POST /api/miniapp/auth { code, provider: 'alipay' }
  // 后端调用 alipay.system.oauth.token → access_token + user_id
  // 后端生成 JWT 返回
});
```

---

## 24.4 后端 API 端点（1天）

### 在 `api_server.py` 新增

```python
# ── 小程序专用端点 ─────────────────────────────

class MiniappAuthRequest(BaseModel):
    code: str                     # 微信 code / 支付宝 authCode
    provider: str                 # "wechat" | "alipay"
    nickname: Optional[str] = None
    avatar: Optional[str] = None

class MiniappAuthResponse(BaseModel):
    token: str                    # JWT
    user: Dict                    # 用户信息
    is_new: bool                  # 是否新注册

@app.post("/api/miniapp/auth", tags=["小程序"])
async def miniapp_auth(req: MiniappAuthRequest):
    """小程序登录：code → openid/user_id → JWT"""
    from tengod.data_store import get_default_store
    store = get_default_store()

    # 1. 验证 code 获取 openid（模拟：实际需调用微信/支付宝服务器 API）
    #    微信: https://api.weixin.qq.com/sns/jscode2session
    #    支付宝: https://openapi.alipay.com/gateway.do
    openid = f"{req.provider}_{req.code[-8:]}"  # 简化实现

    # 2. 查找/创建用户
    user = store.get_user_by_miniapp_openid(req.provider, openid)
    is_new = False
    if not user:
        user = store.create_miniapp_user(req.provider, openid, req.nickname, req.avatar)
        is_new = True

    # 3. 生成 JWT
    from tengod.auth import create_jwt
    token = create_jwt(user_id=user.id, username=user.username, role=user.role)

    return MiniappAuthResponse(
        token=token,
        user={"id": user.id, "username": user.username, "nickname": user.display_name, "role": user.role},
        is_new=is_new
    )


@app.post("/api/miniapp/share/generate", tags=["小程序"])
async def miniapp_share_generate(req: Dict, request: Request):
    """生成命盘分享图片（服务端渲染）"""
    authorize(request, "records:read")
    # 使用 Pillow / matplotlib 生成分享卡片
    # 输出: {"image_url": "https://cdn.example.com/share/xxx.png", "width": 750, "height": 1334}
    pass


@app.get("/api/miniapp/daily-fortune", tags=["小程序"])
async def miniapp_daily_fortune(request: Request, date: str = None):
    """每日运势（轻量，不消耗配额）"""
    authorize(request, "bazi:calc")
    # 基于当前干支 + 用户日主五行 → 生成简短运势
    pass
```

### 在 `data_store.py` 扩展

```python
# 新增字段（User 表）:
miniapp_wechat_openid: Mapped[Optional[str]]  # 微信 openid
miniapp_alipay_openid: Mapped[Optional[str]]  # 支付宝 user_id

# 新增方法:
def get_user_by_miniapp_openid(self, provider, openid) -> Optional[User]
def create_miniapp_user(self, provider, openid, nickname, avatar_url) -> User
```

---

## 24.5 审核与发布准备（0.5天）

### 微信审核要点

```
1. 填写小程序基本信息:
   - 名称: 八字命理 (或变体，避免直接使用"算命"等敏感词)
   - 类目: 工具/效率 → 生活服务 或 教育/文化
   - 简介: 传统文化八字排盘与命理分析工具

2. 功能页面:
   - 首页/排盘/结果/历史/分享 → 所有页面需可访问且无报错
   - 避免"封建迷信"表述，用词参考"命理研究/排盘分析"

3. 用户隐私与协议:
   - 首次登录需弹出《用户协议》与《隐私政策》
   - 收集用户生辰前需明确说明用途

4. 资质文件（若需）:
   - 公司营业执照（企业主体）
   - 小程序名称商标证书（若使用品牌词）
```

---

## 24.6 文件结构汇总

```
新增:
  miniapp/wechat/app.js|.json|.wxss              # 微信小程序（3个入口文件）
  miniapp/wechat/project.config.json              # 开发者工具配置
  miniapp/wechat/sitemap.json                     # 搜索配置
  miniapp/wechat/utils/{auth,api,storage,share}.js # 工具模块（4个）
  miniapp/wechat/components/{bazi-card,pillar-display,wuxing-bar,star-rating}/ # 4个组件
  miniapp/wechat/pages/{index,calc,result,history,case-library,case-detail,profile,share,fortune}/ # 9个页面
  miniapp/alipay/                                # 支付宝小程序（同结构，~30个文件）

修改:
  tengod/data_store.py                           # User 表新增 miniapp 字段，2个新方法
  tengod/api_server.py                           # 新增 3 个小程序专用端点

测试:
  tests/test_miniapp_api.py                      # 小程序 API 测试
```

---

## 24.7 实施顺序

```
第1-2天: 微信小程序（核心: 登录/排盘/结果/历史 4 个页面）
第3天:   微信小程序扩展（案例库/分享/每日运势 + 组件）
第4天:   支付宝小程序（复用微信逻辑，替换 API 前缀 wx.→my.）
第5天:   后端端点 + 测试 + 审核材料准备
```

---

## 24.8 风险与缓解

| 风险 | 概率 | 影响 | 缓解方案 |
|------|------|------|---------|
| 微信审核拒绝（"封建迷信"） | 高 | 高 | 改表述为"命理研究/八字排盘工具"，类目选工具/效率 |
| 支付宝沙箱环境不稳定 | 中 | 低 | 优先上线微信，支付宝作为第二期 |
| 小程序包体积超 2MB 限制 | 中 | 中 | 使用分包加载（subpackages），案例库/分享页作为分包 |
| 用户隐私合规（GDPR/个人信息保护法） | 中 | 高 | 明确告知数据用途，提供删除入口，数据仅存必要字段 |
