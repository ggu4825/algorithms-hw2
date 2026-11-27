"""HTTP server for the in-memory URL shortener."""

from __future__ import annotations

import argparse
import html
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock
from urllib.parse import parse_qs, unquote, urlsplit

import src.shortener as shortener
from src.hash_table import HashTable, LinearProbingHashTable
from src.shortener import configure_backend, expand, get_backend, shorten


_MAX_FORM_BYTES = 32_768
_STATE_LOCK = Lock()

_PAGE_STYLE = """
body { font-family: sans-serif; margin: 2rem auto; max-width: 70rem; padding: 0 1rem; }
input[type=url] { box-sizing: border-box; max-width: 42rem; padding: .6rem; width: 100%; }
button { cursor: pointer; margin-top: .6rem; padding: .6rem 1rem; }
.result, .error { border: 1px solid #bbb; margin: 1rem 0; padding: 1rem; }
.error { border-color: #b91c1c; color: #991b1b; }
.buckets { border-collapse: collapse; width: 100%; }
.buckets th, .buckets td { border: 1px solid #bbb; padding: .5rem; text-align: left; vertical-align: top; }
.chain { align-items: stretch; display: flex; flex-wrap: wrap; gap: .5rem; }
.node { border: 1px solid #888; border-radius: .3rem; max-width: 32rem; overflow-wrap: anywhere; padding: .6rem; }
.arrow { align-self: center; font-size: 1.4rem; }
code { overflow-wrap: anywhere; white-space: pre-wrap; }
"""


def _page(title: str, content: str) -> str:
    return (
        "<!doctype html><html lang=\"ko\"><head><meta charset=\"utf-8\">"
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{html.escape(title)}</title><style>{_PAGE_STYLE}</style></head>"
        f"<body><h1>{html.escape(title)}</h1>{content}</body></html>"
    )


def _horner_steps(key: str, capacity: int) -> str:
    value = 0
    steps = ["h₀ = 0"]
    for character in key:
        previous = value
        value = (31 * value + ord(character)) % capacity
        steps.append(
            f"h = (31 × {previous} + ord({character!r})) mod "
            f"{capacity} = {value}"
        )
    return "\n".join(steps) + f"\nindex = {value}"


def _node_html(
    key: str,
    value: str,
    code: str,
    short_link: str,
    capacity: int,
    key_label: str,
    value_label: str,
    probe_count: int | None = None,
) -> str:
    safe_link = html.escape(short_link, quote=True)
    probe_detail = (
        f"<br><strong>탐사 거리:</strong> {probe_count}칸"
        if probe_count is not None
        else ""
    )
    return (
        '<div class="node">'
        f"<strong>{html.escape(key_label)}:</strong> "
        f"{html.escape(key)}<br>"
        f"<strong>{html.escape(value_label)}:</strong> "
        f"{html.escape(value)}<br>"
        f"{probe_detail}"
        f"<strong>짧은 코드:</strong> {html.escape(code)}<br>"
        f'<strong>짧은 링크:</strong> <a href="{safe_link}">{safe_link}</a>'
        "<details><summary>호너 해시 계산 과정</summary>"
        f"<code>{html.escape(_horner_steps(key, capacity))}</code>"
        "</details></div>"
    )


