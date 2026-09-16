"""Exercise the real Tk form, with temporary storage and no app/LLM startup."""
from __future__ import annotations

import ast
import builtins
import importlib.util
import os
from pathlib import Path
import sys
import tkinter as tk
from tkinter import ttk
from types import MethodType, ModuleType, SimpleNamespace

import pytest


PIN = "solo-pruebas-pin-maestro-largo"


@pytest.fixture(scope="module")
def tk_root():
    # One Tcl interpreter per process; repeated Tk()/destroy() is unreliable on Windows.
    root = tk.Tk()
    root.withdraw()
    yield root
    root.destroy()


@pytest.fixture
def form(tmp_path, monkeypatch, tk_root):
    monkeypatch.setattr(os, "environ", {})
    # Do not execute the suite's __init__ or load real configuration at collection.
    package_name = "platform_form_test_package"
    package = ModuleType(package_name)
    package.__path__ = [str(Path(__file__).resolve().parents[1])]
    monkeypatch.setitem(sys.modules, package_name, package)
    modules = {}
    for name in ("platform_credentials", "platform_credentials_gui"):
        spec = importlib.util.spec_from_file_location(
            f"{package_name}.{name}", Path(package.__path__[0]) / f"{name}.py",
        )
        module = importlib.util.module_from_spec(spec)
        monkeypatch.setitem(sys.modules, spec.name, module)
        spec.loader.exec_module(module)
        modules[name] = module
    gui = modules["platform_credentials_gui"]
    monkeypatch.setattr(gui, "default_vault_path", lambda _: tmp_path / "platform-credentials.vault.json")
    root = tk_root
    notebook = ttk.Notebook(root)
    widget = gui.PlatformCredentialsFrame(notebook, repo_root=tmp_path, institutions=["ITESCA", "UCNL"])
    notebook.add(widget, text="Plataformas")
    yield widget, gui
    for child in root.winfo_children():
        child.destroy()


def populate(widget):
    widget._itesca()
    widget.fields["username"].set("cuenta-totalmente-ficticia")
    widget.fields["password"].set("contraseña-ficticia-para-pruebas")
    widget.fields["pin"].set(PIN)


def select_first(widget):
    account_id = widget.accounts.get_children()[0]
    widget.accounts.selection_set(account_id)
    widget.update()
    return account_id


def test_itesca_form_save_edit_delete_and_lock(form, monkeypatch):
    widget, gui = form
    populate(widget)
    assert widget.fields["institution"].get() == "ITESCA"
    assert widget.fields["url"].get() == "https://cursos3.e-itesca.edu.mx/login/index.php"
    widget._save()
    assert "guardadas cifradas" in widget.status.get()
    assert all(widget.fields[key].get() == "" for key in ("username", "password", "pin"))
    account_id = select_first(widget)
    assert widget.account_id == account_id
    assert widget.fields["username"].get() == widget.fields["password"].get() == ""
    widget.fields["platform"].set("ITESCA Virtual · principal")
    widget.fields["pin"].set(PIN)
    widget._save()
    record = widget.vault.get_credentials(PIN, account_id)
    assert record["platform"] == "ITESCA Virtual · principal"
    assert record["password"] == "contraseña-ficticia-para-pruebas"
    assert record["username"] == "cuenta-totalmente-ficticia"
    widget._lock()
    assert not widget.accounts.get_children()
    assert all(var.get() == "" for var in widget.fields.values())
    widget.fields["pin"].set(PIN)
    widget._load()
    select_first(widget)
    widget.fields["pin"].set(PIN)
    monkeypatch.setattr(gui.messagebox, "askyesno", lambda *a, **kw: True)
    widget._delete()
    assert "eliminada" in widget.status.get()
    assert widget.vault.list_accounts(PIN) == []


def test_no_pin_no_write_and_wrong_pin_clears_secrets(form):
    widget, _ = form
    populate(widget)
    widget.fields["pin"].set("")
    widget._save()
    assert "AULATEX_MASTER_PIN" in widget.status.get()
    assert not widget.vault.path.exists()
    populate(widget)
    widget._save()
    before = widget.vault.path.read_bytes()
    populate(widget)
    widget.fields["pin"].set("pin-incorrecto")
    widget._save()
    assert "PIN incorrecto" in widget.status.get()
    assert widget.vault.path.read_bytes() == before
    assert all(widget.fields[key].get() == "" for key in ("username", "password", "pin"))


def test_explicit_pin_overrides_environment_without_changing_it(form, monkeypatch):
    widget, _ = form
    monkeypatch.setenv("AULATEX_MASTER_PIN", "pin-del-entorno-ficticio")
    populate(widget)
    widget._save()
    assert "guardadas cifradas" in widget.status.get()
    widget._load()
    assert "PIN incorrecto" in widget.status.get()
    assert os.environ["AULATEX_MASTER_PIN"] == "pin-del-entorno-ficticio"
    monkeypatch.setenv("AULATEX_MASTER_PIN", PIN)
    widget._load()
    assert "Lista consultada" in widget.status.get()
    widget._lock()
    assert "entorno" in widget.status.get()
    assert os.environ["AULATEX_MASTER_PIN"] == PIN


