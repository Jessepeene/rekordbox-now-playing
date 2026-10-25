import logging

import requests

from . import config

log = logging.getLogger(__name__)


class ApiClient:
    def __init__(self, settings):
        self._url = settings.url
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"Bearer {settings.token}",
                "Content-Type": "application/json",
            }
        )

    def send_now_playing(self, title, artist):
        payload = {"name": title, "artist": artist, "isPlaying": True}
        return self._post(payload)

    def send_stopped(self):
        payload = {"isPlaying": False}
        return self._post(payload)

    def _post(self, payload):
        try:
            response = self._session.post(self._url, json=payload, timeout=config.REQUEST_TIMEOUT_SECONDS)
            if response.status_code >= 400:
                log.warning("Server rejected payload %s: HTTP %s", payload, response.status_code)
                return False
            log.info("Sent %s", payload)
            return True
        except requests.RequestException as e:
            log.warning("Network error sending %s: %s", payload, e)
            return False
