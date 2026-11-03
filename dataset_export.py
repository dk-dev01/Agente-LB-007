"""Exporta eventos do agente e registra transições reais para CSV/XLSX.

A exportação de eventos produz CSV, JSONL e manifesto a partir das sessões
registradas. DatasetStore captura transições de treino e disponibiliza CSV/XLSX
a partir do modelo em assets/transitions_template.xlsx.
"""
import argparse
import copy
import csv
import json
import threading
import tempfile
import uuid
import zipfile
from collections import Counter, OrderedDict
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "dataset"

# Configuração da exportação de transições de treino para CSV/XLSX.
NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
ET.register_namespace("", NS)
TEMPLATE = ROOT / "assets" / "transitions_template.xlsx"
FIELDS = [
    "seed", "episode", "step", "state", "action", "reward",
    "next_state", "terminated", "truncated",
]
HEADERS = [
    "Semente", "Episódio", "Passo", "Posição antes", "Ação",
    "Recompensa", "Posição depois", "Chegou à saída?", "Limite atingido?",
]
ACTIONS = ["Cima", "Direita", "Baixo", "Esquerda"]


def read_jsonl(path):
    """Lê JSONL, ignorando e avisando sobre linhas inválidas."""
    rows = []
    if not path.exists():
        return rows
    with path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                print(f"Aviso: linha JSON inválida ignorada: {path}:{line_no}")
    return rows


def readable(row):
    """Converte uma transição bruta para valores legíveis na planilha."""
    action_index = int(row["action"])
    return [
        int(row["seed"]),
        int(row["episode"]),
        int(row["step"]),
        row["state"],
        ACTIONS[action_index],
        float(row["reward"]),
        row["next_state"],
        "Sim" if str(row["terminated"]).lower() == "true" else "Não",
        "Sim" if str(row["truncated"]).lower() == "true" else "Não",
    ]


def cell_xml(ref, value, style="0"):
    """Cria o XML de uma célula XLSX."""
    if isinstance(value, (int, float)):
        return f'<c r="{ref}" s="{style}" t="n"><v>{value}</v></c>'
    return (
        f'<c r="{ref}" s="{style}" t="inlineStr">'
        f"<is><t>{escape(str(value))}</t></is></c>"
    )


