"""
Tile Map Editor — Unlimited Layers + Scrollable Palette
========================================================
Controls:
    Left Click         Place tile on current layer
    Right Click        Erase tile from current layer
    WASD / Arrows      Scroll camera
    Scroll Wheel       Scroll palette (when hovering palette) / Cycle tiles (on canvas)
    1-9, 0             Quick select tile
    TAB                Cycle through layers
    + / =              Add new layer
    -                  Remove current layer
    Ctrl+S             Save map
    Ctrl+L             Load map
    Ctrl+N             New map dialog
    Ctrl+Z             Undo
    Ctrl+Y             Redo
    G                  Toggle grid
    F                  Fill current layer
    Ctrl+F             Flood fill current layer
    Escape             Quit
"""

import sys
import os
import pygame
from settings import (
    SCREEN_W, SCREEN_H, TILE_SIZE,
    TILE_TYPES, TILE_ORDER,
    BACKGROUND, GRID_COLOR,
    UI_BG, UI_BORDER, UI_TEXT, UI_TEXT_DIM,
    UI_HIGHLIGHT, UI_BUTTON, UI_BUTTON_HOV,
    UI_SUCCESS, UI_ERROR,
    CURSOR_VALID, CURSOR_ERASE,
)
from tilemap import TileMap


def clamp(value, lo, hi):
    return max(lo, min(hi, value))


