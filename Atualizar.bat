@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Atualizar Editor de Video

set "REPO_URL=https://github.com/tiringabrasil44-lgtm/editor-de-video.git"
set "ZIP_URL=https://github.com/tiringabrasil44-lgtm/editor-de-video/archive/refs/heads/main.zip"

echo.
echo ========================================
echo   Atualizando o Editor de Video...
echo   (automatico - nao precisa digitar nada)
echo ========================================
echo.

where git >nul 2>&1
if errorlevel 1 goto :UPDATE_ZIP

if not exist ".git" (
  echo Primeira vez nesta pasta: conectando no GitHub sozinho...
  git init -b main >nul 2>&1
  git remote remove origin >nul 2>&1
  git remote add origin "%REPO_URL%"
  if errorlevel 1 (
    echo Falhou ao conectar. Tentando pelo ZIP...
    goto :UPDATE_ZIP
  )
)

echo Baixando novidades...
git fetch origin main
if errorlevel 1 (
  echo Git fetch falhou. Tentando pelo ZIP...
  goto :UPDATE_ZIP
)

git checkout -f -B main origin/main
if errorlevel 1 (
  echo Git checkout falhou. Tentando pelo ZIP...
  goto :UPDATE_ZIP
)

goto :DEPS

:UPDATE_ZIP
echo.
echo Baixando atualizacao direto do GitHub (ZIP)...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference='Stop';" ^
  "$zip=Join-Path $env:TEMP 'editor-de-video-update.zip';" ^
  "$out=Join-Path $env:TEMP 'editor-de-video-update';" ^
  "if (Test-Path $out) { Remove-Item $out -Recurse -Force };" ^
  "Invoke-WebRequest -Uri '%ZIP_URL%' -OutFile $zip;" ^
  "Expand-Archive -Path $zip -DestinationPath $out -Force;" ^
  "$src=Get-ChildItem $out -Directory | Select-Object -First 1;" ^
  "Copy-Item -Path (Join-Path $src.FullName '*') -Destination '%~dp0' -Recurse -Force;" ^
  "Remove-Item $zip -Force -ErrorAction SilentlyContinue;" ^
  "Remove-Item $out -Recurse -Force -ErrorAction SilentlyContinue;"
if errorlevel 1 (
  echo.
  echo Nao deu para atualizar. Confira a internet e tente de novo.
  pause
  exit /b 1
)

:DEPS
set "PY="
where py >nul 2>&1 && set "PY=py -3"
if not defined PY where python >nul 2>&1 && set "PY=python"

if not defined PY (
  echo.
  echo Python ainda nao esta instalado neste PC.
  echo Instale UMA vez: https://www.python.org/downloads/
  echo Marque a caixinha: Add python.exe to PATH
  echo Depois rode Atualizar.bat de novo.
  pause
  exit /b 1
)

echo.
echo Instalando FFmpeg e libs automaticamente...
%PY% "setup_deps.py"

echo.
echo ========================================
echo   Pronto! Atualizado.
echo   Agora abra: Abrir Editor.bat
echo ========================================
echo.
pause