def build_xlsx(raw_csv, destination, result, count):
    """Preserva formatos/metadados do modelo e substitui os dados demonstrativos."""
    if not TEMPLATE.exists():
        raise FileNotFoundError(f"Modelo XLSX não encontrado: {TEMPLATE}")

    with (
        zipfile.ZipFile(TEMPLATE) as source,
        zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as target,
    ):
        for item in source.infolist():
            if item.filename == "xl/worksheets/sheet1.xml":
                root = ET.fromstring(source.read(item))
                data = root.find(f"{{{NS}}}sheetData")
                if data is None:
                    raise ValueError("O modelo XLSX não contém sheetData em sheet1.xml.")

                sample = next((row for row in data if row.get("r") == "5"), None)
                if sample is None:
                    raise ValueError("O modelo XLSX não contém a linha de estilo 5.")
                styles = [cell.get("s", "0") for cell in sample]
                if len(styles) < len(FIELDS):
                    styles.extend(["0"] * (len(FIELDS) - len(styles)))

                for row in list(data):
                    try:
                        row_number = int(row.get("r", "0"))
                    except ValueError:
                        continue
                    if row_number >= 5:
                        data.remove(row)

                marker = ET.Element("DATA_ROWS")
                data.append(marker)

                dimension = root.find(f"{{{NS}}}dimension")
                if dimension is not None:
                    dimension.set("ref", f"A1:I{count + 4}")

                auto_filter = root.find(f"{{{NS}}}autoFilter")
                if auto_filter is None:
                    auto_filter = ET.Element(f"{{{NS}}}autoFilter")
                    root.insert(list(root).index(data) + 1, auto_filter)
                auto_filter.set("ref", f"A4:I{count + 4}")

                serialized = ET.tostring(root, encoding="utf-8")
                marker_xml = b"<DATA_ROWS />"
                if marker_xml not in serialized:
                    marker_xml = b"<DATA_ROWS></DATA_ROWS>"
                prefix, suffix = serialized.split(marker_xml, 1)

                with (
                    target.open(item.filename, "w") as output,
                    raw_csv.open(encoding="utf-8", newline="") as stream,
                ):
                    output.write(prefix)
                    for row_number, row in enumerate(csv.DictReader(stream), 5):
                        cells = "".join(
                            cell_xml(
                                f"{chr(65 + column)}{row_number}",
                                value,
                                styles[column],
                            )
                            for column, value in enumerate(readable(row))
                        )
                        output.write(
                            f'<row r="{row_number}" ht="24" customHeight="1">'
                            f"{cells}</row>".encode("utf-8")
                        )
                    output.write(suffix)

            elif item.filename == "xl/worksheets/sheet2.xml":
                root = ET.fromstring(source.read(item))
                config = result["config"]
                values = [
                    result["seed"],
                    config["episodes"],
                    config["max_steps"],
                    config["alpha"],
                    config["gamma"],
                    config["epsilon_start"],
                    config["epsilon_end"],
                    result["step_reward"],
                    result["collision_reward"],
                    result["goal_reward"],
                    count,
                    "Simulação do labirinto; dados gerados durante o treino",
                    " / ".join(result["rows"]),
                ]
                for row_number, value in enumerate(values, 4):
                    row = root.find(f'.//{{{NS}}}row[@r="{row_number}"]')
                    if row is None:
                        continue
                    old_cell = row.find(f'{{{NS}}}c[@r="B{row_number}"]')
                    if old_cell is None:
                        continue
                    new_cell = ET.fromstring(
                        cell_xml(f"B{row_number}", value, old_cell.get("s", "0"))
                    )
                    for element in new_cell.iter():
                        if not element.tag.startswith("{"):
                            element.tag = f"{{{NS}}}{element.tag}"
                    index = list(row).index(old_cell)
                    row.remove(old_cell)
                    row.insert(index, new_cell)

                target.writestr(
                    item,
                    ET.tostring(root, encoding="utf-8", xml_declaration=True),
                )
            else:
                target.writestr(item, source.read(item))


class DatasetStore:
    """Mantém as três execuções recentes nesta sessão do servidor."""

    def __init__(self):
        self.folder = tempfile.TemporaryDirectory(prefix="lb007-datasets-")
        self.entries = OrderedDict()
        self.lock = threading.RLock()

    def capture(self, simulate, data):
        """Executa a simulação, registra transições e guarda os metadados."""
        token = uuid.uuid4().hex
        raw = Path(self.folder.name) / f"{token}.raw.csv"
        count = 0

        try:
            with raw.open("w", encoding="utf-8", newline="") as stream:
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

        meta = {
            key: copy.deepcopy(result[key])
            for key in (
                "seed", "rows", "config", "step_reward",
                "collision_reward", "goal_reward",
            )
        }

        with self.lock:
            self.entries[token] = (raw, meta, count)
            while len(self.entries) > 3:
                old_token, old_entry = self.entries.popitem(last=False)
                old_raw, _, _ = old_entry
                for old_path in Path(self.folder.name).glob(f"{old_token}.*"):
                    old_path.unlink(missing_ok=True)

        result["dataset"] = {
            "id": token,
            "transitions": count,
            "xlsx_url": f"/api/datasets/{token}.xlsx",
            "csv_url": f"/api/datasets/{token}.csv",
        }
        return result

    def file(self, token, kind):
        """Retorna o CSV/XLSX da execução, gerando-o sob demanda."""
        with self.lock:
            entry = self.entries.get(token)
            if entry is None:
                return None

            raw, meta, count = entry
            if kind not in ("xlsx", "csv"):
                return None

            path = Path(self.folder.name) / f"{token}.{kind}"
            if not path.exists():
                if kind == "xlsx":
                    build_xlsx(raw, path, meta, count)
                else:
                    with (
                        raw.open(encoding="utf-8", newline="") as source,
                        path.open("w", encoding="utf-8-sig", newline="") as output,
                    ):
                        writer = csv.writer(output, delimiter=";")
                        writer.writerow(HEADERS)
                        for row in csv.DictReader(source):
                            values = readable(row)
                            values[5] = str(values[5]).replace(".", ",")
                            writer.writerow(values)
            return path

    def close(self):
        """Remove os arquivos temporários da sessão."""
        self.folder.cleanup()


