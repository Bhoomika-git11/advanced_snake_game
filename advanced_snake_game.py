import tkinter as tk
import random
import math
import json
import os
import time

# Constants 
COLS, ROWS = 25, 25
CELL       = 22
WIDTH      = COLS * CELL   # 550
HEIGHT     = ROWS * CELL   # 550
PANEL_H    = 70

# Colours
BG         = "#050a0e"
GRID_COL   = "#0d1f26"
GREEN      = "#00ff88"
RED        = "#ff2d55"
BLUE       = "#00d4ff"
YELLOW     = "#ffd700"
DIM        = "#1a3a4a"
LABEL_COL  = "#2a5a6a"

BEST_FILE  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "snake_best.json")

DIFF_CFG = {
    "easy":   dict(base_speed=160, min_speed=90,  level_step=8,  size_step=1.2, label="EASY",   color=GREEN),
    "medium": dict(base_speed=120, min_speed=60,  level_step=12, size_step=1.8, label="MEDIUM", color=YELLOW),
    "hard":   dict(base_speed=80,  min_speed=40,  level_step=16, size_step=2.5, label="HARD",   color=RED),
}
DIFF_DESC = {
    "easy":   "Chill pace · grows slowly",
    "medium": "Balanced · gets spicy fast",
    "hard":   "Brutal · no mercy",
}

#  Helpers 
def load_best():
    try:
        with open(BEST_FILE) as f:
            return json.load(f).get("best", 0)
    except Exception:
        return 0

def save_best(val):
    try:
        with open(BEST_FILE, "w") as f:
            json.dump({"best": val}, f)
    except Exception:
        pass

def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_hex(r, g, b):
    return f"#{int(r):02x}{int(g):02x}{int(b):02x}"

def alpha_over_bg(r, g, b, a):
    br, bg_, bb = 5, 10, 14
    return rgb_to_hex(br+(r-br)*a, bg_+(g-bg_)*a, bb+(b-bb)*a)

def rounded_rect(canvas, x1, y1, x2, y2, r=4, **kw):
    pts = [
        x1+r, y1,   x2-r, y1,
        x2,   y1,   x2,   y1+r,
        x2,   y2-r, x2,   y2,
        x2-r, y2,   x1+r, y2,
        x1,   y2,   x1,   y2-r,
        x1,   y1+r, x1,   y1,
        x1+r, y1,
    ]
    return canvas.create_polygon(pts, smooth=True, **kw)

#  Particle 
class Particle:
    def __init__(self, x, y, color):
        angle = random.uniform(0, math.tau)
        spd   = random.uniform(1.5, 5.0)
        self.x  = x;  self.y  = y
        self.vx = math.cos(angle)*spd
        self.vy = math.sin(angle)*spd
        self.life  = 1.0
        self.decay = random.uniform(0.03, 0.07)
        self.size  = random.uniform(2, 5)
        self.color = color
        self.id    = None

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.15
        self.life -= self.decay
        return self.life > 0

