# 阶段二十五：国际化（i18n） — 技术实现方案

> 目标：支持英文/日文/韩文/越南文，覆盖东南亚与日韩市场；兼容越南子平/韩国四柱
> 依赖：现有 `api_server.py`（REST 框架）、Web UI（index.html）
> 预计工作量：2-3 人/周

---

## 25.0 架构总览

```
                        ┌─ 用户浏览器语言检测 ─┐
                        │   Accept-Language    │
                        └──────────┬───────────┘
                                   ▼
                        ┌────────────────────────┐
                        │  语言选择器 (5 选项)    │
                        │  中/EN/JA/KO/VI        │
                        └──────────┬─────────────┘
                                   ▼
              ┌─────────────────────────────────────────┐
              │              i18n 层                      │
              │  frontend: i18next (UI 文本翻译)         │
              │  backend:  locale 参数（API 错误信息/说明）│
              │  命理术语对照表: 天干/地支/十神/格局         │
              └──────────┬──────────────────┬────────────┘
                         ▼                  ▼
              前端 UI 文本翻译         八字结果翻译
    (JSON 翻译文件 per language)   (术语映射表 + 模板翻译)
```

---

## 25.1 前端国际化（1天）

### 修改 `web_console/index.html` + 新增 `web_console/locales/*.json`

**翻译文件目录：**
```
web_console/locales/
├── zh-CN.json              # 中文（默认，源语言）
├── en.json                  # 英文
├── ja.json                  # 日文
├── ko.json                  # 韩文
└── vi.json                  # 越南文
```

**翻译文件格式：**
```json
{
  "app": {
    "title": "八字命理分析系统",
    "subtitle": "十神架构 · 中华文明数字永生体"
  },
  "nav": {
    "calc": "排盘",
    "records": "历史",
    "cases": "案例库",
    "knowledge": "知识库",
    "ai": "AI解读",
    "profile": "我的",
    "settings": "设置"
  },
  "input": {
    "name": "姓名",
    "gender": "性别",
    "male": "男",
    "female": "女",
    "birth_date": "出生日期",
    "birth_time": "出生时间",
    "calc_button": "开始排盘",
    "placeholder_date": "请选择出生日期"
  },
  "result": {
    "bazi": "八字",
    "year_pillar": "年柱",
    "month_pillar": "月柱",
    "day_pillar": "日柱",
    "hour_pillar": "时柱",
    "wuxing": "五行分布",
    "shigan": "十神统计",
    "geju": "格局",
    "yongshen": "喜用神",
    "dayun": "大运",
    "save_history": "保存到历史",
    "share_card": "生成分享卡片"
  },
  "wuxing": {
    "jin": "金", "mu": "木", "shui": "水", "huo": "火", "tu": "土"
  },
  "tiangan": {
    "jia": "甲", "yi": "乙", "bing": "丙", "ding": "丁",
    "wu": "戊", "ji": "己", "geng": "庚", "xin": "辛",
    "ren": "壬", "gui": "癸"
  },
  "dizhi": {
    "zi": "子", "chou": "丑", "yin": "寅", "mao": "卯",
    "chen": "辰", "si": "巳", "wu": "午", "wei": "未",
    "shen": "申", "you": "酉", "xu": "戌", "hai": "亥"
  },
  "shigan_table": {
    "bijing": "比肩", "jiecai": "劫财",
    "shishen": "食神", "shangguan": "伤官",
    "piancai": "偏财", "zhengcai": "正财",
    "qisha": "七杀", "zhengguan": "正官",
    "pianyin": "偏印", "zhengyin": "正印"
  },
  "category": {
    "wealth": "富贵", "poverty": "贫贱",
    "luck": "吉凶", "lifespan": "寿夭",
    "marriage": "婚姻", "career": "事业",
    "health": "疾病", "misfortune": "灾厄"
  },
  "common": {
    "loading": "加载中...",
    "error": "出错了",
    "retry": "重试",
    "save": "保存",
    "delete": "删除",
    "confirm": "确认",
    "cancel": "取消",
    "search": "搜索",
    "total": "共 {count} 条"
  },
  "errors": {
    "network": "网络连接失败",
    "unauthorized": "请先登录",
    "quota_exceeded": "今日配额已用完，请升级账户",
    "invalid_input": "输入信息不完整"
  },
  "profile": {
    "quota": "今日配额",
    "used": "已用",
    "remaining": "剩余",
    "language": "语言设置",
    "logout": "退出登录"
  },
  "login": {
    "title": "登录",
    "username": "用户名",
    "password": "密码",
    "button": "登录",
    "no_account": "没有账号？",
    "register_here": "立即注册"
  },
  "register": {
    "title": "注册新账号",
    "password_confirm": "确认密码",
    "button": "注册",
    "have_account": "已有账号？去登录"
  },
  "cases": {
    "title": "命例案例库",
    "featured": "精选案例",
    "all_cases": "全部案例",
    "category_filter": "分类筛选",
    "search_placeholder": "搜索案例标题或摘要..."
  },
  "ai": {
    "title": "AI 智能解读",
    "input_placeholder": "输入你的问题，如：我的事业运势如何？",
    "thinking": "AI 思考中...",
    "analyze": "生成解读"
  }
}
```