class StatusMessage:
    def __init__(self):
        self.text  = ""
        self.color = UI_TEXT
        self.timer = 0.0

    def show(self, text, color=UI_SUCCESS, duration=2.0):
        self.text  = text
        self.color = color
        self.timer = duration

    def update(self, dt):
        if self.timer > 0:
            self.timer -= dt

    def draw(self, surface, font):
        if self.timer > 0:
            rendered = font.render(self.text, True, self.color)
            surface.blit(rendered, (SCREEN_W // 2 - rendered.get_width() // 2, SCREEN_H - 40))


def text_input_dialog(screen, clock, font, prompt, default=""):
    text = default
    cursor_blink = 0.0
    while True:
        dt = clock.tick(60) / 1000
        cursor_blink += dt
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    return text
                elif event.key == pygame.K_ESCAPE:
                    return None
                elif event.key == pygame.K_BACKSPACE:
                    text = text[:-1]
                else:
                    if event.unicode.isprintable() and len(text) < 40:
                        text += event.unicode
        screen.fill(BACKGROUND)
        bw, bh = 500, 160
        bx, by = SCREEN_W // 2 - bw // 2, SCREEN_H // 2 - bh // 2
        br = pygame.Rect(bx, by, bw, bh)
        pygame.draw.rect(screen, UI_BG, br)
        pygame.draw.rect(screen, UI_BORDER, br, 2)
        screen.blit(font.render(prompt, True, UI_TEXT), (bx + 20, by + 20))
        fr = pygame.Rect(bx + 20, by + 60, bw - 40, 36)
        pygame.draw.rect(screen, (40, 40, 55), fr)
        pygame.draw.rect(screen, UI_BORDER, fr, 1)
        cur = "|" if int(cursor_blink * 2) % 2 == 0 else ""
        screen.blit(font.render(text + cur, True, UI_TEXT), (fr.x + 8, fr.y + 6))
        screen.blit(font.render("Enter = confirm   Esc = cancel", True, UI_TEXT_DIM), (bx + 20, by + 115))
        pygame.display.flip()


def new_map_dialog(screen, clock, font):
    cs = text_input_dialog(screen, clock, font, "Map width (columns):", "20")
    if cs is None:
        return None
    rs = text_input_dialog(screen, clock, font, "Map height (rows):", "11")
    if rs is None:
        return None
    try:
        return TileMap(clamp(int(cs), 1, 200), clamp(int(rs), 1, 200))
    except ValueError:
        return None


class Palette:
    WIDTH = 220
    HEADER_HEIGHT = 100
    ITEM_HEIGHT   = 36
    ITEM_MARGIN   = 4
    SCROLL_SPEED  = 30

    def __init__(self, font):
        self.font           = font
        self.selected_index = 0
        self.hovered_index  = -1
        self.active_layer   = 0
        self.scroll_y       = 0
        self.max_scroll     = 0

        # Search / filter
        self.search_text = ""

        # Visible tiles after filtering
        self.visible_tiles = list(range(len(TILE_ORDER)))

    @property
    def selected_tile_id(self):
        return TILE_ORDER[self.selected_index]

    def select_next(self):
        self.selected_index = (self.selected_index + 1) % len(TILE_ORDER)
        self._ensure_visible()

    def select_prev(self):
        self.selected_index = (self.selected_index - 1) % len(TILE_ORDER)
        self._ensure_visible()

    def toggle_layer(self, num_layers=2):
        self.active_layer = (self.active_layer + 1) % num_layers

    def _ensure_visible(self):
        """Scroll to make the selected tile visible."""
        if self.selected_index not in self.visible_tiles:
            return

        vis_pos = self.visible_tiles.index(self.selected_index)
        item_y  = vis_pos * (self.ITEM_HEIGHT + self.ITEM_MARGIN)
        view_h  = SCREEN_H - self.HEADER_HEIGHT - 30

        if item_y < self.scroll_y:
            self.scroll_y = item_y
        elif item_y + self.ITEM_HEIGHT > self.scroll_y + view_h:
            self.scroll_y = item_y + self.ITEM_HEIGHT - view_h

        self._clamp_scroll()

    def _clamp_scroll(self):
        total_h = len(self.visible_tiles) * (self.ITEM_HEIGHT + self.ITEM_MARGIN)
        view_h  = SCREEN_H - self.HEADER_HEIGHT - 30
        self.max_scroll = max(0, total_h - view_h)
        self.scroll_y   = clamp(self.scroll_y, 0, self.max_scroll)

    def handle_click(self, pos):
        mx, my = pos
        if mx > self.WIDTH:
            return False

        content_y = my - self.HEADER_HEIGHT + self.scroll_y
        if my < self.HEADER_HEIGHT:
            return False

        for vi, tile_idx in enumerate(self.visible_tiles):
            iy = vi * (self.ITEM_HEIGHT + self.ITEM_MARGIN)
            if iy <= content_y < iy + self.ITEM_HEIGHT:
                self.selected_index = tile_idx
                return True
        return False

    def handle_scroll(self, direction):
        """Scroll the palette. direction: +1 = down, -1 = up."""
        self.scroll_y += direction * self.SCROLL_SPEED
        self._clamp_scroll()

    def update_hover(self, pos):
        mx, my = pos
        self.hovered_index = -1
        if mx > self.WIDTH or my < self.HEADER_HEIGHT:
            return

        content_y = my - self.HEADER_HEIGHT + self.scroll_y
        for vi, tile_idx in enumerate(self.visible_tiles):
            iy = vi * (self.ITEM_HEIGHT + self.ITEM_MARGIN)
            if iy <= content_y < iy + self.ITEM_HEIGHT:
                self.hovered_index = tile_idx
                return

    def draw(self, surface, images=None, num_layers=2):
        # Panel background
        panel = pygame.Rect(0, 0, self.WIDTH, SCREEN_H)
        pygame.draw.rect(surface, UI_BG, panel)
        pygame.draw.line(surface, UI_BORDER, (self.WIDTH, 0), (self.WIDTH, SCREEN_H), 2)

        # ── Header ──────────────────────────────────────────
        # Title
        title = self.font.render("TILES", True, UI_TEXT)
        surface.blit(title, (self.WIDTH // 2 - title.get_width() // 2, 8))

        # Layer info
        layer_text = f"Layer: {self.active_layer}/{num_layers - 1}  (TAB)"
        layer_surf = self.font.render(layer_text, True, (100, 180, 255))
        surface.blit(layer_surf, (self.WIDTH // 2 - layer_surf.get_width() // 2, 30))

        # Hints
        hint1 = self.font.render("+ Add  - Remove  Scroll", True, UI_TEXT_DIM)
        surface.blit(hint1, (self.WIDTH // 2 - hint1.get_width() // 2, 50))

        tile_count = self.font.render(f"{len(TILE_ORDER)} tiles", True, UI_TEXT_DIM)
        surface.blit(tile_count, (self.WIDTH // 2 - tile_count.get_width() // 2, 70))

        # Separator
        pygame.draw.line(surface, UI_BORDER, (8, self.HEADER_HEIGHT - 4), (self.WIDTH - 8, self.HEADER_HEIGHT - 4))

        # ── Scrollable tile list ────────────────────────────
        self._clamp_scroll()

        # Create a clip region for the tile list area
        list_rect = pygame.Rect(0, self.HEADER_HEIGHT, self.WIDTH, SCREEN_H - self.HEADER_HEIGHT - 26)
        surface.set_clip(list_rect)

        for vi, tile_idx in enumerate(self.visible_tiles):
            tile_id = TILE_ORDER[tile_idx]
            info    = TILE_TYPES[tile_id]

            # Position relative to scroll
            iy = self.HEADER_HEIGHT + vi * (self.ITEM_HEIGHT + self.ITEM_MARGIN) - self.scroll_y

            # Skip if off-screen
            if iy + self.ITEM_HEIGHT < self.HEADER_HEIGHT or iy > SCREEN_H:
                continue

            rect = pygame.Rect(6, iy, self.WIDTH - 12, self.ITEM_HEIGHT)

            is_selected = (tile_idx == self.selected_index)
            is_hovered  = (tile_idx == self.hovered_index)

            # Background
            if is_selected:
                bg_color = (50, 60, 90)
            elif is_hovered:
                bg_color = UI_BUTTON_HOV
            else:
                bg_color = UI_BUTTON

            pygame.draw.rect(surface, bg_color, rect, border_radius=4)

            if is_selected:
                pygame.draw.rect(surface, UI_HIGHLIGHT, rect, 2, border_radius=4)

            # Tile swatch
            swatch = pygame.Rect(rect.x + 4, rect.y + 2, 32, 32)
            if images and tile_id in images:
                surface.blit(pygame.transform.smoothscale(images[tile_id], (32, 32)), swatch.topleft)
            else:
                pygame.draw.rect(surface, info["color"], swatch)
            pygame.draw.rect(surface, UI_BORDER, swatch, 1)

            # Key number
            if tile_idx < 9:
                key_str = str(tile_idx + 1)
            elif tile_idx == 9:
                key_str = "0"
            else:
                key_str = ""

            # Label
            label = f"{key_str:>2} {info['name']}"
            label_color = UI_TEXT if is_selected or is_hovered else UI_TEXT_DIM
            label_surf  = self.font.render(label, True, label_color)
            surface.blit(label_surf, (rect.x + 40, rect.y + self.ITEM_HEIGHT // 2 - label_surf.get_height() // 2))

            # Tile ID badge
            id_surf = self.font.render(tile_id, True, (80, 80, 100))
            surface.blit(id_surf, (rect.right - id_surf.get_width() - 6,
                                   rect.y + self.ITEM_HEIGHT // 2 - id_surf.get_height() // 2))

        surface.set_clip(None)

        # ── Scrollbar ──────────────────────────────────────
        total_h = len(self.visible_tiles) * (self.ITEM_HEIGHT + self.ITEM_MARGIN)
        view_h  = SCREEN_H - self.HEADER_HEIGHT - 26

        if total_h > view_h:
            bar_x     = self.WIDTH - 6
            bar_h     = max(20, int(view_h * (view_h / total_h)))
            bar_range = view_h - bar_h
            bar_y     = self.HEADER_HEIGHT + int(bar_range * (self.scroll_y / max(1, self.max_scroll)))

            # Track
            pygame.draw.rect(surface, (35, 35, 45),
                             (bar_x, self.HEADER_HEIGHT, 4, view_h), border_radius=2)
            # Thumb
            pygame.draw.rect(surface, (80, 80, 100),
                             (bar_x, bar_y, 4, bar_h), border_radius=2)

        # ── Bottom info bar ────────────────────────────────
        bottom_y = SCREEN_H - 22
        sel_info = f"Selected: {TILE_ORDER[self.selected_index]} ({TILE_TYPES[TILE_ORDER[self.selected_index]]['name']})"
        sel_surf = self.font.render(sel_info, True, UI_HIGHLIGHT)
        surface.blit(sel_surf, (self.WIDTH // 2 - sel_surf.get_width() // 2, bottom_y))


class Toolbar:
    HEIGHT = 36

    def __init__(self, font):
        self.font    = font
        self.buttons = []
        self.hovered = -1
        self._build()

    def _build(self):
        labels = [
            ("New  Ctrl+N", "new"),
            ("Save Ctrl+S", "save"),
            ("Load Ctrl+L", "load"),
            ("Undo Ctrl+Z", "undo"),
            ("Redo Ctrl+Y", "redo"),
            ("Grid G", "grid"),
            ("Fill F", "fill"),
        ]
        x = Palette.WIDTH + 10
        for label, action in labels:
            w = self.font.size(label)[0] + 20
            self.buttons.append({
                "label": label,
                "action": action,
                "rect": pygame.Rect(x, 4, w, self.HEIGHT - 8),
            })
            x += w + 6

    def handle_click(self, pos):
        for btn in self.buttons:
            if btn["rect"].collidepoint(pos):
                return btn["action"]
        return None

    def update_hover(self, pos):
        self.hovered = -1
        for i, btn in enumerate(self.buttons):
            if btn["rect"].collidepoint(pos):
                self.hovered = i
                break

    def draw(self, surface):
        pygame.draw.rect(surface, UI_BG,
                         pygame.Rect(Palette.WIDTH, 0, SCREEN_W - Palette.WIDTH, self.HEIGHT))
        pygame.draw.line(surface, UI_BORDER,
                         (Palette.WIDTH, self.HEIGHT), (SCREEN_W, self.HEIGHT), 1)
        for i, btn in enumerate(self.buttons):
            bg = UI_BUTTON_HOV if i == self.hovered else UI_BUTTON
            pygame.draw.rect(surface, bg, btn["rect"], border_radius=3)
            pygame.draw.rect(surface, UI_BORDER, btn["rect"], 1, border_radius=3)
            ls = self.font.render(btn["label"], True, UI_TEXT)
            surface.blit(ls, (btn["rect"].x + btn["rect"].w // 2 - ls.get_width() // 2,
                              btn["rect"].y + btn["rect"].h // 2 - ls.get_height() // 2))


def flood_fill(tilemap, col, row, new_id, layer):
    target = tilemap.get_layer_tile(layer, col, row)
    if target == new_id:
        return
    stack, visited = [(col, row)], set()
    while stack:
        c, r = stack.pop()
        if (c, r) in visited:
            continue
        if c < 0 or c >= tilemap.cols or r < 0 or r >= tilemap.rows:
            continue
        if tilemap.get_layer_tile(layer, c, r) != target:
            continue
        visited.add((c, r))
        tilemap.set_layer_tile(layer, c, r, new_id)
        stack.extend([(c + 1, r), (c - 1, r), (c, r + 1), (c, r - 1)])


class History:
    MAX = 50

    def __init__(self):
        self.undo_stack = []
        self.redo_stack = []

    def save_state(self, tilemap):
        snapshot = {"layers": [[row[:] for row in layer] for layer in tilemap.layers]}
        self.undo_stack.append(snapshot)
        if len(self.undo_stack) > self.MAX:
            self.undo_stack.pop(0)
        self.redo_stack.clear()

    def undo(self, tilemap):
        if not self.undo_stack:
            return False
        self.redo_stack.append({"layers": [[row[:] for row in layer] for layer in tilemap.layers]})
        prev = self.undo_stack.pop()
        tilemap.layers = prev["layers"]
        tilemap.rows   = len(prev["layers"][0])
        tilemap.cols   = len(prev["layers"][0][0]) if prev["layers"][0] else 0
        return True

    def redo(self, tilemap):
        if not self.redo_stack:
            return False
        self.undo_stack.append({"layers": [[row[:] for row in layer] for layer in tilemap.layers]})
        nxt = self.redo_stack.pop()
        tilemap.layers = nxt["layers"]
        tilemap.rows   = len(nxt["layers"][0])
        tilemap.cols   = len(nxt["layers"][0][0]) if nxt["layers"][0] else 0
        return True


class EditorState:
    def __init__(self):
        self.tilemap      = TileMap(20, 11)
        self.camera_x     = 0.0
        self.camera_y     = 0.0
        self.camera_speed = 400
        self.show_grid    = True
        self.drawing      = False
        self.erasing      = False
        self.save_path    = os.path.join("maps", "map_01.txt")
        self.history      = History()
        self.history.save_state(self.tilemap)


def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("Tile Map Editor")

    icon_path = os.path.join("assets", "logo", "game_logo.png")
    if os.path.exists(icon_path):
        pygame.display.set_icon(pygame.image.load(icon_path).convert_alpha())

    clock   = pygame.time.Clock()
    font    = pygame.font.SysFont("consolas", 14)
    state   = EditorState()
    palette = Palette(font)
    toolbar = Toolbar(font)
    status  = StatusMessage()

    canvas_x = Palette.WIDTH
    canvas_y = Toolbar.HEIGHT

    def screen_to_grid(mx, my):
        return (int((mx - canvas_x + state.camera_x) // TILE_SIZE),
                int((my - canvas_y + state.camera_y) // TILE_SIZE))

    def is_on_canvas(mx, my):
        return mx > canvas_x and my > canvas_y

    def is_on_palette(mx, my):
        return mx <= Palette.WIDTH

    def dispatch(action):
        if action == "new":
            new = new_map_dialog(screen, clock, font)
            if new:
                state.tilemap  = new
                state.camera_x = state.camera_y = 0
                state.history  = History()
                state.history.save_state(state.tilemap)
                palette.active_layer = 0
                status.show(f"New map {state.tilemap.cols}x{state.tilemap.rows}", UI_SUCCESS)
        elif action == "save":
            name = text_input_dialog(screen, clock, font, "Save as:", state.save_path)
            if name:
                state.save_path = name
                state.tilemap.save(state.save_path)
                status.show(f"Saved -> {state.save_path}", UI_SUCCESS)
        elif action == "load":
            name = text_input_dialog(screen, clock, font, "Load file:", state.save_path)
            if name and os.path.exists(name):
                state.save_path = name
                state.tilemap   = TileMap.load(state.save_path)
                state.camera_x  = state.camera_y = 0
                state.history   = History()
                state.history.save_state(state.tilemap)
                palette.active_layer = 0
                status.show(f"Loaded <- {state.save_path}", UI_SUCCESS)
            elif name:
                status.show(f"File not found: {name}", UI_ERROR)
        elif action == "undo":
            if state.history.undo(state.tilemap):
                status.show("Undo", UI_TEXT)
            else:
                status.show("Nothing to undo", UI_TEXT_DIM)
        elif action == "redo":
            if state.history.redo(state.tilemap):
                status.show("Redo", UI_TEXT)
            else:
                status.show("Nothing to redo", UI_TEXT_DIM)
        elif action == "grid":
            state.show_grid = not state.show_grid
        elif action == "fill":
            state.history.save_state(state.tilemap)
            for r in range(state.tilemap.rows):
                for c in range(state.tilemap.cols):
                    state.tilemap.set_layer_tile(palette.active_layer, c, r, palette.selected_tile_id)
            status.show(f"Filled layer {palette.active_layer}", UI_SUCCESS)
        elif action == "flood_fill":
            mx, my = pygame.mouse.get_pos()
            gc, gr = screen_to_grid(mx, my)
            if 0 <= gc < state.tilemap.cols and 0 <= gr < state.tilemap.rows:
                state.history.save_state(state.tilemap)
                flood_fill(state.tilemap, gc, gr, palette.selected_tile_id, palette.active_layer)
                status.show(f"Flood fill layer {palette.active_layer}", UI_SUCCESS)

    running = True

    while running:
        dt     = clock.tick(60) / 1000.0
        mx, my = pygame.mouse.get_pos()

        palette.update_hover((mx, my))
        toolbar.update_hover((mx, my))
        status.update(dt)

        tile_images = getattr(state.tilemap, "images", {})

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                ctrl = event.mod & pygame.KMOD_CTRL

                if event.key == pygame.K_ESCAPE:
                    running = False

                elif event.key == pygame.K_TAB:
                    palette.toggle_layer(state.tilemap.num_layers)
                    status.show(f"Layer: {palette.active_layer}/{state.tilemap.num_layers - 1}",
                                (100, 180, 255))

                elif event.key == pygame.K_PLUS or event.key == pygame.K_EQUALS:
                    new_idx = state.tilemap.add_layer()
                    palette.active_layer = new_idx
                    status.show(f"Added layer {new_idx} ({state.tilemap.num_layers} total)", UI_SUCCESS)

                elif event.key == pygame.K_MINUS:
                    if state.tilemap.num_layers > 1:
                        state.history.save_state(state.tilemap)
                        removed = palette.active_layer
                        state.tilemap.remove_layer(removed)
                        palette.active_layer = min(palette.active_layer, state.tilemap.num_layers - 1)
                        status.show(f"Removed layer {removed} ({state.tilemap.num_layers} remain)", UI_ERROR)
                    else:
                        status.show("Can't remove last layer", UI_TEXT_DIM)

                elif ctrl and event.key == pygame.K_s:
                    dispatch("save")
                elif ctrl and event.key == pygame.K_l:
                    dispatch("load")
                elif ctrl and event.key == pygame.K_n:
                    dispatch("new")
                elif ctrl and event.key == pygame.K_z:
                    dispatch("undo")
                elif ctrl and event.key == pygame.K_y:
                    dispatch("redo")
                elif ctrl and event.key == pygame.K_f:
                    dispatch("flood_fill")
                elif not ctrl and event.key == pygame.K_g:
                    dispatch("grid")
                elif not ctrl and event.key == pygame.K_f:
                    dispatch("fill")

                elif pygame.K_1 <= event.key <= pygame.K_9:
                    idx = event.key - pygame.K_1
                    if idx < len(TILE_ORDER):
                        palette.selected_index = idx
                        palette._ensure_visible()
                elif event.key == pygame.K_0:
                    if 9 < len(TILE_ORDER):
                        palette.selected_index = 9
                        palette._ensure_visible()

            elif event.type == pygame.MOUSEWHEEL:
                if is_on_palette(mx, my):
                    # Scroll palette
                    palette.handle_scroll(-event.y)
                else:
                    # Cycle selected tile on canvas
                    if event.y > 0:
                        palette.select_prev()
                    else:
                        palette.select_next()

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    if palette.handle_click((mx, my)):
                        pass
                    elif toolbar.handle_click((mx, my)):
                        for btn in toolbar.buttons:
                            if btn["rect"].collidepoint((mx, my)):
                                dispatch(btn["action"])
                                break
                    elif is_on_canvas(mx, my):
                        state.history.save_state(state.tilemap)
                        state.drawing = True
                        gc, gr = screen_to_grid(mx, my)
                        state.tilemap.set_layer_tile(palette.active_layer, gc, gr, palette.selected_tile_id)

                elif event.button == 3:
                    if is_on_canvas(mx, my):
                        state.history.save_state(state.tilemap)
                        state.erasing = True
                        gc, gr = screen_to_grid(mx, my)
                        state.tilemap.set_layer_tile(palette.active_layer, gc, gr, None)

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    state.drawing = False
                elif event.button == 3:
                    state.erasing = False

        # Continuous draw/erase
        if state.drawing and is_on_canvas(mx, my):
            gc, gr = screen_to_grid(mx, my)
            state.tilemap.set_layer_tile(palette.active_layer, gc, gr, palette.selected_tile_id)

        if state.erasing and is_on_canvas(mx, my):
            gc, gr = screen_to_grid(mx, my)
            state.tilemap.set_layer_tile(palette.active_layer, gc, gr, None)

        # Camera
        keys = pygame.key.get_pressed()
        ctrl = pygame.key.get_mods() & pygame.KMOD_CTRL
        if keys[pygame.K_LEFT]  or keys[pygame.K_a]:
            state.camera_x -= state.camera_speed * dt
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            state.camera_x += state.camera_speed * dt
        if keys[pygame.K_UP]    or keys[pygame.K_w]:
            state.camera_y -= state.camera_speed * dt
        if keys[pygame.K_DOWN]  or (keys[pygame.K_s] and not ctrl):
            state.camera_y += state.camera_speed * dt

        state.camera_x = clamp(state.camera_x, 0, max(0, state.tilemap.cols * TILE_SIZE - (SCREEN_W - canvas_x)))
        state.camera_y = clamp(state.camera_y, 0, max(0, state.tilemap.rows * TILE_SIZE - (SCREEN_H - canvas_y)))

        # ── Draw ──────────────────────────────────────────
        screen.fill(BACKGROUND)

        canvas_rect = pygame.Rect(canvas_x, canvas_y, SCREEN_W - canvas_x, SCREEN_H - canvas_y)
        screen.set_clip(canvas_rect)

        offset_x = state.camera_x - canvas_x
        offset_y = state.camera_y - canvas_y

        state.tilemap.draw(screen, offset_x, offset_y)

        if state.show_grid:
            state.tilemap.draw_grid_lines(screen, offset_x, offset_y)

        # Cursor preview
        if is_on_canvas(mx, my):
            gc, gr = screen_to_grid(mx, my)
            if 0 <= gc < state.tilemap.cols and 0 <= gr < state.tilemap.rows:
                cursor_rect = pygame.Rect(
                    int(gc * TILE_SIZE - offset_x),
                    int(gr * TILE_SIZE - offset_y),
                    TILE_SIZE, TILE_SIZE,
                )
                tid = palette.selected_tile_id
                if tile_images and tid in tile_images:
                    img = tile_images[tid].copy()
                    img.set_alpha(150)
                    screen.blit(img, cursor_rect.topleft)
                else:
                    ps = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
                    ps.fill((*TILE_TYPES[tid]["color"], 100))
                    screen.blit(ps, cursor_rect.topleft)
                pygame.draw.rect(screen, CURSOR_ERASE if state.erasing else CURSOR_VALID, cursor_rect, 2)

        screen.set_clip(None)

        # UI
        palette.draw(screen, tile_images, state.tilemap.num_layers)
        toolbar.draw(screen)

        # Info bar at bottom
        gc, gr    = screen_to_grid(mx, my)
        tile_name = TILE_TYPES[palette.selected_tile_id]["name"]
        info_text = (
            f"Grid: {gc},{gr}  |  "
            f"Map: {state.tilemap.cols}x{state.tilemap.rows}  |  "
            f"Layer: {palette.active_layer}/{state.tilemap.num_layers - 1}  |  "
            f"Tile: {palette.selected_tile_id} ({tile_name})"
        )
        info_bg = pygame.Rect(canvas_x, SCREEN_H - 24, SCREEN_W - canvas_x, 24)
        pygame.draw.rect(screen, UI_BG, info_bg)
        screen.blit(font.render(info_text, True, UI_TEXT_DIM), (canvas_x + 10, SCREEN_H - 20))

        status.draw(screen, font)
        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()