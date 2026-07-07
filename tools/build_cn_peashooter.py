#!/usr/bin/env python3
"""Build CN Peashooter from Chinese assembled sprite frames.
Usage: python3 build_cn_peashooter.py /path/to/Assembled\ Sprites\ (Chinese)/
"""
import sys, glob, os, math, json, shutil
import numpy as np
from PIL import Image

if len(sys.argv) < 2:
    print(f"Usage: {sys.argv[0]} <path_to_cn_frames_folder>")
    sys.exit(1)

frame_dir = sys.argv[1]
names = sorted(glob.glob(os.path.join(frame_dir, '*.png')))
frame_map = {}
for n in names:
    num = int(os.path.basename(n).split('_')[-1].replace('.png', ''))
    frame_map[num] = Image.open(n).convert('RGBA')

def f(idx):
    if idx in frame_map: return frame_map[idx]
    nearest = min(frame_map.keys(), key=lambda x: abs(x - idx))
    return frame_map[nearest]

COLS, ROWS = 8, 9
W, H = 1536, 1872
SW, SH = W // COLS, H // ROWS

def crop_to_content(sprite):
    a = np.array(sprite)
    alpha_ch = a[:,:,3] if a.shape[-1] >= 4 else np.ones(a.shape[:2])*255
    ys, xs = np.where(alpha_ch > 10)
    if len(xs) == 0: return sprite
    m = 4
    return sprite.crop((max(0,xs.min()-m), max(0,ys.min()-m),
                        min(sprite.width,xs.max()+m+1), min(sprite.height,ys.max()+m+1)))

def center(col, row):
    return (col*SW + SW//2, row*SH + SH//2)

def place(cv, sprite, col, row, dx=0, dy=0, flip=False, scale=1.0, alpha=1.0):
    sprite = crop_to_content(sprite)
    cx, cy = center(col, row)
    if flip: sprite = sprite.transpose(Image.FLIP_LEFT_RIGHT)
    if scale != 1.0:
        sprite = sprite.resize((int(sprite.width*scale), int(sprite.height*scale)), Image.LANCZOS)
    if alpha < 1.0:
        a = np.array(sprite, dtype=np.float32); a[:,:,3] *= alpha
        sprite = Image.fromarray(a.astype(np.uint8))
    sw, sh = sprite.size
    cv.paste(sprite, (int(cx-sw/2+dx), int(cy-sh/2+dy)), sprite)

def fill(cv, row, items):
    for col, (s, p) in enumerate(items):
        if col >= COLS: break
        place(cv, s, col, row, **p)
    if items and len(items) < COLS:
        ls, lp = items[-1]
        for col in range(len(items), COLS):
            place(cv, ls, col, row, **lp)

cv = Image.new('RGBA', (W, H), (0,0,0,0))

# Row 0: idle
idle_nums = [95, 96, 97, 98, 99, 100]
idle = [(f(n), {'dy': int(-2*math.sin(i/5*2*math.pi))}) for i,n in enumerate(idle_nums)]
fill(cv, 0, idle)

# Row 1: running-right
for i, n in enumerate([105,106,107,108,109,110,111,112]):
    place(cv, f(n), i, 1, dx=int(10*math.sin(i/7*math.pi)),
          dy=int(-12*abs(math.sin(i/3.5*math.pi))))

# Row 2: running-left
for i, n in enumerate([105,106,107,108,109,110,111,112]):
    place(cv, f(n), i, 2, dx=int(-10*math.sin(i/7*math.pi)),
          dy=int(-12*abs(math.sin(i/3.5*math.pi))), flip=True)

# Row 3: waving
for i, n in enumerate([68,69,70,71]):
    place(cv, f(n), i, 3, dy=int(-4*math.sin(i/3*2*math.pi)))

# Row 4: jumping
jump = [(f(77),5,0.90), (f(78),-28,1.08), (f(79),-36,1.10), (f(80),-18,1.04), (f(81),8,0.85)]
for col, (sprite, dy, scale) in enumerate(jump):
    place(cv, sprite, col, 4, dy=dy, scale=scale)

# Row 5: failed
for col in range(8):
    t = col / 7
    place(cv, f(82+col), col, 5, dy=int(t*26), alpha=max(0.25, 1.0-t*0.75))

# Row 6: waiting
for i, n in enumerate([88,89,90,91,92,93]):
    place(cv, f(n), i, 6, dx=int(4*math.sin(i/5*2*math.pi)),
          dy=int(-3*math.sin(i/5*math.pi)))

# Row 7: running
for i, n in enumerate([113,114,115,116,117,118]):
    place(cv, f(n), i, 7, dx=int(6*math.sin(i/5*math.pi)),
          dy=int(-8*abs(math.sin(i/2.5*math.pi))))

# Row 8: review
for i, n in enumerate([102,103,104,105,106,107]):
    place(cv, f(n), i, 8, dy=int(-2*math.sin(i/5*math.pi)))

cv.save('spritesheet.webp', 'WEBP', quality=92)
pet = {"id":"cn-peashooter","displayName":"Peashooter CN","description":"Chinese-edition Peashooter — 57-frame set with explosive shooting animations!","spritesheetPath":"spritesheet.webp"}
with open('pet.json','w') as f: json.dump(pet, f, indent=2)
print('✅ Built cn-peashooter/')
