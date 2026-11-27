import threading
import unittest
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from urllib.parse import urlencode

import src.shortener as shortener_module
from src.server import ShortenerRequestHandler


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        shortener_module.reset_state("chaining")

        cls.server = ThreadingHTTPServer(
            ("127.0.0.1", 0), ShortenerRequestHandler
        )
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        shortener_module.reset_state("chaining")

    def _request(self, path, *, data=None, headers=None):
        connection = HTTPConnection("127.0.0.1", self.server.server_port)
        try:
            connection.request(
                "POST" if data is not None else "GET",
                path,
                body=data,
                headers=headers or {},
            )
            response = connection.getresponse()
            return response.status, response.headers, response.read().decode("utf-8")
        finally:
            connection.close()

    def _shorten(self, url, headers=None):
        body = f"url={url}".encode("utf-8")
        status, response_headers, content = self._request(
            "/shorten",
            data=body,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Content-Length": str(len(body)),
                **(headers or {}),
            },
        )
        return status, response_headers, content

    def test_home_and_successful_form_use_forwarded_origin(self):
        status, _, content = self._request("/")
        self.assertEqual(status, 200)
        self.assertIn('action="/shorten"', content)

        status, _, content = self._shorten(
            "https%3A%2F%2Fexample.test%2Fpath",
            {
                "Host": "internal.local:8000",
                "X-Forwarded-Host": "my-space.app.github.dev",
                "X-Forwarded-Proto": "https",
            },
        )
        self.assertEqual(status, 200)
        self.assertIn("https://my-space.app.github.dev/", content)

    def test_host_fallback_and_redirect_to_original_url(self):
        original_url = "https://redirect-target.example.test/path"
        status, _, content = self._shorten(original_url)
        self.assertEqual(status, 200)
        self.assertIn(
            f"http://127.0.0.1:{self.server.server_port}/",
            content,
        )
        code = content.split("<code>", 1)[1].split("</code>", 1)[0]

        status, headers, _ = self._request(f"/{code}")
        self.assertEqual(status, 302)
        self.assertEqual(headers["Location"], original_url)

    def test_invalid_input_and_unknown_code_have_error_status(self):
        status, _, _ = self._shorten("not-a-url")
        self.assertEqual(status, 400)

        status, _, _ = self._request("/unknown-code")
        self.assertEqual(status, 404)

    def test_form_accepts_maximum_length_unicode_url(self):
        prefix = "https://example.test/"
        url = prefix + "é" * (2048 - len(prefix))
        body = urlencode({"url": url}).encode("utf-8")

        status, _, _ = self._request(
            "/shorten",
            data=body,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Content-Length": str(len(body)),
            },
        )

        self.assertEqual(status, 200)

    def test_table_shows_chains_horner_steps_and_links(self):
        self._shorten("https://table-entry.example.test/path")
        status, _, content = self._request(
            "/table",
            headers={
                "X-Forwarded-Host": "public.example.test",
                "X-Forwarded-Proto": "https",
            },
        )

        self.assertEqual(status, 200)
        self.assertIn("URL → 짧은 코드", content)
        self.assertIn("짧은 코드 → URL", content)
        self.assertIn("호너 해시 계산 과정", content)
        self.assertIn("https://public.example.test/", content)

    def test_table_links_colliding_nodes_with_arrows(self):
        first_url = "https://chain-0.example.test/"
        first_bucket = shortener_module._url_to_code._index(first_url)
        second_url = next(
            f"https://chain-{index}.example.test/"
            for index in range(1, 100)
            if shortener_module._url_to_code._index(
                f"https://chain-{index}.example.test/"
            )
            == first_bucket
        )
        self._shorten(first_url)
        self._shorten(second_url)

        status, _, content = self._request("/table")

        self.assertEqual(status, 200)
        self.assertIn('<span class="arrow">→</span>', content)

    def test_table_switches_to_linear_and_preserves_links(self):
        original_url = "https://switch-backend.example.test/path"
        status, _, result = self._shorten(original_url)
        self.assertEqual(status, 200)
        code = result.split("<code>", 1)[1].split("</code>", 1)[0]

        status, headers, _ = self._request(
            "/table/backend",
            data=b"backend=linear",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Content-Length": "14",
            },
        )
        self.assertEqual(status, 303)
        self.assertEqual(headers["Location"], "/table")
        self.assertEqual(shortener_module.get_backend(), "linear")
        self.assertEqual(shortener_module.expand(code), original_url)

        status, _, content = self._request("/table")
        self.assertEqual(status, 200)
        self.assertIn("linear", content)
        self.assertIn("탐사 거리:", content)
        self.assertIn(original_url, content)

        status, headers, _ = self._request(
            "/table/backend",
            data=b"backend=chaining",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Content-Length": "16",
            },
        )
        self.assertEqual(status, 303)
        self.assertEqual(headers["Location"], "/table")
        self.assertEqual(shortener_module.get_backend(), "chaining")
        self.assertEqual(shortener_module.expand(code), original_url)

    def test_invalid_backend_selection_returns_bad_request(self):
        status, _, _ = self._request(
            "/table/backend",
            data=b"backend=unknown",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Content-Length": "14",
            },
        )
        self.assertEqual(status, 400)

    def test_invalid_forwarded_origin_is_rejected(self):
        status, _, _ = self._shorten(
            "https://valid-url.example.test/",
            {"X-Forwarded-Host": "attacker.test/path"},
        )
        self.assertEqual(status, 400)


if __name__ == "__main__":
    unittest.main()
