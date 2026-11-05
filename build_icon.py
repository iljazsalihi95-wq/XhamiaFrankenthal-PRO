"""Build Windows icons from the mosque's existing official logo URL."""
from pathlib import Path
from urllib.request import urlopen
from io import BytesIO
from PIL import Image

URL = "https://archive.org/download/20260126-152726-0000/20260126_152726_0000.png"
out = Path("assets")
out.mkdir(exist_ok=True)
with urlopen(URL, timeout=25) as response:
    raw = response.read(5_000_000)
logo = Image.open(BytesIO(raw)).convert("RGBA")
logo.save(out / "mosque_logo.png")
canvas = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
logo.thumbnail((240, 240), Image.Resampling.LANCZOS)
canvas.alpha_composite(logo, ((256 - logo.width) // 2, (256 - logo.height) // 2))
canvas.save(out / "mosque.ico", format="ICO", sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
print("Official mosque logo embedded in installer and desktop executable.")
