from __future__ import annotations

import os
import math
import threading
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from shutil import copy2
from tkinter import filedialog, messagebox, ttk

from .analyze import analyze_text
from .azure_openai_client import invoke_chat
from .bot import _build_channel_text, _build_note_action_messages, _format_action_header, _parse_derivative_markdown
from .config import load_settings, validate_settings
from .document_reader import read_document_text
from .notes import save_note, save_note_derivative
from .polly_tts import synthesize_text_to_single_mp3
from .transcribe import transcribe_audio
from .ui.floating_panel import FloatingResultPanel
from .ui.result_card import ResultCard

try:
    import pygame
except Exception as pygame_import_error:  # pragma: no cover - entorno sin pygame
    pygame = None
    PYGAME_IMPORT_ERROR = pygame_import_error
else:
    PYGAME_IMPORT_ERROR = None


SETTINGS = load_settings()
RESULT_DEFINITIONS = [
    ("note", "Nota guardada"),
    ("explain", "Explicar"),
    ("suggest", "Sugerencias"),
    ("research", "Investigar"),
    ("dialectic", "Dialéctica"),
]


@dataclass
class ResultState:
    key: str
    title: str
    card: ResultCard
    status: str = "Pendiente"
    progress: int = 0
    text: str = ""
    audio_path: Path | None = None


