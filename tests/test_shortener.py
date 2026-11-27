import unittest

from src.shortener import expand, reset_state, shorten


class ShortenerTestCases:
    backend = "chaining"

    def setUp(self):
        reset_state(self.backend)

    def test_sequential_codes_deduplication_and_expansion(self):
        first_url = "http://example.com"
        second_url = "https://example.com"
        case_variant_url = "http://Example.com"
        slash_variant_url = "http://example.com/"

        first_code = shorten(first_url)
        second_code = shorten(second_url)

        self.assertEqual(first_code, "0")
        self.assertEqual(second_code, "1")
        self.assertEqual(shorten(first_url), first_code)

        case_variant_code = shorten(case_variant_url)
        slash_variant_code = shorten(slash_variant_url)
        self.assertEqual(case_variant_code, "2")
        self.assertEqual(slash_variant_code, "3")
        codes = (first_code, second_code, case_variant_code, slash_variant_code)
        for index, code in enumerate(codes):
            for other_code in codes[index + 1 :]:
                self.assertNotEqual(code, other_code)

        self.assertEqual(expand(first_code), first_url)
        self.assertEqual(expand(second_code), second_url)
        self.assertEqual(expand(case_variant_code), case_variant_url)
        self.assertEqual(expand(slash_variant_code), slash_variant_url)

    def test_unknown_code_raises_key_error(self):
        with self.assertRaises(KeyError):
            expand("unknown-code")

    def test_invalid_urls_are_rejected(self):
        invalid_urls = (
            "",
            "   ",
            "https://example.com/path with space",
            "example.com",
            "ftp://example.com",
            "javascript:alert(1)",
            "http://",
            f"http://example.com/{'a' * 2048}",
        )

        for url in invalid_urls:
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    shorten(url)

    def test_non_string_url_is_rejected(self):
        with self.assertRaises(TypeError):
            shorten(None)


class ChainingShortenerTests(ShortenerTestCases, unittest.TestCase):
    backend = "chaining"


class LinearProbingShortenerTests(ShortenerTestCases, unittest.TestCase):
    backend = "linear"


if __name__ == "__main__":
    unittest.main()
