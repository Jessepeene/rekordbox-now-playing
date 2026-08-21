"""A brief centered popup shown on startup so it's obvious the app is
running without having to go find the tray icon. Blocks the calling thread
for the duration of the animation, then returns."""
import tkinter as tk

from . import config

_WIDTH, _HEIGHT = 380, 120
_FADE_STEP = 0.08
_FADE_DELAY_MS = 15
_HOLD_MS = 1800


def show():
    root = tk.Tk()
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    try:
        root.attributes("-alpha", 0.0)
    except Exception:
        pass

    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()
    x = (screen_w - _WIDTH) // 2
    y = (screen_h - _HEIGHT) // 2
    root.geometry(f"{_WIDTH}x{_HEIGHT}+{x}+{y}")

    bg = "#1b1d1f"
    accent = "#2ecc71"

    border = tk.Frame(root, bg=accent)
    border.place(x=0, y=0, relwidth=1, relheight=1)
    frame = tk.Frame(border, bg=bg)
    frame.place(x=2, y=2, width=_WIDTH - 4, height=_HEIGHT - 4)

    tk.Label(
        frame, text=config.APP_NAME, fg="white", bg=bg, font=("Segoe UI", 13, "bold")
    ).pack(pady=(24, 6))
    tk.Label(
        frame,
        text="Running in the background - watching Rekordbox for track changes.",
        fg="#aab0b6",
        bg=bg,
        font=("Segoe UI", 9),
        wraplength=_WIDTH - 40,
        justify="center",
    ).pack()

    def fade(alpha, step, on_done):
        alpha = max(0.0, min(1.0, alpha + step))
        try:
            root.attributes("-alpha", alpha)
        except Exception:
            on_done()
            return
        if (step > 0 and alpha < 1.0) or (step < 0 and alpha > 0.0):
            root.after(_FADE_DELAY_MS, lambda: fade(alpha, step, on_done))
        else:
            on_done()

    def fade_out():
        fade(1.0, -_FADE_STEP, root.destroy)

    def fade_in():
        fade(0.0, _FADE_STEP, lambda: root.after(_HOLD_MS, fade_out))

    root.after(10, fade_in)
    root.mainloop()
