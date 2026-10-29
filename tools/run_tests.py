#!/usr/bin/env python3
"""Convenience test runner that automatically routes to the project's .venv python."""

from pathlib import Path
import subprocess
import sys

_root = Path(__file__).resolve().parent.parent

# Locate project virtual environment python executable
_venv_py_win = _root / ".venv" / "Scripts" / "python.exe"
_venv_py_posix = _root / ".venv" / "bin" / "python"
_target_py = _venv_py_win if _venv_py_win.exists() else _venv_py_posix

if not _target_py.exists():
    _target_py = Path(sys.executable)

# Default test targets
args = sys.argv[1:] if len(sys.argv) > 1 else [
    "tests/test_execution_evidence.py",
    "tests/test_isolated_qml.py",
    "-v",
]

result = subprocess.run([str(_target_py), "-m", "pytest", *args], cwd=str(_root))
sys.exit(result.returncode)