### 前端集成方案（i18next）

**新增 `web_console/app-i18n.js`：**
```javascript
// i18next 初始化 + 语言切换逻辑
// 资源: zh-CN/en/ja/ko/vi 5 套翻译
// 语言选择器: <select id="lang-selector"> 5 个选项
// 持久化: localStorage('preferred_language')
// 回退: 用户选择 → localStorage → 浏览器 Accept-Language → 默认 zh-CN

// 辅助函数:
//   t('key.path')        — 获取翻译文本
//   setLanguage('en')    — 切换语言（重新渲染所有带 data-i18n 的元素）
//   getCurrentLang()     — 当前语言

// 页面元素绑定:
//   <span data-i18n="nav.calc">排盘</span>      → 文本翻译
//   <input data-i18n-placeholder="input.name" placeholder="姓名">
//   document.title = t('app.title')              → 文档标题
```

---

## 25.2 后端国际化（1天）

### 在 `api_server.py` 新增

```python
# ── i18n 支持 ─────────────────────────────

from fastapi import Header

# 支持的语言
SUPPORTED_LOCALES = {"zh-CN", "en", "ja", "ko", "vi"}
DEFAULT_LOCALE = "zh-CN"

# 错误信息翻译表（简化版）
ERROR_MESSAGES = {
    "zh-CN": {
        "unauthorized": "请先登录",
        "quota_exceeded": "今日配额已用完，请升级账户",
        "invalid_input": "输入信息不完整",
        "not_found": "资源不存在",
        "internal_error": "服务器内部错误，请稍后重试",
    },
    "en": {
        "unauthorized": "Please login first",
        "quota_exceeded": "Daily quota exceeded, please upgrade your account",
        "invalid_input": "Incomplete input information",
        "not_found": "Resource not found",
        "internal_error": "Server error, please try again later",
    },
    "ja": {
        "unauthorized": "ログインしてください",
        "quota_exceeded": "今日のクォータを超えました",
        "invalid_input": "入力が不完全です",
        "not_found": "リソースが見つかりません",
        "internal_error": "サーバーエラー、後でもう一度お試しください",
    },
    "ko": {
        "unauthorized": "로그인해 주세요",
        "quota_exceeded": "오늘의 할당량을 초과했습니다",
        "invalid_input": "입력이 불완전합니다",
        "not_found": "리소스를 찾을 수 없습니다",
        "internal_error": "서버 오류, 나중에 다시 시도하세요",
    },
    "vi": {
        "unauthorized": "Vui lòng đăng nhập",
        "quota_exceeded": "Đã vượt quá hạn mức hàng ngày",
        "invalid_input": "Thông tin đầu vào không đầy đủ",
        "not_found": "Không tìm thấy tài nguyên",
        "internal_error": "Lỗi máy chủ, vui lòng thử lại sau",
    },
}

def get_locale(accept_language: str = Header(default=DEFAULT_LOCALE),
               query_locale: str = Query(default=None, alias="locale")) -> str:
    """获取当前语言（查询参数优先于 Header）"""
    if query_locale and query_locale in SUPPORTED_LOCALES:
        return query_locale
    # 从 Accept-Language 解析
    for lang_part in accept_language.split(","):
        lang = lang_part.strip().split(";")[0]
        if lang in SUPPORTED_LOCALES:
            return lang
        # 支持 zh, en, ja 等短码匹配
        short = lang.split("-")[0].lower()
        if short == "zh": return "zh-CN"
        if short == "en": return "en"
        if short == "ja": return "ja"
        if short == "ko": return "ko"
        if short == "vi": return "vi"
    return DEFAULT_LOCALE

def localize_error(locale: str, error_key: str) -> str:
    return ERROR_MESSAGES.get(locale, ERROR_MESSAGES[DEFAULT_LOCALE]).get(
        error_key, ERROR_MESSAGES[DEFAULT_LOCALE].get(error_key, error_key)
    )
```

