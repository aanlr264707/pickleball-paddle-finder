"""Summary statistics: percentiles, per-metric stats and counts."""

from __future__ import annotations

from collections import Counter
from typing import Dict, Iterable, List, Optional, Sequence

from .config import METRICS, METRICS_BY_KEY, STAT_PERCENTILES, TEXT_COLUMNS
from .models import MetricStats, Paddle


def known_values(paddles: Iterable[Paddle], key: str) -> List[float]:
    """Collect every measured value of one metric.

    Args:
        paddles (Iterable[Paddle]): Paddles to read from.
        key (str): Metric key, e.g. ``"power"``.

    Preconditions:
        ``key`` is a numeric metric listed in ``config.METRICS``.

    Returns:
        list[float]: The non-missing values, in paddle order.
    """
    assert key in METRICS_BY_KEY, "known_values: unknown metric key " + repr(key)
    return [p.value(key) for p in paddles if p.value(key) is not None]


def percentile(sorted_values: Sequence[float], pct: float) -> Optional[float]:
    """Compute a percentile with linear interpolation.

    Args:
        sorted_values (Sequence[float]): Values already sorted ascending.
        pct (float): Percentile to compute, 0 to 100.

    Preconditions:
        ``pct`` is between 0 and 100, and ``sorted_values`` is sorted ascending.

    Returns:
        float | None: The percentile value, or None for an empty sequence.
    """
    assert 0 <= pct <= 100, "percentile: pct must be between 0 and 100, got " + str(pct)
    assert all(a <= b for a, b in zip(sorted_values, sorted_values[1:])), \
        "percentile: sorted_values must be sorted ascending"
    if not sorted_values:
        return None
    position = (len(sorted_values) - 1) * pct / 100
    lower = int(position)
    upper = min(lower + 1, len(sorted_values) - 1)
    fraction = position - lower
    return sorted_values[lower] + (sorted_values[upper] - sorted_values[lower]) * fraction


def percentile_rank(stats: MetricStats, value: float) -> int:
    """Find where a value sits within the dataset.

    Args:
        stats (MetricStats): Statistics for the metric.
        value (float): The value to rank.

    Preconditions:
        ``stats.count`` is greater than 0 (it is divided by) and ``value`` is not None.

    Returns:
        int: Percent of paddles whose value is at or below ``value`` (0-100).
    """
    assert stats.count > 0, "percentile_rank: stats must contain at least one value"
    assert value is not None, "percentile_rank: value must not be None"
    at_or_below = sum(1 for v in stats.sorted_values if v <= value)
    return round(at_or_below / stats.count * 100)


def compute_metric_stats(values: List[float]) -> Optional[MetricStats]:
    """Summarise one metric.

    Args:
        values (list[float]): Every measured value of the metric.

    Preconditions:
        ``values`` contains no None entries (missing measurements are removed first).

    Returns:
        MetricStats | None: The statistics, or None if ``values`` is empty.
    """
    assert all(v is not None for v in values), \
        "compute_metric_stats: values must not contain None"
    if not values:
        return None
    ordered = tuple(sorted(values))
    return MetricStats(
        minimum=ordered[0],
        maximum=ordered[-1],
        average=sum(ordered) / len(ordered),
        count=len(ordered),
        percentiles={pct: percentile(ordered, pct) for pct in STAT_PERCENTILES},
        sorted_values=ordered,
    )


def compute_all_stats(paddles: Sequence[Paddle]) -> Dict[str, MetricStats]:
    """Summarise every metric in ``config.METRICS``.

    Args:
        paddles (Sequence[Paddle]): The whole dataset.

    Returns:
        dict[str, MetricStats]: Metric key -> statistics (metrics with no data are left out).
    """
    all_stats = {}
    for spec in METRICS:
        stats = compute_metric_stats(known_values(paddles, spec.key))
        if stats is not None:
            all_stats[spec.key] = stats
    return all_stats


def count_by(paddles: Iterable[Paddle], key: str) -> Counter:
    """Count paddles per distinct value of a text field.

    Args:
        paddles (Iterable[Paddle]): Paddles to count.
        key (str): Text field, e.g. ``"paddle_type"``.

    Preconditions:
        ``key`` is a text field listed in ``config.TEXT_COLUMNS``.

    Returns:
        Counter: Value -> number of paddles (blank values are skipped).
    """
    assert key in TEXT_COLUMNS, "count_by: unknown text field " + repr(key)
    return Counter(p.value(key) for p in paddles if p.value(key))
