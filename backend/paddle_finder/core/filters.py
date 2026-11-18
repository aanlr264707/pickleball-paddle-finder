"""Hard filters (budget, approval, shape, type, feel) and name search."""

from __future__ import annotations

from typing import Iterable, List, Optional

from .config import TOURNAMENT_APPROVAL
from .models import Filters, Paddle


def within_budget(paddle: Paddle, max_price: Optional[float]) -> bool:
    """Check a paddle against the budget.

    Args:
        paddle (Paddle): Paddle to check.
        max_price (float | None): Highest acceptable price; None means no limit.

    Returns:
        bool: True if there is no limit, the price is unknown, or it fits the budget.
    """
    return max_price is None or paddle.price is None or paddle.price <= max_price


def matches_option(actual: str, wanted: Optional[str]) -> bool:
    """Check one categorical requirement.

    Args:
        actual (str): The paddle's value, e.g. ``"Elongated"``.
        wanted (str | None): The required value; None means "any".

    Returns:
        bool: True if nothing was required or the values are equal.
    """
    return wanted is None or actual == wanted


def is_tournament_legal(paddle: Paddle) -> bool:
    """Check for USA Pickleball approval.

    Args:
        paddle (Paddle): Paddle to check.

    Returns:
        bool: True if the approval body includes USAP.
    """
    return TOURNAMENT_APPROVAL in paddle.approval


def passes_filters(paddle: Paddle, filters: Filters) -> bool:
    """Check a paddle against every hard requirement.

    Args:
        paddle (Paddle): Paddle to check.
        filters (Filters): The user's requirements.

    Returns:
        bool: True if the paddle satisfies all of them.
    """
    if not within_budget(paddle, filters.max_price):
        return False
    if filters.tournament_only and not is_tournament_legal(paddle):
        return False
    return (matches_option(paddle.shape, filters.shape)
            and matches_option(paddle.paddle_type, filters.paddle_type)
            and matches_option(paddle.feel, filters.feel))


def filter_paddles(paddles: Iterable[Paddle], filters: Filters) -> List[Paddle]:
    """Keep only the paddles that pass the filters.

    Args:
        paddles (Iterable[Paddle]): Candidate paddles.
        filters (Filters): The user's requirements.

    Returns:
        list[Paddle]: Paddles that passed, in their original order.
    """
    return [p for p in paddles if passes_filters(p, filters)]


def search_by_name(paddles: Iterable[Paddle], text: str) -> List[Paddle]:
    """Find paddles whose brand + name contains some text (case-insensitive).

    Args:
        paddles (Iterable[Paddle]): Paddles to search.
        text (str): Search text, e.g. ``"perseus"``.

    Returns:
        list[Paddle]: Matching paddles; empty when ``text`` is blank.
    """
    text = text.strip().lower()
    if not text:
        return []
    return [p for p in paddles if text in p.full_name.lower()]
