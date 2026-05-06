"""
Dialog system — typewriter-style text popup for sign interactions.
Supports nested, legacy flat, and index-order sign text lookup.
"""

import pygame
from settings import (
    SCREEN_W, SCREEN_H,
    SIGN_CHAR_DELAY, SIGN_LINE_SOUND,
    SIGN_DEFAULT_TEXT, SIGN_TEXTS, SIGN_TEXTS_BY_INDEX,
    SIGN_INTERACT_RANGE,
    UI_TEXT, UI_TEXT_DIM, UI_HIGHLIGHT,
)


class DialogBox:
    def __init__(self, audio=None):
        self.audio = audio

        self.font_text = pygame.font.SysFont("consolas", 20)
        self.font_hint = pygame.font.SysFont("consolas", 14)

        self.active             = False
        self.lines              = []
        self.current_line_index = 0
        self.current_char_index = 0
        self.char_timer         = 0.0
        self.line_complete      = False
        self.displayed_lines    = []

        self.box_width  = min(600, SCREEN_W - 80)
        self.box_height = 160
        self.box_x      = (SCREEN_W - self.box_width) // 2
        self.box_y      = SCREEN_H - self.box_height - 30
        self.padding    = 20
        self.line_height = 28

        self.max_visible_lines = (self.box_height - self.padding * 2 - 20) // self.line_height

        self.slide_offset = self.box_height + 40
        self.target_slide = 0
        self.blink_timer  = 0.0

    def open(self, lines):
        if not lines:
            lines = list(SIGN_DEFAULT_TEXT)
        self.lines              = lines
        self.current_line_index = 0
        self.current_char_index = 0
        self.char_timer         = 0.0
        self.line_complete      = False
        self.displayed_lines    = [""]
        self.active             = True
        self.slide_offset       = self.box_height + 40
        self.target_slide       = 0
        self.blink_timer        = 0.0
        if self.audio:
            self.audio.play_sfx("sign_open")

    def close(self):
        self.active = False
        if self.audio:
            self.audio.play_sfx("sign_close")

    def advance(self):
        if not self.active:
            return
        if not self.line_complete:
            current_line = self.lines[self.current_line_index]
            self.displayed_lines[-1] = current_line
            self.current_char_index  = len(current_line)
            self.line_complete       = True
            return

        self.current_line_index += 1
        if self.current_line_index >= len(self.lines):
            self.close()
            return

        self.current_char_index = 0
        self.char_timer         = 0.0
        self.line_complete      = False
        self.displayed_lines.append("")
        if self.audio and SIGN_LINE_SOUND:
            self.audio.play_sfx("sign_line")

    def update(self, dt):
        if not self.active:
            return
        self.slide_offset += (self.target_slide - self.slide_offset) * 12 * dt
        self.blink_timer  += dt

        if self.line_complete:
            return

        self.char_timer += dt
        if self.char_timer >= SIGN_CHAR_DELAY:
            self.char_timer -= SIGN_CHAR_DELAY
            current_line = self.lines[self.current_line_index]
            if self.current_char_index < len(current_line):
                char = current_line[self.current_char_index]
                self.current_char_index += 1
                self.displayed_lines[-1] = current_line[:self.current_char_index]
                if char != " " and self.audio:
                    self.audio.play_sfx("sign_char")
                if self.current_char_index >= len(current_line):
                    self.line_complete = True

    def draw(self, surface):
        if not self.active:
            return

        slide = int(self.slide_offset)

        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 60))
        surface.blit(overlay, (0, 0))

        box_rect = pygame.Rect(self.box_x, self.box_y + slide, self.box_width, self.box_height)

        sh = pygame.Surface((box_rect.w, box_rect.h), pygame.SRCALPHA)
        sh.fill((0, 0, 0, 80))
        surface.blit(sh, box_rect.move(4, 4).topleft)

        pygame.draw.rect(surface, (25, 25, 35), box_rect, border_radius=8)
        pygame.draw.rect(surface, (80, 80, 100), box_rect, 2, border_radius=8)
        pygame.draw.rect(surface, (50, 50, 65), box_rect.inflate(-8, -8), 1, border_radius=5)

        icon_x, icon_y = box_rect.x + 12, box_rect.y + 10
        pygame.draw.rect(surface, (100, 70, 40), (icon_x, icon_y, 20, 16), border_radius=2)
        pygame.draw.rect(surface, (70, 50, 25), (icon_x + 8, icon_y + 16, 4, 8))
        surface.blit(self.font_hint.render("SIGN", True, UI_TEXT_DIM), (icon_x + 28, icon_y + 2))

        text_x    = box_rect.x + self.padding
        text_y    = box_rect.y + 40
        start_line = max(0, len(self.displayed_lines) - self.max_visible_lines)

        for i in range(start_line, len(self.displayed_lines)):
            line_text = self.displayed_lines[i]
            if line_text:
                color     = UI_TEXT if i == len(self.displayed_lines) - 1 else UI_TEXT_DIM
                text_surf = self.font_text.render(line_text, True, color)
                surface.blit(text_surf, (text_x, text_y + (i - start_line) * self.line_height))

        if self.line_complete:
            blink = int(self.blink_timer * 3) % 2 == 0
            if blink:
                if self.current_line_index >= len(self.lines) - 1:
                    prompt = self.font_hint.render("ENTER to close", True, UI_HIGHLIGHT)
                else:
                    prompt = self.font_hint.render("ENTER ▼", True, UI_HIGHLIGHT)
                surface.blit(prompt, (box_rect.right - prompt.get_width() - 12, box_rect.bottom - 20))

        if len(self.lines) > 1:
            dot_y       = box_rect.bottom - 10
            dot_start_x = box_rect.centerx - (len(self.lines) * 10) // 2
            for i in range(len(self.lines)):
                color = UI_HIGHLIGHT if i <= self.current_line_index else (60, 60, 75)
                pygame.draw.circle(surface, color, (dot_start_x + i * 10, dot_y), 3)