class NotesGUI(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Bot Notas - Interfaz local")
        self._apply_initial_geometry()
        self.minsize(900, 620)
        self.configure(bg="#f6f7fb")

        self.selected_audio_path: Path | None = None
        self.selected_doc_path: Path | None = None
        self.analysis_payload: dict | None = None
        self.note_context: dict | None = None
        self.cards: dict[str, ResultState] = {}
        self.current_playing_key: str | None = None
        self.paused_key: str | None = None
        self.selected_card_key: str | None = None
        self._current_step_key: str | None = None
        self._pygame_ready = False
        self._external_player_fallback = False
        self._audio_player_error = ""
        self.gui_audio_dir = (SETTINGS.audio_storage_dir / "gui").resolve()
        self.gui_audio_dir.mkdir(parents=True, exist_ok=True)

        self._configure_styles()
        self._init_audio_player()
        self._build_header_inputs()
        self._build_actions()
        self._build_result_list()

        self.result_panel = FloatingResultPanel(
            self,
            on_play=self._play_card,
            on_close=self._clear_panel_selection,
        )
        self._bind_shortcuts()
        self.after(80, self._present_window)

    def _apply_initial_geometry(self) -> None:
        self.update_idletasks()
        screen_width = max(self.winfo_screenwidth(), 1024)
        screen_height = max(self.winfo_screenheight(), 720)

        width = min(930, max(900, math.floor(screen_width * 0.72)))
        height = min(999, max(620, math.floor(screen_height * 0.88)))
        pos_x = max(0, (screen_width - width) // 2)
        pos_y = max(0, (screen_height - height) // 2)

        self.geometry(f"{width}x{height}+{pos_x}+{pos_y}")

    def _present_window(self) -> None:
        try:
            self.deiconify()
            self.state("normal")
            self.lift()
            self.attributes("-topmost", True)
            self.focus_force()
            self.after(250, lambda: self.attributes("-topmost", False))
        except tk.TclError:
            return

    def _configure_styles(self) -> None:
        self.option_add("*Font", ("Segoe UI", 10))
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(
            "Modern.Horizontal.TProgressbar",
            troughcolor="#e5e7eb",
            background="#2563eb",
            bordercolor="#e5e7eb",
            lightcolor="#2563eb",
            darkcolor="#2563eb",
        )
        style.configure(
            "Card.Horizontal.TProgressbar",
            troughcolor="#eef2f7",
            background="#60a5fa",
            bordercolor="#eef2f7",
            lightcolor="#60a5fa",
            darkcolor="#60a5fa",
            thickness=5,
        )

    def _build_header_inputs(self) -> None:
        header = tk.Frame(self, bg="#f6f7fb")
        header.pack(fill="x", padx=18, pady=(16, 8))
        header.columnconfigure(0, weight=1)

        tk.Label(
            header,
            text="Texto libre",
            font=("Segoe UI", 10, "bold"),
            fg="#111827",
            bg="#f6f7fb",
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        text_shell = tk.Frame(header, bg="#ffffff", highlightbackground="#d1d5db", highlightthickness=1, bd=0)
        text_shell.grid(row=1, column=0, sticky="ew", pady=(6, 0))
        text_shell.columnconfigure(0, weight=1)

        self.text_input = tk.Text(
            text_shell,
            height=8,
            wrap="word",
            font=("Segoe UI", 10),
            bg="#ffffff",
            fg="#111827",
            relief="flat",
            bd=0,
            padx=12,
            pady=10,
            insertbackground="#111827",
        )
        self.text_input.grid(row=0, column=0, sticky="ew")
        self.text_input.bind("<Alt-Return>", self._generate_from_text_shortcut)

        scrollbar = tk.Scrollbar(text_shell, orient="vertical", command=self.text_input.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.text_input.configure(yscrollcommand=scrollbar.set)

    def _build_actions(self) -> None:
        bar = tk.Frame(self, bg="#ffffff", highlightbackground="#e5e7eb", highlightthickness=1, bd=0)
        bar.pack(fill="x", padx=18, pady=(0, 12))
        bar.columnconfigure(7, weight=1)

        self._button(bar, "Seleccionar audio", self._pick_audio).grid(row=0, column=0, padx=(12, 8), pady=10)
        self.audio_label = self._status_text(bar, "Sin audio")
        self.audio_label.grid(row=0, column=1, sticky="w", padx=(0, 16))

        self._button(bar, "Seleccionar documento", self._pick_document).grid(row=0, column=2, padx=(0, 8), pady=10)
        self.doc_label = self._status_text(bar, "Sin documento")
        self.doc_label.grid(row=0, column=3, sticky="w", padx=(0, 16))

        self.generate_btn = self._button(bar, "Generar nota", self._start_generate, primary=True)
        self.generate_btn.grid(row=0, column=4, padx=(0, 12), pady=10)

        self.global_status = tk.StringVar(value="Listo")
        tk.Label(
            bar,
            textvariable=self.global_status,
            font=("Segoe UI", 9, "bold"),
            fg="#374151",
            bg="#ffffff",
        ).grid(row=0, column=5, sticky="w", padx=(0, 10))

        self.global_progress = ttk.Progressbar(bar, mode="determinate", maximum=100, style="Modern.Horizontal.TProgressbar")
        self.global_progress.grid(row=0, column=6, columnspan=2, sticky="ew", padx=(0, 12))

    def _build_result_list(self) -> None:
        shell = tk.Frame(self, bg="#f6f7fb")
        shell.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        shell.columnconfigure(0, weight=1)

        tk.Label(
            shell,
            text="Resultados",
            font=("Segoe UI", 11, "bold"),
            fg="#111827",
            bg="#f6f7fb",
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", pady=(0, 8))

        list_frame = tk.Frame(shell, bg="#f6f7fb")
        list_frame.grid(row=1, column=0, sticky="nsew")
        list_frame.columnconfigure(0, weight=1)

        for row, (key, title) in enumerate(RESULT_DEFINITIONS):
            card = ResultCard(
                list_frame,
                key,
                title,
                self._show_result_panel,
                self._play_card,
                self._pause_card,
                self._stop_card,
            )
            card.grid(row=row, column=0, sticky="ew", pady=(0, 8))
            card.set_result("Pendiente", "Pendiente", 0)
            self.cards[key] = ResultState(key=key, title=title, card=card)

        shell.rowconfigure(1, weight=1)

    def _pick_audio(self) -> None:
        path = filedialog.askopenfilename(
            title="Seleccionar audio",
            filetypes=[("Audio", "*.ogg *.mp3 *.wav *.m4a"), ("Todos", "*.*")],
        )
        if not path:
            return
        self.selected_audio_path = Path(path)
        self.audio_label.configure(text=self.selected_audio_path.name)

    def _pick_document(self) -> None:
        path = filedialog.askopenfilename(
            title="Seleccionar documento",
            filetypes=[("Documento", "*.pdf *.txt *.md *.docx"), ("Todos", "*.*")],
        )
        if not path:
            return
        self.selected_doc_path = Path(path)
        self.doc_label.configure(text=self.selected_doc_path.name)

    def _start_generate(self) -> None:
        self.generate_btn.configure(state="disabled")
        self.global_status.set("Procesando...")
        self.global_progress.configure(value=5)
        self.result_panel.hide()
        self.selected_card_key = None
        self._current_step_key = None
        for state in self.cards.values():
            self._set_card(state.key, status="Pendiente", progress=0, text="", audio_path=None)

        worker = threading.Thread(target=self._run_pipeline, daemon=True)
        worker.start()

    def _generate_from_text_shortcut(self, _event: tk.Event) -> str:
        if str(self.generate_btn.cget("state")) != "disabled":
            self._start_generate()
        return "break"

    def _run_pipeline(self) -> None:
        try:
            missing = validate_settings(SETTINGS)
            if missing:
                raise RuntimeError("Faltan variables de entorno: " + ", ".join(missing))

            source_text, source_type, source_audio = self._resolve_source_text()

            self._ui(lambda: self.global_progress.configure(value=20))
            self._set_processing("note", "Generando nota...", 20)

            analysis = analyze_text(source_text, source_audio=source_audio, settings=SETTINGS, source_type=source_type)
            saved = save_note(SETTINGS.notes_dir, analysis)

            note_text = self._build_note_text_for_ui(saved.title, analysis)
            note_audio_text = self._build_note_audio_text(saved.title, analysis)
            note_audio_path = self._persist_gui_audio(
                synthesize_text_to_single_mp3(SETTINGS, note_audio_text, f"gui_note_{saved.note_path.stem}"),
                saved.note_path.with_suffix(".mp3").name,
            )

            self.note_context = {
                "title": saved.title,
                "corrected_text": str(analysis.get("corrected_text", "")).strip(),
                "concepts": analysis.get("concepts", []),
                "related_terms": analysis.get("related_terms", []),
            }
            self.analysis_payload = analysis

            # Aqui se conecta el resultado real del pipeline con la tarjeta compacta.
            self._ui(lambda: self._set_card("note", status="Listo", progress=100, text=note_text, audio_path=note_audio_path))
            self._ui(lambda: self.global_progress.configure(value=45))

            actions = ["explain", "suggest", "research", "dialectic"]
            progress_marks = {"explain": 60, "suggest": 72, "research": 84, "dialectic": 96}

            for action in actions:
                self._set_processing(action, "Generando texto...", progress_marks[action] - 8)
                messages = _build_note_action_messages(action, self.note_context)
                max_tokens = SETTINGS.azure_openai_max_output_tokens
                text_result = invoke_chat(SETTINGS, messages, max_tokens=max_tokens, temperature=0.35, response_format_json=False)
                derivative_saved_path = save_note_derivative(saved.note_path, action, text_result, note_title=saved.title)
                derivative_payload = _parse_derivative_markdown(derivative_saved_path.read_text(encoding="utf-8"))
                telegram_text = _build_channel_text(derivative_payload, "telegram")
                audio_text = _build_channel_text(derivative_payload, "audio")

                self._set_processing(action, "Generando audio...", progress_marks[action] - 3)
                audio_path = self._persist_gui_audio(
                    synthesize_text_to_single_mp3(SETTINGS, audio_text, f"gui_{action}_{saved.note_path.stem}"),
                    derivative_saved_path.with_suffix(".mp3").name,
                )
                self._ui(
                    lambda a=action, txt=telegram_text, ap=audio_path: self._set_card(
                        a,
                        status="Listo",
                        progress=100,
                        text=txt,
                        audio_path=ap,
                    )
                )
                self._ui(lambda mark=progress_marks[action]: self.global_progress.configure(value=mark))

            self._current_step_key = None
            self._ui(lambda: self.global_progress.configure(value=100))
            self._ui(lambda: self.global_status.set("Completado"))
        except Exception as exc:
            error_text = str(exc)
            current_key = self._current_step_key
            if current_key:
                self._ui(lambda key=current_key, text=error_text: self._set_card(key, status="Error", progress=100, text=text, audio_path=None))
            self._ui(lambda: self.global_status.set(f"Error: {error_text}"))
            self._ui(lambda: messagebox.showerror("Error", error_text))
        finally:
            self._ui(lambda: self.generate_btn.configure(state="normal"))

    def _resolve_source_text(self) -> tuple[str, str, str]:
        text = self.text_input.get("1.0", "end").strip()
        if text:
            return text, "gui_text", ""

        if self.selected_audio_path:
            transcript = transcribe_audio(str(self.selected_audio_path), SETTINGS)
            return transcript, "gui_audio", str(self.selected_audio_path)

        if self.selected_doc_path:
            doc_text = read_document_text(self.selected_doc_path)
            return doc_text, "gui_document", str(self.selected_doc_path)

        raise RuntimeError("Escribe texto o selecciona un audio/documento para generar la nota.")

    def _set_processing(self, key: str, preview: str, progress: int) -> None:
        self._current_step_key = key
        self._ui(lambda: self._set_card_status(key, "Procesando", preview=preview, progress=progress))

    def _set_card(self, key: str, status: str, progress: int, text: str, audio_path: Path | None) -> None:
        state = self.cards[key]
        state.status = status
        state.progress = progress
        state.text = text
        state.audio_path = audio_path
        preview = self._preview_text(text) if text else status
        state.card.set_result(status, preview, progress, has_audio=self._has_audio(state))
        self._refresh_panel_if_selected(key)

    def _set_card_status(self, key: str, status: str, preview: str | None = None, progress: int | None = None) -> None:
        state = self.cards[key]
        state.status = status
        if progress is not None:
            state.progress = progress
        state.card.set_result(status, preview or self._preview_text(state.text) or status, state.progress, has_audio=self._has_audio(state))
        self._refresh_panel_if_selected(key)

    def _show_result_panel(self, key: str) -> None:
        if self.selected_card_key and self.selected_card_key in self.cards:
            self.cards[self.selected_card_key].card.set_selected(False)

        self.selected_card_key = key
        state = self.cards[key]
        state.card.set_selected(True)
        self.result_panel.show(
            state.card,
            key=key,
            title=state.title,
            status=state.status,
            content=state.text,
            has_audio=self._has_audio(state),
        )

    def _refresh_panel_if_selected(self, key: str) -> None:
        if self.selected_card_key == key and self.result_panel.is_visible():
            self._show_result_panel(key)

    def _clear_panel_selection(self) -> None:
        if self.selected_card_key and self.selected_card_key in self.cards:
            self.cards[self.selected_card_key].card.set_selected(False)
        self.selected_card_key = None

    def _bind_shortcuts(self) -> None:
        for index, (key, _title) in enumerate(RESULT_DEFINITIONS, start=1):
            self.bind_all(f"<Control-Key-{index}>", lambda event, k=key: self._view_shortcut(event, k))
            self.bind_all(f"<Alt-Key-{index}>", lambda event, k=key: self._play_shortcut(event, k))
        self.bind_all("<space>", self._space_shortcut)
        self.bind_all("<KeyPress-space>", self._space_shortcut)
        self.bind_all("<KeyPress-c>", self._copy_shortcut)
        self.bind_all("<KeyPress-C>", self._copy_shortcut)
        self.bind_all("<Escape>", self._escape_shortcut)

    def _view_shortcut(self, _event: tk.Event, key: str) -> str:
        self._show_result_panel(key)
        return "break"

    def _play_shortcut(self, _event: tk.Event, key: str) -> str:
        self._play_card(key)
        return "break"

    def _space_shortcut(self, _event: tk.Event) -> str | None:
        if self.focus_get() is self.text_input:
            return None

        if self.current_playing_key:
            if self.paused_key == self.current_playing_key:
                self._resume_audio(self.current_playing_key)
            else:
                self._pause_audio()
            return "break"

        if not self.result_panel.is_visible() or not self.selected_card_key:
            return None

        state = self.cards[self.selected_card_key]
        if not self._has_audio(state):
            self.result_panel.hide()
            return "break"

        if self.current_playing_key == state.key:
            if state.status.casefold().startswith("pausado"):
                self._resume_audio(state.key)
            else:
                self._pause_audio()
        else:
            self._play_card(state.key)
        return "break"

    def _escape_shortcut(self, _event: tk.Event) -> str | None:
        if self.result_panel.is_visible():
            self.result_panel.hide()
            return "break"
        return None

    def _copy_shortcut(self, _event: tk.Event) -> str | None:
        if self.focus_get() is self.text_input:
            return None
        if not self.result_panel.is_visible():
            return None
        self.result_panel.copy()
        return "break"

    def _build_note_text_for_ui(self, title: str, analysis: dict) -> str:
        concepts = analysis.get("concepts", []) if isinstance(analysis.get("concepts"), list) else []
        related = analysis.get("related_terms", []) if isinstance(analysis.get("related_terms"), list) else []
        concept_lines = []
        for item in concepts[:5]:
            if isinstance(item, dict):
                term = str(item.get("term", "")).strip()
                definition = str(item.get("definition", "")).strip()
                if term:
                    concept_lines.append(f"- {term}: {definition}" if definition else f"- {term}")

        text = [title, "", str(analysis.get("corrected_text", "")).strip()]
        if concept_lines:
            text.extend(["", "Conceptos clave:", *concept_lines])
        if related:
            text.extend(["", "Términos relacionados:", *[f"- {str(item)}" for item in related[:8]]])
        return "\n".join(line for line in text if line is not None).strip()

    def _build_note_audio_text(self, title: str, analysis: dict) -> str:
        corrected = str(analysis.get("corrected_text", "")).strip()
        concepts = analysis.get("concepts", []) if isinstance(analysis.get("concepts"), list) else []
        concept_lines = []
        for item in concepts[:3]:
            if isinstance(item, dict):
                term = str(item.get("term", "")).strip()
                definition = str(item.get("definition", "")).strip()
                if term and definition:
                    concept_lines.append(f"{term}: {definition}")
        parts = [title, corrected]
        if concept_lines:
            parts.append("Conceptos clave.")
            parts.extend(concept_lines)
        return "\n".join(part for part in parts if part).strip()

    def _init_audio_player(self) -> None:
        if pygame is None:
            self._pygame_ready = False
            self._external_player_fallback = True
            self._audio_player_error = f"pygame no disponible: {PYGAME_IMPORT_ERROR}"
            return
        try:
            pygame.mixer.init()
            self._pygame_ready = True
            self._external_player_fallback = False
            self._audio_player_error = ""
        except Exception as exc:
            self._pygame_ready = False
            self._external_player_fallback = True
            self._audio_player_error = f"pygame.mixer no inicializo: {exc}"

    def _play_card(self, key: str) -> None:
        self.focus_set()
        state = self.cards[key]
        if not state.audio_path or not state.audio_path.exists():
            return

        if self.current_playing_key == key and state.status.casefold().startswith("pausado"):
            self._resume_audio(key)
            return

        if not self._pygame_ready:
            self._play_with_external_player(state.audio_path, key)
            return

        try:
            self._stop_audio()
            pygame.mixer.music.load(str(state.audio_path))
            pygame.mixer.music.play()
            self.current_playing_key = key
            self.paused_key = None
            self._set_card_status(key, "Reproduciendo")
            self.after(200, self._monitor_playback)
        except Exception as exc:
            self._audio_player_error = f"pygame no pudo cargar el audio: {exc}"
            self._play_with_external_player(state.audio_path, key)

    def _pause_card(self, key: str) -> None:
        self.focus_set()
        if self.current_playing_key == key:
            self._pause_audio()

    def _stop_card(self, key: str) -> None:
        self.focus_set()
        if self.current_playing_key == key:
            self._stop_audio()

    def _pause_audio(self) -> None:
        if not self._pygame_ready:
            return
        try:
            pygame.mixer.music.pause()
            if self.current_playing_key:
                self.paused_key = self.current_playing_key
                self._set_card_status(self.current_playing_key, "Pausado")
        except Exception:
            return

    def _resume_audio(self, key: str) -> None:
        if not self._pygame_ready or self.current_playing_key != key:
            return
        try:
            pygame.mixer.music.unpause()
            self.paused_key = None
            self._set_card_status(key, "Reproduciendo")
            self.after(200, self._monitor_playback)
        except Exception:
            return

    def _stop_audio(self) -> None:
        if not self._pygame_ready:
            return
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass
        if self.current_playing_key:
            self._set_card_status(self.current_playing_key, "Listo")
        self.current_playing_key = None
        self.paused_key = None

    def _monitor_playback(self) -> None:
        if not self._pygame_ready or self.current_playing_key is None:
            return
        if self.paused_key == self.current_playing_key:
            return
        try:
            busy = pygame.mixer.music.get_busy()
        except Exception:
            busy = False

        if busy:
            self.after(250, self._monitor_playback)
            return

        finished_key = self.current_playing_key
        self.current_playing_key = None
        if finished_key in self.cards:
            self._set_card_status(finished_key, "Listo")

    def _ui(self, callback) -> None:
        self.after(0, callback)

    def _play_with_external_player(self, audio_path: Path, key: str) -> None:
        try:
            os.startfile(str(audio_path))
            suffix = f": {self._audio_player_error}" if self._audio_player_error else ""
            self._set_card_status(key, f"Reproduciendo (externo){suffix}")
        except Exception as exc:
            messagebox.showerror("Reproducción", f"No se pudo reproducir el audio: {exc}")

    def _persist_gui_audio(self, temp_audio_path: Path | None, output_name: str) -> Path | None:
        if temp_audio_path is None:
            return None
        if not temp_audio_path.exists():
            return None

        target = self.gui_audio_dir / output_name
        try:
            if target.exists():
                target.unlink(missing_ok=True)
            copy2(temp_audio_path, target)
            return target
        finally:
            temp_audio_path.unlink(missing_ok=True)

    @staticmethod
    def _button(parent: tk.Misc, text: str, command, primary: bool = False) -> tk.Button:
        return tk.Button(
            parent,
            text=text,
            command=command,
            font=("Segoe UI", 9, "bold"),
            bg="#2563eb" if primary else "#f3f4f6",
            fg="#ffffff" if primary else "#374151",
            activebackground="#1d4ed8" if primary else "#e5e7eb",
            activeforeground="#ffffff" if primary else "#111827",
            bd=0,
            padx=12,
            pady=7,
            cursor="hand2",
        )

    @staticmethod
    def _status_text(parent: tk.Misc, value: str) -> tk.Label:
        return tk.Label(
            parent,
            text=value,
            font=("Segoe UI", 9),
            fg="#6b7280",
            bg="#ffffff",
            anchor="w",
        )

    @staticmethod
    def _preview_text(value: str, limit: int = 140) -> str:
        text = " ".join(value.split())
        if len(text) <= limit:
            return text
        return text[: limit - 3].rstrip() + "..."

    @staticmethod
    def _has_audio(state: ResultState) -> bool:
        return bool(state.audio_path and state.audio_path.exists())


def run_gui() -> None:
    app = NotesGUI()
    app.mainloop()


if __name__ == "__main__":
    run_gui()