#  Main Game 
class SnakeGame:
    def __init__(self, root):
        self.root  = root
        root.title("Snake")
        root.configure(bg=BG)

        root.resizable(True, True)

        self.best       = load_best()
        self.difficulty = "easy"
        self.game_running = False
        self.paused       = False
        self._after_id    = None
        self._anim_id     = None

        self.snake         = []
        self.direction     = (1, 0)
        self.next_direction = (1, 0)
        self.score         = 0
        self.level         = 1
        self.speed         = 120
        self.base_speed    = 120
        self.food          = {"x": 0, "y": 0}
        self.special_food  = None
        self.special_timer = None
        self.particles     = []
        self.eat_flash     = 0
        self.death_flash   = 0
        self.lvlup_anim    = None

        self._build_ui()
        self._show_start()
        self._anim_loop()

    #  UI Build 
    def _build_ui(self):
        # HUD frame
        hud = tk.Frame(self.root, bg=BG, height=PANEL_H)
        hud.pack(fill="x", padx=10, pady=(10,4))

        def stat_col(parent, label_text, var_text, color=BLUE):
            col = tk.Frame(parent, bg=BG)
            col.pack(side="left", expand=True)
            tk.Label(col, text=label_text, bg=BG, fg=LABEL_COL,
                     font=("Courier", 8, "bold")).pack()
            lbl = tk.Label(col, text=var_text, bg=BG, fg=color,
                           font=("Courier", 18, "bold"))
            lbl.pack()
            return lbl

        self.lbl_score = stat_col(hud, "SCORE",  "000", BLUE)
        self.lbl_level = stat_col(hud, "LEVEL",  "01",  BLUE)
        self.lbl_best  = stat_col(hud, "BEST",   "000", BLUE)
        self.lbl_mode  = stat_col(hud, "MODE",   "EASY", GREEN)
        self.lbl_speed = stat_col(hud, "SPEED",  "---", YELLOW)

        # Canvas
        self.cv = tk.Canvas(self.root, width=WIDTH, height=HEIGHT,
                            bg=BG, highlightthickness=2,
                            highlightbackground=DIM)
        self.cv.pack(padx=10, pady=(0,10))

        # Key bindings
        self.root.bind("<KeyPress>", self._on_key)

    # Overlay helpers
    def _clear_overlays(self):
        self.cv.delete("overlay")

    def _show_start(self):
        self._clear_overlays()
        cv = self.cv
        cx, cy = WIDTH//2, HEIGHT//2

        # Dark backdrop
        cv.create_rectangle(0, 0, WIDTH, HEIGHT,
                            fill="#050a0e", stipple="gray50",
                            tags="overlay")
        cv.create_rectangle(0, 0, WIDTH, HEIGHT,
                            fill="#050a0e", tags="overlay")

        # Title
        cv.create_text(cx, cy-130, text="SNAKE",
                       fill=GREEN, font=("Courier", 36, "bold"),
                       tags="overlay")
        cv.create_text(cx, cy-90, text="Navigate · Eat · Grow · Survive",
                       fill=LABEL_COL, font=("Courier", 10),
                       tags="overlay")

        # Difficulty label
        cv.create_text(cx, cy-55, text="SELECT DIFFICULTY",
                       fill=DIM, font=("Courier", 9, "bold"),
                       tags="overlay")

        # Difficulty buttons
        btn_data = [
            ("easy",   "EASY",   cx-120, GREEN),
            ("medium", "MEDIUM", cx,     YELLOW),
            ("hard",   "HARD",   cx+120, RED),
        ]
        self._diff_btns = {}
        for key, lbl, bx, col in btn_data:
            tag = f"diff_{key}"
            r = rounded_rect(cv, bx-38, cy-35, bx+38, cy-10, r=5,
                             fill=BG, outline=col, width=2, tags=("overlay", tag))
            t = cv.create_text(bx, cy-22, text=lbl, fill=col,
                               font=("Courier", 9, "bold"),
                               tags=("overlay", tag))
            self._diff_btns[key] = (r, t, col, bx)
            cv.tag_bind(tag, "<Button-1>", lambda e, k=key: self._select_diff(k))

        # Desc text
        self._diff_desc_id = cv.create_text(cx, cy+2,
                                            text=DIFF_DESC[self.difficulty],
                                            fill=LABEL_COL, font=("Courier", 9),
                                            tags="overlay")

        # START button
        sr = rounded_rect(cv, cx-70, cy+20, cx+70, cy+50, r=6,
                         fill=BG, outline=GREEN, width=2, tags=("overlay","start_btn"))
        st = cv.create_text(cx, cy+35, text="START GAME",
                            fill=GREEN, font=("Courier", 10, "bold"),
                            tags=("overlay","start_btn"))
        cv.tag_bind("start_btn", "<Button-1>", lambda e: self._start_game())
        cv.tag_bind("start_btn", "<Enter>",
                    lambda e: [cv.itemconfig(sr, fill=GREEN),
                               cv.itemconfig(st, fill=BG)])
        cv.tag_bind("start_btn", "<Leave>",
                    lambda e: [cv.itemconfig(sr, fill=BG),
                               cv.itemconfig(st, fill=GREEN)])

        # Key hints
        hints = "↑ ↓ ← →   WASD   P = Pause"
        cv.create_text(cx, cy+75, text=hints, fill=DIM,
                       font=("Courier", 8), tags="overlay")

        self._select_diff(self.difficulty)

    def _select_diff(self, key):
        self.difficulty = key
        cv = self.cv
        for k, (r, t, col, _) in self._diff_btns.items():
            if k == key:
                cv.itemconfig(r, fill=col, outline=col)
                cv.itemconfig(t, fill=BG)
            else:
                cv.itemconfig(r, fill=BG, outline=col)
                cv.itemconfig(t, fill=col)
        cv.itemconfig(self._diff_desc_id, text=DIFF_DESC[key])

    def _show_gameover(self):
        self._clear_overlays()
        cv = self.cv
        cx, cy = WIDTH//2, HEIGHT//2

        cv.create_rectangle(0, 0, WIDTH, HEIGHT,
                            fill="#050a0e", tags="overlay")

        cv.create_text(cx, cy-100, text="GAME OVER",
                       fill=RED, font=("Courier", 34, "bold"),
                       tags="overlay")

        cfg = DIFF_CFG[self.difficulty]
        info = f"Score: {self.score:03d}   Level: {self.level:02d}   {cfg['label']}"
        cv.create_text(cx, cy-55, text=info,
                       fill=YELLOW, font=("Courier", 11, "bold"),
                       tags="overlay")

        if self.score >= self.best and self.score > 0:
            cv.create_text(cx, cy-28, text="✦ NEW HIGH SCORE ✦",
                           fill=YELLOW, font=("Courier", 10, "bold"),
                           tags="overlay")

        def make_btn(label, bx, cmd, col=GREEN):
            tag = f"btn_{label.replace(' ','_')}"
            r = rounded_rect(cv, bx-60, cy, bx+60, cy+32, r=6,
                            fill=BG, outline=col, width=2,
                            tags=("overlay", tag))
            t = cv.create_text(bx, cy+16, text=label, fill=col,
                               font=("Courier", 9, "bold"),
                               tags=("overlay", tag))
            cv.tag_bind(tag, "<Button-1>", lambda e: cmd())
            cv.tag_bind(tag, "<Enter>",
                        lambda e: [cv.itemconfig(r, fill=col),
                                   cv.itemconfig(t, fill=BG)])
            cv.tag_bind(tag, "<Leave>",
                        lambda e: [cv.itemconfig(r, fill=BG),
                                   cv.itemconfig(t, fill=col)])

        make_btn("PLAY AGAIN", cx-75, self._start_game, GREEN)
        make_btn("MENU",       cx+75, self._show_start,  DIM)

    def _show_pause(self):
        cv = self.cv
        cv.create_rectangle(WIDTH//2-120, HEIGHT//2-40,
                            WIDTH//2+120, HEIGHT//2+40,
                            fill="#050a0e", outline=BLUE, width=2,
                            tags="pause_box")
        cv.create_text(WIDTH//2, HEIGHT//2-10, text="PAUSED",
                       fill=BLUE, font=("Courier", 22, "bold"),
                       tags="pause_box")
        cv.create_text(WIDTH//2, HEIGHT//2+18, text="Press P to resume",
                       fill=LABEL_COL, font=("Courier", 9),
                       tags="pause_box")

    #  Game Logic 
    def _start_game(self):
        self._clear_overlays()
        if self._after_id:
            self.root.after_cancel(self._after_id)

        cfg = DIFF_CFG[self.difficulty]
        self.snake    = [{"x": 12, "y": 12}, {"x": 11, "y": 12}, {"x": 10, "y": 12}]
        self.direction      = (1, 0)
        self.next_direction = (1, 0)
        self.score          = 0
        self.level          = 1
        self.base_speed     = cfg["base_speed"]
        self.speed          = self.base_speed
        self.particles      = []
        self.special_food   = None
        self.special_timer  = None
        self.eat_flash      = 0
        self.lvlup_anim     = None
        self.death_flash    = 0
        self.game_running   = True
        self.paused         = False

        self.lbl_mode.config(text=cfg["label"], fg=cfg["color"])
        self._place_food()
        self._update_hud()
        self._schedule_tick()

    def _place_food(self):
        while True:
            fx = random.randint(0, COLS-1)
            fy = random.randint(0, ROWS-1)
            if not any(s["x"]==fx and s["y"]==fy for s in self.snake):
                self.food = {"x": fx, "y": fy}
                break

    def _recalc_speed(self):
        cfg = DIFF_CFG[self.difficulty]
        lb  = (self.level - 1) * cfg["level_step"]
        sb  = int((len(self.snake) - 3) * cfg["size_step"])
        self.speed = max(cfg["min_speed"], self.base_speed - lb - sb)

    def _schedule_tick(self):
        if self.game_running and not self.paused:
            self._after_id = self.root.after(self.speed, self._tick)

    def _tick(self):
        if not self.game_running or self.paused:
            return

        dx, dy = self.next_direction
        if (dx, dy) != (-self.direction[0], -self.direction[1]):
            self.direction = (dx, dy)

        hx = self.snake[0]["x"] + self.direction[0]
        hy = self.snake[0]["y"] + self.direction[1]

        if hx < 0 or hx >= COLS or hy < 0 or hy >= ROWS:
            self._end_game(); return
        if any(s["x"]==hx and s["y"]==hy for s in self.snake):
            self._end_game(); return

        self.snake.insert(0, {"x": hx, "y": hy})
        ate = False

        if hx == self.food["x"] and hy == self.food["y"]:
            self.score += 10 * self.level
            ate = True
            self._spawn_particles(
                hx * CELL + CELL//2, hy * CELL + CELL//2, GREEN, 14)
            self.eat_flash = 8
            self._place_food()
            if self.score >= self.level * 50:
                self.level += 1
                self.lvlup_anim = {"timer": 60, "level": self.level}
                self._spawn_particles(WIDTH//2, HEIGHT//2,
                    DIFF_CFG[self.difficulty]["color"], 30)
            self._recalc_speed()
            self._update_hud()

        if (self.special_food and
                hx == self.special_food["x"] and hy == self.special_food["y"]):
            self.score += 50 * self.level
            ate = True
            self._spawn_particles(
                hx * CELL + CELL//2, hy * CELL + CELL//2, YELLOW, 20)
            self.special_food = None
            if self.special_timer:
                self.root.after_cancel(self.special_timer)
                self.special_timer = None
            self._recalc_speed()
            self._update_hud()

        if not ate:
            self.snake.pop()

        if not self.special_food and random.random() < 0.005:
            while True:
                sx = random.randint(0, COLS-1)
                sy = random.randint(0, ROWS-1)
                if (not any(s["x"]==sx and s["y"]==sy for s in self.snake)
                        and not (sx==self.food["x"] and sy==self.food["y"])):
                    self.special_food = {"x": sx, "y": sy}
                    break
            self.special_timer = self.root.after(5000, self._expire_special)

        self._schedule_tick()

    def _expire_special(self):
        self.special_food  = None
        self.special_timer = None

    def _spawn_particles(self, x, y, color, count=14):
        for _ in range(count):
            self.particles.append(Particle(x, y, color))

    def _end_game(self):
        self.game_running = False
        if self.score > self.best:
            self.best = self.score
            save_best(self.best)
            self._update_hud()
        self.death_flash = 10
        self.root.after(700, self._show_gameover)

    # HUD 
    def _update_hud(self):
        self.lbl_score.config(text=f"{self.score:03d}")
        self.lbl_level.config(text=f"{self.level:02d}")
        self.lbl_best.config( text=f"{self.best:03d}")
        self.lbl_speed.config(text=f"{self.speed}ms")

    # Animation loop 
    def _anim_loop(self):
        self._draw()
        self.root.after(16, self._anim_loop)

    def _draw(self):
        cv = self.cv
        cv.delete("game")

        if not self.game_running and self.death_flash <= 0:
            return

        self._draw_food()
        if self.special_food:
            self._draw_special_food()
        self._draw_snake()
        self._draw_particles()

        if self.eat_flash > 0:
            self.eat_flash -= 1
            a = self.eat_flash / 8
            col = alpha_over_bg(0, 255, 136, a * 0.5)
            cv.create_rectangle(0, 0, WIDTH, HEIGHT,
                                outline=col, width=4, tags="game")

        if self.death_flash > 0:
            self.death_flash -= 1
            a = self.death_flash / 10
            col = alpha_over_bg(255, 45, 85, a)
            cv.create_rectangle(0, 0, WIDTH, HEIGHT,
                                fill=col, tags="game")

        if self.lvlup_anim:
            self._draw_levelup()

    def _draw_grid(self):
        cv = self.cv
        for i in range(COLS+1):
            cv.create_line(i*CELL, 0, i*CELL, HEIGHT,
                          fill="#0d1f26", tags="game")
        for j in range(ROWS+1):
            cv.create_line(0, j*CELL, WIDTH, j*CELL,
                          fill="#0d1f26", tags="game")

    def _draw_snake(self):
        cv = self.cv
        n  = len(self.snake)

        for i, seg in enumerate(self.snake):
            t   = i / max(n, 1)
            pad = 2 if i > 0 else 1
            x1  = seg["x"] * CELL + pad
            y1  = seg["y"] * CELL + pad
            x2  = (seg["x"]+1) * CELL - pad
            y2  = (seg["y"]+1) * CELL - pad

            if i == 0:
                # Glow behind head
                rounded_rect(cv, x1-2, y1-2, x2+2, y2+2, r=5,
                             fill="#004433", outline="", tags="game")
                # Head base
                rounded_rect(cv, x1, y1, x2, y2, r=4,
                             fill=GREEN, outline="", tags="game")
                # Forehead shine strip
                rounded_rect(cv, x1+(x2-x1)//4, y1+2, x2-(x2-x1)//4, y1+(y2-y1)//3,
                             r=3, fill="#aaffd0", outline="", tags="game")
                # Draw detailed face
                self._draw_eyes(seg["x"], seg["y"])
            else:
                g   = max(0, int(200 - t*80))
                b   = max(0, int(100 - t*60))
                col = f"#00{g:02x}{b:02x}"
                rounded_rect(cv, x1, y1, x2, y2, r=3,
                             fill=col, outline="", tags="game")

    def _draw_eyes(self, gx, gy):
        """Detailed reptile eyes + nostrils + forked tongue on snake head."""
        cv  = self.cv
        dx, dy = self.direction
        cx  = gx * CELL + CELL // 2
        cy  = gy * CELL + CELL // 2
        ew  = max(2, CELL // 6)   # eye radius

        # Eye positions + tongue tip based on direction
        if dx == 1:
            eye_offsets = [(CELL//5, -CELL//5), (CELL//5,  CELL//5)]
            tongue_tip  = (cx + CELL//2, cy)
            fdir        = (1, 0)
        elif dx == -1:
            eye_offsets = [(-CELL//5, -CELL//5), (-CELL//5, CELL//5)]
            tongue_tip  = (cx - CELL//2, cy)
            fdir        = (-1, 0)
        elif dy == -1:
            eye_offsets = [(-CELL//5, -CELL//5), (CELL//5, -CELL//5)]
            tongue_tip  = (cx, cy - CELL//2)
            fdir        = (0, -1)
        else:
            eye_offsets = [(-CELL//5, CELL//5), (CELL//5, CELL//5)]
            tongue_tip  = (cx, cy + CELL//2)
            fdir        = (0, 1)

        # Eyes
        for ox, oy in eye_offsets:
            ex, ey = cx + ox, cy + oy
            # White sclera
            cv.create_oval(ex-ew, ey-ew, ex+ew, ey+ew,
                          fill="white", outline="", tags="game")
            # Vertical slit pupil (reptile style)
            pw = max(1, ew // 2)
            cv.create_oval(ex - pw//2, ey - ew + 2,
                          ex + pw//2, ey + ew - 2,
                          fill="#050a0e", outline="", tags="game")
            # Eye shine dot
            cv.create_oval(ex + 1,      ey - ew + 2,
                          ex + pw,      ey - ew + pw + 1,
                          fill="white", outline="", tags="game")
            # Iris ring
            cv.create_oval(ex-ew+1, ey-ew+1, ex+ew-1, ey+ew-1,
                          fill="", outline="#00aa44", width=1, tags="game")

        #  Nostrils 
        ns   = max(1, CELL // 14)
        n_cx = tongue_tip[0] - fdir[0] * CELL // 5
        n_cy = tongue_tip[1] - fdir[1] * CELL // 5
        perp = (-fdir[1], fdir[0])
        for sign in (-1, 1):
            nx = n_cx + sign * perp[0] * (CELL // 7)
            ny = n_cy + sign * perp[1] * (CELL // 7)
            cv.create_oval(nx-ns, ny-ns, nx+ns, ny+ns,
                          fill="#003322", outline="", tags="game")

        #  Forked tongue 
        tx, ty   = tongue_tip
        tlen     = max(4, CELL // 3)
        fork     = max(3, CELL // 5)
        tw       = max(1, CELL // 12)
        # Tongue stem
        cv.create_line(tx, ty,
                      tx + fdir[0]*tlen, ty + fdir[1]*tlen,
                      fill=RED, width=tw, capstyle="round", tags="game")
        # Fork tips
        tip_x = tx + fdir[0]*tlen
        tip_y = ty + fdir[1]*tlen
        cv.create_line(tip_x, tip_y,
                      tip_x + fdir[0]*fork - fdir[1]*fork,
                      tip_y + fdir[1]*fork + fdir[0]*fork,
                      fill=RED, width=max(1, tw-1), capstyle="round", tags="game")
        cv.create_line(tip_x, tip_y,
                      tip_x + fdir[0]*fork + fdir[1]*fork,
                      tip_y + fdir[1]*fork - fdir[0]*fork,
                      fill=RED, width=max(1, tw-1), capstyle="round", tags="game")

    def _draw_food(self):
        cv  = self.cv
        fx  = self.food["x"] * CELL + CELL//2
        fy  = self.food["y"] * CELL + CELL//2
        pulse = math.sin(time.time() * 4) * 2

        r = CELL//2 - 2 + pulse
        for rad, a in [(r+5, 0.12), (r+3, 0.2), (r+1, 0.4)]:
            col = alpha_over_bg(0, 255, 136, a)
            cv.create_oval(fx-rad, fy-rad, fx+rad, fy+rad,
                          fill=col, outline="", tags="game")
        cv.create_oval(fx-r+2, fy-r+2, fx+r-2, fy+r-2,
                      fill=GREEN, outline="#aaffd0", width=1, tags="game")

    def _draw_special_food(self):
        cv  = self.cv
        sx  = self.special_food["x"] * CELL + CELL//2
        sy  = self.special_food["y"] * CELL + CELL//2
        spin = time.time() * 3
        r_outer = CELL * 0.38
        r_inner = CELL * 0.16
        pts = []
        for i in range(10):
            r   = r_outer if i % 2 == 0 else r_inner
            ang = spin + i * math.pi / 5 - math.pi/2
            pts.extend([sx + r*math.cos(ang), sy + r*math.sin(ang)])
        cv.create_polygon(pts, fill=YELLOW, outline="#fff0a0",
                         width=1, tags="game")

    def _draw_particles(self):
        cv   = self.cv
        live = []
        for p in self.particles:
            if p.update():
                a   = max(0, min(1, p.life))
                col = alpha_over_bg(*hex_to_rgb(p.color), a)
                s   = max(1, p.size * p.life)
                cv.create_rectangle(
                    p.x-s, p.y-s, p.x+s, p.y+s,
                    fill=col, outline="", tags="game")
                live.append(p)
        self.particles = live

    def _draw_levelup(self):
        cv  = self.cv
        anim = self.lvlup_anim
        anim["timer"] -= 1
        if anim["timer"] <= 0:
            self.lvlup_anim = None
            return

        t     = anim["timer"] / 60
        fade  = t if t > 0.3 else t/0.3
        scale = 0.5 + (1-t)*0.8
        cx, cy = WIDTH//2, HEIGHT//2

        for i in range(3):
            rad = int((60 + i*35) * (1-t))
            a   = max(0, fade - i*0.25)
            col = alpha_over_bg(0, 255, 136, a * 0.5)
            cv.create_oval(cx-rad, cy-rad, cx+rad, cy+rad,
                          outline=col, width=2, tags="game")

        fs = max(8, int(22 * scale))
        cv.create_text(cx, cy-16,
                      text="LEVEL  UP!",
                      fill=alpha_over_bg(0, 255, 136, fade),
                      font=("Courier", fs, "bold"),
                      tags="game")
        fs2 = max(10, int(34 * scale))
        cv.create_text(cx, cy+18,
                      text=f"{anim['level']:02d}",
                      fill=alpha_over_bg(255, 215, 0, fade),
                      font=("Courier", fs2, "bold"),
                      tags="game")

    #  Input
    def _on_key(self, event):
        k = event.keysym.lower()
        moves = {
            "up":    (0,-1), "w": (0,-1),
            "down":  (0, 1), "s": (0, 1),
            "left":  (-1,0), "a": (-1,0),
            "right": (1, 0), "d": (1, 0),
        }
        if k == "p":
            if not self.game_running:
                return
            self.paused = not self.paused
            if self.paused:
                self._show_pause()
            else:
                self.cv.delete("pause_box")
                self._schedule_tick()
            return
        if k in moves and self.game_running and not self.paused:
            nd = moves[k]
            if (nd[0] != -self.direction[0] or nd[1] != -self.direction[1]):
                self.next_direction = nd

#  Entry Point 
if __name__ == "__main__":
    root = tk.Tk()
    app  = SnakeGame(root)
    root.mainloop()
