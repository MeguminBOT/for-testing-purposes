import tkinter as tk
from tkinter import ttk
from datetime import datetime


class UpdateWindow:
    """Console-like window for showing detailed update progress"""

    def __init__(self, title="Update Progress", width=600, height=400):
        self.window = tk.Toplevel()
        self.window.title(title)
        self.window.geometry(f"{width}x{height}")
        self.window.configure(bg='#1e1e1e')

        self.window.transient()
        self.window.grab_set()
        self.window.focus_set()

        self.console_frame = tk.Frame(self.window, bg='#1e1e1e')
        self.console_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.console_text = tk.Text(
            self.console_frame,
            bg='#1e1e1e',
            fg='#ffffff',
            font=('Consolas', 10),
            insertbackground='#ffffff',
            selectbackground='#3d3d3d',
            wrap=tk.WORD,
            state=tk.DISABLED
        )

        self.scrollbar = ttk.Scrollbar(self.console_frame, orient=tk.VERTICAL, command=self.console_text.yview)
        self.console_text.configure(yscrollcommand=self.scrollbar.set)

        self.console_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.progress_frame = tk.Frame(self.window, bg='#1e1e1e')
        self.progress_frame.pack(fill=tk.X, padx=10, pady=5)

        self.progress_label = tk.Label(
            self.progress_frame,
            text="Initializing...",
            bg='#1e1e1e',
            fg='#ffffff',
            font=('Arial', 9)
        )
        self.progress_label.pack(anchor=tk.W)

        self.progressbar = ttk.Progressbar(
            self.progress_frame,
            orient="horizontal",
            length=width-20,
            mode="determinate"
        )
        self.progressbar.pack(fill=tk.X, pady=(5, 0))

        self.button_frame = tk.Frame(self.window, bg='#1e1e1e')
        self.button_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.restart_btn = tk.Button(
            self.button_frame,
            text="Restart Application",
            state=tk.DISABLED,
            bg='#0d7377',
            fg='white',
            font=('Arial', 9, 'bold'),
            relief=tk.FLAT,
            padx=20
        )
        self.restart_btn.pack(side=tk.RIGHT, padx=(5, 0))

        self.close_btn = tk.Button(
            self.button_frame,
            text="Close",
            command=self.close,
            bg='#444444',
            fg='white',
            font=('Arial', 9),
            relief=tk.FLAT,
            padx=20
        )
        self.close_btn.pack(side=tk.RIGHT)

        self.console_text.tag_configure("info", foreground="#00ff00")
        self.console_text.tag_configure("warning", foreground="#ffff00")
        self.console_text.tag_configure("error", foreground="#ff0000")
        self.console_text.tag_configure("success", foreground="#00ff88")
        self.console_text.tag_configure("timestamp", foreground="#888888")

        self.window.update()

    def log(self, message, level="info"):
        self.window.after(0, self._log_safe, message, level)

    def _log_safe(self, message, level):
        timestamp = datetime.now().strftime("%H:%M:%S")

        self.console_text.config(state=tk.NORMAL)
        self.console_text.insert(tk.END, f"[{timestamp}] ", "timestamp")
        self.console_text.insert(tk.END, f"{message}\n", level)
        self.console_text.see(tk.END)
        self.console_text.config(state=tk.DISABLED)

        self.window.update_idletasks()

    def set_progress(self, value, status_text=""):
        self.window.after(0, self._set_progress_safe, value, status_text)

    def _set_progress_safe(self, value, status_text):
        self.progressbar['value'] = value
        if status_text:
            self.progress_label.config(text=status_text)
        self.window.update_idletasks()

    def enable_restart(self, restart_callback):
        self.window.after(0, self._enable_restart_safe, restart_callback)

    def _enable_restart_safe(self, restart_callback):
        self.restart_btn.config(state=tk.NORMAL, command=restart_callback)

    def close(self):
        try:
            self.window.grab_release()
            self.window.destroy()
        except:
            pass
