#!/usr/bin/env python3
"""
innovator.py — 破界创新器
伤官主理破界，辅助系统在传统范式之外产生新解。
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
import uuid
import time


class InnovationType(Enum):
    """创新类型"""
    COMBINATION = "combination"   # 组合创新
    TRANSFER = "transfer"         # 迁移创新
    REVERSE = "reverse"           # 逆向创新
    BREAKTHROUGH = "breakthrough" # 突破创新


@dataclass
class Idea:
    """创意"""
    id: str
    title: str
    description: str
    innovation_type: InnovationType
    feasibility: float  # 0-1
    impact: float       # 0-1
    created_at: float = field(default_factory=time.time)
    tags: List[str] = field(default_factory=list)

    @property
    def score(self) -> float:
        """综合得分"""
        return (self.feasibility * 0.4 + self.impact * 0.6)


class Innovator:
    """破界创新器 — 破界之锋

    通过组合、迁移、逆向、突破四种方式产生新解。
    """

    def __init__(self):
        self._ideas: List[Idea] = []

    def combine(self, items: List[str], description: str = "") -> Idea:
        """组合创新：将多个元素组合产生新解"""
        title = f"组合: {' × '.join(items)}"
        if not description:
            description = f"将 {' 与 '.join(items)} 组合，形成新方案"
        idea = Idea(
            id=str(uuid.uuid4())[:8],
            title=title,
            description=description,
            innovation_type=InnovationType.COMBINATION,
            feasibility=0.7,
            impact=0.7,
            tags=items,
        )
        self._ideas.append(idea)
        return idea

    def transfer(self, source: str, target: str, description: str = "") -> Idea:
        """迁移创新：将一领域的方案迁移到另一领域"""
        title = f"迁移: {source} → {target}"
        if not description:
            description = f"将 {source} 领域的做法迁移到 {target} 领域"
        idea = Idea(
            id=str(uuid.uuid4())[:8],
            title=title,
            description=description,
            innovation_type=InnovationType.TRANSFER,
            feasibility=0.6,
            impact=0.8,
            tags=[source, target],
        )
        self._ideas.append(idea)
        return idea

    def reverse(self, original: str, description: str = "") -> Idea:
        """逆向创新：反向思考"""
        title = f"逆向: {original}"
        if not description:
            description = f"对 {original} 进行反向思考"
        idea = Idea(
            id=str(uuid.uuid4())[:8],
            title=title,
            description=description,
            innovation_type=InnovationType.REVERSE,
            feasibility=0.5,
            impact=0.9,
            tags=["逆向"],
        )
        self._ideas.append(idea)
        return idea

    def top_ideas(self, n: int = 5) -> List[Idea]:
        """获取得分最高的创意"""
        return sorted(self._ideas, key=lambda i: i.score, reverse=True)[:n]

    def list_by_type(self, itype: InnovationType) -> List[Idea]:
        """按类型筛选"""
        return [i for i in self._ideas if i.innovation_type == itype]

    def report(self) -> Dict[str, Any]:
        """生成创意报告"""
        return {
            "total": len(self._ideas),
            "by_type": {
                itype.value: len(self.list_by_type(itype))
                for itype in InnovationType
            },
            "top_ideas": [
                {
                    "id": i.id,
                    "title": i.title,
                    "score": round(i.score, 3),
                    "type": i.innovation_type.value,
                }
                for i in self.top_ideas()
            ],
            "version": "1.4.0",
        }

    def set_generator(self, generator) -> None:
        """注入 ContentGenerator（食神）实例，用于后续 LLM 调用"""
        self._generator = generator

    def generate_with_llm(self, prompt: str, style: str = "creative") -> Optional[Idea]:
        """用 LLM 实际生成创意"""
        if not hasattr(self, "_generator") or self._generator is None:
            import warnings
            warnings.warn("generator 未注入，LLM 方法不可用")
            return None
        template = """你是一位破界创新专家。请针对「{prompt}」提出一个原创性解决方案，要求：
