"""Step 3: Local API handler and HTTP server for Japanese meeting-notes extraction.

Reuses the pinned core package (crm_extractor from jp-meeting-to-crm-fields v1.0.0)
without rewriting prompts, extraction calls, or prompt-injection defenses.
Compatible with local dict/JSON invocations, local HTTP testing, and AWS Lambda events (Step 4).
"""

from __future__ import annotations

import base64
import hmac
import json
import logging
import os
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Callable

MAX_NOTE_CHARS = 4000
DEFAULT_DAILY_CAP = 50
CRM_FIELDS = ["会社名", "相手", "次アクション", "期限", "リスク"]
NOT_FOUND = "未検出"

logger = logging.getLogger("jp_extraction_service")

_daily_lock = threading.Lock()
_daily_state: dict[str, Any] = {"date": "", "count": 0}


def reset_daily_counter() -> None:
    """Reset the soft in-memory per-container daily request counter (for tests)."""
    with _daily_lock:
        _daily_state["date"] = ""
        _daily_state["count"] = 0


def _get_daily_cap() -> int:
    raw = os.getenv("DAILY_REQUEST_CAP", str(DEFAULT_DAILY_CAP)).strip()
    try:
        cap = int(raw)
        return cap if cap > 0 else DEFAULT_DAILY_CAP
    except ValueError:
        return DEFAULT_DAILY_CAP


def _consume_daily_slot() -> tuple[bool, int, int]:
    """Increment soft per-container UTC daily counter if under cap.

    Note: In AWS Lambda this counter lives in container memory and resets on cold starts
    or across concurrent warm instances. It is a best-effort soft guard, not a hard global limit.
    """
    cap = _get_daily_cap()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with _daily_lock:
        if _daily_state["date"] != today:
            _daily_state["date"] = today
            _daily_state["count"] = 0
        if _daily_state["count"] >= cap:
            return False, _daily_state["count"], cap
        _daily_state["count"] += 1
        return True, _daily_state["count"], cap


def _default_defenses_enabled() -> bool:
    try:
        from crm_extractor.security import defenses_enabled

        return bool(defenses_enabled())
    except ImportError:
        val = os.getenv("DEFENSES_ENABLED", "1").strip().lower()
        return val in {"1", "true", "yes", "on"}


