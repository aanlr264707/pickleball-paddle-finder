"""Data classes used throughout the program.

Every piece of data has a named, typed, documented shape. Records that
never change after creation are ``frozen`` (immutable).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Optional, Tuple


@dataclass(frozen=True)
class Paddle:
    """One paddle from the database. Numeric fields are None when unmeasured.

    Attributes:
        id (int): Stable identifier (row number in the cleaned dataset, from 1).
        brand (str): Manufacturer, e.g. ``"JOOLA"``.
        name (str): Model name, e.g. ``"Perseus Pro V (16mm)"``.
        link (str): Product link.
        year (int | None): Year released.
        approval (str): Approval body, e.g. ``"USAP"`` or ``"UPA-A"``.
        shape (str): ``"Elongated"``, ``"Hybrid"``, ``"Widebody"``...
        face (str): Face material.
        grit (str): Grit type.
        build (str): Build style / generation.
        paddle_type (str): ``"Power"``, ``"All-Court"``, ``"Control"``...
        feel (str): Impact feel, e.g. ``"Soft/Dense"``.
        spin_rating (str): ``"Low"`` to ``"Very High"``.
        spin_durability (str): ``"Tier 1"`` to ``"Tier 4"``.
        price (float | None): Price in dollars.
        weight (float | None): Weight in ounces.
        swing_weight (float | None): Swing weight.
        twist_weight (float | None): Twist weight.
        balance (float | None): Balance point in mm.
        spin (float | None): Spin in RPM.
        power (float | None): Full-swing ball speed in MPH.
        pop (float | None): Short-swing ball speed in MPH.
        core (float | None): Core thickness in mm.
        grip_length (float | None): Grip length in inches.
        grip_size (float | None): Grip circumference in inches.
    """

    id: int
    brand: str
    name: str
    link: str = ""
    year: Optional[int] = None
    approval: str = ""
    shape: str = ""
    face: str = ""
    grit: str = ""
    build: str = ""
    paddle_type: str = ""
    feel: str = ""
    spin_rating: str = ""
    spin_durability: str = ""
    price: Optional[float] = None
    weight: Optional[float] = None
    swing_weight: Optional[float] = None
    twist_weight: Optional[float] = None
    balance: Optional[float] = None
    spin: Optional[float] = None
    power: Optional[float] = None
    pop: Optional[float] = None
    core: Optional[float] = None
    grip_length: Optional[float] = None
    grip_size: Optional[float] = None

    @property
    def full_name(self) -> str:
        """str: Brand and model together, e.g. ``"JOOLA Perseus"``."""
        return self.brand + " " + self.name

    def value(self, key: str):
        """Return a field by its attribute name.

        Lets generic code loop over ``METRICS`` instead of naming each field.

        Args:
            key (str): Attribute name such as ``"swing_weight"`` or ``"shape"``.

        Returns:
            float | int | str | None: The value of that field.
        """
        return getattr(self, key)


@dataclass(frozen=True)
class MetricStats:
    """Summary statistics for one numeric metric across the whole dataset.

    Attributes:
        minimum (float): Smallest value.
        maximum (float): Largest value.
        average (float): Mean value.
        count (int): Number of paddles that have this measurement.
        percentiles (dict[int, float]): Percentile -> value, e.g. ``{50: 114.0}``.
        sorted_values (tuple[float, ...]): Every value, ascending (used for percentile ranks).
    """

    minimum: float
    maximum: float
    average: float
    count: int
    percentiles: Dict[int, float]
    sorted_values: Tuple[float, ...]

    @property
    def median(self) -> float:
        """float: The 50th percentile."""
        return self.percentiles[50]


@dataclass(frozen=True)
class Preference:
    """What the user wants for one metric and how much it matters.

    Attributes:
        metric_key (str): Which metric, e.g. ``"weight"``.
        target (float): The ideal value.
        importance (int): Weight in the overall score, 1 (low) to 5 (high).
    """

    metric_key: str
    target: float
    importance: int


@dataclass(frozen=True)
class Filters:
    """Hard requirements; a paddle failing any of them is excluded.

    A field left as None (or False) means "no requirement".

    Attributes:
        max_price (float | None): Highest price the user will pay.
        tournament_only (bool): Require USA Pickleball (USAP) approval.
        shape (str | None): Required shape.
        paddle_type (str | None): Required paddle type.
        feel (str | None): Required impact feel.
    """

    max_price: Optional[float] = None
    tournament_only: bool = False
    shape: Optional[str] = None
    paddle_type: Optional[str] = None
    feel: Optional[str] = None


@dataclass(frozen=True)
class MetricFit:
    """How closely one paddle matched one preference.

    Attributes:
        metric_key (str): Which metric.
        similarity (float): 0.0 (far from target) to 1.0 (exactly on target).
    """

    metric_key: str
    similarity: float


@dataclass(frozen=True)
class ScoredPaddle:
    """A paddle with its overall match score and per-metric fits.

    Attributes:
        paddle (Paddle): The paddle that was scored.
        score (float): Overall match, 0 to 100.
        fits (tuple[MetricFit, ...]): One fit per preference, in question order.
    """

    paddle: Paddle
    score: float
    fits: Tuple[MetricFit, ...]

    @property
    def best_fit(self) -> Optional[str]:
        """str | None: Metric key with the highest similarity (None if no preferences)."""
        return self._ranked_fit_keys()[-1] if self.fits else None

    @property
    def worst_fit(self) -> Optional[str]:
        """str | None: Metric key with the lowest similarity (None if no preferences)."""
        return self._ranked_fit_keys()[0] if self.fits else None

    def _ranked_fit_keys(self) -> list:
        """Order this paddle's metric keys from worst to best fit.

        Sorts the fits with a custom key: similarity first, then metric key
        alphabetically to break ties.

        Returns:
            list[str]: Metric keys, lowest similarity first.
        """
        ordered = sorted(self.fits, key=lambda fit: (fit.similarity, fit.metric_key))
        return [fit.metric_key for fit in ordered]


@dataclass(frozen=True)
class Preset:
    """A ready-made play style.

    Attributes:
        name (str): Display name, e.g. ``"Power banger"``.
        description (str): One-line summary shown in the menu.
        targets (dict[str, tuple[Level | float, int]]): Metric key ->
            (target level or exact number, importance).
    """

    name: str
    description: str
    targets: Dict[str, Tuple[object, int]]

    @property
    def slug(self) -> str:
        """str: URL-friendly id, e.g. ``"Control / dinker"`` -> ``"control-dinker"``."""
        return re.sub(r"[^a-z0-9]+", "-", self.name.lower()).strip("-")
