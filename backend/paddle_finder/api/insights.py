"""Dataset analytics for the Insights page, computed with pandas.

Everything here runs once when the API starts (the data only changes on a
re-seed), so requests just return the cached result.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List

import pandas as pd

from ..core.config import METRICS_BY_KEY, PADDLE_TYPE_ORDER, TOURNAMENT_APPROVAL

TYPE_AVERAGES = ("price", "power", "pop", "spin", "swing_weight", "twist_weight")
POWER_DRIVERS = ("swing_weight", "weight", "balance", "twist_weight", "core", "grip_length", "price")
TOP_BRANDS = 12


def json_safe(value: Any) -> Any:
    """Turn NaN / numpy scalars into JSON-friendly Python values.

    Args:
        value (Any): A value from a DataFrame.

    Returns:
        Any: None for missing values, a plain float/int otherwise.
    """
    if value is None or value is pd.NA:
        return None
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def records(frame: pd.DataFrame) -> List[Dict[str, Any]]:
    """Convert a DataFrame to a list of JSON-safe row dictionaries.

    Args:
        frame (pandas.DataFrame): Any table.

    Returns:
        list[dict]: One dictionary per row.
    """
    return [{key: json_safe(value) for key, value in row.items()}
            for row in frame.to_dict("records")]


def summary(frame: pd.DataFrame) -> Dict[str, Any]:
    """Headline numbers for the whole dataset.

    Args:
        frame (pandas.DataFrame): Cleaned paddles.

    Returns:
        dict: Paddle and brand counts, price median/range, newest year, share approved.
    """
    return {
        "paddles": int(len(frame)),
        "brands": int(frame["brand"].nunique()),
        "median_price": json_safe(round(frame["price"].median(), 2)),
        "min_price": json_safe(frame["price"].min()),
        "max_price": json_safe(frame["price"].max()),
        "newest_year": json_safe(frame["year"].max()),
        "usap_share": round(float(frame["approval"].str.contains(TOURNAMENT_APPROVAL).mean()), 3),
    }


def by_paddle_type(frame: pd.DataFrame) -> List[Dict[str, Any]]:
    """Count and average key metrics per paddle type, control to power.

    Args:
        frame (pandas.DataFrame): Cleaned paddles.

    Returns:
        list[dict]: One row per type: ``paddle_type``, ``count`` and ``avg_<metric>``.
    """
    grouped = frame.groupby("paddle_type").agg(
        count=("id", "size"),
        **{"avg_" + key: (key, "mean") for key in TYPE_AVERAGES},
    ).round(2).reset_index()
    order = {name: index for index, name in enumerate(PADDLE_TYPE_ORDER)}
    grouped = grouped.sort_values("paddle_type", key=lambda col: col.map(order).fillna(len(order)))
    return records(grouped)


def counts(frame: pd.DataFrame, column: str, limit: int = 0) -> List[Dict[str, Any]]:
    """Count paddles per value of a text column, most common first.

    Args:
        frame (pandas.DataFrame): Cleaned paddles.
        column (str): Column to count, e.g. ``"shape"``.
        limit (int): Keep only the top ``limit`` values (0 keeps all).

    Returns:
        list[dict]: ``{"value", "count"}`` rows.
    """
    values = frame.loc[frame[column] != "", column].value_counts()
    if limit:
        values = values.head(limit)
    return [{"value": name, "count": int(number)} for name, number in values.items()]


def power_drivers(frame: pd.DataFrame) -> List[Dict[str, Any]]:
    """Pearson correlation of each build metric with full-swing power.

    Args:
        frame (pandas.DataFrame): Cleaned paddles.

    Returns:
        list[dict]: ``{"metric", "label", "correlation"}``, strongest relationship first.
    """
    rows = []
    for key in POWER_DRIVERS:
        correlation = frame[key].corr(frame["power"])
        if not math.isnan(correlation):
            rows.append({"metric": key, "label": METRICS_BY_KEY[key].label,
                         "correlation": round(float(correlation), 3)})
    return sorted(rows, key=lambda row: abs(row["correlation"]), reverse=True)


def price_vs_power(frame: pd.DataFrame) -> List[Dict[str, Any]]:
    """Every paddle that has both a price and a power measurement.

    Args:
        frame (pandas.DataFrame): Cleaned paddles.

    Returns:
        list[dict]: ``id``, ``brand``, ``name``, ``price``, ``power``, ``paddle_type`` rows.
    """
    points = frame.dropna(subset=["price", "power"])
    return records(points[["id", "brand", "name", "price", "power", "paddle_type"]])


def build_insights(frame: pd.DataFrame) -> Dict[str, Any]:
    """Every analytic the Insights page shows.

    Args:
        frame (pandas.DataFrame): Cleaned paddles (``etl.CLEAN_COLUMNS``).

    Returns:
        dict: ``summary``, ``by_type``, ``by_shape``, ``top_brands``,
        ``power_drivers`` and ``price_vs_power``.
    """
    return {
        "summary": summary(frame),
        "by_type": by_paddle_type(frame),
        "by_shape": counts(frame, "shape"),
        "top_brands": counts(frame, "brand", TOP_BRANDS),
        "power_drivers": power_drivers(frame),
        "price_vs_power": price_vs_power(frame),
    }
