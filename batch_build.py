#!/usr/bin/env python3
"""Batch build petdex spritesheets from PvZ2 sprite zips. v2 — fixed fill."""
import zipfile, io, os, math, json, shutil
import numpy as np
from PIL import Image

COLS, ROWS = 8, 9
W, H = 1536, 1872
SW, SH = W // COLS, H // ROWS

def load_frames(zpath):
    with zipfile.ZipFile(zpath, 'r') as z:
        names = sorted([n for n in z.namelist()
                       if 'Assembled Sprites' in n and n.endswith('.png')])
        if not names:
            names = sorted([n for n in z.namelist() if n.endswith('.png')])
        return [Image.open(io.BytesIO(z.read(n))).convert('RGBA') for n in names]

def analyze(frames):
    stats = []; prev = None; diffs = []
    for img in frames:
        arr = np.array(img)
        a = arr[:,:,3] if arr.shape[-1]>=4 else np.ones(arr.shape[:2])*255
        ys, xs = np.where(a > 30)
        if len(xs) > 0:
            stats.append({'w': xs.max()-xs.min(), 'h': ys.max()-ys.min(),
                          'cx': (xs.max()+xs.min())/2, 'cy': (ys.max()+ys.min())/2})
        else:
            stats.append({'w':0,'h':0,'cx':0,'cy':0})
        if prev is not None:
            h = min(arr.shape[0], prev.shape[0]); w2 = min(arr.shape[1], prev.shape[1])
            diffs.append(np.abs(arr[:h,:w2,:3].astype(float)-prev[:h,:w2,:3].astype(float)).mean())
        prev = arr
    diffs = np.array(diffs) if diffs else np.array([0])
    widths = np.array([s['w'] for s in stats])
    thresh = diffs.mean() + diffs.std()*2
    boundaries = [0]
    for i,d in enumerate(diffs):
        if d > thresh: boundaries.append(i+1)
    boundaries.append(len(frames))
    merged = [boundaries[0]]
    for b in boundaries[1:-1]:
        if b - merged[-1] >= 3: merged.append(b)
    merged.append(boundaries[-1])
    segs = [(merged[i], merged[i+1]) for i in range(len(merged)-1) if merged[i+1]-merged[i]>=3]
    valid_w = widths[widths>10]
    return {'total':len(frames), 'widths':widths, 'segs':segs, 'stats':stats,
            'avg_w': widths.mean(), 'max_w': widths.max(),
            'min_w': valid_w.min() if len(valid_w)>0 else 0}

def best_segment(analysis, prefer='avg', min_len=6):
    segs = analysis['segs']; widths = analysis['widths']
    best, best_score = None, -1
    for s,e in segs:
        if e-s < min_len: continue
        ws = widths[s:e]
        if prefer == 'wide':
            score = ws.max()
        elif prefer == 'narrow':
            score = -ws.min()
        else:  # avg — smooth, close to average width
            score = 1.0/(1.0 + abs(ws.mean()-analysis['avg_w'])/max(1,analysis['avg_w']))
            score += min((e-s)/20, 1.0)*0.3
        if score > best_score: best_score = score; best = (s,e)
    if best: return best
    return (0, min(20, analysis['total']))

def crop(sprite):
    a = np.array(sprite)
    alpha = a[:,:,3] if a.shape[-1]>=4 else np.ones(a.shape[:2])*255
    ys,xs = np.where(alpha>10)
    if len(xs)==0: return sprite
    m=4
    cropped = sprite.crop((max(0,xs.min()-m), max(0,ys.min()-m),
                           min(sprite.width,xs.max()+m+1), min(sprite.height,ys.max()+m+1)))
    # If cropped sprite is wider than 188px, scale down to fit slot with margin
    max_w = SW - 8  # 184px = 192 - 8px margin — safe from overflow
    if cropped.width > max_w:
        ratio = max_w / cropped.width
        new_h = int(cropped.height * ratio)
        cropped = cropped.resize((max_w, new_h), Image.LANCZOS)
    return cropped