### API 端点 i18n 化

```python
# 示例：在 API 中使用 locale
@app.get("/api/cases", tags=["案例库"])
async def list_cases(request: Request, locale: str = Depends(get_locale),
                     category: str = None, limit: int = 20, offset: int = 0):
    authorize(request, "case:read")
    from tengod.data_store import get_default_store
    cases = get_default_store().list_cases(category=category, limit=limit, offset=offset)
    # 返回时根据 locale 翻译案例分类名（如果分类字段为中文）
    return {"cases": [_translate_case_fields(c, locale) for c in cases], "locale": locale}
```

---

## 25.3 命理术语国际化（0.5天）

### 新建 `tengod/i18n_terms.py`

```python
"""
命理术语国际化对照表

使用方式:
  from tengod.i18n_terms import TERMS, translate
  translate("正官", "en") → "Direct Officer"
  translate("正官格", "ja") → "正官格 (せいかんかく)"
"""

TERMS = {
    # 天干 (10)
    "甲": {"en": "Jia", "ja": "甲(こう)", "ko": "갑", "vi": "Giáp"},
    "乙": {"en": "Yi",  "ja": "乙(おつ)", "ko": "을", "vi": "Ất"},
    "丙": {"en": "Bing", "ja": "丙(へい)", "ko": "병", "vi": "Bính"},
    "丁": {"en": "Ding", "ja": "丁(てい)", "ko": "정", "vi": "Đinh"},
    "戊": {"en": "Wu",  "ja": "戊(ぼ)", "ko": "무", "vi": "Mậu"},
    "己": {"en": "Ji",  "ja": "己(き)", "ko": "기", "vi": "Kỷ"},
    "庚": {"en": "Geng", "ja": "庚(こう)", "ko": "경", "vi": "Canh"},
    "辛": {"en": "Xin", "ja": "辛(しん)", "ko": "신", "vi": "Tân"},
    "壬": {"en": "Ren", "ja": "壬(じん)", "ko": "임", "vi": "Nhâm"},
    "癸": {"en": "Gui", "ja": "癸(き)", "ko": "계", "vi": "Quý"},

    # 地支 (12)
    "子": {"en": "Zi (Rat)",     "ja": "子(ね)",     "ko": "자", "vi": "Tý"},
    "丑": {"en": "Chou (Ox)",    "ja": "丑(うし)",   "ko": "축", "vi": "Sửu"},
    "寅": {"en": "Yin (Tiger)",  "ja": "寅(とら)",   "ko": "인", "vi": "Dần"},
    "卯": {"en": "Mao (Rabbit)", "ja": "卯(う)",     "ko": "묘", "vi": "Mão"},
    "辰": {"en": "Chen (Dragon)","ja": "辰(たつ)",   "ko": "진", "vi": "Thìn"},
    "巳": {"en": "Si (Snake)",   "ja": "巳(み)",     "ko": "사", "vi": "Tỵ"},
    "午": {"en": "Wu (Horse)",   "ja": "午(うま)",   "ko": "오", "vi": "Ngọ"},
    "未": {"en": "Wei (Goat)",   "ja": "未(ひつじ)", "ko": "미", "vi": "Mùi"},
    "申": {"en": "Shen (Monkey)","ja": "申(さる)",   "ko": "신", "vi": "Thân"},
    "酉": {"en": "You (Rooster)","ja": "酉(とり)",   "ko": "유", "vi": "Dậu"},
    "戌": {"en": "Xu (Dog)",     "ja": "戌(いぬ)",   "ko": "술", "vi": "Tuất"},
    "亥": {"en": "Hai (Pig)",    "ja": "亥(い)",     "ko": "해", "vi": "Hợi"},

    # 五行
    "金": {"en": "Metal", "ja": "金(きん)", "ko": "금", "vi": "Kim"},
    "木": {"en": "Wood",  "ja": "木(もく)", "ko": "목", "vi": "Mộc"},
    "水": {"en": "Water", "ja": "水(すい)", "ko": "수", "vi": "Thủy"},
    "火": {"en": "Fire",  "ja": "火(か)",   "ko": "화", "vi": "Hỏa"},
    "土": {"en": "Earth", "ja": "土(ど)",   "ko": "토", "vi": "Thổ"},

    # 十神
    "比肩": {"en": "Direct Friends", "ja": "比肩(ひけん)", "ko": "비견", "vi": "Tỷ kiên"},
    "劫财": {"en": "Rob Wealth",     "ja": "劫財(ごうざい)", "ko": "겁재", "vi": "Kiếp tài"},
    "食神": {"en": "Food God",       "ja": "食神(しょくじん)", "ko": "식신", "vi": "Thực thần"},
    "伤官": {"en": "Hurt Official",  "ja": "傷官(しょうかん)", "ko": "상관", "vi": "Thương quan"},
    "偏财": {"en": "Indirect Wealth","ja": "偏財(へんざい)", "ko": "편재", "vi": "Phiến tài"},
    "正财": {"en": "Direct Wealth",  "ja": "正財(せいざい)", "ko": "정재", "vi": "Chính tài"},
    "七杀": {"en": "Seven Killings", "ja": "七殺(しちさつ)", "ko": "칠살", "vi": "Thất sát"},
    "正官": {"en": "Direct Officer", "ja": "正官(せいかん)", "ko": "정관", "vi": "Chính quan"},
    "偏印": {"en": "Indirect Seal",  "ja": "偏印(へんいん)", "ko": "편인", "vi": "Phiến ấn"},
    "正印": {"en": "Direct Seal",    "ja": "正印(せいいん)", "ko": "정인", "vi": "Chính ấn"},

    # 常见格局
    "正官格": {"en": "Direct Officer Structure", "ja": "正官格(せいかんかく)", "ko": "정관격", "vi": "Cách chính quan"},
    "七杀格": {"en": "Seven Killings Structure",  "ja": "七殺格(しちさつかく)", "ko": "칠살격", "vi": "Cách thất sát"},
    "正印格": {"en": "Direct Seal Structure",     "ja": "正印格(せいいんかく)", "ko": "정인격", "vi": "Cách chính ấn"},
    "食神格": {"en": "Food God Structure",        "ja": "食神格(しょくじんかく)", "ko": "식신격", "vi": "Cách thực thần"},
    "伤官格": {"en": "Hurt Official Structure",   "ja": "傷官格(しょうかんかく)", "ko": "상관격", "vi": "Cách thương quan"},
    "正财格": {"en": "Direct Wealth Structure",   "ja": "正財格(せいざいかく)", "ko": "정재격", "vi": "Cách chính tài"},
    "偏财格": {"en": "Indirect Wealth Structure", "ja": "偏財格(へんざいかく)", "ko": "편재격", "vi": "Cách phiến tài"},
    "从财格": {"en": "Wealth-Following Structure", "ja": "従財格(じゅうざいかく)", "ko": "종재격", "vi": "Cách tòng tài"},
    "从杀格": {"en": "Killing-Following Structure", "ja": "従殺格(じゅうさつかく)", "ko": "종살격", "vi": "Cách tòng sát"},
    "从儿格": {"en": "Child-Following Structure",  "ja": "従児格(じゅうじかく)", "ko": "종아격", "vi": "Cách tòng nhi"},
    "从强格": {"en": "Strength-Following Structure","ja": "従強格(じゅうきょうかく)", "ko": "종강격", "vi": "Cách tòng cường"},
    "专旺格": {"en": "Special Strength Structure",  "ja": "専旺格(せんおうかく)", "ko": "전왕격", "vi": "Cách chuyên vượng"},
}

def translate(term: str, locale: str) -> str:
    """翻译单个命理术语"""
    if locale == "zh-CN" or term not in TERMS:
        return term
    return TERMS[term].get(locale, term)

def translate_dict(data: dict, locale: str) -> dict:
    """递归翻译字典中的命理术语字段"""
    if isinstance(data, str) and data in TERMS:
        return translate(data, locale)
    if isinstance(data, dict):
        return {k: translate_dict(v, locale) for k, v in data.items()}
    if isinstance(data, list):
        return [translate_dict(item, locale) for item in data]
    return data
```

