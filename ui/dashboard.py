"""Desktop dashboard for JARVIS (Tkinter, no extra UI dependency)."""

import json
import logging
import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk

import config
from ai.provider import load_history
from assistant.controller import AssistantController, ACTIVITY_FILE

logger = logging.getLogger(__name__)

BG = "#0b1020"
PANEL = "#111a2e"
PANEL_ALT = "#17223a"
TEXT = "#e6edf7"
MUTED = "#8fa1bb"
ACCENT = "#6ee7d8"
PURPLE = "#a99bff"


class JarvisDashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("JARVIS · Desktop Assistant")
        self.root.geometry("1440x900")
        self.root.minsize(1120, 720)
        self.root.configure(bg=BG)
        self.events = queue.Queue()
        self.controller = AssistantController(self.events.put)
        self.messages = []
        self.activity_rows = []
        self.active_page = "Dashboard"
        self._setup_style()
        self._build_shell()
        self._load_saved_conversation()
        self.show_page("Dashboard")
        self.root.after(100, self._poll_events)
        self.root.after(2500, self._refresh_diagnostics)
        self.root.protocol("WM_DELETE_WINDOW", self._close)

    def _setup_style(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("Treeview", background=PANEL, foreground=TEXT,
                        fieldbackground=PANEL, rowheight=34, borderwidth=0)
        style.configure("Treeview.Heading", background=PANEL_ALT, foreground=MUTED,
                        font=("TkDefaultFont", 9, "bold"), relief="flat")
        style.map("Treeview", background=[("selected", "#263654")], foreground=[("selected", TEXT)])
        style.configure("TEntry", fieldbackground=PANEL_ALT, foreground=TEXT,
                        insertcolor=TEXT, bordercolor="#263654", padding=9)
        style.configure("TCheckbutton", background=BG, foreground=TEXT)
        style.map("TCheckbutton", background=[("active", BG)])
        style.configure("Vertical.TScrollbar", background=PANEL_ALT, troughcolor=BG,
                        bordercolor=BG, arrowcolor=MUTED)

    def _build_shell(self):
        self.shell = tk.Frame(self.root, bg=BG)
        self.shell.pack(fill="both", expand=True)
        self.sidebar = tk.Frame(self.shell, bg="#0e1628", width=218)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        brand = tk.Frame(self.sidebar, bg="#0e1628")
        brand.pack(fill="x", padx=22, pady=(25, 35))
        tk.Label(brand, text="◈  JARVIS", bg="#0e1628", fg=ACCENT,
                 font=("TkDefaultFont", 18, "bold")).pack(anchor="w")
        tk.Label(brand, text="PERSONAL ASSISTANT", bg="#0e1628", fg=MUTED,
                 font=("TkDefaultFont", 8, "bold")).pack(anchor="w", pady=(6, 0))
        self.nav_buttons = {}
        for name, mark in (("Dashboard", "⌂"), ("Activity & history", "◷"), ("Settings", "⚙")):
            button = tk.Button(self.sidebar, text=f"  {mark}    {name}", anchor="w",
                               command=lambda item=name: self.show_page(item),
                               bg="#0e1628", fg=MUTED, activebackground=PANEL_ALT,
                               activeforeground=TEXT, bd=0, padx=16, pady=13,
                               font=("TkDefaultFont", 10))
            button.pack(fill="x", padx=12, pady=2)
            self.nav_buttons[name] = button
        spacer = tk.Frame(self.sidebar, bg="#0e1628")
        spacer.pack(fill="both", expand=True)
        self.sidebar_status = tk.Label(self.sidebar, text="●  SYSTEM READY", anchor="w",
                                       bg="#0e1628", fg=ACCENT,
                                       font=("TkDefaultFont", 9, "bold"))
        self.sidebar_status.pack(fill="x", padx=24, pady=25)
        self.content = tk.Frame(self.shell, bg=BG)
        self.content.pack(side="left", fill="both", expand=True)

    def _header(self, eyebrow, title, subtitle):
        header = tk.Frame(self.content, bg=BG)
        header.pack(fill="x", padx=32, pady=(25, 19))
        tk.Label(header, text=eyebrow.upper(), bg=BG, fg=ACCENT,
                 font=("TkDefaultFont", 8, "bold")).pack(anchor="w")
        tk.Label(header, text=title, bg=BG, fg=TEXT,
                 font=("TkDefaultFont", 22, "bold")).pack(anchor="w", pady=(5, 2))
        tk.Label(header, text=subtitle, bg=BG, fg=MUTED,
                 font=("TkDefaultFont", 10)).pack(anchor="w")

    def _card(self, parent, title=None):
        card = tk.Frame(parent, bg=PANEL, highlightbackground="#1d2a43", highlightthickness=1)
        if title:
            tk.Label(card, text=title, bg=PANEL, fg=TEXT,
                     font=("TkDefaultFont", 11, "bold")).pack(anchor="w", padx=17, pady=(15, 10))
        return card

    def show_page(self, name):
        self.active_page = name
        for child in self.content.winfo_children():
            child.destroy()
        for nav_name, button in self.nav_buttons.items():
            selected = nav_name == name
            button.configure(bg="#1a2942" if selected else "#0e1628",
                             fg=ACCENT if selected else MUTED)
        if name == "Dashboard":
            self._build_dashboard()
        elif name == "Activity & history":
            self._build_history()
        else:
            self._build_settings()

    def _build_dashboard(self):
        self._header("Assistant workspace", "Good day.", "Your JARVIS desktop overview and live conversation.")
        body = tk.Frame(self.content, bg=BG)
        body.pack(fill="both", expand=True, padx=32, pady=(0, 25))
        body.columnconfigure(0, weight=7)
        body.columnconfigure(1, weight=3, minsize=260)
        body.rowconfigure(0, weight=1)
        chat = self._card(body, "Live conversation")
        chat.grid(row=0, column=0, sticky="nsew", padx=(0, 15))
        chat.rowconfigure(1, weight=1)
        chat.columnconfigure(0, weight=1)
        top_line = tk.Frame(chat, bg=PANEL)
        top_line.pack(fill="x", padx=17, pady=(0, 9))
        self.status_label = tk.Label(top_line, text="Ready", bg=PANEL, fg=ACCENT,
                                     font=("TkDefaultFont", 9, "bold"))
        self.status_label.pack(side="left")
        self.voice_button = tk.Button(top_line, text="Start voice", command=self._toggle_voice,
                                      bg="#203553", fg=TEXT, activebackground="#2b4568",
                                      activeforeground=TEXT, relief="flat", padx=14, pady=7,
                                      cursor="hand2")
        self.voice_button.pack(side="right")
        transcript_frame = tk.Frame(chat, bg=PANEL)
        transcript_frame.pack(fill="both", expand=True, padx=16, pady=(0, 12))
        self.transcript = tk.Text(transcript_frame, bg="#0e1628", fg=TEXT, bd=0,
                                  wrap="word", padx=16, pady=14, spacing1=5,
                                  font=("TkDefaultFont", 10), state="disabled",
                                  insertbackground=TEXT)
        scroll = ttk.Scrollbar(transcript_frame, command=self.transcript.yview)
        self.transcript.configure(yscrollcommand=scroll.set)
        self.transcript.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.transcript.tag_configure("user", foreground=ACCENT, font=("TkDefaultFont", 10, "bold"))
        self.transcript.tag_configure("assistant", foreground=PURPLE, font=("TkDefaultFont", 10, "bold"))
        self.transcript.tag_configure("body", foreground=TEXT, lmargin1=2, lmargin2=2, spacing3=12)
        self.transcript.tag_configure("time", foreground=MUTED, font=("TkDefaultFont", 8))
        composer = tk.Frame(chat, bg=PANEL)
        composer.pack(fill="x", padx=16, pady=(0, 16))
        self.command_var = tk.StringVar()
        entry = ttk.Entry(composer, textvariable=self.command_var)
        entry.pack(side="left", fill="x", expand=True, ipady=4)
        entry.bind("<Return>", lambda _event: self._send_command())
        tk.Button(composer, text="Send  →", command=self._send_command,
                  bg=ACCENT, fg="#07131b", activebackground="#94f3e8",
                  relief="flat", padx=16, pady=9, font=("TkDefaultFont", 9, "bold"),
                  cursor="hand2").pack(side="left", padx=(9, 0))
        right = tk.Frame(body, bg=BG)
        right.grid(row=0, column=1, sticky="nsew")
        diag = self._card(right, "System diagnostics")
        diag.pack(fill="x")
        self.diag_labels = {}
        for key in AssistantController.diagnostics():
            row = tk.Frame(diag, bg=PANEL)
            row.pack(fill="x", padx=16, pady=7)
            tk.Label(row, text=key, bg=PANEL, fg=MUTED,
                     font=("TkDefaultFont", 9)).pack(anchor="w")
            value = tk.Label(row, text="Checking…", bg=PANEL, fg=TEXT,
                             font=("TkDefaultFont", 9, "bold"))
            value.pack(anchor="w", pady=(2, 0))
            self.diag_labels[key] = value
        quick = self._card(right, "Recent activity")
        quick.pack(fill="both", expand=True, pady=(14, 0))
        self.recent_activity = tk.Frame(quick, bg=PANEL)
        self.recent_activity.pack(fill="both", expand=True, padx=15, pady=(0, 10))
        tk.Button(quick, text="View activity history  →", command=lambda: self.show_page("Activity & history"),
                  bg=PANEL, fg=ACCENT, activebackground=PANEL_ALT, activeforeground=TEXT,
                  relief="flat", anchor="w", padx=15, pady=10).pack(fill="x", side="bottom")
        self._render_messages()
        self._refresh_diagnostics(schedule=False)
        self._refresh_recent_activity()

    def _render_messages(self):
        if not hasattr(self, "transcript") or not self.transcript.winfo_exists():
            return
        self.transcript.configure(state="normal")
        self.transcript.delete("1.0", "end")
        if not self.messages:
            self.transcript.insert("end", "JARVIS\n", "assistant")
            self.transcript.insert("end", "I'm ready when you are. Enter a command below, or turn on voice listening.\n", "body")
        else:
            for message in self.messages:
                role = message["role"]
                self.transcript.insert("end", f"{'YOU' if role == 'user' else 'JARVIS'}  ", role)
                self.transcript.insert("end", f"{message.get('time', '')}\n", "time")
                self.transcript.insert("end", message["text"] + "\n\n", "body")
        self.transcript.configure(state="disabled")
        self.transcript.see("end")

    def _build_history(self):
        self._header("Records", "Activity & history", "Recent commands, outcomes, and saved AI conversation turns.")
        wrapper = self._card(self.content)
        wrapper.pack(fill="both", expand=True, padx=32, pady=(0, 30))
        toolbar = tk.Frame(wrapper, bg=PANEL)
        toolbar.pack(fill="x", padx=17, pady=15)
        tk.Label(toolbar, text="Recent activity", bg=PANEL, fg=TEXT,
                 font=("TkDefaultFont", 11, "bold")).pack(side="left")
        tk.Button(toolbar, text="Refresh", command=self._populate_history,
                  bg=PANEL_ALT, fg=TEXT, relief="flat", padx=12, pady=6).pack(side="right")
        columns = ("time", "kind", "command", "result")
        self.history_tree = ttk.Treeview(wrapper, columns=columns, show="headings", height=10)
        for col, title, width in (("time", "TIME", 170), ("kind", "SOURCE", 100),
                                  ("command", "COMMAND", 250), ("result", "RESULT", 500)):
            self.history_tree.heading(col, text=title)
            self.history_tree.column(col, width=width, anchor="w")
        self.history_tree.pack(fill="both", expand=True, padx=17, pady=(0, 10))
        tk.Label(wrapper, text="Saved AI conversation", bg=PANEL, fg=TEXT,
                 font=("TkDefaultFont", 10, "bold")).pack(anchor="w", padx=17, pady=(5, 7))
        self.saved_conversation = tk.Text(wrapper, height=7, bg="#0e1628", fg=TEXT,
                                          bd=0, wrap="word", padx=12, pady=10,
                                          font=("TkDefaultFont", 9), state="disabled")
        self.saved_conversation.pack(fill="x", padx=17, pady=(0, 15))
        self._populate_history()

    def _populate_history(self):
        if not hasattr(self, "history_tree") or not self.history_tree.winfo_exists():
            return
        self.history_tree.delete(*self.history_tree.get_children())
        try:
            with ACTIVITY_FILE.open("r", encoding="utf-8") as activity_file:
                entries = json.load(activity_file)
            if not isinstance(entries, list):
                entries = []
        except FileNotFoundError:
            entries = []
        except (OSError, json.JSONDecodeError):
            logger.exception("Could not read activity history")
            entries = []
        for entry in reversed(entries[-250:]):
            self.history_tree.insert("", "end", values=(entry.get("time", ""), entry.get("kind", ""),
                                                          entry.get("command", ""), entry.get("result", "")))
        if hasattr(self, "saved_conversation") and self.saved_conversation.winfo_exists():
            self.saved_conversation.configure(state="normal")
            self.saved_conversation.delete("1.0", "end")
            for item in load_history()[-30:]:
                speaker = "YOU" if item["role"] == "user" else "JARVIS"
                self.saved_conversation.insert("end", f"{speaker}  {item['content']}\n\n")
            if not self.saved_conversation.get("1.0", "end-1c").strip():
                self.saved_conversation.insert("end", "No saved AI conversation yet.")
            self.saved_conversation.configure(state="disabled")

    def _build_settings(self):
        self._header("Preferences", "Settings", "Tune your models, location, microphone, and speech output.")
        card = self._card(self.content, "Assistant preferences")
        card.pack(fill="x", padx=32, pady=(0, 20))
        form = tk.Frame(card, bg=PANEL)
        form.pack(fill="x", padx=20, pady=(0, 18))
        self.setting_vars = {}
        fields = [
            ("gemini_model", "Gemini model", "Primary response model"),
            ("groq_model", "Groq model", "Fallback response model"),
            ("default_city", "Default weather city", "Used when a command does not name a city"),
            ("microphone_index", "Microphone device index", "Restart voice listening after changing"),
            ("speech_rate", "Speech rate", "Words per minute"),
            ("speech_volume", "Speech volume", "Value from 0.0 to 1.0"),
        ]
        current = config.current_settings()
        for row, (key, title, help_text) in enumerate(fields):
            field_label = tk.Frame(form, bg=PANEL)
            field_label.grid(row=row, column=0, sticky="w", pady=10)
            tk.Label(field_label, text=title, bg=PANEL, fg=TEXT,
                     font=("TkDefaultFont", 10, "bold")).pack(anchor="w")
            tk.Label(field_label, text=help_text, bg=PANEL, fg=MUTED,
                     font=("TkDefaultFont", 8)).pack(anchor="w", pady=(3, 0))
            variable = tk.StringVar(value=str(current[key]))
            self.setting_vars[key] = variable
            ttk.Entry(form, textvariable=variable, width=42).grid(row=row, column=1, sticky="ew", padx=(30, 5), pady=17)
        form.columnconfigure(1, weight=1)
        self.speech_enabled_var = tk.BooleanVar(value=current["speech_enabled"])
        ttk.Checkbutton(form, text="Enable spoken responses", variable=self.speech_enabled_var).grid(
            row=len(fields), column=1, sticky="w", padx=(30, 5), pady=(14, 8))
        button_row = tk.Frame(card, bg=PANEL)
        button_row.pack(fill="x", padx=20, pady=(0, 20))
        tk.Button(button_row, text="Save settings", command=self._save_settings,
                  bg=ACCENT, fg="#07131b", activebackground="#94f3e8", relief="flat",
                  padx=17, pady=9, font=("TkDefaultFont", 9, "bold")).pack(side="left")
        tk.Label(button_row, text="API keys are read from your .env file and are never shown here.",
                 bg=PANEL, fg=MUTED, font=("TkDefaultFont", 9)).pack(side="left", padx=18)
        diag = self._card(self.content, "Connected services")
        diag.pack(fill="x", padx=32, pady=(0, 20))
        services = tk.Frame(diag, bg=PANEL)
        services.pack(fill="x", padx=20, pady=(0, 17))
        for idx, (name, state) in enumerate(AssistantController.diagnostics().items()):
            tk.Label(services, text=f"{name}   ·   {state}", bg=PANEL, fg=TEXT,
                     font=("TkDefaultFont", 9)).grid(row=idx // 3, column=idx % 3, sticky="w", padx=10, pady=8)

    def _save_settings(self):
        try:
            values = {key: variable.get().strip() for key, variable in self.setting_vars.items()}
            values["microphone_index"] = int(values["microphone_index"])
            values["speech_rate"] = int(values["speech_rate"])
            values["speech_volume"] = float(values["speech_volume"])
            if values["microphone_index"] < 0:
                raise ValueError("Microphone index must be zero or greater.")
            if not 0 <= values["speech_volume"] <= 1:
                raise ValueError("Speech volume must be between 0 and 1.")
            if values["speech_rate"] < 50:
                raise ValueError("Speech rate must be at least 50.")
            values["speech_enabled"] = self.speech_enabled_var.get()
            old_microphone_index = config.MICROPHONE_INDEX
            was_voice_active = self.controller.voice_active
            config.save_settings(values)
            if was_voice_active and old_microphone_index != config.MICROPHONE_INDEX:
                self.controller.stop_voice()
                self.root.after(300, self._restart_voice_when_stopped)
            self._refresh_diagnostics(schedule=False)
            messagebox.showinfo("Settings saved", "Your preferences have been saved.")
        except (ValueError, OSError) as exc:
            logger.exception("Could not save settings")
            messagebox.showerror("Settings not saved", str(exc))

    def _restart_voice_when_stopped(self):
        thread = self.controller.voice_thread
        if thread and thread.is_alive():
            self.root.after(300, self._restart_voice_when_stopped)
        else:
            self.controller.start_voice()

    def _send_command(self):
        command = self.command_var.get().strip()
        if not command:
            return
        self.command_var.set("")
        threading.Thread(target=self.controller.execute, args=(command, "dashboard"), daemon=True).start()

    def _toggle_voice(self):
        if self.controller.voice_active:
            self.controller.stop_voice()
        else:
            self.controller.start_voice()

    def _refresh_diagnostics(self, schedule=True):
        if hasattr(self, "diag_labels"):
            for name, value in AssistantController.diagnostics().items():
                label = self.diag_labels.get(name)
                if label and label.winfo_exists():
                    label.configure(text=value, fg=ACCENT if value.startswith("Ready") or value.startswith("Enabled") or value.startswith("Configured") else MUTED)
        if schedule:
            self.root.after(5000, self._refresh_diagnostics)

    def _refresh_recent_activity(self):
        if not hasattr(self, "recent_activity") or not self.recent_activity.winfo_exists():
            return
        for child in self.recent_activity.winfo_children():
            child.destroy()
        for entry in self._read_activity()[-4:][::-1]:
            tk.Label(self.recent_activity, text=entry.get("command", ""), bg=PANEL, fg=TEXT,
                     anchor="w", wraplength=245, justify="left",
                     font=("TkDefaultFont", 9, "bold")).pack(fill="x", pady=(8, 2))
            tk.Label(self.recent_activity, text=entry.get("time", ""), bg=PANEL, fg=MUTED,
                     anchor="w", font=("TkDefaultFont", 8)).pack(fill="x")

    @staticmethod
    def _read_activity():
        try:
            with ACTIVITY_FILE.open("r", encoding="utf-8") as activity_file:
                entries = json.load(activity_file)
            return entries if isinstance(entries, list) else []
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            return []

    def _load_saved_conversation(self):
        try:
            self.messages = [
                {"role": item["role"], "text": item["content"], "time": "Saved conversation"}
                for item in load_history()
            ]
        except Exception:
            logger.exception("Could not load conversation for dashboard")
            self.messages = []

    def _poll_events(self):
        try:
            while True:
                event = self.events.get_nowait()
                kind = event.get("type")
                if kind == "clear_conversation":
                    self.messages.clear()
                    self._render_messages()
                elif kind == "message":
                    self.messages.append(event)
                    self.messages = self.messages[-300:]
                    self._render_messages()
                elif kind == "status":
                    if hasattr(self, "status_label") and self.status_label.winfo_exists():
                        self.status_label.configure(text=event.get("text", "Ready"))
                    self.sidebar_status.configure(text=f"●  {event.get('text', 'READY').upper()}")
                elif kind == "voice":
                    if hasattr(self, "voice_button") and self.voice_button.winfo_exists():
                        active = event.get("active", False)
                        self.voice_button.configure(text="Pause voice" if active else "Start voice")
                elif kind == "diagnostic":
                    label = getattr(self, "diag_labels", {}).get(event.get("key"))
                    if label and label.winfo_exists():
                        label.configure(text=event.get("value", "Unknown"), fg=ACCENT)
                elif kind == "activity":
                    self._refresh_recent_activity()
                    self._populate_history()
        except queue.Empty:
            pass
        self.root.after(100, self._poll_events)

    def _close(self):
        self.controller.stop_voice()
        self.root.destroy()


def run_dashboard():
    config.configure_logging()
    root = tk.Tk()
    JarvisDashboard(root)
    root.mainloop()
