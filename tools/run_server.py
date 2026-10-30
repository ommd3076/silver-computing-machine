#!/usr/bin/env python3
"""DebugLeaf Web Server Runner.

Automatically routes to the repository's `.venv` Python and launches Uvicorn
to serve both the FastAPI backend REST API and the integrated HTML/JS frontend.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys
import threading
import time
import webbrowser

_root = Path(__file__).resolve().parent.parent

# Locate project virtual environment python executable
_venv_py_win = _root / ".venv" / "Scripts" / "python.exe"
_venv_py_posix = _root / ".venv" / "bin" / "python"
_target_py = _venv_py_win if _venv_py_win.exists() else _venv_py_posix


def _ensure_venv() -> None:
    if _target_py.exists() and Path(sys.executable).resolve() != _target_py.resolve():
        cmd = [str(_target_py), str(Path(__file__).resolve()), *sys.argv[1:]]
        proc = subprocess.run(cmd, cwd=str(_root))
        sys.exit(proc.returncode)


def main() -> None:
    _ensure_venv()

    parser = argparse.ArgumentParser(description="Run DebugLeaf FastAPI & Web UI Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind (default: 8000)")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically open the browser")
    args = parser.parse_args()

    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

    import uvicorn
    from backend.api import app

    url = f"http://{args.host}:{args.port}"
    print("=" * 68)
    print("  DebugLeaf Platform — Hybrid Quantum Fleet Optimization")
    print("=" * 68)
    print(f"  * Web UI:        {url}/  (or {url}/ui)")
    print(f"  * Swagger Docs:  {url}/docs")
    print(f"  * Health Probe:  {url}/api/v1/health")
    print("=" * 68)
    print("  Press Ctrl+C to stop the server.\n")

    if not args.no_browser:
        def _open():
            time.sleep(1.2)
            try:
                webbrowser.open(url)
            except Exception:
                pass
        threading.Thread(target=_open, daemon=True).start()

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
