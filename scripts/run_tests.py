#!/usr/bin/env python3
"""
Test Runner for DepegAlert Bot
Provides convenient commands for running different types of tests
"""
import os
import subprocess
import sys
from pathlib import Path


def run_command(command: list, description: str) -> int:
    """Run a command and return exit code"""
    print(f"\n🔍 {description}")
    print(f"Running: {' '.join(command)}")
    print("-" * 60)

    result = subprocess.run(
        command, cwd=Path(__file__).parent.parent
    )  # Run from project root
    if result.returncode == 0:
        print(f"✅ {description} completed successfully")
    else:
        print(f"❌ {description} failed")

    return result.returncode


def main():
    """Main test runner function"""
    import argparse

    parser = argparse.ArgumentParser(description="Run DepegAlert Bot tests")
    parser.add_argument(
        "test_type",
        choices=[
            "unit",
            "integration",
            "all",
            "coverage",
            "security",
            "performance",
            "quick",
        ],
        default="all",
        nargs="?",
        help="Type of tests to run",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )
    parser.add_argument(
        "--parallel", "-p", action="store_true", help="Run tests in parallel"
    )
    parser.add_argument(
        "--fail-fast", "-x", action="store_true", help="Stop on first failure"
    )

    args = parser.parse_args()

    # Check if pytest is installed
    try:
        import pytest
    except ImportError:
        print("❌ pytest not installed. Install test dependencies:")
        print("pip install -r requirements.txt")
        sys.exit(1)

    # Base pytest command
    base_cmd = ["python", "-m", "pytest"]

    if args.verbose:
        base_cmd.extend(["-v", "-s"])

    if args.parallel:
        base_cmd.extend(["-n", "auto"])

    if args.fail_fast:
        base_cmd.append("-x")

    exit_code = 0

    if args.test_type == "unit":
        cmd = base_cmd + ["tests/unit", "-m", "unit"]
        exit_code = run_command(cmd, "Running unit tests")

    elif args.test_type == "integration":
        cmd = base_cmd + ["tests/integration", "-m", "integration"]
        exit_code = run_command(cmd, "Running integration tests")

    elif args.test_type == "security":
        cmd = base_cmd + ["tests/", "-m", "security"]
        exit_code = run_command(cmd, "Running security tests")

    elif args.test_type == "performance":
        cmd = base_cmd + ["tests/", "-m", "performance"]
        exit_code = run_command(cmd, "Running performance tests")

    elif args.test_type == "quick":
        cmd = base_cmd + ["tests/unit", "-m", "unit", "--tb=short"]
        exit_code = run_command(cmd, "Running quick unit tests")

    elif args.test_type == "coverage":
        cmd = base_cmd + [
            "tests/",
            "--cov=bot",
            "--cov=core",
            "--cov-report=html:htmlcov",
            "--cov-report=term-missing",
            "--cov-report=xml",
            "--cov-fail-under=80",
        ]
        exit_code = run_command(cmd, "Running tests with coverage")

        if exit_code == 0:
            print("\n📊 Coverage report generated:")
            print("  - HTML: htmlcov/index.html")
            print("  - XML: coverage.xml")

    elif args.test_type == "all":
        # Run unit tests first
        cmd = base_cmd + ["tests/unit", "-m", "unit"]
        exit_code = run_command(cmd, "Running unit tests")

        if exit_code == 0:
            # Run integration tests
            cmd = base_cmd + ["tests/integration", "-m", "integration"]
            exit_code = run_command(cmd, "Running integration tests")

        if exit_code == 0:
            # Run coverage report
            cmd = base_cmd + [
                "tests/",
                "--cov=bot",
                "--cov=core",
                "--cov-report=term-missing",
            ]
            exit_code = run_command(cmd, "Generating coverage report")

    # Summary
    if exit_code == 0:
        print("\n🎉 All tests passed successfully!")
        print("\n📋 Next steps:")
        print("  - Review coverage report: htmlcov/index.html")
        print("  - Add more tests for uncovered code")
        print("  - Run tests in CI/CD pipeline")
    else:
        print(f"\n❌ Tests failed with exit code {exit_code}")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
