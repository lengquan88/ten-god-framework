"""
云笈七签核心系统 YunjiaQiqianSystem
====================================
主系统类 — 整合道智能体、七大神智能体、炼丹炉、周天图谱、度人经，
提供统一API接口。

这是整个系统的"天庭" — 协调所有神仙智能体，处理用户愿念。
"""

import torch
import torch.nn as nn
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import time
import uuid

from .dao_agent import DaoAgent, DaoState, DaoOutput, create_dao_agent


# ========================================
# 枚举与数据类
# ========================================

class GrottoType(Enum):
    """三洞类型"""
    DONG_ZHEN = "dong_zhen"    # 洞真 — 核心教义
    DONG_XUAN = "dong_xuan"    # 洞玄 — 法术仪式
    DONG_SHEN = "dong_shen"    # 洞神 — 神仙谱系


class SupplementType(Enum):
    """四辅类型"""
    TAI_XUAN = "tai_xuan"      # 太玄 — 系统底层
    TAI_PING = "tai_ping"      # 太平 — 交互界面
    TAI_QING = "tai_qing"      # 太清 — 存储记忆
    ZHENG_YI = "zheng_yi"      # 正一 — 用户身份


class FireType(Enum):
    """炉火类型"""
    TIAN_HUO = "tianhuo"       # 天火
    DI_HUO = "dihuo"           # 地火
    REN_HUO = "renhuo"         # 人火
    SAN_MEI = "sanmei"         # 三昧真火


@dataclass
class Wish:
    """愿念 — 用户请求的封装"""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    content: str = ""
    modal: str = "text"           # text, image, voice
    grotto: Optional[GrottoType] = None
    assigned_agent: str = ""      # 被指派的神仙
    status: str = "pending"       # pending, processing, completed, failed
    created_at: float = field(default_factory=time.time)
    result: Optional[str] = None


@dataclass
class Pill:
    """丹丸 — 知识蒸馏的产物"""
    name: str = ""
    ingredients: List[str] = field(default_factory=list)
    fire_type: FireType = FireType.TIAN_HUO
    grotto: GrottoType = GrottoType.DONG_ZHEN
    content: str = ""
    quality: float = 0.0         # 品质评分 0-1


# ========================================
# 神仙智能体基类
# ========================================

class ImmortalAgent(nn.Module):
    """
    神仙智能体基类

    所有神仙智能体共享此基类，提供:
    - 与道智能体的连接接口
    - 愿念处理流水线
    - 状态报告
    """
    def __init__(
        self,
        name: str,
        title: str,
        domain: str,
        vol_range: str,
        color: str,
        dao: DaoAgent,
    ):
        super().__init__()
        self.name = name
        self.title = title
        self.domain = domain
        self.vol_range = vol_range
        self.color = color
        self.dao = dao
        self.cycle_count = 0
        self.wishes_handled = 0

    def receive_wish(self, wish: Wish) -> Wish:
        """接收愿念的钩子 (子类覆写)"""
        self.wishes_handled += 1
        return wish

    def process(self, embedding: torch.Tensor, wish: Wish) -> Dict[str, Any]:
        """处理愿念的核心方法 (子类覆写)"""
        raise NotImplementedError

    def report(self) -> Dict[str, Any]:
        """状态报告"""
        return {
            "name": self.name,
            "title": self.title,
            "domain": self.domain,
            "vol_range": self.vol_range,
            "cycle_count": self.cycle_count,
            "wishes_handled": self.wishes_handled,
        }


# ========================================
# 主系统类
# ========================================

