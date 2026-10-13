from __future__ import annotations

import re
import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog, messagebox

from .result_card import STATUS_STYLES, normalize_status


class FloatingResultPanel:
    """Single reusable popover that displays the full content for one result."""

    def __init__(self, parent: tk.Misc, on_play: Callable[[str], None], on_close: Callable[[], None], on_send_telegram: Callable[[str], None] | None = None) -> None:
        self.parent = parent
        self.on_play = on_play
        self.on_close = on_close
        self.on_send_telegram = on_send_telegram
        self.key: str | None = None
        self.title = ""
        self.status = ""
        self.content = ""
        self._visible = False

        self.shadow = tk.Frame(parent, bg="#cbd5e1", bd=0)
        self.frame = tk.Frame(
            parent,
            bg="#ffffff",
            highlightbackground="#cbd5e1",
            highlightcolor="#cbd5e1",
            highlightthickness=1,
            bd=0,
        )

        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(1, weight=1)

        header = tk.Frame(self.frame, bg="#ffffff")
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 8))
        header.columnconfigure(0, weight=1)

        self.title_label = tk.Label(
            header,
            text="",
            font=("Segoe UI", 12, "bold"),
            fg="#111827",
            bg="#ffffff",
            anchor="w",
        )
        self.title_label.grid(row=0, column=0, sticky="ew")

        self.status_label = tk.Label(
            header,
            text="",
            font=("Segoe UI", 8, "bold"),
            padx=8,
            pady=3,
        )
        self.status_label.grid(row=0, column=1, sticky="e", padx=(10, 8))

        close_button = tk.Button(
            header,
            text="X",
            font=("Segoe UI", 9, "bold"),
            bg="#ffffff",
            fg="#6b7280",
            activebackground="#f3f4f6",
            activeforeground="#111827",
            bd=0,
            width=3,
            cursor="hand2",
            command=self.hide,
        )
        close_button.grid(row=0, column=2, sticky="e")

        text_box = tk.Frame(self.frame, bg="#ffffff")
        text_box.grid(row=1, column=0, sticky="nsew", padx=16)
        text_box.columnconfigure(0, weight=1)
        text_box.rowconfigure(0, weight=1)

        self.text = tk.Text(
            text_box,
            wrap="word",
            font=("Segoe UI", 10),
            bg="#f9fafb",
            fg="#111827",
            relief="flat",
            bd=0,
            padx=12,
            pady=10,
            highlightbackground="#e5e7eb",
            highlightthickness=1,
        )
        self.text.grid(row=0, column=0, sticky="nsew")

        scrollbar = tk.Scrollbar(text_box, orient="vertical", command=self.text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.text.configure(yscrollcommand=scrollbar.set, state="disabled")

        footer = tk.Frame(self.frame, bg="#ffffff")
        footer.grid(row=2, column=0, sticky="ew", padx=16, pady=(12, 16))

        self.play_button = self._make_button(footer, "▶ Reproducir", self._play)
        self.play_button.pack(side="left")
        self._make_button(footer, "Copiar", self._copy).pack(side="left", padx=(8, 0))
        self._make_button(footer, "Guardar MD", self._save_markdown).pack(side="left", padx=(8, 0))
        self._make_button(footer, "Enviar Telegram", self._send_telegram).pack(side="left", padx=(8, 0))
        self._make_button(footer, "Cerrar", self.hide, secondary=True).pack(side="right")

    def show(
        self,
        anchor: tk.Widget,
        key: str,
        title: str,
        status: str,
        content: str,
        has_audio: bool,
    ) -> None:
        self.key = key
        self.title = title
        self.status = status
        self.content = content.strip() or "Sin contenido todavía."

        self.title_label.configure(text=title)
        self._set_status(status)
        self._set_text(self.content)
        self.play_button.configure(state="normal" if has_audio else "disabled")

        self._place_near(anchor)
        self._visible = True
        self.shadow.lift()
        self.frame.lift()

    def hide(self) -> None:
        self.shadow.place_forget()
        self.frame.place_forget()
        self.key = None
        self._visible = False
        self.on_close()

    def is_visible(self) -> bool:
        return self._visible

    def _set_status(self, status: str) -> None:
        style = STATUS_STYLES[normalize_status(status)]
        self.status_label.configure(
            text=f"{style['icon']} {style['label']}",
            fg=style["chip_fg"],
            bg=style["chip_bg"],
        )

    def _set_text(self, content: str) -> None:
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("1.0", content)
        self.text.configure(state="disabled")

    def _place_near(self, anchor: tk.Widget) -> None:
        self.parent.update_idletasks()

        parent_w = max(self.parent.winfo_width(), 760)
        parent_h = max(self.parent.winfo_height(), 560)
        width = min(580, max(440, parent_w - 48))
        height = min(470, max(320, parent_h - 120))

        anchor_x = anchor.winfo_rootx() - self.parent.winfo_rootx()
        anchor_y = anchor.winfo_rooty() - self.parent.winfo_rooty()
        anchor_right = anchor_x + anchor.winfo_width()

        x = anchor_right + 16
        if x + width > parent_w - 18:
            x = max(18, parent_w - width - 18)

        y = anchor_y - 8
        if y + height > parent_h - 18:
            y = max(18, parent_h - height - 18)

        self.shadow.place(x=x + 6, y=y + 6, width=width, height=height)
        self.frame.place(x=x, y=y, width=width, height=height)

    def _play(self) -> None:
        if self.key:
            self.on_play(self.key)

    def copy(self) -> None:
        self._copy()

    def _copy(self) -> None:
        self.parent.clipboard_clear()
        self.parent.clipboard_append(self.content)
        self.parent.update()

    def _save_markdown(self) -> None:
        safe_title = re.sub(r"[^\w-]+", "_", self.title, flags=re.UNICODE).strip("_").lower() or "resultado"
        filename = filedialog.asksaveasfilename(
            parent=self.parent,
            title="Guardar resultado como Markdown",
            defaultextension=".md",
            initialfile=f"{safe_title}.md",
            filetypes=[("Markdown", "*.md"), ("Texto", "*.txt"), ("Todos", "*.*")],
        )
        if not filename:
            return

        content = f"# {self.title}\n\nEstado: {self.status}\n\n{self.content}\n"
        try:
            Path(filename).write_text(content, encoding="utf-8")
        except Exception as exc:
            messagebox.showerror("Guardar MD", f"No se pudo guardar el archivo: {exc}", parent=self.parent)

    def _send_telegram(self) -> None:
        if self.key and self.on_send_telegram:
            self.on_send_telegram(self.key)

    @staticmethod
    def _make_button(parent: tk.Misc, text: str, command: Callable[[], None], secondary: bool = False) -> tk.Button:
        if secondary:
            bg = "#f3f4f6"
            fg = "#374151"
            active = "#e5e7eb"
        else:
            bg = "#eff6ff"
            fg = "#1d4ed8"
            active = "#dbeafe"
        return tk.Button(
            parent,
            text=text,
            command=command,
            font=("Segoe UI", 9, "bold"),
            bg=bg,
            fg=fg,
            activebackground=active,
            activeforeground=fg,
            bd=0,
            padx=12,
            pady=6,
            cursor="hand2",
        )
