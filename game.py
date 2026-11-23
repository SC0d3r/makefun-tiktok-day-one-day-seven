"""Frog Run: a tiny agent-built pond game, rendered frame by frame with PIL.

Day 1 shows the quiet first build. Day 7 shows the same pond and the same
starting frame after a week of daily updates. Everything is deterministic.
"""

import math
import os
import random
import subprocess
import sys
import time

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

W, H = 1080, 1920
FPS = 30
DURATION = 16.5
NFRAMES = int(round(DURATION * FPS))

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(HERE, "fonts")
INTER = os.path.join(FONT_DIR, "Inter-Bold.ttf")
MONO = os.path.join(FONT_DIR, "JetBrainsMono-Bold.ttf")

F_WORD = ImageFont.truetype(INTER, 40)
F_SCORE = ImageFont.truetype(MONO, 38)
F_HUD = ImageFont.truetype(MONO, 28)
F_COMBO = ImageFont.truetype(INTER, 32)
F_HINT = ImageFont.truetype(INTER, 36)
F_POP = ImageFont.truetype(INTER, 44)
F_TINY = ImageFont.truetype(MONO, 22)

MINT = (128, 231, 196)
WHITE = (245, 252, 248)
INK = (8, 20, 18)
PINK = (255, 143, 168)

PAD_POSITIONS = [
    (540, 1180, 150),
    (250, 980, 115),
    (820, 880, 105),
    (920, 1120, 120),
    (380, 1390, 100),
    (680, 1470, 95),
]
EXTRA_PADS = [
    (430, 780, 95),
    (770, 940, 96),
    (540, 1310, 102),
    (250, 1360, 90),
]


def clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, v))


def lerp(a, b, u):
    return a + (b - a) * u


def mix(c1, c2, u):
    return tuple(int(round(lerp(c1[i], c2[i], u))) for i in range(3))


def ease_out(u):
    u = clamp(u)
    return 1.0 - (1.0 - u) ** 3


def ease_in_out(u):
    u = clamp(u)
    return u * u * (3.0 - 2.0 * u)


def rounded_rect(d, box, r, fill):
    x0, y0, x1, y1 = box
    d.rectangle((x0 + r, y0, x1 - r, y1), fill=fill)
    d.rectangle((x0, y0 + r, x1, y1 - r), fill=fill)
    d.ellipse((x0, y0, x0 + 2 * r, y0 + 2 * r), fill=fill)
    d.ellipse((x1 - 2 * r, y0, x1, y0 + 2 * r), fill=fill)
    d.ellipse((x0, y1 - 2 * r, x0 + 2 * r, y1), fill=fill)
    d.ellipse((x1 - 2 * r, y1 - 2 * r, x1, y1), fill=fill)


def draw_text_center(d, x, y, text, font, fill, stroke_width=0, stroke_fill=None):
    w, h = font.getsize(text)
    d.text((x - w / 2.0, y - h / 2.0), text, font=font, fill=fill,
           stroke_width=stroke_width, stroke_fill=stroke_fill)


def draw_text_right(d, x_right, y, text, font, fill, stroke_width=0, stroke_fill=None):
    w, h = font.getsize(text)
    d.text((x_right - w, y), text, font=font, fill=fill,
           stroke_width=stroke_width, stroke_fill=stroke_fill)


def make_pad(radius, seed):
    rng = random.Random(seed)
    pad = Image.new("RGBA", (radius * 2 + 48, int(radius * 1.5) + 48), (0, 0, 0, 0))
    d = ImageDraw.Draw(pad)
    cx = pad.width // 2
    cy = pad.height // 2
    hh = radius * 1.12
    outer = (cx - radius, cy - hh / 2, cx + radius, cy + hh / 2)
    d.ellipse(outer, fill=(24, 78, 52, 255))
    inset = 9
    inner = (outer[0] + inset, outer[1] + inset, outer[2] - inset, outer[3] - inset)
    d.ellipse(inner, fill=(44, 126, 76, 255))

    # Pac-man notch, cut clean through the pad.
    notch = [
        (cx + 6, cy + 4),
        (cx + radius * 1.05, cy - hh * 0.72),
        (cx + radius * 0.42, cy - hh * 0.60),
    ]
    d.polygon(notch, fill=(0, 0, 0, 0))

    for k in range(7):
        ang = math.radians(200 + k * 19 + rng.uniform(-4, 4))
        ex = cx + math.cos(ang) * radius * 0.86
        ey = cy + math.sin(ang) * hh * 0.42
        d.line((cx, cy, ex, ey), fill=(28, 98, 58, 120), width=2)

    d.arc((outer[0] + 22, outer[1] + 18, outer[2] - 22, outer[3] - 18),
          196, 318, fill=(144, 204, 132, 150), width=4)
    d.ellipse((cx - 5, cy - 5, cx + 5, cy + 5), fill=(26, 88, 54, 190))
    return pad


