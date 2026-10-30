"""In-process data revision counters used for deterministic cache invalidation."""
from threading import Lock

_LOCK = Lock()
_VERSIONS: dict[str, int] = {}


def get_data_version(dataset: str) -> int:
    with _LOCK:
        return _VERSIONS.get(dataset, 0)


def bump_data_version(dataset: str) -> int:
    with _LOCK:
        version = _VERSIONS.get(dataset, 0) + 1
        _VERSIONS[dataset] = version
        return version
