# -*- coding: utf-8 -*-
"""
Car Game Enhanced
=================
4-lane road - 800x700 - car selection per mode
Traffic lights (Normal) - Emergency lights and siren
Traffic lights now use real bulb images: red / yellow / green
Red light = must brake; running red = CRASH!
"""

import pygame
from pygame.locals import *
import random

pygame.init()

# ═══════════════════════════════════════════════════════════════════════════════
#  WINDOW & ROAD GEOMETRY
# ═══════════════════════════════════════════════════════════════════════════════
WIDTH, HEIGHT = 800, 700
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption('Car Game Enhanced')

ROAD_L  = 200
ROAD_R  = 600
ROAD_W  = ROAD_R - ROAD_L          # 400
LANE_W  = ROAD_W // 4              # 100
LANES   = [ROAD_L + LANE_W//2 + i*LANE_W for i in range(4)]  # [250,350,450,550]
DIV_XS  = [ROAD_L + LANE_W*(i+1)  for i in range(3)]         # [300,400,500]
MRK_W, MRK_H = 10, 50

PLAYER_X = LANES[1]   # 350
PLAYER_Y = 580

clock = pygame.time.Clock()
FPS   = 60

lane_marker_y = 0
best_score    = 0

# ═══════════════════════════════════════════════════════════════════════════════
#  COLOURS
# ═══════════════════════════════════════════════════════════════════════════════
ROAD_COL  = (80,  80,  92)
SIDE_COL  = (22,  50,  22)
GRASS_COL = (42, 128,  42)
WHITE     = (255, 255, 255)
BLACK     = (  0,   0,   0)
YELLOW_C  = (255, 218,   0)
RED_C     = (200,  30,  30)
DARK_UI   = ( 14,  16,  28)

MODE_COLORS = {
    'Normal':    ( 65, 190,  65),
    'Speedy':    (230, 185,   0),
    'Emergency': (220,  50,  50),
}

# ═══════════════════════════════════════════════════════════════════════════════
#  FONT CACHE
# ═══════════════════════════════════════════════════════════════════════════════
_fcache = {}

def gf(size, bold=False):
    key = (size, bold)
    if key not in _fcache:
        for name in ('segoeui', 'calibri', 'trebuchetms', 'arial'):
            if pygame.font.match_font(name):
                _fcache[key] = pygame.font.SysFont(name, size, bold=bold)
                return _fcache[key]
        _fcache[key] = pygame.font.Font(None, size)
    return _fcache[key]

# ═══════════════════════════════════════════════════════════════════════════════
#  ASSETS
# ═══════════════════════════════════════════════════════════════════════════════
intro_bg   = pygame.transform.smoothscale(
    pygame.image.load('images/intro_car.png'), (WIDTH, HEIGHT))

_raw = {
    'car':          pygame.image.load('images/car.png'),
    'pickup_truck': pygame.image.load('images/pickup_truck.png'),
    'semi_trailer': pygame.image.load('images/semi_trailer.png'),
    'taxi':         pygame.image.load('images/taxi.png'),
    'van':          pygame.image.load('images/van.png'),
    'ambulance':    pygame.image.load('images/ambulance.png'),
}

# ── Traffic light bulb images ──────────────────────────────────────────────────
TL_W, TL_H = 64, 160

_TL_IMAGES = {
    'red':    pygame.transform.smoothscale(
                  pygame.image.load('images/tl_red.png').convert_alpha(), (TL_W, TL_H)),
    'yellow': pygame.transform.smoothscale(
                  pygame.image.load('images/tl_yellow.png').convert_alpha(), (TL_W, TL_H)),
    'green':  pygame.transform.smoothscale(
                  pygame.image.load('images/tl_green.png').convert_alpha(), (TL_W, TL_H)),
}

def get_tl_image(color):
    return _TL_IMAGES.get(color, _TL_IMAGES['red'])

def _scale_to_height(surf, target_h):
    w, h = surf.get_size()
    new_w = max(1, int(w * target_h / h))
    return pygame.transform.smoothscale(surf, (new_w, target_h))

def _add_flash_lights(surf, anim_tick, left_col, right_col):
    result = surf.copy()
    w = result.get_width()
    flash = (anim_tick // 8) % 2
    lc = left_col  if flash == 0 else right_col
    rc = right_col if flash == 0 else left_col
    bar_w = max(6, w // 4)
    bar_h = max(4, int(result.get_height() * 0.04))
    pygame.draw.rect(result, lc,  (2,           2, bar_w, bar_h), border_radius=2)
    pygame.draw.rect(result, rc,  (w - bar_w - 2, 2, bar_w, bar_h), border_radius=2)
    return result

_PLAYER_H = 80

_CAR_IMAGE = {
    'sedan':     'car',
    'suv':       'van',
    'sports':    'taxi',
    'f1':        'car',
    'muscle':    'pickup_truck',
    'ambulance': 'ambulance',
    'police':    'semi_trailer',
}

def make_car_sprite(car_type, color=None, anim_tick=0):
    img_key = _CAR_IMAGE.get(car_type, 'car')
    surf = _scale_to_height(_raw[img_key], _PLAYER_H)
    if car_type == 'ambulance':
        surf = _add_flash_lights(surf, anim_tick, (220, 30, 30), (30, 80, 220))
    elif car_type == 'police':
        surf = _add_flash_lights(surf, anim_tick, (30, 80, 220), (220, 30, 30))
    return surf

npc_images_normal    = [_scale_to_height(_raw[k], 80)
                        for k in ('car', 'pickup_truck', 'semi_trailer', 'taxi', 'van')]
npc_images_emergency = [_scale_to_height(_raw['ambulance'], 80)]

crash_img  = pygame.transform.smoothscale(
    pygame.image.load('images/crash.png'), (90, 90))

# ═══════════════════════════════════════════════════════════════════════════════
#  CAR OPTIONS
# ═══════════════════════════════════════════════════════════════════════════════
CAR_OPTIONS = {
    'Normal': [
        {'name': 'City Sedan',  'type': 'sedan',  'color': (210, 42,  42), 'desc': 'Classic & reliable'},
        {'name': 'Family SUV',  'type': 'suv',    'color': ( 40,100, 220), 'desc': 'Strong & spacious'},
        {'name': 'City Coupe',  'type': 'sports', 'color': (175,175,190), 'desc': 'Sleek daily driver'},
    ],
    'Speedy': [
        {'name': 'Sports GT',   'type': 'sports', 'color': (255,110,   0), 'desc': 'Track-tuned racer'},
        {'name': 'F1 Racer',    'type': 'f1',     'color': (175, 28, 215), 'desc': 'Open-wheel beast'},
        {'name': 'Muscle Car',  'type': 'muscle', 'color': (240,200,   0), 'desc': 'Raw American power'},
    ],
    'Emergency': [
        {'name': 'Ambulance',   'type': 'ambulance', 'color': (230,230,230), 'desc': 'Racing to save lives'},
        {'name': 'Police Car',  'type': 'police',    'color': ( 30, 50, 160), 'desc': 'Enforce the law'},
    ],
}


# ═══════════════════════════════════════════════════════════════════════════════
#  SPRITES
# ═══════════════════════════════════════════════════════════════════════════════
class Vehicle(pygame.sprite.Sprite):
    def __init__(self, image, x, y):
        super().__init__()
        self.image = image.copy()
        self.rect  = self.image.get_rect(center=(x, y))

class PlayerVehicle(pygame.sprite.Sprite):
    def __init__(self, x, y, car_type='sedan', car_color=(220,30,30)):
        super().__init__()
        self.car_type  = car_type
        self.car_color = car_color
        self.anim_tick = 0
        self.image = make_car_sprite(car_type, car_color, 0)
        self.rect  = self.image.get_rect(center=(x, y))
    def tick(self):
        if self.car_type in ('ambulance','police'):
            self.anim_tick += 1
            ctr = self.rect.center
            self.image = make_car_sprite(self.car_type, self.car_color, self.anim_tick)
            self.rect  = self.image.get_rect(center=ctr)

# ═══════════════════════════════════════════════════════════════════════════════
#  UI HELPERS
# ═══════════════════════════════════════════════════════════════════════════════
def draw_button(surface, text, rect, font_size=22,
                col_normal=(200,30,30), col_hover=(240,60,60)):
    x, y, w, h = rect
    mx, my = pygame.mouse.get_pos()
    hover  = x<=mx<=x+w and y<=my<=y+h
    bc  = col_hover if hover else col_normal
    sh  = (max(0,bc[0]-85), max(0,bc[1]-85), max(0,bc[2]-85))
    pygame.draw.rect(surface, sh, (x+3, y+4, w, h), border_radius=7)
    pygame.draw.rect(surface, bc, (x,   y,   w, h), border_radius=7)
    sheen = pygame.Surface((w, h//3), pygame.SRCALPHA)
    sheen.fill((255,255,255,28))
    surface.blit(sheen, (x, y))
    bc2 = (255,200,200) if hover else (max(0,bc[0]-60),max(0,bc[1]-60),max(0,bc[2]-60))
    pygame.draw.rect(surface, bc2, (x, y, w, h), 2, border_radius=7)
    lbl = gf(font_size, bold=True).render(text, True, WHITE)
    surface.blit(lbl, lbl.get_rect(center=(x+w//2, y+h//2)))
    return hover

def draw_gradient_bg(surface):
    for row in range(HEIGHT):
        t = row/HEIGHT
        pygame.draw.line(surface, (int(10+18*t),int(8+10*t),int(35+22*t)), (0,row),(WIDTH,row))

def draw_road_scene(surface, speed):
    global lane_marker_y
    surface.fill(GRASS_COL)
    pygame.draw.rect(surface, SIDE_COL, (0,     0, ROAD_L,       HEIGHT))
    pygame.draw.rect(surface, SIDE_COL, (ROAD_R,0, WIDTH-ROAD_R, HEIGHT))
    pygame.draw.rect(surface, ROAD_COL, (ROAD_L,0, ROAD_W,       HEIGHT))
    pygame.draw.rect(surface, (92,92,106), (ROAD_L,   0, 10, HEIGHT))
    pygame.draw.rect(surface, (92,92,106), (ROAD_R-10,0, 10, HEIGHT))
    pygame.draw.rect(surface, YELLOW_C, (ROAD_L-MRK_W, 0, MRK_W, HEIGHT))
    pygame.draw.rect(surface, YELLOW_C, (ROAD_R,       0, MRK_W, HEIGHT))
    lane_marker_y += speed*2
    if lane_marker_y >= MRK_H*2: lane_marker_y = 0
    for y in range(-MRK_H*2, HEIGHT, MRK_H*2):
        for dx in DIV_XS:
            pygame.draw.rect(surface, WHITE, (dx-MRK_W//2, y+lane_marker_y, MRK_W, MRK_H))

# ═══════════════════════════════════════════════════════════════════════════════
#  HUD
# ═══════════════════════════════════════════════════════════════════════════════
def draw_hud(surface, score, mode, speed, red_warning=False):
    mc = MODE_COLORS[mode]
    rp = pygame.Surface((WIDTH-ROAD_R, HEIGHT), pygame.SRCALPHA)
    rp.fill((12,14,28,215))
    surface.blit(rp, (ROAD_R, 0))
    rx = ROAD_R + 12

    def _blit(txt, fsize, bold, color, pos):
        s = gf(fsize, bold).render(txt, True, color)
        surface.blit(s, pos)

    _blit('SCORE', 12, False, (145,145,178), (rx, 18))
    _blit(str(score), 38, True, YELLOW_C, (rx, 34))
    _blit('BEST',  12, False, (145,145,178), (rx, 82))
    _blit(str(best_score), 22, True, (195,195,120), (rx, 96))
    _blit('MODE',  12, False, (145,145,178), (rx, 132))
    _blit(mode,    20, True,  mc,            (rx, 148))
    _blit('SPEED', 12, False, (145,145,178), (rx, 184))
    _blit(str(speed), 20, True, (95,210,95), (rx, 200))
    if mode == 'Emergency':
        sc = (220,30,30) if (pygame.time.get_ticks()//280)%2==0 else (30,80,220)
        _blit('!! SIREN !!', 14, True, sc, (rx, 238))

    if red_warning:
        warn_col = (255, 60, 60) if (pygame.time.get_ticks()//200)%2==0 else (255,180,0)
        _blit('RED LIGHT!', 13, True, warn_col, (rx, 270))
        _blit('BRAKE NOW!', 12, True, warn_col, (rx, 290))

    lp = pygame.Surface((ROAD_L, HEIGHT), pygame.SRCALPHA)
    lp.fill((12,14,28,215))
    surface.blit(lp, (0, 0))
    lx = 12
    _blit('CONTROLS', 13, True, (145,145,178), (lx, 18))
    for i, hint in enumerate(['<- -> Change lane','Dodge traffic','SPACE  Brake','Y  Play again','N  Quit game']):
        _blit(hint, 12, False, (110,110,145), (lx, 44+i*22))

    _blit('TRAFFIC RULES', 11, True, (145,145,178), (lx, 165))
    _blit('Red = STOP',    11, False, (255,80,80),   (lx, 183))
    _blit('Yellow = SLOW', 11, False, (255,220,0),   (lx, 200))
    _blit('Green = GO',    11, False, (80,220,80),   (lx, 217))

# ═══════════════════════════════════════════════════════════════════════════════
#  SCREEN DRAW FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════
def draw_intro(anim_tick):
    screen.blit(intro_bg, (0,0))
    ov  = pygame.Surface((WIDTH,115), pygame.SRCALPHA); ov.fill((0,0,0,172))
    screen.blit(ov, (0,0))
    ov2 = pygame.Surface((WIDTH,240), pygame.SRCALPHA); ov2.fill((0,0,0,188))
    screen.blit(ov2, (0,HEIGHT-240))
    tf  = gf(66, bold=True)
    sh  = tf.render('Car  Game', True, BLACK)
    screen.blit(sh, sh.get_rect(center=(WIDTH//2+3, 54)))
    t   = tf.render('Car  Game', True, YELLOW_C)
    screen.blit(t,  t.get_rect(center=(WIDTH//2, 51)))
    sub = gf(17).render('Dodge the traffic  —  beat your high score!', True, (208,208,175))
    screen.blit(sub, sub.get_rect(center=(WIDTH//2, 90)))
    bw, bh = 224, 52;  bx = WIDTH//2 - bw//2
    draw_button(screen, 'Play',    (bx, HEIGHT-218, bw, bh))
    draw_button(screen, 'Details', (bx, HEIGHT-155, bw, bh),
                col_normal=(38,78,172), col_hover=(55,108,220))
    draw_button(screen, 'Quit',    (bx, HEIGHT-92,  bw, bh),
                col_normal=(75,75,75),  col_hover=(105,105,105))

def draw_details():
    draw_gradient_bg(screen)
    pw, ph = 530, 430;  px, py = (WIDTH-pw)//2, 55
    pan = pygame.Surface((pw,ph), pygame.SRCALPHA); pan.fill((20,22,55,215))
    screen.blit(pan, (px,py))
    pygame.draw.rect(screen, RED_C, (px,py,pw,ph), 2, border_radius=5)
    h = gf(28,True).render('About This Game', True, YELLOW_C)
    screen.blit(h, h.get_rect(center=(WIDTH//2, py+33)))
    pygame.draw.line(screen, RED_C, (px+30,py+56),(px+pw-30,py+56), 2)
    lines = [
        ('AI 1 Project by',        True),
        ('Abdelrahman Mohammed',      False),
        ('Abdelrahman Mohsen',         False),
        ('Mostafa Makram',         False),
        ('',                           True),
        ('CS Department',              True),
        ('FCIS - Mansoura University', True),
        ('',                           True),
        ('Supervised by',              False),
        ('Dr. Sara El-Metwally',       True),
    ]
    yp = py+72
    for text, bold in lines:
        if not text: yp += 7; continue
        s = gf(17,bold).render(text, True, (255,200,100) if bold else (210,210,240))
        screen.blit(s, s.get_rect(center=(WIDTH//2, yp)));  yp += 26
    prev = _scale_to_height(_raw['car'], 120)
    screen.blit(prev, prev.get_rect(center=(WIDTH//2, py+ph-52)))
    draw_button(screen,'Back',(WIDTH//2-90, py+ph+12, 180,46), font_size=20,
                col_normal=(60,60,60), col_hover=(90,90,90))

def draw_mode_select(anim_tick):
    draw_gradient_bg(screen)
    h = gf(36,True).render('Choose Your Mode', True, YELLOW_C)
    screen.blit(h, h.get_rect(center=(WIDTH//2, 52)))
    pygame.draw.line(screen, RED_C, (WIDTH//2-245,78),(WIDTH//2+245,78), 2)
    entries = [
        ('Normal',    'Classic speed — dodge the traffic — great for beginners', (80,102,640,108)),
        ('Speedy',    'Faster traffic — push your limits — speed up!',        (80,222,640,108)),
        ('Emergency', 'MAX SPEED — lights, siren, ambulance or police car!',  (80,342,640,108)),
    ]
    mpx, mpy = pygame.mouse.get_pos()
    for label, desc, (bx,by,bw,bh) in entries:
        hover = bx<=mpx<=bx+bw and by<=mpy<=by+bh
        mc = MODE_COLORS[label]
        pygame.draw.rect(screen, (50,50,108) if hover else (28,28,68),
                         (bx,by,bw,bh), border_radius=8)
        pygame.draw.rect(screen, mc, (bx,by,bw,bh), 3 if hover else 2, border_radius=8)
        pygame.draw.rect(screen, mc, (bx,by,8,bh), border_radius=4)
        lt = gf(24,True).render(label, True, mc)
        screen.blit(lt, lt.get_rect(midleft=(bx+24, by+38)))
        dt = gf(14).render(desc, True, (172,172,215))
        screen.blit(dt, dt.get_rect(midleft=(bx+24, by+76)))
    draw_button(screen,'Back',(WIDTH//2-90,472,180,46),font_size=20,
                col_normal=(60,60,60),col_hover=(90,90,90))

def draw_car_select(mode, anim_tick):
    draw_gradient_bg(screen)
    mc = MODE_COLORS[mode]
    mpx, mpy = pygame.mouse.get_pos()
    h = gf(32,True).render('Select Your Car', True, WHITE)
    screen.blit(h, h.get_rect(center=(WIDTH//2, 42)))
    ml = gf(18).render(f'Mode:  {mode}', True, mc)
    screen.blit(ml, ml.get_rect(center=(WIDTH//2, 74)))
    pygame.draw.line(screen, mc, (WIDTH//2-220,92),(WIDTH//2+220,92), 2)

    options = CAR_OPTIONS[mode]
    n = len(options);  card_w, card_h = 200, 310;  gap = 30
    total_w = n*card_w + (n-1)*gap;  start_x = (WIDTH-total_w)//2

    for i, opt in enumerate(options):
        cx_c = start_x + i*(card_w+gap);  cy_c = 110
        hover = cx_c<=mpx<=cx_c+card_w and cy_c<=mpy<=cy_c+card_h
        pygame.draw.rect(screen, (50,50,112) if hover else (26,26,62),
                         (cx_c,cy_c,card_w,card_h), border_radius=10)
        pygame.draw.rect(screen, mc if hover else (75,75,118),
                         (cx_c,cy_c,card_w,card_h), 2, border_radius=10)
        raw = make_car_sprite(opt['type'], opt['color'], anim_tick)
        ph  = 138;  pw = max(1, int(ph*raw.get_width()/raw.get_height()))
        prev = pygame.transform.smoothscale(raw, (pw, ph))
        screen.blit(prev, prev.get_rect(center=(cx_c+card_w//2, cy_c+92)))
        ns = gf(17,True).render(opt['name'], True, WHITE)
        screen.blit(ns, ns.get_rect(center=(cx_c+card_w//2, cy_c+182)))
        ds = gf(12).render(opt['desc'], True, (165,165,208))
        screen.blit(ds, ds.get_rect(center=(cx_c+card_w//2, cy_c+204)))
        draw_button(screen,'Select',
                    (cx_c+card_w//2-65, cy_c+228, 130, 40), font_size=15,
                    col_normal=mc, col_hover=tuple(min(255,c+45) for c in mc))
    draw_button(screen,'Back',(WIDTH//2-90,442,180,44),font_size=20,
                col_normal=(60,60,60),col_hover=(90,90,90))

# ═══════════════════════════════════════════════════════════════════════════════
#  TRAFFIC LIGHT RULE ENFORCEMENT
# ═══════════════════════════════════════════════════════════════════════════════
TL_STOP_ZONE = 28  # pixels above/below the light's mid-Y that count as the stop zone

def player_runs_red(player_rect, tlo, speed_f):
    """Return True if player is crossing a red light at speed > threshold."""
    if tlo['color'] != 'red':
        return False
    light_mid_y = tlo['y'] + TL_H // 2
    zone_top    = light_mid_y - TL_STOP_ZONE
    zone_bottom = light_mid_y + TL_STOP_ZONE
    in_zone = player_rect.bottom >= zone_top and player_rect.top <= zone_bottom
    return in_zone and speed_f > 1.5

# ═══════════════════════════════════════════════════════════════════════════════
#  GAME LOOP
# ═══════════════════════════════════════════════════════════════════════════════
def run_game(mode, car_type, car_color):
    global lane_marker_y, best_score
    speed_map    = {'Normal':3, 'Speedy':6, 'Emergency':10}
    veh_map      = {'Normal':3, 'Speedy':4, 'Emergency':5}
    speed_start  = speed_map[mode]
    max_veh      = veh_map[mode]
    score        = 0
    gameover     = False
    gameover_reason = ''
    show_crash   = False
    lane_marker_y= 0

    speed_f      = float(speed_start)
    SPEED_MAX    = float(speed_start)
    ACCEL        = 0.04
    DECEL        = 0.12

    TL_INTERVAL  = 10 * FPS
    tl_timer     = TL_INTERVAL - 1   # first light spawns soon
    tl_objects   = []
    TL_X_LEFT    = ROAD_L - TL_W - 4
    TL_X_RIGHT   = ROAD_R + 4
    TL_SPAWN_Y   = -TL_H - 20

    # Color cycle durations in frames: red->yellow 2s, yellow->green 2s, green->red 5s
    TL_CYCLE = {
        'red':    {'next': 'yellow', 'frames': 2 * FPS},
        'yellow': {'next': 'green',  'frames': 2 * FPS},
        'green':  {'next': 'red',    'frames': 5 * FPS},
    }

    _uid_counter = [0]
    def next_uid():
        _uid_counter[0] += 1
        return _uid_counter[0]

    red_checked_ids = set()   # ids of red lights we've already flagged

    active_npc_images = npc_images_emergency if mode == 'Emergency' else npc_images_normal

    pg  = pygame.sprite.Group()
    vg  = pygame.sprite.Group()
    player = PlayerVehicle(PLAYER_X, PLAYER_Y, car_type, car_color)
    pg.add(player)
    crash_rect = crash_img.get_rect()

    running = True
    while running:
        clock.tick(FPS)
        speed = max(0, int(round(speed_f)))

        # Red warning: any red light on screen above the player
        red_warning = any(
            tlo['color'] == 'red' and 0 < tlo['y'] < PLAYER_Y - 40
            for tlo in tl_objects
        )

        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit(); exit()
            if event.type == KEYDOWN:
                moved = False
                if event.key == K_LEFT and player.rect.centerx > LANES[0]:
                    player.rect.x -= LANE_W;  moved = True
                elif event.key == K_RIGHT and player.rect.centerx < LANES[3]:
                    player.rect.x += LANE_W;  moved = True
                if moved:
                    for veh in vg:
                        if pygame.sprite.collide_rect(player, veh):
                            gameover = True;  show_crash = True
                            gameover_reason = 'You crashed into a vehicle!'
                            if event.key == K_LEFT:
                                player.rect.left = veh.rect.right
                                crash_rect.center = (player.rect.left,
                                    (player.rect.centery+veh.rect.centery)//2)
                            else:
                                player.rect.right = veh.rect.left
                                crash_rect.center = (player.rect.right,
                                    (player.rect.centery+veh.rect.centery)//2)

        keys = pygame.key.get_pressed()
        if keys[K_SPACE]:
            speed_f = max(0.0, speed_f - DECEL)
        else:
            speed_f = min(SPEED_MAX, speed_f + ACCEL)

        # Spawn traffic lights
        tl_timer += 1
        if tl_timer >= TL_INTERVAL:
            tl_timer = 0
            start_col = random.choice(['red', 'yellow', 'green'])
            uid = next_uid()
            for tx in (TL_X_LEFT, TL_X_RIGHT):
                tl_objects.append({
                    'surf':        get_tl_image(start_col),
                    'x':           tx,
                    'y':           float(TL_SPAWN_Y),
                    'color':       start_col,
                    'color_timer': 0,   # frames spent on current color
                    'uid':         uid,
                })

        player.tick()

        draw_road_scene(screen, speed)

        if mode == 'Emergency':
            fc = (218,30,30) if (pygame.time.get_ticks()//260)%2==0 else (30,78,218)
            pygame.draw.rect(screen, fc, (ROAD_L-12, 0, ROAD_W+24, HEIGHT), 5)

        # Draw stop line for red lights + countdown for all colors
        for tlo in tl_objects:
            if 0 < tlo['y'] < HEIGHT:
                frames_left = TL_CYCLE[tlo['color']]['frames'] - tlo['color_timer']
                secs_left   = max(1, (frames_left + FPS - 1) // FPS)
                col_label_colors = {'red': (255,80,80), 'yellow': (255,220,0), 'green': (80,220,80)}
                cd_surf = gf(16, True).render(f'{secs_left}s', True, col_label_colors[tlo['color']])
                screen.blit(cd_surf, cd_surf.get_rect(center=(int(tlo['x']) + TL_W//2,
                                                               int(tlo['y']) + TL_H + 12)))
            if tlo['color'] == 'red' and 0 < tlo['y'] < HEIGHT:
                line_y = int(tlo['y'] + TL_H // 2)
                if (pygame.time.get_ticks() // 200) % 2 == 0:
                    pygame.draw.rect(screen, (255, 0, 0),
                                     (ROAD_L, line_y - 4, ROAD_W, 8))
                    stop_s = gf(14, True).render('S T O P', True, WHITE)
                    screen.blit(stop_s, stop_s.get_rect(center=(ROAD_L + ROAD_W//2, line_y)))

        # Move, cycle color, and draw traffic lights + check red-light crash
        surviving = []
        for tlo in tl_objects:
            tlo['y'] += speed

            # ── Color cycling ────────────────────────────────────────────
            tlo['color_timer'] += 1
            cycle_info = TL_CYCLE[tlo['color']]
            if tlo['color_timer'] >= cycle_info['frames']:
                tlo['color']       = cycle_info['next']
                tlo['color_timer'] = 0
                tlo['surf']        = get_tl_image(tlo['color'])
                if tlo['color'] != 'red':
                    red_checked_ids.discard(tlo['uid'])

            if tlo['y'] < HEIGHT:
                screen.blit(tlo['surf'], (int(tlo['x']), int(tlo['y'])))
                surviving.append(tlo)

                # Red light enforcement — only penalise once per red phase
                if (not gameover
                        and tlo['color'] == 'red'
                        and tlo['uid'] not in red_checked_ids
                        and player_runs_red(player.rect, tlo, speed_f)):
                    gameover = True
                    show_crash = True
                    gameover_reason = 'You ran a RED light!'
                    crash_rect.center = player.rect.center
                    red_checked_ids.add(tlo['uid'])
            else:
                red_checked_ids.discard(tlo.get('uid'))

        tl_objects = surviving

        pg.draw(screen)

        if len(vg) < max_veh:
            can = all(v.rect.top >= v.rect.height*1.5 for v in vg)
            if can:
                vg.add(Vehicle(random.choice(active_npc_images), random.choice(LANES), HEIGHT//-2))

        for veh in list(vg):
            veh.rect.y += speed
            if veh.rect.top >= HEIGHT:
                veh.kill();  score += 1
                if score > best_score: best_score = score
                if score % 5 == 0:
                    SPEED_MAX += 1
                    speed_f = min(speed_f + 1, SPEED_MAX)

        vg.draw(screen)

        hits = pygame.sprite.spritecollide(player, vg, True)
        if hits:
            gameover = True;  show_crash = True
            gameover_reason = 'You crashed into a vehicle!'
            crash_rect.center = (player.rect.centerx, player.rect.top)

        if show_crash:
            screen.blit(crash_img, crash_rect)

        bar_x, bar_y, bar_w, bar_h = ROAD_R + 14, HEIGHT - 60, 12, 50
        pygame.draw.rect(screen, (40,40,60), (bar_x, bar_y, bar_w, bar_h), border_radius=4)
        fill_h = int(bar_h * (speed_f / max(1, SPEED_MAX)))
        fill_col = (30,200,30) if not keys[K_SPACE] else (200,80,30)
        pygame.draw.rect(screen, fill_col,
                         (bar_x, bar_y + bar_h - fill_h, bar_w, fill_h), border_radius=4)
        sp_lbl = gf(11).render('SPD', True, (160,160,200))
        screen.blit(sp_lbl, (bar_x - 2, bar_y - 14))

        draw_hud(screen, score, mode, speed, red_warning=red_warning)

        hint_col = (200,80,30) if keys[K_SPACE] else (130,130,160)
        sp_hint = gf(12).render('SPACE = brake', True, hint_col)
        screen.blit(sp_hint, (ROAD_L + 6, HEIGHT - 18))

        if gameover:
            ov = pygame.Surface((WIDTH,HEIGHT), pygame.SRCALPHA); ov.fill((0,0,0,145))
            screen.blit(ov, (0,0))
            gx,gy,gw,gh = WIDTH//2-245, HEIGHT//2-110, 490, 220
            pygame.draw.rect(screen, DARK_UI, (gx,gy,gw,gh), border_radius=12)
            pygame.draw.rect(screen, RED_C,   (gx,gy,gw,gh), 3,  border_radius=12)
            go = gf(34,True).render('GAME  OVER', True, RED_C)
            screen.blit(go, go.get_rect(center=(WIDTH//2, HEIGHT//2-72)))
            reason_surf = gf(17).render(gameover_reason, True, (255,160,60))
            screen.blit(reason_surf, reason_surf.get_rect(center=(WIDTH//2, HEIGHT//2-36)))
            sc_txt = gf(22).render(f'Score:  {score}', True, YELLOW_C)
            screen.blit(sc_txt, sc_txt.get_rect(center=(WIDTH//2, HEIGHT//2+8)))
            hint = gf(15).render('Press  Y  to play again    or    N  to quit', True, (195,195,195))
            screen.blit(hint, hint.get_rect(center=(WIDTH//2, HEIGHT//2+50)))

        pygame.display.update()

        while gameover:
            clock.tick(FPS)
            for event in pygame.event.get():
                if event.type == QUIT:
                    pygame.quit(); exit()
                if event.type == KEYDOWN:
                    if event.key == K_y:
                        gameover=False; show_crash=False; gameover_reason=''
                        speed_f=float(speed_start); SPEED_MAX=float(speed_start)
                        score=0; lane_marker_y=0; vg.empty()
                        tl_objects.clear(); tl_timer=TL_INTERVAL-1
                        red_checked_ids.clear()
                        player.rect.center=(PLAYER_X,PLAYER_Y)
                    elif event.key == K_n:
                        gameover=False; running=False

# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN STATE MACHINE
# ═══════════════════════════════════════════════════════════════════════════════
STATE_INTRO      = 'intro'
STATE_DETAILS    = 'details'
STATE_MODES      = 'modes'
STATE_CAR_SELECT = 'car_select'

state         = STATE_INTRO
anim_tick     = 0
selected_mode = None

while True:
    clock.tick(FPS)
    anim_tick += 1

    for event in pygame.event.get():
        if event.type == QUIT:
            pygame.quit(); exit()

        if event.type == MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            BW, BH = 224, 52;  BX = WIDTH//2 - BW//2

            if state == STATE_INTRO:
                if BX<=mx<=BX+BW and HEIGHT-218<=my<=HEIGHT-166:
                    state = STATE_MODES
                elif BX<=mx<=BX+BW and HEIGHT-155<=my<=HEIGHT-103:
                    state = STATE_DETAILS
                elif BX<=mx<=BX+BW and HEIGHT-92<=my<=HEIGHT-40:
                    pygame.quit(); exit()

            elif state == STATE_DETAILS:
                pw,ph = 530,430;  px,py = (WIDTH-pw)//2, 55
                bk_y = py+ph+12
                if WIDTH//2-90<=mx<=WIDTH//2+90 and bk_y<=my<=bk_y+46:
                    state = STATE_INTRO

            elif state == STATE_MODES:
                rects = [('Normal',80,102,640,108),
                         ('Speedy',80,222,640,108),
                         ('Emergency',80,342,640,108)]
                for label,rx,ry,rw,rh in rects:
                    if rx<=mx<=rx+rw and ry<=my<=ry+rh:
                        selected_mode = label
                        state = STATE_CAR_SELECT
                        break
                if WIDTH//2-90<=mx<=WIDTH//2+90 and 472<=my<=518:
                    state = STATE_INTRO

            elif state == STATE_CAR_SELECT:
                options = CAR_OPTIONS[selected_mode]
                n = len(options);  card_w=200;  gap=30
                total_w = n*card_w+(n-1)*gap;  start_x = (WIDTH-total_w)//2
                clicked = False
                for i,opt in enumerate(options):
                    cx_c = start_x + i*(card_w+gap)
                    bx_c = cx_c+card_w//2-65;  by_c = 110+228
                    if bx_c<=mx<=bx_c+130 and by_c<=my<=by_c+40:
                        run_game(selected_mode, opt['type'], opt['color'])
                        state=STATE_INTRO;  anim_tick=0;  clicked=True;  break
                if not clicked and WIDTH//2-90<=mx<=WIDTH//2+90 and 442<=my<=486:
                    state = STATE_MODES

    if   state == STATE_INTRO:       draw_intro(anim_tick)
    elif state == STATE_DETAILS:     draw_details()
    elif state == STATE_MODES:       draw_mode_select(anim_tick)
    elif state == STATE_CAR_SELECT:  draw_car_select(selected_mode, anim_tick)

    pygame.display.update()
