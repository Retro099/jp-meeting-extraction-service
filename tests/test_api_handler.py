"""Step 3 tests: local API handler and HTTP server tests (no live network)."""

import json
import sys
import threading
import urllib.error
import urllib.request
from http.server import HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jp_extraction_service.handler import (  # noqa: E402
    CRM_FIELDS,
    MAX_NOTE_CHARS,
    NOT_FOUND,
    handle_extract,
    make_http_handler,
)

SAMPLE_NOTE = "本日は株式会社さくら商事の佐藤様と打ち合わせ。来週金曜までに御見積書を送付する。特段のリスクはなし。"


def _fake_extractor_ok(client, note_text):
    assert client == "dummy-client"
    assert isinstance(note_text, str)
    return {
        "success": True,
        "data": {
            "会社名": "株式会社さくら商事",
            "相手": "佐藤様",
            "次アクション": "御見積書を送付する",
            "期限": "来週金曜",
            "リスク": NOT_FOUND,
        },
        "raw": "{}",
        "latency": 0.42,
        "prompt_tokens": 180,
        "completion_tokens": 45,
        "error": None,
    }


def _fake_extractor_fail(client, note_text):
    return {
        "success": False,
        "data": {},
        "raw": None,
        "latency": 0.12,
        "prompt_tokens": None,
        "completion_tokens": None,
        "error": "upstream timeout",
    }


def test_handle_extract_success_dict_payload():
    res = handle_extract(
        {"note": SAMPLE_NOTE},
        client="dummy-client",
        extractor_fn=_fake_extractor_ok,
    )
    assert res["statusCode"] == 200
    body = json.loads(res["body"])
    assert body["ok"] is True
    assert set(body["data"].keys()) == set(CRM_FIELDS)
    assert body["data"]["会社名"] == "株式会社さくら商事"
    assert body["data"]["相手"] == "佐藤様"
    assert body["data"]["リスク"] == NOT_FOUND
    assert body["meta"]["latency_s"] == 0.42
    assert body["meta"]["prompt_tokens"] == 180
    assert body["meta"]["completion_tokens"] == 45


def test_handle_extract_lambda_style_body_string():
    event = {
        "httpMethod": "POST",
        "path": "/extract",
        "body": json.dumps({"note": SAMPLE_NOTE}, ensure_ascii=False),
    }
    res = handle_extract(event, client="dummy-client", extractor_fn=_fake_extractor_ok)
    assert res["statusCode"] == 200
    body = json.loads(res["body"])
    assert body["ok"] is True
    assert body["data"]["期限"] == "来週金曜"


def test_handle_extract_health_check():
    res = handle_extract({"httpMethod": "GET", "path": "/health"})
    assert res["statusCode"] == 200
    body = json.loads(res["body"])
    assert body["status"] == "ok"
    assert body["version"] == "0.0.1"


def test_handle_extract_rejects_empty_or_missing_note():
    for bad in [{}, {"note": ""}, {"note": "   "}, {"note": 123}]:
        res = handle_extract(bad, client="dummy-client", extractor_fn=_fake_extractor_ok)
        assert res["statusCode"] == 400
        body = json.loads(res["body"])
        assert body["ok"] is False
        assert "note" in body["error"]


def test_handle_extract_rejects_oversized_note():
    long_note = "あ" * (MAX_NOTE_CHARS + 1)
    res = handle_extract(
        {"note": long_note},
        client="dummy-client",
        extractor_fn=_fake_extractor_ok,
    )
    assert res["statusCode"] == 400
    body = json.loads(res["body"])
    assert body["ok"] is False
    assert str(MAX_NOTE_CHARS) in body["error"]


def test_handle_extract_rejects_malformed_json():
    res = handle_extract(
        {"httpMethod": "POST", "path": "/extract", "body": "{not-valid-json"},
        client="dummy-client",
        extractor_fn=_fake_extractor_ok,
    )
    assert res["statusCode"] == 400
    body = json.loads(res["body"])
    assert body["ok"] is False


def test_handle_extract_rejects_wrong_method():
    res = handle_extract(
        {"httpMethod": "DELETE", "path": "/extract"},
        client="dummy-client",
        extractor_fn=_fake_extractor_ok,
    )
    assert res["statusCode"] == 405


def test_handle_extract_upstream_failure_returns_502():
    res = handle_extract(
        {"note": SAMPLE_NOTE},
        client="dummy-client",
        extractor_fn=_fake_extractor_fail,
    )
    assert res["statusCode"] == 502
    body = json.loads(res["body"])
    assert body["ok"] is False
    assert "upstream timeout" in body["error"]


def test_local_http_server_roundtrip():
    handler_cls = make_http_handler(client="dummy-client", extractor_fn=_fake_extractor_ok)
    server = HTTPServer(("127.0.0.1", 0), handler_cls)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=5) as resp:
            assert resp.status == 200
            health = json.loads(resp.read().decode("utf-8"))
            assert health["status"] == "ok"

        req_data = json.dumps({"note": SAMPLE_NOTE}, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/extract",
            data=req_data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            assert resp.status == 200
            out = json.loads(resp.read().decode("utf-8"))
            assert out["ok"] is True
            assert out["data"]["会社名"] == "株式会社さくら商事"
    finally:
        server.shutdown()
        server.server_close()


def test_handle_extract_api_key_auth(monkeypatch):
    monkeypatch.setenv("EXTRACTION_API_KEY", "secret-test-key-123")

    # 1. Missing key returns 401
    res_no_key = handle_extract(
        {"httpMethod": "POST", "path": "/extract", "body": json.dumps({"note": SAMPLE_NOTE})},
        client="dummy-client",
        extractor_fn=_fake_extractor_ok,
    )
    assert res_no_key["statusCode"] == 401
    assert "Unauthorized" in json.loads(res_no_key["body"])["error"]

    # 2. Invalid key returns 401
    res_bad_key = handle_extract(
        {
            "httpMethod": "POST",
            "path": "/extract",
            "headers": {"x-api-key": "wrong-key"},
            "body": json.dumps({"note": SAMPLE_NOTE}),
        },
        client="dummy-client",
        extractor_fn=_fake_extractor_ok,
    )
    assert res_bad_key["statusCode"] == 401

    # 3. Valid key in x-api-key returns 200
    res_ok_header = handle_extract(
        {
            "httpMethod": "POST",
            "path": "/extract",
            "headers": {"x-api-key": "secret-test-key-123"},
            "body": json.dumps({"note": SAMPLE_NOTE}),
        },
        client="dummy-client",
        extractor_fn=_fake_extractor_ok,
    )
    assert res_ok_header["statusCode"] == 200

    # 4. Valid key in Authorization: Bearer returns 200
    res_ok_bearer = handle_extract(
        {
            "httpMethod": "POST",
            "path": "/extract",
            "headers": {"Authorization": "Bearer secret-test-key-123"},
            "body": json.dumps({"note": SAMPLE_NOTE}),
        },
        client="dummy-client",
        extractor_fn=_fake_extractor_ok,
    )
    assert res_ok_bearer["statusCode"] == 200
