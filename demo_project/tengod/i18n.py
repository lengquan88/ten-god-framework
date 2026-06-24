"""Stage 25: i18n / l10n subsystem for tengod.

Provides translation dictionaries covering 天干地支 / 五行 / 十神 /
格局 / 生肖 / UI 标签 / 通用短语 / 错误消息 in zh-CN, zh-TW,
en, ja, ko and vi.
"""

from __future__ import annotations

import datetime as _dt
import json
import locale as _locale_module
import re
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Translation dictionary
# ---------------------------------------------------------------------------

# zh-CN is the canonical term list. All other locales provide a
# term -> translation mapping. Unknown terms fall back to zh-CN.

_TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "zh-CN": {
        # 天干
        "甲": "甲", "乙": "乙", "丙": "丙", "丁": "丁",
        "戊": "戊", "己": "己", "庚": "庚", "辛": "辛",
        "壬": "壬", "癸": "癸",
        # 地支
        "子": "子", "丑": "丑", "寅": "寅", "卯": "卯",
        "辰": "辰", "巳": "巳", "午": "午", "未": "未",
        "申": "申", "酉": "酉", "戌": "戌", "亥": "亥",
        # 五行
        "金": "金", "木": "木", "水": "水", "火": "火", "土": "土",
        # 十神
        "比肩": "比肩", "劫财": "劫财",
        "食神": "食神", "伤官": "伤官",
        "偏财": "偏财", "正财": "正财",
        "七杀": "七杀", "正官": "正官",
        "偏印": "偏印", "正印": "正印",
        # 格局
        "伤官格": "伤官格", "正官格": "正官格", "偏财格": "偏财格",
        "正印格": "正印格", "偏印格": "偏印格", "食神格": "食神格",
        "建禄格": "建禄格", "专旺格": "专旺格", "从格": "从格",
        # 生肖
        "鼠": "鼠", "牛": "牛", "虎": "虎", "兔": "兔",
        "龙": "龙", "蛇": "蛇", "马": "马", "羊": "羊",
        "猴": "猴", "鸡": "鸡", "狗": "狗", "猪": "猪",
        # 星座
        "白羊": "白羊", "金牛": "金牛", "双子": "双子", "巨蟹": "巨蟹",
        "狮子": "狮子", "处女": "处女", "天秤": "天秤", "天蝎": "天蝎",
        "射手": "射手", "摩羯": "摩羯", "水瓶": "水瓶", "双鱼": "双鱼",
        # UI 标签
        "命盘": "命盘", "排盘": "排盘", "分析": "分析", "报告": "报告",
        "大运": "大运", "流年": "流年", "日柱": "日柱", "日主": "日主",
        "年柱": "年柱", "月柱": "月柱", "时柱": "时柱",
        "男": "男", "女": "女",
        "生": "生", "克": "克", "合": "合", "冲": "冲",
        # 通用短语
        "吉": "吉", "平": "平", "凶": "凶",
        "有利": "有利", "不利": "不利", "注意": "注意",
        "好运": "好运", "坏运": "坏运",
        # 错误 / 提示
        "error.invalid_date": "无效的出生日期",
        "error.invalid_hour": "无效的时辰",
        "error.network": "网络异常，请重试",
        "error.token_expired": "登录已过期，请重新登录",
        "error.generic": "系统繁忙，请稍后再试",
        # 常用
        "yes": "是", "no": "否",
        "login": "登录", "share": "分享", "report": "报告",
        "chart": "命盘", "analyze": "分析",
    },
    "zh-TW": {
        "甲": "甲", "乙": "乙", "丙": "丙", "丁": "丁",
        "戊": "戊", "己": "己", "庚": "庚", "辛": "辛",
        "壬": "壬", "癸": "癸",
        "子": "子", "丑": "丑", "寅": "寅", "卯": "卯",
        "辰": "辰", "巳": "巳", "午": "午", "未": "未",
        "申": "申", "酉": "酉", "戌": "戌", "亥": "亥",
        "金": "金", "木": "木", "水": "水", "火": "火", "土": "土",
        "比肩": "比肩", "劫财": "劫財",
        "食神": "食神", "伤官": "傷官",
        "偏财": "偏財", "正财": "正財",
        "七杀": "七殺", "正官": "正官",
        "偏印": "偏印", "正印": "正印",
        "伤官格": "傷官格", "正官格": "正官格", "偏财格": "偏財格",
        "正印格": "正印格", "偏印格": "偏印格", "食神格": "食神格",
        "建禄格": "建祿格", "专旺格": "專旺格", "从格": "從格",
        "鼠": "鼠", "牛": "牛", "虎": "虎", "兔": "兔",
        "龙": "龍", "蛇": "蛇", "马": "馬", "羊": "羊",
        "猴": "猴", "鸡": "雞", "狗": "狗", "猪": "豬",
        "白羊": "牡羊", "金牛": "金牛", "双子": "雙子", "巨蟹": "巨蟹",
        "狮子": "獅子", "处女": "處女", "天秤": "天秤", "天蝎": "天蠍",
        "射手": "射手", "摩羯": "摩羯", "水瓶": "水瓶", "双鱼": "雙魚",
        "命盘": "命盤", "排盘": "排盤", "分析": "分析", "报告": "報告",
        "大运": "大運", "流年": "流年", "日柱": "日柱", "日主": "日主",
        "年柱": "年柱", "月柱": "月柱", "时柱": "時柱",
        "男": "男", "女": "女",
        "生": "生", "克": "剋", "合": "合", "冲": "沖",
        "吉": "吉", "平": "平", "凶": "凶",
        "有利": "有利", "不利": "不利", "注意": "注意",
        "好运": "好運", "坏运": "壞運",
        "error.invalid_date": "無效的出生日期",
        "error.invalid_hour": "無效的時辰",
        "error.network": "網路異常，請重試",
        "error.token_expired": "登入已過期，請重新登入",
        "error.generic": "系統繁忙，請稍後再試",
        "yes": "是", "no": "否",
        "login": "登入", "share": "分享", "report": "報告",
        "chart": "命盤", "analyze": "分析",
    },
    "en": {
        "甲": "Jia", "乙": "Yi", "丙": "Bing", "丁": "Ding",
        "戊": "Wu", "己": "Ji", "庚": "Geng", "辛": "Xin",
        "壬": "Ren", "癸": "Gui",
        "子": "Zi", "丑": "Chou", "寅": "Yin", "卯": "Mao",
        "辰": "Chen", "巳": "Si", "午": "Wu", "未": "Wei",
        "申": "Shen", "酉": "You", "戌": "Xu", "亥": "Hai",
        "金": "Metal", "木": "Wood", "水": "Water",
        "火": "Fire", "土": "Earth",
        "比肩": "Bi Jian (Peer)", "劫财": "Jie Cai (Robber)",
        "食神": "Shi Shen (Food God)", "伤官": "Shang Guan (Hurting Officer)",
        "偏财": "Pian Cai (Indirect Wealth)", "正财": "Zheng Cai (Direct Wealth)",
        "七杀": "Qi Sha (Seven Killings)", "正官": "Zheng Guan (Direct Officer)",
        "偏印": "Pian Yin (Indirect Resource)", "正印": "Zheng Yin (Direct Resource)",
        "伤官格": "Hurting Officer Pattern", "正官格": "Direct Officer Pattern",
        "偏财格": "Indirect Wealth Pattern", "正印格": "Direct Resource Pattern",
        "偏印格": "Indirect Resource Pattern", "食神格": "Food God Pattern",
        "建禄格": "Jian Lu Pattern", "专旺格": "Special Strong Pattern",
        "从格": "Follower Pattern",
        "鼠": "Rat", "牛": "Ox", "虎": "Tiger", "兔": "Rabbit",
        "龙": "Dragon", "蛇": "Snake", "马": "Horse", "羊": "Goat",
        "猴": "Monkey", "鸡": "Rooster", "狗": "Dog", "猪": "Pig",
        "白羊": "Aries", "金牛": "Taurus", "双子": "Gemini", "巨蟹": "Cancer",
        "狮子": "Leo", "处女": "Virgo", "天秤": "Libra", "天蝎": "Scorpio",
        "射手": "Sagittarius", "摩羯": "Capricorn", "水瓶": "Aquarius", "双鱼": "Pisces",
        "命盘": "Chart", "排盘": "Arrange Chart", "分析": "Analysis",
        "报告": "Report", "大运": "Major Fortune", "流年": "Annual Fortune",
        "日柱": "Day Pillar", "日主": "Day Master",
        "年柱": "Year Pillar", "月柱": "Month Pillar", "时柱": "Hour Pillar",
        "男": "Male", "女": "Female",
        "生": "Engender", "克": "Control", "合": "Combine", "冲": "Clash",
        "吉": "Auspicious", "平": "Neutral", "凶": "Inauspicious",
        "有利": "Favorable", "不利": "Unfavorable", "注意": "Attention",
        "好运": "Good Fortune", "坏运": "Bad Fortune",
        "error.invalid_date": "Invalid birth date",
        "error.invalid_hour": "Invalid hour",
        "error.network": "Network error, please retry",
        "error.token_expired": "Session expired, please login again",
        "error.generic": "System busy, please try later",
        "yes": "Yes", "no": "No",
        "login": "Login", "share": "Share", "report": "Report",
        "chart": "Chart", "analyze": "Analyze",
    },
    "ja": {
        "甲": "甲（きのえ）", "乙": "乙（きのと）",
        "丙": "丙（ひのえ）", "丁": "丁（ひのと）",
        "戊": "戊（つちのえ）", "己": "己（つちのと）",
        "庚": "庚（かのえ）", "辛": "辛（かのと）",
        "壬": "壬（みずのえ）", "癸": "癸（みずのと）",
        "子": "子（ね）", "丑": "丑（うし）", "寅": "寅（とら）",
        "卯": "卯（う）", "辰": "辰（たつ）", "巳": "巳（み）",
        "午": "午（うま）", "未": "未（ひつじ）",
        "申": "申（さる）", "酉": "酉（とり）",
        "戌": "戌（いぬ）", "亥": "亥（い）",
        "金": "金", "木": "木", "水": "水", "火": "火", "土": "土",
        "比肩": "比肩（ひけん）", "劫财": "劫財（ごうざい）",
        "食神": "食神（しょくじん）", "伤官": "傷官（しょうかん）",
        "偏财": "偏財（へんざい）", "正财": "正財（せいざい）",
        "七杀": "七殺（しちさつ）", "正官": "正官（せいかん）",
        "偏印": "偏印（へんいん）", "正印": "正印（せいいん）",
        "伤官格": "傷官格", "正官格": "正官格", "偏财格": "偏財格",
        "正印格": "正印格", "偏印格": "偏印格", "食神格": "食神格",
        "建禄格": "建禄格", "专旺格": "専旺格", "从格": "従格",
        "鼠": "鼠（ねずみ）", "牛": "牛（うし）",
        "虎": "虎（とら）", "兔": "兔（うさぎ）",
        "龙": "龍（たつ）", "蛇": "蛇（へび）",
        "马": "馬（うま）", "羊": "羊（ひつじ）",
        "猴": "猿（さる）", "鸡": "鶏（にわとり）",
        "狗": "犬（いぬ）", "猪": "猪（いのしし）",
        "白羊": "牡羊座", "金牛": "牡牛座", "双子": "双子座", "巨蟹": "蟹座",
        "狮子": "獅子座", "处女": "乙女座", "天秤": "天秤座", "天蝎": "蠍座",
        "射手": "射手座", "摩羯": "山羊座", "水瓶": "水瓶座", "双鱼": "魚座",
        "命盘": "命盤（めいばん）", "排盘": "排盤（はいばん）",
        "分析": "分析", "报告": "レポート",
        "大运": "大運（たいうん）", "流年": "流年（りゅうねん）",
        "日柱": "日柱（にっちゅう）", "日主": "日主（にっしゅ）",
        "年柱": "年柱（ねんちゅう）", "月柱": "月柱（げっちゅう）",
        "时柱": "時柱（じちゅう）",
        "男": "男", "女": "女",
        "生": "生ずる", "克": "剋す", "合": "合", "冲": "冲",
        "吉": "吉", "平": "平", "凶": "凶",
        "有利": "有利", "不利": "不利", "注意": "注意",
        "好运": "好運", "坏运": "悪運",
        "error.invalid_date": "無効な生年月日です",
        "error.invalid_hour": "無効な時辰です",
        "error.network": "ネットワークエラー、再試行してください",
        "error.token_expired": "セッションの有効期限が切れました。再ログインしてください",
        "error.generic": "システムが混雑しています。後でもう一度お試しください",
        "yes": "はい", "no": "いいえ",
        "login": "ログイン", "share": "共有", "report": "レポート",
        "chart": "チャート", "analyze": "分析",
    },
    "ko": {
        "甲": "갑", "乙": "을", "丙": "병", "丁": "정",
        "戊": "무", "己": "기", "庚": "경", "辛": "신",
        "壬": "임", "癸": "계",
        "子": "자", "丑": "축", "寅": "인", "卯": "묘",
        "辰": "진", "巳": "사", "午": "오", "未": "미",
        "申": "신", "酉": "유", "戌": "술", "亥": "해",
        "金": "금", "木": "목", "水": "수", "火": "화", "土": "토",
        "比肩": "비견", "劫财": "겁재",
        "食神": "식신", "伤官": "상관",
        "偏财": "편재", "正财": "정재",
        "七杀": "칠살", "正官": "정관",
        "偏印": "편인", "正印": "정인",
        "伤官格": "상관격", "正官格": "정관격", "偏财格": "편재격",
        "正印格": "정인격", "偏印格": "편인격", "食神格": "식신격",
        "建禄格": "건록격", "专旺格": "전왕격", "从格": "종격",
        "鼠": "쥐", "牛": "소", "虎": "호랑이", "兔": "토끼",
        "龙": "용", "蛇": "뱀", "马": "말", "羊": "양",
        "猴": "원숭이", "鸡": "닭", "狗": "개", "猪": "돼지",
        "白羊": "양자리", "金牛": "황소자리", "双子": "쌍둥이자리",
        "巨蟹": "게자리", "狮子": "사자자리", "处女": "처녀자리",
        "天秤": "천칭자리", "天蝎": "전갈자리",
        "射手": "궁수자리", "摩羯": "염소자리",
        "水瓶": "물병자리", "双鱼": "물고기자리",
        "命盘": "명반", "排盘": "배반", "分析": "분석", "报告": "보고서",
        "大运": "대운", "流年": "유년", "日柱": "일주", "日主": "일주",
        "年柱": "년주", "月柱": "월주", "时柱": "시주",
        "男": "남", "女": "여",
        "生": "생", "克": "극", "合": "합", "冲": "충",
        "吉": "길", "平": "평", "凶": "흉",
        "有利": "유리", "不利": "불리", "注意": "주의",
        "好运": "좋은 운", "坏运": "나쁜 운",
        "error.invalid_date": "잘못된 생년월일입니다",
        "error.invalid_hour": "잘못된 시진입니다",
        "error.network": "네트워크 오류, 다시 시도해 주세요",
        "error.token_expired": "세션이 만료되었습니다. 다시 로그인해 주세요",
        "error.generic": "시스템이 바쁩니다. 나중에 다시 시도해 주세요",
        "yes": "예", "no": "아니오",
        "login": "로그인", "share": "공유", "report": "보고서",
        "chart": "차트", "analyze": "분석",
    },
    "vi": {
        "甲": "Giáp", "乙": "Ất", "丙": "Bính", "丁": "Đinh",
        "戊": "Mậu", "己": "Kỷ", "庚": "Canh", "辛": "Tân",
        "壬": "Nhâm", "癸": "Quý",
        "子": "Tý", "丑": "Sửu", "寅": "Dần", "卯": "Mão",
        "辰": "Thìn", "巳": "Tỵ", "午": "Ngọ", "未": "Mùi",
        "申": "Thân", "酉": "Dậu", "戌": "Tuất", "亥": "Hợi",
        "金": "Kim", "木": "Mộc", "水": "Thủy", "火": "Hỏa", "土": "Thổ",
        "比肩": "Tỷ Kiên", "劫财": "Kiếp Tài",
        "食神": "Thực Thần", "伤官": "Thương Quan",
        "偏财": "Thiên Tài", "正财": "Chính Tài",
        "七杀": "Thất Sát", "正官": "Chính Quan",
        "偏印": "Thiên Ấn", "正印": "Chính Ấn",
        "伤官格": "Cách Thương Quan", "正官格": "Cách Chính Quan",
        "偏财格": "Cách Thiên Tài", "正印格": "Cách Chính Ấn",
        "偏印格": "Cách Thiên Ấn", "食神格": "Cách Thực Thần",
        "建禄格": "Cách Kiến Lộc", "专旺格": "Cách Chuyên Vượng",
        "从格": "Cách Tòng",
        "鼠": "Chuột", "牛": "Trâu", "虎": "Hổ", "兔": "Mèo",
        "龙": "Rồng", "蛇": "Rắn", "马": "Ngựa", "羊": "Dê",
        "猴": "Khỉ", "鸡": "Gà", "狗": "Chó", "猪": "Heo",
        "白羊": "Bạch Dương", "金牛": "Kim Ngưu", "双子": "Song Tử",
        "巨蟹": "Cự Giải", "狮子": "Sư Tử", "处女": "Xử Nữ",
        "天秤": "Thiên Bình", "天蝎": "Thiên Yết",
        "射手": "Nhân Mã", "摩羯": "Ma Kết",
        "水瓶": "Bảo Bình", "双鱼": "Song Ngư",
        "命盘": "Bảng mệnh", "排盘": "Sắp xếp mệnh",
        "分析": "Phân tích", "报告": "Báo cáo",
        "大运": "Đại vận", "流年": "Lưu niên",
        "日柱": "Nhật trụ", "日主": "Nhật chủ",
        "年柱": "Niên trụ", "月柱": "Nguyệt trụ", "时柱": "Thời trụ",
        "男": "Nam", "女": "Nữ",
        "生": "Sinh", "克": "Khắc", "合": "Hợp", "冲": "Xung",
        "吉": "Cát", "平": "Bình", "凶": "Hung",
        "有利": "Lợi", "不利": "Bất lợi", "注意": "Lưu ý",
        "好运": "Vận tốt", "坏运": "Vận xấu",
        "error.invalid_date": "Ngày sinh không hợp lệ",
        "error.invalid_hour": "Giờ không hợp lệ",
        "error.network": "Lỗi mạng, vui lòng thử lại",
        "error.token_expired": "Phiên đã hết hạn, vui lòng đăng nhập lại",
        "error.generic": "Hệ thống đang bận, vui lòng thử lại sau",
        "yes": "Có", "no": "Không",
        "login": "Đăng nhập", "share": "Chia sẻ", "report": "Báo cáo",
        "chart": "Biểu đồ", "analyze": "Phân tích",
    },
}

