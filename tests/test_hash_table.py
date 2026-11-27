import unittest

from src.hash_table import HashTable


class HashTableTests(unittest.TestCase):
    def test_empty_table_and_missing_key(self):
        table = HashTable()

        self.assertEqual(len(table), 0)
        self.assertIsNone(table.get("missing"))
        self.assertFalse(table.contains("missing"))

    def test_empty_string_key(self):
        table = HashTable()

        table.put("", "empty")

        self.assertEqual(table.get(""), "empty")
        self.assertTrue(table.contains(""))
        self.assertEqual(len(table), 1)

    def test_replacing_value_does_not_increase_length(self):
        table = HashTable()

        table.put("key", "first")
        table.put("key", "second")

        self.assertEqual(table.get("key"), "second")
        self.assertEqual(len(table), 1)

    def test_colliding_keys_remain_distinguishable(self):
        capacity = 8
        self.assertEqual(
            _horner_index("pots", capacity),
            _horner_index("tops", capacity),
        )

        table = HashTable(capacity)
        table.put("stop", "value-stop")
        table.put("pots", "value-pots")
        table.put("tops", "value-tops")

        self.assertEqual(table.get("stop"), "value-stop")
        self.assertEqual(table.get("pots"), "value-pots")
        self.assertEqual(table.get("tops"), "value-tops")
        self.assertEqual(len(table), 3)

    def test_operations_accept_different_positive_capacities(self):
        for capacity in (1, 3, 8, 17):
            with self.subTest(capacity=capacity):
                table = HashTable(capacity)
                table.put("", "empty")
                table.put("alpha", "one")
                table.put("beta", "two")

                self.assertEqual(table.get(""), "empty")
                self.assertEqual(table.get("alpha"), "one")
                self.assertEqual(table.get("beta"), "two")

    def test_non_string_keys_are_rejected(self):
        table = HashTable()

        for key in (None, 42):
            with self.subTest(key=key):
                for operation in (
                    lambda: table.put(key, "value"),
                    lambda: table.get(key),
                    lambda: table.contains(key),
                ):
                    with self.assertRaises(TypeError):
                        operation()

    def test_invalid_capacities_are_rejected(self):
        for capacity in (0, -1, "8", True):
            with self.subTest(capacity=capacity):
                with self.assertRaises((TypeError, ValueError)):
                    HashTable(capacity)


def _horner_index(key, capacity):
    value = 0
    for character in key:
        value = (31 * value + ord(character)) % capacity
    return value


if __name__ == "__main__":
    unittest.main()
