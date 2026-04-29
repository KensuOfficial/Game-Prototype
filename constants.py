import pygame

pygame.init()
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()

# --- Physics Constants ---
GRAVITY = 1
MOVE_SPEED = 5      # Fixed speed (no acceleration)
JUMP_FORCE = -15
WALL_SLIDE_SPEED = 2.2

# --- Player & World Setup ---
player_rect = pygame.Rect(100, 100, 30, 50)
vel_x = 0
vel_y = 0
on_ground = False
on_wall = 0

# Map layout
platforms = [
    pygame.Rect(0, 550, 2000, 100),
    pygame.Rect(400, 400, 200, 20),
    pygame.Rect(700, 300, 200, 20),
    pygame.Rect(1000, 450, 300, 20),
    pygame.Rect(1700, 200, 20, 400),
]

camera_x = 0
camera_y = 0

while True:
    screen.fill((135, 206, 235))

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            exit()

    # --- 1. Snappy Input Handling ---
    keys = pygame.key.get_pressed()

    # Check left/right - no acceleration, just instant speed
    if keys[pygame.K_LEFT] or keys[pygame.K_a]:
        vel_x = -MOVE_SPEED
    elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
        vel_x = MOVE_SPEED
    else:
        vel_x = 0  # Instant stop - no sliding!

    # --- 2. Gravity & Wall Slide ---
    vel_y += GRAVITY
    if on_wall != 0 and vel_y > WALL_SLIDE_SPEED:
        vel_y = WALL_SLIDE_SPEED

    # --- 3. Jumping ---
    if keys[pygame.K_SPACE]:
        if on_ground:
            vel_y = JUMP_FORCE
            on_ground = False
        elif on_wall != 0:
            vel_y = JUMP_FORCE
            vel_x = -on_wall * 10 # Kick off wall
            on_wall = 0

    # --- 4. Collision & Movement ---
    on_ground = False
    on_wall = 0

    # X-movement
    player_rect.x += vel_x
    for p in platforms:
        if player_rect.colliderect(p):
            if vel_x > 0:
                player_rect.right = p.left
                on_wall = 1
            elif vel_x < 0:
                player_rect.left = p.right
                on_wall = -1
            # We don't set vel_x to 0 here to keep wall-jump momentum working correctly

    # Y-movement
    player_rect.y += vel_y
    for p in platforms:
        if player_rect.colliderect(p):
            if vel_y > 0:
                player_rect.bottom = p.top
                vel_y = 0
                on_ground = True
            elif vel_y < 0:
                player_rect.top = p.bottom
                vel_y = 0

    # --- 5. Camera Logic ---
    camera_x += (player_rect.centerx - WIDTH // 2 - camera_x) / 10
    camera_y += (player_rect.centery - HEIGHT // 2 - camera_y) / 10

    # --- 6. Drawing ---
    for p in platforms:
        drawn_rect = pygame.Rect(p.x - camera_x, p.y - camera_y, p.width, p.height)
        pygame.draw.rect(screen, (34, 139, 34), drawn_rect)

    player_draw_pos = pygame.Rect(player_rect.x - camera_x, player_rect.y - camera_y, player_rect.width, player_rect.height)
    pygame.draw.rect(screen, (255, 0, 0), player_draw_pos)

    pygame.display.update()
    clock.tick(60)
