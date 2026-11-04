"""Verificações da integração web com o núcleo e do contrato HTTP."""
import http.client
import json
import io
import csv
import zipfile
from xml.etree import ElementTree as ET
from pathlib import Path
import sys
import threading
import unittest
from http.server import ThreadingHTTPServer

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import Handler, prepare, simulate


class InterfaceTests(unittest.TestCase):
    def test_simulation_uses_core_and_preserves_protocol(self):
        result = simulate({"rows": ["SG", ".."], "episodes": 100, "seed": 42})
        self.assertEqual(result["trained"]["success_rate"], 1)
        self.assertEqual(result["trained"]["mean_steps_success"], 1)
        self.assertEqual(result["shortest_path"], 1)
        self.assertEqual(result["evaluation"]["episodes"], 200)
        self.assertEqual(len(result["history"]), 100)
        self.assertEqual(len(result["q_table"]), 4)
        self.assertEqual(simulate({"rows": ["SG", ".."], "episodes": 100, "seed": 42}), result)

    def test_blocked_map_is_a_result_not_a_crash(self):
        result = simulate({"rows": ["S#G", "###"], "episodes": 2, "max_steps": 5})
        self.assertIsNone(result["shortest_path"])
        self.assertEqual(result["trained"]["success_rate"], 0)
        self.assertIsNone(result["trained"]["mean_steps_success"])
        self.assertEqual(result["trained_run"]["steps"], 5)

    def test_untrusted_configuration_is_bounded(self):
        for data in ([], {"episodes": 0}, {"episodes": 5001}, {"episodes": 1.5},
                     {"episodes": True}, {"seed": "0"}, {"gamma": 1},
                     {"alpha": float('nan')}, {"rows": ["S.G", ".."]},
                     {"rows": ["SS", ".G"]}, {"rows": "S.G"}):
            with self.subTest(data=data), self.assertRaises(ValueError):
                prepare(data)

    def test_http_assets_training_errors_and_busy(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        server.training_lock = threading.Lock()
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        connection = http.client.HTTPConnection(*server.server_address, timeout=30)
        try:
            for route in ('/', '/style.css', '/app.js', '/api/config'):
                connection.request('GET', route)
                response = connection.getresponse()
                self.assertEqual(response.status, 200)
                self.assertTrue(response.read())
            connection.request('POST', '/api/train', json.dumps({"rows": ["SG", ".."], "episodes": 50}))
            response = connection.getresponse()
            self.assertEqual(response.status, 200)
            result = json.loads(response.read())
            self.assertEqual(result["trained"]["success_rate"], 1)
            self.assertEqual(result['dataset']['transitions'], sum(row['steps'] for row in result['history']))
            for kind in ('csv', 'xlsx'):
                connection.request('GET', result['dataset'][kind + '_url'])
                response = connection.getresponse()
                self.assertEqual(response.status, 200)
                self.assertIn('attachment', response.getheader('Content-Disposition'))
                content = response.read()
                if kind == 'csv':
                    rows = list(csv.reader(io.StringIO(content.decode('utf-8-sig')), delimiter=';'))
                    self.assertEqual(len(rows), result['dataset']['transitions'] + 1)
                    self.assertEqual(rows[0][4], 'Ação')
                    self.assertTrue(all(len(row) == 9 for row in rows))
                    self.assertTrue(all(row[4] in ('Cima', 'Direita', 'Baixo', 'Esquerda') for row in rows[1:]))
                else:
                    ns = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
                    with zipfile.ZipFile(io.BytesIO(content)) as workbook:
                        self.assertIsNone(workbook.testzip())
                        sheet = ET.fromstring(workbook.read('xl/worksheets/sheet1.xml'))
                        data = sheet.find('m:sheetData', ns)
                        self.assertEqual(sum(int(r.get('r')) >= 5 for r in data), result['dataset']['transitions'])
                        self.assertEqual(sheet.find('m:autoFilter', ns).get('ref'), f"A4:I{result['dataset']['transitions'] + 4}")
                        first = next(r for r in data if r.get('r') == '5')
                        self.assertEqual(first[0].get('t'), 'n')
                        self.assertEqual(first[4].find('m:is/m:t', ns).text in ('Cima', 'Direita', 'Baixo', 'Esquerda'), True)
                        self.assertEqual(sheet.find('m:sheetViews/m:sheetView/m:pane', ns).get('ySplit'), '4')
            connection.request('GET', '/api/datasets/' + '0' * 32 + '.xlsx')
            response = connection.getresponse()
            self.assertEqual(response.status, 404)
            response.read()
            for payload in ('{', '{"episodes":5001}', '[]'):
                connection.request('POST', '/api/train', payload)
                response = connection.getresponse()
                self.assertEqual(response.status, 400)
                self.assertIn('error', json.loads(response.read()))
            server.training_lock.acquire()
            try:
                connection.request('POST', '/api/train', '{}')
                response = connection.getresponse()
                self.assertEqual(response.status, 409)
                response.read()
            finally:
                server.training_lock.release()
        finally:
            connection.close()
            server.shutdown()
            server.server_close()
            thread.join()
            if hasattr(server, 'dataset_store'):
                server.dataset_store.close()
