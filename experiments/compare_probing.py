"""Compare separate chaining and linear probing search costs."""

from __future__ import annotations

import csv
import math
import random
from dataclasses import dataclass
from pathlib import Path

from experiments.probe_experiment import (
    CAPACITY,
    FAILED_QUERY_COUNT,
    RANDOM_SEED,
    _count_node_comparisons,
    _random_url,
)
from src.hash_table import HashTable, LinearProbingHashTable


LOAD_FACTORS = tuple(step / 10 for step in range(1, 10))
EXPERIMENT_DIR = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Comparison:
    load_factor: float
    item_count: int
    chaining_success: float
    chaining_success_theory: float
    chaining_failure: float
    chaining_failure_theory: float
    linear_success: float
    linear_success_theory: float
    linear_failure: float
    linear_failure_theory: float


def run_experiment() -> list[Comparison]:
    stored_rng = random.Random(RANDOM_SEED + 2)
    max_item_count = round(CAPACITY * LOAD_FACTORS[-1])
    stored_urls = [
        _random_url(stored_rng, "compare", index)
        for index in range(max_item_count)
    ]
    missing_rng = random.Random(RANDOM_SEED + 3)
    missing_urls = [
        _random_url(missing_rng, "not-stored", index)
        for index in range(FAILED_QUERY_COUNT)
    ]

    comparisons = []
    for requested_load_factor in LOAD_FACTORS:
        item_count = round(CAPACITY * requested_load_factor)
        chaining: HashTable[str] = HashTable(capacity=CAPACITY)
        linear: LinearProbingHashTable[str] = LinearProbingHashTable(
            capacity=CAPACITY
        )
        for url in stored_urls[:item_count]:
            chaining.put(url, url)
            linear.put(url, url)

        load_factor = item_count / CAPACITY
        chaining_success = sum(
            _count_node_comparisons(chaining, url)
            for url in stored_urls[:item_count]
        ) / item_count
        chaining_failure = sum(
            _count_node_comparisons(chaining, url) for url in missing_urls
        ) / FAILED_QUERY_COUNT
        linear_success = sum(
            linear.probe_count(url) for url in stored_urls[:item_count]
        ) / item_count
        linear_failure = sum(
            linear.probe_count(url) for url in missing_urls
        ) / FAILED_QUERY_COUNT

        comparisons.append(
            Comparison(
                load_factor=load_factor,
                item_count=item_count,
                chaining_success=chaining_success,
                chaining_success_theory=1 + load_factor / 2,
                chaining_failure=chaining_failure,
                chaining_failure_theory=load_factor,
                linear_success=linear_success,
                linear_success_theory=(
                    1 + 1 / (1 - load_factor)
                )
                / 2,
                linear_failure=linear_failure,
                linear_failure_theory=(
                    1 + 1 / (1 - load_factor) ** 2
                )
                / 2,
            )
        )
    return comparisons


def _write_csv(comparisons: list[Comparison], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file, lineterminator="\n")
        writer.writerow(
            (
                "load_factor",
                "capacity",
                "item_count",
                "chaining_success_measured",
                "chaining_success_theory",
                "chaining_failure_measured",
                "chaining_failure_theory",
                "linear_success_measured",
                "linear_success_theory",
                "linear_failure_measured",
                "linear_failure_theory",
            )
        )
        for result in comparisons:
            writer.writerow(
                (
                    f"{result.load_factor:.6f}",
                    CAPACITY,
                    result.item_count,
                    f"{result.chaining_success:.6f}",
                    f"{result.chaining_success_theory:.6f}",
                    f"{result.chaining_failure:.6f}",
                    f"{result.chaining_failure_theory:.6f}",
                    f"{result.linear_success:.6f}",
                    f"{result.linear_success_theory:.6f}",
                    f"{result.linear_failure:.6f}",
                    f"{result.linear_failure_theory:.6f}",
                )
            )


