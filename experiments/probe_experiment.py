"""Measure separate-chaining probe counts against simple theoretical estimates."""

from __future__ import annotations

import csv
import math
import random
import string
from dataclasses import dataclass
from pathlib import Path

from src.hash_table import HashTable


CAPACITY = 4093
LOAD_FACTORS = tuple(step / 4 for step in range(1, 17))
FAILED_QUERY_COUNT = 10_000
RANDOM_SEED = 20261127
EXPERIMENT_DIR = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Measurement:
    requested_load_factor: float
    actual_load_factor: float
    item_count: int
    successful_average: float
    successful_theory: float
    unsuccessful_average: float
    unsuccessful_theory: float


def _count_node_comparisons(table: HashTable[str], key: str) -> int:
    """Count chain nodes inspected by a search for key."""
    bucket_index = table._index(key)
    node = table._buckets[bucket_index]
    comparisons = 0
    while node is not None:
        comparisons += 1
        if node.key == key:
            break
        node = node.next
    return comparisons


def _random_url(rng: random.Random, namespace: str, index: int) -> str:
    token = "".join(
        rng.choice(string.ascii_lowercase + string.digits) for _ in range(16)
    )
    return f"https://{namespace}-{index}-{token}.example.test/"


def run_experiment() -> list[Measurement]:
    max_item_count = round(CAPACITY * LOAD_FACTORS[-1])
    stored_rng = random.Random(RANDOM_SEED)
    stored_urls = [
        _random_url(stored_rng, "stored", index)
        for index in range(max_item_count)
    ]
    missing_rng = random.Random(RANDOM_SEED + 1)
    missing_urls = [
        _random_url(missing_rng, "missing", index)
        for index in range(FAILED_QUERY_COUNT)
    ]

    measurements = []
    for requested_load_factor in LOAD_FACTORS:
        item_count = round(CAPACITY * requested_load_factor)
        table: HashTable[str] = HashTable(capacity=CAPACITY)
        for url in stored_urls[:item_count]:
            table.put(url, url)

        actual_load_factor = len(table) / CAPACITY
        successful_average = sum(
            _count_node_comparisons(table, url)
            for url in stored_urls[:item_count]
        ) / item_count
        unsuccessful_average = sum(
            _count_node_comparisons(table, url) for url in missing_urls
        ) / FAILED_QUERY_COUNT

        measurements.append(
            Measurement(
                requested_load_factor=requested_load_factor,
                actual_load_factor=actual_load_factor,
                item_count=item_count,
                successful_average=successful_average,
                successful_theory=1 + actual_load_factor / 2,
                unsuccessful_average=unsuccessful_average,
                unsuccessful_theory=actual_load_factor,
            )
        )
    return measurements


def _write_csv(measurements: list[Measurement], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file, lineterminator="\n")
        writer.writerow(
            (
                "requested_load_factor",
                "actual_load_factor",
                "capacity",
                "item_count",
                "successful_average_nodes",
                "successful_theory_nodes",
                "unsuccessful_average_nodes",
                "unsuccessful_theory_nodes",
            )
        )
        for result in measurements:
            writer.writerow(
                (
                    f"{result.requested_load_factor:.2f}",
                    f"{result.actual_load_factor:.6f}",
                    CAPACITY,
                    result.item_count,
                    f"{result.successful_average:.6f}",
                    f"{result.successful_theory:.6f}",
                    f"{result.unsuccessful_average:.6f}",
                    f"{result.unsuccessful_theory:.6f}",
                )
            )


