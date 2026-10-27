"""Incorporate and transcribe the user-provided UAS recording locally."""
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]
SUBJECT = ROOT / "UAS/licenciatura-en-contaduria-uas/herramientas-digitales"
SOURCE_URL = "https://drive.google.com/file/d/1NaR_KBkiiZRg3ioHxiSRJw_GMqCDf2rD/view"


def main():
    specification = importlib.util.spec_from_file_location(
        "recording_tools", ROOT / "UCNL/assets-ucnl/descargar-transcribir-grabaciones.py"
    )
    recording_tools = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(recording_tools)
    folder = SUBJECT / "referencias-herramientas-digitales/grabaciones/clase-1NaR_KBkiiZRg3ioHxiSRJw_GMqCDf2rD"
    folder.mkdir(parents=True, exist_ok=True)
    control = folder / "control"
    control.mkdir(exist_ok=True)
    (ROOT / "tmp").mkdir(exist_ok=True)
    download = Path.home() / "Downloads/video1860556015.mp4"
    video = folder / download.name
    if not video.exists():
        recording_tools.probe(download)
        shutil.copy2(download, video)
    duration = recording_tools.probe(video)
    receipt = {
        "source_url": SOURCE_URL,
        "incorporated_utc": datetime.now(timezone.utc).isoformat(),
        "file": video.name,
        "bytes": video.stat().st_size,
        "sha256": recording_tools.digest(video),
        "duration_seconds": duration,
        "subject_assignment": "Herramientas digitales UAS; enlace proporcionado por el usuario",
        "class_date": None,
        "week": None,
        "transcription_status": "Pendiente",
        "remote_audio_service": False,
    }
    receipt_path = folder / "procedencia.json"
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"video_verified": True, "duration_seconds": duration, "bytes": receipt["bytes"]}), flush=True)
    subtitles = folder / "transcripcion.srt"
    transcription = recording_tools.transcribe(video, subtitles, control, duration, "Spanish")
    original_result = control / "transcripcion - resultado-motor.json"
    if original_result.exists():
        original_run = json.loads(original_result.read_text(encoding="utf-8"))
        transcription["codigo_motor"] = original_run["codigo_motor"]
        transcription["marcador_fin_motor"] = "Operation finished" in (control / "transcripcion - motor.log").read_text(encoding="utf-8", errors="replace")
    repairs_path = control / "transcripcion - reparaciones.json"
    if repairs_path.exists():
        transcription["duraciones_nulas_corregidas"] = json.loads(repairs_path.read_text(encoding="utf-8"))
    cues = list(recording_tools.srt.parse(subtitles.read_text(encoding="utf-8-sig")))
    recording_tools.validate_cues(cues, duration)
    text = "\n\n".join(f"[{str(cue.start).split('.')[0]}] {cue.content}" for cue in cues) + "\n"
    transcript = folder / "transcripcion.txt"
    transcript.write_text(text, encoding="utf-8")
    receipt.update(
        transcription_status=("Automatica recuperada tras salida anomala; revision humana pendiente"
                              if transcription.get("codigo_motor", 0) else "Automatica; revision humana pendiente"),
        transcription=transcription,
        transcript_sha256=recording_tools.digest(transcript),
        first_segment_seconds=cues[0].start.total_seconds(),
        last_segment_seconds=cues[-1].end.total_seconds(),
    )
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
    (folder / "README.md").write_text(
        "# Grabacion de clase\n\n"
        f"[Origen en Google Drive]({SOURCE_URL}). Incorporada a Herramientas digitales por indicacion del usuario.\n\n"
        "Fecha de clase, semana y nombres de hablantes no acreditados.\n\n"
        "- [Video original](video1860556015.mp4).\n"
        "- [Transcripcion con tiempos](transcripcion.txt).\n"
        "- [Subtitulos SRT](transcripcion.srt).\n"
        "- [Procedencia y verificaciones](procedencia.json).\n\n"
        "Transcripcion automatica en espanol mediante Whisper large-v3 local, sin envio del audio a servicios externos. "
        "Puede contener errores, omisiones o atribuciones incorrectas. No hay diarizacion ni identidades verificadas. "
        "Los tiempos se validaron contra la duracion del video; esto no acredita exactitud palabra por palabra. "
        "Consultar el codigo del motor en procedencia.json: una salida anomala no se presenta como ejecucion limpia. "
        "Conservar como material de apoyo del aula, no citar como autoridad academica independiente.\n",
        encoding="utf-8",
    )
    print(json.dumps({"completed": True, "segments": len(cues), "duration_seconds": duration, "last_segment_seconds": receipt["last_segment_seconds"]}), flush=True)


if __name__ == "__main__":
    main()