@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Atualizar Editor de Video

echo.
echo ========================================
echo   Atualizando o Editor de Video...
echo ========================================
echo.

where git >nul 2>&1
if errorlevel 1 (
  echo Git nao encontrado.
  echo Instale em: https://git-scm.com/download/win
  echo Depois rode este arquivo de novo.
  pause
  exit /b 1
)

if not exist ".git" (
  echo Esta pasta ainda nao esta ligada ao GitHub.
  echo No notebook, na primeira vez rode:
  echo   git clone https://github.com/tiringabrasil44-lgtm/editor-de-video.git
  echo Veja tambem o arquivo PARA-O-MARIDO.txt
  pause
  exit /b 1
)

echo Baixando novidades do GitHub...
git pull
if errorlevel 1 (
  echo.
  echo Nao deu para atualizar. Confira a internet e tente de novo.
  pause
  exit /b 1
)

set "PY="
where py >nul 2>&1 && set "PY=py -3"
if not defined PY where python >nul 2>&1 && set "PY=python"

if defined PY (
  echo.
  echo Conferindo dependencias...
  %PY% -m pip install --user -r requirements.txt >nul 2>&1
)

echo.
echo ========================================
echo   Pronto! Atualizado com sucesso.
echo   Abra o editor com: Abrir Editor.bat
echo ========================================
echo.
pause
