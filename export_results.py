"""Gera versões legíveis do summary.csv sem modificar os resultados originais."""
import csv
from pathlib import Path

VARIANTS = {"reference": "Referência", "E1_constant_exploration": "E1: exploração constante",
            "E2_alpha_05": "E2: aprendizado com alpha 0,5", "E3_step_minus_01": "E3: penalidade por passo -0,1"}
HEADERS = ["Configuração", "Agente", "Chegou à saída (%)", "Variação do sucesso (p.p.)",
           "Passos nos sucessos (média)", "Colisões por tentativa (média)", "Pontuação média"]


def number(value, scale=1):
    return f"{float(value) * scale:.2f}".replace(".", ",") if value else "Não disponível"


def export(folder):
    with (folder / "summary.csv").open(encoding="utf-8-sig", newline="") as f:
        raw = list(csv.DictReader(f))
    rows = [[VARIANTS.get(r["variant"], r["variant"]), {"random": "Aleatório", "trained": "Treinado"}.get(r["policy"], r["policy"]),
             number(r["success_rate"], 100), number(r["success_rate_sd"], 100),
             number(r["mean_steps_success"]), number(r["mean_collisions"]), number(r["mean_return"])] for r in raw]
    with (folder / "resumo_pt.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(HEADERS)
        writer.writerows(rows)
    lines = ["# Resultados do labirinto", "", "Fonte: `summary.csv`. Valores arredondados apenas para apresentação.", "",
             "| " + " | ".join(HEADERS) + " |", "|" + "---|" * len(HEADERS)]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    lines += ["", "## Como interpretar", "",
              "- Chegou à saída: percentual de tentativas bem-sucedidas; maior é melhor.",
              "- Variação do sucesso: desvio padrão entre sementes, em pontos percentuais; não é intervalo de confiança.",
              "- Passos nos sucessos: média das médias por semente, apenas nas tentativas que chegaram à saída. Leia junto com a taxa de sucesso.",
              "- Colisões: média por tentativa, incluindo sucessos e falhas; menor é melhor.",
              "- Pontuação: soma das recompensas. E3 usa outra escala; sua pontuação não deve ser comparada diretamente às demais.",
              "- Aleatório escolhe movimentos ao acaso. Treinado usa a tabela aprendida, sem atualização durante a avaliação.",
              "", "O teste usa o mesmo mapa e início. Os resultados não demonstram desempenho em qualquer labirinto.", ""]
    (folder / "RESUMO.md").write_text("\n".join(lines), encoding="utf8")


if __name__ == "__main__":
    export(Path(__file__).parent / "results")
