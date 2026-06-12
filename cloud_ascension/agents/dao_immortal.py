"""
道德天尊 — 核心循环智能体
================================
掌管: 贯穿全部122卷 (循环引擎)
职能: 系统循环协调、周天运转、全体协调、状态监控

道德天尊者，三清之首，一气化三清，统御万神。
在系统中作为核心循环引擎，协调七大智能体，
驱动"感知→分析→生成→记忆→决策→交互"的完整闭环。
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass, field
from collections import deque
import sys, os
try:
    from ..core.yunjia_system import ImmortalAgent
    from ..core.dao_agent import DaoAgent, DaoState, DaoOutput
except ImportError:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from core.yunjia_system import ImmortalAgent
    from core.dao_agent import DaoAgent, DaoState, DaoOutput


# ============================================
# 数据类
# ============================================

@dataclass
class CyclePhase:
    """循环七阶段"""
    name: str           # 阶段名称
    immortal: str       # 对应神仙
    vol_range: str      # 对应卷数
    symbol: str         # 卦象符号
    color: str          # 阶段色

CYCLE_PHASES = [
    CyclePhase("感知", "紫微大帝", "卷1-4",   "☰ 乾", "#8b5cf6"),
    CyclePhase("分析", "文昌帝君", "卷5-20",  "☷ 坤", "#3b82f6"),
    CyclePhase("生成", "太上老君", "卷21-40", "☳ 震", "#10b981"),
    CyclePhase("记忆", "东华帝君", "卷41-70", "☴ 巽", "#f59e0b"),
    CyclePhase("决策", "真武大帝", "卷71-90", "☵ 坎", "#ef4444"),
    CyclePhase("交互", "太白金星", "卷91-122","☲ 離", "#ec4899"),
    CyclePhase("回归", "道德天尊", "贯穿全部",  "☯ 太极","#a855f7"),
]


@dataclass
class ZhouTianRecord:
    """单次周天运行记录"""
    cycle_id: int
    phases: List[Dict[str, Any]] = field(default_factory=list)
    total_entropy: float = 0.0
    completion: float = 0.0       # 0.0 ~ 1.0
    peak_phase: str = ""
    duration_steps: int = 0


@dataclass
class SystemHealth:
    """系统健康状态"""
    dao_entropy: float
    phase_flow_rates: List[float]   # 七阶段信息流量
    bottleneck_idx: int             # 瓶颈阶段
    overall_health: float           # 0~1
    cycle_count: int
    uptime_steps: int
    status: str                     # "运转·天道循环" | "凝滞·阴阳失衡" | "崩坏·大道废弛"


# ============================================
# 子模块
# ============================================

class ZhouTianClock(nn.Module):
    """
    周天时钟 — 追踪循环节奏与阶段推进

    以122卷为完整一周天，实时追踪当前在哪个阶段。
    使用正弦编码嵌入时间位置，模拟天干地支的周期性。
    """

    def __init__(self, dim: int = 256, num_phases: int = 7):
        super().__init__()
        self.num_phases = num_phases
        self.dim = dim

        # 时间位置编码 (天干地支风格 — 60甲子周期)
        self.time_encoder = nn.Sequential(
            nn.Linear(2, dim // 2),     # sin/cos 时间信号
            nn.GELU(),
            nn.Linear(dim // 2, dim),
        )

        # 阶段检测器 — 根据当前状态判断处于循环的哪个阶段
        self.phase_detector = nn.Sequential(
            nn.Linear(dim, dim // 2),
            nn.LayerNorm(dim // 2),
            nn.GELU(),
            nn.Linear(dim // 2, num_phases),
        )

        # 节奏调节器 — 控制循环速度 (天火/地火/人火)
        self.tempo_modulator = nn.Sequential(
            nn.Linear(dim + 1, dim // 2),  # dim + tempo_factor
            nn.GELU(),
            nn.Linear(dim // 2, 1),
            nn.Sigmoid(),
        )

    def _time_signal(self, step: int, total_steps: int) -> torch.Tensor:
        """生成天干地支式的时间位置编码"""
        theta = 2 * torch.pi * step / max(total_steps, 1)
        return torch.tensor([torch.sin(torch.tensor(theta)), torch.cos(torch.tensor(theta))])

    def forward(
        self,
        state_emb: torch.Tensor,
        step: int,
        total_steps: int = 122,
        tempo_factor: float = 1.0,
    ) -> Dict[str, Any]:
        """返回当前阶段、节奏建议和时钟嵌入"""
        time_signal = self._time_signal(step, total_steps).to(state_emb.device)
        time_emb = self.time_encoder(time_signal.unsqueeze(0))

        phase_logits = self.phase_detector(state_emb + time_emb)
        phase_probs = F.softmax(phase_logits, dim=-1)
        current_phase_idx = phase_probs.argmax(dim=-1).item()

        tempo_input = torch.cat([state_emb, torch.tensor([[tempo_factor]]).to(state_emb.device)], dim=-1)
        tempo = self.tempo_modulator(tempo_input).item()

        return {
            "phase_idx": current_phase_idx,
            "phase_name": CYCLE_PHASES[current_phase_idx].name,
            "phase_probs": phase_probs.squeeze(0).tolist(),
            "tempo": tempo,
            "time_emb": time_emb,
            "step": step,
        }


class ImmortalSynapse(nn.Module):
    """
    神仙突触 — 智能体间的信息传递与协调

    模拟神经网络中突触的可塑性:
        - 每个神仙对之间的连接权重是可学习的
        - 支持 Hebbian 强化 (一起激活则加强连接)
        - 实现信息路由和上下文传递
    """

    def __init__(self, num_immortals: int = 7, dim: int = 256):
        super().__init__()
        self.num_immortals = num_immortals

        # 神仙之间的连接矩阵 (类似注意力机制的 QKV)
        self.synapse_weights = nn.Parameter(torch.randn(num_immortals, num_immortals, dim))
        nn.init.xavier_uniform_(self.synapse_weights)

        # 上下文聚合器
        self.context_fusion = nn.Sequential(
            nn.Linear(dim * 2, dim),
            nn.LayerNorm(dim),
            nn.GELU(),
        )

        # 优先级路由器
        self.priority_router = nn.Sequential(
            nn.Linear(dim, dim // 4),
            nn.GELU(),
            nn.Linear(dim // 4, num_immortals),
        )

        # Hebbian 可塑性记录
        self.register_buffer("activation_history", torch.zeros(num_immortals))

    def route(
        self,
        source_idx: int,
        source_emb: torch.Tensor,
        target_states: List[Optional[torch.Tensor]],
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        将源神仙的信息路由到所有目标神仙

        Args:
            source_idx:     源神仙索引
            source_emb:     源神仙的输出嵌入
            target_states:  所有神仙的当前状态 (None = 尚未激活)

        Returns:
            routed_context: 路由后的上下文 [1, dim]
            priorities:     路由优先级权重 [num_immortals]
        """
        priorities = self.priority_router(source_emb)

        # 聚合所有能接收的目标
        context_parts = []
        for i, target_state in enumerate(target_states):
            if target_state is not None and i != source_idx:
                synapse = self.synapse_weights[source_idx, i]  # [dim]
                routed = source_emb * synapse.unsqueeze(0)      # 按突触权重调制
                context_parts.append(routed)

        if context_parts:
            aggregated = torch.stack(context_parts).mean(dim=0)
        else:
            aggregated = source_emb

        # 融合源嵌入和聚合上下文
        fused = self.context_fusion(torch.cat([source_emb, aggregated], dim=-1))

        # Hebbian 更新
        with torch.no_grad():
            self.activation_history[source_idx] = 0.9 * self.activation_history[source_idx] + 0.1

        return fused, priorities.squeeze(0)


