"""
Player module — sprite-based platformer character with dash and audio.
"""

import os
import json
import math
import pygame

from settings import (
    PLAYER_SPEED, INTERACT_RANGE,
    GRAVITY, MAX_FALL_SPEED,
    JUMP_FORCE, DOUBLE_JUMP_FORCE,
    WALL_SLIDE_SPEED,
    WALL_JUMP_FORCE_X, WALL_JUMP_FORCE_Y,
    COYOTE_TIME, JUMP_BUFFER_TIME, WALL_STICK_TIME,
    WALK_FRAME_DELAY, IDLE_FRAME_DELAY,
    SPRITE_TARGET_HEIGHT, BG_THRESHOLD,
    COLLISION_W_RATIO, COLLISION_H_RATIO,
    MIN_COLLISION_W, MIN_COLLISION_H,
    SWAP_LEFT_RIGHT,
    DASH_SPEED, DASH_DURATION, DASH_COOLDOWN, DASH_GHOST_COUNT,
    BOUNCE_FORCE,
)


def remove_background(surface, bg_color=(0, 0, 0), threshold=40):
    result = surface.convert_alpha()
    w, h   = result.get_size()
    result.lock()
    for y in range(h):
        for x in range(w):
            r, g, b, a = result.get_at((x, y))
            if (abs(r - bg_color[0]) <= threshold and
                abs(g - bg_color[1]) <= threshold and
                abs(b - bg_color[2]) <= threshold):
                result.set_at((x, y), (r, g, b, 0))
    result.unlock()
    return result


class SpriteSheet:
    def __init__(self, image_path, json_path, bg_color=(0, 0, 0), bg_threshold=BG_THRESHOLD):
        self.bg_color     = bg_color
        self.bg_threshold = bg_threshold
        self.is_jpg       = image_path.lower().endswith((".jpg", ".jpeg"))

        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Spritesheet not found: {image_path}")
        self.sheet = pygame.image.load(image_path)
        self.sheet = self.sheet.convert() if self.is_jpg else self.sheet.convert_alpha()

        if not os.path.exists(json_path):
            raise FileNotFoundError(f"JSON not found: {json_path}")
        with open(json_path, "r") as f:
            self.data = json.load(f)

        self.frame_w = self.data["spritesheet_info"]["frame_width"]
        self.frame_h = self.data["spritesheet_info"]["frame_height"]
        self.scale   = SPRITE_TARGET_HEIGHT / self.frame_h
        self.scaled_w = max(1, int(self.frame_w * self.scale))
        self.scaled_h = max(1, int(self.frame_h * self.scale))
        self.collision_w = max(MIN_COLLISION_W, int(self.scaled_w * COLLISION_W_RATIO))
        self.collision_h = max(MIN_COLLISION_H, int(self.scaled_h * COLLISION_H_RATIO))

        raw_right = self._extract("right")
        raw_left  = self._extract("left")
        if SWAP_LEFT_RIGHT:
            self.right_frames = raw_left
            self.left_frames  = raw_right
        else:
            self.right_frames = raw_right
            self.left_frames  = raw_left

    def _extract(self, direction):
        frames = []
        if direction not in self.data["frames"]:
            return frames
        for info in self.data["frames"][direction]:
            rect = pygame.Rect(info["x"], info["y"], self.frame_w, self.frame_h)
            surf = pygame.Surface((self.frame_w, self.frame_h), pygame.SRCALPHA)
            surf.blit(self.sheet, (0, 0), rect)
            if self.is_jpg:
                surf = remove_background(surf, self.bg_color, self.bg_threshold)
            if self.scale != 1.0:
                surf = pygame.transform.smoothscale(surf, (self.scaled_w, self.scaled_h))
            frames.append(surf)
        return frames


