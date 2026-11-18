"""SQL schema plus helpers to create, seed and read the ``paddles`` table.

The schema is defined with SQLAlchemy Core, so the same code runs on
PostgreSQL (Docker / production) and SQLite (local quick start and tests).
"""

from __future__ import annotations

import pandas as pd
from sqlalchemy import (
    Column,
    Engine,
    Float,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    create_engine,
    delete,
    func,
    select,
)

from .etl import CLEAN_COLUMNS

metadata = MetaData()

paddles = Table(
    "paddles", metadata,
    Column("id", Integer, primary_key=True, autoincrement=False),
    Column("brand", String(80), nullable=False),
    Column("name", String(160), nullable=False),
    Column("link", Text, nullable=False, server_default=""),
    Column("approval", String(40), nullable=False, server_default=""),
    Column("shape", String(40), nullable=False, server_default=""),
    Column("face", String(60), nullable=False, server_default=""),
    Column("grit", String(60), nullable=False, server_default=""),
    Column("build", String(60), nullable=False, server_default=""),
    Column("paddle_type", String(40), nullable=False, server_default=""),
    Column("feel", String(40), nullable=False, server_default=""),
    Column("spin_rating", String(20), nullable=False, server_default=""),
    Column("spin_durability", String(20), nullable=False, server_default=""),
    Column("year", Integer),
    Column("price", Float),
    Column("weight", Float),
    Column("swing_weight", Float),
    Column("twist_weight", Float),
    Column("power", Float),
    Column("pop", Float),
    Column("spin", Float),
    Column("balance", Float),
    Column("core", Float),
    Column("grip_length", Float),
    Column("grip_size", Float),
    UniqueConstraint("brand", "name", name="uq_paddles_brand_name"),
    Index("ix_paddles_brand", "brand"),
    Index("ix_paddles_paddle_type", "paddle_type"),
    Index("ix_paddles_shape", "shape"),
    Index("ix_paddles_price", "price"),
)


def make_engine(url: str) -> Engine:
    """Create a SQLAlchemy engine.

    ``postgres://`` and ``postgresql://`` URLs (as hosting providers hand
    them out) are pointed at the psycopg 3 driver.

    Args:
        url (str): Database URL, e.g. ``postgresql://user:pw@host/db`` or ``sqlite:///x.db``.

    Returns:
        sqlalchemy.Engine: A pooled engine.
    """
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            url = "postgresql+psycopg://" + url[len(prefix):]
    return create_engine(url, pool_pre_ping=True, future=True)


def create_schema(engine: Engine) -> None:
    """Create the table and indexes if they don't exist yet.

    Args:
        engine (sqlalchemy.Engine): Target database.
    """
    metadata.create_all(engine)


def count_paddles(engine: Engine) -> int:
    """Count the stored paddles.

    Args:
        engine (sqlalchemy.Engine): Target database.

    Returns:
        int: Number of rows in ``paddles``.
    """
    with engine.connect() as conn:
        return conn.execute(select(func.count()).select_from(paddles)).scalar_one()


def seed(engine: Engine, frame: pd.DataFrame) -> int:
    """Replace every stored paddle with the rows of a cleaned DataFrame.

    Runs in one transaction, so a failed load leaves the old data in place.

    Args:
        engine (sqlalchemy.Engine): Target database.
        frame (pandas.DataFrame): Output of ``etl.load_clean_frame``.

    Preconditions:
        ``frame`` has exactly the columns in ``etl.CLEAN_COLUMNS``.

    Returns:
        int: Number of paddles written.
    """
    assert list(frame.columns) == CLEAN_COLUMNS, "seed: frame must come from etl.clean()"
    create_schema(engine)
    with engine.begin() as conn:
        conn.execute(delete(paddles))
        frame.to_sql(paddles.name, conn, if_exists="append", index=False,
                     method="multi", chunksize=200)
    return len(frame)


def read_frame(engine: Engine) -> pd.DataFrame:
    """Load every stored paddle into a DataFrame, ordered by id.

    Args:
        engine (sqlalchemy.Engine): Source database.

    Returns:
        pandas.DataFrame: Columns in ``etl.CLEAN_COLUMNS`` order.
    """
    with engine.connect() as conn:
        frame = pd.read_sql(select(paddles).order_by(paddles.c.id), conn)
    frame["year"] = frame["year"].astype("Int64")
    return frame[CLEAN_COLUMNS]
