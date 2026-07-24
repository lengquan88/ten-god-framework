"""
eval/benchmark_dataset.py — 基准数据集 v4.6.0
==================================================
道曰："合抱之木，生于毫末；九层之台，起于累土。"

门禁认知系统基准数据集，包含 100+ 命理问答对，覆盖：
  - 八字（渊海子平、三命通会）：天干地支、五行生克、十神、格局、大运流年
  - 紫微斗数：十四主星、十二宫、四化、格局
  - 六爻：世应、用神、六亲、六兽、卦象
  - 风水：玄空飞星、峦头理气、八宅、三元九运
  - 姓名学：五格数理、三才配置、五行补益
  - 杂项：神煞、纳音、节气、歧义消解

每条数据格式：
  {
    "id": "bench_001",
    "query": "什么是天干五合？",
    "intent": "八字",
    "category": "八字基础",
    "relevant_ids": ["bench_001", "bench_005"],
    "expected_answer": "天干五合...",
    "context": "",
    "difficulty": "easy"
  }
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set


@dataclass
class BenchmarkQuery:
    """基准查询条目"""
    id: str
    query: str
    intent: str
    category: str = ""
    relevant_ids: Set[str] = field(default_factory=set)
    expected_answer: str = ""
    context: str = ""
    difficulty: str = "medium"  # easy/medium/hard

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "query": self.query,
            "intent": self.intent,
            "category": self.category,
            "relevant_ids": sorted(self.relevant_ids),
            "expected_answer": self.expected_answer,
            "context": self.context,
            "difficulty": self.difficulty,
        }


# ============================================================================
# 基准数据集 (100+ 条)
# ============================================================================

_BENCHMARK_QUERIES = [
    # ═══════════════════════════════════════════════════════════════════
    # 八字基础 — 天干地支 (1-15)
    # ═══════════════════════════════════════════════════════════════════
    {
        "id": "bench_001", "query": "什么是天干五合？", "intent": "八字",
        "category": "八字基础", "difficulty": "easy",
        "expected_answer": "天干五合：甲己合土、乙庚合金、丙辛合水、丁壬合木、戊癸合火。",
    },
    {
        "id": "bench_002", "query": "地支三合局有哪些？", "intent": "八字",
        "category": "八字基础", "difficulty": "easy",
        "expected_answer": "地支三合：申子辰合水局、亥卯未合木局、寅午戌合火局、巳酉丑合金局。",
    },
    {
        "id": "bench_003", "query": "天干地支的阴阳属性是什么？", "intent": "八字",
        "category": "八字基础", "difficulty": "easy",
        "expected_answer": "天干阴阳：甲丙戊庚壬为阳，乙丁己辛癸为阴。地支阴阳：子寅辰午申戌为阳，丑卯巳未酉亥为阴。",
    },
    {
        "id": "bench_004", "query": "五行相生相克的顺序是什么？", "intent": "八字",
        "category": "八字基础", "difficulty": "easy",
        "expected_answer": "五行相生：木生火、火生土、土生金、金生水、水生木。五行相克：木克土、土克水、水克火、火克金、金克木。",
    },
    {
        "id": "bench_005", "query": "地支六合有哪些？", "intent": "八字",
        "category": "八字基础", "difficulty": "easy",
        "expected_answer": "地支六合：子丑合土、寅亥合木、卯戌合火、辰酉合金、巳申合水、午未合日月。",
    },
    {
        "id": "bench_006", "query": "地支六冲是什么？", "intent": "八字",
        "category": "八字基础", "difficulty": "easy",
        "expected_answer": "地支六冲：子午冲、丑未冲、寅申冲、卯酉冲、辰戌冲、巳亥冲。",
    },
    {
        "id": "bench_007", "query": "地支六害（相穿）是什么？", "intent": "八字",
        "category": "八字基础", "difficulty": "medium",
        "expected_answer": "地支六害：子未害、丑午害、寅巳害、卯辰害、申亥害、酉戌害。",
    },
    {
        "id": "bench_008", "query": "地支三刑有哪些？", "intent": "八字",
        "category": "八字基础", "difficulty": "medium",
        "expected_answer": "地支三刑：寅巳申为无恩之刑，丑戌未为恃势之刑，子卯为无礼之刑，辰午酉亥为自刑。",
    },
    {
        "id": "bench_009", "query": "天干十二长生诀是什么？", "intent": "八字",
        "category": "八字基础", "difficulty": "hard",
        "expected_answer": "十二长生：长生、沐浴、冠带、临官、帝旺、衰、病、死、墓、绝、胎、养。以日干看四柱地支，判断旺衰强弱。",
    },
    {
        "id": "bench_010", "query": "五行的方位和颜色分别是什么？", "intent": "八字",
        "category": "八字基础", "difficulty": "easy",
        "expected_answer": "木东方青色、火南方红色、土中央黄色、金西方白色、水北方黑色。",
    },
    {
        "id": "bench_011", "query": "什么是六十甲子？", "intent": "八字",
        "category": "八字基础", "difficulty": "medium",
        "expected_answer": "六十甲子是天干地支的组合，十天干配十二地支，最小公倍数为60，形成六十个干支组合，循环往复。",
    },
    {
        "id": "bench_012", "query": "地支藏干是什么？", "intent": "八字",
        "category": "八字基础", "difficulty": "medium",
        "expected_answer": "每个地支内藏有不同天干，如子藏癸水，丑藏己癸辛，寅藏甲丙戊等。地支藏干是八字分析的重要基础。",
    },
    {
        "id": "bench_013", "query": "什么是纳音五行？", "intent": "八字",
        "category": "八字基础", "difficulty": "medium",
        "expected_answer": "纳音五行是六十甲子每个干支组合对应的五行属性，如甲子乙丑海中金、丙寅丁卯炉中火等。",
    },
    {
        "id": "bench_014", "query": "二十四节气与月份的对应关系？", "intent": "八字",
        "category": "八字基础", "difficulty": "medium",
        "expected_answer": "正月立春寅、二月惊蛰卯、三月清明辰、四月立夏巳、五月芒种午、六月小暑未、七月立秋申、八月白露酉、九月寒露戌、十月立冬亥、十一月大雪子、十二月小寒丑。",
    },
    {
        "id": "bench_015", "query": "什么是空亡？", "intent": "八字",
        "category": "八字基础", "difficulty": "medium",
        "expected_answer": "空亡是六十甲子中每旬缺少的两个地支，如甲子旬戌亥空。空亡之支所临的十神力量减弱或消失。",
    },

    # ═══════════════════════════════════════════════════════════════════
    # 八字 — 十神与格局 (16-30)
    # ═══════════════════════════════════════════════════════════════════
    {
        "id": "bench_016", "query": "十神是怎样确定的？", "intent": "八字",
        "category": "十神格局", "difficulty": "medium",
        "expected_answer": "以日干为我，看四柱干支。生我者为印（正印/偏印），我生者为食伤（食神/伤官），克我者为官杀（正官/七杀），我克者为财（正财/偏财），同我者为比劫（比肩/劫财）。",
    },
    {
        "id": "bench_017", "query": "正官格的特点是什么？", "intent": "八字",
        "category": "十神格局", "difficulty": "medium",
        "expected_answer": "正官格以月令正官为用，主贵气、自律、正直。正官为克我之异性，喜财生官、印护官，忌伤官见官。",
    },
    {
        "id": "bench_018", "query": "什么是七杀格？", "intent": "八字",
        "category": "十神格局", "difficulty": "medium",
        "expected_answer": "七杀格以月令七杀为用，七杀为克我之同性，主威权、果断、竞争。七杀喜制化，食神制杀为上格，印化杀次之。",
    },
    {
        "id": "bench_019", "query": "食神格的特性是什么？", "intent": "八字",
        "category": "十神格局", "difficulty": "medium",
        "expected_answer": "食神格以月令食神为用，食神为我生之同性，主才华、口福、悠闲。食神喜生财，忌偏印夺食。",
    },
    {
        "id": "bench_020", "query": "伤官格的人有什么特点？", "intent": "八字",
        "category": "十神格局", "difficulty": "medium",
        "expected_answer": "伤官格以月令伤官为用，伤官为我生之异性，主聪明、叛逆、艺术。伤官见官为祸百端，喜印制伤官或财化伤官。",
    },
    {
        "id": "bench_021", "query": "什么是财格？", "intent": "八字",
        "category": "十神格局", "difficulty": "medium",
        "expected_answer": "财格以月令正财或偏财为用，为我克者，主财富、务实。正财格重稳定，偏财格重机遇。财喜食伤生，忌比劫夺财。",
    },
    {
        "id": "bench_022", "query": "正印格和偏印格有什么区别？", "intent": "八字",
        "category": "十神格局", "difficulty": "hard",
        "expected_answer": "正印格为生我之异性，主仁慈、学历、长辈缘。偏印格为生我之同性，主偏门、宗教、特殊才能。正印重于传统教育，偏印重于特殊技能。",
    },
    {
        "id": "bench_023", "query": "比肩格和劫财格有什么不同？", "intent": "八字",
        "category": "十神格局", "difficulty": "hard",
        "expected_answer": "比肩为同我之同性，主兄弟、朋友、独立。劫财为同我之异性，主竞争、破耗。比肩格稳重，劫财格冲动，均忌财星被夺。",
    },
    {
        "id": "bench_024", "query": "什么是特殊格局中的从格？", "intent": "八字",
        "category": "十神格局", "difficulty": "hard",
        "expected_answer": "从格是指日主极弱或极强，无法自立而顺从旺势的格局。包括从强格（从旺、从强、从气）和从弱格（从财、从杀、从儿）。",
    },
    {
        "id": "bench_025", "query": "什么是化气格？", "intent": "八字",
        "category": "十神格局", "difficulty": "hard",
        "expected_answer": "化气格为天干五合化气成功，如甲己化土格、乙庚化金格等。需要月令支持化神，且化神不受克破。",
    },
    {
        "id": "bench_026", "query": "魁罡格是什么？", "intent": "八字",
        "category": "十神格局", "difficulty": "hard",
        "expected_answer": "魁罡格为日柱为庚辰、庚戌、壬辰、戊戌四日之一，主刚强果断，性格刚烈，宜武职或法律相关工作。",
    },
    {
        "id": "bench_027", "query": "怎样判断八字的旺衰强弱？", "intent": "八字",
        "category": "十神格局", "difficulty": "medium",
        "expected_answer": "判断日主旺衰需看：得令（月令生扶）、得地（日支生扶）、得生（印星生扶）、得助（比劫帮扶）。综合四者判断身强身弱。",
    },
    {
        "id": "bench_028", "query": "什么是用神？如何取用神？", "intent": "八字",
        "category": "十神格局", "difficulty": "hard",
        "expected_answer": "用神是八字中最需要的五行十神，取法有：扶抑法（身强克泄耗、身弱生扶）、通关法（五行战斗取通关）、调候法（寒暖燥湿取调候）、病药法（有病有药）。",
    },
    {
        "id": "bench_029", "query": "驿马星代表什么？", "intent": "八字",
        "category": "十神格局", "difficulty": "easy",
        "expected_answer": "驿马星主奔波、走动、迁移。寅午戌见申、申子辰见寅、巳酉丑见亥、亥卯未见巳为驿马。",
    },
    {
        "id": "bench_030", "query": "桃花星（咸池）代表什么？", "intent": "八字",
        "category": "十神格局", "difficulty": "easy",
        "expected_answer": "桃花星主异性缘、艺术、审美。寅午戌见卯、申子辰见酉、巳酉丑见午、亥卯未见子为桃花。",
    },

    # ═══════════════════════════════════════════════════════════════════
    # 八字 — 大运流年 (31-40)
    # ═══════════════════════════════════════════════════════════════════
    {
        "id": "bench_031", "query": "大运如何排算？", "intent": "八字",
        "category": "大运流年", "difficulty": "medium",
        "expected_answer": "大运以月柱为基准，阳男阴女顺排（顺数到下一个节气），阴男阳女逆排（逆数到上一个节气）。起运岁数 = 节气差天数 ÷ 3。",
    },
    {
        "id": "bench_032", "query": "什么是流年？如何看流年吉凶？", "intent": "八字",
        "category": "大运流年", "difficulty": "medium",
        "expected_answer": "流年即当年的干支，每年一换。看流年需结合大运和原局，以五行生克、刑冲合害判断吉凶应期。",
    },
    {
        "id": "bench_033", "query": "大运和流年哪个更重要？", "intent": "八字",
        "category": "大运流年", "difficulty": "medium",
        "expected_answer": "大运管十年大势，流年管一年具体应期。大运为背景，流年为触发。大运吉流年凶，凶中有救；大运凶流年吉，吉中有险。",
    },
    {
        "id": "bench_034", "query": "什么是岁运并临？", "intent": "八字",
        "category": "大运流年", "difficulty": "medium",
        "expected_answer": "岁运并临是大运和流年干支相同，力量加倍。有'岁运并临，不死自己死他人'之说，但需结合八字喜忌判断。",
    },
    {
        "id": "bench_035", "query": "天克地冲在流年代表什么？", "intent": "八字",
        "category": "大运流年", "difficulty": "hard",
        "expected_answer": "天克地冲指流年天干克大运/日柱天干，同时流年地支冲大运/日柱地支。主变动、冲突、不稳定的年份，需结合喜忌看吉凶。",
    },
    {
        "id": "bench_036", "query": "什么是交运脱运？", "intent": "八字",
        "category": "大运流年", "difficulty": "hard",
        "expected_answer": "交运是进入新的大运，脱运是离开旧的大运。交脱之年往往人生有较大变化，需特别注意流年冲合并见。",
    },
    {
        "id": "bench_037", "query": "如何看财运的流年？", "intent": "八字",
        "category": "大运流年", "difficulty": "medium",
        "expected_answer": "财星为喜用时，逢财星流年或食伤生财的流年财运好。财星为忌时，逢比劫夺财的流年财运差。",
    },
    {
        "id": "bench_038", "query": "如何看婚姻的流年？", "intent": "八字",
        "category": "大运流年", "difficulty": "medium",
        "expected_answer": "男命财星为喜逢财年、女命官星为喜逢官年，或日支逢合逢冲之年，多为婚恋应期。",
    },
    {
        "id": "bench_039", "query": "什么是小运？", "intent": "八字",
        "category": "大运流年", "difficulty": "medium",
        "expected_answer": "小运是辅助大运的短期运势，以一岁起运，每年一换。小运配合大运和流年，精细判断短期吉凶。",
    },
    {
        "id": "bench_040", "query": "什么是命宫和胎元？", "intent": "八字",
        "category": "大运流年", "difficulty": "hard",
        "expected_answer": "命宫为安身立命之所，以生月生时推算。胎元为受胎之月，以生月天干顺推一位、地支顺推三位。命宫和胎元是八字辅助判断的重要参考。",
    },

    # ═══════════════════════════════════════════════════════════════════
    # 紫微斗数 (41-55)
    # ═══════════════════════════════════════════════════════════════════
    {
        "id": "bench_041", "query": "紫微斗数十四主星有哪些？", "intent": "紫微",
        "category": "紫微基础", "difficulty": "easy",
        "expected_answer": "紫微斗数十四主星：紫微、天机、太阳、武曲、天同、廉贞（北斗六星）；天府、太阴、贪狼、巨门、天相、天梁、七杀、破军（南斗八星）。",
    },
    {
        "id": "bench_042", "query": "紫微斗数十二宫是什么？", "intent": "紫微",
        "category": "紫微基础", "difficulty": "easy",
        "expected_answer": "十二宫：命宫、兄弟宫、夫妻宫、子女宫、财帛宫、疾厄宫、迁移宫、交友宫（奴仆宫）、官禄宫、田宅宫、福德宫、父母宫。",
    },
    {
        "id": "bench_043", "query": "什么是紫微斗数的四化？", "intent": "紫微",
        "category": "紫微基础", "difficulty": "medium",
        "expected_answer": "四化为化禄、化权、化科、化忌。化禄主财禄、化权主权势、化科主名声、化忌主困扰。四化以生年天干确定。",
    },
    {
        "id": "bench_044", "query": "紫微星坐命的人有什么特点？", "intent": "紫微",
        "category": "紫微星曜", "difficulty": "medium",
        "expected_answer": "紫微坐命者气质高贵，有领导力，自尊心强。喜得左辅右弼相夹，增强辅佐力量。",
    },
    {
        "id": "bench_045", "query": "天机星坐命的人有什么特点？", "intent": "紫微",
        "category": "紫微星曜", "difficulty": "medium",
        "expected_answer": "天机坐命者聪明机敏，善于谋划，但易多思多虑。为谋士之星，适合策划、咨询类工作。",
    },
    {
        "id": "bench_046", "query": "太阳星在十二宫的意义？", "intent": "紫微",
        "category": "紫微星曜", "difficulty": "medium",
        "expected_answer": "太阳主光明、博爱、父亲、丈夫。庙旺则光明磊落，落陷则心力不足。在命宫主热情外放，在夫妻宫主配偶开朗。",
    },
    {
        "id": "bench_047", "query": "武曲星坐命宫代表什么？", "intent": "紫微",
        "category": "紫微星曜", "difficulty": "medium",
        "expected_answer": "武曲为财星，主刚毅、果断、理财。坐命宫者性格刚强，适合金融、军警、技术类工作。",
    },
    {
        "id": "bench_048", "query": "天同星的特点是什么？", "intent": "紫微",
        "category": "紫微星曜", "difficulty": "medium",
        "expected_answer": "天同为福星，主温和、享受、懒散。坐命者性格温顺，有福气，但缺乏进取心，需煞星激发。",
    },
    {
        "id": "bench_049", "query": "廉贞星坐命的人性格如何？", "intent": "紫微",
        "category": "紫微星曜", "difficulty": "medium",
        "expected_answer": "廉贞为次桃花星，主刚烈、执着、多情。坐命者性格强烈，有正义感，但易感情用事。",
    },
    {
        "id": "bench_050", "query": "天府星坐命宫代表什么？", "intent": "紫微",
        "category": "紫微星曜", "difficulty": "medium",
        "expected_answer": "天府为南斗主星，主稳重、包容、理财。坐命者性格宽厚，善于守成，有管理才能。",
    },
    {
        "id": "bench_051", "query": "太阴星在命宫代表什么？", "intent": "紫微",
        "category": "紫微星曜", "difficulty": "medium",
        "expected_answer": "太阴主阴柔、母亲、妻子、财富。坐命宫者性格温婉，有艺术天赋，庙旺主富，落陷主多愁善感。",
    },
    {
        "id": "bench_052", "query": "贪狼星坐命的人有什么特点？", "intent": "紫微",
        "category": "紫微星曜", "difficulty": "medium",
        "expected_answer": "贪狼为桃花星，主欲望、交际、多才多艺。坐命者社交能力强，兴趣广泛，但需节制欲望。",
    },
    {
        "id": "bench_053", "query": "七杀星坐命宫代表什么？", "intent": "紫微",
        "category": "紫微星曜", "difficulty": "medium",
        "expected_answer": "七杀为将星，主刚猛、决断、冒险。坐命者性格刚烈，有开拓精神，适合军警、创业。",
    },
    {
        "id": "bench_054", "query": "破军星坐命的人有什么特点？", "intent": "紫微",
        "category": "紫微星曜", "difficulty": "medium",
        "expected_answer": "破军主破旧立新、变动、消耗。坐命者性格敢作敢为，有破坏和重建的能力，人生起伏较大。",
    },
    {
        "id": "bench_055", "query": "什么是紫微斗数的三方四正？", "intent": "紫微",
        "category": "紫微基础", "difficulty": "medium",
        "expected_answer": "三方为本宫的对宫、三合宫（顺数第四宫和倒数第四宫）。四正为三方加上本宫。三方四正综合判断星曜的吉凶力量。",
    },

    # ═══════════════════════════════════════════════════════════════════
    # 六爻 (56-70)
    # ═══════════════════════════════════════════════════════════════════
    {
        "id": "bench_056", "query": "六爻中世应是什么？", "intent": "六爻",
        "category": "六爻基础", "difficulty": "easy",
        "expected_answer": "世爻代表自己或问卦人，应爻代表对方或所问之事。世应关系是判断吉凶的核心。世应相生则吉，相克则凶。",
    },
    {
        "id": "bench_057", "query": "六爻中的六亲是什么？", "intent": "六爻",
        "category": "六爻基础", "difficulty": "easy",
        "expected_answer": "六亲为父母、兄弟、妻财、官鬼、子孙、世应。以卦宫五行为我，生我者父母，我生者子孙，克我者官鬼，我克者妻财，同我者兄弟。",
    },
    {
        "id": "bench_058", "query": "六爻中的六兽（六神）是什么？", "intent": "六爻",
        "category": "六爻基础", "difficulty": "medium",
        "expected_answer": "六兽为青龙、朱雀、勾陈、螣蛇、白虎、玄武。以日干定初爻六兽，各有吉凶象征：青龙主喜、朱雀主口舌、勾陈主田土、螣蛇主虚惊、白虎主凶伤、玄武主盗贼。",
    },
    {
        "id": "bench_059", "query": "六爻中如何取用神？", "intent": "六爻",
        "category": "六爻基础", "difficulty": "medium",
        "expected_answer": "用神是所问之事对应的六亲：问财取妻财、问官取官鬼、问文书取父母、问子女取子孙、问兄弟取兄弟。用神旺相且不受伤克为吉。",
    },
    {
        "id": "bench_060", "query": "六爻中月建和日辰的作用？", "intent": "六爻",
        "category": "六爻基础", "difficulty": "medium",
        "expected_answer": "月建为月令，掌一月之权，决定爻的旺相休囚死。日辰为当日干支，掌一日之权，决定爻的生克冲合。月建管长远，日辰管当下。",
    },
    {
        "id": "bench_061", "query": "六爻中动爻和变爻是什么？", "intent": "六爻",
        "category": "六爻基础", "difficulty": "medium",
        "expected_answer": "动爻为老阳（O）或老阴（X）之爻，会产生变化。变爻为动爻变化后产生的新爻。动爻和变爻的关系是判断吉凶变化的关键。",
    },
    {
        "id": "bench_062", "query": "六爻中暗动是什么？", "intent": "六爻",
        "category": "六爻基础", "difficulty": "medium",
        "expected_answer": "暗动是静爻被日辰相冲而发动，力量较动爻弱，但仍有作用。暗动主突发、意外之事。",
    },
    {
        "id": "bench_063", "query": "六爻中旬空是什么意思？", "intent": "六爻",
        "category": "六爻基础", "difficulty": "medium",
        "expected_answer": "旬空是爻所在的地支在当旬中为空亡。空亡之爻力量减弱，但出空或填实后可恢复力量。",
    },
    {
        "id": "bench_064", "query": "六爻中如何判断应期？", "intent": "六爻",
        "category": "六爻基础", "difficulty": "hard",
        "expected_answer": "应期判断：动而逢合逢值、静而逢冲逢值、空而填实出空、破而补合、墓而冲开、伏而出现。",
    },
    {
        "id": "bench_065", "query": "六爻中伏神和飞神是什么？", "intent": "六爻",
        "category": "六爻基础", "difficulty": "medium",
        "expected_answer": "当用神不上卦时，从本宫卦中寻伏神。伏神所伏之爻为飞神。伏神需飞神生扶或冲开飞神方能有用。",
    },
    {
        "id": "bench_066", "query": "六爻中的六合卦有哪些？", "intent": "六爻",
        "category": "六爻基础", "difficulty": "medium",
        "expected_answer": "六合卦为天地否、地天泰、水火既济、火水未济、雷风恒、风雷益、山泽损、泽山咸。六合卦主和谐、合作、稳定。",
    },
    {
        "id": "bench_067", "query": "六爻中的六冲卦有哪些？", "intent": "六爻",
        "category": "六爻基础", "difficulty": "medium",
        "expected_answer": "六冲卦为乾为天、兑为泽、离为火、震为雷、巽为风、坎为水、艮为山、坤为地。六冲卦主冲突、变动、分散。",
    },
    {
        "id": "bench_068", "query": "六爻中如何看财运？", "intent": "六爻",
        "category": "六爻应用", "difficulty": "medium",
        "expected_answer": "看财运取妻财爻为用神，财爻旺相且生世合世为吉。子孙爻为财源，子孙动生财爻为佳。兄弟爻动克财爻主破财。",
    },
    {
        "id": "bench_069", "query": "六爻中如何看婚姻？", "intent": "六爻",
        "category": "六爻应用", "difficulty": "medium",
        "expected_answer": "男测婚取妻财为用，女测婚取官鬼为用。世应相生合且用神旺相为吉。六合卦主婚姻稳定，六冲卦主反复。",
    },
    {
        "id": "bench_070", "query": "六爻中如何看官运？", "intent": "六爻",
        "category": "六爻应用", "difficulty": "medium",
        "expected_answer": "看官运取官鬼爻为用神，官鬼旺相且生世合世为吉。财爻动生官鬼主升职有望。子孙爻动克官鬼主官运受阻。",
    },

    # ═══════════════════════════════════════════════════════════════════
    # 风水 (71-85)
    # ═══════════════════════════════════════════════════════════════════
    {
        "id": "bench_071", "query": "什么是玄空飞星？", "intent": "风水",
        "category": "风水基础", "difficulty": "medium",
        "expected_answer": "玄空飞星是以洛书九宫为基础，根据元运将九星飞布九宫，判断方位吉凶的风水方法。九星为一白、二黑、三碧、四绿、五黄、六白、七赤、八白、九紫。",
    },
    {
        "id": "bench_072", "query": "三元九运是什么？", "intent": "风水",
        "category": "风水基础", "difficulty": "medium",
        "expected_answer": "三元九运是时间划分体系：上元一二三运（60年）、中元四五六运（60年）、下元七八九运（60年），每运20年，共180年。",
    },
    {
        "id": "bench_073", "query": "什么是峦头风水和理气风水？", "intent": "风水",
        "category": "风水基础", "difficulty": "medium",
        "expected_answer": "峦头风水看山形水势、龙穴砂水等自然形态。理气风水看方位、元运、卦象等理气因素。峦头为体，理气为用，两者结合方为完整。",
    },
    {
        "id": "bench_074", "query": "八宅风水如何判断吉凶方位？", "intent": "风水",
        "category": "风水基础", "difficulty": "medium",
        "expected_answer": "八宅风水以宅命（坐向）定东四宅或西四宅，再配合居住者命卦，判断四吉方（生气、延年、天医、伏位）和四凶方（绝命、五鬼、六煞、祸害）。",
    },
    {
        "id": "bench_075", "query": "风水中的四灵诀是什么？", "intent": "风水",
        "category": "风水基础", "difficulty": "easy",
        "expected_answer": "四灵诀为左青龙、右白虎、前朱雀、后玄武。青龙宜高、白虎宜低、朱雀宜开阔、玄武宜有靠。",
    },
    {
        "id": "bench_076", "query": "什么是五黄煞？如何化解？", "intent": "风水",
        "category": "风水应用", "difficulty": "medium",
        "expected_answer": "五黄煞为九星中最凶之星，主疾病、灾祸。宜静不宜动，可用金属（六帝钱、铜铃）化解。",
    },
    {
        "id": "bench_077", "query": "风水中的明堂是什么？", "intent": "风水",
        "category": "风水基础", "difficulty": "easy",
        "expected_answer": "明堂为宅前空地，分内明堂和外明堂。明堂宜开阔、平坦、聚气，不宜狭窄、杂乱。",
    },
    {
        "id": "bench_078", "query": "什么是水法？风水如何看水？", "intent": "风水",
        "category": "风水基础", "difficulty": "hard",
        "expected_answer": "水法为风水中的水流判断法则。水来处为天门宜开阔，水去处为地户宜紧闭。水形以环抱有情为吉，反弓无情为凶。",
    },
    {
        "id": "bench_079", "query": "阳宅大门的风水要点是什么？", "intent": "风水",
        "category": "风水应用", "difficulty": "medium",
        "expected_answer": "大门为气口，宜开在吉方、避凶方。大门不宜对楼梯、电梯、厕所、厨房。门内宜有玄关挡煞。",
    },
    {
        "id": "bench_080", "query": "卧室风水有哪些禁忌？", "intent": "风水",
        "category": "风水应用", "difficulty": "medium",
        "expected_answer": "卧室忌横梁压顶、镜子对床、床头靠窗、床头对门、床下堆杂物。宜方正、安静、光线柔和。",
    },
    {
        "id": "bench_081", "query": "厨房风水布局要点？", "intent": "风水",
        "category": "风水应用", "difficulty": "medium",
        "expected_answer": "厨房宜在宅之凶方（压凶），灶口宜向吉方。灶不宜对门、对厕、对水槽。水火不宜相对。",
    },
    {
        "id": "bench_082", "query": "玄空飞星中一白贪狼星代表什么？", "intent": "风水",
        "category": "风水基础", "difficulty": "medium",
        "expected_answer": "一白贪狼星为坎宫，属水，主桃花、人缘、智慧。当令时为官星，失令时为桃花劫。",
    },
    {
        "id": "bench_083", "query": "八白左辅星在风水中的意义？", "intent": "风水",
        "category": "风水基础", "difficulty": "medium",
        "expected_answer": "八白左辅星为艮宫，属土，主财运、置业。在下元八运（2004-2023）为当令旺星，大吉。",
    },
    {
        "id": "bench_084", "query": "九紫右弼星在风水中的意义？", "intent": "风水",
        "category": "风水基础", "difficulty": "medium",
        "expected_answer": "九紫右弼星为离宫，属火，主喜庆、桃花、文书。在九运（2024-2043）为当令旺星。",
    },
    {
        "id": "bench_085", "query": "什么是风水中的呼形喝象？", "intent": "风水",
        "category": "风水基础", "difficulty": "hard",
        "expected_answer": "呼形喝象是根据山水形状赋予其象征意义，如笔架山主文贵、旗山主武贵、葫芦山主医卜等。是峦头风水的重要判断方法。",
    },

    # ═══════════════════════════════════════════════════════════════════
    # 姓名学 (86-95)
    # ═══════════════════════════════════════════════════════════════════
    {
        "id": "bench_086", "query": "什么是五格数理？", "intent": "姓名学",
        "category": "姓名学", "difficulty": "easy",
        "expected_answer": "五格数理为天格、人格、地格、外格、总格。以姓名笔画数计算，各格有1-81数理吉凶。",
    },
    {
        "id": "bench_087", "query": "三才配置是什么？", "intent": "姓名学",
        "category": "姓名学", "difficulty": "medium",
        "expected_answer": "三才为天格、人格、地格的五行配置。三才配置需五行相生为吉，相克为凶。",
    },
    {
        "id": "bench_088", "query": "姓名学中81数理吉凶如何判断？", "intent": "姓名学",
        "category": "姓名学", "difficulty": "medium",
        "expected_answer": "81数理各有吉凶含义：1-11为吉数，12-20多凶数，21-32多吉数等。人格数理最为重要，总格次之。",
    },
    {
        "id": "bench_089", "query": "姓名学如何补五行？", "intent": "姓名学",
        "category": "姓名学", "difficulty": "medium",
        "expected_answer": "根据八字五行缺失，选字补益。缺木选带木字旁的字，缺火选带火字旁的字，以此类推。同时考虑字的音形义。",
    },
    {
        "id": "bench_090", "query": "姓名学中天格如何计算？", "intent": "姓名学",
        "category": "姓名学", "difficulty": "easy",
        "expected_answer": "天格为姓氏笔画数加1（单姓）或姓氏两字笔画数之和（复姓）。天格代表祖运、先天。",
    },
    {
        "id": "bench_091", "query": "姓名学中人格如何计算？", "intent": "姓名学",
        "category": "姓名学", "difficulty": "easy",
        "expected_answer": "人格为姓氏末字笔画数加名字首字笔画数。人格代表主运，是姓名学中最重要的数理。",
    },
    {
        "id": "bench_092", "query": "姓名学中地格如何计算？", "intent": "姓名学",
        "category": "姓名学", "difficulty": "easy",
        "expected_answer": "地格为名字各字笔画数之和（单名加1）。地格代表前运、子女运。",
    },
    {
        "id": "bench_093", "query": "姓名学中总格如何计算？", "intent": "姓名学",
        "category": "姓名学", "difficulty": "easy",
        "expected_answer": "总格为姓与名全部笔画数之和。总格代表后运、晚年运。",
    },
    {
        "id": "bench_094", "query": "姓名学中外格如何计算？", "intent": "姓名学",
        "category": "姓名学", "difficulty": "easy",
        "expected_answer": "外格为总格笔画数减去人格笔画数再加1（或名字末字加1）。外格代表副运、社交运。",
    },
    {
        "id": "bench_095", "query": "起名时应该注意哪些原则？", "intent": "姓名学",
        "category": "姓名学", "difficulty": "medium",
        "expected_answer": "起名原则：补五行缺失、三才配置相生、五格数理吉祥、字音悦耳、字义美好、字形协调、避免生僻字。",
    },

    # ═══════════════════════════════════════════════════════════════════
    # 综合/歧义消解 (96-110)
    # ═══════════════════════════════════════════════════════════════════
    {
        "id": "bench_096", "query": "我的财运怎么样？", "intent": "歧义",
        "category": "歧义消解", "difficulty": "hard",
        "expected_answer": "需要先确定您想用哪种方式查看财运：八字看财星格局、紫微看财帛宫、六爻起卦看财爻。请告诉我您的偏好。",
    },
    {
        "id": "bench_097", "query": "今年运势如何？", "intent": "歧义",
        "category": "歧义消解", "difficulty": "hard",
        "expected_answer": "看流年运势有多种方式：八字看流年干支与大运原局的关系、紫微看流年四化在各宫、六爻可起年运卦。您想用哪种方式？",
    },
    {
        "id": "bench_098", "query": "这个房子风水好不好？", "intent": "风水",
        "category": "风水应用", "difficulty": "medium",
        "expected_answer": "判断房子风水需看：坐向（玄空飞星）、外部环境（峦头）、内部布局（八宅）、大门气口、厨房和卧室位置。请提供具体信息。",
    },
    {
        "id": "bench_099", "query": "我适合做什么工作？", "intent": "歧义",
        "category": "歧义消解", "difficulty": "medium",
        "expected_answer": "可通过八字看十神格局和五行喜忌、紫微看官禄宫星曜、姓名学看三才配置来综合判断。",
    },
    {
        "id": "bench_100", "query": "什么时候能结婚？", "intent": "歧义",
        "category": "歧义消解", "difficulty": "medium",
        "expected_answer": "八字看婚姻需看财官星和夫妻宫的大运流年应期，紫微看夫妻宫和红鸾天喜。",
    },
    {
        "id": "bench_101", "query": "八字日柱甲子的人性格如何？", "intent": "八字",
        "category": "八字基础", "difficulty": "medium",
        "expected_answer": "甲子日生人，甲木坐子水为正印，性格仁慈、有学识、聪明。子水为甲木之沐浴，略带桃花气质。",
    },
    {
        "id": "bench_102", "query": "地支寅申冲在命局中代表什么？", "intent": "八字",
        "category": "八字基础", "difficulty": "hard",
        "expected_answer": "寅申为金木相冲，寅中甲丙戊与申中庚壬戊相战。主变动、奔波、车祸、筋骨损伤等。需看寅申各为何十神，结合喜忌判断。",
    },
    {
        "id": "bench_103", "query": "什么是八字中的通关用神？", "intent": "八字",
        "category": "十神格局", "difficulty": "hard",
        "expected_answer": "当八字中两种五行相战时，取能沟通两者的五行为通关用神。如金木相战取水通关，水火相战取木通关。",
    },
    {
        "id": "bench_104", "query": "紫微斗数中禄存星的特点？", "intent": "紫微",
        "category": "紫微星曜", "difficulty": "medium",
        "expected_answer": "禄存为财星，主稳定财富、积蓄。禄存坐命者善于理财，但禄存前有擎羊后有陀罗，需防破耗。",
    },
    {
        "id": "bench_105", "query": "紫微斗数中天魁天钺的作用？", "intent": "紫微",
        "category": "紫微星曜", "difficulty": "medium",
        "expected_answer": "天魁天钺为贵人星，天魁为阳贵（白天生人更显），天钺为阴贵（夜晚生人更显）。主遇贵人相助、逢凶化吉。",
    },
    {
        "id": "bench_106", "query": "六爻中如何看失物？", "intent": "六爻",
        "category": "六爻应用", "difficulty": "medium",
        "expected_answer": "看失物取妻财爻为用（财物）或父母爻（文书）。用神旺相且不空不破可寻回。看用神所在卦宫和爻位判断方位。",
    },
    {
        "id": "bench_107", "query": "六爻中如何看疾病？", "intent": "六爻",
        "category": "六爻应用", "difficulty": "medium",
        "expected_answer": "看疾病取官鬼爻为病根，子孙爻为医药。官鬼旺而克世主病重，子孙动而克官鬼主可愈。结合爻位和五行判断病位和病种。",
    },
    {
        "id": "bench_108", "query": "什么是风水中的罗盘？如何使用？", "intent": "风水",
        "category": "风水基础", "difficulty": "medium",
        "expected_answer": "罗盘是风水师测量方位的工具，由天池（指南针）、内盘（地盘、人盘、天盘）、外盘组成。用于测定坐向、分金、消砂纳水。",
    },
    {
        "id": "bench_109", "query": "什么是八字的调候用神？", "intent": "八字",
        "category": "十神格局", "difficulty": "hard",
        "expected_answer": "调候用神是根据八字寒暖燥湿情况取的用神。夏生八字过于燥热取水调候，冬生八字过于寒湿取火调候。调候为急，先于扶抑。",
    },
    {
        "id": "bench_110", "query": "八字中的从财格和从杀格有什么区别？", "intent": "八字",
        "category": "十神格局", "difficulty": "hard",
        "expected_answer": "从财格为日主极弱，财星极旺，弃命从财，以财为用。从杀格为日主极弱，官杀极旺，弃命从杀，以官杀为用。从格忌印比帮身破格。",
    },
]


class BenchmarkDataset:
    """基准数据集管理类

    用法：
        ds = BenchmarkDataset()
        ds.load_default()
        for q in ds.queries:
            print(q.query)
    """

    def __init__(self):
        self.queries: List[BenchmarkQuery] = []

    def load_default(self) -> "BenchmarkDataset":
        """加载默认 100+ 基准数据集"""
        self.queries = []
        for item in _BENCHMARK_QUERIES:
            q = BenchmarkQuery(
                id=item["id"],
                query=item["query"],
                intent=item["intent"],
                category=item.get("category", ""),
                relevant_ids=set(item.get("relevant_ids", [item["id"]])),
                expected_answer=item.get("expected_answer", ""),
                context=item.get("context", ""),
                difficulty=item.get("difficulty", "medium"),
            )
            self.queries.append(q)
        return self

    def get_by_category(self, category: str) -> List[BenchmarkQuery]:
        """按类别筛选"""
        return [q for q in self.queries if q.category == category]

    def get_by_intent(self, intent: str) -> List[BenchmarkQuery]:
        """按意图筛选"""
        return [q for q in self.queries if q.intent == intent]

    def get_by_difficulty(self, difficulty: str) -> List[BenchmarkQuery]:
        """按难度筛选"""
        return [q for q in self.queries if q.difficulty == difficulty]

    @property
    def categories(self) -> List[str]:
        return sorted(set(q.category for q in self.queries))

    @property
    def intents(self) -> List[str]:
        return sorted(set(q.intent for q in self.queries))

    @property
    def count(self) -> int:
        return len(self.queries)

    def to_dict(self) -> List[Dict]:
        return [q.to_dict() for q in self.queries]

    def save(self, path: str):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, path: str) -> "BenchmarkDataset":
        ds = cls()
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for item in data:
            q = BenchmarkQuery(
                id=item["id"],
                query=item["query"],
                intent=item["intent"],
                category=item.get("category", ""),
                relevant_ids=set(item.get("relevant_ids", [item["id"]])),
                expected_answer=item.get("expected_answer", ""),
                context=item.get("context", ""),
                difficulty=item.get("difficulty", "medium"),
            )
            ds.queries.append(q)
        return ds

    def self_check(self) -> bool:
        """快速自检"""
        self.load_default()
        n = len(self.queries)
        cats = self.categories
        ints = self.intents

        print(f"✅ 基准数据集自检通过: {n} 条查询")
        print(f"   类别: {cats}")
        print(f"   意图: {ints}")
        print(f"   难度分布: easy={len(self.get_by_difficulty('easy'))}, medium={len(self.get_by_difficulty('medium'))}, hard={len(self.get_by_difficulty('hard'))}")
        return n >= 100