def center(col, row):
    return (col*SW+SW//2, row*SH+SH//2)

def place(cv, sprite, col, row, dx=0, dy=0, flip=False, scale=1.0, alpha=1.0):
    sprite = crop(sprite); cx, cy = center(col, row)
    if flip: sprite = sprite.transpose(Image.FLIP_LEFT_RIGHT)
    if scale != 1.0: sprite = sprite.resize((int(sprite.width*scale), int(sprite.height*scale)), Image.LANCZOS)
    if alpha < 1.0:
        a = np.array(sprite, dtype=np.float32); a[:,:,3] *= alpha
        sprite = Image.fromarray(a.astype(np.uint8))
    sw, sh = sprite.size
    cv.paste(sprite, (int(cx-sw/2+dx), int(cy-sh/2+dy)), sprite)

def fill_row(cv, row, items):
    for col in range(COLS):
        if col < len(items):
            s, p = items[col]
        elif items:
            s, p = items[-1]
        else:
            return
        place(cv, s, col, row, **p)

def f(frames, idx):
    return frames[idx % len(frames)]

def build_one(zpath, pet_id, name, desc):
    print(f"\n{'='*60}")
    print(f"Building: {name} ({pet_id})")
    frames = load_frames(zpath)
    print(f"  {len(frames)} frames")
    if len(frames) < 10:
        print(f"  ❌ Too few frames"); return False, pet_id

    an = analyze(frames)
    idle_seg = best_segment(an, 'avg', 6)
    shoot_seg = best_segment(an, 'wide', 3)
    tired_seg = best_segment(an, 'narrow', 4)

    # Detect natural facing direction
    right_count = 0
    for i in range(min(5, len(frames))):
        arr = np.array(frames[i])
        a = arr[:,:,3] if arr.shape[-1]>=4 else np.ones(arr.shape[:2])*255
        ys, xs = np.where(a>20)
        if len(xs)>0 and xs.mean() > frames[i].width/2:
            right_count += 1
    faces_right = right_count >= 3  # Natural direction

    print(f"  Idle:{idle_seg[0]+1}-{idle_seg[1]} Shoot:{shoot_seg[0]+1}-{shoot_seg[1]} Tired:{tired_seg[0]+1}-{tired_seg[1]}")
    print(f"  Faces: {'RIGHT' if faces_right else 'LEFT'}")

    cv = Image.new('RGBA', (W,H), (0,0,0,0))
    T = len(frames)
    i0, i1 = idle_seg
    s0, s1 = shoot_seg
    t0, t1 = tired_seg

    # Direction logic:
    # running-right (row 1) should face RIGHT → flip if naturally faces left
    # running-left (row 2) should face LEFT → flip if naturally faces right
    flip_for_right = not faces_right  # flip row 1 if sprite faces left
    flip_for_left = faces_right       # flip row 2 if sprite faces right

    # Row 0: idle
    step = max(1, (i1-i0)//6)
    idle_items = [(f(frames, i0 + i*step),
                   {'dy': int(-2*math.sin(i/5*2*math.pi))}) for i in range(6)]
    fill_row(cv, 0, idle_items)

    # Row 1: running-right (should face RIGHT)
    run_r = []
    for i in range(8):
        idx = i0 + int((i1-i0) * i/7) if i1>i0 else i0
        run_r.append((f(frames, idx),
                      {'dx': int(10*math.sin(i/7*math.pi)),
                       'dy': int(-6*abs(math.sin(i/3.5*math.pi))),
                       'flip': flip_for_right}))
    fill_row(cv, 1, run_r)

    # Row 2: running-left (should face LEFT)
    run_l = [(f(frames, i0 + int((i1-i0)*i/7) if i1>i0 else i0),
              {'dx': int(-10*math.sin(i/7*math.pi)),
               'dy': int(-6*abs(math.sin(i/3.5*math.pi))),
               'flip': flip_for_left}) for i in range(8)]
    fill_row(cv, 2, run_l)

    # Row 3: waving
    wb = i0 + (i1-i0)//3
    wave = [(f(frames, wb+i), {'dy': int(-3*math.sin(i/3*2*math.pi))}) for i in range(4)]
    fill_row(cv, 3, wave)

    # Row 4: jumping
    ss = max(1, (s1-s0)//5) if s1>s0 else 1
    jump_nums = [s0 + i*ss for i in range(5)]
    jump_offsets = [(5,0.88), (-22,1.06), (-32,1.10), (-16,1.04), (8,0.85)]
    jump_items = [(f(frames, jump_nums[i] % T),
                   {'dy': jump_offsets[i][0], 'scale': jump_offsets[i][1]}) for i in range(5)]
    fill_row(cv, 4, jump_items)

    # Row 5: failed
    failed_items = []
    for i in range(8):
        tt = i/7
        idx = t0 + i % max(1, t1-t0)
        failed_items.append((f(frames, idx % T),
                            {'dy': int(tt*26), 'alpha': max(0.25, 1.0-tt*0.75)}))
    fill_row(cv, 5, failed_items)

    # Row 6: waiting
    wb2 = min(i0 + (i1-i0)//2, T-6)
    wait_items = [(f(frames, wb2+i),
                   {'dx': int(4*math.sin(i/5*2*math.pi)),
                    'dy': int(-2*math.sin(i/5*math.pi))}) for i in range(6)]
    fill_row(cv, 6, wait_items)

    # Row 7: running
    rb2 = min(i1, T-6)
    run2 = [(f(frames, rb2+i),
             {'dx': int(6*math.sin(i/5*math.pi)),
              'dy': int(-8*abs(math.sin(i/2.5*math.pi)))}) for i in range(6)]
    fill_row(cv, 7, run2)

    # Row 8: review
    rv = min(T-6, i1 + (T-i1)//2)
    review = [(f(frames, rv+i), {'dy': int(-2*math.sin(i/5*math.pi))}) for i in range(6)]
    fill_row(cv, 8, review)

    # Verify
    arr = np.array(cv)
    ok = True
    for row in range(ROWS):
        for col in range(COLS):
            nz = (arr[row*SH:(row+1)*SH, col*SW:(col+1)*SW, 3] > 10).sum()
            if nz < 50:
                print(f"  ⚠️ [{row},{col}] EMPTY!"); ok = False

    out_dir = f'/Users/xxx/Desktop/petdex/{pet_id}'
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, 'spritesheet.webp')
    cv.save(out_path, 'WEBP', quality=92)

    with open(os.path.join(out_dir, 'pet.json'), 'w') as pf:
        json.dump({"id":pet_id,"displayName":name,"description":desc,"spritesheetPath":"spritesheet.webp"}, pf, indent=2)

    inst = f'/Users/xxx/.petdex/pets/{pet_id}'
    os.makedirs(inst, exist_ok=True)
    shutil.copy(out_path, os.path.join(inst, 'spritesheet.webp'))
    shutil.copy(os.path.join(out_dir, 'pet.json'), os.path.join(inst, 'pet.json'))

    kb = os.path.getsize(out_path)/1024
    print(f"  {'✅' if ok else '⚠️'} {out_path} ({W}×{H}, {kb:.0f} KB)")
    return ok, pet_id


# ═══════════════════════════════════════════════════════════════
DOWNLOADS = '/Users/xxx/Downloads'
PETS = [
    ("A.K.E.E.", "akee", "A.K.E.E.", "A.K.E.E. — bouncing seed-shooter from PvZ2!"),
    ("Cactus", "cactus", "Cactus", "Cactus — spiky desert sniper from PvZ2!"),
    ("Adventurer Zombie", "adventurer-zombie", "Adventurer Zombie", "Adventurer Zombie — exploring your desktop!"),
    ("Cowboy Zombie", "cowboy-zombie", "Cowboy Zombie", "Cowboy Zombie — lassoing across your screen!"),
    ("Explorer Zombie", "explorer-zombie", "Explorer Zombie", "Explorer Zombie — torch-lit wanderer!"),
]

results = []
for pattern, pid, name, desc in PETS:
    matches = [f for f in os.listdir(DOWNLOADS) if pattern in f and f.endswith('.zip') and '.download' not in f]
    if not matches:
        print(f"\n⚠️ No zip for {pattern}"); continue
    try:
        ok, id_ = build_one(os.path.join(DOWNLOADS, matches[0]), pid, name, desc)
        results.append((id_, ok))
    except Exception as e:
        print(f"  ❌ {e}"); import traceback; traceback.print_exc()

print(f"\n{'='*60}")
print("DONE!")
for pid, ok in results:
    print(f"  {'✅' if ok else '⚠️'} {pid}")
if results:
    print(f"\npetdex select {results[0][0]}")
EOF
