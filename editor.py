#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Editor de vídeo simples: prévia, cortar e alterar velocidade."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import cv2
from PIL import Image, ImageTk

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD

    BaseTk = TkinterDnD.Tk
    DND_AVAILABLE = True
except ImportError:
    BaseTk = tk.Tk
    DND_AVAILABLE = False
    DND_FILES = "DND_Files"


def find_ffmpeg() -> tuple[str | None, str | None, str | None]:
    # 1) Pasta local do app (baixada pelo Atualizar / Abrir Editor)
    local_bin = Path(__file__).resolve().parent / "ffmpeg" / "bin"
    local_ffmpeg = local_bin / "ffmpeg.exe"
    local_ffprobe = local_bin / "ffprobe.exe"
    local_ffplay = local_bin / "ffplay.exe"
    if local_ffmpeg.is_file() and local_ffprobe.is_file():
        return (
            str(local_ffmpeg),
            str(local_ffprobe),
            str(local_ffplay) if local_ffplay.is_file() else None,
        )

    # 2) PATH do sistema
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    ffplay = shutil.which("ffplay")
    if ffmpeg and ffprobe:
        if not ffplay:
            candidate = Path(ffmpeg).with_name("ffplay.exe")
            if candidate.exists():
                ffplay = str(candidate)
        return ffmpeg, ffprobe, ffplay

    # 3) Instalação via winget
    winget_roots = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages",
    ]
    for root in winget_roots:
        if not root.exists():
            continue
        for exe in root.rglob("ffmpeg.exe"):
            probe = exe.with_name("ffprobe.exe")
            play = exe.with_name("ffplay.exe")
            if probe.exists():
                return str(exe), str(probe), str(play) if play.exists() else None
    return None, None, None


FFMPEG, FFPROBE, FFPLAY = find_ffmpeg()


def probe_duration(path: str) -> float:
    if not FFPROBE:
        raise RuntimeError("ffprobe não encontrado")
    cmd = [
        FFPROBE,
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_format",
        path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)
    return float(data["format"]["duration"])


def format_time(seconds: float) -> str:
    seconds = max(0.0, seconds)
    m, s = divmod(seconds, 60)
    h, m = divmod(int(m), 60)
    if h:
        return f"{h:d}:{m:02d}:{s:06.3f}"
    return f"{int(m):d}:{s:06.3f}"


def parse_time(text: str) -> float:
    text = text.strip().replace(",", ".")
    if not text:
        raise ValueError("tempo vazio")
    parts = text.split(":")
    if len(parts) == 1:
        return float(parts[0])
    if len(parts) == 2:
        return int(parts[0]) * 60 + float(parts[1])
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    raise ValueError("use s, m:s ou h:m:s")


def atempo_chain(speed: float) -> list[str]:
    filters: list[str] = []
    remaining = speed
    while remaining > 2.0 + 1e-9:
        filters.append("atempo=2.0")
        remaining /= 2.0
    while remaining < 0.5 - 1e-9:
        filters.append("atempo=0.5")
        remaining /= 0.5
    filters.append(f"atempo={remaining:.6f}")
    return filters


