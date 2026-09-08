#!/usr/bin/env python3
"""
TEKNOFEST 2026 Akıllı Fabrika Digital Twin (SITL) Simulator
Comprehensive Opaque-Box E2E Test Runner (Tiers 1-4).

Discovers and executes all test suites, calculates metrics,
supports headless CI execution, generates structured JSON report at:
.agents/e2e_test_report.json
"""

import sys
import os
import time
import json
import argparse
import unittest
from datetime import datetime, timezone

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


class DetailedTestResult(unittest.TestResult):
    def __init__(self, stream=None, descriptions=None, verbosity=1):
        super().__init__(stream, descriptions, verbosity)
        self.stream = stream or sys.stdout
        self.verbosity = verbosity
        self.successes = []
        self.test_timings = {}
        self._start_time = 0.0

    def startTest(self, test):
        super().startTest(test)
        self._start_time = time.perf_counter()
        if self.verbosity >= 2:
            self.stream.write(f"  RUNNING: {test.id()} ... ")
            self.stream.flush()

    def addSuccess(self, test):
        super().addSuccess(test)
        duration = time.perf_counter() - self._start_time
        self.successes.append(test)
        self.test_timings[test.id()] = duration
        if self.verbosity >= 2:
            self.stream.write(f"PASS ({duration*1000:.1f}ms)\n")
        elif self.verbosity == 1:
            self.stream.write(".")
            self.stream.flush()

    def addFailure(self, test, err):
        super().addFailure(test, err)
        duration = time.perf_counter() - self._start_time
        self.test_timings[test.id()] = duration
        if self.verbosity >= 2:
            self.stream.write(f"FAIL ({duration*1000:.1f}ms)\n")
        elif self.verbosity == 1:
            self.stream.write("F")
            self.stream.flush()

    def addError(self, test, err):
        super().addError(test, err)
        duration = time.perf_counter() - self._start_time
        self.test_timings[test.id()] = duration
        if self.verbosity >= 2:
            self.stream.write(f"ERROR ({duration*1000:.1f}ms)\n")
        elif self.verbosity == 1:
            self.stream.write("E")
            self.stream.flush()

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        duration = time.perf_counter() - self._start_time
        self.test_timings[test.id()] = duration
        if self.verbosity >= 2:
            self.stream.write(f"SKIP ({reason})\n")
        elif self.verbosity == 1:
            self.stream.write("s")
            self.stream.flush()