def draw_reeds(d, rng):
    for side in (-1, 1):
        for k in range(8):
            if side < 0:
                x = 34 + rng.randint(-8, 52)
            else:
                x = W - 34 - rng.randint(-8, 52)
            base = 1770 + rng.randint(-50, 70)
            top = 1120 + rng.randint(-160, 260)
            bend = rng.randint(-46, 46)
            pts = []
            for i in range(9):
                u = i / 8.0
                px = x + bend * math.sin(u * math.pi) + 14 * math.sin(u * 7 + k)
                py = lerp(base, top, u)
                pts.append((px, py))
            d.line(pts, fill=(22, 70, 48), width=7, joint="curve")
            if k % 3 == 0:
                tipx, tipy = pts[-1]
                d.ellipse((tipx - 13, tipy - 34, tipx + 13, tipy + 30),
                          fill=(94, 62, 38))
                d.line((tipx, tipy - 34, tipx, tipy - 52),
                       fill=(22, 70, 48), width=4)
            leaf_u = 0.55 + rng.uniform(-0.1, 0.25)
            lx, ly = pts[int(leaf_u * 8)]
            direction = side * -1
            leaf = [
                (lx, ly),
                (lx + direction * 42, ly - 38),
                (lx + direction * 68, ly - 16),
                (lx + direction * 30, ly + 10),
            ]
            d.polygon(leaf, fill=(34, 96, 58))


