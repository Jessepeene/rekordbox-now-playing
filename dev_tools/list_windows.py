import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import uiautomation as auto
import psutil

rb_pids = set()
for p in psutil.process_iter(["pid", "name"]):
    if p.info["name"] and p.info["name"].lower() == "rekordbox.exe":
        rb_pids.add(p.info["pid"])

print("rekordbox.exe pids:", rb_pids)

root = auto.GetRootControl()
for child in root.GetChildren():
    try:
        pid = child.ProcessId
        name = child.Name
        cls = child.ClassName
    except Exception:
        continue
    marker = " <== REKORDBOX" if pid in rb_pids else ""
    print(f"pid={pid} class={cls!r} name={name!r}{marker}")
