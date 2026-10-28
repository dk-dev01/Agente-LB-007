"""Interface local do seminário, usando o mesmo núcleo dos experimentos."""
import argparse
from dataclasses import asdict
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import re
from pathlib import Path
import sys
import threading
import webbrowser
from dataset_export import DatasetStore

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
from lb007.core import ACTION_NAMES, Config, DEFAULT_MAP, Maze, evaluate, rollout, train


def number(data, key, default, minimum, maximum, integer=False):
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{key}: informe um número.")
    if not minimum <= value <= maximum or (integer and int(value) != value):
        raise ValueError(f"{key}: use um valor entre {minimum} e {maximum}.")
    return int(value) if integer else float(value)


def prepare(data):
    if not isinstance(data, dict):
        raise ValueError("Envie um objeto JSON.")
    rows = data.get("rows", list(DEFAULT_MAP))
    if (not isinstance(rows, list) or not 2 <= len(rows) <= 12
            or any(not isinstance(row, str) or not 2 <= len(row) <= 12 for row in rows)):
        raise ValueError("Use um mapa de 2 a 12 linhas e colunas.")
    maze = Maze(tuple(rows), step_reward=number(data, "step_reward", -1, -10, 0))
    cfg = Config(
        episodes=number(data, "episodes", 1000, 1, 5000, True),
        max_steps=number(data, "max_steps", 100, 1, 200, True),
        alpha=number(data, "alpha", .1, .001, 1),
        gamma=number(data, "gamma", .95, 0, .999),
        epsilon_start=number(data, "epsilon_start", 1, 0, 1),
        epsilon_end=number(data, "epsilon_end", .05, 0, 1),
    )
    seed = number(data, "seed", 0, 0, 2147483647, True)
    return maze, cfg, seed


def simulate(data, on_transition=None):
    maze, cfg, seed = prepare(data)
    q, history = train(maze, cfg, seed, on_transition=on_transition)
    # Avaliação congelada, com as mesmas sementes e limite para ambas as políticas.
    evaluation_seed, episodes = 100000, 200
    return {
        "rows": list(maze.rows), "config": asdict(cfg), "seed": seed,
        "step_reward": maze.step_reward, "collision_reward": maze.collision_reward,
        "goal_reward": maze.goal_reward, "actions": list(ACTION_NAMES),
        "shortest_path": maze.shortest_path_length(),
        "evaluation": {"episodes": episodes, "seed": evaluation_seed},
        "trained": evaluate(maze, q, episodes, evaluation_seed, cfg.max_steps),
        "random": evaluate(maze, None, episodes, evaluation_seed, cfg.max_steps),
        "trained_run": rollout(maze, q, evaluation_seed, cfg.max_steps),
        "random_run": rollout(maze, None, evaluation_seed, cfg.max_steps),
        "q_table": [{"state": list(state), "values": values} for state, values in q.items()],
        "history": history,
    }


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / "web"), **kwargs)

    def json_response(self, status, data):
        payload = json.dumps(data, ensure_ascii=False, allow_nan=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        download = re.fullmatch(r'/api/datasets/([0-9a-f]{32})\.(xlsx|csv)', self.path)
        if download:
            token, kind = download.groups()
            store = getattr(self.server, 'dataset_store', None)
            if store is None:
                return self.json_response(404, {'error': 'Base indisponível. Execute um treinamento novamente.'})
            with store.lock:
                path = store.file(token, kind)
                if path is None:
                    return self.json_response(404, {'error': 'Base expirada. Execute um treinamento novamente.'})
                self.send_response(200)
                content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' if kind == 'xlsx' else 'text/csv; charset=utf-8'
                self.send_header('Content-Type', content_type)
                self.send_header('Content-Disposition', f'attachment; filename="base-lb007-{token[:8]}.{kind}"')
                self.send_header('Content-Length', str(path.stat().st_size))
                self.send_header('Cache-Control', 'no-store')
                self.end_headers()
                with path.open('rb') as stream:
                    self.copyfile(stream, self.wfile)
        elif self.path == "/api/config":
            self.json_response(200, {"rows": list(DEFAULT_MAP), "config": asdict(Config())})
        elif self.path.startswith("/api/"):
            self.json_response(404, {"error": "Rota não encontrada."})
        else:
            super().do_GET()

    def do_POST(self):
        if self.path != "/api/train":
            return self.json_response(404, {"error": "Rota não encontrada."})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 16384:
                raise ValueError("Corpo da requisição ausente ou muito grande.")
            data = json.loads(self.rfile.read(length))
            # Uma execução por vez: evita sobrecarga ao clicar em várias abas.
            if not self.server.training_lock.acquire(blocking=False):
                return self.json_response(409, {"error": "Já há um treinamento em andamento. Aguarde."})
            try:
                if not hasattr(self.server, 'dataset_store'):
                    self.server.dataset_store = DatasetStore()
                result = self.server.dataset_store.capture(simulate, data)
            finally:
                self.server.training_lock.release()
            self.json_response(200, result)
        except (ValueError, TypeError, UnicodeDecodeError) as exc:
            self.json_response(400, {"error": str(exc)})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--open", action="store_true", help="Abrir o navegador")
    args = parser.parse_args()
    try:
        server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    except OSError as exc:
        parser.exit(1, f"Não foi possível iniciar: {exc}\nTente: python app.py --port 8001\n")
    server.training_lock = threading.Lock()
    url = f"http://127.0.0.1:{server.server_port}"
    print(f"Agente LB 007: {url}\nDeixe este terminal aberto. Ctrl+C encerra o servidor.", flush=True)
    if args.open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor encerrado.")
    finally:
        server.server_close()
        if hasattr(server, 'dataset_store'):
            server.dataset_store.close()


if __name__ == "__main__":
    main()
