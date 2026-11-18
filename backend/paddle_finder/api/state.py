"""What the API keeps in memory between requests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

import pandas as pd
from flask import current_app
from sqlalchemy import Engine

from .. import __version__
from ..core.catalog import PaddleCatalog
from ..data.etl import paddles_from_frame
from ..data.schema import read_frame
from .insights import build_insights

EXTENSION_KEY = "paddle_finder"


@dataclass
class AppState:
    """The database engine plus everything derived from the stored paddles.

    Attributes:
        engine (sqlalchemy.Engine): Connection pool for SQL queries.
        frame (pandas.DataFrame): Every paddle as a DataFrame (for analytics).
        catalog (PaddleCatalog): Every paddle as engine objects, with stats and indexes.
        insights (dict): Pre-computed analytics for ``/api/insights``.
        version (str): Package version.
    """

    engine: Engine
    frame: pd.DataFrame
    catalog: PaddleCatalog
    insights: Dict[str, Any]
    version: str = __version__


def load_state(engine: Engine) -> AppState:
    """Read the paddles table once and build the in-memory state.

    Args:
        engine (sqlalchemy.Engine): Database holding a seeded ``paddles`` table.

    Returns:
        AppState: The state to attach to the app.

    Raises:
        RuntimeError: If the table is empty (seed the database first).
    """
    frame = read_frame(engine)
    if frame.empty:
        raise RuntimeError("The paddles table is empty. Run: python -m paddle_finder.data.seed")
    return AppState(engine=engine, frame=frame, catalog=PaddleCatalog(paddles_from_frame(frame)),
                    insights=build_insights(frame))


def get_state() -> AppState:
    """Return the state of the app handling the current request.

    Returns:
        AppState: The current app's state.
    """
    return current_app.extensions[EXTENSION_KEY]
