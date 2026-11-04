"""Agente visual de Q-learning para Level Devil (v2.1).

Detecta personagem, porta e tela de morte por cor; troca de fase sozinho (um perfil de
aprendizado por fase, reconhecido pela forma do cenário).
"""
from __future__ import annotations

import ctypes
import logging
import math
import os
import sys
import time
from collections import deque
from dataclasses import dataclass
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Callable

import cv2
import numpy as np

from brain import ACTIONS, KEYS, Brain, Step, pick_profile
from vision import death_screen, find_door, find_player, level_hash, solid_color, solid_mask

HERE = Path(__file__).resolve().parent
LOG_PATH = HERE / "agent.log"
PROFILES = HERE / "profiles"
log = logging.getLogger("level_devil")
SWAP = {"a": "d", "d": "a"}


class Cancelled(Exception):
    """Usuário apertou ESC."""


@dataclass
class Config:
    action_seconds: float = 0.12
    xbin_mult: float = 1.6            # largura da faixa do estado = 1.6 x largura do personagem
    teleport_frac: float = 0.12       # salto maior que isso (fração da largura) = respawn/falso positivo
    start_frac: float = 0.07          # "perto do início"
    near_frac: float = 0.10           # "perto da porta"
    lost_frames: int = 3
    respawn_wait: float = 0.7
    stuck_seconds: float = 8.0
    wake_key: str = "space"           # tecla para sair da tela "PRESS ANY KEY"
    restart_key: str | None = None
    save_every: int = 100
    step_cost: float = 0.01
    frontier_gain: float = 3.0
    death_reward: float = -1.0
    win_reward: float = 2.0
    stuck_reward: float = -0.3
    level_change_bits: int = 40       # distância de hash que indica "outra fase"
    new_level_tries: int = 40         # espera máxima pela fase nova após vencer


