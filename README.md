# Agente-LB-007

1. INÍCIO

O Agente-LB-007 é um projeto acadêmico de Inteligência Artificial II que utiliza o algoritmo Q-Learning, uma técnica de aprendizado por reforço, para ensinar um agente a superar obstáculos e alcançar objetivos em um ambiente de jogo.

A proposta é desenvolver um agente capaz de aprender por tentativa e erro. Durante o treinamento, ele executará ações, receberá recompensas ou penalidades e utilizará suas experiências anteriores para melhorar suas próximas decisões.

Inicialmente, será desenvolvido um jogo simples em formato de labirinto ou grade 2D. Após validar o funcionamento do algoritmo, poderão ser estudadas possibilidades de evolução para jogos com obstáculos dinâmicos e mecânicas mais complexas.
---

2. PROBLEMA

Em jogos digitais, um agente pode tomar decisões iniciais ruins, falhar várias vezes e não conseguir alcançar seu objetivo. O desafio é desenvolver um sistema capaz de aprender com essas experiências e melhorar progressivamente seu desempenho, assim como um jogador humano.

O projeto investigará se o Q-Learning permite que um agente aprenda uma estratégia mais eficiente do que uma política de ações aleatórias.

- Questão:
O treinamento com Q-Learning melhora a capacidade de um agente reduzir o número de ações necessárias e alcançar o objetivo, quando comparado a uma política aleatória?
---

3. OBJETIVO

Desenvolver e avaliar um agente baseado em Q-Learning capaz de aprender uma estratégia para alcançar objetivos em um ambiente de jogo, comparando seu desempenho antes e depois do treinamento.

Objetivos Específicos:

[] Desenvolver um ambiente de jogo com estados, ações, obstáculos e objetivos definidos.
[] Implementar uma política aleatória para servir como baseline.
[] Implementar o algoritmo Q-Learning.
[] Treinar o agente por meio de tentativas e erros.
[] Registrar as recompensas e os resultados obtidos durante os episódios.
[] Comparar o desempenho do agente treinado com o baseline.
[] Investigar situações em que o agente apresenta dificuldades ou falha.
[] Desenvolver um protótipo visual para demonstrar o treinamento e o comportamento aprendido.