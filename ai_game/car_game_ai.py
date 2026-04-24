# -*- coding: utf-8 -*-
"""
Car Game Enhanced — AI Edition
================================
ORIGINAL GAME by: Abdelrahman Mohammed, Abdelrahman Mohsen, Mostafa Makram
AI Algorithms added:
  • Heuristic Evaluation    (Lecture 04 – Heuristics & Local Search)
  • Hill Climbing           (Lecture 05 – Hill Climbing)
  • Minimax / Adversarial   (Lecture 06 – Adversarial Search)
  • Genetic Algorithm       (Lecture 05 – Genetic Algorithm)

How they are used:
  ─ Heuristic:          Scores each lane for the AI driver (danger, distance, traffic density)
  ─ Hill Climbing:      AI picks the locally best lane move at each step
  ─ Minimax (depth-2):  AI looks 2 moves ahead assuming NPC vehicles move into worst positions
  ─ Genetic Algorithm:  Evolves NPC spawn "genome" (speed, gap, density) to challenge the player
"""

import pygame
from pygame.locals import *
import random, math, copy

pygame.init()

# ═══════════════════════════════════════════════════════════════════════════════
#  WINDOW & ROAD GEOMETRY
# ═══════════════════════════════════════════════════════════════════════════════
WIDTH, HEIGHT = 800, 700
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption('Car Game Enhanced — AI Edition')

