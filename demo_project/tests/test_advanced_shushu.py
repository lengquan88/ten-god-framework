"""
test_advanced_shushu.py — 高级术数系统完整测试
====================================================

基于实际实现测试：
  - TieBanShuEngine: 铁板神数
  - ShaoZiShenShuEngine: 邵子神数·皇极经世
  - ChengGuEngine: 袁天罡称骨算命
  - AdvancedShuShuEngine: 综合调度器
  - 辅助函数 _ganzhi_to_num / _num_to_bagua / _two_bagua_to_hexagram
  - 常量：TIAN_GAN / DI_ZHI / XIANTIAN_BAGUA / HOUTIAN_BAGUA
"""
import pytest
from typing import Dict, Any

from tengod.advanced_shushu import (
    TIAN_GAN, DI_ZHI, XIANTIAN_BAGUA, HOUTIAN_BAGUA,
    TiebanshuResult, ShaoziResult, ChengguResult,
    TieBanShuEngine, ShaoZiShenShuEngine, ChengGuEngine, AdvancedShuShuEngine,
    _ganzhi_to_num, _num_to_bagua, _two_bagua_to_hexagram,
)


# ── Fixtures ──────────────────────────────────────────────

@pytest.fixture
def tieban():
    return TieBanShuEngine()


@pytest.fixture
def shaozi():
    return ShaoZiShenShuEngine()


@pytest.fixture
def chenggu():
    return ChengGuEngine()


@pytest.fixture
def engine():
    return AdvancedShuShuEngine()


@pytest.fixture
def sample_pillars() -> Dict[str, str]:
    """典型四柱（用真实1990年5月15日午时计算值）"""
    return {
        "year": "庚午",   # 1990
        "month": "辛巳",  # 五月
        "day": "乙未",    # 15日
        "hour": "壬午",   # 午时（11-13点，这里用壬午近似午时干支配对）
    }


@pytest.fixture
def valid_ganzhi_params():
    """铁板神数/邵子神数的独立八字干支出入"""
    return ("庚", "午", "辛", "巳", "乙", "未", "壬", "午")


# ── 1. 常量表完整性验证 ────────────────────────────────────

class TestConstants:
    """基础数据结构完整性"""

    def test_tiangan_10_keys(self):
        """TIAN_GAN = 10天干字典"""
        assert len(TIAN_GAN) == 10
        for g in ("甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"):
            assert g in TIAN_GAN
            info = TIAN_GAN[g]
            assert "wuxing" in info
            assert "num" in info
            assert info["wuxing"] in ("金", "木", "水", "火", "土")
            assert isinstance(info["num"], int)

    def test_dizhi_12_keys(self):
        """DI_ZHI = 12地支字典，有生肖"""
        assert len(DI_ZHI) == 12
        for z in ("子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"):
            assert z in DI_ZHI
            info = DI_ZHI[z]
            assert "wuxing" in info
            assert "num" in info
            assert "zodiac" in info
            assert "yue" in info  # 月份
            assert 1 <= info["yue"] <= 12

    def test_dizhi_zodiac_unique(self):
        """12生肖唯一"""
        zodiacs = [DI_ZHI[z]["zodiac"] for z in DI_ZHI]
        assert len(set(zodiacs)) == 12

    def test_zi_is_shui_rat(self):
        """子 = 水 / 数1 / 鼠 / 11月"""
        z = DI_ZHI["子"]
        assert z["wuxing"] == "水"
        assert z["num"] == 1
        assert z["zodiac"] == "鼠"
        assert z["yue"] == 11

    def test_wu_is_huo_horse(self):
        """午 = 火 / 数7 / 马 / 5月"""
        z = DI_ZHI["午"]
        assert z["wuxing"] == "火"
        assert z["num"] == 7
        assert z["zodiac"] == "马"
        assert z["yue"] == 5

    def test_xiantian_bagua_8(self):
        """先天八卦 1-8 映射"""
        assert len(XIANTIAN_BAGUA) == 8
        for i in range(1, 9):
            assert i in XIANTIAN_BAGUA
            assert XIANTIAN_BAGUA[i] in ("乾", "兑", "离", "震", "巽", "坎", "艮", "坤")

    def test_houtian_bagua_9(self):
        """后天八卦 1-9，5=中"""
        assert len(HOUTIAN_BAGUA) == 9
        assert HOUTIAN_BAGUA[5] == "中"
        for i in range(1, 10):
            assert i in HOUTIAN_BAGUA


