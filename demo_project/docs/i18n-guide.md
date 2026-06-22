# 国际化 (i18n) 指南

Tengod 提供多语言翻译的底层 `tengod.i18n` 模块。

## 支持的语言
- `zh-CN`  简体中文
- `zh-TW`  繁体中文
- `en`     English
- `ja`     日本語
- `ko`     한국어

## 使用方式
```python
from tengod.i18n import get_translator, t

tr = get_translator('en')
print(tr('日主'))       # Day Master
print(t('大运', 'ja'))  # 大運
```

## 添加新语言
1. 在 `tengod/i18n/` 下添加 `xx.json`（`xx` 为语言代码）
2. 以 `zh-CN.json` 为基准，填充各 key 的翻译
3. 在 `tengod.i18n.SUPPORTED_LANGUAGES` 中注册新语言
4. 运行测试验证：`python -m pytest tests/test_phase25.py`
