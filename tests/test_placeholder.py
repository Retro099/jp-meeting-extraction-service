import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import jp_extraction_service  # noqa: E402


def test_version():
    assert jp_extraction_service.__version__ == "0.0.1"
