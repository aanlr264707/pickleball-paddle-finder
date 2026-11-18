"""Turn untrusted request input into engine objects, or raise ``ApiError``.

The engine's functions assert their preconditions. This module is the
boundary that guarantees those preconditions hold for anything a client sends.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Mapping, Optional, Sequence

from ..core.catalog import PaddleCatalog
from ..core.config import (
    API_MAX_COMPARE,
    DEFAULT_IMPORTANCE,
    DEFAULT_PAGE_SIZE,
    MAX_IMPORTANCE,
    MAX_PAGE_SIZE,
    MAX_RESULTS,
    MIN_COMPARE,
    MIN_IMPORTANCE,
    QUESTIONNAIRE_METRICS,
    TOP_N,
    Level,
)
from ..core.models import Filters, Preference
from ..core.presets import find_preset, preset_preferences
from ..core.scoring import resolve_target
from ..data.repository import SORT_COLUMNS, SORT_ORDERS, PaddleQuery
from .errors import ApiError

QUESTIONNAIRE_KEYS = {spec.key for spec in QUESTIONNAIRE_METRICS}
TRUE_WORDS = {"1", "true", "yes", "on"}
FALSE_WORDS = {"0", "false", "no", "off", ""}


# --- Small parsers ----------------------------------------------------------------------

def parse_number(value: Any, field: str, minimum: Optional[float] = None) -> float:
    """Parse a finite number.

    Args:
        value (Any): Number or numeric string.
        field (str): Field name for the error message.
        minimum (float | None): Smallest allowed value.

    Returns:
        float: The number.

    Raises:
        ApiError: If ``value`` is not a finite number or is below ``minimum``.
    """
    if isinstance(value, bool):
        raise ApiError("must be a number", field=field)
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ApiError("must be a number", field=field) from None
    if not math.isfinite(number):
        raise ApiError("must be a finite number", field=field)
    if minimum is not None and number < minimum:
        raise ApiError("must be at least " + str(minimum), field=field)
    return number


def parse_int(value: Any, field: str, low: int, high: int) -> int:
    """Parse a whole number within ``low``..``high``.

    Args:
        value (Any): Number or numeric string.
        field (str): Field name for the error message.
        low (int): Smallest allowed value.
        high (int): Largest allowed value.

    Returns:
        int: The number.

    Raises:
        ApiError: If ``value`` is not a whole number in range.
    """
    number = parse_number(value, field)
    if not number.is_integer() or not low <= number <= high:
        raise ApiError("must be a whole number from " + str(low) + " to " + str(high), field=field)
    return int(number)


def parse_bool(value: Any, field: str) -> bool:
    """Parse a JSON boolean or a query-string flag such as ``"true"`` / ``"1"``.

    Args:
        value (Any): The raw value.
        field (str): Field name for the error message.

    Returns:
        bool: The flag.

    Raises:
        ApiError: If ``value`` is not recognisable as true or false.
    """
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    text = str(value).strip().lower()
    if text in TRUE_WORDS:
        return True
    if text in FALSE_WORDS:
        return False
    raise ApiError("must be true or false", field=field)


def parse_choice(value: Any, field: str, choices: Sequence[str]) -> Optional[str]:
    """Parse an optional value that must be one of ``choices``.

    Args:
        value (Any): The raw value; None or "" mean "any".
        field (str): Field name for the error message.
        choices (Sequence[str]): Allowed values.

    Returns:
        str | None: The value, or None for "any".

    Raises:
        ApiError: If ``value`` is not one of ``choices``.
    """
    if value is None or value == "":
        return None
    if value not in choices:
        raise ApiError("must be one of: " + ", ".join(choices), field=field)
    return value


def require_object(value: Any, field: str) -> Mapping[str, Any]:
    """Check that a JSON value is an object.

    Args:
        value (Any): The raw value.
        field (str): Field name for the error message.

    Returns:
        Mapping[str, Any]: The object (an empty dict for None).

    Raises:
        ApiError: If ``value`` is not an object.
    """
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ApiError("must be a JSON object", field=field)
    return value


# --- Request bodies ----------------------------------------------------------------------

def parse_filters(raw: Any, catalog: PaddleCatalog) -> Filters:
    """Validate the ``filters`` object of a recommendation request.

    Args:
        raw (Any): The JSON value.
        catalog (PaddleCatalog): Supplies the valid shapes, types and feels.

    Returns:
        Filters: The hard requirements.
    """
    body = require_object(raw, "filters")
    max_price = body.get("max_price")
    return Filters(
        max_price=None if max_price in (None, "") else parse_number(max_price, "filters.max_price", 0),
        tournament_only=parse_bool(body.get("tournament_only"), "filters.tournament_only"),
        shape=parse_choice(body.get("shape"), "filters.shape", catalog.options["shape"]),
        paddle_type=parse_choice(body.get("paddle_type"), "filters.paddle_type",
                                 catalog.options["paddle_type"]),
        feel=parse_choice(body.get("feel"), "filters.feel", catalog.options["feel"]),
    )


def parse_target(value: Any, field: str, catalog: PaddleCatalog, metric: str) -> float:
    """Validate a target: ``"low"``, ``"medium"``, ``"high"`` or a number.

    Args:
        value (Any): The raw target.
        field (str): Field name for the error message.
        catalog (PaddleCatalog): Supplies the metric statistics.
        metric (str): Metric key.

    Returns:
        float: The concrete target value.

    Raises:
        ApiError: If the target is missing or not understood.
    """
    if isinstance(value, str) and Level.from_word(value) is None:
        value = parse_number(value, field)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        value = parse_number(value, field)
    elif not isinstance(value, str):
        raise ApiError("must be low, medium, high or a number", field=field)
    target = resolve_target(value, catalog.stats[metric])
    if target is None:
        raise ApiError("must be low, medium, high or a number", field=field)
    return target


def parse_preferences(raw: Any, catalog: PaddleCatalog) -> List[Preference]:
    """Validate the ``preferences`` list of a recommendation request.

    Args:
        raw (Any): The JSON value: ``[{"metric", "target", "importance"}, ...]``.
        catalog (PaddleCatalog): Supplies the metric statistics.

    Returns:
        list[Preference]: One preference per entry.

    Raises:
        ApiError: On an unknown or repeated metric, a bad target or importance.
    """
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ApiError("must be a list", field="preferences")
    preferences: List[Preference] = []
    seen = set()
    for index, item in enumerate(raw):
        prefix = "preferences[" + str(index) + "]"
        entry = require_object(item, prefix)
        metric = entry.get("metric")
        if metric not in QUESTIONNAIRE_KEYS or metric not in catalog.stats:
            raise ApiError("unknown metric " + repr(metric), field=prefix + ".metric")
        if metric in seen:
            raise ApiError("metric " + repr(metric) + " is listed twice", field=prefix + ".metric")
        seen.add(metric)
        target = parse_target(entry.get("target"), prefix + ".target", catalog, metric)
        importance = parse_int(entry.get("importance", DEFAULT_IMPORTANCE), prefix + ".importance",
                               MIN_IMPORTANCE, MAX_IMPORTANCE)
        preferences.append(Preference(metric, target, importance))
    return preferences


def parse_recommendation_request(body: Any, catalog: PaddleCatalog) -> Dict[str, Any]:
    """Validate a whole ``POST /api/recommendations`` body.

    A body may name a ``preset`` (slug) instead of listing ``preferences``.

    Args:
        body (Any): The parsed JSON body.
        catalog (PaddleCatalog): Supplies options and statistics.

    Returns:
        dict: ``filters`` (Filters), ``preferences`` (list[Preference]),
        ``preset`` (Preset | None) and ``limit`` (int).

    Raises:
        ApiError: If any part of the body is invalid.
    """
    body = require_object(body, "body")
    preset = None
    if body.get("preset"):
        preset = find_preset(str(body["preset"]))
        if preset is None:
            raise ApiError("unknown preset " + repr(body["preset"]), field="preset")
        if body.get("preferences"):
            raise ApiError("send either a preset or preferences, not both", field="preferences")
        preferences = preset_preferences(preset, catalog.stats)
    else:
        preferences = parse_preferences(body.get("preferences"), catalog)
    return {
        "filters": parse_filters(body.get("filters"), catalog),
        "preferences": preferences,
        "preset": preset,
        "limit": parse_int(body.get("limit", TOP_N), "limit", 1, MAX_RESULTS),
    }


# --- Query strings ---------------------------------------------------------------------------

def parse_paddle_query(args: Mapping[str, str], catalog: PaddleCatalog) -> PaddleQuery:
    """Validate the query string of ``GET /api/paddles``.

    Args:
        args (Mapping[str, str]): ``request.args``.
        catalog (PaddleCatalog): Supplies the valid brands, types and shapes.

    Returns:
        PaddleQuery: Search, filter, sort and page settings.
    """
    max_price = args.get("max_price")
    return PaddleQuery(
        text=args.get("q", "").strip()[:100],
        brand=parse_choice(args.get("brand"), "brand", catalog.options["brand"]),
        paddle_type=parse_choice(args.get("paddle_type"), "paddle_type",
                                 catalog.options["paddle_type"]),
        shape=parse_choice(args.get("shape"), "shape", catalog.options["shape"]),
        tournament_only=parse_bool(args.get("tournament_only"), "tournament_only"),
        max_price=None if not max_price else parse_number(max_price, "max_price", 0),
        sort=parse_choice(args.get("sort", "name"), "sort", list(SORT_COLUMNS)) or "name",
        order=parse_choice(args.get("order", "asc"), "order", SORT_ORDERS) or "asc",
        page=parse_int(args.get("page", 1), "page", 1, 10_000),
        per_page=parse_int(args.get("per_page", DEFAULT_PAGE_SIZE), "per_page", 1, MAX_PAGE_SIZE),
    )


def parse_compare_ids(raw: Optional[str], catalog: PaddleCatalog) -> List[int]:
    """Validate ``?ids=3,17,42`` for the compare endpoint.

    Args:
        raw (str | None): Comma-separated ids.
        catalog (PaddleCatalog): Used to check the ids exist.

    Returns:
        list[int]: Distinct existing ids, in the order given.

    Raises:
        ApiError: If there are too few/many ids, or one is unknown.
    """
    parts = [part.strip() for part in (raw or "").split(",") if part.strip()]
    ids: List[int] = []
    for part in parts:
        paddle_id = parse_int(part, "ids", 1, 10_000_000)
        if catalog.get(paddle_id) is None:
            raise ApiError("no paddle with id " + str(paddle_id), status=404, field="ids")
        if paddle_id not in ids:
            ids.append(paddle_id)
    if not MIN_COMPARE <= len(ids) <= API_MAX_COMPARE:
        raise ApiError("give " + str(MIN_COMPARE) + " to " + str(API_MAX_COMPARE)
                       + " different paddle ids", field="ids")
    return ids
