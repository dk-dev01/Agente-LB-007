# Relatório de execuções — Maze: Path of Light

Gerado em: 2026-11-02T22:06:19-03:00

## Resumo

- Sessões registradas: 4
- Comandos de movimento observados: 8
- Ações sem deslocamento detectado: 8
- Fases concluídas segundo a heurística do agente: 1
- Falhas de planejamento: 0
- Setas manuais diagnosticadas: 0 (movimento visual detectado: 0)

## Sessões

| Sessão | Início | Estado | Movimentos | Deslocou | Progresso | Bloqueado/sem progresso | Rota não encontrada | Fases |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 20261102_214428_a8be69 | 2026-11-02T21:44:28-03:00 | stopped | 2 | 0 | 0 | 2 | 0 | 0 |
| 20261102_220021_ac3e75 | 2026-11-02T22:00:21-03:00 | stopped | 2 | 0 | 0 | 1 | 0 | 1 |
| 20261102_220127_e9d13c | 2026-11-02T22:01:27-03:00 | stopped | 2 | 0 | 0 | 2 | 0 | 0 |
| 20261102_220526_cb1e27 | 2026-11-02T22:05:26-03:00 | stopped | 2 | 0 | 0 | 2 | 0 | 0 |

## Interpretação e limitações

Os resultados são produzidos automaticamente a partir das capturas e da distância estimada até o portal. A detecção de movimento e os rótulos de progresso/sucesso são heurísticos; revise as imagens antes/depois em `dataset/<sessão>/frames/` antes de tratá-los como verdade de referência.
Cada pasta de sessão contém `session.json` (calibração, região e parâmetros), `events.jsonl` e capturas antes/depois de cada comando. `dataset_export.py` exporta os eventos para CSV/JSONL.

## Arquivos

- Tabela de sessões: `resultados_maze_sessoes.csv`
- Capturas e eventos por sessão: `dataset/<id>/`
- Histórico acumulado: `maze_memoria.jsonl`
- Dataset tabular: `dataset_export.py`
