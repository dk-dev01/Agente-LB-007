# 🤖 Agente-LB-007 — Q-Learning

> Projeto acadêmico de Inteligência Artificial II: desenvolvimento de um agente capaz de aprender a jogar por tentativa e erro utilizando Q-Learning.

---

## 📌 1. Sobre o projeto

O Agente-LB-007 é um projeto acadêmico que utiliza **Q-Learning**, uma técnica de aprendizado por reforço, para ensinar um agente a superar obstáculos e alcançar objetivos em um jogo.

A ideia é fazer com que o agente aprenda com suas próprias experiências. Durante o treinamento, ele executa ações, recebe recompensas ou penalidades e utiliza os resultados anteriores para melhorar suas próximas decisões.

Inicialmente, será desenvolvido um jogo simples no formato de labirinto 2D. Após validar o funcionamento do algoritmo, poderemos investigar sua aplicação em jogos mais complexos, como Flappy Bird e Subway Surfers.

## 🎯 2. Problema de pesquisa

Em jogos digitais, um agente pode tomar decisões ruins, colidir com obstáculos e falhar diversas vezes antes de encontrar uma estratégia eficiente.

O desafio é desenvolver um sistema capaz de aprender com essas experiências e melhorar progressivamente seu desempenho.

**Pergunta de pesquisa:**

O treinamento com Q-Learning permite que um agente alcance objetivos com maior eficiência do que uma estratégia baseada em ações aleatórias?

## 🚀 3. Objetivos

### Objetivo geral

Desenvolver e avaliar um agente baseado em Q-Learning capaz de aprender a alcançar objetivos em um ambiente de jogo, comparando seu desempenho com uma estratégia aleatória.

### Objetivos específicos

- [X] Desenvolver um ambiente de jogo com estados, ações, obstáculos e objetivos definidos.
- [X] Implementar uma estratégia de ações aleatórias (baseline).
- [X] Implementar o algoritmo Q-Learning.
- [X] Treinar o agente por meio de tentativa e erro.
- [X] Registrar as recompensas e os resultados de cada episódio.
- [X] Comparar o desempenho do agente treinado com o baseline.
- [X] Analisar os erros, as falhas e as dificuldades encontradas.
- [X] Desenvolver um protótipo visual para demonstrar o comportamento aprendido.

## 🧠 4. Como o agente aprende?

O Q-Learning permite que o agente aprenda quais ações são mais vantajosas em cada situação.

O funcionamento básico será:

1. **Observar:** identificar a posição e a situação atual do jogo.
2. **Agir:** escolher um movimento, como cima, baixo, esquerda ou direita.
3. **Receber feedback:** ganhar recompensas ou sofrer penalidades.
4. **Aprender:** atualizar os valores da tabela Q com base na experiência.
5. **Repetir:** executar novos episódios para melhorar as decisões.

O objetivo é que, após o treinamento, o agente consiga encontrar estratégias melhores e alcançar o objetivo com mais eficiência.

## 🎮 5. Ambiente inicial

A primeira versão será um labirinto 2D com:

- Posição inicial do agente.
- Objetivo a ser alcançado.
- Obstáculos que devem ser evitados.
- Movimentos permitidos.
- Sistema de recompensas e penalidades.

O ambiente será simples e controlado para facilitar a implementação, os testes e a avaliação do aprendizado.

## 📊 6. Avaliação dos resultados

Para verificar se o treinamento realmente melhora o desempenho do agente, serão utilizadas as seguintes métricas:

- **Taxa de sucesso:** percentual de episódios em que o objetivo foi alcançado.
- **Quantidade de passos:** número de movimentos necessários para concluir o percurso.
- **Recompensa acumulada:** soma das recompensas obtidas durante cada episódio.
- **Taxa de falhas:** percentual de episódios que terminam sem alcançar o objetivo.

Os resultados do agente treinado serão comparados com os resultados da estratégia aleatória.

## 📋 7. Checklist do projeto

### Checkpoint 1 — CONSTRUIR | 27/10/2026

#### Planejamento
- [x] Criar o repositório no GitHub.
- [x] Convidar os integrantes do grupo.
- [X] Definir o escopo inicial do jogo.
- [X] Distribuir as responsabilidades entre os integrantes.
- [ ] Selecionar referências científicas e técnicas.

