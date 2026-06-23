# 国际化 (i18n) 指南

TenGod 提供 `tengod.i18n` 模块实现命理术语的多语言翻译。

## 支持的语言

| 代码 | 名称 | 说明 |
|:---|:---|:---|
| `zh-CN` | 简体中文 | 默认语言 |
| `zh-TW` | 繁體中文 | 繁体中文 |
| `en` | English | 英文 |

## 翻译覆盖范围

翻译表包含 200+ 命理术语，覆盖以下分类：

| 分类 | 词条数 | 示例 |
|:---|:---:|:---|
| 天干 | 10 | 甲→Jia, 乙→Yi |
| 地支 | 12 | 子→Zi, 丑→Chou(醜) |
| 五行 | 5 | 木→Wood, 火→Fire |
| 五行状态 | 5 | 旺→Prosperous, 相→Supporting |
| 十神 | 10 | 比肩→BiJian, 七杀→QiSha(七殺) |
| 神煞 | 20+ | 天乙贵人→TianYi Nobleman, 桃花→Peach Blossom |
| 格局 | 16 | 正官格→Direct Officer Pattern |
| 二十四节气 | 24 | 立春→Lichun, 冬至→Dongzhi |
| 十二时辰 | 12 | 子时→Zi Hour (23-01) |
| 六爻卦名 | 8 | 乾为天→Qian (Heaven) |
| 紫微主星 | 14 | 紫微→ZiWei, 贪狼→TanLang |
| 四柱术语 | 10 | 日主→Day Master, 大运→Major Fortune |
| 常见术语 | 40+ | 相生→Generates, 相冲→Clashes |
| UI 文案 | 18 | 事业→Career, 财运→Wealth |

## 使用方式

### 基础用法

```python
from tengod.i18n import t, set_lang, get_lang

# 默认简体中文
print(get_lang())        # "zh-CN"
print(t("木"))           # "木"

# 切换到英文
set_lang("en")
print(t("木"))           # "Wood"
print(t("甲"))           # "Jia"

# 切换到繁中
set_lang("zh-TW")
print(t("七杀"))         # "七殺"
print(t("丑"))           # "醜"
```

### 指定语言翻译（不改变全局状态）

```python
from tengod.i18n import t

print(t("木", "en"))      # "Wood"
print(t("木", "zh-TW"))   # "木"
```

### 翻译八字四柱

```python
from tengod.i18n import translate_bazi

pillars = {"year": "甲子", "month": "丙寅", "day": "戊午", "hour": "庚申"}
result = translate_bazi(pillars, lang="en")
# {"year": "Jia Zi", "month": "Bing Yin", "day": "Wu Wu", "hour": "Geng Shen"}
```

### 翻译五行数据

```python
from tengod.i18n import translate_wuxing

# 计数格式
counts = {"木": 3, "火": 2, "土": 1}
result = translate_wuxing(counts, lang="en")
# {"Wood": 3, "Fire": 2, "Earth": 1}

# 强弱格式
strength = {"木": {"status": "旺", "strength": 100}}
result = translate_wuxing(strength, lang="en")
# {"Wood": {"status": "Prosperous", "strength": 100}}
```

### 翻译时辰

```python
from tengod.i18n import translate_shier

print(translate_shier("子", lang="en"))     # "Zi Hour (23-01)"
print(translate_shier("子时", lang="en"))    # "Zi Hour (23-01)"
```

### 翻译字典

```python
from tengod.i18n import get_i18n_engine

engine = get_i18n_engine()
data = {"element": "木", "status": "旺", "score": 90}
result = engine.translate_dict(data, lang="en")
# {"element": "Wood", "status": "Prosperous", "score": 90}
```

### 添加自定义翻译

```python
from tengod.i18n import get_i18n_engine

engine = get_i18n_engine()
engine.add_custom("自定义术语", {"en": "Custom Term", "zh-TW": "自定義術語"})
print(engine.translate("自定义术语", "en"))  # "Custom Term"
```

## I18nEngine API

| 方法 | 说明 |
|:---|:---|
| `get_i18n_engine()` | 获取引擎单例 |
| `engine.set_lang(lang)` | 设置当前语言（无效值回退 zh-CN） |
| `engine.get_lang()` | 获取当前语言 |
| `engine.translate(text, lang=None)` | 翻译单词条，找不到则返回原文 |
| `engine.translate_dict(data, keys=None, lang=None)` | 翻译字典（支持嵌套和列表） |
| `engine.has_translation(text, lang=None)` | 检查是否有翻译 |
| `engine.add_custom(key, translations)` | 添加自定义翻译 |
| `engine.get_available_langs()` | 获取可用语言列表 |

## API 端点

| 端点 | 方法 | 说明 |
|:---|:---:|:---|
| `/api/v2/i18n/languages` | GET | 获取支持的语言列表 |
| `/api/v2/i18n/translate` | POST | 批量文本翻译 |

### 批量翻译示例

```bash
POST /api/v2/i18n/translate
Content-Type: application/json

{
  "texts": ["木", "火", "甲"],
  "lang": "en"
}
```

响应：
```json
{
  "lang": "en",
  "translations": {
    "木": "Wood",
    "火": "Fire",
    "甲": "Jia"
  }
}
```

## 添加新语言

1. 在 `tengod/i18n.py` 的 `TRANSLATIONS` 字典中，为每个词条添加新语言的翻译
2. 在 `I18nEngine.set_lang()` 的有效语言列表中添加新语言代码
3. 在 `I18nEngine.get_available_langs()` 中添加新语言信息
4. 运行测试验证：`python -m pytest tests/test_v23_i18n.py -v`
