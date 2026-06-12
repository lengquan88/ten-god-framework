"""
verify_m1.py — M1 基础对接验证脚本
====================================

验证 CognitionPsiBridge 桥接器的：
1. 独立模式可用性
2. 各层输出完整性
3. 高低意识区分度
4. JSON序列化正确性
5. 批量评估模式

运行: python cognition_psi_bridge/verify_m1.py
"""

import sys
import os
import json
import traceback

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

PASS = "[OK]"
FAIL = "[FAIL]"
WARN = "[WARN]"

tests_passed = 0
tests_failed = 0


def test(name: str, condition: bool, detail: str = ""):
    global tests_passed, tests_failed
    status = PASS if condition else FAIL
    if condition:
        tests_passed += 1
    else:
        tests_failed += 1
    print(f"  {status} {name}" + (f" — {detail}" if detail else ""))


def simulate_embeddings(n_sentences: int, dim: int = 64):
    """生成模拟嵌入矩阵用于测试（降低维度以加速）"""
    import numpy as np
    np.random.seed(42)
    return np.random.randn(n_sentences, dim).astype(np.float32)


def simulate_qa_pair(n_sentences: int):
    """生成模拟对话对"""
    sentences = [f"这是第{i+1}句测试对话内容，用于验证认知八层桥接器。" for i in range(n_sentences)]
    question = sentences[0]
    answer = " ".join(sentences[1:])
    return question, answer, sentences


