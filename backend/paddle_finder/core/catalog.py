"""The in-memory paddle catalog.

``PaddleCatalog`` bundles the paddles with everything derived from them,
computed once at load time so no request has to recompute it:

* ``stats``    -- ``dict`` of metric key -> ``MetricStats``
* ``by_id``    -- ``dict`` index of id -> paddle, for O(1) lookups
* ``by_brand`` -- ``dict`` index of brand -> paddles
* ``options``  -- ``dict`` of text field -> sorted distinct values for menus

The catalog itself does no I/O. ``paddle_finder.data`` builds one from the
CSV (CLI) or from the SQL database (web API).
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

from .config import PADDLE_TYPE_ORDER
from .models import Paddle
from .summary_stats import compute_all_stats

MENU_FIELDS = ("brand", "shape", "paddle_type", "feel")


def option_sort_key(field: str, value: str) -> Tuple[int, str]:
    """Sort key for menu values.

    Paddle types follow the control-to-power spectrum; everything else is
    case-insensitive alphabetical.

    Args:
        field (str): Text field the value belongs to.
        value (str): The value to place.

    Returns:
        tuple[int, str]: Position on the spectrum (0 for other fields), then the folded text.
    """
    if field == "paddle_type" and value in PADDLE_TYPE_ORDER:
        return PADDLE_TYPE_ORDER.index(value), ""
    return len(PADDLE_TYPE_ORDER), value.casefold()


class PaddleCatalog:
    """All paddles plus pre-computed statistics and indexes.

    Attributes:
        paddles (tuple[Paddle, ...]): Every paddle, in dataset order (read-only).
        stats (dict[str, MetricStats]): Metric key -> dataset statistics.
        by_id (dict[int, Paddle]): Id -> paddle.
        by_brand (dict[str, list[Paddle]]): Brand -> that brand's paddles.
        options (dict[str, tuple[str, ...]]): Text field -> sorted distinct values.
    """

    def __init__(self, paddles: Sequence[Paddle]):
        """Build the statistics and indexes for a list of paddles.

        Args:
            paddles (Sequence[Paddle]): The paddles to store.

        Preconditions:
            ``paddles`` contains at least one paddle and every id is unique.
        """
        assert len(paddles) > 0, "PaddleCatalog: needs at least one paddle"
        self.paddles: Tuple[Paddle, ...] = tuple(paddles)
        self.by_id: Dict[int, Paddle] = {p.id: p for p in self.paddles}
        assert len(self.by_id) == len(self.paddles), "PaddleCatalog: paddle ids must be unique"
        self.stats = compute_all_stats(self.paddles)
        self.by_brand = self._index_by_brand(self.paddles)
        self.options = {field: self._distinct(self.paddles, field) for field in MENU_FIELDS}

    def __len__(self) -> int:
        """Return the number of paddles.

        Returns:
            int: How many paddles are stored.
        """
        return len(self.paddles)

    @property
    def brand_count(self) -> int:
        """int: Number of distinct brands."""
        return len(self.by_brand)

    def get(self, paddle_id: int) -> Optional[Paddle]:
        """Look up one paddle.

        Args:
            paddle_id (int): The paddle's id.

        Returns:
            Paddle | None: The paddle, or None if no paddle has that id.
        """
        return self.by_id.get(paddle_id)

    def many(self, paddle_ids: Sequence[int]) -> List[Paddle]:
        """Look up several paddles, keeping the order of ``paddle_ids``.

        Args:
            paddle_ids (Sequence[int]): Ids to fetch (unknown ids are skipped).

        Returns:
            list[Paddle]: The paddles that exist.
        """
        return [self.by_id[i] for i in paddle_ids if i in self.by_id]

    @staticmethod
    def _index_by_brand(paddles: Tuple[Paddle, ...]) -> Dict[str, List[Paddle]]:
        """Group paddles by brand.

        Args:
            paddles (tuple[Paddle, ...]): Paddles to group.

        Returns:
            dict[str, list[Paddle]]: Brand -> paddles of that brand, in dataset order.
        """
        index: Dict[str, List[Paddle]] = {}
        for paddle in paddles:
            index.setdefault(paddle.brand, []).append(paddle)
        return index

    @staticmethod
    def _distinct(paddles: Tuple[Paddle, ...], field: str) -> Tuple[str, ...]:
        """List the distinct non-blank values of a text field.

        Args:
            paddles (tuple[Paddle, ...]): Paddles to read.
            field (str): Text field, e.g. ``"shape"``.

        Returns:
            tuple[str, ...]: Distinct values ordered by ``option_sort_key``.
        """
        values = {p.value(field) for p in paddles if p.value(field)}
        return tuple(sorted(values, key=lambda value: option_sort_key(field, value)))
