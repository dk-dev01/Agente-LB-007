# Agente visual de Q-learning para Level Devil (v2.1)

Observa a tela com `mss`, acha personagem e porta **por cor** (sem calibração com cliques) e envia teclas com `pyautogui`.

## Usar
1. `py -m pip install -r requirements.txt`
2. Abra o jogo e deixe a página visível. Dê dois cliques em `iniciar_agente.vbs`.
3. Selecione só a área do jogo (Enter).
4. Inicie a fase. Quando ele achar personagem e porta, toca um bip e abre "Confirmar": confira as caixas e aperte Enter.
5. **F8** para parar. Logs em `agent.log`.

Depois disso ele roda sozinho: na tela **PRESS ANY KEY** aperta uma tecla, e ao passar pela porta reconhece a
fase nova e continua, sem reiniciar o programa.

## O que é salvo
Um arquivo por fase em `profiles/nivel_XXXXXXXX.json`, reconhecido pela forma do cenário (a mesma fase
retoma o treino mesmo depois de fechar o programa). Cada arquivo guarda tabela Q, contagem de tentativas por
estado/ação, ε, episódios e vitórias. Gravação a cada episódio, a cada 100 passos e ao parar (F8), de forma atômica.
`LD_PROFILE=nome` força um único perfil; `LD_DEBUG=1` mostra uma janela com a detecção e os sensores.

## Como funciona
- **Visão** (`vision.py`): personagem = silhueta preta mais alta que larga; porta = retângulo cinza neutro;
  tela de morte = bloco amarelo largo no topo; chão = cor sob os pés; fase = forma do espaço laranja.
- **Aprendizado** (`brain.py`): Q-learning com 6 ações; pulo = **W**, combinável com A/D ao mesmo tempo (W+D, W+A), inclusive no ar. A/D ficam segurados entre os passos, replay reverso no fim do episódio,
  bônus de curiosidade e desempate aleatório.
- **Fim de episódio**: morte (tela de morte, sumiço ou reaparição no início), vitória (porta + cenário mudou) e travado (8 s sem progresso).

## Testes
- `python tests/test_vision.py`: valida a visão nas capturas reais (`tests/*.png`).
- `python sim_test.py`: agente completo contra um platformer sintético com tela de morte, armadilhas
  invisíveis, duas fases e persistência.

## Limites
A visão assume as cores do jogo (personagem preto, porta cinza neutro). Fases com outra paleta ou porta
diferente exigem ajuste em `vision.py`. Q-learning tabular não garante vencer fases que mudam as regras.
