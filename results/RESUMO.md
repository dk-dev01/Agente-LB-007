# Resultados do labirinto

Fonte: `summary.csv`. Valores arredondados apenas para apresentação.

| Configuração | Agente | Chegou à saída (%) | Variação do sucesso (p.p.) | Passos nos sucessos (média) | Colisões por tentativa (média) | Pontuação média |
|---|---|---|---|---|---|---|
| Referência | Aleatório | 31,50 | 5,24 | 63,67 | 40,53 | -162,97 |
| Referência | Treinado | 100,00 | 0,00 | 10,00 | 0,00 | 11,00 |
| E1: exploração constante | Aleatório | 31,50 | 5,24 | 63,67 | 40,53 | -162,97 |
| E1: exploração constante | Treinado | 100,00 | 0,00 | 10,00 | 0,00 | 11,00 |
| E2: aprendizado com alpha 0,5 | Aleatório | 31,50 | 5,24 | 63,67 | 40,53 | -162,97 |
| E2: aprendizado com alpha 0,5 | Treinado | 100,00 | 0,00 | 10,00 | 0,00 | 11,00 |
| E3: penalidade por passo -0,1 | Aleatório | 31,50 | 5,24 | 63,67 | 40,53 | -120,06 |
| E3: penalidade por passo -0,1 | Treinado | 100,00 | 0,00 | 10,00 | 0,00 | 19,10 |

## Como interpretar

- Chegou à saída: percentual de tentativas bem-sucedidas; maior é melhor.
- Variação do sucesso: desvio padrão entre sementes, em pontos percentuais; não é intervalo de confiança.
- Passos nos sucessos: média das médias por semente, apenas nas tentativas que chegaram à saída. Leia junto com a taxa de sucesso.
- Colisões: média por tentativa, incluindo sucessos e falhas; menor é melhor.
- Pontuação: soma das recompensas. E3 usa outra escala; sua pontuação não deve ser comparada diretamente às demais.
- Aleatório escolhe movimentos ao acaso. Treinado usa a tabela aprendida, sem atualização durante a avaliação.

O teste usa o mesmo mapa e início. Os resultados não demonstram desempenho em qualquer labirinto.