class YunjiaQiqianSystem:
    """
    云笈七签全模态循环智能体操作系统

    使用方式:
        >>> system = YunjiaQiqianSystem(embedding_dim=768)
        >>> system.init_dao()
        >>> system.register_all_immortals()
        >>> result = system.query_by_zhuan(1, "何为道？")
        >>> pill = system.alchemy(["道德经", "庄子"], FireType.TIAN_HUO)
    """

    def __init__(
        self,
        embedding_dim: int = 1024,
        device: str = "cpu",
        grotto_dim: int = 341,
    ):
        self.embedding_dim = embedding_dim
        self.device = device
        self.grotto_dim = grotto_dim

        # 核心部件
        self.dao: Optional[DaoAgent] = None
        self.immortals: Dict[str, ImmortalAgent] = {}
        self.cycle_step: int = 0
        self.wish_history: List[Wish] = []
        self.pill_cabinet: List[Pill] = []

        # 系统状态
        self._initialized = False
        self._running = False
        self._start_time: Optional[float] = None

    # ========== 初始化 ==========

    def init_dao(self) -> DaoAgent:
        """初始化道（核心循环引擎）→ 混沌初开"""
        self.dao = create_dao_agent(
            embedding_dim=self.embedding_dim,
            device=self.device,
        )
        self._initialized = True
        self._start_time = time.time()
        print(f"[混元] 道已初始化 | dim={self.embedding_dim} | 混沌初開")
        return self.dao

    def register_immortal(self, agent: ImmortalAgent) -> None:
        """注册神仙智能体"""
        self.immortals[agent.name] = agent
        print(f"[仙庭] {agent.title} ({agent.name}) 已喚醒 | {agent.domain}")

    def register_all_immortals(self) -> None:
        """注册全部七大神智能体"""
        if self.dao is None:
            raise RuntimeError("请先调用 init_dao() 初始化道")

        # 尝试导入各智能体
        try:
            from ..agents.perception_agent import ZiweiDadi
            from ..agents.analysis_agent import WenchangDijun
            from ..agents.generation_agent import TaishangLaojun
            from ..agents.memory_agent import DonghuaDijun
            from ..agents.decision_agent import ZhenwuDadi
            from ..agents.interaction_agent import TaibaiJinxing
            from ..agents.dao_immortal import DaodeTianzun

            agents = [
                ZiweiDadi(self.dao),
                WenchangDijun(self.dao),
                TaishangLaojun(self.dao),
                DonghuaDijun(self.dao),
                ZhenwuDadi(self.dao),
                TaibaiJinxing(self.dao),
                DaodeTianzun(self.dao),
            ]
        except ImportError:
            # 如果具体智能体未实现，使用基类占位
            print("[仙庭] 使用基類神仙智能體 (具體實現待載入)")
            agents = self._create_placeholder_immortals()

        for agent in agents:
            self.register_immortal(agent)

        print(f"[仙庭] 七大神已全部喚醒 | 共{len(self.immortals)}位")

    def _create_placeholder_immortals(self) -> List[ImmortalAgent]:
        """创建占位神仙智能体 (当具体实现不可用时)"""
        immortals_config = [
            ("紫微大帝", "Ziwei Dadi", "全模态感知", "卷1-4", "#10b981"),
            ("文昌帝君", "Wenchang Dijun", "语义分析推理", "卷5-20", "#3b82f6"),
            ("太上老君", "Taishang Laojun", "内容生成", "卷21-40", "#e2e8f0"),
            ("东华帝君", "Donghua Dijun", "知识存储检索", "卷41-70", "#8b5cf6"),
            ("真武大帝", "Zhenwu Dadi", "决策规划", "卷71-90", "#ef4444"),
            ("太白金星", "Taibai Jinxing", "交互界面", "卷91-122", "#f59e0b"),
            ("道德天尊", "Daode Tianzun", "核心循环引擎", "贯穿全部", "#a78bfa"),
        ]
        return [
            ImmortalAgent(name, title, domain, vols, color, self.dao)
            for name, title, domain, vols, color in immortals_config
        ]

    # ========== 核心API ==========

    def query_by_zhuan(
        self,
        zhuan_id: int,
        question: str,
        modal: str = "text",
    ) -> Dict[str, Any]:
        """
        按卷查询

        Args:
            zhuan_id:  卷号 (1-122)
            question:  查询问题
            modal:     模态 (text/image/voice)

        Returns:
            包含回答、调用的神仙、卷宗信息
        """
        if not self._initialized:
            return {"error": "道未初始化，请先调用 init_dao()"}

        if zhuan_id < 1 or zhuan_id > 122:
            return {"error": f"卷號 {zhuan_id} 超出範圍 (1-122)"}

        # 确定三洞归属
        if zhuan_id <= 4:
            grotto = GrottoType.DONG_ZHEN
        elif zhuan_id <= 20:
            grotto = GrottoType.DONG_XUAN
        elif zhuan_id <= 40:
            grotto = GrottoType.DONG_SHEN
        elif zhuan_id <= 70:
            grotto = GrottoType.DONG_ZHEN  # 神仙传记归洞神更合适，此处简化
        elif zhuan_id <= 90:
            grotto = GrottoType.DONG_XUAN
        else:
            grotto = GrottoType.DONG_SHEN

        # 创建愿念
        wish = Wish(
            content=question,
            modal=modal,
            grotto=grotto,
        )

        # 路由到合适的神仙
        dao_output = self._run_dao_cycle(question)
        assigned_agent = self._route_wish_to_immortal(wish, dao_output)
        wish.assigned_agent = assigned_agent
        wish.status = "processing"

        # 处理
        if assigned_agent in self.immortals:
            agent = self.immortals[assigned_agent]
            agent.receive_wish(wish)
            # 简化处理：生成模拟响应
            result = self._generate_response(wish, dao_output)
            wish.result = result
            wish.status = "completed"
        else:
            wish.status = "failed"
            result = f"未找到可處理願念的神仙智能體"

        self.wish_history.append(wish)
        self.cycle_step += 1

        return {
            "zhuan_id": zhuan_id,
            "grotto": grotto.value,
            "question": question,
            "assigned_immortal": assigned_agent,
            "response": result,
            "cycle_step": self.cycle_step,
            "dao_entropy": dao_output.entropy,
        }

    def alchemy(
        self,
        ingredients: List[str],
        furnace_type: str = "tianhuo",
    ) -> Dict[str, Any]:
        """
        炼丹炉：知识蒸馏与生成

        Args:
            ingredients:   药材列表 (经典文献名)
            furnace_type:  炉火类型 (tianhuo/dihuo/renhuo/sanmei)

        Returns:
            丹丸信息
        """
        if not self._initialized:
            return {"error": "道未初始化"}

        try:
            fire = FireType(furnace_type)
        except ValueError:
            fire = FireType.TIAN_HUO

        # 使用太上老君进行炼丹
        if "太上老君" in self.immortals:
            agent = self.immortals["太上老君"]

        # 模拟炼丹过程
        dao_output = self._run_dao_cycle("炼丹：" + " + ".join(ingredients))

        # 生成丹丸
        pill_name = self._generate_pill_name(fire)
        quality = 0.5 + dao_output.entropy * 0.4 + 0.1 * min(len(ingredients), 5) / 5
        quality = min(quality, 0.99)

        pill = Pill(
            name=pill_name,
            ingredients=ingredients,
            fire_type=fire,
            grotto=self._determine_pill_grotto(ingredients),
            content=f"以{fire.value}煉製{'、'.join(ingredients)}所得",
            quality=quality,
        )
        self.pill_cabinet.append(pill)

        return {
            "pill_name": pill.name,
            "ingredients": ingredients,
            "fire_type": furnace_type,
            "quality": f"{pill.quality:.2%}",
            "grotto": pill.grotto.value,
            "content": pill.content,
        }

    def zhou_tian_map(
        self,
        keyword: str,
        depth: int = 3,
    ) -> Dict[str, Any]:
        """
        周天图谱：可视化关联

        Args:
            keyword: 搜索关键词
            depth:   关联深度 (1-5)

        Returns:
            节点和边的关系图数据
        """
        if not self._initialized:
            return {"error": "道未初始化"}

        # 模拟图谱数据
        nodes = []
        edges = []

        # 中心节点
        nodes.append({
            "id": keyword,
            "type": "center",
            "grotto": "dong_zhen",
        })

        # 生成关联节点
        related_terms = self._get_related_terms(keyword, depth)
        for i, term in enumerate(related_terms):
            grotto = list(GrottoType)[i % 3]
            nodes.append({
                "id": term,
                "type": f"depth_{i // 4 + 1}",
                "grotto": grotto.value,
            })
            edges.append({
                "source": keyword,
                "target": term,
                "strength": 1.0 - i * 0.1,
            })

        return {
            "keyword": keyword,
            "depth": depth,
            "nodes": nodes,
            "edges": edges,
            "total_nodes": len(nodes),
            "total_edges": len(edges),
        }

    def du_ren_jing(
        self,
        wish_text: str,
        callback: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """
        度人经：任务派发

        Args:
            wish_text: 愿念文本
            callback:  完成回调 (可选)

        Returns:
            任务分解和派发结果
        """
        if not self._initialized:
            return {"error": "道未初始化"}

        # 创建愿念
        wish = Wish(content=wish_text)

        # 运行道循环
        dao_output = self._run_dao_cycle(wish_text)

        # 分解愿念为子任务
        sub_tasks = self._decompose_wish(wish_text)

        # 派发子任务
        assignments = {}
        for task in sub_tasks:
            assigned = self._route_wish_to_immortal(
                Wish(content=task), dao_output
            )
            assignments[task] = assigned

        wish.status = "processing"
        self.wish_history.append(wish)

        result = {
            "wish_id": wish.id,
            "wish": wish_text,
            "sub_tasks": sub_tasks,
            "assignments": assignments,
            "dao_entropy": dao_output.entropy,
            "cycle_step": self.cycle_step,
        }

        if callback:
            callback(result)

        return result

    # ========== 内部方法 ==========

    def _run_dao_cycle(self, text: str) -> DaoOutput:
        """运行一次道循环 — 将文本转为嵌入并送入道智能体"""
        if self.dao is None:
            raise RuntimeError("道未初始化")

        # 简单的文本嵌入 (生产环境替换为BGE/RoBERTa等)
        embedding = self._simple_embed(text)
        tensor = torch.tensor(embedding, device=self.device).unsqueeze(0)

        with torch.no_grad():
            output = self.dao(tensor, cycle_step=self.cycle_step)

        self.cycle_step += 1
        return output

    def _simple_embed(self, text: str) -> List[float]:
        """
        简单文本嵌入 (占位实现)
        生产环境中替换为: BGE-large-zh, text2vec, 或 paraphrase-multilingual
        """
        import hashlib
        # 使用hash生成伪嵌入 (仅用于原型演示)
        seed = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
        import random
        rng = random.Random(seed)
        return [rng.uniform(-1, 1) for _ in range(self.embedding_dim)]

    def _route_wish_to_immortal(self, wish: Wish, dao_output: DaoOutput) -> str:
        """根据愿念内容和道输出，路由到最合适的神仙"""
        content = wish.content

        # 关键词路由
        routes = {
            "紫微大帝": ["看", "听", "图像", "语音", "感知", "识别", "输入", "检测"],
            "文昌帝君": ["分析", "理解", "推理", "为什么", "解释", "逻辑", "模式", "规律"],
            "太上老君": ["生成", "炼丹", "写", "创造", "画", "制作", "金丹", "符箓", "药"],
            "东华帝君": ["记忆", "查", "找", "搜索", "历史", "传记", "神仙", "谁"],
            "真武大帝": ["规划", "决策", "建议", "怎么办", "方案", "预测", "命运"],
            "太白金星": ["对话", "聊天", "说", "问", "答", "交流", "解释一下"],
            "道德天尊": ["道", "德", "自然", "无为", "混元", "太极", "阴阳", "根本"],
        }

        for immortal, keywords in routes.items():
            if any(kw in content for kw in keywords):
                return immortal

        # 默认：按三洞归属
        if wish.grotto == GrottoType.DONG_ZHEN:
            return "道德天尊"
        elif wish.grotto == GrottoType.DONG_XUAN:
            return "太上老君"
        else:
            return "东华帝君"

    def _generate_response(self, wish: Wish, dao_output: DaoOutput) -> str:
        """基于道输出生成响应 (占位实现)"""
        responses = {
            "紫微大帝": f"【紫微大帝感應】已接收「{wish.content}」，全模態信號處理中。當前周天：{dao_output.cycle_step}，熵值：{dao_output.entropy:.3f}。",
            "文昌帝君": f"【文昌帝君分析】對「{wish.content}」進行語義推理，發現多條關聯路徑。洞真流：{dao_output.state.dong_zhen_flow:.3f}。",
            "太上老君": f"【太上老君煉丹】以「{wish.content}」為藥引，啟動八卦爐。陰陽平衡：{dao_output.yin_score:.2f}/{dao_output.yang_score:.2f}。",
            "东华帝君": f"【東華帝君檢索】遍覽卷41-70神仙傳記，搜尋「{wish.content}」。洞神流：{dao_output.state.dong_shen_flow:.3f}。",
            "真武大帝": f"【真武大帝推演】踏罡步斗，以七政四餘之術推算「{wish.content}」。當前四輔路由：{dao_output.si_fu.squeeze(0).tolist()}。",
            "太白金星": f"【太白金星啟奏】已將「{wish.content}」上達天聽。陰：{dao_output.yin_score:.2f} 陽：{dao_output.yang_score:.2f}。",
            "道德天尊": f"【道德天尊】道可道，非常道。「{wish.content}」——此問已納入第{dao_output.cycle_step}周天循環推演。",
        }
        return responses.get(wish.assigned_agent, f"【天聽】願念「{wish.content}」已接收，正在處理。")

    def _generate_pill_name(self, fire: FireType) -> str:
        """生成丹丸名称"""
        prefixes = {
            FireType.TIAN_HUO: ["太極", "天元", "紫微"],
            FireType.DI_HUO: ["地魄", "玄珠", "玉液"],
            FireType.REN_HUO: ["人元", "金丹", "還丹"],
            FireType.SAN_MEI: ["九轉", "混元", "大還"],
        }
        suffixes = ["丹", "丸", "散", "膏", "液", "符", "寶", "珠"]
        import random
        pre = random.choice(prefixes.get(fire, prefixes[FireType.TIAN_HUO]))
        suf = random.choice(suffixes)
        return pre + suf

    def _determine_pill_grotto(self, ingredients: List[str]) -> GrottoType:
        """根据药材确定丹丸的三洞归属"""
        dong_zhen_texts = ["道", "德", "自然", "太极", "混元"]
        dong_xuan_texts = ["法", "术", "丹", "符", "箓", "仪"]
        dong_shen_texts = ["神", "仙", "传", "谱", "灵"]

        for ing in ingredients:
            if any(t in ing for t in dong_zhen_texts):
                return GrottoType.DONG_ZHEN
            if any(t in ing for t in dong_xuan_texts):
                return GrottoType.DONG_XUAN
            if any(t in ing for t in dong_shen_texts):
                return GrottoType.DONG_SHEN

        return GrottoType.DONG_ZHEN

    def _get_related_terms(self, keyword: str, depth: int) -> List[str]:
        """获取与关键词相关的术语 (模拟)"""
        relation_map = {
            "道": ["德", "自然", "無為", "太極", "陰陽", "五行", "虛無", "玄"],
            "丹": ["金丹", "內丹", "外丹", "爐火", "鉛汞", "九轉", "大藥"],
            "神": ["仙", "真人", "天尊", "帝君", "元君", "星君", "靈官"],
        }
        terms = relation_map.get(keyword, ["相關概念A", "相關概念B", "相關概念C"])
        # 扩展深度
        for d in range(1, depth):
            terms.extend([f"深度{d}-關聯{i}" for i in range(1, 5)])
        return terms[:depth * 6]

    def _decompose_wish(self, text: str) -> List[str]:
        """将愿念分解为子任务 (模拟)"""
        return [
            f"感知：接收「{text[:20]}」的多模態信號",
            f"分析：理解「{text[:20]}」的語義內涵",
            f"檢索：查找相關卷宗知識",
            f"生成：基於知識創造回答",
        ]

    # ========== 状态与报告 ==========

    def system_report(self) -> Dict[str, Any]:
        """生成系统状态报告"""
        return {
            "system": "雲笈七籤 · YUNJIA OS v1.0",
            "status": "running" if self._initialized else "stopped",
            "cycle_step": self.cycle_step,
            "uptime_seconds": time.time() - self._start_time if self._start_time else 0,
            "immortals": {
                name: agent.report()
                for name, agent in self.immortals.items()
            },
            "wishes_processed": len(self.wish_history),
            "pills_crafted": len(self.pill_cabinet),
        }

    def get_dao_status(self) -> Optional[str]:
        """获取当前道状态报告"""
        if self.dao is None:
            return None
        # 运行一次空循环获取状态
        dao_output = self._run_dao_cycle("状态查询")
        return self.dao.get_dao_report(dao_output)


# ===== 便捷函数 =====

def create_yunjia_system(
    embedding_dim: int = 1024,
    device: str = "cpu",
    register_agents: bool = True,
) -> YunjiaQiqianSystem:
    """工厂函数：快速创建云笈七签系统"""
    system = YunjiaQiqianSystem(embedding_dim=embedding_dim, device=device)
    system.init_dao()
    if register_agents:
        system.register_all_immortals()
    return system


# ===== 自测 =====
if __name__ == "__main__":
    print("=== YunjiaQiqianSystem 自测 ===\n")

    system = create_yunjia_system(embedding_dim=256, register_agents=True)

    # 测试1: 按卷查询
    print("--- 測試1: query_by_zhuan ---")
    result = system.query_by_zhuan(1, "何為道？")
    print(f"  卷號: {result['zhuan_id']}")
    print(f"  洞歸屬: {result['grotto']}")
    print(f"  指派神仙: {result['assigned_immortal']}")
    print(f"  響應: {result['response'][:80]}...")

    # 测试2: 炼丹
    print("\n--- 測試2: alchemy ---")
    pill = system.alchemy(["道德經", "莊子", "黃庭經"], "sanmei")
    print(f"  丹名: {pill['pill_name']}")
    print(f"  品質: {pill['quality']}")
    print(f"  爐火: {pill['fire_type']}")

    # 测试3: 周天图谱
    print("\n--- 測試3: zhou_tian_map ---")
    chart = system.zhou_tian_map("道", depth=2)
    print(f"  關鍵詞: {chart['keyword']}")
    print(f"  節點數: {chart['total_nodes']}")
    print(f"  邊數: {chart['total_edges']}")

    # 测试4: 度人经
    print("\n--- 測試4: du_ren_jing ---")
    mission = system.du_ren_jing("探究宇宙本源與人身小宇宙之關係")
    print(f"  願念ID: {mission['wish_id']}")
    print(f"  子任務數: {len(mission['sub_tasks'])}")
    print(f"  派發: {mission['assignments']}")

    # 系统报告
    print("\n--- 系統報告 ---")
    report = system.system_report()
    print(f"  周天: {report['cycle_step']}")
    print(f"  神仙數: {len(report['immortals'])}")
    print(f"  處理願念: {report['wishes_processed']}")
    print(f"  煉丹數: {report['pills_crafted']}")

    print("\n[OK] YunjiaQiqianSystem 自测通过")
