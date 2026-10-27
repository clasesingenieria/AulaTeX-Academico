"""Script de montaje y verificación con FFmpeg para el video de presentación de AM Taller Autocentro.

Modos de uso:
1) Generar pista visual base de 11:00 (12 diapositivas 1080p sincronizadas + subtítulos revisados, SIN simular al estudiante):
   python ensamblar_video_real.py --solo-pista-visual

2) Ensamblar el video final completo cuando el estudiante proporcione su grabación real de cámara y voz:
   python ensamblar_video_real.py --grabacion ruta/a/grabacion_estudiante.mp4 --salida ruta/a/video-final-AM-Taller.mp4
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

MONTAJE_DIR = Path(__file__).resolve().parent
BASE_DIR = MONTAJE_DIR.parent
MANIFEST_PATH = BASE_DIR / "guion-tecnico-temporizado.json"
SRT_PATH = BASE_DIR / "subtitulos-revisados.srt"
VISUAL_TRACK_PATH = MONTAJE_DIR / "pista-visual-diapositivas-11m00s.mp4"


def probe_media(path: Path) -> dict:
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration,size:stream=index,codec_type,codec_name,width,height",
        "-of", "json",
        str(path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return json.loads(res.stdout)


def build_visual_base_track(manifest: dict, out_path: Path) -> dict:
    """Genera la pista visual de las 12 diapositivas a 1920x1080 con transiciones discretas y subtítulos."""
    segments_dir = MONTAJE_DIR / "segmentos-temp"
    segments_dir.mkdir(parents=True, exist_ok=True)
    concat_lines: list[str] = []

    for b in manifest["blocks"]:
        slide_num = b["slide"]
        dur = float(b["duration_sec"])
        slide_img = BASE_DIR / b["slide_image"]
        seg_mp4 = segments_dir / f"seg-{slide_num:02d}.mp4"
        fade_out_start = max(0.0, round(dur - 0.35, 2))
        vf = (
            f"scale=1920:1080:flags=lanczos,format=yuv420p,"
            f"fade=t=in:st=0:d=0.35,fade=t=out:st={fade_out_start}:d=0.35"
        )
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-framerate", "24",
            "-t", f"{dur:.2f}",
            "-i", str(slide_img),
            "-vf", vf,
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-tune", "stillimage",
            "-crf", "20",
            "-pix_fmt", "yuv420p",
            str(seg_mp4),
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        concat_lines.append(f"file '{seg_mp4.as_posix()}'")

    concat_list = segments_dir / "concat.txt"
    concat_list.write_text("\n".join(concat_lines) + "\n", encoding="utf-8")

    cmd_mux = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_list),
        "-i", str(SRT_PATH),
        "-c:v", "copy",
        "-c:s", "mov_text",
        "-metadata:s:s:0", "language=spa",
        "-metadata:s:s:0", "title=Español (revisados)",
        "-movflags", "+faststart",
        str(out_path),
    ]
    subprocess.run(cmd_mux, check=True, capture_output=True)

    for f in segments_dir.glob("*"):
        f.unlink(missing_ok=True)
    segments_dir.rmdir()

    info = probe_media(out_path)
    sha256 = hashlib.sha256(out_path.read_bytes()).hexdigest()
    return {
        "file": str(out_path.relative_to(BASE_DIR)).replace("\\", "/"),
        "bytes": out_path.stat().st_size,
        "sha256": sha256,
        "duration_sec": round(float(info["format"]["duration"]), 2),
        "streams": info.get("streams", []),
        "contains_student_camera_or_voice": False,
        "note": "Pista visual base de las 12 diapositivas con transiciones discretas y subtítulos revisados. No sustituye el video final porque requiere la grabación real de cámara y voz del estudiante.",
    }


def assemble_with_student_recording(manifest: dict, recording_path: Path, out_path: Path) -> dict:
    """Superpone la grabación real de cámara y voz del estudiante en el recuadro derecho sobre las 12 diapositivas."""
    if not recording_path.exists():
        raise FileNotFoundError(f"No existe el archivo de grabación del estudiante: {recording_path}")

    rec_info = probe_media(recording_path)
    streams = rec_info.get("streams", [])
    has_video = any(s.get("codec_type") == "video" for s in streams)
    has_audio = any(s.get("codec_type") == "audio" for s in streams)
    if not (has_video and has_audio):
        raise RuntimeError("La grabación del estudiante debe incluir pista de video (cámara) y pista de audio (voz).")

    rec_duration = float(rec_info["format"]["duration"])
    if not (420.0 <= rec_duration <= 1200.0):
        raise RuntimeError(
            f"La duración real de la grabación ({rec_duration:.1f} s) está fuera del rango exigido de 7 a 20 minutos (420 a 1200 s)."
        )

    if not VISUAL_TRACK_PATH.exists():
        build_visual_base_track(manifest, VISUAL_TRACK_PATH)

    box = manifest["camera_box"]
    x, y, w, h = box["x"], box["y"], box["width"], box["height"]

    filter_complex = (
        f"[1:v]scale={w}:{h}:force_original_aspect_ratio=decrease,"
        f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=#141414,"
        f"drawbox=x=0:y=0:w={w}:h={h}:color=#8F1117:t=3[pip];"
        f"[0:v][pip]overlay=x={x}:y={y}:shortest=1[vout];"
        f"[1:a]highpass=f=80,loudnorm=I=-16:TP=-1.5:LRA=11[aout]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", str(VISUAL_TRACK_PATH),
        "-i", str(recording_path),
        "-i", str(SRT_PATH),
        "-filter_complex", filter_complex,
        "-map", "[vout]",
        "-map", "[aout]",
        "-map", "2:0",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-c:s", "mov_text",
        "-metadata:s:s:0", "language=spa",
        "-movflags", "+faststart",
        str(out_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    out_info = probe_media(out_path)
    return {
        "file": str(out_path),
        "bytes": out_path.stat().st_size,
        "sha256": hashlib.sha256(out_path.read_bytes()).hexdigest(),
        "duration_sec": round(float(out_info["format"]["duration"]), 2),
        "streams": out_info.get("streams", []),
        "contains_student_camera_or_voice": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Montaje del video de presentación AM Taller Autocentro.")
    parser.add_argument("--solo-pista-visual", action="store_true", help="Genera y verifica la pista visual base 1080p con subtítulos.")
    parser.add_argument("--grabacion", type=Path, help="Ruta a la grabación real autorizada de cámara y voz del estudiante.")
    parser.add_argument(
        "--salida",
        type=Path,
        default=MONTAJE_DIR / "video-presentacion-AM-Taller-Autocentro.mp4",
        help="Ruta de salida para el video completo.",
    )
    args = parser.parse_args()

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    if args.solo_pista_visual or not args.grabacion:
        visual_report = build_visual_base_track(manifest, VISUAL_TRACK_PATH)
        report = {
            "status": "visual_base_prepared_awaiting_student_recording",
            "visual_base_track": visual_report,
            "final_video_produced": False,
            "missing_recording": "Falta archivo de grabación real de imagen y voz del estudiante Martín Jonathan de la Cruz Muñoz.",
        }
        (MONTAJE_DIR / "verificacion-montaje.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    final_report = assemble_with_student_recording(manifest, args.grabacion, args.salida)
    report = {
        "status": "final_video_assembled",
        "final_video": final_report,
        "final_video_produced": True,
    }
    (MONTAJE_DIR / "verificacion-montaje.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

