# Registro inicial de apoio por IA

Data: 26/10/2026. Grupo: 01. Tema: Q-learning. Ferramenta: aplicativo Codex, OpenAI. Modelo/versão exibida: a preencher pelo integrante conforme sua interface; não inferir a versão.

## Objetivo

Organizar o trabalho a partir das orientações e preparar a primeira implementação do núcleo Q-learning no repositório informado.

## Prompt inicial

> me ajuda fazer esse seminário, o meu grupo é o Grupo 01, com o tema Q learning

Informação complementar: o grupo tinha apenas o repositório e indicou a branch feature/miguel-qlearning.

## Resposta e trabalho produzido

Proposta de labirinto, comparação com política aleatória, três experimentos e roteiro. Implementação de ambiente, Q-learning, avaliações congeladas, exportação de dados, cinco testes automatizados e documentação. Experimentos executados pelo assistente; resultados registrados sem inventar desempenho do grupo.

## Verificação efetuada pelo assistente

Cinco testes passaram; protocolo com cinco sementes e quatro configurações foi executado. A verificação automática não substitui reprodução e compreensão pelos integrantes.

## Pendências de preenchimento humano

- Decisão do grupo: aceitar, adaptar, usar parcialmente ou rejeitar.
- Alterações feitas pelos integrantes e respectivas razões.
- Execução local e evidências de validação pelo grupo.
- Erros percebidos, utilidade, confiança e compreensão.
- Reflexão sobre o que exigiu julgamento humano.

Não preencher esses campos como concluídos antes das ações reais. Transferir este registro ao modelo oficial do diário quando revisado.

## Continuação em 27/10/2026 — interface web

Contexto fornecido: histórico do projeto e solicitação de interface após os experimentos. O PR #6 já havia sido integrado à main. Foi preparada uma interface local com servidor da biblioteca padrão Python, reaproveitando `train`, `evaluate` e `rollout` sem modificar o núcleo. Inclui edição de paredes, configuração do treino, avaliação de 200 tentativas por agente, animação de trajetórias, inspeção da tabela Q, gráfico do histórico e exportação JSON. A tela descarta resultados quando o ambiente ou os parâmetros mudam.

Foram adicionadas verificações de integração HTTP, validação de entradas, reprodutibilidade e mapa sem caminho. Conferir o relato de entrega para o resultado da execução dos testes e da inspeção visual. A reprodução e a validação pelo grupo permanecem pendentes. Não foram alterados os resultados experimentais originais.

Revisão da interface a pedido de Miguel: removidos slogans, introdução, ícones e explicações da tela. Mantidos os controles e resultados em um layout simples para demonstração ao professor. As explicações foram reunidas no guia de uso. O núcleo do algoritmo e os resultados experimentais originais foram preservados.

## Exportação da base em 27/10/2026

Solicitação de Miguel: o aplicativo gerar uma tabela já organizada para Excel. Foi acrescentado registro das transições durante o treino da interface, download XLSX com colunas em português, ações por extenso, filtros e cabeçalho congelado, além de CSV com separadores adequados ao Excel em português. A planilha inclui mapa, parâmetros e dicionário das colunas da execução correspondente. O modelo visual foi preparado com Artifact Tool e o aplicativo o preenche com biblioteca padrão Python.

Onze testes automatizados passaram, incluindo conferência de que registrar as transições preserva os resultados de aprendizado, contagens por episódio, tipos das células, filtros, isolamento entre execuções e expiração de bases. O download pelo navegador produziu a planilha da execução de 1.000 episódios com 30.597 movimentos, e a aparência das duas abas foi inspecionada. Validação e reflexão pelos integrantes continuam a ser registradas pelo grupo.
