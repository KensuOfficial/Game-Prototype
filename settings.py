# --- Display ---
SCREEN_W = 1280
SCREEN_H = 720

# --- Tile ---
TILE_SIZE = 64

# --- Player ---
PLAYER_SPEED   = 150.0
INTERACT_RANGE = 10

# --- Physics ---
GRAVITY           = 980.0
MAX_FALL_SPEED    = 500.0
JUMP_FORCE        = -420.0
DOUBLE_JUMP_FORCE = -400.0
WALL_SLIDE_SPEED  = 60.0
WALL_JUMP_FORCE_X = 200.0
WALL_JUMP_FORCE_Y = -400.0
COYOTE_TIME       = 0.10
JUMP_BUFFER_TIME  = 0.12
WALL_STICK_TIME   = 0.15
BOUNCE_FORCE      = -800.0

# --- Dash ---
DASH_SPEED       = 560.0
DASH_DURATION    = 0.14
DASH_COOLDOWN    = 0.5
DASH_GHOST_COUNT = 5

# --- Animation ---
WALK_FRAME_DELAY = 0.10
IDLE_FRAME_DELAY = 0.40

# --- Sprite ---
SPRITE_TARGET_HEIGHT = 56
COLLISION_W_RATIO    = 0.55
COLLISION_H_RATIO    = 0.85
MIN_COLLISION_W      = 20
MIN_COLLISION_H      = 30
BG_THRESHOLD         = 40
SWAP_LEFT_RIGHT      = True

# --- Audio ---
MUSIC_VOLUME  = 0.4
SFX_VOLUME    = 0.6
MUSIC_FADEOUT = 1000

MUSIC_PATHS = {
    "menu":    r"C:\Users\PC\Desktop\PocketUPians\assets\sfx\music\Jump The Gap.mp3",
    "level":   r"C:\Users\PC\Desktop\PocketUPians\assets\sfx\music\Jump The Gap.mp3",
    "victory": None,
}

COR_SFX_PATH = r"C:\Users\PC\Desktop\PocketUPians\assets\sfx\sounds\pickupCoin.wav"

# --- Sign / Dialog ---
SIGN_INTERACT_RANGE = 20
SIGN_CHAR_DELAY     = 0.03
SIGN_LINE_SOUND     = True
SIGN_DISMISS_KEY    = "ENTER"

SIGN_DEFAULT_TEXT = [
    "...",
]

SIGN_IMAGE_PATH = r"C:\Users\PC\Desktop\PocketUPians\assets\objects\sign.png"

SIGN_TEXTS = {
    "map_01.txt": {
        "8,7": [
            "Jump over the gap!",
            "Press SPACE twice for double jump.",
        ],
        "3,9": [
            "Welcome!",
            "This is the tutorial.",
        ],
        "14,9": [
            "Great job!",
            "Press Q to dash forward.",
            "Use the portal when you are ready.",
        ],
    },
    "map_02.txt": {
        "9,4": [
            "You made it to level 2!",
            "There is a COR hidden here.",
            "Press F when near it to collect it.",
        ],
        "17,4": [
            "Collect the COR before leaving.",
            "The portal will not open without it.",
        ],
    },
    "map_04.txt": {
        "9,9": [
            "Welcome to level 4!",
            "You'll need some precise jumps here.",
        ],
    },
    "map_05.txt": {
        "5,9": [
            "Level 5!",
            "It's getting a bit wider.",
        ],
    },
    "map_06.txt": {
        "9,9": [
            "Level 6!",
            "Use the boxes to jump.",
        ],
    },
    "map_11.txt": {
        "9,9": [
            "Chapter 2 begins!",
            "You gained a grappling hook.",
            "Use Left Mouse Click to swing from solid walls.",
        ],
    },
}

SIGN_TEXTS_BY_INDEX = {}

