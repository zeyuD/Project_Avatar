### Created by Zeyu Deng on 2026-03-22
# A generic body with a skeleton: idle breathing, walk cycle, jump pose.

#!/usr/bin/env python3
"""
Avatar Generation — Phase 1
Generic body with skeleton: idle breathing, walk cycle, jump.

Controls:
  ← →     walk
  Space   jump
  S       toggle skeleton overlay
  Q/Esc   quit

Requirements:
  pip install pygame
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
GROUND_Y   = HEIGHT - 90    # screen-y of the ground surface

# ── Palette ───────────────────────────────────────────────────────────────────

C_BG       = ( 22,  24,  35)
C_GRID     = ( 32,  36,  50)
C_GROUND   = ( 42,  48,  65)
C_GND_LINE = ( 70,  78, 100)
C_BONE     = (110, 200, 160)
C_JOINT    = (160, 235, 195)
C_BODY     = ( 80, 125, 190)
C_BODY_D   = ( 52,  88, 145)
C_SKIN     = (215, 178, 138)
C_SKIN_D   = (175, 140, 102)
C_HUD      = (140, 150, 175)

# ── Skeleton — rest pose ──────────────────────────────────────────────────────
#
# Body-space coordinates:  origin = hip_center,  x-right,  y-up,  pixels.
# A ~200 px tall figure standing with arms slightly lowered.

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

# Bones: (joint_a, joint_b, draw_thickness)
BONES: list[tuple[str, str, int]] = [
    ("hip_c",      "spine",       4),
    ("spine",      "chest",       4),
    ("chest",      "neck",        3),
    ("neck",       "head",        3),
    ("chest",      "l_shoulder",  3),
    ("l_shoulder", "l_elbow",     3),
    ("l_elbow",    "l_wrist",     2),
    ("chest",      "r_shoulder",  3),
    ("r_shoulder", "r_elbow",     3),
    ("r_elbow",    "r_wrist",     2),
    ("hip_c",      "l_hip",       3),
    ("l_hip",      "l_knee",      4),
    ("l_knee",     "l_ankle",     3),
    ("hip_c",      "r_hip",       3),
    ("r_hip",      "r_knee",      4),
    ("r_knee",     "r_ankle",     3),
]

# Body segments — back layer drawn first (dark), front layer on top (bright).
# (joint_a, joint_b, radius_a, radius_b, fill_color, outline_color)
SEGMENTS_BACK: list[tuple] = [
    ("r_hip",      "r_knee",      10,  8,  C_BODY_D, C_BODY_D),
    ("r_knee",     "r_ankle",      8,  6,  C_BODY_D, C_BODY_D),
    ("r_shoulder", "r_elbow",      9,  7,  C_BODY_D, C_BODY_D),
    ("r_elbow",    "r_wrist",      7,  5,  C_BODY_D, C_BODY_D),
]
SEGMENTS_FRONT: list[tuple] = [
    ("hip_c",      "spine",       18, 18,  C_BODY,   C_BODY_D),
    ("spine",      "chest",       18, 17,  C_BODY,   C_BODY_D),
    ("chest",      "neck",        15,  9,  C_BODY,   C_BODY_D),
    ("l_hip",      "l_knee",      10,  8,  C_BODY,   C_BODY_D),
    ("l_knee",     "l_ankle",      8,  6,  C_BODY,   C_BODY_D),
    ("l_shoulder", "l_elbow",      9,  7,  C_BODY,   C_BODY_D),
    ("l_elbow",    "l_wrist",      7,  5,  C_BODY,   C_BODY_D),
]


# ── Skeleton class ────────────────────────────────────────────────────────────

class Skeleton:
    """
    Maintains world-space joint positions for the current frame.
    Converts body-space REST + per-joint offsets into screen coordinates.
    """

    def __init__(self, root_x: float, root_y: float):
        self.root_x = root_x
        self.root_y = root_y      # screen-y of hip_center
        self.pose: dict[str, tuple[float, float]] = {}
        self.update({})

    def update(self, offsets: dict[str, tuple[float, float]]) -> None:
        """Recompute all joint screen positions."""
        for name, (bx, by) in REST.items():
            dx, dy = offsets.get(name, (0.0, 0.0))
            # body-space y is up; screen-y is down — flip sign
            sx = self.root_x + bx + dx
            sy = self.root_y - (by + dy)
            self.pose[name] = (sx, sy)

    def move_root(self, x: float, y: float) -> None:
        self.root_x, self.root_y = x, y

    def w(self, name: str) -> tuple[float, float]:
        """World (screen) position of joint `name`."""
        return self.pose[name]


# ── Avatar class ──────────────────────────────────────────────────────────────

class Avatar:
    def __init__(self, x: float):
        self.x    = float(x)
        self.y    = float(GROUND_Y)   # screen-y of hip_center
        self.vel_x = 0.0
        self.vel_y = 0.0
        self.on_ground    = True
        self.facing       = 1         # +1 right, -1 left
        self.time         = 0.0       # animation clock (seconds)
        self.show_skeleton = False
        self.skeleton = Skeleton(self.x, self.y)

    # ── Input ─────────────────────────────────────────────────────────────────

    def apply_input(self, keys: pygame.key.ScancodeWrapper) -> None:
        if keys[pygame.K_LEFT]:
            self.vel_x = -MOVE_SPEED
            self.facing = -1
        elif keys[pygame.K_RIGHT]:
            self.vel_x =  MOVE_SPEED
            self.facing =  1
        else:
            self.vel_x = 0.0

        if keys[pygame.K_SPACE] and self.on_ground:
            self.vel_y = JUMP_VEL
            self.on_ground = False

    # ── Physics & animation ───────────────────────────────────────────────────

    def update(self, dt: float) -> None:
        self.time += dt

        # Gravity & movement
        if not self.on_ground:
            self.vel_y += GRAVITY
        self.x += self.vel_x
        self.y += self.vel_y

        # Ground
        if self.y >= GROUND_Y:
            self.y, self.vel_y, self.on_ground = GROUND_Y, 0.0, True

        # Walls
        self.x = max(60.0, min(WIDTH - 60.0, self.x))

        self.skeleton.move_root(self.x, self.y)
        self.skeleton.update(self._offsets())

    def _offsets(self) -> dict[str, tuple[float, float]]:
        """
        Compute per-joint (dx, dy) offsets in body space for this frame.
        dy > 0  →  joint moves up on screen.
        """
        t       = self.time
        moving  = abs(self.vel_x) > 0.1
        airborne = not self.on_ground
        off: dict[str, tuple[float, float]] = {}

        # ── Breathing (always active) ──────────────────────────────────────────
        breath = math.sin(t * 1.5) * 1.8
        off["chest"]      = (0, breath)
        off["neck"]       = (0, breath * 0.8)
        off["head"]       = (0, breath * 0.6)
        off["l_shoulder"] = (0, breath * 0.5)
        off["r_shoulder"] = (0, breath * 0.5)

        # ── Idle sway ─────────────────────────────────────────────────────────
        if not moving and not airborne:
            sway = math.sin(t * 0.55) * 1.0
            off["hip_c"] = (sway * 0.5, 0)
            off["spine"] = (sway * 0.3, 0)

        # ── Walk cycle ────────────────────────────────────────────────────────
        if moving and not airborne:
            freq  = 6.5
            phase = t * freq * self.facing
            sw    = math.sin(phase)
            sw2   = math.sin(phase + math.pi)

            # Vertical bob: hips dip on each footfall
            bob = abs(sw) * -2.8
            off["hip_c"] = (0, bob)
            off["spine"] = (0, bob * 0.4)

            # Leg swing: x-offset drives forward/back stride
            lx = 9.0 * sw
            off["l_hip"]   = ( lx,  0)
            off["l_knee"]  = ( lx * 0.7, -abs(sw)  * 5)
            off["l_ankle"] = ( lx * 0.3,  abs(sw)  * 5)  # lift foot
            off["r_hip"]   = (-lx,  0)
            off["r_knee"]  = (-lx * 0.7, -abs(sw2) * 5)
            off["r_ankle"] = (-lx * 0.3,  abs(sw2) * 5)

            # Arms counter-swing
            ax = 11.0 * sw2
            off["l_shoulder"] = ( ax * 0.35, breath * 0.5)
            off["l_elbow"]    = ( ax * 0.75, 0)
            off["l_wrist"]    = ( ax,         0)
            off["r_shoulder"] = (-ax * 0.35, breath * 0.5)
            off["r_elbow"]    = (-ax * 0.75, 0)
            off["r_wrist"]    = (-ax,         0)

        # ── Jump / fall pose ──────────────────────────────────────────────────
        if airborne:
            tuck = min(abs(self.vel_y) / 6.0, 1.0)
            sign = 1 if self.vel_y < 0 else -0.4    # ascending vs descending
            off["l_knee"]  = (-3, -9 * tuck)
            off["r_knee"]  = ( 3, -9 * tuck)
            off["l_ankle"] = (-2,  6 * tuck * sign)
            off["r_ankle"] = ( 2,  6 * tuck * sign)
            # Arms rise on jump, settle on fall
            arm_y = -14 if self.vel_y < 0 else 5
            off["l_wrist"] = (-5, arm_y)
            off["r_wrist"] = ( 5, arm_y)
            off["l_elbow"] = (-4, arm_y * 0.5)
            off["r_elbow"] = ( 4, arm_y * 0.5)

        return off

    # ── Draw ──────────────────────────────────────────────────────────────────

    def draw(self, surf: pygame.Surface) -> None:
        sk = self.skeleton

        def wp(name: str) -> tuple[int, int]:
            """World position, mirrored when facing left."""
            px, py = sk.w(name)
            if self.facing == -1:
                px = 2 * self.x - px
            return int(px), int(py)

        # Drop shadow
        _draw_shadow(surf, int(self.x), GROUND_Y + 7,
                     width=52, height=14, alpha=70)

        # Back limbs
        for a, b, ra, rb, fill, outline in SEGMENTS_BACK:
            draw_capsule(surf, wp(a), wp(b), ra, rb, fill, outline)

        # Torso + front limbs
        for a, b, ra, rb, fill, outline in SEGMENTS_FRONT:
            draw_capsule(surf, wp(a), wp(b), ra, rb, fill, outline)

        # Head
        hx, hy = wp("head")
        pygame.draw.circle(surf, C_SKIN_D, (hx, hy), 17)
        pygame.draw.circle(surf, C_SKIN,   (hx, hy), 15)

        # Simple face — always looks in the direction of travel
        ex = 5 * self.facing
        pygame.draw.circle(surf, (60, 40, 30), (hx + ex, hy - 3), 2)
        pygame.draw.line(surf, (150, 100, 80),
                         (hx + ex - 3, hy + 4),
                         (hx + ex + 3, hy + 6), 2)

        # Skeleton overlay
        if self.show_skeleton:
            for a, b, thick in BONES:
                pygame.draw.line(surf, C_BONE, wp(a), wp(b), max(1, thick - 1))
            for name in REST:
                r = 4 if name in ("hip_c", "chest", "spine") else 3
                pygame.draw.circle(surf, C_JOINT, wp(name), r)
                pygame.draw.circle(surf, (255, 255, 255), wp(name), 1)


# ── Drawing helpers ───────────────────────────────────────────────────────────

def draw_capsule(
    surf: pygame.Surface,
    pa: tuple[int, int],
    pb: tuple[int, int],
    ra: int,
    rb: int,
    fill: tuple[int, int, int],
    outline: tuple[int, int, int],
) -> None:
    """Tapered capsule from pa (radius ra) to pb (radius rb)."""
    ax, ay = pa
    bx, by = pb
    dx, dy = bx - ax, by - ay
    length = math.hypot(dx, dy)
    if length < 1:
        pygame.draw.circle(surf, fill, pa, ra)
        return

    nx, ny = -dy / length, dx / length   # perpendicular unit vector

    def poly(r1: int, r2: int) -> list[tuple[int, int]]:
        return [
            (int(ax + nx * r1), int(ay + ny * r1)),
            (int(ax - nx * r1), int(ay - ny * r1)),
            (int(bx - nx * r2), int(by - ny * r2)),
            (int(bx + nx * r2), int(by + ny * r2)),
        ]

    pygame.draw.polygon(surf, outline, poly(ra, rb))
    pygame.draw.polygon(surf, fill,    poly(ra - 1, rb - 1))
    pygame.draw.circle(surf, fill,    pa, max(1, ra - 1))
    pygame.draw.circle(surf, fill,    pb, max(1, rb - 1))
    pygame.draw.circle(surf, outline, pa, ra, 1)
    pygame.draw.circle(surf, outline, pb, rb, 1)


def _draw_shadow(
    surf: pygame.Surface,
    cx: int, cy: int,
    width: int, height: int, alpha: int
) -> None:
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
    state = "airborne" if not avatar.on_ground else (
        "walking" if abs(avatar.vel_x) > 0.1 else "idle"
    )
    skel_hint = "[S: hide skeleton]" if avatar.show_skeleton else "[S: show skeleton]"
    lines = [
        "< > : walk     Space : jump     Q : quit     " + skel_hint,
        f"state: {state:10s}  facing: {'right' if avatar.facing == 1 else 'left '}",
    ]
    for i, line in enumerate(lines):
        surf.blit(font.render(line, True, C_HUD), (14, 10 + i * 18))


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Avatar Demo — Phase 1: Skeleton")
    clock = pygame.time.Clock()
    try:
        font = pygame.font.SysFont("monospace", 13)
    except Exception:
        font = pygame.font.Font(None, 16)   # built-in fallback, no file needed

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

        keys = pygame.key.get_pressed()
        avatar.apply_input(keys)
        avatar.update(dt)

        draw_background(screen)
        avatar.draw(screen)
        draw_hud(screen, avatar, font)
        pygame.display.flip()


if __name__ == "__main__":
    main()