def main():
    """Exporta eventos das sessões para CSV, JSONL e manifesto."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default="dataset_export",
        help="prefixo dos arquivos de saída (padrão: dataset_export)",
    )
    args = parser.parse_args()

    prefix = Path(args.out)
    if not prefix.is_absolute():
        prefix = ROOT / prefix

    events = []
    sessions = []

    for event_file in sorted(DATA.glob("*/events.jsonl")):
        session_dir = event_file.parent
        events.extend(read_jsonl(event_file))
        meta_file = session_dir / "session.json"
        if meta_file.exists():
            try:
                sessions.append(json.loads(meta_file.read_text(encoding="utf-8")))
            except json.JSONDecodeError:
                print(f"Aviso: metadados inválidos: {meta_file}")

    for event_file in sorted((ROOT / "diagnosticos").glob("*/eventos.jsonl")):
        diagnostic_id = event_file.parent.name
        for row in read_jsonl(event_file):
            events.append({
                "event_type": "diagnostic_" + str(row.get("event", "event")),
                "session_id": "diagnostic_" + diagnostic_id,
                "time": row.get("time"),
                "move": row.get("move"),
                "key": row.get("key"),
                "ball_before": row.get("ball_before_px"),
                "ball_after": row.get("ball_after_px"),
                "moved": row.get("movement_detected"),
                "ball_detection_before": row.get("detection_before"),
                "ball_detection_after": row.get("detection_after"),
                "image_before": row.get("image_before"),
                "image_after": row.get("image_after"),
                "calibration_image": row.get("initial_image"),
                "outcome": row.get("interpretation"),
            })

    # Compatibilidade com versões antigas que só gravavam maze_memoria.jsonl.
    if not events:
        events = read_jsonl(ROOT / "maze_memoria.jsonl")

    fields = [
        "event_type", "session_id", "time", "move", "key", "ball_before",
        "ball_after", "portal", "ball_detection_before", "ball_detection_after",
        "moved", "closer_to_goal", "success", "outcome", "failure", "reason",
        "status", "movement_count", "distance_to_portal_before_px",
        "distance_to_portal_after_px", "path_cells", "key_hold_seconds",
        "observation_delay_seconds", "image_before", "image_after",
        "calibration_image", "observation_image", "diagnostic_image",
    ]

    csv_path = prefix.with_suffix(".csv")
    jsonl_path = prefix.with_suffix(".jsonl")
    manifest_path = prefix.parent / (prefix.name + "_manifest.json")
    prefix.parent.mkdir(parents=True, exist_ok=True)

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in events:
            writer.writerow({
                key: (
                    json.dumps(row[key], ensure_ascii=False)
                    if isinstance(row.get(key), (list, dict))
                    else row.get(key, "")
                )
                for key in fields
            })

    with jsonl_path.open("w", encoding="utf-8") as f:
        for row in events:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    movement_count = sum(event.get("event_type") == "movement" for event in events)
    manifest = {
        "source": "dataset/*/events.jsonl; fallback maze_memoria.jsonl",
        "sessions": sessions,
        "event_count": len(events),
        "movement_count": movement_count,
        "outputs": {"csv": csv_path.name, "jsonl": jsonl_path.name},
        "label_warning": (
            "moved, closer_to_goal, success and outcome are automatic "
            "observations/heuristics, not manually verified ground-truth labels."
        ),
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Eventos exportados: {len(events)} (movimentos: {movement_count})")
    print(f"CSV: {csv_path}\nJSONL: {jsonl_path}\nManifesto: {manifest_path}")


if __name__ == "__main__":
    main()
