import os
import math
import array
import pygame

from settings import MUSIC_VOLUME, SFX_VOLUME, MUSIC_FADEOUT, MUSIC_PATHS, COR_SFX_PATH


class AudioManager:
    def __init__(self):
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

        self.music_enabled = True
        self.sfx_enabled   = True
        self.music_tracks  = {}
        self.sfx           = {}
        self.current_music = None

        self._load_music_tracks()
        self._load_sfx()
        self._generate_missing_sfx()

        print("Audio manager initialized")
        print(f"  Music tracks : {list(self.music_tracks.keys())}")
        print(f"  Sound effects: {list(self.sfx.keys())}")

    def _load_music_tracks(self):
        for name, path in MUSIC_PATHS.items():
            if path and os.path.exists(path):
                self.music_tracks[name] = path
            elif path:
                print(f"  Music '{name}' not found: {path}")
        music_dir = os.path.join("audio", "music")
        if os.path.exists(music_dir):
            for fn in os.listdir(music_dir):
                if fn.endswith((".mp3", ".ogg", ".wav")):
                    name = os.path.splitext(fn)[0]
                    if name not in self.music_tracks:
                        self.music_tracks[name] = os.path.join(music_dir, fn)

    def _load_sfx(self):
        # Load COR pickup sound from settings path
        if COR_SFX_PATH and os.path.exists(COR_SFX_PATH):
            try:
                snd = pygame.mixer.Sound(COR_SFX_PATH)
                snd.set_volume(SFX_VOLUME)
                self.sfx["cor_collect"] = snd
                print(f"  COR SFX loaded: {COR_SFX_PATH}")
            except pygame.error as e:
                print(f"  Failed to load COR SFX: {e}")

        sfx_dir = os.path.join("audio", "sfx")
        if not os.path.exists(sfx_dir):
            return
        sfx_map = {
            "jump":        ["jump.wav",        "jump.ogg"],
            "double_jump": ["double_jump.wav",  "double_jump.ogg"],
            "dash":        ["dash.wav",         "dash.ogg"],
            "land":        ["land.wav",         "land.ogg"],
            "wall_jump":   ["wall_jump.wav",    "wall_jump.ogg"],
            "portal":      ["portal.wav",       "portal.ogg"],
            "click":       ["click.wav",        "click.ogg"],
            "sign_char":   ["sign_char.wav",    "type.wav"],
            "sign_line":   ["sign_line.wav",    "line.wav"],
            "sign_open":   ["sign_open.wav",    "open.wav"],
            "sign_close":  ["sign_close.wav",   "close.wav"],
            "cor_collect": ["cor_collect.wav",  "collect.wav", "pickupCoin.wav"],
        }
        for name, filenames in sfx_map.items():
            if name in self.sfx:
                continue
            for fn in filenames:
                path = os.path.join(sfx_dir, fn)
                if os.path.exists(path):
                    try:
                        snd = pygame.mixer.Sound(path)
                        snd.set_volume(SFX_VOLUME)
                        self.sfx[name] = snd
                    except pygame.error:
                        pass
                    break

    def _generate_missing_sfx(self):
        sr = 44100

        def beep(freq=440, dur=0.1, vol=0.3):
            n = int(sr * dur)
            buf = array.array("h", [0] * n)
            for i in range(n):
                fade = 1.0 - i / n
                buf[i] = max(-32767, min(32767, int(vol * 32767 * math.sin(2 * math.pi * freq * i / sr) * fade)))
            s = pygame.mixer.Sound(buffer=buf); s.set_volume(SFX_VOLUME); return s

        def sweep(f0=800, f1=200, dur=0.15, vol=0.3):
            n = int(sr * dur)
            buf = array.array("h", [0] * n)
            for i in range(n):
                p = i / n; freq = f0 + (f1 - f0) * p; fade = 1.0 - p
                buf[i] = max(-32767, min(32767, int(vol * 32767 * math.sin(2 * math.pi * freq * i / sr) * fade)))
            s = pygame.mixer.Sound(buffer=buf); s.set_volume(SFX_VOLUME); return s

        def noise(dur=0.05, vol=0.2):
            import random
            n = int(sr * dur)
            buf = array.array("h", [0] * n)
            for i in range(n):
                fade = 1.0 - i / n
                buf[i] = max(-32767, min(32767, int(vol * 32767 * (random.random() * 2 - 1) * fade)))
            s = pygame.mixer.Sound(buffer=buf); s.set_volume(SFX_VOLUME); return s

        def arpeggio(base=400, dur=0.3, vol=0.25):
            n = int(sr * dur); notes = [1.0, 1.25, 1.5, 2.0]; nlen = n // len(notes)
            buf = array.array("h", [0] * n)
            for i in range(n):
                freq = base * notes[min(i // nlen, len(notes) - 1)]; fade = 1.0 - i / n
                buf[i] = max(-32767, min(32767, int(vol * 32767 * math.sin(2 * math.pi * freq * i / sr) * fade)))
            s = pygame.mixer.Sound(buffer=buf); s.set_volume(SFX_VOLUME); return s

        def soft_tick(freq=800, dur=0.02, vol=0.15):
            n = int(sr * dur); buf = array.array("h", [0] * n)
            for i in range(n):
                fade = 1.0 - (i / n) ** 0.3
                buf[i] = max(-32767, min(32767, int(vol * 32767 * math.sin(2 * math.pi * freq * i / sr) * fade)))
            s = pygame.mixer.Sound(buffer=buf); s.set_volume(SFX_VOLUME * 0.5); return s

        def chime(base=600, dur=0.08, vol=0.2):
            n = int(sr * dur); buf = array.array("h", [0] * n)
            for i in range(n):
                p = i / n; freq = base + 200 * p; fade = 1.0 - p
                buf[i] = max(-32767, min(32767, int(vol * 32767 * math.sin(2 * math.pi * freq * i / sr) * fade)))
            s = pygame.mixer.Sound(buffer=buf); s.set_volume(SFX_VOLUME * 0.6); return s

        def cor_jingle(dur=0.4, vol=0.3):
            n = int(sr * dur); notes = [523, 659, 784, 1047]; nlen = n // len(notes)
            buf = array.array("h", [0] * n)
            for i in range(n):
                freq = notes[min(i // nlen, len(notes) - 1)]
                fade = 1.0 - (i % nlen) / nlen
                buf[i] = max(-32767, min(32767, int(vol * 32767 * math.sin(2 * math.pi * freq * i / sr) * fade)))
            s = pygame.mixer.Sound(buffer=buf); s.set_volume(SFX_VOLUME); return s

        defaults = {
            "jump": lambda: beep(500, 0.08), "double_jump": lambda: beep(700, 0.1),
            "dash": lambda: sweep(300, 100, 0.15), "land": lambda: noise(0.06, 0.25),
            "wall_jump": lambda: beep(600, 0.09), "portal": lambda: arpeggio(400, 0.3),
            "click": lambda: beep(1000, 0.02, 0.4), "sign_char": lambda: soft_tick(800, 0.02, 0.15),
            "sign_line": lambda: chime(600, 0.08, 0.2), "sign_open": lambda: beep(400, 0.06, 0.25),
            "sign_close": lambda: beep(300, 0.06, 0.2), "cor_collect": lambda: cor_jingle(0.4, 0.3),
        }
        generated = []
        for name, factory in defaults.items():
            if name not in self.sfx:
                self.sfx[name] = factory()
                generated.append(name)
        if generated:
            print(f"  Generated placeholder sounds: {generated}")

    def play_music(self, track_name, loops=-1, fade_ms=None):
        if not self.music_enabled or track_name == self.current_music or track_name not in self.music_tracks: return
        fade = fade_ms if fade_ms is not None else MUSIC_FADEOUT
        try:
            if pygame.mixer.music.get_busy(): pygame.mixer.music.fadeout(fade)
            pygame.mixer.music.load(self.music_tracks[track_name])
            pygame.mixer.music.set_volume(MUSIC_VOLUME)
            pygame.mixer.music.play(loops)
            self.current_music = track_name
        except pygame.error as e:
            print(f"  Failed to play music '{track_name}': {e}")

    def stop_music(self, fade_ms=None):
        try: pygame.mixer.music.fadeout(fade_ms if fade_ms is not None else MUSIC_FADEOUT)
        except pygame.error: pass
        self.current_music = None

    def pause_music(self):
        try: pygame.mixer.music.pause()
        except pygame.error: pass

    def resume_music(self):
        try: pygame.mixer.music.unpause()
        except pygame.error: pass

    def play_sfx(self, name):
        if not self.sfx_enabled: return
        if name in self.sfx:
            try: self.sfx[name].play()
            except pygame.error: pass

    def toggle_music(self):
        self.music_enabled = not self.music_enabled
        if not self.music_enabled: self.stop_music()
        return self.music_enabled

    def toggle_sfx(self):
        self.sfx_enabled = not self.sfx_enabled
        return self.sfx_enabled