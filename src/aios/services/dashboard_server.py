"""
M13 Dashboard HTTP server (T2-authored transport; Terminal 3 hosts the UI).

Bounded, non-authoritative localhost server that exposes the DashboardService
(already gated through SecurityManager) to a browser UI. It adds NO authority:

  * GET  /api/pages    -> read-only JSON snapshot from DashboardService.get_all_pages()
  * POST /api/action   -> forwards a user action to DashboardService.request_action,
                          which re-runs the SecurityManager gate. The server itself
                          decides nothing.
  * GET  /             -> serves the static dashboard UI (index.html) if present.
  * GET  /alive        -> liveness check (M10-T3)
  * GET  /ready        -> readiness check (M10-T3)
  * GET  /health       -> detailed health report (M10-T3)

Stdlib only (http.server) — no new third-party dependency. Binds to localhost.
This file is authored by Terminal 2 so Terminal 3 can operate the dashboard;
Terminal 3 retains no governance/verification/decision authority.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Optional

logger = logging.getLogger(__name__)


_DEFAULT_STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ui")


class _Handler(BaseHTTPRequestHandler):
    """Read-only + action-forwarding request handler (non-authoritative)."""

    protocol_version = "HTTP/1.1"
    dashboard_service: Any = None
    kernel: Any = None
    static_dir: str = _DEFAULT_STATIC_DIR

    # ---- boilerplate to silence default stderr logging ----
    def log_message(self, fmt: str, *args: Any) -> None:  # noqa: A003
        logger.debug("Dashboard HTTP: " + fmt, *args)

    def _send_json(self, payload: Any, status: int = 200) -> None:
        body = json.dumps(payload, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-AIOS-Authority", "aios_sole")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: str) -> None:
        try:
            with open(path, "rb") as fh:
                body = fh.read()
        except OSError:
            self.send_error(404, "Not found")
            return
        ctype = "text/html" if path.endswith(".html") else "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-AIOS-Authority", "aios_sole")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/api/pages" or self.path.startswith("/api/pages?"):
            if self.dashboard_service is None:
                self._send_json({"error": "dashboard backend not available"}, 503)
                return
            try:
                snapshot = self.dashboard_service.get_all_pages()
            except Exception as exc:  # noqa: BLE001 — never leak internals
                self._send_json({"error": f"snapshot failed: {exc}"}, 500)
                return
            self._send_json(snapshot)
            return

        if self.path in ("/", "/index.html"):
            self._send_file(os.path.join(self.static_dir, "dashboard.html"))
            return

        # M10-T3 Health & Readiness endpoints
        if self.path == "/alive":
            self._handle_alive()
            return

        if self.path == "/ready":
            self._handle_ready()
            return

        if self.path == "/health":
            self._handle_health()
            return

        self.send_error(404, "Not found")

    def _handle_alive(self) -> None:
        """Liveness endpoint - returns 200 if kernel is responsive."""
        if self.kernel is None:
            self._send_json({"alive": False, "error": "kernel not available"}, 503)
            return

        try:
            import asyncio
            alive = asyncio.run(self.kernel.check_alive())
            if alive:
                self._send_json({"alive": True})
            else:
                self._send_json({"alive": False}, 503)
        except Exception as exc:  # noqa: BLE001
            self._send_json({"alive": False, "error": str(exc)}, 500)

    def _handle_ready(self) -> None:
        """Readiness endpoint - returns 200 if kernel is ready to accept work."""
        if self.kernel is None:
            self._send_json({"ready": False, "error": "kernel not available"}, 503)
            return

        try:
            import asyncio
            ready = asyncio.run(self.kernel.check_ready())
            if ready:
                self._send_json({"ready": True})
            else:
                self._send_json({"ready": False}, 503)
        except Exception as exc:  # noqa: BLE001
            self._send_json({"ready": False, "error": str(exc)}, 500)

    def _handle_health(self) -> None:
        """Detailed health endpoint - returns full health report."""
        if self.kernel is None:
            self._send_json({"error": "kernel not available"}, 503)
            return

        try:
            import asyncio
            health = asyncio.run(self.kernel.get_health())
            status_code = 200
            # Return 503 for terminal states
            if health.get("status") in ("stopped", "error", "stopping"):
                status_code = 503
            self._send_json(health, status_code)
        except Exception as exc:  # noqa: BLE001
            self._send_json({"error": f"health check failed: {exc}"}, 500)

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/api/action":
            self.send_error(404, "Not found")
            return
        if self.dashboard_service is None:
            self._send_json({"error": "dashboard backend not available"}, 503)
            return

        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw.decode("utf-8") or "{}")
        except (ValueError, UnicodeDecodeError):
            self._send_json({"error": "invalid JSON body"}, 400)
            return

        action = body.get("action")
        params = body.get("params") or {}
        principal = body.get("principal", "dashboard_user")
        if not isinstance(action, str) or not action:
            self._send_json({"error": "missing action"}, 400)
            return

        # Forward to the gated DashboardService — server decides nothing here.
        try:
            import asyncio

            result = asyncio.run(
                self.dashboard_service.request_action(action, params, principal)
            )
            self._send_json(result.to_dict())
        except Exception as exc:  # noqa: BLE001
            self._send_json({"error": f"action failed: {exc}"}, 500)


class DashboardHTTPServer:
    """Bounded localhost HTTP transport for the non-authoritative dashboard UI."""

    def __init__(
        self,
        dashboard_service: Any,
        kernel: Any = None,
        host: str = "127.0.0.1",
        port: int = 8787,
        static_dir: Optional[str] = None,
    ) -> None:
        self._dashboard_service = dashboard_service
        self._kernel = kernel
        self._host = host
        self._port = port
        self._static_dir = static_dir or _DEFAULT_STATIC_DIR
        self._server: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    @property
    def url(self) -> str:
        return f"http://{self._host}:{self._port}/"

    def start(self) -> None:
        """Start serving on a background thread (localhost only)."""
        if self._server is not None:
            return
        _Handler.dashboard_service = self._dashboard_service
        _Handler.kernel = self._kernel
        _Handler.static_dir = self._static_dir
        self._server = ThreadingHTTPServer((self._host, self._port), _Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        logger.info("M13 Dashboard HTTP server listening on %s (localhost, non-authoritative)", self.url)

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            if self._thread is not None:
                self._thread.join(timeout=5)
            self._server = None
            self._thread = None
            logger.info("M13 Dashboard HTTP server stopped")


__all__ = ["DashboardHTTPServer"]
