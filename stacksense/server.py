"""Local web UI and JSON API. Standard library only."""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from stacksense import __version__
from stacksense.decide import recommend

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
SCENARIOS = ROOT / "scenarios"


def llm_requested() -> bool:
    return os.environ.get("STACKSENSE_LLM", "off").strip().lower() in {"1", "on", "true", "yes"}


class Handler(BaseHTTPRequestHandler):
    server_version = "StackSense/1.0"

    def log_message(self, fmt: str, *args) -> None:
        sys_stderr = __import__("sys").stderr
        sys_stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, payload: object) -> None:
        body = (json.dumps(payload, indent=2) + "\n").encode("utf-8")
        self._send(code, body, "application/json; charset=utf-8")

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        if path in {"/", "/index.html"}:
            self._file(WEB / "index.html", "text/html; charset=utf-8")
            return
        if path == "/app.js":
            self._file(WEB / "app.js", "text/javascript; charset=utf-8")
            return
        if path == "/styles.css":
            self._file(WEB / "styles.css", "text/css; charset=utf-8")
            return
        if path == "/api/health":
            self._json(200, {
                "status": "ok",
                "version": __version__,
                "llm_requested": llm_requested(),
                "llm_called": False,
            })
            return
        if path.startswith("/scenarios/"):
            name = path[len("/scenarios/"):]
            if ".." in name or name.startswith("/"):
                self._json(404, {"error": "not found"})
                return
            target = SCENARIOS / name
            if target.is_file():
                self._file(target, "application/json; charset=utf-8")
                return
        self._json(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        if path != "/api/recommend":
            self._json(404, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length > 2_000_000:
            self._json(400, {"error": "body too large"})
            return
        raw_bytes = self.rfile.read(length) if length else b""
        try:
            raw = json.loads(raw_bytes.decode("utf-8") or "null")
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            self._json(200, recommend({"_bad_json": str(exc)[:200]} if False else _bad_json(exc)))
            return
        if isinstance(raw, list):
            self._json(200, [recommend(item) for item in raw])
            return
        self._json(200, recommend(raw))

    def _file(self, path: Path, content_type: str) -> None:
        if not path.is_file():
            self._json(404, {"error": "not found"})
            return
        self._send(200, path.read_bytes(), content_type)


def _bad_json(exc: Exception) -> dict:
    from stacksense.decide import _invalid
    return _invalid(None, [{"field": "(file)", "message": f"Invalid JSON: {exc}"}], [])


def serve() -> None:
    host = os.environ.get("STACKSENSE_HOST", "127.0.0.1")
    port = int(os.environ.get("STACKSENSE_PORT", "8000"))
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"StackSense {__version__} on http://{host}:{port}  (LLM requested: {llm_requested()}, called: false)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        httpd.server_close()
