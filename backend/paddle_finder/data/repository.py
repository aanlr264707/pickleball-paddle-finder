"""SQL queries against the ``paddles`` table.

Filtering, text search, sorting and pagination run in the database. The
queries return ids, and the API maps them to the cached ``Paddle`` objects
in the ``PaddleCatalog`` (494 rows is small enough to cache, and the
scoring engine needs every candidate in memory anyway).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

from sqlalchemy import Connection, and_, func, or_, select, true

from ..core.config import METRICS, TOURNAMENT_APPROVAL
from ..core.models import Filters
from .schema import paddles

# Sort options exposed by the API -> SQL expression.
SORT_COLUMNS = {
    "name": func.lower(paddles.c.brand.concat(" ").concat(paddles.c.name)),
    "brand": func.lower(paddles.c.brand),
    "year": paddles.c.year,
    **{spec.key: paddles.c[spec.key] for spec in METRICS},
}
SORT_ORDERS = ("asc", "desc")


@dataclass(frozen=True)
class PaddleQuery:
    """Search, filter, sort and page settings for ``search_paddle_ids``.

    Attributes:
        text (str): Words that must all appear in "brand name" (case-insensitive).
        brand (str | None): Exact brand.
        paddle_type (str | None): Exact paddle type.
        shape (str | None): Exact shape.
        tournament_only (bool): Only USAP-approved paddles.
        max_price (float | None): Highest price.
        sort (str): A key of ``SORT_COLUMNS``.
        order (str): ``"asc"`` or ``"desc"``.
        page (int): Page number, from 1.
        per_page (int): Rows per page.
    """

    text: str = ""
    brand: Optional[str] = None
    paddle_type: Optional[str] = None
    shape: Optional[str] = None
    tournament_only: bool = False
    max_price: Optional[float] = None
    sort: str = "name"
    order: str = "asc"
    page: int = 1
    per_page: int = 24


def escape_like(text: str) -> str:
    """Escape LIKE wildcards so user text is matched literally.

    Args:
        text (str): Raw search text.

    Returns:
        str: ``text`` with ``\\``, ``%`` and ``_`` escaped by a backslash.
    """
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _equals(column, value: Optional[str]):
    """SQL condition ``column = value``, or None when no value is required."""
    return None if value is None else column == value


def _approval_condition(tournament_only: bool):
    """SQL condition for USA Pickleball approval, or None when not required."""
    if not tournament_only:
        return None
    return paddles.c.approval.like("%" + TOURNAMENT_APPROVAL + "%")


def _budget_condition(max_price: Optional[float]):
    """SQL condition for the budget. Unknown prices pass, as in the engine."""
    if max_price is None:
        return None
    return or_(paddles.c.price.is_(None), paddles.c.price <= max_price)


def _combine(conditions) -> object:
    """AND together the conditions that are not None (TRUE when there are none)."""
    active = [condition for condition in conditions if condition is not None]
    return and_(true(), *active)


def candidate_ids(conn: Connection, filters: Filters) -> List[int]:
    """Find the paddles that pass the user's hard requirements.

    This is the SQL twin of ``core.filters.filter_paddles``.

    Args:
        conn (sqlalchemy.Connection): Open connection.
        filters (Filters): Budget, approval, shape, type and feel requirements.

    Returns:
        list[int]: Matching ids in dataset order.
    """
    condition = _combine([
        _budget_condition(filters.max_price),
        _approval_condition(filters.tournament_only),
        _equals(paddles.c.shape, filters.shape),
        _equals(paddles.c.paddle_type, filters.paddle_type),
        _equals(paddles.c.feel, filters.feel),
    ])
    rows = conn.execute(select(paddles.c.id).where(condition).order_by(paddles.c.id))
    return [row.id for row in rows]


def search_paddle_ids(conn: Connection, query: PaddleQuery) -> Tuple[List[int], int]:
    """Search, filter, sort and paginate the catalog.

    Missing values sort last in both directions; ties fall back to id so
    pages never overlap.

    Args:
        conn (sqlalchemy.Connection): Open connection.
        query (PaddleQuery): What to search for and how to order it.

    Preconditions:
        ``query.sort`` is in ``SORT_COLUMNS``, ``query.order`` is in
        ``SORT_ORDERS``, ``query.page >= 1`` and ``query.per_page >= 1``.

    Returns:
        tuple[list[int], int]: The ids on the requested page and the total match count.
    """
    assert query.sort in SORT_COLUMNS, "search_paddle_ids: unknown sort " + repr(query.sort)
    assert query.order in SORT_ORDERS, "search_paddle_ids: unknown order " + repr(query.order)
    assert query.page >= 1 and query.per_page >= 1, "search_paddle_ids: bad page settings"

    full_name = paddles.c.brand.concat(" ").concat(paddles.c.name)
    word_conditions = [full_name.ilike("%" + escape_like(word) + "%", escape="\\")
                       for word in query.text.split()]
    condition = _combine(word_conditions + [
        _equals(paddles.c.brand, query.brand),
        _equals(paddles.c.paddle_type, query.paddle_type),
        _equals(paddles.c.shape, query.shape),
        _approval_condition(query.tournament_only),
        _budget_condition(query.max_price),
    ])

    total = conn.execute(select(func.count()).select_from(paddles).where(condition)).scalar_one()
    sort_column = SORT_COLUMNS[query.sort]
    direction = sort_column.desc() if query.order == "desc" else sort_column.asc()
    rows = conn.execute(
        select(paddles.c.id)
        .where(condition)
        .order_by(direction.nulls_last(), paddles.c.id)
        .limit(query.per_page)
        .offset((query.page - 1) * query.per_page)
    )
    return [row.id for row in rows], total