#### Ambiente e implementação
- [X] Criar o ambiente do jogo.
- [X] Definir os estados e as ações do agente.
- [X] Definir as recompensas e penalidades.
- [X] Implementar a estratégia aleatória (baseline).
- [X] Implementar o Q-Learning.
- [X] Executar os primeiros testes.
- [ ] Garantir que o pipeline funcione de ponta a ponta.

#### Análise exploratória (EDA)
- [ ] Registrar os resultados das simulações.
- [X] Analisar a taxa de sucesso e a quantidade de passos.
- [ ] Identificar pelo menos três descobertas relevantes.
- [ ] Registrar as métricas iniciais.
- [ ] Criar gráficos ou tabelas, quando aplicável.

#### Documentação
- [X] Atualizar este README.
- [ ] Selecionar pelo menos cinco referências relevantes.
- [ ] Preparar o rascunho do resumo expandido.
- [X] Preencher o checklist oficial do professor.
- [X] Iniciar o Diário de IA.

#### Revisão final
- [ ] Integrar as alterações dos integrantes.
- [ ] Testar o projeto completo.
- [X] Conferir os arquivos no GitHub.
- [ ] Preparar a demonstração para o professor.

### Checkpoint 2 — INVESTIGAR | 03/11/2026

- [ ] Realizar pelo menos três experimentos controlados.
- [ ] Registrar uma hipótese para cada experimento.
- [ ] Comparar os resultados com o baseline.
- [ ] Analisar as métricas de desempenho.
- [ ] Investigar pelo menos três erros, limitações ou situações inesperadas.
- [ ] Registrar as conclusões e limitações encontradas.

### Pré-banca — VALIDAR | 10/11/2026

- [ ] Concluir a implementação principal.
- [ ] Validar o funcionamento do algoritmo.
- [ ] Testar o pipeline completo.
- [ ] Preparar uma demonstração reproduzível.
- [ ] Organizar os resultados dos experimentos.
- [ ] Preparar a apresentação do projeto.

### Entrega final | 17/11/2026

- [ ] Finalizar o código e as instruções de execução.
- [ ] Finalizar o protótipo web.
- [ ] Finalizar o resumo expandido.
- [ ] Preparar o folder de divulgação científica.
- [ ] Preparar o carrossel ou a postagem para Instagram.
- [ ] Produzir o vídeo de apresentação de 1 a 3 minutos.
- [ ] Finalizar o Model Card.
- [ ] Organizar a ficha de experimentos.
- [ ] Revisar o repositório e os materiais finais.

**Prazo informado pelo professor:** 17/11/2026, até as 17h.

## 👥 8. Organização da equipe

O projeto será desenvolvido por cinco integrantes, com responsabilidades distribuídas entre as seguintes áreas:

- **Coordenação e integração (Derick):** organização do projeto, acompanhamento do cronograma e integração do código.
- **Ambiente de jogo (Miguel):** desenvolvimento do labirinto, dos estados, das ações e das regras.
- **Algoritmo (Luiz Antonio):** implementação e treinamento do Q-Learning.
- **Baseline e avaliação (Andre Ricardo)):** implementação da estratégia aleatória e cálculo das métricas.
- **Análise e documentação (Diego Gabriel):** referências, análise exploratória, documentação e registros dos experimentos.

As responsabilidades específicas serão definidas e registradas pelo grupo.

## 🛠️ 9. Tecnologias

- Python.
- Git e GitHub.
- GitHub Codespaces.
- Bibliotecas de análise e visualização de dados, conforme a necessidade.
- ChatGPT, Claude e Gemini.

## 📚 10. Referências iniciais

1. WATKINS, C. J. C. H.; DAYAN, P. Q-learning. *Machine Learning*, v. 8, p. 279–292, 1992.
2. SUTTON, R. S.; BARTO, A. G. *Reinforcement Learning: An Introduction*. 2. ed. MIT Press, 2018.
3. KAELBLING, L. P.; LITTMAN, M. L.; MOORE, A. W. Reinforcement Learning: A Survey. *Journal of Artificial Intelligence Research*, v. 4, p. 237–285, 1996.
4. WATKINS, C. J. C. H. *Learning from Delayed Rewards*. Tese de doutorado, King's College, Cambridge, 1989.
5. MNIH, V. et al. Human-level control through deep reinforcement learning. *Nature*, v. 518, p. 529–533, 2015.

As referências deverão ser consultadas e utilizadas na fundamentação teórica do projeto.

---

**Agente-LB-007 — Aprendendo com cada tentativa.**
