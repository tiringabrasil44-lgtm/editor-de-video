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
  echo Instale uma vez: https://git-scm.com/download/win
  echo Depois rode este arquivo de novo.
  pause
  exit /b 1
)

if not exist ".git" (
  echo Esta pasta ainda nao esta ligada ao GitHub.
  echo Na primeira vez no notebook rode:
  echo   git clone https://github.com/tiringabrasil44-lgtm/editor-de-video.git
  echo Veja tambem PARA-O-MARIDO.txt
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

if not defined PY (
  echo.
  echo Python ainda nao esta instalado neste PC.
  echo Instale uma vez: https://www.python.org/downloads/
  echo Marque: Add python.exe to PATH
  pause
  exit /b 1
)

echo.
echo Instalando FFmpeg e libs automaticamente (sem Path manual)...
%PY% "setup_deps.py"

echo.
echo ========================================
echo   Pronto! Atualizado.
echo   Agora abra: Abrir Editor.bat
echo ========================================
echo.
pause
