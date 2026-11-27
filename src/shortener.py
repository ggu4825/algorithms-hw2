"""In-memory URL shortening backed by custom hash tables."""

from typing import Literal
from urllib.parse import urlsplit

from src.base62 import encode
from src.hash_table import HashTable, LinearProbingHashTable


Backend = Literal["chaining", "linear"]
_Table = HashTable[str] | LinearProbingHashTable[str]

_table_backend: Backend = "chaining"
_url_to_code: _Table = HashTable()
_code_to_url: _Table = HashTable()
_next_identifier = 0


def _new_table(backend: Backend, capacity: int) -> _Table:
    if backend == "linear":
        return LinearProbingHashTable(capacity)
    return HashTable(capacity)


def get_backend() -> Backend:
    """Return the active hash-table implementation."""
    return _table_backend


def configure_backend(backend: Backend) -> None:
    """Switch table implementations while preserving stored URLs and codes."""
    global _table_backend, _url_to_code, _code_to_url

    if backend not in ("chaining", "linear"):
        raise ValueError("backend must be 'chaining' or 'linear'")
    if backend == _table_backend:
        return

    capacity = max(
        _url_to_code.capacity,
        _code_to_url.capacity,
        len(_url_to_code) + 1,
        len(_code_to_url) + 1,
    )
    new_url_to_code = _new_table(backend, capacity)
    new_code_to_url = _new_table(backend, capacity)
    for url, code in _url_to_code.items():
        new_url_to_code.put(url, code)
    for code, url in _code_to_url.items():
        new_code_to_url.put(code, url)

    _table_backend = backend
    _url_to_code = new_url_to_code
    _code_to_url = new_code_to_url


def reset_state(backend: Backend | None = None) -> None:
    """Clear stored URLs and optionally select a backend."""
    global _url_to_code, _code_to_url, _next_identifier

    if backend is not None:
        configure_backend(backend)
    capacity = max(_url_to_code.capacity, _code_to_url.capacity)
    _url_to_code = _new_table(_table_backend, capacity)
    _code_to_url = _new_table(_table_backend, capacity)
    _next_identifier = 0


def _validate_url(url: str) -> None:
    if not isinstance(url, str):
        raise TypeError("url must be a string")
    if not url:
        raise ValueError("url must not be empty")
    if len(url) > 2048:
        raise ValueError("url must be at most 2048 characters")
    if any(character.isspace() for character in url):
        raise ValueError("url must not contain whitespace")

    try:
        parsed = urlsplit(url)
        hostname = parsed.hostname
        parsed.port
    except ValueError:
        raise ValueError("url is invalid") from None

    if parsed.scheme.lower() not in ("http", "https") or not hostname:
        raise ValueError("url must be an absolute HTTP or HTTPS URL with a host")


def shorten(url: str) -> str:
    """Return a stable base62 code for an absolute HTTP(S) URL."""
    global _next_identifier

    _validate_url(url)
    if _url_to_code.contains(url):
        code = _url_to_code.get(url)
        if code is not None:
            return code

    code = encode(_next_identifier)
    _url_to_code.put(url, code)
    _code_to_url.put(code, url)
    _next_identifier += 1
    return code


def expand(code: str) -> str:
    """Return the URL associated with code, raising KeyError if unknown."""
    if not _code_to_url.contains(code):
        raise KeyError(code)

    url = _code_to_url.get(code)
    if url is None:
        raise KeyError(code)
    return url
