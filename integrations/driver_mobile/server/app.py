"""ASGI Composite Application for DebugLeaf Driver Mobile Integration.

Composes the existing backend FastAPI application with the isolated
driver mobile subapplication under a single ASGI gateway.
"""
from __future__ import annotations

import logging
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api import create_app as create_backend_app
from backend.auth import AuthConfig
from .api import router as demo_router
from .auth import DemoAuthManager
from .config import IntegrationConfig, config as default_config
from .coordinator import TransactionalDemoCoordinator
from .storage import TransactionalDemoStore

logger = logging.getLogger(__name__)

DEMO_FIXTURE_CODES = [
    {
        "code": "PAIR01",
        "driver_id": "driver_1",
        "vehicle_id": "vehicle_1",
        "driver_name": "Ramesh Kumar",
    },
    {
        "code": "PAIR02",
        "driver_id": "driver_2",
        "vehicle_id": "vehicle_2",
        "driver_name": "Suresh Sharma",
    },
]


def create_demo_subapp(
    store: TransactionalDemoStore,
    coordinator: TransactionalDemoCoordinator,
    auth_manager: DemoAuthManager,
    cfg: IntegrationConfig,
) -> FastAPI:
    """Create isolated FastAPI subapplication for /api/v1/demo/* routes."""
    demo_app = FastAPI(
        title="DebugLeaf Driver Mobile API",
        version="1.0.0",
        description="Isolated driver edge integration and synchronisation API",
        openapi_url="/api/v1/demo/openapi.json",
        docs_url="/api/v1/demo/docs",
    )

    # Attach shared dependencies to app state
    demo_app.state.demo_store = store
    demo_app.state.demo_coordinator = coordinator
    demo_app.state.demo_auth_manager = auth_manager
    demo_app.state.integration_config = cfg

    # Add CORS middleware for mobile & diagnostic dashboard access
    demo_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Sanitized error handlers
    @demo_app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
        details = []
        for err in exc.errors():
            loc = err.get("loc", [])
            field = ".".join(str(item) for item in loc if item not in ("body",))
            details.append({"field": field or "body", "message": err.get("msg", "invalid")})
        return JSONResponse(
            status_code=422,
            content={"error": {"code": "invalid_request", "message": "Request validation failed", "details": details}},
        )

    @demo_app.exception_handler(HTTPException)
    async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
        if isinstance(exc.detail, dict) and "error" in exc.detail:
            return JSONResponse(status_code=exc.status_code, content=exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": "http_error", "message": str(exc.detail)}},
        )

    @demo_app.exception_handler(Exception)
    async def generic_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error in demo API")
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "internal_error", "message": "An internal server error occurred"}},
        )

    demo_app.include_router(demo_router)
    return demo_app


