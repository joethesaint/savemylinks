"""Join the frames from tools/screenshots.mjs into the README GIF (needs Pillow).

    python tools/make_gif.py docs/screenshots/frames docs/screenshots/keyboard.gif
"""
import sys
from pathlib import Path

from PIL import Image

frames_dir, out = Path(sys.argv[1]), Path(sys.argv[2])
WIDTH = 960  # README width; keeps the file small
frames = []
for f in sorted(frames_dir.glob("*.png")):
    im = Image.open(f).convert("RGB")
    im = im.resize((WIDTH, round(im.height * WIDTH / im.width)), Image.LANCZOS)
    frames.append(im.quantize(colors=128, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE))
frames[0].save(out, save_all=True, append_images=frames[1:], duration=450, loop=0, optimize=True, disposal=2)
print(f"{out}: {len(frames)} frames, {out.stat().st_size / 1024:.0f} KB")
