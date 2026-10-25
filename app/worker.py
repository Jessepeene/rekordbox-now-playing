import logging
import threading
import time

import comtypes

from . import config
from .api_client import ApiClient
from .scraper import RekordboxScraper, RekordboxNotRunning
from .state import PlaybackState

log = logging.getLogger(__name__)


class Worker:
    """Runs the scrape -> decide -> broadcast loop on a background thread.

    `status` is one of: "unconfigured" (no API URL/token found), "error"
    (Rekordbox not running), "waiting" (broadcasting paused by the user),
    "idle" (Rekordbox open, nothing playing), "playing". `status_text` is a
    human-readable description for the tray menu.
    """

    def __init__(self, api_settings):
        self._scraper = RekordboxScraper()
        self._state = PlaybackState()
        self._stop_event = threading.Event()
        self._api = ApiClient(api_settings) if api_settings else None
        self._enabled = self._api is not None

        self.status = "error"
        self.status_text = "Looking for Rekordbox..." if self.is_configured else self._not_configured_text()
        self._on_status_change = None

    def set_status_change_callback(self, callback):
        self._on_status_change = callback

    def _set_status(self, status, text):
        if status != self.status or text != self.status_text:
            self.status = status
            self.status_text = text
            if self._on_status_change:
                try:
                    self._on_status_change(status, text)
                except Exception:
                    log.exception("status change callback failed")

    @property
    def broadcasting_enabled(self):
        return self._enabled

    @property
    def is_configured(self):
        return self._api is not None

    def set_broadcasting_enabled(self, value):
        self._enabled = value and self.is_configured

    @staticmethod
    def _not_configured_text():
        return f"Not set up - add config.json at {config.config_file_paths()[0]}"

    def stop(self):
        self._stop_event.set()

    def run(self):
        log.info("Worker started")
        comtypes.CoInitialize()
        try:
            while not self._stop_event.is_set():
                cycle_start = time.monotonic()
                try:
                    self._tick()
                except Exception:
                    log.exception("Unhandled error in worker tick")

                elapsed = time.monotonic() - cycle_start
                remaining = config.POLL_INTERVAL_SECONDS - elapsed
                if remaining > 0:
                    self._stop_event.wait(remaining)
        finally:
            comtypes.CoUninitialize()
        log.info("Worker stopped")

    def _tick(self):
        if not self.is_configured:
            self._set_status("unconfigured", self._not_configured_text())
            return

        if not self._enabled:
            self._set_status("waiting", "Broadcasting paused")
            return

        try:
            decks = self._scraper.read_decks()
        except RekordboxNotRunning:
            self._set_status("error", "Rekordbox is not running")
            return

        decision = self._state.evaluate(decks)

        if decision.should_send:
            if decision.is_playing:
                ok = self._api.send_now_playing(decision.title, decision.artist)
                if not ok:
                    log.warning("Failed to report now playing (will retry on next change/heartbeat)")
            else:
                self._api.send_stopped()

        if decision.is_playing:
            title, artist = self._state.current_display()
            label = f"{title} - {artist}" if title else "Playing"
            self._set_status("playing", label)
        else:
            self._set_status("idle", "Rekordbox open, nothing playing")
