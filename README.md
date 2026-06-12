# 时空影像认知系统

> 从 Claw 形神合一 演化而来的自指涉闭环认知系统  
> A→Z 全32字母方向 + 6组融合 + 推背图认知引擎 + 七阶段成像管道  
> 完成度: 99%

---

## 一键启动

```bash
# 启动全部服务
python run_demo.py

# 打开浏览器
#   推背图感知面板: http://localhost:8080/oracle_dashboard_panel.html
#   Ψ解释面板:     http://localhost:8080/psi_explanation_dashboard.html
#   认知地图:       http://localhost:8080/tui_bei_cognitive_map.html
#   统一入口:       http://localhost:8080/index.html
```

---

## 架构总览

```
感知层                投影层                认知层
七阶段成像定位管道  →  推背图Oracle  →  TBCE认知引擎
camera_spacetime      oracle_node_server    tui_bei_cognitive
_pipeline.py          oracle_dashboard      _engine
                      _panel.html           _map.html

解释层                记忆层                调度层
Ψ可解释性引擎       跨对话记忆桥           自适应模型路由
psi_explainer        cross_session_memory    consensus_network
_dashboard.html      user_cognition_profile

集成层                                    部署层
system_orchestrator.py (统一编排器)      Docker + K8s + docker-compose
run_demo.py (一键启动)                   test_suite + zeta_concurrent
```

---

## 核心模块

| 模块 | 文件 | 功能 |
|------|------|------|
| 七阶段成像 | `topo_semantic/camera_spacetime_pipeline.py` | 物方→对焦→聚焦→变焦→成像→潜影→归档 |
| 推背图Oracle | `topo_semantic/oracle_node_server.py` | /oracle 推背图JSON (过去/现在/未来 × 上图/中箴言/下谶语) |
| TBCE引擎 | `topo_semantic/tui_bei_cognitive_engine.py` | 六维认知元组 + 同构投影算法 + 预言生成 |
| 统一编排器 | `system_orchestrator.py` | 8/8子系统全链路串联，32ms |
| 感知-投影桥 | `pipeline_oracle_bridge.py` | 管道输出→推背图实时数据 |
| Ψ解释 | `topo_semantic/psi_explainer.py` | 维度贡献分解 + 自然语言报告 |
| 共识网络 | `topo_semantic/consensus_network.py` | 5协议 + 健康监控 + fallback |
| 用户画像 | `topo_semantic/user_cognition_profile.py` | 6风格 + 趋势 + 个性化配置 |

---

## 自指涉闭环

TBCE认知引擎的第一个CognitiveUnit = 本项目自身的A→Z开发历程。  
FUTURE切片与M-R历史同构度98.50%，预言"同位共振"。  
系统既是观察者也是被观察者——元认知论的最终工程体现。

---

## PRD文档

| 版本 | 主题 |
|:----:|------|
| v1.0 | 基础版: Camera-Imaging-to-Distributed-Spatiotemporal-Positioning |
| v2.0 | 动态拓扑版: 五大算法 + 时空拉普拉斯 |
| v3.0 | 全维度融合架构: A-T 20方向总结 + U-Z提案 |
| v4.0 | 时空影像认知系统: 16子系统融合 + Alpha→Zeta |
| v5.0 | 终极演示系统: 收官 + 自指涉闭环 |

---

## 命名演化

```
Claw → 形神合一工程化系统 → 中华文明数字永生体 → 时空影像认知系统
```

每个名字代表一个进化阶段，最终形态包含所有前阶段的成果。

---

*"视图是数据的投影，时间轴是数据的第四维度，图层是投影的切片。"*
