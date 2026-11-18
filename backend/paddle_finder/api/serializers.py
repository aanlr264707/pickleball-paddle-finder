"""Convert engine objects to JSON-ready dictionaries."""

from __future__ import annotations

from dataclasses import asdict
from typing import Dict

from ..core.config import METRICS, METRICS_BY_KEY, QUESTIONNAIRE_METRICS, MetricSpec
from ..core.filters import is_tournament_legal
from ..core.models import MetricStats, Paddle, Preference, Preset, ScoredPaddle
from ..core.summary_stats import percentile_rank

QUESTIONNAIRE_KEYS = {spec.key for spec in QUESTIONNAIRE_METRICS}


def paddle_dict(paddle: Paddle) -> dict:
    """Every field of a paddle plus a few derived flags.

    Args:
        paddle (Paddle): The paddle.

    Returns:
        dict: Paddle fields, ``full_name`` and ``tournament_legal``.
    """
    data = asdict(paddle)
    data["full_name"] = paddle.full_name
    data["tournament_legal"] = is_tournament_legal(paddle)
    return data


def percentiles_dict(paddle: Paddle, stats: Dict[str, MetricStats]) -> Dict[str, int]:
    """Where each of a paddle's measurements sits in the dataset.

    Args:
        paddle (Paddle): The paddle.
        stats (dict[str, MetricStats]): Dataset statistics per metric.

    Returns:
        dict[str, int]: Metric key -> percentile rank (0-100); missing values are left out.
    """
    return {spec.key: percentile_rank(stats[spec.key], paddle.value(spec.key))
            for spec in METRICS
            if spec.key in stats and paddle.value(spec.key) is not None}


def scored_dict(rank: int, item: ScoredPaddle) -> dict:
    """One ranked recommendation.

    Args:
        rank (int): Position, from 1.
        item (ScoredPaddle): The scored paddle.

    Returns:
        dict: Rank, rounded score, best/worst fit, per-metric fits and the paddle.
    """
    return {
        "rank": rank,
        "score": round(item.score, 1),
        "best_fit": item.best_fit,
        "worst_fit": item.worst_fit,
        "fits": [{"metric": fit.metric_key,
                  "similarity": round(fit.similarity, 3),
                  "value": item.paddle.value(fit.metric_key)} for fit in item.fits],
        "paddle": paddle_dict(item.paddle),
    }


def preference_dict(preference: Preference) -> dict:
    """A resolved preference, so the client can show the targets actually used.

    Args:
        preference (Preference): The preference.

    Returns:
        dict: Metric key and label, numeric target and importance.
    """
    return {"metric": preference.metric_key,
            "label": METRICS_BY_KEY[preference.metric_key].label,
            "target": round(preference.target, 3),
            "importance": preference.importance}


def metric_dict(spec: MetricSpec, stats: MetricStats) -> dict:
    """A metric's description and dataset statistics.

    Args:
        spec (MetricSpec): The metric.
        stats (MetricStats): Its statistics.

    Returns:
        dict: Labels, units and min/max/average/percentile values.
    """
    return {
        "key": spec.key, "label": spec.label, "unit": spec.unit, "description": spec.description,
        "in_questionnaire": spec.key in QUESTIONNAIRE_KEYS,
        "count": stats.count,
        "min": stats.minimum, "max": stats.maximum, "average": round(stats.average, 3),
        "percentiles": {str(pct): round(value, 3) for pct, value in stats.percentiles.items()},
    }


def preset_dict(preset: Preset) -> dict:
    """A play-style preset.

    Args:
        preset (Preset): The preset.

    Returns:
        dict: Slug, name, description and targets (level names or numbers).
    """
    targets = []
    for key, (target, importance) in preset.targets.items():
        shown = target.name.lower() if hasattr(target, "name") else target
        targets.append({"metric": key, "label": METRICS_BY_KEY[key].label,
                        "target": shown, "importance": importance})
    return {"slug": preset.slug, "name": preset.name, "description": preset.description,
            "targets": targets}
