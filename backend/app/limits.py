"""Upload validation and a small in-memory rate limiter for a free public tool."""

from __future__ import annotations

import io
import threading
import time
import zipfile
from collections import defaultdict, deque

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 150 * 1024 * 1024
MAX_ZIP_ENTRIES = 3000
MAX_BLOCKS = 3000


class UploadError(ValueError):
    """Raised with a message that is safe to show to the user."""


def validate_docx(data: bytes) -> None:
    if not data:
        raise UploadError("The file is empty.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise UploadError("The file is larger than 10 MB.")
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            infos = zf.infolist()
            names = {i.filename for i in infos}
            if len(infos) > MAX_ZIP_ENTRIES or sum(i.file_size for i in infos) > MAX_UNCOMPRESSED_BYTES:
                raise UploadError("The file is too large once unpacked.")
            if "word/document.xml" not in names:
                raise UploadError("This does not look like a Word (.docx) document.")
            if any(n.lower().endswith("vbaproject.bin") for n in names):
                raise UploadError("Documents with macros (.docm) are not supported. Save it as .docx first.")
    except zipfile.BadZipFile as exc:
        raise UploadError("This is not a valid .docx file. Older .doc files must be saved as .docx first.") from exc


class RateLimiter:
    """Sliding-window limit per client key (IP address)."""

    def __init__(self, max_requests: int, window_seconds: float):
        self.max_requests = max_requests
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] > self.window:
                hits.popleft()
            if len(hits) >= self.max_requests:
                return False
            hits.append(now)
            if len(self._hits) > 10_000:  # keep memory bounded
                for k in [k for k, v in self._hits.items() if not v]:
                    del self._hits[k]
            return True
