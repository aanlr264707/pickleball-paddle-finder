"""Command line: clean the CSV with pandas and load it into the database.

Usage::

    python -m paddle_finder.data.seed                 # uses $DATABASE_URL
    python -m paddle_finder.data.seed --if-empty      # skip when data exists
    python -m paddle_finder.data.seed --csv other.csv --database-url sqlite:///x.db
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Optional, Sequence

from ..core.config import DEFAULT_DATA_FILE
from .etl import load_clean_frame
from .schema import count_paddles, create_schema, make_engine, seed

DEFAULT_SQLITE = "sqlite:///instance/paddles.db"


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Parse arguments and seed the database.

    Args:
        argv (Sequence[str] | None): Arguments (defaults to ``sys.argv[1:]``).

    Returns:
        int: Process exit code (0 on success).
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--csv", default=DEFAULT_DATA_FILE, help="CSV file to load")
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL", DEFAULT_SQLITE))
    parser.add_argument("--if-empty", action="store_true", help="only seed an empty table")
    args = parser.parse_args(argv)

    if args.database_url.startswith("sqlite:///") and not args.database_url.startswith("sqlite:////"):
        os.makedirs(os.path.dirname(args.database_url[len("sqlite:///"):]) or ".", exist_ok=True)
    engine = make_engine(args.database_url)
    create_schema(engine)
    if args.if_empty and count_paddles(engine) > 0:
        print("paddles table already has data; skipping seed")
        return 0
    written = seed(engine, load_clean_frame(args.csv))
    print("Loaded " + str(written) + " paddles into " + engine.dialect.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
