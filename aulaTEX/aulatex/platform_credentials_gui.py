"""Dedicated local form; platform secrets never enter the notes/LLM pipeline."""
from __future__ import annotations

import os
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from .platform_credentials import PlatformCredentialVault, VaultError, default_vault_path


PLATFORM_PRESETS = {
    "ITESCA Virtual": ("ITESCA", "https://cursos3.e-itesca.edu.mx/login/index.php"),
    "Nexus UANL": ("UANL", "https://plataformanexus.uanl.mx/#/Login"),
    "Mi UnADM": ("UnADM", "https://aulavirtual.unadmexico.mx/login/index.php"),
    "UAS Virtual FCA": ("UAS", "https://virtual.uas.edu.mx/fca/"),
}


class PlatformCredentialsFrame(ttk.Frame):
    def __init__(self, parent, *, repo_root: Path, institutions: list[str]) -> None:
        super().__init__(parent, padding=12)
        self.vault = PlatformCredentialVault(default_vault_path(repo_root))
        self.account_id: str | None = None
        self.fields = {key: tk.StringVar(self) for key in (
            "institution", "platform", "url", "username", "password", "pin",
        )}
        self.status = tk.StringVar(self, value="Bóveda bloqueada. Introduce el PIN para consultar o guardar.")
        self.use_environment_pin = tk.BooleanVar(self, value=False)
        self.preset = tk.StringVar(self, value="Personalizada")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)
        ttk.Label(self, text="Credenciales institucionales · bóveda local cifrada", font=("Segoe UI", 12, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w")
        ttk.Label(self, text="No se envían a motores LLM ni se guardan en el repositorio. Usa una frase maestra larga y única.",
                  wraplength=850).grid(row=1, column=0, columnspan=3, sticky="w", pady=(6, 10))
        panes = ttk.Panedwindow(self, orient="horizontal")
        panes.grid(row=2, column=0, sticky="nsew")
        list_frame = ttk.Frame(panes)
        self.editor_frame = ttk.Frame(panes, padding=(16, 0, 0, 0))
        panes.add(list_frame, weight=1)
        panes.add(self.editor_frame, weight=1)
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        self.editor_frame.columnconfigure(1, weight=1)
        self.accounts = ttk.Treeview(list_frame, columns=("account_id", "institution", "platform", "url"),
                                     displaycolumns=("institution", "platform", "url", "account_id"),
                                     show="headings", height=8, selectmode="browse")
        for key, title in (("account_id", "Ref."), ("institution", "Institución"),
                   ("platform", "Cuenta"), ("url", "Sitio")):
            self.accounts.heading(key, text=title)
            self.accounts.column(key, width={"account_id": 70, "institution": 100, "platform": 110, "url": 110}[key], minwidth=70)
        self.accounts.grid(row=0, column=0, sticky="nsew")
        vertical = ttk.Scrollbar(list_frame, orient="vertical", command=self.accounts.yview)
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal = ttk.Scrollbar(list_frame, orient="horizontal", command=self.accounts.xview)
        horizontal.grid(row=1, column=0, sticky="ew")
        self.accounts.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        self.empty_state = ttk.Label(self.accounts, text="Bóveda bloqueada", wraplength=240, anchor="center")
        self.empty_state.place(relx=0.5, rely=0.5, anchor="center")
        self.accounts.bind("<<TreeviewSelect>>", self._select)
        list_actions = ttk.Frame(list_frame)
        list_actions.grid(row=2, column=0, columnspan=2, sticky="ew", pady=8)
        for title, command in (("Nueva", self._new), ("Eliminar", self._delete), ("Detalles", self._details)):
            ttk.Button(list_actions, text=title, command=command).pack(side="left", padx=(0, 6))
        ttk.Label(self.editor_frame, text="Plataforma").grid(row=0, column=0, sticky="w", pady=(0, 12))
        presets = ttk.Combobox(self.editor_frame, textvariable=self.preset, state="readonly",
                              values=("Personalizada", *PLATFORM_PRESETS))
        presets.grid(row=0, column=1, sticky="ew", padx=(12, 0), pady=(0, 12))
        presets.bind("<<ComboboxSelected>>", self._apply_preset)
        labels = (("institution", "Institución"), ("platform", "Alias de cuenta"),
                  ("url", "Sitio HTTPS"), ("username", "Usuario"), ("password", "Contraseña"),
                  ("pin", "Frase maestra"))
        for row, (key, label) in enumerate(labels, start=1):
            ttk.Label(self.editor_frame, text=label).grid(row=row, column=0, sticky="w", pady=5)
            if key == "institution":
                entry = ttk.Combobox(self.editor_frame, textvariable=self.fields[key], values=sorted(set(institutions)))
            else:
                entry = ttk.Entry(self.editor_frame, textvariable=self.fields[key], show="*" if key in ("username", "password", "pin") else "")
            entry.grid(row=row, column=1, sticky="ew", padx=(12, 0), pady=5)
        ttk.Checkbutton(self.editor_frame, text="Usar PIN del entorno", variable=self.use_environment_pin).grid(
            row=7, column=0, columnspan=2, sticky="w", pady=8)
        edit_actions = ttk.Frame(self.editor_frame)
        edit_actions.grid(row=8, column=0, columnspan=2, sticky="ew", pady=8)
        for title, command in (("Consultar", self._load), ("Guardar cifrado", self._save), ("Limpiar", self._new)):
            ttk.Button(edit_actions, text=title, command=command).pack(side="left", padx=(0, 6))
        ttk.Label(self, text="Al editar, usuario y contraseña vacíos conservan los existentes.",
              wraplength=850).grid(row=4, column=0, sticky="w", pady=6)
        buttons = ttk.Frame(self)
        buttons.grid(row=3, column=0, sticky="w", pady=8)
        for text, command in (("Bloquear", self._lock), ("Cambiar frase maestra", self._rotate)):
            ttk.Button(buttons, text=text, command=command).pack(side="left", padx=(0, 6))
        ttk.Label(self, textvariable=self.status, wraplength=850).grid(row=5, column=0, sticky="w", pady=4)
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
        explicit = self.fields["pin"].get()
        if explicit:
            return explicit
        return os.environ.get("AULATEX_MASTER_PIN", "") if self.use_environment_pin.get() else ""

    def _clear_secrets(self) -> None:
        for key in ("username", "password", "pin"):
            self.fields[key].set("")

    def _refresh(self, pin: str) -> None:
        rows = self.vault.list_accounts(pin)
        self.accounts.delete(*self.accounts.get_children())
        self.account_id = None
        for row in rows:
            self.accounts.insert("", "end", iid=row["id"], values=(row["id"][:8], row["institution"], row["platform"], row["url"]))
        if rows:
            self.empty_state.place_forget()
        else:
            self.empty_state.configure(text="No hay cuentas guardadas")
            self.empty_state.place(relx=0.5, rely=0.5, anchor="center")

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
        self.preset.set("Personalizada")
        self.accounts.selection_remove(*self.accounts.selection())
        for var in self.fields.values():
            var.set("")
        self.status.set("Nueva cuenta: completa institución, plataforma, sitio, usuario, contraseña y PIN.")

    def _apply_preset(self, _event=None) -> None:
        selected = self.preset.get()
        self._new()
        self.preset.set(selected)
        if selected in PLATFORM_PRESETS:
            institution, url = PLATFORM_PRESETS[selected]
            self.fields["institution"].set(institution)
            self.fields["platform"].set(selected)
            self.fields["url"].set(url)

    def _details(self) -> None:
        details = f"Bóveda local: {self.vault.path}"
        if self.account_id:
            details += f"\n\nCuenta: {self.account_id}"
            details += "\n" + "\n".join(self.accounts.item(self.account_id, "values")[1:])
        messagebox.showinfo("Detalles de la bóveda", details, parent=self)

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
        self.use_environment_pin.set(False)
        self.accounts.delete(*self.accounts.get_children())
        self.empty_state.configure(text="Bóveda bloqueada")
        self.empty_state.place(relx=0.5, rely=0.5, anchor="center")
        self.status.set("Bóveda bloqueada. Campos limpiados y uso del PIN del entorno desactivado en esta ventana.")