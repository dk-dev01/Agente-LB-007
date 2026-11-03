"""Exporta os eventos do agente para CSV e JSONL prontos para documentação."""
import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "dataset"


def read_jsonl(path):
    rows=[]
    if not path.exists():
        return rows
    with path.open(encoding="utf-8") as f:
        for line_no,line in enumerate(f,1):
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                print(f"Aviso: linha JSON inválida ignorada: {path}:{line_no}")
    return rows


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",default="dataset_export",help="prefixo dos arquivos de saída (padrão: dataset_export)")
    args=parser.parse_args()
    prefix=Path(args.out)
    if not prefix.is_absolute(): prefix=ROOT/prefix
    events=[]
    sessions=[]
    for event_file in sorted(DATA.glob("*/events.jsonl")):
        session_dir=event_file.parent
        events.extend(read_jsonl(event_file))
        meta_file=session_dir/"session.json"
        if meta_file.exists():
            try: sessions.append(json.loads(meta_file.read_text(encoding="utf-8")))
            except json.JSONDecodeError: print(f"Aviso: metadados inválidos: {meta_file}")
    for event_file in sorted((ROOT/"diagnosticos").glob("*/eventos.jsonl")):
        diag_id=event_file.parent.name
        for row in read_jsonl(event_file):
            events.append({"event_type":"diagnostic_"+str(row.get("event","event")),
                           "session_id":"diagnostic_"+diag_id,"time":row.get("time"),"move":row.get("move"),
                           "key":row.get("key"),"ball_before":row.get("ball_before_px"),
                           "ball_after":row.get("ball_after_px"),"moved":row.get("movement_detected"),
                           "ball_detection_before":row.get("detection_before"),"ball_detection_after":row.get("detection_after"),
                           "image_before":row.get("image_before"),"image_after":row.get("image_after"),
                           "calibration_image":row.get("initial_image"),"outcome":row.get("interpretation")})
    # Compatibilidade com versões antigas que só gravavam maze_memoria.jsonl.
    if not events:
        events=read_jsonl(ROOT/"maze_memoria.jsonl")
    fields=["event_type","session_id","time","move","key","ball_before","ball_after","portal","ball_detection_before","ball_detection_after",
            "moved","closer_to_goal","success","outcome","failure","reason","status","movement_count",
            "distance_to_portal_before_px","distance_to_portal_after_px","path_cells","key_hold_seconds",
            "observation_delay_seconds","image_before","image_after","calibration_image","observation_image",
            "diagnostic_image"]
    csv_path=prefix.with_suffix(".csv")
    jsonl_path=prefix.with_suffix(".jsonl")
    manifest_path=prefix.parent/(prefix.name+"_manifest.json")
    prefix.parent.mkdir(parents=True,exist_ok=True)
    with csv_path.open("w",newline="",encoding="utf-8-sig") as f:
        writer=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore")
        writer.writeheader()
        for row in events:
            writer.writerow({k:json.dumps(row[k],ensure_ascii=False) if isinstance(row.get(k),(list,dict)) else row.get(k,"") for k in fields})
    with jsonl_path.open("w",encoding="utf-8") as f:
        for row in events: f.write(json.dumps(row,ensure_ascii=False)+"\n")
    movement_count=sum(e.get("event_type")=="movement" for e in events)
    manifest={"source":"dataset/*/events.jsonl; fallback maze_memoria.jsonl", "sessions":sessions,
              "event_count":len(events),"movement_count":movement_count,
              "outputs":{"csv":csv_path.name,"jsonl":jsonl_path.name},
              "label_warning":"moved, closer_to_goal, success and outcome are automatic observations/heuristics, not manually verified ground-truth labels."}
    manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"Eventos exportados: {len(events)} (movimentos: {movement_count})")
    print(f"CSV: {csv_path}\nJSONL: {jsonl_path}\nManifesto: {manifest_path}")


if __name__=="__main__": main()
