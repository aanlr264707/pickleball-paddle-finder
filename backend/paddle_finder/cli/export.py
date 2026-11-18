"""Save recommendations to a CSV file that opens in Numbers or Excel."""

from __future__ import annotations

import csv
from typing import List, Sequence

from ..core.config import METRICS
from ..core.models import ScoredPaddle

LEADING_HEADERS = ("Rank", "Brand", "Paddle", "Match %")
# (paddle attribute, column header) for the text columns after the metrics.
TRAILING_FIELDS = (("shape", "Shape"), ("paddle_type", "Type"), ("feel", "Impact Feel"),
                   ("approval", "Approval"), ("link", "Link"))


def header_row() -> List[str]:
    """Build the header row of the export file.

    Returns:
        list[str]: Rank/name columns, one column per metric, then the text columns.
    """
    return (list(LEADING_HEADERS) + [spec.column for spec in METRICS]
            + [label for _, label in TRAILING_FIELDS])


def to_row(rank: int, item: ScoredPaddle) -> list:
    """Convert one recommendation into CSV cells.

    Args:
        rank (int): Position in the results, starting at 1.
        item (ScoredPaddle): The scored paddle.

    Returns:
        list: Cell values in the same order as ``header_row()``.
    """
    paddle = item.paddle
    return ([rank, paddle.brand, paddle.name, round(item.score, 1)]
            + [paddle.value(spec.key) for spec in METRICS]
            + [paddle.value(key) for key, _ in TRAILING_FIELDS])


def write_recommendations(results: Sequence[ScoredPaddle], path: str) -> None:
    """Write the ranked recommendations to a CSV file (overwriting it).

    Args:
        results (Sequence[ScoredPaddle]): Results, best match first.
        path (str): File to write, e.g. ``"recommendations.csv"``.

    Preconditions:
        ``path`` ends with ``".csv"``.
    """
    assert path.endswith(".csv"), "write_recommendations: path must end with .csv, got " + path
    with open(path, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(header_row())
        for rank, item in enumerate(results, start=1):
            writer.writerow(to_row(rank, item))
