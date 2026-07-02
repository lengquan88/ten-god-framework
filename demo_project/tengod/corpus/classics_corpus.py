"""
classics_corpus.py — 命理经典语料库 v3.6.0
===============================================
道曰："执古之道，以御今之有。"

中华命理经典文献结构化入库，支持：
  - 渊海子平（八字经典）
  - 三命通会（八字集大成）
  - 紫微斗数全书（紫微经典）
  - 易隐（六爻经典）
  - 葬书/青囊经（风水经典）
  - 姓名学（五格数理）

结构化格式：
  {
    "id": "unique_id",
    "source": "渊海子平",
    "chapter": "第一章",
    "text": "原文内容",
    "category": "八字",
    "keywords": ["天干", "地支", "五行"],
    "embedding": null (运行时生成)
  }

用法：
    corpus = ClassicsCorpus()
    corpus.load_all()
    results = corpus.search("天干 地支 五行", top_k=10)
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

_CORPUS_DIR = os.path.dirname(os.path.abspath(__file__))


# ============================================================================
# 经典文献数据
# ============================================================================

# 渊海子平（八字经典）
_YUANHAI_ZIPING = [
    {"chapter": "论天干", "text": "甲乙木，丙丁火，戊己土，庚辛金，壬癸水。天干有阴阳，甲丙戊庚壬为阳，乙丁己辛癸为阴。天干相合：甲己合土，乙庚合金，丙辛合水，丁壬合木，戊癸合火。", "keywords": ["天干", "阴阳", "相合", "五行"]},
    {"chapter": "论地支", "text": "子丑寅卯辰巳午未申酉戌亥为十二地支。子水、丑土、寅木、卯木、辰土、巳火、午火、未土、申金、酉金、戌土、亥水。地支三合：申子辰合水，亥卯未合木，寅午戌合火，巳酉丑合金。", "keywords": ["地支", "三合", "方位"]},
    {"chapter": "论五行生克", "text": "五行相生：木生火，火生土，土生金，金生水，水生木。五行相克：木克土，土克水，水克火，火克金，金克木。生我者为印，我生者为食伤，克我者为官杀，我克者为财，同我者为比劫。", "keywords": ["五行", "生克", "十神", "印", "食伤", "官杀", "财", "比劫"]},
    {"chapter": "论十神", "text": "十神者：正官、七杀、正印、偏印、正财、偏财、食神、伤官、比肩、劫财。以日干为我，看四柱天干地支所藏，定十神。正官为克我之异性，七杀为克我之同性，正印为生我之异性，偏印为生我之同性。", "keywords": ["十神", "正官", "七杀", "正印", "偏印", "正财", "偏财", "食神", "伤官", "比肩", "劫财"]},
    {"chapter": "论大运流年", "text": "大运以月柱为基，阳男阴女顺排，阴男阳女逆排。起运岁数以节气至出生日之差计算。流年者，每年之干支也。大运管十年，流年管一年。大运吉凶须结合原局，流年应期以五行生克为断。", "keywords": ["大运", "流年", "起运", "节气", "顺排", "逆排"]},
    {"chapter": "论格局", "text": "格局者，八格为正格，外格为变格。正格：正官格、七杀格、正印格、偏印格、正财格、偏财格、食神格、伤官格。变格：从格、化格、专旺格等。格局清浊贵贱，以用神为枢。", "keywords": ["格局", "正格", "变格", "从格", "化格", "专旺", "用神"]},
]

# 三命通会（八字集大成）
_SANMING_TONGHUI = [
    {"chapter": "论六十甲子", "text": "甲子乙丑海中金，丙寅丁卯炉中火，戊辰己巳大林木，庚午辛未路旁土，壬申癸酉剑锋金。六十甲子纳音，以干支五行合化而成。", "keywords": ["六十甲子", "纳音", "海中金", "炉中火", "大林木"]},
    {"chapter": "论神煞", "text": "神煞者，天乙贵人、文昌、学堂、将星、华盖、驿马、桃花、羊刃、劫煞、亡神等。天乙贵人：甲戊庚牛羊，乙己鼠猴乡，丙丁猪鸡位，壬癸兔蛇藏，六辛逢马虎，此是贵人方。", "keywords": ["神煞", "天乙贵人", "文昌", "将星", "华盖", "驿马", "桃花", "羊刃"]},
    {"chapter": "论用神", "text": "用神者，八字之中最得力之字也。以日主强弱为基，旺则用克泄耗，弱则用生扶助。调候用神以月令为纲，冬用水火，夏用水金。", "keywords": ["用神", "日主", "身强", "身弱", "调候", "扶抑"]},
    {"chapter": "论六亲", "text": "六亲：父母、兄弟、妻财、子孙。以十神论六亲，正印为母，偏财为父，比肩为兄弟，正财为妻，官杀为子女。", "keywords": ["六亲", "父母", "兄弟", "妻财", "子孙"]},
]

# 紫微斗数全书
_ZIWEI_QUANSHU = [
    {"chapter": "论十二宫", "text": "紫微斗数十二宫：命宫为根基，兄弟宫论手足，夫妻宫看姻缘，子女宫论后嗣，财帛宫主财运，疾厄宫观健康，迁移宫主出行，交友宫论朋友，官禄宫主事业，田宅宫看房产，福德宫主福报，父母宫论尊长。", "keywords": ["十二宫", "命宫", "兄弟宫", "夫妻宫", "子女宫", "财帛宫", "疾厄宫", "迁移宫", "交友宫", "官禄宫", "田宅宫", "福德宫", "父母宫"]},
    {"chapter": "论十四主星", "text": "十四主星：紫微、天机、太阳、武曲、天同、廉贞、天府、太阴、贪狼、巨门、天相、天梁、七杀、破军。紫微为帝星，天机为谋士，太阳为光明，武曲为财星，天同为福星，廉贞为囚星，天府为库星，太阴为月星，贪狼为桃花，巨门为暗星，天相为印星，天梁为寿星，七杀为将星，破军为耗星。", "keywords": ["十四主星", "紫微", "天机", "太阳", "武曲", "天同", "廉贞", "天府", "太阴", "贪狼", "巨门", "天相", "天梁", "七杀", "破军"]},
    {"chapter": "论四化", "text": "四化者，化禄、化权、化科、化忌。化禄为福，化权为势，化科为名，化忌为厄。四化飞星以生年天干定之，甲廉破武阳，乙机梁紫阴，丙同机昌廉，丁阴同机巨。", "keywords": ["四化", "化禄", "化权", "化科", "化忌", "飞星"]},
    {"chapter": "论三方四正", "text": "三方者，命宫、财帛宫、官禄宫也。四正者，三方加迁移宫。三方四正为命盘核心，星曜分布以三方四正为要。", "keywords": ["三方四正", "对宫", "夹宫", "借星"]},
]

# 六爻经典
_LIUYAO_JINGDIAN = [
    {"chapter": "论起卦", "text": "六爻起卦法：以三枚铜钱，合掌摇晃，掷于案上。三枚皆正面为老阳（变爻），三枚皆反面为老阴（变爻），两正一反为少阳，两反一正为少阴。自下而上，六次得六爻，组成一卦。", "keywords": ["起卦", "铜钱", "老阳", "老阴", "少阳", "少阴", "变爻"]},
    {"chapter": "论六亲", "text": "六爻六亲：父母、兄弟、妻财、官鬼、子孙。以卦宫所属五行为我，各爻地支五行生克定六亲。生我者父母，我生者子孙，克我者官鬼，我克者妻财，同我者兄弟。", "keywords": ["六亲", "父母", "兄弟", "妻财", "官鬼", "子孙"]},
    {"chapter": "论六兽", "text": "六兽：青龙、朱雀、勾陈、腾蛇、白虎、玄武。以日辰天干起六兽，甲乙起青龙，丙丁起朱雀，戊日起勾陈，己日起腾蛇，庚辛起白虎，壬癸起玄武。", "keywords": ["六兽", "青龙", "朱雀", "勾陈", "腾蛇", "白虎", "玄武"]},
    {"chapter": "论用神", "text": "用神以六亲取用。占父母以父母爻为用神，占兄弟以兄弟爻为用神，占妻财以妻财爻为用神，占官讼以官鬼爻为用神，占子孙以子孙爻为用神。", "keywords": ["用神", "元神", "忌神", "仇神", "世爻", "应爻"]},
]

# 风水经典
_FENGSHUI_JINGDIAN = [
    {"chapter": "论龙穴砂水向", "text": "风水五诀：龙、穴、砂、水、向。龙者，山脉之势也；穴者，气之所聚也；砂者，环抱之山也；水者，来去之流也；向者，坐向之位也。五者俱备，方为吉地。", "keywords": ["龙", "穴", "砂", "水", "向", "峦头"]},
    {"chapter": "论玄空飞星", "text": "玄空飞星以九宫飞布论吉凶。运星入中，山向两星顺逆飞布。旺山旺向为上吉，双星会向次之，上山下水为凶。三元九运，一运二十年，三元共一百八十年。", "keywords": ["玄空", "飞星", "九宫", "三元九运", "山星", "向星", "旺山旺向"]},
    {"chapter": "论八宅", "text": "八宅以命卦配宅卦。命卦以出生年定，宅卦以坐向定。东西四命：坎离震巽为东四命，乾坤艮兑为西四命。命宅相配为吉，相克为凶。", "keywords": ["八宅", "命卦", "宅卦", "东四命", "西四命"]},
]

# 姓名学
_XINGMINGXUE = [
    {"chapter": "论五格", "text": "五格：天格、人格、地格、外格、总格。天格为祖先传承，人格为自身运势，地格为根基，外格为外界关系，总格为一生总结。", "keywords": ["五格", "天格", "人格", "地格", "外格", "总格"]},
    {"chapter": "论三才", "text": "三才配置：天格、人格、地格之五行关系。三才相生为吉，相克为凶。木木木大吉，木木火中吉，木木土中吉，金金金大凶。", "keywords": ["三才", "配置", "五行"]},
    {"chapter": "论81数理", "text": "81数理：1数太极之数，2数混沌之数，3数进取之数，4数破坏之数，5数福寿之数，6数安稳之数，7数刚毅之数，8数勤勉之数，9数穷困之数。", "keywords": ["81数理", "吉凶", "数理"]},
    {"chapter": "论生肖取名", "text": "生肖取名：以出生年份生肖为据。鼠喜米豆，牛喜草田，虎喜山林，兔喜洞穴，龙喜水云，蛇喜洞穴，马喜草原，羊喜草山，猴喜林果，鸡喜米谷，狗喜肉骨，猪喜食槽。", "keywords": ["生肖", "取名", "十二生肖"]},
]


class ClassicsCorpus:
    """命理经典语料库 v3.6.0"""

    def __init__(self):
        self._entries: List[Dict[str, Any]] = []
        self._loaded = False

    def load_all(self) -> "ClassicsCorpus":
        """加载全部经典文献"""
        if self._loaded:
            return self

        sources = [
            ("渊海子平", "八字", _YUANHAI_ZIPING),
            ("三命通会", "八字", _SANMING_TONGHUI),
            ("紫微斗数全书", "紫微斗数", _ZIWEI_QUANSHU),
            ("六爻经典", "六爻占卜", _LIUYAO_JINGDIAN),
            ("风水经典", "风水堪舆", _FENGSHUI_JINGDIAN),
            ("姓名学", "姓名学", _XINGMINGXUE),
        ]

        idx = 0
        for source_name, category, entries in sources:
            for entry in entries:
                self._entries.append({
                    "id": f"classic_{idx:04d}",
                    "source": source_name,
                    "chapter": entry["chapter"],
                    "text": entry["text"],
                    "category": category,
                    "keywords": entry["keywords"],
                })
                idx += 1

        self._loaded = True
        return self

    def search(self, query: str, top_k: int = 10, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """关键词检索

        Args:
            query: 查询文本
            top_k: 返回数量
            category: 可选的分类过滤

        Returns:
            按关键词匹配度排序的条目列表
        """
        results = []
        for entry in self._entries:
            if category and entry["category"] != category:
                continue
            # 关键词匹配分数
            score = 0
            # 在文本中匹配
            for kw in entry["keywords"]:
                if kw in query:
                    score += 1
            # 反向：查询词在文本中
            for word in query:
                if word in entry["text"]:
                    score += 0.5
            if score > 0:
                results.append((score, entry))

        results.sort(key=lambda x: x[0], reverse=True)
        return [
            {"score": round(s, 2), **entry}
            for s, entry in results[:top_k]
        ]

    def get_by_category(self, category: str) -> List[Dict[str, Any]]:
        """按分类获取全部条目"""
        return [entry for entry in self._entries if entry["category"] == category]

    def get_all_texts(self) -> List[str]:
        """获取所有文本（用于嵌入训练）"""
        return [entry["text"] for entry in self._entries]

    def get_stats(self) -> Dict[str, Any]:
        """获取语料库统计"""
        if not self._loaded:
            self.load_all()
        categories = {}
        for entry in self._entries:
            cat = entry["category"]
            categories[cat] = categories.get(cat, 0) + 1
        return {
            "total_entries": len(self._entries),
            "sources": list(set(e["source"] for e in self._entries)),
            "categories": categories,
            "total_chars": sum(len(e["text"]) for e in self._entries),
        }


# ============================================================================
# 自检
# ============================================================================

if __name__ == "__main__":
    corpus = ClassicsCorpus()
    corpus.load_all()
    stats = corpus.get_stats()
    print("=" * 60)
    print("  命理经典语料库 v3.6.0")
    print("=" * 60)
    print(f"\n  条目总数: {stats['total_entries']}")
    print(f"  总字符数: {stats['total_chars']}")
    print(f"  分类分布: {stats['categories']}")

    print("\n  检索测试: '天干 地支 五行'")
    results = corpus.search("天干 地支 五行", top_k=3)
    for r in results:
        print(f"    [{r['score']}] {r['source']} · {r['chapter']}: {r['text'][:50]}...")

    print("\n  八字分类检索: '大运 流年 用神'")
    results = corpus.search("大运 流年 用神", top_k=3, category="八字")
    for r in results:
        print(f"    [{r['score']}] {r['source']} · {r['chapter']}")

    print("\n" + "=" * 60)
    print("  自检完成")
    print("=" * 60)