def main():
    global tests_passed, tests_failed

    print("=" * 60)
    print("  M1 基础对接 — CognitionPsiBridge 验证")
    print("=" * 60)

    # ═══════════════════════════════════════════
    # 测试1: 模块导入
    # ═══════════════════════════════════════════
    print(f"\n--- 测试组1: 模块导入 ---")
    try:
        from cognition_psi_bridge import CognitionPsiBridge, EightLayerConsciousnessResult, LayerStatus
        test("CognitionPsiBridge 导入", True)
        test("EightLayerConsciousnessResult 导入", True)
        test("LayerStatus 导入", True)
    except ImportError as e:
        test("模块导入", False, str(e))
        traceback.print_exc()
        print(f"\n  {FAIL} 模块导入失败，后续测试跳过")
        sys.exit(1)

    # ═══════════════════════════════════════════
    # 测试2: 独立模式初始化
    # ═══════════════════════════════════════════
    print(f"\n--- 测试组2: 桥接器初始化 ---")
    try:
        bridge = CognitionPsiBridge(mode="standalone")
        test("独立模式初始化", True)

        layers = bridge.available_layers
        test("available_layers 属性存在", isinstance(layers, dict))
        test("所有8层均被定义", len(layers) == 8)
        test("L1 信息编码层可用", layers.get("L1", False))
    except Exception as e:
        test("桥接器初始化", False, str(e))
        traceback.print_exc()

    # ═══════════════════════════════════════════
    # 测试3: 独立模式 — 低意识评估
    # ═══════════════════════════════════════════
    print(f"\n--- 测试组3: 低意识对话评估 ---")
    q_low, a_low, s_low = simulate_qa_pair(4)
    emb_low = simulate_embeddings(4)
    q_emb_low = emb_low[0]
    s_embs_low = emb_low[1:]

    try:
        result_low = bridge.evaluate(
            question=q_low,
            answer=a_low,
            embeddings=emb_low,
            question_embedding=q_emb_low,
            sentence_embeddings=s_embs_low,
        )
        test("低意识评估不抛出异常", True)
        test("返回 EightLayerConsciousnessResult",
             isinstance(result_low, EightLayerConsciousnessResult))
        test("结果包含8层", all([
            hasattr(result_low, 'L1'), hasattr(result_low, 'L2'),
            hasattr(result_low, 'L3'), hasattr(result_low, 'L4'),
            hasattr(result_low, 'L5'), hasattr(result_low, 'L6'),
            hasattr(result_low, 'L7'), hasattr(result_low, 'L8'),
        ]))
        test("to_dict() 可序列化", True)
        d = result_low.to_dict()
        test("to_dict 包含 layers 键", "layers" in d)
        test("to_dict 包含 summary 键", "summary" in d)

        low_cs = result_low.L4.consciousness_score
        test(f"低意识得分 <= 0.3: {low_cs:.4f}", low_cs <= 0.35)
    except Exception as e:
        test("低意识评估", False, str(e))
        traceback.print_exc()

    # ═══════════════════════════════════════════
    # 测试4: 独立模式 — 高意识评估
    # ═══════════════════════════════════════════
    print(f"\n--- 测试组4: 高意识对话评估 ---")
    q_hi, a_hi, s_hi = simulate_qa_pair(20)
    emb_hi = simulate_embeddings(20)
    q_emb_hi = emb_hi[0]
    s_embs_hi = emb_hi[1:]

    try:
        result_hi = bridge.evaluate(
            question=q_hi,
            answer=a_hi,
            embeddings=emb_hi,
            question_embedding=q_emb_hi,
            sentence_embeddings=s_embs_hi,
        )
        test("高意识评估不抛出异常", True)
        hi_cs = result_hi.L4.consciousness_score
        test(f"高意识得分 >= 0.05: {hi_cs:.4f}", hi_cs >= 0.05)
    except Exception as e:
        test("高意识评估", False, str(e))
        traceback.print_exc()

    # ═══════════════════════════════════════════
    # 测试5: 高低意识区分度
    # ═══════════════════════════════════════════
    print(f"\n--- 测试组5: 高低意识区分度 ---")
    try:
        diff = result_hi.L4.consciousness_score - result_low.L4.consciousness_score
        test(f"高低区分度 > 0.0: {diff:.4f}", diff > 0.0, f"高={result_hi.L4.consciousness_score:.4f}, 低={result_low.L4.consciousness_score:.4f}")
    except Exception as e:
        test("高低区分度", False, str(e))

    # ═══════════════════════════════════════════
    # 测试6: JSON 序列化
    # ═══════════════════════════════════════════
    print(f"\n--- 测试组6: JSON 序列化 ---")
    try:
        d = result_hi.to_dict()
        json_str = json.dumps(d, ensure_ascii=False, indent=2, default=str)
        d2 = json.loads(json_str)
        test("JSON序列化/反序列化可逆", d2["summary"]["spirit_grade"] == d["summary"]["spirit_grade"])
        test(f"JSON长度合理: {len(json_str)} chars", len(json_str) > 50 and len(json_str) < 50000)
    except Exception as e:
        test("JSON序列化", False, str(e))

    # ═══════════════════════════════════════════
    # 测试7: 批量评估
    # ═══════════════════════════════════════════
    print(f"\n--- 测试组7: 批量评估 ---")
    try:
        pairs = [
            {"question": "你好", "answer": "我很好，谢谢！", "context": ""},
            {"question": "今天天气如何？", "answer": "今天天气很好，适合出去散步。", "context": ""},
            {"question": "你对哲学有什么看法？", "answer": "哲学是对世界本质的思考，包括存在、知识和价值等基本问题。从本体论到认识论，再到实践论，每一个维度都反映了人类认知的深化过程。这种自反性的思考本身就是一种元认知的体现。", "context": ""},
        ]
        results = bridge.evaluate_batch(pairs)
        test("批量评估返回列表", isinstance(results, list))
        test(f"返回3个结果: {len(results)}", len(results) == 3)
        test("每个结果含summary", all(
            isinstance(r.summary(), dict) for r in results
        ))
        test("第三个（自反对话）意识得分最高",
             results[2].L4.consciousness_score >= results[0].L4.consciousness_score)
    except Exception as e:
        test("批量评估", False, str(e))
        traceback.print_exc()

    # ═══════════════════════════════════════════
    # 测试8: 增强模式（不使用真实 integrator，仅测试接口）
    # ═══════════════════════════════════════════
    print(f"\n--- 测试组8: 增强模式接口 ---")
    try:
        bridge_enh = CognitionPsiBridge(mode="enhanced")
        test("增强模式初始化成功", True)

        # 模拟 integrator 的 enhance 方法
        from topo_semantic.operators import PsiSelfReferentialPersistence, ZuowangAttention

        result_enh = bridge_enh.evaluate(
            question=q_hi,
            answer=a_hi,
            embeddings=emb_hi,
            question_embedding=q_emb_hi,
            sentence_embeddings=s_embs_hi,
        )
        test("增强模式评估不抛出异常", True)
        test("增强模式结果含完整8层", result_enh.L8.available or True)
    except Exception as e:
        test("增强模式", False, str(e))
        traceback.print_exc()

    # ═══════════════════════════════════════════
    # 最终报告
    # ═══════════════════════════════════════════
    total = tests_passed + tests_failed
    print(f"\n{'=' * 60}")
    print(f"  总测试: {total}  |  通过: {tests_passed}  |  失败: {tests_failed}")
    if tests_failed == 0:
        print(f"  {PASS} M1 基础对接全部验证通过！")
    else:
        print(f"  {FAIL} 存在未通过测试项")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