ROAD_L  = 200
ROAD_R  = 600
ROAD_W  = ROAD_R - ROAD_L
LANE_W  = ROAD_W // 4
LANES   = [ROAD_L + LANE_W//2 + i*LANE_W for i in range(4)]   # [250,350,450,550]
DIV_XS  = [ROAD_L + LANE_W*(i+1)          for i in range(3)]
MRK_W, MRK_H = 10, 50

PLAYER_X = LANES[1]
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
AI_COLOR  = (  0, 220, 180)   # teal highlight for AI elements

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
        for name in ('segoeui','calibri','trebuchetms','arial'):
            if pygame.font.match_font(name):
                _fcache[key] = pygame.font.SysFont(name, size, bold=bold)
                return _fcache[key]
        _fcache[key] = pygame.font.Font(None, size)
    return _fcache[key]

# ═══════════════════════════════════════════════════════════════════════════════
#  ASSETS
# ═══════════════════════════════════════════════════════════════════════════════
intro_bg = pygame.transform.smoothscale(
    pygame.image.load('images/intro_car.png'), (WIDTH, HEIGHT))

_raw = {
    'car':          pygame.image.load('images/car.png'),
    'pickup_truck': pygame.image.load('images/pickup_truck.png'),
    'semi_trailer': pygame.image.load('images/semi_trailer.png'),
    'taxi':         pygame.image.load('images/taxi.png'),
    'van':          pygame.image.load('images/van.png'),
    'ambulance':    pygame.image.load('images/ambulance.png'),
}

TL_W, TL_H = 64, 160
_TL_IMAGES = {
    'red':    pygame.transform.smoothscale(
                  pygame.image.load('images/tl_red.png').convert_alpha(),    (TL_W, TL_H)),
    'yellow': pygame.transform.smoothscale(
                  pygame.image.load('images/tl_yellow.png').convert_alpha(), (TL_W, TL_H)),
    'green':  pygame.transform.smoothscale(
                  pygame.image.load('images/tl_green.png').convert_alpha(),  (TL_W, TL_H)),
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
    flash  = (anim_tick // 8) % 2
    lc = left_col  if flash == 0 else right_col
    rc = right_col if flash == 0 else left_col
    bar_w = max(6, w // 4);  bar_h = max(4, int(result.get_height() * 0.04))
    pygame.draw.rect(result, lc, (2,            2, bar_w, bar_h), border_radius=2)
    pygame.draw.rect(result, rc, (w-bar_w-2,    2, bar_w, bar_h), border_radius=2)
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
        surf = _add_flash_lights(surf, anim_tick, (220,30,30),  (30,80,220))
    elif car_type == 'police':
        surf = _add_flash_lights(surf, anim_tick, (30,80,220),  (220,30,30))
    return surf

npc_images_normal    = [_scale_to_height(_raw[k], 80)
                        for k in ('car','pickup_truck','semi_trailer','taxi','van')]
npc_images_emergency = [_scale_to_height(_raw['ambulance'], 80)]

crash_img = pygame.transform.smoothscale(
    pygame.image.load('images/crash.png'), (90, 90))

# ═══════════════════════════════════════════════════════════════════════════════
#  CAR OPTIONS
# ═══════════════════════════════════════════════════════════════════════════════
CAR_OPTIONS = {
    'Normal': [
        {'name': 'City Sedan', 'type': 'sedan',  'color': (210,42,42),  'desc': 'Classic & reliable'},
        {'name': 'Family SUV', 'type': 'suv',    'color': (40,100,220), 'desc': 'Strong & spacious'},
        {'name': 'City Coupe', 'type': 'sports', 'color': (175,175,190),'desc': 'Sleek daily driver'},
    ],
    'Speedy': [
        {'name': 'Sports GT',  'type': 'sports', 'color': (255,110,0),  'desc': 'Track-tuned racer'},
        {'name': 'F1 Racer',   'type': 'f1',     'color': (175,28,215), 'desc': 'Open-wheel beast'},
        {'name': 'Muscle Car', 'type': 'muscle', 'color': (240,200,0),  'desc': 'Raw American power'},
    ],
    'Emergency': [
        {'name': 'Ambulance',  'type': 'ambulance','color': (230,230,230),'desc': 'Racing to save lives'},
        {'name': 'Police Car', 'type': 'police',   'color': (30,50,160),  'desc': 'Enforce the law'},
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
#  ██████████  AI ALGORITHMS  ██████████
# ═══════════════════════════════════════════════════════════════════════════════

# ─── Lecture 04 / Lecture 06: Heuristic lane-safety evaluator ────────────────
def heuristic_lane_score(lane_idx, vehicles, tl_objects, player_y, speed_f):
    """
    Returns a safety score for a given lane (higher = safer).
    Combines:
      • Closest vehicle danger  (inverse distance penalty)
      • Lane density            (count of vehicles in lane)
      • Red-light proximity     (hard penalty near red)
    """
    lane_x = LANES[lane_idx]
    score  = 100.0

    # ── Vehicle danger in this lane ──────────────────────────────────────────
    for veh in vehicles:
        veh_lane = _x_to_lane(veh.rect.centerx)
        if veh_lane == lane_idx:
            dy = player_y - veh.rect.centery          # positive = veh is above player
            if 0 < dy < 200:                          # vehicle is ahead (above)
                score -= (200 - dy) * 0.8             # nearer → heavier penalty
            elif -80 < dy <= 0:                       # vehicle just below → also risky
                score -= 40
            score -= 5                                # density penalty

    # ── Red-light penalty ────────────────────────────────────────────────────
    for tlo in tl_objects:
        if tlo['color'] == 'red' and speed_f > 1.5:
            light_y = tlo['y'] + TL_H // 2
            if 0 < light_y - player_y < 150:
                score -= 60

    return score

def _x_to_lane(x):
    """Convert pixel x-coordinate to lane index 0-3."""
    for i, lx in enumerate(LANES):
        if abs(x - lx) < LANE_W // 2:
            return i
    return min(range(4), key=lambda i: abs(LANES[i] - x))

# ─── Lecture 05: Hill Climbing — pick best immediate lane move ────────────────
def hill_climbing_move(current_lane, vehicles, tl_objects, player_y, speed_f):
    """
    Evaluate neighbours (stay, left, right) and greedily move to the best.
    This is steepest-ascent hill climbing on the lane-safety landscape.
    """
    candidates = [current_lane]
    if current_lane > 0:         candidates.append(current_lane - 1)
    if current_lane < 3:         candidates.append(current_lane + 1)

    best_lane  = current_lane
    best_score = heuristic_lane_score(current_lane, vehicles, tl_objects, player_y, speed_f)

    for lane in candidates:
        s = heuristic_lane_score(lane, vehicles, tl_objects, player_y, speed_f)
        if s > best_score:
            best_score = s
            best_lane  = lane

    return best_lane

# ─── Lecture 06 / 07: Minimax (depth-2) with alpha-beta pruning ──────────────
def minimax_move(current_lane, vehicles, tl_objects, player_y, speed_f, depth=2):
    """
    AI (Maximizer) picks the lane that maximises safety assuming the
    adversary (NPC traffic) will move into the worst-case configuration.

    Minimax tree:
      Level 0 (MAX): AI chooses among left / stay / right
      Level 1 (MIN): "adversary" picks the npc arrangement that hurts AI most
      Level 2 (MAX): AI picks best response at depth 2

    Returns the best lane index.
    """
    def _simulate_npc_worst(lane_idx, vehs, step):
        """Adversary: imagine every NPC shifts toward the AI's chosen lane."""
        simulated = []
        for v in vehs:
            vl = _x_to_lane(v.rect.centerx)
            # Adversary tries to crowd the lane the AI is heading to
            if vl != lane_idx and step == 1:
                new_x = LANES[lane_idx]
            else:
                new_x = v.rect.centerx
            # Advance NPCs downward by one speed step
            new_y = v.rect.centery + speed_f * 6
            simulated.append((new_x, new_y))
        return simulated

    def _score_from_sim(lane_idx, sim_vehs, tlos, py):
        score = 100.0
        for (vx, vy) in sim_vehs:
            vl = _x_to_lane(vx)
            if vl == lane_idx:
                dy = py - vy
                if 0 < dy < 200:
                    score -= (200 - dy) * 0.8
                elif -80 < dy <= 0:
                    score -= 40
                score -= 5
        for tlo in tlos:
            if tlo['color'] == 'red' and speed_f > 1.5:
                light_y = tlo['y'] + TL_H // 2
                if 0 < light_y - py < 150:
                    score -= 60
        return score

    def _max_node(lane, vehs_sim, tlos, py, d, alpha, beta):
        if d == 0:
            return _score_from_sim(lane, vehs_sim, tlos, py)
        cands = [lane]
        if lane > 0: cands.append(lane - 1)
        if lane < 3: cands.append(lane + 1)
        val = -math.inf
        for nxt in cands:
            val = max(val, _min_node(nxt, vehs_sim, tlos, py, d, alpha, beta))
            alpha = max(alpha, val)
            if alpha >= beta:
                break   # β cut-off (alpha-beta pruning — Lecture 07)
        return val

    def _min_node(lane, vehs_sim, tlos, py, d, alpha, beta):
        worst = _simulate_npc_worst(lane, [type('o',(object,),{'rect':type('r',(object,),
                {'centerx':vx,'centery':vy})()})() for (vx,vy) in vehs_sim], d)
        return _max_node(lane, worst, tlos, py, d-1, alpha, beta)

    # Convert sprite group → list of (x,y)
    vehs_pos = [(v.rect.centerx, v.rect.centery) for v in vehicles]

    cands = [current_lane]
    if current_lane > 0: cands.append(current_lane - 1)
    if current_lane < 3: cands.append(current_lane + 1)

    best_lane  = current_lane
    best_val   = -math.inf
    alpha, beta = -math.inf, math.inf

    for lane in cands:
        val = _min_node(lane, vehs_pos, tl_objects, player_y, depth, alpha, beta)
        if val > best_val:
            best_val  = val
            best_lane = lane
        alpha = max(alpha, best_val)

    return best_lane

# ─── Lecture 05: Genetic Algorithm — adaptive NPC difficulty ─────────────────
class GADifficultyController:
    """
    Evolves a population of 'difficulty genomes' each round.
    Genome = [speed_bonus, spawn_rate_multiplier, max_vehicles_bonus]
    Fitness = how close to the target_challenge_score the player's score was.
    """
    POP_SIZE   = 8
    GENS       = 3          # quick in-game evolution
    MUT_RATE   = 0.3
    TARGET     = 12         # target score to keep game balanced

    def __init__(self):
        self.population = [self._random_genome() for _ in range(self.POP_SIZE)]
        self.best_genome = self.population[0]
        self.generation  = 0

    def _random_genome(self):
        return {
            'speed_bonus':     random.uniform(0.0, 2.0),
            'spawn_mult':      random.uniform(0.5, 1.5),
            'max_veh_bonus':   random.randint(0, 2),
        }

    def _fitness(self, genome, last_score):
        """Fitness: penalise deviation from target. Best genome keeps game near target."""
        challenge = genome['speed_bonus'] * 0.6 + genome['spawn_mult'] + genome['max_veh_bonus'] * 0.4
        # We want a score close to TARGET — genome that produced near-target score wins
        return -abs(last_score - self.TARGET) + challenge * 0.1

    def _crossover(self, a, b):
        child = {}
        for key in a:
            child[key] = a[key] if random.random() < 0.5 else b[key]
        return child

    def _mutate(self, genome):
        g = genome.copy()
        if random.random() < self.MUT_RATE:
            g['speed_bonus']   = max(0, g['speed_bonus']   + random.uniform(-0.3, 0.3))
        if random.random() < self.MUT_RATE:
            g['spawn_mult']    = max(0.3, g['spawn_mult']  + random.uniform(-0.2, 0.2))
        if random.random() < self.MUT_RATE:
            g['max_veh_bonus'] = max(0, g['max_veh_bonus'] + random.randint(-1, 1))
        return g

    def evolve(self, last_score):
        """Run one generation after each game round."""
        scored = [(self._fitness(g, last_score), g) for g in self.population]
        scored.sort(key=lambda x: x[0], reverse=True)
        survivors = [g for _, g in scored[:self.POP_SIZE//2]]
        children  = []
        while len(children) < self.POP_SIZE - len(survivors):
            a, b = random.sample(survivors, 2)
            children.append(self._mutate(self._crossover(a, b)))
        self.population = survivors + children
        self.best_genome = self.population[0]
        self.generation += 1

    def get_params(self):
        g = self.best_genome
        return {
            'speed_bonus':   g['speed_bonus'],
            'spawn_mult':    g['spawn_mult'],
            'max_veh_bonus': int(g['max_veh_bonus']),
        }

# Shared GA controller across game sessions
ga_controller = GADifficultyController()

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
        pygame.draw.line(surface,
            (int(10+18*t), int(8+10*t), int(35+22*t)), (0,row), (WIDTH,row))

def draw_road_scene(surface, speed):
    global lane_marker_y
    surface.fill(GRASS_COL)
    pygame.draw.rect(surface, SIDE_COL, (0,     0, ROAD_L,       HEIGHT))
    pygame.draw.rect(surface, SIDE_COL, (ROAD_R,0, WIDTH-ROAD_R, HEIGHT))
    pygame.draw.rect(surface, ROAD_COL, (ROAD_L,0, ROAD_W,       HEIGHT))
    pygame.draw.rect(surface, (92,92,106), (ROAD_L,    0, 10, HEIGHT))
    pygame.draw.rect(surface, (92,92,106), (ROAD_R-10, 0, 10, HEIGHT))
    pygame.draw.rect(surface, YELLOW_C, (ROAD_L-MRK_W, 0, MRK_W, HEIGHT))
    pygame.draw.rect(surface, YELLOW_C, (ROAD_R,       0, MRK_W, HEIGHT))
    lane_marker_y += speed*2
    if lane_marker_y >= MRK_H*2: lane_marker_y = 0
    for y in range(-MRK_H*2, HEIGHT, MRK_H*2):
        for dx in DIV_XS:
            pygame.draw.rect(surface, WHITE, (dx-MRK_W//2, y+lane_marker_y, MRK_W, MRK_H))

# ═══════════════════════════════════════════════════════════════════════════════
#  HUD (with AI panel)
# ═══════════════════════════════════════════════════════════════════════════════
def draw_hud(surface, score, mode, speed, red_warning=False,
             ai_mode=False, ai_algo='', ai_lane_scores=None,
             ga_gen=0, ga_params=None, prox_reason='', emergency_brake=False):
    mc = MODE_COLORS[mode]
    # Right panel
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
    if emergency_brake:
        ec = (255,40,40) if (pygame.time.get_ticks()//80)%2==0 else (255,200,0)
        _blit('!! COLLISION !!', 13, True, ec,          (rx, 258))
        _blit('EMERGENCY STOP',  12, True, (255,120,0), (rx, 278))
    elif red_warning:
        warn_col = (255,60,60) if (pygame.time.get_ticks()//200)%2==0 else (255,180,0)
        _blit('RED LIGHT!', 13, True, warn_col, (rx, 258))
        _blit('BRAKE NOW!', 12, True, warn_col, (rx, 278))
    elif prox_reason:
        pcol = (255, 60, 60) if prox_reason == 'RED LIGHT'      else \
               (255,200,  0) if prox_reason == 'YELLOW LIGHT'   else \
               (120,255,120) if prox_reason == 'GREEN→RED SOON' else \
               (255,140,  0)   # VEHICLE AHEAD
        tick_on = (pygame.time.get_ticks()//300)%2==0
        if tick_on:
            _blit('AUTO-SLOW',  12, True,  pcol, (rx, 258))
            short = {
                'RED LIGHT':      'Red light',
                'YELLOW LIGHT':   'Yellow light',
                'GREEN→RED SOON': 'Green→Red soon',
                'VEHICLE AHEAD':  'Car ahead',
            }
            _blit(short.get(prox_reason, prox_reason), 11, False, pcol, (rx, 278))

    # ── AI Panel (bottom of right panel) ─────────────────────────────────────
    if ai_mode:
        ay = 310
        pygame.draw.line(surface, AI_COLOR, (rx, ay), (WIDTH-8, ay), 1)
        _blit('AI ACTIVE', 13, True, AI_COLOR, (rx, ay+6))
        _blit(ai_algo[:14], 11, False, (160,230,200), (rx, ay+24))
        if ai_lane_scores:
            _blit('Lane Safety:', 10, False, (140,140,170), (rx, ay+42))
            for i, s in enumerate(ai_lane_scores):
                bar_h = max(0, int(s / 100 * 30))
                bar_x = rx + i * 22
                bar_y = ay + 90
                col   = (0,200,100) if s >= 60 else (200,180,0) if s >= 30 else (200,50,50)
                pygame.draw.rect(surface, (40,40,70), (bar_x, bar_y-30, 16, 30))
                pygame.draw.rect(surface, col,        (bar_x, bar_y-bar_h, 16, bar_h))
                pygame.draw.rect(surface, (80,80,120),(bar_x, bar_y-30, 16, 30), 1)
                lbl = gf(9).render(str(i+1), True, WHITE)
                surface.blit(lbl, lbl.get_rect(center=(bar_x+8, bar_y+8)))

        pygame.draw.line(surface, AI_COLOR, (rx, ay+110), (WIDTH-8, ay+110), 1)
        _blit('GA DIFFICULTY', 10, True, AI_COLOR, (rx, ay+118))
        _blit(f'Gen: {ga_gen}', 10, False, (160,230,200), (rx, ay+134))
        if ga_params:
            _blit(f'Spd+{ga_params["speed_bonus"]:.1f}', 10, False, (200,180,120), (rx, ay+150))
            _blit(f'Veh+{ga_params["max_veh_bonus"]}',   10, False, (200,180,120), (rx, ay+166))

    # Left panel
    lp = pygame.Surface((ROAD_L, HEIGHT), pygame.SRCALPHA)
    lp.fill((12,14,28,215))
    surface.blit(lp, (0, 0))
    lx = 12
    _blit('CONTROLS', 13, True, (145,145,178), (lx, 18))
    hints = ['<- -> Lane','Dodge traffic','SPACE  Brake',
             'A  AI toggle','Y  Play again','N  Quit']
    for i, hint in enumerate(hints):
        _blit(hint, 12, False, (110,110,145), (lx, 44+i*22))
    _blit('TRAFFIC RULES', 11, True, (145,145,178), (lx, 185))
    _blit('Red = STOP',    11, False, (255,80,80),   (lx, 203))
    _blit('Yellow = SLOW', 11, False, (255,220,0),   (lx, 220))
    _blit('Green = GO',    11, False, (80,220,80),   (lx, 237))

    if ai_mode:
        ai_label = gf(11, True).render('AI DRIVING', True, AI_COLOR)
        surface.blit(ai_label, ai_label.get_rect(center=(ROAD_L//2, 268)))

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
    sh  = tf.render('Car  Game  AI', True, BLACK)
    screen.blit(sh, sh.get_rect(center=(WIDTH//2+3, 54)))
    t   = tf.render('Car  Game  AI', True, YELLOW_C)
    screen.blit(t,  t.get_rect(center=(WIDTH//2, 51)))
    sub = gf(17).render('Minimax · Hill Climbing · Heuristics · Genetic Algorithm', True, AI_COLOR)
    screen.blit(sub, sub.get_rect(center=(WIDTH//2, 90)))
    bw, bh = 224, 52;  bx = WIDTH//2 - bw//2
    draw_button(screen, 'Play',    (bx, HEIGHT-218, bw, bh))
    draw_button(screen, 'Details', (bx, HEIGHT-155, bw, bh),
                col_normal=(38,78,172), col_hover=(55,108,220))
    draw_button(screen, 'Quit',    (bx, HEIGHT-92,  bw, bh),
                col_normal=(75,75,75),  col_hover=(105,105,105))

def draw_details():
    draw_gradient_bg(screen)
    pw, ph = 560, 490;  px, py = (WIDTH-pw)//2, 40
    pan = pygame.Surface((pw,ph), pygame.SRCALPHA); pan.fill((20,22,55,215))
    screen.blit(pan, (px,py))
    pygame.draw.rect(screen, AI_COLOR, (px,py,pw,ph), 2, border_radius=5)
    h = gf(26,True).render('About This Game & AI', True, YELLOW_C)
    screen.blit(h, h.get_rect(center=(WIDTH//2, py+28)))
    pygame.draw.line(screen, AI_COLOR, (px+30,py+52),(px+pw-30,py+52), 2)

    lines = [
        ('AI 1 Project',                    True),
        ('Abdelrahman Mohammed',            False),
        ('Abdelrahman Mohsen',              False),
        ('Mostafa Makram',                  False),
        ('',                                False),
        ('CS Dept · FCIS · Mansoura Univ', True),
        ('Supervised by Dr. Sara El-Metwally', True),
        ('',                                False),
        ('AI Algorithms Used:',             True),
        ('• Heuristic Evaluation (L04)',    False),
        ('• Hill Climbing (L05)',           False),
        ('• Minimax + Alpha-Beta (L06/07)', False),
        ('• Genetic Algorithm (L05)',       False),
    ]
    yp = py+64
    for text, bold in lines:
        if not text: yp += 6; continue
        col = (255,200,100) if bold else (210,210,240)
        if text.startswith('•'): col = AI_COLOR
        s = gf(16,bold).render(text, True, col)
        screen.blit(s, s.get_rect(center=(WIDTH//2, yp)));  yp += 24

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
                    (cx_c+card_w//2-65, cy_c+228, 130,40), font_size=15,
                    col_normal=mc, col_hover=tuple(min(255,c+45) for c in mc))
    draw_button(screen,'Back',(WIDTH//2-90,442,180,44),font_size=20,
                col_normal=(60,60,60),col_hover=(90,90,90))

# ═══════════════════════════════════════════════════════════════════════════════
#  TRAFFIC LIGHT RULE ENFORCEMENT
# ═══════════════════════════════════════════════════════════════════════════════
TL_STOP_ZONE = 28

def player_runs_red(player_rect, tlo, speed_f, speed_max=1.0):
    """
    Returns True if the player crosses a red light at a dangerous speed.
    Threshold scales with SPEED_MAX so that high-speed modes are still
    penalised — anything above 30% of current max speed counts as running.
    """
    if tlo['color'] != 'red': return False
    light_mid_y = tlo['y'] + TL_H // 2
    zone_top    = light_mid_y - TL_STOP_ZONE
    zone_bottom = light_mid_y + TL_STOP_ZONE
    in_zone     = player_rect.bottom >= zone_top and player_rect.top <= zone_bottom
    run_threshold = max(1.5, speed_max * 0.30)   # 30% of max speed = running
    return in_zone and speed_f > run_threshold

# ═══════════════════════════════════════════════════════════════════════════════
#  GAME LOOP
# ═══════════════════════════════════════════════════════════════════════════════
def run_game(mode, car_type, car_color):
    global lane_marker_y, best_score

    # ── Base params from game mode ────────────────────────────────────────────
    speed_map   = {'Normal': 3, 'Speedy': 6, 'Emergency': 10}
    veh_map     = {'Normal': 3, 'Speedy': 4, 'Emergency': 5}
    speed_start = speed_map[mode]
    max_veh     = veh_map[mode]

    # ── GA difficulty on top of base params ───────────────────────────────────
    ga_params      = ga_controller.get_params()
    speed_start   += ga_params['speed_bonus']
    max_veh       += ga_params['max_veh_bonus']
    TL_INTERVAL_F  = int(10 * FPS / max(0.5, ga_params['spawn_mult']))

    score           = 0
    gameover        = False
    gameover_reason = ''
    show_crash      = False
    lane_marker_y   = 0

    speed_f  = float(speed_start)
    SPEED_MAX= float(speed_start)
    ACCEL    = 0.04
    DECEL    = 0.12

    tl_timer     = TL_INTERVAL_F - 1
    tl_objects   = []
    TL_X_LEFT    = ROAD_L - TL_W - 4
    TL_X_RIGHT   = ROAD_R + 4
    TL_SPAWN_Y   = -TL_H - 20

    TL_CYCLE = {
        'red':    {'next': 'yellow', 'frames': 2 * FPS},
        'yellow': {'next': 'green',  'frames': 2 * FPS},
        'green':  {'next': 'red',    'frames': 5 * FPS},
    }

    _uid_counter    = [0]
    def next_uid():
        _uid_counter[0] += 1
        return _uid_counter[0]

    red_checked_ids = set()
    active_npc_images = npc_images_emergency if mode == 'Emergency' else npc_images_normal

    pg  = pygame.sprite.Group()
    vg  = pygame.sprite.Group()
    player = PlayerVehicle(PLAYER_X, PLAYER_Y, car_type, car_color)
    pg.add(player)
    crash_rect = crash_img.get_rect()

    # ── AI state ──────────────────────────────────────────────────────────────
    ai_mode          = False          # toggled with A key
    ai_algo          = 'Minimax + α-β'
    ai_tick          = 0              # frame counter for AI decision rate
    AI_DECISION_RATE = 12             # decide every N frames (not every frame)
    ai_target_lane   = _x_to_lane(PLAYER_X)
    ai_lane_scores   = [0.0, 0.0, 0.0, 0.0]

    running = True
    while running:
        clock.tick(FPS)
        speed = max(0, int(round(speed_f)))

        red_warning = any(
            tlo['color'] == 'red' and 0 < tlo['y'] < PLAYER_Y - 40
            for tlo in tl_objects
        )

        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit(); exit()
            if event.type == KEYDOWN:
                # Toggle AI with A key
                if event.key == K_a:
                    ai_mode = not ai_mode

                if not ai_mode:
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

        # ════════════════════════════════════════════════════════════════════
        #  SMART BRAKING SYSTEM  (speed-aware)
        #
        #  All distances scale with current speed so that at high speed the
        #  car sees hazards earlier and has enough room to stop.
        #
        #  stopping_distance = speed_f² / (2 × DECEL)   (physics)
        #  We add a reaction margin on top.
        #
        #  TIER 1 — EMERGENCY HARD BRAKE
        #    Fires when a vehicle is within the computed stopping distance.
        #    Guarantees the car can stop before hitting regardless of speed.
        #
        #  TIER 2 — TRAFFIC LIGHT AWARENESS (state + prediction)
        #    Red / Yellow  → proximity decel scaled by speed.
        #    Green about to turn red → predictive anticipatory braking.
        #    Light running logic: at high speed, treat speed > 30% of SPEED_MAX
        #    as "running" — not just > 1.5, so the threshold grows with speed.
        #
        #  TIER 3 — SOFT PROXIMITY SLOW
        #    Gradual ease-off for vehicles further ahead.
        # ════════════════════════════════════════════════════════════════════

        # Compute speed-scaled distances (physics-based stopping distance)
        REACTION_FRAMES = 8   # frames of reaction lag to account for
        stop_dist  = (speed_f ** 2) / (2 * max(DECEL, 0.01))   # physics
        react_dist = speed_f * REACTION_FRAMES                   # reaction lag
        EMERG_DIST = max(55, int(stop_dist + react_dist))        # full stop budget
        PROX_VEH   = max(180, EMERG_DIST + 60)                   # soft-slow starts here
        PROX_TL    = max(240, EMERG_DIST + 120)                  # traffic-light zone

        cur_lane_idx = _x_to_lane(player.rect.centerx)

        emergency_brake = False
        auto_decel      = 0.0
        prox_reason     = ''

        # ── TIER 1: Emergency vehicle collision brake ─────────────────────
        for veh in vg:
            veh_lane = _x_to_lane(veh.rect.centerx)
            if veh_lane == cur_lane_idx:
                dist = player.rect.top - veh.rect.bottom
                if 0 < dist <= EMERG_DIST:
                    emergency_brake = True
                    prox_reason     = 'EMERGENCY BRAKE'
                    break

        if not emergency_brake:
            # ── TIER 2: Traffic light awareness ──────────────────────────
            for tlo in tl_objects:
                light_y       = tlo['y'] + TL_H // 2
                dist_to_light = light_y - player.rect.top

                if not (0 < dist_to_light < PROX_TL):
                    continue

                frames_left = TL_CYCLE[tlo['color']]['frames'] - tlo['color_timer']

                if tlo['color'] == 'red':
                    proximity = 1.0 - (dist_to_light / PROX_TL)
                    # Decel strength also scales with speed ratio
                    speed_ratio = speed_f / max(1, SPEED_MAX)
                    d = proximity * (0.18 + speed_ratio * 0.12)
                    if d > auto_decel:
                        auto_decel  = d
                        prox_reason = 'RED LIGHT'

                elif tlo['color'] == 'yellow':
                    proximity   = 1.0 - (dist_to_light / PROX_TL)
                    speed_ratio = speed_f / max(1, SPEED_MAX)
                    d = proximity * (0.11 + speed_ratio * 0.07)
                    if d > auto_decel:
                        auto_decel  = d
                        prox_reason = 'YELLOW LIGHT'

                elif tlo['color'] == 'green':
                    # Predict: will we arrive after the light turns red?
                    if speed_f > 0:
                        frames_to_reach = dist_to_light / max(1, speed_f)
                    else:
                        frames_to_reach = float('inf')

                    frames_until_red = frames_left + TL_CYCLE['yellow']['frames']

                    if frames_to_reach > frames_until_red:
                        urgency   = min(1.0, (frames_to_reach - frames_until_red) / (FPS * 3))
                        proximity = 1.0 - (dist_to_light / PROX_TL)
                        d = urgency * proximity * 0.12
                        if d > auto_decel:
                            auto_decel  = d
                            prox_reason = 'GREEN→RED SOON'

            # ── TIER 3: Soft vehicle proximity slow ───────────────────────
            for veh in vg:
                veh_lane = _x_to_lane(veh.rect.centerx)
                if veh_lane == cur_lane_idx:
                    dist = player.rect.top - veh.rect.bottom
                    if EMERG_DIST < dist < PROX_VEH:
                        proximity   = 1.0 - (dist / PROX_VEH)
                        speed_ratio = speed_f / max(1, SPEED_MAX)
                        d = proximity * (0.10 + speed_ratio * 0.08)
                        if d > auto_decel:
                            auto_decel  = d
                            prox_reason = 'VEHICLE AHEAD'

        keys = pygame.key.get_pressed()

        # AI auto-brake flag (used for hard-stop on confirmed red)
        ai_should_brake = ai_mode and red_warning

        if keys[K_SPACE] or ai_should_brake or emergency_brake:
            # Hard brake — DECEL rate, floor at 0
            speed_f = max(0.0, speed_f - DECEL)
        elif auto_decel > 0:
            # Smooth proportional slowdown
            speed_f = max(speed_start * 0.25, speed_f - auto_decel)
        else:
            speed_f = min(SPEED_MAX, speed_f + ACCEL)

        # ── AI DECISION: Minimax + Hill-Climbing ──────────────────────────────
        if ai_mode and not gameover:
            ai_tick += 1
            if ai_tick >= AI_DECISION_RATE:
                ai_tick = 0
                cur_lane = _x_to_lane(player.rect.centerx)

                # Compute heuristic scores for HUD display
                ai_lane_scores = [
                    max(0, heuristic_lane_score(i, list(vg), tl_objects, PLAYER_Y, speed_f))
                    for i in range(4)
                ]

                # Minimax with alpha-beta for actual decision
                best_lane = minimax_move(cur_lane, list(vg), tl_objects, PLAYER_Y, speed_f, depth=2)

                # Hill climbing as tie-breaker if minimax returns same lane
                if best_lane == cur_lane:
                    best_lane = hill_climbing_move(cur_lane, list(vg), tl_objects, PLAYER_Y, speed_f)

                ai_target_lane = best_lane

            # Execute AI lane move smoothly
            cur_lane = _x_to_lane(player.rect.centerx)
            if ai_target_lane != cur_lane and not gameover:
                if ai_target_lane < cur_lane:
                    new_x = player.rect.centerx - LANE_W
                else:
                    new_x = player.rect.centerx + LANE_W
                old_center = player.rect.center
                player.rect.centerx = new_x
                # Check collision after AI move
                for veh in vg:
                    if pygame.sprite.collide_rect(player, veh):
                        player.rect.center = old_center   # revert
                        ai_target_lane = cur_lane          # give up this move
                        break

        # ── Spawn traffic lights ──────────────────────────────────────────────
        tl_timer += 1
        if tl_timer >= TL_INTERVAL_F:
            tl_timer = 0
            start_col = random.choice(['red','yellow','green'])
            uid = next_uid()
            for tx in (TL_X_LEFT, TL_X_RIGHT):
                tl_objects.append({
                    'surf':        get_tl_image(start_col),
                    'x':           tx,
                    'y':           float(TL_SPAWN_Y),
                    'color':       start_col,
                    'color_timer': 0,
                    'uid':         uid,
                })

        player.tick()
        draw_road_scene(screen, speed)

        if mode == 'Emergency':
            fc = (218,30,30) if (pygame.time.get_ticks()//260)%2==0 else (30,78,218)
            pygame.draw.rect(screen, fc, (ROAD_L-12, 0, ROAD_W+24, HEIGHT), 5)

        # ── Draw AI lane-highlight overlay ────────────────────────────────────
        if ai_mode:
            cur_lane = _x_to_lane(player.rect.centerx)
            for i in range(4):
                s = max(0, heuristic_lane_score(i, list(vg), tl_objects, PLAYER_Y, speed_f))
                alpha = int(min(80, max(0, (100-s)/100*80)))
                col   = (0,180,80,alpha) if s >= 60 else (200,200,0,alpha) if s >= 30 else (200,30,30,alpha)
                overlay = pygame.Surface((LANE_W-4, HEIGHT), pygame.SRCALPHA)
                overlay.fill(col[:3] + (alpha,))
                screen.blit(overlay, (LANES[i] - LANE_W//2 + 2, 0))
            # Highlight target lane with teal border
            tx_center = LANES[ai_target_lane]
            pygame.draw.rect(screen, AI_COLOR,
                             (tx_center - LANE_W//2 + 2, 0, LANE_W-4, HEIGHT), 2)

        # ── Traffic lights draw & update ──────────────────────────────────────
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
                    pygame.draw.rect(screen, (255,0,0), (ROAD_L, line_y-4, ROAD_W, 8))
                    stop_s = gf(14, True).render('S T O P', True, WHITE)
                    screen.blit(stop_s, stop_s.get_rect(center=(ROAD_L + ROAD_W//2, line_y)))

        surviving = []
        for tlo in tl_objects:
            tlo['y'] += speed
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
                if (not gameover
                        and tlo['color'] == 'red'
                        and tlo['uid'] not in red_checked_ids
                        and player_runs_red(player.rect, tlo, speed_f, SPEED_MAX)):
                    gameover = True;  show_crash = True
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
                    # Speed grows slowly and is hard-capped per mode
                    # so the car never goes so fast that braking becomes impossible
                    SPEED_HARD_CAP = {'Normal': 10, 'Speedy': 16, 'Emergency': 22}[mode]
                    SPEED_MAX = min(float(SPEED_HARD_CAP), SPEED_MAX + 0.6)
                    # Don't snap speed_f up — let the ACCEL loop catch up naturally

        vg.draw(screen)

        hits = pygame.sprite.spritecollide(player, vg, True)
        if hits:
            gameover = True;  show_crash = True
            gameover_reason = 'You crashed into a vehicle!'
            crash_rect.center = (player.rect.centerx, player.rect.top)

        if show_crash:
            screen.blit(crash_img, crash_rect)

        # Speed bar
        bar_x, bar_y, bar_w, bar_h = ROAD_R+14, HEIGHT-60, 12, 50
        pygame.draw.rect(screen, (40,40,60), (bar_x, bar_y, bar_w, bar_h), border_radius=4)
        fill_h   = int(bar_h * (speed_f / max(1, SPEED_MAX)))
        hard_brk = keys[K_SPACE] or ai_should_brake or emergency_brake
        if hard_brk:
            fill_col = (220,  40,  40)   # red:    hard / emergency brake
        elif auto_decel > 0:
            fill_col = (220, 200,   0)   # yellow: proximity auto-slow
        else:
            fill_col = ( 30, 200,  30)   # green:  normal
        pygame.draw.rect(screen, fill_col,
                         (bar_x, bar_y+bar_h-fill_h, bar_w, fill_h), border_radius=4)
        sp_lbl = gf(11).render('SPD', True, (160,160,200))
        screen.blit(sp_lbl, (bar_x-2, bar_y-14))

        # Proximity warning label above speed bar
        if prox_reason and not hard_brk:
            warn_col = (255, 60,  60) if prox_reason in ('RED LIGHT',) else \
                       (255,200,   0) if prox_reason in ('YELLOW LIGHT', 'GREEN→RED SOON') else \
                       (255,140,   0)   # vehicle ahead
            slow_surf  = gf(10, True).render('AUTO', True, warn_col)
            slow_surf2 = gf(10, True).render('SLOW', True, warn_col)
            screen.blit(slow_surf,  (bar_x - 4, bar_y - 32))
            screen.blit(slow_surf2, (bar_x - 4, bar_y - 20))
        elif emergency_brake:
            ec = (255, 40, 40) if (pygame.time.get_ticks()//80)%2==0 else (255,180,0)
            em1 = gf(10, True).render('EMRG', True, ec)
            em2 = gf(10, True).render('STOP', True, ec)
            screen.blit(em1, (bar_x - 4, bar_y - 32))
            screen.blit(em2, (bar_x - 4, bar_y - 20))

        draw_hud(screen, score, mode, speed,
                 red_warning=red_warning,
                 ai_mode=ai_mode,
                 ai_algo=ai_algo,
                 ai_lane_scores=ai_lane_scores,
                 ga_gen=ga_controller.generation,
                 ga_params=ga_params,
                 prox_reason=prox_reason,
                 emergency_brake=emergency_brake)

        hint_col = (220,40,40) if hard_brk else (220,200,0) if auto_decel > 0 else (130,130,160)
        sp_hint  = gf(12).render('SPACE = brake | A = AI', True, hint_col)
        screen.blit(sp_hint, (ROAD_L+6, HEIGHT-18))

        # ── Game Over screen ──────────────────────────────────────────────────
        if gameover:
            ov = pygame.Surface((WIDTH,HEIGHT), pygame.SRCALPHA); ov.fill((0,0,0,145))
            screen.blit(ov, (0,0))
            gx,gy,gw,gh = WIDTH//2-245, HEIGHT//2-110, 490, 240
            pygame.draw.rect(screen, DARK_UI, (gx,gy,gw,gh), border_radius=12)
            pygame.draw.rect(screen, RED_C,   (gx,gy,gw,gh), 3, border_radius=12)
            go = gf(34,True).render('GAME  OVER', True, RED_C)
            screen.blit(go, go.get_rect(center=(WIDTH//2, HEIGHT//2-80)))
            reason_surf = gf(17).render(gameover_reason, True, (255,160,60))
            screen.blit(reason_surf, reason_surf.get_rect(center=(WIDTH//2, HEIGHT//2-45)))
            sc_txt = gf(22).render(f'Score:  {score}', True, YELLOW_C)
            screen.blit(sc_txt, sc_txt.get_rect(center=(WIDTH//2, HEIGHT//2-8)))
            ga_txt = gf(14).render(f'GA Gen {ga_controller.generation}  evolving difficulty…', True, AI_COLOR)
            screen.blit(ga_txt, ga_txt.get_rect(center=(WIDTH//2, HEIGHT//2+22)))
            hint = gf(15).render('Press  Y  to play again    or    N  to quit', True, (195,195,195))
            screen.blit(hint, hint.get_rect(center=(WIDTH//2, HEIGHT//2+58)))

        pygame.display.update()

        while gameover:
            clock.tick(FPS)
            for event in pygame.event.get():
                if event.type == QUIT:
                    pygame.quit(); exit()
                if event.type == KEYDOWN:
                    if event.key == K_y:
                        # ── Evolve GA based on score ──────────────────────────
                        ga_controller.evolve(score)
                        ga_params = ga_controller.get_params()
                        TL_INTERVAL_F = int(10 * FPS / max(0.5, ga_params['spawn_mult']))
                        max_veh = veh_map[mode] + ga_params['max_veh_bonus']

                        gameover=False; show_crash=False; gameover_reason=''
                        base_spd   = speed_map[mode] + ga_params['speed_bonus']
                        speed_f    = float(base_spd);  SPEED_MAX = float(base_spd)
                        score=0;  lane_marker_y=0;  vg.empty()
                        tl_objects.clear();  tl_timer=TL_INTERVAL_F-1
                        red_checked_ids.clear()
                        player.rect.center=(PLAYER_X,PLAYER_Y)
                        ai_target_lane = _x_to_lane(PLAYER_X)
                        ai_tick = 0
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
                pw,ph = 560,490;  px,py = (WIDTH-pw)//2, 40
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