_LOCALE_NAMES: Dict[str, str] = {
    "zh-CN": "简体中文",
    "zh-TW": "繁體中文",
    "en": "English",
    "ja": "日本語",
    "ko": "한국어",
    "vi": "Tiếng Việt",
}

# Ganzhi normalization maps between traditional / simplified Chinese forms.
# Most ganzhi look identical between zh-CN / zh-TW, but we still support an
# explicit mapping table for regional variants (e.g. 丑/丑, etc.)
_GANZHI_NORMALIZE: Dict[str, Dict[str, str]] = {
    "zh-TW": {
        "丑": "丑", "戌": "戌", "龙": "龍", "马": "馬",
    },
}


# ---------------------------------------------------------------------------
# I18nManager
# ---------------------------------------------------------------------------

class I18nManager:
    """Central i18n manager for tengod."""

    def __init__(self, default_locale: str = "zh-CN") -> None:
        if default_locale not in _TRANSLATIONS:
            default_locale = "zh-CN"
        self._locale: str = default_locale
        self._custom: Dict[str, Dict[str, str]] = {}

    # ---- Locale management -----------------------------------------------
    def set_locale(self, locale: str) -> str:
        if locale in _TRANSLATIONS:
            self._locale = locale
        return self._locale

    def get_locale(self) -> str:
        return self._locale

    def get_all_locales(self) -> List[str]:
        return sorted(_TRANSLATIONS.keys())

    def get_locale_name(self, locale: Optional[str] = None) -> str:
        locale = locale or self._locale
        return _LOCALE_NAMES.get(locale, locale)

    # ---- Translation primitives ------------------------------------------
    def translate(self, term: Any, locale: Optional[str] = None) -> str:
        if term is None:
            return ""
        text = str(term)
        locale = locale or self._locale
        locale_map = _TRANSLATIONS.get(locale, {})
        if text in locale_map:
            return locale_map[text]
        # Fall back to custom overrides for this locale
        custom = self._custom.get(locale, {})
        if text in custom:
            return custom[text]
        # zh-CN is considered the canonical source: if zh-CN has the term
        # but the target locale doesn't, return the zh-CN term.
        zh_cn = _TRANSLATIONS.get("zh-CN", {})
        if text in zh_cn:
            return zh_cn[text]
        return text

    def bulk_translate(self, terms: List[Any], locale: Optional[str] = None) -> List[str]:
        return [self.translate(term, locale) for term in terms]

    def translate_dict(
        self,
        d: Dict[str, Any],
        keys_to_translate: List[str],
        locale: Optional[str] = None,
    ) -> Dict[str, Any]:
        result = dict(d)
        for key in keys_to_translate:
            if key in result:
                value = result[key]
                if isinstance(value, list):
                    result[key] = [
                        self.translate(item, locale) if isinstance(item, str) else item
                        for item in value
                    ]
                else:
                    result[key] = self.translate(value, locale)
        return result

    def translate_bazi_result(
        self,
        result: Dict[str, Any],
        locale: Optional[str] = None,
    ) -> Dict[str, Any]:
        default_keys = [
            "day_master", "geju", "dayun", "liunian",
            "wuxing", "analysis", "relation", "element",
            "gan", "zhi", "ganzhi",
        ]
        return self._translate_recursive(result, default_keys, locale)

    def translate_trajectory(
        self,
        trajectory: Dict[str, Any],
        locale: Optional[str] = None,
    ) -> Dict[str, Any]:
        default_keys = [
            "day_master", "element", "relation", "gan", "zhi",
            "ganzhi", "wuxing",
        ]
        return self._translate_recursive(trajectory, default_keys, locale)

    def translate_report(self, report_text: str, locale: Optional[str] = None) -> str:
        if not isinstance(report_text, str):
            return str(report_text)
        # Replace known term tokens with their translated forms.
        mapping = _TRANSLATIONS.get(locale or self._locale, {})
        zh_cn = _TRANSLATIONS.get("zh-CN", {})
        # Longer tokens first to avoid partial collisions
        terms_sorted = sorted(
            (k for k in zh_cn.keys() if len(k) >= 1), key=len, reverse=True
        )
        out = report_text
        for term in terms_sorted:
            if term in mapping and mapping[term] != term:
                # Escape regex special characters in Chinese terms (rare but safe)
                safe = re.escape(term)
                out = re.sub(safe, mapping[term], out)
        return out

    # ---- Formatting ------------------------------------------------------
    def format_number(self, num: Any, locale: Optional[str] = None) -> str:
        try:
            value = float(num)
        except (TypeError, ValueError):
            return str(num)
        loc = locale or self._locale
        try:
            if loc == "en":
                return f"{value:,.2f}"
            if loc == "ja":
                return f"{value:,.2f}"
            if loc == "ko":
                return f"{value:,.2f}"
            if loc == "vi":
                # Space-separated thousands, comma for decimals is common
                parts = f"{value:,.2f}".split(".")
                int_part = parts[0].replace(",", ".")
                return f"{int_part},{parts[1]}" if len(parts) == 2 else int_part
            # zh-CN / zh-TW: use comma thousands separator
            return f"{value:,.2f}"
        except Exception:
            return str(num)

    def format_date(self, dt: Any, locale: Optional[str] = None) -> str:
        if dt is None:
            return ""
        if isinstance(dt, (int, float)):
            try:
                dt = _dt.datetime.fromtimestamp(dt)
            except (OSError, ValueError, OverflowError):
                return str(dt)
        if not isinstance(dt, (_dt.date, _dt.datetime)):
            parsed = self._parse_date_soft(str(dt))
            if parsed is not None:
                dt = parsed
            else:
                return str(dt)
        loc = locale or self._locale
        formats = {
            "zh-CN": "%Y年%m月%d日",
            "zh-TW": "%Y年%m月%d日",
            "en": "%d/%m/%Y",
            "ja": "%Y年%m月%d日",
            "ko": "%Y년 %m월 %d일",
            "vi": "%d/%m/%Y",
        }
        try:
            return dt.strftime(formats.get(loc, "%Y-%m-%d"))
        except Exception:
            return str(dt)

    # ---- UI labels -------------------------------------------------------
    def get_ui_label(self, key: str, locale: Optional[str] = None) -> str:
        return self.translate(key, locale)

    # ---- Custom translations ---------------------------------------------
    def merge_custom_translations(self, locale: str, translation_dict: Dict[str, str]) -> None:
        if locale not in _TRANSLATIONS:
            # Still accept custom mappings for unsupported locales so that users
            # can extend without waiting on library updates.
            pass
        self._custom.setdefault(locale, {}).update(translation_dict or {})

    # ---- Regional helpers ------------------------------------------------
    def get_compatibility_notes(self, locale: Optional[str] = None) -> Dict[str, str]:
        loc = locale or self._locale
        notes = {
            "zh-CN": "中国大陆使用简体中文；部分术语与港台地区存在差异。",
            "zh-TW": "台湾/港澳地区使用繁体中文；部分术语写法与简体不同。",
            "en": "Chinese metaphysical terms are transliterated / translated. Some regional nuance is lost.",
            "ja": "日本式の術語は中国本土と異なる場合があります。",
            "ko": "한국어 명리 용어는 중국어 본래 용어와 약간 다를 수 있습니다.",
            "vi": "Một số thuật ngữ có sự khác biệt giữa các vùng miền Trung Quốc.",
        }
        return {
            "locale": loc,
            "note": notes.get(loc, notes["zh-CN"]),
        }

    def get_locale_for_market(self, market: str) -> str:
        if not market:
            return self._locale
        code = str(market).strip().upper()
        mapping = {
            "CN": "zh-CN", "ZH": "zh-CN", "ZH-CN": "zh-CN",
            "TW": "zh-TW", "HK": "zh-TW", "MO": "zh-TW",
            "ZH-TW": "zh-TW",
            "US": "en", "UK": "en", "GB": "en", "AU": "en", "CA": "en",
            "EN": "en",
            "JP": "ja", "JA": "ja",
            "KR": "ko", "KO": "ko",
            "VN": "vi", "VI": "vi",
        }
        return mapping.get(code, self._locale)

    def normalize_ganzhi_for_locale(self, ganzhi_text: str, locale: Optional[str] = None) -> str:
        if not isinstance(ganzhi_text, str):
            return str(ganzhi_text)
        loc = locale or self._locale
        norm = _GANZHI_NORMALIZE.get(loc, {})
        result = ganzhi_text
        for source, target in norm.items():
            result = result.replace(source, target)
        return result

    # ---- Private helpers -------------------------------------------------
    def _translate_recursive(
        self,
        obj: Any,
        keys: List[str],
        locale: Optional[str] = None,
    ) -> Any:
        if isinstance(obj, dict):
            result: Dict[str, Any] = {}
            for k, v in obj.items():
                if k in keys:
                    if isinstance(v, (dict, list)):
                        result[k] = self._translate_recursive(v, keys, locale)
                    else:
                        result[k] = self.translate(v, locale)
                else:
                    result[k] = self._translate_recursive(v, keys, locale)
            return result
        if isinstance(obj, list):
            return [self._translate_recursive(item, keys, locale) for item in obj]
        if isinstance(obj, str):
            return self.translate(obj, locale) if obj in (
                _TRANSLATIONS.get(locale or self._locale, {})
            ) else obj
        return obj

    @staticmethod
    def _parse_date_soft(text: str) -> Optional[_dt.date]:
        text = (text or "").strip()
        patterns = [
            r"(\d{4})[-/.年](\d{1,2})[-/.月](\d{1,2})",
            r"(\d{4})(\d{2})(\d{2})",
        ]
        for pat in patterns:
            m = re.search(pat, text)
            if m:
                try:
                    return _dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
                except ValueError:
                    return None
        return None


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

