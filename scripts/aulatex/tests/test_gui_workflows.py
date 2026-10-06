from __future__ import annotations

import ast
import importlib.util
import queue
import re
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
from types import MethodType, SimpleNamespace
from unittest.mock import Mock

import pytest


GUI_PATH = Path(__file__).resolve().parents[1] / "gui.py"
widget_spec = importlib.util.spec_from_file_location("isolated_gui_widgets", GUI_PATH.with_name("gui_widgets.py"))
widgets = importlib.util.module_from_spec(widget_spec)
widget_spec.loader.exec_module(widgets)


def load_methods(*names, **dependencies):
    module = ast.parse(GUI_PATH.read_text(encoding="utf-8"))
    app = next(node for node in module.body if isinstance(node, ast.ClassDef) and node.name == "AulaTeXApp")
    methods = [node for node in app.body if isinstance(node, ast.FunctionDef) and node.name in names]
    namespace = dict(dependencies)
    future = ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)
    tree = ast.fix_missing_locations(ast.Module(body=[future, *methods], type_ignores=[]))
    exec(compile(tree, str(GUI_PATH), "exec"), namespace)
    return namespace


@pytest.mark.parametrize("prompt", [
    "Explica como compilar un documento sin ejecutarlo",
    "No compilar en ITESCA",
    "Analiza carpeta significa explorar?",
    "Como hago una lista de .tex?",
    "/compilar",
])
def test_chat_never_executes_tools_from_prose(prompt):
    methods = load_methods("_handle_local_tool_prompt")
    workspace = Mock()
    assert methods["_handle_local_tool_prompt"](SimpleNamespace(workspace=workspace), prompt) is None
    assert workspace.mock_calls == []


def test_chat_read_only_tools_require_exact_commands():
    methods = load_methods("_handle_local_tool_prompt")
    workspace = Mock()
    workspace.find_tex_files.return_value = ["ficticio.tex"]
    workspace.relative.side_effect = str
    workspace.context_summary.return_value = "Contexto ficticio"
    app = SimpleNamespace(workspace=workspace)
    assert "ficticio.tex" in methods["_handle_local_tool_prompt"](app, " /listar-tex ")
    assert methods["_handle_local_tool_prompt"](app, "/explorar") == "Contexto ficticio"
    workspace.compile_tex.assert_not_called()


@pytest.fixture
def app(tk_root, monkeypatch):
    source = ast.parse(GUI_PATH.read_text(encoding="utf-8"))
    definition = next(node for node in source.body if isinstance(node, ast.ClassDef) and node.name == "AulaTeXApp")
    for method in definition.body:
        if isinstance(method, ast.FunctionDef) and method.name != "__init__":
            monkeypatch.setattr(tk_root, method.name, Mock(), raising=False)
    tk_root.diagnostics_enabled = False
    tk_root._ordered_feedback_engines.return_value = ["Motor ficticio"]
    yield tk_root
    for child in tk_root.winfo_children():
        child.destroy()
    tk_root.withdraw()


def bind_methods(app, *names, **dependencies):
    methods = load_methods(*names, tk=tk, ttk=ttk, Path=Path,
                           ScrolledText=ScrolledText, EnginePicker=widgets.EnginePicker, ScrollableForm=widgets.ScrollableForm,
                           UNSELECTED_OPTION="Sin seleccionar", DEFAULT_MAX_TOKENS=4096,
                           PROPAGATION_VALUES=("ascendente",), **dependencies)
    for name in names:
        setattr(app, name, MethodType(methods[name], app))
    return methods


def test_agent_mode_hides_irrelevant_options_and_has_no_default_target(app):
    app.agent_tab = ttk.Frame(app)
    app.agent_tab.pack(fill="both", expand=True)
    bind_methods(app, "_build_agent_tab", "_sync_agent_mode")
    app._build_agent_tab()
    assert app.agent_target.get() == ""
    assert app.agent_workflow_frame.winfo_manager() == ""
    assert app.agent_monitor_frame.winfo_manager() == "grid"
    assert app.agent_run_button.cget("text") == "Revisar archivos"
    app.agent_monitor_mode.set(False)
    app._sync_agent_mode()
    assert app.agent_workflow_frame.winfo_manager() == "grid"
    assert app.agent_monitor_frame.winfo_manager() == ""
    assert app.agent_run_button.cget("text") == "Ejecutar agente"


