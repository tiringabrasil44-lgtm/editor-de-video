#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Baixa FFmpeg e dependências Python automaticamente na pasta do app."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FFMPEG_DIR = ROOT / "ffmpeg"
FFMPEG_BIN = FFMPEG_DIR / "bin"
FFMPEG_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"


def local_ffmpeg_ok() -> bool:
    return (FFMPEG_BIN / "ffmpeg.exe").is_file() and (FFMPEG_BIN / "ffprobe.exe").is_file()


def system_ffmpeg_ok() -> bool:
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def ensure_ffmpeg() -> bool:
    if local_ffmpeg_ok() or system_ffmpeg_ok():
        print("FFmpeg: OK")
        return True

    print("FFmpeg nao encontrado. Baixando automaticamente (pode levar 1-2 min)...")
    FFMPEG_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = FFMPEG_DIR / "ffmpeg-essentials.zip"

    try:
        urllib.request.urlretrieve(FFMPEG_URL, zip_path)
    except Exception as exc:
        print(f"Falha ao baixar FFmpeg: {exc}")
        print("Confira a internet e rode Atualizar.bat de novo.")
        return False

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
            # Procura ffmpeg.exe / ffprobe.exe / ffplay.exe dentro do zip
            wanted = ("ffmpeg.exe", "ffprobe.exe", "ffplay.exe")
            FFMPEG_BIN.mkdir(parents=True, exist_ok=True)
            for name in names:
                base = Path(name).name.lower()
                if base in wanted and not name.endswith("/"):
                    target = FFMPEG_BIN / Path(name).name
                    with zf.open(name) as src, open(target, "wb") as dst:
                        shutil.copyfileobj(src, dst)
        zip_path.unlink(missing_ok=True)
    except Exception as exc:
        print(f"Falha ao extrair FFmpeg: {exc}")
        return False

    if local_ffmpeg_ok():
        print("FFmpeg: instalado na pasta do programa.")
        return True

    print("Download concluiu, mas ffmpeg.exe nao foi encontrado no pacote.")
    return False


def ensure_python_packages() -> None:
    packages = ["tkinterdnd2", "opencv-python-headless", "pillow"]
    for pkg in packages:
        mod = {
            "tkinterdnd2": "tkinterdnd2",
            "opencv-python-headless": "cv2",
            "pillow": "PIL",
        }[pkg]
        try:
            __import__(mod)
            print(f"Python ({mod}): OK")
        except ImportError:
            print(f"Instalando {pkg}...")
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "--user", pkg],
                stdout=subprocess.DEVNULL,
            )


def main() -> int:
    os.chdir(ROOT)
    print("Preparando o Editor de Video...")
    print()
    try:
        ensure_python_packages()
    except Exception as exc:
        print(f"Aviso nas libs Python: {exc}")
    print()
    ok = ensure_ffmpeg()
    print()
    if ok:
        print("Tudo pronto.")
        return 0
    print("Ainda falta o FFmpeg. Rode Atualizar.bat com internet.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