class FallbackSpriteSheet:
    def __init__(self):
        self.scaled_w    = int(SPRITE_TARGET_HEIGHT * 0.65)
        self.scaled_h    = SPRITE_TARGET_HEIGHT
        self.collision_w = max(MIN_COLLISION_W, int(self.scaled_w * COLLISION_W_RATIO))
        self.collision_h = max(MIN_COLLISION_H, int(self.scaled_h * COLLISION_H_RATIO))
        self.right_frames = self._make_frames(True)
        self.left_frames  = self._make_frames(False)

    def _make_frames(self, facing_right):
        frames = []
        w, h = self.scaled_w, self.scaled_h
        for i in range(4):
            s = pygame.Surface((w, h), pygame.SRCALPHA)
            pygame.draw.rect(s, (0, 200, 120), (0, 0, w, h), border_radius=6)
            pygame.draw.rect(s, (0, 100, 60),  (0, 0, w, h), 2, border_radius=6)
            cx  = w // 2
            ey  = int(h * 0.3)
            off = 2 if facing_right else -2
            pygame.draw.circle(s, (255, 255, 255), (cx - 6, ey), 4)
            pygame.draw.circle(s, (255, 255, 255), (cx + 6, ey), 4)
            pygame.draw.circle(s, (0, 0, 0), (cx - 6 + off, ey), 2)
            pygame.draw.circle(s, (0, 0, 0), (cx + 6 + off, ey), 2)
            leg = [-2, 0, 2, 0][i]
            pygame.draw.line(s, (0, 100, 60), (cx - 4 + leg, h - 6), (cx - 4 + leg, h - 1), 2)
            pygame.draw.line(s, (0, 100, 60), (cx + 4 - leg, h - 6), (cx + 4 - leg, h - 1), 2)
            frames.append(s)
        return frames


class Animator:
    def __init__(self, sprite_sheet):
        rf = sprite_sheet.right_frames
        lf = sprite_sheet.left_frames
        self.walk_right  = [rf[0], rf[1], rf[2], rf[3], rf[2], rf[1]] if len(rf) >= 4 else list(rf)
        self.walk_left   = [lf[0], lf[1], lf[2], lf[3], lf[2], lf[1]] if len(lf) >= 4 else list(lf)
        self.idle_right  = rf[0] if rf else None
        self.idle_left   = lf[0] if lf else None
        self.state       = "idle_right"
        self.frame_index = 0
        self.timer       = 0.0

    @property
    def delay(self):
        return WALK_FRAME_DELAY if "walk" in self.state else IDLE_FRAME_DELAY

    @property
    def current_frames(self):
        if self.state == "walk_right": return self.walk_right or None
        if self.state == "walk_left":  return self.walk_left  or None
        return None

    @property
    def current_surface(self):
        frames = self.current_frames
        if frames: return frames[self.frame_index % len(frames)]
        if self.state == "idle_left" and self.idle_left: return self.idle_left
        return self.idle_right

    def set_state(self, new_state):
        if new_state != self.state:
            self.state       = new_state
            self.frame_index = 0
            self.timer       = 0.0

    def update(self, dt):
        self.timer += dt
        if self.timer >= self.delay:
            self.timer -= self.delay
            frames = self.current_frames
            if frames:
                self.frame_index = (self.frame_index + 1) % len(frames)


class Ghost:
    def __init__(self, x, y, surface, sprite_w, sprite_h, col_h):
        self.x        = x
        self.y        = y
        self.surface  = surface
        self.sprite_w = sprite_w
        self.sprite_h = sprite_h
        self.col_h    = col_h
        self.alpha    = 180.0
        self.alive    = True

    def update(self, dt):
        self.alpha -= 600 * dt
        if self.alpha <= 0:
            self.alpha = 0
            self.alive = False

    def draw(self, surface, cam_x, cam_y):
        if not self.alive or self.surface is None:
            return
        ghost_surf = self.surface.copy()
        tint = pygame.Surface(ghost_surf.get_size(), pygame.SRCALPHA)
        tint.fill((100, 200, 255, int(self.alpha * 0.5)))
        ghost_surf.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        ghost_surf.set_alpha(int(self.alpha))
        dx = int(self.x - self.sprite_w / 2 - cam_x)
        dy = int((self.y + self.col_h / 2) - self.sprite_h - cam_y)
        surface.blit(ghost_surf, (dx, dy))