# --- Tile Image Paths ---
TILE_IMAGE_PATHS = {
    "G": r"C:\Users\PC\Desktop\PocketUPians\assets\objects\sign.png",
    "W": r"C:\Users\PC\Desktop\PocketUPians\assets\objects\white wall.png",
    "A": r"C:\Users\PC\Desktop\PocketUPians\assets\objects\chalkboard upper right corner.png",
    "B": r"C:\Users\PC\Desktop\PocketUPians\assets\objects\chalkboard surface.png",
    "C": r"C:\Users\PC\Desktop\PocketUPians\assets\objects\chalkboard lower right corner.png",
    "D": r"C:\Users\PC\Desktop\PocketUPians\assets\objects\chalkboard lower left corner.png",
    "E": r"C:\Users\PC\Desktop\PocketUPians\assets\objects\chalkboard upper left corner.png",
    "R": r"C:\Users\PC\Desktop\PocketUPians\assets\objects\COR.png",
    "H": r"C:\Users\PC\Desktop\PocketUPians\assets\objects\bag.png",
    "I": r"C:\Users\PC\Desktop\PocketUPians\assets\objects\ID.png",
    "K": r"C:\Users\PC\Desktop\PocketUPians\assets\objects\key.png",
    "N": r"C:\Users\PC\Desktop\PocketUPians\assets\objects\open door.png",
    "M": r"C:\Users\PC\Desktop\PocketUPians\assets\objects\closed door.png",
    "J": r"C:\Users\PC\Desktop\PocketUPians\assets\objects\box.png",
    "P": r"C:\Users\PC\Desktop\PocketUPians\assets\character\character.jpg",
}

# --- Tile Types ---
TILE_TYPES = {
    "S": {"color": (120, 120, 120), "solid": True,  "name": "Stone"},
    "G": {"color": (100, 70,  40),  "solid": False, "name": "Sign"},
    "X": {"color": (255, 215, 0),   "solid": False, "name": "Portal"},
    "O": {"color": (255, 140, 0),   "solid": False, "name": "Spawn"},
    "W": {"color": (240, 240, 240), "solid": False, "name": "White Wall"},
    "A": {"color": (60,  80,  60),  "solid": False, "name": "CB UpperR"},
    "B": {"color": (40,  70,  40),  "solid": False, "name": "CB Surface"},
    "C": {"color": (60,  80,  60),  "solid": False, "name": "CB LowerR"},
    "D": {"color": (60,  80,  60),  "solid": False, "name": "CB LowerL"},
    "E": {"color": (60,  80,  60),  "solid": False, "name": "CB UpperL"},
    "R": {"color": (220, 180, 50),  "solid": False, "name": "COR"},
    "H": {"color": (139, 90,  43),  "solid": False, "name": "Bag"},
    "I": {"color": (200, 200, 220), "solid": False, "name": "ID"},
    "K": {"color": (200, 180, 50),  "solid": False, "name": "Key"},
    "N": {"color": (100, 70,  40),  "solid": False, "name": "Open Door"},
    "M": {"color": (80,  55,  30),  "solid": True,  "name": "Closed Door"},
    "J": {"color": (160, 120, 60),  "solid": True,  "name": "Box"},
    "P": {"color": (180, 100, 180), "solid": False, "name": "NPC"},
    "U": {"color": (50,  255, 100), "solid": True,  "name": "Bounce Pad"},
}

TILE_ORDER = ["S", "G", "X", "O", "W", "A", "B", "C", "D", "E", "R", "H", "I", "K", "N", "M", "J", "P", "U"]

# --- COR Collectible ---
COR_FLOAT_SPEED   = 2.0
COR_FLOAT_HEIGHT  = 6
COR_COLLECT_RANGE = 30
COR_COLLECT_KEY   = "F"

COR_REQUIRED_LEVELS = [
    "map_02.txt",
    "map_03.txt",
    "map_04.txt",
    "map_05.txt",
    "map_06.txt",
    "map_07.txt",
    "map_08.txt",
    "map_09.txt",
    "map_10.txt",
    "map_11.txt",
    "map_12.txt",
    "map_13.txt",
    "map_14.txt",
    "map_15.txt",
    "map_16.txt",
    "map_17.txt",
    "map_18.txt",
    "map_19.txt",
    "map_20.txt",
]

# --- Half-height solid tiles ---
HALF_HEIGHT_TILES = ["J"]

# --- Colors ---
BACKGROUND    = (30,  30,  40)
GRID_COLOR    = (50,  50,  60)

UI_BG         = (20,  20,  30)
UI_BORDER     = (80,  80,  100)
UI_TEXT       = (220, 220, 220)
UI_TEXT_DIM   = (140, 140, 160)
UI_HIGHLIGHT  = (255, 200, 50)

UI_BUTTON     = (60,  60,  80)
UI_BUTTON_HOV = (80,  80,  110)
UI_SUCCESS    = (50,  200, 80)
UI_ERROR      = (200, 50,  50)

CURSOR_VALID  = (255, 255, 255)
CURSOR_ERASE  = (255, 60,  60)