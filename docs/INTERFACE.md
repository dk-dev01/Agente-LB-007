# Guia de uso para Miguel

Requer Python 3.10 ou superior. Não há bibliotecas Python para instalar.

## Abrir

No Windows, dê dois cliques em `INICIAR_INTERFACE.bat`. Ele procura o Python incluído no Codex e, em seguida, `py` ou `python`, sem caminhos com nome de usuário fixo. Ou, no terminal da pasta do projeto:

```bash
python app.py --open
```

Se o comando do seu computador for `py`, use `py -3 app.py --open`. O navegador abre em http://127.0.0.1:8000. Deixe o terminal aberto; Ctrl+C encerra. Se a porta estiver ocupada, use `python app.py --port 8001 --open`. Não abra `web/index.html` diretamente: o treino precisa do servidor Python.

## Roteiro de uma demonstração de 5 minutos

1. Mostre início, paredes e saída. O agente pode mover para cima, direita, baixo e esquerda. Colisão: −3; saída: +20; passo comum: −1.
2. Clique em **Treinar**. O servidor executa o mesmo `train` dos experimentos, usando os valores selecionados. O navegador aguarda e exibe o histórico depois da conclusão; não é uma transmissão de treino em tempo real.
3. Compare a taxa de sucesso em **200 tentativas por agente**, com tabela congelada e sementes de avaliação iguais para ambos. O treino usa uma única semente por execução desta interface.
4. Clique em **Agente aleatório** e depois **Agente treinado**. As animações mostram uma tentativa de cada política, não todas as 200. Pausa e velocidade controlam a reprodução. No mapa, A representa o agente, I o início e F a saída.
5. Selecione uma casa e consulte seus valores Q. Ative **Política** para visualizar ações com maior Q: C (cima), D (direita), B (baixo) e E (esquerda). Em empate, mais de uma letra pode aparecer. A política usa desempate aleatório reproduzível.
6. Altere alpha, epsilon, recompensa ou uma parede e treine novamente. A interface descarta os resultados anteriores, evitando usar uma tabela aprendida em outro ambiente. Início e saída permanecem fixos. É possível criar um mapa sem saída; a tela informa isso em uma linha. Ao treinar, o modo de edição é encerrado.
7. Clique em **Exportar JSON** para registrar mapa, parâmetros, semente, avaliações, trajetórias, histórico e tabela Q.
8. Clique em **Baixar base Excel** para receber um `.xlsx` com todos os movimentos do treinamento atual, cabeçalhos em português, ações por extenso, números em células numéricas, filtros e cabeçalho fixo. A aba **Execução** registra mapa, parâmetros e descrição das colunas. **Baixar base CSV** oferece os mesmos movimentos com ponto e vírgula, decimais com vírgula e UTF-8 com BOM, para o Excel em português. As posições `(linha, coluna)` começam em zero, como no código original.

A base é registrada durante o próprio treino, sem executar outro treinamento ao baixar. O JSON contém o identificador e a contagem da base; os registros completos são baixados pelos novos botões. A cada mudança de mapa ou parâmetros os botões são desabilitados até um novo treino. As três bases mais recentes ficam em armazenamento temporário da sessão; baixe antes de encerrar o servidor. Downloads de bases expiradas mostram um aviso e exigem novo treinamento. As exportações não alteram os arquivos de `results/`.

## O que cada parâmetro significa

- **Episódios:** quantidade de tentativas de treino. Cada uma começa no início do mapa e termina na saída ou no limite de passos.
- **Alpha:** quanto uma experiência muda o valor guardado na tabela Q. Um valor maior dá mais peso à atualização recente.
- **Gamma:** peso das recompensas futuras no cálculo. Quanto mais próximo de 1, maior a importância do que pode acontecer adiante.
- **Epsilon inicial e final:** chance de escolher uma ação aleatória durante o treinamento. A variação entre os dois valores é linear; valores iguais mantêm a exploração constante.
- **Recompensa por passo:** penalidade de um movimento comum. A colisão continua valendo -3 e a chegada à saída, +20.
- **Semente:** controla as escolhas aleatórias para permitir repetir a execução com as mesmas condições.

## Como explicar as tabelas e o gráfico

**Sucesso** é a porcentagem das 200 avaliações em que o agente chegou à saída. **Passos** considera somente as tentativas com sucesso. **Colisões** considera todas as tentativas. Se não houver sucesso, não há média de passos até a saída.

A **tabela Q** mostra quatro estimativas para a casa selecionada. Valores maiores indicam ações preferidas. O destaque pode aparecer em mais de uma ação se houver empate. Na saída, os valores ficam em zero porque o episódio já terminou.

O **gráfico de treinamento** agrupa até 50 episódios por ponto e mostra a porcentagem de sucesso naquele bloco. Ele inclui as escolhas exploratórias do treino. A tabela de resultados usa uma avaliação separada, com a tabela Q congelada.

O **menor caminho** é calculado por busca em largura para comparação. Esse cálculo não é usado pelo agente para aprender ou escolher movimentos.

Essas explicações ficam neste guia; a interface mostra apenas os controles, os dados e as mensagens necessárias para a execução.

## Limites e resultados

Os valores mostrados são calculados no servidor, não copiados de `results/`. Alterar uma configuração não garante diferença no desempenho final. Um gráfico de sucesso durante treino inclui exploração; a avaliação final não usa exploração deliberada e não atualiza a tabela. Recompensas acumuladas com penalidades diferentes não são diretamente comparáveis.

O treino é processado em lote. Aguarde a resposta; há limite de 5.000 episódios e 200 passos na API (a tela usa 100 passos). Mapas têm de 2 a 12 linhas e colunas. O servidor aceita uma execução de treino por vez e escuta somente neste computador.

O layout usa fontes do sistema e funciona sem internet. A interface não altera os arquivos dos experimentos em `results/`.

## Atualizar sua branch com estes arquivos

Na cópia **já clonada** do repositório, confirme `git status` e a branch antes de copiar. Copie os arquivos desta entrega para a raiz do repositório, preservando a pasta `.git` da sua cópia. Não coloque um projeto dentro de outro.

```bash
git switch feature/miguel-qlearning
git pull --ff-only origin feature/miguel-qlearning
```

Como o PR #6 já foi integrado, traga também a `main` se ainda faltar:

```bash
git fetch origin
git merge origin/main
```

Depois de copiar e testar:

```bash
py -3 -m unittest discover -s tests -v
git add app.py INICIAR_INTERFACE.bat web tests/test_app.py README.md docs/INTERFACE.md docs/DIARIO_IA.md
git diff --cached --stat
git commit -m "Adiciona interface web para demonstrar Q-learning"
git push origin feature/miguel-qlearning
```

Como o PR #6 está fechado por integração, abra **um novo PR** de `feature/miguel-qlearning` para `main` para estas mudanças. O push sozinho não reabre o PR antigo. Se o Git informar arquivos locais modificados antes de atualizar, preserve-os e resolva a situação antes de copiar ou mesclar.
