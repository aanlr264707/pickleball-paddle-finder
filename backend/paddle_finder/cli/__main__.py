"""Entry point for the terminal app.

Usage::

    python -m paddle_finder.cli                  # uses data/paddle_database.csv
    python -m paddle_finder.cli path/to/file.csv
"""

import os
import sys

from ..core.config import DEFAULT_DATA_FILE
from ..data.etl import catalog_from_csv
from .app import PaddleFinderApp


def main() -> None:
    """Load the CSV and start the interactive menu."""
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DATA_FILE
    if not os.path.exists(path):
        print("Could not find " + path)
        sys.exit(1)
    PaddleFinderApp(catalog_from_csv(path)).run()


if __name__ == "__main__":
    main()