def test_feedback_controls_do_not_share_grid_cells(app):
    app.feedback_tab = ttk.Frame(app)
    app.feedback_tab.pack(fill="both", expand=True)
    bind_methods(app, "_build_feedback_tab")
    app._build_feedback_tab()
    for parent in (app.feedback_tab, app.feedback_run_button.master):
        cells = [(child.grid_info()["row"], child.grid_info()["column"])
                 for child in parent.winfo_children() if child.winfo_manager() == "grid"]
        assert len(cells) == len(set(cells))
    assert isinstance(app.feedback_output.master.master.master, ttk.Notebook)


@pytest.mark.parametrize("target, activity, cycles", [("", 1, 1), (".", "x", 1), (".", 1, 0)])
def test_invalid_agent_inputs_do_not_start_work(app, tmp_path, target, activity, cycles):
    messages = Mock()
    bind_methods(app, "_run_agent", messagebox=messages)
    app.workspace = SimpleNamespace(repo_root=tmp_path)
    app.agent_target = tk.StringVar(app, value=target)
    app.agent_activity = tk.IntVar(app, value=activity)
    app.agent_max_cycles = tk.IntVar(app, value=cycles)
    app.agent_monitor_mode = tk.BooleanVar(app, value=True)
    app._run_agent()
    messages.showwarning.assert_called_once()
    app._run_activity_monitor.assert_not_called()
    app._thread.assert_not_called()


def test_navigation_defers_settings_and_tools(app):
    bind_methods(app, "_build_ui")
    app._build_ui()
    assert [app.main_notebook.tab(tab, "text") for tab in app.main_notebook.tabs()] == [
        "Proyecto", "Investigación", "Producción", "Memoria", "Asistente"]
    assert len(app.production_tab.tabs()) == 3
    app._build_credentials_tab.assert_not_called()
    app._build_platforms_tab.assert_not_called()
    app._build_extractor_tab.assert_not_called()
    app._build_arch_tab.assert_not_called()


def test_project_context_populates_all_workflows(app, tmp_path):
    bind_methods(app, "_use_selected_scope", re=re)
    app._active_jobs = set()
    app.workspace = SimpleNamespace(repo_root=tmp_path)
    app.template_tree = Mock()
    app.template_tree.selection.return_value = ("selected",)
    app.template_nodes = {"selected": SimpleNamespace(key="activity-7", level="actividad", label="Actividad 7",
        institution="Instituto", career="Carrera", subject="Materia", activity="Actividad 7", relative_path="materia")}
    for prefix in ("feedback", "investigation", "generation"):
        for field in ("institution", "career", "subject", "activity"):
            if prefix != "generation" or field != "activity":
                setattr(app, f"{prefix}_{field}", tk.StringVar(app))
    for name in ("context_label", "generation_node_level", "agent_target", "agent_level", "compile_target", "task_status"):
        setattr(app, name, tk.StringVar(app))
    app.agent_activity = tk.IntVar(app)
    app.generation_activity_number = tk.IntVar(app)
    app.investigation_queries_text = tk.Text(app)
    app.investigation_urls_text = tk.Text(app)
    app._use_selected_scope()
    assert app.context_key == "activity-7"
    assert app.feedback_activity.get() == app.investigation_activity.get() == "Actividad 7"
    assert app.generation_subject.get() == "Materia"
    assert app.agent_activity.get() == app.generation_activity_number.get() == 7
    assert app.agent_target.get() == "materia"
    assert app.generation_node_level.get() == "actividad"
    assert app._set_text.call_args_list == [
        ((app.investigation_queries_text, ""),), ((app.investigation_urls_text, ""),)]