def build_background(extra_pads=False):
    rng = random.Random(20261123)
    img = Image.new("RGB", (W, H), (2, 8, 10))
    d = ImageDraw.Draw(img)

    top_col = (8, 62, 70)
    bot_col = (2, 7, 10)
    for y in range(H):
        u = (y / (H - 1.0)) ** 0.82
        d.line((0, y, W, y), fill=mix(top_col, bot_col, u))

    # Soft radial pond glow.
    glow = Image.new("L", (W, H), 0)
    gd = ImageDraw.Draw(glow)
    gd.ellipse((120, 650, 960, 1500), fill=84)
    gd.ellipse((300, 800, 790, 1320), fill=110)
    glow = glow.filter(ImageFilter.GaussianBlur(130))
    glow = glow.point(lambda v: int(v * 0.62))
    tint = Image.new("RGB", (W, H), (40, 162, 142))
    img.paste(tint, (0, 0), glow)

    # Faint horizontal caustics.
    caus = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    cd = ImageDraw.Draw(caus)
    for row in range(120, 1470, 52):
        pts = []
        phase = rng.uniform(0, 6.28)
        amp = rng.uniform(3, 10)
        for x in range(-20, W + 40, 36):
            pts.append((x, row + amp * math.sin(x / 95.0 + phase)))
        alpha = rng.randint(7, 18)
        cd.line(pts, fill=(118, 226, 204, alpha), width=2)
        if rng.random() < 0.55:
            seg = pts[rng.randint(2, 20): rng.randint(22, 28)]
            if len(seg) > 1:
                cd.line(seg, fill=(172, 248, 224, 26), width=3)
    img = Image.alpha_composite(img.convert("RGBA"), caus).convert("RGB")
    d = ImageDraw.Draw(img)

    draw_reeds(d, rng)

    # Brown log, top left.
    log = [(26, 306), (356, 278), (424, 330), (404, 382), (60, 412), (18, 362)]
    d.polygon(log, fill=(38, 24, 16))
    d.polygon([(34, 316), (354, 290), (398, 330), (382, 366), (66, 394), (32, 352)],
              fill=(104, 64, 38))
    d.line((58, 330, 360, 307), fill=(146, 96, 58), width=8)
    d.ellipse((378, 290, 442, 370), fill=(128, 80, 46))
    d.ellipse((390, 300, 432, 360), fill=(88, 54, 32))
    d.ellipse((398, 311, 425, 349), fill=(122, 76, 44))
    d.ellipse((405, 321, 419, 339), fill=(70, 44, 28))
    for k in range(4):
        d.ellipse((72 + k * 62, 330 + (k % 2) * 12, 104 + k * 62, 348 + (k % 2) * 12),
                  fill=(70, 104, 52, 255))

    # Grey rock, bottom right.
    d.ellipse((772, 1738, 1080, 1876), fill=(2, 10, 12))
    rock = [(808, 1832), (838, 1700), (910, 1628), (1002, 1646),
            (1060, 1726), (1038, 1832), (926, 1862)]
    d.polygon(rock, fill=(78, 86, 92))
    d.polygon([(844, 1740), (912, 1660), (966, 1680), (930, 1782)], fill=(112, 121, 126))
    d.polygon([(928, 1790), (1004, 1690), (1038, 1742), (1002, 1822)], fill=(62, 70, 76))
    d.polygon([(852, 1808), (902, 1760), (930, 1810), (902, 1838)], fill=(140, 148, 152))
    d.line((920, 1668, 946, 1642), fill=(88, 126, 78), width=6)

    pads = list(PAD_POSITIONS)
    if extra_pads:
        pads += list(EXTRA_PADS)
    for idx, (x, y, r) in enumerate(pads):
        pad = make_pad(r, 7000 + idx)
        img.paste(pad, (x - pad.width // 2, y - pad.height // 2), pad)

    return img


# ---------------------------------------------------------------------------
# Frog and critters


def make_frog_sprite(look_x=0.0, look_y=0.0):
    s = 2
    sw, sh = 200 * s, 178 * s
    im = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)

    def E(box, fill, outline=None):
        box = tuple(v * s for v in box)
        if outline is not None:
            d.ellipse((box[0] - 4, box[1] - 4, box[2] + 4, box[3] + 4), fill=outline)
        d.ellipse(box, fill=fill)

    dark = (34, 104, 58, 255)
    green = (96, 198, 98, 255)
    light = (150, 226, 132, 255)

    E((10, 116, 60, 160), dark)
    E((140, 116, 190, 160), dark)
    E((8, 90, 40, 120), dark)
    E((160, 90, 192, 120), dark)
    E((26, 54, 174, 158), green, dark)
    E((52, 86, 148, 158), light)
    E((56, 28, 86, 62), green, dark)
    E((114, 28, 144, 62), green, dark)

    px = look_x * 4.5
    py = look_y * 4.5
    E((60, 34, 82, 56), (250, 255, 250, 255))
    E((118, 34, 140, 56), (250, 255, 250, 255))
    d.ellipse((66 * s + px, 40 * s + py, 76 * s + px, 50 * s + py), fill=(18, 34, 30, 255))
    d.ellipse((122 * s + px, 40 * s + py, 132 * s + px, 50 * s + py), fill=(18, 34, 30, 255))
    d.ellipse((68 * s + px, 42 * s + py, 72 * s + px, 46 * s + py), fill=(255, 255, 255, 220))
    d.ellipse((124 * s + px, 42 * s + py, 128 * s + px, 46 * s + py), fill=(255, 255, 255, 220))

    d.arc((70 * s, 94 * s, 130 * s, 136 * s), 16, 164, fill=(28, 82, 46, 230), width=4 * s)
    d.ellipse((78 * s, 82 * s, 84 * s, 88 * s), fill=(34, 100, 56, 180))
    d.ellipse((116 * s, 82 * s, 122 * s, 88 * s), fill=(34, 100, 56, 180))
    d.ellipse((44 * s, 96 * s, 62 * s, 106 * s), fill=(255, 146, 166, 110))
    d.ellipse((138 * s, 96 * s, 156 * s, 106 * s), fill=(255, 146, 166, 110))

    for toe in range(3):
        d.line((14 * s + toe * 12 * s, 148 * s, 8 * s + toe * 13 * s, 160 * s),
               fill=(26, 84, 46, 255), width=3 * s)
        d.line((148 * s + toe * 12 * s, 148 * s, 154 * s + toe * 13 * s, 160 * s),
               fill=(26, 84, 46, 255), width=3 * s)

    return im.resize((200, 178), Image.LANCZOS)


def draw_frog(layer, x, y, t, squash=0.0, look_x=0.0, look_y=0.0):
    d = ImageDraw.Draw(layer)
    breathe = 1.0 + 0.02 * math.sin(t * 2 * math.pi * 0.65)
    sx = breathe * (1.0 + 0.16 * squash)
    sy = breathe * (1.0 - 0.13 * squash)
    shadow_w = 128 * breathe
    d.ellipse((x - shadow_w / 2, y + 52, x + shadow_w / 2, y + 88),
              fill=(0, 0, 0, 92))
    sprite = make_frog_sprite(look_x, look_y)
    dw = max(2, int(round(200 * sx)))
    dh = max(2, int(round(178 * sy)))
    sprite = sprite.resize((dw, dh), Image.LANCZOS)
    layer.paste(sprite, (int(round(x - dw / 2)), int(round(y - 100 * sy))), sprite)


def draw_fly(layer, x, y, t, firefly=False, scale=1.0):
    d = ImageDraw.Draw(layer)
    if firefly:
        for r, a in ((17, 26), (11, 44), (6, 90)):
            d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 236, 120, a))
        d.ellipse((x - 4, y - 4, x + 4, y + 4), fill=(255, 250, 196, 255))
        d.line((x - 2, y + 4, x - 5, y + 10), fill=(180, 240, 120, 160), width=2)
        return
    wf = 0.6 + 0.4 * math.sin(t * 28 + x * 0.1)
    d.ellipse((x - 12 * scale, y - 7 * scale, x - 3 * scale, y + 7 * scale),
              fill=(246, 250, 240, 170))
    d.ellipse((x + 3 * scale, y - 7 * scale, x + 12 * scale, y + 7 * scale),
              fill=(246, 250, 240, 170))
    d.ellipse((x - 6 * scale, y - 4 * scale, x + 6 * scale, y + 5 * scale),
              fill=(32, 40, 42, 255))
    d.ellipse((x - 6 * scale, y - 9 * scale, x - 1 * scale, y - 3 * scale),
              fill=(58, 66, 68, 255))
    d.ellipse((x + 1 * scale, y - 9 * scale, x + 6 * scale, y - 3 * scale),
              fill=(226, 82, 82, 230))
    d.line((x - 5 * scale, y - 45 * wf * scale, x - 13 * scale, y - 2 * scale),
           fill=(255, 255, 255, 120), width=1)
    d.line((x + 5 * scale, y - 45 * wf * scale, x + 13 * scale, y - 2 * scale),
           fill=(255, 255, 255, 120), width=1)


