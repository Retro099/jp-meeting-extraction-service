"""Japanese meeting-notes extraction service (in progress)."""

from jp_extraction_service.handler import MAX_NOTE_CHARS, handle_extract

__version__ = "0.0.1"
__all__ = ["__version__", "MAX_NOTE_CHARS", "handle_extract"]
