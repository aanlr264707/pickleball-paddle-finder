"""Extract-transform-load for the raw paddle spreadsheet, built on pandas.

The raw CSV is a hand-maintained spreadsheet export, so it needs cleaning
before anything can trust it:

* prices like ``"$169.99"`` and percentages like ``"59%"`` become numbers
* stray whitespace (``"Elongated "``) is stripped
* the same brand typed different ways (``"GRUVN"`` / ``"Gruvn"``,
  ``"Element6"`` / ``"Element 6"``) is merged into one spelling
* physically impossible values (a 5.75 in grip *size*) become missing
* links that aren't URLs ("Coming Soon") become blank
* rows without a paddle name and duplicate paddles are dropped

Every consumer (the CLI, the database seeder and the API) goes through
``load_clean_frame`` so the rules live in exactly one place.
"""

from __future__ import annotations

import math
from typing import Dict, List

import pandas as pd

from ..core.catalog import PaddleCatalog
from ..core.config import METRICS, TEXT_COLUMNS, VALID_RANGES, YEAR_COLUMN
from ..core.models import Paddle

TEXT_KEYS: List[str] = list(TEXT_COLUMNS)
NUMERIC_KEYS: List[str] = [spec.key for spec in METRICS]
# Raw CSV header -> clean column name.
RENAME: Dict[str, str] = {
    **{column: key for key, column in TEXT_COLUMNS.items()},
    **{spec.column: spec.key for spec in METRICS},
    YEAR_COLUMN: "year",
}
CLEAN_COLUMNS: List[str] = ["id"] + TEXT_KEYS + ["year"] + NUMERIC_KEYS


def read_raw(path: str) -> pd.DataFrame:
    """Read the CSV exactly as written (every cell as text, blanks kept as "").

    Args:
        path (str): Location of the CSV file.

    Returns:
        pandas.DataFrame: The raw table.

    Raises:
        FileNotFoundError: If ``path`` does not exist.
    """
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def to_number(column: pd.Series) -> pd.Series:
    """Convert text such as ``"$1,169.99"`` or ``"59%"`` to floats.

    Args:
        column (pandas.Series): Text cells.

    Returns:
        pandas.Series: Floats, NaN where the cell was blank or not a number.
    """
    cleaned = column.astype(str).str.strip().str.replace(r"[$,%]", "", regex=True)
    return pd.to_numeric(cleaned, errors="coerce").astype(float)


def canonical_brands(brands: pd.Series) -> pd.Series:
    """Merge brand names that differ only in case, spacing or punctuation.

    The most common spelling in the data wins (ties: alphabetical).

    Args:
        brands (pandas.Series): Brand names.

    Returns:
        pandas.Series: Brand names with one spelling per brand.
    """
    match_key = brands.str.casefold().str.replace(r"[^0-9a-z]", "", regex=True)
    counts = (pd.DataFrame({"key": match_key, "brand": brands})
              .value_counts()
              .reset_index(name="n")
              .sort_values(["key", "n", "brand"], ascending=[True, False, True]))
    winner = counts.drop_duplicates("key").set_index("key")["brand"]
    return match_key.map(winner)


def clean(raw: pd.DataFrame) -> pd.DataFrame:
    """Apply every cleaning rule and give each paddle a stable id.

    Args:
        raw (pandas.DataFrame): Output of ``read_raw``.

    Returns:
        pandas.DataFrame: One row per paddle with the columns in ``CLEAN_COLUMNS``.

    Raises:
        ValueError: If a required column is missing from the CSV.
    """
    missing = [column for column in RENAME if column not in raw.columns]
    if missing:
        raise ValueError("CSV is missing required columns: " + ", ".join(missing))

    frame = raw[list(RENAME)].rename(columns=RENAME)
    for key in TEXT_KEYS:
        frame[key] = frame[key].str.strip()
    frame = frame[frame["name"] != ""].copy()
    frame["brand"] = canonical_brands(frame["brand"])
    frame["link"] = frame["link"].where(frame["link"].str.match(r"https?://"), "")

    for key in NUMERIC_KEYS:
        frame[key] = to_number(frame[key])
    for key, (low, high) in VALID_RANGES.items():
        frame[key] = frame[key].where(frame[key].between(low, high))
    frame["year"] = to_number(frame["year"]).round().astype("Int64")

    frame = frame.drop_duplicates(["brand", "name"]).reset_index(drop=True)
    frame.insert(0, "id", range(1, len(frame) + 1))
    return frame[CLEAN_COLUMNS]


def load_clean_frame(path: str) -> pd.DataFrame:
    """Read and clean the CSV in one step.

    Args:
        path (str): Location of the CSV file.

    Returns:
        pandas.DataFrame: The cleaned table.
    """
    return clean(read_raw(path))


def _optional_float(value) -> "float | None":
    """Return ``value`` as a float, or None for NaN / NA / None."""
    if value is None or value is pd.NA or (isinstance(value, float) and math.isnan(value)):
        return None
    return float(value)


def paddles_from_frame(frame: pd.DataFrame) -> List[Paddle]:
    """Turn cleaned rows into ``Paddle`` objects (plain Python types, None for missing).

    Args:
        frame (pandas.DataFrame): A table with the ``CLEAN_COLUMNS`` columns.

    Returns:
        list[Paddle]: One paddle per row, in row order.
    """
    paddles = []
    for row in frame.to_dict("records"):
        year = _optional_float(row["year"])
        paddles.append(Paddle(
            id=int(row["id"]),
            year=None if year is None else int(year),
            **{key: "" if row[key] is None else str(row[key]) for key in TEXT_KEYS},
            **{key: _optional_float(row[key]) for key in NUMERIC_KEYS},
        ))
    return paddles


def catalog_from_csv(path: str) -> PaddleCatalog:
    """Build an in-memory catalog straight from the CSV (used by the CLI).

    Args:
        path (str): Location of the CSV file.

    Returns:
        PaddleCatalog: The cleaned paddles with statistics and indexes.
    """
    return PaddleCatalog(paddles_from_frame(load_clean_frame(path)))
