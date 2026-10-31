@echo off
chcp 65001 >nul
cd /d "%~dp0"

where py >nul 2>nul && (set PY=py) || (set PY=python)

if not exist .env (
  copy .env.example .env >nul
  echo Fichier .env cree : ouvre-le et colle ta cle ANTHROPIC_API_KEY, puis relance.
  notepad .env
  pause
  exit /b
)

if not exist .installe (
  echo Installation des dependances, une seule fois...
  %PY% -m pip install -q -r requirements.txt || (echo Echec de l installation. & pause & exit /b 1)
  echo ok> .installe
)

%PY% main.py %*
echo.
pause
