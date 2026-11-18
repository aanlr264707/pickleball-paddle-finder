"""Every question the program asks the user.

All input handling lives here, so no other module calls ``input()``. The
higher-level prompts are built from a few small helpers (``ask``,
``prompt_number``, ``prompt_numbered_choice``) instead of repeating the
same parsing code in each question.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence

from ..core.config import (
    DEFAULT_IMPORTANCE,
    MAX_IMPORTANCE,
    MAX_SEARCH_RESULTS,
    MIN_IMPORTANCE,
    QUESTIONNAIRE_METRICS,
    MetricSpec,
)
from ..core.filters import search_by_name
from ..core.models import Filters, MetricStats, Paddle, Preference
from ..core.scoring import resolve_target
from .display import format_number

# --- Building blocks -------------------------------------------------------------

def ask(prompt: str) -> str:
    """Show a prompt and read one line.

    Args:
        prompt (str): Text shown before the cursor.

    Returns:
        str: The user's answer with surrounding whitespace removed.
    """
    return input(prompt).strip()


def prompt_number(prompt: str) -> Optional[float]:
    """Ask for a number; ``$`` signs and commas are ignored.

    Args:
        prompt (str): Text shown before the cursor.

    Returns:
        float | None: The number, or None for a blank or invalid answer.
    """
    answer = ask(prompt).replace("$", "").replace(",", "")
    try:
        return float(answer) if answer else None
    except ValueError:
        return None


def prompt_yes_no(prompt: str) -> bool:
    """Ask a yes/no question.

    Args:
        prompt (str): Text shown before the cursor.

    Returns:
        bool: True if the answer starts with "y" (case-insensitive).
    """
    return ask(prompt).lower().startswith("y")


def prompt_numbered_choice(prompt: str, count: int) -> Optional[int]:
    """Ask the user to pick an item by its number.

    Args:
        prompt (str): Text shown before the cursor.
        count (int): How many numbered items were shown (valid answers are 1..count).

    Preconditions:
        ``count`` is at least 1 (there is something to choose).

    Returns:
        int | None: The zero-based index chosen, or None for a blank/invalid answer.
    """
    assert count >= 1, "prompt_numbered_choice: count must be at least 1, got " + str(count)
    answer = ask(prompt)
    if answer.isdigit() and 1 <= int(answer) <= count:
        return int(answer) - 1
    return None


def prompt_option(question: str, options: Sequence[str]) -> Optional[str]:
    """Show a numbered list with a ``0. Any`` choice and read the selection.

    Args:
        question (str): Heading printed above the list.
        options (Sequence[str]): The choices to number from 1.

    Preconditions:
        ``options`` is not empty.

    Returns:
        str | None: The chosen option, or None for "Any" or an invalid answer.
    """
    assert len(options) > 0, "prompt_option: options must not be empty"
    print()
    print(question)
    print("  0. Any")
    for number, option in enumerate(options, start=1):
        print("  " + str(number) + ". " + option)
    index = prompt_numbered_choice("  Choose a number: ", len(options))
    return None if index is None else options[index]


# --- Questionnaire ------------------------------------------------------------------

def prompt_budget() -> Optional[float]:
    """Ask for the most the user will spend.

    Returns:
        float | None: The budget in dollars, or None for no limit.
    """
    return prompt_number("Max budget in dollars (Enter for no limit): ")


def prompt_importance() -> int:
    """Ask how much a metric matters.

    Returns:
        int: A value from ``MIN_IMPORTANCE`` to ``MAX_IMPORTANCE``;
        ``DEFAULT_IMPORTANCE`` for a blank or invalid answer.
    """
    answer = ask("  How important is this? (" + str(MIN_IMPORTANCE) + "-"
                 + str(MAX_IMPORTANCE) + ", default " + str(DEFAULT_IMPORTANCE) + "): ")
    if answer.isdigit() and MIN_IMPORTANCE <= int(answer) <= MAX_IMPORTANCE:
        return int(answer)
    return DEFAULT_IMPORTANCE


def prompt_metric_preference(spec: MetricSpec, stats: MetricStats) -> Optional[Preference]:
    """Ask for one metric's target and importance.

    Args:
        spec (MetricSpec): The metric being asked about.
        stats (MetricStats): Its dataset statistics (shown as a range and
            used to convert low / medium / high into values).

    Returns:
        Preference | None: The answer, or None if the user skipped the metric
        or typed something that isn't a level or a number.
    """
    print()
    print(spec.label + " (" + spec.unit + ") - " + spec.description)
    print("  range " + format_number(stats.minimum) + " - " + format_number(stats.maximum)
          + ", typical " + format_number(stats.median))
    answer = ask("  Target? low / medium / high / a number / Enter to skip: ")
    if not answer:
        return None
    target = resolve_target(answer, stats)
    if target is None:
        print("  Didn't understand that, skipping " + spec.label + ".")
        return None
    return Preference(spec.key, target, prompt_importance())


def prompt_preferences(stats: Dict[str, MetricStats]) -> List[Preference]:
    """Ask about every questionnaire metric in turn.

    Args:
        stats (dict[str, MetricStats]): Dataset statistics per metric.

    Returns:
        list[Preference]: Preferences for the metrics the user answered.
    """
    preferences = []
    for spec in QUESTIONNAIRE_METRICS:
        if spec.key in stats:
            preference = prompt_metric_preference(spec, stats[spec.key])
            if preference is not None:
                preferences.append(preference)
    return preferences


def prompt_filters(options: Dict[str, Sequence[str]]) -> Filters:
    """Ask for the hard requirements.

    Args:
        options (dict[str, Sequence[str]]): Text field -> distinct values to
            offer (needs ``"shape"``, ``"paddle_type"`` and ``"feel"``).

    Returns:
        Filters: Budget, tournament approval, shape, type and feel requirements.
    """
    return Filters(
        max_price=prompt_budget(),
        tournament_only=prompt_yes_no(
            "Do you need a USA Pickleball (USAP) approved paddle for tournaments? (y/n): "),
        shape=prompt_option("Preferred shape?", options["shape"]),
        paddle_type=prompt_option("Preferred paddle type?", options["paddle_type"]),
        feel=prompt_option("Preferred impact feel?", options["feel"]),
    )


# --- Picking a paddle by name ------------------------------------------------------

def prompt_pick_paddle(paddles: Sequence[Paddle], prompt: str) -> Optional[Paddle]:
    """Search by name and let the user pick one paddle from the matches.

    Args:
        paddles (Sequence[Paddle]): Paddles to search.
        prompt (str): Text shown before the cursor.

    Returns:
        Paddle | None: The chosen paddle, or None if the search was blank,
        found nothing, or the choice was invalid.
    """
    text = ask(prompt)
    if not text:
        return None
    found = search_by_name(paddles, text)
    if not found:
        print("  No match for '" + text + "'")
        return None
    if len(found) == 1:
        return found[0]
    shown = found[:MAX_SEARCH_RESULTS]
    for number, paddle in enumerate(shown, start=1):
        print("  " + str(number) + ". " + paddle.full_name)
    index = prompt_numbered_choice("  Which one? ", len(shown))
    if index is None:
        print("  Invalid choice.")
        return None
    return shown[index]
