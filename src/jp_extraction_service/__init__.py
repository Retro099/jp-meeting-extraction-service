"""Japanese meeting-notes extraction service."""

from typing import Any

__version__ = "0.0.1"
MAX_NOTE_CHARS = 4000


def handle_extract(*args: Any, **kwargs: Any) -> Any:
    from jp_extraction_service.handler import handle_extract as _handle_extract

    return _handle_extract(*args, **kwargs)


__all__ = ["__version__", "MAX_NOTE_CHARS", "handle_extract"]
