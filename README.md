# Agente LB 007

Projeto do Grupo 01 de Inteligência Artificial II: um agente aprende a percorrer um labirinto usando Q-learning tabular. Inclui núcleo científico, experimentos e interface web local para visualizar o aprendizado. O desempenho é avaliado no mapa usado para treinar; mudanças no ambiente exigem novo treinamento.

## Problema de pesquisa e objetivos

O Q-learning permite que um agente alcance objetivos com maior eficiência do que uma estratégia aleatória?

O objetivo geral é desenvolver e avaliar um agente baseado em Q-learning capaz de alcançar objetivos em um jogo.

- [x] Desenvolver o ambiente do labirinto.
- [x] Implementar uma estratégia aleatória (baseline).
- [x] Implementar o algoritmo Q-learning e treinar o agente.
- [x] Registrar recompensas e comparar resultados com o baseline.
- [x] Analisar erros e dificuldades iniciais.
- [x] Criar um protótipo visual.

## Executar

Requer Python 3.10 ou superior. Sem bibliotecas externas.

### Interface visual

No Windows, abra `INICIAR_INTERFACE.bat` ou execute na pasta do projeto:

```bash
python app.py --open
```

Se necessário, substitua `python` por `py -3`. Acesse http://127.0.0.1:8000 e mantenha o terminal aberto. Treine o agente, compare os resultados, anime as trajetórias e inspecione a tabela Q clicando nas casas. Você pode editar paredes e parâmetros para um novo treino. [Instruções e roteiro de demonstração](docs/INTERFACE.md).

### Experimentos e testes

```bash
python -m unittest discover -s tests -v
python run.py
```

O segundo comando executa quatro configurações, cinco sementes de treinamento por configuração, 1.000 episódios de treino por semente e 200 episódios de avaliação por semente/política. Para uma execução rápida de desenvolvimento:

```bash
python run.py --episodes 100 --seeds 2 --eval-episodes 50 --output results_smoke
```

Resultados em `results/`: métricas por semente, resumo com média e desvio padrão, histórico de treinamento, tabela Q, trajetória ilustrativa, casos-limite e configuração reproduzível. `transitions_seed0.csv` registra todas as transições da referência com semente 0; é regenerado e ignorado no Git para evitar volume desnecessário.

## Ambiente e método

Mapa sintético 6 × 6, com 9 paredes e 27 posições livres, incluindo a saída. Estado = posição. Ações = cima, direita, baixo, esquerda. Colisão mantém a posição e vale −3; movimento comum vale −1; alcançar a saída vale +20 e encerra o episódio. O limite de coleta é 100 passos. A saída é terminal; o limite de passos é uma truncagem e mantém o bootstrap na atualização Q.

```text
Q(s,a) ← Q(s,a) + α [r + γ max Q(s',a') − Q(s,a)]
```

Na chegada à saída, o alvo é apenas r. α controla o tamanho da atualização; γ desconta recompensas futuras. A política epsilon-greedy escolhe uma ação aleatória com probabilidade epsilon; caso contrário, usa a maior estimativa Q, com desempate aleatório reproduzível.

O mapa permanece fixo durante cada treinamento. A avaliação usa a tabela congelada, sem exploração deliberada ou atualizações, e sementes separadas. Esse protocolo mede desempenho no mesmo ambiente, não generalização para labirintos novos. Epsilon permanece positivo no treino e alpha é constante: não alegamos que esta configuração finita satisfaz uma garantia assintótica de convergência.

## Como ler os resultados

Abra [resultados.xlsx](results/resultados.xlsx) no Excel para consultar a tabela formatada em português. É uma fotografia dos dados de `summary.csv` desta revisão.

Para regenerar as tabelas em português sem instalar dependências:

```bash
python export_results.py
```

Esse comando lê `results/summary.csv` e atualiza `results/RESUMO.md` e `results/resumo_pt.csv` (ponto e vírgula, decimais com vírgula e UTF-8 com BOM, adequado ao Excel em português). O XLSX incluído não é atualizado por esse comando. O CSV original permanece com precisão integral para análise e reprodução.

[Ver a tabela diretamente no GitHub](results/RESUMO.md).

## Resultados iniciais

Execução de 26/10/2026: agente aleatório com 31,5% de sucesso; Q-learning de referência com 100%, em 10 passos nas tentativas bem-sucedidas. O menor caminho também possui 10 passos, calculado por BFS apenas como referência. Todas as variantes treinadas empataram no desempenho final. Consulte `docs/RESULTADOS.md` para limites e interpretação.

## Integração com o jogo

O módulo `src/lb007/core.py` expõe `Maze`, `Config`, `train`, `rollout` e `evaluate`. `train` devolve tabela Q e histórico; aceita um callback opcional `on_transition`. `rollout` devolve caminho e métricas sem alterar a tabela, adequado para animar o personagem. A ordem das ações está em `ACTION_NAMES`.

Ao mudar o mapa na interface, identifique a política antiga como treinada em outro ambiente e ofereça novo treinamento. Não prometa que uma tabela baseada apenas na posição se adapte automaticamente ao mapa alterado. Mapas sem caminho podem ser detectados por `shortest_path_length()` e exibidos como caso-limite.

## Organização

- `src/lb007/core.py`: ambiente, algoritmo e avaliação.
- `app.py` e `web/`: servidor local e interface de demonstração com treino e avaliação reais.
- `INICIAR_INTERFACE.bat`: inicialização no Windows.
- `run.py`: protocolo experimental e exportação CSV/JSON.
- `tests/test_core.py`: testes de dinâmica, equação, reprodutibilidade, avaliação congelada e casos inválidos.
- `tests/test_app.py`: integração da interface, protocolo HTTP, validação e mapa sem saída.
- `docs/INTERFACE.md`: execução, roteiro da demonstração e atualização da branch.
- `docs/PLANO.md`: roteiro de seminário, divisão sugerida e pendências.
- `docs/RESULTADOS.md`: evidências reais e ficha de experimentos.
- `docs/DIARIO_IA.md`: registro inicial de apoio por IA, com revisão humana pendente.

## Referência

Watkins, C. J. C. H.; Dayan, P. (1992). Q-learning. Machine Learning, 8, 279–292. https://www.gatsby.ucl.ac.uk/~dayan/papers/cjch.pdf

## Entregas pendentes

Slides, resumo no template vigente da FIB, folder/QR Code, carrossel, vídeo, Model Card e validação pelo grupo. O protótipo web roda localmente; sua publicação não faz parte desta versão. Cada integrante precisa entender e defender suas escolhas.