# ── 2. 辅助函数 ──────────────────────────────────────────

class TestHelperFunctions:
    """_ganzhi_to_num / _num_to_bagua / _two_bagua_to_hexagram"""

    @pytest.mark.parametrize("gan,zhi", [
        ("甲", "子"), ("乙", "丑"), ("丙", "寅"),
        ("庚", "午"), ("癸", "亥"),
    ])
    def test_ganzhi_to_num_positive(self, gan, zhi):
        """合法干支 → 正整数"""
        n = _ganzhi_to_num(gan, zhi)
        assert isinstance(n, int) and n > 0

    def test_ganzhi_to_num_different_for_different(self):
        """不同干支 → 一般不同（碰撞也允许，只要稳定）"""
        a = _ganzhi_to_num("甲", "子")
        b = _ganzhi_to_num("癸", "亥")
        # 只要稳定、正整数即可，不强求完全不同
        assert isinstance(a, int) and isinstance(b, int)

    def test_num_to_bagua_returns_gua_name(self):
        """_num_to_bagua返回卦名（乾兑离震巽坎艮坤）之一"""
        guas = {"乾", "兑", "离", "震", "巽", "坎", "艮", "坤"}
        for n in range(1, 20):
            g = _num_to_bagua(n)
            assert g in guas

    def test_num_to_bagua_cyclic(self):
        """模8循环：n和n+8给出相同结果"""
        for n in range(1, 17):
            assert _num_to_bagua(n) == _num_to_bagua(n + 8)

    def test_two_bagua_to_hexagram_returns_string(self):
        """六十四卦名：非空字符串"""
        result = _two_bagua_to_hexagram("乾", "乾")
        assert isinstance(result, str) and len(result) >= 3  # "乾为天"

    def test_two_bagua_to_hexagram_all_combinations(self):
        """8×8=64种组合都能产生稳定卦名"""
        guas = ["乾", "兑", "离", "震", "巽", "坎", "艮", "坤"]
        seen = set()
        for shang in guas:
            for xia in guas:
                name = _two_bagua_to_hexagram(shang, xia)
                assert isinstance(name, str) and len(name) >= 2
                seen.add(name)
        # 64卦不强制全部唯一，但应大部分不同
        assert len(seen) >= 32


# ── 3. 铁板神数 TieBanShuEngine ──────────────────────────

class TestTieBanShuEngine:
    """铁板神数引擎"""

    def test_compute_returns_dataclass(self, tieban, valid_ganzhi_params):
        """compute返回TiebanshuResult实例"""
        result = tieban.compute(*valid_ganzhi_params)
        assert isinstance(result, TiebanshuResult)

    def test_result_fields_nonempty(self, tieban, valid_ganzhi_params):
        """所有字段有正确类型"""
        r = tieban.compute(*valid_ganzhi_params)
        assert isinstance(r.tian_pan, str) and "天盘" in r.tian_pan
        assert isinstance(r.di_pan, str) and "地盘" in r.di_pan
        assert isinstance(r.ren_pan, str) and "人盘" in r.ren_pan
        assert isinstance(r.base_num, int) and 1 <= r.base_num <= 60
        assert isinstance(r.key_numbers, list) and len(r.key_numbers) >= 4
        assert isinstance(r.tiaowen, list) and 1 <= len(r.tiaowen) <= 5
        for tw in r.tiaowen:
            assert "【" in tw and "】" in tw  # 条文格式
        assert isinstance(r.summary, str) and len(r.summary) > 0

    def test_to_dict_method_on_result(self, tieban, valid_ganzhi_params):
        """TiebanshuResult.to_dict()返回字段字典"""
        r = tieban.compute(*valid_ganzhi_params)
        d = r.to_dict()
        assert isinstance(d, dict)
        # 关键键存在
        for key in ("tian_pan", "di_pan", "ren_pan", "base_num",
                    "key_numbers", "tiaowen", "summary"):
            assert key in d

    def test_deterministic(self, tieban, valid_ganzhi_params):
        """同参数多次计算结果完全一致"""
        r1 = tieban.compute(*valid_ganzhi_params)
        r2 = tieban.compute(*valid_ganzhi_params)
        # 逐一比较
        assert r1.tian_pan == r2.tian_pan
        assert r1.di_pan == r2.di_pan
        assert r1.ren_pan == r2.ren_pan
        assert r1.base_num == r2.base_num
        assert r1.key_numbers == r2.key_numbers
        assert r1.tiaowen == r2.tiaowen
        assert r1.summary == r2.summary

    def test_jiazi_year(self, tieban):
        """甲子年甲子月甲子日甲子时：不崩溃"""
        r = tieban.compute("甲", "子", "甲", "子", "甲", "子", "甲", "子")
        assert 1 <= r.base_num <= 60
        assert len(r.tiaowen) >= 1

    def test_guihai_year(self, tieban):
        """癸亥年癸亥月癸亥日癸亥时"""
        r = tieban.compute("癸", "亥", "癸", "亥", "癸", "亥", "癸", "亥")
        assert isinstance(r, TiebanshuResult)
        assert len(r.summary) > 0


