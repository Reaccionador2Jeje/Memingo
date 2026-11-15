"""Memingo Desktop: a lightweight cross-platform editor for .mgo programs."""
from __future__ import annotations
import json, os, tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from . import __version__
from .interpreter import Interpreter, RuntimeErrorMemingo
from .lexer import LexerError
from .parser import ParseError, parse
from .packages import init_project

CONFIG_DIR = Path(os.environ.get("APPDATA" if os.name == "nt" else "XDG_CONFIG_HOME",
    str(Path.home() / ("AppData/Roaming" if os.name == "nt" else ".config")))) / "Memingo"
CONFIG_FILE = CONFIG_DIR / "desktop.json"
STARTER = '''# Welcome to Memingo
vibe name = "Memingo"
spill "Hello " + name

ritual greet(person) {
    spill "Welcome, " + person
}
greet("creator")
'''

class FirstRunWizard(tk.Toplevel):
    """Choose a workspace and optionally create a starter project."""
    def __init__(self, parent, complete):
        super().__init__(parent)
        self.complete = complete
        self.title("Welcome to Memingo")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        body = ttk.Frame(self, padding=24)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="Welcome to Memingo", font=("Segoe UI", 19, "bold")).pack(anchor="w")
        ttk.Label(body, text="Your workspace for learning, writing and running Memingo programs.",
                  wraplength=420).pack(anchor="w", pady=(8, 18))
        ttk.Label(body, text="Choose your projects folder").pack(anchor="w")
        row = ttk.Frame(body)
        row.pack(fill="x", pady=(6, 16))
        self.workspace = tk.StringVar(value=str(Path.home() / "MemingoProjects"))
        ttk.Entry(row, textvariable=self.workspace, width=44).pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="Browse…", command=self.browse).pack(side="left", padx=(8, 0))
        self.create_sample = tk.BooleanVar(value=True)
        ttk.Checkbutton(body, text="Create a starter project named Hello-Memingo",
                        variable=self.create_sample).pack(anchor="w", pady=(0, 18))
        ttk.Label(body, text="Memingo Desktop works offline; package downloads happen only when requested.",
                  wraplength=420).pack(anchor="w")
        ttk.Button(body, text="Finish setup", command=self.finish).pack(anchor="e", pady=(22, 0))
        self.bind("<Return>", lambda _event: self.finish())
        self.geometry("520x300")

    def browse(self):
        selected = filedialog.askdirectory(initialdir=self.workspace.get(), parent=self)
        if selected:
            self.workspace.set(selected)

    def finish(self):
        root = Path(self.workspace.get()).expanduser()
        try:
            root.mkdir(parents=True, exist_ok=True)
            if self.create_sample.get():
                project = root / "Hello-Memingo"
                project.mkdir(exist_ok=True)
                entry = project / "main.mgo"
                if not entry.exists():
                    entry.write_text(STARTER, encoding="utf-8")
                init_project(project, "hello-memingo")
            self.complete(root)
            self.destroy()
        except (OSError, ValueError) as exc:
            messagebox.showerror("Setup could not finish", str(exc), parent=self)

