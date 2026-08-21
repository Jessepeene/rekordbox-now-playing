import ctypes
import logging
import sys

from app import config, singleinstance, splash, tray
from app.logging_setup import configure_logging

log = logging.getLogger(__name__)


def _install_crash_logging():
    def excepthook(exc_type, exc_value, exc_tb):
        log.critical("Unhandled exception", exc_info=(exc_type, exc_value, exc_tb))

    sys.excepthook = excepthook


def main():
    configure_logging()
    _install_crash_logging()

    if not singleinstance.acquire():
        ctypes.windll.user32.MessageBoxW(
            0, f"{config.APP_NAME} is already running (check your system tray).", config.APP_NAME, 0x40
        )
        return

    log.info("%s starting", config.APP_NAME)
    try:
        splash.show()
    except Exception:
        log.exception("Failed to show startup splash")

    try:
        tray.run()
    except Exception:
        log.exception("Fatal error")
        raise


if __name__ == "__main__":
    main()
