from __future__ import annotations

import os
import queue
import re
import subprocess
import threading
import tkinter as tk
import json
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

from .activity_monitor import ActivityMonitor, ActivityMonitorRequest
from .agent import AgentRequest, AulaTeXAgent
from .agentic_patterns import pattern_catalog_markdown
from .chat_sessions import AulaTeXChatStore, MULTIMOTOR_SEVERITY_LABELS, multimotor_severity_label
from .config import (
    credential_catalog,
    credential_status,
    diagnostic_metrics_enabled,
    encrypt_env_secrets,
    read_env_values,
    write_env_values,
)
from .construction import ConstructionBuilder, ConstructionEvent, ConstructionRequest, ConstructionStore
from .editorial_memory import (
    EDITORIAL_LEVELS,
    ENGINE_PRIORITY,
    MEMORY_SECTIONS,
    EditorialMemoryBuilder,
    EditorialMemoryEvent,
    EditorialMemoryRequest,
    EditorialMemoryStore,
)
from .investigation import (
    KNOWLEDGE_SECTIONS,
    InvestigationBuildResult,
    InvestigationBuilder,
    InvestigationEvent,
    InvestigationRequest,
    InvestigationStore,
)
from .llm_bridge import DEFAULT_MAX_TOKENS, LLM_ENGINES, AulaTeXLLMClient
from .gui_widgets import EnginePicker, ScrollableForm
from .workspace import GENERATION_MARKER_FILENAME, AulaTeXWorkspace, EditorialScope


UNSELECTED_OPTION = "Sin seleccionar"
PROPAGATION_LABELS = {
    "local": "Solo origen",
    "lateral": "Lateral entre hermanos",
    "ascendente": "Ascendente",
    "ascendente-exhaustivo": "Ascendente exhaustivo",
    "descendente": "Descendente padre→hijo",
    "recursivo": "Recursivo completo",
    "bidireccional": "Bidireccional progresivo",
}
PROPAGATION_VALUES = tuple(PROPAGATION_LABELS)


class ToolTip:
    def __init__(self, widget, text: str, *, wraplength: int = 340) -> None:
        self.widget = widget
        self.text = text
        self.wraplength = wraplength
        self.tip_window: tk.Toplevel | None = None
        self.widget.bind("<Enter>", self._show, add="+")
        self.widget.bind("<Leave>", self._hide, add="+")
        self.widget.bind("<ButtonPress>", self._hide, add="+")

    def _show(self, _event=None) -> None:
        if self.tip_window is not None or not self.text.strip():
            return
        x = self.widget.winfo_rootx() + 18
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 10
        self.tip_window = tk.Toplevel(self.widget)
        self.tip_window.wm_overrideredirect(True)
        self.tip_window.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            self.tip_window,
            text=self.text,
            justify="left",
            background="#fffde7",
            relief="solid",
            borderwidth=1,
            wraplength=self.wraplength,
            padx=8,
            pady=6,
        )
        label.pack()

    def _hide(self, _event=None) -> None:
        if self.tip_window is not None:
            self.tip_window.destroy()
            self.tip_window = None


