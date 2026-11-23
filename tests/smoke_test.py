"""HTTP Server Smoke Test for CI: verifies module invocation, health endpoint, and safe error rejection."""

from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.error
import urllib.request


def run_smoke_test(host: str = "127.0.0.1", port: int = 8000) -> None:
    print(f"Starting jp_extraction_service.handler on {host}:{port}...")
    proc = subprocess.Popen([sys.executable, "-m", "jp_extraction_service.handler"])
    time.sleep(2)

    try:
        # 1. Test GET /health
        health_url = f"http://{host}:{port}/health"
        print(f"Checking GET {health_url}...")
        with urllib.request.urlopen(health_url, timeout=5) as resp:
            assert resp.status == 200, f"Expected status 200, got {resp.status}"
            data = json.loads(resp.read().decode("utf-8"))
            assert data.get("status") == "ok", f"Unexpected health response: {data}"
            assert "version" in data
            print(f"[PASS] Health check: {data}")

        # 2. Test POST /extract without upstream API key
        extract_url = f"http://{host}:{port}/extract"
        print(f"Checking POST {extract_url} without AICREDITS_API_KEY...")
        req = urllib.request.Request(
            extract_url,
            data=json.dumps({"note": "テスト商談メモ"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(req, timeout=5)
            raise AssertionError("Expected HTTP 500 error when AICREDITS_API_KEY is not configured")
        except urllib.error.HTTPError as err:
            assert err.code == 500, f"Expected 500 error, got {err.code}"
            err_data = json.loads(err.read().decode("utf-8"))
            assert err_data.get("ok") is False
            assert "AICREDITS_API_KEY" in err_data.get("error", "")
            print(f"[PASS] Safe rejection without key: {err_data}")

        print("=== Smoke test PASSED successfully ===")
    finally:
        proc.terminate()
        proc.wait(timeout=5)


if __name__ == "__main__":
    run_smoke_test()
