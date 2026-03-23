### Created by Zeyu Deng on 2026-03-22
# A generic body with a skeleton: idle breathing, walk cycle, jump pose.


#!/usr/bin/env python3
"""
Avatar Generation — Phase 1b: Pixel Skin
Pixel art sprites driven by the skeleton system.

Controls:
  ← →     walk
  Space   jump
  S       toggle skeleton overlay
  Q/Esc   quit
"""

import math
import sys
import pygame

# ── Window & physics ──────────────────────────────────────────────────────────
WIDTH, HEIGHT = 800, 600
FPS        = 60
GRAVITY    = 0.55
JUMP_VEL   = -13.5
MOVE_SPEED = 3.5
GROUND_Y   = HEIGHT - 90

# ── Scene colors ──────────────────────────────────────────────────────────────
C_BG       = ( 22,  24,  35)
C_GRID     = ( 32,  36,  50)
C_GROUND   = ( 42,  48,  65)
C_GND_LINE = ( 70,  78, 100)
C_BONE     = (110, 200, 160)
C_JOINT    = (160, 235, 195)
C_HUD      = (140, 150, 175)

# ── Pixel art palette ─────────────────────────────────────────────────────────
PA: dict = {
    '.': None,
    # skin
    'S': (214, 164, 110),  's': (165, 118,  75),
    # hair
    'H': ( 45,  28,  12),  'h': ( 68,  44,  22),
    # face details
    'E': ( 35,  22,   8),  'W': (240, 232, 218),  # eye pupil / white
    'M': (165,  82,  72),  'n': (188, 138,  95),  # mouth / nose
    # shirt (blue)
    'B': ( 68, 112, 188),  'b': ( 45,  80, 155),  'T': (160, 195, 235),
    # pants (dark navy)
    'P': ( 38,  44,  82),  'p': ( 24,  28,  55),
    # shoes
    'X': ( 42,  30,  18),  'x': ( 28,  18,  10),
    # belt
    'G': ( 80,  68,  50),  'g': ( 55,  44,  30),
}

PSCALE = 3   # 1 art pixel → 3×3 screen pixels

# ── Sprite helpers ────────────────────────────────────────────────────────────

def make_sprite(charmap: str, scale: int = PSCALE) -> pygame.Surface:
    rows = charmap.strip().split('\n')
    H = len(rows)
    W = max(len(r) for r in rows)
    surf = pygame.Surface((W * scale, H * scale), pygame.SRCALPHA)
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            c = PA.get(ch)
            if c is not None:
                pygame.draw.rect(surf, c, (x * scale, y * scale, scale, scale))
    return surf


def darken(surf: pygame.Surface, factor: float = 0.65) -> pygame.Surface:
    d = surf.copy()
    d.fill((int(255 * factor),) * 3, special_flags=pygame.BLEND_MULT)
    return d


# ── Sprite definitions ────────────────────────────────────────────────────────
# All limb maps are oriented POINTING DOWN:
#   row 0  = proximal joint (shoulder, hip, …)
#   last row = distal joint (elbow, knee, …)
# They are rotated at draw time to follow the actual bone vector.
#
# Approximate rendered sizes at PSCALE=3:
#   HEAD       10×10 → 30×30 px
#   TORSO       7×21 → 21×63 px  (bone hip_c→chest ≈ 64 px)
#   UPPER_ARM   5×12 → 15×36 px  (bone ≈ 34 px)
#   LOWER_ARM   5×11 → 15×33 px  (bone ≈ 33 px)
#   UPPER_LEG   6×14 → 18×42 px  (bone ≈ 42 px)
#   LOWER_LEG   6×14 → 18×42 px  (bone ≈ 44 px)

HEAD_MAP = """\
..HHHHHH..
.HhHHHhhH.
HhSSSSSSsH
HSWEWSsssH
HSSSSSSssH
HSSnnSSssH
HSsMSSsssH
.HSSSSssH.
..HHHHhH..
...HHHH..."""

