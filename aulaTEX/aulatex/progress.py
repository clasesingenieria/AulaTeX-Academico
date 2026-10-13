"""Protocolo de progreso observable para comandos largos de AulaTeX.

Los comandos de larga duración (motor inteligente, ciclos monitorizados,
memoria editorial) suelen bloquear la consola sin retroalimentación hasta
terminar. Este módulo define un canal de progreso ligero, inspirado en el
monitor Git+LLM de ``C:\\ahk-Autohokey`` (marcadores ``::progress::`` que un
lanzador PowerShell parsea en tiempo real para pintar una barra y un log).

Reglas de diseño:

* Los marcadores se emiten a ``stderr`` para NO contaminar el ``stdout`` que
  transporta el JSON de resultado del CLI. El lanzador lee ambos flujos.
* Cada marcador es una única línea autocontenida y fácil de parsear con regex.
* La emisión es tolerante a fallos: si el flujo no acepta escritura, se ignora.

Marcadores emitidos:

``::progress::<0-100>::<mensaje>``
    Actualiza barra de avance global y la línea de estado.
``::stage::<id>::<titulo>``
    Marca el inicio de una etapa (p. ej. un target del motor inteligente).
``::notice::<mensaje>``
    Línea informativa (subpaso, detalle, advertencia no fatal).
``::result::<status>::<mensaje>``
    Resultado de una etapa/acción. ``status`` ∈ {success, error, cancelled,
    warning, skipped, running}.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import IO


def _sanitize(value: object) -> str:
    """Colapsa saltos de línea para preservar la regla de una línea por marcador."""

    text = "" if value is None else str(value)
    return text.replace("\r", " ").replace("\n", " ").strip()


@dataclass
class ProgressReporter:
    """Emite marcadores de progreso hacia un flujo (por defecto ``stderr``).

    El reporter es deliberadamente stateless respecto al porcentaje: el llamador
    decide cuánto avance representa cada paso. Si se prefiere un avance por pasos
    homogéneo, usar :class:`StepProgress`.
    """

    stream: IO[str] = field(default_factory=lambda: sys.stderr)
    enabled: bool = True

    def _emit(self, line: str) -> None:
        if not self.enabled or self.stream is None:
            return
        try:
            self.stream.write(line + "\n")
            self.stream.flush()
        except (ValueError, OSError):
            # Flujo cerrado o no escribible: el progreso es best-effort.
            pass

    def progress(self, percent: float, message: str = "") -> None:
        clamped = max(0, min(100, int(round(percent))))
        self._emit(f"::progress::{clamped}::{_sanitize(message)}")

    def stage(self, stage_id: str, title: str) -> None:
        self._emit(f"::stage::{_sanitize(stage_id)}::{_sanitize(title)}")

    def notice(self, message: str) -> None:
        self._emit(f"::notice::{_sanitize(message)}")

    def result(self, status: str, message: str = "") -> None:
        status_clean = _sanitize(status).lower() or "running"
        self._emit(f"::result::{status_clean}::{_sanitize(message)}")


class NullProgressReporter(ProgressReporter):
    """Reporter inerte para ejecuciones sin monitor (no emite nada)."""

    def __init__(self) -> None:  # noqa: D401 - constructor simple
        super().__init__(stream=sys.stderr, enabled=False)

    def _emit(self, line: str) -> None:  # noqa: D401 - inerte
        return


@dataclass
class StepProgress:
    """Convierte un total de pasos conocido en porcentajes homogéneos.

    Uso típico en un ejecutor con ``N`` targets: ``StepProgress(reporter, N)``
    y luego ``step.advance("target X hecho")`` tras cada uno.
    """

    reporter: ProgressReporter
    total: int
    _done: int = 0

    def start(self, message: str = "Iniciando…") -> None:
        self._done = 0
        self.reporter.progress(0, message)

    def advance(self, message: str = "", *, completed: int | None = None) -> None:
        if completed is not None:
            self._done = max(0, min(self.total, int(completed)))
        else:
            self._done = min(self.total, self._done + 1)
        percent = 100.0 if self.total <= 0 else (self._done / self.total) * 100.0
        self.reporter.progress(percent, message)

    def finish(self, message: str = "Completado.") -> None:
        self._done = self.total
        self.reporter.progress(100, message)


def resolve_reporter(enabled: bool) -> ProgressReporter:
    """Fábrica: devuelve un reporter activo o inerte según el flag."""

    return ProgressReporter(enabled=True) if enabled else NullProgressReporter()
