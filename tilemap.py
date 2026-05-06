import os
import re
import math
import json
import pygame
from settings import (
    TILE_SIZE, TILE_TYPES, GRID_COLOR, TILE_IMAGE_PATHS,
    COR_FLOAT_SPEED, COR_FLOAT_HEIGHT, BG_THRESHOLD,
)

try:
    from settings import HALF_HEIGHT_TILES
except ImportError:
    HALF_HEIGHT_TILES = []


class TileMap:
    def __init__(self, cols, rows, layout=None, num_layers=2):
        self.cols = cols
        self.rows = rows
        self.layers = []
        for _ in range(max(num_layers, 1)):
            self.layers.append([[None for _ in range(cols)] for _ in range(rows)])
        self.collected_cors = set()
        if layout:
            self._parse_layout(layout)
        self.images = {}
        self._load_images()

    @property
    def num_layers(self):
        return len(self.layers)

    @property
    def bg(self):
        return self.layers[0]

    @bg.setter
    def bg(self, v):
        self.layers[0] = v

    @property
    def fg(self):
        return self.layers[1] if len(self.layers) > 1 else self.layers[0]

    @fg.setter
    def fg(self, v):
        if len(self.layers) > 1:
            self.layers[1] = v

    @property
    def grid(self):
        merged = []
        for r in range(self.rows):
            row = []
            for c in range(self.cols):
                tile = None
                for layer in self.layers:
                    if layer[r][c]:
                        tile = layer[r][c]
                row.append(tile)
            merged.append(row)
        return merged

    @grid.setter
    def grid(self, value):
        self.layers[0] = value
        for i in range(1, len(self.layers)):
            self.layers[i] = [[None for _ in range(self.cols)] for _ in range(self.rows)]

    def add_layer(self):
        self.layers.append([[None for _ in range(self.cols)] for _ in range(self.rows)])
        return len(self.layers) - 1

    def remove_layer(self, index):
        if len(self.layers) <= 1:
            return False
        if 0 <= index < len(self.layers):
            self.layers.pop(index)
            return True
        return False

    def set_layer_tile(self, li, col, row, tid):
        if 0 <= li < len(self.layers) and 0 <= col < self.cols and 0 <= row < self.rows:
            self.layers[li][row][col] = tid

    def get_layer_tile(self, li, col, row):
        if 0 <= li < len(self.layers) and 0 <= col < self.cols and 0 <= row < self.rows:
            return self.layers[li][row][col]
        return None

    def set_bg(self, c, r, t):
        self.set_layer_tile(0, c, r, t)

    def get_bg(self, c, r):
        return self.get_layer_tile(0, c, r)

    def set_fg(self, c, r, t):
        if len(self.layers) > 1:
            self.set_layer_tile(1, c, r, t)

    def get_fg(self, c, r):
        return self.get_layer_tile(1, c, r) if len(self.layers) > 1 else None

    def set_tile(self, col, row, tid):
        if tid and tid in TILE_TYPES and TILE_TYPES[tid]["solid"]:
            self.set_layer_tile(0, col, row, tid)
        elif len(self.layers) > 1:
            self.set_layer_tile(1, col, row, tid)
        else:
            self.set_layer_tile(0, col, row, tid)

    def get_tile(self, col, row):
        for i in range(len(self.layers) - 1, -1, -1):
            tid = self.get_layer_tile(i, col, row)
            if tid:
                return tid
        return None

    # ── Image loading ─────────────────────────────────────

    def _load_images(self):
        for tid, path in TILE_IMAGE_PATHS.items():
            if not path:
                continue
            for tp in [path, os.path.join("assets", "objects", os.path.basename(path))]:
                if not os.path.exists(tp):
                    continue
                try:
                    if tid == "P":
                        self._load_npc_frame(tid, tp)
                    else:
                        img = pygame.image.load(tp).convert_alpha()
                        self.images[tid] = pygame.transform.smoothscale(img, (TILE_SIZE, TILE_SIZE))
                        print(f"  Tile '{tid}' image loaded: {tp}")
                    break
                except pygame.error as e:
                    print(f"  Failed to load tile '{tid}': {e}")

    def _load_npc_frame(self, tid, image_path):
        """Extract a single frame from a character spritesheet for the NPC tile."""
        sheet  = pygame.image.load(image_path)
        is_jpg = image_path.lower().endswith((".jpg", ".jpeg"))

        if is_jpg:
            sheet = sheet.convert()
        else:
            sheet = sheet.convert_alpha()

        # Try to find JSON frame data
        json_path = None
        base_dir  = os.path.dirname(image_path)

        for jp in [
            os.path.join(base_dir, "character_animation_frames.json"),
            "character_animation_frames.json",
        ]:
            if os.path.exists(jp):
                json_path = jp
                break

        frame_w, frame_h = 64, 64
        fx, fy = 0, 0

        if json_path:
            try:
                with open(json_path, "r") as f:
                    data = json.load(f)

                frame_w = data["spritesheet_info"]["frame_width"]
                frame_h = data["spritesheet_info"]["frame_height"]

                # Get first frame from any available direction
                for direction in ["right", "left", "down", "up"]:
                    if direction in data["frames"] and len(data["frames"][direction]) > 0:
                        first = data["frames"][direction][0]
                        fx, fy = first["x"], first["y"]
                        break

                print(f"  NPC JSON loaded: frame {fx},{fy} size {frame_w}x{frame_h}")
            except (json.JSONDecodeError, KeyError) as e:
                print(f"  NPC JSON parse error: {e}")
        else:
            # Guess frame size from sheet
            sw, sh = sheet.get_width(), sheet.get_height()
            if sw >= 128 and sh >= 128:
                frame_w = sw // 4
                frame_h = sh // 4
            elif sw >= 64 and sh >= 64:
                frame_w = min(64, sw)
                frame_h = min(64, sh)

        # Extract single frame
        frame_surf = pygame.Surface((frame_w, frame_h), pygame.SRCALPHA)
        frame_surf.blit(sheet, (0, 0), pygame.Rect(fx, fy, frame_w, frame_h))

        # Remove black background if JPG
        if is_jpg:
            threshold = BG_THRESHOLD
            frame_surf = frame_surf.convert_alpha()
            frame_surf.lock()
            for y in range(frame_h):
                for x in range(frame_w):
                    r, g, b, a = frame_surf.get_at((x, y))
                    if abs(r) <= threshold and abs(g) <= threshold and abs(b) <= threshold:
                        frame_surf.set_at((x, y), (r, g, b, 0))
            frame_surf.unlock()

        # Scale to tile size
        self.images[tid] = pygame.transform.smoothscale(frame_surf, (TILE_SIZE, TILE_SIZE))
        print(f"  Tile '{tid}' NPC frame loaded: {image_path} (frame {fx},{fy} {frame_w}x{frame_h})")

    # ── Layout parsing ────────────────────────────────────

    def _parse_layout(self, layout):
        for r, row_str in enumerate(layout):
            for c, ch in enumerate(row_str):
                if r < self.rows and c < self.cols and ch != ".":
                    if ch in TILE_TYPES and TILE_TYPES[ch]["solid"]:
                        self.layers[0][r][c] = ch
                    elif len(self.layers) > 1:
                        self.layers[1][r][c] = ch
                    else:
                        self.layers[0][r][c] = ch

    # ── Collision ─────────────────────────────────────────

    def get_solid_rects(self):
        rects = []
        for r in range(self.rows):
            for c in range(self.cols):
                for layer in self.layers:
                    tid = layer[r][c]
                    if tid and tid in TILE_TYPES and TILE_TYPES[tid]["solid"]:
                        px = c * TILE_SIZE
                        py = r * TILE_SIZE
                        if tid in HALF_HEIGHT_TILES:
                            half = TILE_SIZE // 2
                            rects.append(pygame.Rect(px, py + half, TILE_SIZE, half))
                        else:
                            rects.append(pygame.Rect(px, py, TILE_SIZE, TILE_SIZE))
                        break
        return rects

    def get_tiles_of_type(self, tile_id):
        rects = []
        for r in range(self.rows):
            for c in range(self.cols):
                if (c, r) in self.collected_cors:
                    continue
                for layer in self.layers:
                    if layer[r][c] == tile_id:
                        rects.append(pygame.Rect(c * TILE_SIZE, r * TILE_SIZE, TILE_SIZE, TILE_SIZE))
                        break
        return rects

    def get_sign_positions(self):
        signs = []
        for r in range(self.rows):
            for c in range(self.cols):
                for layer in self.layers:
                    if layer[r][c] == "G":
                        signs.append((c, r, pygame.Rect(c * TILE_SIZE, r * TILE_SIZE, TILE_SIZE, TILE_SIZE)))
                        break
        return signs

    def get_cor_positions(self):
        cors = []
        for r in range(self.rows):
            for c in range(self.cols):
                if (c, r) in self.collected_cors:
                    continue
                for layer in self.layers:
                    if layer[r][c] == "R":
                        cors.append((c, r, pygame.Rect(c * TILE_SIZE, r * TILE_SIZE, TILE_SIZE, TILE_SIZE)))
                        break
        return cors

    def collect_cor(self, col, row):
        self.collected_cors.add((col, row))

    def find_spawn_point(self):
        for r in range(self.rows):
            for c in range(self.cols):
                for layer in self.layers:
                    if layer[r][c] == "O":
                        return (c * TILE_SIZE + TILE_SIZE / 2, r * TILE_SIZE + TILE_SIZE / 2)

        solid_set, empty_list = set(), []
        for r in range(self.rows):
            for c in range(self.cols):
                m = self.get_tile(c, r)
                if m and m in TILE_TYPES and TILE_TYPES[m]["solid"]:
                    solid_set.add((c, r))

        for r in range(self.rows):
            for c in range(self.cols):
                m  = self.get_tile(c, r)
                ie = m is None or (m in TILE_TYPES and not TILE_TYPES[m]["solid"] and m not in ("X", "O", "G", "R"))
                if ie:
                    empty_list.append((c, r))
                    if (c, r + 1) in solid_set and (c, r - 1) not in solid_set:
                        return (c * TILE_SIZE + TILE_SIZE / 2, r * TILE_SIZE + TILE_SIZE / 2)

        if empty_list:
            c, r = empty_list[0]
            return (c * TILE_SIZE + TILE_SIZE / 2, r * TILE_SIZE + TILE_SIZE / 2)
        return (TILE_SIZE * 2, TILE_SIZE * 2)

    # ── Drawing ───────────────────────────────────────────

    def draw(self, surface, offset_x, offset_y):
        sw, sh = surface.get_width(), surface.get_height()
        sc = max(0, int(offset_x // TILE_SIZE))
        ec = min(self.cols, int((offset_x + sw) // TILE_SIZE) + 2)
        sr = max(0, int(offset_y // TILE_SIZE))
        er = min(self.rows, int((offset_y + sh) // TILE_SIZE) + 2)
        ticks = pygame.time.get_ticks()

        for r in range(sr, er):
            for c in range(sc, ec):
                rect = pygame.Rect(int(c * TILE_SIZE - offset_x), int(r * TILE_SIZE - offset_y), TILE_SIZE, TILE_SIZE)
                for layer in self.layers:
                    tid = layer[r][c]
                    if not tid or tid not in TILE_TYPES:
                        continue
                    if tid in ("R", "K") and (c, r) in self.collected_cors:
                        continue

                    if tid == "R":
                        self._draw_cor(surface, rect, c, r, ticks)
                    elif tid == "K":
                        self._draw_floating_item(surface, rect, c, r, ticks, "K")
                    elif tid in self.images:
                        surface.blit(self.images[tid], rect.topleft)
                    elif tid == "G":
                        self._draw_sign_fallback(surface, rect)
                    else:
                        pygame.draw.rect(surface, TILE_TYPES[tid]["color"], rect)
                        pygame.draw.rect(surface, GRID_COLOR, rect, 1)

                    if tid == "X":
                        self._draw_portal(surface, rect)
                    elif tid == "O":
                        self._draw_spawn(surface, rect)

    def _draw_floating_item(self, surface, rect, col, row, ticks, tile_id):
        phase     = (col * 97 + row * 151) % 1000
        t         = (ticks + phase) / 1000.0
        bob       = int(math.sin(t * COR_FLOAT_SPEED) * COR_FLOAT_HEIGHT)
        pulse     = abs(math.sin(t * 1.5))
        draw_rect = rect.move(0, bob)

        gs = TILE_SIZE + 6
        ga = int(30 + 25 * pulse)
        glow = pygame.Surface((gs, gs), pygame.SRCALPHA)
        pygame.draw.ellipse(glow, (200, 180, 50, ga), (0, 0, gs, gs))
        surface.blit(glow, (draw_rect.x - 3, draw_rect.y - 3))

        if tile_id in self.images:
            surface.blit(self.images[tile_id], draw_rect.topleft)
        else:
            color = TILE_TYPES.get(tile_id, {}).get("color", (200, 180, 50))
            pygame.draw.rect(surface, color, draw_rect, border_radius=4)
            pygame.draw.rect(surface, (150, 130, 30), draw_rect, 2, border_radius=4)

    def _draw_cor(self, surface, rect, col, row, ticks):
        phase     = (col * 73 + row * 137) % 1000
        t         = (ticks + phase) / 1000.0
        bob       = int(math.sin(t * COR_FLOAT_SPEED) * COR_FLOAT_HEIGHT)
        pulse     = abs(math.sin(t * 1.5))
        draw_rect = rect.move(0, bob)

        gs = TILE_SIZE + 8
        ga = int(40 + 30 * pulse)
        glow = pygame.Surface((gs, gs), pygame.SRCALPHA)
        pygame.draw.ellipse(glow, (255, 220, 80, ga), (0, 0, gs, gs))
        surface.blit(glow, (draw_rect.x - 4, draw_rect.y - 4))

        if "R" in self.images:
            surface.blit(self.images["R"], draw_rect.topleft)
        else:
            pygame.draw.rect(surface, (220, 180, 50), draw_rect, border_radius=6)
            pygame.draw.rect(surface, (180, 140, 30), draw_rect, 2, border_radius=6)
            font = pygame.font.SysFont("consolas", 14, bold=True)
            txt  = font.render("COR", True, (80, 50, 10))
            surface.blit(txt, (draw_rect.centerx - txt.get_width() // 2, draw_rect.centery - txt.get_height() // 2))

    def _draw_portal(self, surface, rect):
        ticks = pygame.time.get_ticks()
        pulse = abs((ticks % 1000) - 500) / 500.0
        size  = int((TILE_SIZE // 4) * (0.6 + 0.4 * pulse))
        alpha = int(150 + 105 * pulse)
        gs    = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        pts   = [(rect.w // 2, rect.h // 2 - size), (rect.w // 2 + size, rect.h // 2),
                 (rect.w // 2, rect.h // 2 + size), (rect.w // 2 - size, rect.h // 2)]
        pygame.draw.polygon(gs, (255, 255, 200, alpha), pts)
        surface.blit(gs, rect.topleft)

    def _draw_spawn(self, surface, rect):
        ticks  = pygame.time.get_ticks()
        bob    = abs((ticks % 800) - 400) / 400.0
        offset = int(bob * 6)
        cx, cy = rect.centerx, rect.centery + offset - 3
        pts    = [(cx, cy + 12), (cx - 10, cy - 4), (cx - 4, cy - 4),
                  (cx - 4, cy - 14), (cx + 4, cy - 14), (cx + 4, cy - 4), (cx + 10, cy - 4)]
        gs    = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        local = [(px - rect.x, py - rect.y) for px, py in pts]
        pygame.draw.polygon(gs, (255, 255, 255, 200), local)
        surface.blit(gs, rect.topleft)

    def _draw_sign_fallback(self, surface, rect):
        pygame.draw.rect(surface, TILE_TYPES["G"]["color"], rect)
        pygame.draw.rect(surface, GRID_COLOR, rect, 1)
        gs     = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        post_x = rect.w // 2
        pygame.draw.rect(gs, (70, 50, 25), (post_x - 3, rect.h // 2, 6, rect.h // 2))
        bw, bh = rect.w - 16, rect.h // 2 - 4
        bx, by = (rect.w - bw) // 2, 6
        pygame.draw.rect(gs, (140, 100, 50), (bx, by, bw, bh), border_radius=3)
        pygame.draw.rect(gs, (90, 65, 30), (bx, by, bw, bh), 2, border_radius=3)
        for i in range(3):
            lw = bw - 12 - i * 6
            if lw > 0:
                pygame.draw.rect(gs, (200, 180, 140), (bx + 6, by + 6 + i * 7, lw, 3))
        surface.blit(gs, rect.topleft)

    def draw_grid_lines(self, surface, ox, oy):
        for r in range(self.rows + 1):
            y = int(r * TILE_SIZE - oy)
            pygame.draw.line(surface, GRID_COLOR, (int(-ox), y), (int(self.cols * TILE_SIZE - ox), y))
        for c in range(self.cols + 1):
            x = int(c * TILE_SIZE - ox)
            pygame.draw.line(surface, GRID_COLOR, (x, int(-oy)), (x, int(self.rows * TILE_SIZE - oy)))

    # ── Save / Load ───────────────────────────────────────

    def save(self, filepath):
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w") as f:
            f.write(f"{self.cols},{self.rows},{len(self.layers)}\n")
            for idx, layer in enumerate(self.layers):
                f.write(f"#L{idx}\n")
                for r in range(self.rows):
                    f.write("".join(layer[r][c] if layer[r][c] else "." for c in range(self.cols)) + "\n")

    @classmethod
    def load(cls, filepath):
        with open(filepath, "r") as f:
            header    = f.readline().strip()
            remaining = f.read()

        parts = header.split(",")
        cols  = int(parts[0])
        rows  = int(parts[1])
        nl    = int(parts[2]) if len(parts) > 2 else 2
        tm    = cls(cols, rows, num_layers=nl)

        if "#L" in remaining:
            blocks = re.split(r"#L\d+\n", remaining)
            blocks = [b for b in blocks if b.strip()]
            for idx, block in enumerate(blocks):
                if idx >= len(tm.layers):
                    tm.add_layer()
                for r, line in enumerate(block.strip().split("\n")):
                    if r >= rows: break
                    for c, ch in enumerate(line):
                        if c < cols and ch != ".":
                            tm.layers[idx][r][c] = ch
        elif "#BG" in remaining and "#FG" in remaining:
            p = remaining.split("#FG")
            for r, line in enumerate(p[0].replace("#BG", "").strip().split("\n")):
                if r >= rows: break
                for c, ch in enumerate(line):
                    if c < cols and ch != ".":
                        tm.layers[0][r][c] = ch
            for r, line in enumerate(p[1].strip().split("\n")):
                if r >= rows: break
                for c, ch in enumerate(line):
                    if c < cols and ch != ".":
                        if len(tm.layers) > 1:
                            tm.layers[1][r][c] = ch
        else:
            for r, line in enumerate(remaining.strip().split("\n")):
                if r >= rows: break
                for c, ch in enumerate(line):
                    if c < cols and ch != ".":
                        if ch in TILE_TYPES and TILE_TYPES[ch]["solid"]:
                            tm.layers[0][r][c] = ch
                        elif len(tm.layers) > 1:
                            tm.layers[1][r][c] = ch
                        else:
                            tm.layers[0][r][c] = ch
        return tm