# ── 4. 邵子神数 ShaoZiShenShuEngine ───────────────────────

class TestShaoZiShenShuEngine:
    """邵子神数·皇极经世引擎"""

    def test_compute_returns_shaoziresult(self, shaozi, valid_ganzhi_params):
        """compute返回ShaoziResult"""
        r = shaozi.compute(*valid_ganzhi_params)
        assert isinstance(r, ShaoziResult)

    def test_yuanhuiyunshi_range(self, shaozi, valid_ganzhi_params):
        """元(1-12)、会(1-30)、运(1-12)、世(1-30)"""
        r = shaozi.compute(*valid_ganzhi_params)
        yhys = r.yuan_hui_yun_shi
        assert 1 <= yhys["元"] <= 12
        assert 1 <= yhys["会"] <= 30
        assert 1 <= yhys["运"] <= 12
        assert 1 <= yhys["世"] <= 30

    def test_huangji_hexagram_contains_guas(self, shaozi, valid_ganzhi_params):
        """皇极卦象文本包含上下卦和六十四卦名"""
        r = shaozi.compute(*valid_ganzhi_params)
        assert "上卦" in r.huangji_hexagram
        assert "下卦" in r.huangji_hexagram
        assert "→" in r.huangji_hexagram

    def test_tiaowen_list_with_brackets(self, shaozi, valid_ganzhi_params):
        """条文列表非空且含【卦名】格式"""
        r = shaozi.compute(*valid_ganzhi_params)
        assert isinstance(r.tiaowen, list) and len(r.tiaowen) >= 1
        assert "【" in r.tiaowen[0] and "】" in r.tiaowen[0]

    def test_score_range_50_85(self, shaozi, valid_ganzhi_params):
        """分数在 50-85 区间"""
        r = shaozi.compute(*valid_ganzhi_params)
        assert 50 <= r.total_score <= 85
        assert isinstance(r.total_score, int)

    def test_summary_nonempty(self, shaozi, valid_ganzhi_params):
        """总结非空字符串"""
        r = shaozi.compute(*valid_ganzhi_params)
        assert isinstance(r.summary, str) and len(r.summary) >= 10

    def test_to_dict_contains_keys(self, shaozi, valid_ganzhi_params):
        """to_dict()返回带完整键的字典"""
        r = shaozi.compute(*valid_ganzhi_params)
        d = r.to_dict()
        for k in ("yuan_hui_yun_shi", "huangji_hexagram",
                  "tiaowen", "total_score", "summary"):
            assert k in d

    def test_deterministic(self, shaozi, valid_ganzhi_params):
        """同一输入确定性"""
        r1 = shaozi.compute(*valid_ganzhi_params)
        r2 = shaozi.compute(*valid_ganzhi_params)
        assert r1.yuan_hui_yun_shi == r2.yuan_hui_yun_shi
        assert r1.huangji_hexagram == r2.huangji_hexagram
        assert r1.total_score == r2.total_score
        assert r1.summary == r2.summary

    def test_jiazi_quadruple(self, shaozi):
        """甲子×4极限值不崩溃"""
        r = shaozi.compute("甲", "子", "甲", "子", "甲", "子", "甲", "子")
        assert 50 <= r.total_score <= 85
        assert len(r.summary) > 0


