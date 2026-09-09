"""
Test runner script for Guessly.

Usage:
  python run_tests.py              # Run all tests
  python run_tests.py -v           # Verbose output
  python run_tests.py -k engine    # Run tests matching 'engine'
  python run_tests.py --cov        # Run with coverage report
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent


def run_tests(args=None):
    """Run pytest with the given arguments."""
    cmd = [sys.executable, "-m", "pytest", "tests/"]
    
    if args:
        cmd.extend(args)
    
    print(f"Running: {' '.join(cmd)}")
    print("=" * 60)
    
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    return result.returncode


def main():
    args = sys.argv[1:]
    
    # Show help if requested
    if "-h" in args or "--help" in args:
        print(__doc__)
        return 0
    
    # Run tests
    return run_tests(args)


if __name__ == "__main__":
    sys.exit(main())
