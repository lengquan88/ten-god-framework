"""
module_registry.py — 物方空间模块注册表 v2.21.0
================================================
道曰："有名万物之母。"

全量注册所有tengod模块到物方空间。
每个模块自动生成TBCE六维坐标，并分配认知层和Ψ算子。

注册策略：
- 骨架版（自动生成）：基于静态分析（代码行数/依赖/测试覆盖）自动生成坐标
- 精确版（手动精调）：关键模块手动调整坐标，确保语义准确性
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import time

from .object_space import (
    ObjectSpaceManager,
    OntologyJudge,
    get_object_space,
)
from .tbce_unit import TBCECoordinates, CognitiveUnit, GateState


# ============================================================================
# 模块注册表 —— 骨架版（自动生成）
# ============================================================================

# 所有模块的静态信息，由代码扫描自动生成
# 格式: {name, module_path, lines_of_code, dependency_count, is_core, has_tests, test_coverage}

TENGOD_MODULES: List[Dict[str, Any]] = [
    # ── 核心引擎层（L1-L4）──────────────────────────────
    {
        "name": "core",
        "module_path": "tengod.core",
        "lines_of_code": 800,
        "dependency_count": 8,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.90,
        "psi_operator": "EmbeddingProvider",
        "palace_id": 5,  # 中五
        "tense": "present",
        "description": "十神框架核心引擎，定义基础数据结构与顶层调度",
        "consensus_layer": 3,  # L3 专家路由
    },
    {
        "name": "bazi_calculator",
        "module_path": "tengod.bazi_calculator",
        "lines_of_code": 600,
        "dependency_count": 5,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.95,
        "psi_operator": "EmbeddingProvider",
        "palace_id": 1,  # 坎一
        "tense": "present",
        "description": "八字计算引擎，日柱/时柱/节气精确计算",
        "consensus_layer": 3,
    },
    {
        "name": "bazi_analyzer",
        "module_path": "tengod.bazi_analyzer",
        "lines_of_code": 500,
        "dependency_count": 6,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.90,
        "psi_operator": "Tortuosity",
        "palace_id": 6,  # 乾六
        "tense": "present",
        "description": "八字分析引擎，十神/格局/用神分析",
        "consensus_layer": 3,
    },
    {
        "name": "dayun_liunian",
        "module_path": "tengod.dayun_liunian",
        "lines_of_code": 400,
        "dependency_count": 4,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.88,
        "psi_operator": "Tortuosity",
        "palace_id": None,
        "tense": "present",
        "description": "大运流年推演引擎",
    },
    {
        "name": "geju_engine",
        "module_path": "tengod.geju_engine",
        "lines_of_code": 350,
        "dependency_count": 5,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.85,
        "psi_operator": "PersistenceDiagram",
        "palace_id": None,
        "tense": "present",
        "description": "格局分析引擎，正格/变格/特殊格局",
    },
    {
        "name": "shensha_engine",
        "module_path": "tengod.shensha_engine",
        "lines_of_code": 300,
        "dependency_count": 3,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.85,
        "psi_operator": "PersistenceDiagram",
        "palace_id": None,
        "tense": "present",
        "description": "神煞引擎，天乙/桃花/驿马/空亡等",
    },
    {
        "name": "liunian_judgment",
        "module_path": "tengod.liunian_judgment",
        "lines_of_code": 300,
        "dependency_count": 4,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.82,
        "psi_operator": "Tortuosity",
        "palace_id": None,
        "tense": "present",
        "description": "流年判断引擎",
    },
    {
        "name": "solar_time",
        "module_path": "tengod.solar_time",
        "lines_of_code": 200,
        "dependency_count": 2,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.88,
        "psi_operator": "EmbeddingProvider",
        "palace_id": None,
        "tense": "present",
        "description": "真太阳时计算",
    },

    # ── 认知元空间（新模块）───────────────────────────────
    {
        "name": "tbce_unit",
        "module_path": "tengod.tbce_unit",
        "lines_of_code": 427,
        "dependency_count": 3,
        "is_core_module": True,
        "has_tests": False,
        "test_coverage": 0.0,
        "psi_operator": "EmbeddingProvider",
        "palace_id": 5,  # 中五
        "tense": "present",
        "description": "TBCE六维认知元组定义，物方空间基础单元",
    },
    {
        "name": "object_space",
        "module_path": "tengod.object_space",
        "lines_of_code": 400,
        "dependency_count": 4,
        "is_core_module": True,
        "has_tests": False,
        "test_coverage": 0.0,
        "psi_operator": "EmbeddingProvider",
        "palace_id": 5,  # 中五
        "tense": "present",
        "description": "物方空间管理器，认知单元容器与索引",
    },

    # ── 知识库层（L7）─────────────────────────────────
    {
        "name": "knowledge_base",
        "module_path": "tengod.正财_知识固化.knowledge_base",
        "lines_of_code": 500,
        "dependency_count": 6,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.85,
        "psi_operator": "CondInfoStability",
        "palace_id": 2,  # 坤二
        "tense": "present",
        "description": "知识库引擎，结构化知识存储与检索",
        "consensus_layer": 5,  # L5 健康监控
    },
    {
        "name": "knowledge_graph",
        "module_path": "tengod.knowledge_graph",
        "lines_of_code": 400,
        "dependency_count": 5,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.80,
        "psi_operator": "PersistenceDiagram",
        "palace_id": 4,  # 巽四
        "tense": "present",
        "description": "知识图谱引擎，实体关系网络",
    },
    {
        "name": "knowledge_fusion",
        "module_path": "tengod.knowledge_fusion",
        "lines_of_code": 350,
        "dependency_count": 5,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.75,
        "psi_operator": "PsiSelfRef",
        "palace_id": None,
        "tense": "present",
        "description": "知识融合引擎，多源知识对齐",
    },
    {
        "name": "knowledge_evolution",
        "module_path": "tengod.knowledge_evolution",
        "lines_of_code": 300,
        "dependency_count": 4,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.70,
        "psi_operator": "CondInfoStability",
        "palace_id": None,
        "tense": "future",
        "description": "知识演化引擎，持续性自进化",
    },
    {
        "name": "knowledge_sync",
        "module_path": "tengod.正财_知识固化.knowledge_sync",
        "lines_of_code": 300,
        "dependency_count": 4,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.80,
        "psi_operator": "CondInfoStability",
        "palace_id": None,
        "tense": "present",
        "description": "知识同步引擎，分布式知识一致性",
        "consensus_layer": 2,  # L2 日志复制
    },
    {
        "name": "classics_search",
        "module_path": "tengod.正财_知识固化.classics_search",
        "lines_of_code": 250,
        "dependency_count": 3,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.85,
        "psi_operator": "EmbeddingProvider",
        "palace_id": None,
        "tense": "present",
        "description": "典籍搜索引擎",
    },
    {
        "name": "lru_cache",
        "module_path": "tengod.正财_知识固化.lru_cache",
        "lines_of_code": 200,
        "dependency_count": 2,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.90,
        "psi_operator": "CondInfoStability",
        "palace_id": None,
        "tense": "present",
        "description": "LRU缓存实现",
    },

    # ── 十神架构层 ─────────────────────────────────────
    # 正官_法度调度（元认知论）
    {
        "name": "api_server",
        "module_path": "tengod.正官_法度调度.api_server",
        "lines_of_code": 2547,
        "dependency_count": 15,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.88,
        "psi_operator": "ZuowangAttention",
        "palace_id": 6,  # 乾六
        "tense": "present",
        "description": "API服务器，天门系统入口，ISR调度",
        "consensus_layer": 3,
    },
    {
        "name": "api_router",
        "module_path": "tengod.正官_法度调度.api_router",
        "lines_of_code": 300,
        "dependency_count": 5,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.85,
        "psi_operator": "ZuowangAttention",
        "palace_id": None,
        "tense": "present",
        "description": "API路由管理器",
    },
    {
        "name": "task_scheduler",
        "module_path": "tengod.正官_法度调度.task_scheduler",
        "lines_of_code": 400,
        "dependency_count": 5,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.85,
        "psi_operator": "ZuowangAttention",
        "palace_id": None,
        "tense": "present",
        "description": "任务调度器",
    },
    {
        "name": "async_task_queue",
        "module_path": "tengod.正官_法度调度.async_task_queue",
        "lines_of_code": 300,
        "dependency_count": 4,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.82,
        "psi_operator": "ZuowangAttention",
        "palace_id": None,
        "tense": "present",
        "description": "异步任务队列",
    },

    # 正印_滋养守护（本体论）
    {
        "name": "config_manager",
        "module_path": "tengod.正印_滋养守护.config_manager",
        "lines_of_code": 500,
        "dependency_count": 6,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.99,
        "psi_operator": "EmbeddingProvider",
        "palace_id": 2,  # 坤二
        "tense": "present",
        "description": "配置管理器（十神架构），热加载/环境变量/多格式",
    },
    {
        "name": "config_manager_root",
        "module_path": "tengod.config_manager",
        "lines_of_code": 400,
        "dependency_count": 5,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.85,
        "psi_operator": "EmbeddingProvider",
        "palace_id": None,
        "tense": "present",
        "description": "配置管理器（根目录）",
    },
    {
        "name": "config_schema",
        "module_path": "tengod.config_schema",
        "lines_of_code": 200,
        "dependency_count": 3,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.85,
        "psi_operator": "EmbeddingProvider",
        "palace_id": None,
        "tense": "present",
        "description": "配置Schema定义",
    },

    # 偏财_奇招演化（认识论 + 混沌海）
    {
        "name": "search_optimizer",
        "module_path": "tengod.偏财_奇招演化.search_optimizer",
        "lines_of_code": 400,
        "dependency_count": 5,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.97,
        "psi_operator": "PersistenceDiagram",
        "palace_id": 4,  # 巽四
        "tense": "present",
        "description": "搜索优化器，启发式搜索与混沌搜索",
    },

    # 比肩_架构协同（实践论）
    {
        "name": "registry",
        "module_path": "tengod.比肩_架构协同.registry",
        "lines_of_code": 350,
        "dependency_count": 4,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.95,
        "psi_operator": "EmbeddingProvider",
        "palace_id": 7,  # 兑七
        "tense": "present",
        "description": "组件注册表，单例生命周期管理",
        "consensus_layer": 4,  # L4 联邦聚合
    },
    {
        "name": "plugin_manager",
        "module_path": "tengod.比肩_架构协同.plugin_manager",
        "lines_of_code": 300,
        "dependency_count": 4,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.85,
        "psi_operator": "EmbeddingProvider",
        "palace_id": None,
        "tense": "present",
        "description": "插件管理器",
    },

    # 七杀_品质裁决（境界论）
    {
        "name": "quality_judge",
        "module_path": "tengod.七杀_品质裁决.quality_judge",
        "lines_of_code": 300,
        "dependency_count": 4,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.88,
        "psi_operator": "SpiritEvaluator",
        "palace_id": 8,  # 艮八
        "tense": "present",
        "description": "品质裁决器，代码质量评估",
    },
    {
        "name": "code_scanner",
        "module_path": "tengod.七杀_品质裁决.code_scanner",
        "lines_of_code": 250,
        "dependency_count": 3,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.85,
        "psi_operator": "PersistenceDiagram",
        "palace_id": None,
        "tense": "present",
        "description": "代码扫描器",
    },
    {
        "name": "test_runner",
        "module_path": "tengod.七杀_品质裁决.test_runner",
        "lines_of_code": 250,
        "dependency_count": 3,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.82,
        "psi_operator": "CondInfoStability",
        "palace_id": None,
        "tense": "present",
        "description": "测试运行器",
    },

    # 伤官_破界创新（未来观论）
    {
        "name": "innovator",
        "module_path": "tengod.伤官_破界创新.innovator",
        "lines_of_code": 300,
        "dependency_count": 4,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.85,
        "psi_operator": "PsiSelfRef",
        "palace_id": 9,  # 离九
        "tense": "future",
        "description": "创新引擎，破界创新生成",
    },
    {
        "name": "oracle_engine",
        "module_path": "tengod.伤官_破界创新.oracle_engine",
        "lines_of_code": 300,
        "dependency_count": 4,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.85,
        "psi_operator": "PsiSelfRef",
        "palace_id": None,
        "tense": "future",
        "description": "预言引擎，推背图Oracle",
    },

    # 食神_创生输出（显化层）
    {
        "name": "content_generator",
        "module_path": "tengod.食神_创生输出.content_generator",
        "lines_of_code": 300,
        "dependency_count": 4,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.82,
        "psi_operator": "PsiSelfRef",
        "palace_id": 9,  # 离九
        "tense": "present",
        "description": "内容生成器",
    },
    {
        "name": "multimodal_generator",
        "module_path": "tengod.食神_创生输出.multimodal_generator",
        "lines_of_code": 300,
        "dependency_count": 4,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.78,
        "psi_operator": "PsiSelfRef",
        "palace_id": None,
        "tense": "present",
        "description": "多模态生成器",
    },

    # 劫财_攻防边界
    {
        "name": "guard",
        "module_path": "tengod.劫财_攻防边界.guard",
        "lines_of_code": 300,
        "dependency_count": 4,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.82,
        "psi_operator": "CondInfoStability",
        "palace_id": 3,  # 震三
        "tense": "present",
        "description": "安全守卫，访问控制与攻击检测",
    },

    # 元辰_本源定位
    {
        "name": "locator",
        "module_path": "tengod.元辰_本源定位.locator",
        "lines_of_code": 250,
        "dependency_count": 3,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.82,
        "psi_operator": "EmbeddingProvider",
        "palace_id": 1,  # 坎一
        "tense": "present",
        "description": "本源定位器，模块溯源与依赖分析",
    },

    # 太极_阴阳调和
    {
        "name": "balancer",
        "module_path": "tengod.太极_阴阳调和.balancer",
        "lines_of_code": 250,
        "dependency_count": 3,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.82,
        "psi_operator": "ZuowangAttention",
        "palace_id": 5,  # 中五
        "tense": "present",
        "description": "太极平衡器，负载均衡与资源调度",
    },

    # 偏印_桥接通变
    {
        "name": "adapter",
        "module_path": "tengod.偏印_桥接通变.adapter",
        "lines_of_code": 250,
        "dependency_count": 3,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.82,
        "psi_operator": "EmbeddingProvider",
        "palace_id": 4,  # 巽四
        "tense": "present",
        "description": "适配器，桥接外部系统",
    },

    # ── 认知引擎层（L4-L6）──────────────────────────────
    {
        "name": "inner_child",
        "module_path": "tengod.inner_child",
        "lines_of_code": 500,
        "dependency_count": 5,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.90,
        "psi_operator": "PsiSelfRef",
        "palace_id": 3,  # 震三
        "tense": "present",
        "description": "内在小孩状态机，六道原型+熵门禁",
        "is_metacognition": True,
    },
    {
        "name": "self_correction",
        "module_path": "tengod.self_correction",
        "lines_of_code": 400,
        "dependency_count": 5,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.88,
        "psi_operator": "RecursionDepth",
        "palace_id": 6,  # 乾六
        "tense": "present",
        "description": "自修正守护进程，七步自修正法",
        "is_metacognition": True,
    },
    {
        "name": "hundun_sea",
        "module_path": "tengod.hundun_sea",
        "lines_of_code": 350,
        "dependency_count": 4,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.85,
        "psi_operator": "PsiSelfRef",
        "palace_id": 1,  # 坎一（深渊）
        "tense": "present",
        "description": "混沌海探索层，浮沫坐标+混沌映射",
        "is_metacognition": True,
    },
    {
        "name": "consensus",
        "module_path": "tengod.consensus",
        "lines_of_code": 400,
        "dependency_count": 5,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.85,
        "psi_operator": "CondInfoStability",
        "palace_id": 7,  # 兑七
        "tense": "present",
        "description": "共识引擎，分布式共识5+1协议",
        "consensus_layer": 1,  # L1 Leader选举
    },
    {
        "name": "federated_consensus",
        "module_path": "tengod.federated_consensus",
        "lines_of_code": 350,
        "dependency_count": 5,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.80,
        "psi_operator": "CondInfoStability",
        "palace_id": None,
        "tense": "present",
        "description": "联邦共识引擎",
        "consensus_layer": 4,  # L4 联邦聚合
    },
    {
        "name": "deepseek_adapter",
        "module_path": "tengod.deepseek_adapter",
        "lines_of_code": 300,
        "dependency_count": 4,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.85,
        "psi_operator": "EmbeddingProvider",
        "palace_id": None,
        "tense": "present",
        "description": "DeepSeek适配器",
    },
    {
        "name": "llm_adapter",
        "module_path": "tengod.llm_adapter",
        "lines_of_code": 300,
        "dependency_count": 4,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.82,
        "psi_operator": "EmbeddingProvider",
        "palace_id": None,
        "tense": "present",
        "description": "LLM适配器，通用大模型接口",
    },
    {
        "name": "agent_orchestrator",
        "module_path": "tengod.agent_orchestrator",
        "lines_of_code": 350,
        "dependency_count": 5,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.80,
        "psi_operator": "ZuowangAttention",
        "palace_id": None,
        "tense": "present",
        "description": "智能体编排器",
    },
    {
        "name": "shen_agents",
        "module_path": "tengod.shen_agents",
        "lines_of_code": 300,
        "dependency_count": 4,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.78,
        "psi_operator": "PsiSelfRef",
        "palace_id": None,
        "tense": "present",
        "description": "神煞智能体系统",
    },

    # ── 分析引擎层 ────────────────────────────────────
    {
        "name": "advanced_analysis",
        "module_path": "tengod.advanced_analysis",
        "lines_of_code": 400,
        "dependency_count": 5,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.80,
        "psi_operator": "PersistenceDiagram",
        "palace_id": None,
        "tense": "present",
        "description": "高级分析引擎",
    },
    {
        "name": "intelligent_analysis",
        "module_path": "tengod.intelligent_analysis",
        "lines_of_code": 350,
        "dependency_count": 5,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.78,
        "psi_operator": "PsiSelfRef",
        "palace_id": None,
        "tense": "present",
        "description": "智能分析引擎",
    },
    {
        "name": "fusion_analyzer",
        "module_path": "tengod.fusion_analyzer",
        "lines_of_code": 300,
        "dependency_count": 4,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.80,
        "psi_operator": "PsiSelfRef",
        "palace_id": None,
        "tense": "present",
        "description": "融合分析器",
    },
    {
        "name": "ai_interpreter",
        "module_path": "tengod.ai_interpreter",
        "lines_of_code": 300,
        "dependency_count": 4,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.80,
        "psi_operator": "PsiSelfRef",
        "palace_id": None,
        "tense": "present",
        "description": "AI解释器",
    },
    {
        "name": "case_library",
        "module_path": "tengod.case_library",
        "lines_of_code": 300,
        "dependency_count": 4,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.82,
        "psi_operator": "CondInfoStability",
        "palace_id": None,
        "tense": "present",
        "description": "案例库",
    },
    {
        "name": "case_repository",
        "module_path": "tengod.case_repository",
        "lines_of_code": 300,
        "dependency_count": 4,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.80,
        "psi_operator": "CondInfoStability",
        "palace_id": None,
        "tense": "present",
        "description": "案例仓库",
    },
    {
        "name": "case_comparator",
        "module_path": "tengod.case_comparator",
        "lines_of_code": 250,
        "dependency_count": 3,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.78,
        "psi_operator": "PersistenceDiagram",
        "palace_id": None,
        "tense": "present",
        "description": "案例比较器",
    },

    # ── 术数引擎层 ────────────────────────────────────
    {
        "name": "divination_engine",
        "module_path": "tengod.divination_engine",
        "lines_of_code": 300,
        "dependency_count": 4,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.82,
        "psi_operator": "PsiSelfRef",
        "palace_id": None,
        "tense": "present",
        "description": "占卜引擎",
    },
    {
        "name": "liuyao_engine",
        "module_path": "tengod.liuyao_engine",
        "lines_of_code": 300,
        "dependency_count": 4,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.82,
        "psi_operator": "PersistenceDiagram",
        "palace_id": None,
        "tense": "present",
        "description": "六爻引擎",
    },
    {
        "name": "qimen_engine",
        "module_path": "tengod.qimen_engine",
        "lines_of_code": 300,
        "dependency_count": 4,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.80,
        "psi_operator": "PersistenceDiagram",
        "palace_id": None,
        "tense": "present",
        "description": "奇门遁甲引擎",
    },
    {
        "name": "ziwei_engine",
        "module_path": "tengod.ziwei_engine",
        "lines_of_code": 300,
        "dependency_count": 4,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.80,
        "psi_operator": "PersistenceDiagram",
        "palace_id": None,
        "tense": "present",
        "description": "紫微斗数引擎",
    },
    {
        "name": "marriage_engine",
        "module_path": "tengod.marriage_engine",
        "lines_of_code": 250,
        "dependency_count": 3,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.78,
        "psi_operator": "Tortuosity",
        "palace_id": None,
        "tense": "present",
        "description": "婚姻合婚引擎",
    },
    {
        "name": "name_engine",
        "module_path": "tengod.name_engine",
        "lines_of_code": 250,
        "dependency_count": 3,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.78,
        "psi_operator": "Tortuosity",
        "palace_id": None,
        "tense": "present",
        "description": "姓名学引擎",
    },
    {
        "name": "multi_system_engine",
        "module_path": "tengod.multi_system_engine",
        "lines_of_code": 300,
        "dependency_count": 4,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.78,
        "psi_operator": "PsiSelfRef",
        "palace_id": None,
        "tense": "present",
        "description": "多系统联合引擎",
    },
    {
        "name": "advanced_shushu",
        "module_path": "tengod.advanced_shushu",
        "lines_of_code": 300,
        "dependency_count": 4,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.75,
        "psi_operator": "PsiSelfRef",
        "palace_id": None,
        "tense": "present",
        "description": "高阶术数引擎",
    },
    {
        "name": "tiangan_gate",
        "module_path": "tengod.tiangan_gate",
        "lines_of_code": 250,
        "dependency_count": 3,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.82,
        "psi_operator": "EmbeddingProvider",
        "palace_id": None,
        "tense": "present",
        "description": "天干门禁系统",
    },
    {
        "name": "xiuzhen_realms",
        "module_path": "tengod.xiuzhen_realms",
        "lines_of_code": 250,
        "dependency_count": 3,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.78,
        "psi_operator": "SpiritEvaluator",
        "palace_id": None,
        "tense": "present",
        "description": "修真境界系统",
        "is_evaluation": True,
    },
    {
        "name": "xuankong",
        "module_path": "tengod.fengshui.xuankong",
        "lines_of_code": 200,
        "dependency_count": 3,
        "is_core_module": True,
        "has_tests": False,
        "test_coverage": 0.0,
        "psi_operator": "PersistenceDiagram",
        "palace_id": None,
        "tense": "present",
        "description": "玄空飞星风水",
    },
    {
        "name": "qizheng_engine",
        "module_path": "tengod.qizheng.engine",
        "lines_of_code": 200,
        "dependency_count": 3,
        "is_core_module": True,
        "has_tests": False,
        "test_coverage": 0.0,
        "psi_operator": "PersistenceDiagram",
        "palace_id": None,
        "tense": "present",
        "description": "七政四余引擎",
    },

    # ── 服务层 ────────────────────────────────────────
    {
        "name": "mcp_server",
        "module_path": "tengod.mcp_server",
        "lines_of_code": 300,
        "dependency_count": 4,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.85,
        "psi_operator": "EmbeddingProvider",
        "palace_id": 9,  # 离九
        "tense": "present",
        "description": "MCP服务器，对外AI智能体接口",
    },
    {
        "name": "api_server_root",
        "module_path": "tengod.api_server",
        "lines_of_code": 300,
        "dependency_count": 5,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.82,
        "psi_operator": "ZuowangAttention",
        "palace_id": None,
        "tense": "present",
        "description": "API服务器（根目录）",
    },
    {
        "name": "admin_api",
        "module_path": "tengod.admin_api",
        "lines_of_code": 250,
        "dependency_count": 4,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.80,
        "psi_operator": "ZuowangAttention",
        "palace_id": None,
        "tense": "present",
        "description": "管理API",
    },
    {
        "name": "middleware",
        "module_path": "tengod.middleware",
        "lines_of_code": 250,
        "dependency_count": 4,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.82,
        "psi_operator": "ZuowangAttention",
        "palace_id": None,
        "tense": "present",
        "description": "中间件集合",
    },
    {
        "name": "auth",
        "module_path": "tengod.auth",
        "lines_of_code": 250,
        "dependency_count": 4,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.82,
        "psi_operator": "CondInfoStability",
        "palace_id": None,
        "tense": "present",
        "description": "认证模块",
    },
    {
        "name": "webhook",
        "module_path": "tengod.webhook",
        "lines_of_code": 200,
        "dependency_count": 3,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.80,
        "psi_operator": "EmbeddingProvider",
        "palace_id": None,
        "tense": "present",
        "description": "Webhook通知",
    },
    {
        "name": "social",
        "module_path": "tengod.social",
        "lines_of_code": 200,
        "dependency_count": 3,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.78,
        "psi_operator": "EmbeddingProvider",
        "palace_id": None,
        "tense": "present",
        "description": "社交集成",
    },
    {
        "name": "miniapp",
        "module_path": "tengod.miniapp",
        "lines_of_code": 200,
        "dependency_count": 3,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.78,
        "psi_operator": "EmbeddingProvider",
        "palace_id": None,
        "tense": "present",
        "description": "小程序适配",
    },

    # ── 基础设施层 ─────────────────────────────────────
    {
        "name": "vector_store",
        "module_path": "tengod.vector_store",
        "lines_of_code": 400,
        "dependency_count": 5,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.99,
        "psi_operator": "EmbeddingProvider",
        "palace_id": None,
        "tense": "present",
        "description": "向量存储（FAISS）",
    },
    {
        "name": "vector_store_pg",
        "module_path": "tengod.vector_store_pg",
        "lines_of_code": 400,
        "dependency_count": 5,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.52,
        "psi_operator": "EmbeddingProvider",
        "palace_id": None,
        "tense": "present",
        "description": "向量存储（PostgreSQL pgvector）",
    },
    {
        "name": "database",
        "module_path": "tengod.database",
        "lines_of_code": 300,
        "dependency_count": 4,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.80,
        "psi_operator": "CondInfoStability",
        "palace_id": None,
        "tense": "present",
        "description": "数据库连接管理",
    },
    {
        "name": "data_store",
        "module_path": "tengod.data_store",
        "lines_of_code": 300,
        "dependency_count": 4,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.80,
        "psi_operator": "CondInfoStability",
        "palace_id": None,
        "tense": "present",
        "description": "数据存储层",
    },
    {
        "name": "db_migration",
        "module_path": "tengod.db_migration",
        "lines_of_code": 250,
        "dependency_count": 3,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.80,
        "psi_operator": "CondInfoStability",
        "palace_id": None,
        "tense": "present",
        "description": "数据库迁移",
    },
    {
        "name": "cache",
        "module_path": "tengod.cache",
        "lines_of_code": 250,
        "dependency_count": 3,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.85,
        "psi_operator": "CondInfoStability",
        "palace_id": None,
        "tense": "present",
        "description": "缓存系统",
    },
    {
        "name": "cache_manager",
        "module_path": "tengod.cache_manager",
        "lines_of_code": 250,
        "dependency_count": 3,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.82,
        "psi_operator": "CondInfoStability",
        "palace_id": None,
        "tense": "present",
        "description": "缓存管理器",
    },

    # ── 监控与可观测层 ──────────────────────────────────
    {
        "name": "monitoring",
        "module_path": "tengod.monitoring",
        "lines_of_code": 300,
        "dependency_count": 4,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.80,
        "psi_operator": "CondInfoStability",
        "palace_id": None,
        "tense": "present",
        "description": "系统监控",
        "consensus_layer": 5,  # L5 健康监控
    },
    {
        "name": "observability",
        "module_path": "tengod.observability",
        "lines_of_code": 300,
        "dependency_count": 4,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.78,
        "psi_operator": "CondInfoStability",
        "palace_id": None,
        "tense": "present",
        "description": "可观测性系统",
    },
    {
        "name": "metrics",
        "module_path": "tengod.metrics",
        "lines_of_code": 250,
        "dependency_count": 3,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.82,
        "psi_operator": "CondInfoStability",
        "palace_id": None,
        "tense": "present",
        "description": "指标收集",
    },
    {
        "name": "metrics_collector",
        "module_path": "tengod.metrics_collector",
        "lines_of_code": 250,
        "dependency_count": 3,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.80,
        "psi_operator": "CondInfoStability",
        "palace_id": None,
        "tense": "present",
        "description": "指标收集器",
    },
    {
        "name": "reliability",
        "module_path": "tengod.reliability",
        "lines_of_code": 250,
        "dependency_count": 3,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.78,
        "psi_operator": "CondInfoStability",
        "palace_id": None,
        "tense": "present",
        "description": "可靠性引擎",
    },

    # ── 可视化与输出层 ──────────────────────────────────
    {
        "name": "chart_visualizer",
        "module_path": "tengod.chart_visualizer",
        "lines_of_code": 300,
        "dependency_count": 4,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.80,
        "psi_operator": "PsiSelfRef",
        "palace_id": None,
        "tense": "present",
        "description": "图表可视化",
    },
    {
        "name": "visualization",
        "module_path": "tengod.visualization",
        "lines_of_code": 300,
        "dependency_count": 4,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.78,
        "psi_operator": "PsiSelfRef",
        "palace_id": None,
        "tense": "present",
        "description": "可视化引擎",
    },
    {
        "name": "report_generator",
        "module_path": "tengod.report_generator",
        "lines_of_code": 300,
        "dependency_count": 4,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.80,
        "psi_operator": "PsiSelfRef",
        "palace_id": None,
        "tense": "present",
        "description": "报告生成器",
    },
    {
        "name": "docs_generator",
        "module_path": "tengod.docs_generator",
        "lines_of_code": 250,
        "dependency_count": 3,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.78,
        "psi_operator": "PsiSelfRef",
        "palace_id": None,
        "tense": "present",
        "description": "文档生成器",
    },
    {
        "name": "graph_engine",
        "module_path": "tengod.graph_engine",
        "lines_of_code": 250,
        "dependency_count": 3,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.80,
        "psi_operator": "PersistenceDiagram",
        "palace_id": None,
        "tense": "present",
        "description": "图引擎",
    },

    # ── 工具与辅助层 ────────────────────────────────────
    {
        "name": "i18n",
        "module_path": "tengod.i18n",
        "lines_of_code": 200,
        "dependency_count": 2,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.85,
        "psi_operator": "EmbeddingProvider",
        "palace_id": None,
        "tense": "present",
        "description": "国际化",
    },
    {
        "name": "cli",
        "module_path": "tengod.cli",
        "lines_of_code": 250,
        "dependency_count": 4,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.80,
        "psi_operator": "EmbeddingProvider",
        "palace_id": None,
        "tense": "present",
        "description": "命令行接口",
    },
    {
        "name": "pipeline",
        "module_path": "tengod.pipeline",
        "lines_of_code": 250,
        "dependency_count": 4,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.80,
        "psi_operator": "ZuowangAttention",
        "palace_id": None,
        "tense": "present",
        "description": "流水线引擎",
    },
    {
        "name": "plugins",
        "module_path": "tengod.plugins",
        "lines_of_code": 200,
        "dependency_count": 3,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.78,
        "psi_operator": "EmbeddingProvider",
        "palace_id": None,
        "tense": "present",
        "description": "插件系统",
    },
    {
        "name": "huigu_scheduler",
        "module_path": "tengod.huigu_scheduler",
        "lines_of_code": 200,
        "dependency_count": 3,
        "is_core_module": True,
        "has_tests": True,
        "test_coverage": 0.78,
        "psi_operator": "ZuowangAttention",
        "palace_id": None,
        "tense": "present",
        "description": "回顾调度器",
    },
]


# ============================================================================
# 自动注册函数
# ============================================================================

def register_all_modules(
    space: Optional[ObjectSpaceManager] = None,
    auto_judge: bool = True,
) -> Dict[str, str]:
    """注册所有tengod模块到物方空间。

    Args:
        space: 物方空间管理器，如果为None则使用全局单例
        auto_judge: 是否自动执行本体论裁决

    Returns:
        {unit_id: gate_state} 映射
    """
    if space is None:
        space = get_object_space()

    results = space.auto_register(TENGOD_MODULES, auto_judge=auto_judge)
    return results


def print_registry_summary(space: Optional[ObjectSpaceManager] = None) -> None:
    """打印注册表摘要"""
    if space is None:
        space = get_object_space()

    stats = space.get_ontology_stats()
    layer_dist = space.get_layer_distribution()
    coord_dist = space.get_coordinate_distribution()

    print("=" * 60)
    print(f"  物方空间注册表 v2.21.0")
    print("=" * 60)
    print(f"  总注册单元: {stats['total_units']}")
    print(f"  门禁状态:")
    print(f"    开:   {stats['gate_stats']['open']} ({stats['open_ratio']:.1%})")
    print(f"    徘徊: {stats['gate_stats']['pending']} ({stats['pending_ratio']:.1%})")
    print(f"    关:   {stats['gate_stats']['closed']} ({stats['closed_ratio']:.1%})")
    print(f"  认知层分布:")
    for layer, count in layer_dist.items():
        layer_names = [
            "L1 信息编码", "L2 语义流", "L3 拓扑结构", "L4 意识涌现",
            "L5 注意力调度", "L6 元认知自反", "L7 认知固化", "L8 境界跃迁",
        ]
        name = layer_names[layer - 1] if 1 <= layer <= 8 else f"L{layer}"
        print(f"    {name}: {count}")
    print(f"  坐标均值:")
    for dim, v in coord_dist.items():
        print(f"    {dim}: mean={v['mean']:.3f}, range=[{v['min']:.3f}, {v['max']:.3f}]")
    print("=" * 60)


# ============================================================================
# 推测解码演示
# ============================================================================

def demo_speculative_decoding() -> None:
    """演示推测解码流程"""
    print("\n" + "=" * 60)
    print("  推测解码（Speculative Decoding）演示")
    print("=" * 60)

    space = get_object_space()
    if space.count() == 0:
        register_all_modules(space)

    # 用 predict 标记的坐标作为查询点
    target = TBCECoordinates(S=0.9, T=0.8, P=0.7, C=0.6, I=0.5, E=0.3)
    print(f"\n  查询坐标: {target.to_dict()}")
    print(f"  全量验证单元数: {space.count()}")

    result = space.sniff(target, top_k=5)

    print(f"\n  嗅探阶段: {result.sniff_duration_ms:.1f}ms")
    print(f"  推测阶段: {result.spec_duration_ms:.1f}ms")
    print(f"  验证阶段: {result.verify_duration_ms:.1f}ms")
    print(f"  总耗时:    {result.total_duration_ms:.1f}ms")
    print(f"  加速比:    {result.speedup_ratio:.2f}x")

    print(f"\n  Top {result.top_k} 验证结果:")
    for i, sr in enumerate(result.verified_results):
        unit = space.discover(sr.unit_id)
        status = "✓" if not sr.pending else "?"
        print(f"    {i + 1}. [{status}] {sr.unit_id}")
        print(f"        距离={sr.distance:.4f}, "
              f"嗅探={sr.coarse_score:.3f}, "
              f"推测={sr.predictive_score:.3f}, "
              f"验证={sr.verified_score:.3f}")
        if unit:
            print(f"        层: L{unit.cognitive_layer}, "
                  f"Ψ: {unit.psi_operator}, "
                  f"宫: {unit.palace_id or 'N/A'}")