from pathlib import Path
from PIL import Image

out = Path(__file__).resolve().parent / "assets"
logo = Image.open(out / "mosque_logo.png").convert("RGBA")
canvas = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
logo.thumbnail((240, 240), Image.Resampling.LANCZOS)
canvas.alpha_composite(logo, ((256 - logo.width) // 2, (256 - logo.height) // 2))
canvas.save(out / "mosque.ico", format="ICO", sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
wizard = Image.new("RGB", (164, 314), "#082d55")
logo.thumbnail((146, 146), Image.Resampling.LANCZOS)
wizard.paste(logo, ((164 - logo.width) // 2, (314 - logo.height) // 2), logo)
wizard.save(out / "wizard.bmp")
logo.convert("RGB").resize((55,55), Image.Resampling.LANCZOS).save(out / "wizard_small.bmp")
print("Official mosque logo embedded in installer and desktop executable.")
