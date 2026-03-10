import tkinter as tk
from tkinter import messagebox
import time
import random
import heapq
import json
import os
import math
import threading

# =========================
# Core puzzle + A* search
# =========================

class PuzzleState:
    def __init__(self, board, moves=0, previous=None):
        self.board = board
        self.moves = moves
        self.previous = previous
        self.empty_index = board.index(0)
        self._cached_h = 0

    def __lt__(self, other):
        return (self.moves + self._cached_h) < (other.moves + other._cached_h)

    def compute_h(self, goal, method="Manhattan"):
        if method == "Manhattan":
            h = 0
            for i, tile in enumerate(self.board):
                if tile == 0: continue
                gx, gy = divmod(goal.index(tile), 3)
                cx, cy = divmod(i, 3)
                h += abs(gx - cx) + abs(gy - cy)
            self._cached_h = h
            return h
        elif method == "Misplaced":
            h = sum(1 for i, tile in enumerate(self.board) if tile != 0 and tile != goal[i])
            self._cached_h = h
            return h
        elif method == "Linear Conflict":
            h = 0
            for i, tile in enumerate(self.board):
                if tile == 0: continue
                gx, gy = divmod(goal.index(tile), 3)
                cx, cy = divmod(i, 3)
                h += abs(gx - cx) + abs(gy - cy)
            for row in range(3):
                tiles = []
                for col in range(3):
                    idx = row * 3 + col
                    tile = self.board[idx]
                    if tile != 0 and goal.index(tile) // 3 == row:
                        tiles.append(goal.index(tile) % 3)
                for i in range(len(tiles)):
                    for j in range(i + 1, len(tiles)):
                        if tiles[i] > tiles[j]: h += 2
            for col in range(3):
                tiles = []
                for row in range(3):
                    idx = row * 3 + col
                    tile = self.board[idx]
                    if tile != 0 and goal.index(tile) % 3 == col:
                        tiles.append(goal.index(tile) // 3)
                for i in range(len(tiles)):
                    for j in range(i + 1, len(tiles)):
                        if tiles[i] > tiles[j]: h += 2
            self._cached_h = h
            return h
        self._cached_h = 0
        return 0

    def neighbors(self):
        neigh = []
        x, y = divmod(self.empty_index, 3)
        for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < 3 and 0 <= ny < 3:
                idx = nx * 3 + ny
                nb = self.board[:]
                nb[self.empty_index], nb[idx] = nb[idx], nb[self.empty_index]
                neigh.append(PuzzleState(nb, self.moves + 1, self))
        return neigh

def is_solvable(board, goal=None):
    if goal is None:
        goal = [1,2,3,4,5,6,7,8,0]
    goal_pos = {tile: i for i, tile in enumerate(goal) if tile != 0}
    tiles = [x for x in board if x != 0]
    inv = 0
    for i in range(len(tiles)):
        for j in range(i+1, len(tiles)):
            if goal_pos[tiles[i]] > goal_pos[tiles[j]]:
                inv += 1
    return inv % 2 == 0

def solve_puzzle(start, goal, heuristic="Manhattan", max_nodes=500000):
    start_state = PuzzleState(start)
    start_state.compute_h(goal, heuristic)
    counter = 0
    frontier = [(start_state.moves + start_state._cached_h, start_state.moves, counter, start_state)]
    explored = set()
    explored_count = 0
    while frontier:
        _, _, _, current = heapq.heappop(frontier)
        explored_count += 1
        if current.board == goal:
            path = []
            while current:
                path.append(current.board)
                current = current.previous
            return path[::-1], explored_count
        tcur = tuple(current.board)
        if tcur in explored:
            continue
        explored.add(tcur)
        if explored_count > max_nodes:
            return None, explored_count
        for n in current.neighbors():
            t = tuple(n.board)
            if t in explored:
                continue
            n.compute_h(goal, heuristic)
            counter += 1
            heapq.heappush(frontier, (n.moves + n._cached_h, n.moves, counter, n))
    return None, explored_count

def random_solvable_board(moves=60, start=None):
    board = start[:] if start else [1,2,3,4,5,6,7,8,0]
    st = PuzzleState(board)
    for _ in range(moves):
        st = random.choice(st.neighbors())
    return st.board

# =========================
# Sound engine
# =========================
class SoundEngine:
    def __init__(self):
        self.enabled = True
    def _play(self, freq, dur):
        if not self.enabled: return
        try:
            import winsound
            winsound.Beep(max(37,min(32767,int(freq))), dur)
        except: pass
    def play_move(self):
        threading.Thread(target=self._play, args=(440,40), daemon=True).start()
    def play_hint(self):
        threading.Thread(target=self._play, args=(600,60), daemon=True).start()
    def play_win(self):
        def seq():
            for f in [523,659,784,1047]:
                self._play(f, 100)
                time.sleep(0.06)
        threading.Thread(target=seq, daemon=True).start()
    def play_undo(self):
        threading.Thread(target=self._play, args=(300,40), daemon=True).start()
    def play_error(self):
        threading.Thread(target=self._play, args=(200,80), daemon=True).start()
    def play_shuffle(self):
        def seq():
            for f in [300,350,400]:
                self._play(f, 40)
                time.sleep(0.03)
        threading.Thread(target=seq, daemon=True).start()

# =========================
# Themes
# =========================
THEMES = {
    "Light": {
        "bg":"#f0f4ff","panel":"#ffffff","hud_bg":"#ffffff","hud_border":"#c5cfe8",
        "tile":"#4285f4","tile_border":"#1a73e8","tile_hover":"#5b9af5",
        "empty":"#dce8f7","grid":"#b0bec5","text":"#202124","tile_text":"#ffffff",
        "accent":"#ff7043","accent2":"#00c853","history_bg":"#f8f9ff","history_text":"#444",
        "goal_tile":"#00897b","goal_border":"#00695c","progress_bg":"#e0e7ff",
        "progress_fill":"#4285f4","particle":"#ffb300","shadow":"#c0c8e8",
    },
    "Dark": {
        "bg":"#0d1117","panel":"#161b22","hud_bg":"#161b22","hud_border":"#30363d",
        "tile":"#388bfd","tile_border":"#1f6feb","tile_hover":"#58a6ff",
        "empty":"#21262d","grid":"#30363d","text":"#c9d1d9","tile_text":"#ffffff",
        "accent":"#f78166","accent2":"#3fb950","history_bg":"#161b22","history_text":"#8b949e",
        "goal_tile":"#238636","goal_border":"#2ea043","progress_bg":"#21262d",
        "progress_fill":"#388bfd","particle":"#d29922","shadow":"#010409",
    },
    "Neon": {
        "bg":"#0a0010","panel":"#110020","hud_bg":"#110020","hud_border":"#7c00ff",
        "tile":"#7c00ff","tile_border":"#bf00ff","tile_hover":"#a020f0",
        "empty":"#1a0030","grid":"#3d0080","text":"#e0d0ff","tile_text":"#ffffff",
        "accent":"#ff00aa","accent2":"#00ffcc","history_bg":"#110020","history_text":"#aa88ff",
        "goal_tile":"#00ffaa","goal_border":"#00cc88","progress_bg":"#1a0030",
        "progress_fill":"#bf00ff","particle":"#ff00ff","shadow":"#05000a",
    },
    "Sunset": {
        "bg":"#1a0533","panel":"#2d0a4e","hud_bg":"#2d0a4e","hud_border":"#7b2d8b",
        "tile":"#e91e8c","tile_border":"#c2185b","tile_hover":"#f06292",
        "empty":"#3d1060","grid":"#6a1b7a","text":"#ffd6f0","tile_text":"#ffffff",
        "accent":"#ff6e40","accent2":"#ffd740","history_bg":"#2d0a4e","history_text":"#cc88bb",
        "goal_tile":"#ff6e40","goal_border":"#e64a19","progress_bg":"#3d1060",
        "progress_fill":"#e91e8c","particle":"#ffd740","shadow":"#0d0020",
    },
}

SCORES_FILE = os.path.join(os.path.expanduser("~"), ".eight_puzzle_v2.json")

def load_scores():
    try:
        if os.path.exists(SCORES_FILE):
            with open(SCORES_FILE) as f:
                return json.load(f)
    except: pass
    return {"best":{"Easy":None,"Medium":None,"Hard":None},"leaderboard":[]}

def save_scores(scores):
    try:
        with open(SCORES_FILE,"w") as f:
            json.dump(scores, f, indent=2)
    except: pass

# =========================
# Particle
# =========================
class Particle:
    def __init__(self, x, y, color):
        self.x, self.y = x, y
        angle = random.uniform(0, 2*math.pi)
        speed = random.uniform(2, 9)
        self.vx = math.cos(angle)*speed
        self.vy = math.sin(angle)*speed - 4
        self.life = random.uniform(0.6, 1.3)
        self.max_life = self.life
        self.color = color
        self.size = random.uniform(4, 10)
        self.vy_g = 0.3
    def update(self, dt):
        self.x += self.vx*dt*28
        self.y += self.vy*dt*28
        self.vy += self.vy_g
        self.life -= dt
        return self.life > 0
    def draw(self, canvas):
        a = max(0, self.life/self.max_life)
        s = self.size*a
        if s < 0.5: return
        canvas.create_oval(self.x-s, self.y-s, self.x+s, self.y+s,
                           fill=self.color, outline="")

# =========================
# Game
# =========================
class EightPuzzleGame:
    def __init__(self, root):
        self.root = root
        self.root.title("8-Puzzle Challenge")
        self.root.resizable(False, False)
        self.theme_name = "Light"
        self.theme = THEMES["Light"]
        self.scores = load_scores()
        self.sound = SoundEngine()

        self.goal = [1,2,3,4,5,6,7,8,0]
        self.board = self.goal[:]
        self.initial_board = self.goal[:]
        self.moves = 0
        self.start_time = None
        self.playing = False

        self.move_history = []
        self.undo_stack = []
        self.redo_stack = []

        self.solution = []
        self.anim_index = 0
        self.animating = False
        self.explored_count = 0
        self.solve_time = 0.0
        self.heuristic = "Manhattan"
        self._solving = False

        self.difficulty = tk.StringVar(value="Medium")
        self.diff_moves = {"Easy":20,"Medium":50,"Hard":100}

        self.particles = []
        self.particle_running = False
        self.hover_index = None
        self._click_index = None

        self.total_games = 0
        self.total_wins = 0
        self.win_streak = 0
        self.player_name = "Player"
        self._stats_timer = None

        self.build_start_screen()

    # ========== START SCREEN ==========
    def build_start_screen(self):
        t = self.theme
        self.start_frame = tk.Frame(self.root, bg=t["bg"])
        self.start_frame.pack(fill="both", expand=True)

        self.title_canvas = tk.Canvas(self.start_frame, width=500, height=76, bg=t["bg"], highlightthickness=0)
        self.title_canvas.pack(pady=(28,0))
        self._title_frame = 0
        self._animate_title()

        tk.Label(self.start_frame, text="Arrange tiles 1–8 into order  |  Powered by A* Search",
                 font=("Segoe UI",10), fg=t["text"], bg=t["bg"]).pack(pady=(2,12))

        row_top = tk.Frame(self.start_frame, bg=t["bg"])
        row_top.pack()

        self.preview_canvas = tk.Canvas(row_top, width=210, height=210, bg=t["bg"], highlightthickness=0)
        self.preview_canvas.grid(row=0, column=0, padx=16)
        self._preview_board = random_solvable_board(moves=10)
        self._preview_tick = 0
        self._animate_preview()

        stats_f = tk.Frame(row_top, bg=t["panel"], highlightbackground=t["hud_border"], highlightthickness=1)
        stats_f.grid(row=0, column=1, padx=10, sticky="ns")
        tk.Label(stats_f, text="YOUR STATS", font=("Segoe UI",9,"bold"), bg=t["panel"], fg=t["accent"]).pack(pady=(10,4))
        self.start_stats_lbl = tk.Label(stats_f, text=self._stats_text(), font=("Consolas",10),
                                        bg=t["panel"], fg=t["text"], justify="left")
        self.start_stats_lbl.pack(padx=16, pady=4)
        self.best_label = tk.Label(stats_f, text="", bg=t["panel"], fg=t["accent2"], font=("Segoe UI",9))
        self.best_label.pack(pady=(4,10), padx=10)
        self._update_best_preview()

        opts = tk.Frame(self.start_frame, bg=t["bg"])
        opts.pack(pady=10)
        lbl_kw = dict(bg=t["bg"], fg=t["text"], font=("Segoe UI",10))
        tk.Label(opts, text="Name:", **lbl_kw).grid(row=0, column=0, padx=6, pady=4, sticky="e")
        self.name_var = tk.StringVar(value=self.player_name)
        tk.Entry(opts, textvariable=self.name_var, width=12, font=("Segoe UI",10)).grid(row=0, column=1, padx=6)
        tk.Label(opts, text="Difficulty:", **lbl_kw).grid(row=0, column=2, padx=6, sticky="e")
        tk.OptionMenu(opts, self.difficulty, "Easy","Medium","Hard").grid(row=0, column=3, padx=6)
        tk.Label(opts, text="Heuristic:", **lbl_kw).grid(row=1, column=0, padx=6, pady=4, sticky="e")
        self.heuristic_var = tk.StringVar(value="Manhattan")
        tk.OptionMenu(opts, self.heuristic_var, "Manhattan","Misplaced","Linear Conflict").grid(row=1, column=1, padx=6)
        tk.Label(opts, text="Theme:", **lbl_kw).grid(row=1, column=2, padx=6, sticky="e")
        self.theme_var = tk.StringVar(value=self.theme_name)
        tk.OptionMenu(opts, self.theme_var, *THEMES.keys(), command=self._change_theme_start).grid(row=1, column=3, padx=6)
        self.sound_var = tk.BooleanVar(value=True)
        tk.Checkbutton(opts, text="🔊 Sound", variable=self.sound_var, bg=t["bg"], fg=t["text"],
                       selectcolor=t["bg"], font=("Segoe UI",10),
                       command=lambda: setattr(self.sound,"enabled",self.sound_var.get())
                       ).grid(row=2, column=0, columnspan=2, pady=4)

        btns = tk.Frame(self.start_frame, bg=t["bg"])
        btns.pack(pady=(8,4))
        bs = dict(font=("Segoe UI",11,"bold"), width=13, relief="flat", cursor="hand2", pady=6)
        tk.Button(btns, text="▶  Start Game", bg=t["tile"], fg=t["tile_text"], command=self.start_game, **bs).grid(row=0, column=0, padx=5, pady=4)
        tk.Button(btns, text="🏆 Leaderboard", bg=t["accent2"], fg="#fff", command=self.show_leaderboard, **bs).grid(row=0, column=1, padx=5, pady=4)
        tk.Button(btns, text="📖 How to Play", bg=t["panel"], fg=t["text"], command=self.show_instructions, **{**bs,"relief":"solid"}).grid(row=0, column=2, padx=5, pady=4)
        tk.Button(btns, text="✖  Exit", bg=t["accent"], fg="#fff", command=self.root.quit, **bs).grid(row=0, column=3, padx=5, pady=4)
        self.root.configure(bg=t["bg"])

    def _stats_text(self):
        return (f"  Games:   {self.total_games}\n"
                f"  Wins:    {self.total_wins}\n"
                f"  Streak:  {self.win_streak} 🔥\n")

    def _update_best_preview(self):
        lines = []
        for d in ["Easy","Medium","Hard"]:
            b = self.scores["best"].get(d)
            lines.append(f"{d}: {b['moves']}m {b['time']:.1f}s" if b else f"{d}: —")
        self.best_label.configure(text="\n".join(lines))

    def _animate_title(self):
        if not hasattr(self,"title_canvas") or not self.title_canvas.winfo_exists(): return
        self.title_canvas.delete("all")
        t = self.theme
        text = "8-Puzzle  Challenge"
        for i, ch in enumerate(text):
            off = math.sin(self._title_frame*0.07 + i*0.55)*9
            col = t["tile"] if i%2==0 else t["accent"]
            self.title_canvas.create_text(28+i*24, 38+off, text=ch,
                                          font=("Segoe UI",22,"bold"), fill=col)
        self._title_frame += 1
        self._title_anim_id = self.root.after(38, self._animate_title)

    def _animate_preview(self):
        if not hasattr(self,"preview_canvas") or not self.preview_canvas.winfo_exists(): return
        self._preview_tick += 1
        if self._preview_tick % 55 == 0:
            self._preview_board = random.choice(PuzzleState(self._preview_board).neighbors()).board
        self._draw_preview(self._preview_board, self._preview_tick)
        self._preview_anim_id = self.root.after(50, self._animate_preview)

    def _draw_preview(self, board, tick):
        self.preview_canvas.delete("all")
        t = self.theme
        cell, pad = 62, 6
        for i, tile in enumerate(board):
            r, c = divmod(i, 3)
            cx = pad + c*cell + cell//2
            cy = pad + r*cell + cell//2
            p = 1.0 + 0.025*math.sin(tick*0.09 + i*0.7)
            hw = (cell//2 - 3)*p
            if tile == 0:
                self.preview_canvas.create_rectangle(cx-hw,cy-hw,cx+hw,cy+hw,
                                                     fill=t["empty"],outline=t["grid"],width=2)
            else:
                self.preview_canvas.create_rectangle(cx-hw+3,cy-hw+3,cx+hw+3,cy+hw+3,
                                                     fill=t["shadow"],outline="")
                self.preview_canvas.create_rectangle(cx-hw,cy-hw,cx+hw,cy+hw,
                                                     fill=t["tile"],outline=t["tile_border"],width=2)
                self.preview_canvas.create_text(cx,cy,text=str(tile),
                                                fill=t["tile_text"],font=("Segoe UI",17,"bold"))

    def _change_theme_start(self, name):
        self.theme_name = name
        self.theme = THEMES[name]
        for attr in ("_title_anim_id","_preview_anim_id"):
            if hasattr(self, attr):
                try: self.root.after_cancel(getattr(self, attr))
                except: pass
        self.start_frame.destroy()
        self.build_start_screen()

    def show_instructions(self):
        messagebox.showinfo("How to Play",
            "🎯 GOAL\nArrange tiles 1–8 with the empty space at the bottom-right.\n\n"
            "🖱️ CONTROLS\n• Click a tile next to the blank to slide it.\n"
            "• Arrow Keys move the blank.\n• Z = Undo  Y = Redo  H = Hint\n\n"
            "🔧 FEATURES\n• Undo / Redo moves at any time.\n"
            "• Hint: shows the next optimal A* move.\n"
            "• Auto-Solve: A* solves it with smooth animation.\n"
            "• Move History: full log — double-click to jump back!\n"
            "• Custom Goal: set your own target arrangement.\n"
            "• Leaderboard: top 50 scores saved locally.\n"
            "• 4 beautiful themes + confetti on win!\n\n"
            "💡 TIPS\nLinear Conflict is the strongest heuristic.\n"
            "Correct-position tiles glow green!")

    def show_leaderboard(self):
        lb = self.scores.get("leaderboard",[])
        win = tk.Toplevel(self.root)
        win.title("🏆 Leaderboard")
        win.configure(bg=self.theme["bg"])
        win.resizable(False,False)
        win.grab_set()
        tk.Label(win,text="🏆  TOP SCORES",font=("Segoe UI",14,"bold"),
                 bg=self.theme["bg"],fg=self.theme["accent"]).pack(pady=(14,6))
        frame = tk.Frame(win,bg=self.theme["panel"],
                         highlightbackground=self.theme["hud_border"],highlightthickness=1)
        frame.pack(padx=20,pady=6)
        headers=["#","Name","Diff","Moves","Time","Heuristic"]
        widths= [3,   10,   8,    6,      7,     14]
        for col,(h,w) in enumerate(zip(headers,widths)):
            tk.Label(frame,text=h,font=("Consolas",10,"bold"),
                     bg=self.theme["hud_border"],fg=self.theme["tile_text"],
                     width=w,anchor="center").grid(row=0,column=col,padx=1,pady=1,sticky="we")
        if not lb:
            tk.Label(frame,text="No scores yet — play a game!",
                     font=("Segoe UI",10),bg=self.theme["panel"],fg=self.theme["text"]
                     ).grid(row=1,column=0,columnspan=6,pady=10)
        else:
            for rank,entry in enumerate(lb[:10],1):
                rbg = self.theme["tile"] if rank==1 else self.theme["panel"]
                rfg = self.theme["tile_text"] if rank==1 else self.theme["text"]
                vals=[str(rank),entry.get("name","?"),entry.get("difficulty","?"),
                      str(entry.get("moves","?")),f"{entry.get('time',0):.2f}s",
                      entry.get("heuristic","?")]
                for col,(v,w) in enumerate(zip(vals,widths)):
                    tk.Label(frame,text=v,font=("Consolas",10),bg=rbg,fg=rfg,
                             width=w,anchor="center").grid(row=rank,column=col,padx=1,pady=1,sticky="we")
        bf = tk.Frame(win,bg=self.theme["bg"]); bf.pack(pady=8)
        tk.Button(bf,text="Clear All",font=("Segoe UI",9),bg=self.theme["accent"],fg="#fff",
                  relief="flat",command=lambda:self._clear_lb(win)).grid(row=0,column=0,padx=6)
        tk.Button(bf,text="Close",font=("Segoe UI",10),relief="flat",
                  bg=self.theme["tile"],fg=self.theme["tile_text"],
                  command=win.destroy).grid(row=0,column=1,padx=6)

    def _clear_lb(self, win):
        if messagebox.askyesno("Clear?","Clear all leaderboard scores?",parent=win):
            self.scores["leaderboard"]=[]
            self.scores["best"]={"Easy":None,"Medium":None,"Hard":None}
            save_scores(self.scores); win.destroy(); self.show_leaderboard()

    def start_game(self):
        self.player_name = self.name_var.get().strip() or "Player"
        for attr in ("_title_anim_id","_preview_anim_id"):
            if hasattr(self, attr):
                try: self.root.after_cancel(getattr(self, attr))
                except: pass
        self.start_frame.destroy()
        self.build_game_ui()
        self.apply_theme_game()
        self.new_game()

    # ========== GAME UI ==========
    def build_game_ui(self):
        t = self.theme
        self.root.configure(bg=t["bg"])

        self.hud = tk.Frame(self.root,bg=t["hud_bg"],
                            highlightbackground=t["hud_border"],highlightthickness=1)
        self.hud.grid(row=0,column=0,columnspan=3,sticky="we",padx=8,pady=(8,0))
        self.lbl_title = tk.Label(self.hud,text="8‑Puzzle",font=("Segoe UI",13,"bold"),
                                  bg=t["hud_bg"],fg=t["tile"])
        self.lbl_title.pack(side="left",padx=10)
        self.lbl_stats = tk.Label(self.hud,text="⏱ 0.00s   🎯 0 moves",
                                  font=("Segoe UI",10),bg=t["hud_bg"],fg=t["text"])
        self.lbl_stats.pack(side="left",padx=10)
        self.lbl_best = tk.Label(self.hud,text="🏆 Best: —",
                                 font=("Segoe UI",10),bg=t["hud_bg"],fg=t["accent2"])
        self.lbl_best.pack(side="left",padx=10)
        self.lbl_player = tk.Label(self.hud,text=f"👤 {self.player_name}",
                                   font=("Segoe UI",10),bg=t["hud_bg"],fg=t["text"])
        self.lbl_player.pack(side="left",padx=10)
        tk.Button(self.hud,text="⬡ Theme",font=("Segoe UI",9),bg=t["panel"],fg=t["text"],
                  relief="flat",command=self.cycle_theme_game).pack(side="right",padx=6,pady=4)
        tk.Button(self.hud,text="← Menu",font=("Segoe UI",9),bg=t["accent"],fg="#fff",
                  relief="flat",command=self.return_to_menu).pack(side="right",padx=6,pady=4)

        self.canvas_size = 390
        self.canvas = tk.Canvas(self.root,width=self.canvas_size,height=self.canvas_size,
                                bg=t["bg"],highlightthickness=0)
        self.canvas.grid(row=1,column=0,padx=12,pady=10)
        self.canvas.bind("<Button-1>",self.on_click)
        self.canvas.bind("<ButtonRelease-1>",self.on_release)
        self.canvas.bind("<Motion>",self.on_hover)
        self.canvas.bind("<Leave>",lambda e: self._clear_hover())

        # Progress bar
        pf = tk.Frame(self.root,bg=t["bg"])
        pf.grid(row=2,column=0,sticky="we",padx=12)
        tk.Label(pf,text="Progress:",bg=t["bg"],fg=t["text"],font=("Segoe UI",8)).pack(side="left")
        self.prog_canvas = tk.Canvas(pf,width=285,height=14,bg=t["progress_bg"],
                                     highlightthickness=1,highlightbackground=t["hud_border"])
        self.prog_canvas.pack(side="left",padx=6)
        self.lbl_pct = tk.Label(pf,text="0%",bg=t["bg"],fg=t["text"],font=("Segoe UI",8))
        self.lbl_pct.pack(side="left")

        # Goal mini
        gf = tk.Frame(self.root,bg=t["bg"])
        gf.grid(row=3,column=0,padx=12,pady=(2,6))
        tk.Label(gf,text="Target:",bg=t["bg"],fg=t["text"],font=("Segoe UI",8,"bold")).pack(side="left")
        self.goal_mini = tk.Canvas(gf,width=100,height=36,bg=t["bg"],highlightthickness=0)
        self.goal_mini.pack(side="left",padx=4)
        tk.Button(gf,text="✎ Custom Goal",font=("Segoe UI",8),bg=t["goal_tile"],fg="#fff",
                  relief="flat",command=self.open_custom_goal).pack(side="left",padx=6)
        tk.Button(gf,text="↺ Reset Goal",font=("Segoe UI",8),bg=t["panel"],fg=t["text"],
                  relief="flat",command=self.reset_goal).pack(side="left")

        # Right panel
        right = tk.Frame(self.root,bg=t["bg"])
        right.grid(row=1,column=1,rowspan=3,sticky="ns",padx=6,pady=10)

        self.lbl_solver = tk.Label(right,text="Solver: —",anchor="w",
                                   font=("Segoe UI",9),bg=t["bg"],fg=t["text"])
        self.lbl_solver.pack(fill="x",pady=(0,6))

        ctrl = tk.Frame(right,bg=t["bg"]); ctrl.pack(fill="x")
        tk.Label(ctrl,text="Difficulty:",bg=t["bg"],fg=t["text"],font=("Segoe UI",9)
                 ).grid(row=0,column=0,sticky="w")
        tk.OptionMenu(ctrl,self.difficulty,"Easy","Medium","Hard",
                      command=lambda _:self.update_best_label()).grid(row=0,column=1,sticky="we")
        tk.Label(ctrl,text="Heuristic:",bg=t["bg"],fg=t["text"],font=("Segoe UI",9)
                 ).grid(row=1,column=0,sticky="w")
        self.heuristic_var = tk.StringVar(value=self.heuristic)
        tk.OptionMenu(ctrl,self.heuristic_var,"Manhattan","Misplaced","Linear Conflict"
                      ).grid(row=1,column=1,sticky="we")

        bs = dict(relief="flat",cursor="hand2",font=("Segoe UI",9))
        tk.Button(ctrl,text="🎲 New Game",bg=t["tile"],fg=t["tile_text"],
                  command=self.new_game,**bs).grid(row=2,column=0,sticky="we",pady=(6,2))
        tk.Button(ctrl,text="↺ Restart",bg=t["panel"],fg=t["text"],
                  command=self.restart_game,**bs).grid(row=2,column=1,sticky="we",pady=(6,2))
        tk.Button(ctrl,text="↩ Undo",bg=t["panel"],fg=t["text"],
                  command=self.undo_move,**bs).grid(row=3,column=0,sticky="we",pady=2)
        tk.Button(ctrl,text="↪ Redo",bg=t["panel"],fg=t["text"],
                  command=self.redo_move,**bs).grid(row=3,column=1,sticky="we",pady=2)
        tk.Button(ctrl,text="💡 Hint",bg=t["accent2"],fg="#fff",
                  command=self.show_hint,**bs).grid(row=4,column=0,sticky="we",pady=2)
        tk.Button(ctrl,text="🤖 Auto-Solve",bg=t["accent"],fg="#fff",
                  command=self.auto_solve,**bs).grid(row=4,column=1,sticky="we",pady=2)
        tk.Label(ctrl,text="Anim speed:",bg=t["bg"],fg=t["text"],
                 font=("Segoe UI",8)).grid(row=5,column=0,sticky="w",pady=(4,0))
        self.speed_scale = tk.Scale(ctrl,from_=30,to=600,orient="horizontal",
                                    bg=t["bg"],fg=t["text"],highlightthickness=0,
                                    troughcolor=t["progress_bg"])
        self.speed_scale.set(150)
        self.speed_scale.grid(row=5,column=1,sticky="we")
        self.sound_var = tk.BooleanVar(value=self.sound.enabled)
        tk.Checkbutton(ctrl,text="🔊 Sound",variable=self.sound_var,bg=t["bg"],fg=t["text"],
                       selectcolor=t["bg"],font=("Segoe UI",9),
                       command=lambda:setattr(self.sound,"enabled",self.sound_var.get())
                       ).grid(row=6,column=0,columnspan=2,pady=4)

        # Move History
        tk.Label(right,text="📋 Move History",bg=t["bg"],fg=t["text"],
                 font=("Segoe UI",9,"bold")).pack(pady=(8,2))
        hist_f = tk.Frame(right,bg=t["history_bg"],
                          highlightbackground=t["hud_border"],highlightthickness=1)
        hist_f.pack(fill="both",expand=True)
        sb = tk.Scrollbar(hist_f); sb.pack(side="right",fill="y")
        self.history_list = tk.Listbox(hist_f,font=("Consolas",9),
                                       bg=t["history_bg"],fg=t["history_text"],
                                       selectbackground=t["tile"],selectforeground=t["tile_text"],
                                       yscrollcommand=sb.set,height=12,width=22,
                                       relief="flat",bd=0,highlightthickness=0)
        self.history_list.pack(side="left",fill="both",expand=True)
        sb.config(command=self.history_list.yview)
        self.history_list.bind("<Double-Button-1>",self.jump_to_history)
        tk.Label(right,text="Double-click to jump to move",bg=t["bg"],fg=t["history_text"],
                 font=("Segoe UI",7)).pack()

        tk.Button(right,text="📊 Session Stats",bg=t["panel"],fg=t["text"],
                  font=("Segoe UI",9),relief="flat",
                  command=self.show_session_stats).pack(fill="x",pady=(6,2))
        tk.Button(right,text="🏆 Leaderboard",bg=t["accent2"],fg="#fff",
                  font=("Segoe UI",9),relief="flat",
                  command=self.show_leaderboard).pack(fill="x",pady=2)

        self.root.bind("<Up>",    lambda e: self.try_move_by_direction(-1,0))
        self.root.bind("<Down>",  lambda e: self.try_move_by_direction(1,0))
        self.root.bind("<Left>",  lambda e: self.try_move_by_direction(0,-1))
        self.root.bind("<Right>", lambda e: self.try_move_by_direction(0,1))
        self.root.bind("<z>",     lambda e: self.undo_move())
        self.root.bind("<y>",     lambda e: self.redo_move())
        self.root.bind("<h>",     lambda e: self.show_hint())

    def apply_theme_game(self):
        t = self.theme
        self.root.configure(bg=t["bg"])
        if hasattr(self,"canvas"): self.canvas.configure(bg=t["bg"])
        if hasattr(self,"hud"):
            self.hud.configure(bg=t["hud_bg"],highlightbackground=t["hud_border"])

    def cycle_theme_game(self):
        names = list(THEMES.keys())
        idx = names.index(self.theme_name)
        self.theme_name = names[(idx+1)%len(names)]
        self.theme = THEMES[self.theme_name]
        board_b = self.board[:]
        moves_b = self.moves
        hist_b = list(self.move_history)
        undo_b = list(self.undo_stack)
        playing_b = self.playing
        start_b = self.start_time
        init_b = self.initial_board[:]
        for w in self.root.grid_slaves(): w.destroy()
        if self._stats_timer:
            try: self.root.after_cancel(self._stats_timer)
            except: pass
        self.build_game_ui()
        self.apply_theme_game()
        self.board = board_b
        self.moves = moves_b
        self.move_history = hist_b
        self.undo_stack = undo_b
        self.playing = playing_b
        self.start_time = start_b
        self.initial_board = init_b
        self.draw_board(self.board)
        self._start_stats_timer()
        self.update_stats_display()
        self.refresh_history_list()
        self.draw_goal_mini()
        self.update_progress()

    def return_to_menu(self):
        self._stop_particles()
        self.animating = False
        if self._stats_timer:
            try: self.root.after_cancel(self._stats_timer)
            except: pass
        for w in self.root.grid_slaves(): w.destroy()
        for w in self.root.pack_slaves(): w.destroy()
        self.build_start_screen()

    # ========== LIFECYCLE ==========
    def new_game(self):
        diff = self.difficulty.get()
        moves = self.diff_moves[diff]
        self.board = random_solvable_board(moves=moves, start=self.goal)
        while self.board == self.goal:
            self.board = random_solvable_board(moves=moves, start=self.goal)
        self.initial_board = self.board[:]
        self.moves = 0
        self.move_history = []
        self.undo_stack = []
        self.redo_stack = []
        self.playing = True
        self.start_time = time.perf_counter()
        self.animating = False
        self.solution = []
        self.total_games += 1
        self.draw_board(self.board)
        self._start_stats_timer()
        self.update_stats_display()
        self.update_best_label()
        self.refresh_history_list()
        self.draw_goal_mini()
        self.update_progress()
        self.lbl_solver.configure(text="Solver: —")
        self.sound.play_shuffle()

    def restart_game(self):
        self.board = self.initial_board[:]
        self.moves = 0
        self.move_history = []
        self.undo_stack = []
        self.redo_stack = []
        self.playing = True
        self.start_time = time.perf_counter()
        self.animating = False
        self.solution = []
        self.draw_board(self.board)
        self._start_stats_timer()
        self.update_stats_display()
        self.refresh_history_list()
        self.update_progress()
        self.lbl_solver.configure(text="Solver: —")

    def finish_game_if_goal(self):
        if self.board == self.goal and self.playing:
            self.playing = False
            elapsed = time.perf_counter() - self.start_time if self.start_time else 0.0
            self.total_wins += 1
            self.win_streak += 1
            self._launch_confetti()
            self.update_best_score(self.moves, elapsed)
            self.update_best_label()
            self._add_to_leaderboard(self.moves, elapsed)
            self.update_progress()
            self.sound.play_win()
            self.root.after(500, lambda: messagebox.showinfo(
                "🎉 Victory!",
                f"Congratulations, {self.player_name}!\n\n"
                f"Difficulty:  {self.difficulty.get()}\n"
                f"Moves:       {self.moves}\n"
                f"Time:        {elapsed:.2f}s\n"
                f"Streak:      {self.win_streak} 🔥\n\n"
                "Score saved to leaderboard!"))

    def update_best_score(self, moves, time_s):
        diff = self.difficulty.get()
        best = self.scores["best"].get(diff)
        if best is None or moves < best["moves"] or (moves==best["moves"] and time_s<best["time"]):
            self.scores["best"][diff] = {"moves":moves,"time":time_s}
            save_scores(self.scores)

    def _add_to_leaderboard(self, moves, elapsed):
        entry = {"name":self.player_name,"difficulty":self.difficulty.get(),
                 "moves":moves,"time":elapsed,"heuristic":self.heuristic_var.get()}
        lb = self.scores.setdefault("leaderboard",[])
        lb.append(entry)
        lb.sort(key=lambda x:(x["moves"],x["time"]))
        self.scores["leaderboard"] = lb[:50]
        save_scores(self.scores)

    def update_best_label(self):
        diff = self.difficulty.get()
        best = self.scores["best"].get(diff)
        txt = "🏆 Best: " + (f"{best['moves']}m {best['time']:.1f}s" if best else "—")
        self.lbl_best.configure(text=txt)

    def show_session_stats(self):
        messagebox.showinfo("📊 Session Stats",
            f"Player:    {self.player_name}\n"
            f"Games:     {self.total_games}\n"
            f"Wins:      {self.total_wins}\n"
            f"Streak:    {self.win_streak} 🔥\n"
            f"Win Rate:  {100*self.total_wins//max(1,self.total_games)}%")

    # ========== CUSTOM GOAL ==========
    def open_custom_goal(self):
        win = tk.Toplevel(self.root)
        win.title("✎ Custom Goal")
        win.configure(bg=self.theme["bg"])
        win.resizable(False, False)
        win.grab_set()

        tk.Label(win, text="Enter 9 space-separated numbers (0–8, 0=empty)\ne.g.  1 2 3 4 5 6 7 8 0",
                 bg=self.theme["bg"], fg=self.theme["text"], font=("Segoe UI",10)).pack(pady=12, padx=14)

        canv = tk.Canvas(win, width=240, height=240, bg=self.theme["bg"], highlightthickness=0)
        canv.pack(padx=20, pady=6)

        def draw_c(board):
            canv.delete("all")
            t = self.theme; cell=70; pad=15
            for i,tile in enumerate(board):
                r,c = divmod(i,3)
                x0,y0 = pad+c*cell, pad+r*cell
                x1,y1 = x0+cell-4, y0+cell-4
                fill = t["goal_tile"] if tile!=0 else t["empty"]
                border = t["goal_border"] if tile!=0 else t["grid"]
                canv.create_rectangle(x0,y0,x1,y1,fill=fill,outline=border,width=2)
                if tile!=0:
                    canv.create_text((x0+x1)//2,(y0+y1)//2,text=str(tile),
                                     fill="#fff",font=("Segoe UI",18,"bold"))
        draw_c(self.goal)

        entry_var = tk.StringVar(value=" ".join(map(str,self.goal)))
        tk.Entry(win,textvariable=entry_var,width=28,font=("Segoe UI",11),justify="center").pack(padx=12,pady=6)

        def preview():
            try:
                nums = list(map(int, entry_var.get().split()))
                if sorted(nums)!=list(range(9)): raise ValueError
                draw_c(nums); return nums
            except:
                messagebox.showerror("Invalid","Enter exactly 0–8 each once.",parent=win)
                return None

        def confirm():
            nums = preview()
            if nums is None: return
            self.goal = nums
            self.draw_goal_mini()
            self.update_progress()
            win.destroy()
            messagebox.showinfo("Goal Set",f"Custom goal set!\nStart a new game to apply it.")

        bf = tk.Frame(win,bg=self.theme["bg"]); bf.pack(pady=10)
        tk.Button(bf,text="👁 Preview",font=("Segoe UI",9),relief="flat",
                  bg=self.theme["panel"],fg=self.theme["text"],command=preview).grid(row=0,column=0,padx=6)
        tk.Button(bf,text="✔ Set Goal",font=("Segoe UI",9),relief="flat",
                  bg=self.theme["goal_tile"],fg="#fff",command=confirm).grid(row=0,column=1,padx=6)
        tk.Button(bf,text="Cancel",font=("Segoe UI",9),relief="flat",
                  bg=self.theme["accent"],fg="#fff",command=win.destroy).grid(row=0,column=2,padx=6)

    def reset_goal(self):
        self.goal = [1,2,3,4,5,6,7,8,0]
        self.draw_goal_mini()
        self.update_progress()

    def draw_goal_mini(self):
        if not hasattr(self,"goal_mini"): return
        self.goal_mini.delete("all")
        t = self.theme; cell=11
        for i,tile in enumerate(self.goal):
            r,c = divmod(i,3)
            x0,y0 = c*cell+1, r*cell+1
            x1,y1 = x0+cell-2, y0+cell-2
            fill = t["goal_tile"] if tile!=0 else t["empty"]
            self.goal_mini.create_rectangle(x0,y0,x1,y1,fill=fill,outline="")
            if tile!=0:
                self.goal_mini.create_text((x0+x1)//2,(y0+y1)//2,text=str(tile),
                                           fill="#fff",font=("Segoe UI",6,"bold"))

    # ========== PROGRESS ==========
    def update_progress(self):
        if not hasattr(self,"prog_canvas"): return
        total = sum(abs(divmod(self.goal.index(tile),3)[0]-divmod(i,3)[0]) +
                    abs(divmod(self.goal.index(tile),3)[1]-divmod(i,3)[1])
                    for i,tile in enumerate(self.initial_board) if tile!=0)
        current = sum(abs(divmod(self.goal.index(tile),3)[0]-divmod(i,3)[0]) +
                      abs(divmod(self.goal.index(tile),3)[1]-divmod(i,3)[1])
                      for i,tile in enumerate(self.board) if tile!=0)
        pct = 100 if total==0 else max(0,min(100,int(100*(1-current/total))))
        w = 285
        self.prog_canvas.delete("all")
        t = self.theme
        self.prog_canvas.configure(bg=t["progress_bg"])
        if pct > 0:
            fw = int(w*pct/100)
            self.prog_canvas.create_rectangle(0,0,fw,14,fill=t["progress_fill"],outline="")
            # shine strip (lighter tone of fill color)
            self.prog_canvas.create_rectangle(0,0,fw,5,fill=t["tile_hover"],outline="")
        self.lbl_pct.configure(text=f"{pct}%")

    # ========== STATS TIMER ==========
    def _start_stats_timer(self):
        if self._stats_timer:
            try: self.root.after_cancel(self._stats_timer)
            except: pass
        self._tick_stats()

    def _tick_stats(self):
        self.update_stats_display()
        self._stats_timer = self.root.after(250, self._tick_stats)

    def update_stats_display(self):
        if not hasattr(self,"lbl_stats"): return
        secs = (time.perf_counter()-self.start_time) if self.start_time else 0.0
        self.lbl_stats.configure(text=f"⏱ {secs:.2f}s   🎯 {self.moves} moves")

    # ========== HISTORY ==========
    def _log_move(self, tile, board_before):
        self.move_history.append({"num":self.moves,"tile":tile,"board":board_before[:]})
        self.refresh_history_list()

    def refresh_history_list(self):
        if not hasattr(self,"history_list"): return
        self.history_list.delete(0,tk.END)
        for e in self.move_history:
            self.history_list.insert(tk.END, f"#{e['num']:3d}  Tile {e['tile']}")
        if self.move_history:
            self.history_list.see(tk.END)

    def jump_to_history(self, event):
        if self.animating: return
        sel = self.history_list.curselection()
        if not sel: return
        idx = sel[0]
        if idx < len(self.move_history):
            e = self.move_history[idx]
            self.undo_stack.append(self.board[:])
            self.board = e["board"][:]
            self.moves = e["num"]
            self.draw_board(self.board)
            self.update_progress()
            self.sound.play_undo()

    # ========== INTERACTIVITY ==========
    def on_hover(self, event):
        idx = self.pos_to_index(event.x, event.y)
        if idx != self.hover_index:
            self.hover_index = idx
            self.draw_board(self.board)

    def _clear_hover(self):
        self.hover_index = None
        if hasattr(self,"board"): self.draw_board(self.board)

    def try_move_by_direction(self, dx, dy):
        if not self.playing or self.animating: return
        empty = self.board.index(0)
        ex,ey = divmod(empty,3)
        nx,ny = ex+dx, ey+dy
        if 0<=nx<3 and 0<=ny<3:
            self._do_move(nx*3+ny)

    def on_click(self, event):
        self._click_index = self.pos_to_index(event.x, event.y)

    def on_release(self, event):
        if not self.playing or self.animating: return
        idx = self.pos_to_index(event.x, event.y)
        if idx is not None and self._click_index==idx:
            self._do_move(idx)

    def _do_move(self, idx):
        empty = self.board.index(0)
        if idx==empty: return
        ex,ey = divmod(empty,3)
        rx,ry = divmod(idx,3)
        if abs(ex-rx)+abs(ey-ry)==1:
            tile_moved = self.board[idx]
            board_before = self.board[:]
            self.push_undo()
            newb = self.board[:]
            newb[empty],newb[idx] = newb[idx],newb[empty]
            self.animate_transition(self.board, newb, duration_ms=100)
            self.board = newb
            self.moves += 1
            self.redo_stack.clear()
            self.draw_board(self.board)
            self.update_progress()
            self._log_move(tile_moved, board_before)
            self.finish_game_if_goal()
            self.sound.play_move()
        else:
            self.sound.play_error()

    def pos_to_index(self, x, y):
        cell = self.canvas_size//3
        c,r = x//cell, y//cell
        if 0<=r<3 and 0<=c<3:
            return r*3+c
        return None

    def push_undo(self):
        self.undo_stack.append(self.board[:])

    def undo_move(self):
        if not self.undo_stack or self.animating: return
        self.redo_stack.append(self.board[:])
        self.board = self.undo_stack.pop()
        self.moves = max(0, self.moves-1)
        if self.move_history: self.move_history.pop()
        self.draw_board(self.board)
        self.update_progress()
        self.refresh_history_list()
        self.sound.play_undo()

    def redo_move(self):
        if not self.redo_stack or self.animating: return
        self.undo_stack.append(self.board[:])
        self.board = self.redo_stack.pop()
        self.moves += 1
        self.draw_board(self.board)
        self.update_progress()
        self.sound.play_move()

    # ========== HINT / SOLVE ==========
    def show_hint(self):
        if self.animating: return
        if not is_solvable(self.board, self.goal):
            messagebox.showwarning("Unsolvable","Board not solvable with current goal."); return
        h = self.heuristic_var.get()
        t0 = time.perf_counter()
        path, explored = solve_puzzle(self.board, self.goal, heuristic=h)
        t1 = time.perf_counter()
        if not path or len(path)<2:
            self.lbl_solver.configure(text="Solver: Already at goal!"); return
        self.lbl_solver.configure(text=f"💡 Hint ({t1-t0:.2f}s, {explored} nodes)")
        self.highlight_transition(self.board, path[1], duration_ms=220)
        self.sound.play_hint()

    def auto_solve(self):
        if self.animating or self._solving: return
        if not is_solvable(self.board, self.goal):
            messagebox.showwarning("Unsolvable","Board not solvable."); return
        h = self.heuristic_var.get()
        self.heuristic = h
        self.lbl_solver.configure(text=f"🤖 A* ({h}) solving...")
        self.root.update_idletasks()
        self._solving = True
        def run():
            t0 = time.perf_counter()
            path, explored = solve_puzzle(self.board, self.goal, heuristic=h)
            t1 = time.perf_counter()
            self.root.after(0, lambda: self._on_solve_done(path, explored, t1-t0))
        threading.Thread(target=run, daemon=True).start()

    def _on_solve_done(self, path, explored, elapsed):
        self._solving = False
        self.solve_time = elapsed
        self.explored_count = explored
        if not path:
            self.lbl_solver.configure(text="❌ No solution found."); return
        self.solution = path
        self.anim_index = 0
        self.animating = True
        self.playing = False
        self.animate_solution()

    def animate_solution(self):
        if not self.animating or not self.solution: return
        idx = self.anim_index
        if idx >= len(self.solution)-1:
            self.animating = False
            self.lbl_solver.configure(
                text=f"✅ Solved: {len(self.solution)-1} steps ({self.solve_time:.2f}s, {self.explored_count} nodes)")
            self.board = self.solution[-1]
            self.draw_board(self.board)
            self.update_progress()
            return
        speed = self.speed_scale.get()
        self.animate_transition(self.solution[idx], self.solution[idx+1], duration_ms=speed)
        self.board = self.solution[idx+1]
        self.anim_index += 1
        self.root.after(speed, self.animate_solution)

    # ========== DRAWING ==========
    def draw_board(self, board):
        t = self.theme
        self.canvas.delete("all")
        size = self.canvas_size
        cell = size//3

        self.canvas.create_rectangle(0,0,size,size,fill=t["empty"],outline="")

        for i,tile in enumerate(board):
            r,c = divmod(i,3)
            x0,y0 = c*cell+3, r*cell+3
            x1,y1 = x0+cell-6, y0+cell-6
            cx,cy = (x0+x1)//2, (y0+y1)//2

            if tile==0:
                self.canvas.create_rectangle(x0,y0,x1,y1,fill=t["empty"],
                                             outline=t["grid"],width=1,dash=(4,4))
            else:
                is_hover = (i==self.hover_index)
                in_place = (i<len(self.goal) and board[i]==self.goal[i])
                if in_place:
                    fill = t["accent2"]
                    border = t["goal_border"]
                elif is_hover:
                    fill = t["tile_hover"]
                    border = t["tile_border"]
                else:
                    fill = t["tile"]
                    border = t["tile_border"]

                # Shadow
                self.canvas.create_rectangle(x0+4,y0+4,x1+4,y1+4,
                                             fill=t["shadow"],outline="")
                # Tile
                self.canvas.create_rectangle(x0,y0,x1,y1,fill=fill,outline=border,width=2)
                # Shine
                self.canvas.create_rectangle(x0+4,y0+4,x0+20,y0+10,
                                             fill="#7eb8f7" if not in_place else "#66d9a0",outline="")
                # Number
                self.canvas.create_text(cx,cy,text=str(tile),
                                        fill=t["tile_text"],font=("Segoe UI",22,"bold"))

        for k in range(4):
            self.canvas.create_line(k*cell,0,k*cell,size,fill=t["grid"],width=2)
            self.canvas.create_line(0,k*cell,size,k*cell,fill=t["grid"],width=2)

        for p in self.particles:
            p.draw(self.canvas)

    def animate_transition(self, a, b, duration_ms=110):
        size = self.canvas_size; cell = size//3
        diffs = [i for i in range(9) if a[i]!=b[i]]
        if len(diffs)!=2: self.draw_board(b); return
        mai = next(i for i in diffs if a[i]!=0)
        mv = a[mai]
        sr,sc = divmod(mai,3)
        er,ec = divmod(b.index(mv),3)
        self.draw_board(a)
        x0,y0 = sc*cell+3, sr*cell+3
        x1,y1 = x0+cell-6, y0+cell-6
        self.canvas.create_rectangle(x0,y0,x1,y1,fill=self.theme["empty"],
                                     outline=self.theme["grid"],width=1,dash=(4,4))
        shd = self.canvas.create_rectangle(x0+4,y0+4,x1+4,y1+4,fill=self.theme["shadow"],outline="")
        rect = self.canvas.create_rectangle(x0,y0,x1,y1,fill=self.theme["tile"],
                                            outline=self.theme["tile_border"],width=2)
        shine = self.canvas.create_rectangle(x0+4,y0+4,x0+20,y0+10,fill=self.theme["tile_hover"],outline="")
        txt = self.canvas.create_text((x0+x1)//2,(y0+y1)//2,text=str(mv),
                                      fill=self.theme["tile_text"],font=("Segoe UI",22,"bold"))
        steps = max(6, duration_ms//16)
        exx,eyy = ec*cell+3, er*cell+3
        dx,dy = (exx-x0)/steps, (eyy-y0)/steps
        def step(k=0):
            if k>=steps: self.draw_board(b); return
            for item in (shd,rect,shine,txt): self.canvas.move(item,dx,dy)
            self.root.after(max(8,duration_ms//steps), lambda:step(k+1))
        step()

    def highlight_transition(self, a, b, duration_ms=220):
        size = self.canvas_size; cell = size//3
        diffs = [i for i in range(9) if a[i]!=b[i]]
        if len(diffs)!=2: self.draw_board(b); return
        mai = next(i for i in diffs if a[i]!=0)
        mv = a[mai]
        sr,sc = divmod(mai,3)
        er,ec = divmod(b.index(mv),3)
        self.draw_board(a)
        x0,y0 = sc*cell+3, sr*cell+3
        x1,y1 = x0+cell-6, y0+cell-6
        rect = self.canvas.create_rectangle(x0,y0,x1,y1,fill=self.theme["accent"],
                                            outline=self.theme["tile_border"],width=2)
        txt = self.canvas.create_text((x0+x1)//2,(y0+y1)//2,text=str(mv),
                                      fill=self.theme["tile_text"],font=("Segoe UI",22,"bold"))
        steps = max(6, duration_ms//16)
        exx,eyy = ec*cell+3, er*cell+3
        dx,dy = (exx-x0)/steps, (eyy-y0)/steps
        def step(k=0):
            if k>=steps: self.draw_board(b); return
            self.canvas.move(rect,dx,dy); self.canvas.move(txt,dx,dy)
            self.root.after(max(8,duration_ms//steps), lambda:step(k+1))
        step()

    # ========== PARTICLES ==========
    def _launch_confetti(self):
        self.particles = []
        t = self.theme
        colors = [t["tile"],t["accent"],t["accent2"],t["particle"],"#ffffff",t["goal_tile"]]
        s = self.canvas_size
        for _ in range(90):
            x = random.uniform(s*0.1, s*0.9)
            y = random.uniform(s*0.05, s*0.55)
            self.particles.append(Particle(x,y,random.choice(colors)))
        self.particle_running = True
        self._run_particles()

    def _run_particles(self):
        if not self.particle_running: return
        self.particles = [p for p in self.particles if p.update(0.05)]
        if self.particles:
            self.draw_board(self.board)
            self.root.after(50, self._run_particles)
        else:
            self.particle_running = False
            self.draw_board(self.board)

    def _stop_particles(self):
        self.particle_running = False
        self.particles = []

def main():
    root = tk.Tk()
    root.title("8-Puzzle Challenge")
    app = EightPuzzleGame(root)
    root.mainloop()

if __name__ == "__main__":
    main()
