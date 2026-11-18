"""REST endpoints, all under ``/api``.

Each view only coordinates: validation turns input into engine objects,
the repository runs SQL, the engine scores, the serializers shape JSON.
"""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from ..core import presets, scoring
from ..core.config import METRICS, SIMILAR_LIMIT
from ..data import repository
from .errors import ApiError
from .serializers import metric_dict, paddle_dict, percentiles_dict, preference_dict, preset_dict, scored_dict
from .state import get_state
from .validation import parse_compare_ids, parse_int, parse_paddle_query, parse_recommendation_request

bp = Blueprint("api", __name__, url_prefix="/api")


@bp.get("/health")
def health():
    """Liveness check: is the API up and is the database reachable?"""
    state = get_state()
    return jsonify(status="ok", database=state.engine.dialect.name,
                   paddles=len(state.catalog), version=state.version)


@bp.get("/metrics")
def metrics():
    """Every numeric metric with its description and dataset statistics."""
    stats = get_state().catalog.stats
    return jsonify([metric_dict(spec, stats[spec.key]) for spec in METRICS if spec.key in stats])


@bp.get("/options")
def options():
    """Distinct values for the shape, paddle type, impact feel and brand menus."""
    return jsonify({field: list(values) for field, values in get_state().catalog.options.items()})


@bp.get("/presets")
def preset_list():
    """The ready-made play styles."""
    return jsonify([preset_dict(preset) for preset in presets.PRESETS])


@bp.post("/recommendations")
def recommend():
    """Filter in SQL, score in the engine, return the best matches.

    Body: ``{"filters": {...}, "preferences": [...]}`` or ``{"preset": "<slug>"}``.
    """
    state = get_state()
    body = request.get_json(silent=True)
    if body is None and request.get_data():
        raise ApiError("request body must be valid JSON", field="body")
    parsed = parse_recommendation_request(body, state.catalog)
    with state.engine.connect() as conn:
        candidate_ids = repository.candidate_ids(conn, parsed["filters"])
    candidates = state.catalog.many(candidate_ids)
    results = scoring.rank_paddles(candidates, parsed["preferences"], state.catalog.stats,
                                   parsed["limit"]) if candidates else []
    return jsonify(
        candidates=len(candidates),
        ranked=bool(parsed["preferences"]),
        preset=parsed["preset"].slug if parsed["preset"] else None,
        preferences=[preference_dict(p) for p in parsed["preferences"]],
        results=[scored_dict(rank, item) for rank, item in enumerate(results, start=1)],
    )


@bp.get("/paddles")
def paddle_list():
    """Search, filter, sort and paginate the catalog (all done in SQL)."""
    state = get_state()
    query = parse_paddle_query(request.args, state.catalog)
    with state.engine.connect() as conn:
        ids, total = repository.search_paddle_ids(conn, query)
    pages = (total + query.per_page - 1) // query.per_page
    return jsonify(items=[paddle_dict(p) for p in state.catalog.many(ids)], total=total,
                   page=query.page, per_page=query.per_page, pages=pages)


def _require_paddle(paddle_id: int):
    """Return the paddle with ``paddle_id`` or raise a 404 ``ApiError``."""
    paddle = get_state().catalog.get(paddle_id)
    if paddle is None:
        raise ApiError("no paddle with id " + str(paddle_id), status=404)
    return paddle


@bp.get("/paddles/<int:paddle_id>")
def paddle_detail(paddle_id: int):
    """One paddle with the dataset percentile of every measurement."""
    paddle = _require_paddle(paddle_id)
    return jsonify(paddle=paddle_dict(paddle),
                   percentiles=percentiles_dict(paddle, get_state().catalog.stats))


@bp.get("/paddles/<int:paddle_id>/similar")
def similar(paddle_id: int):
    """The paddles whose measurements are closest to this one."""
    state = get_state()
    paddle = _require_paddle(paddle_id)
    limit = parse_int(request.args.get("limit", SIMILAR_LIMIT), "limit", 1, 20)
    results = scoring.find_similar(paddle, state.catalog.paddles, state.catalog.stats, limit)
    return jsonify([scored_dict(rank, item) for rank, item in enumerate(results, start=1)])


@bp.get("/compare")
def compare():
    """Two to four paddles side by side, with percentiles. ``?ids=1,2,3``."""
    state = get_state()
    ids = parse_compare_ids(request.args.get("ids"), state.catalog)
    return jsonify([{"paddle": paddle_dict(p), "percentiles": percentiles_dict(p, state.catalog.stats)}
                    for p in state.catalog.many(ids)])


@bp.get("/insights")
def insights():
    """Dataset analytics computed with pandas at startup."""
    return jsonify(get_state().insights)
