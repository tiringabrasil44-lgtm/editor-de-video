#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Baixa FFmpeg automaticamente na pasta do programa."""

from __future__ import annotations

import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

FFMPEG_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def ffmpeg_bin_dir() -> Path:
    return app_dir() / "ffmpeg" / "bin"


def local_ffmpeg_paths() -> tuple[Path, Path, Path]:
    bin_dir = ffmpeg_bin_dir()
    return bin_dir / "ffmpeg.exe", bin_dir / "ffprobe.exe", bin_dir / "ffplay.exe"


def local_ffmpeg_ok() -> bool:
    ffmpeg, ffprobe, _ = local_ffmpeg_paths()
    return ffmpeg.is_file() and ffprobe.is_file()


def system_ffmpeg_ok() -> bool:
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def ensure_ffmpeg(log=print) -> bool:
    if local_ffmpeg_ok() or system_ffmpeg_ok():
        log("FFmpeg: OK")
        return True

    log("Baixando FFmpeg automaticamente (1–2 min, só na 1ª vez)...")
    ffmpeg_dir = app_dir() / "ffmpeg"
    bin_dir = ffmpeg_bin_dir()
    ffmpeg_dir.mkdir(parents=True, exist_ok=True)
    zip_path = ffmpeg_dir / "ffmpeg-essentials.zip"

    try:
        urllib.request.urlretrieve(FFMPEG_URL, zip_path)
    except Exception as exc:
        log(f"Falha ao baixar FFmpeg: {exc}")
        return False

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            wanted = ("ffmpeg.exe", "ffprobe.exe", "ffplay.exe")
            bin_dir.mkdir(parents=True, exist_ok=True)
            for name in zf.namelist():
                base = Path(name).name.lower()
                if base in wanted and not name.endswith("/"):
                    target = bin_dir / Path(name).name
                    with zf.open(name) as src, open(target, "wb") as dst:
                        shutil.copyfileobj(src, dst)
        zip_path.unlink(missing_ok=True)
    except Exception as exc:
        log(f"Falha ao extrair FFmpeg: {exc}")
        return False

    if local_ffmpeg_ok():
        log("FFmpeg instalado.")
        return True
    log("Download ok, mas ffmpeg.exe não apareceu.")
    return False


def main() -> int:
    ok = ensure_ffmpeg()
    # Mantém compatibilidade com o .bat antigo (libs Python)
    if not getattr(sys, "frozen", False):
        try:
            import cv2  # noqa: F401
            import PIL  # noqa: F401
        except ImportError:
            import subprocess

            subprocess.check_call(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "--user",
                    "tkinterdnd2",
                    "opencv-python-headless",
                    "pillow",
                ]
            )
        try:
            import tkinterdnd2  # noqa: F401
        except ImportError:
            import subprocess

            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "--user", "tkinterdnd2"]
            )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
