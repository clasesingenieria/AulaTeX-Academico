"""Dedicated local form; platform secrets never enter the notes/LLM pipeline."""
from __future__ import annotations

import os
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from .platform_credentials import PlatformCredentialVault, VaultError, default_vault_path


class PlatformCredentialsFrame(ttk.Frame):
    def __init__(self, parent, *, repo_root: Path, institutions: list[str]) -> None:
        super().__init__(parent, padding=12)
        self.vault = PlatformCredentialVault(default_vault_path(repo_root))
        self.account_id: str | None = None
        self.fields = {key: tk.StringVar(self) for key in (
            "institution", "platform", "url", "username", "password", "pin",
        )}
        self.status = tk.StringVar(self, value="Bóveda bloqueada. Introduce el PIN para consultar o guardar.")
        self.columnconfigure(1, weight=1)
        self.rowconfigure(2, weight=1)
        ttk.Label(self, text="Credenciales institucionales · bóveda local cifrada", font=("Segoe UI", 12, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w")
        ttk.Label(self, text="No se envían a motores LLM ni se guardan en el repositorio. Usa una frase maestra larga y única.",
                  wraplength=850).grid(row=1, column=0, columnspan=3, sticky="w", pady=(6, 10))
        self.accounts = ttk.Treeview(self, columns=("account_id", "institution", "platform", "url"), show="headings", height=6)
        for key, title in (("account_id", "ID de cuenta"), ("institution", "Institución"),
                           ("platform", "Plataforma / cuenta"), ("url", "Sitio")):
            self.accounts.heading(key, text=title)
            self.accounts.column(key, width={"account_id": 240, "institution": 140, "platform": 140, "url": 340}[key])
        self.accounts.grid(row=2, column=0, columnspan=3, sticky="nsew", pady=(0, 10))
        self.accounts.bind("<<TreeviewSelect>>", self._select)
        labels = (("institution", "Institución"), ("platform", "Plataforma / alias de cuenta"),
                  ("url", "Sitio HTTPS"), ("username", "Usuario"), ("password", "Contraseña"),
                  ("pin", "AULATEX_MASTER_PIN"))
        for row, (key, label) in enumerate(labels, start=3):
            ttk.Label(self, text=label).grid(row=row, column=0, sticky="w", pady=3)
            if key == "institution":
                entry = ttk.Combobox(self, textvariable=self.fields[key], values=sorted(set(institutions)))
            else:
                entry = ttk.Entry(self, textvariable=self.fields[key], show="*" if key in ("username", "password", "pin") else "")
            entry.grid(row=row, column=1, columnspan=2, sticky="ew", padx=(12, 0), pady=3)
        ttk.Label(self, text="Al editar, usuario/contraseña vacíos conservan los existentes. El PIN vacío usa la variable de entorno, si existe.",
                  wraplength=850).grid(row=9, column=0, columnspan=3, sticky="w", pady=6)
        buttons = ttk.Frame(self)
        buttons.grid(row=10, column=0, columnspan=3, sticky="w", pady=8)
        for text, command in (("Consultar", self._load), ("Nueva", self._new), ("Ejemplo ITESCA", self._itesca),
                              ("Guardar cifrado", self._save), ("Eliminar", self._delete),
                              ("Cambiar PIN", self._rotate), ("Limpiar / bloquear", self._lock)):
            ttk.Button(buttons, text=text, command=command).pack(side="left", padx=(0, 6))
        ttk.Label(self, textvariable=self.status, wraplength=850).grid(row=11, column=0, columnspan=3, sticky="w", pady=4)
        ttk.Label(self, text=f"Bóveda: {self.vault.path}", wraplength=850).grid(row=12, column=0, columnspan=3, sticky="w")
        # Clear pending secrets and visible metadata after five minutes without input.
        self._idle_job = None
        self._bind_activity(self)
        self._touch()
        self.bind("<Destroy>", self._destroyed, add="+")

    def _bind_activity(self, widget) -> None:
        widget.bind("<KeyPress>", self._touch, add="+")
        widget.bind("<ButtonPress>", self._touch, add="+")
        for child in widget.winfo_children():
            self._bind_activity(child)

    def _touch(self, _event=None) -> None:
        if self._idle_job is not None:
            self.after_cancel(self._idle_job)
        self._idle_job = self.after(300_000, self._lock)

    def _destroyed(self, event) -> None:
        if event.widget is self and self._idle_job is not None:
            self.after_cancel(self._idle_job)

    def _pin(self) -> str:
        return self.fields["pin"].get() or os.environ.get("AULATEX_MASTER_PIN", "")

    def _clear_secrets(self) -> None:
        for key in ("username", "password", "pin"):
            self.fields[key].set("")

    def _refresh(self, pin: str) -> None:
        rows = self.vault.list_accounts(pin)
        self.accounts.delete(*self.accounts.get_children())
        self.account_id = None
        for row in rows:
            self.accounts.insert("", "end", iid=row["id"], values=(row["id"], row["institution"], row["platform"], row["url"]))

    def _run(self, operation) -> None:
        try:
            operation(self._pin())
        except VaultError as exc:
            self.status.set(str(exc))
        except Exception:
            # Tk's default callback traceback may contain sensitive context.
            self.status.set("No se pudo completar la operación local. No se mostrarán detalles sensibles.")
        finally:
            self._clear_secrets()

    def _load(self) -> None:
        def operation(pin):
            self._refresh(pin)
            self._new()
            self.status.set("Lista consultada. No se muestran ni se precargan usuarios o contraseñas.")
        self._run(operation)

    def _select(self, _event=None) -> None:
        selection = self.accounts.selection()
        if not selection:
            return
        self.account_id = selection[0]
        for key, value in zip(("institution", "platform", "url"), self.accounts.item(self.account_id, "values")[1:]):
            self.fields[key].set(value)
        self._clear_secrets()
        self.status.set("Edición: introduce el PIN y solo los secretos que desees sustituir.")

    def _new(self) -> None:
        self.account_id = None
        self.accounts.selection_remove(*self.accounts.selection())
        for var in self.fields.values():
            var.set("")
        self.status.set("Nueva cuenta: completa institución, plataforma, sitio, usuario, contraseña y PIN.")

    def _itesca(self) -> None:
        self._new()
        self.fields["institution"].set("ITESCA")
        self.fields["platform"].set("ITESCA Virtual")
        self.fields["url"].set("https://cursos3.e-itesca.edu.mx/login/index.php")

    def _save(self) -> None:
        def operation(pin):
            self.vault.save(pin, account_id=self.account_id, **{
                key: self.fields[key].get() for key in ("institution", "platform", "url", "username", "password")
            })
            self._refresh(pin)
            self._new()
            self.status.set("Credenciales guardadas cifradas. Campos sensibles limpiados.")
        self._run(operation)

    def _delete(self) -> None:
        if self.account_id is None:
            self.status.set("Selecciona una cuenta para eliminarla.")
            return
        if not messagebox.askyesno("Eliminar cuenta", f"¿Eliminar la cuenta {self.account_id} de la bóveda?", parent=self):
            return
        def operation(pin):
            self.vault.delete(pin, self.account_id)
            self._refresh(pin)
            self._new()
            self.status.set("Cuenta eliminada de la bóveda local.")
        self._run(operation)

    def _rotate(self) -> None:
        def operation(pin):
            new_pin = simpledialog.askstring("PIN de plataformas", "Nuevo PIN (solo esta bóveda):", show="*", parent=self)
            if new_pin is None:
                return
            confirmation = simpledialog.askstring("Confirmar PIN", "Repite el nuevo PIN:", show="*", parent=self)
            if new_pin != confirmation:
                raise VaultError("Los PIN no coinciden; no se modificó la bóveda.")
            self.vault.rotate_pin(pin, new_pin)
            self._lock()
            self.status.set("PIN cambiado solo para plataformas. Actualiza tu entorno por separado si lo usabas.")
        self._run(operation)

    def _lock(self) -> None:
        self._new()
        self.accounts.delete(*self.accounts.get_children())
        self.status.set("Campos y lista limpiados. El PIN del entorno, si existe, sigue disponible para el proceso.")