def draw_dragonfly(layer, x, y, t, direction):
    d = ImageDraw.Draw(layer)
    flap = 0.55 + 0.45 * abs(math.sin(t * 19))
    body = (24, 64, 82, 235)
    d.line((x - direction * 30, y + 8, x + direction * 18, y - 8),
           fill=body, width=7)
    d.ellipse((x + direction * 14, y - 16, x + direction * 34, y - 2),
              fill=(38, 92, 110, 255))
    d.ellipse((x + direction * 22, y - 19, x + direction * 28, y - 13),
              fill=(230, 255, 250, 255))
    for side in (-1, 1):
        wx = 22 * flap
        wy = side * 14
        d.polygon([
            (x + 2 * direction, y - 4),
            (x + wx * direction, y - 4 + wy),
            (x + 2 * direction, y + 8),
        ], fill=(190, 240, 244, 120))
        d.polygon([
            (x - 12 * direction, y - 2),
            (x - 28 * direction, y - 6 + wy),
            (x - 8 * direction, y + 8),
        ], fill=(190, 240, 244, 100))


def draw_ripple(layer, x, y, age, life, max_r, alpha=120):
    if age < 0 or age > life:
        return
    d = ImageDraw.Draw(layer)
    u = age / life
    r = 12 + (max_r - 12) * ease_out(u)
    a = int(alpha * (1.0 - u))
    d.ellipse((x - r, y - r * 0.42, x + r, y + r * 0.42),
              outline=(196, 255, 234, a), width=3)
    if r > 42:
        r2 = r * 0.72
        d.ellipse((x - r2, y - r2 * 0.4, x + r2, y + r2 * 0.4),
                  outline=(160, 240, 214, max(0, a - 35)), width=2)


