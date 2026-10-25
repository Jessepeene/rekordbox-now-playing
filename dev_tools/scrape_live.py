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


def scrape(win, debug=False):
    texts = []
    walk_text_names(win, texts)
    if debug:
        print("ALL TEXTS:", texts)

    decks = []
    for i, t in enumerate(texts):
        if not REMAINING_RE.match(t) or i < 4:
            continue
        elapsed = None
        for j in range(i + 1, min(i + 4, len(texts))):
            if ELAPSED_RE.match(texts[j]):
                elapsed = texts[j]
                break
        if elapsed is None:
            continue
        decks.append({
            "title": texts[i - 4],
            "artist": texts[i - 3],
            "bpm": texts[i - 2],
            "key": texts[i - 1],
            "remaining": t,
            "elapsed": elapsed,
        })
    return decks


def main():
    win = find_rekordbox_window()
    if win is None:
        print("Rekordbox window not found")
        return

    for i in range(6):
        t0 = time.time()
        decks = scrape(win, debug=(i == 0))
        dt = time.time() - t0
        print(f"--- poll {i} (scrape took {dt*1000:.0f}ms) ---")
        for d in decks:
            print(d)
        time.sleep(1)


if __name__ == "__main__":
    main()
