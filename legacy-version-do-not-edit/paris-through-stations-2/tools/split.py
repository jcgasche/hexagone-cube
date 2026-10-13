# Splits a tall screenshot into parts that can be read one by one. Usage: python3 tools/split.py shot.png [height]. Needs Pillow.
import sys
from PIL import Image
fn, h = sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 1500
im = Image.open(fn); W, H = im.size; n = 0
for y in range(0, H, h):
    n += 1; im.crop((0, y, W, min(H, y + h))).save(fn.replace('.png', f'_{n}.png'))
print(fn, W, H, n, 'parts')
