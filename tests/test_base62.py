import unittest

from src.base62 import decode, encode


class Base62Tests(unittest.TestCase):
    def test_encode_zero_and_alphabet_boundaries(self):
        self.assertEqual(encode(0), "0")
        self.assertEqual(encode(9), "9")
        self.assertEqual(encode(10), "a")
        self.assertEqual(encode(35), "z")
        self.assertEqual(encode(36), "A")
        self.assertEqual(encode(61), "Z")
        self.assertEqual(encode(62), "10")

    def test_round_trip(self):
        for value in (1, 123, 62**5 + 987654321):
            with self.subTest(value=value):
                self.assertEqual(decode(encode(value)), value)

    def test_encode_rejects_negative_and_non_integer_values(self):
        with self.assertRaises(ValueError):
            encode(-1)
        for value in ("1", 1.5, True):
            with self.subTest(value=value):
                with self.assertRaises(TypeError):
                    encode(value)

    def test_decode_rejects_empty_and_invalid_strings(self):
        for value in ("", "a-b", "한"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    decode(value)

    def test_decode_rejects_non_string_values(self):
        for value in (None, 12):
            with self.subTest(value=value):
                with self.assertRaises(TypeError):
                    decode(value)


if __name__ == "__main__":
    unittest.main()
