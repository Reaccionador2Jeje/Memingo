from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
BRANDING = ROOT / "branding"
DIST = ROOT / "dist"
DIST.mkdir(exist_ok=True)
SIZES = (16, 32, 48, 64, 128, 256, 512, 1024)

def gradient(size, stops):
    image = Image.new("RGBA", (size, size))
    px = image.load()
    for y in range(size):
        t = y / max(1, size - 1)
        for x in range(size):
            u = x / max(1, size - 1)
            p = min(1.0, max(0.0, (t * 0.65 + u * 0.35)))
            idx = min(len(stops) - 2, int(p * (len(stops) - 1)))
            f = p * (len(stops) - 1) - idx
            a, b = stops[idx], stops[idx + 1]
            px[x, y] = tuple(round(a[c] + (b[c] - a[c]) * f) for c in range(4))
    return image

def app_icon(size=1024):
    base = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(base)
    m = size / 1024
    d.rounded_rectangle((40*m, 40*m, 984*m, 984*m), radius=220*m, fill=(12, 19, 42, 255))
    # Gradient chat-bubble outline, composited through a line mask.
    mask = Image.new("L", (size, size), 0)
    md = ImageDraw.Draw(mask)
    pts = [(260,300),(300,235),(370,205),(690,205),(755,270),(755,590),(690,655),(500,655),(365,770),(365,655),(300,655),(260,610),(260,300)]
    md.line([(int(x*m),int(y*m)) for x,y in pts], fill=255, width=max(8,int(30*m)), joint="curve")
    grad = gradient(size, [(36,225,235,255),(55,145,255,255),(135,90,245,255),(238,90,190,255)])
    base.alpha_composite(Image.composite(grad, Image.new("RGBA",(size,size)), mask))
    d = ImageDraw.Draw(base)
    # Code brackets.
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", int(230*m))
    except OSError:
        font = ImageFont.load_default()
    d.text((320*m,350*m), "</>", font=font, fill=(242,247,255,255), stroke_width=max(1,int(2*m)))
    # Small sparkle.
    cx, cy = 790*m, 190*m
    r1, r2 = 43*m, 12*m
    d.polygon([(cx,cy-r1),(cx+r2,cy-r2),(cx+r1,cy),(cx+r2,cy+r2),(cx,cy+r1),(cx-r2,cy+r2),(cx-r1,cy),(cx-r2,cy-r2)], fill=(255,211,91,255))
    return base

def file_icon(size=1024):
    base = Image.new("RGBA",(size,size),(0,0,0,0))
    d = ImageDraw.Draw(base)
    m=size/1024
    d.rounded_rectangle((180*m,70*m,845*m,950*m),radius=70*m,fill=(242,246,255,255),outline=(190,205,230,255),width=max(2,int(12*m)))
    d.polygon([(650*m,70*m),(845*m,265*m),(650*m,265*m)],fill=(190,210,245,255))
    grad=gradient(size,[(35,205,225,255),(65,130,255,255),(145,85,235,255)])
    mask=Image.new("L",(size,size),0); md=ImageDraw.Draw(mask)
    try: font=ImageFont.truetype("DejaVuSans-Bold.ttf",int(235*m))
    except OSError: font=ImageFont.load_default()
    md.text((240*m,390*m),"</>",font=font,fill=255,stroke_width=max(1,int(2*m)))
    base.alpha_composite(Image.composite(grad,Image.new("RGBA",(size,size)),mask))
    return base

def save_icon(image, stem, iconset):
    png=BRANDING/f"{stem}.png"
    image.save(png)
    iconset.mkdir(parents=True,exist_ok=True)
    for size in (16,32,64,128,256,512):
        image.resize((size,size),Image.Resampling.LANCZOS).save(iconset/f"icon_{size}x{size}.png")
    for size in (16,32,128,256,512):
        image.resize((size*2,size*2),Image.Resampling.LANCZOS).save(iconset/f"icon_{size}x{size}@2x.png")
    image.save(BRANDING/f"{stem}.ico",sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])

save_icon(app_icon(), "memingo", DIST/"memingo.iconset")
save_icon(file_icon(), "memingo-file", DIST/"memingo-file.iconset")