1. 方案名称（中文，5字以内）
2. 创新类型（组合/迁移/逆向/突破之一）
3. 简要描述（2-3句）
4. 可行性评估（0-1之间）
5. 影响评估（0-1之间）
请用JSON格式返回，字段：title, description, innovation_type, feasibility, impact"""
        full_prompt = template.format(prompt=prompt)
        try:
            result = self._generator.generate(full_prompt, style=style)
            import json, re
            json_match = re.search(r'\{[^{}]*"title"[^{}]*\}', result, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                data = json.loads(result)
            type_map = {
                "组合": InnovationType.COMBINATION,
                "迁移": InnovationType.TRANSFER,
                "逆向": InnovationType.REVERSE,
                "突破": InnovationType.BREAKTHROUGH,
            }
            innovation_type = type_map.get(data.get("innovation_type", ""), InnovationType.COMBINATION)
            idea = Idea(
                id=str(uuid.uuid4())[:8],
                title=data.get("title", "未命名"),
                description=data.get("description", ""),
                innovation_type=innovation_type,
                feasibility=float(data.get("feasibility", 0.5)),
                impact=float(data.get("impact", 0.5)),
                tags=[prompt[:10]],
            )
            self._ideas.append(idea)
            return idea
        except Exception:
            idea = Idea(
                id=str(uuid.uuid4())[:8],
                title="LLM生成",
                description=f"针对「{prompt}」的创意方案",
                innovation_type=InnovationType.COMBINATION,
                feasibility=0.5,
                impact=0.5,
                tags=[prompt[:10]],
            )
            self._ideas.append(idea)
            return idea

    def elaborate_idea(self, idea_id: str, style: str = "detailed") -> Optional[str]:
        """用 LLM 将创意扩展为详细方案"""
        if not hasattr(self, "_generator") or self._generator is None:
            import warnings
            warnings.warn("generator 未注入，LLM 方法不可用")
            return None
        idea = next((i for i in self._ideas if i.id == idea_id), None)
        if idea is None:
            return None
        template = """请将以下创意扩展为详细实施方案：

创意：{title}
类型：{itype}
描述：{description}

请给出3-5个具体实施步骤，用中文描述，每步200字左右。"""
        prompt = template.format(
            title=idea.title,
            itype=idea.innovation_type.value,
            description=idea.description,
        )
        try:
            from 食神_创生输出 import GenerationConfig
            cfg = GenerationConfig(style=style)
            return self._generator.generate(prompt, cfg)
        except Exception as e:
            return f"方案扩展失败: {str(e)}"

    def evaluate_with_llm(self, idea_id: str) -> Optional[Dict[str, Any]]:
        """用 LLM 对创意做可行性评估"""
        if not hasattr(self, "_generator") or self._generator is None:
            import warnings
            warnings.warn("generator 未注入，LLM 方法不可用")
            return None
        idea = next((i for i in self._ideas if i.id == idea_id), None)
        if idea is None:
            return None
        template = """请评估以下创意的可行性：

创意：{title}
类型：{itype}
描述：{description}

请从以下维度评估（0-1分）：
1. 创新度
2. 可行性
3. 风险
4. 潜在影响

请用JSON格式返回：{{"innovation": 0.0-1.0, "feasibility": 0.0-1.0, "risk": 0.0-1.0, "impact": 0.0-1.0, "suggestions": "建议文本"}}"""
        prompt = template.format(
            title=idea.title,
            itype=idea.innovation_type.value,
            description=idea.description,
        )
        try:
            from 食神_创生输出 import GenerationConfig
            cfg = GenerationConfig(style="evaluation")
            result = self._generator.generate(prompt, cfg)
            import json, re
            json_match = re.search(r'\{[^{}]*"innovation"[^{}]*\}', result, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                data = json.loads(result)
            return data
        except Exception:
            return {"innovation": idea.score, "feasibility": idea.feasibility, "risk": 0.5, "impact": idea.impact, "suggestions": "评估失败"}

    def idea_to_knowledge(self, idea_id: str, kb) -> Optional[Dict[str, Any]]:
        """将创意存入正财知识库"""
        idea = next((i for i in self._ideas if i.id == idea_id), None)
        if idea is None:
            return None
        info = {
            "title": idea.title,
            "description": idea.description,
            "tags": idea.tags + [idea.innovation_type.value],
            "innovation_type": idea.innovation_type.value,
            "feasibility": idea.feasibility,
            "impact": idea.impact,
            "score": idea.score,
        }
        node = kb.add_node(
            name=f"[创意]{idea.title}",
            node_type=f"idea_{idea.innovation_type.value}",
            properties=info,
        )
        return {"id": node.id, "name": node.name, "node_type": node.node_type}

    def pipeline(self, items: List[str], *, use_llm: bool = True, save_to_kb=None) -> Dict[str, Any]:
        """完整闭环流程"""
        if use_llm and hasattr(self, "_generator") and self._generator is not None:
            combined = " + ".join(items)
            idea = self.generate_with_llm(combined)
        else:
            idea = self.combine(items)
        if idea is None:
            return {"status": "failed", "reason": "创意生成失败"}
        result = {"idea_id": idea.id, "title": idea.title, "steps": []}
        if use_llm and hasattr(self, "_generator") and self._generator is not None:
            elaborated = self.elaborate_idea(idea.id)
            if elaborated:
                result["elaborated"] = elaborated
        if save_to_kb is not None:
            saved = self.idea_to_knowledge(idea.id, save_to_kb)
            result["knowledge_saved"] = saved is not None
        return result


__all__ = ["Innovator", "Idea", "InnovationType"]
