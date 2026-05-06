import sys
import os
import math
import random
import pygame

from settings import (
    SCREEN_W, SCREEN_H, TILE_SIZE, BACKGROUND,
    COR_COLLECT_RANGE, COR_REQUIRED_LEVELS,
    COR_FLOAT_SPEED, COR_FLOAT_HEIGHT,
    UI_TEXT, UI_TEXT_DIM, UI_HIGHLIGHT,
)
from tilemap import TileMap
from player import Player, SpriteSheet, FallbackSpriteSheet
from audio import AudioManager
from dialog import SignManager


# ══════════════════════════════════════════════
# LOADING SCREEN
# ══════════════════════════════════════════════

class LoadingScreen:
    """
    Black screen with floating logo.
    mode="startup"  — longer display, fade out
    mode="level"    — shorter display, fade out
    """

    def __init__(self, screen, clock):
        self.screen = screen
        self.clock  = clock
        self.logo   = None

        logo_path = r"C:\Users\PC\Desktop\PocketUPians\assets\logo\logo.png"
        if os.path.exists(logo_path):
            try:
                raw = pygame.image.load(logo_path).convert_alpha()
                iw, ih = raw.get_width(), raw.get_height()
                target_h = 220
                target_w = int(iw * (target_h / ih))
                max_w = int(SCREEN_W * 0.70)
                if target_w > max_w:
                    target_w = max_w
                    target_h = int(ih * (max_w / iw))
                self.logo = pygame.transform.smoothscale(raw, (target_w, target_h))
            except pygame.error:
                pass

    def run(self, mode="startup", level_name=""):
        """
        Show loading screen.
        mode="startup" — 2.5s show + fade
        mode="level"   — 1.0s show + fade, shows level name
        """
        if mode == "startup":
            show_duration = 2.5
            fade_speed    = 300
            text_below    = "Loading"
        else:
            show_duration = 1.0
            fade_speed    = 500
            text_below    = f"Loading {level_name}" if level_name else "Loading"

        timer = 0.0
        phase = "show"
        alpha = 255.0

        font_loading = pygame.font.SysFont("consolas", 18)
        font_level   = pygame.font.SysFont("consolas", 24, bold=True)

        while True:
            dt = self.clock.tick(60) / 1000.0
            if dt > 0.05:
                dt = 0.05

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                # Skip on any key/click for startup only
                if mode == "startup":
                    if event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
                        return

            timer += dt

            if phase == "show":
                if timer >= show_duration:
                    phase = "fade"
                    timer = 0.0
            elif phase == "fade":
                alpha -= fade_speed * dt
                if alpha <= 0:
                    return

            # Draw
            self.screen.fill((0, 0, 0))

            bob = int(math.sin(timer * 2.0) * 8)

            if self.logo:
                lx = SCREEN_W // 2 - self.logo.get_width() // 2
                ly = SCREEN_H // 2 - self.logo.get_height() // 2 + bob - 20

                logo_copy = self.logo.copy()
                if phase == "fade":
                    logo_copy.set_alpha(max(0, int(alpha)))

                self.screen.blit(logo_copy, (lx, ly))
                text_y = ly + self.logo.get_height() + 20
            else:
                fallback = font_level.render("POCKETUPIANS", True, UI_HIGHLIGHT)
                if phase == "fade":
                    fallback.set_alpha(max(0, int(alpha)))
                fx = SCREEN_W // 2 - fallback.get_width() // 2
                fy = SCREEN_H // 2 - fallback.get_height() // 2 + bob
                self.screen.blit(fallback, (fx, fy))
                text_y = fy + fallback.get_height() + 20

            # Loading text with animated dots
            dots = "." * (int(timer * 3) % 4)
            loading_text = font_loading.render(f"{text_below}{dots}", True, (120, 120, 140))
            if phase == "fade":
                loading_text.set_alpha(max(0, int(alpha)))
            self.screen.blit(loading_text, (SCREEN_W // 2 - loading_text.get_width() // 2, text_y))

            # Level name display for level loading
            if mode == "level" and level_name:
                name_text = font_level.render(level_name, True, (180, 180, 200))
                if phase == "fade":
                    name_text.set_alpha(max(0, int(alpha)))
                self.screen.blit(name_text, (SCREEN_W // 2 - name_text.get_width() // 2, text_y + 30))

            pygame.display.flip()


# ══════════════════════════════════════════════
# MENU
# ══════════════════════════════════════════════

class MenuParticle:
    def __init__(self):
        self.reset()
        self.y = random.uniform(0, SCREEN_H)

    def reset(self):
        self.x     = random.uniform(0, SCREEN_W)
        self.y     = SCREEN_H + 20
        self.size  = random.uniform(2, 5)
        self.speed = random.uniform(20, 55)
        self.alpha = random.randint(25, 90)
        self.sway  = random.uniform(0.4, 1.8)
        self.phase = random.uniform(0, math.pi * 2)

    def update(self, dt):
        self.y -= self.speed * dt
        self.x += math.sin(pygame.time.get_ticks() * 0.001 * self.sway + self.phase) * 0.4
        if self.y < -20:
            self.reset()

    def draw(self, surface):
        r = int(self.size)
        if r < 1:
            return
        s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (255, 255, 255, self.alpha), (r, r), r)
        surface.blit(s, (int(self.x - r), int(self.y - r)))


class Button:
    def __init__(self, x, y, w, h, text, font, action):
        self.rect = pygame.Rect(x, y, w, h)
        self.text, self.font, self.action = text, font, action
        self.hovered, self.pressed = False, False
        self.hover_t, self.press_t = 0.0, 0.0

    def update(self, dt, mp):
        self.hovered = self.rect.collidepoint(mp)
        self.hover_t += ((1.0 if self.hovered else 0.0) - self.hover_t) * 10 * dt
        if self.press_t > 0:
            self.press_t = max(0.0, self.press_t - dt * 5)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.hovered:
            self.pressed, self.press_t = True, 1.0
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.pressed and self.hovered:
                self.pressed = False
                return self.action
            self.pressed = False
        return None

    def draw(self, surface):
        cn, ch, cp = (60, 60, 80), (80, 80, 110), (40, 40, 60)
        cg, cb = UI_HIGHLIGHT, (100, 100, 130)
        t = self.hover_t
        bg = cp if self.press_t > 0 else tuple(int(cn[i] + (ch[i] - cn[i]) * t) for i in range(3))
        if t > 0.05:
            gr = self.rect.inflate(20, 20)
            gs = pygame.Surface((gr.w, gr.h), pygame.SRCALPHA)
            pygame.draw.rect(gs, (*cg, int(40 * t)), (0, 0, gr.w, gr.h), border_radius=16)
            surface.blit(gs, gr.topleft)
        pygame.draw.rect(surface, bg, self.rect, border_radius=10)
        bc = tuple(int(cb[i] + (cg[i] - cb[i]) * t) for i in range(3))
        pygame.draw.rect(surface, bc, self.rect, 2, border_radius=10)
        ts = self.font.render(self.text, True, (220, 220, 220))
        surface.blit(ts, (self.rect.centerx - ts.get_width() // 2,
                          self.rect.centery - ts.get_height() // 2 + int(2 * self.press_t)))


class MainMenu:
    def __init__(self, preview_sprite=None, audio=None, instant=False, max_unlocked=0):
        self.audio = audio
        self.font_title  = pygame.font.SysFont("consolas", 72, bold=True)
        self.font_sub    = pygame.font.SysFont("consolas", 18)
        self.font_button = pygame.font.SysFont("consolas", 28, bold=True)
        self.font_hint   = pygame.font.SysFont("consolas", 16)
        self.bg_particles = [MenuParticle() for _ in range(30)]

        logo_path = r"C:\Users\PC\Desktop\PocketUPians\assets\logo\logo.png"
        self.logo = None
        self.logo_alpha = 255.0 if instant else 0.0
        if os.path.exists(logo_path):
            try:
                raw = pygame.image.load(logo_path).convert_alpha()
                iw, ih = raw.get_width(), raw.get_height()
                target_h = 180
                target_w = int(iw * (target_h / ih))
                max_w = int(SCREEN_W * 0.75)
                if target_w > max_w:
                    target_w = max_w
                    target_h = int(ih * (max_w / iw))
                self.logo = pygame.transform.smoothscale(raw, (target_w, target_h))
            except pygame.error:
                pass

        self.preview_sprite = None
        if preview_sprite:
            try:
                th = 90
                sc = th / preview_sprite.get_height()
                self.preview_sprite = pygame.transform.smoothscale(
                    preview_sprite,
                    (int(preview_sprite.get_width() * sc), int(preview_sprite.get_height() * sc)),
                )
            except pygame.error:
                self.preview_sprite = preview_sprite

        logo_h    = self.logo.get_height() if self.logo else 80
        sub_h     = self.font_sub.get_height()
        preview_h = self.preview_sprite.get_height() if self.preview_sprite else 80
        btn_h     = 50
        gap       = 12

        total = logo_h + gap + sub_h + gap + preview_h + gap + btn_h + gap + btn_h
        start_y = max(15, (SCREEN_H - total - 50) // 2)

        self.logo_y      = start_y
        self.subtitle_y  = self.logo_y + logo_h + gap
        self.preview_y   = self.subtitle_y + sub_h + gap + preview_h // 2
        buttons_top      = self.subtitle_y + sub_h + gap + preview_h + gap

        if buttons_top + btn_h * 4 + gap * 3 > SCREEN_H - 45:
            buttons_top = SCREEN_H - 45 - btn_h * 4 - gap * 3

        bw = 240
        bx = SCREEN_W // 2 - bw // 2
        self.buttons = [
            Button(bx, buttons_top, bw, btn_h, "RESUME", self.font_button, "resume"),
            Button(bx, buttons_top + btn_h + gap, bw, btn_h, "NEW GAME", self.font_button, "new_game"),
            Button(bx, buttons_top + 2 * (btn_h + gap), bw, btn_h, "LEVELS", self.font_button, "levels"),
            Button(bx, buttons_top + 3 * (btn_h + gap), bw, btn_h, "QUIT", self.font_button, "quit")
        ]

        self.title_bob     = 0.0
        self.preview_bob   = 0.0
        self.title_alpha   = 255.0 if instant else 0.0
        self.fade_alpha    = 0.0 if instant else 255.0
        self.fade_in_done  = instant
        self.fading_out    = False
        self.fade_out_done = False
        self.pending_action = None

    def update(self, dt):
        mp = pygame.mouse.get_pos()
        for p in self.bg_particles:
            p.update(dt)
        for btn in self.buttons:
            btn.update(dt, mp)
        self.title_bob   += dt * 2.5
        self.preview_bob  = self.title_bob
        self.title_alpha  = min(255.0, self.title_alpha + dt * 220)
        self.logo_alpha   = self.title_alpha
        if not self.fade_in_done:
            self.fade_alpha -= dt * 400
            if self.fade_alpha <= 0:
                self.fade_alpha, self.fade_in_done = 0.0, True
        if self.fading_out:
            self.fade_alpha += dt * 400
            if self.fade_alpha >= 255:
                self.fade_alpha, self.fade_out_done = 255.0, True

    def handle_event(self, event):
        if self.fading_out:
            return None
        for btn in self.buttons:
            action = btn.handle_event(event)
            if action:
                if self.audio:
                    self.audio.play_sfx("click")
                if action == "quit":
                    return "quit"
                if action in ("new_game", "resume", "levels"):
                    self.fading_out, self.pending_action = True, action
                    return action if action == "levels" else None
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                if self.audio:
                    self.audio.play_sfx("click")
                act = self.buttons[0].action
                self.fading_out, self.pending_action = True, act
                return act if act == "levels" else None
            elif event.key == pygame.K_ESCAPE:
                return "quit"
        return None

    def is_done(self):
        return (True, self.pending_action) if self.fade_out_done else (False, None)

    def draw(self, surface):
        for y in range(SCREEN_H):
            t = y / SCREEN_H
            surface.fill((int(20 + 15 * t), int(20 + 15 * t), int(30 + 20 * t)), (0, y, SCREEN_W, 1))
        for p in self.bg_particles:
            p.draw(surface)

        bob = int(math.sin(self.preview_bob) * 4)
        ly = self.logo_y + bob

        if self.logo:
            lc = self.logo.copy()
            lc.set_alpha(int(self.logo_alpha))
            surface.blit(lc, (SCREEN_W // 2 - lc.get_width() // 2, ly))
            actual_bottom = ly + lc.get_height()
        else:
            ts = self.font_title.render("POCKETUPIANS", True, UI_HIGHLIGHT)
            ts.set_alpha(int(self.title_alpha))
            surface.blit(ts, (SCREEN_W // 2 - ts.get_width() // 2, ly))
            actual_bottom = ly + ts.get_height()

        sub_y = actual_bottom + 10
        ss = self.font_sub.render("A PyGame Adventure", True, UI_TEXT_DIM)
        ss.set_alpha(int(self.title_alpha * 0.8))
        surface.blit(ss, (SCREEN_W // 2 - ss.get_width() // 2, sub_y))

        cx = SCREEN_W // 2
        cy = self.preview_y + bob
        if self.preview_sprite:
            pw, ph = self.preview_sprite.get_width(), self.preview_sprite.get_height()
            sw = int(pw * 0.5)
            sh = pygame.Surface((sw, 6), pygame.SRCALPHA)
            pygame.draw.ellipse(sh, (0, 0, 0, 40), (0, 0, sw, 6))
            surface.blit(sh, (cx - sw // 2, cy + ph // 2 + 6))
            surface.blit(self.preview_sprite, (cx - pw // 2, cy - ph // 2))
        else:
            r = pygame.Rect(cx - 25, cy - 35, 50, 70)
            pygame.draw.rect(surface, (0, 200, 120), r, border_radius=8)
            pygame.draw.rect(surface, (0, 100, 60), r, 2, border_radius=8)

        for btn in self.buttons:
            btn.draw(surface)

        hs = self.font_hint.render("Press ENTER to start  |  ESC to quit", True, UI_TEXT_DIM)
        surface.blit(hs, (SCREEN_W // 2 - hs.get_width() // 2, SCREEN_H - 30))

        if self.fade_alpha > 0:
            ov = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            ov.fill((0, 0, 0, int(self.fade_alpha)))
            surface.blit(ov, (0, 0))


class LevelSelectMenu:
    def __init__(self, max_unlocked, audio=None):
        self.audio = audio
        self.font_title  = pygame.font.SysFont("consolas", 48, bold=True)
        self.font_button = pygame.font.SysFont("consolas", 24, bold=True)
        self.buttons = []
        
        bw, bh = 150, 50
        gap_x, gap_y = 20, 20
        cols = 5
        start_x = SCREEN_W // 2 - (cols * bw + (cols - 1) * gap_x) // 2
        start_y = 200
        
        for i in range(max_unlocked + 1):
            r = i // cols
            c = i % cols
            bx = start_x + c * (bw + gap_x)
            by = start_y + r * (bh + gap_y)
            self.buttons.append(Button(bx, by, bw, bh, f"Level {i+1}", self.font_button, f"level_{i}"))
            
        # Add back button
        self.buttons.append(Button(SCREEN_W // 2 - 100, SCREEN_H - 100, 200, 50, "BACK", self.font_button, "back"))
        self.bg_particles = [MenuParticle() for _ in range(30)]

    def update(self, dt):
        mp = pygame.mouse.get_pos()
        for p in self.bg_particles:
            p.update(dt)
        for btn in self.buttons:
            btn.update(dt, mp)

    def handle_event(self, event):
        for btn in self.buttons:
            action = btn.handle_event(event)
            if action:
                if self.audio:
                    self.audio.play_sfx("click")
                return action
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            return "back"
        return None

    def draw(self, surface):
        for y in range(SCREEN_H):
            t = y / SCREEN_H
            surface.fill((int(20 + 15 * t), int(20 + 15 * t), int(30 + 20 * t)), (0, y, SCREEN_W, 1))
        for p in self.bg_particles:
            p.draw(surface)
            
        ts = self.font_title.render("SELECT LEVEL", True, UI_HIGHLIGHT)
        surface.blit(ts, (SCREEN_W // 2 - ts.get_width() // 2, 80))
        
        for btn in self.buttons:
            btn.draw(surface)


class PauseMenu:
    def __init__(self, audio=None):
        self.audio = audio
        self.font_title  = pygame.font.SysFont("consolas", 48, bold=True)
        self.font_button = pygame.font.SysFont("consolas", 24, bold=True)
        bw, bh = 200, 50
        bx, by = SCREEN_W // 2 - bw // 2, SCREEN_H // 2 - 20
        self.buttons = [
            Button(bx, by, bw, bh, "RESUME", self.font_button, "resume"),
            Button(bx, by + 70, bw, bh, "MAIN MENU", self.font_button, "menu"),
            Button(bx, by + 140, bw, bh, "QUIT", self.font_button, "quit"),
        ]
        self.overlay_alpha, self.active = 0.0, False

    def show(self):
        self.active = True

    def hide(self):
        self.active, self.overlay_alpha = False, 0.0

    def update(self, dt):
        if not self.active:
            return
        self.overlay_alpha = min(180.0, self.overlay_alpha + dt * 600)
        for btn in self.buttons:
            btn.update(dt, pygame.mouse.get_pos())

    def handle_event(self, event):
        if not self.active:
            return None
        for btn in self.buttons:
            a = btn.handle_event(event)
            if a:
                if self.audio:
                    self.audio.play_sfx("click")
                return a
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            return "resume"
        return None

    def draw(self, surface):
        if not self.active:
            return
        ov = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        ov.fill((0, 0, 0, int(self.overlay_alpha)))
        surface.blit(ov, (0, 0))
        ts = self.font_title.render("PAUSED", True, UI_HIGHLIGHT)
        surface.blit(ts, (SCREEN_W // 2 - ts.get_width() // 2, SCREEN_H // 2 - 140))
        for btn in self.buttons:
            btn.draw(surface)


class Camera:
    def __init__(self):
        self.x, self.y, self.smooth = 0.0, 0.0, 5.0

    def update(self, player, tilemap, dt):
        lx = player.vx * 0.3 if abs(player.vx) > 10 else 0.0
        ly = player.vy * 0.15 if abs(player.vy) > 10 else 0.0
        self.x += (player.x + lx - SCREEN_W / 2 - self.x) * self.smooth * dt
        self.y += (player.y + ly - SCREEN_H / 2 - self.y) * self.smooth * dt
        self.x = max(0.0, min(self.x, float(max(0, tilemap.cols * TILE_SIZE - SCREEN_W))))
        self.y = max(0.0, min(self.y, float(max(0, tilemap.rows * TILE_SIZE - SCREEN_H))))
        self.x, self.y = round(self.x), round(self.y)


class LevelManager:
    def __init__(self, folder="maps"):
        self.folder, self.files, self.current_index = folder, [], 0
        self.max_unlocked = 0
        self._scan()
        self._load_save()

    def _load_save(self):
        try:
            import json
            with open("save_data.json", "r") as f:
                data = json.load(f)
                self.max_unlocked = data.get("max_unlocked", 0)
        except Exception:
            self.max_unlocked = 0

    def _save_progress(self):
        if self.current_index > self.max_unlocked:
            self.max_unlocked = self.current_index
        try:
            import json
            with open("save_data.json", "w") as f:
                json.dump({"max_unlocked": self.max_unlocked}, f)
        except Exception:
            pass

    def _scan(self):
        self.files.clear()
        if not os.path.exists(self.folder):
            return
        for f in sorted(os.listdir(self.folder)):
            if f.endswith(".txt"):
                self.files.append(os.path.join(self.folder, f))

    def reset(self):
        self.current_index = 0

    @property
    def total(self):
        return len(self.files)

    @property
    def name(self):
        return os.path.basename(self.files[self.current_index]) if self.files else "map_01.txt"

    def load_current(self):
        if self.files:
            return TileMap.load(self.files[self.current_index])
        layout = [
            "SSSSSSSSSSSSSSSSSSSS", "S..................S", "S..................S",
            "S.O................S", "S..................S", "S..................S",
            "S..................S", "S..................S", "S..................S",
            "S..G....G..R.G..X..S", "SSSSSSSSSSSSSSSSSSSS",
        ]
        return TileMap(max(len(r) for r in layout), len(layout), layout)

    def advance(self):
        if self.current_index > self.max_unlocked:
            self.max_unlocked = self.current_index
        if self.current_index < len(self.files) - 1:
            self.current_index += 1
            if self.current_index > self.max_unlocked:
                self.max_unlocked = self.current_index
            self._save_progress()
            return True
        self._save_progress()
        return False


class HUD:
    def __init__(self):
        self.font_large = pygame.font.SysFont("consolas", 24, bold=True)
        self.font_small = pygame.font.SysFont("consolas", 16)
        self.font_title = pygame.font.SysFont("consolas", 48, bold=True)
        self.font_cor   = pygame.font.SysFont("consolas", 18, bold=True)
        self.transition_alpha, self.transitioning = 0.0, False
        self.transition_phase, self.transition_speed = "none", 400.0
        self.on_mid = None
        self._ct, self._cs, self._cb = None, None, None
        self.blocked_msg, self.blocked_timer = "", 0.0

    def show_blocked(self, msg, duration=2.0):
        self.blocked_msg, self.blocked_timer = msg, duration

    def draw_level_info(self, surface, name, num, total):
        s  = self.font_small.render(f"Level {num}/{total}  -  {name}", True, UI_TEXT_DIM)
        bg = pygame.Surface((s.get_width() + 20, s.get_height() + 10), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 120))
        surface.blit(bg, (10, 10))
        surface.blit(s,  (20, 15))

    def draw_cor_counter(self, surface, collected, total):
        if total <= 0:
            return
        color = (80, 255, 80) if collected >= total else (255, 220, 80)
        s  = self.font_cor.render(f"COR: {collected}/{total}", True, color)
        bg = pygame.Surface((s.get_width() + 16, s.get_height() + 8), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 120))
        surface.blit(bg, (10, 40))
        surface.blit(s,  (18, 44))

    def draw_controls(self, surface):
        lines = ["A / D   Move", "SPACE   Jump", "Q       Dash",
                 "F       Collect", "ENTER   Interact", "ESC     Pause"]
        y = SCREEN_H - 24 * len(lines) - 10
        for line in lines:
            s  = self.font_small.render(line, True, UI_TEXT_DIM)
            bg = pygame.Surface((s.get_width() + 10, s.get_height() + 4), pygame.SRCALPHA)
            bg.fill((0, 0, 0, 80))
            surface.blit(bg, (SCREEN_W - s.get_width() - 20, y))
            surface.blit(s,  (SCREEN_W - s.get_width() - 15, y + 2))
            y += 22

    def draw_player_state(self, surface, player):
        parts = []
        if player.on_ground: parts.append("GROUND")
        if player.on_wall:   parts.append(f"WALL ({'L' if player.wall_dir == -1 else 'R'})")
        if not player.on_ground and not player.on_wall: parts.append("AIR")
        parts.append(f"Jumps:{player.jumps_left}")
        if player.is_dashing: parts.append("DASH")
        elif player.dash_cooldown_timer > 0: parts.append(f"CD:{player.dash_cooldown_timer:.1f}")
        else: parts.append("DASH:OK")
        text = "  |  ".join(parts)
        if text != self._ct:
            self._ct = text
            self._cs = self.font_small.render(text, True, UI_TEXT_DIM)
            self._cb = pygame.Surface((self._cs.get_width() + 10, self._cs.get_height() + 4), pygame.SRCALPHA)
            self._cb.fill((0, 0, 0, 80))
        surface.blit(self._cb, (10, SCREEN_H - 30))
        surface.blit(self._cs, (15, SCREEN_H - 28))

    def draw_blocked_message(self, surface, dt):
        if self.blocked_timer <= 0:
            return
        self.blocked_timer = max(0.0, self.blocked_timer - dt)
        alpha = min(255, int(self.blocked_timer * 255))
        if alpha <= 0:
            return
        s  = self.font_large.render(self.blocked_msg, True, (255, 80, 80))
        bg = pygame.Surface((s.get_width() + 30, s.get_height() + 16), pygame.SRCALPHA)
        bg.fill((0, 0, 0, min(alpha, 150)))
        bg.blit(s, (15, 8))
        bg.set_alpha(alpha)
        surface.blit(bg, (SCREEN_W // 2 - bg.get_width() // 2, SCREEN_H // 2 - 60))

    def draw_complete(self, surface):
        s  = self.font_title.render("All Levels Complete!", True, UI_HIGHLIGHT)
        s2 = self.font_large.render("Press ENTER to return to menu", True, UI_TEXT)
        surface.blit(s,  (SCREEN_W // 2 - s.get_width()  // 2, SCREEN_H // 2 - s.get_height() // 2))
        surface.blit(s2, (SCREEN_W // 2 - s2.get_width() // 2, SCREEN_H // 2 + 40))

    def start_transition(self, cb):
        self.transitioning, self.transition_phase = True, "fade_out"
        self.transition_alpha, self.on_mid = 0.0, cb

    def update_transition(self, dt):
        if not self.transitioning:
            return False
        if self.transition_phase == "fade_out":
            self.transition_alpha += self.transition_speed * dt
            if self.transition_alpha >= 255:
                self.transition_alpha, self.transition_phase = 255.0, "fade_in"
                if self.on_mid:
                    self.on_mid()
                    self.on_mid = None
        elif self.transition_phase == "fade_in":
            self.transition_alpha -= self.transition_speed * dt
            if self.transition_alpha <= 0:
                self.transition_alpha, self.transition_phase, self.transitioning = 0.0, "none", False
        return True

    def draw_transition(self, surface):
        if self.transitioning and self.transition_alpha > 0:
            ov = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            ov.fill((0, 0, 0, int(self.transition_alpha)))
            surface.blit(ov, (0, 0))


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("PocketUPians")

        icon_path = os.path.join("assets", "logo", "game_logo.png")
        if os.path.exists(icon_path):
            pygame.display.set_icon(pygame.image.load(icon_path).convert_alpha())

        self.clock = pygame.time.Clock()

        # Loading screen — shared instance
        self.loading_screen = LoadingScreen(self.screen, self.clock)

        # Show startup loading screen
        self.loading_screen.run(mode="startup")

        self.audio = AudioManager()
        self.sprite_sheet = self._load_sprite_sheet()
        preview = self.sprite_sheet.right_frames[0] if self.sprite_sheet else None

        self.level_mgr = LevelManager("maps")

        self.state      = "menu"
        self.main_menu  = MainMenu(preview_sprite=preview, audio=self.audio, instant=False, max_unlocked=self.level_mgr.max_unlocked)
        self.level_select_menu = LevelSelectMenu(self.level_mgr.max_unlocked, audio=self.audio)
        self.pause_menu = PauseMenu(audio=self.audio)
        self.audio.play_music("menu")

        self.tilemap      = None
        self.solid_rects  = None
        self.portal_rects = None
        self.bounce_rects = None
        self.player       = None
        self.camera       = None
        self.hud          = None
        self.sign_mgr     = None
        self.paused       = False
        self.all_complete = False
        self.cors_total     = 0
        self.cors_collected = 0
        self.near_cor       = False
        self.nearby_cor     = None
        self.near_key       = False
        self.nearby_key     = None
        self.keys_total     = 0
        self.keys_collected = 0

    def _load_sprite_sheet(self):
        image_path = "character.jpg"
        if not os.path.exists(image_path):
            image_path = os.path.join("assets", "character", "character.jpg")
        jsn     = "character_animation_frames.json"
        alt_dir = os.path.join(os.path.expanduser("~"), ".gemini", "tmp", "project")
        if not os.path.exists(image_path) and os.path.exists(os.path.join(alt_dir, "character.jpg")):
            image_path = os.path.join(alt_dir, "character.jpg")
        if not os.path.exists(jsn) and os.path.exists(os.path.join(alt_dir, "character_animation_frames.json")):
            jsn = os.path.join(alt_dir, "character_animation_frames.json")
        try:
            return SpriteSheet(image_path, jsn)
        except FileNotFoundError as e:
            print(f"Warning: {e}\nUsing placeholder.")
            return None

    def start_game(self, new_game=False):
        self.state, self.paused, self.all_complete = "playing", False, False
        if new_game:
            self.level_mgr.reset()
        self.camera   = Camera()
        self.hud      = HUD()
        self.sign_mgr = SignManager(audio=self.audio)
        self._load_level()
        self.audio.play_music("level")

    def _load_level(self):
        # Show level loading screen
        level_name = self.level_mgr.name
        self.loading_screen.run(mode="level", level_name=level_name)

        self.tilemap      = self.level_mgr.load_current()
        self.solid_rects  = self.tilemap.get_solid_rects()
        self.portal_rects = self.tilemap.get_tiles_of_type("X")
        self.bounce_rects = self.tilemap.get_tiles_of_type("U")
        sheet = self.sprite_sheet if self.sprite_sheet else FallbackSpriteSheet()
        spawn = self.tilemap.find_spawn_point()
        
        max_jumps = 3 if self.level_mgr.current_index >= 7 else 2
        self.player = Player(spawn[0], spawn[1], sheet, self.audio, max_jumps=max_jumps)
        self.camera.x = round(self.player.x - SCREEN_W / 2)
        self.camera.y = round(self.player.y - SCREEN_H / 2)
        if self.sign_mgr:
            self.sign_mgr.load_signs(self.tilemap, level_name)
        self.cors_total     = len(self.tilemap.get_cor_positions())
        self.cors_collected = 0
        self.near_cor       = False
        self.nearby_cor     = None
        self.keys_total     = len(self.tilemap.get_tiles_of_type("K"))
        self.keys_collected = 0
        self.near_key       = False
        self.nearby_key     = None

    def _advance_level(self):
        if self.level_mgr.advance():
            self._load_level()
        else:
            self.all_complete = True
            self.audio.play_music("victory", loops=0)

    def _check_cor_proximity(self):
        pr = self.player.rect.inflate(COR_COLLECT_RANGE, COR_COLLECT_RANGE)
        self.near_cor, self.nearby_cor = False, None
        pcx, pcy = self.player.rect.center
        best = float("inf")
        for col, row, rect in self.tilemap.get_cor_positions():
            if pr.colliderect(rect):
                d = (rect.centerx - pcx) ** 2 + (rect.centery - pcy) ** 2
                if d < best:
                    best = d
                    self.near_cor, self.nearby_cor = True, (col, row)

    def _check_key_proximity(self):
        pr = self.player.rect.inflate(COR_COLLECT_RANGE, COR_COLLECT_RANGE)
        self.near_key, self.nearby_key = False, None
        pcx, pcy = self.player.rect.center
        best = float("inf")
        for r in range(self.tilemap.rows):
            for c in range(self.tilemap.cols):
                if (c, r) in self.tilemap.collected_cors:
                    continue
                for layer in self.tilemap.layers:
                    if layer[r][c] == "K":
                        rect = pygame.Rect(c * TILE_SIZE, r * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                        if pr.colliderect(rect):
                            d = (rect.centerx - pcx) ** 2 + (rect.centery - pcy) ** 2
                            if d < best:
                                best = d
                                self.near_key, self.nearby_key = True, (c, r)
                        break

    def _collect_cor(self):
        if self.near_cor and self.nearby_cor:
            self.tilemap.collect_cor(*self.nearby_cor)
            self.cors_collected += 1
            self.audio.play_sfx("cor_collect")
            self.near_cor, self.nearby_cor = False, None
            print(f"  COR collected! ({self.cors_collected}/{self.cors_total})")
            return
        if self.near_key and self.nearby_key:
            self.tilemap.collect_cor(*self.nearby_key)
            self.keys_collected += 1
            self.audio.play_sfx("cor_collect")
            self.near_key, self.nearby_key = False, None
            print(f"  Key collected! ({self.keys_collected}/{self.keys_total})")
            return

    def _is_cor_required(self):
        return self.level_mgr.name in COR_REQUIRED_LEVELS

    def _all_cors_collected(self):
        return self.cors_total == 0 or self.cors_collected >= self.cors_total

    def _try_use_portal(self):
        if self._is_cor_required() and not self._all_cors_collected():
            remaining = self.cors_total - self.cors_collected
            self.hud.show_blocked(f"Collect all COR first! ({remaining} remaining)")
            return
        self.audio.play_sfx("portal")
        self.hud.start_transition(self._advance_level)

    def return_to_menu(self):
        self.state, self.paused, self.all_complete = "menu", False, False
        if self.pause_menu:
            self.pause_menu.hide()
        preview = self.sprite_sheet.right_frames[0] if self.sprite_sheet else None
        self.main_menu = MainMenu(preview_sprite=preview, audio=self.audio, instant=True, max_unlocked=self.level_mgr.max_unlocked)
        self.level_select_menu = LevelSelectMenu(self.level_mgr.max_unlocked, audio=self.audio)
        self.audio.play_music("menu")

    def run(self):
        running = True

        while running:
            dt = self.clock.tick(60) / 1000.0
            if dt > 0.033:
                dt = 0.033

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    continue

                if self.state == "menu":
                    a = self.main_menu.handle_event(event)
                    if a == "quit":
                        running = False
                    elif a == "levels":
                        self.state = "level_select"
                        self.main_menu.fading_out = False
                        self.main_menu.fade_alpha = 0
                
                elif self.state == "level_select":
                    a = self.level_select_menu.handle_event(event)
                    if a == "back":
                        self.state = "menu"
                    elif a is not None and a.startswith("level_"):
                        lvl_idx = int(a.split("_")[1])
                        self.level_mgr.current_index = lvl_idx
                        self.start_game()

                elif self.state == "playing":
                    if self.paused:
                        a = self.pause_menu.handle_event(event)
                        if a == "resume":
                            self.paused = False
                            self.pause_menu.hide()
                            self.audio.resume_music()
                        elif a == "menu":
                            self.return_to_menu()
                        elif a == "quit":
                            running = False

                    elif self.sign_mgr and self.sign_mgr.is_dialog_active:
                        if event.type == pygame.KEYDOWN:
                            if event.key == pygame.K_RETURN:
                                self.sign_mgr.interact()
                            elif event.key == pygame.K_ESCAPE:
                                self.sign_mgr.dialog.close()

                    else:
                        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                            if not self.hud.transitioning and not self.all_complete:
                                can_hook = self.level_mgr.current_index >= 10
                                self.player.handle_hook_press(pygame.mouse.get_pos(), self.solid_rects, self.camera.x, self.camera.y, can_hook)

                        if event.type == pygame.KEYDOWN:
                            if event.key == pygame.K_ESCAPE:
                                self.paused = True
                                self.pause_menu.show()
                                self.audio.pause_music()
                            elif event.key == pygame.K_SPACE:
                                if not self.hud.transitioning and not self.all_complete:
                                    self.player.handle_jump_press()
                            elif event.key == pygame.K_q:
                                if not self.hud.transitioning and not self.all_complete:
                                    self.player.handle_dash_press()
                            elif event.key == pygame.K_f:
                                if not self.hud.transitioning and not self.all_complete:
                                    self._collect_cor()
                            elif event.key == pygame.K_RETURN:
                                if self.all_complete:
                                    self.return_to_menu()
                                elif self.sign_mgr and self.sign_mgr.near_sign:
                                    self.sign_mgr.interact()
                                elif self.player.near_portal and not self.hud.transitioning:
                                    self._try_use_portal()

            # Update
            if self.state == "menu":
                self.main_menu.update(dt)
                done, a = self.main_menu.is_done()
                if done and a in ("new_game", "resume"):
                    if a == "new_game":
                        self.start_game(new_game=True)
                    else:
                        self.level_mgr.current_index = self.level_mgr.max_unlocked
                        self.start_game()
            
            elif self.state == "level_select":
                self.level_select_menu.update(dt)

            elif self.state == "playing":
                if self.paused:
                    self.pause_menu.update(dt)
                else:
                    if self.sign_mgr:
                        self.sign_mgr.update(dt)
                    tr = self.hud.update_transition(dt)
                    if not tr and not self.all_complete:
                        if not (self.sign_mgr and self.sign_mgr.is_dialog_active):
                            self.player.update(dt, pygame.key.get_pressed(), self.solid_rects, self.bounce_rects)
                        self.player.check_portal_proximity(self.portal_rects)
                        if self.sign_mgr:
                            self.sign_mgr.check_proximity(self.player.rect)
                        self._check_cor_proximity()
                        self._check_key_proximity()
                        self.camera.update(self.player, self.tilemap, dt)

            # Draw
            if self.state == "menu":
                self.main_menu.draw(self.screen)
                
            elif self.state == "level_select":
                self.level_select_menu.draw(self.screen)

            elif self.state == "playing":
                self.screen.fill(BACKGROUND)

                if not self.all_complete:
                    self.tilemap.draw(self.screen, self.camera.x, self.camera.y)
                    self.player.draw(self.screen, self.camera.x, self.camera.y)

                    self.hud.draw_level_info(
                        self.screen, self.level_mgr.name,
                        self.level_mgr.current_index + 1,
                        max(self.level_mgr.total, 1),
                    )
                    self.hud.draw_cor_counter(self.screen, self.cors_collected, self.cors_total)

                    # Key counter
                    if self.keys_total > 0:
                        kc = (80, 255, 80) if self.keys_collected >= self.keys_total else (200, 180, 50)
                        kf = pygame.font.SysFont("consolas", 18, bold=True)
                        ks = kf.render(f"Keys: {self.keys_collected}/{self.keys_total}", True, kc)
                        kb = pygame.Surface((ks.get_width() + 16, ks.get_height() + 8), pygame.SRCALPHA)
                        kb.fill((0, 0, 0, 120))
                        self.screen.blit(kb, (10, 65))
                        self.screen.blit(ks, (18, 69))

                    self.hud.draw_controls(self.screen)
                    self.hud.draw_player_state(self.screen, self.player)

                    # Collect prompts
                    show_collect, collect_text = False, ""
                    if self.near_cor:
                        show_collect, collect_text = True, "Press F to collect COR"
                    elif self.near_key:
                        show_collect, collect_text = True, "Press F to pick up Key"

                    if show_collect and not (self.sign_mgr and self.sign_mgr.is_dialog_active):
                        hf    = pygame.font.SysFont("consolas", 20, bold=True)
                        ticks = pygame.time.get_ticks()
                        pulse = abs((ticks % 1000) - 500) / 500.0
                        alpha = int(160 + 95 * pulse)
                        s     = hf.render(collect_text, True, (255, 220, 80))
                        bg    = pygame.Surface((s.get_width() + 20, s.get_height() + 12), pygame.SRCALPHA)
                        bg.fill((0, 0, 0, min(alpha, 160)))
                        bg.blit(s, (10, 6))
                        bg.set_alpha(alpha)
                        self.screen.blit(bg, (SCREEN_W // 2 - bg.get_width() // 2, SCREEN_H - 110))

                    # Sign / portal prompts
                    if self.sign_mgr:
                        if not self.sign_mgr.is_dialog_active:
                            self.sign_mgr.draw_interact_hint(self.screen)
                            if self.player.near_portal and not self.hud.transitioning:
                                if not self.sign_mgr.near_sign:
                                    hf    = pygame.font.SysFont("consolas", 24, bold=True)
                                    ticks = pygame.time.get_ticks()
                                    pulse = abs((ticks % 1000) - 500) / 500.0
                                    alpha = int(180 + 75 * pulse)
                                    if self._is_cor_required() and not self._all_cors_collected():
                                        remaining = self.cors_total - self.cors_collected
                                        pt = f"Collect all COR first! ({remaining} remaining)"
                                        pc = (255, 100, 100)
                                    else:
                                        pt = "Press ENTER to go to next level"
                                        pc = UI_HIGHLIGHT
                                    s  = hf.render(pt, True, pc)
                                    ps = pygame.Surface((s.get_width() + 30, s.get_height() + 16), pygame.SRCALPHA)
                                    ps.fill((0, 0, 0, min(alpha, 180)))
                                    ps.blit(s, (15, 8))
                                    ps.set_alpha(alpha)
                                    self.screen.blit(ps, (SCREEN_W // 2 - ps.get_width() // 2, SCREEN_H - 80))
                        else:
                            self.sign_mgr.draw(self.screen)

                    self.hud.draw_blocked_message(self.screen, dt)
                    self.hud.draw_transition(self.screen)
                else:
                    self.hud.draw_complete(self.screen)

                if self.paused:
                    self.pause_menu.draw(self.screen)

            pygame.display.flip()

        pygame.quit()
        sys.exit()


def main():
    game = Game()
    game.run()


if __name__ == "__main__":
    main()