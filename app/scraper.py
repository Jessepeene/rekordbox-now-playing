"""
Reads currently-loaded deck info out of a running Rekordbox window using
Microsoft UI Automation.

Rekordbox's UI (JUCE-based) does not expose stable AutomationIds - control
names are just the currently displayed text, and the accessibility tree is
mostly flat. So decks are located positionally: for each deck, Rekordbox
draws [Title, Artist, BPM, Key, ..., RemainingTime, RemainingFrac,
ElapsedTime, ElapsedFrac] as consecutive TextControl elements, in on-screen
left-to-right order (Deck 1 before Deck 2). We anchor on the remaining-time
and elapsed-time text (they have a distinctive "-mm:ss" / "mm:ss" shape) and
read the four text elements immediately preceding them.
"""
import re
import dataclasses

import psutil
import uiautomation as auto

REMAINING_RE = re.compile(r"^-\d{1,2}:\d{2}$")
ELAPSED_RE = re.compile(r"^\d{1,2}:\d{2}$")

_MAX_WALK_DEPTH = 25


@dataclasses.dataclass
class DeckInfo:
    index: int
    title: str
    artist: str
    elapsed: str


class RekordboxNotRunning(Exception):
    pass


def _find_rekordbox_window():
    rb_pids = set()
    for p in psutil.process_iter(["pid", "name"]):
        name = p.info.get("name")
        if name and name.lower() == "rekordbox.exe":
            rb_pids.add(p.info["pid"])

    if not rb_pids:
        return None

    root = auto.GetRootControl()
    for child in root.GetChildren():
        try:
            if child.ProcessId in rb_pids and child.ControlTypeName == "WindowControl":
                return child
        except Exception:
            continue
    return None


def _walk_text_names(control, out, depth=0):
    if depth > _MAX_WALK_DEPTH:
        return
    try:
        if control.ControlTypeName == "TextControl":
            name = control.Name
            if name:
                out.append(name)
        children = control.GetChildren()
    except Exception:
        children = []
    for c in children:
        _walk_text_names(c, out, depth + 1)


def _find_workspace_container(win):
    """The main window has ~15 direct children (menu items, title bar, etc).
    Deck/mixer info lives inside whichever CustomControl child has the most
    descendants - found dynamically so we don't depend on a fixed index."""
    best = None
    best_count = -1
    try:
        top_children = win.GetChildren()
    except Exception:
        return None
    for c in top_children:
        try:
            if c.ControlTypeName != "CustomControl":
                continue
            count = len(c.GetChildren())
        except Exception:
            continue
        if count > best_count:
            best_count = count
            best = c
    return best


def _parse_decks(texts):
    decks = []
    for i, t in enumerate(texts):
        if not REMAINING_RE.match(t) or i < 4:
            continue
        elapsed = None
        for j in range(i + 1, min(i + 4, len(texts))):
            if ELAPSED_RE.match(texts[j]):
                elapsed = texts[j]
                break
        if elapsed is None:
            continue

        title = texts[i - 4]
        artist = texts[i - 3]
        # Sanity check: title/artist shouldn't look like the numeric BPM/key
        # fields next to them - if they do, our positional anchor is wrong
        # (e.g. layout changed) and we should skip this match rather than
        # report garbage.
        if REMAINING_RE.match(title) or ELAPSED_RE.match(title):
            continue

        decks.append(DeckInfo(index=len(decks), title=title, artist=artist, elapsed=elapsed))
    return decks


class RekordboxScraper:
    """Keeps a cached handle to the Rekordbox window and re-finds it if it
    disappears (app closed/restarted)."""

    def __init__(self):
        self._window = None

    def _ensure_window(self):
        if self._window is not None:
            try:
                # Touching a property forces a liveness check of the cached element.
                _ = self._window.ProcessId
                return self._window
            except Exception:
                self._window = None

        self._window = _find_rekordbox_window()
        return self._window

    def is_running(self):
        return self._ensure_window() is not None

    def read_decks(self):
        """Returns a list of DeckInfo, one per deck currently showing a
        loaded track. Raises RekordboxNotRunning if Rekordbox isn't open."""
        win = self._ensure_window()
        if win is None:
            raise RekordboxNotRunning()

        container = _find_workspace_container(win)
        texts = []
        if container is not None:
            _walk_text_names(container, texts)

        decks = _parse_decks(texts)
        if not decks:
            # Layout may differ from what we expect (rare) - fall back to a
            # full-window walk once before giving up for this poll.
            texts = []
            _walk_text_names(win, texts)
            decks = _parse_decks(texts)

        return decks
