"""Gera um resumo documental em Markdown e CSV para as sessões do agente."""
import argparse
import csv
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parent
DATA=ROOT/"dataset"


def read_events(path):
    result=[]
    if path.exists():
        with path.open(encoding="utf-8") as f:
            for line in f:
                try: result.append(json.loads(line))
                except json.JSONDecodeError: pass
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix",default="resultados_maze",help="prefixo dos arquivos (padrão: resultados_maze)")
    args=parser.parse_args()
    prefix=Path(args.prefix)
    if not prefix.is_absolute(): prefix=ROOT/prefix
    sessions=[]
    for event_file in sorted(DATA.glob("*/events.jsonl")):
        folder=event_file.parent
        meta_path=folder/"session.json"
        try: meta=json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {"session_id":folder.name}
        except json.JSONDecodeError: meta={"session_id":folder.name}
        events=read_events(event_file)
        moves=[e for e in events if e.get("event_type")=="movement"]
        counts=Counter(e.get("outcome","unlabeled") for e in moves)
        sessions.append({"session_id":meta.get("session_id",folder.name),"started_at":meta.get("started_at",""),
                         "ended_at":meta.get("ended_at",""),"status":meta.get("status","unknown"),
                         "moves":len(moves),"moves_observed":sum(bool(e.get("moved")) for e in moves),
                         "progress":counts.get("progress",0),"blocked_or_wrong":counts.get("blocked_or_wrong",0),
                         "success_labels":counts.get("success",0),
                         "planning_failures":sum(e.get("event_type")=="planning_failure" for e in events),
                         "completed_levels":sum(e.get("event_type")=="level_completed" for e in events),
                         "metadata":meta})
    diagnostic_count=0
    diagnostic_moved=0
    for event_file in sorted((ROOT/"diagnosticos").glob("*/eventos.jsonl")):
        diag_events=read_events(event_file)
        arrow_events=[e for e in diag_events if e.get("event") in ("manual_arrow","synthetic_arrow_test")]
        diagnostic_count+=len(arrow_events)
        diagnostic_moved+=sum(bool(e.get("movement_detected")) for e in arrow_events)
    synthetic_count=sum(e.get("event_type")=="diagnostic_synthetic_arrow_test" for path in (ROOT/"diagnosticos").glob("*/eventos.jsonl") for e in read_events(path))
    prefix.parent.mkdir(parents=True,exist_ok=True)
    csv_path=prefix.with_name(prefix.name+"_sessoes.csv")
    md_path=prefix.with_suffix(".md")
    columns=["session_id","started_at","ended_at","status","moves","moves_observed","progress","blocked_or_wrong","success_labels","planning_failures","completed_levels"]
    with csv_path.open("w",newline="",encoding="utf-8-sig") as f:
        writer=csv.DictWriter(f,fieldnames=columns); writer.writeheader()
        for s in sessions: writer.writerow({k:s[k] for k in columns})
    total_moves=sum(s["moves"] for s in sessions)
    lines=["# Relatório de execuções — Maze: Path of Light","",
           f"Gerado em: {datetime.now().astimezone().isoformat(timespec='seconds')}","",
           "## Resumo","",f"- Sessões registradas: {len(sessions)}",f"- Comandos de movimento observados: {total_moves}",
           f"- Ações sem deslocamento detectado: {sum(s['moves']-s['moves_observed'] for s in sessions)}",
           f"- Fases concluídas segundo a heurística do agente: {sum(s['completed_levels'] for s in sessions)}",
           f"- Falhas de planejamento: {sum(s['planning_failures'] for s in sessions)}",
           f"- Setas testadas no diagnóstico: {diagnostic_count}, incluindo testes sintéticos: {synthetic_count} (movimento visual detectado: {diagnostic_moved})","",
           "## Sessões","",
           "| Sessão | Início | Estado | Movimentos | Deslocou | Progresso | Bloqueado/sem progresso | Rota não encontrada | Fases |",
           "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    for s in sessions:
        lines.append(f"| {s['session_id']} | {s['started_at']} | {s['status']} | {s['moves']} | {s['moves_observed']} | {s['progress']} | {s['blocked_or_wrong']} | {s['planning_failures']} | {s['completed_levels']} |")
    lines += ["","## Interpretação e limitações","",
              "Os resultados são produzidos automaticamente a partir das capturas e da distância estimada até o portal. A detecção de movimento e os rótulos de progresso/sucesso são heurísticos; revise as imagens antes/depois em `dataset/<sessão>/frames/` antes de tratá-los como verdade de referência.",
              "Cada pasta de sessão contém `session.json` (calibração, região e parâmetros), `events.jsonl` e capturas antes/depois de cada comando. `dataset_export.py` exporta os eventos para CSV/JSONL.",
              "","## Arquivos","",f"- Tabela de sessões: `{csv_path.name}`","- Capturas e eventos por sessão: `dataset/<id>/`","- Histórico acumulado: `maze_memoria.jsonl`","- Dataset tabular: `dataset_export.py`"]
    md_path.write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(f"Relatório: {md_path}\nTabela: {csv_path}")


if __name__=="__main__": main()
