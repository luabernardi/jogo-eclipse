import math
import random
import pygame

pygame.init()
try:
    pygame.mixer.quit()
except Exception:
    pass

# ============================================================
# ECLIPSE SPIKE - VERSAO 6
#
# MODOS:
#   1) 1V1 contra BOT
#   2) 2V2 contra BOTS
#   3) 1V1 LOCAL
#
# NOVO:
#   - Selecao de dificuldade para modos contra bot
#   - Saque com diferentes trajetorias
#   - Regra de 3 toques mais completa
#   - Sem bloqueio: foco em defesa, mergulho e ataques direcionais
#   - IA com posicionamento basico no 2V2
#   - Bots com reacao/precisao por dificuldade
#   - Bola fora e toque na rede
#   - Set 3 ate 15 pontos
#   - Melhor de 3 sets
#   - Maximo de 3 toques por equipe, sem sequencia obrigatoria de movimentos
# ============================================================

GAME_W = 1280
GAME_H = 720
FPS = 60

# ------------------------- CORES -----------------------------
BG = (2, 6, 23)
NAVY = (15, 23, 42)
SLATE = (71, 85, 105)
WHITE = (248, 250, 252)
BLUE = (37, 99, 235)
BLUE_DARK = (29, 78, 216)
CYAN = (56, 189, 248)
RED = (220, 38, 38)
RED_LIGHT = (248, 113, 113)
GREEN = (16, 185, 129)
YELLOW = (251, 191, 36)
ORANGE = (245, 158, 11)
PURPLE = (143, 66, 255)
PINK = (236, 72, 153)
GRAY = (148, 163, 184)
DARK_GREEN = (16, 105, 86)

SKIN_PLAYER = (254, 215, 170)
SKIN_AI = (252, 165, 165)
HAIR_PLAYER = (30, 27, 75)
HAIR_AI = (69, 26, 3)

screen = pygame.display.set_mode((GAME_W, GAME_H), pygame.DOUBLEBUF)
pygame.display.set_caption("Eclipse Spike")
clock = pygame.time.Clock()
FONT_CACHE = {}


def font(size, bold=True):
    key = (size, bold)
    if key not in FONT_CACHE:
        FONT_CACHE[key] = pygame.font.SysFont("arial", size, bold=bold)
    return FONT_CACHE[key]


def text(surface, value, pos, size, color=WHITE, center=False):
    img = font(size).render(str(value), True, color)
    if center:
        rect = img.get_rect(center=(int(pos[0]), int(pos[1])))
    else:
        rect = img.get_rect(topleft=(int(pos[0]), int(pos[1])))
    surface.blit(img, rect)
    return rect


def rounded(surface, rect, color, radius=16, border=None, width=2):
    pygame.draw.rect(surface, color, rect, border_radius=radius)
    if border is not None:
        pygame.draw.rect(surface, border, rect, width=width, border_radius=radius)


def beep(freq=300, duration=0.08):
    # O Eclipse Spike fica propositalmente sem som.
    return None


# ============================================================
# QUADRA
# ============================================================

GRAVITY = 0.46
COURT_Y = 580
COURT_LEFT = 140
COURT_RIGHT = GAME_W - 140
NET_X = GAME_W // 2
NET_HEIGHT = 70
NET_TOP = COURT_Y - NET_HEIGHT
THREE_M = 150


# ============================================================
# EFEITOS
# ============================================================

particles = []
floating_texts = []
camera_shake = 0.0