def _table_html(
    table: HashTable[str] | LinearProbingHashTable[str],
    origin: str,
    title: str,
    key_label: str,
    value_label: str,
    url_is_key: bool,
) -> str:
    rows = []
    if isinstance(table, LinearProbingHashTable):
        for index, entry in enumerate(table._slots):
            if entry is None:
                rows.append(f"<tr><th>{index}</th><td>비어 있음</td></tr>")
                continue
            code = entry.value if url_is_key else entry.key
            short_link = f"{origin}/{code}"
            node_html = _node_html(
                entry.key,
                entry.value,
                code,
                short_link,
                table.capacity,
                key_label,
                value_label,
                table.probe_count(entry.key),
            )
            rows.append(f'<tr><th>{index}</th><td>{node_html}</td></tr>')
        return (
            f"<h2>{html.escape(title)}</h2>"
            '<table class="buckets"><thead><tr><th>칸</th><th>저장 항목</th>'
            "</tr></thead><tbody>"
            + "".join(rows)
            + "</tbody></table>"
        )

    for index, first_node in enumerate(table._buckets):
        chain = []
        node = first_node
        while node is not None:
            if url_is_key:
                code = node.value
            else:
                code = node.key
            short_link = f"{origin}/{code}"
            chain.append(
                _node_html(
                    node.key,
                    node.value,
                    code,
                    short_link,
                    table.capacity,
                    key_label,
                    value_label,
                )
            )
            node = node.next

        chain_html = (
            '<div class="chain">'
            + '<span class="arrow">→</span>'.join(chain)
            + "</div>"
            if chain
            else "비어 있음"
        )
        rows.append(f"<tr><th>{index}</th><td>{chain_html}</td></tr>")

    return (
        f"<h2>{html.escape(title)}</h2>"
        '<table class="buckets"><thead><tr><th>칸</th><th>연결 리스트</th>'
        "</tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )


class ShortenerRequestHandler(BaseHTTPRequestHandler):
    """Render the shortener UI and serve redirects."""

    server_version = "URLShortener/1.0"

    def _send_html(self, status: int, content: str) -> None:
        body = content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _request_origin(self) -> str:
        forwarded_host = self.headers.get("X-Forwarded-Host")
        authority = (
            forwarded_host.split(",", 1)[0].strip()
            if forwarded_host
            else self.headers.get("Host", "")
        )
        forwarded_proto = self.headers.get("X-Forwarded-Proto")
        scheme = (
            forwarded_proto.split(",", 1)[0].strip().lower()
            if forwarded_proto
            else "http"
        )

        if scheme not in ("http", "https"):
            raise ValueError("Invalid forwarded protocol")
        if (
            not authority
            or any(character.isspace() or ord(character) < 33 for character in authority)
            or any(character in authority for character in "/\\?#@")
        ):
            raise ValueError("Invalid host")

        try:
            parsed = urlsplit(f"//{authority}")
            parsed.port
        except ValueError:
            raise ValueError("Invalid host") from None
        if not parsed.hostname or parsed.path or parsed.netloc != authority:
            raise ValueError("Invalid host")
        return f"{scheme}://{authority}"

    def do_GET(self) -> None:
        request_path = urlsplit(self.path).path
        if request_path == "/":
            content = (
                '<form action="/shorten" method="post">'
                '<label for="url">줄일 URL</label><br>'
                '<input id="url" name="url" type="url" required '
                'maxlength="2048" placeholder="https://example.com/">'
                '<br><button type="submit">줄이기</button></form>'
                '<p><a href="/table">해시 테이블 보기</a></p>'
            )
            self._send_html(200, _page("URL 단축기", content))
            return

        if request_path == "/table":
            try:
                origin = self._request_origin()
            except ValueError as error:
                self._send_html(
                    400,
                    _page("잘못된 요청", f'<p class="error">{html.escape(str(error))}</p>'),
                )
                return
            with _STATE_LOCK:
                selected_backend = get_backend()
                selector = (
                    '<form action="/table/backend" method="post">'
                    '<label for="backend">충돌 처리 방식</label> '
                    '<select id="backend" name="backend">'
                    f'<option value="chaining"{" selected" if selected_backend == "chaining" else ""}>'
                    "개별 체이닝</option>"
                    f'<option value="linear"{" selected" if selected_backend == "linear" else ""}>'
                    "선형 탐지</option>"
                    '</select> <button type="submit">방식 바꾸기</button></form>'
                    "<p>방식을 바꾸어도 기존 URL과 짧은 코드는 유지됩니다.</p>"
                )
                content = (
                    '<p><a href="/">처음으로</a></p>'
                    + selector
                    + _table_html(
                        shortener._url_to_code,
                        origin,
                        f"URL → 짧은 코드 ({selected_backend})",
                        "URL 키",
                        "짧은 코드",
                        True,
                    )
                    + _table_html(
                        shortener._code_to_url,
                        origin,
                        "짧은 코드 → URL",
                        "짧은 코드",
                        "URL",
                        False,
                    )
                )
            self._send_html(200, _page("해시 테이블", content))
            return

        code = unquote(request_path[1:]) if request_path.startswith("/") else ""
        if code and "/" not in code:
            try:
                with _STATE_LOCK:
                    url = expand(code)
            except KeyError:
                self._send_html(
                    404,
                    _page("찾을 수 없음", '<p class="error">알 수 없는 짧은 코드입니다.</p>'),
                )
                return
            self.send_response(302)
            self.send_header("Location", url)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return

        self._send_html(
            404,
            _page("찾을 수 없음", '<p class="error">페이지를 찾을 수 없습니다.</p>'),
        )

    def do_POST(self) -> None:
        if urlsplit(self.path).path != "/shorten":
            if urlsplit(self.path).path == "/table/backend":
                self._select_backend()
                return
            self._send_html(
                404,
                _page("찾을 수 없음", '<p class="error">페이지를 찾을 수 없습니다.</p>'),
            )
            return

        try:
            content_length = int(self.headers.get("Content-Length", ""))
            if content_length < 0 or content_length > _MAX_FORM_BYTES:
                raise ValueError("Invalid form length")
            form_body = self.rfile.read(content_length).decode("utf-8")
            form = parse_qs(form_body, strict_parsing=True)
            urls = form.get("url", [])
            if len(urls) != 1:
                raise ValueError("URL 입력이 필요합니다.")
            origin = self._request_origin()
            with _STATE_LOCK:
                code = shorten(urls[0])
        except (UnicodeDecodeError, ValueError) as error:
            self._send_html(
                400,
                _page(
                    "입력 오류",
                    f'<p class="error">{html.escape(str(error))}</p>'
                    '<p><a href="/">다시 입력</a></p>',
                ),
            )
            return
        except OverflowError as error:
            self._send_html(
                503,
                _page(
                    "테이블 가득 참",
                    f'<p class="error">{html.escape(str(error))}</p>'
                    '<p><a href="/table">테이블 보기</a></p>',
                ),
            )
            return

        short_link = f"{origin}/{code}"
        safe_link = html.escape(short_link, quote=True)
        content = (
            '<div class="result"><p>단축이 완료되었습니다.</p>'
            f"<p>코드: <code>{html.escape(code)}</code></p>"
            f'<p>짧은 링크: <a href="{safe_link}">{safe_link}</a></p></div>'
            '<p><a href="/">다른 URL 줄이기</a> · '
            '<a href="/table">해시 테이블 보기</a></p>'
        )
        self._send_html(200, _page("단축 결과", content))

    def _select_backend(self) -> None:
        try:
            content_length = int(self.headers.get("Content-Length", ""))
            if content_length < 0 or content_length > _MAX_FORM_BYTES:
                raise ValueError("Invalid form length")
            form_body = self.rfile.read(content_length).decode("utf-8")
            form = parse_qs(form_body, strict_parsing=True)
            backends = form.get("backend", [])
            if len(backends) != 1 or backends[0] not in ("chaining", "linear"):
                raise ValueError("알 수 없는 해시 테이블 방식입니다.")
            with _STATE_LOCK:
                configure_backend(backends[0])
        except (UnicodeDecodeError, ValueError) as error:
            self._send_html(
                400,
                _page(
                    "입력 오류",
                    f'<p class="error">{html.escape(str(error))}</p>'
                    '<p><a href="/table">테이블 보기</a></p>',
                ),
            )
            return

        self.send_response(303)
        self.send_header("Location", "/table")
        self.send_header("Content-Length", "0")
        self.end_headers()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the URL shortener web server.")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if not 0 < args.port < 65536:
        parser.error("--port must be between 1 and 65535")

    server = ThreadingHTTPServer(("0.0.0.0", args.port), ShortenerRequestHandler)
    print(f"Serving URL shortener on port {args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping URL shortener")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