def _write_svg(measurements: list[Measurement], path: Path) -> None:
    width, height = 900, 480
    left, top, plot_width, plot_height = 80, 55, 560, 340
    bottom = top + plot_height
    max_y = max(
        5,
        math.ceil(
            max(
                max(
                    result.successful_average,
                    result.successful_theory,
                    result.unsuccessful_average,
                    result.unsuccessful_theory,
                )
                for result in measurements
            )
            + 0.1
        ),
    )

    def x_position(load_factor: float) -> float:
        return left + load_factor / 4 * plot_width

    def y_position(nodes: float) -> float:
        return bottom - nodes / max_y * plot_height

    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<text x="450" y="28" text-anchor="middle" font-family="sans-serif" '
        'font-size="18">Hash table probe counts vs. load factor</text>',
    ]

    for tick in range(max_y + 1):
        y = y_position(tick)
        elements.append(
            f'<line x1="{left}" y1="{y:.1f}" x2="{left + plot_width}" '
            f'y2="{y:.1f}" stroke="#dddddd"/>'
        )
        elements.append(
            f'<text x="{left - 12}" y="{y + 4:.1f}" text-anchor="end" '
            f'font-family="sans-serif" font-size="12">{tick}</text>'
        )

    for tick in range(9):
        load_factor = tick / 2
        x = x_position(load_factor)
        elements.append(
            f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{bottom}" '
            'stroke="#eeeeee"/>'
        )
        elements.append(
            f'<text x="{x:.1f}" y="{bottom + 22}" text-anchor="middle" '
            f'font-family="sans-serif" font-size="12">{load_factor:.1f}</text>'
        )

    elements.extend(
        (
            f'<line x1="{left}" y1="{top}" x2="{left}" y2="{bottom}" '
            'stroke="#222222"/>',
            f'<line x1="{left}" y1="{bottom}" x2="{left + plot_width}" '
            f'y2="{bottom}" stroke="#222222"/>',
            f'<text x="{left + plot_width / 2}" y="{height - 20}" '
            'text-anchor="middle" font-family="sans-serif" font-size="14">'
            'Load factor (alpha)</text>',
            f'<text x="20" y="{top + plot_height / 2}" '
            f'transform="rotate(-90 20 {top + plot_height / 2})" '
            'text-anchor="middle" font-family="sans-serif" font-size="14">'
            'Average nodes compared</text>',
        )
    )

    series = (
        (
            "Successful (measured)",
            [result.successful_average for result in measurements],
            "#2563eb",
            "",
        ),
        (
            "Successful (theory)",
            [result.successful_theory for result in measurements],
            "#2563eb",
            "6 4",
        ),
        (
            "Unsuccessful (measured)",
            [result.unsuccessful_average for result in measurements],
            "#dc2626",
            "",
        ),
        (
            "Unsuccessful (theory)",
            [result.unsuccessful_theory for result in measurements],
            "#dc2626",
            "6 4",
        ),
    )
    for label, values, color, dash in series:
        points = [
            (
                x_position(result.actual_load_factor),
                y_position(value),
            )
            for result, value in zip(measurements, values)
        ]
        point_string = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
        dash_attribute = f' stroke-dasharray="{dash}"' if dash else ""
        elements.append(
            f'<polyline points="{point_string}" fill="none" stroke="{color}" '
            f'stroke-width="2"{dash_attribute}/>'
        )
        for x, y in points:
            elements.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.5" fill="{color}"/>'
            )

    legend_x, legend_y = 675, 105
    for index, (label, _, color, dash) in enumerate(series):
        y = legend_y + index * 28
        dash_attribute = f' stroke-dasharray="{dash}"' if dash else ""
        elements.append(
            f'<line x1="{legend_x}" y1="{y}" x2="{legend_x + 30}" y2="{y}" '
            f'stroke="{color}" stroke-width="2"{dash_attribute}/>'
        )
        elements.append(
            f'<text x="{legend_x + 40}" y="{y + 4}" font-family="sans-serif" '
            f'font-size="12">{label}</text>'
        )

    elements.append("</svg>")
    path.write_text("\n".join(elements) + "\n", encoding="utf-8")


def _print_table(measurements: list[Measurement]) -> None:
    print(
        "alpha(actual)  n      successful measured/theory"
        "  unsuccessful measured/theory"
    )
    for result in measurements:
        print(
            f"{result.actual_load_factor:12.4f}  {result.item_count:5d}  "
            f"{result.successful_average:8.4f}/{result.successful_theory:8.4f}  "
            f"{result.unsuccessful_average:10.4f}/"
            f"{result.unsuccessful_theory:8.4f}"
        )


def main() -> None:
    measurements = run_experiment()
    csv_path = EXPERIMENT_DIR / "results.csv"
    svg_path = EXPERIMENT_DIR / "results.svg"
    _write_csv(measurements, csv_path)
    _write_svg(measurements, svg_path)
    _print_table(measurements)
    print(f"\nSaved {csv_path} and {svg_path}")


if __name__ == "__main__":
    main()
