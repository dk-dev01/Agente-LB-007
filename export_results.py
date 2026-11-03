"""Gera relatórios das sessões do agente e versões legíveis dos resultados dos experimentos."""
import argparse
import csv
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "dataset"

VARIANTS = {
    "reference": "Referência",
    "E1_constant_exploration": "E1: exploração constante",
    "E2_alpha_05": "E2: aprendizado com alpha 0,5",
    "E3_step_minus_01": "E3: penalidade por passo -0,1",
}
HEADERS = [
    "Configuração",
    "Agente",
    "Chegou à saída (%)",
    "Variação do sucesso (p.p.)",
    "Passos nos sucessos (média)",
    "Colisões por tentativa (média)",
    "Pontuação média",
]


def number(value, scale=1):
    return f"{float(value) * scale:.2f}".replace(".", ",") if value else "Não disponível"


def export(folder):
    """Gera resumo_pt.csv e RESUMO.md a partir de results/summary.csv."""
    summary_path = folder / "summary.csv"
    if not summary_path.exists():
        print(f"Resumo dos experimentos não gerado: arquivo não encontrado em {summary_path}")
        return

    with summary_path.open(encoding="utf-8-sig", newline="") as f:
        raw = list(csv.DictReader(f))

    rows = [
        [
            VARIANTS.get(r["variant"], r["variant"]),
            {"random": "Aleatório", "trained": "Treinado"}.get(r["policy"], r["policy"]),
            number(r["success_rate"], 100),
            number(r["success_rate_sd"], 100),
            number(r["mean_steps_success"]),
            number(r["mean_collisions"]),
            number(r["mean_return"]),
        ]
        for r in raw
    ]

    with (folder / "resumo_pt.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(HEADERS)
        writer.writerows(rows)

    lines = [
        "# Resultados do labirinto",
        "",
        "Fonte: `summary.csv`. Valores arredondados apenas para apresentação.",
        "",
        "| " + " | ".join(HEADERS) + " |",
        "|" + "---|" * len(HEADERS),
    ]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    lines += [
        "",
        "## Como interpretar",
        "",
        "- Chegou à saída: percentual de tentativas bem-sucedidas; maior é melhor.",
        "- Variação do sucesso: desvio padrão entre sementes, em pontos percentuais; não é intervalo de confiança.",
        "- Passos nos sucessos: média das médias por semente, apenas nas tentativas que chegaram à saída. Leia junto com a taxa de sucesso.",
        "- Colisões: média por tentativa, incluindo sucessos e falhas; menor é melhor.",
        "- Pontuação: soma das recompensas. E3 usa outra escala; sua pontuação não deve ser comparada diretamente às demais.",
        "- Aleatório escolhe movimentos ao acaso. Treinado usa a tabela aprendida, sem atualização durante a avaliação.",
        "",
        "O teste usa o mesmo mapa e início. Os resultados não demonstram desempenho em qualquer labirinto.",
        "",
    ]
    (folder / "RESUMO.md").write_text("\n".join(lines), encoding="utf-8")


def read_events(path):
    result = []
    if path.exists():
        with path.open(encoding="utf-8") as f:
            for line in f:
                try:
                    result.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return result


def main():
    """Gera relatório Markdown e CSV das sessões registradas."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--prefix",
        default="resultados_maze",
        help="prefixo dos arquivos (padrão: resultados_maze)",
    )
    args = parser.parse_args()

    prefix = Path(args.prefix)
    if not prefix.is_absolute():
        prefix = ROOT / prefix

    sessions = []
    for event_file in sorted(DATA.glob("*/events.jsonl")):
        folder = event_file.parent
        meta_path = folder / "session.json"
        try:
            meta = (
                json.loads(meta_path.read_text(encoding="utf-8"))
                if meta_path.exists()
                else {"session_id": folder.name}
            )
        except json.JSONDecodeError:
            meta = {"session_id": folder.name}

        events = read_events(event_file)
        moves = [e for e in events if e.get("event_type") == "movement"]
        counts = Counter(e.get("outcome", "unlabeled") for e in moves)
        sessions.append({
            "session_id": meta.get("session_id", folder.name),
            "started_at": meta.get("started_at", ""),
            "ended_at": meta.get("ended_at", ""),
            "status": meta.get("status", "unknown"),
            "moves": len(moves),
            "moves_observed": sum(bool(e.get("moved")) for e in moves),
            "progress": counts.get("progress", 0),
            "blocked_or_wrong": counts.get("blocked_or_wrong", 0),
            "success_labels": counts.get("success", 0),
            "planning_failures": sum(e.get("event_type") == "planning_failure" for e in events),
            "completed_levels": sum(e.get("event_type") == "level_completed" for e in events),
            "metadata": meta,
        })

    diagnostic_count = 0
    diagnostic_moved = 0
    diagnostic_files = sorted((ROOT / "diagnosticos").glob("*/eventos.jsonl"))
    for event_file in diagnostic_files:
        diag_events = read_events(event_file)
        arrow_events = [
            e for e in diag_events
            if e.get("event") in ("manual_arrow", "synthetic_arrow_test")
        ]
        diagnostic_count += len(arrow_events)
        diagnostic_moved += sum(bool(e.get("movement_detected")) for e in arrow_events)

    synthetic_count = sum(
        e.get("event_type") == "diagnostic_synthetic_arrow_test"
        for path in diagnostic_files
        for e in read_events(path)
    )

    prefix.parent.mkdir(parents=True, exist_ok=True)
    csv_path = prefix.with_name(prefix.name + "_sessoes.csv")
    md_path = prefix.with_suffix(".md")
    columns = [
        "session_id", "started_at", "ended_at", "status", "moves",
        "moves_observed", "progress", "blocked_or_wrong", "success_labels",
        "planning_failures", "completed_levels",
    ]

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for session in sessions:
            writer.writerow({key: session[key] for key in columns})

    total_moves = sum(s["moves"] for s in sessions)
    lines = [
        "# Relatório de execuções — Maze: Path of Light",
        "",
        f"Gerado em: {datetime.now().astimezone().isoformat(timespec='seconds')}",
        "",
        "## Resumo",
        "",
        f"- Sessões registradas: {len(sessions)}",
        f"- Comandos de movimento observados: {total_moves}",
        f"- Ações sem deslocamento detectado: {sum(s['moves'] - s['moves_observed'] for s in sessions)}",
        f"- Fases concluídas segundo a heurística do agente: {sum(s['completed_levels'] for s in sessions)}",
        f"- Falhas de planejamento: {sum(s['planning_failures'] for s in sessions)}",
        f"- Setas testadas no diagnóstico: {diagnostic_count}, incluindo testes sintéticos: {synthetic_count} (movimento visual detectado: {diagnostic_moved})",
        "",
        "## Sessões",
        "",
        "| Sessão | Início | Estado | Movimentos | Deslocou | Progresso | Bloqueado/sem progresso | Rota não encontrada | Fases |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for session in sessions:
        lines.append(
            f"| {session['session_id']} | {session['started_at']} | {session['status']} "
            f"| {session['moves']} | {session['moves_observed']} | {session['progress']} "
            f"| {session['blocked_or_wrong']} | {session['planning_failures']} "
            f"| {session['completed_levels']} |"
        )

    lines += [
        "",
        "## Interpretação e limitações",
        "",
        "Os resultados são produzidos automaticamente a partir das capturas e da distância estimada até o portal. A detecção de movimento e os rótulos de progresso/sucesso são heurísticos; revise as imagens antes/depois em `dataset/<sessão>/frames/` antes de tratá-los como verdade de referência.",
        "Cada pasta de sessão contém `session.json` (calibração, região e parâmetros), `events.jsonl` e capturas antes/depois de cada comando. `dataset_export.py` exporta os eventos para CSV/JSONL.",
        "",
        "## Arquivos",
        "",
        f"- Tabela de sessões: `{csv_path.name}`",
        "- Capturas e eventos por sessão: `dataset/<id>/`",
        "- Histórico acumulado: `maze_memoria.jsonl`",
        "- Dataset tabular: `dataset_export.py`",
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Relatório: {md_path}\nTabela: {csv_path}")


if __name__ == "__main__":
    main()
    export(ROOT / "results")
