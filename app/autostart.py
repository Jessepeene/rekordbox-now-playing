import os
import subprocess
import sys

from . import config


def _startup_folder():
    appdata = os.environ["APPDATA"]
    return os.path.join(appdata, "Microsoft", "Windows", "Start Menu", "Programs", "Startup")


def _shortcut_path():
    return os.path.join(_startup_folder(), f"{config.APP_NAME}.lnk")


def _target_path():
    if getattr(sys, "frozen", False):
        return sys.executable
    return sys.executable  # dev mode: points at venv's python(w).exe, fine for testing only


def is_enabled():
    return os.path.exists(_shortcut_path())


def enable():
    target = _target_path()
    args = "" if getattr(sys, "frozen", False) else os.path.abspath(sys.argv[0])
    shortcut = _shortcut_path()

    ps_script = (
        "$s = (New-Object -COM WScript.Shell).CreateShortcut('{lnk}'); "
        "$s.TargetPath = '{target}'; "
        "$s.Arguments = '{args}'; "
        "$s.WorkingDirectory = '{workdir}'; "
        "$s.Save()"
    ).format(
        lnk=shortcut.replace("'", "''"),
        target=target.replace("'", "''"),
        args=args.replace("'", "''"),
        workdir=os.path.dirname(target).replace("'", "''"),
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
        check=True,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )


def disable():
    path = _shortcut_path()
    if os.path.exists(path):
        os.remove(path)
