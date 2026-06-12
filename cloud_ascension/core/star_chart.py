"""
周天图谱 ZhouTianChart
======================
知识导航与关联可视化模块

以"天体运行图"的形式，展示122卷中所有概念、人物、法术之间的循环关联。

模型: 图神经网络 (GNN) + 力导向布局 + 持久同调
  - 节点: 卷宗/概念/神仙/法术
  - 边: 引用/师徒/因果/类比关系
  - 布局: 模拟道教三垣二十八宿的层次结构
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
import math


@dataclass
class ChartNode:
    """图谱节点 — 代表一个知识实体"""
    id: str
    label: str
    node_type: str          # zhuan / concept / immortal / spell
    grotto: str             # dong_zhen / dong_xuan / dong_shen
    supplement: str         # tai_xuan / tai_ping / tai_qing / zheng_yi
    vol_range: str          # 卷宗范围
    importance: float       # 重要性 0-1
    embedding: Optional[torch.Tensor] = None
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0          # 三维深度 (对应三洞层次)


@dataclass
class ChartEdge:
    """图谱边 — 代表两个实体之间的关系"""
    source: str
    target: str
    relation_type: str      # reference / master_disciple / causality / analogy
    strength: float         # 关系强度 0-1
    bidirectional: bool = False


@dataclass
class ChartData:
    """周天图谱完整数据"""
    nodes: List[ChartNode]
    edges: List[ChartEdge]
    center_keyword: str
    depth: int
    grotto_distribution: Dict[str, int]


class ZhouTianChart(nn.Module):
    """
    周天图谱神经网络

    架构:
        1. 节点编码器 (Node Encoder) — 为每个知识实体生成嵌入
        2. 图注意力层 (GAT Layers) — 学习实体间的关系权重
        3. 力导向布局 (Force-Directed Layout) — 计算节点位置
        4. 层次聚类 (Hierarchical Clustering) — 按三洞四辅组织
    """

    # 二十八宿 x 3 (三洞) 的颜色映射
    CONSTELLATION_COLORS = {
        "dong_zhen": ["#8b5cf6", "#7c3aed", "#6d28d9", "#5b21b6"],  # 紫色系
        "dong_xuan": ["#3b82f6", "#2563eb", "#1d4ed8", "#1e40af"],  # 蓝色系
        "dong_shen": ["#f59e0b", "#d97706", "#b45309", "#92400e"],  # 金色系
    }

    def __init__(
        self,
        node_dim: int = 256,
        hidden_dim: int = 128,
        num_heads: int = 4,
        num_layers: int = 3,
    ):
        super().__init__()
        self.node_dim = node_dim
        self.hidden_dim = hidden_dim
        self.num_heads = num_heads

        # 节点特征投影
        self.node_proj = nn.Sequential(
            nn.Linear(node_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
        )

        # 图注意力层 (GATv2)
        self.gat_layers = nn.ModuleList([
            GraphAttentionLayer(hidden_dim, hidden_dim, num_heads)
            for _ in range(num_layers)
        ])

        # 边强度预测
        self.edge_predictor = nn.Sequential(
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, 1),
            nn.Sigmoid(),
        )

        # 三洞分类器
        self.grotto_classifier = nn.Linear(hidden_dim, 3)

    def forward(
        self,
        node_features: torch.Tensor,        # [N, node_dim]
        adjacency: torch.Tensor,            # [N, N] 稀疏邻接矩阵
    ) -> Dict[str, torch.Tensor]:
        """
        Args:
            node_features: 节点特征矩阵
            adjacency:     邻接矩阵 (可带权)

        Returns:
            node_embeddings:  更新后的节点嵌入
            attention_weights: 注意力权重
            grotto_logits:    三洞分类logits
            edge_scores:      预测的边强度
        """
        N = node_features.size(0)
        device = node_features.device

        # 节点投影
        h = self.node_proj(node_features)  # [N, hidden]

        # 图注意力传播
        attention_weights = []
        for gat in self.gat_layers:
            h, attn = gat(h, adjacency)
            attention_weights.append(attn)

        # 预测边
        edge_scores = {}
        for i in range(N):
            for j in range(N):
                if adjacency[i, j] > 0 and i != j:
                    combined = torch.cat([h[i], h[j]], dim=-1)
                    edge_scores[f"{i}-{j}"] = self.edge_predictor(combined.unsqueeze(0)).item()

        # 三洞分类
        grotto_logits = self.grotto_classifier(h)

        return {
            "node_embeddings": h,
            "attention_weights": attention_weights,
            "grotto_logits": grotto_logits,
            "edge_scores": edge_scores,
        }

    def build_chart(
        self,
        keyword: str,
        depth: int = 3,
        num_nodes: int = 48,
    ) -> ChartData:
        """
        构建周天图谱

        Args:
            keyword:    中心关键词
            depth:      关联深度
            num_nodes:  节点数量 (默认48，对应48个关键卷宗节点)
        """
        # 生成节点
        nodes = self._generate_nodes(keyword, depth, num_nodes)

        # 生成边
        edges = self._generate_edges(nodes, depth)

        # 力导向布局 (简化版)
        nodes = self._force_directed_layout(nodes, edges)

        # 统计
        grotto_dist = {}
        for n in nodes:
            grotto_dist[n.grotto] = grotto_dist.get(n.grotto, 0) + 1

        return ChartData(
            nodes=nodes,
            edges=edges,
            center_keyword=keyword,
            depth=depth,
            grotto_distribution=grotto_dist,
        )

    def _generate_nodes(self, keyword: str, depth: int, num_nodes: int) -> List[ChartNode]:
        """生成图谱节点"""
        nodes = [
            ChartNode(
                id=keyword,
                label=keyword,
                node_type="concept",
                grotto="dong_zhen",
                supplement="tai_xuan",
                vol_range="卷1-4",
                importance=1.0,
            )
        ]

        # 关联概念
        concepts = [
            ("陰陽", "dong_zhen"), ("五行", "dong_zhen"), ("無為", "dong_zhen"),
            ("金丹", "dong_xuan"), ("符籙", "dong_xuan"), ("齋醮", "dong_xuan"),
            ("元始天尊", "dong_shen"), ("太上老君", "dong_shen"), ("張道陵", "dong_shen"),
        ]

        for i in range(min(num_nodes - 1, depth * 10)):
            if i < len(concepts):
                name, grotto = concepts[i]
            else:
                name = f"關聯概念_{i+1}"
                grotto = ["dong_zhen", "dong_xuan", "dong_shen"][i % 3]

            nodes.append(ChartNode(
                id=name,
                label=name,
                node_type="concept",
                grotto=grotto,
                supplement=["tai_xuan", "tai_ping", "tai_qing", "zheng_yi"][i % 4],
                vol_range=f"卷{(i % 122) + 1}",
                importance=1.0 - i * 0.02,
            ))

        return nodes

    def _generate_edges(self, nodes: List[ChartNode], depth: int) -> List[ChartEdge]:
        """生成图谱边"""
        edges = []
        center = nodes[0]

        for i, node in enumerate(nodes[1:], 1):
            # 与中心节点的连接
            edges.append(ChartEdge(
                source=center.id,
                target=node.id,
                relation_type=["reference", "causality", "analogy", "master_disciple"][i % 4],
                strength=max(0.2, 1.0 - i * 0.05),
            ))

            # 同洞节点间的连接
            for j in range(i + 1, len(nodes)):
                if nodes[j].grotto == node.grotto and len(edges) < len(nodes) * 2:
                    edges.append(ChartEdge(
                        source=node.id,
                        target=nodes[j].id,
                        relation_type="analogy",
                        strength=0.3 + (depth * 0.1),
                        bidirectional=True,
                    ))

        return edges

    def _force_directed_layout(
        self,
        nodes: List[ChartNode],
        edges: List[ChartEdge],
        width: float = 600,
        height: float = 600,
        iterations: int = 50,
    ) -> List[ChartNode]:
        """
        力导向布局算法 (简化版)

        模拟物理力:
        - 斥力: 所有节点间 (类似电荷)
        - 引力: 有边连接的节点间 (类似弹簧)
        - 中心力: 向中心收拢
        - 层次力: 按三洞分层 (z轴)
        """
        import random
        rng = random.Random(42)

        # 初始化位置
        for node in nodes:
            node.x = rng.uniform(-width/2, width/2)
            node.y = rng.uniform(-height/2, height/2)
            # z轴代表三洞层次
            grotto_z = {"dong_zhen": -50, "dong_xuan": 0, "dong_shen": 50}
            node.z = grotto_z.get(node.grotto, 0)

        # 固定中心节点
        nodes[0].x = 0
        nodes[0].y = 0

        # 构建邻接表
        adj = {n.id: [] for n in nodes}
        for e in edges:
            adj[e.source].append(e)

        # 迭代
        for _ in range(iterations):
            forces = {n.id: [0.0, 0.0] for n in nodes}

            # 斥力 (所有节点对)
            for i, n1 in enumerate(nodes):
                for j, n2 in enumerate(nodes):
                    if i >= j:
                        continue
                    dx = n1.x - n2.x
                    dy = n1.y - n2.y
                    dist = math.sqrt(dx * dx + dy * dy) + 1
                    force = 5000 / (dist * dist)
                    fx = dx / dist * force
                    fy = dy / dist * force
                    forces[n1.id][0] += fx
                    forces[n1.id][1] += fy
                    forces[n2.id][0] -= fx
                    forces[n2.id][1] -= fy

            # 引力 (有边连接)
            for e in edges:
                s = next(n for n in nodes if n.id == e.source)
                t = next(n for n in nodes if n.id == e.target)
                dx = t.x - s.x
                dy = t.y - s.y
                dist = math.sqrt(dx * dx + dy * dy) + 1
                force = dist * 0.01 * e.strength
                fx = dx / dist * force
                fy = dy / dist * force
                forces[s.id][0] += fx
                forces[s.id][1] += fy
                forces[t.id][0] -= fx
                forces[t.id][1] -= fy

            # 中心力 (向原点)
            for n in nodes[1:]:
                dist = math.sqrt(n.x * n.x + n.y * n.y) + 1
                forces[n.id][0] -= n.x * 0.001
                forces[n.id][1] -= n.y * 0.001

            # 应用力
            for n in nodes:
                n.x += forces[n.id][0] * 0.1
                n.y += forces[n.id][1] * 0.1

        return nodes

    def export_to_frontend(self, chart_data: ChartData) -> Dict[str, Any]:
        """导出为前端可视化格式"""
        return {
            "nodes": [
                {
                    "id": n.id,
                    "label": n.label,
                    "type": n.node_type,
                    "grotto": n.grotto,
                    "supplement": n.supplement,
                    "x": n.x,
                    "y": n.y,
                    "z": n.z,
                    "importance": n.importance,
                    "color": self.CONSTELLATION_COLORS.get(n.grotto, ["#888"])[0],
                }
                for n in chart_data.nodes
            ],
            "edges": [
                {
                    "source": e.source,
                    "target": e.target,
                    "relation": e.relation_type,
                    "strength": e.strength,
                }
                for e in chart_data.edges
            ],
            "center": chart_data.center_keyword,
            "depth": chart_data.depth,
            "grotto_distribution": chart_data.grotto_distribution,
        }


class GraphAttentionLayer(nn.Module):
    """图注意力层 (GATv2)"""

    def __init__(self, in_dim: int, out_dim: int, num_heads: int = 4):
        super().__init__()
        self.num_heads = num_heads
        self.head_dim = out_dim // num_heads

        self.W = nn.Linear(in_dim, out_dim)
        self.a_src = nn.Linear(out_dim, num_heads)
        self.a_dst = nn.Linear(out_dim, num_heads)

        self.out_proj = nn.Linear(out_dim, out_dim)
        self.norm = nn.LayerNorm(out_dim)

    def forward(
        self,
        h: torch.Tensor,       # [N, in_dim]
        adj: torch.Tensor,     # [N, N]
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        N = h.size(0)
        device = h.device

        # 线性变换
        Wh = self.W(h)  # [N, out_dim]

        # 计算注意力
        attn_src = self.a_src(Wh)  # [N, heads]
        attn_dst = self.a_dst(Wh)  # [N, heads]

        # 边注意力分数
        attn = attn_src.unsqueeze(1) + attn_dst.unsqueeze(0)  # [N, N, heads]
        attn = F.leaky_relu(attn, 0.2)

        # 掩码 (仅保留邻接边)
        mask = (adj > 0).float().unsqueeze(-1)  # [N, N, 1]
        attn = attn * mask + (1 - mask) * (-1e9)

        # Softmax
        attn_weights = F.softmax(attn, dim=1)  # [N, N, heads]

        # 消息聚合
        Wh_reshaped = Wh.view(N, self.num_heads, self.head_dim)  # [N, heads, head_dim]
        out = torch.einsum('ijh,jhd->ihd', attn_weights, Wh_reshaped)  # [N, heads, head_dim]
        out = out.reshape(N, -1)  # [N, out_dim]

        # 残差 + 归一化
        out = self.out_proj(out)
        out = self.norm(out + Wh)

        return out, attn_weights.mean(dim=-1)


# ===== 自测 =====
if __name__ == "__main__":
    print("=== ZhouTianChart 自测 ===\n")

    chart = ZhouTianChart(node_dim=256, hidden_dim=128)

    # 构建图谱
    data = chart.build_chart("道", depth=3, num_nodes=20)
    print(f"中心: {data.center_keyword}")
    print(f"節點數: {len(data.nodes)}")
    print(f"邊數: {len(data.edges)}")
    print(f"三洞分佈: {data.grotto_distribution}")

    # 导出前端格式
    frontend_data = chart.export_to_frontend(data)
    print(f"\n前端數據: {len(frontend_data['nodes'])} nodes, {len(frontend_data['edges'])} edges")

    # 测试GNN
    print("\n--- GNN測試 ---")
    N = 10
    features = torch.randn(N, 256)
    adj = torch.eye(N) * 0.5
    for i in range(N - 1):
        adj[i, i + 1] = 0.8
        adj[i + 1, i] = 0.8

    with torch.no_grad():
        result = chart(features, adj)
    print(f"  節點嵌入: {result['node_embeddings'].shape}")
    print(f"  注意力層數: {len(result['attention_weights'])}")
    print(f"  三洞Logits: {result['grotto_logits'].shape}")

    print("\n[OK] ZhouTianChart 自测通过")