class MemingoDesktop(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"Memingo Desktop {__version__}")
        self.geometry("1100x740")
        self.minsize(760, 520)
        self.current_file = None
        self.workspace = Path.home() / "MemingoProjects"
        self._build_ui()
        self._load_settings()
        if not CONFIG_FILE.exists():
            self.after(180, lambda: FirstRunWizard(self, self._finish_setup))

    def _build_ui(self):
        style = ttk.Style(self)
        try: style.theme_use("clam")
        except tk.TclError: pass
        style.configure("TFrame", background="#171c28")
        style.configure("TLabel", background="#171c28", foreground="#e7eaf2")
        style.configure("TButton", padding=(10, 7))
        style.configure("Toolbar.TFrame", background="#202738")
        style.configure("Status.TLabel", background="#202738", foreground="#aab4c8")
        toolbar = ttk.Frame(self, style="Toolbar.TFrame", padding=8)
        toolbar.pack(fill="x")
        ttk.Label(toolbar, text="◆ MEMINGO", font=("Segoe UI", 13, "bold")).pack(side="left", padx=(4, 18))
        for label, action in (("New", self.new_file), ("Open", self.open_file),
                              ("Save", self.save_file), ("Run ▶", self.run_code)):
            ttk.Button(toolbar, text=label, command=action).pack(side="left", padx=3)
        content = ttk.Frame(self, padding=10)
        content.pack(fill="both", expand=True)
        self.file_label = ttk.Label(content, text="Untitled.mgo", font=("Segoe UI", 10, "bold"))
        self.file_label.pack(anchor="w", pady=(0, 7))
        editor_frame = ttk.Frame(content)
        editor_frame.pack(fill="both", expand=True)
        self.editor = tk.Text(editor_frame, wrap="none", undo=True, font=("Consolas", 12),
            bg="#0d1119", fg="#e6edf3", insertbackground="#ffffff",
            selectbackground="#28456d", padx=12, pady=12, relief="flat")
        yscroll = ttk.Scrollbar(editor_frame, orient="vertical", command=self.editor.yview)
        xscroll = ttk.Scrollbar(content, orient="horizontal", command=self.editor.xview)
        self.editor.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.editor.pack(side="left", fill="both", expand=True)
        yscroll.pack(side="right", fill="y")
        xscroll.pack(fill="x")
        self.editor.insert("1.0", STARTER)
        output_header = ttk.Frame(content)
        output_header.pack(fill="x", pady=(10, 4))
        ttk.Label(output_header, text="OUTPUT", font=("Segoe UI", 9, "bold")).pack(side="left")
        ttk.Button(output_header, text="Clear", command=self.clear_output).pack(side="right")
        self.output = tk.Text(content, height=9, wrap="word", state="disabled",
            font=("Consolas", 10), bg="#0b0e14", fg="#c8d2e3", padx=10, pady=8, relief="flat")
        self.output.pack(fill="x")
        status = ttk.Frame(self, style="Toolbar.TFrame", padding=(10, 5))
        status.pack(fill="x", side="bottom")
        ttk.Label(status, text=f"Memingo {__version__}  •  .mgo", style="Status.TLabel").pack(side="left")
        ttk.Label(status, text="Ready", style="Status.TLabel").pack(side="right")
        self.bind("<Control-n>", lambda _e: self.new_file())
        self.bind("<Control-o>", lambda _e: self.open_file())
        self.bind("<Control-s>", lambda _e: self.save_file())
        self.bind("<F5>", lambda _e: self.run_code())
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _load_settings(self):
        try:
            settings = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            self.workspace = Path(settings.get("workspace", str(self.workspace))).expanduser()
        except (OSError, ValueError, TypeError): pass

    def _finish_setup(self, workspace):
        self.workspace = workspace
        self._save_settings()
        self._write_output(f"Setup complete. Workspace: {workspace}")

    def _save_settings(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps({"workspace": str(self.workspace)}, indent=2), encoding="utf-8")

    def _write_output(self, text):
        self.output.configure(state="normal")
        self.output.insert("end", text.rstrip() + "\n")
        self.output.see("end")
        self.output.configure(state="disabled")

    def clear_output(self):
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.configure(state="disabled")

    def new_file(self):
        self.current_file = None
        self.file_label.configure(text="Untitled.mgo")
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", STARTER)

    def open_file(self):
        path = filedialog.askopenfilename(title="Open Memingo source", initialdir=self.workspace,
            filetypes=[("Memingo source", "*.mgo"), ("All files", "*.*")])
        if not path: return
        try:
            self.current_file = Path(path)
            self.editor.delete("1.0", "end")
            self.editor.insert("1.0", self.current_file.read_text(encoding="utf-8"))
            self.file_label.configure(text=self.current_file.name)
        except (OSError, UnicodeError) as exc:
            messagebox.showerror("Open failed", str(exc), parent=self)

    def save_file(self):
        if self.current_file is None:
            path = filedialog.asksaveasfilename(title="Save Memingo source", initialdir=self.workspace,
                defaultextension=".mgo", filetypes=[("Memingo source", "*.mgo")])
            if not path: return False
            self.current_file = Path(path)
        try:
            self.current_file.parent.mkdir(parents=True, exist_ok=True)
            self.current_file.write_text(self.editor.get("1.0", "end-1c"), encoding="utf-8")
            self.file_label.configure(text=self.current_file.name)
            self._write_output(f"Saved {self.current_file}")
            return True
        except (OSError, UnicodeError) as exc:
            messagebox.showerror("Save failed", str(exc), parent=self)
            return False

    def run_code(self):
        source = self.editor.get("1.0", "end-1c")
        project_dir = self.current_file.parent if self.current_file else self.workspace
        self.clear_output()
        interpreter = Interpreter(project_directory=project_dir)
        try:
            interpreter.run(parse(source))
            lines = interpreter.output
            self._write_output("\n".join(str(line) for line in lines) if lines else "Program finished with no output.")
        except (LexerError, ParseError, RuntimeErrorMemingo, RecursionError, OSError, ValueError) as exc:
            self._write_output(f"Memingo error: {exc}")

    def _on_close(self):
        try: self._save_settings()
        except OSError: pass
        self.destroy()

def main():
    MemingoDesktop().mainloop()

if __name__ == "__main__":
    main()
