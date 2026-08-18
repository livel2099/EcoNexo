from PIL import Image, ImageDraw
from pathlib import Path
src = Path(r"tmp\docx\word-screens-foreground")
out = Path(r"tmp\docx\contact-sheets")
out.mkdir(parents=True, exist_ok=True)
files = sorted(src.glob("page-*.png"))
for gi in range(0, len(files), 4):
    group = files[gi:gi+4]
    sheet = Image.new("RGB", (640, 820), "#dfe8e5")
    draw = ImageDraw.Draw(sheet)
    for j, path in enumerate(group):
        im = Image.open(path).convert("RGB").crop((610, 175, 1295, 1045))
        im.thumbnail((300, 380))
        x = 10 + (j % 2) * 315
        y = 25 + (j // 2) * 395
        sheet.paste(im, (x, y))
        draw.text((x, 7 + (j // 2) * 395), path.stem, fill="#164E63")
    sheet.save(out / f"sheet-{gi//4+1:02d}.jpg", quality=72, optimize=True)
print(f"SHEETS={len(list(out.glob('sheet-*.jpg')))} PAGES={len(files)}")