class EditorApp(BaseTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Editor de Vídeo")
        self.geometry("720x820")
        self.minsize(640, 700)
        self.configure(bg="#f4f4f4")

        self.video_path: str | None = None
        self.duration = 0.0
        self._busy = False

        self.cap: cv2.VideoCapture | None = None
        self._fps = 25.0
        self._playing = False
        self._paused = False
        self._play_token = 0
        self._photo: ImageTk.PhotoImage | None = None
        self._last_frame = None
        self._ffplay_proc: subprocess.Popen | None = None
        self._preview_w = 680
        self._preview_h = 360

        self._build_ui()
        self._enable_drag_drop()
        self._check_tools()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self) -> None:
        pad = {"padx": 16, "pady": 4}

        title = tk.Label(
            self,
            text="Editor de Vídeo",
            font=("Segoe UI", 18, "bold"),
            bg="#f4f4f4",
            fg="#1a1a1a",
        )
        title.pack(anchor="w", padx=16, pady=(12, 2))

        subtitle = tk.Label(
            self,
            text="Arraste o vídeo, ajuste corte/velocidade e teste na prévia antes de salvar.",
            font=("Segoe UI", 10),
            bg="#f4f4f4",
            fg="#555555",
        )
        subtitle.pack(anchor="w", padx=16, pady=(0, 6))

        self.drop_zone = tk.Label(
            self,
            text="Arraste e solte o vídeo aqui",
            font=("Segoe UI", 11),
            bg="#e8eef5",
            fg="#2a4a6a",
            relief="ridge",
            bd=2,
            height=2,
            cursor="hand2",
        )
        self.drop_zone.pack(fill="x", padx=16, pady=(0, 6))
        self.drop_zone.bind("<Button-1>", lambda _e: self.choose_video())

        file_frame = ttk.Frame(self)
        file_frame.pack(fill="x", **pad)
        ttk.Button(file_frame, text="Escolher vídeo…", command=self.choose_video).pack(
            side="left"
        )
        self.file_label = ttk.Label(file_frame, text="Nenhum arquivo selecionado")
        self.file_label.pack(side="left", padx=10)

        preview_box = ttk.LabelFrame(self, text="Prévia", padding=8)
        preview_box.pack(fill="both", expand=True, padx=16, pady=4)

        self.preview_label = tk.Label(
            preview_box,
            text="O vídeo aparece aqui",
            bg="#111111",
            fg="#aaaaaa",
            font=("Segoe UI", 12),
            width=80,
            height=18,
        )
        self.preview_label.pack(fill="both", expand=True)
        self.preview_label.bind("<Configure>", self._on_preview_resize)

        transport = ttk.Frame(preview_box)
        transport.pack(fill="x", pady=(8, 0))
        self.play_btn = ttk.Button(transport, text="▶ Play", command=self.play_preview)
        self.play_btn.pack(side="left")
        self.pause_btn = ttk.Button(transport, text="⏸ Pause", command=self.pause_preview)
        self.pause_btn.pack(side="left", padx=6)
        self.stop_btn = ttk.Button(transport, text="⏹ Parar", command=self.stop_preview)
        self.stop_btn.pack(side="left")
        self.audio_btn = ttk.Button(
            transport, text="🔊 Prévia com áudio", command=self.preview_with_audio
        )
        self.audio_btn.pack(side="left", padx=10)
        self.preview_time = ttk.Label(transport, text="0:00 / 0:00")
        self.preview_time.pack(side="right")

        info = ttk.Frame(self)
        info.pack(fill="x", **pad)
        self.duration_label = ttk.Label(info, text="Duração: —")
        self.duration_label.pack(anchor="w")

        cut = ttk.LabelFrame(self, text="Cortar", padding=8)
        cut.pack(fill="x", **pad)
        row1 = ttk.Frame(cut)
        row1.pack(fill="x", pady=2)
        ttk.Label(row1, text="Início (m:s):").pack(side="left")
        self.start_var = tk.StringVar(value="0:00.000")
        ttk.Entry(row1, textvariable=self.start_var, width=14).pack(side="left", padx=8)
        ttk.Button(row1, text="Ir ao início", command=self.seek_to_start).pack(side="left")

        row2 = ttk.Frame(cut)
        row2.pack(fill="x", pady=2)
        ttk.Label(row2, text="Fim (m:s):").pack(side="left")
        self.end_var = tk.StringVar(value="0:00.000")
        ttk.Entry(row2, textvariable=self.end_var, width=14).pack(side="left", padx=8)

        speed = ttk.LabelFrame(self, text="Velocidade", padding=8)
        speed.pack(fill="x", **pad)
        row3 = ttk.Frame(speed)
        row3.pack(fill="x")
        ttk.Label(row3, text="Velocidade:").pack(side="left")
        self.speed_var = tk.DoubleVar(value=1.0)
        self.speed_scale = ttk.Scale(
            row3,
            from_=0.25,
            to=3.0,
            orient="horizontal",
            variable=self.speed_var,
            command=self._on_speed_change,
        )
        self.speed_scale.pack(side="left", fill="x", expand=True, padx=8)
        self.speed_label = ttk.Label(row3, text="1.00x", width=6)
        self.speed_label.pack(side="left")

        actions = ttk.Frame(self)
        actions.pack(fill="x", **pad)
        self.export_btn = ttk.Button(
            actions, text="Salvar vídeo editado…", command=self.export_video
        )
        self.export_btn.pack(side="left")
        ttk.Button(actions, text="Abrir pasta deste app", command=self.open_app_folder).pack(
            side="left", padx=8
        )

        self.status = ttk.Label(self, text="Pronto.", foreground="#333333")
        self.status.pack(anchor="w", padx=16, pady=(4, 2))
        self.progress = ttk.Progressbar(self, mode="indeterminate")
        self.progress.pack(fill="x", padx=16, pady=(0, 12))

    def _on_preview_resize(self, event: tk.Event) -> None:
        if event.width > 40 and event.height > 40:
            self._preview_w = event.width
            self._preview_h = event.height

    def _enable_drag_drop(self) -> None:
        if not DND_AVAILABLE:
            self.drop_zone.config(
                text="Clique aqui ou use o botão para escolher o vídeo"
            )
            return
        for widget in (self, self.drop_zone, self.preview_label):
            widget.drop_target_register(DND_FILES)
            widget.dnd_bind("<<Drop>>", self._on_drop)
            widget.dnd_bind("<<DragEnter>>", self._on_drag_enter)
            widget.dnd_bind("<<DragLeave>>", self._on_drag_leave)

    def _on_drag_enter(self, _event: object) -> None:
        self.drop_zone.config(bg="#cfe0f5", text="Solte o vídeo agora")

    def _on_drag_leave(self, _event: object) -> None:
        self._reset_drop_zone()

    def _reset_drop_zone(self) -> None:
        if self.video_path:
            name = Path(self.video_path).name
            self.drop_zone.config(bg="#e8eef5", text=f"Vídeo: {name}  ·  solte outro para trocar")
        else:
            self.drop_zone.config(bg="#e8eef5", text="Arraste e solte o vídeo aqui")

    def _on_drop(self, event: object) -> str:
        raw = getattr(event, "data", "") or ""
        paths = self._parse_drop_paths(raw)
        self._reset_drop_zone()
        if not paths:
            messagebox.showwarning("Atenção", "Não foi possível ler o arquivo solto.")
            return "break"
        self.load_video(paths[0])
        return "break"

    @staticmethod
    def _parse_drop_paths(data: str) -> list[str]:
        paths: list[str] = []
        current = ""
        in_brace = False
        for ch in data:
            if ch == "{":
                in_brace = True
                current = ""
            elif ch == "}":
                in_brace = False
                if current:
                    paths.append(current)
                current = ""
            elif ch == " " and not in_brace:
                if current:
                    paths.append(current)
                current = ""
            else:
                current += ch
        if current:
            paths.append(current)
        return [p.strip().strip('"') for p in paths if p.strip()]

    def _check_tools(self) -> None:
        if not FFMPEG or not FFPROBE:
            messagebox.showerror(
                "FFmpeg não encontrado",
                "Feche o editor e abra de novo com Abrir Editor.bat\n"
                "(ou rode Atualizar.bat).\n\n"
                "Ele baixa o FFmpeg sozinho — precisa de internet.",
            )
            self.status.config(text="Rode Abrir Editor.bat / Atualizar.bat com internet.")
        if not FFPLAY:
            self.audio_btn.config(state="disabled")

    def _on_speed_change(self, _value: str | None = None) -> None:
        speed = float(self.speed_var.get())
        self.speed_label.config(text=f"{speed:.2f}x")
        if self._last_frame is not None:
            self._display_frame(self._last_frame)
        if self._playing and not self._paused:
            self.status.config(text=f"Velocidade da prévia: {speed:.2f}x")

    def choose_video(self) -> None:
        path = filedialog.askopenfilename(
            title="Escolher vídeo",
            filetypes=[
                ("Todos os arquivos", "*.*"),
                (
                    "Vídeos comuns",
                    "*.mp4 *.mov *.mkv *.avi *.webm *.m4v *.wmv *.flv *.ts *.mts *.m2ts *.3gp *.ogv *.mpg *.mpeg",
                ),
            ],
        )
        if path:
            self.load_video(path)

    def load_video(self, path: str) -> None:
        if not path or not Path(path).is_file():
            messagebox.showerror("Erro", "Arquivo não encontrado.")
            return
        try:
            duration = probe_duration(path)
        except Exception as exc:
            messagebox.showerror(
                "Formato não lido",
                "Não foi possível abrir este arquivo como vídeo.\n\n"
                f"Detalhe: {exc}",
            )
            return

        self.stop_preview()
        if self.cap is not None:
            self.cap.release()
            self.cap = None

        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            messagebox.showerror(
                "Prévia",
                "O FFmpeg leu o arquivo, mas a prévia visual não abriu este formato.\n"
                "Você ainda pode exportar. Use também 'Prévia com áudio'.",
            )
            cap.release()
        else:
            self.cap = cap
            fps = float(cap.get(cv2.CAP_PROP_FPS) or 0)
            self._fps = fps if fps > 1 else 25.0

        self.video_path = path
        self.duration = duration
        name = Path(path).name
        self.file_label.config(text=name)
        self.duration_label.config(
            text=f"Duração: {format_time(duration)} ({duration:.2f}s)"
        )
        self.start_var.set("0:00.000")
        self.end_var.set(format_time(duration))
        self._reset_drop_zone()
        self.status.config(text=f"Vídeo carregado: {name}")
        self.preview_time.config(text=f"0:00 / {format_time(duration)}")
        self.show_frame_at(0.0)

    def show_frame_at(self, seconds: float) -> None:
        if self.cap is None:
            return
        seconds = max(0.0, min(seconds, max(self.duration - 0.05, 0.0)))
        self.cap.set(cv2.CAP_PROP_POS_MSEC, seconds * 1000.0)
        ok, frame = self.cap.read()
        if ok:
            self._display_frame(frame)
            self.preview_time.config(
                text=f"{format_time(seconds)} / {format_time(self.duration)}"
            )

    def _display_frame(self, frame) -> None:
        self._last_frame = frame
        canvas = frame.copy()
        speed = float(self.speed_var.get())
        label = f"{speed:.2f}x"
        font = cv2.FONT_HERSHEY_SIMPLEX
        scale = max(canvas.shape[1] / 640.0, 0.8)
        thickness = max(2, int(scale * 2))
        (tw, th), baseline = cv2.getTextSize(label, font, scale, thickness)
        pad = 12
        x, y = pad, pad + th
        cv2.rectangle(
            canvas,
            (x - 8, y - th - 8),
            (x + tw + 8, y + baseline + 6),
            (0, 0, 0),
            -1,
        )
        cv2.putText(
            canvas,
            label,
            (x, y),
            font,
            scale,
            (0, 255, 180),
            thickness,
            cv2.LINE_AA,
        )

        rgb = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb)
        max_w = max(self._preview_w - 4, 320)
        max_h = max(self._preview_h - 4, 180)
        img.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
        self._photo = ImageTk.PhotoImage(img)
        self.preview_label.config(image=self._photo, text="")

    def _read_edit_range(self) -> tuple[float, float, float]:
        start = parse_time(self.start_var.get())
        end = parse_time(self.end_var.get())
        speed = float(self.speed_var.get())
        if start < 0 or end <= start:
            raise ValueError("O fim precisa ser maior que o início.")
        if start >= self.duration:
            raise ValueError("O início passa da duração do vídeo.")
        end = min(end, self.duration)
        if speed < 0.25 or speed > 3.0:
            raise ValueError("Use uma velocidade entre 0.25 e 3.0.")
        return start, end, speed

    def seek_to_start(self) -> None:
        if not self.video_path:
            return
        try:
            start, _, _ = self._read_edit_range()
        except ValueError as exc:
            messagebox.showerror("Tempo inválido", str(exc))
            return
        self.stop_preview(keep_frame=False)
        self.show_frame_at(start)

    def play_preview(self) -> None:
        if not self.video_path:
            messagebox.showwarning("Atenção", "Escolha um vídeo primeiro.")
            return
        if self.cap is None:
            messagebox.showwarning(
                "Prévia",
                "Este formato não tem prévia visual. Use 'Prévia com áudio'.",
            )
            return
        try:
            start, end, speed = self._read_edit_range()
        except ValueError as exc:
            messagebox.showerror("Ajuste inválido", str(exc))
            return

        if self._paused and self._playing:
            self._paused = False
            self.status.config(text="Prévia retomada.")
            return

        self.stop_preview(keep_frame=False)
        self._playing = True
        self._paused = False
        self._play_token += 1
        token = self._play_token
        self.status.config(
            text=f"Tocando prévia · corte {format_time(start)}–{format_time(end)} · {speed:.2f}x"
        )
        threading.Thread(
            target=self._playback_loop,
            args=(token, start, end, speed),
            daemon=True,
        ).start()

    def pause_preview(self) -> None:
        if self._playing:
            self._paused = not self._paused
            self.status.config(
                text="Prévia pausada." if self._paused else "Prévia retomada."
            )

    def stop_preview(self, keep_frame: bool = True) -> None:
        self._playing = False
        self._paused = False
        self._play_token += 1
        self._stop_ffplay()
        if keep_frame and self.video_path:
            try:
                start = parse_time(self.start_var.get())
            except ValueError:
                start = 0.0
            self.after(0, lambda: self.show_frame_at(start))

    def _playback_loop(
        self, token: int, start: float, end: float, speed: float
    ) -> None:
        assert self.cap is not None
        self.cap.set(cv2.CAP_PROP_POS_MSEC, start * 1000.0)
        pos = start

        while self._playing and token == self._play_token:
            while self._paused and self._playing and token == self._play_token:
                time.sleep(0.05)

            if not self._playing or token != self._play_token:
                break

            # Velocidade ao vivo: muda assim que você mexe no controle
            live_speed = float(self.speed_var.get())
            frame_interval = 1.0 / (self._fps * max(live_speed, 0.01))

            t0 = time.perf_counter()
            ok, frame = self.cap.read()
            if not ok:
                break

            pos_msec = float(self.cap.get(cv2.CAP_PROP_POS_MSEC) or 0)
            pos = pos_msec / 1000.0 if pos_msec > 0 else pos + (1.0 / self._fps)
            if pos >= end:
                break

            self.after(0, lambda f=frame, p=pos: self._on_play_frame(f, p, token))
            elapsed = time.perf_counter() - t0
            time.sleep(max(0.0, frame_interval - elapsed))

        if token == self._play_token:
            self.after(0, self._on_play_finished)

    def _on_play_frame(self, frame, pos: float, token: int) -> None:
        if token != self._play_token:
            return
        self._display_frame(frame)
        self.preview_time.config(
            text=f"{format_time(pos)} / {format_time(self.duration)}"
        )

    def _on_play_finished(self) -> None:
        self._playing = False
        self._paused = False
        self.status.config(text="Prévia terminou. Ajuste e teste de novo, ou salve.")

    def preview_with_audio(self) -> None:
        if not self.video_path:
            messagebox.showwarning("Atenção", "Escolha um vídeo primeiro.")
            return
        if not FFPLAY:
            messagebox.showerror("Erro", "ffplay não encontrado (vem com o FFmpeg).")
            return
        try:
            start, end, speed = self._read_edit_range()
        except ValueError as exc:
            messagebox.showerror("Ajuste inválido", str(exc))
            return

        self._stop_ffplay()
        duration = end - start
        setpts = 1.0 / speed
        af = ",".join(atempo_chain(speed))
        cmd = [
            FFPLAY,
            "-hide_banner",
            "-loglevel",
            "error",
            "-autoexit",
            "-ss",
            f"{start:.3f}",
            "-t",
            f"{duration:.3f}",
            "-i",
            self.video_path,
            "-vf",
            f"setpts={setpts}*PTS",
            "-af",
            af,
        ]
        try:
            self._ffplay_proc = subprocess.Popen(cmd)
            self.status.config(
                text="Prévia com áudio aberta em outra janela (feche ela para parar)."
            )
        except Exception as exc:
            messagebox.showerror("Erro", f"Não foi possível abrir a prévia:\n{exc}")

    def _stop_ffplay(self) -> None:
        if self._ffplay_proc and self._ffplay_proc.poll() is None:
            self._ffplay_proc.terminate()
            try:
                self._ffplay_proc.wait(timeout=1.5)
            except subprocess.TimeoutExpired:
                self._ffplay_proc.kill()
        self._ffplay_proc = None

    def open_app_folder(self) -> None:
        os.startfile(Path(__file__).resolve().parent)

    def export_video(self) -> None:
        if self._busy:
            return
        if not self.video_path:
            messagebox.showwarning("Atenção", "Escolha um vídeo primeiro.")
            return
        if not FFMPEG:
            messagebox.showerror("Erro", "FFmpeg não encontrado.")
            return
        try:
            start, end, speed = self._read_edit_range()
        except ValueError as exc:
            messagebox.showerror("Ajuste inválido", str(exc))
            return

        src = Path(self.video_path)
        out = filedialog.asksaveasfilename(
            title="Salvar vídeo editado",
            defaultextension=".mp4",
            initialfile=f"{src.stem}_editado.mp4",
            filetypes=[("MP4", "*.mp4"), ("Todos os arquivos", "*.*")],
        )
        if not out:
            return

        self.stop_preview()
        self._set_busy(True, "Exportando… isso pode levar alguns minutos.")
        threading.Thread(
            target=self._run_export,
            args=(self.video_path, out, start, end, speed),
            daemon=True,
        ).start()

    def _set_busy(self, busy: bool, message: str) -> None:
        self._busy = busy
        state = "disabled" if busy else "normal"
        self.export_btn.config(state=state)
        self.play_btn.config(state=state)
        self.status.config(text=message)
        if busy:
            self.progress.start(12)
        else:
            self.progress.stop()

    def _run_export(
        self, src: str, out: str, start: float, end: float, speed: float
    ) -> None:
        duration = end - start
        setpts = 1.0 / speed
        af = ",".join(atempo_chain(speed))
        cmd = [
            FFMPEG,
            "-y",
            "-ss",
            f"{start:.3f}",
            "-i",
            src,
            "-t",
            f"{duration:.3f}",
            "-vf",
            f"setpts={setpts}*PTS",
            "-af",
            af,
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "23",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            out,
        ]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True)
            if proc.returncode != 0:
                err = (proc.stderr or proc.stdout or "erro desconhecido")[-800:]
                self.after(0, lambda: self._export_failed(err))
                return
            self.after(0, lambda: self._export_ok(out))
        except Exception as exc:
            self.after(0, lambda: self._export_failed(str(exc)))

    def _export_ok(self, out: str) -> None:
        self._set_busy(False, f"Pronto! Salvo em: {out}")
        if messagebox.askyesno("Concluído", f"Vídeo salvo em:\n{out}\n\nAbrir a pasta?"):
            os.startfile(Path(out).resolve().parent)

    def _export_failed(self, err: str) -> None:
        self._set_busy(False, "Falha ao exportar.")
        messagebox.showerror("Erro ao exportar", err)

    def _on_close(self) -> None:
        self.stop_preview(keep_frame=False)
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        self.destroy()


def main() -> None:
    app = EditorApp()
    app.mainloop()


if __name__ == "__main__":
    main()
