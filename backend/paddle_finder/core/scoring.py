"""Score and rank paddles against a user's preferences.

For each preference a paddle gets a similarity from 0 to 1::

    similarity = max(0, 1 - |value - target| / spread)

where ``spread`` is the distance between the metric's 10th and 90th
percentile (so one outlier paddle can't squash every score). The overall
match is the importance-weighted average of the similarities, as a percent.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence

from .config import (
    MAX_IMPORTANCE,
    MIN_IMPORTANCE,
    MISSING_SIMILARITY,
    SIMILARITY_METRICS,
    SPREAD_HIGH,
    SPREAD_LOW,
    Level,
)
from .models import MetricFit, MetricStats, Paddle, Preference, ScoredPaddle


def resolve_target(answer, stats: MetricStats) -> Optional[float]:
    """Turn a level or a typed answer into a concrete target value.

    Args:
        answer (Level | str | float): A ``Level``, a level word such as
            ``"high"``, or a number (as a number or as text).
        stats (MetricStats): Statistics for the metric, used to look up the
            percentile a level stands for.

    Returns:
        float | None: The target, or None if ``answer`` is not understood.
    """
    if isinstance(answer, Level):
        return stats.percentiles[answer.value]
    if isinstance(answer, (int, float)):
        return float(answer)
    level = Level.from_word(answer)
    if level is not None:
        return stats.percentiles[level.value]
    try:
        return float(answer)
    except ValueError:
        return None


def metric_spread(stats: MetricStats) -> float:
    """Measure how spread out a metric is.

    Args:
        stats (MetricStats): Statistics for the metric.

    Returns:
        float: The 10th-to-90th percentile distance, or 1.0 if that is zero.
    """
    spread = stats.percentiles[SPREAD_HIGH] - stats.percentiles[SPREAD_LOW]
    return spread if spread > 0 else 1.0


def similarity(value: Optional[float], target: float, spread: float) -> float:
    """Score how close a value is to a target.

    Args:
        value (float | None): The paddle's measurement; None if unmeasured.
        target (float): The user's ideal value.
        spread (float): Typical spread of the metric (see ``metric_spread``).

    Preconditions:
        ``spread`` is greater than 0 (it is divided by).

    Returns:
        float: 1.0 on target, falling to 0.0 one spread away;
        ``MISSING_SIMILARITY`` when ``value`` is None.
    """
    assert spread > 0, "similarity: spread must be greater than 0, got " + str(spread)
    if value is None:
        return MISSING_SIMILARITY
    return max(0.0, 1.0 - abs(value - target) / spread)


def score_paddle(paddle: Paddle, preferences: Sequence[Preference],
                 stats: Dict[str, MetricStats]) -> ScoredPaddle:
    """Score one paddle against every preference.

    Args:
        paddle (Paddle): Paddle to score.
        preferences (Sequence[Preference]): The user's targets and importances.
        stats (dict[str, MetricStats]): Dataset statistics per metric.

    Preconditions:
        Every preference's metric has an entry in ``stats``, and every
        importance is between ``MIN_IMPORTANCE`` and ``MAX_IMPORTANCE``.

    Returns:
        ScoredPaddle: The overall match % (0 when there are no preferences)
        and one ``MetricFit`` per preference.
    """
    assert all(pref.metric_key in stats for pref in preferences), \
        "score_paddle: every preference's metric must have statistics"
    assert all(MIN_IMPORTANCE <= pref.importance <= MAX_IMPORTANCE for pref in preferences), \
        ("score_paddle: importance must be between " + str(MIN_IMPORTANCE)
         + " and " + str(MAX_IMPORTANCE))
    fits = []
    weighted_total = 0.0
    total_importance = 0
    for pref in preferences:
        spread = metric_spread(stats[pref.metric_key])
        fit = similarity(paddle.value(pref.metric_key), pref.target, spread)
        fits.append(MetricFit(pref.metric_key, fit))
        weighted_total += fit * pref.importance
        total_importance += pref.importance
    score = weighted_total / total_importance * 100 if total_importance else 0.0
    return ScoredPaddle(paddle, score, tuple(fits))


def match_score(item: ScoredPaddle) -> float:
    """Sort key used to rank results by their overall match.

    Args:
        item (ScoredPaddle): A scored paddle.

    Returns:
        float: The paddle's match score (0 to 100).
    """
    return item.score


def rank_paddles(paddles: Sequence[Paddle], preferences: Sequence[Preference],
                 stats: Dict[str, MetricStats], top_n: int) -> List[ScoredPaddle]:
    """Score every paddle and keep the best matches.

    Sorts with the custom key ``match_score``, highest first. Python's sort
    is stable, so ties keep the order the paddles appear in the database.

    Args:
        paddles (Sequence[Paddle]): Candidate paddles.
        preferences (Sequence[Preference]): The user's targets and importances.
        stats (dict[str, MetricStats]): Dataset statistics per metric.
        top_n (int): How many results to return.

    Preconditions:
        ``top_n`` is at least 1.

    Returns:
        list[ScoredPaddle]: Up to ``top_n`` results, best match first.
    """
    assert top_n >= 1, "rank_paddles: top_n must be at least 1, got " + str(top_n)
    scored = [score_paddle(p, preferences, stats) for p in paddles]
    ranked = sorted(scored, key=match_score, reverse=True)
    return ranked[:top_n]


def profile_preferences(paddle: Paddle, stats: Dict[str, MetricStats],
                        keys: Sequence[str] = SIMILARITY_METRICS) -> List[Preference]:
    """Use a paddle's own measurements as targets (equal importance).

    Args:
        paddle (Paddle): The reference paddle.
        stats (dict[str, MetricStats]): Dataset statistics per metric.
        keys (Sequence[str]): Metrics that describe how a paddle plays.

    Returns:
        list[Preference]: One preference per metric the paddle has a value for.
    """
    return [Preference(key, paddle.value(key), MIN_IMPORTANCE)
            for key in keys if key in stats and paddle.value(key) is not None]


def find_similar(paddle: Paddle, paddles: Sequence[Paddle], stats: Dict[str, MetricStats],
                 limit: int) -> List[ScoredPaddle]:
    """Find the paddles that play most like ``paddle``.

    "Similar" uses the same Match % as recommendations, with the reference
    paddle's own measurements as the targets.

    Args:
        paddle (Paddle): The reference paddle.
        paddles (Sequence[Paddle]): Every candidate (the reference itself is skipped).
        stats (dict[str, MetricStats]): Dataset statistics per metric.
        limit (int): How many similar paddles to return.

    Preconditions:
        ``limit`` is at least 1.

    Returns:
        list[ScoredPaddle]: Up to ``limit`` paddles, most similar first.
    """
    assert limit >= 1, "find_similar: limit must be at least 1, got " + str(limit)
    others = [p for p in paddles if p.id != paddle.id]
    return rank_paddles(others, profile_preferences(paddle, stats), stats, limit)