def test_busy_work_prevents_project_switch_and_close(app):
    messages = Mock()
    bind_methods(app, "_use_selected_scope", "_request_close", messagebox=messages)
    app._active_jobs = {"generation"}
    app.template_tree = Mock()
    app._use_selected_scope()
    app.template_tree.selection.assert_not_called()
    app._request_close()
    assert app.winfo_exists()
    assert messages.showinfo.call_count == 2


@pytest.mark.parametrize("size", ["980x640", "1180x760"])
@pytest.mark.parametrize("diagnostics", [False, True])
def test_editorial_outputs_remain_usable_at_supported_sizes(app, size, diagnostics):
    app.diagnostics_enabled = diagnostics
    bind_methods(app, "_build_builder_tab", "_build_investigation_tab", "_build_feedback_tab")
    notebook = ttk.Notebook(app)
    notebook.pack(fill="both", expand=True)
    app.geometry(size)
    app.deiconify()
    for attribute, builder, output_name in (
        ("builder_tab", "_build_builder_tab", "generation_output"),
        ("investigation_tab", "_build_investigation_tab", "investigation_output"),
        ("feedback_tab", "_build_feedback_tab", "feedback_output"),
    ):
        frame = ttk.Frame(notebook, padding=12)
        setattr(app, attribute, frame)
        notebook.add(frame, text=attribute)
        getattr(app, builder)()
        notebook.select(frame)
        output = getattr(app, output_name)
        results = output.master.master.master
        results.select(output.master.master)
        app.update()
        assert output.winfo_height() >= 120
        assert output.winfo_rooty() + output.winfo_height() <= frame.winfo_rooty() + frame.winfo_height()
        assert output.winfo_rootx() + output.winfo_width() <= frame.winfo_rootx() + frame.winfo_width()


def test_engine_picker_keeps_a_valid_selection_and_follows_reset(app):
    variable = tk.StringVar(app, value="First, Second")
    picker = widgets.EnginePicker(app, textvariable=variable, choices=["First", "Second"])
    picker.variables["First"].set(False)
    picker._choose()
    assert variable.get() == "Second"
    picker.variables["Second"].set(False)
    picker._choose()
    assert variable.get() == "Second"
    assert picker.variables["Second"].get()
    variable.set("First")
    assert picker.variables["First"].get()
    assert not picker.variables["Second"].get()


def test_failed_chat_restores_prompt_and_releases_controls(app, monkeypatch):
    bind_methods(app, "_drain_events", queue=queue)
    app.events = queue.Queue()
    app.llm_status = tk.StringVar(app)
    app.prompt_text = tk.Text(app)
    app.events.put(("llm-error", {"error": "Fallo ficticio", "prompt": "Mi borrador", "session_key": "editorial"}))
    monkeypatch.setattr(app, "after", Mock())
    app._drain_events()
    app._set_busy.assert_called_once_with("llm-chat", False)
    app._set_text.assert_called_once_with(app.prompt_text, "Mi borrador")
    app._refresh_llm_view.assert_called_once_with("editorial", status="Fallo ficticio")


@pytest.mark.parametrize("method, store_method", [
    ("_compact_selected_llm_session", "compact_session"),
    ("_export_selected_llm_session", "export_session_markdown"),
])
def test_chat_maintenance_reports_failures(app, method, store_method):
    bind_methods(app, method)
    app._selected_llm_session.return_value = "editorial"
    app.chat_store = Mock()
    getattr(app.chat_store, store_method).side_effect = RuntimeError("Fallo ficticio")
    app.events = queue.Queue()
    app._thread.side_effect = lambda work: work()
    getattr(app, method)()
    app._set_busy.assert_called_once_with("llm-chat", True)
    assert app.events.get_nowait() == ("llm-error", "Fallo ficticio")


def test_results_are_available_only_for_existing_files(app, tmp_path):
    bind_methods(app, "_record_result")
    app.workspace = SimpleNamespace(repo_root=tmp_path)
    app._result_paths = {}
    app._result_indices = {"compile": 0}
    app.results_menu = Mock()
    app._record_result("compile", "missing.pdf")
    assert not app._result_paths
    path = tmp_path / "ficticio.pdf"
    path.touch()
    app._record_result("compile", path)
    assert app._result_paths["compile"] == path
    app.results_menu.entryconfigure.assert_called_once_with(0, state="normal")