def draw_heart(d, cx, cy, size, fill):
    r = size * 0.3
    d.ellipse((cx - size * 0.5, cy - size * 0.38, cx - size * 0.5 + 2 * r,
               cy - size * 0.38 + 2 * r), fill=fill)
    d.ellipse((cx + size * 0.5 - 2 * r, cy - size * 0.38, cx + size * 0.5,
               cy - size * 0.38 + 2 * r), fill=fill)
    d.polygon([(cx - size * 0.48, cy - size * 0.1),
               (cx + size * 0.48, cy - size * 0.1),
               (cx, cy + size * 0.55)], fill=fill)


# ---------------------------------------------------------------------------
# HUD


def draw_top_bar(d, score, day):
    d.ellipse((44, 62, 76, 82), fill=(52, 140, 82, 255))
    d.polygon([(60, 74), (76, 64), (73, 78)], fill=(20, 60, 42, 0))
    d.text((88, 52), "FROG RUN", font=F_WORD, fill=WHITE,
           stroke_width=2, stroke_fill=(6, 18, 16, 200))
    text = "SCORE %04d" % score if day == 7 else "SCORE %03d" % score
    draw_text_right(d, W - 46, 56, text, F_SCORE, MINT,
                    stroke_width=2, stroke_fill=(6, 18, 16, 200))


def draw_day7_hud(d, combo, score):
    d.text((56, 132), "WAVE 7", font=F_HUD, fill=MINT)
    d.text((250, 128), "COMBO x%d" % combo, font=F_COMBO, fill=WHITE)
    for i in range(3):
        draw_heart(d, 908 + i * 54, 160, 38, (255, 110, 140, 245))
    d.text((56, 186), "WAVE PROGRESS", font=F_TINY, fill=(180, 226, 212, 210))
    draw_text_right(d, W - 46, 186, "70%", F_TINY, MINT)
    rounded_rect(d, (56, 216, W - 46, 230), 7, (8, 32, 30, 190))
    rounded_rect(d, (56, 216, 56 + int((W - 102) * 0.70), 230), 7, MINT)


def draw_hint(d, text):
    draw_text_center(d, W / 2, 1808, text, F_HINT, (232, 250, 240, 210),
                     stroke_width=2, stroke_fill=(4, 14, 12, 180))


# ---------------------------------------------------------------------------
# Day 1


def render_day1(t, bg):
    frame = bg.copy().convert("RGBA")
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)

    draw_ripple(layer, 540, 1188, t - 0.55, 1.5, 230, 88)

    fly_x, fly_y = 676.0, 1112.0 + 10 * math.sin(t * 2.6)
    caught = t >= 2.2
    if not caught:
        draw_fly(layer, fly_x, fly_y, t, False, 1.15)

    look_x = clamp((fly_x - 540) / 220.0, -1, 1) if not caught else 0
    look_y = clamp((fly_y - 1130) / 200.0, -1, 1) if not caught else 0
    draw_frog(layer, 540, 1180, t, 0.0, look_x, look_y)

    if caught:
        age = t - 2.2
        if age < 0.26:
            tip = ease_out(age / 0.26)
            mx, my = 540, 1182
            tx = lerp(mx, fly_x, tip)
            ty = lerp(my, fly_y, tip)
            d.line((mx, my, tx, ty), fill=(255, 118, 146, 245), width=10)
            d.ellipse((tx - 9, ty - 9, tx + 9, ty + 9), fill=(255, 146, 168, 255))
        if age < 1.0:
            u = age / 1.0
            draw_text_center(d, fly_x, fly_y - 20 - 70 * u, "+10", F_POP,
                             (255, 246, 156, int(255 * (1 - u))),
                             stroke_width=3, stroke_fill=(10, 30, 24, int(220 * (1 - u))))
            for k in range(7):
                ang = k * 0.9 + 0.3
                pr = 10 + 46 * ease_out(u)
                px = fly_x + math.cos(ang) * pr
                py = fly_y + math.sin(ang) * pr
                d.ellipse((px - 3, py - 3, px + 3, py + 3),
                          fill=(255, 236, 142, int(230 * (1 - u))))

    score = 10 if caught else 0
    draw_top_bar(d, score, 1)
    draw_hint(d, "one fly. one frog.")

    frame = Image.alpha_composite(frame, layer)
    return frame.convert("RGB")


