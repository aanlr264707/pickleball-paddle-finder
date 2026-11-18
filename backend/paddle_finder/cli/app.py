"""The interactive menu.

``PaddleFinderApp`` owns a ``PaddleCatalog`` and has one short method per
menu option. Each method only coordinates: questions come from
``user_input``, the math from ``filters`` / ``scoring``, the output from
``display`` and ``export``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence

from ..core import filters, presets, scoring
from ..core.catalog import PaddleCatalog
from ..core.config import MAX_COMPARE, MAX_SEARCH_RESULTS, MIN_COMPARE, RESULTS_FILE, TOP_N
from ..core.models import Filters, Paddle, Preference
from . import display, export, user_input


@dataclass(frozen=True)
class MenuItem:
    """One main-menu entry.

    Attributes:
        label (str): Text shown in the menu.
        method_name (str): Name of the ``PaddleFinderApp`` method to run.
    """

    label: str
    method_name: str


MENU: Dict[str, MenuItem] = {
    "1": MenuItem("Find my paddle (questionnaire)", "find_my_paddle"),
    "2": MenuItem("Quick presets by play style", "use_preset"),
    "3": MenuItem("Look up a paddle", "look_up"),
    "4": MenuItem("Compare paddles side by side", "compare"),
    "5": MenuItem("Dataset summary", "summary"),
}
QUIT_KEYS = frozenset({"6", "q", "quit"})
QUIT_LABEL = "6. Quit"


class PaddleFinderApp:
    """Interactive paddle recommender.

    Attributes:
        database (PaddleCatalog): The loaded paddles, statistics and indexes.
    """

    def __init__(self, database: PaddleCatalog):
        """Create the app around an already-loaded database.

        Args:
            database (PaddleCatalog): The paddle data to work with.
        """
        self.database = database

    # --- Shared workflow -----------------------------------------------------------------

    def recommend(self, paddle_filters: Filters, preferences: Sequence[Preference]) -> None:
        """Filter, rank, print and save recommendations.

        Shared by the questionnaire and the presets (Phase 1 repeated this code in both).

        Args:
            paddle_filters (Filters): Hard requirements.
            preferences (Sequence[Preference]): Targets to score against.
        """
        candidates = filters.filter_paddles(self.database.paddles, paddle_filters)
        if not candidates:
            print("No paddles match those filters. Try loosening budget/shape/type/feel.")
            return
        if not preferences:
            print("You skipped every metric, so results are only filtered, not ranked.")
        print(str(len(candidates)) + " paddles passed your filters. Scoring them...")
        results = scoring.rank_paddles(candidates, preferences, self.database.stats, TOP_N)
        display.print_results(results)
        export.write_recommendations(results, RESULTS_FILE)
        print("Saved these results to " + RESULTS_FILE)

    # --- Menu actions ------------------------------------------------------------------

    def find_my_paddle(self) -> None:
        """Menu 1: run the full questionnaire and recommend paddles."""
        print()
        print("--- Paddle questionnaire --- (press Enter to skip any question)")
        paddle_filters = user_input.prompt_filters(self.database.options)
        preferences = user_input.prompt_preferences(self.database.stats)
        self.recommend(paddle_filters, preferences)

    def use_preset(self) -> None:
        """Menu 2: pick a play-style preset, then a budget, and recommend paddles."""
        print()
        print("Player presets:")
        for number, preset in enumerate(presets.PRESETS, start=1):
            print("  {}. {:<18} - {}".format(number, preset.name, preset.description))
        index = user_input.prompt_numbered_choice("Choose a preset: ", len(presets.PRESETS))
        if index is None:
            print("Invalid choice.")
            return
        preferences = presets.preset_preferences(presets.PRESETS[index], self.database.stats)
        self.recommend(Filters(max_price=user_input.prompt_budget()), preferences)

    def look_up(self) -> None:
        """Menu 3: search by brand or name and show full details."""
        text = user_input.ask("Search for a paddle (brand or name): ")
        found = filters.search_by_name(self.database.paddles, text)
        if not found:
            print("No paddles found.")
            return
        if len(found) > MAX_SEARCH_RESULTS:
            print(str(len(found)) + " matches, showing the first " + str(MAX_SEARCH_RESULTS)
                  + ". Be more specific to narrow it down.")
        display.print_paddles(found[:MAX_SEARCH_RESULTS])

    def compare(self) -> None:
        """Menu 4: choose 2-3 paddles and print them side by side."""
        chosen: List[Paddle] = []
        for number in range(1, MAX_COMPARE + 1):
            optional = number > MIN_COMPARE
            suffix = " (search text, Enter to stop): " if optional else " (search text): "
            paddle = user_input.prompt_pick_paddle(self.database.paddles,
                                                   "Paddle " + str(number) + suffix)
            if paddle is None:
                if optional:
                    break
                return
            chosen.append(paddle)
        display.print_comparison(chosen, self.database.stats)

    def summary(self) -> None:
        """Menu 5: print dataset statistics."""
        display.print_summary(self.database)

    # --- Main loop ----------------------------------------------------------------------

    @staticmethod
    def print_menu() -> None:
        """Print the main menu."""
        print()
        print("===== PICKLEBALL PADDLE FINDER =====")
        for key, item in MENU.items():
            print(key + ". " + item.label)
        print(QUIT_LABEL)

    def run(self) -> None:
        """Show the menu repeatedly and run the chosen action until the user quits."""
        print("Loaded " + str(len(self.database)) + " paddles.")
        while True:
            self.print_menu()
            choice = user_input.ask("Choose an option: ").lower()
            if choice in QUIT_KEYS:
                print("Good luck on the court!")
                return
            if choice in MENU:
                getattr(self, MENU[choice].method_name)()
            else:
                print("Invalid option.")
