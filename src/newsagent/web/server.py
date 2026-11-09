# =============================================================================
# Module: newsagent.web.server
# Responsibilities: Local stdlib HTTP server and JSON API over the pipeline/report/trend services.
# Dependencies: http.server, config, pipeline, report, store, trend
# Dependents: cli, ui/
# ADRs: ADR-0010
# Traceability: docs/decisions/README.md
# =============================================================================
"""Local HTML interface (stdlib http.server).

Appearance lives in ``ui/`` (templates/static/themes), configuration in
``config/``; this module only exposes the core pipeline as a small JSON API.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from ..config import Config
from ..keys import KEY_FILENAME, ensure_key_file
from ..pipeline import run_pipeline
from ..report import list_reports, load_report
from ..store import Store, utc_now
from ..trend import analyze_trends

ROOT = Path(__file__).resolve().parents[3]
UI_DIR = ROOT / "ui"


class RunState:
    """Mutable status of the background 'generate report' job (single job at a time)."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.running = False
        self.started_at: str | None = None
        self.finished_at: str | None = None
        self.error: str | None = None
        self.stats: dict[str, Any] = {}

    def snapshot(self) -> dict[str, Any]:
        """Return a thread-safe snapshot of run state.

        Preconditions:
            RunState exists.
        Postconditions:
            Dict with running/started_at/finished_at/error/stats.
        Prohibitions:
            Do not mutate the returned dict.
        Raises:
            None.
        """
        with self.lock:
            return {
                "running": self.running,
                "started_at": self.started_at,
                "finished_at": self.finished_at,
                "error": self.error,
                "stats": self.stats,
            }


