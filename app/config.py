import json
import os
import sys

APP_NAME = "Rekordbox Now Playing"

POLL_INTERVAL_SECONDS = 1.0
HEARTBEAT_INTERVAL_SECONDS = 15.0
REQUEST_TIMEOUT_SECONDS = 5.0

PAUSE_DEBOUNCE_POLLS = 2

# A same-track elapsed-time change of at most this many seconds is treated
# as normal playback ticking forward. Anything bigger (or backwards) is a
# seek/hot-cue/needle-drop jump, not proof that the deck is playing.
MAX_PLAUSIBLE_TICK_SECONDS = 2

# The API endpoint and auth token used to be hardcoded here, which only
# worked for a single, shared deployment. Now every DJ gets their own token
# from their dashboard, delivered as a config.json placed next to this exe
# (the dashboard's "Download companion app" button zips the two together) --
# so this exe never needs rebuilding per DJ, only when the app itself
# changes. The hardcoded values below are dev-mode fallbacks only, used when
# no config.json is present (e.g. running from source without one).
_DEFAULT_API_URL = "https://songrequester.netlify.app/api/report-now-playing"
_DEFAULT_API_TOKEN = ""


def _app_dir():
    """Directory to look for config.json in: next to the exe when frozen by
    PyInstaller (sys.executable still points at the original exe path even
    in --onefile mode, not the temp extraction dir), or the repo root when
    running from source for local development."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_overrides():
    path = os.path.join(_app_dir(), "config.json")
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


_overrides = _load_overrides()
API_URL = _overrides.get("apiUrl") or _DEFAULT_API_URL
API_TOKEN = _overrides.get("token") or _DEFAULT_API_TOKEN
CONFIGURED = bool(API_TOKEN)
