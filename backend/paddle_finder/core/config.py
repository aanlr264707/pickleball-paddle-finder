"""Constants and metric definitions shared by the whole program.

Every numeric metric is described once, in the ``METRICS`` tuple. The
loader, questionnaire, scorer, display and export code all loop over this
one table instead of repeating a block of code per metric, so adding a new
metric means adding one line here.

Attributes:
    DEFAULT_DATA_FILE (str): The raw CSV in the repository's ``data/`` folder
        (override with the ``PADDLE_DATA_FILE`` environment variable).
    RESULTS_FILE (str): File name the CLI saves recommendations to.
    METRICS (tuple[MetricSpec, ...]): Every numeric metric, in display order.
    METRICS_BY_KEY (dict[str, MetricSpec]): ``METRICS`` indexed by attribute name.
    QUESTIONNAIRE_METRICS (tuple[MetricSpec, ...]): Metrics the questionnaire asks about.
    TEXT_COLUMNS (dict[str, str]): Paddle attribute name -> CSV column for text fields.
    CATEGORY_LABELS (dict[str, str]): Text fields shown in the comparison table.
    VALID_RANGES (dict[str, tuple[float, float]]): Plausible ranges used for data cleaning.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional

# --- Files ---------------------------------------------------------------------

PACKAGE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_DIR = os.path.dirname(os.path.dirname(PACKAGE_DIR))
DEFAULT_DATA_FILE = os.environ.get(
    "PADDLE_DATA_FILE", os.path.join(REPO_DIR, "data", "paddle_database.csv"))
RESULTS_FILE = "recommendations.csv"


# --- Numeric metrics ---------------------------------------------------------------

@dataclass(frozen=True)
class MetricSpec:
    """Describes one numeric metric (immutable).

    Attributes:
        key (str): Attribute name on the ``Paddle`` data class.
        column (str): Header of the matching column in the CSV file.
        label (str): Short human-readable name, e.g. ``"Swing Weight"``.
        unit (str): Unit shown to the user, e.g. ``"oz"``.
        description (str): One-line explanation used in the questionnaire.
    """

    key: str
    column: str
    label: str
    unit: str
    description: str


METRICS = (
    MetricSpec("price", "Price", "Price", "$", "What the paddle costs"),
    MetricSpec("weight", "Weight (oz)", "Weight", "oz", "Static weight of the paddle"),
    MetricSpec("swing_weight", "Swing Weight", "Swing Weight", "units",
               "How heavy it feels when swinging (higher = more power, slower hands)"),
    MetricSpec("twist_weight", "Twist Weight", "Twist Weight", "units",
               "Stability / forgiveness on off-center hits"),
    MetricSpec("power", "Power (MPH)", "Power", "MPH", "Full-swing ball speed"),
    MetricSpec("pop", "Pop (MPH)", "Pop", "MPH", "Short-swing ball speed (volleys, hands battles)"),
    MetricSpec("spin", "Spin (RPM)", "Spin", "RPM", "Measured spin potential"),
    MetricSpec("balance", "Balance Point (mm)", "Balance", "mm", "Higher = more head-heavy"),
    MetricSpec("core", "Core Thickness (mm)", "Core", "mm", "Thicker = softer feel and more control"),
    MetricSpec("grip_length", "Grip Length (in)", "Grip Length", "in",
               "Longer helps two-handed backhands"),
    MetricSpec("grip_size", "Grip Size (in)", "Grip Size", "in", "Handle circumference"),
)

METRICS_BY_KEY: Dict[str, MetricSpec] = {spec.key: spec for spec in METRICS}

# Price is handled by the budget filter, so the questionnaire skips it.
QUESTIONNAIRE_METRICS = tuple(spec for spec in METRICS if spec.key != "price")


# --- Text (categorical) fields ---------------------------------------------------

TEXT_COLUMNS: Dict[str, str] = {
    "brand": "Brand",
    "name": "Paddle Name",
    "link": "Link to Paddle",
    "approval": "Approval Body",
    "shape": "Shape",
    "face": "Face Material",
    "grit": "Grit Type",
    "build": "Build Style",
    "paddle_type": "Paddle Type",
    "feel": "Impact Feel",
    "spin_rating": "Spin Rating",
    "spin_durability": "Spin Durability",
}
YEAR_COLUMN = "Year Released"

CATEGORY_LABELS: Dict[str, str] = {
    "shape": "Shape",
    "paddle_type": "Type",
    "feel": "Feel",
    "approval": "Approval",
    "spin_durability": "Spin Durability",
}


# --- Data cleaning -------------------------------------------------------------------

# Values outside these ranges are data-entry errors and are stored as None.
# (One row lists a 5.75 in grip *size*, which is really a grip length.)
VALID_RANGES = {"grip_size": (3.5, 5.0)}


# --- Target levels ------------------------------------------------------------------

class Level(Enum):
    """A target a user can type instead of a number.

    Each member's value is the dataset percentile it stands for.

    Attributes:
        LOW: The 20th percentile of a metric.
        MEDIUM: The 50th percentile (median) of a metric.
        HIGH: The 80th percentile of a metric.
    """

    LOW = 20
    MEDIUM = 50
    HIGH = 80

    @classmethod
    def from_word(cls, word: str) -> Optional["Level"]:
        """Look up a level from what the user typed.

        Args:
            word (str): The user's answer, e.g. ``"high"``, ``"h"`` or ``"Med"``.

        Returns:
            Level | None: The matching level, or None if ``word`` is not a level word.
        """
        return LEVEL_WORDS.get(word.strip().lower())


LEVEL_WORDS: Dict[str, Level] = {
    "low": Level.LOW, "l": Level.LOW,
    "medium": Level.MEDIUM, "med": Level.MEDIUM, "m": Level.MEDIUM,
    "high": Level.HIGH, "h": Level.HIGH,
}


# --- Scoring and interface constants -------------------------------------------------

STAT_PERCENTILES = (10, 20, 50, 80, 90)   # percentiles pre-computed for every metric
SPREAD_LOW, SPREAD_HIGH = 10, 90          # similarity is measured against this spread
MISSING_SIMILARITY = 0.5                  # neutral score when a paddle lacks a measurement
DEFAULT_IMPORTANCE = 3
MIN_IMPORTANCE, MAX_IMPORTANCE = 1, 5
TOP_N = 10
MAX_SEARCH_RESULTS = 15
MIN_COMPARE, MAX_COMPARE = 2, 3
TOURNAMENT_APPROVAL = "USAP"

# --- Web API ----------------------------------------------------------------------------

MAX_RESULTS = 50                 # most recommendations one request may ask for
API_MAX_COMPARE = 4              # the web compare view has room for four columns
DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE = 24, 100
SIMILAR_LIMIT = 6

# Metrics that describe how a paddle plays; used to find "similar" paddles.
SIMILARITY_METRICS = ("weight", "swing_weight", "twist_weight", "balance",
                      "power", "pop", "spin", "core")

# Paddle types from most control-oriented to most power-oriented.
PADDLE_TYPE_ORDER = ("Control", "Control +", "All-Court", "All-Court +", "Power", "Power +")
