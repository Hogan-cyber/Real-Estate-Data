"""One bounded, immutable Arrow snapshot per Python session; no disk cache."""
import datetime as dt
import threading
import time

MAX_BYTES = 8 * 1024 * 1024
_entry = None
_lock = threading.RLock()


def clear():
    global _entry
    with _lock:
        _entry = None


def discard(key):
    global _entry
    with _lock:
        if _entry is not None and _entry[0] == key:
            _entry = None


def get_or_load(key, loader, *, refresh=False):
    global _entry
    # Single flight for simultaneous first reads; publish only a fully validated
    # immutable table. A failed forced refresh leaves no stale entry to reuse.
    with _lock:
        if refresh:
            _entry = None
        if _entry is not None and _entry[0] == key:
            return _entry[3]
        snapshot = loader()
        if snapshot['table'].get_total_buffer_size() <= MAX_BYTES:
            _entry = (key, time.monotonic(), dt.datetime.now(dt.timezone.utc).isoformat(), snapshot)
        else:
            _entry = None
        return snapshot


def info():
    with _lock:
        snapshot = _entry[3] if _entry else None
        return dict(entries=int(_entry is not None), bytes=snapshot['table'].get_total_buffer_size() if snapshot else 0,
                    max_bytes=MAX_BYTES, ttl_seconds=None, policy='session; explicit refresh',
                    age_seconds=max(0,time.monotonic()-_entry[1]) if _entry else 0,
                    loaded_at=_entry[2] if _entry else None,
                    source=snapshot['source'] if snapshot else None,
                    downloaded_bytes=snapshot['downloaded_bytes'] if snapshot else 0,
                    data_generated_at=(snapshot['table'].schema.metadata or {}).get(
                        b'hk_property_data.generated_at', b'').decode() or None if snapshot else None)
