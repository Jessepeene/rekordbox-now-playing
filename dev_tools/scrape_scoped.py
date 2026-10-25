import sys, io, time, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import uiautomation as auto
import psutil

REMAINING_RE = re.compile(r"^-\d{1,2}:\d{2}$")
ELAPSED_RE = re.compile(r"^\d{1,2}:\d{2}$")


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


def walk_text_names(control, out, depth=0, max_depth=20):
    if depth > max_depth:
        return
    try:
        if control.ControlTypeName == "TextControl":
            name = control.Name
            if name:
                out.append(name)
        children = control.GetChildren()
    except Exception:
        children = []
    for c in children:
        walk_text_names(c, out, depth + 1, max_depth)


def find_workspace_container(win):
    best = None
    best_count = -1
    for c in win.GetChildren():
        try:
            if c.ControlTypeName != "CustomControl":
                continue
            kids = c.GetChildren()
        except Exception:
            continue
        if len(kids) > best_count:
            best_count = len(kids)
            best = c
    return best


def main():
    win = find_rekordbox_window()
    if win is None:
        print("Rekordbox window not found")
        return

    container = find_workspace_container(win)
    print(f"Chosen container: Name={container.Name!r} children={len(container.GetChildren())}")

    for i in range(5):
        t0 = time.time()
        texts = []
        walk_text_names(container, texts)
        dt = time.time() - t0
        decks = []
        for idx, t in enumerate(texts):
            if not REMAINING_RE.match(t) or idx < 4:
                continue
            elapsed = None
            for j in range(idx + 1, min(idx + 4, len(texts))):
                if ELAPSED_RE.match(texts[j]):
                    elapsed = texts[j]
                    break
            if elapsed:
                decks.append((texts[idx-4], texts[idx-3], t, elapsed))
        print(f"poll {i}: {dt*1000:.0f}ms, {len(texts)} texts, decks={decks}")
        time.sleep(1)


if __name__ == "__main__":
    main()
