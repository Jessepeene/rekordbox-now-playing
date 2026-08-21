from PIL import Image, ImageDraw

_SIZE = 64

_COLORS = {
    "playing": (46, 204, 113),  # green
    "idle": (149, 165, 166),  # gray - rekordbox open, nothing playing
    "waiting": (241, 196, 15),  # amber - broadcasting paused by user
    "error": (231, 76, 60),  # red - rekordbox not running
}


def _base_icon(color):
    img = Image.new("RGBA", (_SIZE, _SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse((4, 4, _SIZE - 4, _SIZE - 4), fill=color)

    # simple "now playing" bars glyph
    bar_color = (255, 255, 255, 255)
    bars = [(22, 34, 30, 46), (32, 22, 40, 46), (42, 30, 50, 46)]
    for x0, y0, x1, y1 in bars:
        draw.rectangle((x0, y0, x1, y1), fill=bar_color)

    return img


_CACHE = {name: _base_icon(color) for name, color in _COLORS.items()}


def get(state):
    return _CACHE.get(state, _CACHE["idle"])