def test_rotate_confirmation_and_success(form, monkeypatch):
    widget, gui = form
    populate(widget)
    widget._save()
    before = widget.vault.path.read_bytes()
    answers = iter(["nuevo-pin-ficticio", "no-coincide"])
    monkeypatch.setattr(gui.simpledialog, "askstring", lambda *a, **kw: next(answers))
    widget.fields["pin"].set(PIN)
    widget._rotate()
    assert "no coinciden" in widget.status.get()
    assert widget.vault.path.read_bytes() == before
    answers = iter(["nuevo-pin-ficticio", "nuevo-pin-ficticio"])
    widget.fields["pin"].set(PIN)
    widget._rotate()
    assert "PIN cambiado" in widget.status.get()
    assert len(widget.vault.list_accounts("nuevo-pin-ficticio")) == 1
    assert not widget.accounts.get_children()


def test_masking_idle_callback_and_unexpected_errors(form):
    widget, _ = form
    masked = {str(entry.cget("textvariable")): entry.cget("show")
              for entry in widget.winfo_children() if isinstance(entry, ttk.Entry)}
    for key in ("username", "password", "pin"):
        assert masked[str(widget.fields[key])] == "*"
    populate(widget)
    old_job = widget._idle_job
    widget._touch()
    assert widget._idle_job != old_job
    callback = widget.tk.call("after", "info", widget._idle_job)[0]
    widget.tk.eval(callback)
    assert all(var.get() == "" for var in widget.fields.values())
    populate(widget)

    def failing_operation(_pin):
        raise RuntimeError("contraseña-ficticia-no-debe-aparecer")

    widget._run(failing_operation)
    assert "contraseña-ficticia" not in widget.status.get()
    assert "detalles sensibles" in widget.status.get()
    assert widget.fields["pin"].get() == ""


def test_multiple_accounts_have_distinct_visible_ids(form):
    widget, _ = form
    for username in ("usuario-ficticio-uno", "usuario-ficticio-dos"):
        populate(widget)
        widget.fields["username"].set(username)
        widget._save()
    rows = [widget.accounts.item(node, "values") for node in widget.accounts.get_children()]
    assert len(rows) == 2
    assert rows[0][0] != rows[1][0]
    assert rows[0][1:] == rows[1][1:]
    assert "usuario-ficticio" not in str(rows)


@pytest.mark.parametrize("missing_crypto", [False, True])
def test_main_notebook_integration_without_app_side_effects(form, monkeypatch, tmp_path, missing_crypto):
    widget, gui = form
    # Execute the actual notebook construction methods, but not editorial builders,
    # configuration imports, LLM constructors, or background indexing.
    tree = ast.parse((Path(__file__).resolve().parents[1] / "gui.py").read_text(encoding="utf-8"))
    app = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "AulaTeXApp")
    selected = [node for node in app.body if isinstance(node, ast.FunctionDef)
                and node.name in ("_build_ui", "_build_platforms_tab")]
    namespace = {"ttk": ttk, "__package__": gui.__package__}
    exec(compile(ast.Module(body=selected, type_ignores=[]), "isolated-notebook-construction", "exec"), namespace)
    root = widget.winfo_toplevel()
    monkeypatch.setattr(root, "workspace", SimpleNamespace(repo_root=tmp_path), raising=False)
    monkeypatch.setattr(root, "editorial_scopes", {
        "itesca": SimpleNamespace(level="institucion", institution="ITESCA", label="ITESCA"),
    }, raising=False)
    for node in app.body:
        if isinstance(node, ast.FunctionDef) and node.name.startswith("_build_"):
            value = MethodType(namespace[node.name], root) if node.name in namespace else lambda: None
            monkeypatch.setattr(root, node.name, value, raising=False)
    if missing_crypto:
        original_import = builtins.__import__

        def missing_dependency(name, *args, **kwargs):
            if name == "platform_credentials_gui":
                raise ModuleNotFoundError("dependencia ficticia ausente", name="cryptography")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", missing_dependency)
    root._build_ui()
    notebook = root.platforms_tab.master
    assert notebook.tab(root.platforms_tab, "text") == "Plataformas"
    assert notebook.tab(root.credentials_tab, "text") == "Credenciales"
    if missing_crypto:
        assert not isinstance(root.platforms_tab, gui.PlatformCredentialsFrame)
        assert "No se guardarán credenciales sin cifrado" in root.platforms_tab.winfo_children()[0].cget("text")
    else:
        assert isinstance(root.platforms_tab, gui.PlatformCredentialsFrame)
        assert root.platforms_tab.vault.path.parent == tmp_path