import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import uiautomation as auto
import psutil

rb_pids = set()
for p in psutil.process_iter(["pid", "name"]):
    if p.info["name"] and p.info["name"].lower() == "rekordbox.exe":
        rb_pids.add(p.info["pid"])

root = auto.GetRootControl()
for child in root.GetChildren():
    try:
        pid = child.ProcessId
    except Exception:
        continue
    if pid in rb_pids:
        rect = child.BoundingRectangle
        kids = child.GetChildren()
        print(f"Window Name={child.Name!r} Class={child.ClassName!r} Rect={rect} NumChildren={len(kids)}")
        for k in kids:
            print(f"   child: [{k.ControlTypeName}] Name={k.Name!r} NumGrandchildren={len(k.GetChildren())}")
