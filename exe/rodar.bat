@echo off
chcp 65001 >nul
cd /d "%~dp0.."
if not exist "app.py" (
    echo Coloque este arquivo na pasta exe, dentro do projeto Agente-LB-007.
    pause
    exit /b 1
)
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
echo Python 3.10 ou superior nao encontrado. Instale o Python e tente novamente.
:fim
pause
