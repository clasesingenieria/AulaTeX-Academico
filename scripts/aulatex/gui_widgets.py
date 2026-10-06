from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class ScrollableForm(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.canvas = tk.Canvas(self, highlightthickness=0, height=240, width=1)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        vertical = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal = ttk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)
        horizontal.grid(row=1, column=0, sticky="ew")
        self.canvas.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        self.body = ttk.Frame(self.canvas)
        self.body.columnconfigure(0, weight=1)
        self.window = self.canvas.create_window((0, 0), window=self.body, anchor="nw")
        self.body.bind("<Configure>", self._resize)
        self.canvas.bind("<Configure>", self._resize)

    def _resize(self, _event=None):
        self.canvas.itemconfigure(self.window, width=max(self.canvas.winfo_width(), self.body.winfo_reqwidth()))
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def bind_content(self):
        def bind(widget):
            if not isinstance(widget, (tk.Text, ttk.Combobox, ttk.Spinbox)):
                widget.bind("<MouseWheel>", self._wheel, add="+")
                widget.bind("<Button-4>", self._wheel, add="+")
                widget.bind("<Button-5>", self._wheel, add="+")
            widget.bind("<FocusIn>", self._reveal, add="+")
            for child in widget.winfo_children():
                bind(child)
        bind(self.body)
        self.canvas.bind("<MouseWheel>", self._wheel, add="+")

    def _wheel(self, event):
        direction = -1 if event.num == 4 or event.delta > 0 else 1
        self.canvas.yview_scroll(direction * 3, "units")
        return "break"

    def _reveal(self, event):
        top = event.widget.winfo_rooty() - self.body.winfo_rooty()
        bottom = top + event.widget.winfo_height()
        visible_top = self.canvas.canvasy(0)
        visible_height = self.canvas.winfo_height()
        if top < visible_top:
            self.canvas.yview_moveto(top / max(1, self.body.winfo_height()))
        elif bottom > visible_top + visible_height:
            self.canvas.yview_moveto((bottom - visible_height) / max(1, self.body.winfo_height()))


class EnginePicker(ttk.Menubutton):
    def __init__(self, parent, *, textvariable, choices):
        super().__init__(parent, text="Motores", width=24)
        self.value = textvariable
        self.choices = tuple(dict.fromkeys(choices))
        self.variables = {name: tk.BooleanVar(self) for name in self.choices}
        self.menu = tk.Menu(self, tearoff=False)
        for name, variable in self.variables.items():
            self.menu.add_checkbutton(label=name, variable=variable, command=self._choose)
        self.configure(menu=self.menu)
        self.trace = self.value.trace_add("write", self._sync)
        self.bind("<Destroy>", self._destroyed, add="+")
        self._sync()

    def _sync(self, *_args):
        selected = [name.strip() for name in self.value.get().split(",") if name.strip()]
        for name, variable in self.variables.items():
            variable.set(name in selected)
        self.configure(text=selected[0] if len(selected) == 1 else f"{len(selected)} motores")

    def _choose(self):
        selected = [name for name, variable in self.variables.items() if variable.get()]
        if selected:
            self.value.set(", ".join(selected))
        else:
            self._sync()

    def _destroyed(self, event):
        if event.widget is self:
            self.value.trace_remove("write", self.trace)