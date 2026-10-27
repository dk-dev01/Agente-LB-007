"""Teste de ponta a ponta sem o jogo: mini-platformer sintético (cores do jogo real) alimenta o Agent.

Cobre: tela de morte que só continua com uma tecla, armadilhas invisíveis, troca automática de fase
(um perfil de aprendizado por fase) e persistência em disco.

Uso:  python sim_test.py
"""
from __future__ import annotations

import random
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from agent import Agent, Config
from brain import Brain, pick_profile

W, H = 640, 260
BROWN, ORANGE, GRAY, BLACK, YELLOW = (7, 107, 153), (84, 184, 254), (192, 192, 192), (0, 0, 0), (90, 233, 241)  # BGR


@dataclass
class Level:
    ground: int
    gaps: list
    wall: tuple          # x0, x1, altura
    spike: tuple         # armadilha INVISÍVEL no chão
    ceil: tuple          # zona INVISÍVEL: pular mata
    door_x: int
    start_x: int = 40


LEVELS = [
    Level(160, [(200, 262), (400, 470)], (120, 140, 18), (305, 335), (520, 575), 600),
    Level(190, [(150, 215)], (260, 285, 18), (330, 360), (0, -1), 560),
]


class FakeGame:
    def __init__(self):
        self.t = 0
        self.deaths = 0
        self.idx = 0
        self.finished = False
        self.trans = 0
        self.dead = False
        self._spawn()

    @property
    def lv(self) -> Level:
        return LEVELS[min(self.idx, len(LEVELS) - 1)]

    def _spawn(self):
        self.x, self.y = self.lv.start_x, self.lv.ground - 13
        self.vx = self.vy = 0
        self.face, self.dead = 1, False

    def _gap(self, x):
        return any(a <= x <= b for a, b in self.lv.gaps)

    def press(self, keys, seconds):
        self.t += 1
        if self.finished or self.trans:
            return
        if self.dead:
            if keys:                    # PRESS ANY KEY
                self._spawn()
            return
        L = self.lv
        if "d" in keys:
            self.vx, self.face = 14, 1
        elif "a" in keys:
            self.vx, self.face = -14, -1
        on_ground = self.y >= L.ground - 13 and not self._gap(self.x)
        if "w" in keys and on_ground:
            self.vy = -15
        if on_ground and not keys:
            self.vx = 0
        nx = int(np.clip(self.x + self.vx, 25, W - 25))
        if self.y + 13 > L.ground - L.wall[2] and self.x < L.wall[0] <= nx + 5:
            nx = L.wall[0] - 6
        self.x = nx
        self.vy += 4
        ny = self.y + self.vy
        if self.y <= L.ground - 13 and ny >= L.ground - 13 and self.vy >= 0 and not self._gap(self.x):
            self.y, self.vy = L.ground - 13, 0
            if not keys:
                self.vx = 0
        else:
            self.y = ny
        feet = self.y + 13
        if (feet > H or (L.spike[0] <= self.x <= L.spike[1] and feet >= L.ground - 6)
                or (L.ceil[0] <= self.x <= L.ceil[1] and feet < L.ground - 8)):
            self.deaths += 1
            self.dead = True
        if abs(self.x - L.door_x) <= 12 and abs(self.y - (L.ground - 13)) <= 10:
            self.idx += 1
            if self.idx >= len(LEVELS):
                self.finished = True
            else:
                self.trans = 2
                self._spawn()

    def frame(self) -> np.ndarray:
        img = np.empty((H, W, 3), np.uint8)
        img[:] = BROWN
        if self.finished or self.trans:
            self.trans = max(0, self.trans - 1)
            return img
        L = self.lv
        img[L.ground - 60:L.ground, 20:W - 20] = ORANGE
        for a, b in L.gaps:
            img[L.ground:, a:b + 1] = ORANGE
        img[L.ground - L.wall[2]:L.ground, L.wall[0]:L.wall[1]] = BROWN
        for i in range(5):                                   # HUD: quadradinhos pretos
            img[8:24, 300 + i * 20:316 + i * 20] = BLACK if i < 2 else BROWN
        dx = L.door_x                                        # porta cinza com borda
        img[L.ground - 27:L.ground, dx - 11:dx + 12] = BROWN
        img[L.ground - 25:L.ground, dx - 9:dx + 10] = GRAY
        if self.dead:
            img[78:95, 236:404] = YELLOW                     # "PRESS ANY KEY"
        else:
            img[12:36, 20:48] = YELLOW                       # ícone amarelo do HUD (não é tela de morte)
            if self.y + 13 <= H:
                img[self.y - 12:self.y + 13, self.x - 5:self.x + 5] = BLACK
        return img


def run_one(seed: int, max_steps=6000, folder: Path | None = None, **brain_kw) -> dict:
    random.seed(seed)
    np.random.seed(seed)
    folder = folder or Path(tempfile.mkdtemp())
    game = FakeGame()

    def factory(h: int) -> Brain:
        path, _ = pick_profile(folder, h)
        b = Brain(path, **brain_kw)
        b.meta["hash"] = f"{h:x}"
        return b

    agent = Agent(game.frame, game.press, lambda: None, None, Config(),
                  stop=lambda: game.finished or game.t > max_steps,
                  clock=lambda: game.t * 0.15, sleep=lambda s: None, brain_factory=factory)
    agent.run()
    return {"niveis": game.idx, "terminou": game.finished, "passos": game.t, "mortes": game.deaths,
            "perfis": sorted(p.name for p in folder.glob("*.json")), "folder": folder}


if __name__ == "__main__":
    ok = True
    for seed in range(2):
        r = run_one(seed)
        recarregado = [Brain(r["folder"] / n) for n in r["perfis"]]
        print(f"semente {seed}: fases concluídas {r['niveis']}/{len(LEVELS)} | mortes {r['mortes']} | "
              f"passos {r['passos']} | perfis salvos {len(r['perfis'])} | "
              f"episódios recarregados do disco {[b.episodes for b in recarregado]}")
        ok &= r["terminou"] and len(r["perfis"]) == len(LEVELS) and all(b.episodes > 0 for b in recarregado)
    print("OK" if ok else "FALHOU")
    sys.exit(0 if ok else 1)
