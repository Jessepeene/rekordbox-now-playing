"""
App constants, plus the API endpoint and token loaded at runtime.

The endpoint and token are never stored in source. Each is resolved
independently, first match wins:

1. Environment variables RNP_API_URL / RNP_API_TOKEN
2. config.json next to the exe (or the repo root when running from
   source) - this is how the RequestApp dashboard delivers a per-DJ config
   alongside the downloaded app
3. %APPDATA%\\RekordboxNowPlaying\\config.json

A config file holds {"apiUrl": "...", "token": "..."} (the dashboard's
format); "api_url" / "api_token" are accepted too.
"""
import dataclasses
import json
import logging
import os
import sys

from .logging_setup import app_data_dir

log = logging.getLogger(__name__)

APP_NAME = "Rekordbox Now Playing"

POLL_INTERVAL_SECONDS = 1.0
HEARTBEAT_INTERVAL_SECONDS = 15.0
REQUEST_TIMEOUT_SECONDS = 5.0

PAUSE_DEBOUNCE_POLLS = 2

# A same-track elapsed-time change of at most this many seconds is treated
# as normal playback ticking forward. Anything bigger (or backwards) is a
# seek/hot-cue/needle-drop jump, not proof that the deck is playing.
MAX_PLAUSIBLE_TICK_SECONDS = 2

ENV_API_URL = "RNP_API_URL"
ENV_API_TOKEN = "RNP_API_TOKEN"


@dataclasses.dataclass(frozen=True)
class ApiSettings:
    url: str
    token: str = dataclasses.field(repr=False)


def _app_dir():
    """Next to the exe when frozen by PyInstaller (sys.executable is the
    real exe path, not a temp extraction dir), or the repo root when
    running from source."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def config_file_paths():
    """Config file locations, in order of precedence."""
    return [
        os.path.join(_app_dir(), "config.json"),
        os.path.join(app_data_dir(), "config.json"),
    ]


def _read_config_file(path):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        log.error("Could not read %s: %s", path, e)
        return {}
    if not isinstance(data, dict):
        log.error("Could not read %s: expected a JSON object", path)
        return {}
    return data


def load_api_settings():
    """Returns ApiSettings, or None if the URL or token is missing (the
    reason is logged - never the token itself)."""
    paths = config_file_paths()
    url = os.environ.get(ENV_API_URL)
    token = os.environ.get(ENV_API_TOKEN)
    for path in paths:
        values = _read_config_file(path)
        url = url or values.get("apiUrl") or values.get("api_url")
        token = token or values.get("token") or values.get("api_token")

    missing = [name for name, value in (("API URL", url), ("API token", token)) if not value]
    if missing:
        log.error(
            "Not configured: missing %s. Set %s / %s or create config.json in one of: %s "
            "(see config.example.json). Broadcasting is disabled.",
            " and ".join(missing), ENV_API_URL, ENV_API_TOKEN, ", ".join(paths),
        )
        return None

    return ApiSettings(url=str(url), token=str(token))
