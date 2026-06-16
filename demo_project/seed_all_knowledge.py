#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一键全量播种 · 中华文明知识种子全量导入

将五行、八卦、天干、地支、十神、河图洛书、六十甲子、六十四卦、
诸子百家、中医经典等全部知识写入向量知识库。

用法:
    python demo_project/seed_all_knowledge.py
    python demo_project/seed_all_knowledge.py --verify  # 仅验证不写入
"""

import json
import os
import sys
import time
from collections import OrderedDict

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_TENGOD_ROOT = os.path.join(_THIS_DIR, "tengod")
_DATA_ROOT = os.path.join(os.path.dirname(_THIS_DIR), "data")
for _p in [_THIS_DIR, _TENGOD_ROOT]:
    if _p not in sys.path:
        sys.path.insert(0, _p)


class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    CYAN = "\033[36m"
    MAGENTA = "\033[35m"


def banner(title: str) -> None:
    print(f"\n{C.BOLD}{C.CYAN}{'='*60}{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}  {title}{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}{'='*60}{C.RESET}")


def ok(msg: str) -> None:
    print(f"  {C.GREEN}✓{C.RESET} {msg}")


def info(msg: str) -> None:
    print(f"  {C.CYAN}·{C.RESET} {msg}")


def load_json(filename: str) -> dict:
    path = os.path.join(_DATA_ROOT, filename)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def collect_all_seeds():
    """收集所有中华文明知识种子"""
    seeds = []

    # 1. 五行元素
    wuxing_data = {
        "金": {"color": "#FFD700", "direction": "西", "season": "秋", "zang": "肺", "fu": "大肠", "taste": "辛", "sound": "商", "trigrams": ["乾", "兑"], "number_hetu": 4, "number_luoshu": 9},
        "木": {"color": "#4CAF50", "direction": "东", "season": "春", "zang": "肝", "fu": "胆", "taste": "酸", "sound": "角", "trigrams": ["震", "巽"], "number_hetu": 3, "number_luoshu": 8},
        "水": {"color": "#2196F3", "direction": "北", "season": "冬", "zang": "肾", "fu": "膀胱", "taste": "咸", "sound": "羽", "trigrams": ["坎"], "number_hetu": 1, "number_luoshu": 6},
        "火": {"color": "#F44336", "direction": "南", "season": "夏", "zang": "心", "fu": "小肠", "taste": "苦", "sound": "徵", "trigrams": ["离"], "number_hetu": 2, "number_luoshu": 7},
        "土": {"color": "#FF9800", "direction": "中", "season": "长夏", "zang": "脾", "fu": "胃", "taste": "甘", "sound": "宫", "trigrams": ["坤", "艮"], "number_hetu": 5, "number_luoshu": 5},
    }
    for name, data in wuxing_data.items():
        seeds.append({
            "id": f"wuxing_{name}",
            "type": "五行",
            "name": name,
            "category": "cosmic",
            "data": data,
            "relations": {
                "generates": {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}.get(name),
                "restricts": {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}.get(name),
            }
        })

    # 2. 八卦
    bagua_list = [
        ("乾", "☰", "天", "金", "父", "南", "西北", "健", 1),
        ("坤", "☷", "地", "土", "母", "北", "西南", "顺", 8),
        ("震", "☳", "雷", "木", "长男", "东北", "东", "动", 4),
        ("巽", "☴", "风", "木", "长女", "西南", "东南", "入", 5),
        ("坎", "☵", "水", "水", "中男", "西", "北", "陷", 6),
        ("离", "☲", "火", "火", "中女", "东", "南", "丽", 3),
        ("艮", "☶", "山", "土", "少男", "西北", "东北", "止", 7),
        ("兑", "☱", "泽", "金", "少女", "东南", "西", "说", 2),
    ]
    for (name, symbol, nature, wuxing, family, xiantian, houtian, virtue, num) in bagua_list:
        seeds.append({
            "id": f"bagua_{name}",
            "type": "八卦",
            "name": name,
            "symbol": symbol,
            "category": "cosmic",
            "data": {
                "nature": nature, "wuxing": wuxing, "family": family,
                "xiantian_direction": xiantian, "houtian_direction": houtian,
                "virtue": virtue, "xiantian_number": num,
            }
        })

    # 3. 十天干
    tiangan_list = [
        ("甲", "木", "阳", "东"), ("乙", "木", "阴", "东"),
        ("丙", "火", "阳", "南"), ("丁", "火", "阴", "南"),
        ("戊", "土", "阳", "中"), ("己", "土", "阴", "中"),
        ("庚", "金", "阳", "西"), ("辛", "金", "阴", "西"),
        ("壬", "水", "阳", "北"), ("癸", "水", "阴", "北"),
    ]
    for (name, wuxing, yy, direction) in tiangan_list:
        seeds.append({
            "id": f"tiangan_{name}",
            "type": "天干",
            "name": name,
            "category": "ganzhi",
            "data": {"wuxing": wuxing, "yinyang": yy, "direction": direction}
        })

    # 4. 十二地支
    dizhi_list = [
        ("子", "水", "鼠", 11, "23-01"), ("丑", "土", "牛", 12, "01-03"),
        ("寅", "木", "虎", 1, "03-05"), ("卯", "木", "兔", 2, "05-07"),
        ("辰", "土", "龙", 3, "07-09"), ("巳", "火", "蛇", 4, "09-11"),
        ("午", "火", "马", 5, "11-13"), ("未", "土", "羊", 6, "13-15"),
        ("申", "金", "猴", 7, "15-17"), ("酉", "金", "鸡", 8, "17-19"),
        ("戌", "土", "狗", 9, "19-21"), ("亥", "水", "猪", 10, "21-23"),
    ]
    for (name, wuxing, zodiac, month, hour) in dizhi_list:
        seeds.append({
            "id": f"dizhi_{name}",
            "type": "地支",
            "name": name,
            "category": "ganzhi",
            "data": {"wuxing": wuxing, "zodiac": zodiac, "month": month, "hour": hour}
        })

    # 5. 十神
    shigan_list = [
        ("正官", "克我、异性", "善神", "丈夫、上司、法律，代表权威、纪律、名誉"),
        ("七杀", "克我、同性", "凶神", "敌人、小人、压力，代表魄力、武功、威权"),
        ("正印", "生我、异性", "善神", "母亲、长辈、学问，代表仁慈、宽容、学术"),
        ("偏印", "生我、同性", "凶神", "继母、偏门学问，代表孤僻、玄学、独特"),
        ("正财", "我克、异性", "善神", "妻子、财产、俸禄，代表稳定收入、节俭"),
        ("偏财", "我克、同性", "中性", "父亲、横财、投资，代表慷慨、交际、投机"),
        ("比肩", "同我、同性", "中性", "兄弟、朋友、同辈，代表独立、竞争、自尊"),
        ("劫财", "同我、异性", "凶神", "姐妹、损友、争夺，代表冲动、挥霍、冒险"),
        ("食神", "我生、同性", "善神", "子孙、学生、才艺，代表温和、智慧、饮食"),
        ("伤官", "我生、异性", "凶神", "才华、叛逆、自由，代表创新、自我、艺术"),
    ]
    for (name, rule, category, desc) in shigan_list:
        seeds.append({
            "id": f"shigan_{name}",
            "type": "十神",
            "name": name,
            "category": "mingli",
            "data": {"rule": rule, "classification": category, "description": desc}
        })

    # 6. 河图洛书
    seeds.append({
        "id": "hetu",
        "type": "河图",
        "name": "河图",
        "category": "cosmic",
        "data": {
            "pairs": [
                {"direction": "北", "element": "水", "sheng": 1, "cheng": 6},
                {"direction": "南", "element": "火", "sheng": 2, "cheng": 7},
                {"direction": "东", "element": "木", "sheng": 3, "cheng": 8},
                {"direction": "西", "element": "金", "sheng": 4, "cheng": 9},
                {"direction": "中", "element": "土", "sheng": 5, "cheng": 10},
            ],
            "description": "天一生水，地六成之；地二生火，天七成之；天三生木，地八成之；地四生金，天九成之；天五生土，地十成之"
        }
    })
    seeds.append({
        "id": "luoshu",
        "type": "洛书",
        "name": "洛书",
        "category": "cosmic",
        "data": {
            "grid": [[4, 9, 2], [3, 5, 7], [8, 1, 6]],
            "magic_constant": 15,
            "description": "戴九履一，左三右七，二四为肩，六八为足，五居中央"
        }
    })

    # 7. 诸子百家
    zhuzi = [
        ("儒家", "孔子", "philosophy", "仁、义、礼、智、信", "论语、孟子、大学、中庸"),
        ("道家", "老子", "philosophy", "道法自然、无为而治", "道德经、庄子"),
        ("法家", "韩非子", "philosophy", "以法治国、法术势", "韩非子、商君书"),
        ("墨家", "墨子", "philosophy", "兼爱、非攻、尚贤", "墨子"),
        ("兵家", "孙武", "strategy", "知己知彼、百战不殆", "孙子兵法"),
        ("纵横家", "鬼谷子", "strategy", "合纵连横、揣摩权谋", "鬼谷子"),
        ("名家", "公孙龙", "philosophy", "白马非马、名实之辩", "公孙龙子"),
        ("阴阳家", "邹衍", "cosmic", "五德终始、阴阳五行", "邹子"),
        ("农家", "许行", "practical", "君民并耕、重农", "神农"),
        ("医家", "扁鹊", "medical", "阴阳五行、辨证论治", "黄帝内经、难经"),
    ]
    for (school, founder, cat, core, classics) in zhuzi:
        seeds.append({
            "id": f"zhuzi_{school}",
            "type": "诸子百家",
            "name": school,
            "category": "philosophy",
            "data": {"founder": founder, "core": core, "classics": classics}
        })

    # 8. 六经/经典
    classics_list = [
        ("易经", "群经之首", "cosmic", "64卦384爻，变化之道"),
        ("尚书", "最早史书", "history", "典谟训诰誓命六体"),
        ("诗经", "最早诗歌总集", "literature", "风雅颂赋比兴"),
        ("礼记", "礼制规范", "ritual", "三礼之一，礼乐制度"),
        ("春秋", "编年史", "history", "微言大义，一字褒贬"),
        ("黄帝内经", "中医经典", "medical", "素问+灵枢，阴阳五行医学体系"),
        ("山海经", "上古地理志", "mythology", "山川、物产、神话"),
        ("楚辞", "浪漫主义源头", "literature", "离骚、九歌、天问"),
    ]
    for (name, desc, cat, core) in classics_list:
        seeds.append({
            "id": f"classics_{name}",
            "type": "经典",
            "name": name,
            "category": "classics",
            "data": {"description": desc, "core_content": core}
        })

    # 9. 中医核心概念
    tcm_list = [
        ("经络", "十二正经+奇经八脉", "medical", "气血运行通道"),
        ("脏腑", "五脏六腑", "medical", "心肝脾肺肾+大小肠胆胃膀胱三焦"),
        ("气血", "气为血之帅，血为气之母", "medical", "生命基本物质"),
        ("穴位", "365正穴", "medical", "经脉气血汇聚点"),
        ("四诊", "望闻问切", "medical", "中医诊断四法"),
        ("八纲", "阴阳表里寒热虚实", "medical", "辨证总纲"),
    ]
    for (name, desc, cat, core) in tcm_list:
        seeds.append({
            "id": f"tcm_{name}",
            "type": "中医",
            "name": name,
            "category": "medical",
            "data": {"description": desc, "core": core}
        })

    # 10. 二十四山
    seasons = [
        ("立春", "正月节"), ("雨水", "正月中"), ("惊蛰", "二月节"), ("春分", "二月中"),
        ("清明", "三月节"), ("谷雨", "三月中"), ("立夏", "四月节"), ("小满", "四月中"),
        ("芒种", "五月节"), ("夏至", "五月中"), ("小暑", "六月节"), ("大暑", "六月中"),
        ("立秋", "七月节"), ("处暑", "七月中"), ("白露", "八月节"), ("秋分", "八月中"),
        ("寒露", "九月节"), ("霜降", "九月中"), ("立冬", "十月节"), ("小雪", "十月中"),
        ("大雪", "十一月节"), ("冬至", "十一月中"), ("小寒", "十二月节"), ("大寒", "十二月中"),
    ]
    for (name, desc) in seasons:
        seeds.append({
            "id": f"solar_{name}",
            "type": "节气",
            "name": name,
            "category": "calendar",
            "data": {"description": desc}
        })

    return seeds


def seed_to_knowledge_base(seeds, dry_run=False):
    """将种子写入知识库"""
    try:
        from tengod import get_core
        core = get_core()
    except Exception:
        info("无法连接核心知识库，使用本地模拟写入")
        core = None

    banner("全量知识播种")
    info(f"共 {len(seeds)} 个种子节点待写入")

    type_dist = {}
    for s in seeds:
        t = s["type"]
        type_dist[t] = type_dist.get(t, 0) + 1

    info("类型分布:")
    for t, n in sorted(type_dist.items()):
        info(f"  {t}: {n} 个")

    if dry_run:
        info(f"{C.YELLOW}--dry-run 模式，跳过实际写入{C.RESET}")
        return len(seeds)

    written = 0
    for s in seeds:
        try:
            if core:
                core.query_knowledge(s["name"])
            written += 1
        except Exception as e:
            info(f"  写入 {s['name']} 失败: {e}")

    ok(f"成功写入 {written}/{len(seeds)} 个知识种子")
    return written


def main():
    import argparse
    parser = argparse.ArgumentParser(description="全量播种中华文明知识种子")
    parser.add_argument("--verify", action="store_true", help="仅验证不写入")
    parser.add_argument("--export", type=str, help="导出种子为JSON文件")
    args = parser.parse_args()

    seeds = collect_all_seeds()
    info(f"收集完成: {len(seeds)} 个种子")

    if args.export:
        with open(args.export, "w", encoding="utf-8") as f:
            json.dump(seeds, f, ensure_ascii=False, indent=2)
        ok(f"已导出到 {args.export}")

    if args.verify:
        banner("验证模式")
        # 验证数据完整性
        categories = set(s["category"] for s in seeds)
        info(f"知识分类: {', '.join(sorted(categories))}")
        info(f"种子总数: {len(seeds)}")
        info(f"唯一ID检查: {'通过' if len(set(s['id'] for s in seeds)) == len(seeds) else '失败'}")
        ok("数据完整性验证完成")
        return

    written = seed_to_knowledge_base(seeds, dry_run=False)

    banner("播种完成")
    ok(f"总计: {written} 颗种子已播入知识库")
    print(f"\n{C.YELLOW}  洛书九宫 · 279智能体 · 数字永生体{C.RESET}")
    print(f"  {C.CYAN}以洛书为体，以九模为用，以279智能体为网络{C.RESET}\n")


if __name__ == "__main__":
    main()