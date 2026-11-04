"""Implementação didática sem dependências externas. Estados: (linha, coluna)."""
from dataclasses import dataclass
from collections import deque
import random

DEFAULT_MAP = ("S.....", ".##.#.", "....#.", ".##...", "...##.", ".#...G")
ACTIONS = ((-1, 0), (0, 1), (1, 0), (0, -1))  # cima, direita, baixo, esquerda
ACTION_NAMES = ("cima", "direita", "baixo", "esquerda")


@dataclass(frozen=True)
class Maze:
    rows: tuple = DEFAULT_MAP
    step_reward: float = -1.0
    collision_reward: float = -3.0
    goal_reward: float = 20.0

    def __post_init__(self):
        if not self.rows or not self.rows[0] or any(len(r) != len(self.rows[0]) for r in self.rows):
            raise ValueError("O mapa deve ser retangular e não vazio.")
        if any(c not in "S.G#" for r in self.rows for c in r):
            raise ValueError("Use apenas S, G, ponto e #.")
        for symbol in "SG":
            if sum(r.count(symbol) for r in self.rows) != 1:
                raise ValueError(f"O mapa precisa de exatamente um {symbol}.")

    def position(self, symbol):
        return next((r, c) for r, row in enumerate(self.rows) for c, v in enumerate(row) if v == symbol)

    @property
    def start(self):
        return self.position("S")

    @property
    def goal(self):
        return self.position("G")

    @property
    def states(self):
        return [(r, c) for r, row in enumerate(self.rows) for c, v in enumerate(row) if v != "#"]

    def step(self, state, action):
        if state not in self.states or action not in range(4):
            raise ValueError("Estado ou ação inválidos.")
        if state == self.goal:
            return state, 0.0, True, False
        dr, dc = ACTIONS[action]
        nxt = (state[0] + dr, state[1] + dc)
        if nxt not in self.states:
            return state, self.collision_reward, False, True
        terminal = nxt == self.goal
        return nxt, self.goal_reward if terminal else self.step_reward, terminal, False

    def shortest_path_length(self):
        """BFS é referência de distância, não o agente usado no treinamento."""
        queue, seen = deque([(self.start, 0)]), {self.start}
        while queue:
            state, distance = queue.popleft()
            if state == self.goal:
                return distance
            for a in range(4):
                nxt, _, _, _ = self.step(state, a)
                if nxt not in seen:
                    seen.add(nxt)
                    queue.append((nxt, distance + 1))
        return None


@dataclass(frozen=True)
class Config:
    episodes: int = 1000
    max_steps: int = 100
    alpha: float = 0.1
    gamma: float = 0.95
    epsilon_start: float = 1.0
    epsilon_end: float = 0.05

    def __post_init__(self):
        if self.episodes < 1 or self.max_steps < 1:
            raise ValueError("Episódios e limite de passos devem ser positivos.")
        if not 0 < self.alpha <= 1 or not 0 <= self.gamma < 1:
            raise ValueError("Exige 0 < alpha <= 1 e 0 <= gamma < 1.")
        if not all(0 <= e <= 1 for e in (self.epsilon_start, self.epsilon_end)):
            raise ValueError("Epsilon deve estar entre 0 e 1.")

    def epsilon(self, episode):
        fraction = episode / max(1, self.episodes - 1)
        return self.epsilon_start + fraction * (self.epsilon_end - self.epsilon_start)


def greedy(q, state, rng):
    values = q[state]
    best = max(values)
    return rng.choice([a for a, value in enumerate(values) if value == best])


def update(q, state, action, reward, nxt, terminal, alpha, gamma):
    # A saída é terminal: não existe valor futuro após alcançá-la.
    target = reward if terminal else reward + gamma * max(q[nxt])
    q[state][action] += alpha * (target - q[state][action])


def train(maze, config, seed=0, on_transition=None):
    rng = random.Random(seed)
    q = {state: [0.0] * 4 for state in maze.states}
    history = []
    for episode in range(config.episodes):
        state = maze.start
        total, collisions, terminal = 0.0, 0, False
        eps = config.epsilon(episode)
        for step in range(1, config.max_steps + 1):
            action = rng.randrange(4) if rng.random() < eps else greedy(q, state, rng)
            nxt, reward, terminal, collision = maze.step(state, action)
            truncated = step == config.max_steps and not terminal
            # Limite de coleta não é estado terminal do MDP: mantém bootstrap.
            update(q, state, action, reward, nxt, terminal, config.alpha, config.gamma)
            if on_transition:
                on_transition({"seed": seed, "episode": episode + 1, "step": step,
                               "state": state, "action": action, "reward": reward,
                               "next_state": nxt, "terminated": terminal, "truncated": truncated})
            total += reward
            collisions += collision
            state = nxt
            if terminal:
                break
        history.append({"episode": episode + 1, "epsilon": eps, "success": terminal,
                        "steps": step, "return": total, "collisions": collisions})
    return q, history


def rollout(maze, q=None, seed=0, max_steps=100):
    """q=None: baseline aleatório. Com q: política gulosa, sem aprender."""
    if max_steps < 1:
        raise ValueError("Limite de passos deve ser positivo.")
    rng, state = random.Random(seed), maze.start
    path, total, collisions = [state], 0.0, 0
    for step in range(1, max_steps + 1):
        action = rng.randrange(4) if q is None else greedy(q, state, rng)
        state, reward, terminal, collision = maze.step(state, action)
        path.append(state)
        total += reward
        collisions += collision
        if terminal:
            break
    return {"success": terminal, "steps": step, "return": total,
            "collisions": collisions, "path": path}


def evaluate(maze, q=None, episodes=200, seed=100000, max_steps=100):
    if episodes < 1:
        raise ValueError("Quantidade de avaliações deve ser positiva.")
    runs = [rollout(maze, q, seed + i, max_steps) for i in range(episodes)]
    wins = [r for r in runs if r["success"]]
    return {"success_rate": len(wins) / episodes,
            "mean_steps_success": sum(r["steps"] for r in wins) / len(wins) if wins else None,
            "mean_return": sum(r["return"] for r in runs) / episodes,
            "mean_collisions": sum(r["collisions"] for r in runs) / episodes}