def _build_default_client() -> Any:
    api_key = os.getenv("AICREDITS_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("AICREDITS_API_KEY is not configured")
    from crm_extractor.prompts import API_BASE_URL
    from openai import OpenAI

    return OpenAI(
        api_key=api_key,
        base_url=API_BASE_URL,
        timeout=50,
        max_retries=0,
    )


def _get_default_extractor() -> Callable[[Any, str], dict[str, Any]]:
    from crm_extractor.extractor import extract_crm_data

    return extract_crm_data


def _response(status_code: int, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json; charset=utf-8"},
        "body": json.dumps(payload, ensure_ascii=False),
    }


def _calculate_estimated_cost(prompt_tokens: int | None, completion_tokens: int | None) -> tuple[float, float]:
    """Estimate Qwen 2.5 72B inference cost in USD and INR.

    Rates: $0.0004 / 1k prompt tokens, $0.0012 / 1k completion tokens.
    Exchange rate: ~85.0 INR/USD.
    """
    pt = prompt_tokens or 0
    ct = completion_tokens or 0
    usd = (pt * 0.0004 / 1000.0) + (ct * 0.0012 / 1000.0)
    inr = usd * 85.0
    return round(usd, 6), round(inr, 4)


def _check_auth(event: dict[str, Any] | None) -> tuple[bool, str | None]:
    """Verify API key authentication if EXTRACTION_API_KEY is configured.

    If EXTRACTION_API_KEY is not set, requests are allowed (local development/mock mode).
    Uses hmac.compare_digest to prevent timing side-channels.
    """
    expected_key = os.getenv("EXTRACTION_API_KEY", "").strip()
    if not expected_key:
        return True, None

    if not isinstance(event, dict):
        return False, "Unauthorized: missing request headers."

    headers = event.get("headers") or {}
    normalized_headers = {k.lower(): v for k, v in headers.items()}
    auth_header = str(normalized_headers.get("authorization", "")).strip()
    bearer_token = auth_header[7:].strip() if auth_header.lower().startswith("bearer ") else ""
    provided_key = str(normalized_headers.get("x-api-key") or bearer_token or "").strip()

    if not provided_key or not hmac.compare_digest(provided_key, expected_key):
        return False, "Unauthorized: invalid or missing API key."

    return True, None


def _decode_raw_body(raw_body: str, is_b64: bool) -> tuple[str | None, str | None]:
    if not is_b64:
        return raw_body, None
    try:
        decoded_bytes = base64.b64decode(raw_body, validate=True)
        return decoded_bytes.decode("utf-8"), None
    except (ValueError, UnicodeDecodeError):
        return None, "Malformed base64-encoded request body."


def _parse_event_payload(event: dict[str, Any] | str | None) -> tuple[dict[str, Any] | None, str | None]:
    if event is None:
        return None, "Request payload must be a JSON object."
    if isinstance(event, str):
        try:
            parsed = json.loads(event)
        except json.JSONDecodeError:
            return None, "Malformed JSON in request body."
        if not isinstance(parsed, dict):
            return None, "Request body must decode to a JSON object."
        return parsed, None
    if not isinstance(event, dict):
        return None, "Request payload must be a JSON object."
    if "body" in event and "note" not in event:
        raw_body = event.get("body")
        if raw_body is None:
            return None, "Request body is empty."
        if isinstance(raw_body, str):
            decoded_body, b64_err = _decode_raw_body(raw_body, bool(event.get("isBase64Encoded")))
            if b64_err is not None or decoded_body is None:
                return None, b64_err or "Malformed base64-encoded request body."
            try:
                parsed = json.loads(decoded_body)
            except json.JSONDecodeError:
                return None, "Malformed JSON in request body."
            if not isinstance(parsed, dict):
                return None, "Request body must decode to a JSON object."
            return parsed, None
        if isinstance(raw_body, dict):
            return raw_body, None
        return None, "Invalid request body format."
    return event, None


def handle_extract(
    event: dict[str, Any] | str | None,
    context: Any = None,
    *,
    client: Any = None,
    extractor_fn: Callable[[Any, str], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Process a single meeting-note extraction request and return an HTTP-style response dict."""
    del context  # unused in Step 3 local handler; reserved for Step 4 Lambda signature

    if isinstance(event, dict):
        method = str(
            event.get("httpMethod")
            or event.get("requestContext", {}).get("http", {}).get("method")
            or "POST"
        ).upper()
        path = str(event.get("path") or event.get("rawPath") or "/extract")
        if method == "GET" and path.rstrip("/") in {"", "/health", "/healthz"}:
            return _response(
                200,
                {
                    "status": "ok",
                    "version": "0.0.1",
                    "defenses_enabled": _default_defenses_enabled(),
                },
            )
        if method not in {"POST"}:
            return _response(405, {"ok": False, "error": f"Method {method} not allowed."})

        is_auth, auth_err = _check_auth(event)
        if not is_auth:
            return _response(401, {"ok": False, "error": auth_err or "Unauthorized."})

    payload, err = _parse_event_payload(event)
    if err is not None or payload is None:
        return _response(400, {"ok": False, "error": err or "Invalid request payload."})

    note = payload.get("note")
    if not isinstance(note, str) or not note.strip():
        return _response(400, {"ok": False, "error": "Field 'note' must be a non-empty string."})

    if len(note) > MAX_NOTE_CHARS:
        return _response(
            400,
            {"ok": False, "error": f"Field 'note' exceeds maximum length of {MAX_NOTE_CHARS} characters."},
        )

    if extractor_fn is None:
        try:
            extractor_fn = _get_default_extractor()
        except Exception as exc:
            return _response(500, {"ok": False, "error": f"Core extractor unavailable: {exc}"})

    if client is None:
        try:
            client = _build_default_client()
        except Exception as exc:
            return _response(500, {"ok": False, "error": str(exc)})

    allowed, _, cap = _consume_daily_slot()
    if not allowed:
        return _response(
            429,
            {
                "ok": False,
                "error": f"Daily demo request cap reached ({cap}/day soft per-container limit).",
            },
        )

    try:
        result = extractor_fn(client, note)
    except Exception as exc:
        return _response(502, {"ok": False, "error": f"Upstream extraction call failed: {exc}"})

    if not isinstance(result, dict) or not result.get("success"):
        err_msg = result.get("error") if isinstance(result, dict) else None
        return _response(
            502,
            {"ok": False, "error": str(err_msg or "Extraction failed.")},
        )

    raw_data = result.get("data")
    if not isinstance(raw_data, dict):
        raw_data = {}
    fields = {field: str(raw_data.get(field, NOT_FOUND)) for field in CRM_FIELDS}

    prompt_tokens = result.get("prompt_tokens")
    completion_tokens = result.get("completion_tokens")
    latency_s = result.get("latency")
    est_usd, est_inr = _calculate_estimated_cost(prompt_tokens, completion_tokens)

    log_entry = {
        "event": "extraction_complete",
        "status": 200,
        "latency_s": latency_s,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": (prompt_tokens or 0) + (completion_tokens or 0),
        "estimated_cost_usd": est_usd,
        "estimated_cost_inr": est_inr,
        "defenses_enabled": _default_defenses_enabled(),
    }
    logger.info(json.dumps(log_entry, ensure_ascii=False))

    return _response(
        200,
        {
            "ok": True,
            "data": fields,
            "meta": {
                "defenses_enabled": _default_defenses_enabled(),
                "latency_s": latency_s,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "estimated_cost_usd": est_usd,
                "estimated_cost_inr": est_inr,
            },
        },
    )


def make_http_handler(
    *,
    client: Any = None,
    extractor_fn: Callable[[Any, str], dict[str, Any]] | None = None,
) -> type[BaseHTTPRequestHandler]:
    """Create a stdlib BaseHTTPRequestHandler bound to `handle_extract` for local runs and tests."""

    class ExtractionHTTPRequestHandler(BaseHTTPRequestHandler):
        def _send(self, result: dict[str, Any]) -> None:
            body_bytes = result["body"].encode("utf-8")
            self.send_response(int(result["statusCode"]))
            for k, v in result.get("headers", {}).items():
                self.send_header(k, v)
            self.send_header("Content-Length", str(len(body_bytes)))
            self.end_headers()
            self.wfile.write(body_bytes)

        def do_GET(self) -> None:  # noqa: N802
            headers_dict = {k: v for k, v in self.headers.items()}
            res = handle_extract(
                {"httpMethod": "GET", "path": self.path, "headers": headers_dict},
                client=client,
                extractor_fn=extractor_fn,
            )
            self._send(res)

        def do_POST(self) -> None:  # noqa: N802
            if self.path.rstrip("/") not in {"", "/extract"}:
                self._send(_response(404, {"ok": False, "error": "Not found."}))
                return
            length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(length).decode("utf-8", errors="replace")
            headers_dict = {k: v for k, v in self.headers.items()}
            res = handle_extract(
                {"httpMethod": "POST", "path": self.path, "body": raw_body, "headers": headers_dict},
                client=client,
                extractor_fn=extractor_fn,
            )
            self._send(res)

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            return

    return ExtractionHTTPRequestHandler


def run_local_server(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Run the local HTTP extraction server on http://<host>:<port>."""
    os.environ.setdefault("DEFENSES_ENABLED", "1")
    server = HTTPServer((host, port), make_http_handler())
    print(f"Serving jp-meeting-extraction-service on http://{host}:{port} (POST /extract, GET /health)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    run_local_server()
