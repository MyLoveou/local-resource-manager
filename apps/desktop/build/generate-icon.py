"""Generate app icon: rounded gradient square + white media folder + play triangle.

用法：apps/backend/.venv/Scripts/python apps/desktop/build/generate-icon.py
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

SIZE = 1024
OUT = Path(__file__).resolve().parent

# 对角渐变
top_left = (91, 108, 255)
bottom_right = (20, 200, 176)
gradient = Image.new("RGB", (SIZE, SIZE))
pixels = gradient.load()
for y in range(SIZE):
    for x in range(SIZE):
        t = (x + y) / (2 * (SIZE - 1))
        pixels[x, y] = tuple(
            round(top_left[i] + (bottom_right[i] - top_left[i]) * t) for i in range(3)
        )

# 圆角遮罩
mask = Image.new("L", (SIZE, SIZE), 0)
ImageDraw.Draw(mask).rounded_rectangle((0, 0, SIZE, SIZE), radius=228, fill=255)
icon = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
icon.paste(gradient, (0, 0), mask)

# 文件夹投影
shadow = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
sd = ImageDraw.Draw(shadow)
sd.rounded_rectangle((250, 400, 794, 772), radius=64, fill=(10, 20, 40, 90))
sd.rounded_rectangle((258, 300, 572, 452), radius=44, fill=(10, 20, 40, 90))
shadow = shadow.filter(ImageFilter.GaussianBlur(18))
icon.alpha_composite(shadow, (0, 12))

draw = ImageDraw.Draw(icon)
white = (255, 255, 255, 255)
draw.rounded_rectangle((250, 296, 566, 452), radius=46, fill=white)
draw.rounded_rectangle((250, 384, 774, 748), radius=58, fill=white)

triangle = [(458, 466), (458, 666), (642, 566)]
draw.polygon(triangle, fill=(35, 48, 88, 255))

icon.resize((512, 512), Image.LANCZOS).save(OUT / "icon.png")
icon.save(
    OUT / "icon.ico",
    sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
)
print("generated", OUT / "icon.ico", OUT / "icon.png")