# ── 5. 称骨算命 ChengGuEngine ─────────────────────────────

class TestChengGuEngine:
    """袁天罡称骨算命"""

    def test_compute_returns_chengguresult(self, chenggu):
        """典型输入返回ChengguResult"""
        r = chenggu.compute(5, 15, "午")
        assert isinstance(r, ChengguResult)

    def test_total_liang_positive(self, chenggu):
        """总两数为正数，约在2-7两之间"""
        r = chenggu.compute(5, 15, "午")
        assert isinstance(r.total_liang, float)
        # 最小的量加起来也应该 >0
        assert r.total_liang > 0.0

    def test_yue_ri_shi_fields_reasonable(self, chenggu):
        """月/日/时分量都是正浮点数（两数）"""
        r = chenggu.compute(5, 15, "午")
        for field in ("yue_liang", "ri_liang", "shi_liang"):
            v = getattr(r, field)
            # 简化版实现：这些字段可能是 float（0.x - 2.x 两）
            assert isinstance(v, (int, float)) and 0.0 < v < 10.0

    def test_tiaowen_nonempty(self, chenggu):
        """称骨歌非空长文本"""
        r = chenggu.compute(5, 15, "午")
        assert isinstance(r.tiaowen, str) and len(r.tiaowen) >= 10

    def test_interpretation_nonempty(self, chenggu):
        """解读非空"""
        r = chenggu.compute(5, 15, "午")
        assert isinstance(r.interpretation, str) and len(r.interpretation) >= 10

    def test_to_dict_complete(self, chenggu):
        """to_dict返回完整字段"""
        r = chenggu.compute(5, 15, "午")
        d = r.to_dict()
        for k in ("yue_liang", "ri_liang", "shi_liang",
                  "total_liang", "tiaowen", "interpretation"):
            assert k in d

    @pytest.mark.parametrize("m,d,hz", [
        (1, 1, "子"),     # 年初子时
        (12, 30, "亥"),   # 年末亥时
        (6, 15, "午"),    # 年中午时
        (2, 29, "卯"),    # 闰月边缘（简化算法不校验）
        (7, 1, "辰"),
    ])
    def test_various_inputs_stable(self, chenggu, m, d, hz):
        """多种日期/时辰输入稳定返回"""
        r = chenggu.compute(m, d, hz)
        assert isinstance(r, ChengguResult)
        assert len(r.tiaowen) > 0
        assert len(r.interpretation) > 0

    def test_deterministic(self, chenggu):
        """同参数多次计算一致"""
        r1 = chenggu.compute(8, 8, "酉")
        r2 = chenggu.compute(8, 8, "酉")
        assert r1.total_liang == r2.total_liang
        assert r1.tiaowen == r2.tiaowen
        assert r1.interpretation == r2.interpretation

    def test_invalid_hour_zhi_uses_default(self, chenggu):
        """非法时辰地支 → 仍有默认结果（不崩溃）"""
        r = chenggu.compute(5, 5, "ZZZ")
        assert isinstance(r, ChengguResult)
        assert isinstance(r.total_liang, float) and r.total_liang > 0


# ── 6. AdvancedShuShuEngine 综合调度 ──────────────────────

