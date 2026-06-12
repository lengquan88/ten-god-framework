"""
核心道智能体 DaoAgent
================================
在系统中扮演"道"的角色，执行最底层的循环逻辑。

架构:
    1. 阴阳门控 (Yin-Yang Gate) — 调节输入信号的阴阳平衡
    2. 循环引擎 (Zhou Tian LSTM) — 模拟周天运行，维持系统时序状态
    3. 三洞分流 (Three Grottoes Encoder) — 将知识分流至洞真/洞玄/洞神
    4. 四辅门控 (Four Supplements Gate) — 路由至太玄/太平/太清/正一

数学表述:
    道生一: x → Embedding
    一生二: x → [yin_score, yang_score]
    二生三: balanced → [dong_zhen, dong_xuan, dong_shen]
    三生万物: combined → si_fu routing
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, Tuple, Optional
from dataclasses import dataclass
import math


@dataclass
class DaoState:
    """道的内部状态 — 跨时间步传递的隐变量"""
    hidden: torch.Tensor      # LSTM hidden state
    cell: torch.Tensor        # LSTM cell state
    cycle_step: int           # 当前周天数
    yin_balance: float        # 阴平衡系数
    yang_balance: float       # 阳平衡系数
    dong_zhen_flow: float     # 洞真信息流量
    dong_xuan_flow: float     # 洞玄信息流量
    dong_shen_flow: float     # 洞神信息流量


@dataclass
class DaoOutput:
    """道处理后的输出"""
    dong_zhen: torch.Tensor       # 洞真向量 (核心教义)
    dong_xuan: torch.Tensor       # 洞玄向量 (法术仪式)
    dong_shen: torch.Tensor       # 洞神向量 (神仙谱系)
    si_fu: torch.Tensor           # 四辅路由权重 [太玄, 太平, 太清, 正一]
    yin_score: float              # 阴分
    yang_score: float             # 阳分
    cycle_step: int               # 当前周天
    entropy: float                # 系统熵 (信息不确定性)
    state: DaoState               # 内部状态 (供下次调用)


class YinYangGate(nn.Module):
    """
    阴阳门控模块
    -----------------
    将输入信号分解为阴阳两个维度:
        yin  = sigmoid(W_yin · x)   — 接收、收敛、内化
        yang = sigmoid(W_yang · x)  — 发散、表达、外化

    平衡公式: x_balanced = x * yin + x * yang
    当 yin ≈ yang ≈ 0.5 时，系统处于"太极"状态。
    """
    def __init__(self, dim: int):
        super().__init__()
        self.yin_proj = nn.Sequential(
            nn.Linear(dim, dim // 2),
            nn.LayerNorm(dim // 2),
            nn.GELU(),
            nn.Linear(dim // 2, 1),
        )
        self.yang_proj = nn.Sequential(
            nn.Linear(dim, dim // 2),
            nn.LayerNorm(dim // 2),
            nn.GELU(),
            nn.Linear(dim // 2, 1),
        )

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Args:
            x: [batch, dim] 输入嵌入
        Returns:
            yin_score:  [batch, 1] 阴门控值
            yang_score: [batch, 1] 阳门控值
            balanced:   [batch, dim] 阴阳平衡后的表示
        """
        yin = torch.sigmoid(self.yin_proj(x))
        yang = torch.sigmoid(self.yang_proj(x))
        balanced = x * yin + x * yang
        return yin, yang, balanced


class ThreeGrottoesEncoder(nn.Module):
    """
    三洞编码器
    ----------
    将经过阴阳平衡的表示分流至三个知识领域:
        - 洞真 (True Grotto):  核心教义、宇宙观、哲学思辨  → 紫色
        - 洞玄 (Mysterious):   法术、仪式、金丹、符箓    → 蓝色
        - 洞神 (Spiritual):    神仙谱系、传记、灵验故事  → 金色

    每个洞有其独特的编码偏置，模拟不同领域知识的特征空间。
    """
    def __init__(self, dim: int, grotto_dim: Optional[int] = None):
        super().__init__()
        out_dim = grotto_dim or dim // 3

        # 洞真编码器 — 哲学/教义 (深度思辨)
        self.dong_zhen = nn.Sequential(
            nn.Linear(dim, dim),
            nn.LayerNorm(dim),
            nn.GELU(),
            nn.Linear(dim, out_dim),
            nn.LayerNorm(out_dim),
        )

        # 洞玄编码器 — 法术/仪式 (操作规范)
        self.dong_xuan = nn.Sequential(
            nn.Linear(dim, dim),
            nn.LayerNorm(dim),
            nn.GELU(),
            nn.Linear(dim, out_dim),
            nn.LayerNorm(out_dim),
        )

        # 洞神编码器 — 神仙/谱系 (关系网络)
        self.dong_shen = nn.Sequential(
            nn.Linear(dim, dim),
            nn.LayerNorm(dim),
            nn.GELU(),
            nn.Linear(dim, out_dim),
            nn.LayerNorm(out_dim),
        )

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        return self.dong_zhen(x), self.dong_xuan(x), self.dong_shen(x)