class AulaTeXApp(tk.Tk):
    def __init__(self, *, diagnostics_enabled: bool | None = None) -> None:
        super().__init__()
        self.title("AulaTeX - suite editorial e investigacion")
        self.geometry("1180x760")
        self.minsize(980, 640)

        self.diagnostics_enabled = diagnostic_metrics_enabled() if diagnostics_enabled is None else diagnostics_enabled
        self.workspace = AulaTeXWorkspace()
        self.llm = AulaTeXLLMClient()
        self.chat_store = AulaTeXChatStore(self.workspace, self.llm)
        self.agent = AulaTeXAgent(self.workspace, self.llm)
        self.editorial_store = EditorialMemoryStore(self.workspace, diagnostics_enabled=self.diagnostics_enabled)
        self.editorial_builder = EditorialMemoryBuilder(self.workspace, self.llm, self.editorial_store)
        self.investigation_store = InvestigationStore(self.workspace, diagnostics_enabled=self.diagnostics_enabled)
        self.investigation_builder = InvestigationBuilder(self.workspace, self.llm, self.investigation_store, self.editorial_store)
        self.construction_store = ConstructionStore(self.workspace, diagnostics_enabled=self.diagnostics_enabled)
        self.construction_builder = ConstructionBuilder(self.workspace, self.llm, self.construction_store, self.editorial_store)
        self.editorial_scopes = {}
        self.editorial_children = {}
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self._tooltips: list[ToolTip] = []
        self._busy_groups: dict[str, list[tuple[object, str]]] = {}
        self.llm_session_nodes: dict[str, str] = {}
        self.template_node_values: dict[str, tuple[str, str, str]] = {}
        self._tree_refresh_pending = False
        self._tree_refresh_queued = False
        self.llm_multi_severity = tk.StringVar(value="normal")
        self.feedback_cancel_event = threading.Event()
        self.feedback_resume_checkpoint = tk.StringVar(value="")
        self.investigation_cancel_event = threading.Event()
        self.generation_cancel_event = threading.Event()

        self._build_ui()
        self.after(250, self._drain_events)

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self._active_jobs = set()
        self._aux_windows = {}
        self._result_paths = {}
        self.context_key = ""
        self.context_label = tk.StringVar(self, value="Sin proyecto seleccionado")
        self.task_status = tk.StringVar(self, value="Listo")
        header = ttk.Frame(self, padding=(12, 8))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(1, weight=1)
        ttk.Label(header, text="AulaTeX", font=("TkDefaultFont", 14, "bold")).grid(row=0, column=0, padx=(0, 20))
        ttk.Label(header, textvariable=self.context_label, wraplength=600).grid(row=0, column=1, sticky="w")
        results_button = ttk.Menubutton(header, text="Resultados")
        results_button.grid(row=0, column=2, sticky="e")
        self.results_menu = tk.Menu(results_button, tearoff=False)
        self._result_indices = {}
        for index, (group, label) in enumerate((("compile", "Último PDF"), ("agent", "Informe del agente"),
                ("generation", "Nodo generado"), ("investigation", "Investigación"),
                ("feedback", "Memoria"), ("llm-chat", "Chat exportado"))):
            self._result_indices[group] = index
            self.results_menu.add_command(label=label, state="disabled", command=lambda key=group: self._open_result(key))
        results_button.configure(menu=self.results_menu)
        self.main_notebook = ttk.Notebook(self)
        self.main_notebook.grid(row=1, column=0, sticky="nsew")
        notebook = self.main_notebook
        self.panel_tab = ttk.Frame(notebook, padding=12)
        self.investigation_tab = ttk.Frame(notebook, padding=12)
        self.production_tab = ttk.Notebook(notebook)
        self.feedback_tab = ttk.Frame(notebook, padding=12)
        self.llm_tab = ttk.Frame(notebook, padding=12)
        for frame, title in ((self.panel_tab, "Proyecto"), (self.investigation_tab, "Investigación"),
                             (self.production_tab, "Producción"), (self.feedback_tab, "Memoria"),
                             (self.llm_tab, "Asistente")):
            notebook.add(frame, text=title)
        self.builder_tab = ttk.Frame(self.production_tab, padding=12)
        self.agent_tab = ttk.Frame(self.production_tab, padding=12)
        self.compile_tab = ttk.Frame(self.production_tab, padding=12)
        for frame, title in ((self.builder_tab, "Generar"), (self.agent_tab, "Revisar / ejecutar"),
                             (self.compile_tab, "Compilar")):
            self.production_tab.add(frame, text=title)
        menu = tk.Menu(self)
        tools = tk.Menu(menu, tearoff=False)
        tools.add_command(label="Extractor", command=self._open_tools)
        tools.add_command(label="Comprobar proveedores IA", command=self._check_llms)
        menu.add_cascade(label="Herramientas", menu=tools)
        menu.add_command(label="Configuración", command=self._open_settings)
        view_menu = tk.Menu(menu, tearoff=False)
        resolution_menu = tk.Menu(view_menu, tearoff=False)
        for width, height in ((980, 640), (1180, 760), (1366, 768), (1600, 900), (1920, 1080)):
            resolution_menu.add_command(label=f"{width} x {height}",
                                        command=lambda size=(width, height): self._set_resolution(*size))
        resolution_menu.add_separator()
        resolution_menu.add_command(label="Ajustar al monitor", command=self._fit_monitor)
        resolution_menu.add_command(label="Maximizar", command=self._maximize_window)
        resolution_menu.add_command(label="Restaurar tamaño inicial", command=lambda: self._set_resolution(1180, 760))
        view_menu.add_cascade(label="Resolución", menu=resolution_menu)
        menu.add_cascade(label="Vista", menu=view_menu)
        help_menu = tk.Menu(menu, tearoff=False)
        help_menu.add_command(label="Arquitectura", command=self._show_architecture)
        menu.add_cascade(label="Ayuda", menu=help_menu)
        self.configure(menu=menu)
        ttk.Label(self, textvariable=self.task_status, padding=(12, 4)).grid(row=2, column=0, sticky="ew")
        self.protocol("WM_DELETE_WINDOW", self._request_close)

        self._build_panel_tab()
        self._build_llm_tab()
        self._build_agent_tab()
        self._build_builder_tab()
        self._build_feedback_tab()
        self._build_investigation_tab()
        self._build_compile_tab()

    def _monitor_work_area(self) -> tuple[int, int, int, int]:
        if os.name == "nt":
            import ctypes
            from ctypes import wintypes

            class MonitorInfo(ctypes.Structure):
                _fields_ = [("size", wintypes.DWORD), ("monitor", wintypes.RECT),
                            ("work", wintypes.RECT), ("flags", wintypes.DWORD)]

            user32 = ctypes.windll.user32
            user32.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
            user32.MonitorFromWindow.restype = wintypes.HANDLE
            user32.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MonitorInfo)]
            user32.GetMonitorInfoW.restype = wintypes.BOOL
            info = MonitorInfo()
            info.size = ctypes.sizeof(info)
            monitor = user32.MonitorFromWindow(self.winfo_id(), 2)
            if user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
                return info.work.left, info.work.top, info.work.right, info.work.bottom
        return 0, 0, self.winfo_screenwidth(), self.winfo_screenheight()

    def _set_resolution(self, width: int, height: int) -> None:
        self.state("normal")
        self.update_idletasks()
        left, top, right, bottom = self._monitor_work_area()
        available_width = max(1, right - left - 32)
        available_height = max(1, bottom - top - 80)
        width = min(width, available_width)
        height = min(height, available_height)
        self.minsize(min(980, width), min(640, height))
        self.geometry(f"{width}x{height}")
        self.task_status.set(f"Resolución de ventana: {width} x {height}")

    def _fit_monitor(self) -> None:
        left, top, right, bottom = self._monitor_work_area()
        self._set_resolution(right - left, bottom - top)

    def _maximize_window(self) -> None:
        try:
            self.state("zoomed")
        except tk.TclError:
            self._fit_monitor()

    def _open_auxiliary(self, key, title, pages) -> None:
        existing = self._aux_windows.get(key)
        if existing is not None and existing.winfo_exists():
            existing.deiconify()
            existing.lift()
            return
        window = tk.Toplevel(self)
        window.title(f"AulaTeX - {title}")
        window.geometry("1000x700")
        window.minsize(900, 600)
        window.transient(self)
        self._aux_windows[key] = window
        notebook = ttk.Notebook(window)
        notebook.pack(fill="both", expand=True)
        for attribute, label, builder in pages:
            if attribute == "platforms_tab":
                frame = self._build_platforms_tab(notebook)
                setattr(self, attribute, frame)
            else:
                frame = ttk.Frame(notebook, padding=12)
                setattr(self, attribute, frame)
                getattr(self, builder)()
            notebook.add(frame, text=label)
        window.protocol("WM_DELETE_WINDOW", lambda: self._close_auxiliary(key))

    def _close_auxiliary(self, key) -> None:
        if key == "tools" and "extractor" in self._active_jobs:
            messagebox.showinfo("AulaTeX", "Espera a que termine la comprobación del extractor.", parent=self)
            return
        if key == "settings":
            for variable in getattr(self, "_credential_vars", {}).values():
                variable.set("")
            if hasattr(self.platforms_tab, "_lock"):
                self.platforms_tab._lock()
        self._aux_windows.pop(key).destroy()

    def _open_settings(self) -> None:
        self._open_auxiliary("settings", "Configuración", (
            ("credentials_tab", "Proveedores IA", "_build_credentials_tab"),
            ("platforms_tab", "Cuentas institucionales", "_build_platforms_tab"),
        ))

    def _open_tools(self) -> None:
        self._open_auxiliary("tools", "Herramientas", (("extractor_tab", "Extractor", "_build_extractor_tab"),))

    def _show_architecture(self) -> None:
        self._open_auxiliary("help", "Ayuda", (("arch_tab", "Arquitectura", "_build_arch_tab"),))

    def _request_close(self) -> None:
        if self._active_jobs:
            messagebox.showinfo("AulaTeX", "Hay tareas en curso. Cancela las tareas que lo permitan y espera a que terminen antes de cerrar.", parent=self)
            return
        self.destroy()

    def _record_result(self, group, path) -> None:
        if path is None:
            return
        resolved = (self.workspace.repo_root / Path(path)).resolve()
        if resolved.exists():
            self._result_paths[group] = resolved
            self.results_menu.entryconfigure(self._result_indices[group], state="normal")

    def _open_result(self, group) -> None:
        path = self._result_paths.get(group)
        if path is None or not path.exists():
            messagebox.showinfo("AulaTeX", "El resultado ya no está disponible.", parent=self)
            return
        try:
            if os.name == "nt":
                os.startfile(str(path))
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except OSError as exc:
            messagebox.showerror("AulaTeX", f"No se pudo abrir el resultado: {exc}", parent=self)

    def _use_selected_scope(self) -> None:
        if self._active_jobs:
            messagebox.showinfo("AulaTeX", "Espera a que terminen las tareas antes de cambiar de proyecto.", parent=self)
            return
        selected = self.template_tree.selection()
        scope = self.template_nodes.get(selected[0]) if selected else None
        if scope is None:
            messagebox.showinfo("AulaTeX", "Selecciona un nodo del proyecto.", parent=self)
            return
        self.context_key = scope.key
        self.context_label.set(" / ".join(value for value in (
            scope.institution, scope.career, scope.subject, scope.activity) if value) or scope.label)
        for prefix in ("feedback", "investigation", "generation"):
            for field in ("institution", "career", "subject", "activity"):
                variable = getattr(self, f"{prefix}_{field}", None)
                if variable is not None:
                    variable.set(getattr(scope, field, "") or UNSELECTED_OPTION)
        self.generation_node_level.set({"interinstitucional": "institucion", "institucion": "carrera",
                                        "carrera": "materia"}.get(scope.level, "actividad"))
        self.agent_target.set(scope.relative_path if scope.level != "interinstitucional" else "")
        self.agent_level.set("materia" if scope.level == "actividad" else scope.level)
        activity = re.search(r"\d+", scope.activity)
        self.agent_activity.set(int(activity.group()) if activity else 1)
        self.generation_activity_number.set(self.agent_activity.get())
        self._set_text(self.investigation_queries_text, "")
        self._set_text(self.investigation_urls_text, "")
        self.compile_target.set("")
        target = self.workspace.repo_root / scope.relative_path
        if target.is_file() and target.suffix.lower() == ".tex":
            self.compile_target.set(scope.relative_path)
        self._refresh_generation_catalog()
        self._refresh_feedback()
        self._refresh_investigation()
        self.task_status.set("Contexto aplicado a las pantallas de trabajo.")

    def _build_platforms_tab(self, notebook):
        try:
            from .platform_credentials_gui import PlatformCredentialsFrame
        except ModuleNotFoundError as exc:
            if not (exc.name or "").startswith("cryptography"):
                raise
            frame = ttk.Frame(notebook, padding=12)
            ttk.Label(
                frame,
                text="Plataformas no disponible: instala la dependencia cryptography "
                     "en el entorno Python de AulaTeX. No se guardarán credenciales sin cifrado.",
                wraplength=800,
            ).pack(anchor="w")
            return frame
        return PlatformCredentialsFrame(
            notebook, repo_root=self.workspace.repo_root,
            institutions=[scope.institution or scope.label for scope in self.editorial_scopes.values()
                          if scope.level == "institucion"],
        )

    def _build_panel_tab(self) -> None:
        self.panel_tab.columnconfigure(1, weight=1)
        self.panel_tab.rowconfigure(3, weight=1)
        ttk.Label(self.panel_tab, text="Repositorio").grid(row=0, column=0, sticky="w")
        ttk.Label(self.panel_tab, text=str(self.workspace.repo_root)).grid(row=0, column=1, sticky="w")
        ttk.Button(self.panel_tab, text="Usar selección", command=self._use_selected_scope).grid(row=2, column=0, sticky="w", pady=12)
        ttk.Button(self.panel_tab, text="Actualizar proyecto", command=self._refresh_tree).grid(row=2, column=1, sticky="w", pady=12)

        columns = ("mem", "lock", "gen")
        self.template_tree = ttk.Treeview(self.panel_tab, columns=columns, show="tree headings")
        self.template_tree.heading("#0", text="Nodos editoriales")
        self.template_tree.heading("mem", text="Memoria")
        self.template_tree.heading("lock", text="Fijas")
        self.template_tree.heading("gen", text="Gen")
        self.template_tree.column("#0", width=480)
        self.template_tree.column("mem", width=100, anchor="center")
        self.template_tree.column("lock", width=100, anchor="center")
        self.template_tree.column("gen", width=100, anchor="center")
        self.template_tree.grid(row=3, column=0, columnspan=2, sticky="nsew")

        self.template_details = tk.Text(self.panel_tab, height=8)
        self.template_details.grid(row=4, column=0, columnspan=2, sticky="ew")
        self.template_tree.bind("<<TreeviewSelect>>", self._on_template_selected)
        self.template_tree.bind("<Return>", self._show_template_node_details)
        self.template_tree.bind("<KP_Enter>", self._show_template_node_details)
        self.template_tree.bind("<Double-1>", self._toggle_template_node)
        self._set_text(
            self.template_details,
            "Cargando arbol editorial. La ventana ya esta lista y el indice se completara en segundo plano.\n",
        )
        self.after(50, self._refresh_tree)

    def _build_credentials_tab(self) -> None:
        self.credentials_tab.columnconfigure(0, weight=1)
        self.credentials_tab.rowconfigure(2, weight=1)

        header = ttk.Frame(self.credentials_tab)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        ttk.Label(
            header,
            text="Configura y embebe las credenciales del entorno directamente en el archivo .env del workspace.",
            wraplength=760,
            justify="left",
        ).grid(row=0, column=0, sticky="w")
        ttk.Button(header, text="Como funciona", command=self._show_credentials_help).grid(row=0, column=1, sticky="e")

        path_row = ttk.Frame(self.credentials_tab)
        path_row.grid(row=1, column=0, sticky="ew", pady=(6, 8))
        path_row.columnconfigure(1, weight=1)
        ttk.Label(path_row, text="Archivo .env").grid(row=0, column=0, sticky="w")
        ttk.Label(path_row, text=str(self.llm.env_path)).grid(row=0, column=1, sticky="w", padx=(8, 0))

        canvas = tk.Canvas(self.credentials_tab, highlightthickness=0)
        canvas.grid(row=2, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(self.credentials_tab, orient="vertical", command=canvas.yview)
        scrollbar.grid(row=2, column=1, sticky="ns")
        canvas.configure(yscrollcommand=scrollbar.set)

        inner = ttk.Frame(canvas)
        inner_window = canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.columnconfigure(0, weight=1)

        def _on_inner_configure(_event=None) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas_configure(event) -> None:
            canvas.itemconfigure(inner_window, width=event.width)

        inner.bind("<Configure>", _on_inner_configure)
        canvas.bind("<Configure>", _on_canvas_configure)

        self._credential_vars: dict[str, tk.StringVar] = {}
        self._credential_show_vars: dict[str, tk.BooleanVar] = {}
        self._credential_status_labels: dict[str, ttk.Label] = {}

        catalog = credential_catalog()
        stored = read_env_values(
            [field.key for group in catalog for field in group.fields],
            self.llm.env_path,
        )

        for row_index, group in enumerate(catalog):
            frame = ttk.LabelFrame(inner, text=group.title, padding=10)
            frame.grid(row=row_index, column=0, sticky="ew", pady=(0, 10), padx=(0, 4))
            frame.columnconfigure(1, weight=1)

            status_label = ttk.Label(frame, text="", foreground="#616161")
            status_label.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 4))
            self._credential_status_labels[group.group_id] = status_label
            if group.description:
                ttk.Label(frame, text=group.description, foreground="#616161").grid(
                    row=1, column=0, columnspan=3, sticky="w", pady=(0, 6)
                )

            for field_index, field in enumerate(group.fields):
                grid_row = field_index + 2
                label_text = field.label + ("" if field.required else "  (opcional)")
                ttk.Label(frame, text=label_text).grid(row=grid_row, column=0, sticky="w", pady=2)
                var = tk.StringVar(value=stored.get(field.key, ""))
                self._credential_vars[field.key] = var
                show_char = "" if not field.secret else "*"
                entry = ttk.Entry(frame, textvariable=var, show=show_char)
                entry.grid(row=grid_row, column=1, sticky="ew", padx=(8, 8), pady=2)
                if field.help:
                    self._attach_tooltip(entry, field.help)
                if field.secret:
                    show_var = tk.BooleanVar(value=False)
                    self._credential_show_vars[field.key] = show_var
                    ttk.Checkbutton(
                        frame,
                        text="Ver",
                        variable=show_var,
                        command=lambda e=entry, v=show_var: e.configure(show="" if v.get() else "*"),
                    ).grid(row=grid_row, column=2, sticky="w", pady=2)

        actions = ttk.Frame(self.credentials_tab)
        actions.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        self.credentials_save_button = ttk.Button(actions, text="Guardar credenciales", command=self._save_credentials)
        self.credentials_save_button.grid(row=0, column=0, sticky="w")
        ttk.Button(actions, text="Recargar desde .env", command=self._reload_credentials).grid(row=0, column=1, sticky="w", padx=(8, 0))
        ttk.Button(actions, text="Verificar estado", command=self._refresh_credential_status).grid(row=0, column=2, sticky="w", padx=(8, 0))
        ttk.Button(actions, text="Cifrar secretos ahora", command=self._encrypt_credentials).grid(row=0, column=3, sticky="w", padx=(8, 0))

        self.credentials_status_text = ttk.Label(self.credentials_tab, text="", foreground="#2e7d32")
        self.credentials_status_text.grid(row=4, column=0, sticky="w", pady=(6, 0))

        self._refresh_credential_status()

    def _show_credentials_help(self) -> None:
        messagebox.showinfo(
            "AulaTeX - Credenciales",
            "1. Cada tarjeta agrupa las claves de un motor LLM o servicio (voz, traducción, video).\n"
            "2. Los campos secretos aparecen enmascarados; usa 'Ver' para revisarlos.\n"
            "3. 'Guardar credenciales' escribe los valores en el archivo .env del workspace,\n"
            "   preservando comentarios y el orden existente; los campos vacíos no borran claves.\n"
            "4. 'Recargar desde .env' descarta los cambios sin guardar y vuelve a leer el archivo.\n"
            "5. 'Verificar estado' recalcula qué motores tienen sus tres claves obligatorias completas.\n"
            "6. Al guardar, los secretos se cifran automáticamente con la clave local\n"
            "   (scripts/secret.key) y quedan en el .env con el prefijo 'enc:'.\n"
            "7. 'Cifrar secretos ahora' fuerza el cifrado de cualquier valor que haya quedado en claro.\n"
            "8. Respalda scripts/secret.key fuera del repositorio: sin ella los valores 'enc:'\n"
            "   son irrecuperables y habría que rotar todas las claves.\n"
            "9. Las credenciales quedan embebidas localmente; no se envían a ningún servicio al guardarlas.",
        )

    def _refresh_credential_status(self) -> None:
        statuses = {status.prefix: status for status in credential_status()}
        prefix_by_group = {
            "model_router": "MODEL_ROUTER",
            "claude_foundry": "ANTHROPIC_FOUNDRY",
            "gpt_5_6_sol": "AZURE_OPENAI_GPT_5_6_SOL",
            "gpt_5_6_luna": "AZURE_OPENAI_GPT_5_6_LUNA",
            "gpt_5_6_terra": "AZURE_OPENAI_GPT_5_6_TERRA",
            "gpt_pro": "GPT_PRO",
            "codex": "CODEX",
        }
        for group_id, label in self._credential_status_labels.items():
            prefix = prefix_by_group.get(group_id)
            if prefix and prefix in statuses:
                status = statuses[prefix]
                if status.ok:
                    label.configure(text="Completo", foreground="#2e7d32")
                else:
                    missing = ", ".join(s.rsplit("_", 1)[-1] for s in status.missing)
                    label.configure(text=f"Faltan: {missing}", foreground="#c62828")
            else:
                filled = any(
                    self._credential_vars[field.key].get().strip()
                    for group in credential_catalog()
                    if group.group_id == group_id
                    for field in group.fields
                )
                label.configure(
                    text="Configurado" if filled else "Sin configurar",
                    foreground="#2e7d32" if filled else "#616161",
                )

    def _reload_credentials(self) -> None:
        stored = read_env_values(list(self._credential_vars.keys()), self.llm.env_path)
        for key, var in self._credential_vars.items():
            var.set(stored.get(key, ""))
        self.credentials_status_text.configure(text="Valores recargados desde el archivo .env.", foreground="#616161")
        self._refresh_credential_status()

    def _save_credentials(self) -> None:
        values = {key: var.get() for key, var in self._credential_vars.items()}
        try:
            written_path = write_env_values(values, self.llm.env_path)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("AulaTeX", f"No se pudieron guardar las credenciales: {exc}")
            return
        self.credentials_status_text.configure(
            text=f"Credenciales guardadas y cifradas en {written_path}",
            foreground="#2e7d32",
        )
        self._refresh_credential_status()

    def _encrypt_credentials(self) -> None:
        try:
            cifrados = encrypt_env_secrets(self.llm.env_path)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("AulaTeX", f"No se pudieron cifrar los secretos: {exc}")
            return
        if cifrados < 0:
            self.credentials_status_text.configure(
                text="No hay clave local disponible; instala 'cryptography' y verifica scripts/secret.key.",
                foreground="#c62828",
            )
            return
        if cifrados == 0:
            self.credentials_status_text.configure(
                text="Todos los secretos del .env ya estaban cifrados.",
                foreground="#2e7d32",
            )
            return
        self.credentials_status_text.configure(
            text=f"Cifrados {cifrados} secretos en el archivo .env.",
            foreground="#2e7d32",
        )

    def _build_llm_tab(self) -> None:
        self.llm_tab.columnconfigure(0, weight=1)
        self.llm_tab.rowconfigure(1, weight=1)

        header = ttk.Frame(self.llm_tab)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        header.columnconfigure(0, weight=1)
        ttk.Label(
            header,
            text="Chat AulaTeX con sesiones persistentes, compactacion y modo multimotor.",
        ).grid(row=0, column=0, sticky="w")
        help_button = ttk.Button(header, text="Como usar", command=self._show_llm_help)
        help_button.grid(row=0, column=1, sticky="e")

        paned = ttk.Panedwindow(self.llm_tab, orient="horizontal")
        paned.grid(row=1, column=0, sticky="nsew")

        sidebar = ttk.LabelFrame(paned, text="Sesiones tematicas", padding=10)
        content = ttk.Frame(paned, padding=(12, 0, 0, 0))
        paned.add(sidebar, weight=1)
        paned.add(content, weight=4)

        sidebar.columnconfigure(0, weight=1)
        sidebar.rowconfigure(1, weight=1)
        ttk.Label(
            sidebar,
            text="Cinco espacios fijos: cada uno conserva historial y memoria compactada.",
            wraplength=250,
        ).grid(row=0, column=0, sticky="ew")

        self.llm_session_tree = ttk.Treeview(sidebar, columns=("motor", "ctx", "estado"), displaycolumns=("ctx",), show="tree headings", height=12)
        self.llm_session_tree.heading("#0", text="Tema")
        self.llm_session_tree.heading("motor", text="Motor")
        self.llm_session_tree.heading("ctx", text="Contexto")
        self.llm_session_tree.heading("estado", text="Activos")
        self.llm_session_tree.column("#0", width=130)
        self.llm_session_tree.column("motor", width=120, anchor="center")
        self.llm_session_tree.column("ctx", width=92, anchor="center")
        self.llm_session_tree.column("estado", width=70, anchor="center")
        self.llm_session_tree.grid(row=1, column=0, sticky="nsew", pady=(8, 0))
        self.llm_session_tree.bind("<<TreeviewSelect>>", self._on_llm_session_selected)

        session_actions = ttk.Frame(sidebar)
        session_actions.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        compact_button = ttk.Button(session_actions, text="Compactar", command=self._compact_selected_llm_session)
        compact_button.grid(row=0, column=0, sticky="w")
        export_button = ttk.Button(session_actions, text="Exportar", command=self._export_selected_llm_session)
        export_button.grid(row=0, column=1, sticky="w", padx=(8, 0))
        clear_button = ttk.Button(session_actions, text="Limpiar", command=self._clear_selected_llm_session)
        clear_button.grid(row=0, column=2, sticky="w", padx=(8, 0))

        content.columnconfigure(0, weight=1)
        content.rowconfigure(2, weight=1)

        self.llm_session_title = tk.StringVar(value="Editorial")
        self.llm_session_meta = tk.StringVar(value="Selecciona una sesion para comenzar.")
        ttk.Label(content, textvariable=self.llm_session_title, font=("TkDefaultFont", 11, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(content, textvariable=self.llm_session_meta, wraplength=760).grid(row=1, column=0, sticky="ew", pady=(4, 10))

        conversation = ttk.Notebook(content)
        conversation.grid(row=2, column=0, sticky="nsew")
        transcript_frame = ttk.Frame(conversation, padding=8)
        conversation.add(transcript_frame, text="Conversación")
        transcript_frame.columnconfigure(0, weight=1)
        transcript_frame.rowconfigure(0, weight=1)
        self.llm_output = ScrolledText(transcript_frame, height=12, width=40, wrap="word")
        self.llm_output.grid(row=0, column=0, sticky="nsew")

        prompt_frame = ttk.LabelFrame(content, text="Nuevo mensaje", padding=8)
        prompt_frame.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        prompt_frame.columnconfigure(0, weight=1)
        self.prompt_text = ScrolledText(prompt_frame, height=4, width=40, wrap="word")
        self.prompt_text.grid(row=0, column=0, sticky="ew")
        prompt_actions = ttk.Frame(prompt_frame)
        prompt_actions.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        prompt_actions.columnconfigure(1, weight=1)
        self.llm_send_button = ttk.Button(prompt_actions, text="Enviar al chat", command=self._run_llm_prompt)
        self.llm_send_button.grid(row=0, column=0, sticky="w")
        ttk.Label(prompt_actions, text="Profundidad").grid(row=0, column=1, sticky="e", padx=(12, 6))
        self.llm_multi_severity_combo = ttk.Combobox(
            prompt_actions,
            textvariable=self.llm_multi_severity,
            values=tuple(MULTIMOTOR_SEVERITY_LABELS),
            state="readonly",
            width=12,
        )
        self.llm_multi_severity_combo.grid(row=0, column=2, sticky="e")
        self.llm_status = tk.StringVar(value="Listo")
        ttk.Label(prompt_actions, textvariable=self.llm_status, wraplength=480).grid(row=1, column=0, columnspan=3, sticky="w", pady=(6, 0))

        memory_frame = ttk.Frame(conversation, padding=8)
        conversation.add(memory_frame, text="Memoria y diagnóstico")
        memory_frame.columnconfigure(0, weight=1)
        memory_frame.rowconfigure(0, weight=1)
        self.llm_system = ScrolledText(memory_frame, height=12, width=40, wrap="word")
        self.llm_system.grid(row=0, column=0, sticky="nsew")

        self._attach_tooltip(
            help_button,
            "Abre una guia corta de uso del chat: cuando usar cada sesion, como se guarda el historial y como funciona la compactacion.",
        )
        self._attach_tooltip(
            self.llm_session_tree,
            "Cada fila es una sesion fija por tema. Se muestra motor, contexto estimado y numero de mensajes activos frente al total historico.",
        )
        self._attach_tooltip(
            compact_button,
            "Fuerza la compactacion del historial seleccionado para convertir mensajes antiguos en memoria breve reutilizable.",
        )
        self._attach_tooltip(
            export_button,
            "Exporta la sesion completa a Markdown dentro de retroalimentacion-editorial/aulatex/llm-chat/exports.",
        )
        self._attach_tooltip(
            clear_button,
            "Borra los mensajes y la memoria compactada de la sesion actual. Util cuando quieras reiniciar solo ese tema.",
        )
        self._attach_tooltip(
            self.prompt_text,
            "Escribe aqui la instruccion. El sistema agrega memoria compactada e historial reciente automaticamente antes de consultar el motor asignado.",
        )
        self._attach_tooltip(
            self.llm_send_button,
            "Envia el mensaje a la sesion activa. En MultiMotor se consultan todos los motores en paralelo y se sintetiza consenso.",
        )
        self._attach_tooltip(
            self.llm_multi_severity_combo,
            "Controla la profundidad de MultiMotor: rapido prioriza velocidad, normal equilibra y profundo solicita analisis y validaciones extra.",
        )
        self._attach_tooltip(
            self.llm_system,
            "Muestra ayuda del tema, resumen compacto persistente y, si aplica, el detalle del ultimo consenso multimotor.",
        )
        self._register_busy_widgets("llm-chat", self.llm_send_button, self.llm_multi_severity_combo,
                        self.prompt_text, compact_button, export_button, clear_button)

        self._refresh_llm_sessions()
        self._refresh_llm_view("editorial")

    def _build_agent_tab(self) -> None:
        self.agent_tab.columnconfigure(1, weight=1)
        self.agent_target = tk.StringVar(value="")
        self.agent_level = tk.StringVar(value="materia")
        self.agent_action = tk.StringVar(value="generar-actividad")
        self.agent_activity = tk.IntVar(value=1)
        self.agent_iterations = tk.IntVar(value=5)
        self.agent_engines = tk.StringVar(value=", ".join(self._ordered_feedback_engines()))
        self.agent_compile = tk.BooleanVar(value=True)
        self.agent_apply = tk.BooleanVar(value=False)
        self.agent_monitor_mode = tk.BooleanVar(value=True)
        self.agent_run_extractor = tk.BooleanVar(value=True)
        self.agent_max_cycles = tk.IntVar(value=1)

        mode_frame = ttk.Frame(self.agent_tab)
        mode_frame.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 12))
        mode_controls = []
        for title, value in (("Revisar archivos", True), ("Ejecutar agente", False)):
            control = ttk.Radiobutton(mode_frame, text=title, variable=self.agent_monitor_mode,
                                      value=value, command=self._sync_agent_mode)
            control.pack(side="left", padx=(0, 16))
            mode_controls.append(control)
        ttk.Label(self.agent_tab, text="Objetivo").grid(row=1, column=0, sticky="w")
        target_entry = ttk.Entry(self.agent_tab, textvariable=self.agent_target)
        target_entry.grid(row=1, column=1, sticky="ew")
        self.agent_browse_button = ttk.Button(self.agent_tab, text="Buscar", command=self._browse_agent_target)
        self.agent_browse_button.grid(row=1, column=2, padx=(8, 0))
        ttk.Label(self.agent_tab, text="Actividad").grid(row=2, column=0, sticky="w", pady=8)
        activity_spin = ttk.Spinbox(self.agent_tab, from_=1, to=99, textvariable=self.agent_activity, width=8)
        activity_spin.grid(row=2, column=1, sticky="w", pady=8)
        self.agent_workflow_frame = ttk.Frame(self.agent_tab)
        self.agent_workflow_frame.grid(row=3, column=0, columnspan=3, sticky="ew")
        self.agent_workflow_frame.columnconfigure(1, weight=1)
        workflow_controls = []
        for row, (title, variable, choices) in enumerate((
            ("Nivel", self.agent_level, ("institucion", "carrera", "materia")),
            ("Acción", self.agent_action, ("generar-plantilla", "generar-actividad", "realizar-actividad", "evaluar")),
        )):
            ttk.Label(self.agent_workflow_frame, text=title).grid(row=row, column=0, sticky="w", pady=4)
            control = ttk.Combobox(self.agent_workflow_frame, textvariable=variable, values=choices, state="readonly")
            control.grid(row=row, column=1, sticky="ew", padx=(12, 0), pady=4)
            workflow_controls.append(control)
        ttk.Label(self.agent_workflow_frame, text="Motores").grid(row=2, column=0, sticky="w", pady=4)
        engines_entry = EnginePicker(self.agent_workflow_frame, textvariable=self.agent_engines, choices=self._ordered_feedback_engines())
        engines_entry.grid(row=2, column=1, sticky="ew", padx=(12, 0), pady=4)
        ttk.Label(self.agent_workflow_frame, text="Iteraciones").grid(row=3, column=0, sticky="w", pady=4)
        iterations_spin = ttk.Spinbox(self.agent_workflow_frame, from_=1, to=500, textvariable=self.agent_iterations, width=8)
        iterations_spin.grid(row=3, column=1, sticky="w", padx=(12, 0), pady=4)
        apply_check = ttk.Checkbutton(self.agent_workflow_frame, text="Copiar reporte al objetivo", variable=self.agent_apply)
        apply_check.grid(row=4, column=1, sticky="w", padx=(12, 0), pady=4)
        self.agent_monitor_frame = ttk.Frame(self.agent_tab)
        self.agent_monitor_frame.grid(row=3, column=0, columnspan=3, sticky="ew")
        ttk.Label(self.agent_monitor_frame, text="Ciclos de revisión").grid(row=0, column=0, sticky="w")
        cycles_spin = ttk.Spinbox(self.agent_monitor_frame, from_=1, to=20, textvariable=self.agent_max_cycles, width=8)
        cycles_spin.grid(row=0, column=1, sticky="w", padx=12)
        extractor_check = ttk.Checkbutton(self.agent_monitor_frame, text="Ejecutar extractor", variable=self.agent_run_extractor)
        extractor_check.grid(row=1, column=1, sticky="w", padx=12, pady=8)
        compile_check = ttk.Checkbutton(self.agent_tab, text="Compilar y diagnosticar TeX", variable=self.agent_compile)
        compile_check.grid(row=4, column=1, sticky="w", pady=8)
        self.agent_run_button = ttk.Button(self.agent_tab, command=self._run_agent)
        self.agent_run_button.grid(row=5, column=1, sticky="w", pady=10)
        self.agent_output = ScrolledText(self.agent_tab, height=10, wrap="word", state="disabled")
        self.agent_output.grid(row=6, column=0, columnspan=3, sticky="nsew")
        self.agent_tab.rowconfigure(6, weight=1)
        self._attach_tooltip(self.agent_browse_button, "Selecciona la carpeta objetivo desde donde el agente leerá contexto y aplicará la memoria editorial heredada.")
        self._attach_tooltip(self.agent_run_button, "Ejecuta el flujo monitorizado observar→extraer→revisar→evaluar→memoria con compuertas contractuales.")
        self._register_busy_widgets("agent", self.agent_run_button, self.agent_browse_button,
                                    target_entry, activity_spin, *mode_controls, *workflow_controls,
                                    engines_entry, iterations_spin, apply_check, cycles_spin,
                                    extractor_check, compile_check)
        self._sync_agent_mode()

    def _sync_agent_mode(self) -> None:
        monitor = self.agent_monitor_mode.get()
        self.agent_monitor_frame.grid() if monitor else self.agent_monitor_frame.grid_remove()
        self.agent_workflow_frame.grid_remove() if monitor else self.agent_workflow_frame.grid()
        self.agent_run_button.configure(text="Revisar archivos" if monitor else "Ejecutar agente")

    def _build_arch_tab(self) -> None:
        self.arch_tab.columnconfigure(0, weight=1)
        self.arch_tab.rowconfigure(0, weight=1)
        self.arch_text = tk.Text(self.arch_tab, height=32, wrap="word")
        self.arch_text.grid(row=0, column=0, sticky="nsew")
        self.arch_text.insert("end", pattern_catalog_markdown())
        self.arch_text.configure(state="disabled")

    def _build_builder_tab(self) -> None:
        self.builder_tab.columnconfigure(0, weight=1)
        self.builder_tab.rowconfigure(0, weight=1, minsize=160)
        self.builder_tab.rowconfigure(2, weight=1, minsize=160)
        form = ScrollableForm(self.builder_tab)
        form.grid(row=0, column=0, sticky="nsew")

        self.generation_institution = tk.StringVar(value=UNSELECTED_OPTION)
        self.generation_career = tk.StringVar(value=UNSELECTED_OPTION)
        self.generation_subject = tk.StringVar(value=UNSELECTED_OPTION)
        self.generation_node_level = tk.StringVar(value="actividad")
        self.generation_mode = tk.StringVar(value="crear")
        self.generation_node_name = tk.StringVar(value="")
        self.generation_activity_number = tk.IntVar(value=1)
        self.generation_destination = tk.StringVar(value="")
        self.generation_ingest_document = tk.StringVar(value="")
        self.generation_iterations = tk.IntVar(value=2)
        self.generation_max_tokens = tk.IntVar(value=DEFAULT_MAX_TOKENS)
        self.generation_engines = tk.StringVar(value=", ".join(self._ordered_feedback_engines()))
        self.generation_scope_status = tk.StringVar(value="Padre editorial: pendiente")
        self.generation_progress_status = tk.StringVar(value="Listo para generar memoria fundacional.")
        self.generation_progress = tk.DoubleVar(value=0.0)

        header = ttk.Frame(form.body)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        ttk.Label(
            header,
            text="Generación editorial",
            font=("TkDefaultFont", 12, "bold"),
            wraplength=900,
        ).grid(row=0, column=0, sticky="w")
        self.generation_help_button = ttk.Button(header, text="Ayuda", command=self._show_generation_help)
        self.generation_help_button.grid(row=0, column=1, sticky="e")

        source_frame = ttk.LabelFrame(form.body, text="Padre editorial", padding=10)
        source_frame.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        for index in range(6):
            source_frame.columnconfigure(index, weight=1 if index % 2 else 0)

        ttk.Label(source_frame, text="Institucion").grid(row=0, column=0, sticky="w")
        self.generation_institution_combo = ttk.Combobox(source_frame, textvariable=self.generation_institution, state="readonly", width=12)
        self.generation_institution_combo.grid(row=0, column=1, columnspan=5, sticky="ew", padx=(6, 0))
        self.generation_institution_combo.bind("<<ComboboxSelected>>", self._on_generation_parent_changed)

        ttk.Label(source_frame, text="Carrera").grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.generation_career_combo = ttk.Combobox(source_frame, textvariable=self.generation_career, state="readonly", width=12)
        self.generation_career_combo.grid(row=1, column=1, columnspan=5, sticky="ew", padx=(6, 0), pady=(6, 0))
        self.generation_career_combo.bind("<<ComboboxSelected>>", self._on_generation_parent_changed)

        ttk.Label(source_frame, text="Materia").grid(row=2, column=0, sticky="w", pady=(6, 0))
        self.generation_subject_combo = ttk.Combobox(source_frame, textvariable=self.generation_subject, state="readonly", width=12)
        self.generation_subject_combo.grid(row=2, column=1, columnspan=5, sticky="ew", padx=(6, 0), pady=(6, 0))
        self.generation_subject_combo.bind("<<ComboboxSelected>>", self._on_generation_parent_changed)

        ttk.Label(source_frame, textvariable=self.generation_scope_status, wraplength=700).grid(row=3, column=0, columnspan=6, sticky="w", pady=(10, 0))

        control_frame = ttk.LabelFrame(form.body, text="Definición del nodo", padding=10)
        control_frame.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        for index in range(8):
            control_frame.columnconfigure(index, weight=1 if index in {1, 3, 5} else 0)

        ttk.Label(control_frame, text="Tipo de nodo").grid(row=0, column=0, sticky="w")
        self.generation_level_combo = ttk.Combobox(
            control_frame,
            textvariable=self.generation_node_level,
            values=("institucion", "carrera", "materia", "actividad"),
            state="readonly",
        )
        self.generation_level_combo.grid(row=0, column=1, sticky="ew", padx=(6, 12))
        self.generation_level_combo.bind("<<ComboboxSelected>>", self._on_generation_level_changed)

        ttk.Label(control_frame, text="Modo").grid(row=0, column=2, sticky="w")
        self.generation_mode_combo = ttk.Combobox(
            control_frame,
            textvariable=self.generation_mode,
            values=("crear", "reforzar"),
            state="readonly",
        )
        self.generation_mode_combo.grid(row=0, column=3, sticky="ew", padx=(6, 12))
        self.generation_mode_combo.bind("<<ComboboxSelected>>", self._on_generation_level_changed)

        ttk.Label(control_frame, text="Numero de actividad").grid(row=0, column=4, sticky="w")
        self.generation_activity_spin = ttk.Spinbox(control_frame, from_=1, to=99, textvariable=self.generation_activity_number, width=8)
        self.generation_activity_spin.grid(row=0, column=5, sticky="w", padx=(6, 12))

        ttk.Label(control_frame, text="Iteraciones").grid(row=0, column=6, sticky="w")
        self.generation_iterations_spin = ttk.Spinbox(control_frame, from_=1, to=500, textvariable=self.generation_iterations, width=8)
        self.generation_iterations_spin.grid(row=0, column=7, sticky="w", padx=(6, 0))

        ttk.Label(control_frame, text="Nombre del nodo").grid(row=1, column=0, sticky="w", pady=(10, 0))
        self.generation_name_entry = ttk.Entry(control_frame, textvariable=self.generation_node_name)
        self.generation_name_entry.grid(row=1, column=1, columnspan=3, sticky="ew", padx=(6, 12), pady=(10, 0))
        self.generation_name_entry.bind("<KeyRelease>", self._on_generation_level_changed)

        ttk.Label(control_frame, text="Destino").grid(row=1, column=4, sticky="w", pady=(10, 0))
        self.generation_destination_entry = ttk.Entry(control_frame, textvariable=self.generation_destination)
        self.generation_destination_entry.grid(row=1, column=5, columnspan=2, sticky="ew", padx=(6, 12), pady=(10, 0))
        self.generation_destination_entry.bind("<KeyRelease>", self._on_generation_level_changed)
        self.generation_destination_button = ttk.Button(control_frame, text="Buscar", command=self._browse_generation_destination)
        self.generation_destination_button.grid(row=1, column=7, sticky="w", pady=(10, 0))

        ttk.Label(control_frame, text="Motores en orden").grid(row=2, column=0, sticky="w", pady=(10, 0))
        self.generation_engines_entry = EnginePicker(control_frame, textvariable=self.generation_engines, choices=self._ordered_feedback_engines())
        self.generation_engines_entry.grid(row=2, column=1, columnspan=5, sticky="ew", padx=(6, 12), pady=(10, 0))

        ttk.Label(control_frame, text="Max tokens").grid(row=2, column=6, sticky="w", pady=(10, 0))
        self.generation_tokens_spin = ttk.Spinbox(control_frame, from_=128, to=DEFAULT_MAX_TOKENS, increment=128, textvariable=self.generation_max_tokens, width=10)
        self.generation_tokens_spin.grid(row=2, column=7, sticky="w", padx=(6, 0), pady=(10, 0))

        ttk.Label(control_frame, text="Ingesta textual").grid(row=3, column=0, sticky="nw", pady=(10, 0))
        self.generation_ingest_text = tk.Text(control_frame, height=5, width=32, wrap="word")
        self.generation_ingest_text.grid(row=3, column=1, columnspan=7, sticky="ew", padx=(6, 0), pady=(10, 0))
        self.generation_ingest_text.bind("<KeyRelease>", self._on_generation_level_changed)

        ttk.Label(control_frame, text="Documento de ingesta").grid(row=4, column=0, sticky="w", pady=(10, 0))
        self.generation_ingest_document_entry = ttk.Entry(control_frame, textvariable=self.generation_ingest_document)
        self.generation_ingest_document_entry.grid(row=4, column=1, columnspan=6, sticky="ew", padx=(6, 12), pady=(10, 0))
        self.generation_ingest_document_entry.bind("<KeyRelease>", self._on_generation_level_changed)
        self.generation_ingest_document_button = ttk.Button(control_frame, text="Buscar documento", command=self._browse_generation_ingest_document)
        self.generation_ingest_document_button.grid(row=4, column=7, sticky="w", pady=(10, 0))

        action_frame = ttk.Frame(self.builder_tab)
        action_frame.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        action_frame.columnconfigure(4, weight=1)
        self.generation_run_button = ttk.Button(action_frame, text="Generar nodo", command=self._run_generation)
        self.generation_run_button.grid(row=0, column=0, sticky="w")
        self.generation_cancel_button = ttk.Button(action_frame, text="Cancelar", command=self._cancel_generation, state="disabled")
        self.generation_cancel_button.grid(row=0, column=1, sticky="w", padx=(8, 0))
        self.generation_refresh_button = ttk.Button(action_frame, text="Nuevo formulario", command=self._reset_generation_view)
        self.generation_refresh_button.grid(row=0, column=2, sticky="w", padx=(8, 0))
        ttk.Progressbar(action_frame, variable=self.generation_progress, maximum=100).grid(row=0, column=4, sticky="ew", padx=(12, 0))
        ttk.Label(action_frame, textvariable=self.generation_progress_status).grid(row=1, column=0, columnspan=5, sticky="w", pady=(8, 0))

        results = ttk.Notebook(self.builder_tab)
        results.grid(row=2, column=0, sticky="nsew", pady=(10, 0))
        preview_frame = ttk.Frame(results, padding=8)
        results.add(preview_frame, text="Vista previa")
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(0, weight=1)
        self.generation_preview_text = ScrolledText(preview_frame, height=8, wrap="word")
        self.generation_preview_text.grid(row=0, column=0, sticky="nsew")

        self.generation_metrics_text = None
        if self.diagnostics_enabled:
            metrics_frame = ttk.Frame(results, padding=8)
            results.add(metrics_frame, text="Métricas")
            metrics_frame.columnconfigure(0, weight=1)
            metrics_frame.rowconfigure(0, weight=1)
            self.generation_metrics_text = ScrolledText(metrics_frame, height=8, wrap="word")
            self.generation_metrics_text.grid(row=0, column=0, sticky="nsew")

        output_frame = ttk.Frame(results, padding=8)
        results.add(output_frame, text="Ejecución")
        output_frame.columnconfigure(0, weight=1)
        output_frame.rowconfigure(0, weight=1)
        self.generation_output = ScrolledText(output_frame, height=8, wrap="word", state="disabled")
        self.generation_output.grid(row=0, column=0, sticky="nsew")
        for child in control_frame.winfo_children():
            position = child.grid_info()
            row, column = position["row"], position["column"]
            if row == 0:
                child.grid_configure(row=column // 2, column=column % 2, columnspan=1)
            elif row == 1:
                if column < 4:
                    child.grid_configure(row=4, column=min(column, 1), columnspan=1)
                else:
                    child.grid_configure(row=5, column=0 if column == 4 else 2 if column == 7 else 1, columnspan=1)
            elif row == 2:
                child.grid_configure(row=6 if column < 6 else 7, column=0 if column in (0, 6) else 1, columnspan=1)
            elif row == 3:
                child.grid_configure(row=8, column=min(column, 1), columnspan=2 if column else 1)
            elif row == 4:
                child.grid_configure(row=9, column=0 if column == 0 else 2 if column == 7 else 1, columnspan=1)
            if isinstance(child, ttk.Combobox):
                child.configure(width=10)
            elif isinstance(child, ttk.Entry):
                child.configure(width=12)
        for index in range(8):
            control_frame.columnconfigure(index, weight=1 if index == 1 else 0)

        self._attach_tooltip(self.generation_help_button, "Abre una guía corta sobre generación editorial, memoria fundacional, ancestros, hermanos, destino y contrato futuro del Agente.")
        self._attach_tooltip(self.generation_institution_combo, "Selecciona la institución padre cuando el nodo nuevo depende de ella. El filtrado de carrera y materia se actualiza de forma dependiente.")
        self._attach_tooltip(self.generation_career_combo, "Selecciona la carrera padre si el nuevo nodo es una materia o si la actividad depende de una materia dentro de esa carrera.")
        self._attach_tooltip(self.generation_subject_combo, "Selecciona la materia padre cuando vayas a generar o reforzar una actividad.")
        self._attach_tooltip(self.generation_level_combo, "Define si vas a generar o reforzar una institución, carrera, materia o actividad.")
        self._attach_tooltip(self.generation_mode_combo, "Crear exige nodo y destino nuevos. Reforzar permite reutilizar un destino existente y mejorar la memoria fundacional sin regresión.")
        self._attach_tooltip(self.generation_activity_spin, "Solo aplica a actividades. Sirve para validar numeración y para nombrar la maqueta inicial de forma consistente.")
        self._attach_tooltip(self.generation_iterations_spin, "Número de ciclos completos del orquestador. Cada ciclo vuelve a consultar los motores en el orden configurado.")
        self._attach_tooltip(self.generation_name_entry, "Nombre editorial del nodo nuevo o del nodo a reforzar. Se usa para clave, etiqueta y maqueta.")
        self._attach_tooltip(self.generation_destination_entry, "Ruta destino relativa o absoluta. Puede ser una carpeta existente para reforzar o una nueva para crear el nodo.")
        self._attach_tooltip(self.generation_destination_button, "Selecciona una carpeta ya existente como destino. Si necesitas una carpeta nueva, puedes escribirla manualmente en el campo de destino.")
        self._attach_tooltip(self.generation_ingest_text, "Texto libre opcional. Puedes pegar lineamientos, instrucciones del docente o notas editoriales; también funciona combinado con el documento.")
        self._attach_tooltip(self.generation_ingest_document_entry, "Documento opcional de apoyo. Puedes usarlo solo o junto con la ingesta textual para orientar memoria y TEX editorial.")
        self._attach_tooltip(self.generation_ingest_document_button, "Selecciona un documento de apoyo para usarlo como ingesta. Se intentará leer si es texto o DOCX; otros tipos se conservarán como referencia contextual.")
        self._attach_tooltip(self.generation_engines_entry, "Selecciona los motores. Se ejecutan en el orden del menú.")
        self._attach_tooltip(self.generation_tokens_spin, "Límite de salida por llamada LLM para cada motor y ciclo.")
        self._attach_tooltip(self.generation_run_button, "Inicia la generación editorial descendente del nodo configurado y persiste memoria, plan y maqueta.")
        self._attach_tooltip(self.generation_cancel_button, "Solicita cancelación cooperativa. La corrida se cierra cuando termina la llamada LLM que esté en curso.")
        self._attach_tooltip(self.generation_refresh_button, "Reinicia la pestaña Generación a su estado inicial, recarga el catálogo editorial y deja la vista lista para otra corrida.")
        self._attach_tooltip(self.generation_preview_text, "Muestra el padre resuelto, la clave del nodo, el destino final, el modo crear/reforzar y el contrato editorial del destino.")
        if self.generation_metrics_text is not None:
            self._attach_tooltip(self.generation_metrics_text, "Resume llamadas, caracteres, tiempos y errores por motor, además del avance por ciclo del nodo actualmente previsualizado.")
        self._attach_tooltip(self.generation_output, "Bitácora en vivo del orquestador de generación: inicio, progreso por motor, resultados y cierre de la corrida.")
        self._register_busy_widgets(
            "generation",
            self.generation_run_button,
            self.generation_refresh_button,
            self.generation_help_button,
            self.generation_institution_combo,
            self.generation_career_combo,
            self.generation_subject_combo,
            self.generation_level_combo,
            self.generation_mode_combo,
            self.generation_activity_spin,
            self.generation_iterations_spin,
            self.generation_name_entry,
            self.generation_destination_entry,
            self.generation_destination_button,
            self.generation_ingest_text,
            self.generation_ingest_document_entry,
            self.generation_ingest_document_button,
            self.generation_engines_entry,
            self.generation_tokens_spin,
        )

        form.bind_content()
        self._refresh_generation_catalog()

    def _build_compile_tab(self) -> None:
        self.compile_tab.columnconfigure(1, weight=1)
        self.compile_target = tk.StringVar(value="")
        ttk.Label(self.compile_tab, text="Archivo .tex").grid(row=0, column=0, sticky="w")
        ttk.Entry(self.compile_tab, textvariable=self.compile_target).grid(row=0, column=1, sticky="ew")
        self.compile_browse_button = ttk.Button(self.compile_tab, text="Buscar", command=self._browse_tex)
        self.compile_browse_button.grid(row=0, column=2, padx=(8, 0))
        self.compile_run_button = ttk.Button(self.compile_tab, text="Compilar", command=self._compile_selected)
        self.compile_run_button.grid(row=1, column=1, sticky="w", pady=10)
        self.compile_output = ScrolledText(self.compile_tab, height=18, wrap="word", state="disabled")
        self.compile_output.grid(row=2, column=0, columnspan=3, sticky="nsew")
        self.compile_tab.rowconfigure(2, weight=1)
        self._attach_tooltip(self.compile_browse_button, "Busca un archivo TeX concreto para compilar con el wrapper compartido latexmk-build.ps1.")
        self._attach_tooltip(self.compile_run_button, "Lanza la compilación del TeX seleccionado y muestra el tail de stdout/stderr.")
        self._register_busy_widgets("compile", self.compile_run_button, self.compile_browse_button)

    def _build_extractor_tab(self) -> None:
        self.extractor_open_button = ttk.Button(self.extractor_tab, text="Abrir extractor GUI", command=self._open_extractor_gui)
        self.extractor_open_button.grid(row=0, column=0, sticky="w")
        self.extractor_probe_button = ttk.Button(self.extractor_tab, text="Probar configuracion", command=self._probe_extractor)
        self.extractor_probe_button.grid(row=0, column=1, sticky="w", padx=(8, 0))
        self.extractor_output = ScrolledText(self.extractor_tab, height=18, wrap="word", state="disabled")
        self.extractor_output.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(10, 0))
        self.extractor_tab.rowconfigure(1, weight=1)
        self.extractor_tab.columnconfigure(1, weight=1)
        self._attach_tooltip(self.extractor_open_button, "Abre la interfaz específica del extractor de conceptos e ideas en una ventana separada.")
        self._attach_tooltip(self.extractor_probe_button, "Ejecuta la comprobación de configuración del extractor y reporta el resultado en esta pestaña.")
        self._register_busy_widgets("extractor", self.extractor_probe_button)

    def _build_feedback_tab(self) -> None:
        self.feedback_tab.columnconfigure(0, weight=1)
        self.feedback_tab.rowconfigure(4, weight=1)
        ttk.Label(self.feedback_tab, text="Memoria editorial", font=("TkDefaultFont", 12, "bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 8))

        self.feedback_institution = tk.StringVar(value=UNSELECTED_OPTION)
        self.feedback_career = tk.StringVar(value=UNSELECTED_OPTION)
        self.feedback_subject = tk.StringVar(value=UNSELECTED_OPTION)
        self.feedback_activity = tk.StringVar(value=UNSELECTED_OPTION)
        self.feedback_build_level = tk.StringVar(value="materia")
        self.feedback_propagation = tk.StringVar(value="ascendente")
        self.feedback_iterations = tk.IntVar(value=2)
        self.feedback_max_tokens = tk.IntVar(value=DEFAULT_MAX_TOKENS)
        self.feedback_engines = tk.StringVar(value=", ".join(self._ordered_feedback_engines()))
        self.feedback_scope_status = tk.StringVar(value="Origen resuelto: pendiente")
        self.feedback_progress_status = tk.StringVar(value="Listo para construir memoria editorial.")
        self.feedback_progress = tk.DoubleVar(value=0.0)

        source_frame = ttk.LabelFrame(self.feedback_tab, text="Origen editorial", padding=10)
        source_frame.grid(row=1, column=0, sticky="ew")
        for index in range(8):
            source_frame.columnconfigure(index, weight=1 if index % 2 else 0)

        ttk.Label(source_frame, text="Institucion").grid(row=0, column=0, sticky="w")
        self.feedback_institution_combo = ttk.Combobox(source_frame, textvariable=self.feedback_institution, state="readonly")
        self.feedback_institution_combo.grid(row=0, column=1, sticky="ew", padx=(6, 12))
        self.feedback_institution_combo.bind("<<ComboboxSelected>>", self._on_feedback_source_changed)

        ttk.Label(source_frame, text="Carrera").grid(row=0, column=2, sticky="w")
        self.feedback_career_combo = ttk.Combobox(source_frame, textvariable=self.feedback_career, state="readonly")
        self.feedback_career_combo.grid(row=0, column=3, sticky="ew", padx=(6, 12))
        self.feedback_career_combo.bind("<<ComboboxSelected>>", self._on_feedback_source_changed)

        ttk.Label(source_frame, text="Materia").grid(row=0, column=4, sticky="w")
        self.feedback_subject_combo = ttk.Combobox(source_frame, textvariable=self.feedback_subject, state="readonly")
        self.feedback_subject_combo.grid(row=0, column=5, sticky="ew", padx=(6, 12))
        self.feedback_subject_combo.bind("<<ComboboxSelected>>", self._on_feedback_source_changed)

        ttk.Label(source_frame, text="Actividad").grid(row=0, column=6, sticky="w")
        self.feedback_activity_combo = ttk.Combobox(source_frame, textvariable=self.feedback_activity, state="readonly")
        self.feedback_activity_combo.grid(row=0, column=7, sticky="ew", padx=(6, 0))
        self.feedback_activity_combo.bind("<<ComboboxSelected>>", self._on_feedback_source_changed)

        ttk.Label(source_frame, textvariable=self.feedback_scope_status).grid(row=1, column=0, columnspan=8, sticky="w", pady=(10, 0))

        control_frame = ttk.LabelFrame(self.feedback_tab, text="Construcción, fusión histórica y retroalimentación", padding=10)
        control_frame.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        for index in range(6):
            control_frame.columnconfigure(index, weight=1 if index in {1, 3, 5} else 0)

        ttk.Label(control_frame, text="Nivel destino").grid(row=0, column=0, sticky="w")
        self.feedback_build_combo = ttk.Combobox(control_frame, textvariable=self.feedback_build_level, state="readonly")
        self.feedback_build_combo.grid(row=0, column=1, sticky="ew", padx=(6, 12))
        self.feedback_build_combo.bind("<<ComboboxSelected>>", self._on_feedback_plan_changed)

        ttk.Label(control_frame, text="Propagacion").grid(row=0, column=2, sticky="w")
        self.feedback_propagation_combo = ttk.Combobox(
            control_frame,
            textvariable=self.feedback_propagation,
            values=PROPAGATION_VALUES,
            state="readonly",
        )
        self.feedback_propagation_combo.grid(row=0, column=3, sticky="ew", padx=(6, 12))
        self.feedback_propagation_combo.bind("<<ComboboxSelected>>", self._on_feedback_plan_changed)

        ttk.Label(control_frame, text="Iteraciones").grid(row=0, column=4, sticky="w")
        self.feedback_iterations_spin = ttk.Spinbox(control_frame, from_=1, to=500, textvariable=self.feedback_iterations, width=8)
        self.feedback_iterations_spin.grid(row=0, column=5, sticky="w", padx=(6, 0))

        ttk.Label(control_frame, text="Motores en orden").grid(row=1, column=0, sticky="w", pady=(10, 0))
        self.feedback_engines_entry = EnginePicker(control_frame, textvariable=self.feedback_engines, choices=self._ordered_feedback_engines())
        self.feedback_engines_entry.grid(row=1, column=1, columnspan=3, sticky="ew", padx=(6, 12), pady=(10, 0))
        ttk.Label(control_frame, text="Max tokens").grid(row=1, column=4, sticky="w", pady=(10, 0))
        self.feedback_tokens_spin = ttk.Spinbox(control_frame, from_=128, to=200000, increment=128, textvariable=self.feedback_max_tokens, width=10)
        self.feedback_tokens_spin.grid(row=1, column=5, sticky="w", padx=(6, 0), pady=(10, 0))

        action_frame = ttk.Frame(self.feedback_tab)
        action_frame.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        action_frame.columnconfigure(7, weight=1)
        self.feedback_run_button = ttk.Button(action_frame, text="Construir memoria", command=self._run_feedback_memory)
        self.feedback_run_button.grid(row=0, column=0, sticky="w")
        self.feedback_cancel_button = ttk.Button(action_frame, text="Cancelar", command=self._cancel_feedback_memory, state="disabled")
        self.feedback_cancel_button.grid(row=0, column=1, sticky="w", padx=(8, 0))
        self.feedback_resume_button = ttk.Button(action_frame, text="Reanudar", command=self._resume_feedback_memory, state="disabled")
        self.feedback_resume_button.grid(row=0, column=2, sticky="w", padx=(8, 0))
        self.feedback_lock_button = ttk.Button(action_frame, text="Fijar reglas", command=self._lock_feedback_scope)
        self.feedback_lock_button.grid(row=0, column=3, sticky="w", padx=(8, 0))
        self.feedback_unlock_button = ttk.Button(action_frame, text="Liberar reglas", command=self._unlock_feedback_scope)
        self.feedback_unlock_button.grid(row=0, column=4, sticky="w", padx=(8, 0))
        self.feedback_refresh_button = ttk.Button(action_frame, text="Actualizar", command=self._refresh_feedback)
        self.feedback_refresh_button.grid(row=0, column=5, sticky="w", padx=(8, 0))
        self.feedback_help_button = ttk.Button(action_frame, text="Ayuda", command=self._show_feedback_help)
        self.feedback_help_button.grid(row=0, column=6, sticky="w", padx=(8, 0))
        ttk.Progressbar(action_frame, variable=self.feedback_progress, maximum=100).grid(row=0, column=7, sticky="ew", padx=(12, 0))
        ttk.Label(action_frame, textvariable=self.feedback_progress_status).grid(row=1, column=0, columnspan=8, sticky="w", pady=(8, 0))

        results = ttk.Notebook(self.feedback_tab)
        results.grid(row=4, column=0, sticky="nsew", pady=(10, 0))
        plan_frame = ttk.Frame(results, padding=8)
        results.add(plan_frame, text="Plan")
        plan_frame.columnconfigure(0, weight=1)
        plan_frame.rowconfigure(0, weight=1)
        self.feedback_plan_text = ScrolledText(plan_frame, height=8, wrap="word")
        self.feedback_plan_text.grid(row=0, column=0, sticky="nsew")

        self.feedback_metrics_text = None
        if self.diagnostics_enabled:
            metrics_frame = ttk.Frame(results, padding=8)
            results.add(metrics_frame, text="Métricas")
            metrics_frame.columnconfigure(0, weight=1)
            metrics_frame.rowconfigure(0, weight=1)
            self.feedback_metrics_text = ScrolledText(metrics_frame, height=8, wrap="word")
            self.feedback_metrics_text.grid(row=0, column=0, sticky="nsew")

        memory_frame = ttk.Frame(results, padding=8)
        results.add(memory_frame, text="Memoria")
        memory_frame.columnconfigure(0, weight=1)
        memory_frame.rowconfigure(0, weight=1)
        self.feedback_memory_text = ScrolledText(memory_frame, height=8, wrap="word")
        self.feedback_memory_text.grid(row=0, column=0, sticky="nsew")

        output_frame = ttk.Frame(results, padding=8)
        results.add(output_frame, text="Ejecución")
        output_frame.columnconfigure(0, weight=1)
        output_frame.rowconfigure(0, weight=1)
        self.feedback_output = ScrolledText(output_frame, height=8, wrap="word", state="disabled")
        self.feedback_output.grid(row=0, column=0, sticky="nsew")
        for child in source_frame.winfo_children():
            if isinstance(child, ttk.Combobox):
                child.configure(width=10)

        self._attach_tooltip(self.feedback_institution_combo, "Selecciona la institución base. Al cambiarla se filtran carreras, materias y actividades disponibles para construir memoria editorial.")
        self._attach_tooltip(self.feedback_career_combo, "Selecciona el programa educativo. Si dejas materia vacía, la propagación lateral puede abarcar otros programas de la institución.")
        self._attach_tooltip(self.feedback_subject_combo, "Selecciona la materia si quieres precisión local; desde aquí también se habilita la selección de actividades detectadas.")
        self._attach_tooltip(self.feedback_activity_combo, "La actividad afina el punto de arranque. La memoria puede propagarse desde ella hacia materia, carrera, institución e interinstitucional.")
        self._attach_tooltip(self.feedback_build_combo, "Define hasta qué nivel debe llegar la construcción en esta corrida. En local y lateral se fija al nivel del nodo origen. En descendente permite bajar hacia hijos; en ascendente y recursivo permite subir hacia padres.")
        self._attach_tooltip(self.feedback_propagation_combo, "Local: consolida sólo el nodo origen usando TEX/programa/BIB. Lateral: transfiere patrones entre hermanos del mismo nivel. Ascendente: sube hasta el nivel destino. Ascendente exhaustivo: incorpora hermanos antes de consolidar cada ascenso. Descendente: construye o refuerza hijos desde el padre. Recursivo completo: consolida subárboles completos al subir. Bidireccional progresivo: permite comunicación vertical completa, subiendo o bajando según el nivel destino.")
        self._attach_tooltip(self.feedback_iterations_spin, "Número de pasadas completas del orquestador. Cada ciclo vuelve a consultar los motores en el orden configurado.")
        self._attach_tooltip(self.feedback_engines_entry, "Selecciona los motores. Se ejecutan en el orden del menú.")
        self._attach_tooltip(self.feedback_tokens_spin, "Límite de salida por llamada LLM. Útil para controlar profundidad y costo por ciclo.")
        self._attach_tooltip(self.feedback_run_button, "Inicia la fusión de Markdown/JSON históricos del nodo y construye memoria editorial usando el DNA histórico disponible.")
        self._attach_tooltip(self.feedback_cancel_button, "Solicita cancelación cooperativa. La corrida termina al cerrar la llamada LLM en curso y conserva lo ya consolidado.")
        self._attach_tooltip(self.feedback_lock_button, "Fija las secciones actuales del scope para que siguientes corridas no las modifiquen. Se mantiene el principio de no regresión.")
        self._attach_tooltip(self.feedback_unlock_button, "Libera las fijaciones manuales del scope actual para permitir nuevas fusiones en próximas corridas.")
        self._attach_tooltip(self.feedback_refresh_button, "Relee catálogo, plan y memoria persistida desde la base SQLite y los snapshots del scope actual.")
        self._attach_tooltip(self.feedback_help_button, "Abre una guía corta para operar la construcción de memoria editorial y entender las opciones de propagación.")
        self._attach_tooltip(self.feedback_plan_text, "Vista previa del recorrido de consolidación. Muestra orden de scopes, estrategia editorial y absorción histórica esperada antes de construir memoria nueva.")
        if self.feedback_metrics_text is not None:
            self._attach_tooltip(self.feedback_metrics_text, "Resumen histórico por motor y por ciclo para los scopes actualmente incluidos en el plan visible.")
        self._attach_tooltip(self.feedback_memory_text, "Memoria editorial persistida del scope actual, herencia útil, reglas fijadas y aprendizaje reutilizable que alimenta el DNA histórico.")
        self._attach_tooltip(self.feedback_output, "Bitácora en vivo del orquestador: inicio, fusión histórica, progreso por motor, resultados, cancelación o cierre de corrida.")
        self._register_busy_widgets(
            "feedback",
            self.feedback_run_button,
            self.feedback_lock_button,
            self.feedback_unlock_button,
            self.feedback_refresh_button,
            self.feedback_institution_combo,
            self.feedback_career_combo,
            self.feedback_subject_combo,
            self.feedback_activity_combo,
            self.feedback_build_combo,
            self.feedback_propagation_combo,
            self.feedback_iterations_spin,
            self.feedback_engines_entry,
            self.feedback_tokens_spin,
        )

        self._refresh_feedback_catalog()
        self._refresh_feedback()

    def _build_investigation_tab(self) -> None:
        self.investigation_tab.columnconfigure(0, weight=1)
        self.investigation_tab.rowconfigure(0, weight=1, minsize=160)
        self.investigation_tab.rowconfigure(2, weight=1, minsize=160)
        form = ScrollableForm(self.investigation_tab)
        form.grid(row=0, column=0, sticky="nsew")

        self.investigation_institution = tk.StringVar(value=UNSELECTED_OPTION)
        self.investigation_career = tk.StringVar(value=UNSELECTED_OPTION)
        self.investigation_subject = tk.StringVar(value=UNSELECTED_OPTION)
        self.investigation_activity = tk.StringVar(value=UNSELECTED_OPTION)
        self.investigation_iterations = tk.IntVar(value=2)
        self.investigation_max_tokens = tk.IntVar(value=DEFAULT_MAX_TOKENS)
        self.investigation_engines = tk.StringVar(value=", ".join(self._ordered_feedback_engines()))
        self.investigation_scope_status = tk.StringVar(value="Scope de investigación: pendiente")
        self.investigation_progress_status = tk.StringVar(value="Listo para consolidar la base de conocimiento.")
        self.investigation_progress = tk.DoubleVar(value=0.0)

        header = ttk.Frame(form.body)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        ttk.Label(
            header,
            text="Investigación documental",
            font=("TkDefaultFont", 12, "bold"),
            wraplength=940,
        ).grid(row=0, column=0, sticky="w")
        self.investigation_help_button = ttk.Button(header, text="Ayuda", command=self._show_investigation_help)
        self.investigation_help_button.grid(row=0, column=1, sticky="e")

        source_frame = ttk.LabelFrame(form.body, text="Origen editorial", padding=10)
        source_frame.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        for index in range(8):
            source_frame.columnconfigure(index, weight=1 if index % 2 else 0)

        ttk.Label(source_frame, text="Institucion").grid(row=0, column=0, sticky="w")
        self.investigation_institution_combo = ttk.Combobox(source_frame, textvariable=self.investigation_institution, state="readonly")
        self.investigation_institution_combo.grid(row=0, column=1, sticky="ew", padx=(6, 12))
        self.investigation_institution_combo.bind("<<ComboboxSelected>>", self._on_investigation_source_changed)

        ttk.Label(source_frame, text="Carrera").grid(row=0, column=2, sticky="w")
        self.investigation_career_combo = ttk.Combobox(source_frame, textvariable=self.investigation_career, state="readonly")
        self.investigation_career_combo.grid(row=0, column=3, sticky="ew", padx=(6, 12))
        self.investigation_career_combo.bind("<<ComboboxSelected>>", self._on_investigation_source_changed)

        ttk.Label(source_frame, text="Materia").grid(row=0, column=4, sticky="w")
        self.investigation_subject_combo = ttk.Combobox(source_frame, textvariable=self.investigation_subject, state="readonly")
        self.investigation_subject_combo.grid(row=0, column=5, sticky="ew", padx=(6, 12))
        self.investigation_subject_combo.bind("<<ComboboxSelected>>", self._on_investigation_source_changed)

        ttk.Label(source_frame, text="Actividad").grid(row=0, column=6, sticky="w")
        self.investigation_activity_combo = ttk.Combobox(source_frame, textvariable=self.investigation_activity, state="readonly")
        self.investigation_activity_combo.grid(row=0, column=7, sticky="ew", padx=(6, 0))
        self.investigation_activity_combo.bind("<<ComboboxSelected>>", self._on_investigation_source_changed)

        ttk.Label(source_frame, textvariable=self.investigation_scope_status).grid(row=1, column=0, columnspan=8, sticky="w", pady=(10, 0))

        control_frame = ttk.LabelFrame(form.body, text="Consultas y motores", padding=10)
        control_frame.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        for index in range(6):
            control_frame.columnconfigure(index, weight=1 if index in {1, 3, 5} else 0)

        ttk.Label(control_frame, text="Iteraciones").grid(row=0, column=0, sticky="w")
        self.investigation_iterations_spin = ttk.Spinbox(control_frame, from_=1, to=500, textvariable=self.investigation_iterations, width=8)
        self.investigation_iterations_spin.grid(row=0, column=1, sticky="w", padx=(6, 12))

        ttk.Label(control_frame, text="Motores en orden").grid(row=0, column=2, sticky="w")
        self.investigation_engines_entry = EnginePicker(control_frame, textvariable=self.investigation_engines, choices=self._ordered_feedback_engines())
        self.investigation_engines_entry.grid(row=0, column=3, sticky="ew", padx=(6, 12))

        ttk.Label(control_frame, text="Max tokens").grid(row=0, column=4, sticky="w")
        self.investigation_tokens_spin = ttk.Spinbox(control_frame, from_=128, to=DEFAULT_MAX_TOKENS, increment=128, textvariable=self.investigation_max_tokens, width=10)
        self.investigation_tokens_spin.grid(row=0, column=5, sticky="w", padx=(6, 0))

        ttk.Label(control_frame, text="Consultas web").grid(row=1, column=0, sticky="nw", pady=(10, 0))
        self.investigation_queries_text = tk.Text(control_frame, height=5, wrap="word")
        self.investigation_queries_text.grid(row=1, column=1, columnspan=5, sticky="ew", padx=(6, 0), pady=(10, 0))

        ttk.Label(control_frame, text="URLs semilla").grid(row=2, column=0, sticky="nw", pady=(10, 0))
        self.investigation_urls_text = tk.Text(control_frame, height=4, wrap="word")
        self.investigation_urls_text.grid(row=2, column=1, columnspan=5, sticky="ew", padx=(6, 0), pady=(10, 0))

        action_frame = ttk.Frame(self.investigation_tab)
        action_frame.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        action_frame.columnconfigure(5, weight=1)
        self.investigation_run_button = ttk.Button(action_frame, text="Consolidar investigación", command=self._run_investigation)
        self.investigation_run_button.grid(row=0, column=0, sticky="w")
        self.investigation_cancel_button = ttk.Button(action_frame, text="Cancelar", command=self._cancel_investigation, state="disabled")
        self.investigation_cancel_button.grid(row=0, column=1, sticky="w", padx=(8, 0))
        self.investigation_refresh_button = ttk.Button(action_frame, text="Refrescar vista", command=self._refresh_investigation)
        self.investigation_refresh_button.grid(row=0, column=2, sticky="w", padx=(8, 0))
        self.investigation_defaults_button = ttk.Button(action_frame, text="Restaurar consultas", command=self._reset_investigation_queries)
        self.investigation_defaults_button.grid(row=0, column=3, sticky="w", padx=(8, 0))
        ttk.Progressbar(action_frame, variable=self.investigation_progress, maximum=100).grid(row=0, column=5, sticky="ew", padx=(12, 0))
        ttk.Label(action_frame, textvariable=self.investigation_progress_status).grid(row=1, column=0, columnspan=6, sticky="w", pady=(8, 0))

        results = ttk.Notebook(self.investigation_tab)
        results.grid(row=2, column=0, sticky="nsew", pady=(10, 0))
        preview_frame = ttk.Frame(results, padding=8)
        results.add(preview_frame, text="Plan")
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(0, weight=1)
        self.investigation_preview_text = ScrolledText(preview_frame, height=8, wrap="word")
        self.investigation_preview_text.grid(row=0, column=0, sticky="nsew")

        knowledge_frame = ttk.Frame(results, padding=8)
        results.add(knowledge_frame, text="Conocimiento")
        knowledge_frame.columnconfigure(0, weight=1)
        knowledge_frame.rowconfigure(0, weight=1)
        self.investigation_knowledge_text = ScrolledText(knowledge_frame, height=8, wrap="word")
        self.investigation_knowledge_text.grid(row=0, column=0, sticky="nsew")

        self.investigation_metrics_text = None
        if self.diagnostics_enabled:
            metrics_frame = ttk.Frame(results, padding=8)
            results.add(metrics_frame, text="Métricas")
            metrics_frame.columnconfigure(0, weight=1)
            metrics_frame.rowconfigure(0, weight=1)
            self.investigation_metrics_text = ScrolledText(metrics_frame, height=8, wrap="word")
            self.investigation_metrics_text.grid(row=0, column=0, sticky="nsew")

        output_frame = ttk.Frame(results, padding=8)
        results.add(output_frame, text="Ejecución")
        output_frame.columnconfigure(0, weight=1)
        output_frame.rowconfigure(0, weight=1)
        self.investigation_output = ScrolledText(output_frame, height=8, wrap="word", state="disabled")
        self.investigation_output.grid(row=0, column=0, sticky="nsew")
        for child in source_frame.winfo_children():
            if isinstance(child, ttk.Combobox):
                child.configure(width=10)

        self._attach_tooltip(self.investigation_help_button, "Explica cómo usar la fase Investigación para consolidar bibliografía, referencias, programa analítico y assets antes del extractor.")
        self._attach_tooltip(self.investigation_institution_combo, "Selecciona la institución base. El resto de filtros se actualiza según la jerarquía editorial detectada.")
        self._attach_tooltip(self.investigation_career_combo, "Selecciona la carrera cuando quieras investigar un programa completo o una materia dentro de esa trayectoria.")
        self._attach_tooltip(self.investigation_subject_combo, "Selecciona la materia para priorizar programa analítico, bibliografía recomendada y carpeta de referencias.")
        self._attach_tooltip(self.investigation_activity_combo, "Refina la investigación a una actividad concreta. Esto permite crear una carpeta de referencias específica si hace falta.")
        self._attach_tooltip(self.investigation_iterations_spin, "Número de ciclos del orquestador. Cada pasada reevalúa el conocimiento acumulado y refuerza hallazgos útiles.")
        self._attach_tooltip(self.investigation_engines_entry, "Selecciona los motores. Se ejecutan en el orden del menú.")
        self._attach_tooltip(self.investigation_tokens_spin, "Límite de salida por llamada LLM durante la fase Investigación.")
        self._attach_tooltip(self.investigation_queries_text, "Una consulta por línea. Si lo dejas vacío, AulaTeX propondrá búsquedas por defecto según el scope seleccionado.")
        self._attach_tooltip(self.investigation_urls_text, "Una URL por línea. Útil para sembrar sitios institucionales, PDF curriculares o fuentes recomendadas antes de lanzar la corrida.")
        self._attach_tooltip(self.investigation_run_button, "Inicia la consolidación de base de conocimiento y materializa artefactos como base-conocimiento, BibTeX, referencias, assets y programa analítico cuando aplique.")
        self._attach_tooltip(self.investigation_cancel_button, "Solicita cancelación cooperativa. La corrida se detiene al terminar la llamada LLM en curso.")
        self._attach_tooltip(self.investigation_refresh_button, "Relee el scope, la vista previa y el conocimiento persistido para la selección actual.")
        self._attach_tooltip(self.investigation_defaults_button, "Rellena de nuevo las consultas sugeridas para el scope actual, respetando la estructura editorial del repositorio.")
        self._attach_tooltip(self.investigation_preview_text, "Muestra los archivos y carpetas que AulaTeX planea consolidar para el scope seleccionado antes de invocar el extractor.")
        self._attach_tooltip(self.investigation_knowledge_text, "Renderiza la base de conocimiento persistida actualmente para el scope: hallazgos locales, web, bibliografía, vacíos y acciones siguientes.")
        if self.investigation_metrics_text is not None:
            self._attach_tooltip(self.investigation_metrics_text, "Resume el historial de llamadas por motor y por ciclo en la fase Investigación para este scope.")
        self._attach_tooltip(self.investigation_output, "Bitácora en vivo de la corrida de Investigación: inicio, progreso, resultados, cancelación y cierre.")
        self._register_busy_widgets(
            "investigation",
            self.investigation_run_button,
            self.investigation_refresh_button,
            self.investigation_defaults_button,
            self.investigation_help_button,
            self.investigation_institution_combo,
            self.investigation_career_combo,
            self.investigation_subject_combo,
            self.investigation_activity_combo,
            self.investigation_iterations_spin,
            self.investigation_engines_entry,
            self.investigation_tokens_spin,
            self.investigation_queries_text,
            self.investigation_urls_text,
        )

        form.bind_content()
        self._refresh_investigation_catalog()
        self._refresh_investigation()

    def _thread(self, fn) -> None:
        threading.Thread(target=fn, daemon=True).start()

    def _log(self, widget: tk.Text, text: str) -> None:
        previous_state = str(widget.cget("state"))
        widget.configure(state="normal")
        widget.insert("end", text + "\n")
        widget.see("end")
        if previous_state == "disabled":
            widget.configure(state="disabled")

    def _set_text(self, widget: tk.Text, text: str, *, readonly: bool = False) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("end", text)
        widget.see("end")
        if readonly:
            widget.configure(state="disabled")

    def _attach_tooltip(self, widget, text: str) -> None:
        self._tooltips.append(ToolTip(widget, text))

    def _register_busy_widgets(self, group: str, *widgets) -> None:
        self._busy_groups[group] = [(widget, str(widget.cget("state"))) for widget in widgets]

    def _set_busy(self, group: str, busy: bool) -> None:
        if busy:
            self._active_jobs.add(group)
        else:
            self._active_jobs.discard(group)
        labels = {"agent": "Agente", "compile": "Compilación", "generation": "Generación",
                  "feedback": "Memoria", "investigation": "Investigación", "llm-chat": "Asistente",
                  "extractor": "Extractor", "llm-check": "Comprobación IA"}
        self.task_status.set("En curso: " + ", ".join(labels.get(item, item) for item in sorted(self._active_jobs))
                             if self._active_jobs else "Listo")
        for widget, initial_state in self._busy_groups.get(group, []):
            widget.configure(state="disabled" if busy else initial_state)
        if group == "feedback":
            self.feedback_cancel_button.configure(state="normal" if busy else "disabled")
        if group == "investigation":
            self.investigation_cancel_button.configure(state="normal" if busy else "disabled")
        if group == "generation":
            self.generation_cancel_button.configure(state="normal" if busy else "disabled")
            if not busy:
                self._sync_generation_form_state()

    def _show_llm_help(self) -> None:
        messagebox.showinfo(
            "AulaTeX - Chat LLM",
            "1. Elige una sesion fija segun el tipo de trabajo.\n"
            "2. Escribe el mensaje en 'Nuevo mensaje'.\n"
            "3. AulaTeX guarda el historial automaticamente.\n"
            "4. Cuando el contexto crece, se compacta a una memoria breve reutilizable.\n"
            "5. Usa MultiMotor para consultas importantes: lanza todos los motores en paralelo y devuelve consenso.\n"
            "6. Ajusta la severidad de MultiMotor: rapido / normal / profundo.\n\n"
            "Sesiones sugeridas:\n"
            "- Editorial: tono, estilo y lineamientos.\n"
            "- Proyecto: estructura, alcance y entregables.\n"
            "- Investigacion: conceptos, autores y sintesis.\n"
            "- Operativo: LaTeX, scripts y compilacion.\n"
            "- MultiMotor: contraste entre todos los motores.",
        )

    def _show_feedback_help(self) -> None:
        messagebox.showinfo(
            "AulaTeX - Memoria editorial",
            "1. Selecciona institución, carrera, materia y, si aplica, actividad.\n"
            "2. Elige el nivel destino y el modo de propagación. 'Local' fija el destino al nodo origen; 'lateral' trabaja entre hermanos del mismo nivel; 'descendente' baja del padre a sus hijos; 'ascendente' y 'recursivo' suben; 'bidireccional' permite comunicación vertical progresiva según el nivel destino.\n"
            "3. Ajusta iteraciones, motores y max tokens.\n"
            "4. Revisa el plan de propagación antes de ejecutar.\n"
            "5. Construye la memoria: el progreso avanza por scope, ciclo y motor.\n"
            "6. Usa descendente cuando quieras construir o reforzar cerebros hijos a partir del padre; AulaTeX intentará construir cuando falte memoria y reforzar cuando ya exista.\n"
            "7. Usa lateral para aprendizaje entre hermanos: transfiere patrones reutilizables sin copiar redacción literal.\n"
            "8. Usa recursivo completo cuando necesites una construcción editorial integral: consolida el subárbol completo de cada ancestro antes de seguir subiendo.\n"
            "9. El ciclo actual absorbe Markdown/JSON históricos, fusiona sin pérdida y genera DNA histórico del nodo antes de llamar al motor.\n"
            "10. Para todos los nodos del workspace usa scripts/prueeba-lote-ejecucion.ps1: primero sin -Execute para planear y después con -Execute para correr por lotes.\n"
            "11. Usa 'Fijar reglas actuales' para congelar secciones validadas y evitar que futuras corridas las alteren.\n"
            "12. Si necesitas medir desempeño por motor y por ciclo, activa el modo diagnóstico con --diagnostics o AULATEX_ENABLE_DIAGNOSTIC_METRICS=1.\n"
            "13. Si cancelas, se conserva lo ya consolidado y el manifiesto queda marcado como cancelado.",
        )

    def _show_investigation_help(self) -> None:
        messagebox.showinfo(
            "AulaTeX - Investigación",
            "1. Selecciona institución, carrera, materia o actividad.\n"
            "2. Ajusta iteraciones, motores y max tokens.\n"
            "3. Escribe consultas web y URLs semilla si ya conoces fuentes clave.\n"
            "4. Revisa la vista previa: AulaTeX mostrará la bibliografía, referencias, programa analítico y assets que piensa consolidar.\n"
            "5. Ejecuta la corrida para reunir base de conocimiento previa al extractor.\n"
            "6. La salida persiste base-conocimiento y fuentes-web del scope; además refuerza el archivo .bib canonico y crea carpetas de referencias o assets cuando corresponda.\n"
            "7. Si necesitas medir desempeño por motor y por ciclo, activa el modo diagnóstico con --diagnostics o AULATEX_ENABLE_DIAGNOSTIC_METRICS=1.\n"
            "8. Para materias se intenta preparar programa-analitico-*.md si aún no existe; para actividades se crea una carpeta de referencias específica.",
        )

    def _show_generation_help(self) -> None:
        messagebox.showinfo(
            "AulaTeX - Generación editorial",
            "1. Generación crea o refuerza nodos editoriales descendentes sin ejecutar todavía investigación ni redacción completa.\n"
            "2. La memoria fundacional se construye con ancestros + padre + síntesis de hermanos + reglas interinstitucionales.\n"
            "3. Los ancestros son todos los niveles superiores disponibles; el padre es el nodo inmediatamente superior.\n"
            "4. Los hermanos sirven solo para sintetizar patrones editoriales recurrentes, no para copiar memoria literal.\n"
            "5. Puedes aportar ingesta textual, un documento de apoyo o ambos; la generación los toma como restricciones editoriales y material base.\n"
            "6. El destino puede ser una carpeta existente para reforzar o una nueva para crear el nodo.\n"
            "7. La salida produce memoria-fundacional-<slug>.json, plan.md y maqueta-<slug>.tex, dejando además un marcador interno para que AulaTeX reconozca el nodo generado.\n"
            "8. La maqueta-<slug>.tex funciona como instructivo editorial con indicaciones para plantilla, actividad, reporte y presentación.\n"
            "9. Después, el Agente podrá investigar, redactar, evaluar y compilar sobre esa maqueta, pero esa fase no se ejecuta en esta pestaña.",
        )

    def _refresh_generation_catalog(self) -> None:
        institutions = sorted(scope.label for scope in self.editorial_scopes.values() if scope.level == "institucion")
        self.generation_institution_combo.configure(values=self._with_unselected(institutions))
        if self.generation_institution.get() not in self.generation_institution_combo.cget("values"):
            self.generation_institution.set(UNSELECTED_OPTION)
        self._sync_generation_parent_filters()
        self._sync_generation_form_state()
        self._refresh_generation_preview()

    def _reset_generation_view(self) -> None:
        self.generation_cancel_event = threading.Event()
        self.generation_institution.set(UNSELECTED_OPTION)
        self.generation_career.set(UNSELECTED_OPTION)
        self.generation_subject.set(UNSELECTED_OPTION)
        self.generation_node_level.set("actividad")
        self.generation_mode.set("crear")
        self.generation_node_name.set("")
        self.generation_activity_number.set(1)
        self.generation_destination.set("")
        self.generation_ingest_document.set("")
        self.generation_iterations.set(2)
        self.generation_max_tokens.set(DEFAULT_MAX_TOKENS)
        self.generation_engines.set(", ".join(self._ordered_feedback_engines()))
        self.generation_ingest_text.delete("1.0", "end")
        self.generation_progress.set(0.0)
        self.generation_scope_status.set("Padre editorial: pendiente")
        self.generation_progress_status.set("Listo para generar memoria fundacional.")
        self._set_text(self.generation_output, "")
        self._refresh_generation_catalog()

    def _sync_generation_parent_filters(self) -> None:
        institution = self._selected_feedback_value(self.generation_institution)
        selected_career = self._selected_feedback_value(self.generation_career)
        selected_subject = self._selected_feedback_value(self.generation_subject)

        careers = sorted(
            scope.label
            for scope in self.editorial_scopes.values()
            if scope.level == "carrera" and scope.institution == institution
        )
        career_values = self._with_unselected(careers)
        self.generation_career_combo.configure(values=career_values)
        if selected_career not in careers:
            self.generation_career.set(UNSELECTED_OPTION)
            selected_career = ""

        subjects = sorted(
            scope.label
            for scope in self.editorial_scopes.values()
            if scope.level == "materia"
            and scope.institution == institution
            and scope.career == selected_career
        )
        self.generation_subject_combo.configure(values=self._with_unselected(subjects))
        if selected_subject not in subjects:
            self.generation_subject.set(UNSELECTED_OPTION)

    def _sync_generation_form_state(self) -> None:
        level = self.generation_node_level.get()
        if level == "institucion":
            self.generation_institution.set(UNSELECTED_OPTION)
            self.generation_career.set(UNSELECTED_OPTION)
            self.generation_subject.set(UNSELECTED_OPTION)
            self.generation_institution_combo.configure(state="disabled")
            self.generation_career_combo.configure(state="disabled")
            self.generation_subject_combo.configure(state="disabled")
        elif level == "carrera":
            self.generation_career.set(UNSELECTED_OPTION)
            self.generation_subject.set(UNSELECTED_OPTION)
            self.generation_institution_combo.configure(state="readonly")
            self.generation_career_combo.configure(state="disabled")
            self.generation_subject_combo.configure(state="disabled")
        elif level == "materia":
            self.generation_subject.set(UNSELECTED_OPTION)
            self.generation_institution_combo.configure(state="readonly")
            self.generation_career_combo.configure(state="readonly")
            self.generation_subject_combo.configure(state="disabled")
        else:
            self.generation_institution_combo.configure(state="readonly")
            self.generation_career_combo.configure(state="readonly")
            self.generation_subject_combo.configure(state="readonly")
        self.generation_activity_spin.configure(state="normal" if level == "actividad" else "disabled")

    def _on_generation_parent_changed(self, _event=None) -> None:
        self._sync_generation_parent_filters()
        self._refresh_generation_preview()

    def _on_generation_level_changed(self, _event=None) -> None:
        self._sync_generation_parent_filters()
        self._sync_generation_form_state()
        self._refresh_generation_preview()

    def _resolve_generation_parent_scope(self) -> EditorialScope | None:
        level = self.generation_node_level.get()
        institution = self._selected_feedback_value(self.generation_institution)
        career = self._selected_feedback_value(self.generation_career)
        subject = self._selected_feedback_value(self.generation_subject)

        if level == "institucion":
            return self.editorial_scopes.get("interinstitucional")
        if level == "carrera":
            if not institution:
                return None
            return self.editorial_scopes.get(self.workspace._scope_key("institucion", institution=institution))
        if level == "materia":
            if career:
                return self.editorial_scopes.get(self.workspace._scope_key("carrera", institution=institution, career=career))
            if institution:
                return self.editorial_scopes.get(self.workspace._scope_key("institucion", institution=institution))
            return None
        if not subject:
            return None
        return self.editorial_scopes.get(self.workspace._scope_key("materia", institution=institution, career=career, subject=subject))

    def _parse_generation_engines(self) -> list[str]:
        selected = [item.strip() for item in self.generation_engines.get().split(",") if item.strip()]
        valid = [engine for engine in selected if engine in self.llm.engines()]
        return valid or self._ordered_feedback_engines()

    def _build_generation_request(self) -> ConstructionRequest:
        parent_scope = self._resolve_generation_parent_scope()
        if parent_scope is None:
            raise ValueError("Selecciona un padre editorial válido para el nivel solicitado.")
        name = self.generation_node_name.get().strip()
        if not name:
            raise ValueError("Escribe el nombre del nodo a generar o reforzar.")
        ingest_text = self.generation_ingest_text.get("1.0", "end").strip()
        return ConstructionRequest(
            parent_scope_key=parent_scope.key,
            node_level=self.generation_node_level.get(),
            node_name=name,
            activity_number=max(1, int(self.generation_activity_number.get())),
            operation_mode=self.generation_mode.get(),
            destination_path=self.generation_destination.get().strip(),
            ingest_text=ingest_text,
            ingest_document_path=self.generation_ingest_document.get().strip(),
            engines=self._parse_generation_engines(),
            iterations=max(1, int(self.generation_iterations.get())),
            max_tokens=max(128, int(self.generation_max_tokens.get())),
        )

    def _refresh_generation_preview(self) -> None:
        self.generation_preview_text.delete("1.0", "end")
        if self.generation_metrics_text is not None:
            self.generation_metrics_text.delete("1.0", "end")
        parent_scope = self._resolve_generation_parent_scope()
        if parent_scope is None:
            self.generation_scope_status.set("Padre editorial: pendiente")
            self.generation_preview_text.insert(
                "end",
                "Selecciona el padre editorial adecuado según el nivel:\n"
                "- Institución: padre interinstitucional.\n"
                "- Carrera: requiere institución.\n"
                "- Materia: requiere institución y opcionalmente carrera.\n"
                "- Actividad: requiere materia.\n",
            )
            if self.generation_metrics_text is not None:
                self.generation_metrics_text.insert("end", "# Metricas de generación\n\n- Sin nodo previsualizado.\n")
            return

        self.generation_scope_status.set(
            f"Padre editorial: {parent_scope.level} | {parent_scope.key} | ruta {parent_scope.relative_path or '.'}"
        )
        try:
            request = self._build_generation_request()
            node = self.construction_builder.preview_node(request)
        except ValueError as exc:
            self.generation_preview_text.insert("end", f"Vista previa incompleta: {exc}\n")
            if self.generation_metrics_text is not None:
                self.generation_metrics_text.insert("end", "# Metricas de generación\n\n- El nodo todavía no puede resolverse.\n")
            return

        destination_exists = node.output_dir.exists()
        context_target = node.output_dir if destination_exists else node.output_dir.parent
        destination_context = self.workspace.context_summary(context_target, max_chars=2200)
        self.generation_preview_text.insert(
            "end",
            f"Nodo: {node.label}\n"
            f"Clave: {node.key}\n"
            f"Nivel: {node.level}\n"
            f"Modo: {node.operation_mode}\n"
            f"Padre: {node.parent_scope_key}\n"
            f"Destino: {node.relative_path}\n"
            f"Existe en disco: {'sí' if destination_exists else 'no'}\n"
            f"Ingesta textual: {'sí' if request.ingest_text else 'no'}\n"
            f"Documento de ingesta: {request.ingest_document_path or 'no'}\n"
            f"Entrada futura del agente: {node.future_agent_entrypoint}\n\n"
            f"Contrato del destino:\n{self.construction_builder._destination_contract(node)}\n\n"
            f"Contexto disponible:\n{destination_context}\n",
        )
        if self.generation_metrics_text is not None:
            self.generation_metrics_text.insert("end", self.construction_store.render_metrics_markdown(node.key))

    def _browse_generation_destination(self) -> None:
        path = filedialog.askdirectory(initialdir=str(self.workspace.repo_root))
        if path:
            self.generation_destination.set(self.workspace.relative(path))
            self._refresh_generation_preview()

    def _browse_generation_ingest_document(self) -> None:
        path = filedialog.askopenfilename(initialdir=str(self.workspace.repo_root))
        if path:
            self.generation_ingest_document.set(self.workspace.relative(path))
            self._refresh_generation_preview()

    def _run_generation(self) -> None:
        try:
            request = self._build_generation_request()
            node = self.construction_builder.preview_node(request)
        except ValueError as exc:
            messagebox.showwarning("AulaTeX", str(exc))
            return

        self.generation_cancel_event = threading.Event()
        self.generation_progress.set(0.0)
        self.generation_progress_status.set("Generando memoria fundacional, plan y maqueta...")
        self._log(
            self.generation_output,
            f"[GENERACION] Inicio {node.key} | modo={request.operation_mode} | destino={node.relative_path} | motores={', '.join(self._parse_generation_engines())}",
        )
        self._set_busy("generation", True)

        def on_progress(event: ConstructionEvent) -> None:
            self.events.put(("generation-progress", event))

        def work() -> None:
            try:
                result = self.construction_builder.build(request, progress=on_progress, cancel_event=self.generation_cancel_event)
                self.events.put(("generation-result", result))
            except Exception as exc:
                self.events.put(("generation-error", f"[GENERACION] ERROR {type(exc).__name__}: {exc}"))

        self._thread(work)

    def _cancel_generation(self) -> None:
        if self.generation_cancel_button.cget("state") == "disabled":
            return
        self.generation_cancel_event.set()
        self.generation_progress_status.set("Cancelación solicitada. Se cerrará al terminar la llamada en curso.")
        self._log(self.generation_output, "[GENERACION] Cancelación solicitada por el usuario.")

    def _handle_generation_progress(self, event: ConstructionEvent) -> None:
        percent = 0.0
        if event.total > 0:
            percent = (float(event.current) / float(event.total)) * 100.0
        self.generation_progress.set(percent)
        self.generation_progress_status.set(event.message)
        prefix = f"[{event.kind.upper()}]"
        if event.engine:
            prefix += f" {event.engine}"
        if event.cycle:
            prefix += f" ciclo={event.cycle}"
        if event.node_key:
            prefix += f" node={event.node_key}"
        self._log(self.generation_output, f"{prefix} {event.message}")
        if event.kind in {"result", "done"}:
            self._refresh_generation_preview()

    def _selected_llm_session(self) -> str:
        selected = self.llm_session_tree.selection() if hasattr(self, "llm_session_tree") else ()
        if selected:
            return self.llm_session_nodes.get(selected[0], "editorial")
        states = self.chat_store.list_sessions()
        return states[0].definition.key if states else "editorial"

    def _refresh_llm_sessions(self) -> None:
        if not hasattr(self, "llm_session_tree"):
            return
        selected_key = self._selected_llm_session()
        for item in self.llm_session_tree.get_children():
            self.llm_session_tree.delete(item)
        self.llm_session_nodes = {}
        for state in self.chat_store.list_sessions():
            mode_label = "Todos" if state.definition.mode == "multi" else state.definition.assigned_engine
            node = self.llm_session_tree.insert(
                "",
                "end",
                text=state.definition.label,
                values=(mode_label, state.context_label, f"{state.active_messages}/{state.message_count}"),
                open=True,
            )
            self.llm_session_nodes[node] = state.definition.key
            if state.definition.key == selected_key:
                self.llm_session_tree.selection_set(node)
                self.llm_session_tree.focus(node)
        if not self.llm_session_tree.selection() and self.llm_session_tree.get_children():
            first = self.llm_session_tree.get_children()[0]
            self.llm_session_tree.selection_set(first)
            self.llm_session_tree.focus(first)

    def _on_llm_session_selected(self, _event=None) -> None:
        self._refresh_llm_view(self._selected_llm_session())

    def _refresh_llm_view(self, session_key: str | None = None, *, status: str | None = None) -> None:
        key = session_key or self._selected_llm_session()
        state = self.chat_store.get_session_state(key)
        messages = self.chat_store.get_messages(key, include_compacted=False, limit=80)
        timeline = self.chat_store.get_visible_history(key, message_limit=80, compaction_limit=20)
        if state.definition.mode == "multi":
            self.llm_multi_severity_combo.configure(state="readonly")
        else:
            self.llm_multi_severity_combo.configure(state="disabled")
        self.llm_session_title.set(state.definition.label)
        self.llm_session_meta.set(
            f"{state.definition.description} | Modo: {'multimotor' if state.definition.mode == 'multi' else 'especializado'} | "
            f"Motores: {', '.join(state.definition.engine_list)} | Contexto estimado: ~{state.context_label} | "
            f"Compactaciones: {state.compaction_count}"
        )
        transcript = self._format_llm_transcript(timeline)
        diagnostics = self._format_llm_diagnostics(state, messages)
        self._set_text(self.llm_output, transcript, readonly=True)
        self._set_text(self.llm_system, diagnostics, readonly=True)
        self.llm_status.set(status or f"Sesion activa: {state.definition.label}")

    def _format_llm_transcript(self, timeline) -> str:
        if not timeline:
            return (
                "Sin mensajes aun.\n\n"
                "Sugerencia: usa una sesion tematica distinta para cada tipo de trabajo y deja que AulaTeX compacte el contexto automaticamente."
            )
        chunks: list[str] = []
        for item in timeline:
            if item.kind == "compaction" and item.compaction is not None:
                summary = item.compaction
                chunks.extend(
                    [
                        f"Resumen compactado #{summary.id}",
                        f"Mensajes resumidos: {summary.compacted_messages} | Caracteres: {summary.compacted_chars}",
                        summary.summary_text,
                        "",
                        "═" * 72,
                        "",
                    ]
                )
                continue
            if item.message is None:
                continue
            role = "Usuario" if item.message.role == "user" else "Asistente"
            engine = f" [{item.message.engine}]" if item.message.engine else ""
            chunks.extend([f"{role}{engine}", item.message.content, "", "─" * 72, ""])
        return "\n".join(chunks).strip()

    def _format_llm_diagnostics(self, state, messages) -> str:
        lines = [
            self.chat_store.session_help(state.definition.key),
            "",
            f"Contexto estimado actual: ~{state.context_label}",
            f"Mensajes activos: {state.active_messages} de {state.message_count}",
            f"Compactaciones registradas: {state.compaction_count}",
            "",
            "Memoria compactada vigente:",
            state.summary_text or "Sin memoria compactada aun.",
        ]
        if state.definition.mode == "multi":
            lines.extend(["", f"Severidad MultiMotor seleccionada: {multimotor_severity_label(self.llm_multi_severity.get())}"])
        last_multi = None
        for message in reversed(messages):
            if isinstance(message.metadata, dict) and message.metadata.get("engine_results"):
                last_multi = message.metadata["engine_results"]
                break
        if last_multi:
            lines.extend(["", "Ultimo consenso multimotor:"])
            for item in last_multi:
                engine = item.get("engine", "Motor")
                ok = "OK" if item.get("ok") else "ERROR"
                body = item.get("text") or item.get("error") or "Sin contenido."
                lines.append(f"- {engine}: {ok} | {body[:220].replace(chr(10), ' ')}")
        return "\n".join(lines).strip()

    def _compact_selected_llm_session(self) -> None:
        session_key = self._selected_llm_session()
        self._set_busy("llm-chat", True)

        def work() -> None:
            try:
                compacted = self.chat_store.compact_session(session_key, force=True)
                status = "Sesion compactada." if compacted else "No habia suficiente historial para compactar."
                self.events.put(("llm-refresh", {"session_key": session_key, "status": status}))
            except Exception as exc:
                self.events.put(("llm-error", str(exc)))

        self._thread(work)

    def _export_selected_llm_session(self) -> None:
        session_key = self._selected_llm_session()
        self._set_busy("llm-chat", True)

        def work() -> None:
            try:
                path = self.chat_store.export_session_markdown(session_key)
                self.events.put(("result-path", ("llm-chat", path)))
                self.events.put(("llm-refresh", {"session_key": session_key, "status": f"Sesion exportada en {path}"}))
            except Exception as exc:
                self.events.put(("llm-error", str(exc)))

        self._thread(work)

    def _clear_selected_llm_session(self) -> None:
        session_key = self._selected_llm_session()
        state = self.chat_store.get_session_state(session_key)
        confirmed = messagebox.askyesno(
            "AulaTeX",
            f"¿Reiniciar la sesion '{state.definition.label}'? Se borrara historial y memoria compactada de ese tema.",
        )
        if not confirmed:
            return
        self.chat_store.clear_session(session_key)
        self._refresh_llm_sessions()
        self._refresh_llm_view(session_key, status=f"Sesion {state.definition.label} reiniciada.")

    def _check_llms(self) -> None:
        if "llm-check" in self._active_jobs:
            return
        self._set_busy("llm-check", True)
        self.main_notebook.select(self.llm_tab)
        def work() -> None:
            try:
                for engine in self.llm.engines():
                    result = self.llm.check(engine)
                    self.events.put(("llm", f"[LLM] {engine}: {'OK' if result.ok else 'ERROR'} {result.text or result.error}"))
            except Exception as exc:
                self.events.put(("llm", f"[LLM] ERROR: {exc}"))
            finally:
                self.events.put(("llm-check-finished", None))

        self._thread(work)

    def _refresh_tree(self) -> None:
        selected_key = ""
        selected = self.template_tree.selection()
        if selected:
            current_scope = self.template_nodes.get(selected[0]) if hasattr(self, "template_nodes") else None
            selected_key = current_scope.key if current_scope is not None else ""
        if self._tree_refresh_pending:
            self._tree_refresh_queued = True
            return

        self._tree_refresh_pending = True
        self._tree_refresh_queued = False
        self._set_text(
            self.template_details,
            "Cargando arbol editorial. El inventario, las memorias y los artefactos se estan resolviendo.\n",
        )

        def work() -> None:
            try:
                editorial_scopes, editorial_children = self.workspace.editorial_scope_index()
                scope_keys = list(editorial_scopes)
                memories = self.editorial_store.get_memories(scope_keys)
                existing_nodes = self.construction_store.node_exists_many(scope_keys)
                node_values: dict[str, tuple[str, str, str]] = {}
                for scope in editorial_scopes.values():
                    memory = memories.get(scope.key, {})
                    has_memory = any(memory.get(section) for section in MEMORY_SECTIONS)
                    generation_ready = self._scope_has_generation_artifacts(scope, existing_nodes=existing_nodes)
                    node_values[scope.key] = (
                        "[x]" if has_memory else "[ ]",
                        str(len(memory.get("locked_sections", []))) if has_memory else "0",
                        "[x]" if generation_ready else "[ ]",
                    )
                self.events.put(
                    (
                        "tree-refresh",
                        {
                            "selected_key": selected_key,
                            "editorial_scopes": editorial_scopes,
                            "editorial_children": editorial_children,
                            "node_values": node_values,
                        },
                    )
                )
            except Exception as exc:
                self.events.put(("tree-refresh-error", f"[ARBOL] ERROR {type(exc).__name__}: {exc}"))

        self._thread(work)

    def _apply_tree_refresh(self, payload: dict) -> None:
        for item in self.template_tree.get_children():
            self.template_tree.delete(item)

        self.editorial_scopes = payload.get("editorial_scopes", {})
        self.editorial_children = payload.get("editorial_children", {})
        self.template_node_values = payload.get("node_values", {})
        if not self._active_jobs.intersection({"generation", "feedback", "investigation"}):
            self._refresh_generation_catalog()
            self._refresh_feedback()
            self._refresh_investigation()
        self._set_text(
            self.template_details,
            "Selecciona un nodo editorial para ver el resumen. Presiona Enter para abrir el visor del nodo. "
            "Usa flechas o doble clic para expandir y contraer niveles.\n",
        )

        self.template_nodes = {}
        root_scope = self.editorial_scopes.get("interinstitucional")
        if root_scope is not None:
            self._insert_template_node("", root_scope)

        selected_key = str(payload.get("selected_key") or "")
        if selected_key:
            for item, scope in self.template_nodes.items():
                if scope.key == selected_key:
                    self.template_tree.selection_set(item)
                    self.template_tree.focus(item)
                    self.template_tree.see(item)
                    self._on_template_selected()
                    break
        elif self.template_tree.get_children():
            first = self.template_tree.get_children()[0]
            self.template_tree.selection_set(first)
            self.template_tree.focus(first)
            self._on_template_selected()

    def _insert_template_node(self, parent: str, scope: EditorialScope) -> None:
        values = self.template_node_values.get(scope.key)
        if values is None:
            memory = self.editorial_store.get_memory(scope.key)
            has_memory = any(memory.get(section) for section in MEMORY_SECTIONS)
            generation_ready = self._scope_has_generation_artifacts(scope)
            values = (
                "[x]" if has_memory else "[ ]",
                str(len(memory.get("locked_sections", []))) if has_memory else "0",
                "[x]" if generation_ready else "[ ]",
            )
        item = self.template_tree.insert(
            parent,
            "end",
            text=f"{scope.level}: {scope.label}",
            values=values,
            open=scope.level in {"interinstitucional", "institucion", "carrera"},
        )
        self.template_nodes[item] = scope
        for child in self.editorial_children.get(scope.key, []):
            self._insert_template_node(item, child)

    def _scope_has_generation_artifacts(self, scope: EditorialScope, *, existing_nodes: set[str] | None = None) -> bool:
        if existing_nodes is not None:
            if scope.key in existing_nodes:
                return True
        elif self.construction_store.node_exists(scope.key):
            return True
        if not scope.relative_path or scope.relative_path == ".":
            return False
        scope_path = self.workspace.resolve_target(scope.relative_path)
        if not scope_path.exists() or not scope_path.is_dir():
            return False
        if (scope_path / GENERATION_MARKER_FILENAME).exists():
            return True
        return (
            any(scope_path.glob("memoria-fundacional*.json"))
            or (scope_path / "plan.md").exists()
            or any(scope_path.glob("maqueta*.tex"))
        )

    def _render_template_scope_summary(self, scope: EditorialScope) -> str:
        memory = self.editorial_store.get_memory(scope.key)
        local_sections = [section for section in MEMORY_SECTIONS if memory.get(section)]
        generation_state = "sí" if self._scope_has_generation_artifacts(scope) else "no"
        lines = [
            f"Nivel: {scope.level}",
            f"Etiqueta: {scope.label}",
            f"Clave: {scope.key}",
            f"Ruta: {scope.relative_path or '.'}",
            f"Padre: {scope.parent_key or 'raíz'}",
            f"Memoria local: {'sí' if local_sections else 'no'}",
            f"Secciones con contenido: {', '.join(local_sections) or 'ninguna'}",
            f"Secciones fijadas: {', '.join(memory.get('locked_sections', [])) or 'ninguna'}",
            f"Artefactos de generación: {generation_state}",
            "",
            "Atajos:",
            "- Enter: visualizar nodo",
            "- Doble clic: expandir o contraer",
            "- Flechas: navegar el árbol",
        ]
        if self.diagnostics_enabled:
            lines.extend(["", self.editorial_store.render_metrics_markdown([scope.key]).strip()])
        return "\n".join(lines).strip()

    def _on_template_selected(self, _event=None) -> None:
        selected = self.template_tree.selection()
        if not selected:
            return
        scope = self.template_nodes.get(selected[0])
        if scope is None:
            return
        self._set_text(self.template_details, self._render_template_scope_summary(scope))

    def _toggle_template_node(self, event=None):
        item = self.template_tree.identify_row(event.y) if event is not None else ""
        if not item:
            item = self.template_tree.focus()
        if not item:
            return "break"
        self.template_tree.selection_set(item)
        self.template_tree.focus(item)
        self.template_tree.item(item, open=not bool(self.template_tree.item(item, "open")))
        return "break"

    def _show_template_node_details(self, _event=None):
        selected = self.template_tree.selection()
        if not selected:
            return "break"
        scope = self.template_nodes.get(selected[0])
        if scope is None:
            return "break"

        window = tk.Toplevel(self)
        window.title(f"Nodo editorial | {scope.label}")
        window.geometry("980x720")
        window.minsize(760, 520)
        window.transient(self)

        container = ttk.Frame(window, padding=12)
        container.pack(fill="both", expand=True)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(1, weight=1)

        header = ttk.Frame(container)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text=f"{scope.level} | {scope.label}", font=("TkDefaultFont", 11, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(header, text=f"Clave: {scope.key} | Ruta: {scope.relative_path or '.'}", wraplength=860).grid(row=1, column=0, sticky="w", pady=(4, 0))

        notebook = ttk.Notebook(container)
        notebook.grid(row=1, column=0, sticky="nsew")

        summary_text = self._build_template_scope_dialog_summary(scope)
        memory_text = self._build_template_scope_memory(scope)
        inherited_text = self._build_template_scope_inherited_memory(scope)
        generation_text = self._build_template_scope_generation(scope)

        for tab_title, content in (
            ("Resumen", summary_text),
            ("Memoria", memory_text),
            ("Herencia", inherited_text),
            ("Generación", generation_text),
        ):
            frame = ttk.Frame(notebook, padding=8)
            frame.columnconfigure(0, weight=1)
            frame.rowconfigure(0, weight=1)
            text = tk.Text(frame, wrap="word")
            text.grid(row=0, column=0, sticky="nsew")
            self._set_text(text, content, readonly=True)
            notebook.add(frame, text=tab_title)

        ttk.Button(container, text="Cerrar", command=window.destroy).grid(row=2, column=0, sticky="e", pady=(10, 0))
        return "break"

    def _build_template_scope_dialog_summary(self, scope: EditorialScope) -> str:
        chain = [f"{item.level}: {item.label}" for item in reversed(self.workspace.scope_chain(scope.key))]
        body = (
            f"Nivel: {scope.level}\n"
            f"Etiqueta: {scope.label}\n"
            f"Clave: {scope.key}\n"
            f"Ruta: {scope.relative_path or '.'}\n"
            f"Padre: {scope.parent_key or 'raíz'}\n"
            f"Cadena editorial: {' > '.join(chain)}\n"
        )
        if self.diagnostics_enabled:
            editorial_metrics = self.editorial_store.render_metrics_markdown([scope.key]).strip()
            construction_metrics = self.construction_store.render_metrics_markdown(scope.key).strip()
            body += f"\n\n{editorial_metrics}\n\n{construction_metrics}"
        return body

    def _build_template_scope_memory(self, scope: EditorialScope) -> str:
        memory = self.editorial_store.get_memory(scope.key)
        if any(memory.get(section) for section in MEMORY_SECTIONS):
            return self.editorial_store.render_memory_markdown(scope, memory)
        return (
            "# Memoria editorial AulaTeX\n\n"
            "- Este nodo todavía no tiene memoria local persistida.\n"
            "- Puede heredar contexto desde sus ancestros o desde snapshots de generación."
        )

    def _build_template_scope_inherited_memory(self, scope: EditorialScope) -> str:
        inherited = self.editorial_store.summarize_for_scope(scope.key, include_ancestors=True, max_chars=14000).strip()
        if inherited:
            return inherited
        return "# Herencia editorial\n\n- No hay memoria heredada disponible todavía para este nodo.\n"

    def _build_template_scope_generation(self, scope: EditorialScope) -> str:
        latest_run = self.construction_store.get_latest_run(scope.key)
        snapshots = self.construction_store.list_memory_snapshots(scope.key, limit=12)
        cycles = self.construction_store.list_recent_cycles(scope.key, limit=12) if self.diagnostics_enabled else []
        lines = ["# Generación editorial", ""]
        if latest_run is not None:
            status = "OK" if int(latest_run["ok"] or 0) else "ERROR"
            if int(latest_run["cancelled"] or 0):
                status = "CANCELADA"
            lines.extend(
                [
                    "## Última corrida",
                    "",
                    f"- Run ID: {latest_run['run_id']}",
                    f"- Estado: {status}",
                    f"- Creada: {latest_run['created_at']}",
                    f"- Finalizada: {latest_run['completed_at'] or 'en curso o sin cierre'}",
                    f"- Iteraciones: {latest_run['iterations']}",
                    f"- Manifiesto: {latest_run['manifest_path'] or 'sin manifiesto'}",
                    "",
                ]
            )
        else:
            lines.extend(["## Última corrida", "", "- No hay corridas de generación registradas para este nodo.", ""])

        if self.diagnostics_enabled:
            lines.extend([self.construction_store.render_metrics_markdown(scope.key).strip(), ""])

        if snapshots:
            lines.extend(["## Snapshots de memoria", ""])
            for snapshot in snapshots:
                summary = str(snapshot["summary_text"] or "").strip().replace("\n", " ")
                lines.append(
                    f"- {snapshot['memory_kind']} | {snapshot['created_at']} | run={snapshot['run_id']} | {summary[:220] or 'sin resumen'}"
                )
            lines.append("")
        else:
            lines.extend(["## Snapshots de memoria", "", "- No hay snapshots de generación para este nodo.", ""])

        if cycles:
            lines.extend(["## Ciclos recientes", ""])
            for cycle in cycles:
                lines.append(
                    f"- Ciclo {cycle['cycle_index']} | {cycle['engine']} | {'OK' if int(cycle['ok'] or 0) else 'ERROR'} | "
                    f"chars={int(cycle['response_chars'] or 0)} | memoria={int(cycle['memory_items'] or 0)} | "
                    f"secciones={int(cycle['sections_created'] or 0)} | avance={int(cycle['progress_percent'] or 0)}% | {cycle['created_at']}"
                )
            lines.append("")
        else:
            lines.extend(["## Ciclos recientes", "", "- No hay ciclos de generación persistidos para este nodo.", ""])

        return "\n".join(lines).strip()

    def _run_llm_prompt(self) -> None:
        session_key = self._selected_llm_session()
        prompt = self.prompt_text.get("1.0", "end").strip()
        if not prompt:
            messagebox.showwarning("AulaTeX", "Escribe un prompt.")
            return
        self.prompt_text.delete("1.0", "end")
        severity = self.llm_multi_severity.get()
        self._set_busy("llm-chat", True)

        def work() -> None:
            try:
                self.events.put(("llm-system", f"Procesando en {self.chat_store.get_definition(session_key).label}..."))
                tool_result = self._handle_local_tool_prompt(prompt)
                if tool_result is not None:
                    result = self.chat_store.record_local_exchange(session_key, prompt, tool_result)
                else:
                    result = self.chat_store.send_prompt(session_key, prompt, severity=severity)
                self.events.put(("llm-refresh", {"session_key": session_key, "status": result.status_message}))
            except Exception as exc:
                self.events.put(("llm-error", {"error": f"{type(exc).__name__}: {exc}",
                                               "prompt": prompt, "session_key": session_key}))

        self._thread(work)

    def _handle_local_tool_prompt(self, prompt: str) -> str | None:
        text = prompt.strip().casefold()

        if text == "/listar-tex":
            files = self.workspace.find_tex_files(limit=200)
            return "[HERRAMIENTA] Archivos TEX encontrados\n\n" + "\n".join(self.workspace.relative(f) for f in files[:200])

        if text == "/explorar":
            return self.workspace.context_summary(".", max_chars=4000)

        return None

    def _browse_agent_target(self) -> None:
        path = filedialog.askdirectory(initialdir=str(self.workspace.repo_root))
        if path:
            self.agent_target.set(self.workspace.relative(path))

    def _run_agent(self) -> None:
        try:
            target = self.agent_target.get().strip()
            if not target or not (self.workspace.repo_root / target).exists():
                raise ValueError("Selecciona un objetivo existente.")
            if not 1 <= self.agent_activity.get() <= 99:
                raise ValueError("La actividad debe estar entre 1 y 99.")
            if self.agent_monitor_mode.get():
                if not 1 <= self.agent_max_cycles.get() <= 20:
                    raise ValueError("Los ciclos deben estar entre 1 y 20.")
            elif not 1 <= self.agent_iterations.get() <= 500:
                raise ValueError("Las iteraciones deben estar entre 1 y 500.")
        except (ValueError, tk.TclError) as exc:
            messagebox.showwarning("AulaTeX", f"Revisa la configuración: {exc}", parent=self)
            return
        if self.agent_monitor_mode.get():
            self._run_activity_monitor()
            return

        engines = [item.strip() for item in self.agent_engines.get().split(",") if item.strip()]
        request = AgentRequest(
            target=self.agent_target.get(),
            level=self.agent_level.get(),
            action=self.agent_action.get(),
            activity_number=int(self.agent_activity.get()),
            engines=engines,
            iterations=int(self.agent_iterations.get()),
            compile_tex=bool(self.agent_compile.get()),
            apply_feedback=bool(self.agent_apply.get()),
        )
        self._set_busy("agent", True)

        def work() -> None:
            try:
                result = self.agent.run(request)
                self.events.put(("result-path", ("agent", result.report_path)))
                self.events.put(("agent", f"[AGENTE] {'OK' if result.ok else 'CON OBSERVACIONES'}\nReporte: {result.report_path}"))
            except Exception as exc:
                self.events.put(("agent-error", f"[AGENTE] ERROR {type(exc).__name__}: {exc}"))

        self._thread(work)

    def _run_activity_monitor(self) -> None:
        monitor = ActivityMonitor(self.workspace)
        request = ActivityMonitorRequest(
            target=self.agent_target.get(),
            activity_number=int(self.agent_activity.get()),
            max_cycles=int(self.agent_max_cycles.get()),
            compile_check=bool(self.agent_compile.get()),
            run_extractor=bool(self.agent_run_extractor.get()),
        )
        self._set_busy("agent", True)

        def work() -> None:
            try:
                result = monitor.run(request)
                self.events.put(("result-path", ("agent", result.report_path)))
                self.events.put(
                    (
                        "agent",
                        f"[MONITOR] {'PASS' if result.ok else 'PENDIENTE'}\nManifest: {result.manifest_path}\nReporte: {result.report_path}",
                    )
                )
            except Exception as exc:
                self.events.put(("agent-error", f"[MONITOR] ERROR {type(exc).__name__}: {exc}"))

        self._thread(work)

    def _browse_tex(self) -> None:
        path = filedialog.askopenfilename(initialdir=str(self.workspace.repo_root), filetypes=[("TeX", "*.tex")])
        if path:
            self.compile_target.set(self.workspace.relative(path))

    def _compile_selected(self) -> None:
        target = self.compile_target.get().strip()
        if not target:
            messagebox.showwarning("AulaTeX", "Selecciona un archivo .tex.")
            return
        self._set_busy("compile", True)

        def work() -> None:
            try:
                result = self.workspace.compile_tex(target)
                if result.ok:
                    self.events.put(("result-path", ("compile", Path(target).with_suffix(".pdf"))))
                self.events.put(("compile", f"[COMPILAR] {'OK' if result.ok else 'ERROR'} {target}\n{result.stdout[-4000:]}\n{result.stderr[-2000:]}"))
            except Exception as exc:
                self.events.put(("compile-error", f"[COMPILAR] ERROR {type(exc).__name__}: {exc}"))

        self._thread(work)

    def _open_extractor_gui(self) -> None:
        script = self.workspace.scripts_dir / "extractor.ps1"
        subprocess.Popen(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script)], cwd=str(self.workspace.repo_root))

    def _probe_extractor(self) -> None:
        script = self.workspace.scripts_dir / "extractor-conceptos-ideas" / "runners" / "probar_configuracion.ps1"
        self._set_busy("extractor", True)

        def work() -> None:
            try:
                proc = subprocess.run(
                    ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script)],
                    cwd=str(script.parent),
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
                self.events.put(("extractor", f"[EXTRACTOR] {proc.returncode}\n{proc.stdout}\n{proc.stderr}"))
            except Exception as exc:
                self.events.put(("extractor-error", f"[EXTRACTOR] ERROR {type(exc).__name__}: {exc}"))

        self._thread(work)

    def _refresh_feedback(self) -> None:
        self._refresh_feedback_catalog()
        self._refresh_feedback_plan_and_memory()

    def _refresh_feedback_catalog(self) -> None:
        institutions = sorted(scope.label for scope in self.editorial_scopes.values() if scope.level == "institucion")
        self.feedback_institution_combo.configure(values=self._with_unselected(institutions))
        if self.feedback_institution.get() not in self.feedback_institution_combo.cget("values"):
            self.feedback_institution.set(UNSELECTED_OPTION)
        self._sync_feedback_source_filters()

    def _sync_feedback_source_filters(self) -> None:
        institution = self._selected_feedback_value(self.feedback_institution)
        selected_career = self._selected_feedback_value(self.feedback_career)
        selected_subject = self._selected_feedback_value(self.feedback_subject)
        selected_activity = self._selected_feedback_value(self.feedback_activity)

        careers = sorted(
            scope.label
            for scope in self.editorial_scopes.values()
            if scope.level == "carrera" and scope.institution == institution
        )
        career_values = self._with_unselected(careers)
        self.feedback_career_combo.configure(values=career_values)
        if selected_career not in careers:
            self.feedback_career.set(UNSELECTED_OPTION)
            selected_career = ""

        subjects = sorted(
            scope.label
            for scope in self.editorial_scopes.values()
            if scope.level == "materia"
            and scope.institution == institution
            and scope.career == selected_career
        )
        subject_values = self._with_unselected(subjects)
        self.feedback_subject_combo.configure(values=subject_values)
        if selected_subject not in subjects:
            self.feedback_subject.set(UNSELECTED_OPTION)
            selected_subject = ""

        activities = sorted(
            scope.label
            for scope in self.editorial_scopes.values()
            if scope.level == "actividad"
            and scope.institution == institution
            and scope.career == selected_career
            and scope.subject == selected_subject
        )
        activity_values = self._with_unselected(activities)
        self.feedback_activity_combo.configure(values=activity_values)
        if selected_activity not in activities:
            self.feedback_activity.set(UNSELECTED_OPTION)

    def _on_feedback_source_changed(self, _event=None) -> None:
        self._sync_feedback_source_filters()
        self._refresh_feedback_plan_and_memory()

    def _on_feedback_plan_changed(self, _event=None) -> None:
        self._refresh_feedback_plan_and_memory()

    def _effective_feedback_build_level(self, scope: EditorialScope | None) -> str:
        if scope is None:
            return self.feedback_build_level.get() or "interinstitucional"
        if self.feedback_propagation.get() in {"local", "lateral"}:
            return scope.level
        selected = self.feedback_build_level.get() or scope.level
        return selected if selected in EDITORIAL_LEVELS else scope.level

    def _resolve_feedback_scope(self) -> EditorialScope | None:
        institution = self._selected_feedback_value(self.feedback_institution)
        career = self._selected_feedback_value(self.feedback_career)
        subject = self._selected_feedback_value(self.feedback_subject)
        activity = self._selected_feedback_value(self.feedback_activity)

        if activity and subject:
            key = self.workspace._scope_key("actividad", institution=institution, career=career, subject=subject, activity=activity)
        elif subject:
            key = self.workspace._scope_key("materia", institution=institution, career=career, subject=subject)
        elif career:
            key = self.workspace._scope_key("carrera", institution=institution, career=career)
        elif institution:
            key = self.workspace._scope_key("institucion", institution=institution)
        else:
            key = "interinstitucional"
        return self.editorial_scopes.get(key)

    def _refresh_feedback_plan_and_memory(self) -> None:
        scope = self._resolve_feedback_scope()
        self._refresh_feedback_build_levels(scope)

        self.feedback_plan_text.delete("1.0", "end")
        if self.feedback_metrics_text is not None:
            self.feedback_metrics_text.delete("1.0", "end")
        self.feedback_memory_text.delete("1.0", "end")

        if scope is None:
            self.feedback_scope_status.set("Origen resuelto: no encontrado")
            self.feedback_plan_text.insert("end", "Selecciona una institucion, carrera, materia o actividad valida.\n")
            if self.feedback_metrics_text is not None:
                self.feedback_metrics_text.insert("end", "# Metricas\n\n- Sin plan activo.\n")
            self.feedback_memory_text.insert("end", self._feedback_schema_preview())
            return

        self.feedback_scope_status.set(
            f"Origen resuelto: {scope.level} | {scope.key} | ruta {scope.relative_path or '.'}"
        )
        build_level = self._effective_feedback_build_level(scope)
        try:
            plan = self.editorial_builder.plan_scopes(scope.key, build_level, self.feedback_propagation.get())
        except ValueError as exc:
            plan = []
            self.feedback_plan_text.insert("end", f"Plan invalido: {exc}\n")

        self.feedback_plan_text.insert("end", f"Propagacion: {PROPAGATION_LABELS.get(self.feedback_propagation.get(), self.feedback_propagation.get())}\n")
        self.feedback_plan_text.insert("end", f"Nivel destino: {build_level}\n")
        self.feedback_plan_text.insert("end", "Fusion previa: activa. AulaTeX absorbe Markdown/JSON historicos del scope, genera DNA historico y lo inyecta en el prompt del ciclo.\n")
        self.feedback_plan_text.insert("end", "Ejecucion lote recomendada: scripts/prueeba-lote-ejecucion.ps1 primero en modo plan y despues con -Execute.\n\n")
        if self.feedback_propagation.get() == "local":
            self.feedback_plan_text.insert("end", "Modo local: la memoria editorial se construye sólo para el nodo origen usando sus fuentes editoriales directas y su DNA historico fusionado.\n\n")
        elif self.feedback_propagation.get() == "lateral":
            self.feedback_plan_text.insert("end", "Modo lateral: AulaTeX sincroniza aprendizaje reutilizable entre nodos hermanos del mismo nivel sin copiar redacción literal.\n\n")
        elif self.feedback_propagation.get() == "descendente":
            self.feedback_plan_text.insert("end", "Modo descendente: AulaTeX baja del nodo origen hacia hijos para construir andamiaje cuando falte memoria o reforzarla cuando ya exista.\n\n")
        elif self.feedback_propagation.get() == "bidireccional":
            self.feedback_plan_text.insert("end", "Modo bidireccional: AulaTeX permite comunicación vertical progresiva entre padres e hijos según el nivel destino seleccionado.\n\n")
        if plan:
            for index, item in enumerate(plan, start=1):
                transfer = self.editorial_builder.describe_scope_transfer(scope.key, item.key, self.feedback_propagation.get())
                self.feedback_plan_text.insert(
                    "end",
                    f"{index}. {item.level} | {item.label} | {item.key} | {transfer.get('objective', 'refuerzo')} | {transfer.get('strategy', 'progresiva')}\n",
                )
        else:
            self.feedback_plan_text.insert("end", "No hay scopes programados para esta combinacion.\n")
        if self.feedback_metrics_text is not None:
            self.feedback_metrics_text.insert("end", self.editorial_store.render_metrics_markdown([item.key for item in plan] or [scope.key]))

        memory = self.editorial_store.get_memory(scope.key)
        if any(memory.get(section) for section in MEMORY_SECTIONS):
            self.feedback_memory_text.insert("end", self.editorial_store.render_memory_markdown(scope, memory))
            inherited = self.editorial_store.summarize_for_scope(scope.key, include_ancestors=True, max_chars=7000)
            if inherited.strip():
                self.feedback_memory_text.insert("end", "\n\n## Herencia util\n\n")
                self.feedback_memory_text.insert("end", inherited)
        else:
            self.feedback_memory_text.insert("end", self._feedback_schema_preview(scope))

    def _refresh_feedback_build_levels(self, scope: EditorialScope | None) -> None:
        mode = self.feedback_propagation.get()
        if scope is None:
            options = ["interinstitucional"]
            default_level = "interinstitucional"
        else:
            start_index = EDITORIAL_LEVELS.index(scope.level)
            if mode in {"local", "lateral"}:
                options = [scope.level]
                default_level = scope.level
            elif mode == "descendente":
                options = list(reversed(EDITORIAL_LEVELS[: start_index + 1]))
                default_level = options[1] if len(options) > 1 else options[0]
            elif mode == "bidireccional":
                options = list(EDITORIAL_LEVELS)
                default_level = scope.level
            else:
                options = list(EDITORIAL_LEVELS[start_index:])
                default_level = "materia" if scope.level == "actividad" else scope.level
                if default_level not in options:
                    default_level = options[0]
        self.feedback_build_combo.configure(values=options)
        if mode in {"local", "lateral"} and scope is not None:
            self.feedback_build_level.set(scope.level)
            self.feedback_build_combo.configure(state="disabled")
        else:
            self.feedback_build_combo.configure(state="readonly")
            if self.feedback_build_level.get() not in options:
                self.feedback_build_level.set(default_level)

    def _feedback_schema_preview(self, scope: EditorialScope | None = None) -> str:
        lines = ["# Estructura de memoria editorial", ""]
        if scope is not None:
            lines.extend(
                [
                    f"- Alcance actual: {scope.level}",
                    f"- Scope: {scope.key}",
                    "",
                ]
            )
        lines.append("## Secciones persistentes")
        lines.append("")
        for section in MEMORY_SECTIONS:
            lines.append(f"- {section}: lista de reglas o hallazgos compactados sin perdida")
        lines.extend(
            [
                "",
                "## Principios",
                "",
                "- No regresion: solo union y deduplicacion, nunca borrado destructivo.",
                "- Propagacion: local, lateral, ascendente, descendente o bidireccional segun la estrategia elegida.",
                "- Reutilizacion: el Agente consume esta memoria para plantillas y actividades aguas abajo.",
            ]
        )
        return "\n".join(lines)

    def _investigation_schema_preview(self, scope: EditorialScope | None = None) -> str:
        lines = ["# Base de conocimiento prevista", ""]
        if scope is not None:
            lines.extend(
                [
                    f"- Alcance actual: {scope.level}",
                    f"- Scope: {scope.key}",
                    "",
                ]
            )
        lines.append("## Secciones persistentes")
        lines.append("")
        for section in KNOWLEDGE_SECTIONS:
            lines.append(f"- {section}: inventario, hallazgos y acciones deduplicadas")
        lines.extend(
            [
                "- bib_entries: entradas BibTeX consolidadas o sugeridas.",
                "",
                "## Artefactos canónicos",
                "",
                "- investigacion-aulatex/base-conocimiento.json",
                "- investigacion-aulatex/base-conocimiento.md",
                "- investigacion-aulatex/fuentes-web.md",
                "- archivo .bib del scope o sugerido si aún no existe",
                "- referencias-*/ o assets-*/ según el nivel seleccionado",
            ]
        )
        return "\n".join(lines)

    def _ordered_feedback_engines(self) -> list[str]:
        return sorted(self.llm.engines(), key=lambda engine: (ENGINE_PRIORITY.get(engine, 999), engine))

    def _parse_feedback_engines(self) -> list[str]:
        selected = [item.strip() for item in self.feedback_engines.get().split(",") if item.strip()]
        valid = [engine for engine in selected if engine in self.llm.engines()]
        return valid or self._ordered_feedback_engines()

    def _selected_feedback_value(self, variable: tk.StringVar) -> str:
        value = variable.get().strip()
        if not value or value == UNSELECTED_OPTION:
            return ""
        return value

    def _parse_lines_from_widget(self, widget: tk.Text) -> list[str]:
        return [line.strip() for line in widget.get("1.0", "end").splitlines() if line.strip()]

    def _with_unselected(self, values: list[str]) -> tuple[str, ...]:
        return tuple([UNSELECTED_OPTION, *values])

    def _run_feedback_memory(self) -> None:
        scope = self._resolve_feedback_scope()
        if scope is None:
            messagebox.showwarning("AulaTeX", "Selecciona un scope editorial valido.")
            return

        engines = self._parse_feedback_engines()
        request = EditorialMemoryRequest(
            source_scope_key=scope.key,
            build_level=self._effective_feedback_build_level(scope),
            propagation_mode=self.feedback_propagation.get(),
            iterations=max(1, int(self.feedback_iterations.get())),
            engines=engines,
            max_tokens=max(128, int(self.feedback_max_tokens.get())),
        )

        self.feedback_cancel_event = threading.Event()
        self.feedback_progress.set(0.0)
        if request.propagation_mode == "local":
            self.feedback_progress_status.set("Construyendo memoria editorial local desde fuentes del nodo origen...")
        elif request.propagation_mode == "lateral":
            self.feedback_progress_status.set("Propagando aprendizaje lateral entre nodos hermanos...")
        elif request.propagation_mode == "descendente":
            self.feedback_progress_status.set("Construyendo o reforzando memoria editorial descendente desde el nodo padre...")
        elif request.propagation_mode == "bidireccional":
            self.feedback_progress_status.set("Sincronizando memoria editorial en modo bidireccional progresivo...")
        else:
            self.feedback_progress_status.set("Construyendo memoria editorial...")
        self._log(self.feedback_output, f"[MEMORIA] Inicio en {scope.key} con motores: {', '.join(engines)}")
        self._set_busy("feedback", True)

        def on_progress(event: EditorialMemoryEvent) -> None:
            self.events.put(("feedback-progress", event))

        def work() -> None:
            try:
                result = self.editorial_builder.build(request, progress=on_progress, cancel_event=self.feedback_cancel_event)
                self.events.put(("feedback-result", result))
            except Exception as exc:
                self.events.put(("feedback-error", f"[MEMORIA] ERROR {type(exc).__name__}: {exc}"))

        self._thread(work)

    def _refresh_investigation_catalog(self) -> None:
        institutions = sorted(scope.label for scope in self.editorial_scopes.values() if scope.level == "institucion")
        self.investigation_institution_combo.configure(values=self._with_unselected(institutions))
        if self.investigation_institution.get() not in self.investigation_institution_combo.cget("values"):
            self.investigation_institution.set(UNSELECTED_OPTION)
        self._sync_investigation_source_filters()

    def _sync_investigation_source_filters(self) -> None:
        institution = self._selected_feedback_value(self.investigation_institution)
        selected_career = self._selected_feedback_value(self.investigation_career)
        selected_subject = self._selected_feedback_value(self.investigation_subject)
        selected_activity = self._selected_feedback_value(self.investigation_activity)

        careers = sorted(
            scope.label
            for scope in self.editorial_scopes.values()
            if scope.level == "carrera" and scope.institution == institution
        )
        self.investigation_career_combo.configure(values=self._with_unselected(careers))
        if selected_career not in careers:
            self.investigation_career.set(UNSELECTED_OPTION)
            selected_career = ""

        subjects = sorted(
            scope.label
            for scope in self.editorial_scopes.values()
            if scope.level == "materia"
            and scope.institution == institution
            and scope.career == selected_career
        )
        self.investigation_subject_combo.configure(values=self._with_unselected(subjects))
        if selected_subject not in subjects:
            self.investigation_subject.set(UNSELECTED_OPTION)
            selected_subject = ""

        activities = sorted(
            scope.label
            for scope in self.editorial_scopes.values()
            if scope.level == "actividad"
            and scope.institution == institution
            and scope.career == selected_career
            and scope.subject == selected_subject
        )
        self.investigation_activity_combo.configure(values=self._with_unselected(activities))
        if selected_activity not in activities:
            self.investigation_activity.set(UNSELECTED_OPTION)

    def _on_investigation_source_changed(self, _event=None) -> None:
        self._sync_investigation_source_filters()
        self._refresh_investigation()

    def _resolve_investigation_scope(self) -> EditorialScope | None:
        institution = self._selected_feedback_value(self.investigation_institution)
        career = self._selected_feedback_value(self.investigation_career)
        subject = self._selected_feedback_value(self.investigation_subject)
        activity = self._selected_feedback_value(self.investigation_activity)

        if activity and subject:
            key = self.workspace._scope_key("actividad", institution=institution, career=career, subject=subject, activity=activity)
        elif subject:
            key = self.workspace._scope_key("materia", institution=institution, career=career, subject=subject)
        elif career:
            key = self.workspace._scope_key("carrera", institution=institution, career=career)
        elif institution:
            key = self.workspace._scope_key("institucion", institution=institution)
        else:
            key = "interinstitucional"
        return self.editorial_scopes.get(key)

    def _reset_investigation_queries(self) -> None:
        scope = self._resolve_investigation_scope()
        if scope is None:
            return
        defaults = self.investigation_builder.default_search_terms(scope)
        self._set_text(self.investigation_queries_text, "\n".join(defaults))
        self._refresh_investigation()

    def _refresh_investigation(self) -> None:
        self._refresh_investigation_catalog()
        scope = self._resolve_investigation_scope()
        self.investigation_preview_text.delete("1.0", "end")
        if self.investigation_metrics_text is not None:
            self.investigation_metrics_text.delete("1.0", "end")
        self.investigation_knowledge_text.delete("1.0", "end")
        if scope is None:
            self.investigation_scope_status.set("Scope de investigación: no encontrado")
            self.investigation_preview_text.insert("end", "Selecciona un scope válido para consolidar la base de conocimiento.\n")
            if self.investigation_metrics_text is not None:
                self.investigation_metrics_text.insert("end", "# Metricas de investigación\n\n- Sin scope seleccionado.\n")
            self.investigation_knowledge_text.insert("end", self._investigation_schema_preview())
            return

        self.investigation_scope_status.set(f"Scope de investigación: {scope.level} | {scope.key} | ruta {scope.relative_path or '.'}")
        queries = self._parse_lines_from_widget(self.investigation_queries_text)
        if not queries:
            queries = self.investigation_builder.default_search_terms(scope)
            self._set_text(self.investigation_queries_text, "\n".join(queries))
        seed_urls = self._parse_lines_from_widget(self.investigation_urls_text)
        self.investigation_preview_text.insert("end", self.investigation_builder.preview_markdown(scope, queries, seed_urls))
        if self.investigation_metrics_text is not None:
            self.investigation_metrics_text.insert("end", self.investigation_store.render_metrics_markdown(scope.key))
        payload = self.investigation_store.get_knowledge(scope.key)
        if any(payload.get(section) for section in KNOWLEDGE_SECTIONS) or payload.get("bib_entries"):
            self.investigation_knowledge_text.insert("end", self.investigation_store.render_knowledge_markdown(scope, payload))
        else:
            self.investigation_knowledge_text.insert("end", self._investigation_schema_preview(scope))

    def _parse_investigation_engines(self) -> list[str]:
        selected = [item.strip() for item in self.investigation_engines.get().split(",") if item.strip()]
        valid = [engine for engine in selected if engine in self.llm.engines()]
        return valid or self._ordered_feedback_engines()

    def _run_investigation(self) -> None:
        scope = self._resolve_investigation_scope()
        if scope is None:
            messagebox.showwarning("AulaTeX", "Selecciona un scope editorial válido para investigar.")
            return

        queries = self._parse_lines_from_widget(self.investigation_queries_text)
        if not queries:
            queries = self.investigation_builder.default_search_terms(scope)
            self._set_text(self.investigation_queries_text, "\n".join(queries))
        seed_urls = self._parse_lines_from_widget(self.investigation_urls_text)
        request = InvestigationRequest(
            scope_key=scope.key,
            iterations=max(1, int(self.investigation_iterations.get())),
            engines=self._parse_investigation_engines(),
            max_tokens=max(128, int(self.investigation_max_tokens.get())),
            search_terms=tuple(queries),
            seed_urls=tuple(seed_urls),
        )

        self.investigation_cancel_event = threading.Event()
        self.investigation_progress.set(0.0)
        self.investigation_progress_status.set("Consolidando base de conocimiento...")
        self._log(self.investigation_output, f"[INVESTIGACION] Inicio en {scope.key} con motores: {', '.join(self._parse_investigation_engines())}")
        self._set_busy("investigation", True)

        def on_progress(event: InvestigationEvent) -> None:
            self.events.put(("investigation-progress", event))

        def work() -> None:
            try:
                result = self.investigation_builder.build(request, progress=on_progress, cancel_event=self.investigation_cancel_event)
                self.events.put(("investigation-result", result))
            except Exception as exc:
                self.events.put(("investigation-error", f"[INVESTIGACION] ERROR {type(exc).__name__}: {exc}"))

        self._thread(work)

    def _cancel_investigation(self) -> None:
        if self.investigation_cancel_button.cget("state") == "disabled":
            return
        self.investigation_cancel_event.set()
        self.investigation_progress_status.set("Cancelación solicitada. Se cerrará al terminar la llamada en curso.")
        self._log(self.investigation_output, "[INVESTIGACION] Cancelación solicitada por el usuario.")

    def _handle_investigation_progress(self, event: InvestigationEvent) -> None:
        percent = 0.0
        if event.total > 0:
            percent = (float(event.current) / float(event.total)) * 100.0
        self.investigation_progress.set(percent)
        self.investigation_progress_status.set(event.message)
        prefix = f"[{event.kind.upper()}]"
        if event.engine:
            prefix += f" {event.engine}"
        if event.cycle:
            prefix += f" ciclo={event.cycle}"
        if event.scope_key:
            prefix += f" scope={event.scope_key}"
        self._log(self.investigation_output, f"{prefix} {event.message}")
        if event.kind in {"result", "done"}:
            self._refresh_investigation()

    def _cancel_feedback_memory(self) -> None:
        if self.feedback_cancel_button.cget("state") == "disabled":
            return
        self.feedback_cancel_event.set()
        self.feedback_progress_status.set("Cancelación solicitada. Se cerrará al terminar la llamada en curso.")
        self._log(self.feedback_output, "[MEMORIA] Cancelación solicitada por el usuario.")

    def _resume_feedback_memory(self) -> None:
        checkpoint = self.feedback_resume_checkpoint.get().strip()
        if not checkpoint:
            messagebox.showinfo("AulaTeX", "No hay checkpoint disponible para reanudar.")
            return
        self._set_busy("feedback", True)
        self.feedback_progress_status.set("Reanudando memoria editorial desde checkpoint...")
        self._log(self.feedback_output, f"[MEMORIA] Reanudando desde checkpoint: {checkpoint}")

        def work() -> None:
            try:
                proc = subprocess.run(
                    [
                        "python",
                        "-m",
                        "scripts.aulatex.cli",
                        "editorial-memory",
                        "--target",
                        str(self.workspace.repo_root),
                        "--resume-checkpoint",
                        checkpoint,
                    ],
                    cwd=str(self.workspace.repo_root),
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                )
                payload = proc.stdout.strip() or proc.stderr.strip()
                self.events.put(("feedback-resume", payload))
            except Exception as exc:
                self.events.put(("feedback-error", f"[MEMORIA] ERROR REANUDANDO {type(exc).__name__}: {exc}"))

        self._thread(work)

    def _lock_feedback_scope(self) -> None:
        scope = self._resolve_feedback_scope()
        if scope is None:
            messagebox.showwarning("AulaTeX", "Selecciona un scope editorial antes de fijar reglas.")
            return
        payload = self.editorial_store.lock_scope_sections(scope.key)
        locked = payload.get("locked_sections", [])
        self._log(self.feedback_output, f"[MEMORIA] Scope fijado: {scope.key} | secciones={', '.join(locked) or 'ninguna'}")
        self._refresh_feedback_plan_and_memory()

    def _unlock_feedback_scope(self) -> None:
        scope = self._resolve_feedback_scope()
        if scope is None:
            messagebox.showwarning("AulaTeX", "Selecciona un scope editorial antes de liberar fijación.")
            return
        self.editorial_store.unlock_scope_sections(scope.key)
        self._log(self.feedback_output, f"[MEMORIA] Fijación liberada para {scope.key}")
        self._refresh_feedback_plan_and_memory()

    def _drain_events(self) -> None:
        for _ in range(100):
            try:
                category, event = self.events.get_nowait()
            except queue.Empty:
                break
            if category == "result-path":
                self._record_result(*event)
            elif category == "llm-check-finished":
                self._set_busy("llm-check", False)
            elif category == "agent":
                self._set_busy("agent", False)
                self._log(self.agent_output, event)
            elif category == "agent-error":
                self._set_busy("agent", False)
                self._log(self.agent_output, str(event))
            elif category == "llm":
                self._log(self.llm_output, event)
            elif category == "llm-system":
                self.llm_status.set(event)
            elif category == "llm-refresh":
                self._set_busy("llm-chat", False)
                payload = event if isinstance(event, dict) else {}
                self._refresh_llm_sessions()
                self._refresh_llm_view(payload.get("session_key"), status=payload.get("status"))
            elif category == "llm-error":
                self._set_busy("llm-chat", False)
                self.llm_status.set("Error en el chat LLM")
                payload = event if isinstance(event, dict) else {"error": str(event)}
                if payload.get("prompt"):
                    self._set_text(self.prompt_text, payload["prompt"])
                self._refresh_llm_sessions()
                self._refresh_llm_view(payload.get("session_key") or self._selected_llm_session(), status=payload["error"])
            elif category == "tree-refresh":
                self._tree_refresh_pending = False
                self._apply_tree_refresh(event if isinstance(event, dict) else {})
                if self._tree_refresh_queued:
                    self._tree_refresh_queued = False
                    self.after(10, self._refresh_tree)
            elif category == "tree-refresh-error":
                self._tree_refresh_pending = False
                self._set_text(self.template_details, str(event))
                if self._tree_refresh_queued:
                    self._tree_refresh_queued = False
                    self.after(10, self._refresh_tree)
            elif category == "compile":
                self._set_busy("compile", False)
                self._log(self.compile_output, event)
            elif category == "compile-error":
                self._set_busy("compile", False)
                self._log(self.compile_output, str(event))
            elif category == "extractor":
                self._set_busy("extractor", False)
                self._log(self.extractor_output, event)
            elif category == "extractor-error":
                self._set_busy("extractor", False)
                self._log(self.extractor_output, str(event))
            elif category == "feedback-progress":
                self._handle_feedback_progress(event)
            elif category == "feedback-result":
                self._set_busy("feedback", False)
                self._record_result("feedback", event.manifest_path)
                self.feedback_progress.set(100.0)
                if event.cancelled:
                    self.feedback_progress_status.set("Memoria editorial cancelada.")
                    self._log(self.feedback_output, f"[MEMORIA] CANCELADA\nManifest: {event.manifest_path}")
                else:
                    self.feedback_progress_status.set(f"Memoria editorial cerrada: {'OK' if event.ok else 'CON OBSERVACIONES'}")
                    self._log(self.feedback_output, f"[MEMORIA] {'OK' if event.ok else 'CON OBSERVACIONES'}\nManifest: {event.manifest_path}")
                    if not event.ok:
                        checkpoint_dir = self.workspace.temp_root / "editorial-memory" / "checkpoints"
                        checkpoints = sorted(checkpoint_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
                        if checkpoints:
                            self.feedback_resume_checkpoint.set(str(checkpoints[0]))
                            self.feedback_resume_button.configure(state="normal")
                            self._log(self.feedback_output, f"[MEMORIA] Checkpoint temporal detectado para reanudar: {checkpoints[0]}")
                self._refresh_feedback()
            elif category == "feedback-error":
                self._set_busy("feedback", False)
                self.feedback_progress_status.set("Fallo en la construccion de memoria editorial.")
                self._log(self.feedback_output, str(event))
            elif category == "feedback-resume":
                self._set_busy("feedback", False)
                self.feedback_progress_status.set("Reanudación completada.")
                self._log(self.feedback_output, f"[MEMORIA] REANUDACIÓN\n{event}")
                self._refresh_feedback()
            elif category == "investigation-progress":
                self._handle_investigation_progress(event)
            elif category == "investigation-result":
                self._set_busy("investigation", False)
                self._record_result("investigation", event.knowledge_path)
                self.investigation_progress.set(100.0)
                if event.cancelled:
                    self.investigation_progress_status.set("Investigación cancelada.")
                    self._log(self.investigation_output, f"[INVESTIGACION] CANCELADA\nManifest: {event.manifest_path}")
                else:
                    self.investigation_progress_status.set(f"Investigación cerrada: {'OK' if event.ok else 'CON OBSERVACIONES'}")
                    self._log(
                        self.investigation_output,
                        f"[INVESTIGACION] {'OK' if event.ok else 'CON OBSERVACIONES'}\nManifest: {event.manifest_path}\nArtefactos: {event.knowledge_path}, {event.bibliography_path}, {event.web_sources_path}",
                    )
                self._refresh_investigation()
            elif category == "investigation-error":
                self._set_busy("investigation", False)
                self.investigation_progress_status.set("Fallo en la consolidación de investigación.")
                self._log(self.investigation_output, str(event))
            elif category == "generation-progress":
                self._handle_generation_progress(event)
            elif category == "generation-result":
                self._set_busy("generation", False)
                self._record_result("generation", event.manifest_path.parent)
                self.generation_progress.set(100.0)
                if event.cancelled:
                    self.generation_progress_status.set("Generación cancelada.")
                    self._log(self.generation_output, f"[GENERACION] CANCELADA\nManifest: {event.manifest_path}")
                else:
                    self.generation_progress_status.set(f"Generación cerrada: {'OK' if event.ok else 'CON OBSERVACIONES'}")
                    self._log(
                        self.generation_output,
                        f"[GENERACION] {'OK' if event.ok else 'CON OBSERVACIONES'}\nManifest: {event.manifest_path}\nArtefactos: {event.memory_path}, {event.plan_path}, {event.maqueta_path}",
                    )
                self._refresh_generation_catalog()
                self._refresh_feedback_catalog()
                self._refresh_tree()
            elif category == "generation-error":
                self._set_busy("generation", False)
                self.generation_progress_status.set("Fallo en la generación editorial.")
                self._log(self.generation_output, str(event))
        self.after(250, self._drain_events)

    def _handle_feedback_progress(self, event: EditorialMemoryEvent) -> None:
        percent = 0.0
        if event.total > 0:
            percent = (float(event.current) / float(event.total)) * 100.0
        self.feedback_progress.set(percent)
        self.feedback_progress_status.set(event.message)
        prefix = f"[{event.kind.upper()}]"
        if event.engine:
            prefix += f" {event.engine}"
        if event.cycle:
            prefix += f" ciclo={event.cycle}"
        if event.scope_key:
            prefix += f" scope={event.scope_key}"
        self._log(self.feedback_output, f"{prefix} {event.message}")
        if event.kind in {"result", "done"}:
            self._refresh_feedback_plan_and_memory()


def main(*, diagnostics_enabled: bool | None = None) -> None:
    app = AulaTeXApp(diagnostics_enabled=diagnostics_enabled)
    app.mainloop()
