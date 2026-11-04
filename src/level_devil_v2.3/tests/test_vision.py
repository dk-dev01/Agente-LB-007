"""Valida a visão nas capturas reais do jogo. Uso: python tests/test_vision.py"""
import sys, pathlib
import cv2
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from vision import find_player, find_door, death_screen, level_hash, solid_color

here = pathlib.Path(__file__).parent
morte, fase = cv2.imread(str(here / "tela_morte.png")), cv2.imread(str(here / "fase3.png"))

p = find_player(fase); d = find_door(fase)
assert p and (p.w, p.h) == (10, 25), p
assert d and abs(d.w - 23) <= 1 and abs(d.h - 27) <= 1, d
assert not death_screen(fase), "HUD amarelo não pode contar como tela de morte"
assert death_screen(morte), "PRESS ANY KEY deve ser detectado"
assert find_player(morte) is None, "personagem morto não deve ser detectado"
assert find_door(morte) is not None
assert tuple(int(v) for v in solid_color(fase, p)[::-1]) == (153, 107, 7), solid_color(fase, p)
hm, hf = level_hash(morte), level_hash(fase)
print("player", p, "| door", d, "| dist hash morte x fase3:", bin(hm ^ hf).count("1"), "/ 1024")
print("OK")
