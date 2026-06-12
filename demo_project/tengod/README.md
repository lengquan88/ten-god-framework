# DemoApp — 十神架构

> 由 init_tengod.py 初始化 @ 2026-06-11T18:50:46

## 目录结构

```
tengod/
├── 比肩_架构协同/    # 核心编排/入口点
├── 劫财_攻防边界/    # 安全防护/权限校验
├── 食神_创生输出/    # 内容生成/LLM调用
├── 伤官_破界创新/    # 因果推理/模型训练
├── 正财_知识固化/    # 数据存储/知识图谱
├── 偏财_奇招演化/    # 搜索优化/算法调参
├── 正官_法度调度/    # API服务/任务调度
├── 七杀_品质裁决/    # 测试评估/质量监控
├── 正印_滋养守护/    # 配置管理/环境初始化
└── 偏印_桥接通变/    # 桥接适配/协议转换
```

## 快速开始

```bash
# 扫描项目
python tengod_scan.py

# 导出JSON报告
python tengod_scan.py --json

# 查看初始化报告
cat tengod_init_report.json
```

## 关键词映射

在 `tengod_scan.py` 中的 `GODS` 字典中自定义关键词映射。

## 进阶工具

从 [Claw 项目](https://github.com/your-org/claw) 复制进阶引擎:
- `tengod_omni_map.py` — 全知地图
- `tengod_auto_healer.py` — 自愈引擎
- `fix_all_chains.py` — 一键修复
- `shenke_daemon.py` — 守护进程
- `shenke_optimizer.py` — 优化智能体
- `tengod_causal.py` — 因果历史
- `tengod_doctrine.py` — 道标系统