class SignManager:
    """
    Sign text lookup priority:
    1. SIGN_TEXTS[level_name]["col,row"]   — nested format
    2. SIGN_TEXTS["level_name:col,row"]    — legacy flat format
    3. SIGN_TEXTS_BY_INDEX[level_name][i]  — index-order format
    4. SIGN_DEFAULT_TEXT
    """

    def __init__(self, audio=None):
        self.audio             = audio
        self.dialog            = DialogBox(audio)
        self.signs             = []
        self.near_sign         = False
        self.nearby_sign_index = -1
        self.level_name        = ""

    def _resolve_sign_text(self, level_name, col, row, sign_index):
        # 1) Nested format
        if level_name in SIGN_TEXTS:
            entry = SIGN_TEXTS[level_name]
            if isinstance(entry, dict):
                pos_key = f"{col},{row}"
                if pos_key in entry:
                    return list(entry[pos_key]), "nested"

        # 2) Legacy flat format
        legacy_key = f"{level_name}:{col},{row}"
        if legacy_key in SIGN_TEXTS and isinstance(SIGN_TEXTS[legacy_key], list):
            return list(SIGN_TEXTS[legacy_key]), "legacy"

        # 3) Index format
        if level_name in SIGN_TEXTS_BY_INDEX:
            level_signs = SIGN_TEXTS_BY_INDEX[level_name]
            if sign_index < len(level_signs):
                return list(level_signs[sign_index]), "index"

        return list(SIGN_DEFAULT_TEXT), "default"

    def load_signs(self, tilemap, level_name=""):
        self.level_name = level_name
        self.signs      = []

        raw_signs = sorted(tilemap.get_sign_positions(), key=lambda s: (s[1], s[0]))

        if raw_signs:
            print(f"  Signs loaded for '{level_name}':")

        for sign_index, (col, row, rect) in enumerate(raw_signs):
            text, source = self._resolve_sign_text(level_name, col, row, sign_index)
            self.signs.append({
                "col":    col,
                "row":    row,
                "rect":   rect,
                "index":  sign_index,
                "text":   text,
                "source": source,
            })
            print(f"    sign#{sign_index}  pos=({col},{row})  source={source}")
            for line in text:
                print(f"      -> \"{line}\"")

    def check_proximity(self, player_rect):
        expanded   = player_rect.inflate(SIGN_INTERACT_RANGE * 2, SIGN_INTERACT_RANGE * 2)
        self.near_sign         = False
        self.nearby_sign_index = -1
        pcx, pcy   = player_rect.center
        best_index = -1
        best_dist  = float("inf")

        for i, sign in enumerate(self.signs):
            if expanded.colliderect(sign["rect"]):
                sx, sy = sign["rect"].center
                dist   = (sx - pcx) ** 2 + (sy - pcy) ** 2
                if dist < best_dist:
                    best_dist  = dist
                    best_index = i

        if best_index != -1:
            self.near_sign         = True
            self.nearby_sign_index = best_index
            return True
        return False

    def interact(self):
        if not self.near_sign or self.nearby_sign_index < 0:
            return False
        if self.dialog.active:
            self.dialog.advance()
            return True
        self.dialog.open(self.signs[self.nearby_sign_index]["text"])
        return True

    def update(self, dt):
        self.dialog.update(dt)

    def draw(self, surface):
        self.dialog.draw(surface)

    def draw_interact_hint(self, surface):
        if not self.near_sign or self.dialog.active:
            return
        font  = pygame.font.SysFont("consolas", 16)
        ticks = pygame.time.get_ticks()
        pulse = abs((ticks % 1000) - 500) / 500.0
        alpha = int(160 + 95 * pulse)
        s     = font.render("Press ENTER to read", True, UI_HIGHLIGHT)
        bg    = pygame.Surface((s.get_width() + 16, s.get_height() + 8), pygame.SRCALPHA)
        bg.fill((0, 0, 0, min(alpha, 160)))
        bg.blit(s, (8, 4))
        bg.set_alpha(alpha)
        surface.blit(bg, (SCREEN_W // 2 - bg.get_width() // 2, SCREEN_H - 80))

    @property
    def is_dialog_active(self):
        return self.dialog.active