class Particle:
    def __init__(self, x, y, vx, vy, color, size, life, shape="circle"):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.size = size
        self.life = life
        self.max_life = life
        self.shape = shape

    def update(self, dt):
        scale = dt * FPS
        self.x += self.vx * scale
        self.y += self.vy * scale
        self.vy += 0.08 * scale
        self.life -= scale

    def draw(self, surface):
        if self.life <= 0:
            return
        alpha = max(0, min(255, int(255 * self.life / self.max_life)))
        layer = pygame.Surface((100, 100), pygame.SRCALPHA)
        color = (*self.color, alpha)
        if self.shape == "ring":
            radius = int(self.size * (1.0 + (1.0 - self.life / self.max_life) * 2.0))
            pygame.draw.circle(layer, color, (50, 50), max(2, radius), 3)
        elif self.shape == "spark":
            pygame.draw.line(
                layer,
                color,
                (50 - self.size, 50),
                (50 + self.size, 50),
                max(2, self.size // 2),
            )
        else:
            pygame.draw.circle(layer, color, (50, 50), max(1, int(self.size)))
        surface.blit(layer, (int(self.x - 50), int(self.y - 50)))


class FloatingText:
    def __init__(self, x, y, value, color):
        self.x = x
        self.y = y
        self.value = value
        self.color = color
        self.life = 48.0

    def update(self, dt):
        self.y -= 1.65 * dt * FPS
        self.life -= dt * FPS

    def draw(self, surface):
        if self.life <= 0:
            return
        alpha = max(0, min(255, int(255 * self.life / 48)))
        layer = pygame.Surface((600, 80), pygame.SRCALPHA)
        img = font(28).render(self.value, True, (*self.color, alpha))
        outline = font(28).render(self.value, True, (2, 6, 23, alpha))
        rect = img.get_rect(center=(300, 40))
        layer.blit(outline, (rect.x + 3, rect.y + 3))
        layer.blit(img, rect)
        surface.blit(layer, (int(self.x - 300), int(self.y - 40)))


def spawn_action_text(x, y, value, color=YELLOW):
    floating_texts.append(FloatingText(x, y - 20, value, color))


def hit_sparks(x, y, color=ORANGE, count=14):
    particles.append(Particle(x, y, 0, 0, color, 14, 16, "ring"))
    for _ in range(count):
        angle = random.random() * math.tau
        speed = 3 + random.random() * 7
        particles.append(
            Particle(
                x,
                y,
                math.cos(angle) * speed,
                math.sin(angle) * speed,
                color,
                random.randint(3, 7),
                random.uniform(18, 34),
                "spark" if random.random() > 0.5 else "circle",
            )
        )


def net_sparks():
    for _ in range(12):
        x = NET_X + random.uniform(-9, 9)
        y = NET_TOP + random.uniform(0, NET_HEIGHT)
        particles.append(
            Particle(x, y, random.uniform(-2, 2), random.uniform(-3.5, 2), WHITE, 3, 22, "spark")
        )


# ============================================================
# CONFIGURACOES DE JOGO
# ============================================================

DIFFICULTIES = {
    "FACIL": {
        "label": "FACIL",
        "speed": 4.7,
        "reaction": 22,
        "error": 0.22,
        "jump_chance": 0.72,
    },
    "NORMAL": {
        "label": "NORMAL",
        "speed": 5.5,
        "reaction": 13,
        "error": 0.10,
        "jump_chance": 0.86,
    },
    "DIFICIL": {
        "label": "DIFICIL",
        "speed": 6.15,
        "reaction": 7,
        "error": 0.045,
        "jump_chance": 0.96,
    },
}

difficulty = "NORMAL"
pending_mode = None
serve_style_choice = "NORMAL"
serve_direction = 0.0
serve_charge = 0.55
serve_charge_dir = 1.0


# ============================================================
# BOLA
# ============================================================

class Volleyball:
    def __init__(self):
        self.radius = 16
        self.reset("left")

    def reset(self, server_team):
        self.x = COURT_LEFT + 120 if server_team == "left" else COURT_RIGHT - 120
        self.y = COURT_Y - 170
        self.vx = 0.0
        self.vy = 0.0
        self.rotation = 0.0
        self.spin = 0.0
        self.hit_cooldown = 0.0
        self.is_serving = True
        self.last_team = None
        self.last_cross_side = server_team
        self.last_touch_player = None
        self.team_touches = {"left": 0, "right": 0}
        self.trail = []
        self.serve_timer = 0.0
        self.bounce_count = 0

    def serve(self, team, style="NORMAL", direction=0.0, charge=0.55):
        self.is_serving = False
        self.last_team = team
        self.last_touch_player = None
        self.last_cross_side = team
        self.team_touches = {"left": 0, "right": 0}

        charge = max(0.25, min(1.0, charge))
        direction = max(-1.0, min(1.0, direction))
        if style == "POWER":
            base_vx = 11.8 + 3.0 * charge
            base_vy = -11.6 - 1.0 * charge
            self.spin = direction * 0.8
        elif style == "FLOAT":
            base_vx = 8.8 + 1.8 * charge
            base_vy = -13.0 - 0.6 * charge
            self.spin = direction * 0.3
        else:
            base_vx = 9.5 + 2.3 * charge
            base_vy = -12.7 - 0.8 * charge
            self.spin = direction * 0.45

        if team == "left":
            self.vx = base_vx + direction * 3.4
        else:
            self.vx = -base_vx + direction * 3.4
        self.vy = base_vy
        self.hit_cooldown = 10
        self.serve_timer = 0
        self.bounce_count = 0
        label = {"NORMAL": "SAQUE", "FLOAT": "SAQUE FLUTUANTE", "POWER": "SAQUE FORTE"}.get(style, "SAQUE")
        color = YELLOW if style == "NORMAL" else ORANGE if style == "POWER" else CYAN
        spawn_action_text(self.x, self.y, label, color)
        hit_sparks(self.x, self.y, color, 10)

    def update(self, dt, score_callback):
        scale = dt * FPS
        if self.hit_cooldown > 0:
            self.hit_cooldown -= scale

        if self.is_serving:
            self.serve_timer += scale
            bounce = math.sin(pygame.time.get_ticks() * 0.008) * 7
            self.y = COURT_Y - 170 + bounce
            return

        if game_state != "PLAYING":
            return

        old_x = self.x
        # Gravity + a tiny spin curve. It is deliberately subtle so the ball still feels controllable.
        self.vy += GRAVITY * (1.0 - min(0.14, abs(self.spin) * 0.018)) * scale
        self.x += self.vx * scale
        self.y += self.vy * scale
        self.vx += self.spin * 0.035 * scale
        self.spin *= 0.992 ** scale
        self.vx *= 0.997 ** scale
        self.rotation += self.vx * 0.075 * scale

        # Lateral out.
        if self.x < COURT_LEFT - self.radius - 12:
            hit_sparks(COURT_LEFT - 3, max(COURT_Y - 25, min(COURT_Y, self.y)), WHITE, 12)
            score_callback("right")
            return
        if self.x > COURT_RIGHT + self.radius + 12:
            hit_sparks(COURT_RIGHT + 3, max(COURT_Y - 25, min(COURT_Y, self.y)), WHITE, 12)
            score_callback("left")
            return

        # Antenna zone: touching the imaginary antenna above the net is out.
        if (
            abs(self.x - NET_X) < 11 + self.radius * 0.25
            and NET_TOP - 38 < self.y < NET_TOP + 2
        ):
            net_sparks()
            spawn_action_text(self.x, self.y - 25, "ANTENA!", RED_LIGHT)
            score_callback("right" if self.x < NET_X else "left")
            return

        # The ball crosses the net only when it is above the tape.
        crossed = False
        if old_x < NET_X <= self.x or old_x > NET_X >= self.x:
            if self.y <= NET_TOP + 5:
                crossed = True
                receiving = "right" if self.x >= NET_X else "left"
                self.team_touches = {"left": 0, "right": 0}
                self.last_team = None
                self.last_touch_player = None
                self.last_cross_side = receiving
                spawn_action_text(NET_X, NET_TOP - 18, "RECEPCAO", CYAN)
            else:
                # Didn't clear the net: hit it.
                net_sparks()
                self.vx *= 0.38
                self.vy = abs(self.vy) * 0.42
                self.spin *= 0.4

        # Net collision while the ball is inside the net rectangle.
        if (
            self.x + self.radius > NET_X - 7
            and self.x - self.radius < NET_X + 7
            and self.y + self.radius > NET_TOP
            and self.y - self.radius < COURT_Y
        ):
            net_sparks()
            # A near-vertical contact drops the ball. A glancing contact sends it back softly.
            if self.y < NET_TOP + 10 and self.vy > 0:
                self.y = NET_TOP - self.radius
                self.vy = -abs(self.vy) * 0.48
            elif self.x < NET_X:
                self.x = NET_X - 8 - self.radius
                self.vx = -abs(self.vx) * 0.40
                self.vy += 0.9
            else:
                self.x = NET_X + 8 + self.radius
                self.vx = abs(self.vx) * 0.40
                self.vy += 0.9

        # Ground: only a ball inside the court scores by side.
        if self.y + self.radius >= COURT_Y:
            self.y = COURT_Y - self.radius
            self.bounce_count += 1
            hit_sparks(self.x, COURT_Y - 5, YELLOW, 14)
            score_callback("right" if self.x < NET_X else "left")
            return

        speed = math.hypot(self.vx, self.vy)
        if speed > 2.2:
            self.trail.append((self.x, self.y, speed))
            if len(self.trail) > 12:
                self.trail.pop(0)
        elif self.trail:
            self.trail.pop(0)

    def draw(self, surface):
        for i, (x, y, speed) in enumerate(self.trail):
            progress = (i + 1) / max(1, len(self.trail))
            alpha = int(progress * 62)
            size = max(2, int(self.radius * (0.30 + 0.46 * progress)))
            layer = pygame.Surface((size * 4, size * 4), pygame.SRCALPHA)
            color_base = RED_LIGHT if speed > 13 else YELLOW
            pygame.draw.circle(layer, (*color_base, alpha), (size * 2, size * 2), size)
            surface.blit(layer, (int(x - size * 2), int(y - size * 2)))

        shadow_scale = max(0.15, 1 - max(0, COURT_Y - self.y) / 500)
        pygame.draw.ellipse(
            surface,
            BG,
            (
                int(self.x - self.radius * shadow_scale),
                int(COURT_Y + 5 - self.radius * 0.3 * shadow_scale),
                int(self.radius * 2 * shadow_scale),
                int(self.radius * 0.6 * shadow_scale),
            ),
        )

        x, y = int(self.x), int(self.y)
        pygame.draw.circle(surface, (203, 213, 225), (x, y), self.radius + 1)
        pygame.draw.circle(surface, WHITE, (x - 2, y - 2), self.radius)
        rect = (
            x - self.radius + 2,
            y - self.radius + 2,
            (self.radius - 2) * 2,
            (self.radius - 2) * 2,
        )
        pygame.draw.arc(surface, BLUE, rect, self.rotation - 0.2, self.rotation + 1.5, 4)
        pygame.draw.arc(surface, ORANGE, rect, self.rotation + 1.8, self.rotation + 3.7, 4)
        pygame.draw.arc(surface, BLUE_DARK, rect, self.rotation + 4.0, self.rotation + 5.7, 4)
        pygame.draw.circle(surface, NAVY, (x, y), self.radius, 1)
        pygame.draw.circle(surface, WHITE, (x - 6, y - 6), 5)


# ============================================================
# JOGADOR
# ============================================================

class VolleyballPlayer:
    def __init__(self, x, team, human=False, number="7", name="Jogador"):
        self.team = team
        self.human = human
        self.is_ai = not human
        self.number = number
        self.name = name
        self.width = 44
        self.height = 92
        self.skin_color = SKIN_PLAYER if team == "left" else SKIN_AI
        self.jersey_color = BLUE if team == "left" else RED
        self.jersey_accent = BLUE_DARK if team == "left" else (153, 27, 27)
        self.hair_color = HAIR_PLAYER if team == "left" else HAIR_AI
        self.anim_time = random.random() * 10
        self.land_timer = 0
        self.state = "IDLE"
        self.state_timer = 0
        self.action_progress = 0
        self.vx = 0.0
        self.vy = 0.0
        self.move_input = 0.0
        self.desired_vx = 0.0
        self.block_cooldown = 0.0
        self.x = x
        self.y = COURT_Y
        self.is_grounded = True
        self.stamina = 100
        self.target_x = x
        self.zone = 0
        self.ai_timer = random.uniform(0, 14)
        self.serving_style = "NORMAL"

    def reset(self, x=None):
        if x is not None:
            self.x = x
            self.target_x = x
        self.y = COURT_Y
        self.vx = 0
        self.vy = 0
        self.move_input = 0.0
        self.desired_vx = 0.0
        self.block_cooldown = 0.0
        self.is_grounded = True
        self.stamina = 100
        self.state = "IDLE"
        self.state_timer = 0
        self.action_progress = 0
        self.land_timer = 0
        self.anim_time = random.random() * 10
        self.ai_timer = random.uniform(0, 12)

    def jump(self, force=14.5):
        if self.is_grounded and self.stamina >= 10:
            self.vy = -force
            self.is_grounded = False
            self.stamina -= 10
            self.land_timer = 0
            self.state = "IDLE"
            self.state_timer = 0
            self.anim_time += 0.3

    def set_move_input(self, direction):
        self.move_input = max(-1.0, min(1.0, float(direction)))

    def within_own_side(self, x):
        if self.team == "left":
            return x < NET_X + 16
        return x > NET_X - 16

    def update_physics(self, dt):
        scale = dt * FPS
        was_grounded = self.is_grounded

        # Acceleration/deceleration instead of instant speed changes.
        stamina_factor = 0.72 if self.stamina < 20 else 0.88 if self.stamina < 40 else 1.0
        max_speed = (6.65 if self.human else DIFFICULTIES[difficulty]["speed"] + 0.45) * stamina_factor
        self.desired_vx = self.move_input * max_speed
        accel = 0.92 if self.is_grounded else 0.52
        delta = self.desired_vx - self.vx
        self.vx += max(-accel * scale, min(accel * scale, delta))
        if abs(self.move_input) < 0.05:
            self.vx *= 0.80 ** scale

        self.vy += GRAVITY * scale
        self.y += self.vy * scale
        self.x += self.vx * scale

        if self.y >= COURT_Y:
            self.y = COURT_Y
            self.vy = 0
            if not was_grounded:
                self.land_timer = 10
                hit_sparks(self.x, COURT_Y - 5, (148, 163, 184), 4)
            self.is_grounded = True
        else:
            self.is_grounded = False

        if self.team == "left":
            self.x = max(COURT_LEFT + 24, min(NET_X - 30, self.x))
        else:
            self.x = max(NET_X + 30, min(COURT_RIGHT - 24, self.x))

        if self.state_timer > 0:
            self.state_timer -= scale
            self.action_progress = max(0.0, min(1.0, 1.0 - self.state_timer / 26.0))
            if self.state_timer <= 0:
                self.state = "IDLE"
                self.action_progress = 0

        if self.land_timer > 0:
            self.land_timer -= scale
        if self.ai_timer > 0:
            self.ai_timer -= scale
        if self.block_cooldown > 0:
            self.block_cooldown -= scale

        # Stamina: movement drains a little, rest regenerates.
        if abs(self.move_input) > 0.05:
            self.stamina = max(0.0, self.stamina - 0.11 * abs(self.move_input) * scale)
        else:
            regen = 0.30 if self.is_grounded else 0.10
            self.stamina = min(100.0, self.stamina + regen * scale)

        if abs(self.vx) > 0.35:
            self.anim_time += abs(self.vx) * 0.026 * scale
        else:
            self.anim_time += 0.023 * scale

    def can_act(self):
        if self.state != "IDLE" or ball.hit_cooldown > 0 or game_state != "PLAYING":
            return False
        if self.is_ai and self.ai_timer > 0:
            return False
        return True

    def perform_action(self, action):
        if not self.can_act():
            return False

        if ball.is_serving:
            if self.team == current_server:
                serve_style = "NORMAL"
                if action == "SPIKE":
                    serve_style = "POWER"
                elif action == "SET":
                    serve_style = "FLOAT"
                ball.serve(self.team, serve_style)
                self.ai_timer = DIFFICULTIES[difficulty]["reaction"]
                return True
            return False

        if ball.is_serving:
            return False
        if not self.within_own_side(ball.x) and False:
            return False

        self.state = action
        self.state_timer = 26 if False else 22
        self.action_progress = 0
        self.try_hit_ball()
        return True

    def _can_touch_again(self):
        # No 2V2, o mesmo jogador nao pode fazer dois toques consecutivos.
        if mode == "1V1_LOCAL" or mode == "1V1_BOT":
            return True
        return ball.last_touch_player is not self

    def try_hit_ball(self):
        global camera_shake
        if ball.is_serving or ball.hit_cooldown > 0 or game_state != "PLAYING":
            return False

        facing = 1 if self.team == "left" else -1

        if self.state == "DIVE":
            # Mergulho: alcance maior no chao, sem consumir uma acao ofensiva especial.
            if self.is_grounded and ball.y > COURT_Y - 105 and math.hypot(ball.x - (self.x + facing * 28), ball.y - (self.y - 25)) < 145:
                ball.team_touches[self.team] += 1
                ball.last_team = self.team
                ball.last_touch_player = self
                ball.hit_cooldown = 13
                target = find_teammate_target(self)
                tx = target.x if target else (NET_X - 85 if self.team == "left" else NET_X + 85)
                ball.vx = max(-7.0, min(7.0, (tx - ball.x) * 0.10))
                ball.vy = -10.8
                spawn_action_text(ball.x, ball.y, f"MERGULHO #{ball.team_touches[self.team]}", GREEN)
                hit_sparks(ball.x, ball.y, GREEN, 18)
                self.vy = -4.5
                return True
            return False

        # Cada acao pode ser usada em qualquer toque.
        # Nao existe mais uma sequencia obrigatoria (manchete -> toque -> cortada).
        if self.state == "BUMP":
            hx, hy, reach = self.x + facing * 22, self.y - 45, 105
        elif self.state == "SET":
            hx, hy, reach = self.x + facing * 3, self.y - 82, 102
        else:
            hx, hy, reach = self.x + facing * 28, self.y - 83, 120

        if math.hypot(ball.x - hx, ball.y - hy) > reach:
            return False

        if not self._can_touch_again():
            spawn_action_text(ball.x, ball.y, "TOQUE DUPLO!", RED_LIGHT)
            hit_sparks(ball.x, ball.y, RED_LIGHT, 14)
            score_point("right" if self.team == "left" else "left")
            return False

        touches = ball.team_touches[self.team]
        if touches >= 3:
            spawn_action_text(ball.x, ball.y, "4 TOQUES!", RED_LIGHT)
            hit_sparks(ball.x, ball.y, RED_LIGHT, 18)
            score_point("right" if self.team == "left" else "left")
            return False

        # Pequena chance de erro do bot conforme dificuldade.
        if self.is_ai and random.random() < DIFFICULTIES[difficulty]["error"]:
            ball.hit_cooldown = 9
            self.ai_timer = DIFFICULTIES[difficulty]["reaction"] + 9
            spawn_action_text(self.x, self.y - 115, "ERRO", RED_LIGHT)
            return False

        ball.team_touches[self.team] += 1
        ball.last_team = self.team
        ball.last_touch_player = self
        ball.hit_cooldown = 12
        touch_number = ball.team_touches[self.team]
        target = find_teammate_target(self)

        if self.state == "BUMP":
            # Manchete: pode ser recepcao, passe para a parceira ou ate devolucao direta.
            if touch_number == 3:
                target_x = NET_X + facing * 35
                ball.vx = max(-7.0, min(7.0, (target_x - ball.x) * 0.10))
                ball.vy = -11.8
                label = "MANCHETE #3"
            else:
                tx = target.x if target else (NET_X - 90 if self.team == "left" else NET_X + 90)
                desired_x = tx + facing * random.uniform(-22, 22)
                ball.vx = max(-6.4, min(6.4, (desired_x - ball.x) * 0.090))
                ball.vy = -14.6
                ball.spin = (desired_x - ball.x) * 0.008
                label = f"MANCHETE #{touch_number}"
            color = GREEN
            hit_sparks(ball.x, ball.y, color, 13)
            spawn_action_text(ball.x, ball.y, label, color)
            beep(300, 0.065)

        elif self.state == "SET":
            # Toque/levantamento tambem pode ser o primeiro, segundo ou terceiro contato.
            tx = target.x if target else (NET_X + facing * 55)
            if touch_number == 3:
                # No terceiro contato, direciona para o outro lado sem obrigar uma cortada.
                target_x = NET_X + facing * 95
                ball.vx = max(-7.2, min(7.2, (target_x - ball.x) * 0.11))
                ball.vy = -11.2
            else:
                desired_x = tx + facing * random.uniform(-18, 18)
                ball.vx = max(-5.8, min(5.8, (desired_x - ball.x) * 0.095))
                ball.vy = -17.4
            ball.spin = facing * 0.18
            color = CYAN
            spawn_action_text(ball.x, ball.y, f"TOQUE #{touch_number}", color)
            hit_sparks(ball.x, ball.y, color, 13)
            beep(440, 0.07)

        elif self.state == "DROP":
            # Largadinha: toque curto por cima da rede, mais lento e controlado.
            target_x = NET_X + facing * 135
            ball.vx = max(-5.8, min(5.8, (target_x - ball.x) * 0.075))
            ball.vy = -8.0
            ball.spin = facing * 0.25
            label = f"LARGADINHA #{touch_number}"
            spawn_action_text(ball.x, ball.y, label, CYAN)
            hit_sparks(ball.x, ball.y, CYAN, 16)
        else:  # SPIKE
            # Cortada pode acontecer em qualquer toque, inclusive no primeiro.
            if not self.is_grounded:
                power = 13.4 + random.random() * 2.8
                ball.vx = facing * power
                ball.vy = 4.4 + random.random() * 4.4
                ball.spin = facing * 0.95
            else:
                ball.vx = facing * (10.7 + random.random() * 2.6)
                ball.vy = -5.0
                ball.spin = facing * 0.70
            label = f"CORTADA #{touch_number}"
            color = RED_LIGHT if touch_number == 3 else ORANGE
            spawn_action_text(ball.x, ball.y, label, color)
            hit_sparks(ball.x, ball.y, color, 22)
            camera_shake = max(camera_shake, 12 if touch_number == 3 else 7)
            beep(420, 0.14)

        return True

    def update_ai(self):
        if not self.is_ai or game_state != "PLAYING":
            return

        info = DIFFICULTIES[difficulty]
        side = self.team
        own = [p for p in all_players if p.team == side]
        touches = ball.team_touches[side]
        incoming = self.within_own_side(ball.x) and not ball.is_serving

        # Posicao-base do jogador no 2V2.
        if len(own) > 1:
            if side == "left":
                base = COURT_LEFT + (115 if self.zone == 0 else 280)
            else:
                base = COURT_RIGHT - (115 if self.zone == 0 else 280)
        else:
            base = COURT_LEFT + 190 if side == "left" else COURT_RIGHT - 190

        target = base

        # Previsao curta da trajetoria para o bot nao correr atras da bola de forma cega.
        projected = ball.x + ball.vx * 8.0
        projected = max(COURT_LEFT + 40, min(COURT_RIGHT - 40, projected))

        if incoming:
            candidate = min(own, key=lambda p: abs(p.x - projected))

            if touches == 0:
                if self is candidate:
                    target = projected + (12 if side == "left" else -12)
                else:
                    target = base + (projected - base) * 0.12
            elif touches == 1:
                # Um jogador fica para o levantamento e o outro cobre ataque/defesa.
                setter = min(own, key=lambda p: abs((NET_X - (120 if side == "left" else -120)) - p.x))
                if self is setter:
                    target = NET_X - 118 if side == "left" else NET_X + 118
                else:
                    target = projected + (18 if side == "left" else -18)
            else:
                target = NET_X - 70 if side == "left" else NET_X + 70
        else:
            # Defesa em camadas: linha de fundo + cobertura do corredor onde a bola deve voltar.
            if len(own) > 1:
                target = base + (projected - base) * 0.18
            else:
                target = base + (projected - base) * 0.32

        target = max(COURT_LEFT + 30, min(COURT_RIGHT - 30, target))
        if side == "left":
            target = min(target, NET_X - 42)
        else:
            target = max(target, NET_X + 42)

        dx = target - self.x
        max_speed = info["speed"]
        if abs(dx) > 7:
            self.set_move_input(math.copysign(1.0, dx))
        else:
            self.set_move_input(0.0)

        if not incoming:
            return

        # Defesa: a IA pode escolher qualquer movimento em qualquer toque.
        reach = math.hypot(ball.x - self.x, ball.y - (self.y - 58))
        if reach < 145 and ball.y > COURT_Y - 235:
            near_net = abs(ball.x - NET_X) < 120
            if self.is_grounded and ball.y > COURT_Y - 105 and reach < 138 and random.random() < 0.28:
                self.perform_action("DIVE")
            elif not self.is_grounded and near_net and ball.y < NET_TOP + 95:
                action = "SPIKE" if random.random() < 0.58 else ("DROP" if random.random() < 0.35 else "SET")
                self.perform_action(action)
            elif ball.y < COURT_Y - 115 and random.random() < 0.34:
                # Pode tocar de qualquer jeito, sem seguir a ordem tradicional.
                action = random.choice(["BUMP", "SET", "SPIKE", "DROP"])
                if action == "SPIKE" and self.is_grounded:
                    self.jump(14.7)
                if self.is_grounded or action != "SPIKE":
                    self.perform_action(action)
            else:
                self.perform_action(random.choice(["BUMP", "BUMP", "SET", "DROP"]))
            self.ai_timer = info["reaction"] + random.uniform(2, 9)

    def update(self, dt):
        self.update_physics(dt)
        self.update_ai()
        if self.state != "IDLE" and self.state_timer > 0 and ball.hit_cooldown <= 0:
            self.try_hit_ball()

    def draw(self, surface):
        facing = 1 if self.team == "left" else -1
        moving = abs(self.vx) > 0.45
        phase = math.sin(self.anim_time) if moving else 0
        phase2 = math.sin(self.anim_time + math.pi) if moving else 0
        jump_height = max(0, COURT_Y - self.y)
        crouch = 9 * math.sin(math.pi * self.action_progress) if self.state == "BUMP" else 0
        lean = max(-7, min(7, self.vx * 0.7)) if moving else 0
        body_x = self.x + lean
        body_y = self.y - crouch

        shadow_w = max(18, 44 - jump_height * 0.10)
        shadow_h = max(5, 12 - jump_height * 0.035)
        pygame.draw.ellipse(
            surface,
            BG,
            (int(self.x - shadow_w / 2), int(COURT_Y - 3), int(shadow_w), int(shadow_h)),
        )

        hip_y = body_y - 37
        if self.state == "SPIKE" and not self.is_grounded:
            knee_l = (body_x - 15, hip_y + 13)
            knee_r = (body_x + 15, hip_y + 8)
            foot_l = (body_x - 25, hip_y + 31)
            foot_r = (body_x + 25, hip_y + 27)
        else:
            swing = phase * (9 if moving else 0)
            swing2 = phase2 * (9 if moving else 0)
            knee_l = (body_x - 8 + swing, hip_y + 20)
            knee_r = (body_x + 8 + swing2, hip_y + 20)
            foot_l = (body_x - 11 + swing2, self.y - 5)
            foot_r = (body_x + 11 + swing, self.y - 5)

        pygame.draw.line(surface, self.skin_color, (body_x - 7, hip_y), knee_l, 8)
        pygame.draw.line(surface, self.skin_color, (body_x + 7, hip_y), knee_r, 8)
        pygame.draw.circle(surface, self.skin_color, (int(knee_l[0]), int(knee_l[1])), 5)
        pygame.draw.circle(surface, self.skin_color, (int(knee_r[0]), int(knee_r[1])), 5)
        pygame.draw.line(surface, self.skin_color, knee_l, foot_l, 8)
        pygame.draw.line(surface, self.skin_color, knee_r, foot_r, 8)
        pygame.draw.circle(surface, NAVY, (int(knee_l[0]), int(knee_l[1])), 6, 2)
        pygame.draw.circle(surface, NAVY, (int(knee_r[0]), int(knee_r[1])), 6, 2)
        pygame.draw.ellipse(surface, WHITE, (int(foot_l[0] - 9), int(foot_l[1] - 4), 19, 9))
        pygame.draw.ellipse(surface, WHITE, (int(foot_r[0] - 9), int(foot_r[1] - 4), 19, 9))

        torso = pygame.Rect(int(body_x - 15), int(body_y - 68), 30, 34)
        rounded(surface, torso, self.jersey_color, 7)
        accent_x = torso.x if facing > 0 else torso.right - 5
        pygame.draw.rect(surface, self.jersey_accent, (accent_x, torso.y, 5, torso.height))
        text(surface, self.number, torso.center, 12, WHITE, True)

        neck_y = body_y - 72
        pygame.draw.rect(surface, self.skin_color, (int(body_x - 5), int(neck_y), 10, 12))
        head_x, head_y = body_x, body_y - 86
        pygame.draw.circle(surface, self.skin_color, (int(head_x), int(head_y)), 14)
        pygame.draw.circle(surface, self.hair_color, (int(head_x), int(head_y - 4)), 14)
        pygame.draw.arc(
            surface,
            self.hair_color,
            (int(head_x - 14), int(head_y - 13), 28, 25),
            math.pi,
            math.tau,
            5,
        )
        eye_x = head_x + facing * 5
        pygame.draw.circle(surface, NAVY, (int(eye_x), int(head_y - 2)), 2)
        pygame.draw.arc(
            surface,
            NAVY,
            (int(head_x + facing * 1 - 4), int(head_y + 1), 8, 5),
            0,
            math.pi,
            1,
        )

        shoulder_l = (body_x - 11, body_y - 61)
        shoulder_r = (body_x + 11, body_y - 61)
        if self.state == "BUMP":
            arm_y = body_y - 45
            hand_x = body_x + facing * 25
            pygame.draw.line(surface, self.skin_color, shoulder_l, (body_x + facing * 5, arm_y), 7)
            pygame.draw.line(surface, self.skin_color, shoulder_r, (body_x + facing * 10, arm_y + 2), 7)
            pygame.draw.line(surface, self.skin_color, (body_x + facing * 5, arm_y), (hand_x, arm_y + 3), 7)
            pygame.draw.line(surface, self.skin_color, (body_x + facing * 10, arm_y + 2), (hand_x + facing * 3, arm_y + 3), 7)
        elif self.state == "SET":
            for side in (-1, 1):
                s = shoulder_l if side < 0 else shoulder_r
                hand = (body_x + side * 13 + facing * 7, body_y - 99)
                pygame.draw.line(surface, self.skin_color, s, (body_x + side * 11, body_y - 82), 7)
                pygame.draw.line(surface, self.skin_color, (body_x + side * 11, body_y - 82), hand, 7)
                pygame.draw.circle(surface, self.skin_color, (int(hand[0]), int(hand[1])), 5)
        elif self.state == "SPIKE":
            dominant = (body_x + facing * 6, body_y - 103)
            other = (body_x + facing * 8 - 9 * facing, body_y - 88)
            pygame.draw.line(surface, self.skin_color, shoulder_l, (body_x - facing * 4, body_y - 80), 7)
            pygame.draw.line(surface, self.skin_color, (body_x - facing * 4, body_y - 80), other, 7)
            pygame.draw.line(surface, self.skin_color, shoulder_r, (body_x + facing * 2, body_y - 83), 7)
            pygame.draw.line(surface, self.skin_color, (body_x + facing * 2, body_y - 83), dominant, 7)
            pygame.draw.circle(surface, self.skin_color, (int(dominant[0]), int(dominant[1])), 5)
        else:
            arm_swing = phase2 * 5
            pygame.draw.line(surface, self.skin_color, shoulder_l, (body_x - 18, body_y - 35 + arm_swing), 7)
            pygame.draw.line(surface, self.skin_color, shoulder_r, (body_x + 18, body_y - 35 - arm_swing), 7)

        # Joelheiras e faixa de cabelo para dar mais identidade.
        pygame.draw.rect(surface, (30, 41, 59), (int(knee_l[0] - 4), int(knee_l[1] - 2), 8, 6), border_radius=2)
        pygame.draw.rect(surface, (30, 41, 59), (int(knee_r[0] - 4), int(knee_r[1] - 2), 8, 6), border_radius=2)
        text(surface, self.name, (int(self.x), int(self.y + 17)), 10, WHITE, True)

        if self.state != "IDLE":
            color = {
                "BUMP": GREEN,
                "SET": CYAN,
                "SPIKE": RED_LIGHT,
                "DROP": CYAN,
                "DIVE": GREEN,
            }.get(self.state, WHITE)
            pygame.draw.circle(surface, color, (int(self.x), int(self.y - 119)), 5)


# ============================================================
# ESTADO / EQUIPES
# ============================================================

game_state = "MENU"
menu_page = "MAIN"
mode = None

score = {"left": 0, "right": 0}
last_score = {"left": 0, "right": 0}
sets = {"left": 0, "right": 0}
current_server = "left"
point_announce = ""
point_timer = 0.0
set_announce = ""
set_timer = 0.0
match_started = False
training_mode = False
player_style = 0
court_swapped = False
rotation_count = {"left": 0, "right": 0}
celebration_timer = 0.0

ball = Volleyball()
all_players = []
left_team = []
right_team = []
keys_down = set()

CONTROL_P1 = {
    "left": (pygame.K_a, pygame.K_LEFT),
    "right": (pygame.K_d, pygame.K_RIGHT),
    "jump": (pygame.K_w, pygame.K_SPACE, pygame.K_UP),
    "BUMP": (pygame.K_z,),
    "SET": (pygame.K_x,),
    "SPIKE": (pygame.K_c,),
    "DROP": (pygame.K_v,),
    "DIVE": (pygame.K_b,),
}

CONTROL_LOCAL_P1 = {
    "left": (pygame.K_a,),
    "right": (pygame.K_d,),
    "jump": (pygame.K_w, pygame.K_SPACE),
    "BUMP": (pygame.K_z,),
    "SET": (pygame.K_x,),
    "SPIKE": (pygame.K_c,),
    "DROP": (pygame.K_v,),
    "DIVE": (pygame.K_b,),
}

CONTROL_P2 = {
    "left": (pygame.K_LEFT,),
    "right": (pygame.K_RIGHT,),
    "jump": (pygame.K_UP,),
    "BUMP": (pygame.K_j,),
    "SET": (pygame.K_k,),
    "SPIKE": (pygame.K_l,),
    "DROP": (pygame.K_o,),
    "DIVE": (pygame.K_p,),
}


def key_is_down(keys, key_tuple):
    return any(k in keys for k in key_tuple)


def find_teammate_target(actor):
    mates = [p for p in all_players if p.team == actor.team and p is not actor]
    if not mates:
        return None
    return min(mates, key=lambda p: abs(p.x - ball.x))


def team_start_x(team, count, index):
    if count == 1:
        return COURT_LEFT + 175 if team == "left" else COURT_RIGHT - 175
    if team == "left":
        return COURT_LEFT + 115 + index * 150
    return COURT_RIGHT - 115 - index * 150


def configure_mode(selected_mode):
    global mode, all_players, left_team, right_team
    mode = selected_mode
    all_players = []
    left_team = []
    right_team = []

    global training_mode
    training_mode = selected_mode == "TREINO"
    if mode == "TREINO":
        left_team = [VolleyballPlayer(team_start_x("left", 1, 0), "left", True, "7", "TREINO")]
        right_team = []
    elif mode == "1V1_BOT":
        left_team = [VolleyballPlayer(team_start_x("left", 1, 0), "left", True, "7", "VOCE")]
        right_team = [VolleyballPlayer(team_start_x("right", 1, 0), "right", False, "1", "BOT")]
    elif mode == "2V2_BOT":
        left_team = [
            VolleyballPlayer(team_start_x("left", 2, 0), "left", True, "7", "VOCE"),
            VolleyballPlayer(team_start_x("left", 2, 1), "left", False, "11", "ALIADA"),
        ]
        right_team = [
            VolleyballPlayer(team_start_x("right", 2, 0), "right", False, "1", "BOT 1"),
            VolleyballPlayer(team_start_x("right", 2, 1), "right", False, "2", "BOT 2"),
        ]
    else:
        left_team = [VolleyballPlayer(team_start_x("left", 1, 0), "left", True, "7", "P1")]
        right_team = [VolleyballPlayer(team_start_x("right", 1, 0), "right", True, "10", "P2")]

    for team in (left_team, right_team):
        for i, player in enumerate(team):
            player.zone = i

    all_players = left_team + right_team


def reset_match():
    global score, last_score, sets, current_server
    global point_announce, point_timer, set_announce, set_timer, game_state
    global serve_style_choice, serve_direction, serve_charge, serve_charge_dir
    score = {"left": 0, "right": 0}
    last_score = {"left": 0, "right": 0}
    sets = {"left": 0, "right": 0}
    current_server = "left"
    point_announce = ""
    point_timer = 0
    set_announce = ""
    set_timer = 0
    serve_style_choice = "NORMAL"
    serve_direction = 0.0
    serve_charge = 0.55
    serve_charge_dir = 1.0

    for i, p in enumerate(left_team):
        p.reset(team_start_x("left", len(left_team), i))
    for i, p in enumerate(right_team):
        p.reset(team_start_x("right", len(right_team), i))

    ball.reset(current_server)
    game_state = "PLAYING"


def start_selected_mode(selected_mode):
    configure_mode(selected_mode)
    reset_match()


def set_target_points():
    # Terceiro set (2-0, 1-1 ou 0-2 -> proximo set e o terceiro apenas se 1-1).
    played_sets = sets["left"] + sets["right"]
    return 15 if played_sets >= 2 else 25


def set_finished(winner):
    global sets, score, last_score, set_announce, set_timer, game_state
    sets[winner] += 1
    last_score = score.copy()
    score = {"left": 0, "right": 0}
    set_announce = "TIME DA ESQUERDA GANHOU O SET!" if winner == "left" else "TIME DA DIREITA GANHOU O SET!"
    set_timer = 125
    if sets[winner] >= 2:
        game_state = "MATCHOVER"
    else:
        game_state = "SET_WON"


def score_point(winner):
    global score, current_server, point_announce, point_timer, game_state
    if game_state != "PLAYING":
        return
    if training_mode:
        ball.reset("left")
        spawn_action_text(GAME_W // 2, 190, "TREINO — TENTE NOVAMENTE", CYAN)
        return
    score[winner] += 1
    if mode == "2V2_BOT" and winner != current_server:
        rotation_count[winner] += 1
        team = left_team if winner == "left" else right_team
        if len(team) > 1:
            team[:] = [team[1], team[0]]
            for i, p in enumerate(team):
                p.zone = i
        spawn_action_text(NET_X, 205, "RODIZIO!", PURPLE)
    current_server = winner
    point_announce = "PONTO DO SEU TIME!" if winner == "left" else "PONTO DO ADVERSARIO!"
    point_timer = 75
    beep(700 if winner == "left" else 520, 0.11)

    target = set_target_points()
    other = "right" if winner == "left" else "left"
    if score[winner] >= target and score[winner] - score[other] >= 2:
        set_finished(winner)
    else:
        game_state = "POINT_SCORED"


def continue_after_point():
    global game_state
    ball.reset(current_server)
    for i, p in enumerate(left_team):
        p.reset(team_start_x("left", len(left_team), i))
    for i, p in enumerate(right_team):
        p.reset(team_start_x("right", len(right_team), i))
    game_state = "PLAYING"


def continue_after_set():
    global game_state
    ball.reset(current_server)
    for i, p in enumerate(left_team):
        p.reset(team_start_x("left", len(left_team), i))
    for i, p in enumerate(right_team):
        p.reset(team_start_x("right", len(right_team), i))
    game_state = "PLAYING"


# ============================================================
# DESENHO DA QUADRA
# ============================================================

def draw_court(surface):
    surface.fill(BG)

    # Fundo do ginasio.
    for y in range(0, COURT_Y):
        t = y / COURT_Y
        col = (int(2 + 12 * t), int(6 + 14 * t), int(23 + 31 * t))
        pygame.draw.line(surface, col, (0, y), (GAME_W, y))

    # Faixas e luzes do teto.
    for x in (110, 360, 610, 860, 1110):
        pygame.draw.rect(surface, (34, 48, 72), (x, 76, 150, 6), border_radius=3)
        pygame.draw.rect(surface, (70, 92, 126), (x + 35, 80, 80, 3), border_radius=2)

    # Arquibancadas em 3 camadas.
    seat_colors = [(30, 41, 59), (38, 50, 72), (45, 58, 82)]
    for row, y0 in enumerate((315, 338, 361)):
        pygame.draw.rect(surface, seat_colors[row], (0, y0, GAME_W, 22))
        for x in range(18, GAME_W - 18, 31):
            bob = math.sin(x * 0.065 + row) * 2
            head = (x, int(y0 - 5 + bob))
            body = (x - 8, int(y0 + 5 + bob), 16, 13)
            skin = (226, 190, 160) if (x // 31 + row) % 3 else (245, 205, 173)
            shirt = (76, 89, 115) if (x // 31 + row) % 2 else (108, 55, 142)
            pygame.draw.circle(surface, skin, head, 6)
            pygame.draw.rect(surface, shirt, body, border_radius=5)

    # Banners.
    rounded(surface, (56, 260, 260, 42), NAVY, 10, PURPLE, 2)
    text(surface, "ECLIPSE SPIKE", (186, 281), 16, WHITE, True)
    rounded(surface, (964, 260, 260, 42), NAVY, 10, ORANGE, 2)
    text(surface, "ECLIPSE LEAGUE", (1094, 281), 16, WHITE, True)

    # Piso.
    for y in range(COURT_Y, GAME_H):
        t = (y - COURT_Y) / (GAME_H - COURT_Y)
        col = (int(7 + 5 * t), int(144 - 26 * t), int(128 - 18 * t))
        pygame.draw.line(surface, col, (0, y), (GAME_W, y))

    # Faixas laterais / reflexo do piso.
    for x in range(COURT_LEFT + 22, COURT_RIGHT - 20, 115):
        pygame.draw.line(surface, (19, 114, 133), (x, COURT_Y + 9), (x + 28, GAME_H), 3)

    # Area de jogo e linhas.
    court_rect = pygame.Rect(COURT_LEFT, COURT_Y - 118, COURT_RIGHT - COURT_LEFT, 118)
    pygame.draw.rect(surface, (10, 130, 154), court_rect)
    pygame.draw.rect(surface, (15, 142, 167), (COURT_LEFT + 7, COURT_Y - 111, COURT_RIGHT - COURT_LEFT - 14, 104))
    pygame.draw.line(surface, WHITE, (COURT_LEFT, COURT_Y), (COURT_RIGHT, COURT_Y), 7)
    pygame.draw.line(surface, WHITE, (COURT_LEFT, COURT_Y - 118), (COURT_RIGHT, COURT_Y - 118), 5)
    pygame.draw.line(surface, WHITE, (COURT_LEFT, COURT_Y - 118), (COURT_LEFT, COURT_Y), 5)
    pygame.draw.line(surface, WHITE, (COURT_RIGHT, COURT_Y - 118), (COURT_RIGHT, COURT_Y), 5)

    # Linha central/3 metros.
    line_color = (38, 73, 151)
    pygame.draw.line(surface, line_color, (NET_X - THREE_M, COURT_Y), (NET_X - THREE_M, COURT_Y - 118), 5)
    pygame.draw.line(surface, line_color, (NET_X + THREE_M, COURT_Y), (NET_X + THREE_M, COURT_Y - 118), 5)
    pygame.draw.line(surface, (208, 242, 255), (NET_X - 2, COURT_Y - 118), (NET_X - 2, COURT_Y), 2)

    # Logo central.
    text(surface, "ECLIPSE", (NET_X - 105, COURT_Y - 52), 24, (215, 224, 255), True)
    text(surface, "SPIKE", (NET_X + 105, COURT_Y - 52), 24, (255, 226, 170), True)

    # Postes, antenas e rede baixa e limpa.
    post = (148, 163, 184)
    pygame.draw.rect(surface, post, (NET_X - 6, NET_TOP - 3, 12, NET_HEIGHT + 7))
    pygame.draw.line(surface, WHITE, (NET_X - 10, NET_TOP + 2), (NET_X + 10, NET_TOP + 2), 5)
    pygame.draw.line(surface, (123, 141, 163), (NET_X, NET_TOP + 7), (NET_X, COURT_Y), 2)
    pygame.draw.line(surface, WHITE, (NET_X - 2, NET_TOP - 38), (NET_X - 2, NET_TOP + 2), 4)
    pygame.draw.circle(surface, ORANGE, (NET_X - 2, NET_TOP - 41), 5)
    pygame.draw.line(surface, WHITE, (NET_X + 2, NET_TOP - 38), (NET_X + 2, NET_TOP + 2), 4)
    pygame.draw.circle(surface, ORANGE, (NET_X + 2, NET_TOP - 41), 5)

    # Mesa do marcador.
    rounded(surface, (55, 115, 250, 48), NAVY, 10, SLATE, 2)
    text(surface, "ECLIPSE SPIKE", (180, 139), 16, YELLOW, True)
    rounded(surface, (975, 115, 250, 48), NAVY, 10, SLATE, 2)
    text(surface, "SPIKE ARENA", (1100, 139), 16, CYAN, True)


def draw_touch_sequence(surface):
    active_team = ball.last_cross_side
    count = ball.team_touches[active_team]

    x0 = 420
    y = 145
    rounded(surface, (x0, y, 440, 62), NAVY, 14, SLATE, 1)
    text(surface, "TOQUES DA EQUIPE", (x0 + 86, y + 13), 12, GRAY, True)
    for i in range(3):
        x = x0 + 190 + i * 72
        active = count >= i + 1
        color = CYAN if active_team == "left" else RED_LIGHT
        fill = color if active else (30, 41, 59)
        rounded(surface, (x - 28, y + 10, 56, 40), fill, 10, color, 2)
        text(surface, str(i + 1), (x, y + 30), 14, WHITE, True)
    remaining = max(0, 3 - count)
    text(surface, f"{remaining} restante(s)", (x0 + 342, y + 31), 11, WHITE, True)


def draw_serve_panel(surface):
    if not ball.is_serving or game_state != "PLAYING":
        return
    server_is_human = (
        (current_server == "left" and human_left_player() is not None) or
        (current_server == "right" and human_right_player() is not None)
    )
    if not server_is_human:
        return

    x, y, w, h = 330, GAME_H - 116, 620, 88
    rounded(surface, (x, y, w, h), NAVY, 18, ORANGE, 2)
    text(surface, "SAQUE", (x + 62, y + 20), 16, ORANGE, True)
    styles = [("NORMAL", GREEN), ("FLUTUANTE", CYAN), ("FORTE", RED_LIGHT)]
    for i, (label, color) in enumerate(styles):
        rx = x + 125 + i * 130
        selected = serve_style_choice == {"NORMAL":"NORMAL","FLUTUANTE":"FLOAT","FORTE":"POWER"}[label]
        rounded(surface, (rx, y + 9, 116, 30), color if selected else (35, 45, 62), 10, color, 2)
        text(surface, label, (rx + 58, y + 24), 10, WHITE, True)

    # Bar of force.
    bar_x, bar_y, bar_w = x + 125, y + 52, 315
    rounded(surface, (bar_x, bar_y, bar_w, 12), (30, 41, 59), 6, SLATE, 1)
    fill_w = int((bar_w - 4) * serve_charge)
    rounded(surface, (bar_x + 2, bar_y + 2, max(4, fill_w), 8), ORANGE, 4)
    direction_label = "ESQUERDA" if serve_direction < -0.25 else "DIREITA" if serve_direction > 0.25 else "CENTRO"
    text(surface, f"DIRECAO: {direction_label}", (x + 488, y + 24), 11, WHITE, True)
    text(surface, "Z normal  |  X flutuante  |  C forte  |  A/D ou setas = direcao  |  ESPACO = sacar", (x + 310, y + 78), 10, GRAY, True)


def draw_hud(surface):
    rounded(surface, (GAME_W // 2 - 205, 16, 410, 84), NAVY, 18, SLATE, 2)
    left_label = "VOCE" if mode != "1V1_LOCAL" else "P1"
    right_label = "BOTS" if mode == "2V2_BOT" else ("BOT" if mode == "1V1_BOT" else "P2")
    text(surface, left_label, (GAME_W // 2 - 122, 31), 13, CYAN, True)
    text(surface, right_label, (GAME_W // 2 + 122, 31), 13, RED_LIGHT, True)
    text(surface, score["left"], (GAME_W // 2 - 72, 69), 34, CYAN, True)
    text(surface, score["right"], (GAME_W // 2 + 72, 69), 34, RED_LIGHT, True)
    text(surface, ":", (GAME_W // 2, 66), 24, SLATE, True)
    set_number = sets["left"] + sets["right"] + 1
    target = set_target_points()
    text(surface, f"SET {set_number} | PRIMEIRO A {target} | SETS {sets['left']}-{sets['right']}", (GAME_W // 2, 112), 14, WHITE, True)

    # Caixa de toque atual.
    rounded(surface, (34, 36, 245, 84), NAVY, 12, BLUE_DARK, 2)
    text(surface, f"ESQUERDA: {ball.team_touches['left']}/3", (50, 50), 14, CYAN)
    text(surface, f"DIREITA: {ball.team_touches['right']}/3", (50, 80), 14, RED_LIGHT)

    text(surface, f"DIFICULDADE: {DIFFICULTIES[difficulty]['label']}", (GAME_W - 248, 48), 12, GRAY)
    text(surface, f"MODO: {mode_label(mode)}", (GAME_W - 248, 70), 12, GRAY)
    if training_mode:
        text(surface, "TREINO: Z manchete | X toque | C cortada | V largadinha | B mergulho", (GAME_W // 2, GAME_H - 24), 12, CYAN, True)

    if left_team:
        human = next((p for p in left_team if p.human), None)
        if human:
            rounded(surface, (40, GAME_H - 51, 180, 14), NAVY, 7)
            w = int(176 * human.stamina / 100)
            if w > 0:
                rounded(surface, (42, GAME_H - 49, w, 10), CYAN, 5)
            text(surface, "STAMINA", (46, GAME_H - 72), 10, WHITE)

    if game_state == "POINT_SCORED":
        text(surface, point_announce, (GAME_W // 2, GAME_H // 2 - 84), 40, YELLOW, True)
        text(surface, "Proximo saque: equipe que marcou o ponto", (GAME_W // 2, GAME_H // 2 - 40), 15, WHITE, True)
    elif game_state == "SET_WON":
        text(surface, set_announce, (GAME_W // 2, GAME_H // 2 - 72), 32, YELLOW, True)
        text(surface, "ENTER para continuar", (GAME_W // 2, GAME_H // 2 - 27), 17, WHITE, True)


def draw_pause_overlay(surface):
    overlay = pygame.Surface((GAME_W, GAME_H), pygame.SRCALPHA)
    overlay.fill((2, 6, 23, 175))
    surface.blit(overlay, (0, 0))
    rounded(surface, (410, 175, 460, 330), NAVY, 28, PURPLE, 3)
    text(surface, "PAUSADO", (640, 250), 42, WHITE, True)
    text(surface, "ESC ou ENTER = continuar", (640, 305), 16, CYAN, True)
    text(surface, "R = reiniciar partida", (640, 340), 15, GRAY, True)
    rounded(surface, (505, 392, 270, 54), PURPLE, 15, (189, 134, 255), 2)
    text(surface, "CONTINUAR", (640, 420), 18, WHITE, True)
    rounded(surface, (505, 462, 270, 54), NAVY, 15, SLATE, 2)
    text(surface, "VOLTAR AO MENU", (640, 490), 16, WHITE, True)


def mode_label(value):
    return {
        "1V1_BOT": "1V1 x BOT",
        "2V2_BOT": "2V2 x BOTS",
        "1V1_LOCAL": "1V1 LOCAL",
        "TREINO": "TREINO",
    }.get(value, "-")


# ============================================================
# MENUS
# ============================================================

def draw_menu_background(surface):
    draw_court(surface)
    overlay = pygame.Surface((GAME_W, GAME_H), pygame.SRCALPHA)
    overlay.fill((2, 6, 23, 190))
    surface.blit(overlay, (0, 0))


def draw_main_menu(surface):
    draw_menu_background(surface)
    rounded(surface, (300, 78, 680, 568), NAVY, 28, SLATE, 2)
    text(surface, "ECLIPSE", (640, 168), 58, ORANGE, True)
    text(surface, "SPIKE", (640, 226), 58, PURPLE, True)
    text(surface, "VOLEI EM PYTHON", (640, 267), 16, GRAY, True)
    text(surface, "1V1 | 2V2 | LOCAL  •  3 toques  •  defesa  •  ataques  •  sets", (640, 296), 13, CYAN, True)
    text(surface, "Saques, fisica melhorada, stamina e IA por dificuldade", (640, 318), 11, GRAY, True)

    rounded(surface, (430, 334, 420, 60), PURPLE, 18, (189, 134, 255), 2)
    text(surface, "JOGAR", (640, 365), 24, WHITE, True)
    rounded(surface, (430, 412, 200, 58), NAVY, 16, SLATE, 2)
    text(surface, "TREINO", (530, 441), 20, CYAN, True)
    rounded(surface, (650, 412, 200, 58), NAVY, 16, SLATE, 2)
    text(surface, "COMO JOGAR", (750, 441), 17, WHITE, True)
    rounded(surface, (430, 488, 420, 58), NAVY, 16, SLATE, 2)
    text(surface, "SAIR", (640, 517), 20, WHITE, True)
    text(surface, "ENTER abre a selecao de modo  •  sem audio  •  sem bloqueio", (640, 588), 13, GRAY, True)


def mode_rects():
    return [
        ((180, 220, 270, 235), "1V1_BOT"),
        ((505, 220, 270, 235), "2V2_BOT"),
        ((830, 220, 270, 235), "1V1_LOCAL"),
        ((505, 470, 270, 105), "TREINO"),
    ]


def draw_mode_menu(surface):
    draw_menu_background(surface)
    rounded(surface, (110, 70, 1060, 595), NAVY, 28, SLATE, 2)
    text(surface, "COMO VOCE QUER JOGAR?", (640, 126), 34, ORANGE, True)
    text(surface, "Escolha o modo da partida", (640, 160), 15, GRAY, True)
    text(surface, "No 1V1 LOCAL, duas pessoas jogam no mesmo computador.", (640, 185), 12, WHITE, True)

    cards = [
        ((180, 220, 270, 235), "1V1", "CONTRA BOT", "VOCE x 1 bot", "1V1_BOT", BLUE),
        ((505, 220, 270, 235), "2V2", "CONTRA BOTS", "VOCE + aliada x 2 bots", "2V2_BOT", PURPLE),
        ((830, 220, 270, 235), "1V1", "LOCAL", "P1 x P2 no mesmo PC", "1V1_LOCAL", PINK),
        ((505, 470, 270, 105), "TREINO", "SEM ADVERSARIO", "Teste movimentos e ataques", "TREINO", CYAN),
    ]

    mx, my = pygame.mouse.get_pos()
    for rect, title, subtitle, desc, code, color in cards:
        hover = rect[0] <= mx <= rect[0] + rect[2] and rect[1] <= my <= rect[1] + rect[3]
        border = WHITE if hover else color
        fill = (45, 52, 72) if hover else (30, 41, 59)
        rounded(surface, rect, fill, 22, border, 3)
        text(surface, title, (rect[0] + rect[2] // 2, rect[1] + 55), 34, color, True)
        text(surface, subtitle, (rect[0] + rect[2] // 2, rect[1] + 99), 15, WHITE, True)
        text(surface, desc, (rect[0] + rect[2] // 2, rect[1] + 137), 13, (203, 213, 225), True)
        rounded(surface, (rect[0] + 65, rect[1] + 173, 140, 34), color, 12)
        text(surface, "ESCOLHER", (rect[0] + rect[2] // 2, rect[1] + 190), 13, WHITE, True)

    rounded(surface, (510, 520, 260, 50), NAVY, 14, SLATE, 2)
    text(surface, "VOLTAR (ESC)", (640, 545), 17, WHITE, True)


def difficulty_rects():
    return [
        ((315, 215, 200, 170), "FACIL"),
        ((540, 215, 200, 170), "NORMAL"),
        ((765, 215, 200, 170), "DIFICIL"),
    ]


def draw_difficulty_menu(surface):
    draw_menu_background(surface)
    rounded(surface, (200, 90, 880, 510), NAVY, 28, SLATE, 2)
    text(surface, "ESCOLHA A DIFICULDADE", (640, 145), 34, ORANGE, True)
    mode_text = "1V1 contra BOT" if pending_mode == "1V1_BOT" else "2V2 contra BOTS"
    text(surface, f"Modo: {mode_text}", (640, 177), 15, GRAY, True)

    cards = [
        ((315, 215, 200, 170), "FACIL", "Mais erros dos bots", GREEN),
        ((540, 215, 200, 170), "NORMAL", "Desafio equilibrado", CYAN),
        ((765, 215, 200, 170), "DIFICIL", "Reacao mais rapida", RED_LIGHT),
    ]
    mx, my = pygame.mouse.get_pos()
    for rect, label, desc, color in cards:
        hover = rect[0] <= mx <= rect[0] + rect[2] and rect[1] <= my <= rect[1] + rect[3]
        rounded(surface, rect, (45, 52, 72) if hover else (30, 41, 59), 18, WHITE if hover else color, 3)
        text(surface, label, (rect[0] + rect[2] // 2, rect[1] + 55), 25, color, True)
        text(surface, desc, (rect[0] + rect[2] // 2, rect[1] + 105), 12, WHITE, True)
        text(surface, "CLIQUE", (rect[0] + rect[2] // 2, rect[1] + 145), 11, GRAY, True)

    text(surface, "ENTER = NORMAL | ESC = voltar", (640, 530), 13, GRAY, True)


def draw_tutorial(surface):
    draw_menu_background(surface)
    rounded(surface, (175, 34, 930, 655), NAVY, 28, SLATE, 2)
    text(surface, "COMO JOGAR", (640, 92), 36, ORANGE, True)

    rows = [
        ("MOVER", "P1: A/D  |  P2: SETAS", CYAN),
        ("PULAR", "P1: W/ESPACO  |  P2: ↑", CYAN),
        ("MANCHETE", "P1: Z  |  P2: J", GREEN),
        ("TOQUE", "P1: X  |  P2: K", CYAN),
        ("CORTADA", "P1: C  |  P2: L", RED_LIGHT),
        ("LARGADINHA", "P1: V  |  P2: O", CYAN),
        ("MERGULHO", "P1: B  |  P2: P", GREEN),
    ]
    y = 132
    for label, control, color in rows:
        rounded(surface, (265, y, 750, 42), (19, 29, 48), 10, SLATE, 1)
        text(surface, label, (320, y + 21), 14, color, True)
        text(surface, control, (690, y + 21), 14, WHITE, True)
        y += 49

    rounded(surface, (265, 430, 750, 160), (30, 41, 59), 16, SLATE, 1)
    text(surface, "REGRAS", (640, 457), 18, YELLOW, True)
    text(surface, "A equipe pode usar manchete, toque, largadinha ou cortada em qualquer ordem.", (640, 486), 13, WHITE, True)
    text(surface, "Sao no maximo 3 toques por lado. No 4o, o ponto vai para o adversario.", (640, 511), 13, WHITE, True)
    text(surface, "No 2V2, um jogador nao pode tocar duas vezes seguidas.", (640, 536), 13, WHITE, True)
    text(surface, "Nao existe bloqueio: a defesa usa deslocamento, mergulho e posicionamento.", (640, 561), 13, WHITE, True)

    rounded(surface, (265, 605, 750, 34), NAVY, 9, PURPLE, 1)
    text(surface, "SAQUE: Z normal | X flutuante | C forte | A/D ou setas = direcao | ESPACO = sacar", (640, 622), 10, WHITE, True)
    text(surface, "ESC durante a partida = PAUSAR  |  R pausado = reiniciar", (640, 652), 10, GRAY, True)


def draw_matchover(surface):
    overlay = pygame.Surface((GAME_W, GAME_H), pygame.SRCALPHA)
    overlay.fill((2, 6, 23, 228))
    surface.blit(overlay, (0, 0))
    rounded(surface, (330, 125, 620, 465), NAVY, 28, SLATE, 2)

    user_won = sets["left"] > sets["right"]
    title = "PARTIDA ENCERRADA" if not user_won else "PARTIDA ENCERRADA"
    color = GREEN if user_won else RED_LIGHT
    text(surface, title, (640, 206), 32, color, True)
    text(surface, "TIME DA ESQUERDA" if user_won else "TIME DA DIREITA", (640, 248), 22, color, True)
    text(surface, f"SETS  {sets['left']} - {sets['right']}", (640, 315), 36, WHITE, True)
    text(surface, f"ULTIMO SET  {last_score['left']} - {last_score['right']}", (640, 360), 18, GRAY, True)

    rounded(surface, (450, 415, 380, 58), ORANGE, 18)
    text(surface, "JOGAR NOVAMENTE", (640, 444), 19, WHITE, True)
    text(surface, "ENTER", (640, 489), 12, GRAY, True)
    rounded(surface, (500, 525, 280, 42), NAVY, 12, SLATE, 2)
    text(surface, "MENU (ESC)", (640, 546), 15, WHITE, True)


# ============================================================
# EVENTOS / CONTROLES
# ============================================================

def human_left_player():
    return next((p for p in left_team if p.human), None)


def human_right_player():
    return next((p for p in right_team if p.human), None)


def set_serve_direction_from_controls():
    global serve_direction
    direction = 0.0
    if mode in ("1V1_BOT", "2V2_BOT"):
        if key_is_down(keys_down, CONTROL_P1["left"]):
            direction -= 1.0
        if key_is_down(keys_down, CONTROL_P1["right"]):
            direction += 1.0
    elif mode == "1V1_LOCAL":
        server = human_left_player() if current_server == "left" else human_right_player()
        controls = CONTROL_LOCAL_P1 if server is human_left_player() else CONTROL_P2
        if server is not None:
            if key_is_down(keys_down, controls["left"]):
                direction -= 1.0
            if key_is_down(keys_down, controls["right"]):
                direction += 1.0
    serve_direction = max(-1.0, min(1.0, direction))


def human_serve(style=None):
    global serve_style_choice
    if style is not None:
        serve_style_choice = style
    if not ball.is_serving or current_server not in ("left", "right"):
        return
    charge = serve_charge
    ball.serve(current_server, serve_style_choice, serve_direction, charge)


def try_player_action(player, action):
    if player is None:
        return
    player.perform_action(action)


def start_bot_serve_if_needed():
    if not ball.is_serving or current_server != "right" or mode == "1V1_LOCAL":
        return
    if ball.serve_timer > 34:
        style = "NORMAL"
        if difficulty == "DIFICIL" and random.random() < 0.42:
            style = "POWER"
        elif difficulty == "NORMAL" and random.random() < 0.30:
            style = "FLOAT"
        direction = random.uniform(-0.75, 0.75)
        charge = random.uniform(0.45, 1.0)
        ball.serve("right", style, direction, charge)


# ============================================================
# LOOP PRINCIPAL
# ============================================================

running = True

while running:
    dt = min(clock.tick(FPS) / 1000.0, 0.033)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.KEYDOWN:
            keys_down.add(event.key)

            # ESC.
            if event.key == pygame.K_ESCAPE:
                if game_state == "PLAYING":
                    game_state = "PAUSED"
                elif game_state == "PAUSED":
                    game_state = "PLAYING"
                elif game_state in ("POINT_SCORED", "SET_WON"):
                    game_state = "MENU"
                    menu_page = "MAIN"
                elif game_state == "MATCHOVER":
                    game_state = "MENU"
                    menu_page = "MAIN"
                elif game_state == "MENU" and menu_page in ("MODE", "TUTORIAL", "DIFFICULTY"):
                    menu_page = "MAIN"
                elif game_state == "MENU" and menu_page == "MAIN":
                    running = False

            # ENTER.
            if event.key == pygame.K_RETURN:
                if game_state == "MENU" and menu_page == "MAIN":
                    menu_page = "MODE"
                elif game_state == "MENU" and menu_page == "MODE":
                    pending_mode = "1V1_BOT"
                    menu_page = "DIFFICULTY"
                elif game_state == "MENU" and menu_page == "DIFFICULTY":
                    difficulty = "NORMAL"
                    start_selected_mode(pending_mode)
                elif game_state == "MENU" and menu_page == "TUTORIAL":
                    menu_page = "MAIN"
                elif game_state == "PAUSED":
                    game_state = "PLAYING"
                elif game_state == "SET_WON":
                    continue_after_set()
                elif game_state == "MATCHOVER":
                    reset_match()

            if game_state == "PAUSED" and event.key == pygame.K_r:
                reset_match()

            # Jogador 1 - modos com bot.
            if game_state == "PLAYING" and mode in ("1V1_BOT", "2V2_BOT"):
                p1 = human_left_player()
                if p1:
                    if event.key in CONTROL_P1["jump"]:
                        if ball.is_serving and current_server == "left":
                            human_serve()
                        else:
                            p1.jump()
                    if ball.is_serving and current_server == "left":
                        if event.key in CONTROL_P1["BUMP"]:
                            human_serve("NORMAL")
                        elif event.key in CONTROL_P1["SET"]:
                            human_serve("FLOAT")
                        elif event.key in CONTROL_P1["SPIKE"]:
                            human_serve("POWER")
                    else:
                        if event.key in CONTROL_P1["BUMP"]:
                            try_player_action(p1, "BUMP")
                        if event.key in CONTROL_P1["SET"]:
                            try_player_action(p1, "SET")
                        if event.key in CONTROL_P1["SPIKE"]:
                            p1.jump()
                            try_player_action(p1, "SPIKE")
                        if event.key in CONTROL_P1["DROP"]:
                            try_player_action(p1, "DROP")
                        if event.key in CONTROL_P1["DIVE"]:
                            try_player_action(p1, "DIVE")

            # Jogador 1 - local.
            if game_state == "PLAYING" and mode == "1V1_LOCAL":
                p1 = human_left_player()
                if p1:
                    if event.key in CONTROL_LOCAL_P1["jump"]:
                        if ball.is_serving and current_server == "left":
                            human_serve()
                        else:
                            p1.jump()
                    if ball.is_serving and current_server == "left":
                        if event.key in CONTROL_LOCAL_P1["BUMP"]:
                            human_serve("NORMAL")
                        elif event.key in CONTROL_LOCAL_P1["SET"]:
                            human_serve("FLOAT")
                        elif event.key in CONTROL_LOCAL_P1["SPIKE"]:
                            human_serve("POWER")
                    else:
                        for action in ("BUMP", "SET"):
                            if event.key in CONTROL_LOCAL_P1[action]:
                                try_player_action(p1, action)
                        if event.key in CONTROL_LOCAL_P1["SPIKE"]:
                            p1.jump()
                            try_player_action(p1, "SPIKE")
                        if event.key in CONTROL_LOCAL_P1["DROP"]:
                            try_player_action(p1, "DROP")
                        if event.key in CONTROL_LOCAL_P1["DIVE"]:
                            try_player_action(p1, "DIVE")

            # Jogador 2 - local.
            if game_state == "PLAYING" and mode == "1V1_LOCAL":
                p2 = human_right_player()
                if p2:
                    if event.key in CONTROL_P2["jump"]:
                        if ball.is_serving and current_server == "right":
                            human_serve()
                        else:
                            p2.jump()
                    if ball.is_serving and current_server == "right":
                        if event.key in CONTROL_P2["BUMP"]:
                            human_serve("NORMAL")
                        elif event.key in CONTROL_P2["SET"]:
                            human_serve("FLOAT")
                        elif event.key in CONTROL_P2["SPIKE"]:
                            human_serve("POWER")
                    else:
                        for action in ("BUMP", "SET"):
                            if event.key in CONTROL_P2[action]:
                                try_player_action(p2, action)
                        if event.key in CONTROL_P2["SPIKE"]:
                            p2.jump()
                            try_player_action(p2, "SPIKE")
                        if event.key in CONTROL_P2["DROP"]:
                            try_player_action(p2, "DROP")
                        if event.key in CONTROL_P2["DIVE"]:
                            try_player_action(p2, "DIVE")

        elif event.type == pygame.KEYUP:
            keys_down.discard(event.key)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos

            if game_state == "MENU":
                if menu_page == "MAIN":
                    if 430 <= mx <= 850 and 334 <= my <= 394:
                        menu_page = "MODE"
                    elif 430 <= mx <= 630 and 412 <= my <= 470:
                        start_selected_mode("TREINO")
                    elif 650 <= mx <= 850 and 412 <= my <= 470:
                        menu_page = "TUTORIAL"
                    elif 430 <= mx <= 850 and 488 <= my <= 546:
                        running = False

                elif menu_page == "MODE":
                    for rect, selected in mode_rects():
                        x, y, w, h = rect
                        if x <= mx <= x + w and y <= my <= y + h:
                            if selected in ("1V1_LOCAL", "TREINO"):
                                start_selected_mode(selected)
                            else:
                                pending_mode = selected
                                menu_page = "DIFFICULTY"
                            break
                    if 510 <= mx <= 770 and 520 <= my <= 570:
                        menu_page = "MAIN"

                elif menu_page == "DIFFICULTY":
                    for rect, selected in difficulty_rects():
                        x, y, w, h = rect
                        if x <= mx <= x + w and y <= my <= y + h:
                            difficulty = selected
                            start_selected_mode(pending_mode)
                            break

                elif menu_page == "TUTORIAL":
                    menu_page = "MAIN"

            elif game_state == "MATCHOVER":
                if 450 <= mx <= 830 and 415 <= my <= 473:
                    reset_match()
                elif 500 <= mx <= 780 and 525 <= my <= 567:
                    game_state = "MENU"
                    menu_page = "MAIN"

    # ========================================================
    # ATUALIZACAO
    # ========================================================

    if game_state == "PLAYING":
        # Barra de força do saque oscila enquanto a bola espera, como um saque carregado.
        if ball.is_serving:
            serve_charge += serve_charge_dir * 0.018 * (dt * FPS)
            if serve_charge >= 1.0:
                serve_charge = 1.0
                serve_charge_dir = -1.0
            elif serve_charge <= 0.28:
                serve_charge = 0.28
                serve_charge_dir = 1.0
            set_serve_direction_from_controls()

        # Movimento humano.
        if mode in ("1V1_BOT", "2V2_BOT"):
            p1 = human_left_player()
            if p1:
                direction = 0
                if key_is_down(keys_down, CONTROL_P1["left"]):
                    direction -= 1
                if key_is_down(keys_down, CONTROL_P1["right"]):
                    direction += 1
                p1.set_move_input(direction)

        elif mode == "1V1_LOCAL":
            p1 = human_left_player()
            p2 = human_right_player()
            if p1:
                direction = 0
                if key_is_down(keys_down, CONTROL_LOCAL_P1["left"]):
                    direction -= 1
                if key_is_down(keys_down, CONTROL_LOCAL_P1["right"]):
                    direction += 1
                p1.set_move_input(direction)
            if p2:
                direction = 0
                if key_is_down(keys_down, CONTROL_P2["left"]):
                    direction -= 1
                if key_is_down(keys_down, CONTROL_P2["right"]):
                    direction += 1
                p2.set_move_input(direction)

        start_bot_serve_if_needed()
        ball.update(dt, score_point)
        for player in all_players:
            player.update(dt)

    elif game_state == "PAUSED":
        pass
    elif game_state == "POINT_SCORED":
        point_timer -= dt * FPS
        if point_timer <= 0:
            continue_after_point()

    # Particulas e textos.
    for particle in particles[:]:
        particle.update(dt)
        if particle.life <= 0:
            particles.remove(particle)

    for floater in floating_texts[:]:
        floater.update(dt)
        if floater.life <= 0:
            floating_texts.remove(floater)

    # ========================================================
    # DESENHO
    # ========================================================

    frame = pygame.Surface((GAME_W, GAME_H)).convert()

    if game_state == "MENU":
        if menu_page == "MAIN":
            draw_main_menu(frame)
        elif menu_page == "MODE":
            draw_mode_menu(frame)
        elif menu_page == "DIFFICULTY":
            draw_difficulty_menu(frame)
        else:
            draw_tutorial(frame)
    else:
        draw_court(frame)
        draw_touch_sequence(frame)
        for particle in particles:
            particle.draw(frame)
        for player in all_players:
            player.draw(frame)
        ball.draw(frame)
        for floater in floating_texts:
            floater.draw(frame)
        draw_hud(frame)
        draw_serve_panel(frame)
        if game_state == "PAUSED":
            draw_pause_overlay(frame)
        if game_state == "MATCHOVER":
            draw_matchover(frame)

    if camera_shake > 0:
        shake_x = random.uniform(-camera_shake / 2, camera_shake / 2)
        shake_y = random.uniform(-camera_shake / 2, camera_shake / 2)
        screen.fill(BG)
        screen.blit(frame, (int(shake_x), int(shake_y)))
        camera_shake *= 0.85 ** (dt * FPS)
        if camera_shake < 0.5:
            camera_shake = 0
    else:
        screen.blit(frame, (0, 0))

    pygame.display.flip()

pygame.quit()
