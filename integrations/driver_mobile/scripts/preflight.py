"""Preflight diagnostic script for DebugLeaf Driver Mobile integration.

Checks:
- Python version and installed package versions
- Host LAN IPv4 discovery for physical device connectivity
- Port 8000 availability
- SQLite database directory permissions
- Dispatcher and Admin authentication token configuration
"""
from __future__ import annotations

import os
import socket
import sys
from pathlib import Path


def get_lan_ip() -> str:
    """Determine host's private IPv4 address on the local network."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Does not actually transmit packets, just determines routing interface
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def check_port_free(host: str, port: int) -> bool:
    """Check if server port is free to bind."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return True
        except OSError:
            return False


def run_preflight() -> int:
    print("=" * 60)
    print(" DEBUGLEAF DRIVER MOBILE INTEGRATION — PREFLIGHT CHECK")
    print("=" * 60)

    # 1. Python Environment
    print(f"[*] Python Executable: {sys.executable}")
    print(f"[*] Python Version:    {sys.version.split()[0]}")
    if sys.version_info < (3, 10):
        print(" [!] WARNING: Python 3.10+ recommended")

    # 2. Key Dependencies
    deps = ["fastapi", "starlette", "pydantic", "uvicorn", "pytest", "sqlite3"]
    missing = []
    for dep in deps:
        try:
            mod = __import__(dep)
            ver = getattr(mod, "__version__", "builtin")
            print(f" [+] Found {dep:<12} (version {ver})")
        except ImportError:
            missing.append(dep)
            print(f" [-] MISSING {dep}")

    if missing:
        print(f"\n[FATAL] Missing required packages: {', '.join(missing)}")
        return 1

    # 3. Network & Host IP Discovery
    lan_ip = get_lan_ip()
    print(f"\n[*] Discovered Private LAN IP: {lan_ip}")
    print(f"    -> Mobile phones must connect to: http://{lan_ip}:8000/api/v1/demo")

    port_free = check_port_free("0.0.0.0", 8000)
    if port_free:
        print(" [+] Port 8000 is available for binding")
    else:
        print(" [!] Port 8000 is currently in use (check for active uvicorn process)")

    # 4. Storage & Runtime Directory
    runtime_dir = Path(".runtime")
    try:
        runtime_dir.mkdir(parents=True, exist_ok=True)
        test_file = runtime_dir / ".preflight_write_test"
        test_file.write_text("ok")
        test_file.unlink()
        print(f" [+] Runtime directory '{runtime_dir.resolve()}' is writable")
    except Exception as exc:
        print(f" [!] Error writing to runtime directory: {exc}")
        return 1

    # 5. Auth Credentials check
    disp_token = os.environ.get("DEBUGLEAF_DISPATCHER_TOKEN")
    admin_token = os.environ.get("DEBUGLEAF_ADMIN_TOKEN")
    auth_mode = os.environ.get("DEBUGLEAF_AUTH_MODE", "token")
    print(f"\n[*] Auth Mode: {auth_mode}")
    print(f"    Dispatcher Token configured: {'YES' if disp_token else 'NO (set DEBUGLEAF_DISPATCHER_TOKEN)'}")
    print(f"    Admin Token configured:      {'YES' if admin_token else 'NO (set DEBUGLEAF_ADMIN_TOKEN)'}")

    print("\n" + "=" * 60)
    print(" PREFLIGHT RESULT: ALL CORE CHECKS PASSED")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(run_preflight())