TORSO_MAP = """\
.TBBBT.
TBBBBBT
bBBBBBb
bBBBBBb
bBBBBBb
bBBBBBb
bBBBBBb
bBBGBBb
bBGgGBb
bPPPPPb
bPPPPPb
bPPPPPb
pPPPPPp
pPPPPPp
pPPPPPp
pPPPPPp
.pPPPp.
..pPp..
..pPp..
..pPp..
...p..."""

UPPER_ARM_MAP = """\
.BBB.
bBBBb
bBBBb
bBBBb
bBBBb
bBBBb
bBBBb
bBSSb
.bSs.
.SSs.
..S..
..S.."""

LOWER_ARM_MAP = """\
.SSS.
SSSss
SSSss
SSSss
SSSss
SSSss
SSSss
.SSs.
.SSs.
..Ss.
..S.."""

UPPER_LEG_MAP = """\
.PPPP.
PPPPpP
PPPPpP
PPPPpP
PPPPpP
PPPPpP
PPPPpP
PPPPpP
PPPPpP
.PPPp.
.PPPp.
..PPp.
..Pp..
...p.."""

LOWER_LEG_MAP = """\
.PPPP.
PPPPpP
PPPPpP
PPPPpP
PPPPpP
XXXXXX
XxXXXX
XxXXXX
XxXXXX
XxXXXX
.xXXX.
.xXXX.
..XXx.
..XX.."""


# ── PixelSkin ─────────────────────────────────────────────────────────────────

class PixelSkin:
    """Holds all pre-rendered pixel art surfaces for one avatar."""

    def __init__(self):
        self.head       = make_sprite(HEAD_MAP)
        self.torso      = make_sprite(TORSO_MAP)
        ua              = make_sprite(UPPER_ARM_MAP)
        la              = make_sprite(LOWER_ARM_MAP)
        ul              = make_sprite(UPPER_LEG_MAP)
        ll              = make_sprite(LOWER_LEG_MAP)
        self.upper_arm       = ua
        self.lower_arm       = la
        self.upper_leg       = ul
        self.lower_leg       = ll
        # Darker copies for the back (further-from-viewer) limbs
        self.upper_arm_dark  = darken(ua)
        self.lower_arm_dark  = darken(la)
        self.upper_leg_dark  = darken(ul)
        self.lower_leg_dark  = darken(ll)


# ── Skeleton ──────────────────────────────────────────────────────────────────
# Body-space: origin = hip_center, x-right, y-up (screen y is flipped on draw)

REST: dict[str, tuple[float, float]] = {
    "hip_c":       (  0,    0),
    "spine":       (  0,   34),
    "chest":       (  0,   64),
    "neck":        (  0,   80),
    "head":        (  0,  108),
    "l_shoulder":  (-28,   60),
    "l_elbow":     (-44,   30),
    "l_wrist":     (-50,   -2),
    "r_shoulder":  ( 28,   60),
    "r_elbow":     ( 44,   30),
    "r_wrist":     ( 50,   -2),
    "l_hip":       (-14,   -4),
    "l_knee":      (-17,  -46),
    "l_ankle":     (-15,  -90),
    "r_hip":       ( 14,   -4),
    "r_knee":      ( 17,  -46),
    "r_ankle":     ( 15,  -90),
}

BONES: list[tuple[str, str, int]] = [
    ("hip_c", "spine",      4), ("spine",      "chest",     4),
    ("chest", "neck",       3), ("neck",        "head",      3),
    ("chest", "l_shoulder", 3), ("l_shoulder", "l_elbow",   3),
    ("l_elbow", "l_wrist",  2),
    ("chest", "r_shoulder", 3), ("r_shoulder", "r_elbow",   3),
    ("r_elbow", "r_wrist",  2),
    ("hip_c", "l_hip",      3), ("l_hip",      "l_knee",    4),
    ("l_knee", "l_ankle",   3),
    ("hip_c", "r_hip",      3), ("r_hip",      "r_knee",    4),
    ("r_knee", "r_ankle",   3),
]