# ---------------------------------------------------------------------------
# Day 7


PATH = [(540, 1180), (300, 1000), (760, 940), (840, 1200), (540, 1300), (250, 1350)]
HOP_START = [4.05, 4.60, 5.30, 6.00, 6.70]
HOP_END = [4.60, 5.30, 6.00, 6.70, 7.40]
CATCH_TIMES = [4.60, 4.75, 5.30, 5.45, 6.00, 6.15, 6.70, 6.85, 7.40, 7.55, 8.10, 8.80]
FLY_ANCHORS = [
    (676, 1086), (436, 1102), (612, 1002), (778, 1008),
    (356, 940), (712, 884), (902, 1034), (508, 1236),
    (706, 1252), (844, 1126), (326, 1194), (618, 1352),
    (944, 902), (196, 1084),
]
FIREFLIES = {3, 5, 8, 11, 12, 13}


def fly_pos(index, t):
    ax, ay = FLY_ANCHORS[index]
    ph = index * 1.71
    x = ax + 27 * math.sin(t * 1.25 + ph)
    y = ay + 17 * math.sin(t * 1.8 + ph * 1.3)
    return x, y


def frog_state(t):
    if t <= HOP_START[0]:
        return PATH[0][0], PATH[0][1], 0.0, 0.0
    for i in range(5):
        if HOP_START[i] <= t <= HOP_END[i]:
            u = (t - HOP_START[i]) / (HOP_END[i] - HOP_START[i])
            x0, y0 = PATH[i]
            x1, y1 = PATH[i + 1]
            x = lerp(x0, x1, ease_in_out(u))
            y = lerp(y0, y1, ease_in_out(u)) - 148 * math.sin(math.pi * u)
            squash = 0.0
            if u > 0.82:
                squash = math.sin((u - 0.82) / 0.18 * math.pi) * 0.8
            if u < 0.14:
                squash = math.sin((0.14 - u) / 0.14 * math.pi) * 0.35
            return x, y, squash, 1.0 if x1 >= x0 else -1.0
    x, y = PATH[-1]
    bounce = 0.0
    for te in HOP_END:
        age = t - te
        if 0 <= age < 0.3:
            bounce = max(bounce, math.sin(age / 0.3 * math.pi) * 0.45)
    return x, y, bounce, -1.0