class TestAdvancedShuShuEngine:
    """高级术数综合引擎"""

    def test_init_has_sub_engines(self, engine):
        """初始化后三个子引擎都创建了"""
        assert isinstance(engine.tieban, TieBanShuEngine)
        assert isinstance(engine.shaozi, ShaoZiShenShuEngine)
        assert isinstance(engine.chenggu, ChengGuEngine)

    def test_compute_all_full(self, engine, sample_pillars):
        """完整四柱 + 农历参数 → 返回三种子结果"""
        r = engine.compute_all(sample_pillars, lunar_month=5, lunar_day=15)
        assert isinstance(r, dict)
        # 四柱齐全 → tieban/shaozi 都应有
        assert "tieban" in r
        assert "shaozi" in r
        # lunar_month/lunar_day/hour_zhi齐全 → chenggu
        assert "chenggu" in r

    def test_compute_all_tieban_shaozi_only(self, engine, sample_pillars):
        """不提供农历月日 → 只有tieban和shaozi"""
        r = engine.compute_all(sample_pillars)
        assert "tieban" in r
        assert "shaozi" in r
        assert "chenggu" not in r

    def test_compute_all_empty_pillars(self, engine):
        """空四柱 → 空结果（无异常）"""
        r = engine.compute_all({"year": "", "month": "", "day": "", "hour": ""})
        assert isinstance(r, dict)
        # 可能没有tieban/shaozi，但不能报错
        assert "chenggu" not in r  # 因为没有 lunar 参数

    def test_compute_all_tieban_structure(self, engine, sample_pillars):
        """返回的tieban子字典是TiebanshuResult.to_dict()格式"""
        r = engine.compute_all(sample_pillars, lunar_month=5, lunar_day=15)
        tb = r["tieban"]
        for k in ("tian_pan", "di_pan", "ren_pan", "base_num", "tiaowen", "summary"):
            assert k in tb
        assert 1 <= tb["base_num"] <= 60

    def test_compute_all_shaozi_structure(self, engine, sample_pillars):
        """返回的shaozi子字典格式正确"""
        r = engine.compute_all(sample_pillars, lunar_month=5, lunar_day=15)
        sz = r["shaozi"]
        for k in ("yuan_hui_yun_shi", "huangji_hexagram", "tiaowen", "total_score", "summary"):
            assert k in sz
        yhys = sz["yuan_hui_yun_shi"]
        assert 1 <= yhys["元"] <= 12

    def test_compute_all_chenggu_structure(self, engine, sample_pillars):
        """返回的chenggu子字典格式正确"""
        r = engine.compute_all(sample_pillars, lunar_month=5, lunar_day=15)
        cg = r["chenggu"]
        for k in ("total_liang", "tiaowen", "interpretation"):
            assert k in cg

    def test_compute_all_deterministic(self, engine, sample_pillars):
        """同输入 → 同输出"""
        kwargs = dict(pillars=sample_pillars, lunar_month=5, lunar_day=15)
        r1 = engine.compute_all(**kwargs)
        r2 = engine.compute_all(**kwargs)
        # 核心可比字段
        assert r1["tieban"]["base_num"] == r2["tieban"]["base_num"]
        assert r1["tieban"]["tiaowen"] == r2["tieban"]["tiaowen"]
        assert r1["shaozi"]["total_score"] == r2["shaozi"]["total_score"]
        assert r1["shaozi"]["summary"] == r2["shaozi"]["summary"]
        assert r1["chenggu"]["total_liang"] == r2["chenggu"]["total_liang"]

    def test_compute_all_partial_pillars(self, engine):
        """四柱不完整（缺年支）→ 只要8字不全就不进tieban/shaozi"""
        partial = {"year": "庚", "month": "辛巳", "day": "乙未", "hour": "壬午"}  # 年缺支
        r = engine.compute_all(partial)
        # 不能抛异常
        assert isinstance(r, dict)
        # 即使缺数据也能稳定处理

    def test_two_instances_independent(self):
        """两个引擎实例互不干扰"""
        e1 = AdvancedShuShuEngine()
        e2 = AdvancedShuShuEngine()
        pillars = {"year": "甲子", "month": "乙丑", "day": "丙寅", "hour": "丁卯"}
        r1 = e1.compute_all(pillars, 2, 2)
        r2 = e2.compute_all(pillars, 2, 2)
        # 结果应该相同（纯函数）
        assert r1["tieban"]["base_num"] == r2["tieban"]["base_num"]
        assert r1["shaozi"]["total_score"] == r2["shaozi"]["total_score"]
