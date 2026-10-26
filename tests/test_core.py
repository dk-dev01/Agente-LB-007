import sys
from pathlib import Path
import unittest
import copy
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from lb007.core import Maze, Config, train, evaluate, update


class CoreTests(unittest.TestCase):
    def test_collision_and_goal(self):
        maze = Maze(("SG", ".."))
        self.assertEqual(maze.step(maze.start, 0), (maze.start, -3, False, True))
        self.assertEqual(maze.step(maze.start, 1), (maze.goal, 20, True, False))

    def test_bellman_update_and_terminal(self):
        q = {(0, 0): [2., 0., 0., 0.], (0, 1): [10.] * 4}
        update(q, (0, 0), 0, -1, (0, 1), False, .5, .9)
        self.assertEqual(q[(0, 0)][0], 5.)
        update(q, (0, 0), 0, 20, (0, 1), True, .5, .9)
        self.assertEqual(q[(0, 0)][0], 12.5)

    def test_seed_reproducibility_and_frozen_evaluation(self):
        maze, cfg = Maze(("S.G", "...")), Config(episodes=100)
        q, history = train(maze, cfg, 42)
        self.assertEqual((q, history), train(maze, cfg, 42))
        before = copy.deepcopy(q)
        metrics = evaluate(maze, q, episodes=20)
        self.assertEqual(q, before)
        self.assertEqual(metrics["success_rate"], 1.)
        self.assertEqual(metrics["mean_steps_success"], 2.)

    def test_unreachable_terminates_by_limit(self):
        maze = Maze(("S#G",))
        self.assertIsNone(maze.shortest_path_length())
        q, history = train(maze, Config(episodes=2, max_steps=7))
        self.assertEqual(history[-1]["steps"], 7)
        metrics = evaluate(maze, q, episodes=3, max_steps=7)
        self.assertEqual(metrics["success_rate"], 0)
        self.assertIsNone(metrics["mean_steps_success"])

    def test_invalid_maps(self):
        for rows in (("SSG",), ("SG", "."), ("SXG",), ("...",)):
            with self.assertRaises(ValueError):
                Maze(rows)


if __name__ == "__main__":
    unittest.main()