# Simple charset heuristics for locale detection from text content.
_HIRAGANA_RE = re.compile(r"[\u3040-\u309F]")
_KATAKANA_RE = re.compile(r"[\u30A0-\u30FF]")
_HANGUL_RE = re.compile(r"[\uAC00-\uD7AF]")
_TRADITIONAL_HINT_CHARS = "這裡為什麼人們說話很溫暖時間圖畫"
_EN_RE = re.compile(r"[A-Za-z]{3,}")
_VI_DIACRITICS_RE = re.compile(r"[ăâđêôơưàáạảãằắặẳẵầấậẩẫèéẹẻẽềếệểễìíịỉĩòóọỏõồốộổỗờớợởỡùúụủũừứựửữỳýỵỷỹĂÂĐÊÔƠƯÀÁẠẢÃẰẮẶẲẴẦẤẬẨẪÈÉẸẺẼỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕỒỐỘỔỖỜỚỢỞỠÙÚỤỦŨỪỨỰỬỮỲÝỴỶỸ]")


def detect_locale_from_text(text: str) -> str:
    """Best-effort locale detection from a text snippet."""
    if not isinstance(text, str) or not text.strip():
        return "zh-CN"
    if _HANGUL_RE.search(text):
        return "ko"
    if _HIRAGANA_RE.search(text) or _KATAKANA_RE.search(text):
        return "ja"
    if _VI_DIACRITICS_RE.search(text):
        return "vi"
    if _EN_RE.search(text):
        return "en"
    # Chinese: check for traditional-specific characters.
    traditional_hits = sum(1 for ch in text if ch in _TRADITIONAL_HINT_CHARS)
    if traditional_hits >= 2:
        return "zh-TW"
    return "zh-CN"


_instance: Optional[I18nManager] = None


def get_i18n_manager() -> I18nManager:
    """Return the process-wide :class:`I18nManager` singleton."""
    global _instance
    if _instance is None:
        _instance = I18nManager()
    return _instance
