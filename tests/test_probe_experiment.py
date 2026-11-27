import unittest

from experiments.probe_experiment import _count_node_comparisons
from src.hash_table import HashTable


class ProbeExperimentTests(unittest.TestCase):
    def test_comparison_count_includes_nodes_until_match_or_chain_end(self):
        table = HashTable[str](capacity=8)
        table.put("pots", "first")
        table.put("tops", "second")

        self.assertEqual(_count_node_comparisons(table, "tops"), 1)
        self.assertEqual(_count_node_comparisons(table, "pots"), 2)

        missing_key = next(
            f"missing-{index}"
            for index in range(100)
            if table._index(f"missing-{index}") == table._index("pots")
        )
        self.assertEqual(_count_node_comparisons(table, missing_key), 2)
        self.assertEqual(_count_node_comparisons(table, "absent"), 0)


if __name__ == "__main__":
    unittest.main()
