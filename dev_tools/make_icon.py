"""Generates the .ico used for the built exe / taskbar."""
from PIL import Image, ImageDraw

SIZE = 256


def build():
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    pad = 8
    draw.ellipse((pad, pad, SIZE - pad, SIZE - pad), fill=(46, 204, 113, 255))

    bar_color = (255, 255, 255, 255)
    cx, cy = SIZE / 2, SIZE / 2
    bars = [(-36, -46, -14, 46), (-11, -70, 11, 46), (14, -30, 36, 46)]
    for dx0, dy0, dx1, dy1 in bars:
        draw.rounded_rectangle(
            (cx + dx0, cy + dy0, cx + dx1, cy + dy1), radius=8, fill=bar_color
        )

    img.save("app_icon.ico", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("wrote app_icon.ico")


if __name__ == "__main__":
    build()
