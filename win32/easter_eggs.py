"""Easter eggs utilities.

Used to add lightweight, non-intrusive fun moments.

Current implementation is intentionally simple so it doesn't depend on extra packages.
"""

from __future__ import annotations

import datetime
import random


_EASTER_EGG_LINES = [
    "Psst… drag text like it’s magnetized. 🧲",
    "Word-like editor detected. Calibrating pixels… 🖨️",
    "May your PDFs be aligned and your margins forgiving. 📏",
    "Easter egg engaged. Somewhere, a pixel smiles. 😄",
    "Ctrl+Z is your time machine. Use wisely. ⏪",
    "If this were Word, the ribbon would be judging you. 🎛️",
    "Remember: drag to move, handles to resize. (Like magic, but real) ✨",
]


def pick_easter_egg(now: datetime.datetime | None = None) -> str:
    now = now or datetime.datetime.now()

    # Deterministic-ish on date so it feels 'special'
    day_seed = now.toordinal()
    rng = random.Random(day_seed)

    # Make Fridays a bit more sparkly
    if now.weekday() == 4:  # Friday
        return "Friday magic! " + rng.choice(_EASTER_EGG_LINES)

    return rng.choice(_EASTER_EGG_LINES)


def should_show_easter_egg(action_counter: int) -> bool:
    """Return True occasionally to avoid annoying the user."""
    if action_counter <= 0:
        return False
    # Show after some actions, with diminishing frequency.
    return action_counter in {3, 8, 15, 24, 35}

