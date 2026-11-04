import csv
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import simulate
from dataset_export import DatasetStore


class DatasetTests(unittest.TestCase):
    def test_logging_preserves_learning_and_matches_every_step(self):
        data = {'episodes': 24, 'seed': 0}
        baseline = simulate(data)
        store = DatasetStore()
        try:
            result = store.capture(simulate, data)
            token = result.pop('dataset')['id']
            self.assertEqual(baseline, result)
            raw = store.entries[token][0]
            with raw.open(encoding='utf8', newline='') as stream:
                rows = list(csv.DictReader(stream))
            for episode in result['history']:
                steps = [r for r in rows if int(r['episode']) == episode['episode']]
                self.assertEqual(len(steps), episode['steps'])
                self.assertAlmostEqual(sum(float(r['reward']) for r in steps), episode['return'])
                self.assertEqual(steps[-1]['terminated'] == 'True', episode['success'])
            self.assertEqual(rows[0]['state'], '(0, 0)')
        finally:
            store.close()

    def test_exports_are_isolated_by_run_and_old_runs_expire(self):
        store = DatasetStore()
        try:
            ids = []
            for seed in range(4):
                result = store.capture(simulate, {'episodes': 1, 'rows': ['SG', '..'], 'seed': seed})
                ids.append(result['dataset']['id'])
            self.assertIsNone(store.file(ids[0], 'csv'))
            self.assertEqual(len(store.entries), 3)
            with store.file(ids[-1], 'csv').open(encoding='utf-8-sig', newline='') as stream:
                rows = list(csv.DictReader(stream, delimiter=';'))
            self.assertTrue(all(r['Semente'] == '3' for r in rows))
        finally:
            store.close()