@pytest.mark.parametrize("size", ["980x640", "1180x760"])
def test_complete_navigation_layout_without_service_startup(app, size, tmp_path):
    bind_methods(app, "_build_ui", "_build_panel_tab", "_build_llm_tab", "_build_agent_tab", "_sync_agent_mode",
                 "_build_builder_tab", "_build_feedback_tab", "_build_investigation_tab", "_build_compile_tab",
                 "_register_busy_widgets", MULTIMOTOR_SEVERITY_LABELS=("normal",))
    app.workspace = SimpleNamespace(repo_root=tmp_path)
    app.llm_multi_severity = tk.StringVar(app, value="normal")
    app._busy_groups = {}
    app._build_ui()
    app.geometry(size)
    app.deiconify()
    for tab in app.main_notebook.tabs():
        app.main_notebook.select(tab)
        frame = app.nametowidget(tab)
        pages = app.production_tab.tabs() if frame is app.production_tab else (None,)
        for page in pages:
            if page:
                app.production_tab.select(page)
            app.update()
            assert frame.winfo_reqwidth() <= frame.winfo_width()
    assert "agent" in app._busy_groups
    assert "llm-chat" in app._busy_groups
    for job in app.tk.call("after", "info"):
        app.after_cancel(job)


def test_settings_close_clears_provider_fields_and_locks_vault(app):
    bind_methods(app, "_close_auxiliary")
    app._active_jobs = set()
    app._credential_vars = {"ficticio": tk.StringVar(app, value="clave-ficticia")}
    app.platforms_tab = SimpleNamespace(_lock=Mock())
    window = tk.Toplevel(app)
    app._aux_windows = {"settings": window}
    app._close_auxiliary("settings")
    assert app._credential_vars["ficticio"].get() == ""
    app.platforms_tab._lock.assert_called_once()
    assert not window.winfo_exists()


def test_generation_form_fits_high_dpi_without_horizontal_scroll(app):
    scaling = app.tk.call("tk", "scaling")
    try:
        app.tk.call("tk", "scaling", 2.3)
        app.geometry("980x640")
        app.deiconify()
        app.builder_tab = ttk.Frame(app, padding=12)
        app.builder_tab.pack(fill="both", expand=True)
        bind_methods(app, "_build_builder_tab")
        app._build_builder_tab()
        app.update()
        form = next(child for child in app.builder_tab.winfo_children() if isinstance(child, widgets.ScrollableForm))
        assert form.body.winfo_width() <= form.canvas.winfo_width() + 2
    finally:
        app.tk.call("tk", "scaling", scaling)


@pytest.mark.parametrize("requested, area, expected", [
    ((1180, 760), (0, 0, 1920, 1040), (1180, 760)),
    ((1920, 1080), (0, 0, 1366, 728), (1334, 648)),
    ((1180, 760), (-1280, 0, 0, 984), (1180, 760)),
    ((1180, 760), (0, 0, 800, 600), (768, 520)),
])
def test_resolution_fits_current_monitor_without_changing_tk_scale(app, requested, area, expected):
    bind_methods(app, "_set_resolution")
    app._monitor_work_area.return_value = area
    app.task_status = tk.StringVar(app)
    scaling = app.tk.call("tk", "scaling")
    app._set_resolution(*requested)
    app.update_idletasks()
    assert (app.winfo_width(), app.winfo_height()) == expected
    assert app.tk.call("tk", "scaling") == scaling
    assert f"{expected[0]} x {expected[1]}" in app.task_status.get()
    app.minsize(1, 1)


def test_fit_monitor_uses_current_work_area(app):
    bind_methods(app, "_fit_monitor")
    app._monitor_work_area.return_value = (1920, 0, 3840, 1040)
    app._fit_monitor()
    app._set_resolution.assert_called_once_with(1920, 1040)