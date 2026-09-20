@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Gerar EditorDeVideo.exe

set "PY=py -3"
where py >nul 2>&1 || set "PY=python"

echo Instalando PyInstaller se precisar...
%PY% -m pip install --user pyinstaller tkinterdnd2 opencv-python-headless pillow >nul

echo.
echo Gerando o programa (.exe)... isso pode demorar alguns minutos.
echo.

%PY% -m PyInstaller --noconfirm --clean --windowed --onedir ^
  --name "EditorDeVideo" ^
  --collect-all tkinterdnd2 ^
  --collect-all cv2 ^
  --hidden-import PIL ^
  --hidden-import setup_deps ^
  editor.py

if errorlevel 1 (
  echo Falha no build.
  pause
  exit /b 1
)

echo.
echo Pronto: pasta dist\EditorDeVideo\
echo.
