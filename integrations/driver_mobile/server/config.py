"""Configuration module for DebugLeaf driver mobile integration."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class IntegrationConfig:
    db_path: Path
    auth_mode: str
    dispatcher_token: str
    admin_token: str
    researcher_token: str
    session_ttl_minutes: int
    pairing_max_attempts: int
    pairing_window_seconds: int
    fixture_mode: bool
    host: str
    port: int

    @classmethod
    def from_env(cls) -> "IntegrationConfig":
        db_raw = os.environ.get("DEBUGLEAF_DEMO_DB_PATH", ".runtime/demo_store.sqlite3")
        db_path = Path(db_raw)
        
        auth_mode = os.environ.get("DEBUGLEAF_AUTH_MODE", "token").strip().lower()
        dispatcher_token = os.environ.get(
            "DEBUGLEAF_DISPATCHER_TOKEN", "DEBUGLEAF_DISPATCHER_SECRET_KEY_9988"
        )
        admin_token = os.environ.get(
            "DEBUGLEAF_ADMIN_TOKEN", "DEBUGLEAF_ADMIN_SECRET_KEY_7766"
        )
        researcher_token = os.environ.get(
            "DEBUGLEAF_RESEARCHER_TOKEN", "DEBUGLEAF_RESEARCHER_SECRET_KEY_5544"
        )
        
        session_ttl = int(os.environ.get("DEBUGLEAF_SESSION_TTL_MINUTES", "240"))
        pairing_max_attempts = int(os.environ.get("DEBUGLEAF_PAIRING_MAX_ATTEMPTS", "5"))
        pairing_window_seconds = int(os.environ.get("DEBUGLEAF_PAIRING_WINDOW_SECONDS", "60"))
        
        fixture_mode_raw = os.environ.get("DEBUGLEAF_DEMO_FIXTURE_MODE", "0").strip().lower()
        fixture_mode = fixture_mode_raw in ("1", "true", "yes")
        
        host = os.environ.get("DEBUGLEAF_HOST", "0.0.0.0")
        port = int(os.environ.get("DEBUGLEAF_PORT", "8000"))
        
        return cls(
            db_path=db_path,
            auth_mode=auth_mode,
            dispatcher_token=dispatcher_token,
            admin_token=admin_token,
            researcher_token=researcher_token,
            session_ttl_minutes=session_ttl,
            pairing_max_attempts=pairing_max_attempts,
            pairing_window_seconds=pairing_window_seconds,
            fixture_mode=fixture_mode,
            host=host,
            port=port,
        )


config = IntegrationConfig.from_env()
