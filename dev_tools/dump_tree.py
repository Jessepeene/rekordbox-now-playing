"""
Developer-only diagnostic: dumps the Rekordbox UI Automation tree to a text file
so we can find the real AutomationId/Name/ControlType of the deck text elements.

Not shipped to end users.
"""
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import uiautomation as auto
import psutil

OUT_PATH = "dev_tools/tree_dump.txt"


def find_rekordbox_window():
    rb_pids = set()
    for p in psutil.process_iter(["pid", "name"]):
        if p.info["name"] and p.info["name"].lower() == "rekordbox.exe":
            rb_pids.add(p.info["pid"])

    root = auto.GetRootControl()
    for child in root.GetChildren():
        try:
            if child.ProcessId in rb_pids:
                return child
        except Exception:
            continue
    return None


def dump(control, out, depth=0, max_depth=14):
    if depth > max_depth:
        return
    try:
        indent = "  " * depth
        info = (
            f"{indent}[{control.ControlTypeName}] "
            f"Name={control.Name!r} "
            f"AutomationId={control.AutomationId!r} "
            f"ClassName={control.ClassName!r}"
        )
        out.write(info + "\n")
    except Exception as e:
        out.write(f"{'  '*depth}<error reading control: {e}>\n")
        return

    try:
        children = control.GetChildren()
    except Exception:
        children = []
    for child in children:
        dump(child, out, depth + 1, max_depth)


def main():
    win = find_rekordbox_window()
    if win is None:
        print("Could not find a top-level Rekordbox window. Is it running?")
        return

    print(f"Found window: Name={win.Name!r} ClassName={win.ClassName!r}")
    with open(OUT_PATH, "w", encoding="utf-8") as out:
        out.write(f"Window: Name={win.Name!r} ClassName={win.ClassName!r}\n")
        dump(win, out)
    print(f"Tree dumped to {OUT_PATH}")


if __name__ == "__main__":
    main()
