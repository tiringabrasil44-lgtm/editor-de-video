@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Editor de Video

set "PY="
where py >nul 2>&1 && set "PY=py -3"
if not defined PY where python >nul 2>&1 && set "PY=python"

if not defined PY (
  echo.
  echo Python nao encontrado.
  echo No notebook, instale so o Python uma vez:
  echo   https://www.python.org/downloads/
  echo Marque a caixinha: Add python.exe to PATH
  echo Depois abra de novo este arquivo.
  echo.
  pause
  exit /b 1
)

echo Preparando dependencias (FFmpeg e libs)... isso e automatico.
%PY% "setup_deps.py"
if errorlevel 1 (
  echo.
  echo Se falhou o download, confira a internet e tente de novo.
  pause
)

%PY% "editor.py"
if errorlevel 1 pause
