"""Everything the program prints: tables, paddle cards and reports.

Missing values, prices and numbers are always formatted through
``format_number`` / ``format_price`` / ``or_dash``, so the formatting is
written once instead of inline in every print statement (as in Phase 1).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Optional, Sequence

from ..core.config import CATEGORY_LABELS, MAX_COMPARE, METRICS, METRICS_BY_KEY, MIN_COMPARE
from ..core.models import MetricStats, Paddle, ScoredPaddle
from ..core.summary_stats import count_by, percentile_rank

if TYPE_CHECKING:  # only needed for type hints; avoids an import at run time
    from ..core.catalog import PaddleCatalog

TABLE_WIDTH = 112
NAME_WIDTH = 42
COMPARE_LABEL_WIDTH = 16
COMPARE_COLUMN_WIDTH = 28

# Columns of the results table: (metric key, header, width).
RESULT_COLUMNS = (("weight", "Wt", 6), ("swing_weight", "SW", 5), ("twist_weight", "TW", 6),
                  ("power", "Power", 6), ("pop", "Pop", 6), ("spin", "Spin", 6))


# --- Formatting helpers -------------------------------------------------------------

def format_number(value: Optional[float]) -> str:
    """Format a number without needless decimals.

    Args:
        value (float | int | None): The number to format.

    Returns:
        str: e.g. ``116.0 -> "116"``, ``7.960 -> "7.96"``; ``"-"`` for None.
    """
    if value is None:
        return "-"
    if float(value).is_integer():
        return str(int(value))
    return ("%.3f" % value).rstrip("0").rstrip(".")


def format_price(value: Optional[float]) -> str:
    """Format a price.

    Args:
        value (float | None): Price in dollars.

    Returns:
        str: e.g. ``"$169.99"``; ``"-"`` when unknown.
    """
    return "-" if value is None else "$%.2f" % value


def or_dash(text: str) -> str:
    """Show blank text as a dash.

    Args:
        text (str): Text that may be empty.

    Returns:
        str: ``text``, or ``"-"`` if it is empty.
    """
    return text if text else "-"


def truncate(text: str, width: int) -> str:
    """Shorten text to fit a column.

    Args:
        text (str): Text to shorten.
        width (int): Maximum number of characters.

    Preconditions:
        ``width`` is at least 1.

    Returns:
        str: ``text`` unchanged, or cut to ``width`` characters ending in ``"~"``.
    """
    assert width >= 1, "truncate: width must be at least 1, got " + str(width)
    return text if len(text) <= width else text[:width - 1] + "~"


def print_rule(char: str = "=") -> None:
    """Print a horizontal line the width of the results table.

    Args:
        char (str): Character to repeat. Defaults to ``"="``.
    """
    print(char * TABLE_WIDTH)


# --- Recommendation table -----------------------------------------------------------

def results_header() -> str:
    """Build the header line of the recommendations table.

    Returns:
        str: Column headings, aligned to ``result_row``.
    """
    line = "{:<3} {:<{w}} {:>6} {:>8}".format("#", "Paddle", "Match", "Price", w=NAME_WIDTH)
    for _, header, width in RESULT_COLUMNS:
        line += " {:>{w}}".format(header, w=width)
    return line + "  Type"


def result_row(rank: int, item: ScoredPaddle) -> str:
    """Build one line of the recommendations table.

    Args:
        rank (int): Position in the results, starting at 1.
        item (ScoredPaddle): The scored paddle.

    Returns:
        str: Rank, name, match %, price, key metrics and type.
    """
    paddle = item.paddle
    line = "{:<3} {:<{w}} {:>5.1f}% {:>8}".format(
        rank, truncate(paddle.full_name, NAME_WIDTH), item.score, format_price(paddle.price),
        w=NAME_WIDTH)
    for key, _, width in RESULT_COLUMNS:
        line += " {:>{w}}".format(format_number(paddle.value(key)), w=width)
    return line + "  " + paddle.paddle_type


def result_detail(item: ScoredPaddle) -> str:
    """Build the explanation line printed under a result row.

    Args:
        item (ScoredPaddle): The scored paddle.

    Returns:
        str: Best/weakest fitting metric, shape, core and approval.
    """
    paddle = item.paddle
    parts = []
    if item.best_fit is not None:
        parts.append("best fit: " + METRICS_BY_KEY[item.best_fit].label
                     + "   weakest fit: " + METRICS_BY_KEY[item.worst_fit].label)
    extra = paddle.shape + ", " + format_number(paddle.core) + "mm, " + paddle.approval
    parts.append(extra)
    return "      " + "   | ".join(parts)


def print_results(results: Sequence[ScoredPaddle]) -> None:
    """Print the ranked recommendations table.

    Args:
        results (Sequence[ScoredPaddle]): Results, best match first.
    """
    print()
    print_rule()
    print("TOP " + str(len(results)) + " PADDLES FOR YOU")
    print_rule()
    print(results_header())
    print_rule("-")
    for rank, item in enumerate(results, start=1):
        print(result_row(rank, item))
        print(result_detail(item))
    print_rule()


# --- Single paddle card ---------------------------------------------------------------

def print_paddle(paddle: Paddle) -> None:
    """Print every known detail about one paddle.

    Args:
        paddle (Paddle): The paddle to describe.
    """
    n = format_number
    print()
    print("*** " + paddle.full_name + " ***")
    print("  Price: " + format_price(paddle.price))
    print("  Link: " + or_dash(paddle.link))
    print("  Year: " + n(paddle.year) + "   Approval: " + paddle.approval)
    print("  Shape: " + paddle.shape + "   Type: " + paddle.paddle_type
          + "   Feel: " + or_dash(paddle.feel))
    print("  Face: " + or_dash(paddle.face) + "   Grit: " + paddle.grit
          + "   Build: " + paddle.build)
    print("  Core: " + n(paddle.core) + " mm   Grip length: " + n(paddle.grip_length)
          + " in   Grip size: " + n(paddle.grip_size) + " in")
    print("  Weight: " + n(paddle.weight) + " oz   Swing weight: " + n(paddle.swing_weight)
          + "   Twist weight: " + n(paddle.twist_weight))
    print("  Balance: " + n(paddle.balance) + " mm   Spin: " + n(paddle.spin) + " RPM ("
          + or_dash(paddle.spin_rating) + ")   Spin durability: " + or_dash(paddle.spin_durability))
    print("  Power: " + n(paddle.power) + " MPH   Pop: " + n(paddle.pop) + " MPH")


def print_paddles(paddles: Sequence[Paddle]) -> None:
    """Print a detail card for each paddle.

    Args:
        paddles (Sequence[Paddle]): Paddles to describe.
    """
    for paddle in paddles:
        print_paddle(paddle)


# --- Side-by-side comparison -------------------------------------------------------------

def comparison_cell(value: Optional[float], stats: MetricStats) -> str:
    """Format a metric value with its percentile.

    Args:
        value (float | None): The paddle's value.
        stats (MetricStats): Statistics for the metric.

    Returns:
        str: e.g. ``"7.96 (40%ile)"``; ``"-"`` when missing.
    """
    if value is None:
        return "-"
    return format_number(value) + " (" + str(percentile_rank(stats, value)) + "%ile)"


def comparison_line(label: str, cells: Sequence[str]) -> str:
    """Build one row of the comparison table.

    Args:
        label (str): Row label, e.g. ``"Weight"``.
        cells (Sequence[str]): One already-formatted cell per paddle.

    Returns:
        str: The aligned row.
    """
    line = "{:<{w}}".format(label, w=COMPARE_LABEL_WIDTH)
    for cell in cells:
        line += "{:>{w}}".format(cell, w=COMPARE_COLUMN_WIDTH)
    return line


def print_comparison(paddles: Sequence[Paddle], stats: Dict[str, MetricStats]) -> None:
    """Print paddles side by side with each metric's dataset percentile.

    Args:
        paddles (Sequence[Paddle]): The paddles to compare (2-3 fit the screen).
        stats (dict[str, MetricStats]): Dataset statistics per metric.

    Preconditions:
        ``paddles`` holds between ``MIN_COMPARE`` and ``MAX_COMPARE`` paddles.
    """
    assert MIN_COMPARE <= len(paddles) <= MAX_COMPARE, \
        ("print_comparison: need " + str(MIN_COMPARE) + " to " + str(MAX_COMPARE)
         + " paddles, got " + str(len(paddles)))
    names =[truncate(p.full_name, COMPARE_COLUMN_WIDTH - 1) for p in paddles]
    header = comparison_line("", names)
    print()
    print(header)
    print("-" * len(header))
    for spec in METRICS:
        if spec.key in stats:
            cells = [comparison_cell(p.value(spec.key), stats[spec.key]) for p in paddles]
            print(comparison_line(spec.label, cells))
    for key, label in CATEGORY_LABELS.items():
        print(comparison_line(label, [or_dash(p.value(key)) for p in paddles]))


# --- Dataset summary ----------------------------------------------------------------------

def print_summary(database: "PaddleCatalog") -> None:
    """Print min/median/average/max for every metric and paddle counts by type.

    The type counts are sorted with a custom key: most paddles first, then
    alphabetically by type name for ties.

    Args:
        database (PaddleCatalog): The loaded database.
    """
    row = "{:<16} {:>8} {:>8} {:>8} {:>8} {:>8}"
    print()
    print("Dataset: " + str(len(database)) + " paddles from "
          + str(database.brand_count) + " brands")
    print(row.format("Metric", "Min", "Median", "Avg", "Max", "Count"))
    for spec in METRICS:
        if spec.key in database.stats:
            s = database.stats[spec.key]
            print(row.format(spec.label, format_number(s.minimum), format_number(round(s.median, 2)),
                             format_number(round(s.average, 2)), format_number(s.maximum), s.count))
    print()
    print("Paddles by type (most common first):")
    type_counts = count_by(database.paddles, "paddle_type")
    for paddle_type, count in sorted(type_counts.items(), key=lambda pair: (-pair[1], pair[0])):
        print("  " + paddle_type + ": " + str(count))
