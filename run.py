"""Execute python run.py --help. Usa somente a biblioteca padrão."""
import argparse
import csv
import json
from pathlib import Path
import statistics
import sys
from dataclasses import asdict, replace

sys.path.insert(0, str(Path(__file__).parent / "src"))
from lb007.core import Config, Maze, train, evaluate, rollout


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description="Q-learning tabular em labirinto")
    parser.add_argument("--episodes", type=int, default=1000)
    parser.add_argument("--seeds", type=int, default=5)
    parser.add_argument("--eval-episodes", type=int, default=200)
    parser.add_argument("--output", type=Path, default=Path("results"))
    args = parser.parse_args()
    if args.seeds < 1 or args.eval_episodes < 1:
        parser.error("Seeds e episódios de avaliação devem ser positivos.")
    config, maze = Config(episodes=args.episodes), Maze()
    args.output.mkdir(parents=True, exist_ok=True)
    variants = [
        ("reference", maze, config),
        ("E1_constant_exploration", maze, replace(config, epsilon_start=.2, epsilon_end=.2)),
        ("E2_alpha_05", maze, replace(config, alpha=.5)),
        ("E3_step_minus_01", replace(maze, step_reward=-.1), config),
    ]
    manifest = {"environment": asdict(maze), "config": asdict(config),
                "training_seeds": list(range(args.seeds)), "evaluation_episodes": args.eval_episodes,
                "evaluation_seed_base": 100000,
                "variants": {name: {"maze": asdict(m), "config": asdict(c)} for name, m, c in variants},
                "scope": "Mesmo mapa e início; episódios novos, Q congelada; não demonstra generalização a novos mapas."}
    (args.output / "config.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    results, history = [], []
    reference_q = None
    for seed in range(args.seeds):
        eval_seed = 100000 + seed * args.eval_episodes
        for name, env, cfg in variants:
            # Salva transições da execução de referência da primeira semente para EDA.
            transitions = [] if seed == 0 and name == "reference" else None
            q, episodes = train(env, cfg, seed, transitions.append if transitions is not None else None)
            if transitions is not None:
                write_csv(args.output / "transitions_seed0.csv", transitions)
                reference_q = q
                (args.output / "q_table.json").write_text(json.dumps([
                    {"state": list(s), "values": values} for s, values in q.items()
                ], indent=2), encoding="utf-8")
            history.extend({"variant": name, "seed": seed, **row} for row in episodes)
            for policy, table in (("random", None), ("trained", q)):
                results.append({"variant": name, "seed": seed, "policy": policy,
                                **evaluate(env, table, args.eval_episodes, eval_seed, cfg.max_steps)})
            print(f"Concluído: seed={seed} {name}", flush=True)
    write_csv(args.output / "metrics.csv", results)
    write_csv(args.output / "training.csv", history)
    summary = []
    for name, _, _ in variants:
        for policy in ("random", "trained"):
            rows = [r for r in results if r["variant"] == name and r["policy"] == policy]
            record = {"variant": name, "policy": policy}
            for metric in ("success_rate", "mean_steps_success", "mean_return", "mean_collisions"):
                values = [r[metric] for r in rows if r[metric] is not None]
                record[metric] = statistics.mean(values) if values else None
                record[metric + "_sd"] = statistics.stdev(values) if len(values) > 1 else None
            summary.append(record)
    write_csv(args.output / "summary.csv", summary)
    # Casos-limite reais: pouco treino, mapa alterado e destino isolado.
    low_q, _ = train(maze, replace(config, episodes=1, epsilon_start=0, epsilon_end=0), 0)
    changed = Maze(("S.#...", ".##.#.", "....#.", ".##...", "...##.", ".#...G"))
    impossible = Maze(("S.....", ".##.#.", "....#.", ".##...", "...###", ".#..#G"))
    cases = []
    for name, env, table in (("little_training", maze, low_q), ("changed_map_without_retraining", changed, reference_q), ("unreachable_goal", impossible, reference_q)):
        cases.append({"case": name, "shortest_path": env.shortest_path_length(),
                      **evaluate(env, table, args.eval_episodes, 900000)})
    (args.output / "edge_cases.json").write_text(json.dumps(cases, indent=2), encoding="utf-8")
    (args.output / "example_path.json").write_text(json.dumps(rollout(maze, reference_q), indent=2), encoding="utf-8")
    print(f"Resultados salvos em {args.output.resolve()}")


if __name__ == "__main__":
    main()
