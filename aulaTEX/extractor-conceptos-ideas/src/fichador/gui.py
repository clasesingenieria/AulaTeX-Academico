from __future__ import annotations

import contextlib
import re
import shutil
import threading
import unicodedata
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .cli import main as cli_main
from .concept_extractor import extract_candidate_concepts, extract_candidate_concepts_from_planeacion
from .document_reader import extract_pages_from_sources, parse_extensions, read_any_text_file
from .preprocessing import build_fragments, load_concept_lines, unique_preserve_order
from .planeacion_parser import parse_planeacion_text, summarize_planeacion_analysis

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
                    return _slugify(low[len(prefix):])
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
        self.title("Extractor de conceptos e ideas")
        self.geometry("940x700")
        self.minsize(860, 620)

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

    def _build_ui(self) -> None:
        frame = ttk.Frame(self, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Extractor de conceptos e ideas", font=("Segoe UI", 14, "bold")).pack(anchor="w")
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
        self.sources_list = tk.Listbox(list_frame, height=8, selectmode=tk.EXTENDED)
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
        motor_combo = ttk.Combobox(grid, textvariable=self.workflow_var, values=["anthropicfoundry", "tfidf", "tfhub", "azure", "openai"], state="readonly", width=20)
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
        ttk.Checkbutton(grid, text="Limpiar input de prueba antes de copiar", variable=self.clean_inputs_var).grid(row=3, column=0, columnspan=2, sticky="w", padx=(0, 12), pady=4)
        ttk.Checkbutton(grid, text="Limpiar output antes de ejecutar", variable=self.clean_output_var).grid(row=3, column=2, columnspan=2, sticky="w", padx=(0, 12), pady=4)
        ttk.Checkbutton(grid, text="Usar conceptos previsualizados/editados", variable=self.use_previewed_concepts_var).grid(row=3, column=4, sticky="w", padx=(0, 12), pady=4)

        concepts_frame = ttk.LabelFrame(self.advanced_frame, text="Conceptos automáticos y edición manual")
        concepts_frame.pack(fill=tk.BOTH, expand=True, pady=8)
        concept_actions = ttk.Frame(concepts_frame)
        concept_actions.pack(fill=tk.X, padx=8, pady=8)
        ttk.Button(concept_actions, text="Previsualizar conceptos", command=self.preview_concepts).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(concept_actions, text="Seleccionar conceptos opcionales", command=self.select_conceptos).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(concept_actions, text="Cargar conceptos desde archivo", command=self.load_selected_concepts_into_editor).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(concept_actions, text="Limpiar editor", command=self.clear_concepts_editor).pack(side=tk.LEFT)

        self.concepts_editor = tk.Text(concepts_frame, wrap="word", height=10)
        self.concepts_editor.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        self.concepts_editor.insert("1.0", "# Un concepto por línea.\n# Puedes previsualizar, editar o pegar tu propia lista.\n")

        self.status_var = tk.StringVar(value="Listo.")
        ttk.Label(frame, textvariable=self.status_var, foreground="#0a5").pack(anchor="w", pady=(4, 6))

        ttk.Label(frame, text="Retroalimentación", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.feedback = tk.Text(frame, wrap="word", height=10)
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
        planeacion = INPUT_PLANEACIONES / self.planeacion_path.name if self.planeacion_path else INPUT_PLANEACIONES / "planeacion_ejemplo.txt"
        output_dir = self.derived_output_dir or GUI_OUTPUT
        args = [
            "--motor", self.workflow_var.get(),
            "--fuentes", str(INPUT_FUENTES),
            "--planeacion", str(planeacion),
            "--salida", str(output_dir),
            "--umbral", self.threshold_var.get(),
            "--max-caracteres-fragmento", self.max_fragment_var.get(),
            "--min-caracteres-fragmento", self.min_fragment_var.get(),
            "--top-k", self.top_k_var.get(),
            "--max-citas", self.max_citas_var.get(),
            "--auto-conceptos", str(self.auto_concepts_var.get()),
            "--extensiones", self.extensions_var.get(),
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
            import os
            os.startfile(output_dir)  # type: ignore[attr-defined]
        except Exception as exc:
            messagebox.showerror("No se pudo abrir", str(exc))


def main() -> None:
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
