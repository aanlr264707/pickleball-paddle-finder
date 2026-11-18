"""Ready-made play-style profiles.

Each preset is pure data, so adding a play style means adding one ``Preset`` entry.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from .config import Level
from .models import MetricStats, Preference, Preset
from .scoring import resolve_target

PRESETS = (
    Preset("Power banger", "high power, high pop, high swing weight",
           {"power": (Level.HIGH, 5), "pop": (Level.HIGH, 4), "swing_weight": (Level.HIGH, 3)}),
    Preset("Control / dinker", "low power, high twist weight, thick core",
           {"power": (Level.LOW, 4), "twist_weight": (Level.HIGH, 4), "core": (16, 3)}),
    Preset("Spin player", "high spin, medium power",
           {"spin": (Level.HIGH, 5), "power": (Level.MEDIUM, 2)}),
    Preset("Arm-friendly", "low swing weight, high twist weight, thick core",
           {"swing_weight": (Level.LOW, 5), "twist_weight": (Level.HIGH, 4), "core": (16, 3)}),
    Preset("Fast hands", "low swing weight, high pop",
           {"swing_weight": (Level.LOW, 5), "pop": (Level.HIGH, 4)}),
)

PRESETS_BY_SLUG: Dict[str, Preset] = {preset.slug: preset for preset in PRESETS}


def find_preset(slug: str) -> Optional[Preset]:
    """Look up a preset by its slug.

    Args:
        slug (str): e.g. ``"power-banger"``.

    Returns:
        Preset | None: The preset, or None if no preset has that slug.
    """
    return PRESETS_BY_SLUG.get(slug)


def preset_preferences(preset: Preset, stats: Dict[str, MetricStats]) -> List[Preference]:
    """Turn a preset's levels and numbers into concrete preferences.

    Args:
        preset (Preset): The chosen play style.
        stats (dict[str, MetricStats]): Dataset statistics, used to convert
            levels such as ``Level.HIGH`` into actual values.

    Preconditions:
        Every metric named in ``preset.targets`` has an entry in ``stats``.

    Returns:
        list[Preference]: One preference per metric in the preset.
    """
    assert all(key in stats for key in preset.targets), \
        "preset_preferences: preset '" + preset.name + "' uses a metric with no statistics"
    return [Preference(key, resolve_target(target, stats[key]), importance)
            for key, (target, importance) in preset.targets.items()]
