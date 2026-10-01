"""Desktop dashboard for JARVIS (Tkinter, no extra UI dependency)."""

import json
import logging
import queue
import threading
import tkinter as tk
from datetime import datetime
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
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        window_width = min(1536, int(screen_width * 0.94))
        window_height = min(1024, int(screen_height * 0.88))
        minimum_width = min(1080, int(screen_width * 0.88))
        minimum_height = min(680, int(screen_height * 0.78))
        self.compact_window = window_width < 1320 or window_height < 820
        self.root.geometry(
            f"{window_width}x{window_height}+{max(0, (screen_width-window_width)//2)}+"
            f"{max(0, (screen_height-window_height)//2)}"
        )
        self.root.minsize(minimum_width, minimum_height)
        self.root.configure(bg=BG)
        self.events = queue.Queue()
        self.controller = AssistantController(self.events.put)
        self.messages = []
        self.activity_rows = []
        self.active_page = "Dashboard"
        self.is_dark = config.THEME != "light"
        self._setup_style()
        self._build_shell()
        self._load_saved_conversation()
        self.show_page("Dashboard")
        self.root.after(100, self._poll_events)
        self.root.after(2500, self._refresh_diagnostics)
        self.root.protocol("WM_DELETE_WINDOW", self._close)
        self._resize_job = None
        self.root.bind("<Configure>", self._on_root_configure, add="+")
        self.root.after_idle(self._apply_responsive_layout)

    def _toggle_theme(self):
        self.is_dark = not self.is_dark
        theme = "dark" if self.is_dark else "light"
        try:
            config.save_settings({"theme": theme})
        except OSError:
            self.is_dark = not self.is_dark
            logger.exception("Could not save theme preference")
            messagebox.showerror("Theme not saved", "Could not save your theme preference.")
            return
        self.theme_button.configure(text="Light theme" if self.is_dark else "Dark theme")
        self._apply_theme()

    def _apply_theme(self):
        dark = {
            "#0b1020": BG, "#111a2e": PANEL, "#17223a": PANEL_ALT,
            "#e6edf7": TEXT, "#8fa1bb": MUTED, "#6ee7d8": ACCENT,
            "#a99bff": PURPLE,
        }
        light = {
            "#0b1020": "#f3f4f6", "#111a2e": "#ffffff", "#17223a": "#e5e7eb",
            "#e6edf7": "#111827", "#8fa1bb": "#4b5563", "#6ee7d8": "#111827",
            "#a99bff": "#374151", "#061321": "#ffffff", "#071321": "#f8fafc",
            "#087e9c": "#111827", "#066b87": "#374151",
            "#0c1a2b": "#ffffff", "#071a2a": "#f3f4f6", "#0b1b2d": "#f8fafc",
            "#122a3a": "#cbd5e1", "#12415b": "#94a3b8", "#07577b": "#374151",
            "#08709a": "#374151", "#0875a3": "#374151", "#087fae": "#374151",
            "#168fc0": "#374151", "#8ceeff": "#374151", "#b9f8ff": "#374151",
            "#b4f4ff": "#374151", "#42cfff": "#374151", "#8fc8f2": "#374151",
            "#10314b": "#e2e8f0", "#b8f2ff": "#374151", "#72bce8": "#374151",
            "#a8d9ff": "#374151", "#61bde8": "#374151", "#93d3ff": "#374151",
            "#203553": "#e5e7eb", "#2b4568": "#d1d5db", "#263654": "#d1d5db",
            "#073654": "#e5e7eb", "#9beeff": "#374151", "#0b263c": "#e0f2fe",
            "#0a2033": "#f8fafc", "#10283d": "#e5e7eb", "#09243a": "#e0f2fe",
            "#124f70": "#374151", "#66eaff": "#374151", "#00c9ff": "#374151",
            "#078dbb": "#374151", "#28f1ff": "#374151", "#12c9ff": "#374151",
            "#48caff": "#374151", "#27e5b0": "#111827", "#31d9ff": "#374151",
            "#65b9e9": "#374151", "#07131b": "#ffffff", "#94f3e8": "#111827",
        }
        palette = dark if self.is_dark else light
        self.root.configure(bg=palette["#0b1020"])
        self._recolor_widget(self.root, palette)
        style = ttk.Style(self.root)
        panel, panel_alt = palette["#111a2e"], palette["#17223a"]
        style.configure("Treeview", background=panel, foreground=palette["#e6edf7"],
                        fieldbackground=panel)
        style.configure("Treeview.Heading", background=panel_alt, foreground=palette["#8fa1bb"])
        style.map("Treeview", background=[("selected", panel_alt)],
                  foreground=[("selected", palette["#e6edf7"])])
        style.configure("TEntry", fieldbackground=panel_alt, foreground=palette["#e6edf7"],
                        insertcolor=palette["#e6edf7"])
        style.configure("TCheckbutton", background=palette["#0b1020"], foreground=palette["#e6edf7"])

    def _recolor_widget(self, widget, palette):
        color_options = ("bg", "background", "highlightbackground", "activebackground",
                         "troughcolor", "insertbackground", "fg", "foreground",
                         "activeforeground", "insertforeground")
        originals = getattr(widget, "_jarvis_original_colors", None)
        if originals is None:
            originals = {}
            for option in color_options:
                try:
                    originals[option] = widget.cget(option)
                except (tk.TclError, TypeError):
                    pass
            widget._jarvis_original_colors = originals
        for option, original in originals.items():
            replacement = palette.get(original, original)
            try:
                if replacement:
                    widget.configure(**{option: replacement})
            except (tk.TclError, TypeError):
                pass

        if isinstance(widget, tk.Text):
            original_tags = getattr(widget, "_jarvis_original_tags", None)
            if original_tags is None:
                original_tags = {
                    tag: widget.tag_cget(tag, "background")
                    for tag in ("user_body", "assistant_body", "error_body")
                }
                widget._jarvis_original_tags = original_tags
            for tag, original in original_tags.items():
                if original:
                    widget.tag_configure(tag, background=palette.get(original, original))

        if isinstance(widget, tk.Canvas):
            original_items = getattr(widget, "_jarvis_original_items", {})
            for item in widget.find_all():
                for option in ("fill", "outline"):
                    try:
                        key = (item, option)
                        if key not in original_items:
                            original_items[key] = widget.itemcget(item, option)
                        original = original_items[key]
                        replacement = palette.get(original, original)
                        if replacement:
                            widget.itemconfigure(item, **{option: replacement})
                    except tk.TclError:
                        pass
            widget._jarvis_original_items = original_items
        for child in widget.winfo_children():
            self._recolor_widget(child, palette)

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

        masthead_height = 108 if self.compact_window else 132
        masthead = tk.Frame(self.shell, bg="#061321", height=masthead_height,
                            highlightbackground="#07577b", highlightthickness=1)
        masthead.pack(fill="x", side="top")
        masthead.pack_propagate(False)
        brand = tk.Frame(masthead, bg="#061321")
        brand.pack(side="left", fill="y", padx=18, pady=8 if self.compact_window else 13)
        logo_size = 82 if self.compact_window else 100
        logo_center = logo_size / 2
        logo = tk.Canvas(brand, width=logo_size, height=logo_size, bg="#061321", highlightthickness=0)
        logo.pack(side="left")
        for radius, color, width in ((logo_size * .43, "#087fae", 2),
                                     (logo_size * .36, ACCENT, 2),
                                     (logo_size * .27, "#168fc0", 3)):
            logo.create_oval(logo_center-radius, logo_center-radius,
                             logo_center+radius, logo_center+radius, outline=color, width=width)
        core = logo_size * .17
        logo.create_oval(logo_center-core, logo_center-core, logo_center+core,
                         logo_center+core, fill="#8ceeff", outline="#b9f8ff", width=2)
        import math
        orbit = logo_size * .34
        dot = max(3, logo_size * .04)
        for angle in range(0, 360, 45):
            cx = logo_center + orbit * math.cos(math.radians(angle))
            cy = logo_center + orbit * math.sin(math.radians(angle))
            logo.create_oval(cx-dot, cy-dot, cx+dot, cy+dot, fill="#b4f4ff", outline="#42cfff")
        wordmark = tk.Frame(brand, bg="#061321")
        wordmark.pack(side="left", padx=17, pady=(9, 0))
        tk.Label(wordmark, text="J.A.R.V.I.S.", bg="#061321", fg="#a8d9ff",
                 font=("TkDefaultFont", 24 if self.compact_window else 28, "bold")).pack(anchor="w")
        tk.Label(wordmark, text="Y O U R   P E R S O N A L   A I   A S S I S T A N T",
                 bg="#061321", fg="#61bde8", font=("TkDefaultFont", 9, "bold")).pack(anchor="w", pady=(2, 0))
        date_panel = tk.Frame(masthead, bg="#071a2a", highlightbackground="#0875a3", highlightthickness=1)
        date_panel.pack(side="right", fill="y", padx=(10, 18), pady=10 if self.compact_window else 15)
        self.date_label = tk.Label(date_panel, text="", bg="#071a2a", fg="#93d3ff",
                                   font=("TkDefaultFont", 11))
        self.date_label.pack(anchor="w", padx=20, pady=(10, 0))
        self.clock_label = tk.Label(date_panel, text="", bg="#071a2a", fg="#a8d9ff",
                                    font=("TkDefaultFont", 20 if self.compact_window else 23, "bold"))
        self.clock_label.pack(anchor="w", padx=20, pady=(1, 8))
        self.theme_button = tk.Button(masthead, text="Light theme" if self.is_dark else "Dark theme",
                                      command=self._toggle_theme, bg="#0c1a2b", fg="#8fc8f2",
                                      activebackground="#10314b", activeforeground="#b8f2ff",
                                      relief="flat", padx=13, pady=8, cursor="hand2")
        self.theme_button.pack(side="right", padx=12)
        self._update_clock()

        workspace = tk.Frame(self.shell, bg=BG)
        workspace.pack(fill="both", expand=True)
        self.sidebar = tk.Frame(workspace, bg="#071321", width=190 if self.compact_window else 228,
                                 highlightbackground="#07577b", highlightthickness=1)
        self.sidebar.pack(side="left", fill="y", padx=(12, 8), pady=12)
        self.sidebar.pack_propagate(False)
        nav_items = [
            ("Home", "⌂", lambda: self.show_page("Dashboard")),
            ("Chat", "▤", lambda: self.show_page("Dashboard")),
            ("Voice", "♩", self._toggle_voice),
            ("Weather", "☁", lambda: self._quick_command("weather")),
            ("News", "▣", lambda: self._quick_command("latest news")),
            ("YouTube", "▶", lambda: self._quick_command("play")),
            ("Web Search", "⌕", lambda: self._quick_command("search")),
            ("Apps", "▦", lambda: self._quick_command("open google")),
            ("System", "⚙", lambda: self.show_page("Activity & history")),
            ("Settings", "⚙", lambda: self.show_page("Settings")),
        ]
        self.nav_buttons = {}
        for label, icon, callback in nav_items:
            button = tk.Button(self.sidebar, text=f"  {icon}    {label}", anchor="w",
                               command=callback, bg="#071321", fg="#8fc8f2",
                               activebackground="#10314b", activeforeground="#b8f2ff",
                               bd=0, padx=10, pady=8 if self.compact_window else 12,
                               font=("TkDefaultFont", 10 if self.compact_window else 11),
                               cursor="hand2")
            button.pack(fill="x", padx=7, pady=2)
            self.nav_buttons[label] = button
            button.bind("<Enter>", lambda _event, item=label: self._nav_hover(item, True))
            button.bind("<Leave>", lambda _event, item=label: self._nav_hover(item, False))
            if label not in {"Home", "Settings"}:
                tk.Frame(self.sidebar, bg="#122a3a", height=1).pack(fill="x", padx=17)
        spacer = tk.Frame(self.sidebar, bg="#071321")
        spacer.pack(fill="both", expand=True)
        self.sidebar_status = tk.Label(self.sidebar, text="●  SYSTEM READY", anchor="w",
                                       bg="#071321", fg=ACCENT,
                                       font=("TkDefaultFont", 9, "bold"))
        self.sidebar_status.pack(fill="x", padx=18, pady=(12, 5))
        for title, value in (("AI Provider", "Gemini / Groq"), ("Conversation Memory", "Active")):
            mini = tk.Frame(self.sidebar, bg="#0b1b2d", highlightbackground="#12415b", highlightthickness=1)
            mini.pack(fill="x", padx=9, pady=4)
            tk.Label(mini, text=title, bg="#0b1b2d", fg="#72bce8",
                     font=("TkDefaultFont", 8)).pack(anchor="w", padx=10, pady=(6, 0))
            tk.Label(mini, text=value, bg="#0b1b2d", fg=TEXT,
                     font=("TkDefaultFont", 9, "bold")).pack(anchor="w", padx=10, pady=(1, 7))
        self.content = tk.Frame(workspace, bg=BG)
        self.content.pack(side="left", fill="both", expand=True, padx=(2, 12), pady=12)

    def _nav_hover(self, label, hovering):
        button = self.nav_buttons.get(label)
        if not button:
            return
        selected = (label == ("Home" if self.active_page == "Dashboard" else self.active_page)
                    or (self.active_page == "Activity & history" and label == "System"))
        button.configure(bg="#073654" if selected else ("#10283d" if hovering else "#071321"))

    def _on_root_configure(self, event):
        if event.widget is not self.root:
            return
        if self._resize_job:
            self.root.after_cancel(self._resize_job)
        self._resize_job = self.root.after(120, self._apply_responsive_layout)

    def _apply_responsive_layout(self):
        self._resize_job = None
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        if width <= 1 or height <= 1:
            return
        narrow = width < 1180
        self.sidebar.configure(width=174 if narrow else (190 if self.compact_window else 228))
        body = getattr(self, "dashboard_body", None)
        if body and body.winfo_exists():
            body.columnconfigure(1, minsize=210 if narrow else (225 if self.compact_window else 260))
            body.columnconfigure(0, weight=6 if narrow else 7)
            body.columnconfigure(1, weight=4 if narrow else 3)
    def _update_clock(self):
        now = datetime.now()
        self.date_label.configure(text=now.strftime("%a, %d %b %Y"))
        self.clock_label.configure(text=now.strftime("%I:%M %p"))
        self.root.after(1000, self._update_clock)

    def _header(self, eyebrow, title, subtitle):
        header = tk.Frame(self.content, bg=BG)
        header.pack(fill="x", padx=24 if self.compact_window else 32,
                    pady=(14, 10) if self.compact_window else (25, 19))
        tk.Label(header, text=eyebrow.upper(), bg=BG, fg=ACCENT,
                 font=("TkDefaultFont", 8, "bold")).pack(anchor="w")
        tk.Label(header, text=title, bg=BG, fg=TEXT,
                 font=("TkDefaultFont", 19 if self.compact_window else 22, "bold")).pack(anchor="w", pady=(4, 2))
        tk.Label(header, text=subtitle, bg=BG, fg=MUTED,
                 font=("TkDefaultFont", 10)).pack(anchor="w")

    def _card(self, parent, title=None):
        card = tk.Frame(parent, bg="#0c1a2b", highlightbackground="#08709a", highlightthickness=1)
        if title:
            tk.Label(card, text=title, bg="#0c1a2b", fg=TEXT,
                     font=("TkDefaultFont", 11, "bold")).pack(anchor="w", padx=17, pady=(15, 10))
        return card

    def show_page(self, name):
        self.active_page = name
        animation_id = getattr(self, "wave_animation_id", None)
        if animation_id:
            try:
                self.root.after_cancel(animation_id)
            except tk.TclError:
                pass
            self.wave_animation_id = None
        for child in self.content.winfo_children():
            child.destroy()
        selected_nav = "Home" if name == "Dashboard" else name
        for nav_name, button in self.nav_buttons.items():
            selected = nav_name == selected_nav or (name == "Activity & history" and nav_name == "System")
            button.configure(bg="#073654" if selected else "#071321",
                             fg="#9beeff" if selected else "#8fc8f2",
                             highlightbackground="#00bff3" if selected else "#071321",
                             highlightthickness=1 if selected else 0)
        if name == "Dashboard":
            self._build_dashboard()
        elif name == "Activity & history":
            self._build_history()
        else:
            self._build_settings()
        self._apply_theme()
        self.root.after_idle(self._apply_responsive_layout)

    def _build_dashboard(self):
        self._header("HOME  /  ASSISTANT", "Live conversation", "Your personal AI assistant is ready.")
        body = tk.Frame(self.content, bg=BG)
        body.pack(fill="both", expand=True,
                  padx=18 if self.compact_window else 32,
                  pady=(0, 12) if self.compact_window else (0, 25))
        self.dashboard_body = body
        body.columnconfigure(0, weight=7)
        body.columnconfigure(1, weight=3, minsize=225 if self.compact_window else 260)
        body.rowconfigure(0, weight=1)
        chat = self._card(body, "Live conversation")
        chat.grid(row=0, column=0, sticky="nsew", padx=(0, 15))
        chat.rowconfigure(1, weight=1)
        chat.columnconfigure(0, weight=1)
        top_line = tk.Frame(chat, bg="#0c1a2b")
        top_line.pack(fill="x", padx=17, pady=(0, 9))
        self.assistant_state = "ready"
        self.processing_dots = 0
        self.status_label = tk.Label(top_line, text="READY · TYPE OR START VOICE", bg="#0c1a2b", fg=ACCENT,
                                     font=("TkDefaultFont", 9, "bold"))
        self.status_label.pack(side="left")
        self.provider_label = tk.Label(top_line, text="GEMINI  ·  GROQ BACKUP", bg="#0c1a2b", fg=MUTED,
                                       font=("TkDefaultFont", 8, "bold"))
        self.provider_label.pack(side="right")
        transcript_frame = tk.Frame(chat, bg="#0c1a2b")
        self.transcript = tk.Text(transcript_frame, bg="#071321", fg=TEXT, bd=0,
                                  wrap="word", padx=16, pady=14, spacing1=5,
                                  font=("TkDefaultFont", 10), state="disabled",
                                  insertbackground=TEXT)
        scroll = ttk.Scrollbar(transcript_frame, command=self.transcript.yview)
        self.transcript.configure(yscrollcommand=scroll.set)
        self.transcript.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.transcript.tag_configure("user", foreground="#8bd9ff", font=("TkDefaultFont", 10, "bold"))
        self.transcript.tag_configure("assistant", foreground="#7eeaff", font=("TkDefaultFont", 10, "bold"))
        self.transcript.tag_configure("user_body", background="#0b263c", foreground=TEXT,
                                      lmargin1=12, lmargin2=12, rmargin=12, spacing1=5, spacing3=13)
        self.transcript.tag_configure("assistant_body", background="#0a2033", foreground=TEXT,
                                      lmargin1=12, lmargin2=12, rmargin=12, spacing1=5, spacing3=13)
        self.transcript.tag_configure("time", foreground=MUTED, font=("TkDefaultFont", 8))
        self.transcript.tag_configure("error", foreground="#ff9a9a", font=("TkDefaultFont", 10, "bold"))
        self.transcript.tag_configure("error_body", background="#351b27", foreground="#ffe1e1",
                                      lmargin1=12, lmargin2=12, rmargin=12, spacing1=5, spacing3=13)
        composer = tk.Frame(chat, bg="#0c1a2b")
        composer.pack(fill="x", padx=16, pady=(0, 16))
        transcript_frame.pack(fill="both", expand=True, padx=16, pady=(0, 12))
        self.command_var = tk.StringVar()
        self.voice_button_icon = self._make_voice_icon()
        voice_is_active = self.controller.voice_active
        self.main_voice_button = tk.Button(composer,
                                           text="Pause voice" if voice_is_active else "Start voice",
                                           image=self.voice_button_icon, compound="left",
                                           command=self._toggle_voice,
                                           bg="#a33b48" if voice_is_active else "#087e9c",
                                           fg="#f8feff",
                                           activebackground="#8e2e3a" if voice_is_active else "#066b87",
                                           activeforeground="#ffffff", relief="flat", bd=0,
                                           padx=15, pady=9, font=("TkDefaultFont", 10, "bold"),
                                           cursor="hand2", highlightbackground="#48dfff",
                                           highlightthickness=1)
        self.main_voice_button.pack(side="right", padx=(9, 0))
        tk.Button(composer, text="Send  →", command=self._send_command,
                  bg=ACCENT, fg="#07131b", activebackground="#94f3e8",
                  relief="flat", padx=16, pady=9, font=("TkDefaultFont", 9, "bold"),
                  cursor="hand2").pack(side="right", padx=(9, 0))
        entry = ttk.Entry(composer, textvariable=self.command_var)
        self.command_entry = entry
        entry.pack(side="left", fill="x", expand=True, ipady=4)
        entry.bind("<Return>", lambda _event: self._send_command())
        right = tk.Frame(body, bg=BG)
        right.grid(row=0, column=1, sticky="nsew")
        diag = self._card(right)
        diag.pack(fill="x")
        diag_header = tk.Frame(diag, bg="#0c1a2b")
        diag_header.pack(fill="x", padx=12, pady=(9, 5))
        tk.Label(diag_header, text="SYSTEM STATUS", bg="#0c1a2b", fg="#31d9ff",
                 font=("TkDefaultFont", 9, "bold")).pack(side="left")
        tk.Label(diag_header, text="● LIVE", bg="#0c1a2b", fg="#27e5b0",
                 font=("TkDefaultFont", 8, "bold")).pack(side="right")
        self.diag_labels, self.diag_dots = {}, {}
        service_icons = {"Microphone": "♩", "Internet": "⌁", "Gemini": "✧", "Groq": "◇",
                         "Weather API": "☁", "Speech Output": "◖", "Conversation Memory": "▤",
                         "Conversation store": "▣"}
        grid = tk.Frame(diag, bg="#0c1a2b")
        grid.pack(fill="x", padx=8, pady=(0, 8))
        grid.columnconfigure(0, weight=1, uniform="service")
        grid.columnconfigure(1, weight=1, uniform="service")
        dashboard_services = tuple(AssistantController.diagnostics())[:-1]
        for index, key in enumerate(dashboard_services):
            tile = tk.Frame(grid, bg="#071a2a", highlightbackground="#10314b", highlightthickness=1)
            tile.grid(row=index // 2, column=index % 2, sticky="ew", padx=3, pady=3)
            tk.Label(tile, text=service_icons.get(key, "•"), bg="#071a2a", fg="#72bce8",
                     font=("TkDefaultFont", 10, "bold")).pack(side="left", padx=(7, 5), pady=5)
            tk.Label(tile, text=key.replace(" API", ""), bg="#071a2a", fg="#acd9f2",
                     font=("TkDefaultFont", 8)).pack(side="left", anchor="w")
            dot = tk.Label(tile, text="●", bg="#071a2a", fg="#eab308", font=("TkDefaultFont", 7))
            dot.pack(side="right", padx=(2, 4))
            value = tk.Label(tile, text="Not tested", bg="#071a2a", fg="#eab308",
                             font=("TkDefaultFont", 7, "bold"))
            value.pack(side="right", padx=(0, 5))
            self.diag_labels[key], self.diag_dots[key] = value, dot
        commands_card = self._card(right, "⚡  QUICK ACTIONS")
        commands_card.pack(fill="x", pady=(8, 0))
        actions = (("☁", "Weather", "Forecast", "weather in London"),
                   ("▣", "News", "Headlines", "latest news"),
                   ("▶", "YouTube", "Play music", "play a song by Queen"),
                   ("⌕", "Web Search", "Find anything", "search for artificial intelligence"),
                   ("▦", "Open App", "Launch an app", "open google"),
                   ("▤", "New Chat", "Clear context", "new chat"))
        self.quick_command_buttons = []
        action_grid = tk.Frame(commands_card, bg="#0c1a2b")
        action_grid.pack(fill="x", padx=7, pady=(0, 8))
        for column in range(2):
            action_grid.columnconfigure(column, weight=1, uniform="actions")
        for index, (icon, label, description, prompt) in enumerate(actions):
            button = tk.Button(action_grid, text=f"{icon}  {label}\n{description}", anchor="w",
                               command=lambda value=prompt: self._quick_command(value),
                               bg="#071a2a", fg="#a5dcff", activebackground="#10283d",
                               activeforeground=TEXT, bd=0, padx=7, pady=6,
                               font=("TkDefaultFont", 8, "bold"), cursor="hand2",
                               highlightbackground="#10314b", highlightthickness=1)
            button.grid(row=index // 2, column=index % 2, sticky="ew", padx=3, pady=3)
            self.quick_command_buttons.append(button)
        quick = self._card(right, "◷  RECENT ACTIVITY")
        quick.pack(fill="both", expand=True, pady=(12, 0))
        self.recent_activity = tk.Frame(quick, bg="#0c1a2b")
        self.recent_activity.pack(fill="both", expand=True, padx=15, pady=(0, 10))
        tk.Button(quick, text="View activity history  →", command=lambda: self.show_page("Activity & history"),
                  bg="#0c1a2b", fg=ACCENT, activebackground=PANEL_ALT, activeforeground=TEXT,
                  relief="flat", anchor="w", padx=15, pady=10).pack(fill="x", side="bottom")
        self._render_messages()
        self._refresh_diagnostics(schedule=False)
        self._refresh_recent_activity()
        self._build_voice_dock()

    def _quick_row(self, parent, icon, label, prompt):
        row = tk.Frame(parent, bg="#0c1a2b")
        row.pack(fill="x", padx=12, pady=2)
        button = tk.Button(row, text=f"{icon}   {label}", anchor="w",
                           command=lambda value=prompt: self._quick_command(value),
                           bg="#0c1a2b", fg="#a5dcff", activebackground="#10283d",
                           activeforeground=TEXT, bd=0, padx=5, pady=5,
                           font=("TkDefaultFont", 9), cursor="hand2")
        button.pack(fill="x")
        divider = tk.Frame(parent, bg="#122a3a", height=1)
        divider.pack(fill="x", padx=13)
        return row, divider

    def _quick_command(self, prompt):
        if self.active_page != "Dashboard":
            self.show_page("Dashboard")
        self.command_var.set(prompt)
        self._send_command()

    def _build_voice_dock(self):
        dock = tk.Frame(self.content, bg="#061321", highlightbackground="#07577b", highlightthickness=1)
        dock.pack(fill="x", side="bottom", pady=(8, 0))
        row = tk.Frame(dock, bg="#061321", height=92)
        row.pack(fill="x", padx=18, pady=(5, 0))
        row.pack_propagate(False)
        self.speech_button = tk.Button(row, text="◖))" if config.SPEECH_ENABLED else "◖×",
                                       command=self._toggle_speech, bg="#061321", fg="#83d7ff",
                                       activebackground="#10283d", relief="flat",
                                       font=("TkDefaultFont", 14), width=5, cursor="hand2")
        self.speech_button.pack(side="left")
        tk.Button(row, text="▦", command=self._focus_command, bg="#061321", fg="#83d7ff",
                  activebackground="#10283d", relief="flat", font=("TkDefaultFont", 17),
                  width=4, cursor="hand2").pack(side="right")
        self.waveform = tk.Canvas(row, height=52, bg="#061321", highlightthickness=0)
        self.waveform.pack(side="left", fill="both", expand=True, padx=8)
        self.voice_circle = tk.Canvas(row, width=88, height=88, bg="#061321", highlightthickness=0,
                                      cursor="hand2")
        self.voice_circle.place(relx=0.5, rely=0.5, anchor="center")
        active_outline = "#28f1ff" if self.controller.voice_active else "#00c9ff"
        active_mic = "#bafaff" if self.controller.voice_active else "#66eaff"
        self.voice_circle.create_oval(4, 4, 84, 84, outline="#078dbb", width=2, tags="ring")
        self.voice_circle.create_oval(10, 10, 78, 78, outline=active_outline, width=3, tags="ring")
        self.voice_circle.create_oval(18, 18, 70, 70, fill="#09243a", outline="#124f70", width=2)
        self.voice_circle.create_oval(36, 26, 52, 51, fill=active_mic, outline="#b9f8ff", width=1, tags="mic")
        self.voice_circle.create_arc(28, 34, 60, 64, start=180, extent=180, style="arc",
                                     outline="#66eaff", width=3, tags="mic")
        self.voice_circle.create_line(44, 60, 44, 68, fill="#66eaff", width=3, tags="mic")
        self.voice_circle.create_line(36, 68, 52, 68, fill="#66eaff", width=3, tags="mic")
        self.voice_circle.bind("<Button-1>", lambda _event: self._toggle_voice())
        self.listening_label = tk.Label(dock, text="SAY ‘JARVIS’ TO BEGIN · MIC READY", bg="#061321", fg="#a8d9ff",
                                        font=("TkDefaultFont", 12, "bold"))
        self.listening_label.pack(pady=(0, 2))
        tk.Label(dock, text='Voice is ready when you are', bg="#061321", fg="#65b9e9",
                 font=("TkDefaultFont", 9)).pack(pady=(0, 7))
        self._animate_waveform()

    def _make_voice_icon(self):
        """Create a small microphone bitmap so the main action has a clear icon."""
        icon = tk.PhotoImage(master=self.root, width=20, height=24)
        color = "#f8feff"
        # Capsule, cradle, stem, and base drawn as crisp pixel blocks.
        for y, left, right in ((2, 9, 11), (3, 8, 12), (4, 7, 13),
                               (5, 7, 13), (6, 7, 13), (7, 7, 13),
                               (8, 7, 13), (9, 7, 13), (10, 8, 12), (11, 9, 11)):
            icon.put(color, to=(left, y, right + 1, y + 1))
        for y in (9, 10, 11, 12):
            icon.put(color, to=(5, y, 7, y + 1))
            icon.put(color, to=(13, y, 15, y + 1))
        icon.put(color, to=(5, 13, 15, 14))
        icon.put(color, to=(9, 14, 11, 19))
        icon.put(color, to=(6, 19, 14, 21))
        return icon

    def _toggle_speech(self):
        settings = config.current_settings()
        settings["speech_enabled"] = not config.SPEECH_ENABLED
        try:
            config.save_settings(settings)
            self.speech_button.configure(text="◖))" if config.SPEECH_ENABLED else "◖×")
            self._refresh_diagnostics(schedule=False)
        except OSError:
            logger.exception("Could not update speech output setting")
            messagebox.showerror("Setting not saved", "Could not update speech output.")

    def _focus_command(self):
        if hasattr(self, "command_entry") and self.command_entry.winfo_exists():
            self.command_entry.focus_set()

    def _animate_waveform(self):
        canvas = getattr(self, "waveform", None)
        if not canvas or not canvas.winfo_exists():
            return
        import math
        width = max(canvas.winfo_width(), 300)
        height = 52
        canvas.delete("all")
        mid = height / 2
        phase = datetime.now().timestamp() * 5
        for x in range(0, width, 7):
            envelope = 0.18 + 0.82 * abs(math.sin(x / max(width, 1) * math.pi))
            wave = abs(math.sin(x * 0.075 + phase)) * envelope
            bar = 4 + wave * 20
            wave_color = "#12c9ff" if self.is_dark else "#374151"
            canvas.create_line(x, mid - bar, x, mid + bar, fill=wave_color, width=2)
        self.wave_animation_id = self.root.after(90, self._animate_waveform)

    def _render_messages(self):
        if not hasattr(self, "transcript") or not self.transcript.winfo_exists():
            return
        self.transcript.configure(state="normal")
        self.transcript.delete("1.0", "end")
        if not self.messages:
            self.transcript.insert("end", "◉  JARVIS  ·  READY\n", "assistant")
            self.transcript.insert("end", "I'm ready when you are. Enter a command below, or tap the microphone to speak.\n\n", "assistant_body")
        else:
            for message in self.messages:
                role = message.get("role", "assistant")
                if role == "user":
                    label, label_tag, body_tag = "●  YOU", "user", "user_body"
                elif role == "error":
                    label, label_tag, body_tag = "⚠  JARVIS · SERVICE ERROR", "error", "error_body"
                else:
                    label = "◉  JARVIS"
                    provider = message.get("provider")
                    if provider:
                        label += f"  ·  {provider.upper()}"
                    label_tag, body_tag = "assistant", "assistant_body"
                self.transcript.insert("end", label + "  ", label_tag)
                self.transcript.insert("end", f"{message.get('time', '')}\n", "time")
                self.transcript.insert("end", message.get("text", "") + "\n", body_tag)
                if message.get("details"):
                    self.transcript.insert("end", message["details"] + "\n", "error_body")
                self.transcript.insert("end", "\n")
        self.transcript.configure(state="disabled")
        self.transcript.see("end")

    def _set_assistant_state(self, state):
        self.assistant_state = state
        labels = {"ready": ("SAY ‘JARVIS’ TO BEGIN · MIC READY", ACCENT),
                  "listening": ("LISTENING · SAY ‘JARVIS’", "#28f1ff"),
                  "processing": ("THINKING", "#93d3ff"),
                  "speaking": ("SPEAKING", "#a99bff"),
                  "error": ("ACTION NEEDS ATTENTION", "#ff8585")}
        if state == "error" and getattr(self, "assistant_error_detail", None) == "microphone":
            labels["error"] = ("MICROPHONE UNAVAILABLE", "#ff8585")
        if state == "processing":
            self.processing_dots = (self.processing_dots + 1) % 4
            label, color = labels[state]
            label += "." * self.processing_dots
            self.root.after(350, lambda: self._set_assistant_state("processing")
                            if self.assistant_state == "processing" else None)
        else:
            label, color = labels.get(state, labels["ready"])
        if hasattr(self, "status_label") and self.status_label.winfo_exists():
            self.status_label.configure(text=label, fg=color)
        if hasattr(self, "listening_label") and self.listening_label.winfo_exists():
            self.listening_label.configure(text=label, fg=color)
        if hasattr(self, "voice_circle") and self.voice_circle.winfo_exists():
            outline = {"listening": "#28f1ff", "processing": "#93d3ff",
                       "speaking": "#a99bff", "error": "#ff8585"}.get(state, "#00c9ff")
            self.voice_circle.itemconfigure("ring", outline=outline)

    def _build_history(self):
        self._header("Records", "Activity & history", "Recent commands, outcomes, and saved AI conversation turns.")
        wrapper = self._card(self.content)
        wrapper.pack(fill="both", expand=True, padx=32, pady=(0, 30))
        toolbar = tk.Frame(wrapper, bg="#0c1a2b")
        toolbar.pack(fill="x", padx=17, pady=15)
        tk.Label(toolbar, text="Recent activity", bg="#0c1a2b", fg=TEXT,
                 font=("TkDefaultFont", 11, "bold")).pack(side="left")
        tk.Button(toolbar, text="Refresh", command=self._populate_history,
                  bg="#10283d", fg=TEXT, relief="flat", padx=12, pady=6).pack(side="right")
        columns = ("time", "kind", "command", "result")
        self.history_tree = ttk.Treeview(wrapper, columns=columns, show="headings", height=10)
        for col, title, width in (("time", "TIME", 170), ("kind", "SOURCE", 100),
                                  ("command", "COMMAND", 250), ("result", "RESULT", 500)):
            self.history_tree.heading(col, text=title)
            self.history_tree.column(col, width=width, anchor="w")
        self.history_tree.pack(fill="both", expand=True, padx=17, pady=(0, 10))
        tk.Label(wrapper, text="Saved AI conversation", bg="#0c1a2b", fg=TEXT,
                 font=("TkDefaultFont", 10, "bold")).pack(anchor="w", padx=17, pady=(5, 7))
        self.saved_conversation = tk.Text(wrapper, height=7, bg="#071321", fg=TEXT,
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
        form = tk.Frame(card, bg="#0c1a2b")
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
            field_label = tk.Frame(form, bg="#0c1a2b")
            field_label.grid(row=row, column=0, sticky="w", pady=10)
            tk.Label(field_label, text=title, bg="#0c1a2b", fg=TEXT,
                     font=("TkDefaultFont", 10, "bold")).pack(anchor="w")
            tk.Label(field_label, text=help_text, bg="#0c1a2b", fg=MUTED,
                     font=("TkDefaultFont", 8)).pack(anchor="w", pady=(3, 0))
            variable = tk.StringVar(value=str(current[key]))
            self.setting_vars[key] = variable
            ttk.Entry(form, textvariable=variable, width=42).grid(row=row, column=1, sticky="ew", padx=(30, 5), pady=17)
        form.columnconfigure(1, weight=1)
        self.speech_enabled_var = tk.BooleanVar(value=current["speech_enabled"])
        ttk.Checkbutton(form, text="Enable spoken responses", variable=self.speech_enabled_var).grid(
            row=len(fields), column=1, sticky="w", padx=(30, 5), pady=(14, 8))
        button_row = tk.Frame(card, bg="#0c1a2b")
        button_row.pack(fill="x", padx=20, pady=(0, 20))
        tk.Button(button_row, text="Save settings", command=self._save_settings,
                  bg=ACCENT, fg="#07131b", activebackground="#94f3e8", relief="flat",
                  padx=17, pady=9, font=("TkDefaultFont", 9, "bold")).pack(side="left")
        tk.Label(button_row, text="API keys are read from your .env file and are never shown here.",
                 bg="#0c1a2b", fg=MUTED, font=("TkDefaultFont", 9)).pack(side="left", padx=18)
        diag = self._card(self.content, "Connected services")
        diag.pack(fill="x", padx=32, pady=(0, 20))
        services = tk.Frame(diag, bg="#0c1a2b")
        services.pack(fill="x", padx=20, pady=(0, 17))
        self.settings_diag_labels = {}
        for idx, (name, state) in enumerate(AssistantController.diagnostics().items()):
            label = tk.Label(services, text=f"{name}   ·   {state}", bg="#0c1a2b", fg=TEXT,
                             font=("TkDefaultFont", 9))
            label.grid(row=idx // 3, column=idx % 3, sticky="w", padx=10, pady=8)
            self.settings_diag_labels[name] = label

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

    @staticmethod
    def _diagnostic_color(value):
        value = value.lower()
        if any(word in value for word in ("unavailable", "no api key", "not configured", "failed", "could not")):
            return "#fb7185"
        if any(word in value for word in ("online", "connected", "active", "listening", "enabled", "available", "ready")):
            return "#27e5b0"
        return "#eab308"

    def _style_diagnostic(self, name, value):
        label = getattr(self, "diag_labels", {}).get(name)
        dot = getattr(self, "diag_dots", {}).get(name)
        color = self._diagnostic_color(value)
        if label and label.winfo_exists():
            label.configure(text=value, fg=color)
        if dot and dot.winfo_exists():
            dot.configure(fg=color)

    def _refresh_diagnostics(self, schedule=True):
        diagnostics = AssistantController.diagnostics()
        for labels, settings_page in (
            (getattr(self, "diag_labels", {}), False),
            (getattr(self, "settings_diag_labels", {}), True),
        ):
            for name, value in diagnostics.items():
                label = labels.get(name)
                if label and label.winfo_exists():
                    if settings_page:
                        label.configure(text=f"{name}   ·   {value}", fg=self._diagnostic_color(value))
                    else:
                        self._style_diagnostic(name, value)
        if schedule:
            self.root.after(5000, self._refresh_diagnostics)

    def _refresh_recent_activity(self):
        if not hasattr(self, "recent_activity") or not self.recent_activity.winfo_exists():
            return
        for child in self.recent_activity.winfo_children():
            child.destroy()
        for entry in self._read_activity()[-4:][::-1]:
            command = entry.get("command", "")
            lowered = command.lower()
            icon = "☁" if "weather" in lowered else "▶" if "play" in lowered else "▣" if "news" in lowered else "⌕" if "search" in lowered else "▤"
            row = tk.Frame(self.recent_activity, bg="#0c1a2b")
            row.pack(fill="x", pady=5)
            tk.Label(row, text=icon, bg="#0c1a2b", fg="#48caff",
                     font=("TkDefaultFont", 12)).pack(side="left", padx=(0, 8))
            tk.Label(row, text=command, bg="#0c1a2b", fg=TEXT,
                     anchor="w", wraplength=170, justify="left",
                     font=("TkDefaultFont", 9, "bold")).pack(side="left", fill="x", expand=True)
            tk.Label(row, text=entry.get("time", "").split("T")[-1][:5], bg="#0c1a2b", fg=MUTED,
                     anchor="e", font=("TkDefaultFont", 8)).pack(side="right")

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
                elif kind == "transcription":
                    self.command_var.set(event.get("text", ""))
                elif kind == "status":
                    if hasattr(self, "listening_label") and self.listening_label.winfo_exists():
                        self.listening_label.configure(text=event.get("text", "Ready").upper())
                    if hasattr(self, "status_label") and self.status_label.winfo_exists() and self.assistant_state not in {"processing", "speaking", "error"}:
                        self.status_label.configure(text=event.get("text", "Ready"))
                    self.sidebar_status.configure(text=f"●  {event.get('text', 'READY').upper()}")
                elif kind == "assistant_state":
                    self.assistant_error_detail = event.get("detail")
                    self._set_assistant_state(event.get("state", "ready"))
                elif kind == "provider":
                    name = event.get("name", "Unavailable")
                    if hasattr(self, "provider_label") and self.provider_label.winfo_exists():
                        self.provider_label.configure(text=(f"{name.upper()} · GROQ FALLBACK" if name == "Gemini" else f"ACTIVE · {name.upper()}"))
                elif kind == "voice":
                    active = event.get("active", False)
                    if hasattr(self, "main_voice_button") and self.main_voice_button.winfo_exists():
                        self.main_voice_button.configure(text="Pause voice" if active else "Start voice",
                                                         bg="#a33b48" if active else "#087e9c",
                                                         activebackground="#8e2e3a" if active else "#066b87")
                    if hasattr(self, "voice_circle") and self.voice_circle.winfo_exists():
                        self.voice_circle.itemconfigure("ring", outline="#28f1ff" if active else "#00c9ff")
                        self.voice_circle.itemconfigure("mic", fill="#bafaff" if active else "#66eaff")
                elif kind == "diagnostic":
                    self._refresh_diagnostics(schedule=False)
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
