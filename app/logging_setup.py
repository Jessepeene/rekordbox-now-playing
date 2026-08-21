import logging
import logging.handlers
import os


def app_data_dir():
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    path = os.path.join(base, "RekordboxNowPlaying")
    os.makedirs(path, exist_ok=True)
    return path


def log_file_path():
    return os.path.join(app_data_dir(), "log.txt")


def configure_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    handler = logging.handlers.RotatingFileHandler(
        log_file_path(), maxBytes=1_000_000, backupCount=2, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(handler)

    logging.getLogger("comtypes").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    return logger