def _write_svg(comparisons: list[Comparison], path: Path) -> None:
    width, height = 1100, 780
    left, plot_width = 85, 650
    panel_height = 260
    panel_tops = (75, 430)
    series = (
        (
            "Chaining measured",
            "chaining_success",
            "#2563eb",
            "",
        ),
        (
            "Chaining theory",
            "chaining_success_theory",
            "#2563eb",
            "7 5",
        ),
        (
            "Linear probing measured",
            "linear_success",
            "#ea580c",
            "",
        ),
        (
            "Linear probing theory",
            "linear_success_theory",
            "#ea580c",
            "7 5",
        ),
    )
    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
        f'height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<text x="550" y="32" text-anchor="middle" font-family="sans-serif" '
        'font-size="20">Separate chaining vs. linear probing</text>',
    ]

    panels = (
        (
            "Successful search",
            "success",
            series,
        ),
        (
            "Unsuccessful search",
            "failure",
            (
                ("Chaining measured", "chaining_failure", "#16a34a", ""),
                ("Chaining theory", "chaining_failure_theory", "#16a34a", "7 5"),
                ("Linear probing measured", "linear_failure", "#dc2626", ""),
                ("Linear probing theory", "linear_failure_theory", "#dc2626", "7 5"),
            ),
        ),
    )
    for panel_index, (title, _, panel_series) in enumerate(panels):
        top = panel_tops[panel_index]
        bottom = top + panel_height
        max_value = max(
            getattr(result, field)
            for result in comparisons
            for _, field, _, _ in panel_series
        )
        y_max = max(1, math.ceil(max_value * 1.08))

        def x_position(load_factor: float) -> float:
            return left + (load_factor - 0.1) / 0.8 * plot_width

        def y_position(value: float) -> float:
            return bottom - value / y_max * panel_height

        elements.append(
            f'<text x="{left}" y="{top - 18}" font-family="sans-serif" '
            f'font-size="16">{title} (average slots/nodes inspected)</text>'
        )
        tick_step = max(1, math.ceil(y_max / 5))
        for tick in range(0, y_max + 1, tick_step):
            y = y_position(tick)
            elements.extend(
                (
                    f'<line x1="{left}" y1="{y:.1f}" '
                    f'x2="{left + plot_width}" y2="{y:.1f}" '
                    'stroke="#dddddd"/>',
                    f'<text x="{left - 12}" y="{y + 4:.1f}" '
                    'text-anchor="end" font-family="sans-serif" '
                    f'font-size="12">{tick}</text>',
                )
            )
        for result in comparisons:
            x = x_position(result.load_factor)
            elements.extend(
                (
                    f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" '
                    f'y2="{bottom}" stroke="#eeeeee"/>',
                    f'<text x="{x:.1f}" y="{bottom + 20}" '
                    'text-anchor="middle" font-family="sans-serif" '
                    f'font-size="11">{result.load_factor:.1f}</text>',
                )
            )
        elements.extend(
            (
                f'<line x1="{left}" y1="{top}" x2="{left}" '
                f'y2="{bottom}" stroke="#222222"/>',
                f'<line x1="{left}" y1="{bottom}" '
                f'x2="{left + plot_width}" y2="{bottom}" '
                'stroke="#222222"/>',
            )
        )
        if panel_index == 1:
            elements.append(
                f'<text x="{left + plot_width / 2}" y="{bottom + 43}" '
                'text-anchor="middle" font-family="sans-serif" '
                'font-size="14">Load factor (alpha)</text>'
            )

        for label, field, color, dash in panel_series:
            points = " ".join(
                f"{x_position(result.load_factor):.1f},"
                f"{y_position(getattr(result, field)):.1f}"
                for result in comparisons
            )
            dash_attribute = f' stroke-dasharray="{dash}"' if dash else ""
            elements.append(
                f'<polyline points="{points}" fill="none" stroke="{color}" '
                f'stroke-width="2"{dash_attribute}/>'
            )
            for result in comparisons:
                elements.append(
                    f'<circle cx="{x_position(result.load_factor):.1f}" '
                    f'cy="{y_position(getattr(result, field)):.1f}" '
                    f'r="3" fill="{color}"/>'
                )

            legend_y = top + 35 + panel_series.index(
                (label, field, color, dash)
            ) * 30
            elements.extend(
                (
                    f'<line x1="790" y1="{legend_y}" x2="825" '
                    f'y2="{legend_y}" stroke="{color}" stroke-width="2"'
                    f'{dash_attribute}/>',
                    f'<text x="835" y="{legend_y + 4}" '
                    'font-family="sans-serif" font-size="12">'
                    f'{label}</text>',
                )
            )

    elements.append("</svg>")
    path.write_text("\n".join(elements) + "\n", encoding="utf-8")


def _print_table(comparisons: list[Comparison]) -> None:
    print(
        "alpha  chaining success (measured/theory)  "
        "linear success (measured/theory)  "
        "chaining failure (measured/theory)  "
        "linear failure (measured/theory)"
    )
    for result in comparisons:
        print(
            f"{result.load_factor:.1f}  "
            f"{result.chaining_success:.3f}/{result.chaining_success_theory:.3f}  "
            f"{result.linear_success:.3f}/{result.linear_success_theory:.3f}  "
            f"{result.chaining_failure:.3f}/{result.chaining_failure_theory:.3f}  "
            f"{result.linear_failure:.3f}/{result.linear_failure_theory:.3f}"
        )


def main() -> None:
    comparisons = run_experiment()
    csv_path = EXPERIMENT_DIR / "linear_probing_results.csv"
    svg_path = EXPERIMENT_DIR / "linear_probing_results.svg"
    _write_csv(comparisons, csv_path)
    _write_svg(comparisons, svg_path)
    _print_table(comparisons)
    print(f"\nSaved {csv_path} and {svg_path}")


if __name__ == "__main__":
    main()
