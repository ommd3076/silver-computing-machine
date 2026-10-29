"""Stopped-service reset script for DebugLeaf driver mobile demo state.

Isolates changes to .runtime/demo_store.sqlite3 only.
Never touches backend/india_eta.sqlite3, debugleaf.sqlite3, or model checkpoints.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Add repo root to import path
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from integrations.driver_mobile.server.app import DEMO_FIXTURE_CODES
from integrations.driver_mobile.server.coordinator import TransactionalDemoCoordinator
from integrations.driver_mobile.server.storage import TransactionalDemoStore


def reset_demo() -> int:
    db_raw = os.environ.get("DEBUGLEAF_DEMO_DB_PATH", ".runtime/demo_store.sqlite3")
    db_path = Path(db_raw)
    print("=" * 60)
    print(f" RESETTING DEMO STATE: {db_path.resolve()}")
    print("=" * 60)

    # Initialize store and reset pairing codes
    store = TransactionalDemoStore(db_path)
    
    # 1. Reset database tables (sessions, driver_state, reports, jobs, audits)
    with store._connection() as conn:
        conn.executescript("""
            DELETE FROM sessions;
            DELETE FROM driver_state;
            DELETE FROM congestion_reports;
            DELETE FROM planning_jobs;
            DELETE FROM audit_events;
            DELETE FROM pairing_rate_limits;
        """)

    # 2. Reset pairing codes to unused state
    store.seed_pairing_codes(DEMO_FIXTURE_CODES, reset=True)
    print("[+] Reset pairing codes: PAIR01 (Driver 1), PAIR02 (Driver 2)")

    # 3. Initialize default driver route assignments
    coord = TransactionalDemoCoordinator(store)
    coord._ensure_default_state()
    print("[+] Initialized Driver 1 on Expressway Route (route_v1_primary, v1)")
    print("[+] Initialized Driver 2 on South Arterial Route (route_v2_primary, v1)")

    print("\n" + "=" * 60)
    print(" DEMO STATE RESET COMPLETE: READY FOR PRESENTATION")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(reset_demo())
