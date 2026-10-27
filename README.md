# Agente LB 007

Projeto do Grupo 01 de Inteligência Artificial II. Um agente com Q-learning aprende a percorrer um labirinto e é comparado com uma estratégia de movimentos aleatórios.

## Executar

Requer Python 3.10 ou superior. Não é necessário instalar bibliotecas adicionais.

No Windows, abra `INICIAR_INTERFACE.bat` ou execute na pasta do projeto:

```bash
python app.py --open
```

Se necessário, use `py -3` no lugar de `python`. O navegador abre em http://127.0.0.1:8000. Mantenha o terminal aberto enquanto estiver usando a interface.

## Testes e experimentos

```bash
python -m unittest discover -s tests -v
python run.py
```

Os experimentos salvam os arquivos em `results/`. O protocolo padrão usa quatro configurações e cinco sementes de treinamento; a interface executa uma configuração por vez.

## Arquivos principais

- `src/lb007/core.py`: ambiente e Q-learning.
- `app.py`: servidor local.
- `web/`: interface.
- `run.py`: experimentos.
- `tests/`: testes automatizados.
- `results/`: dados e tabelas dos experimentos.
- `docs/RESULTADOS.md`: análise dos resultados.
- `docs/DIARIO_IA.md`: registro de apoio de IA no desenvolvimento.

O desempenho é medido no mesmo mapa do treinamento. Alterar o mapa exige novo treino.
