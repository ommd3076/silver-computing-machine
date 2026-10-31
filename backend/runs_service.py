"""Backend service for managing dispatcher plan runs, recovery re-planning, and evidence."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any


class RunsService:
    """Manages active dispatch plans, recovery re-plans, and operational telemetry."""

    def __init__(self, fixture_path: Path | str | None = None) -> None:
        self._lock = threading.Lock()
        if fixture_path is None:
            self._fixture_path = Path("fixtures/active_runs.json")
        else:
            self._fixture_path = Path(fixture_path)
        self._runs: dict[str, dict[str, Any]] = {}
        self._evidence: dict[str, Any] = {}
        self._events: list[dict[str, Any]] = []
        self._load_fixtures()

    def _load_fixtures(self) -> None:
        if self._fixture_path.exists():
            try:
                with open(self._fixture_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                bengaluru = data.get("bengaluru", {})
                solomon = data.get("solomon", {})
                if bengaluru:
                    self._runs[bengaluru["id"]] = bengaluru
                if solomon:
                    self._runs[solomon["id"]] = solomon
                self._evidence = data.get("evidence", {})
                self._events = data.get("events", [])
            except Exception as e:
                print(f"[RunsService] Warning loading fixtures: {e}")

    def list_runs(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._runs.values())

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        with self._lock:
            return self._runs.get(run_id)

    def get_evidence(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._evidence)

    def get_events(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._events)