class Player:
    def __init__(self, x, y, sprite_sheet, audio=None, max_jumps=2):
        self.x     = round(float(x))
        self.y     = round(float(y))
        self.audio = audio
        self.max_jumps = max_jumps

        self.sprite_w = sprite_sheet.scaled_w
        self.sprite_h = sprite_sheet.scaled_h
        self.w        = sprite_sheet.collision_w
        self.h        = sprite_sheet.collision_h

        self.animator = Animator(sprite_sheet)

        self.vx = 0.0
        self.vy = 0.0

        self.on_ground   = False
        self.on_wall     = False
        self.wall_dir    = 0
        self.facing      = 1
        self.near_portal = False

        self.jumps_left       = self.max_jumps
        self.coyote_timer     = 0.0
        self.jump_buffer      = 0.0
        self.wall_stick_timer = 0.0
        self._ground_y        = self.y

        self.is_dashing           = False
        self.dash_timer           = 0.0
        self.dash_cooldown_timer  = 0.0
        self.dash_dir             = 1
        self.can_dash             = True
        self.ghosts               = []
        self._ghost_spawn_timer   = 0.0
        self._ghost_spawn_interval = DASH_DURATION / max(1, DASH_GHOST_COUNT)
        
        self.is_hooking = False
        self.hook_point = None
        self.hook_length = 0.0

    @property
    def rect(self):
        return pygame.Rect(int(self.x - self.w / 2), int(self.y - self.h / 2), self.w, self.h)

    def _play_sfx(self, name):
        if self.audio:
            self.audio.play_sfx(name)

    def update(self, dt, keys, solid_rects, bounce_rects=None):
        if dt > 0.033:
            dt = 0.033

        if self.dash_cooldown_timer > 0:
            self.dash_cooldown_timer = max(0, self.dash_cooldown_timer - dt)

        if self.on_ground:
            self.can_dash = True

        for ghost in self.ghosts:
            ghost.update(dt)
        self.ghosts = [g for g in self.ghosts if g.alive]

        if not pygame.mouse.get_pressed()[0]:
            self.is_hooking = False

        if self.is_hooking and self.hook_point:
            hx, hy = self.hook_point
            dx = self.x - hx
            dy = self.y - hy
            dist = math.hypot(dx, dy)
            
            if dist > self.hook_length:
                ratio = self.hook_length / max(0.1, dist)
                self.x = hx + dx * ratio
                self.y = hy + dy * ratio
                
                nx = dx / max(0.1, dist)
                ny = dy / max(0.1, dist)
                dot = self.vx * nx + self.vy * ny
                self.vx -= dot * nx
                self.vy -= dot * ny
                
            if keys[pygame.K_w]:
                self.hook_length = max(20.0, self.hook_length - 200 * dt)
            if keys[pygame.K_s]:
                self.hook_length = min(800.0, self.hook_length + 200 * dt)
                
            self.vy += GRAVITY * dt
            if self.vy > MAX_FALL_SPEED: self.vy = MAX_FALL_SPEED
            
            move_x = 0
            if keys[pygame.K_a]: move_x -= 1
            if keys[pygame.K_d]: move_x += 1
            if move_x != 0:
                self.vx += move_x * 800 * dt
                self.facing = move_x
                
            self.x += self.vx * dt
            self._collide_x(solid_rects)
            self.y += self.vy * dt
            self._collide_y(solid_rects, bounce_rects)
            
            self._update_animation(dt, move_x)
            self.on_ground = False
            return

        if self.is_dashing:
            self.dash_timer         -= dt
            self._ghost_spawn_timer -= dt
            if self._ghost_spawn_timer <= 0:
                self._ghost_spawn_timer = self._ghost_spawn_interval
                sprite = self.animator.current_surface
                if sprite:
                    self.ghosts.append(Ghost(self.x, self.y, sprite, self.sprite_w, self.sprite_h, self.h))

            self.vx = self.dash_dir * DASH_SPEED
            self.vy = 0.0

            if self.dash_timer <= 0:
                self.is_dashing = False
                self.vx = self.dash_dir * PLAYER_SPEED * 0.5

            self.x += self.vx * dt
            self._collide_x(solid_rects)
            self._check_still_grounded(solid_rects)
            self._update_animation(dt, self.dash_dir)
            return

        move_x = 0
        if keys[pygame.K_a]: move_x -= 1
        if keys[pygame.K_d]: move_x += 1
        if move_x != 0: self.facing = move_x

        target_vx = move_x * PLAYER_SPEED
        if self.on_ground:
            if move_x == 0:
                self.vx *= 0.65
                if abs(self.vx) < 1.0: self.vx = 0.0
            else:
                self.vx += (target_vx - self.vx) * min(1.0, 15.0 * dt)
        else:
            self.vx += (target_vx - self.vx) * min(1.0, 8.0 * dt)
        self.vx = max(-PLAYER_SPEED, min(PLAYER_SPEED, self.vx))

        if not self.on_ground:
            if self.on_wall and self.vy > 0 and move_x != 0:
                self.vy += GRAVITY * 0.25 * dt
                if self.vy > WALL_SLIDE_SPEED: self.vy = WALL_SLIDE_SPEED
            else:
                self.vy += GRAVITY * dt
                if self.vy > MAX_FALL_SPEED: self.vy = MAX_FALL_SPEED
        else:
            self.vy = 0.0

        if self.on_ground:
            self.coyote_timer = COYOTE_TIME
        else:
            self.coyote_timer -= dt

        self.jump_buffer -= dt
        if self.jump_buffer > 0: self._try_jump()

        if self.on_wall and not self.on_ground:
            self.wall_stick_timer -= dt
        else:
            self.wall_stick_timer = WALL_STICK_TIME

        was_on_ground = self.on_ground

        if self.vx != 0.0:
            self.x += self.vx * dt
            self._collide_x(solid_rects)

        if self.vy != 0.0:
            self.on_ground = False
            self.y        += self.vy * dt
            self._collide_y(solid_rects, bounce_rects)
        else:
            self._check_still_grounded(solid_rects)

        self.on_wall  = False
        self.wall_dir = 0
        if not self.on_ground:
            self._check_walls(solid_rects)

        if not was_on_ground and self.on_ground:
            self._on_land()

        if self.on_ground and self.vx == 0.0:
            self.x = round(self.x)
            self.y = self._ground_y

        if self.y > 8000:
            self.y  = 200.0
            self.vy = 0.0

        self._update_animation(dt, move_x)

    def handle_jump_press(self):
        if self.is_dashing: return
        self.jump_buffer = JUMP_BUFFER_TIME
        self._try_jump()

    def handle_dash_press(self):
        if self.is_dashing or self.dash_cooldown_timer > 0 or not self.can_dash:
            return
        self.is_dashing          = True
        self.dash_timer          = DASH_DURATION
        self.dash_cooldown_timer = DASH_COOLDOWN
        self.dash_dir            = self.facing
        self.can_dash            = False
        self.vy                  = 0.0
        self.vx                  = self.dash_dir * DASH_SPEED
        self._ghost_spawn_timer  = 0.0
        self._play_sfx("dash")
        sprite = self.animator.current_surface
        if sprite:
            self.ghosts.append(Ghost(self.x, self.y, sprite, self.sprite_w, self.sprite_h, self.h))

    def handle_hook_press(self, mouse_pos, solid_rects, cam_x, cam_y, can_hook):
        if not can_hook or self.is_dashing: return
        mx, my = mouse_pos
        world_x = mx + cam_x
        world_y = my + cam_y
        
        px, py = self.x, self.y
        dx = world_x - px
        dy = world_y - py
        dist = math.hypot(dx, dy)
        
        if dist > 800:
            return
            
        steps = int(dist / 10)
        for i in range(steps):
            t = i / max(1, steps)
            cx = px + dx * t
            cy = py + dy * t
            for r in solid_rects:
                if r.collidepoint(cx, cy):
                    self.is_hooking = True
                    self.hook_point = (cx, cy)
                    self.hook_length = math.hypot(cx - px, cy - py)
                    self._play_sfx("dash")
                    return

    def check_portal_proximity(self, portal_rects):
        expanded = self.rect.inflate(INTERACT_RANGE * 2, INTERACT_RANGE * 2)
        for portal in portal_rects:
            if expanded.colliderect(portal):
                self.near_portal = True
                return True
        self.near_portal = False
        return False

    def _try_jump(self):
        if self.on_wall and not self.on_ground and self.wall_dir != 0:
            self._wall_jump(); self.jump_buffer = 0
        elif self.coyote_timer > 0 and self.jumps_left >= self.max_jumps:
            self._ground_jump(); self.jump_buffer = 0
        elif self.jumps_left > 0 and not self.on_ground and self.coyote_timer <= 0:
            self._air_jump(); self.jump_buffer = 0

    def _ground_jump(self):
        self.vy = JUMP_FORCE; self.on_ground = False
        self.coyote_timer = 0.0; self.jumps_left = self.max_jumps - 1
        self._play_sfx("jump")

    def _air_jump(self):
        self.vy = DOUBLE_JUMP_FORCE; self.jumps_left -= 1
        self._play_sfx("double_jump")

    def _wall_jump(self):
        self.vx = -self.wall_dir * WALL_JUMP_FORCE_X
        self.vy = WALL_JUMP_FORCE_Y
        self.facing = -self.wall_dir
        self.jumps_left = self.max_jumps - 1; self.on_wall = False; self.coyote_timer = 0.0
        self._play_sfx("wall_jump")

    def _on_land(self):
        self.jumps_left = self.max_jumps
        self._play_sfx("land")

    def _collide_x(self, solid_rects):
        pr = self.rect
        for wall in solid_rects:
            if pr.colliderect(wall):
                if self.vx > 0:   self.x = wall.left  - self.w / 2
                elif self.vx < 0: self.x = wall.right + self.w / 2
                self.vx = 0.0
                if self.is_dashing: self.is_dashing = False
                pr = self.rect

    def _collide_y(self, solid_rects, bounce_rects=None):
        pr = self.rect
        for wall in solid_rects:
            if pr.colliderect(wall):
                if self.vy > 0:
                    if bounce_rects and wall in bounce_rects:
                        self.y = wall.top - self.h / 2
                        self.vy = BOUNCE_FORCE
                        self.on_ground = False
                        self._play_sfx("jump")
                    else:
                        self.y = wall.top - self.h / 2
                        self.vy = 0.0; self.on_ground = True; self._ground_y = self.y
                elif self.vy < 0:
                    self.y = wall.bottom + self.h / 2; self.vy = 0.0
                pr = self.rect

    def _check_still_grounded(self, solid_rects):
        feet = pygame.Rect(int(self.x - self.w / 2) + 2, int(self.y + self.h / 2), self.w - 4, 2)
        for wall in solid_rects:
            if feet.colliderect(wall):
                self.on_ground = True; self.vy = 0.0; return
        self.on_ground = False

    def _check_walls(self, solid_rects):
        margin = 4
        r_box = pygame.Rect(int(self.x + self.w / 2),          int(self.y - self.h / 2 + 4), margin, self.h - 8)
        l_box = pygame.Rect(int(self.x - self.w / 2 - margin), int(self.y - self.h / 2 + 4), margin, self.h - 8)
        for wall in solid_rects:
            if r_box.colliderect(wall): self.on_wall = True; self.wall_dir = 1;  return
        for wall in solid_rects:
            if l_box.colliderect(wall): self.on_wall = True; self.wall_dir = -1; return

    def _update_animation(self, dt, move_x):
        if self.on_wall and not self.on_ground:
            state = "idle_left" if self.wall_dir == 1 else "idle_right"
        elif move_x < 0: state = "walk_left"
        elif move_x > 0: state = "walk_right"
        else:            state = "idle_left" if self.facing < 0 else "idle_right"
        self.animator.set_state(state)
        self.animator.update(dt)

    def draw(self, surface, cam_x, cam_y):
        if self.is_hooking and self.hook_point:
            hx, hy = self.hook_point
            pygame.draw.line(surface, (220, 220, 220), (int(self.x - cam_x), int(self.y - cam_y)), (int(hx - cam_x), int(hy - cam_y)), 2)

        for ghost in self.ghosts:
            ghost.draw(surface, cam_x, cam_y)

        sprite = self.animator.current_surface
        if sprite is None:
            pygame.draw.rect(surface, (255, 0, 255), self.rect.move(-cam_x, -cam_y))
            return

        draw_x = int(self.x - self.sprite_w / 2 - cam_x)
        draw_y = int((self.y + self.h / 2) - self.sprite_h - cam_y)

        shadow_w = max(10, int(self.w * 0.8))
        sh_surf  = pygame.Surface((shadow_w, 6), pygame.SRCALPHA)
        pygame.draw.ellipse(sh_surf, (0, 0, 0, 50), (0, 0, shadow_w, 6))
        surface.blit(sh_surf, (int(self.x - shadow_w / 2 - cam_x), int(self.y + self.h / 2 - cam_y - 2)))

        surface.blit(sprite, (draw_x, draw_y))

        total   = self.max_jumps
        spacing = 14
        sx      = self.x - cam_x - ((total - 1) * spacing) / 2
        dy      = draw_y - 10
        for i in range(total):
            dx = int(sx + i * spacing)
            d  = int(dy)
            if i < self.jumps_left:
                pygame.draw.circle(surface, (40, 180, 220),  (dx, d), 5)
                pygame.draw.circle(surface, (120, 230, 255), (dx, d), 3)
                pygame.draw.circle(surface, (255, 255, 255), (dx, d), 1)
            else:
                pygame.draw.circle(surface, (50, 50, 65), (dx, d), 5)
                pygame.draw.circle(surface, (35, 35, 45), (dx, d), 3)

        if self.dash_cooldown_timer > 0:
            bw, bh = 24, 3
            bx     = int(self.x - cam_x - bw / 2)
            by     = int(dy - 10)
            fw     = int(bw * (1.0 - self.dash_cooldown_timer / DASH_COOLDOWN))
            pygame.draw.rect(surface, (40, 40, 55), (bx, by, bw, bh))
            if fw > 0:
                pygame.draw.rect(surface, (80, 200, 255), (bx, by, fw, bh))
        elif self.can_dash:
            dx2  = int(self.x - cam_x)
            dy2  = int(dy - 10)
            pts  = [(dx2, dy2 - 3), (dx2 + 3, dy2), (dx2, dy2 + 3), (dx2 - 3, dy2)]
            pygame.draw.polygon(surface, (80, 200, 255), pts)

        if self.on_wall and not self.on_ground and self.vy > 0:
            ix = int(self.x + self.wall_dir * (self.w / 2 + 4) - cam_x)
            for i in range(3):
                s = pygame.Surface((3, 6), pygame.SRCALPHA)
                s.fill((255, 255, 255, 80))
                surface.blit(s, (ix, int(self.y - self.h / 4 + i * 12 - cam_y)))