def render_day7(t, bg):
    frame = bg.copy().convert("RGBA")
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)

    for idx in range(5):
        draw_ripple(layer, PATH[idx][0], PATH[idx][1] + 10,
                    t - HOP_END[idx], 1.4, 250, 100)
    for k, (rt, rx, ry) in enumerate([
        (5.05, 430, 1060), (5.85, 890, 980), (6.55, 620, 1400),
        (7.25, 320, 1290), (8.35, 760, 1160), (9.25, 470, 880),
    ]):
        draw_ripple(layer, rx, ry, t - rt, 1.6, 180 + 25 * k, 72)

    combo = 1
    for ct in CATCH_TIMES:
        if t >= ct:
            combo += 1
    combo = min(12, max(1, combo - 1))
    score = int(round(1240 * (combo - 1) / 11.0))

    caught_count = 0
    for ct in CATCH_TIMES:
        if t >= ct:
            caught_count += 1

    # Flies and fireflies.
    for i in range(14):
        if i < 12 and t >= CATCH_TIMES[i]:
            continue
        fx, fy = fly_pos(i, t)
        draw_fly(layer, fx, fy, t, i in FIREFLIES, 1.0)

    # Dragonflies cross the frame.
    if 4.4 <= t <= 7.9:
        u = (t - 4.4) / 3.5
        draw_dragonfly(layer, lerp(-90, W + 90, u), 716 + 34 * math.sin(u * 6), t, 1)
    if 6.2 <= t <= 9.8:
        u = (t - 6.2) / 3.6
        draw_dragonfly(layer, lerp(W + 70, -70, u), 962 + 26 * math.sin(u * 5), t, -1)

    frog_x, frog_y, squash, face = frog_state(t)

    look_x = 0.0
    look_y = 0.2
    if caught_count and t - CATCH_TIMES[min(caught_count, 12) - 1] < 0.3:
        i = min(caught_count, 12) - 1
        tx, ty = fly_pos(i, t)
        look_x = clamp((tx - frog_x) / 180.0, -1, 1)
        look_y = clamp((ty - frog_y) / 180.0, -1, 1)
    draw_frog(layer, frog_x, frog_y, t, squash, look_x, look_y)

    # Catch pops, bursts and tongue.
    for i, ct in enumerate(CATCH_TIMES):
        age = t - ct
        if age < 0:
            continue
        tx, ty = fly_pos(i, ct)
        if age < 0.22:
            tip = ease_out(age / 0.22)
            mx, my = frog_x, frog_y + 6
            ex = lerp(mx, tx, tip)
            ey = lerp(my, ty, tip)
            d.line((mx, my, ex, ey), fill=(255, 118, 146, 245), width=10)
            d.ellipse((ex - 9, ey - 9, ex + 9, ey + 9), fill=(255, 146, 168, 255))
        if age < 0.95:
            u = age / 0.95
            draw_text_center(d, tx, ty - 26 - 84 * ease_out(u), "+10", F_POP,
                             (255, 246, 156, int(255 * (1 - u))),
                             stroke_width=3, stroke_fill=(10, 30, 24, int(210 * (1 - u))))
        if age < 0.65:
            u = age / 0.65
            rng = random.Random(9100 + i)
            for k in range(11):
                ang = rng.uniform(0, 6.283)
                spd = rng.uniform(60, 190)
                px = tx + math.cos(ang) * spd * u
                py = ty + math.sin(ang) * spd * u + 90 * u * u
                rr = 4 * (1 - u) + 1
                col = (255, 236, 142, int(240 * (1 - u))) if k % 3 else (150, 250, 214, int(220 * (1 - u)))
                d.ellipse((px - rr, py - rr, px + rr, py + rr), fill=col)

    draw_top_bar(d, score, 7)
    draw_day7_hud(d, combo, score)
    draw_hint(d, "wave 7")

    frame = Image.alpha_composite(frame, layer)
    return frame.convert("RGB")


# ---------------------------------------------------------------------------


def render_frame(i, bg1, bg7):
    t = i / float(FPS)
    if t < 4.0:
        frame = render_day1(t, bg1)
    else:
        frame = render_day7(t, bg7)
        if t >= 14.0:
            u = clamp((t - 14.0) / 0.85)
            u = ease_in_out(u)
            if u > 0.01:
                small = frame.resize((270, 480), Image.BILINEAR)
                small = small.filter(ImageFilter.GaussianBlur(7.0 * u))
                frame = small.resize((W, H), Image.BILINEAR)
                frame = ImageEnhance.Color(frame).enhance(1.0 - 0.45 * u)
                frame = ImageEnhance.Brightness(frame).enhance(1.0 - 0.22 * u)
    return frame


def main():
    print("stage 1/5: build static pond (day 1 and day 7 maps)")
    t0 = time.time()
    bg1 = build_background(False)
    bg7 = build_background(True)
    print("  backgrounds ready in %.2fs" % (time.time() - t0))

    out = os.path.join(HERE, "game.mp4")
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", "%dx%d" % (W, H), "-r", str(FPS), "-i", "pipe:0",
        "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", "-r", str(FPS), "-frames:v", str(NFRAMES),
        "-t", "%.3f" % DURATION, "-movflags", "+faststart", out,
    ]
    print("stage 2/5: render %d frames at %dx%d %d fps" % (NFRAMES, W, H, FPS))
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    start = time.time()
    try:
        for i in range(NFRAMES):
            frame = render_frame(i, bg1, bg7)
            proc.stdin.write(frame.tobytes())
            if i % 60 == 0 or i == NFRAMES - 1:
                print("  frame %3d/%d  t=%.2fs  elapsed=%.1fs" % (
                    i + 1, NFRAMES, i / float(FPS), time.time() - start))
    finally:
        proc.stdin.close()
        rc = proc.wait()
    if rc != 0:
        print("ffmpeg failed with code %d" % rc, file=sys.stderr)
        return rc
    print("stage 3/5: wrote %s in %.1fs" % (out, time.time() - start))
    print("stage 4/5: ffprobe game.mp4")
    subprocess.run([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration,size:stream=codec_name,width,height,r_frame_rate",
        "-of", "default=nw=1", out,
    ], check=True)
    print("stage 5/5: done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
