"""Authentication and FastAPI dependencies for DebugLeaf driver mobile integration.

Enforces:
- Scoped one-time pairing
- Cryptographically secure opaque bearer tokens
- Rate limits on pairing attempts
- Strict driver vs dispatcher authorization separation
- Input bounds and token sanitization
"""
from __future__ import annotations

import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import Depends, HTTPException, Request

from .config import IntegrationConfig, config as default_config
from .storage import TransactionalDemoStore, RateLimitExceededError


class DemoAuthManager:
    """Manages pairing codes and driver bearer sessions."""

    def __init__(self, store: TransactionalDemoStore, config: Optional[IntegrationConfig] = None) -> None:
        self.store = store
        self.config = config or default_config

    def redeem_code(self, code: str, client_ip: str) -> Optional[dict[str, Any]]:
        """Redeem a one-time code for a driver bearer token.
        
        Enforces rate limiting and input size bounds.
        """
        # Rate limit check
        allowed = self.store.check_and_record_rate_limit(
            client_ip,
            max_attempts=self.config.pairing_max_attempts,
            window_seconds=self.config.pairing_window_seconds,
        )
        if not allowed:
            raise RateLimitExceededError("Too many pairing attempts; please wait before retrying")

        clean_code = code.strip().upper()
        if len(clean_code) > 32 or not clean_code:
            return None

        token = "demo_sess_" + secrets.token_hex(20)
        expires_dt = datetime.now(timezone.utc) + timedelta(minutes=self.config.session_ttl_minutes)
        expires_at = expires_dt.isoformat()

        driver_info = self.store.redeem_code(clean_code, token, expires_at)
        if not driver_info:
            return None

        return {
            "token": token,
            "expires_at": expires_at,
            "driver_id": driver_info["driver_id"],
            "vehicle_id": driver_info["vehicle_id"],
            "driver_name": driver_info["driver_name"],
        }

    def verify_token(self, token: str) -> Optional[dict[str, Any]]:
        """Verify token validity, expiration, and non-revocation."""
        if not token or not token.startswith("demo_sess_") or len(token) > 128:
            return None

        session = self.store.get_session(token)
        if not session:
            return None

        try:
            exp = datetime.fromisoformat(session["expires_at"])
            if datetime.now(timezone.utc) > exp:
                return None
        except Exception:
            return None

        return {
            "driver_id": session["driver_id"],
            "vehicle_id": session["vehicle_id"],
            "driver_name": session["driver_name"],
            "token": token,
        }

    def revoke_token(self, token: str) -> bool:
        if not token or not token.startswith("demo_sess_"):
            return False
        return self.store.revoke_session(token)


# -----------------------------------------------------------------------------
# FastAPI Dependencies
# -----------------------------------------------------------------------------

def get_bearer_token(request: Request) -> str:
    """Extract raw bearer token from Authorization header."""
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail={"error": {"code": "authentication_required", "message": "Bearer token required"}},
        )
    return auth_header[7:].strip()


async def get_current_driver(request: Request) -> dict[str, Any]:
    """Dependency for driver-authenticated endpoints.
    
    Resolves driver identity exclusively from the validated session token.
    """
    token = get_bearer_token(request)
    auth_mgr: DemoAuthManager = request.app.state.demo_auth_manager
    driver = auth_mgr.verify_token(token)
    if not driver:
        raise HTTPException(
            status_code=401,
            detail={"error": {"code": "invalid_session", "message": "Session is invalid or expired"}},
        )
    return driver


async def require_dispatcher_or_admin(request: Request) -> dict[str, str]:
    """Dependency for dispatcher-only endpoints.
    
    Verifies DEBUGLEAF_DISPATCHER_TOKEN or DEBUGLEAF_ADMIN_TOKEN.
    Driver tokens are explicitly rejected with 403 Forbidden.
    """
    token = get_bearer_token(request)
    cfg: IntegrationConfig = request.app.state.integration_config

    # Explicit rejection of driver sessions on dispatcher endpoints
    if token.startswith("demo_sess_"):
        raise HTTPException(
            status_code=403,
            detail={"error": {"code": "authorization_denied", "message": "Driver session token is not authorized for dispatcher endpoints"}},
        )

    matched_role: Optional[str] = None
    if cfg.dispatcher_token and hmac.compare_digest(token.encode("utf-8"), cfg.dispatcher_token.encode("utf-8")):
        matched_role = "dispatcher"
    elif cfg.admin_token and hmac.compare_digest(token.encode("utf-8"), cfg.admin_token.encode("utf-8")):
        matched_role = "admin"

    if not matched_role:
        raise HTTPException(
            status_code=401,
            detail={"error": {"code": "authentication_failed", "message": "Bearer token is invalid"}},
        )

    return {"role": matched_role}
