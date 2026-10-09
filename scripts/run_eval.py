#!/usr/bin/env python3
"""Run InboxGPT Ground-Truth Evaluation Benchmark (50 Emails)."""

import argparse
import sys
from inboxgpt.eval.evaluator import BenchmarkEvaluator, print_evaluation_report


def main():
    parser = argparse.ArgumentParser(description="InboxGPT 50-Email Benchmark Evaluator")
    parser.add_argument("--live-llm", action="store_true", help="Use live Google Gemini LLM instead of heuristic")
    args = parser.parse_args()

    print("\n[+] Loading 50 Curated Ground-Truth Emails for InboxGPT...")
    evaluator = BenchmarkEvaluator()
    metrics = evaluator.run_evaluation(use_live_llm=args.live_llm)
    print_evaluation_report(metrics)

    if metrics.protected_violation_count > 0 or metrics.cleanup_safety_violations > 0:
        print("\n[!] FATAL: Safety invariants failed! Protected emails were violated.")
        sys.exit(1)

    print("\n[PASS] ALL INVARIANTS PASSED: 0 Protected Email Violations (100% Safety Guarantee).\n")
    sys.exit(0)


if __name__ == "__main__":
    main()
