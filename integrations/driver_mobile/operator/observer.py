"""Integration-owned Dispatcher Operator Console (CLI Observer).

Displays real-time fleet overview, route revisions, active incidents,
and driver acknowledgement states directly from the authoritative backend.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime


def fetch_overview(base_url: str, token: str) -> dict:
    url = f"{base_url.rstrip('/')}/dispatcher/overview"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        err_msg = exc.read().decode("utf-8")
        print(f"[ERROR] HTTP {exc.code}: {err_msg}", file=sys.stderr)
        raise
    except Exception as exc:
        print(f"[ERROR] Network failure: {exc}", file=sys.stderr)
        raise


def render_dashboard(data: dict) -> None:
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    drivers = data.get("drivers", [])
    incidents = data.get("active_incidents", [])

    print("\n" + "=" * 78)
    print(f" DEBUGLEAF / arQ — DISPATCHER OPERATOR CONSOLE   [{now_str}]")
    print("=" * 78)

    print("\n[ACTIVE FLEET STATUS]")
    print(f"{'DRIVER ID':<12} {'NAME':<16} {'VEHICLE':<12} {'VER':<5} {'ACK':<5} {'CORRIDOR':<22} {'DELAY'}")
    print("-" * 78)
    for d in drivers:
        did = d.get("driver_id", "")
        name = d.get("driver_name", "")
        veh = d.get("vehicle_id", "")
        ver = str(d.get("route_version", 1))
        ack = str(d.get("last_ack_version", 0))
        corr = d.get("corridor", "")
        delay = f"+{d.get('active_delay_seconds', 0.0):.0f}s"
        status_flag = "SYNCED" if ver == ack else "PENDING_ACK"
        print(f"{did:<12} {name:<16} {veh:<12} {ver:<5} {ack:<5} {corr:<22} {delay:<8} [{status_flag}]")

    print("\n[ACTIVE INCIDENT OVERLAYS]")
    if not incidents:
        print("  (No active incident overlays recorded on corridors)")
    else:
        print(f"{'EVENT ID':<24} {'DRIVER':<10} {'SEGMENT':<18} {'SEVERITY':<10} {'DELAY':<8} {'REPORTED AT'}")
        print("-" * 78)
        for inc in incidents:
            eid = inc.get("event_id", "")
            d_id = inc.get("driver_id", "")
            seg = inc.get("segment_id", "")
            sev = inc.get("severity", "").upper()
            dly = f"+{inc.get('delay_seconds', 0):.0f}s"
            rep = inc.get("reported_at", "")[:19]
            print(f"{eid:<24} {d_id:<10} {seg:<18} {sev:<10} {dly:<8} {rep}")

    print("=" * 78)


def main():
    parser = argparse.ArgumentParser(description="DebugLeaf Dispatcher CLI Observer")
    parser.add_argument("--url", default="http://127.0.0.1:8000/api/v1/demo", help="Base demo API URL")
    parser.add_argument("--token", default=os.environ.get("DEBUGLEAF_DISPATCHER_TOKEN", "DEBUGLEAF_DISPATCHER_SECRET_KEY_9988"), help="Dispatcher Bearer Token")
    parser.add_argument("--watch", action="store_true", help="Continuously poll every 2 seconds")
    parser.add_argument("--interval", type=float, default=2.0, help="Poll interval in seconds")
    args = parser.parse_args()

    if not args.token:
        print("[FATAL] Dispatcher token required. Set DEBUGLEAF_DISPATCHER_TOKEN or pass --token", file=sys.stderr)
        sys.exit(1)

    if not args.watch:
        try:
            data = fetch_overview(args.url, args.token)
            render_dashboard(data)
        except Exception:
            sys.exit(1)
        return

    print(f"[*] Starting dispatcher live watch (polling every {args.interval}s)... Press Ctrl+C to exit.")
    try:
        while True:
            try:
                data = fetch_overview(args.url, args.token)
                render_dashboard(data)
            except Exception as e:
                print(f"[!] Poll error: {e}")
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nExiting operator console.")


if __name__ == "__main__":
    main()
