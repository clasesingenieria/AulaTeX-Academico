from __future__ import annotations

import contextlib
import json
import os
from pathlib import Path
import re
import shutil
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any
import unicodedata

from .cli import main as cli_main
from .concept_extractor import extract_candidate_concepts, extract_candidate_concepts_from_planeacion
from .document_reader import extract_pages_from_sources, parse_extensions, read_any_text_file
from .nova_activity_extractor import (
    DEFAULT_SUBJECT_DIR,
    ActivityExtractionTracker,
    get_paths_for_activity,
)
from .planeacion_parser import parse_planeacion_text, summarize_planeacion_analysis
from .preprocessing import build_fragments, load_concept_lines, unique_preserve_order

ROOT = Path(__file__).resolve().parents[2]
INPUT_FUENTES = ROOT / "input" / "fuentes"
INPUT_PLANEACIONES = ROOT / "input" / "planeaciones"
OUTPUT_ROOT = ROOT / "output"
GUI_OUTPUT = OUTPUT_ROOT / "gui_run"
ALLOWED_SOURCE_EXTS = {".pdf", ".docx", ".txt", ".md", ".markdown"}


def _strip_accents(text: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFKD", text) if not unicodedata.combining(ch))


def _slugify(text: str) -> str:
    text = _strip_accents(text.lower())
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def _infer_week_code_from_name_or_text(path: Path | None) -> str | None:
    if not path:
        return None
    candidates = [path.name, path.stem]
    for candidate in candidates:
        normalized = _strip_accents(candidate.lower())
        m = re.search(r"\bs\s*0*(\d{1,2})\b", normalized)
        if m:
            return f"S{int(m.group(1)):02d}"
        m = re.search(r"semana\s*0*(\d{1,2})\b", normalized)
        if m:
            return f"S{int(m.group(1)):02d}"

    try:
        text = read_any_text_file(path)
    except Exception:
        text = ""
    if text:
        normalized = _strip_accents(text.lower())
        m = re.search(r"semana\s*0*(\d{1,2})\b", normalized)
        if m:
            return f"S{int(m.group(1)):02d}"
    return None


def _infer_subject_slug(paths: list[Path], planeacion_path: Path | None) -> str:
    candidates = list(paths)
    if planeacion_path:
        candidates.append(planeacion_path)

    prefixes = (
        "libros-",
        "referencias-",
        "planeaciones-",
        "notas-",
        "conceptos-",
        "reporte-",
    )

    for path in candidates:
        for part in [path.name] + [p.name for p in path.parents if p.name][:4]:
            low = _strip_accents(part.lower())
            for prefix in prefixes:
                if low.startswith(prefix):
                    return _slugify(low[len(prefix) :])
    if planeacion_path:
        return _slugify(planeacion_path.parent.name)
    if paths:
        return _slugify(paths[0].parent.name if paths[0].is_file() else paths[0].name)
    return "materia"


class _FeedbackWriter:
    def __init__(self, emit_line) -> None:
        self._emit_line = emit_line
        self._buffer = ""

    def write(self, text: str) -> int:
        if not text:
            return 0
        self._buffer += text
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            if line.strip():
                self._emit_line(line)
        return len(text)

    def flush(self) -> None:
        if self._buffer.strip():
            self._emit_line(self._buffer)
        self._buffer = ""


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("AulaTeX — Extractor de Conceptos, Ideas e Investigación por Actividad (Amazon Nova Pro)")
        self.geometry("1280x840")
        self.minsize(1060, 700)

        # Estado de la pestaña de Trabajos por Actividad (Nova Pro)
        self.subject_dir_var = tk.StringVar(value=str(DEFAULT_SUBJECT_DIR))
        self.batch_workers_var = tk.IntVar(value=4)
        self.batch_running = False
        self.global_progress_var = tk.DoubleVar(value=0.0)
        self.active_stage_progress_var = tk.DoubleVar(value=0.0)
        self.summary_completed_var = tk.StringVar(value="Actividades: 0 / 22 (0%)")
        self.summary_sources_var = tk.StringVar(value="Fuentes leídas: 0")
        self.summary_fichas_var = tk.StringVar(value="Fichas de conceptos: 0")
        self.summary_ideas_var = tk.StringVar(value="Ideas (3 tiempos): 0")
        self.summary_tokens_var = tk.StringVar(value="Tokens Nova Pro: 0")
        self.batch_status_var = tk.StringVar(value="Listo para ejecutar o inspeccionar extracciones por actividad.")
        self.tracker: ActivityExtractionTracker | None = None

        # Estado de la pestaña manual original
        self.workflow_var = tk.StringVar(value="anthropicfoundry")
        self.recursive_var = tk.BooleanVar(value=True)
        self.clean_inputs_var = tk.BooleanVar(value=True)
        self.clean_output_var = tk.BooleanVar(value=True)
        self.auto_concepts_var = tk.IntVar(value=20)
        self.threshold_var = tk.StringVar(value="0.08")
        self.max_fragment_var = tk.StringVar(value="850")
        self.min_fragment_var = tk.StringVar(value="120")
        self.top_k_var = tk.StringVar(value="10")
        self.max_citas_var = tk.StringVar(value="5")
        self.extensions_var = tk.StringVar(value=",".join(sorted(ALLOWED_SOURCE_EXTS)))
        self.use_previewed_concepts_var = tk.BooleanVar(value=False)
        self.fuentes_items: list[Path] = []
        self.previewed_concepts: list[str] = []
        self.planeacion_path: Path | None = None
        self.conceptos_path: Path | None = None
        self.output_base_dir: Path | None = None
        self.derived_output_dir: Path | None = None
        self.is_running = False

        self._build_ui()
        self._init_tracker_and_refresh()
        self.after(2000, self._poll_disk_state)

    def _build_ui(self) -> None:
        self.main_notebook = ttk.Notebook(self)
        self.main_notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self.tab_batch = ttk.Frame(self.main_notebook, padding=10)
        self.tab_manual = ttk.Frame(self.main_notebook, padding=10)
        self.main_notebook.add(
            self.tab_batch,
            text="  1. Trabajos por Actividad (AulaTeX — Amazon Nova Pro)  ",
        )
        self.main_notebook.add(
            self.tab_manual,
            text="  2. Ejecución Manual / Individual  ",
        )

        self._build_batch_tab(self.tab_batch)
        self._build_manual_tab(self.tab_manual)

    # ------------------------------------------------------------------
    # PESTAÑA 1: TRABAJOS POR ACTIVIDAD (AMAZON NOVA PRO)
    # ------------------------------------------------------------------
    def _build_batch_tab(self, parent: ttk.Frame) -> None:
        header = ttk.Frame(parent)
        header.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(
            header,
            text="Gestor de Extracción Conceptual e Investigación por Actividad — Amazon Nova Pro",
            font=("Segoe UI", 13, "bold"),
        ).pack(side=tk.LEFT)
        ttk.Label(
            header,
            text="Salidas sincronizadas en: extractor-aulatex/conceptos-*  |  referencias-*/conceptos-*  |  notas-*/actividad-XX/conceptos/",
            foreground="#1b5e20",
            font=("Segoe UI", 9, "italic"),
        ).pack(side=tk.RIGHT)

        # Selector de materia
        subj_frame = ttk.LabelFrame(parent, text="Materia activa y configuración de extracción")
        subj_frame.pack(fill=tk.X, pady=4)
        subj_row = ttk.Frame(subj_frame)
        subj_row.pack(fill=tk.X, padx=8, pady=6)
        ttk.Label(subj_row, text="Carpeta de la materia:").pack(side=tk.LEFT, padx=(0, 6))
        ttk.Entry(subj_row, textvariable=self.subject_dir_var, width=82).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        ttk.Button(subj_row, text="Cambiar materia...", command=self._choose_subject_dir).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(subj_row, text="Recargar estado", command=self._init_tracker_and_refresh).pack(side=tk.LEFT)

        # Panel de métricas y barras de progreso
        dash = ttk.LabelFrame(parent, text="Avance Global y Métricas del Trabajo de Extracción")
        dash.pack(fill=tk.X, pady=4)

        metrics_row = ttk.Frame(dash)
        metrics_row.pack(fill=tk.X, padx=8, pady=(6, 4))
        for var, fg in (
            (self.summary_completed_var, "#0d47a1"),
            (self.summary_sources_var, "#333333"),
            (self.summary_fichas_var, "#1b5e20"),
            (self.summary_ideas_var, "#4a148c"),
            (self.summary_tokens_var, "#b71c1c"),
        ):
            lbl = ttk.Label(metrics_row, textvariable=var, font=("Segoe UI", 10, "bold"), foreground=fg)
            lbl.pack(side=tk.LEFT, padx=(0, 22))

        prog_row = ttk.Frame(dash)
        prog_row.pack(fill=tk.X, padx=8, pady=(2, 4))
        ttk.Label(prog_row, text="Progreso global (22 actividades):", width=28).pack(side=tk.LEFT)
        self.global_pbar = ttk.Progressbar(prog_row, variable=self.global_progress_var, maximum=100.0)
        self.global_pbar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 12))

        stage_row = ttk.Frame(dash)
        stage_row.pack(fill=tk.X, padx=8, pady=(0, 6))
        ttk.Label(stage_row, text="Avance actividad seleccionada:", width=28).pack(side=tk.LEFT)
        self.stage_pbar = ttk.Progressbar(stage_row, variable=self.active_stage_progress_var, maximum=100.0)
        self.stage_pbar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 12))
        ttk.Label(stage_row, textvariable=self.batch_status_var, foreground="#0a5").pack(side=tk.LEFT)

        # Barra de acciones de ejecución
        toolbar = ttk.Frame(parent)
        toolbar.pack(fill=tk.X, pady=4)
        self.btn_run_all = ttk.Button(
            toolbar,
            text="▶ Ejecutar todas (1–22)",
            command=lambda: self._start_batch_extraction(mode="all", force_nova=False),
        )
        self.btn_run_all.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_run_pending = ttk.Button(
            toolbar,
            text="▶ Ejecutar pendientes",
            command=lambda: self._start_batch_extraction(mode="pending", force_nova=False),
        )
        self.btn_run_pending.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_run_selected = ttk.Button(
            toolbar,
            text="▶ Ejecutar seleccionadas",
            command=lambda: self._start_batch_extraction(mode="selected", force_nova=False),
        )
        self.btn_run_selected.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_rerun_force = ttk.Button(
            toolbar,
            text="↻ Re-ejecutar con Nova Pro",
            command=lambda: self._start_batch_extraction(mode="selected", force_nova=True),
        )
        self.btn_rerun_force.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_stop_batch = ttk.Button(
            toolbar,
            text="⏹ Detener",
            command=self._stop_batch_extraction,
            state=tk.DISABLED,
        )
        self.btn_stop_batch.pack(side=tk.LEFT, padx=(0, 12))

        ttk.Label(toolbar, text="Hilos Nova Pro:").pack(side=tk.LEFT, padx=(0, 4))
        ttk.Spinbox(toolbar, from_=1, to=6, textvariable=self.batch_workers_var, width=4).pack(side=tk.LEFT, padx=(0, 14))

        ttk.Button(toolbar, text="📂 Abrir carpeta conceptos", command=self._open_selected_conceptos_dir).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(toolbar, text="📂 Abrir carpeta notas", command=self._open_selected_notas_dir).pack(side=tk.LEFT)

        # PanedWindow vertical: arriba tabla de 22 actividades, abajo inspector y bitácora
        paned = ttk.PanedWindow(parent, orient=tk.VERTICAL)
        paned.pack(fill=tk.BOTH, expand=True, pady=(4, 0))

        table_frame = ttk.LabelFrame(paned, text="Trabajos de Extracción por Actividad (1 a 22)")
        paned.add(table_frame, weight=3)

        cols = (
            "act",
            "modulo",
            "unidad",
            "titulo",
            "tipo",
            "estado",
            "etapa",
            "avance",
            "fuentes",
            "conceptos",
            "fichas",
            "ideas",
            "tokens",
            "tiempo",
        )
        self.jobs_tree = ttk.Treeview(table_frame, columns=cols, show="headings", selectmode="extended", height=12)
        headings = {
            "act": ("Act.", 48, "center"),
            "modulo": ("Módulo", 60, "center"),
            "unidad": ("Unidad", 155, "w"),
            "titulo": ("Actividad en Plataforma", 230, "w"),
            "tipo": ("Tipo", 110, "w"),
            "estado": ("Estado", 95, "center"),
            "etapa": ("Etapa de Extracción", 175, "w"),
            "avance": ("Avance", 62, "center"),
            "fuentes": ("Fuentes", 58, "center"),
            "conceptos": ("Conceptos", 68, "center"),
            "fichas": ("Fichas", 55, "center"),
            "ideas": ("Ideas", 55, "center"),
            "tokens": ("Tokens Nova", 82, "e"),
            "tiempo": ("Tiempo", 65, "e"),
        }
        for col, (text, width, anchor) in headings.items():
            self.jobs_tree.heading(col, text=text)
            self.jobs_tree.column(col, width=width, anchor=anchor)

        self.jobs_tree.tag_configure("completado", background="#e8f5e9")
        self.jobs_tree.tag_configure("ejecutando", background="#e3f2fd")
        self.jobs_tree.tag_configure("cola", background="#fff8e1")
        self.jobs_tree.tag_configure("error", background="#ffebee")
        self.jobs_tree.tag_configure("pendiente", background="#ffffff")

        tree_scroll_y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.jobs_tree.yview)
        self.jobs_tree.configure(yscrollcommand=tree_scroll_y.set)
        self.jobs_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6, 0), pady=6)
        tree_scroll_y.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 6), pady=6)
        self.jobs_tree.bind("<<TreeviewSelect>>", self._on_job_selected)

        # Panel inferior: Detalle de actividad seleccionada y bitácora en vivo
        detail_notebook = ttk.Notebook(paned)
        paned.add(detail_notebook, weight=2)

        tab_sintesis = ttk.Frame(detail_notebook, padding=6)
        tab_fichas = ttk.Frame(detail_notebook, padding=6)
        tab_log = ttk.Frame(detail_notebook, padding=6)
        detail_notebook.add(tab_sintesis, text="  Síntesis e Investigación Amazon Nova Pro (3 Tiempos)  ")
        detail_notebook.add(tab_fichas, text="  Fichas de Conceptos e Ideas Extraídas  ")
        detail_notebook.add(tab_log, text="  Bitácora de Ejecución en Vivo  ")

        self.sintesis_text = tk.Text(tab_sintesis, wrap="word", height=10, font=("Consolas", 9))
        sintesis_scroll = ttk.Scrollbar(tab_sintesis, orient=tk.VERTICAL, command=self.sintesis_text.yview)
        self.sintesis_text.configure(yscrollcommand=sintesis_scroll.set)
        self.sintesis_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sintesis_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.fichas_preview_text = tk.Text(tab_fichas, wrap="word", height=10, font=("Consolas", 9))
        fichas_scroll = ttk.Scrollbar(tab_fichas, orient=tk.VERTICAL, command=self.fichas_preview_text.yview)
        self.fichas_preview_text.configure(yscrollcommand=fichas_scroll.set)
        self.fichas_preview_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        fichas_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.batch_log_text = tk.Text(tab_log, wrap="word", height=10, font=("Consolas", 9))
        log_scroll = ttk.Scrollbar(tab_log, orient=tk.VERTICAL, command=self.batch_log_text.yview)
        self.batch_log_text.configure(yscrollcommand=log_scroll.set)
        self.batch_log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def _choose_subject_dir(self) -> None:
        folder = filedialog.askdirectory(title="Selecciona la carpeta raíz de la materia")
        if not folder:
            return
        self.subject_dir_var.set(folder)
        self._init_tracker_and_refresh()

    def _append_batch_log(self, line: str) -> None:
        def _do() -> None:
            self.batch_log_text.insert(tk.END, line + "\n")
            self.batch_log_text.see(tk.END)
            self.batch_status_var.set(line[-95:])

        self.after(0, _do)

    def _init_tracker_and_refresh(self) -> None:
        subj_path = Path(self.subject_dir_var.get())
        if not subj_path.exists():
            return
        self.tracker = ActivityExtractionTracker(
            subj_path,
            on_log=self._append_batch_log,
            on_update=lambda st: self.after(0, lambda: self._render_tracker_state(st)),
        )
        self._render_tracker_state(self.tracker.state)

    def _poll_disk_state(self) -> None:
        """Sincroniza periódicamente desde estado-trabajos-extraccion.json en disco."""
        try:
            subj_path = Path(self.subject_dir_var.get())
            state_file = subj_path / "extractor-aulatex" / "estado-trabajos-extraccion.json"
            if state_file.exists() and not self.batch_running:
                raw = json.loads(state_file.read_text(encoding="utf-8"))
                self._render_tracker_state(raw)
        except Exception:
            pass
        finally:
            self.after(2000, self._poll_disk_state)

    def _render_tracker_state(self, state: dict[str, Any]) -> None:
        jobs = state.get("jobs", [])
        total = max(1, len(jobs))
        completed = sum(1 for j in jobs if j.get("status") == "Completado")
        overall = float(state.get("overall_progress", round(completed * 100.0 / total, 1)))
        total_sources = sum(int(j.get("sources_count", 0)) for j in jobs)
        total_fichas = sum(int(j.get("fichas_count", 0)) for j in jobs)
        total_ideas = sum(int(j.get("ideas_count", 0)) for j in jobs)
        total_tokens = sum(int(j.get("total_tokens", 0)) for j in jobs)

        self.global_progress_var.set(overall)
        self.summary_completed_var.set(f"Actividades: {completed} / {len(jobs)} ({overall:.1f}%)")
        self.summary_sources_var.set(f"Fuentes leídas: {total_sources}")
        self.summary_fichas_var.set(f"Fichas de conceptos: {total_fichas}")
        self.summary_ideas_var.set(f"Ideas (3 tiempos): {total_ideas}")
        self.summary_tokens_var.set(f"Tokens Nova Pro: {total_tokens:,}")

        selected_iids = self.jobs_tree.selection()
        for job in jobs:
            iid = f"A{int(job['num']):02d}"
            status = job.get("status", "Pendiente")
            tag = (
                "completado"
                if status == "Completado"
                else "ejecutando"
                if status == "En ejecución"
                else "cola"
                if status == "En cola"
                else "error"
                if status == "Error"
                else "pendiente"
            )
            values = (
                job.get("code", iid),
                job.get("module_id", ""),
                job.get("unit_title", ""),
                job.get("moodle_title", ""),
                job.get("kind", ""),
                status,
                job.get("stage", ""),
                f"{int(job.get('progress', 0))}%",
                job.get("sources_count", 0),
                job.get("concepts_count", 0),
                job.get("fichas_count", 0),
                job.get("ideas_count", 0),
                f"{int(job.get('total_tokens', 0)):,}",
                f"{float(job.get('elapsed_seconds', 0.0)):.1f}s",
            )
            if self.jobs_tree.exists(iid):
                self.jobs_tree.item(iid, values=values, tags=(tag,))
            else:
                self.jobs_tree.insert("", tk.END, iid=iid, values=values, tags=(tag,))

        if selected_iids:
            self.jobs_tree.selection_set(selected_iids)
            first_num = int(selected_iids[0].lstrip("A"))
            for j in jobs:
                if int(j["num"]) == first_num:
                    self.active_stage_progress_var.set(float(j.get("progress", 0)))
                    break
        elif jobs:
            self.jobs_tree.selection_set("A01")
            self._on_job_selected()

    def _get_selected_activity_numbers(self) -> list[int]:
        sel = self.jobs_tree.selection()
        return [int(iid.lstrip("A")) for iid in sel if iid.startswith("A")]

    def _on_job_selected(self, _event=None) -> None:
        nums = self._get_selected_activity_numbers()
        if not nums or not self.tracker:
            return
        num = nums[0]
        act = next((a for a in self.tracker.activities if int(a["num"]) == num), None)
        if not act:
            return
        paths = get_paths_for_activity(self.tracker.subject_dir, act)
        job = next((j for j in self.tracker.state.get("jobs", []) if int(j["num"]) == num), {})
        self.active_stage_progress_var.set(float(job.get("progress", 0)))

        # Cargar síntesis Nova Pro o consigna
        self.sintesis_text.delete("1.0", tk.END)
        header_info = (
            f"=== ACTIVIDAD {num} ({act['code']}) — {act['moodle_title']} ===\n"
            f"Carpeta conceptos (extractor-aulatex): {paths['extractor_conceptos_dir']}\n"
            f"Carpeta conceptos (referencias):       {paths['ref_conceptos_dir']}\n"
            f"Carpeta notas por actividad:           {paths['act_notes_dir']}\n\n"
        )
        self.sintesis_text.insert(tk.END, header_info)
        nova_md = paths["extractor_conceptos_dir"] / "sintesis_tres_tiempos_nova_pro.md"
        if nova_md.exists():
            self.sintesis_text.insert(tk.END, nova_md.read_text(encoding="utf-8", errors="replace"))
        elif paths["consigna_file"].exists():
            self.sintesis_text.insert(tk.END, paths["consigna_file"].read_text(encoding="utf-8", errors="replace"))

        # Cargar fichas de conceptos
        self.fichas_preview_text.delete("1.0", tk.END)
        fichas_md = paths["extractor_conceptos_dir"] / "fichas_conceptos.md"
        if fichas_md.exists():
            self.fichas_preview_text.insert(tk.END, fichas_md.read_text(encoding="utf-8", errors="replace")[:25000])
        else:
            self.fichas_preview_text.insert(tk.END, "Aún no se han generado fichas para esta actividad.")

    def _set_batch_buttons_state(self, running: bool) -> None:
        self.batch_running = running
        state_run = tk.DISABLED if running else tk.NORMAL
        self.btn_run_all.config(state=state_run)
        self.btn_run_pending.config(state=state_run)
        self.btn_run_selected.config(state=state_run)
        self.btn_rerun_force.config(state=state_run)
        self.btn_stop_batch.config(state=tk.NORMAL if running else tk.DISABLED)

    def _start_batch_extraction(self, *, mode: str, force_nova: bool) -> None:
        if self.batch_running:
            return
        self._init_tracker_and_refresh()
        if not self.tracker:
            return

        if mode == "all":
            target_nums = [int(a["num"]) for a in self.tracker.activities]
        elif mode == "pending":
            target_nums = [
                int(j["num"])
                for j in self.tracker.state.get("jobs", [])
                if j.get("status") != "Completado"
            ]
            if not target_nums:
                messagebox.showinfo("Completado", "Todas las 22 actividades ya cuentan con extracción completa.")
                return
        else:
            target_nums = self._get_selected_activity_numbers()
            if not target_nums:
                messagebox.showwarning("Selección vacía", "Selecciona al menos una actividad en la tabla.")
                return

        workers = max(1, int(self.batch_workers_var.get()))
        self._set_batch_buttons_state(True)

        def _worker() -> None:
            try:
                assert self.tracker is not None
                self.tracker.run_batch(target_nums, max_workers=workers, force_nova=force_nova)
                self.after(0, self._on_job_selected)
            except Exception as exc:
                self._append_batch_log(f"ERROR CRÍTICO EN LOTE: {exc}")
            finally:
                self.after(0, lambda: self._set_batch_buttons_state(False))

        threading.Thread(target=_worker, daemon=True).start()

    def _stop_batch_extraction(self) -> None:
        if self.tracker:
            self.tracker.stop_requested = True
            self._append_batch_log("Solicitando detención al finalizar las llamadas activas...")

    def _open_selected_conceptos_dir(self) -> None:
        nums = self._get_selected_activity_numbers() or [1]
        if not self.tracker:
            return
        act = next((a for a in self.tracker.activities if int(a["num"]) == nums[0]), None)
        if not act:
            return
        paths = get_paths_for_activity(self.tracker.subject_dir, act)
        target = paths["extractor_conceptos_dir"]
        target.mkdir(parents=True, exist_ok=True)
        os.startfile(target)  # type: ignore[attr-defined]

    def _open_selected_notas_dir(self) -> None:
        nums = self._get_selected_activity_numbers() or [1]
        if not self.tracker:
            return
        act = next((a for a in self.tracker.activities if int(a["num"]) == nums[0]), None)
        if not act:
            return
        paths = get_paths_for_activity(self.tracker.subject_dir, act)
        target = paths["act_notes_dir"]
        target.mkdir(parents=True, exist_ok=True)
        os.startfile(target)  # type: ignore[attr-defined]

    # ------------------------------------------------------------------
    # PESTAÑA 2: FLUJO MANUAL / INDIVIDUAL (ORIGINAL PRESERVADO)
    # ------------------------------------------------------------------
    def _build_manual_tab(self, frame: ttk.Frame) -> None:
        ttk.Label(frame, text="Extractor de conceptos e ideas (Modo Manual)", font=("Segoe UI", 14, "bold")).pack(anchor="w")
        ttk.Label(
            frame,
            text="Solo necesitas 3 cosas: carpeta de libros, archivo de planeación y carpeta base donde se creará la carpeta de resultados.",
            foreground="#444",
        ).pack(anchor="w", pady=(2, 10))

        info = ttk.LabelFrame(frame, text="Entradas esenciales")
        info.pack(fill=tk.X, pady=6)
        ttk.Label(info, text="1) Selecciona la carpeta de libros o fuentes de la materia.").pack(anchor="w", padx=10, pady=(8, 2))
        ttk.Label(info, text="2) Selecciona el archivo de planeación.").pack(anchor="w", padx=10, pady=2)
        ttk.Label(info, text="3) Selecciona la carpeta base donde se creará automáticamente la carpeta de conceptos.").pack(anchor="w", padx=10, pady=(2, 8))

        quick = ttk.LabelFrame(frame, text="Flujo principal")
        quick.pack(fill=tk.X, pady=8)
        quick_buttons = ttk.Frame(quick)
        quick_buttons.pack(fill=tk.X, padx=8, pady=8)
        ttk.Button(quick_buttons, text="1. Seleccionar carpeta de fuentes", command=self.add_source_folder).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(quick_buttons, text="2. Seleccionar planeación", command=self.select_planeacion).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(quick_buttons, text="3. Seleccionar carpeta base de salida", command=self.select_output_base).pack(side=tk.LEFT, padx=(0, 8))

        paths = ttk.LabelFrame(frame, text="Resumen de selección")
        paths.pack(fill=tk.BOTH, expand=False, pady=8)

        list_frame = ttk.Frame(paths)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=(8, 8))
        self.sources_list = tk.Listbox(list_frame, height=6, selectmode=tk.EXTENDED)
        self.sources_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.sources_list.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.sources_list.config(yscrollcommand=scroll.set)

        self.planeacion_label = ttk.Label(paths, text="Planeación: no seleccionada")
        self.planeacion_label.pack(anchor="w", padx=8, pady=(0, 4))
        self.output_base_label = ttk.Label(paths, text="Carpeta base de salida: no seleccionada")
        self.output_base_label.pack(anchor="w", padx=8, pady=(0, 4))
        self.output_target_label = ttk.Label(paths, text="Carpeta final de resultados: no definida")
        self.output_target_label.pack(anchor="w", padx=8, pady=(0, 4))
        self.conceptos_label = ttk.Label(paths, text="Conceptos: automático desde la planeación y el corpus")
        self.conceptos_label.pack(anchor="w", padx=8, pady=(0, 8))

        actions = ttk.Frame(frame)
        actions.pack(fill=tk.X, pady=8)
        self.run_button = ttk.Button(actions, text="Ejecutar extractor", command=self.run_pipeline)
        self.run_button.pack(side=tk.LEFT)
        ttk.Button(actions, text="Abrir carpeta de resultados", command=self.open_output_folder).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(actions, text="Mostrar / ocultar opciones avanzadas", command=self._toggle_advanced).pack(side=tk.RIGHT)

        self.advanced_frame = ttk.LabelFrame(frame, text="Opciones avanzadas")
        self.advanced_frame.pack(fill=tk.BOTH, expand=True, pady=8)
        grid = ttk.Frame(self.advanced_frame)
        grid.pack(fill=tk.X, padx=8, pady=8)
        ttk.Label(grid, text="Motor").grid(row=0, column=0, sticky="w", padx=(0, 6), pady=4)
        motor_combo = ttk.Combobox(
            grid,
            textvariable=self.workflow_var,
            values=["anthropicfoundry", "tfidf", "tfhub", "azure", "openai"],
            state="readonly",
            width=20,
        )
        motor_combo.grid(row=0, column=1, sticky="w", padx=(0, 12), pady=4)
        fields = [
            ("Umbral", self.threshold_var),
            ("Máx. caracteres fragmento", self.max_fragment_var),
            ("Mín. caracteres fragmento", self.min_fragment_var),
            ("Top K", self.top_k_var),
            ("Máx. citas", self.max_citas_var),
        ]
        for idx, (label, var) in enumerate(fields):
            ttk.Label(grid, text=label).grid(row=1, column=(idx % 3) * 2, sticky="w", padx=(0, 6), pady=4)
            ttk.Entry(grid, textvariable=var, width=10).grid(row=1, column=(idx % 3) * 2 + 1, sticky="w", padx=(0, 12), pady=4)
        ttk.Label(grid, text="Conceptos automáticos").grid(row=2, column=0, sticky="w", padx=(0, 6), pady=4)
        ttk.Spinbox(grid, from_=5, to=80, textvariable=self.auto_concepts_var, width=8).grid(row=2, column=1, sticky="w", padx=(0, 12), pady=4)
        ttk.Label(grid, text="Extensiones").grid(row=2, column=2, sticky="w", padx=(0, 6), pady=4)
        ttk.Entry(grid, textvariable=self.extensions_var, width=22).grid(row=2, column=3, sticky="w", padx=(0, 12), pady=4)
        ttk.Checkbutton(grid, text="Buscar en subcarpetas", variable=self.recursive_var).grid(row=2, column=4, sticky="w", padx=(0, 12), pady=4)
        ttk.Checkbutton(grid, text="Limpiar input de prueba antes de copiar", variable=self.clean_inputs_var).grid(
            row=3, column=0, columnspan=2, sticky="w", padx=(0, 12), pady=4
        )
        ttk.Checkbutton(grid, text="Limpiar output antes de ejecutar", variable=self.clean_output_var).grid(
            row=3, column=2, columnspan=2, sticky="w", padx=(0, 12), pady=4
        )
        ttk.Checkbutton(grid, text="Usar conceptos previsualizados/editados", variable=self.use_previewed_concepts_var).grid(
            row=3, column=4, sticky="w", padx=(0, 12), pady=4
        )

        concepts_frame = ttk.LabelFrame(self.advanced_frame, text="Conceptos automáticos y edición manual")
        concepts_frame.pack(fill=tk.BOTH, expand=True, pady=8)
        concept_actions = ttk.Frame(concepts_frame)
        concept_actions.pack(fill=tk.X, padx=8, pady=8)
        ttk.Button(concept_actions, text="Previsualizar conceptos", command=self.preview_concepts).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(concept_actions, text="Seleccionar conceptos opcionales", command=self.select_conceptos).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(concept_actions, text="Cargar conceptos desde archivo", command=self.load_selected_concepts_into_editor).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(concept_actions, text="Limpiar editor", command=self.clear_concepts_editor).pack(side=tk.LEFT)

        self.concepts_editor = tk.Text(concepts_frame, wrap="word", height=8)
        self.concepts_editor.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        self.concepts_editor.insert("1.0", "# Un concepto por línea.\n# Puedes previsualizar, editar o pegar tu propia lista.\n")

        self.status_var = tk.StringVar(value="Listo.")
        ttk.Label(frame, textvariable=self.status_var, foreground="#0a5").pack(anchor="w", pady=(4, 6))

        ttk.Label(frame, text="Retroalimentación", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.feedback = tk.Text(frame, wrap="word", height=8)
        self.feedback.pack(fill=tk.BOTH, expand=True)
        self.feedback.insert("1.0", "Aquí aparecerá el resumen de calidad y ejecución.\n")
        self.feedback.configure(state=tk.DISABLED)

        self.advanced_frame.pack_forget()

    def _append_feedback(self, text: str) -> None:
        self.feedback.configure(state=tk.NORMAL)
        self.feedback.insert(tk.END, text + "\n")
        self.feedback.see(tk.END)
        self.feedback.configure(state=tk.DISABLED)

    def _set_status(self, text: str) -> None:
        self.after(0, lambda: self.status_var.set(text))

    def _append_feedback_async(self, text: str) -> None:
        self.after(0, lambda: self._append_feedback(text))

    def _toggle_advanced(self) -> None:
        if self.advanced_frame.winfo_ismapped():
            self.advanced_frame.pack_forget()
        else:
            self.advanced_frame.pack(fill=tk.BOTH, expand=True, pady=8, before=self.feedback)

    def _recompute_output_target(self) -> None:
        if not self.output_base_dir:
            self.derived_output_dir = None
            self.output_target_label.config(text="Carpeta final de resultados: no definida")
            return

        subject_slug = _infer_subject_slug(self.fuentes_items, self.planeacion_path)
        week_code = _infer_week_code_from_name_or_text(self.planeacion_path) or "S00"
        folder_name = f"conceptos-{subject_slug}-{week_code}"
        self.derived_output_dir = self.output_base_dir / folder_name
        self.output_target_label.config(text=f"Carpeta final de resultados: {self.derived_output_dir}")

    def _set_running(self, running: bool) -> None:
        self.is_running = running
        self.run_button.config(state=tk.DISABLED if running else tk.NORMAL)
        self.run_button.config(text="Ejecutando..." if running else "Ejecutar extractor")

    def _set_concepts_text(self, concepts: list[str], *, header: str | None = None) -> None:
        self.concepts_editor.delete("1.0", tk.END)
        if header:
            self.concepts_editor.insert(tk.END, f"# {header}\n")
        for concept in concepts:
            self.concepts_editor.insert(tk.END, concept + "\n")

    def _read_manual_concepts(self) -> list[str]:
        text = self.concepts_editor.get("1.0", tk.END)
        concepts: list[str] = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            concepts.append(stripped)
        return unique_preserve_order(concepts)

    def _write_runtime_concepts_file(self) -> Path | None:
        concepts = self._read_manual_concepts()
        if not concepts:
            return None
        runtime_path = INPUT_PLANEACIONES / "_conceptos_gui_runtime.txt"
        runtime_path.write_text("\n".join(concepts) + "\n", encoding="utf-8")
        return runtime_path

    def _get_extensions(self) -> set[str]:
        return parse_extensions(self.extensions_var.get())

    def _collect_preview_fragments(self):
        preview_root = ROOT / "input" / "_gui_preview_fuentes"
        if preview_root.exists():
            shutil.rmtree(preview_root)
        preview_root.mkdir(parents=True, exist_ok=True)
        for item in self.fuentes_items:
            target = preview_root / item.name
            if item.is_dir():
                shutil.copytree(item, target)
            else:
                shutil.copy2(item, target)
        pages, report = extract_pages_from_sources(
            preview_root,
            recursive=self.recursive_var.get(),
            extensions=self._get_extensions(),
        )
        fragments = build_fragments(
            pages,
            max_chars=int(self.max_fragment_var.get()),
            min_chars=int(self.min_fragment_var.get()),
        )
        return preview_root, pages, report, fragments

    def remove_selected_sources(self) -> None:
        selected = list(self.sources_list.curselection())
        if not selected:
            return
        for idx in reversed(selected):
            self.sources_list.delete(idx)
            del self.fuentes_items[idx]
        self._recompute_output_target()
        self.status_var.set(f"Fuentes seleccionadas: {len(self.fuentes_items)}")

    def clear_sources(self) -> None:
        self.sources_list.delete(0, tk.END)
        self.fuentes_items.clear()
        self._recompute_output_target()
        self.status_var.set("Fuentes limpiadas")

    def clear_concepts_editor(self) -> None:
        self.previewed_concepts = []
        self._set_concepts_text([], header="Un concepto por línea")

    def load_selected_concepts_into_editor(self) -> None:
        if not self.conceptos_path:
            messagebox.showinfo("Sin archivo", "Primero selecciona un archivo de conceptos.")
            return
        concepts = load_concept_lines(str(self.conceptos_path))
        self.previewed_concepts = concepts
        self._set_concepts_text(concepts, header="Conceptos cargados desde archivo")
        self.status_var.set(f"Conceptos cargados: {len(concepts)}")

    def preview_concepts(self) -> None:
        if not self.fuentes_items and not self.planeacion_path and not self.conceptos_path:
            messagebox.showwarning("Faltan entradas", "Agrega fuentes, planeación o conceptos antes de previsualizar.")
            return
        try:
            from_file = load_concept_lines(str(self.conceptos_path)) if self.conceptos_path else []
            from_plan = []
            if self.planeacion_path:
                planeacion_text = read_any_text_file(self.planeacion_path)
                if planeacion_text.strip():
                    analysis = parse_planeacion_text(planeacion_text)
                    summary = summarize_planeacion_analysis(analysis)
                    if summary:
                        self._append_feedback(f"Interpretación de planeación: {summary}")
                    from_plan = extract_candidate_concepts_from_planeacion(analysis, top_n=self.auto_concepts_var.get())
            from_corpus = []
            loaded_files = 0
            fragment_count = 0
            preview_root = None
            if self.fuentes_items:
                preview_root, pages, report, fragments = self._collect_preview_fragments()
                loaded_files = len(report.loaded_files)
                fragment_count = len(fragments)
                from_corpus = extract_candidate_concepts(fragments, top_n=self.auto_concepts_var.get())
            concepts = unique_preserve_order(from_file + from_plan + from_corpus)
            self.previewed_concepts = concepts
            self._set_concepts_text(concepts, header="Conceptos previsualizados y editables")
            self._append_feedback(
                f"Previsualización: archivo={len(from_file)}, planeación={len(from_plan)}, corpus={len(from_corpus)}, total={len(concepts)}"
            )
            if loaded_files or fragment_count:
                self._append_feedback(f"Vista previa corpus: fuentes útiles={loaded_files}, fragmentos={fragment_count}")
            self.status_var.set(f"Conceptos previsualizados: {len(concepts)}")
            if preview_root and preview_root.exists():
                shutil.rmtree(preview_root)
        except Exception as exc:
            messagebox.showerror("Error al previsualizar", str(exc))

    def _copy_to_sources(self, src: Path) -> None:
        target = INPUT_FUENTES / src.name
        if src.is_dir():
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(src, target)
        else:
            shutil.copy2(src, target)

    def add_source_files(self) -> None:
        files = filedialog.askopenfilenames(title="Selecciona archivos fuente")
        if not files:
            return
        for raw in files:
            path = Path(raw)
            if path.suffix.lower() in ALLOWED_SOURCE_EXTS:
                self.fuentes_items.append(path)
                self.sources_list.insert(tk.END, str(path))
        self._recompute_output_target()
        self.status_var.set(f"Fuentes seleccionadas: {len(self.fuentes_items)}")

    def add_source_folder(self) -> None:
        folder = filedialog.askdirectory(title="Selecciona carpeta de fuentes")
        if not folder:
            return
        path = Path(folder)
        self.fuentes_items.append(path)
        self.sources_list.insert(tk.END, str(path))
        self._recompute_output_target()
        self.status_var.set(f"Fuentes seleccionadas: {len(self.fuentes_items)}")

    def select_planeacion(self) -> None:
        file = filedialog.askopenfilename(title="Selecciona planeación", filetypes=[("Documentos", "*.pdf *.docx *.txt *.md")])
        if not file:
            return
        self.planeacion_path = Path(file)
        self.planeacion_label.config(text=f"Planeación: {self.planeacion_path}")
        self._recompute_output_target()

    def select_output_base(self) -> None:
        folder = filedialog.askdirectory(title="Selecciona carpeta base donde se creará la carpeta de resultados")
        if not folder:
            return
        self.output_base_dir = Path(folder)
        self.output_base_label.config(text=f"Carpeta base de salida: {self.output_base_dir}")
        self._recompute_output_target()

    def select_conceptos(self) -> None:
        file = filedialog.askopenfilename(title="Selecciona archivo de conceptos", filetypes=[("Texto", "*.txt *.md")])
        if not file:
            return
        self.conceptos_path = Path(file)
        self.conceptos_label.config(text=f"Conceptos: {self.conceptos_path}")

    def _reset_dir(self, path: Path) -> None:
        if path.exists():
            shutil.rmtree(path)
        path.mkdir(parents=True, exist_ok=True)

    def _prepare_inputs(self) -> None:
        INPUT_FUENTES.mkdir(parents=True, exist_ok=True)
        INPUT_PLANEACIONES.mkdir(parents=True, exist_ok=True)
        if self.clean_inputs_var.get():
            self._reset_dir(INPUT_FUENTES)
            self._reset_dir(INPUT_PLANEACIONES)
        for item in self.fuentes_items:
            self._copy_to_sources(item)
        if self.planeacion_path:
            shutil.copy2(self.planeacion_path, INPUT_PLANEACIONES / self.planeacion_path.name)
        if self.conceptos_path and not self.use_previewed_concepts_var.get():
            shutil.copy2(self.conceptos_path, INPUT_PLANEACIONES / self.conceptos_path.name)

    def _build_args(self) -> list[str]:
        planeacion = (
            INPUT_PLANEACIONES / self.planeacion_path.name
            if self.planeacion_path
            else INPUT_PLANEACIONES / "planeacion_ejemplo.txt"
        )
        output_dir = self.derived_output_dir or GUI_OUTPUT
        args = [
            "--motor",
            self.workflow_var.get(),
            "--fuentes",
            str(INPUT_FUENTES),
            "--planeacion",
            str(planeacion),
            "--salida",
            str(output_dir),
            "--umbral",
            self.threshold_var.get(),
            "--max-caracteres-fragmento",
            self.max_fragment_var.get(),
            "--min-caracteres-fragmento",
            self.min_fragment_var.get(),
            "--top-k",
            self.top_k_var.get(),
            "--max-citas",
            self.max_citas_var.get(),
            "--auto-conceptos",
            str(self.auto_concepts_var.get()),
            "--extensiones",
            self.extensions_var.get(),
        ]
        if self.workflow_var.get() == "anthropicfoundry":
            args.extend(["--auto-conceptos-motor", "anthropic-chat", "--normalizar-conceptos-con-chat", "--planeacion-asistida-con-chat"])
        args.append("--recursivo" if self.recursive_var.get() else "--no-recursivo")
        runtime_concepts = self._write_runtime_concepts_file() if self.use_previewed_concepts_var.get() else None
        if runtime_concepts:
            args.extend(["--conceptos", str(runtime_concepts)])
        elif self.conceptos_path:
            args.extend(["--conceptos", str(INPUT_PLANEACIONES / self.conceptos_path.name)])
        return args

    def _summarize_results(self) -> None:
        output_dir = self.derived_output_dir or GUI_OUTPUT
        md_path = output_dir / "fichas_conceptos.md"
        if not md_path.exists():
            self._append_feedback("No se encontró el archivo Markdown de salida.")
            return
        text = md_path.read_text(encoding="utf-8")
        alta = text.count("**Calidad estimada:** alta")
        media = text.count("**Calidad estimada:** media")
        baja = text.count("**Calidad estimada:** baja")
        sin_hallazgos = text.count("**Calidad estimada:** sin hallazgos")
        self._append_feedback("Ejecución completada.")
        self._append_feedback(f"Calidad alta: {alta} | media: {media} | baja: {baja} | sin hallazgos: {sin_hallazgos}")
        if baja or sin_hallazgos:
            self._append_feedback("Sugerencia: subir el umbral o usar conceptos más específicos para reducir ruido.")
        else:
            self._append_feedback("Resultado consistente: predominan fichas con señales útiles de calidad.")
        self._append_feedback(f"Salida disponible en: {output_dir}")

    def run_pipeline(self) -> None:
        if self.is_running:
            return
        if not self.fuentes_items:
            messagebox.showwarning("Faltan fuentes", "Agrega al menos un archivo o carpeta de fuentes.")
            return
        if not self.planeacion_path:
            messagebox.showwarning("Falta planeación", "Selecciona un archivo de planeación.")
            return
        if not self.output_base_dir:
            messagebox.showwarning("Falta carpeta base de salida", "Selecciona la carpeta base donde se creará la carpeta de resultados.")
            return

        def worker() -> None:
            try:
                self.after(0, lambda: self._set_running(True))
                self._set_status("Preparando entradas...")
                self._append_feedback_async("--- Nueva ejecución ---")
                self._append_feedback_async("Preparando archivos de entrada...")
                self._prepare_inputs()
                output_dir = self.derived_output_dir or GUI_OUTPUT
                if self.clean_output_var.get():
                    self._append_feedback_async(f"Limpiando salida previa: {output_dir}")
                    self._reset_dir(output_dir)
                args = self._build_args()
                concepts_count = len(self._read_manual_concepts()) if self.use_previewed_concepts_var.get() else 0
                if concepts_count:
                    self._append_feedback_async(f"Se ejecutará con {concepts_count} conceptos revisados manualmente.")
                self._append_feedback_async(f"Salida objetivo: {output_dir}")
                self._append_feedback_async("Iniciando flujo del extractor...")
                self._set_status("Ejecutando flujo...")
                writer = _FeedbackWriter(self._append_feedback_async)
                with contextlib.redirect_stdout(writer), contextlib.redirect_stderr(writer):
                    cli_main(args)
                writer.flush()
                self._set_status("Ejecución finalizada")
                self.after(0, self._summarize_results)
            except Exception as exc:
                self._set_status("Error durante la ejecución")
                self._append_feedback_async(f"ERROR: {exc}")
                self.after(0, lambda: messagebox.showerror("Error", str(exc)))
            finally:
                self.after(0, lambda: self._set_running(False))

        threading.Thread(target=worker, daemon=True).start()

    def open_output_folder(self) -> None:
        output_dir = self.derived_output_dir or GUI_OUTPUT
        output_dir.mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(output_dir)  # type: ignore[attr-defined]
        except Exception as exc:
            messagebox.showerror("No se pudo abrir", str(exc))


def main() -> None:
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