def make_handler(config: Config):
    """Build the HTTP handler class bound to config and run state.

    Preconditions:
        Config is loaded; UI static directory exists.
    Postconditions:
        ApiHandler subclass ready for ThreadingHTTPServer.
    Prohibitions:
        Do not expose the server beyond localhost.
    Raises:
        None.
    """
    state = RunState()

    class ApiHandler(BaseHTTPRequestHandler):
        server_version = "AIAgentUI/0.1"

        def log_message(self, fmt: str, *args: Any) -> None:  # keep console readable
            """Suppress the default per-request logging of BaseHTTPRequestHandler.

            Preconditions:
                Called by the stdlib handler for each request.
            Postconditions:
                Nothing is written to stderr for normal requests.
            Prohibitions:
                Do not replace this with noisy logging in the request path.
            Raises:
                None.
            """
            return

        # ---------- helpers ----------
        def _json(self, payload: Any, status: int = 200) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _file(self, path: Path, content_type: str) -> None:
            if not path.exists() or not path.is_file():
                self._json({"error": "not found"}, 404)
                return
            body = path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _body(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length") or 0)
            if length <= 0:
                return {}
            try:
                return json.loads(self.rfile.read(length).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                return {}

        @staticmethod
        def _guess_type(name: str) -> str:
            if name.endswith(".js"):
                return "application/javascript; charset=utf-8"
            if name.endswith(".css"):
                return "text/css; charset=utf-8"
            return "application/octet-stream"

        # ---------- GET ----------
        def do_GET(self) -> None:  # noqa: N802 - http.server API
            """Serve UI assets and read-only JSON APIs.

            Preconditions:
                The request path is a UI asset, theme, or one of /api/status, /api/setup,
                /api/reports, /api/report/*, /api/trend/latest.
            Postconditions:
                A file response or JSON response is written; 404 JSON for unknown paths.
            Prohibitions:
                Do not expose secret values in /api/setup (only booleans and the keys-file path).
            Raises:
                None; handler-level errors are converted into HTTP responses.
            """
            path = urlparse(self.path).path
            if path == "/":
                return self._file(UI_DIR / "index.html", "text/html; charset=utf-8")
            if path.startswith("/static/"):
                name = Path(path[len("/static/"):]).name
                return self._file(UI_DIR / "static" / name, self._guess_type(name))
            if path.startswith("/themes/"):
                name = Path(path[len("/themes/"):]).name
                return self._file(UI_DIR / "themes" / name, "text/css; charset=utf-8")
            if path == "/api/setup":
                keys_file = config.root / KEY_FILENAME
                return self._json({
                    "deepseek_configured": bool(config.secret("DEEPSEEK_API_KEY", fallback_file="ds_key.txt")),
                    "github_configured": bool(config.secret("GITHUB_TOKEN")),
                    "keys_file": str(keys_file),
                    "keys_file_exists": keys_file.exists(),
                    "instructions": "在 keys.txt 中填写 KEY=VALUE；也兼容 .env / ds_key.txt",
                })
            if path == "/api/status":
                return self._json({"status": state.snapshot(), "reports": len(list_reports(config))})
            if path == "/api/reports":
                meta = [
                    {key: entry[key] for key in ("date", "item_count", "model", "degraded")}
                    for entry in list_reports(config)
                ]
                return self._json({"reports": meta})
            if path == "/api/report/latest":
                report = load_report(config)
                if report is None:
                    return self._json({"error": "no report yet"}, 404)
                return self._json({"report": report})
            if path.startswith("/api/report/"):
                date = path[len("/api/report/"):]
                report = load_report(config, date)
                if report is None:
                    return self._json({"error": "report not found"}, 404)
                return self._json({"report": report})
            if path == "/api/trend/latest":
                store = Store(config.db_path)
                store.init_schema()
                try:
                    trend = store.latest_trend()
                finally:
                    store.close()
                return self._json({"trend": trend})
            return self._json({"error": "not found"}, 404)

        # ---------- POST ----------
        def do_POST(self) -> None:  # noqa: N802 - http.server API
            """Handle run/trend commands.

            Preconditions:
                /api/run accepts an optional JSON body (no_llm/top/window_days/sources);
                /api/trend accepts an optional days value; config is loaded.
            Postconditions:
                202 for an accepted background run, 409 for a concurrent run, 200/503/404 for trend.
            Prohibitions:
                Do not start a second pipeline run while one is executing.
            Raises:
                None; failures are reported as JSON error responses.
            """
            path = urlparse(self.path).path
            if path == "/api/run":
                with state.lock:
                    if state.running:
                        return self._json({"error": "a report is already being generated"}, 409)
                    state.running = True
                    state.started_at = utc_now().strftime("%Y-%m-%dT%H:%M:%SZ")
                    state.finished_at = None
                    state.error = None
                    state.stats = {}
                options = self._body() or {}

                def worker() -> None:
                    try:
                        stats = run_pipeline(
                            config,
                            no_llm=bool(options.get("no_llm")),
                            top_n=options.get("top"),
                            window_days=options.get("window_days"),
                            source_ids=options.get("sources"),
                        )
                        with state.lock:
                            state.stats = stats
                    except Exception as exc:  # noqa: BLE001 - surfaced to UI
                        with state.lock:
                            state.error = str(exc)
                    finally:
                        with state.lock:
                            state.running = False
                            state.finished_at = utc_now().strftime("%Y-%m-%dT%H:%M:%SZ")

                threading.Thread(target=worker, daemon=True).start()
                return self._json({"status": "started"}, 202)

            if path == "/api/trend":
                options = self._body() or {}
                days = int(options.get("days") or config.get("trend.window_days", 14))
                store = Store(config.db_path)
                store.init_schema()
                try:
                    result = analyze_trends(config, store, days=days)
                finally:
                    store.close()
                status = 200 if result.get("status") == "ok" else 503 if result.get("status") == "no_key" else 404
                return self._json({"trend": result}, status)

            return self._json({"error": "not found"}, 404)

    return ApiHandler


def serve(config: Config, host: str = "127.0.0.1", port: int = 8765) -> None:
    """Start the local report UI server.

    Preconditions:
        host/port are valid and bindable; config is loaded.
    Postconditions:
        Creates the local keys.txt from its template on first run, then blocks
        until interrupted.
    Prohibitions:
        Do not bind 0.0.0.0 in normal use.
    Raises:
        OSError when the port is already in use.
    """
    handler = make_handler(config)
    key_path, key_created = ensure_key_file(config.root)
    if key_created:
        print(f"首次使用：已创建密钥文件 {key_path}，请填写 DEEPSEEK_API_KEY 后重启界面。")
    httpd = ThreadingHTTPServer((host, port), handler)
    print(f"AI News Agent UI: http://{host}:{port}  (Ctrl+C to stop)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopping...")
    finally:
        httpd.server_close()