def run_e2e_tests(tier: str = "all", headless: bool = True,
                  report_path: str = None, verbosity: int = 1) -> int:
    """Executes the E2E test suite and writes .agents/e2e_test_report.json."""
    if headless:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"
        os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

    if report_path is None:
        report_path = os.path.join(PROJECT_ROOT, ".agents", "e2e_test_report.json")

    print("\n" + "=" * 78)
    print(" TEKNOFEST 2026 AKILLI FABRIKA SITL SIMULATOR - E2E TEST SUITE")
    print("=" * 78)
    print(f" Mode: {'HEADLESS CI' if headless else 'INTERACTIVE'}")
    print(f" Target Tier: {tier.upper()}")
    print(f" Output Report: {report_path}")
    print("-" * 78)

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    tests_dir = os.path.dirname(os.path.abspath(__file__))

    tier_files = {
        "1": "test_tier1_features.py",
        "2": "test_tier2_boundaries.py",
        "3": "test_tier3_pairwise.py",
        "4": "test_tier4_applications.py"
    }

    if tier in tier_files:
        filename = tier_files[tier]
        s = loader.discover(tests_dir, pattern=filename)
        suite.addTests(s)
    elif tier == "all":
        for t_num in sorted(tier_files.keys()):
            s = loader.discover(tests_dir, pattern=tier_files[t_num])
            suite.addTests(s)
    else:
        print(f"ERROR: Unknown tier '{tier}'. Choose from: 1, 2, 3, 4, all.")
        return 2

    start_wall_time = time.perf_counter()
    result = DetailedTestResult(verbosity=verbosity)
    suite.run(result)
    total_duration = time.perf_counter() - start_wall_time
    if verbosity == 1:
        print()

    total_tests = result.testsRun
    failed_count = len(result.failures)
    error_count = len(result.errors)
    skipped_count = len(result.skipped)
    passed_count = len(result.successes)
    pass_rate = (passed_count / total_tests * 100.0) if total_tests > 0 else 0.0

    # Classify metrics by Tier
    tier_metrics = {
        "tier1_features": {"total": 0, "passed": 0, "failed": 0, "errors": 0},
        "tier2_boundaries": {"total": 0, "passed": 0, "failed": 0, "errors": 0},
        "tier3_pairwise": {"total": 0, "passed": 0, "failed": 0, "errors": 0},
        "tier4_applications": {"total": 0, "passed": 0, "failed": 0, "errors": 0}
    }

    for test in result.successes:
        t_id = test.id()
        if "test_tier1" in t_id:
            tier_metrics["tier1_features"]["total"] += 1
            tier_metrics["tier1_features"]["passed"] += 1
        elif "test_tier2" in t_id:
            tier_metrics["tier2_boundaries"]["total"] += 1
            tier_metrics["tier2_boundaries"]["passed"] += 1
        elif "test_tier3" in t_id:
            tier_metrics["tier3_pairwise"]["total"] += 1
            tier_metrics["tier3_pairwise"]["passed"] += 1
        elif "test_tier4" in t_id:
            tier_metrics["tier4_applications"]["total"] += 1
            tier_metrics["tier4_applications"]["passed"] += 1

    for test, tb in result.failures:
        t_id = test.id()
        for k in tier_metrics:
            key_short = k.split("_")[0]
            if key_short in t_id:
                tier_metrics[k]["total"] += 1
                tier_metrics[k]["failed"] += 1

    for test, tb in result.errors:
        t_id = test.id()
        for k in tier_metrics:
            key_short = k.split("_")[0]
            if key_short in t_id:
                tier_metrics[k]["total"] += 1
                tier_metrics[k]["errors"] += 1

    status_str = "PASSED" if (failed_count == 0 and error_count == 0) else "FAILED"

    # Terminal Summary Table
    print("\n" + "=" * 78)
    print(" TEST EXECUTION SUMMARY")
    print("=" * 78)
    print(f" {'TIER':<30} | {'TOTAL':<8} | {'PASS':<8} | {'FAIL':<8} | {'RATE':<8}")
    print("-" * 78)
    names = {
        "tier1_features": "Tier 1: Feature Coverage",
        "tier2_boundaries": "Tier 2: Boundaries & Corners",
        "tier3_pairwise": "Tier 3: Pairwise Combinations",
        "tier4_applications": "Tier 4: E2E Workload Scenarios"
    }
    for k, name in names.items():
        m = tier_metrics[k]
        rate = (m["passed"] / m["total"] * 100.0) if m["total"] > 0 else 0.0
        print(f" {name:<30} | {m['total']:<8} | {m['passed']:<8} | {m['failed']+m['errors']:<8} | {rate:>5.1f}%")
    print("-" * 78)
    print(f" {'OVERALL TOTAL':<30} | {total_tests:<8} | {passed_count:<8} | {failed_count+error_count:<8} | {pass_rate:>5.1f}%")
    print("=" * 78)
    print(f" Result: {status_str} (Duration: {total_duration:.2f}s)")

    # Print failures if any
    if result.failures or result.errors:
        print("\n" + "!" * 78)
        print(" FAILURE DETAILS:")
        print("!" * 78)
        for test, tb in result.failures:
            print(f"\n[FAIL] {test.id()}:\n{tb}")
        for test, tb in result.errors:
            print(f"\n[ERROR] {test.id()}:\n{tb}")

    # Build JSON Report
    report_dict = {
        "project": "TEKNOFEST 2026 Mesleki Yetenek Akıllı Fabrika Digital Twin SITL",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": status_str,
        "summary": {
            "total_tests": total_tests,
            "passed": passed_count,
            "failed": failed_count,
            "errors": error_count,
            "skipped": skipped_count,
            "pass_rate_percent": round(pass_rate, 2),
            "duration_seconds": round(total_duration, 4)
        },
        "tier_metrics": tier_metrics,
        "failures": [
            {"test": test.id(), "type": "FAIL", "traceback": tb}
            for test, tb in result.failures
        ] + [
            {"test": test.id(), "type": "ERROR", "traceback": tb}
            for test, tb in result.errors
        ]
    }

    try:
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report_dict, f, indent=2)
        print(f"\n Report saved successfully to: {report_path}\n")
    except Exception as e:
        print(f"\n WARNING: Could not save report to {report_path}: {e}\n")

    return 0 if status_str == "PASSED" else 1


def main():
    parser = argparse.ArgumentParser(
        description="TEKNOFEST 2026 Akıllı Fabrika SITL Simulator E2E Test Runner"
    )
    parser.add_argument(
        "--tier",
        choices=["1", "2", "3", "4", "all"],
        default="all",
        help="Specify which tier to execute (default: all)"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=True,
        help="Run tests in headless mode (default: True)"
    )
    parser.add_argument(
        "--report",
        type=str,
        default=None,
        help="Path to save JSON test report (default: .agents/e2e_test_report.json)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose test output"
    )

    args = parser.parse_args()
    exit_code = run_e2e_tests(
        tier=args.tier,
        headless=args.headless,
        report_path=args.report,
        verbosity=2 if args.verbose else 1
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
