"""Visão por cor para o Level Devil.

O jogo usa cores chapadas (personagem preto, porta cinza, fundo laranja, paredes marrons),
então segmentar por cor é mais robusto que template matching e dispensa calibração manual.
Os filtros de tamanho são proporcionais à largura da área capturada (referência: 844 px).
"""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

REF_WIDTH = 844.0
HASH_BITS = 1024


@dataclass
class Blob:
    x: int
    y: int
    w: int
    h: int
    area: int

    @property
    def center(self) -> tuple[int, int]:
        return self.x + self.w // 2, self.y + self.h // 2


def _blobs(mask: np.ndarray) -> list[Blob]:
    n, _, st, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), connectivity=8)
    return [Blob(int(st[i][0]), int(st[i][1]), int(st[i][2]), int(st[i][3]), int(st[i][4])) for i in range(1, n)]


def _scale(frame: np.ndarray) -> float:
    return frame.shape[1] / REF_WIDTH


def find_player(frame: np.ndarray, prev: tuple[int, int] | None = None) -> Blob | None:
    """Silhueta preta mais alta que larga. Ignora os quadradinhos do HUD (quadrados)."""
    s = _scale(frame)
    mask = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)[..., 2] < 50
    cands = [b for b in _blobs(mask)
             if 8 * s <= b.h <= 70 * s and 3 * s <= b.w <= 30 * s
             and b.h >= 1.5 * b.w and b.area >= 0.4 * b.w * b.h]
    if not cands:
        return None
    if prev is not None:
        return min(cands, key=lambda b: (b.center[0] - prev[0]) ** 2 + (b.center[1] - prev[1]) ** 2)
    return max(cands, key=lambda b: b.area)


def find_door(frame: np.ndarray) -> Blob | None:
    """Retângulo cinza neutro (baixa saturação) mais ou menos quadrado."""
    s = _scale(frame)
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = (hsv[..., 1] < 40) & (hsv[..., 2] > 170) & (hsv[..., 2] < 215)
    cands = [b for b in _blobs(mask)
             if 12 * s <= b.w <= 60 * s and 14 * s <= b.h <= 70 * s
             and 0.9 <= b.h / b.w <= 1.8 and b.area >= 0.4 * b.w * b.h]
    return max(cands, key=lambda b: b.area) if cands else None


def death_screen(frame: np.ndarray) -> bool:
    """Texto amarelo largo 'PRESS ANY KEY' no topo. O ícone amarelo do HUD é pequeno demais."""
    h, w = frame.shape[:2]
    b, g, r = (frame[: int(h * 0.4), :, i].astype(np.int16) for i in range(3))
    yellow = ((r > 225) & (g > 215) & (b < 175)).astype(np.uint8)
    merged = cv2.dilate(yellow, np.ones((3, 21), np.uint8))   # junta letras e palavras
    return any(bl.w >= 0.12 * w and bl.h <= 0.12 * h and bl.area >= 0.12 * w
               for bl in _blobs(merged))


def solid_color(frame: np.ndarray, player: Blob) -> np.ndarray:
    """Cor do chão logo abaixo dos pés do personagem (mediana de um pequeno recorte)."""
    cx, _ = player.center
    y = min(frame.shape[0] - 1, player.y + player.h + 3)
    patch = frame[y:y + 2, max(0, cx - 3):cx + 4].reshape(-1, 3)
    return np.median(patch, axis=0)


def solid_mask(frame: np.ndarray, color: np.ndarray, tol: int = 40) -> np.ndarray:
    return np.abs(frame.astype(np.int16) - color.astype(np.int16)).max(axis=2) < tol


def level_hash(frame: np.ndarray) -> int:
    """Assinatura da fase: forma do espaço aberto (laranja), imune a HUD, personagem e porta."""
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    open_space = ((hsv[..., 2] > 200) & (hsv[..., 1] > 100)).astype(np.uint8) * 255
    n = int(HASH_BITS ** 0.5)
    small = cv2.resize(open_space, (n, n), interpolation=cv2.INTER_AREA)
    return int("".join("1" if v > 127 else "0" for v in small.flatten()), 2)
