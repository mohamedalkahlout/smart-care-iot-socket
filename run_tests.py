#!/usr/bin/env python3
"""
Unified Test Runner for Smart Socket System.
Runs unit tests for Safety Guard, Control Logic, Thermal Simulator, and ML Modules.
"""
import sys
import os
import unittest

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

def main():
    print("=" * 65)
    print("[TESTS] Running Smart Socket Test Suite...")
    print("=" * 65)

    loader = unittest.TestLoader()
    start_dir = os.path.join(os.path.dirname(__file__), "tests")
    suite = loader.discover(start_dir, pattern="test_*.py")

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("=" * 65)
    if result.wasSuccessful():
        print(f"[SUCCESS] All {result.testsRun} tests passed successfully!")
        return 0
    else:
        print(f"[FAILURE] Tests failed: {len(result.failures)} failures, {len(result.errors)} errors.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