class Skeleton:
    def __init__(self, root_x: float, root_y: float):
        self.root_x = root_x
        self.root_y = root_y
        self.pose: dict[str, tuple[float, float]] = {}
        self.update({})

    def update(self, offsets: dict[str, tuple[float, float]]) -> None:
        for name, (bx, by) in REST.items():
            dx, dy = offsets.get(name, (0.0, 0.0))
            self.pose[name] = (self.root_x + bx + dx,
                               self.root_y - (by + dy))  # flip y

    def move_root(self, x: float, y: float) -> None:
        self.root_x, self.root_y = x, y

    def w(self, name: str) -> tuple[float, float]:
        return self.pose[name]


# ── Bone-sprite renderer ──────────────────────────────────────────────────────

def draw_bone_sprite(
    surf: pygame.Surface,
    sprite: pygame.Surface,
    pa: tuple[int, int],
    pb: tuple[int, int],
    flip_x: bool = False,
) -> None:
    """
    Rotate `sprite` so its vertical axis aligns with the bone pa→pb,
    then blit centered on the bone midpoint.

    Convention: sprite row-0 = near pa, last row = near pb (pointing down).
    Rotation formula: pygame_angle = 90 - degrees(atan2(dy, dx))
    """
    dx = pb[0] - pa[0]
    dy = pb[1] - pa[1]
    s = pygame.transform.flip(sprite, True, False) if flip_x else sprite
    angle = 90.0 - math.degrees(math.atan2(dy, dx))
    rot = pygame.transform.rotate(s, angle)
    mx = (pa[0] + pb[0]) // 2
    my = (pa[1] + pb[1]) // 2
    surf.blit(rot, (mx - rot.get_width() // 2, my - rot.get_height() // 2))


# ── Avatar ────────────────────────────────────────────────────────────────────

class Avatar:
    def __init__(self, x: float):
        self.x         = float(x)
        self.y         = float(GROUND_Y)
        self.vel_x     = 0.0
        self.vel_y     = 0.0
        self.on_ground = True
        self.facing    = 1        # +1 right, -1 left
        self.time      = 0.0
        self.show_skeleton = False
        self.skeleton  = Skeleton(self.x, self.y)

    # ── Input ─────────────────────────────────────────────────────────────────

    def apply_input(self, keys) -> None:
        if keys[pygame.K_LEFT]:
            self.vel_x, self.facing = -MOVE_SPEED, -1
        elif keys[pygame.K_RIGHT]:
            self.vel_x, self.facing =  MOVE_SPEED,  1
        else:
            self.vel_x = 0.0
        if keys[pygame.K_SPACE] and self.on_ground:
            self.vel_y     = JUMP_VEL
            self.on_ground = False

    # ── Physics ───────────────────────────────────────────────────────────────

    def update(self, dt: float) -> None:
        self.time += dt
        if not self.on_ground:
            self.vel_y += GRAVITY
        self.x += self.vel_x
        self.y += self.vel_y
        if self.y >= GROUND_Y:
            self.y, self.vel_y, self.on_ground = GROUND_Y, 0.0, True
        self.x = max(60.0, min(WIDTH - 60.0, self.x))
        self.skeleton.move_root(self.x, self.y)
        self.skeleton.update(self._offsets())

    # ── Animation ─────────────────────────────────────────────────────────────

    def _offsets(self) -> dict[str, tuple[float, float]]:
        t        = self.time
        moving   = abs(self.vel_x) > 0.1
        airborne = not self.on_ground
        off: dict[str, tuple[float, float]] = {}

        # Breathing — always active
        breath = math.sin(t * 1.5) * 1.8
        off["chest"]      = (0, breath)
        off["neck"]       = (0, breath * 0.8)
        off["head"]       = (0, breath * 0.6)
        off["l_shoulder"] = (0, breath * 0.5)
        off["r_shoulder"] = (0, breath * 0.5)

        # Idle sway
        if not moving and not airborne:
            sway = math.sin(t * 0.55) * 1.0
            off["hip_c"] = (sway * 0.5, 0)
            off["spine"] = (sway * 0.3, 0)

        # Walk cycle
        if moving and not airborne:
            freq  = 6.5
            phase = t * freq * self.facing
            sw    = math.sin(phase)
            sw2   = math.sin(phase + math.pi)
            bob   = abs(sw) * -2.8
            off["hip_c"] = (0, bob)
            off["spine"] = (0, bob * 0.4)

            lx = 9.0 * sw
            off["l_hip"]   = ( lx,  0)
            off["l_knee"]  = ( lx * 0.7, -abs(sw)  * 5)
            off["l_ankle"] = ( lx * 0.3,  abs(sw)  * 5)
            off["r_hip"]   = (-lx,  0)
            off["r_knee"]  = (-lx * 0.7, -abs(sw2) * 5)
            off["r_ankle"] = (-lx * 0.3,  abs(sw2) * 5)

            ax = 11.0 * sw2
            off["l_shoulder"] = ( ax * 0.35, breath * 0.5)
            off["l_elbow"]    = ( ax * 0.75, 0)
            off["l_wrist"]    = ( ax,         0)
            off["r_shoulder"] = (-ax * 0.35, breath * 0.5)
            off["r_elbow"]    = (-ax * 0.75, 0)
            off["r_wrist"]    = (-ax,         0)

        # Jump / fall pose
        if airborne:
            tuck  = min(abs(self.vel_y) / 6.0, 1.0)
            sign  = 1 if self.vel_y < 0 else -0.4
            off["l_knee"]  = (-3, -9 * tuck)
            off["r_knee"]  = ( 3, -9 * tuck)
            off["l_ankle"] = (-2,  6 * tuck * sign)
            off["r_ankle"] = ( 2,  6 * tuck * sign)
            arm_y = -14 if self.vel_y < 0 else 5
            off["l_wrist"] = (-5, arm_y)
            off["r_wrist"] = ( 5, arm_y)
            off["l_elbow"] = (-4, arm_y * 0.5)
            off["r_elbow"] = ( 4, arm_y * 0.5)

        return off

    # ── Draw ──────────────────────────────────────────────────────────────────

    def draw(self, surf: pygame.Surface, skin: PixelSkin) -> None:
        sk   = self.skeleton
        flip = (self.facing == -1)

        def wp(name: str) -> tuple[int, int]:
            """World (screen) position, mirrored when facing left."""
            px, py = sk.w(name)
            if flip:
                px = 2 * self.x - px
            return int(px), int(py)

        _draw_shadow(surf, int(self.x), GROUND_Y + 7, 54, 14, 70)

        # ── Draw order: back limbs → torso → front limbs → head ──────────────
        #
        # l_* joints = front (closer to viewer).
        # r_* joints = back (further from viewer), drawn darker.
        # When flip=True the positions are mirrored but the labelling holds.

        # Back arm
        draw_bone_sprite(surf, skin.upper_arm_dark,
                         wp('r_shoulder'), wp('r_elbow'), flip)
        draw_bone_sprite(surf, skin.lower_arm_dark,
                         wp('r_elbow'),    wp('r_wrist'), flip)

        # Back leg
        draw_bone_sprite(surf, skin.upper_leg_dark,
                         wp('r_hip'),  wp('r_knee'),  flip)
        draw_bone_sprite(surf, skin.lower_leg_dark,
                         wp('r_knee'), wp('r_ankle'), flip)

        # Torso — pa=chest (top), pb=hip_c (bottom) so sprite row-0 = collar
        draw_bone_sprite(surf, skin.torso,
                         wp('chest'), wp('hip_c'), flip)

        # Front leg
        draw_bone_sprite(surf, skin.upper_leg,
                         wp('l_hip'),  wp('l_knee'),  flip)
        draw_bone_sprite(surf, skin.lower_leg,
                         wp('l_knee'), wp('l_ankle'), flip)

        # Front arm
        draw_bone_sprite(surf, skin.upper_arm,
                         wp('l_shoulder'), wp('l_elbow'), flip)
        draw_bone_sprite(surf, skin.lower_arm,
                         wp('l_elbow'),    wp('l_wrist'), flip)

        # Head — centered at head joint, flipped for direction
        hx, hy = wp('head')
        hs = pygame.transform.flip(skin.head, True, False) if flip else skin.head
        surf.blit(hs, (hx - hs.get_width() // 2, hy - hs.get_height() // 2))

        # Skeleton overlay (press S)
        if self.show_skeleton:
            for a, b, thick in BONES:
                pygame.draw.line(surf, C_BONE, wp(a), wp(b), max(1, thick - 1))
            for name in REST:
                r = 4 if name in ('hip_c', 'chest', 'spine') else 3
                pygame.draw.circle(surf, C_JOINT,        wp(name), r)
                pygame.draw.circle(surf, (255, 255, 255), wp(name), 1)


# ── Scene helpers ─────────────────────────────────────────────────────────────

def _draw_shadow(surf, cx, cy, width, height, alpha):
    s = pygame.Surface((width, height), pygame.SRCALPHA)
    pygame.draw.ellipse(s, (0, 0, 0, alpha), (0, 0, width, height))
    surf.blit(s, (cx - width // 2, cy - height // 2))


def draw_background(surf: pygame.Surface) -> None:
    surf.fill(C_BG)
    for x in range(0, WIDTH, 40):
        pygame.draw.line(surf, C_GRID, (x, 0), (x, GROUND_Y))
    for y in range(0, GROUND_Y, 40):
        pygame.draw.line(surf, C_GRID, (0, y), (WIDTH, y))
    pygame.draw.rect(surf, C_GROUND, (0, GROUND_Y, WIDTH, HEIGHT - GROUND_Y))
    pygame.draw.line(surf, C_GND_LINE, (0, GROUND_Y), (WIDTH, GROUND_Y), 2)


def draw_hud(surf: pygame.Surface, avatar: Avatar, font: pygame.font.Font) -> None:
    state = ('airborne' if not avatar.on_ground
             else ('walking' if abs(avatar.vel_x) > 0.1 else 'idle'))
    sk_hint = '[S: hide skeleton]' if avatar.show_skeleton else '[S: show skeleton]'
    lines = [
        '← → : walk     Space : jump     Q : quit     ' + sk_hint,
        f'state: {state:10s}  facing: {"right" if avatar.facing == 1 else "left "}',
    ]
    for i, line in enumerate(lines):
        surf.blit(font.render(line, True, C_HUD), (14, 10 + i * 18))


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    pygame.init()
    pygame.font.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption('Avatar Demo — Phase 1b: Pixel Skin')
    clock = pygame.time.Clock()
    try:
        font = pygame.font.SysFont('monospace', 13)
    except Exception:
        font = pygame.font.Font(None, 16)

    skin   = PixelSkin()
    avatar = Avatar(WIDTH // 2)

    while True:
        dt = clock.tick(FPS) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_q, pygame.K_ESCAPE):
                    pygame.quit(); sys.exit()
                if event.key == pygame.K_s:
                    avatar.show_skeleton = not avatar.show_skeleton

        avatar.apply_input(pygame.key.get_pressed())
        avatar.update(dt)
        draw_background(screen)
        avatar.draw(screen, skin)
        draw_hud(screen, avatar, font)
        pygame.display.flip()


if __name__ == '__main__':
    main()