#!/usr/bin/env python3
"""DebugLeaf - Unified Application Runner for Quant-A-Maze 3.0.

Launches the FastAPI backend serving both the REST API endpoints and
the interactive offline-compatible HTML/CSS/JS frontend dashboard.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys

_root = Path(__file__).resolve().parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

# Locate project virtual environment python executable
_venv_py_win = _root / ".venv" / "Scripts" / "python.exe"
_venv_py_posix = _root / ".venv" / "bin" / "python"
_target_py = _venv_py_win if _venv_py_win.exists() else _venv_py_posix

# Auto-switch to virtual environment interpreter if running under external Python
if _target_py.exists() and Path(sys.executable).resolve() != _target_py.resolve():
    try:
        import uvicorn
        import fastapi
    except ImportError:
        res = subprocess.run([str(_target_py), *sys.argv])
        sys.exit(res.returncode)

import uvicorn


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="DebugLeaf Platform Server")
    parser.add_argument("--host", default="127.0.0.1", help="Bind socket host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Bind socket port (default: 8000)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload on code change")
    return parser.parse_args()


def print_banner(host: str, port: int) -> None:
    url = f"http://{host}:{port}"
    print("=" * 72)
    print("  DebugLeaf Platform - Hybrid Quantum-Classical Dispatch & ETA")
    print("  Quant-A-Maze 3.0 Final Evaluation Demonstration Server")
    print("=" * 72)
    print(f"  * Web Dashboard:   {url}/")
    print(f"  * UI Route:        {url}/ui")
    print(f"  * API Health:      {url}/api/v1/health")
    print(f"  * OpenAPI Docs:    {url}/docs")
    print("-" * 72)
    print("  Interactive Demonstration Tabs:")
    print("    [1] Classical vs. Quantum QAOA Fleet Dispatch")
    print("    [2] India Delivery ETA (Classical GBDT + 4Q Residual VQC)")
    print("    [3] Scenario & Candidate Delivery Route Generator")
    print("    [4] Financial Dispatch & Late Penalty Optimization")
    print("    [5] Dynamic Disruption Recovery with Cryptographic Audit Trail")
    print("    [6] Independent Domain Plan Validator")
    print("    [7] Platform Architecture & Provenance Telemetry")
    print("=" * 72)
    print("  Press Ctrl+C to stop the server.\n")


def main() -> None:
    args = parse_args()
    print_banner(args.host, args.port)
    uvicorn.run(
        "backend.api:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )


if __name__ == "__main__":
    main()
