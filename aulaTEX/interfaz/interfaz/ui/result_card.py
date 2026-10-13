from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import ttk


STATUS_STYLES = {
    "ready": {
        "icon": "✓",
        "label": "Listo",
        "chip_bg": "#dcfce7",
        "chip_fg": "#166534",
        "accent": "#22c55e",
    },
    "processing": {
        "icon": "⏳",
        "label": "Procesando",
        "chip_bg": "#fef3c7",
        "chip_fg": "#92400e",
        "accent": "#f59e0b",
    },
    "pending": {
        "icon": "○",
        "label": "Pendiente",
        "chip_bg": "#f3f4f6",
        "chip_fg": "#4b5563",
        "accent": "#9ca3af",
    },
    "error": {
        "icon": "⚠",
        "label": "Error",
        "chip_bg": "#fee2e2",
        "chip_fg": "#991b1b",
        "accent": "#ef4444",
    },
}


def normalize_status(status: str) -> str:
    text = status.strip().casefold()
    if "error" in text or "fall" in text or "no pude" in text:
        return "error"
    if "listo" in text or "complet" in text:
        return "ready"
    if "proces" in text or "generando" in text or "reproduciendo" in text or "pausado" in text:
        return "processing"
    return "pending"


class ResultCard(tk.Frame):
    """Compact clickable row used by the local GUI result list."""

    def __init__(
        self,
        parent: tk.Misc,
        key: str,
        title: str,
        on_view: Callable[[str], None],
        on_play: Callable[[str], None],
        on_pause: Callable[[str], None],
        on_stop: Callable[[str], None],
    ) -> None:
        super().__init__(
            parent,
            bg="#ffffff",
            highlightbackground="#e5e7eb",
            highlightcolor="#2563eb",
            highlightthickness=1,
            bd=0,
        )
        self.key = key
        self.title = title
        self._on_view = on_view
        self._on_play = on_play
        self._on_pause = on_pause
        self._on_stop = on_stop
        self._selected = False
        self._status_key = "pending"

        self.columnconfigure(2, weight=1)

        self.accent = tk.Frame(self, width=4, bg=STATUS_STYLES["pending"]["accent"])
        self.accent.grid(row=0, column=0, rowspan=3, sticky="ns")

        self.icon_label = tk.Label(
            self,
            text=STATUS_STYLES["pending"]["icon"],
            font=("Segoe UI Symbol", 16),
            fg="#6b7280",
            bg="#ffffff",
            width=3,
        )
        self.icon_label.grid(row=0, column=1, rowspan=2, sticky="ns", padx=(10, 4), pady=12)

        self.title_label = tk.Label(
            self,
            text=title,
            font=("Segoe UI", 10, "bold"),
            fg="#111827",
            bg="#ffffff",
            anchor="w",
        )
        self.title_label.grid(row=0, column=2, sticky="ew", pady=(12, 2))

        self.preview_label = tk.Label(
            self,
            text="Pendiente",
            font=("Segoe UI", 9),
            fg="#6b7280",
            bg="#ffffff",
            anchor="nw",
            justify="left",
            height=2,
        )
        self.preview_label.grid(row=1, column=2, sticky="nsew", pady=(0, 10))

        self.status_label = tk.Label(
            self,
            text="○ Pendiente",
            font=("Segoe UI", 8, "bold"),
            fg=STATUS_STYLES["pending"]["chip_fg"],
            bg=STATUS_STYLES["pending"]["chip_bg"],
            padx=8,
            pady=3,
        )
        self.status_label.grid(row=0, column=3, sticky="e", padx=(10, 8), pady=(12, 2))

        self.view_button = self._action_button(
            self,
            "Ver",
            self._select,
            bg="#eff6ff",
            fg="#1d4ed8",
            active="#dbeafe",
        )
        self.view_button.grid(row=0, column=4, sticky="e", padx=(0, 10), pady=(12, 2))

        action_bar = tk.Frame(self, bg="#ffffff")
        action_bar.grid(row=1, column=3, columnspan=2, sticky="e", padx=(10, 10), pady=(0, 10))

        self.play_button = self._action_button(action_bar, "Play", lambda: self._on_play(self.key))
        self.play_button.pack(side="left")
        self.pause_button = self._action_button(action_bar, "Pause", lambda: self._on_pause(self.key))
        self.pause_button.pack(side="left", padx=(6, 0))
        self.stop_button = self._action_button(action_bar, "Stop", lambda: self._on_stop(self.key))
        self.stop_button.pack(side="left", padx=(6, 0))

        self.progress = ttk.Progressbar(self, mode="determinate", maximum=100, style="Card.Horizontal.TProgressbar")
        self.progress.grid(row=2, column=1, columnspan=4, sticky="ew", padx=10, pady=(0, 8))

        self._bind_clicks(self)
        self.bind("<Configure>", self._update_preview_wrap)
        self._set_audio_controls(False)

    def set_result(self, status: str, preview: str, progress: int, has_audio: bool = False) -> None:
        status_key = normalize_status(status)
        self._status_key = status_key
        style = STATUS_STYLES[status_key]
        self.icon_label.configure(text=style["icon"], fg=style["chip_fg"])
        self.status_label.configure(
            text=f"{style['icon']} {style['label']}",
            fg=style["chip_fg"],
            bg=style["chip_bg"],
        )
        self.preview_label.configure(text=self._two_line_preview(preview or status))
        self.accent.configure(bg="#2563eb" if self._selected else style["accent"])
        self.progress.configure(value=max(0, min(progress, 100)))
        self.view_button.configure(text="Ver" if has_audio or preview else "Abrir")
        self._set_audio_controls(has_audio)

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        self.configure(highlightbackground="#2563eb" if selected else "#e5e7eb", highlightthickness=2 if selected else 1)
        self.accent.configure(bg="#2563eb" if selected else STATUS_STYLES[self._status_key]["accent"])

    def _select(self) -> None:
        self._on_view(self.key)

    def _bind_clicks(self, widget: tk.Widget) -> None:
        widget.bind("<Button-1>", lambda _event: self._select())
        widget.configure(cursor="hand2")
        for child in widget.winfo_children():
            if not isinstance(child, tk.Button):
                self._bind_clicks(child)

    def _set_audio_controls(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        self.play_button.configure(state=state)
        self.pause_button.configure(state=state)
        self.stop_button.configure(state=state)

    def _update_preview_wrap(self, _event: tk.Event | None = None) -> None:
        action_width = 290
        self.preview_label.configure(wraplength=max(260, self.winfo_width() - action_width))

    @staticmethod
    def _action_button(
        parent: tk.Misc,
        text: str,
        command: Callable[[], None],
        bg: str = "#f3f4f6",
        fg: str = "#374151",
        active: str = "#e5e7eb",
    ) -> tk.Button:
        return tk.Button(
            parent,
            text=text,
            command=command,
            font=("Segoe UI", 8, "bold"),
            bg=bg,
            fg=fg,
            activebackground=active,
            activeforeground=fg,
            bd=0,
            padx=8,
            pady=4,
            cursor="hand2",
            takefocus=0,
        )

    @staticmethod
    def _two_line_preview(value: str, limit: int = 210) -> str:
        text = " ".join(value.split())
        if not text:
            return "Sin contenido todavía"
        if len(text) <= limit:
            return text
        return text[: limit - 3].rstrip() + "..."
