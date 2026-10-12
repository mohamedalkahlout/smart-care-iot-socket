#!/usr/bin/env python3
"""
Test Runner for SmartCare Hub Multi-Socket Project.
Executes all unit, conformance, and multi-channel test suites.
"""
import sys
import unittest

def main():
    print("=" * 65)
    print(" [TESTS] Running SmartCare Multi-Socket Hub Test Suite...")
    print("=" * 65)

    loader = unittest.TestLoader()
    suite = loader.discover("tests", pattern="test_*.py")

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("=" * 65)
    if result.wasSuccessful():
        print(f" [SUCCESS] All {result.testsRun} tests passed successfully!")
        print("=" * 65)
        sys.exit(0)
    else:
        print(f" [FAILED] {len(result.failures)} failures, {len(result.errors)} errors.")
        print("=" * 65)
        sys.exit(1)

if __name__ == "__main__":
    main()
