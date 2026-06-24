"""
shen_agents.py — 十神智能体 v2.13.0
=====================================
14 个十神智能体，各自专精一个分析维度，集成到 AgentOrchestrator 工具链。

每个智能体：
  - 接收八字数据 / 用户问题
  - 从各自维度输出分析结果
  - 可被编排器调度、组合使用

十神 → 职能映射：
  七杀 → 挑战与机遇分析
  伤官 → 创新与突破分析
  偏印 → 智慧与学习分析
  偏财 → 投资与投机分析
  元辰 → 本源与根基分析
  劫财 → 竞争与合作分析
  太极 → 平衡与调和分析
  正印 → 贵人与学业分析
  正官 → 事业与官运分析
  正财 → 稳定收入分析
  比肩 → 人际与协作分析
  食神 → 创意与享乐分析
  四柱 → 五行综合诊断
  流年 → 运势趋势预测
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
import json


# ============================================================================
# 智能体基类
# ============================================================================

@dataclass
class ShenAgent:
    """十神智能体基类"""
    name: str           # 十神名称，如 "七杀"
    title: str          # 职能标题，如 "品质裁决"
    description: str    # 分析描述
    category: str = "shen"  # 分类：shen/综合/预测

    def analyze(self, bazi_data: Dict[str, Any], question: str = "") -> Dict[str, Any]:
        """执行分析（子类可覆盖）"""
        return {
            "agent": self.name,
            "title": self.title,
            "analysis": self._default_analysis(bazi_data),
            "confidence": 0.75,
        }

    def _default_analysis(self, bazi_data: Dict[str, Any]) -> str:
        return f"【{self.name}·{self.title}】基于命盘数据，{self.description}"

    def to_tool_spec(self) -> Dict:
        """转换为 OpenAI function calling 格式"""
        return {
            "type": "function",
            "function": {
                "name": f"shen_{self.name}",
                "description": f"{self.title}：{self.description}",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "bazi_data": {"type": "object", "description": "八字命盘数据"},
                        "question": {"type": "string", "description": "用户具体问题"},
                    },
                    "required": ["bazi_data"],
                },
            },
        }


# ============================================================================
# 14 个十神智能体实现
# ============================================================================

# 天干十神断语映射
SHIGAN_ANALYSIS = {
    "正官": "正官代表事业、官运、纪律。正官旺者，行事规整，事业稳步上升，适合体制内发展。",
    "七杀": "七杀代表挑战、权威、魄力。七杀旺者，有开创精神，适合创业、军警、竞争性行业。",
    "正财": "正财代表稳定收入、工资、储蓄。正财旺者，财源稳定，理财能力强，适合稳健投资。",
    "偏财": "偏财代表意外之财、投机、流动性收入。偏财旺者，有投资眼光，但需防财来财去。",
    "正印": "正印代表学业、贵人、长辈缘。正印旺者，学习能力强，有长辈贵人扶持，适合文化教育行业。",
    "偏印": "偏印代表智慧、玄学、冷门技术。偏印旺者，思维独特，适合研究、技术、玄学领域。",
    "食神": "食神代表才华、创意、享乐。食神旺者，创造力强，社交丰富，适合艺术、设计、餐饮行业。",
    "伤官": "伤官代表创新、突破、个性。伤官旺者，有独特见解，但需防口舌是非，适合创意行业。",
    "比肩": "比肩代表朋友、同事、合作。比肩旺者，人缘好，适合团队合作，但需防分财。",
    "劫财": "劫财代表竞争、争夺、小人。劫财旺者，竞争意识强，但需防破财、防小人。",
}


class QishaAgent(ShenAgent):
    """七杀·品质裁决 — 挑战与机遇分析"""
    def __init__(self):
        super().__init__("七杀", "品质裁决", "分析命主面临的挑战、竞争压力与突破机遇，评估魄力与领导力")

    def analyze(self, bazi_data, question=""):
        pillars = bazi_data.get("pillars", {})
        day_master = bazi_data.get("day_master", "")
        day_pillar = pillars.get("day", "")
        shigan = bazi_data.get("shigan_map", {})

        # 查找七杀出现的柱位
        qisha_appearances = []
        for k, v in shigan.items():
            if "七杀" in str(v):
                qisha_appearances.append(k.replace("_gan", "柱"))

        result = {
            "agent": self.name,
            "title": self.title,
            "analysis": SHIGAN_ANALYSIS.get("七杀", ""),
            "qisha_locations": qisha_appearances,
            "verdict": "挑战型" if qisha_appearances else "稳健型",
            "suggestions": [
                "主动应对挑战，化压力为动力",
                "适合竞争性行业，勇于开拓",
                "注意劳逸结合，避免过度消耗",
            ],
            "confidence": 0.80,
        }
        return result


class ShangguanAgent(ShenAgent):
    """伤官·破界创新 — 创新与突破分析"""
    def __init__(self):
        super().__init__("伤官", "破界创新", "分析命主的创造力、独特见解与突破性思维")

    def analyze(self, bazi_data, question=""):
        result = {
            "agent": self.name,
            "title": self.title,
            "analysis": SHIGAN_ANALYSIS.get("伤官", ""),
            "creative_strength": 0.75,
            "suggestions": [
                "发挥创意优势，尝试新领域",
                "注意表达方式，防口舌是非",
                "适合创意、设计、艺术类工作",
            ],
            "confidence": 0.78,
        }
        return result


class PianyinAgent(ShenAgent):
    """偏印·桥接通变 — 智慧与学习分析"""
    def __init__(self):
        super().__init__("偏印", "桥接通变", "分析命主的学习能力、思维方式与玄学天赋")

    def analyze(self, bazi_data, question=""):
        result = {
            "agent": self.name,
            "title": self.title,
            "analysis": SHIGAN_ANALYSIS.get("偏印", ""),
            "learning_aptitude": 0.70,
            "suggestions": [
                "适合钻研技术、学术、玄学",
                "独立思考能力强，适合独立研究",
                "注意劳逸结合，避免过度钻研",
            ],
            "confidence": 0.76,
        }
        return result


class PiancaiAgent(ShenAgent):
    """偏财·奇招演化 — 投资与投机分析"""
    def __init__(self):
        super().__init__("偏财", "奇招演化", "分析命主的投资眼光、偏财运与风险偏好")

    def analyze(self, bazi_data, question=""):
        result = {
            "agent": self.name,
            "title": self.title,
            "analysis": SHIGAN_ANALYSIS.get("偏财", ""),
            "risk_tolerance": 0.65,
            "suggestions": [
                "有投资眼光，但需风险控制",
                "适合副业、兼职增加收入",
                "注意见好就收，忌贪心不足",
            ],
            "confidence": 0.77,
        }
        return result


class YuanchenAgent(ShenAgent):
    """元辰·本源定位 — 本源与根基分析"""
    def __init__(self):
        super().__init__("元辰", "本源定位", "分析命主的根本特质、五行根基与核心优势")

    def analyze(self, bazi_data, question=""):
        day_master = bazi_data.get("day_master", "")
        pillars = bazi_data.get("pillars", {})

        # 五行统计
        wuxing_count = {"木": 0, "火": 0, "土": 0, "金": 0, "水": 0}
        gan_wuxing = {"甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土",
                      "己": "土", "庚": "金", "辛": "金", "壬": "水", "癸": "水"}
        for p in pillars.values():
            if len(p) >= 2:
                g, z = p[0], p[1]
                if g in gan_wuxing:
                    wuxing_count[gan_wuxing[g]] += 1

        dominant = max(wuxing_count, key=wuxing_count.get)
        weakest = min(wuxing_count, key=wuxing_count.get)

        result = {
            "agent": self.name,
            "title": self.title,
            "analysis": f"命主五行分布：{wuxing_count}。最强五行：{dominant}，最弱五行：{weakest}。",
            "wuxing_distribution": wuxing_count,
            "dominant_element": dominant,
            "weakest_element": weakest,
            "core_traits": self._derive_traits(dominant),
            "suggestions": [
                f"发挥{dominant}五行优势",
                f"适当补充{weakest}五行能量",
                "立足根本，扬长避短",
            ],
            "confidence": 0.85,
        }
        return result

    def _derive_traits(self, element: str) -> str:
        traits = {
            "木": "仁慈、生长、创新、有韧性",
            "火": "热情、领导力、行动力、感染力",
            "土": "诚信、稳重、包容、务实",
            "金": "果断、刚毅、执行力、正义感",
            "水": "智慧、灵活、沟通力、适应力",
        }
        return traits.get(element, "综合型")


class JiecaiAgent(ShenAgent):
    """劫财·攻防边界 — 竞争与合作分析"""
    def __init__(self):
        super().__init__("劫财", "攻防边界", "分析命主的人际竞争、合作风险与防小人策略")

    def analyze(self, bazi_data, question=""):
        result = {
            "agent": self.name,
            "title": self.title,
            "analysis": SHIGAN_ANALYSIS.get("劫财", ""),
            "competition_level": 0.60,
            "suggestions": [
                "谨慎对待合伙投资",
                "注意钱财保密，不轻易借贷",
                "感情上注意维护信任",
            ],
            "confidence": 0.75,
        }
        return result


class TaijiAgent(ShenAgent):
    """太极·阴阳调和 — 平衡与调和分析"""
    def __init__(self):
        super().__init__("太极", "阴阳调和", "分析命局的阴阳平衡与五行调和状态")

    def analyze(self, bazi_data, question=""):
        pillars = bazi_data.get("pillars", {})
        gan_yinyang = {"甲": "阳", "乙": "阴", "丙": "阳", "丁": "阴", "戊": "阳",
                       "己": "阴", "庚": "阳", "辛": "阴", "壬": "阳", "癸": "阴"}

        yang_count, yin_count = 0, 0
        for p in pillars.values():
            if len(p) >= 2:
                g = p[0]
                if gan_yinyang.get(g) == "阳":
                    yang_count += 1
                else:
                    yin_count += 1

        balance = "阴阳平衡" if abs(yang_count - yin_count) <= 1 else ("阳盛" if yang_count > yin_count else "阴盛")

        result = {
            "agent": self.name,
            "title": self.title,
            "analysis": f"命局阴阳状态：{balance}（阳{yang_count}，阴{yin_count}）。",
            "yang_count": yang_count,
            "yin_count": yin_count,
            "balance_status": balance,
            "suggestions": [
                "阴阳平衡者，行事稳重，适应力强" if balance == "阴阳平衡" else
                "阳盛者宜增加阴柔之力，避免刚愎" if balance == "阳盛" else
                "阴盛者宜增加阳刚之力，避免优柔",
                "注意生活作息的阴阳调和",
            ],
            "confidence": 0.82,
        }
        return result


class ZhengyinAgent(ShenAgent):
    """正印·滋养守护 — 贵人与学业分析"""
    def __init__(self):
        super().__init__("正印", "滋养守护", "分析命主的贵人缘、学业运与长辈助力")

    def analyze(self, bazi_data, question=""):
        result = {
            "agent": self.name,
            "title": self.title,
            "analysis": SHIGAN_ANALYSIS.get("正印", ""),
            "mentor_luck": 0.75,
            "suggestions": [
                "虚心求教，贵人多为长辈上司",
                "适合文化教育、研究类工作",
                "注重学习进修，提升自我",
            ],
            "confidence": 0.79,
        }
        return result


class ZhengguanAgent(ShenAgent):
    """正官·法度调度 — 事业与官运分析"""
    def __init__(self):
        super().__init__("正官", "法度调度", "分析命主的事业发展、职位晋升与职场关系")

    def analyze(self, bazi_data, question=""):
        result = {
            "agent": self.name,
            "title": self.title,
            "analysis": SHIGAN_ANALYSIS.get("正官", ""),
            "career_prospect": "良好",
            "suggestions": [
                "把握职场机遇，争取晋升",
                "注重人际关系，维护上级信任",
                "遵纪守法，避免职场纠纷",
            ],
            "confidence": 0.80,
        }
        return result


class ZhengcaiAgent(ShenAgent):
    """正财·知识固化 — 稳定收入分析"""
    def __init__(self):
        super().__init__("正财", "知识固化", "分析命主的稳定收入、理财能力与财富积累")

    def analyze(self, bazi_data, question=""):
        result = {
            "agent": self.name,
            "title": self.title,
            "analysis": SHIGAN_ANALYSIS.get("正财", ""),
            "wealth_stability": 0.70,
            "suggestions": [
                "适合稳健理财，定期储蓄",
                "专注主业，正财稳定增长",
                "已婚者家庭收入增加，注意理财规划",
            ],
            "confidence": 0.78,
        }
        return result


class BijianAgent(ShenAgent):
    """比肩·架构协同 — 人际与协作分析"""
    def __init__(self):
        super().__init__("比肩", "架构协同", "分析命主的人际关系、团队协作与朋友缘分")

    def analyze(self, bazi_data, question=""):
        result = {
            "agent": self.name,
            "title": self.title,
            "analysis": SHIGAN_ANALYSIS.get("比肩", ""),
            "social_score": 0.72,
            "suggestions": [
                "利用好人缘，拓展社交圈",
                "适合团队合作，发挥集体力量",
                "注意与朋友间的金钱往来",
            ],
            "confidence": 0.76,
        }
        return result


class ShishenAgent(ShenAgent):
    """食神·创生输出 — 创意与享乐分析"""
    def __init__(self):
        super().__init__("食神", "创生输出", "分析命主的创造力、才华展示与生活品质")

    def analyze(self, bazi_data, question=""):
        result = {
            "agent": self.name,
            "title": self.title,
            "analysis": SHIGAN_ANALYSIS.get("食神", ""),
            "creativity": 0.80,
            "suggestions": [
                "发挥才华，展示自我",
                "适合艺术、设计、餐饮等创意行业",
                "享受生活，但需注意适度",
            ],
            "confidence": 0.77,
        }
        return result


# ============================================================================
# 综合智能体（非十神，但属于智能体系统）
# ============================================================================

class SizhuAgent(ShenAgent):
    """四柱·五行综合诊断 — 全面五行分析"""
    def __init__(self):
        super().__init__("四柱", "五行综合诊断", "全面分析命局五行、日主强弱、格局特点", category="综合")

    def analyze(self, bazi_data, question=""):
        pillars = bazi_data.get("pillars", {})
        day_master = bazi_data.get("day_master", "")

        result = {
            "agent": self.name,
            "title": self.title,
            "analysis": f"日主{day_master}，四柱排布：{pillars}",
            "pillars": pillars,
            "day_master": day_master,
            "suggestions": [
                "了解自身五行特质，明确发展方向",
                "根据日主强弱选择适合的行业",
                "结合大运流年把握人生节奏",
            ],
            "confidence": 0.85,
        }
        return result


class LiunianAgent(ShenAgent):
    """流年·运势趋势预测 — 趋势分析"""
    def __init__(self):
        super().__init__("流年", "运势趋势预测", "分析当前及未来年份的运势趋势与关键节点", category="预测")

    def analyze(self, bazi_data, question=""):
        result = {
            "agent": self.name,
            "title": self.title,
            "analysis": "基于命局与流年干支关系，推演运势趋势。",
            "suggestions": [
                "关注关键年份的运势变化",
                "在运势上升期积极进取",
                "在运势低迷期保守为要",
            ],
            "confidence": 0.75,
        }
        return result


# ============================================================================
# 智能体注册表
# ============================================================================

# 所有十神智能体
ALL_SHEN_AGENTS: Dict[str, ShenAgent] = {
    "七杀": QishaAgent(),
    "伤官": ShangguanAgent(),
    "偏印": PianyinAgent(),
    "偏财": PiancaiAgent(),
    "元辰": YuanchenAgent(),
    "劫财": JiecaiAgent(),
    "太极": TaijiAgent(),
    "正印": ZhengyinAgent(),
    "正官": ZhengguanAgent(),
    "正财": ZhengcaiAgent(),
    "比肩": BijianAgent(),
    "食神": ShishenAgent(),
}

# 综合智能体
COMPREHENSIVE_AGENTS: Dict[str, ShenAgent] = {
    "四柱": SizhuAgent(),
    "流年": LiunianAgent(),
}

# 全部智能体
ALL_AGENTS: Dict[str, ShenAgent] = {**ALL_SHEN_AGENTS, **COMPREHENSIVE_AGENTS}


def get_agent(name: str) -> Optional[ShenAgent]:
    """获取指定智能体"""
    return ALL_AGENTS.get(name)


def list_agents() -> List[Dict[str, str]]:
    """列出所有智能体"""
    return [
        {"name": a.name, "title": a.title, "description": a.description, "category": a.category}
        for a in ALL_AGENTS.values()
    ]


def analyze_with_agents(
    bazi_data: Dict[str, Any],
    agent_names: Optional[List[str]] = None,
    question: str = "",
) -> Dict[str, Any]:
    """
    使用指定智能体（或全部）进行分析。

    Args:
        bazi_data: 八字命盘数据
        agent_names: 智能体名称列表（None = 全部）
        question: 用户问题

    Returns:
        {"agents": [...], "summary": "..."}
    """
    agents_to_use = []
    if agent_names:
        for name in agent_names:
            agent = get_agent(name)
            if agent:
                agents_to_use.append(agent)
    else:
        agents_to_use = list(ALL_SHEN_AGENTS.values())

    results = []
    for agent in agents_to_use:
        result = agent.analyze(bazi_data, question)
        results.append(result)

    # 汇总
    summary_parts = []
    for r in results:
        if r.get("analysis"):
            summary_parts.append(f"【{r['agent']}】{r['analysis'][:100]}")

    return {
        "agents": results,
        "count": len(results),
        "summary": "\n".join(summary_parts),
    }


def get_all_agent_tool_specs() -> List[Dict]:
    """获取所有智能体的 function calling 规格"""
    specs = []
    for agent in ALL_AGENTS.values():
        specs.append(agent.to_tool_spec())
    return specs


def agent_tool_dispatcher(agent_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """智能体工具分发器（用于 AgentOrchestrator 工具链）"""
    agent = get_agent(agent_name)
    if not agent:
        return {"tool": f"shen_{agent_name}", "result": f"智能体 '{agent_name}' 不存在"}
    analysis = agent.analyze(
        params.get("bazi_data", {}),
        params.get("question", ""),
    )
    return {"tool": f"shen_{agent_name}", "result": analysis}


__all__ = [
    "ShenAgent",
    "QishaAgent", "ShangguanAgent", "PianyinAgent", "PiancaiAgent",
    "YuanchenAgent", "JiecaiAgent", "TaijiAgent",
    "ZhengyinAgent", "ZhengguanAgent", "ZhengcaiAgent",
    "BijianAgent", "ShishenAgent",
    "SizhuAgent", "LiunianAgent",
    "ALL_SHEN_AGENTS", "COMPREHENSIVE_AGENTS", "ALL_AGENTS",
    "get_agent", "list_agents", "analyze_with_agents",
    "get_all_agent_tool_specs", "agent_tool_dispatcher",
]