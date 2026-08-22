import logging
import os
import threading

import pystray
from pystray import MenuItem

from . import autostart, config, icons, logging_setup
from .worker import Worker

log = logging.getLogger(__name__)


def _open_log(icon, item):
    try:
        os.startfile(logging_setup.log_file_path())
    except Exception:
        log.exception("Failed to open log file")


def _toggle_autostart(icon, item):
    try:
        if autostart.is_enabled():
            autostart.disable()
        else:
            autostart.enable()
    except Exception:
        log.exception("Failed to toggle autostart")


def _toggle_broadcasting(worker):
    def handler(icon, item):
        worker.set_broadcasting_enabled(not worker.broadcasting_enabled)

    return handler


def run():
    worker = Worker()

    status_item = MenuItem(lambda item: worker.status_text, None, enabled=False)
    broadcasting_item = MenuItem(
        "Broadcasting enabled",
        _toggle_broadcasting(worker),
        checked=lambda item: worker.broadcasting_enabled,
    )
    autostart_item = MenuItem(
        "Start with Windows",
        _toggle_autostart,
        checked=lambda item: autostart.is_enabled(),
    )
    log_item = MenuItem("View log", _open_log)
    exit_item = MenuItem("Exit", lambda icon, item: _shutdown(icon, worker))

    menu = pystray.Menu(status_item, broadcasting_item, autostart_item, log_item, exit_item)
    icon = pystray.Icon(config.APP_NAME, icons.get("error"), config.APP_NAME, menu)

    def on_status_change(status, text):
        icon.icon = icons.get(status)
        icon.title = f"{config.APP_NAME}\n{text}"

    worker.set_status_change_callback(on_status_change)

    def setup(icon):
        icon.visible = True
        # A brief confirmation that it's running, without a separate GUI
        # toolkit: an animated Tkinter splash used to serve this role, but a
        # native Tcl/Tk crash during its fade animation can't be caught by a
        # Python try/except and silently kills the whole process before the
        # tray icon ever appears -- exactly this notify() call replaces it,
        # using the tray icon's own (already-proven-working) backend instead.
        try:
            icon.notify(f"{config.APP_NAME} is running in your system tray.", config.APP_NAME)
        except Exception:
            log.exception("Failed to show startup notification")
        threading.Thread(target=worker.run, daemon=True).start()

    icon.run(setup=setup)


def _shutdown(icon, worker):
    worker.stop()
    icon.stop()
