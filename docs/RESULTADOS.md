# Resultados iniciais do Agente LB 007

Execução real em 26/10/2026, pelo comando `python run.py`. Os dados completos e configurações estão em `results/`. Não são resultados coletados por integrantes do grupo; foram executados durante o desenvolvimento assistido por IA e precisam de reprodução e revisão pelo grupo.

## Protocolo

Cinco sementes de treinamento (0–4), 1.000 episódios cada, limite de 100 passos, alpha 0,1, gamma 0,95 e epsilon linear de 1 a 0,05 na referência. Avaliação: 200 episódios por semente e política, totalizando 1.000 por configuração/política. Nenhuma atualização da tabela durante avaliação. Mesmo mapa e mesma posição inicial. Ambiente determinístico; os 1.000 testes não equivalem a 1.000 mapas independentes.

## Comparação final

| Política | Sucesso médio | Desvio padrão entre sementes | Passos médios nos sucessos | Colisões por episódio |
|---|---:|---:|---:|---:|
| Aleatória | 31,5% | 5,24 pontos percentuais | 63,67 | 40,53 |
| Q-learning de referência | 100% | 0 | 10 | 0 |

Passos são a média das médias por semente, considerando apenas sucessos; falhas são reportadas pela taxa de sucesso. O desvio padrão é entre cinco execuções, não um intervalo de confiança. Não medir sucesso apenas pelos passos: excluir falhas dessa média pode esconder um agente ruim.

## Ficha de experimentos

Hipóteses definidas antes da execução, a partir da proposta inicial do projeto. Cada variante é comparada diretamente à referência, não à variante anterior.

| Experimento | Hipótese | Alteração | Resultado final | Interpretação |
|---|---|---|---|---|
| E1 | Exploração decrescente pode favorecer o aprendizado | Epsilon constante 0,2 versus linear 1 → 0,05 | Ambos 100% e 10 passos | Sem evidência de vantagem final neste mapa; comparar custo do treino |
| E2 | Alpha maior pode acelerar ou desestabilizar atualizações | Alpha 0,5 versus 0,1 | Ambos 100% e 10 passos | Métrica final não distingue as opções; não concluir superioridade |
| E3 | Penalidade maior por passo pode incentivar trajetórias curtas | −0,1 versus −1 por movimento comum | Ambos 100% e 10 passos | Ambos chegaram ao menor caminho; retornos não são diretamente comparáveis entre escalas |

## Evolução durante treinamento

Valores agregados sobre cinco sementes; cada janela contém 500 episódios. Incluem ações exploratórias, portanto não representam avaliação da política gulosa em checkpoints.

| Configuração | Sucesso nos episódios 1–100 | Passos médios 1–100, incluindo falhas | Passos médios 901–1000 |
|---|---:|---:|---:|
| Referência | 50,0% | 81,32 | 11,130 |
| E1 epsilon constante | 98,6% | 22,29 | 12,444 |
| E2 alpha 0,5 | 51,0% | 79,71 | 11,006 |
| E3 penalidade −0,1 | 50,2% | 80,84 | 11,106 |

Todos obtiveram 100% de sucesso na última janela. A referência começa com quase todas as ações aleatórias; E1 começa com 20% de exploração. A diferença inicial é influenciada pela própria política de coleta. Para afirmar qual aprende mais rápido, acrescentar avaliações congeladas nos mesmos checkpoints de treino. Essas avaliações ainda não foram implementadas.

## Três descobertas exploratórias

Na referência, semente 0, o arquivo de transições possui 30.597 registros:

1. Foram visitadas as 26 posições não terminais como origem de uma ação. A saída é a 27ª posição livre e encerra o episódio. Cobertura neste mapa não prova generalização.
2. Houve 9.627 movimentos que mantiveram a posição, correspondendo a colisões neste ambiente. Isso expõe o custo da exploração.
3. Houve 934 episódios encerrados na saída e 66 por limite de passos. Truncagem e término real precisam ser separados nos registros e na atualização.

O dataset é sintético, gerado pelo ambiente e pela política de coleta. Não há atributos ausentes a imputar ou escala numérica a padronizar: estados são identificadores discretos. As limitações principais são cobertura, dependência entre transições e restrição a um mapa.

## Casos-limite executados

200 avaliações por caso, usando sementes a partir de 900000:

- **Um episódio de treinamento, epsilon zero:** 0% de sucesso e 98 colisões médias. Evidência de insuficiência nessa execução, não prova de que epsilon zero sempre falha; desempates ainda são aleatórios.
- **Uma parede adicionada em (0,2), sem retreinar:** 100% de sucesso e 10 passos. A alteração não impediu a política aprendida. Não é prova de robustez geral; para investigar sensibilidade, testar outras paredes, especialmente no caminho usado.
- **Saída isolada:** 0% de sucesso; BFS confirma que não existe caminho. O episódio termina pelo limite, com 92 colisões médias. O sistema precisa explicar a impossibilidade em vez de prometer aprendizado.

## Conclusão defensável

O Q-learning aprendeu uma política de menor caminho no labirinto fixo utilizado, superando o baseline aleatório na taxa de sucesso. Os três fatores testados não mudaram o desempenho final após 1.000 episódios. O estudo ainda não mede generalização, cenários estocásticos, desempenho em mapas maiores ou estabilidade em uma amostra ampla de ambientes.
