"""Build a Linux x86_64 Python 3.13 AWS Lambda deployment ZIP without Windows binaries or UI bloat."""

from __future__ import annotations

import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = ROOT / "dist"
STAGE_DIR = ROOT / "build" / "lambda_stage"
ZIP_PATH = DIST_DIR / "lambda_deploy.zip"
CORE_REQ = "jp-meeting-to-crm-fields @ git+https://github.com/Retro099/jp-meeting-to-crm-fields@7e24c95524d1387f7143628ef5bc0d61a06e7890"


def _run(cmd: list[str]) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True)


def build_zip() -> Path:
    if STAGE_DIR.exists():
        shutil.rmtree(STAGE_DIR)
    STAGE_DIR.mkdir(parents=True, exist_ok=True)
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()

    py = sys.executable

    # 1. Install OpenAI SDK and its dependencies for Linux x86_64 Python 3.13 (binary wheels only)
    _run(
        [
            py,
            "-m",
            "pip",
            "install",
            "--no-cache-dir",
            "--target",
            str(STAGE_DIR),
            "--platform",
            "manylinux2014_x86_64",
            "--implementation",
            "cp",
            "--python-version",
            "3.13",
            "--only-binary=:all:",
            "openai==3.22.1",
        ]
    )

    # 2. Install pinned pure-Python core crm_extractor without Streamlit/Pandas UI extras
    _run(
        [
            py,
            "-m",
            "pip",
            "install",
            "--no-cache-dir",
            "--no-deps",
            "--target",
            str(STAGE_DIR),
            CORE_REQ,
        ]
    )

    # 3. Copy service package
    shutil.copytree(ROOT / "src" / "jp_extraction_service", STAGE_DIR / "jp_extraction_service")

    # 4. Prune caches, CLI stubs (Windows pip --target generates bin/*.exe), and UI entrypoints
    bin_dir = STAGE_DIR / "bin"
    if bin_dir.exists():
        shutil.rmtree(bin_dir)
    for pattern in ("__pycache__", "*.pyc", "*.pyo", "app.py"):
        for match in STAGE_DIR.rglob(pattern):
            if match.is_dir():
                shutil.rmtree(match)
            else:
                match.unlink()

    bad_exts = (".pyd", ".dll", ".exe", ".env")
    bad_files: list[str] = []
    file_count = 0
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in sorted(STAGE_DIR.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(STAGE_DIR).as_posix()
            if rel.lower().endswith(bad_exts) or ".secrets" in rel.lower():
                bad_files.append(rel)
            zf.write(path, rel)
            file_count += 1

    if bad_files:
        raise RuntimeError(f"Disallowed files found in Lambda ZIP: {bad_files}")

    size_mb = ZIP_PATH.stat().st_size / (1024 * 1024)
    print(f"Built {ZIP_PATH} ({file_count} files, {size_mb:.2f} MiB)")
    return ZIP_PATH


if __name__ == "__main__":
    build_zip()
