"""In-memory URL shortening backed by custom hash tables."""

from urllib.parse import urlsplit

from src.base62 import encode
from src.hash_table import HashTable


_url_to_code: HashTable[str] = HashTable()
_code_to_url: HashTable[str] = HashTable()
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
