# Plano de seminário do Grupo 01

Título sugerido: Q-learning aplicado a um agente em labirinto.

Apresentação em 01/12/2026. Entrega comum em 17/11/2026 até 17h. Pré-banca em 10/11. Checkpoints em 27/10 e 03/11. Confirmar eventuais atualizações do professor.

## Roteiro de 40 minutos

| Minutos | Conteúdo e evidência |
|---|---|
| 0–3 | Pergunta à plateia: como sair de um labirinto sem conhecer o caminho? Mostrar movimentos aleatórios |
| 3–7 | Problema, público e objetivo; simulação didática, sem alegar implantação em robô real |
| 7–15 | Agente, estado, ação, recompensa, episódio, política; tabela Q; epsilon-greedy; equação e exemplo numérico |
| 15–20 | Mapa, regras, origem sintética dos dados e três descobertas da EDA |
| 20–28 | Baseline, protocolo, três hipóteses e resultados; explicar o empate das variantes |
| 28–32 | Pouco treinamento, mapa alterado e saída impossível; limites de generalização |
| 32–38 | Demonstração do jogo web quando integrado; alteração proposta pela plateia; novo treinamento |
| 38–40 | Conclusão apoiada nos dados e próximos passos |

Exemplo numérico: Q atual = 2, alpha = 0,5, recompensa = −1, gamma = 0,9, melhor Q do próximo estado = 10. Alvo = −1 + 0,9 × 10 = 8. Novo Q = 2 + 0,5 × (8 − 2) = 5. Na saída, não se adiciona valor futuro.

## Divisão sugerida de cinco frentes

Distribuição a decidir pelo grupo, sem atribuir nomes automaticamente: ambiente e regras; algoritmo e testes; experimentos e gráficos; interface e demonstração; comunicação e materiais. Todos devem conseguir explicar o projeto inteiro.

## Próximas entregas

1. Reproduzir os testes e resultados em um computador do grupo e registrar dúvidas.
2. Integrar o núcleo à interface web, com mapa, animação, seleção de parâmetros, indicadores e visualização da tabela Q.
3. Adicionar gráficos de aprendizado a partir de training.csv; distinguir treinamento de avaliação.
4. Preparar desafio ao vivo, detecção de mapa impossível e plano B sem internet.
5. Criar slides com as evidências revisadas e ensaiar o núcleo de 40 minutos.
6. Produzir resumo de duas páginas no template vigente da Jornada FIB, Model Card de uma página, ficha de experimentos, folder com QR Code, carrossel e vídeo de 1–3 minutos.
7. Manter diário de IA com o processo real; não preencher validações ou reflexões que ninguém realizou.

## Perguntas para ensaio

- Por que Q-learning? O problema é uma sequência de decisões com recompensas e estados discretos.
- Qual é o baseline? Política aleatória, com as mesmas regras e orçamento de avaliação.
- Onde estão os dados? Nas transições geradas pela interação e nos históricos por episódio.
- Por que não basta usar BFS? Num mapa conhecido, BFS resolve menor caminho; aqui investigamos aprendizado por experiência. BFS é referência para medir distância, não parte do agente.
- O agente funciona em qualquer mapa? Não. A tabela é específica do ambiente treinado.
- Por que 100% não significa problema resolvido universalmente? O teste utiliza um mapa fixo, determinístico e pequeno.
- O que o empate dos experimentos ensina? A métrica final saturou; é preciso estudar custo de aprendizagem e ambientes adicionais antes de alegar superioridade.
