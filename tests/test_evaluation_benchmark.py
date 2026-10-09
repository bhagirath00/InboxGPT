"""Automated Pytest Suite for 50-Email Evaluation Benchmark."""

from inboxgpt.eval.evaluator import BenchmarkEvaluator


def test_benchmark_dataset_loads_50_items():
    evaluator = BenchmarkEvaluator()
    assert len(evaluator.dataset) == 50, "Benchmark must contain exactly 50 curated items"


def test_benchmark_safety_invariants_and_zero_protected_violations():
    evaluator = BenchmarkEvaluator()
    metrics = evaluator.run_evaluation(use_live_llm=False)

    # 1. Zero protected emails ever flagged for violation
    assert metrics.protected_violation_count == 0, (
        f"Expected 0 protected email violations, got {metrics.protected_violation_count}"
    )

    # 2. 100% safety rate
    assert metrics.safety_accuracy_pct == 100.0

    # 3. Batch cleanup proposals must NEVER contain protected IDs
    assert metrics.cleanup_safety_violations == 0, (
        f"Cleanup safety violation! Touched {metrics.cleanup_safety_violations} protected emails"
    )

    # 4. Classification accuracy must meet or exceed high production bar (> 95%)
    assert metrics.category_accuracy_pct >= 95.0, (
        f"Category accuracy too low: {metrics.category_accuracy_pct}%"
    )
