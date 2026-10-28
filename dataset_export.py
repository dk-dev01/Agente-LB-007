"""Registra transições reais e preenche o modelo XLSX sem dependências extras.

O modelo em assets foi criado com Artifact Tool. A exportação em execução usa
somente CSV, ZIP e XML da biblioteca padrão; as linhas são escritas em fluxo.
"""
import csv
from collections import OrderedDict
import copy
from pathlib import Path
import tempfile
import threading
import uuid
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape
import zipfile

NS = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
ET.register_namespace('', NS)
TEMPLATE = Path(__file__).parent / 'assets' / 'transitions_template.xlsx'
FIELDS = ['seed', 'episode', 'step', 'state', 'action', 'reward', 'next_state', 'terminated', 'truncated']
HEADERS = ['Semente', 'Episódio', 'Passo', 'Posição antes', 'Ação', 'Recompensa', 'Posição depois', 'Chegou à saída?', 'Limite atingido?']
ACTIONS = ['Cima', 'Direita', 'Baixo', 'Esquerda']


def readable(row):
    return [int(row['seed']), int(row['episode']), int(row['step']), row['state'],
            ACTIONS[int(row['action'])], float(row['reward']), row['next_state'],
            'Sim' if row['terminated'] == 'True' else 'Não',
            'Sim' if row['truncated'] == 'True' else 'Não']


def cell_xml(ref, value, style='0'):
    if isinstance(value, (int, float)):
        return f'<c r="{ref}" s="{style}" t="n"><v>{value}</v></c>'
    return f'<c r="{ref}" s="{style}" t="inlineStr"><is><t>{escape(str(value))}</t></is></c>'


def build_xlsx(raw_csv, destination, result, count):
    """Conserva formatos e metadados do modelo; substitui os dados demonstrativos."""
    with zipfile.ZipFile(TEMPLATE) as source, zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as target:
        for item in source.infolist():
            if item.filename == 'xl/worksheets/sheet1.xml':
                root = ET.fromstring(source.read(item))
                data = root.find(f'{{{NS}}}sheetData')
                sample = next(r for r in data if r.get('r') == '5')
                styles = [c.get('s', '0') for c in sample]
                for row in list(data):
                    if int(row.get('r')) >= 5:
                        data.remove(row)
                data.append(ET.Element('DATA_ROWS'))
                dimension = root.find(f'{{{NS}}}dimension')
                if dimension is not None:
                    dimension.set('ref', f'A1:I{count + 4}')
                filt = root.find(f'{{{NS}}}autoFilter')
                if filt is None:
                    filt = ET.Element(f'{{{NS}}}autoFilter')
                    root.insert(list(root).index(data) + 1, filt)
                filt.set('ref', f'A4:I{count + 4}')
                prefix, suffix = ET.tostring(root, encoding='utf-8').split(b'<DATA_ROWS />')
                with target.open(item.filename, 'w') as output, raw_csv.open(encoding='utf8', newline='') as stream:
                    output.write(prefix)
                    for i, row in enumerate(csv.DictReader(stream), 5):
                        cells = ''.join(cell_xml(f'{chr(65+j)}{i}', v, styles[j]) for j, v in enumerate(readable(row)))
                        output.write(f'<row r="{i}" ht="24" customHeight="1">{cells}</row>'.encode('utf8'))
                    output.write(suffix)
            elif item.filename == 'xl/worksheets/sheet2.xml':
                root = ET.fromstring(source.read(item))
                cfg = result['config']
                values = [result['seed'], cfg['episodes'], cfg['max_steps'], cfg['alpha'], cfg['gamma'],
                          cfg['epsilon_start'], cfg['epsilon_end'], result['step_reward'],
                          result['collision_reward'], result['goal_reward'], count,
                          'Simulação do labirinto; dados gerados durante o treino', ' / '.join(result['rows'])]
                for i, value in enumerate(values, 4):
                    row = root.find(f'.//{{{NS}}}row[@r="{i}"]')
                    old = row.find(f'{{{NS}}}c[@r="B{i}"]')
                    new = ET.fromstring(cell_xml(f'B{i}', value, old.get('s', '0')))
                    # Coloca o novo elemento no namespace da planilha.
                    for el in new.iter():
                        el.tag = f'{{{NS}}}{el.tag}'
                    index = list(row).index(old)
                    row.remove(old)
                    row.insert(index, new)
                target.writestr(item, ET.tostring(root, encoding='utf-8', xml_declaration=True))
            else:
                target.writestr(item, source.read(item))


class DatasetStore:
    """Mantém as três execuções recentes nesta sessão do servidor."""
    def __init__(self):
        self.folder = tempfile.TemporaryDirectory(prefix='lb007-datasets-')
        self.entries = OrderedDict()
        self.lock = threading.RLock()

    def capture(self, simulate, data):
        token = uuid.uuid4().hex
        raw = Path(self.folder.name) / f'{token}.raw.csv'
        count = 0
        try:
            with raw.open('w', encoding='utf8', newline='') as stream:
                writer = csv.DictWriter(stream, fieldnames=FIELDS)
                writer.writeheader()
                def record(row):
                    nonlocal count
                    writer.writerow(row)
                    count += 1
                result = simulate(data, on_transition=record)
        except Exception:
            raw.unlink(missing_ok=True)
            raise
        meta = {key: copy.deepcopy(result[key]) for key in ['seed', 'rows', 'config', 'step_reward', 'collision_reward', 'goal_reward']}
        with self.lock:
            self.entries[token] = (raw, meta, count)
            while len(self.entries) > 3:
                old, _ = self.entries.popitem(last=False)
                for path in Path(self.folder.name).glob(f'{old}.*'):
                    path.unlink(missing_ok=True)
        result['dataset'] = {'id': token, 'transitions': count,
                             'xlsx_url': f'/api/datasets/{token}.xlsx',
                             'csv_url': f'/api/datasets/{token}.csv'}
        return result

    def file(self, token, kind):
        entry = self.entries.get(token)
        if entry is None:
            return None
        raw, meta, count = entry
        path = Path(self.folder.name) / f'{token}.{kind}'
        if not path.exists():
            if kind == 'xlsx':
                build_xlsx(raw, path, meta, count)
            elif kind == 'csv':
                with raw.open(encoding='utf8', newline='') as source, path.open('w', encoding='utf-8-sig', newline='') as output:
                    writer = csv.writer(output, delimiter=';')
                    writer.writerow(HEADERS)
                    for row in csv.DictReader(source):
                        values = readable(row)
                        values[5] = str(values[5]).replace('.', ',')
                        writer.writerow(values)
            else:
                return None
        return path

    def close(self):
        self.folder.cleanup()
