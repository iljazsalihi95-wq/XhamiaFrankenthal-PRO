from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

out = Path(__file__).resolve().parent / "assets"
logo = Image.open(out / "mosque_logo.png").convert("RGBA")


def place_logo(image, size, center):
    emblem = logo.copy()
    emblem.thumbnail((size, size), Image.Resampling.LANCZOS)
    point = (center[0] - emblem.width // 2, center[1] - emblem.height // 2)
    image.paste(emblem, point, emblem)


canvas = Image.new("RGBA", (256, 256))
place_logo(canvas, 250, (128, 128))
canvas.save(out / "mosque.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
wizard = Image.new("RGB", (164, 314))
draw = ImageDraw.Draw(wizard)
for y in range(314):
    draw.line((0, y, 163, y), fill=(7, 33 + y // 8, 60 + y // 5))
place_logo(wizard, 126, (82, 108))
draw.line((24, 187, 140, 187), fill="#e7bd62", width=2)
draw.multiline_text((82, 205), "XHAMIA\nFRANKENTHAL PRO", fill="#ffda7c",
                    font=ImageFont.load_default(size=14), anchor="ma", align="center", spacing=6)
wizard.save(out / "wizard.bmp")
small = Image.new("RGB", (55, 55), "#0a3458")
place_logo(small, 53, (27, 27))
small.save(out / "wizard_small.bmp")