class CompositeGateway:
    """Top-level ASGI Gateway composing backend and demo applications."""

    def __init__(
        self,
        demo_app: FastAPI,
        backend_app: FastAPI,
        store: TransactionalDemoStore,
        cfg: IntegrationConfig,
    ) -> None:
        self.demo_app = demo_app
        self.backend_app = backend_app
        self.store = store
        self.cfg = cfg
        self._lifespan_stack: Optional[AsyncExitStack] = None

    async def _on_startup(self) -> None:
        """Initialize resources and seed fixtures if configured."""
        logger.info("Initializing DebugLeaf Driver Mobile integration")
        self._lifespan_stack = AsyncExitStack()
        # Cooperatively enter backend and demo lifespans
        if hasattr(self.backend_app, "router") and hasattr(self.backend_app.router, "lifespan_context"):
            try:
                await self._lifespan_stack.enter_async_context(self.backend_app.router.lifespan_context(self.backend_app))
            except Exception as exc:
                logger.warning("Could not enter backend lifespan context: %s", exc)
        if hasattr(self.demo_app, "router") and hasattr(self.demo_app.router, "lifespan_context"):
            try:
                await self._lifespan_stack.enter_async_context(self.demo_app.router.lifespan_context(self.demo_app))
            except Exception as exc:
                logger.warning("Could not enter demo lifespan context: %s", exc)

        if self.cfg.fixture_mode:
            logger.info("Seeding deterministic pairing codes PAIR01, PAIR02 (fixture mode)")
            self.store.seed_pairing_codes(DEMO_FIXTURE_CODES, reset=False)

    async def _on_shutdown(self) -> None:
        """Gracefully terminate background workers and databases."""
        logger.info("Shutting down DebugLeaf Driver Mobile integration")
        if self._lifespan_stack is not None:
            try:
                await self._lifespan_stack.aclose()
            except Exception as exc:
                logger.warning("Error closing lifespan contexts: %s", exc)

        # Close backend job manager if initialized
        if hasattr(self.backend_app.state, "job_manager") and self.backend_app.state.job_manager is not None:
            try:
                self.backend_app.state.job_manager.close(wait=True)
            except Exception as exc:
                logger.warning("Error closing backend job_manager: %s", exc)

        # Close backend eta jobs if initialized
        if hasattr(self.backend_app.state, "eta_jobs") and self.backend_app.state.eta_jobs is not None:
            try:
                self.backend_app.state.eta_jobs.close(wait=True)
            except Exception as exc:
                logger.warning("Error closing backend eta_jobs: %s", exc)

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        scope_type = scope.get("type")

        if scope_type == "http":
            path = scope.get("path", "")
            if path == "/api/v1/demo" or path.startswith("/api/v1/demo/"):
                await self.demo_app(scope, receive, send)
            else:
                await self.backend_app(scope, receive, send)
            return

        if scope_type == "lifespan":
            while True:
                message = await receive()
                if message["type"] == "lifespan.startup":
                    try:
                        await self._on_startup()
                        await send({"type": "lifespan.startup.complete"})
                    except Exception as exc:
                        logger.error("Startup failed: %s", exc)
                        await send({"type": "lifespan.startup.failed", "message": str(exc)})
                        return
                elif message["type"] == "lifespan.shutdown":
                    try:
                        await self._on_shutdown()
                        await send({"type": "lifespan.shutdown.complete"})
                    except Exception as exc:
                        logger.error("Shutdown failed: %s", exc)
                        await send({"type": "lifespan.shutdown.failed", "message": str(exc)})
                    return

        # Fallback to backend app for any other ASGI protocols (e.g. websocket)
        await self.backend_app(scope, receive, send)


def create_composite_app(
    cfg: Optional[IntegrationConfig] = None,
    backend_app: Optional[FastAPI] = None,
) -> CompositeGateway:
    """Factory to instantiate the composite application."""
    active_cfg = cfg or default_config

    # 1. Instantiate backend app
    if backend_app is None:
        # Build backend auth config matching active settings
        if active_cfg.auth_mode == "token":
            backend_tokens = {
                "dispatcher": active_cfg.dispatcher_token,
                "admin": active_cfg.admin_token,
                "researcher": active_cfg.researcher_token,
            }
            backend_auth = AuthConfig.from_mapping("token", backend_tokens)
        else:
            backend_auth = AuthConfig.from_mapping("local")
        backend = create_backend_app(auth_config=backend_auth)
    else:
        backend = backend_app

    # 2. Instantiate integration services
    store = TransactionalDemoStore(active_cfg.db_path)
    coordinator = TransactionalDemoCoordinator(store)
    auth_manager = DemoAuthManager(store, active_cfg)

    # 3. Instantiate demo subapplication
    demo_app = create_demo_subapp(store, coordinator, auth_manager, active_cfg)

    # 4. Compose under top-level ASGI gateway
    gateway = CompositeGateway(demo_app, backend, store, active_cfg)
    return gateway


# Launch target
app = create_composite_app()
