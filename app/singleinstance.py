import ctypes

_ERROR_ALREADY_EXISTS = 183
_handle = None


def acquire(name="Global\\RekordboxNowPlayingBroadcaster"):
    """Returns True if this is the only running instance. The mutex handle
    is kept alive for the process lifetime (module-level) and released
    automatically on exit."""
    global _handle
    _handle = ctypes.windll.kernel32.CreateMutexW(None, False, name)
    last_error = ctypes.windll.kernel32.GetLastError()
    return last_error != _ERROR_ALREADY_EXISTS