class FourSupplementsGate(nn.Module):
    """
    四辅门控路由
    ------------
    将三洞输出与循环状态融合，路由至四个辅助子系统:
        - 太玄 (Supreme Mystery):  系统底层/内核
        - 太平 (Great Peace):      交互/界面/用户体验
        - 太清 (Supreme Clarity):  存储/记忆/持久化
        - 正一 (Right Unity):      用户身份/权限/安全
    """
    def __init__(self, dim: int):
        super().__init__()
        self.fusion = nn.Sequential(
            nn.Linear(dim * 2, dim),
            nn.LayerNorm(dim),
            nn.GELU(),
        )
        self.router = nn.Linear(dim, 4)

    def forward(self, cyclic_out: torch.Tensor, original: torch.Tensor) -> torch.Tensor:
        """
        Args:
            cyclic_out: 经过LSTM循环处理后的表示
            original:   原始输入表示
        Returns:
            si_fu: [batch, 4] 四辅路由权重 (softmax归一化)
        """
        combined = torch.cat([cyclic_out, original], dim=-1)
        fused = self.fusion(combined)
        return F.softmax(self.router(fused), dim=-1)


class DaoAgent(nn.Module):
    """
    核心道智能体 — 系统的"道"层

    设计哲学:
        道者，萬物之奧，善人之寶，不善人之所保。
        此智能體非決策者，而是使決策成為可能的"場"。
        它不回答問題，而是為所有答案提供存在的條件。

    使用方式:
        >>> dao = DaoAgent(embedding_dim=1024)
        >>> x = torch.randn(1, 1024)  # 任意模态嵌入
        >>> output = dao(x, cycle_step=0)
        >>> print(output.dong_zhen.shape)  # torch.Size([1, 341])
    """

    def __init__(
        self,
        embedding_dim: int = 1024,
        grotto_dim: int = 341,
        lstm_layers: int = 3,
        dropout: float = 0.1,
    ):
        """
        Args:
            embedding_dim:  输入嵌入维度 (默认1024)
            grotto_dim:     三洞输出维度 (默认341, ≈1024/3)
            lstm_layers:    周天LSTM层数 (默认3，对应三生万物)
            dropout:        Dropout比率
        """
        super().__init__()
        self.embedding_dim = embedding_dim
        self.grotto_dim = grotto_dim
        self.lstm_layers = lstm_layers

        # 1. 输入归一化
        self.input_norm = nn.LayerNorm(embedding_dim)

        # 2. 阴阳门控
        self.yin_yang = YinYangGate(embedding_dim)

        # 3. 循环引擎 (周天 LSTM)
        #    3层LSTM对应"三" -> "万物"的生成过程
        self.zhou_tian = nn.LSTM(
            input_size=embedding_dim,
            hidden_size=embedding_dim,
            num_layers=lstm_layers,
            batch_first=True,
            dropout=dropout if lstm_layers > 1 else 0,
            bidirectional=False,
        )

        # 4. 循环后归一化
        self.cycle_norm = nn.LayerNorm(embedding_dim)

        # 5. 三洞分流
        self.three_grottoes = ThreeGrottoesEncoder(embedding_dim, grotto_dim)

        # 6. 四辅门控
        self.four_supplements = FourSupplementsGate(embedding_dim)

        # 7. 熵估计器 (系统自我感知)
        self.entropy_estimator = nn.Sequential(
            nn.Linear(embedding_dim, embedding_dim // 4),
            nn.GELU(),
            nn.Linear(embedding_dim // 4, 1),
            nn.Sigmoid(),
        )

        # 初始化权重
        self._init_weights()

    def _init_weights(self):
        """以'道法自然'的方式初始化权重 — 正态分布，小方差"""
        for name, param in self.named_parameters():
            if 'weight' in name and param.dim() >= 2:
                nn.init.orthogonal_(param, gain=math.sqrt(2))
            elif 'weight' in name:
                nn.init.normal_(param, mean=0.0, std=0.02)
            elif 'bias' in name:
                nn.init.zeros_(param)

    def _init_state(self, batch_size: int, device: torch.device) -> DaoState:
        """初始化道的内在状态"""
        h0 = torch.zeros(self.lstm_layers, batch_size, self.embedding_dim, device=device)
        c0 = torch.zeros(self.lstm_layers, batch_size, self.embedding_dim, device=device)
        return DaoState(
            hidden=h0,
            cell=c0,
            cycle_step=0,
            yin_balance=0.5,
            yang_balance=0.5,
            dong_zhen_flow=0.0,
            dong_xuan_flow=0.0,
            dong_shen_flow=0.0,
        )

    def forward(
        self,
        x: torch.Tensor,
        cycle_step: int = 0,
        prev_state: Optional[DaoState] = None,
    ) -> DaoOutput:
        """
        道智能体的前向传播 — 模拟"道生一，一生二，二生三，三生万物"

        Args:
            x:           [batch_size, embedding_dim] 任意模态的嵌入向量
            cycle_step:  当前周天数 (用于追踪系统运行时间)
            prev_state:  前一个时间步的道状态 (None则初始化)

        Returns:
            DaoOutput: 包含三洞分流、四辅路由、阴阳得分、系统熵和内部状态
        """
        batch_size = x.size(0)
        device = x.device

        # 初始化或继承状态
        if prev_state is None:
            state = self._init_state(batch_size, device)
        else:
            state = prev_state

        # === 0. 归一化 ===
        x = self.input_norm(x)

        # === 1. 阴阳调节 (道生一 → 一生二) ===
        yin_score, yang_score, x_balanced = self.yin_yang(x)
        yin_val = yin_score.mean().item()
        yang_val = yang_score.mean().item()

        # === 2. 循环更新 (二生三) ===
        #    将平衡信号送入周天LSTM，模拟"运行一周天"
        cyclic_out, (h_n, c_n) = self.zhou_tian(
            x_balanced.unsqueeze(1),
            (state.hidden, state.cell)
        )
        cyclic_out = self.cycle_norm(cyclic_out.squeeze(1))

        # === 3. 三洞分流 (三生万物) ===
        dong_zhen, dong_xuan, dong_shen = self.three_grottoes(cyclic_out)

        # 计算各洞信息流量 (L2范数)
        dz_flow = dong_zhen.norm(dim=-1).mean().item()
        dx_flow = dong_xuan.norm(dim=-1).mean().item()
        ds_flow = dong_shen.norm(dim=-1).mean().item()

        # === 4. 四辅门控 ===
        si_fu = self.four_supplements(cyclic_out, x_balanced)

        # === 5. 系统熵估计 ===
        entropy = self.entropy_estimator(cyclic_out).mean().item()

        # === 6. 更新状态 ===
        new_state = DaoState(
            hidden=h_n,
            cell=c_n,
            cycle_step=cycle_step + 1,
            yin_balance=yin_val,
            yang_balance=yang_val,
            dong_zhen_flow=dz_flow,
            dong_xuan_flow=dx_flow,
            dong_shen_flow=ds_flow,
        )

        return DaoOutput(
            dong_zhen=dong_zhen,
            dong_xuan=dong_xuan,
            dong_shen=dong_shen,
            si_fu=si_fu,
            yin_score=yin_val,
            yang_score=yang_val,
            cycle_step=cycle_step,
            entropy=entropy,
            state=new_state,
        )

    def get_dao_report(self, output: DaoOutput) -> str:
        """生成'道'的状态报告 (用于UI展示)"""
        grottoes = [
            ("洞真", output.dong_zhen.norm(dim=-1).mean().item(), "#8b5cf6"),
            ("洞玄", output.dong_xuan.norm(dim=-1).mean().item(), "#3b82f6"),
            ("洞神", output.dong_shen.norm(dim=-1).mean().item(), "#f59e0b"),
        ]
        supplements = ["太玄", "太平", "太清", "正一"]

        lines = [
            f"══════ 第{output.cycle_step}周天 · 道運行報告 ══════",
            f"陰: {output.yin_score:.3f} | 陽: {output.yang_score:.3f}",
            f"熵: {output.entropy:.3f}",
            f"--- 三洞分流 ---",
        ]
        for name, flow, _ in grottoes:
            bar = "█" * int(flow * 20)
            lines.append(f"  {name}: {bar} ({flow:.4f})")

        lines.append("--- 四輔路由 ---")
        si_fu_vals = output.si_fu.squeeze(0).tolist()
        for name, val in zip(supplements, si_fu_vals):
            bar = "█" * int(val * 20)
            lines.append(f"  {name}: {bar} ({val:.3f})")

        return "\n".join(lines)


# ===== 便捷函数 =====

def create_dao_agent(
    embedding_dim: int = 1024,
    device: str = "cpu",
) -> DaoAgent:
    """工厂函数：创建并初始化DaoAgent"""
    dao = DaoAgent(embedding_dim=embedding_dim)
    dao.to(device)
    dao.eval()
    return dao


# ===== 自测 =====
if __name__ == "__main__":
    print("=== DaoAgent 自测 ===")
    dao = create_dao_agent(embedding_dim=768)

    # 模拟多步输入 (循环推演)
    x = torch.randn(2, 768)
    state = None

    for step in range(5):
        output = dao(x, cycle_step=step, prev_state=state)
        state = output.state
        print(f"\nStep {step}:")
        print(f"  Yin={output.yin_score:.3f} Yang={output.yang_score:.3f}")
        print(f"  Entropy={output.entropy:.3f}")
        print(f"  DongZhen shape={output.dong_zhen.shape}")
        print(f"  SiFu={output.si_fu.squeeze(0).tolist()}")

    print("\n" + dao.get_dao_report(output))
    print("\n[OK] DaoAgent 自测通过")