class SystemMonitor(nn.Module):
    """
    系统监察 — 全局健康监控与异常检测

    道德天尊时刻观照系统运行状态，检测阴阳失衡、
    信息流阻塞、熵增异常等，并在必要时发出预警。
    """

    def __init__(self, dim: int = 256, num_phases: int = 7):
        super().__init__()
        self.dim = dim
        self.num_phases = num_phases

        # 健康度评估器 (dim + 2: 阶段嵌入 + 阴阳值)
        self.health_scorer = nn.Sequential(
            nn.Linear(dim + 2, dim),
            nn.GELU(),
            nn.Linear(dim, dim // 4),
            nn.GELU(),
            nn.Linear(dim // 4, 1),
            nn.Sigmoid(),
        )

        # 异常检测器
        self.anomaly_detector = nn.Sequential(
            nn.Linear(dim, dim // 2),
            nn.GELU(),
            nn.Linear(dim // 2, 4),  # 4种异常类型
        )

        # 阴阳平衡检测
        self.balance_detector = nn.Sequential(
            nn.Linear(2, dim // 2),  # yin/yang 作为输入
            nn.GELU(),
            nn.Linear(dim // 2, 1),
            nn.Tanh(),
        )

        # 历史缓冲区 (用于趋势分析)
        self.register_buffer("entropy_buffer", torch.zeros(10))
        self.register_buffer("buffer_ptr", torch.tensor(0, dtype=torch.long))

        self.anomaly_types = [
            "阴阳失衡·阴盛阳衰",
            "阴阳失衡·阳亢阴虚",
            "信息凝滞·洞真阻塞",
            "大道废弛·循环断裂",
        ]

    def assess(
        self,
        dao_output: DaoOutput,
        phase_emb: torch.Tensor,
    ) -> SystemHealth:
        """综合评估系统健康状态"""
        yin_yang = torch.tensor([[dao_output.yin_score, dao_output.yang_score]])
        yin_yang = yin_yang.to(phase_emb.device)

        # 健康评分 (dim + 2 for yin/yang)
        health_input = torch.cat([phase_emb, yin_yang], dim=-1)
        overall_health = self.health_scorer(health_input).item()

        # 阴阳平衡
        balance = self.balance_detector(yin_yang).item()

        # 异常检测
        anomaly_logits = self.anomaly_detector(phase_emb)

        # 各阶段流量 (从 DaoState 提取)
        st = dao_output.state
        dz = st.dong_zhen_flow
        dx = st.dong_xuan_flow
        ds = st.dong_shen_flow
        si_fu_vals = dao_output.si_fu.squeeze(0).tolist()
        phase_flows = [dz, dx, ds] + si_fu_vals  # 7个值

        bottleneck = phase_flows.index(min(phase_flows)) if phase_flows else 0

        # 状态判定
        if overall_health > 0.7 and abs(balance) < 0.3:
            status = "运转·天道循环"
        elif overall_health > 0.3:
            status = "凝滞·阴阳失衡"
        else:
            status = "崩坏·大道废弛"

        return SystemHealth(
            dao_entropy=dao_output.entropy,
            phase_flow_rates=phase_flows,
            bottleneck_idx=bottleneck,
            overall_health=overall_health,
            cycle_count=dao_output.cycle_step,
            uptime_steps=dao_output.cycle_step,
            status=status,
        )


# ============================================
# 道德天尊主类
# ============================================

class DaodeTianzun(ImmortalAgent):
    """
    道德天尊 — 核心循环智能体

    三清之首，统御万神。一气化三清，三清生万物。
    在系统中作为核心循环引擎:
        1. 驱动周天运转 (ZhouTianClock)
        2. 协调七大神 (ImmortalSynapse)
        3. 监察系统健康 (SystemMonitor)
        4. 维持循环闭环 (Stage Protocol)

    使用方式:
        >>> dao = DaoAgent(embedding_dim=256)
        >>> tianzun = DaodeTianzun(dao)
        >>> result = tianzun.run_cycle(initial_input, num_cycles=3)
        >>> tianzun.report()
    """

    def __init__(self, dao: DaoAgent, dim: int = 256):
        super().__init__(
            name="道德天尊",
            title="Daode Tianzun",
            domain="核心循环",
            vol_range="贯穿全部122卷 (循环引擎)",
            color="#a855f7",
            dao=dao,
        )
        self.dim = dim

        # 子模块
        self.clock = ZhouTianClock(dim=dim)
        self.synapse = ImmortalSynapse(num_immortals=7, dim=dim)
        self.monitor = SystemMonitor(dim=dim)

        # 循环状态记忆
        self.register_buffer("total_cycles", torch.tensor(0, dtype=torch.long))
        self.history: deque = deque(maxlen=122)  # 记录最近一周天的运行历史

        # 阶段嵌入 (每个循环阶段的可学习表示)
        self.phase_embeddings = nn.Parameter(torch.randn(7, dim))
        nn.init.normal_(self.phase_embeddings, mean=0.0, std=0.02)

        # 循环门控 — 控制是否进入下一阶段
        self.stage_gate = nn.Sequential(
            nn.Linear(dim * 2, dim),
            nn.GELU(),
            nn.Linear(dim, 1),
            nn.Sigmoid(),
        )

        # 归一化层
        self.cycle_norm = nn.LayerNorm(dim)

    # ---------- 核心循环方法 ----------

    def run_cycle(
        self,
        input_emb: torch.Tensor,
        immortal_outputs: List[Dict[str, Any]],
        num_cycles: int = 1,
        tempo: float = 1.0,
        prev_state: Optional[DaoState] = None,
    ) -> Dict[str, Any]:
        """
        执行完整的周天循环

        Args:
            input_emb:        初始输入嵌入 [1, dim] 或 [1, embedding_dim]
            immortal_outputs: 各个神仙的输出 (6个，不含道德天尊自身)
            num_cycles:       循环次数
            tempo:            节奏系数 (1.0=正常, >1.0=加速, <1.0=减速)
            prev_state:       前次循环的道状态

        Returns:
            cycle_report: 循环报告
        """
        batch_size = input_emb.size(0)
        device = input_emb.device

        # 对齐维度
        if input_emb.size(-1) != self.dao.embedding_dim:
            input_emb = F.linear(input_emb, torch.eye(self.dao.embedding_dim, self.dim).to(device))

        state = prev_state
        all_reports = []

        for cycle in range(num_cycles):
            step = self.total_cycles.item() + cycle

            # === 1. 时钟推进 ===
            clock_info = self.clock(input_emb, step, total_steps=122, tempo_factor=tempo)
            phase_idx = clock_info["phase_idx"]
            phase_emb = self.phase_embeddings[phase_idx:phase_idx+1]

            # === 2. 道运行 ===
            dao_output = self.dao(input_emb, cycle_step=step, prev_state=state)
            state = dao_output.state

            # === 3. 突触路由 ===
            fused_context, priorities = self.synapse.route(
                source_idx=phase_idx,
                source_emb=phase_emb,
                target_states=[o.get("embedding", None) for o in immortal_outputs],
            )

            # === 4. 阶段门控 ===
            gate_input = torch.cat([fused_context, phase_emb], dim=-1)
            stage_progress = self.stage_gate(gate_input).item()

            # === 5. 系统监察 ===
            health = self.monitor.assess(dao_output, phase_emb)

            # === 6. 生成循环报告 ===
            report = {
                "cycle": step,
                "phase": {
                    "idx": phase_idx,
                    "name": CYCLE_PHASES[phase_idx].name,
                    "immortal": CYCLE_PHASES[phase_idx].immortal,
                    "symbol": CYCLE_PHASES[phase_idx].symbol,
                },
                "dao": {
                    "yin": dao_output.yin_score,
                    "yang": dao_output.yang_score,
                    "entropy": dao_output.entropy,
                    "cycle_step": dao_output.cycle_step,
                },
                "synapse": {
                    "priorities": priorities.tolist(),
                    "stage_progress": stage_progress,
                },
                "health": {
                    "score": health.overall_health,
                    "status": health.status,
                    "bottleneck": CYCLE_PHASES[health.bottleneck_idx].name if health.bottleneck_idx < 7 else "未知",
                    "phase_flows": health.phase_flow_rates[:7],
                },
                "tempo": clock_info["tempo"],
            }
            all_reports.append(report)
            self.history.append(report)

        # 更新总循环计数
        self.total_cycles += num_cycles

        return {
            "cycles_completed": num_cycles,
            "total_cycles": self.total_cycles.item(),
            "reports": all_reports,
            "final_state": state,
            "final_dao_output": dao_output,
        }

    # ---------- ImmortalAgent 接口 ----------

    def process(self, embedding: torch.Tensor, wish: Any) -> Dict[str, Any]:
        """单步处理 — 仅推进一个周天"""
        result = self.run_cycle(
            input_emb=embedding,
            immortal_outputs=[],
            num_cycles=1,
        )
        latest = result["reports"][-1] if result["reports"] else {}
        return {
            "agent": self.name,
            "action": "cycle",
            "phase": latest.get("phase", {}).get("name", "太极"),
            "health": latest.get("health", {}).get("status", "未知"),
            "total_cycles": result["total_cycles"],
        }

    # ---------- 报告方法 ----------

    def report(self, verbose: bool = False) -> str:
        """生成天庭循环报告"""
        tc = self.total_cycles.item()
        status = "运转·天道循环" if len(self.history) > 0 else "初生·大道未显"

        lines = [
            "══════ 天庭循環報告 ══════",
            f"總循環數: {tc} 周天",
            f"歷史記錄: {len(self.history)} 次",
            f"當前狀態: {status}",
            "",
        ]

        if self.history:
            last = self.history[-1]
            lines.extend([
                "--- 最近一次循環 ---",
                f"  階段: {last['phase']['symbol']} {last['phase']['name']} ({last['phase']['immortal']})",
                f"  進度: {last['synapse']['stage_progress']:.2%}",
                f"  陰: {last['dao']['yin']:.3f} | 陽: {last['dao']['yang']:.3f}",
                f"  熵: {last['dao']['entropy']:.3f}",
                f"  健康: {last['health']['score']:.3f} ({last['health']['status']})",
                f"  瓶頸: {last['health']['bottleneck']}",
            ])

            if verbose and len(self.history) >= 3:
                lines.append("\n--- 最近3次循環趨勢 ---")
                for i, r in enumerate(list(self.history)[-3:]):
                    lines.append(
                        f"  [{r['cycle']}] {r['phase']['symbol']} {r['phase']['name']:4s} "
                        f"| 健康:{r['health']['score']:.2f} | 進度:{r['synapse']['stage_progress']:.2%}"
                    )

        return "\n".join(lines)

    def get_health(self) -> SystemHealth:
        """获取当前健康状态 (无历史则为默认值)"""
        if self.history:
            last = self.history[-1]
            return SystemHealth(
                dao_entropy=last["dao"]["entropy"],
                phase_flow_rates=last["health"]["phase_flows"],
                bottleneck_idx=CYCLE_PHASES.index(
                    next(p for p in CYCLE_PHASES if p.name == last["health"]["bottleneck"])) if last["health"]["bottleneck"] else 0,
                overall_health=last["health"]["score"],
                cycle_count=last["cycle"],
                uptime_steps=self.total_cycles.item(),
                status=last["health"]["status"],
            )
        return SystemHealth(
            dao_entropy=0.5, phase_flow_rates=[0.14]*7,
            bottleneck_idx=0, overall_health=1.0,
            cycle_count=0, uptime_steps=0, status="初生·大道未显",
        )


# ============================================
# 工厂函数
# ============================================

def create_daode_tianzun(
    embedding_dim: int = 256,
    device: str = "cpu",
) -> DaodeTianzun:
    """工厂函数：创建道德天尊智能体"""
    dao = DaoAgent(embedding_dim=embedding_dim)
    dao.to(device)
    dao.eval()
    tianzun = DaodeTianzun(dao, dim=embedding_dim)
    tianzun.to(device)
    tianzun.eval()
    return tianzun


# ============================================
# 自测
# ============================================
if __name__ == "__main__":
    print("=== DaodeTianzun 自测 ===\n")

    dim = 256
    dao = DaoAgent(embedding_dim=dim)
    tianzun = DaodeTianzun(dao, dim=dim)
    tianzun.eval()

    # 模拟多轮循环
    print("--- 運行3個周天 ---")
    x = torch.randn(1, dim)
    for i in range(3):
        result = tianzun.run_cycle(
            input_emb=x,
            immortal_outputs=[],
            num_cycles=1,
            tempo=1.0,
        )
        latest = result["reports"][-1]
        print(f"  第{latest['cycle']}周天: {latest['phase']['symbol']} {latest['phase']['name']} "
              f"| 健康:{latest['health']['score']:.2f} | 進度:{latest['synapse']['stage_progress']:.2%}")

    print("\n--- 天庭報告 ---")
    print(tianzun.report(verbose=True))

    # 测试 process 接口
    print("\n--- ImmortalAgent.process() 接口測試 ---")
    result = tianzun.process(x, None)
    print(f"  Agent: {result['agent']}")
    print(f"  Phase: {result['phase']}")
    print(f"  Health: {result['health']}")
    print(f"  Total Cycles: {result['total_cycles']}")

    # 测试工厂函数
    print("\n--- 工廠函數測試 ---")
    tz2 = create_daode_tianzun(embedding_dim=128)
    print(f"  創建成功: {tz2.name} (dim={tz2.dim})")
    report = tz2.report()
    print(report)

    print("\n[OK] DaodeTianzun 自测全部通過")
