@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Iniciando a interface do Agente LB 007...
py -3 -c "import sys; sys.exit(sys.version_info < (3, 10))" >nul 2>&1
if not errorlevel 1 (
    py -3 app.py --open
    goto fim
)
python -c "import sys; sys.exit(sys.version_info < (3, 10))" >nul 2>&1
if not errorlevel 1 (
    python app.py --open
    goto fim
)
echo Python 3.10 ou superior nao encontrado neste computador.
echo Instale o Python de python.org ou solicite a instalacao ao responsavel pelo computador.
echo Selecione a opcao Add Python to PATH durante a instalacao.
:fim
pause