---

## 25.4 区域命理规则兼容（0.5天）

### 越南子平（Vietnamese Tử Bình Dố）

**差异：**
- 越南采用节气与中国一致，但年分界有细微差异（部分流派以立春为界）
- 越南八字排盘使用与中国相同的天干地支系统

**实现：**
```python
# 在 bazi_calculator.py 中新增区域性参数
# BaziCalculator.calc(year, month, day, hour, gender, region="cn" | "vn" | "kr")
# region="vn"：使用越南历法（与中国一致，保留入口供未来扩展）
# region="kr"：韩国四柱（檀君纪元转换 + 特定规则）
```

### 韩国四柱（Saju）

**差异：**
- 韩国传统使用檀君纪元（기원전 2333년），公历转换需处理
- 部分流派使用阴历月份（与中国节气法不同）

**实现：**
```python
# 在 bazi_calculator.py 中新增 _to_dangun_year() 方法
# 韩国四柱计算（Saju）
```

---

## 25.5 AI 解读多语言（0.5天）

### 修改 `ai_interpreter.py`

```python
# 现有 _build_interpretation_prompt() 新增 locale 参数
# 当 locale != zh-CN 时，prompt 中增加 "Please respond in {locale}"
# 或改用模板翻译：预写各语言的解读模板（结构化输出）

# 简化方案：
def build_prompt(locale, pillars, analysis, question=None):
    if locale == "zh-CN":
        return f"基于以下八字信息生成中文解读：\n{pillars}\n{analysis}\n..."
    elif locale == "en":
        return f"Based on the following Bazi chart, generate an interpretation in English:\n{pillars}\n{analysis}\n..."
    elif locale == "ja":
        return f"以下の八字に基づき、日本語で解釈を生成してください：\n{pillars}\n{analysis}\n..."
    # ... ko, vi
    return f"Generate Bazi interpretation in {locale}:\n{pillars}\n{analysis}"

# API 端调用时传入 locale:
# POST /api/ai/interpret?locale=en
```