def probe_rects(x: int, y: int, pw: int, ph: int, d: int) -> dict[str, tuple[int, int, int, int]]:
    """Sensores (x0, y0, x1, y1). `d` = +1 se o objetivo está à direita, -1 à esquerda."""
    bottom = y + ph // 2

    def ahead(a: int, b: int) -> tuple[int, int]:
        p, q = x + d * a, x + d * b
        return min(p, q), max(p, q)

    fx = ahead(pw // 2 + 3, pw // 2 + 3 + 2 * pw)
    wx = ahead(pw // 2 + 2, pw // 2 + 2 + 2 * pw)
    return {
        "ground": (x - pw // 2, bottom + 2, x + pw // 2, bottom + 5),   # sob os pés
        "floor": (fx[0], bottom + 2, fx[1], bottom + 5),                # chão logo à frente
        "wall": (wx[0], y - ph // 2 + 3, wx[1], bottom - 3),           # obstáculo à frente
    }


def solid_fraction(mask: np.ndarray, rect) -> float:
    x0, y0, x1, y1 = rect
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(mask.shape[1], x1), min(mask.shape[0], y1)
    if x1 <= x0 or y1 <= y0:
        return 0.0
    return float(mask[y0:y1, x0:x1].mean())


class Agent:
    def __init__(self, grab: Callable[[], np.ndarray], press: Callable[[tuple, float], None],
                 release: Callable[[], None], brain: Brain | None, cfg: Config | None = None,
                 stop: Callable[[], bool] = lambda: False, clock=time.monotonic, sleep=time.sleep,
                 brain_factory: Callable[[int], Brain] | None = None):
        self.grab, self.press, self.release = grab, press, release
        self.brain, self.cfg, self.stop = brain, cfg or Config(), stop
        self.clock, self.sleep, self.brain_factory = clock, sleep, brain_factory
        self.debug = os.environ.get("LD_DEBUG") == "1"
        self.scene = False
        self.prev_hash: int | None = None
        self.tries = 0
        self._cand = None
        self.levels_done = 0
        self.level_hash = 0

    # ---------- cena (fase) ----------
    def _init_scene(self, frame: np.ndarray) -> bool:
        """Tenta reconhecer a fase atual: personagem parado + porta visíveis."""
        p, d = find_player(frame), find_door(frame)
        if p is None or d is None or death_screen(frame):
            self._cand = None
            return False
        if self._cand is None or math.dist(self._cand, p.center) > 2:   # exige 2 quadros estáveis
            self._cand = p.center
            return False
        h = level_hash(frame)
        if self.prev_hash is not None and self.tries < self.cfg.new_level_tries:
            self.tries += 1
            if bin(h ^ self.prev_hash).count("1") <= self.cfg.level_change_bits:
                return False                                            # ainda é a fase antiga
        self.prev_hash, self._cand = None, None
        cfg, width = self.cfg, frame.shape[1]
        if self.brain_factory is not None:
            if self.brain is not None:
                self.brain.save()
            self.brain = self.brain_factory(h)
        self.level_hash = h
        self.pw, self.ph = p.w, p.h
        self.start, self.goal = p.center, d.center
        self.dir = 1 if d.center[0] >= p.center[0] else -1
        self.span = max(30, abs(d.center[0] - p.center[0]))
        self.door_wh = (d.w, d.h)
        self.solid = solid_color(frame, p)
        self.xbin, self.ybin = max(6, int(p.w * cfg.xbin_mult)), max(8, p.h)
        self.teleport = max(40, int(cfg.teleport_frac * width))
        self.start_r = max(25, int(cfg.start_frac * width))
        self.near = max(40, int(cfg.near_frac * width))
        self.scene = True
        self._reset()
        log.info("Fase reconhecida: início=%s porta=%s direção=%s | perfil: episódios=%d vitórias=%d estados=%d",
                 self.start, self.goal, "→" if self.dir > 0 else "←", self.brain.episodes, self.brain.wins,
                 len(self.brain.q))
        return True

    def _reset(self) -> None:
        self.pos = None
        self.pending: tuple[str, int] | None = None
        self.best_prog, self.best_t = 0, self.clock()
        self.lost = 0
        self.steps = 0
        self.door_dist = None
        self.motion: deque = deque(maxlen=30)
        self.waited = 0
        self.awaiting = False

    # ---------- estado ----------
    def _state(self, frame: np.ndarray, pos) -> str:
        x, y = pos
        mask = solid_mask(frame, self.solid)
        r = probe_rects(x, y, self.pw, self.ph, self.dir)
        ground = solid_fraction(mask, r["ground"]) > 0.30
        floor = solid_fraction(mask, r["floor"]) > 0.50
        wall = solid_fraction(mask, r["wall"]) > 0.20
        dy = 0 if self.pos is None else y - self.pos[1]
        vy = -1 if dy < -3 else (1 if dy > 3 else 0)       # subindo / parado / caindo
        xb = int(np.clip(self.dir * (x - self.start[0]) // self.xbin, -2, 150))
        yb = int(np.clip(round((self.start[1] - y) / self.ybin), -4, 8))
        return f"{xb}:{yb}:{vy}:{int(ground)}{int(floor)}{int(wall)}"

    def _keys(self, action: int) -> tuple:
        keys = KEYS[ACTIONS[action]]
        return tuple(SWAP.get(k, k) for k in keys) if self.dir < 0 else keys

    # ---------- episódios ----------
    def _end(self, kind: str) -> None:
        cfg, brain = self.cfg, self.brain
        reward = {"death": cfg.death_reward, "win": cfg.win_reward, "stuck": cfg.stuck_reward}[kind]
        if self.pending:
            s, a = self.pending
            brain.learn(Step(s, a, reward, s, True))
        brain.end_episode(kind)   # replay reverso + grava o perfil em disco
        log.info("Episódio %d (%s) | passos=%d | progresso=%d | ε=%.2f | estados=%d | vitórias=%d",
                 brain.episodes, kind, self.steps, self.best_prog, brain.epsilon, len(brain.q), brain.wins)
        self._reset()

    def _loss_kind(self, frame: np.ndarray | None = None) -> str:
        """Personagem sumiu/reapareceu no início: morte ou vitória? Vitória = estava perto da porta
        e o cenário mudou de verdade (hash diferente)."""
        if self.door_dist is None or self.door_dist > self.near:
            return "death"
        if frame is None:
            self.sleep(1.2)
            frame = self.grab()
        if death_screen(frame):
            return "death"
        return "win" if bin(level_hash(frame) ^ self.level_hash).count("1") > self.cfg.level_change_bits else "death"

    def _next_level(self) -> None:
        self.levels_done += 1
        log.info("Fase concluída (%d). Aguardando a próxima fase...", self.levels_done)
        self.prev_hash, self.tries, self.scene = self.level_hash, 0, False
        self.sleep(1.0)

    def _wake(self) -> None:
        """Na tela 'PRESS ANY KEY' qualquer tecla continua o jogo."""
        self.waited += 1
        if self.waited % 3 == 1:
            self.press((self.cfg.wake_key,), 0.05)
        if self.waited % 150 == 0:
            log.warning("Personagem não reaparece há um bom tempo. Se a fase mudou de aparência, reinicie.")

    # ---------- loop ----------
    def run(self) -> str:
        cfg = self.cfg
        try:
            while not self.stop():
                frame = self.grab()
                if not self.scene:
                    if not self._init_scene(frame):
                        self.sleep(0.15)
                    continue
                brain = self.brain
                if death_screen(frame):
                    if not self.awaiting:
                        self._end("death")
                        self.awaiting = True
                    self._wake()
                    self.sleep(0.1)
                    continue

                pb = find_player(frame, self.pos)
                pos = pb.center if pb else None
                ok = pos is not None
                if ok and self.pos is not None and math.dist(pos, self.pos) > self.teleport:
                    if math.dist(pos, self.start) <= self.start_r:
                        kind = self._loss_kind(frame)   # reapareceu no início: morreu ou trocou de fase
                        self._end(kind)
                        if kind == "win":
                            self._next_level()
                            continue
                    else:
                        ok = False                 # salto improvável: falso positivo
                if not ok:
                    self.release()
                    if self.awaiting:
                        self._wake()
                        self.sleep(0.1)
                        continue
                    self.lost += 1
                    if self.lost < cfg.lost_frames:
                        self.sleep(0.08)
                        continue
                    kind = self._loss_kind()
                    self._end(kind)
                    if kind == "win":
                        self._next_level()
                    else:
                        self.awaiting = True
                        self.sleep(cfg.respawn_wait)
                    continue
                self.lost, self.awaiting, self.waited = 0, False, 0
                x, y = pos

                door = find_door(frame)
                dpos = door.center if door else self.goal
                self.door_dist = math.dist(pos, dpos)
                if door and abs(x - dpos[0]) <= door.w // 2 + 2 and abs(y - dpos[1]) <= door.h // 2 + 2:
                    self._end("win")
                    self._next_level()
                    continue

                state = self._state(frame, pos)
                prog = self.dir * (x - self.start[0])
                if self.pending:
                    gain = max(0, prog - self.best_prog) / self.span * cfg.frontier_gain
                    brain.learn(Step(*self.pending, gain - cfg.step_cost, state, False))
                now = self.clock()
                if prog > self.best_prog + 2:
                    self.best_prog, self.best_t = prog, now
                elif now - self.best_t > cfg.stuck_seconds:
                    self._end("stuck")
                    if cfg.restart_key:
                        self.press((cfg.restart_key,), 0.1)
                    continue

                action = brain.choose(state)
                self.press(self._keys(action), cfg.action_seconds)
                if self.pos is not None:
                    self.motion.append(abs(x - self.pos[0]) + abs(y - self.pos[1]))
                    if len(self.motion) == 30 and sum(self.motion) < 6:
                        log.warning("Personagem parado há 30 passos: as teclas podem não estar chegando ao jogo "
                                    "(clique na janela do jogo) ou ele está preso.")
                        self.motion.clear()
                self.pending = (state, action)
                self.pos = pos
                self.steps += 1
                if self.debug:
                    self._overlay(frame, pos, dpos, state)
                if self.steps % cfg.save_every == 0:
                    brain.save()
                    log.info("passos=%d x=%d ação=%s estados=%d ε=%.2f",
                             self.steps, x, ACTIONS[action], len(brain.q), brain.epsilon)
            return "stopped"
        finally:
            self.release()
            if self.brain is not None:
                self.brain.save()

    def _overlay(self, frame, pos, door, state) -> None:
        view = frame.copy()
        for r in probe_rects(pos[0], pos[1], self.pw, self.ph, self.dir).values():
            cv2.rectangle(view, (r[0], r[1]), (r[2], r[3]), (0, 200, 0), 1)
        cv2.circle(view, pos, 3, (0, 0, 255), -1)
        cv2.circle(view, door, 3, (255, 0, 0), -1)
        cv2.putText(view, state, (8, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
        cv2.imshow("LD_DEBUG", view)
        cv2.waitKey(1)


# ----------------------------------------------------------------- GUI / Windows
def minimize_console() -> None:
    try:
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 6)
    except (AttributeError, OSError):
        pass


def stop_requested() -> bool:
    try:
        return bool(ctypes.windll.user32.GetAsyncKeyState(0x77) & 0x8000)  # F8
    except (AttributeError, OSError):
        return False


def beep() -> None:
    try:
        ctypes.windll.user32.MessageBeep(0)
    except (AttributeError, OSError):
        pass


def screen_size() -> tuple[int, int]:
    try:
        u = ctypes.windll.user32
        return u.GetSystemMetrics(0), u.GetSystemMetrics(1)
    except (AttributeError, OSError):
        return 1600, 900


def fit(image: np.ndarray, frac: float = 0.9) -> tuple[np.ndarray, float]:
    """Reduz só se não couber na tela; a janela é AUTOSIZE, então nunca estica."""
    sw, sh = screen_size()
    scale = min(1.0, sw * frac / image.shape[1], sh * frac / image.shape[0])
    if scale < 1.0:
        image = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    return image, scale


def open_window(title: str) -> None:
    cv2.namedWindow(title, cv2.WINDOW_AUTOSIZE)
    cv2.moveWindow(title, 0, 0)
    try:
        cv2.setWindowProperty(title, cv2.WND_PROP_TOPMOST, 1)
    except cv2.error:
        pass


def choose_region(sct, grab_monitor) -> dict[str, int]:
    minimize_console()
    time.sleep(0.5)
    monitor = sct.monitors[1]
    preview, scale = fit(grab_monitor(monitor))
    cv2.putText(preview, "Arraste para selecionar SO a area do jogo; ENTER confirma | ESC cancela", (18, 34),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (20, 20, 230), 2, cv2.LINE_AA)
    title = "1/2 - Area do jogo"
    open_window(title)
    x, y, w, h = cv2.selectROI(title, preview, showCrosshair=True)
    cv2.destroyWindow(title)
    if not w or not h:
        raise Cancelled()
    return {"left": monitor["left"] + int(x / scale), "top": monitor["top"] + int(y / scale),
            "width": int(w / scale), "height": int(h / scale)}


def wait_for_scene(grab) -> np.ndarray | None:
    """Sem janelas abertas (para não aparecerem na captura) até achar personagem e porta."""
    log.info("Inicie a fase no jogo. Aguardando personagem e porta (F8 cancela)...")
    while not stop_requested():
        frame = grab()
        if find_player(frame) is not None and find_door(frame) is not None and not death_screen(frame):
            return frame
        time.sleep(0.3)
    return None


def confirm_scene(frame: np.ndarray) -> None:
    view = frame.copy()
    p, d = find_player(frame), find_door(frame)
    for blob, color, name in ((p, (0, 200, 0), "personagem"), (d, (255, 0, 0), "porta")):
        cv2.rectangle(view, (blob.x, blob.y), (blob.x + blob.w, blob.y + blob.h), color, 2)
        cv2.putText(view, name, (blob.x - 10, blob.y - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2, cv2.LINE_AA)
    view, _ = fit(view)
    cv2.putText(view, "2/2 - Caixas corretas? ENTER inicia | ESC cancela", (12, 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 220), 2, cv2.LINE_AA)
    title = "2/2 - Confirmar"
    open_window(title)
    cv2.imshow(title, view)
    while True:
        key = cv2.waitKey(30) & 0xFF
        if key in (10, 13):
            break
        if key == 27:
            cv2.destroyWindow(title)
            raise Cancelled()
    cv2.destroyWindow(title)


def setup_logging() -> None:
    log.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(message)s", "%H:%M:%S")
    fh = RotatingFileHandler(LOG_PATH, maxBytes=500_000, backupCount=1, encoding="utf-8")
    fh.setFormatter(fmt)
    log.addHandler(fh)
    if sys.stdout is not None:  # com `pyw` não há console
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(fmt)
        log.addHandler(sh)


def main() -> None:
    setup_logging()
    try:
        import mss
        import pyautogui

        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.01
        MSS = getattr(mss, "MSS", None) or mss.mss  # compatível com versões diferentes do mss

        def bgr(shot) -> np.ndarray:
            return cv2.cvtColor(np.asarray(shot), cv2.COLOR_BGRA2BGR)

        with MSS() as sct:
            region = choose_region(sct, lambda m: bgr(sct.grab(m)))
            grab = lambda: bgr(sct.grab(region))  # noqa: E731
            frame = wait_for_scene(grab)
            if frame is None:
                return
            beep()
            confirm_scene(frame)

            def factory(h: int) -> Brain:
                path, why = pick_profile(PROFILES, h, name=os.environ.get("LD_PROFILE"))
                brain = Brain(path)
                brain.meta["hash"] = f"{h:x}"
                log.info("Perfil %s (%s) | episódios=%d vitórias=%d estados=%d",
                         path.name, why, brain.episodes, brain.wins, len(brain.q))
                return brain

            held: set[str] = set()

            def press(keys, seconds):
                """A/D ficam segurados entre os passos (sem soluços no ar); W e as demais teclas são pulsadas."""
                want = set(keys)
                for k in list(held):
                    if k not in want:
                        pyautogui.keyUp(k)
                        held.discard(k)
                for k in want - held:
                    pyautogui.keyDown(k)
                    held.add(k)
                time.sleep(seconds)
                for k in list(held - {"a", "d"}):
                    pyautogui.keyUp(k)
                    held.discard(k)

            def release():
                for k in ("a", "d", "w", "space"):
                    pyautogui.keyUp(k)
                held.clear()

            player = find_player(frame)
            pyautogui.click(region["left"] + player.center[0], region["top"] + player.center[1])  # dá foco ao jogo
            log.info("Iniciando em 2 s; F8 para parar.")
            time.sleep(2)
            agent = Agent(grab, press, release, None, Config(), stop=stop_requested, brain_factory=factory)
            log.info("Fim: %s | fases concluídas nesta sessão: %d", agent.run(), agent.levels_done)
    except Cancelled:
        log.info("Cancelado.")
    except Exception:
        log.exception("Erro inesperado")
    finally:
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
