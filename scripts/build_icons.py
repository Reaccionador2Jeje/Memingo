from pathlib import Path
import cairosvg
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
BRANDING = ROOT / "branding"
ICONSET = ROOT / "dist" / "memingo.iconset"
FILE_ICONSET = ROOT / "dist" / "memingo-file.iconset"
ICONSET.mkdir(parents=True, exist_ok=True)
FILE_ICONSET.mkdir(parents=True, exist_ok=True)

def render(svg_name, png_name):
    target = BRANDING / png_name
    cairosvg.svg2png(url=str(BRANDING / svg_name), write_to=str(target),
                     output_width=1024, output_height=1024)
    return target

app_png = render("memingo-icon.svg", "memingo.png")
file_png = render("memingo-file.svg", "memingo-file.png")

for size in (16, 32, 48, 64, 128, 256, 512):
    Image.open(app_png).convert("RGBA").resize((size, size), Image.Resampling.LANCZOS).save(
        ICONSET / f"icon_{size}x{size}.png")
for size in (16, 32, 128, 256, 512):
    Image.open(file_png).convert("RGBA").resize((size, size), Image.Resampling.LANCZOS).save(
        FILE_ICONSET / f"icon_{size}x{size}.png")

Image.open(app_png).convert("RGBA").save(BRANDING / "memingo.ico",
    sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
Image.open(file_png).convert("RGBA").save(BRANDING / "memingo-file.ico",
    sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