---

## 25.6 文件结构汇总

```
新增:
  web_console/locales/{zh-CN,en,ja,ko,vi}.json    # 5 套翻译
  web_console/app-i18n.js                         # 前端 i18next 初始化 + 语言切换
  tengod/i18n_terms.py                            # 命理术语对照表

修改:
  web_console/index.html                          # 集成语言选择器 + data-i18n 属性
  tengod/api_server.py                            # get_locale() + ERROR_MESSAGES 多语言
  tengod/bazi_calculator.py                       # 新增 region 参数支持越南/韩国四柱
  tengod/ai_interpreter.py                        # 新增 locale 参数，多语言 prompt

测试:
  tests/test_i18n.py                              # 翻译完整性 + API locale 参数
```

---

## 25.7 实施顺序

```
第1天: i18next 前端集成 + 5 套翻译文件 + 语言选择器 UI
第2天: 命理术语对照表 + 后端 i18n 支持 + API locale 参数
第3天: 区域命理规则（越南子平 + 韩国四柱） + AI 多语言 + 测试
```

---

## 25.8 风险与缓解

| 风险 | 概率 | 影响 | 缓解方案 |
|------|------|------|---------|
| 翻译质量不专业（术语不准） | 高 | 中 | 邀请专业命理译者审核，或使用人工翻译 |
| 翻译文件缺失（部分 key 未翻译） | 中 | 低 | CI 中加校验脚本：检查各语言 key 数量与中文源一致 |
| 日文/韩文/越南文字体显示乱码 | 低 | 中 | 使用 Unicode；<meta charset="UTF-8">；预加载 Noto Sans JP/KR 字体 |
| AI 多语言输出不一致 | 中 | 低 | Prompt 中明确指定语言；或使用模板翻译替代纯 AI 生成 |
