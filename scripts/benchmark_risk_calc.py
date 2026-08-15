#!/usr/bin/env python3
"""Benchmark script for risk level calculation in scripts/privilege_and_safety_test.py."""

import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from scripts import privilege_and_safety_test


def run_benchmark():
    """Measures baseline execution time for risk level calculation logic."""
    test_cases = [
        [],
        [{"severity": "LOW_RISK"}],
        [{"severity": "MEDIUM_RISK"}],
        [{"severity": "HIGH_RISK"}],
        [{"severity": "CRITICAL_RISK"}],
        [{"severity": "LOW_RISK"}, {"severity": "MEDIUM_RISK"}, {"severity": "HIGH_RISK"}],
        [{"severity": "LOW_RISK"}, {"severity": "HIGH_RISK"}, {"severity": "CRITICAL_RISK"}],
        [{"severity": "MEDIUM_RISK"} for _ in range(100)],
    ]

    iterations = 200000

    start_time = time.perf_counter()
    for _ in range(iterations):
        for issues in test_cases:
            privilege_and_safety_test.check_safety_calc_risk(issues)
    elapsed_time = time.perf_counter() - start_time

    print(f"Execution time for {iterations * len(test_cases)} iterations: {elapsed_time:.6f} seconds")
    return elapsed_time


if __name__ == "__main__":
    run_benchmark()
