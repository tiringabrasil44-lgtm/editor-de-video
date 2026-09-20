@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Editor de Video

set "PY="
where py >nul 2>&1 && set "PY=py -3"
if not defined PY where python >nul 2>&1 && set "PY=python"

if not defined PY (
  echo Python nao encontrado.
  echo Instale em: https://www.python.org/downloads/
  echo Marque a opcao "Add Python to PATH" na instalacao.
  pause
  exit /b 1
)

%PY% -c "import tkinterdnd2" >nul 2>&1
if errorlevel 1 %PY% -m pip install --user tkinterdnd2

%PY% -c "import cv2, PIL" >nul 2>&1
if errorlevel 1 %PY% -m pip install --user opencv-python-headless pillow

%PY% "editor.py"
if errorlevel 1 pause
