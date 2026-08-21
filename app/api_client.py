import logging

import requests

from . import config

log = logging.getLogger(__name__)

_session = requests.Session()
_session.headers.update(
    {
        "Authorization": f"Bearer {config.API_TOKEN}",
        "Content-Type": "application/json",
    }
)


def send_now_playing(title, artist):
    payload = {"name": title, "artist": artist, "isPlaying": True}
    return _post(payload)


def send_stopped():
    payload = {"isPlaying": False}
    return _post(payload)


def _post(payload):
    try:
        response = _session.post(config.API_URL, json=payload, timeout=config.REQUEST_TIMEOUT_SECONDS)
        if response.status_code >= 400:
            log.warning("Server rejected payload %s: HTTP %s", payload, response.status_code)
            return False
        log.info("Sent %s", payload)
        return True
    except requests.RequestException as e:
        log.warning("Network error sending %s: %s", payload, e)
        return False
