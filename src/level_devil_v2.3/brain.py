"""Cérebro do agente: Q-learning com replay reverso e bônus de exploração.

Não depende de tela nem de teclado, então pode ser testado sozinho (sim_test.py).
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import random
from collections import deque
from dataclasses import dataclass
from pathlib import Path

ACTIONS = ("left", "right", "jump", "right+jump", "left+jump", "wait")
KEYS = {
    "left": ("a",), "right": ("d",), "jump": ("w",),
    "right+jump": ("d", "w"), "left+jump": ("a", "w"), "wait": (),
}
PRIOR = (-0.05, 0.08, 0.0, 0.06, -0.05, -0.03)  # leve viés para a direita
EXPLORE_WEIGHTS = (2, 35, 8, 35, 4, 6)
SCHEMA = 2
HASH_BITS = 1024


@dataclass
class Step:
    state: str
    action: int
    reward: float
    next_state: str
    done: bool


class Brain:
    def __init__(self, path: Path | None = None, alpha=0.25, gamma=0.95, epsilon=0.25,
                 eps_min=0.03, eps_decay=0.97, bonus=0.10, replay_passes=4, buffer=600):
        self.path = path
        self.alpha, self.gamma = alpha, gamma
        self.epsilon, self.eps_min, self.eps_decay = epsilon, eps_min, eps_decay
        self.bonus, self.replay_passes = bonus, replay_passes
        self.q: dict[str, list[float]] = {}
        self.n: dict[str, list[int]] = {}
        self.episodes = 0
        self.wins = 0
        self.meta: dict = {}
        self.buffer: deque[Step] = deque(maxlen=buffer)
        if path is not None:
            self.load()

    # ---------- política ----------
    def _row(self, s: str) -> list[float]:
        return self.q.setdefault(s, list(PRIOR))

    def _cnt(self, s: str) -> list[int]:
        return self.n.setdefault(s, [0] * len(ACTIONS))

    def choose(self, s: str) -> int:
        q, n = self._row(s), self._cnt(s)
        if random.random() < self.epsilon:
            a = random.choices(range(len(ACTIONS)), weights=EXPLORE_WEIGHTS, k=1)[0]
        else:
            # Q + bônus de curiosidade: ações pouco testadas naquele estado ganham prioridade.
            scores = [q[i] + self.bonus / math.sqrt(n[i] + 1) for i in range(len(ACTIONS))]
            top = max(scores)
            a = random.choice([i for i, v in enumerate(scores) if v >= top - 1e-9])  # desempate aleatório
        n[a] += 1
        return a

    # ---------- aprendizado ----------
    def _td(self, st: Step) -> None:
        q = self._row(st.state)
        future = 0.0 if st.done else max(self._row(st.next_state))
        q[st.action] += self.alpha * (st.reward + self.gamma * future - q[st.action])

    def learn(self, st: Step) -> None:
        self.buffer.append(st)
        self._td(st)

    def end_episode(self, kind: str) -> None:
        """Replay reverso: propaga a morte/vitória para os passos que a causaram."""
        for _ in range(self.replay_passes):
            for st in reversed(self.buffer):
                self._td(st)
        self.buffer.clear()
        self.episodes += 1
        self.wins += kind == "win"
        self.epsilon = max(self.eps_min, self.epsilon * self.eps_decay)
        self.save()

    # ---------- persistência ----------
    def load(self) -> bool:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if data.get("schema") != SCHEMA:
                return False
            self.q, self.n = data["q"], data["n"]
            self.epsilon = float(data.get("epsilon", self.epsilon))
            self.episodes, self.wins = int(data.get("episodes", 0)), int(data.get("wins", 0))
            self.meta = data.get("meta", {})
            return True
        except (OSError, ValueError, KeyError, TypeError):
            return False

    def save(self) -> None:
        if self.path is None:
            return
        data = {"schema": SCHEMA, "epsilon": self.epsilon, "episodes": self.episodes,
                "wins": self.wins, "meta": self.meta, "q": self.q, "n": self.n}
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, self.path)  # gravação atômica: nunca deixa a tabela pela metade


def pick_profile(folder: Path, level_hash: int, tolerance=0.05, name: str | None = None) -> tuple[Path, str]:
    """Um arquivo de aprendizado por fase, reconhecido pela aparência do 1º quadro."""
    folder.mkdir(exist_ok=True)
    if name:
        return folder / f"{name}.json", f"manual '{name}'"
    best = None
    for p in folder.glob("*.json"):
        try:
            h = int(json.loads(p.read_text(encoding="utf-8"))["meta"]["hash"], 16)
        except (OSError, ValueError, KeyError, TypeError):
            continue
        d = bin(h ^ level_hash).count("1")
        if d <= tolerance * HASH_BITS and (best is None or d < best[0]):
            best = (d, p)
    if best:
        return best[1], f"fase conhecida (distância {best[0]})"
    digest = hashlib.sha1(f"{level_hash:x}".encode()).hexdigest()[:8]   # bits iniciais são iguais em toda fase
    return folder / f"nivel_{digest}.json", "fase nova"
