import pytest

from paddle_finder.core import filters, presets, scoring
from paddle_finder.core.config import PADDLE_TYPE_ORDER, Level
from paddle_finder.core.models import Filters, Preference


def test_similarity_is_one_on_target_and_zero_one_spread_away():
    assert scoring.similarity(10, 10, 4) == 1.0
    assert scoring.similarity(12, 10, 4) == 0.5
    assert scoring.similarity(30, 10, 4) == 0.0
    assert scoring.similarity(None, 10, 4) == 0.5


def test_similarity_precondition():
    with pytest.raises(AssertionError):
        scoring.similarity(1, 1, 0)


def test_ranking_is_best_first(catalog):
    prefs = [Preference("power", catalog.stats["power"].maximum, 5)]
    results = scoring.rank_paddles(catalog.paddles, prefs, catalog.stats, 10)
    scores = [item.score for item in results]
    assert scores == sorted(scores, reverse=True)
    assert results[0].paddle.power == catalog.stats["power"].maximum


def test_ties_keep_dataset_order(catalog):
    results = scoring.rank_paddles(catalog.paddles, [], catalog.stats, 5)
    assert [item.paddle.id for item in results] == [1, 2, 3, 4, 5]


def test_levels_resolve_to_percentiles(catalog):
    stats = catalog.stats["swing_weight"]
    assert scoring.resolve_target(Level.HIGH, stats) == stats.percentiles[80]
    assert scoring.resolve_target("med", stats) == stats.median
    assert scoring.resolve_target("112", stats) == 112.0
    assert scoring.resolve_target("banana", stats) is None


def test_preset_slugs_and_lookup(catalog):
    assert [p.slug for p in presets.PRESETS] == [
        "power-banger", "control-dinker", "spin-player", "arm-friendly", "fast-hands"]
    preset = presets.find_preset("spin-player")
    prefs = presets.preset_preferences(preset, catalog.stats)
    assert {p.metric_key for p in prefs} == {"spin", "power"}
    assert presets.find_preset("nope") is None


def test_similar_paddles_exclude_the_paddle_itself(catalog):
    paddle = catalog.get(1)
    results = scoring.find_similar(paddle, catalog.paddles, catalog.stats, 5)
    assert len(results) == 5
    assert paddle.id not in [item.paddle.id for item in results]
    assert results[0].score >= results[-1].score > 50


def test_filters(catalog):
    picked = filters.filter_paddles(catalog.paddles, Filters(max_price=150, tournament_only=True))
    assert picked
    assert all(p.price is None or p.price <= 150 for p in picked)
    assert all("USAP" in p.approval for p in picked)


def test_paddle_type_menu_follows_the_control_to_power_spectrum(catalog):
    assert catalog.options["paddle_type"] == PADDLE_TYPE_ORDER


def test_catalog_lookups(catalog):
    assert catalog.get(3).id == 3
    assert catalog.get(99999) is None
    assert [p.id for p in catalog.many([5, 2, 99999])] == [5, 2]
