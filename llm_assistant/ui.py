"""Минималистичное однооконное представление LLM Assistant v2.0.0.

Главный экран построен вокруг чата. Файлы, веб, код и настройки открываются
в скрываемой правой панели, а редкие команды собраны в меню ☰.
"""

from .common import *  # noqa: F401,F403


class UIMixin:
    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        self.C = {
            # Industrial Terminal: тёмный фон, бирюзовые органы управления,
            # зелёные состояния и янтарные предупреждения.
            "bg": "#071014",
            "bg2": "#0b171b",
            "bg3": "#102126",
            "panel": "#0a1519",
            "border": "#244047",
            "fg": "#d8eceb",
            "muted": "#77969a",
            "accent": "#20cfc2",
            "accent2": "#147e83",
            # Яркое выделение текста в чате. Цвет намеренно контрастный,
            # чтобы выделение было видно поверх фонов сообщений и кода.
            "selection_bg": "#ffd740",
            "selection_fg": "#101318",
            "user_bg": "#10262a",
            "llm_bg": "#0c2027",
            "sys_bg": "#10251d",
            "code_bg": "#050b0e",
            "code_fg": "#d8c47a",
            "code_hover": "#0e252a",
            "gold": "#ffc857",
            "green": "#4ce0a2",
            "red": "#ff6b6b",
            "cyan": "#38e8ff",
            "free": "#193037",
        }
        self.root.configure(bg=self.C["bg"])
        style.configure("TSash", sashrelief="flat", sashwidth=5, background=self.C["border"])
        style.configure("TNotebook", background=self.C["panel"], borderwidth=0)
        style.configure(
            "TNotebook.Tab",
            background=self.C["bg3"], foreground=self.C["muted"],
            padding=[12, 7], borderwidth=0,
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", self.C["panel"])],
            foreground=[("selected", self.C["fg"])],
        )
        style.configure("TCombobox", fieldbackground=self.C["bg3"], background=self.C["bg3"])
        style.configure("Horizontal.TProgressbar", troughcolor=self.C["bg3"], background=self.C["accent"])
        style.configure("Deck.Horizontal.TProgressbar", troughcolor=self.C["bg3"], background=self.C["green"], thickness=8)

    # ──────────────────────────────────────────────
    # Главное меню и верхняя панель
    # ──────────────────────────────────────────────
    def _create_menu(self):
        """Создать компактное всплывающее меню вместо постоянной строки меню."""
        mb = tk.Menu(self.root, tearoff=0, bg=self.C["bg3"], fg=self.C["fg"])
        self._main_menu = mb

        fm = tk.Menu(mb, tearoff=0)
        fm.add_command(label="📄 Открыть файл", command=self._open_file)
        fm.add_command(label="📦 Открыть ZIP", command=self._open_zip)
        fm.add_command(label="📂 Открыть папку", command=self._open_folder)
        fm.add_separator()
        fm.add_command(label="💾 Сохранить диалог", command=self._save_conversation)
        fm.add_command(label="📤 Экспорт кода", command=self._export_all_code)
        fm.add_separator()
        fm.add_command(label="🚪 Выход", command=self._on_close)
        mb.add_cascade(label="📁 Файл", menu=fm)

        sess = tk.Menu(mb, tearoff=0)
        sess.add_command(label="💾 Сохранить сессию", command=self._save_current_session)
        sess.add_command(label="💾 Сохранить как...", command=self._save_session_as)
        sess.add_command(label="📂 Загрузить сессию...", command=self._load_session_dialog)
        sess.add_separator()
        sess.add_command(label="♻ Новый контекст...", command=self._show_context_menu)
        sess.add_command(label="🆕 Новая чистая сессия", command=self._new_session)
        sess.add_command(label="📋 Список сессий", command=self._list_sessions)
        sess.add_command(label="🗑️ Удалить текущую", command=self._delete_session)
        mb.add_cascade(label="💾 Сессия", menu=sess)

        server = tk.Menu(mb, tearoff=0)
        for name, url in SERVERS.items():
            server.add_radiobutton(
                label=f"{name}  ({url})", variable=self._server_var, value=name,
                command=lambda n=name: self._select_server(n),
            )
        server.add_separator()
        server.add_command(label="🔧 Свой URL...", command=self._custom_server)
        server.add_command(label="🔄 Проверить соединение", command=self._check_connection)
        server.add_command(label="▶ Запустить выбранный сервер", command=self._start_selected_server)
        mb.add_cascade(label="🖥️ Сервер", menu=server)

        tools = tk.Menu(mb, tearoff=0)
        tools.add_command(label="🔍 Поиск", command=lambda: self._show_right_tab("web"))
        tools.add_command(label="🌐 URL→Текст", command=self._fetch_url_dialog)
        tools.add_command(label="🔑 API ключи", command=self._open_api_settings)
        tools.add_command(label="⚡ Извлечь код", command=self._extract_all_code)
        tools.add_command(label="📊 Статистика", command=self._show_stats)
        tools.add_command(label="🗑️ Очистить чат", command=self._clear_chat)
        mb.add_cascade(label="🧰 Инструменты", menu=tools)

        templates = tk.Menu(mb, tearoff=0)
        for label in TEMPLATES:
            templates.add_command(label=label, command=lambda value=label: self._apply_template(value))
        mb.add_cascade(label="📋 Шаблоны", menu=templates)

        language = tk.Menu(mb, tearoff=0)
        for mode in LANGUAGE_PROFILES:
            language.add_radiobutton(
                label=mode, variable=self._language_var, value=mode,
                command=lambda value=mode: self._set_language(value),
            )
        mb.add_cascade(label="🌐 Language", menu=language)

        security = tk.Menu(mb, tearoff=0)
        security.add_command(label="⚙ Настройки защиты...", command=self._open_security_settings)
        security.add_command(label="🔒 Заблокировать сейчас", command=self._security_lock_now)
        mb.add_cascade(label="🔐 Защита", menu=security)

    def _show_main_menu(self):
        x = self._menu_btn.winfo_rootx()
        y = self._menu_btn.winfo_rooty() + self._menu_btn.winfo_height()
        try:
            self._main_menu.tk_popup(x, y)
        finally:
            self._main_menu.grab_release()

    def _flat_button(self, parent, text, command, *, accent=False, width=None):
        return tk.Button(
            parent, text=text, command=command,
            bg=self.C["accent"] if accent else self.C["bg3"],
            fg="white" if accent else self.C["fg"],
            activebackground=self.C["accent2"] if accent else self.C["border"],
            activeforeground="white", relief=tk.FLAT, bd=0,
            padx=10, pady=6, width=width, cursor="hand2",
            font=("Segoe UI", 9, "bold" if accent else "normal"),
        )

    def _create_toolbar(self):
        top = tk.Frame(self.root, bg=self.C["panel"], height=54, highlightthickness=1,
                       highlightbackground=self.C["border"])
        top.pack(fill=tk.X)
        top.pack_propagate(False)
        self._topbar = top

        self._menu_btn = self._flat_button(top, "☰", self._show_main_menu, width=3)
        self._menu_btn.pack(side=tk.LEFT, padx=(8, 4), pady=8)

        tk.Label(
            top, text="LLM Assistant", bg=self.C["panel"], fg=self.C["fg"],
            font=("Segoe UI", 13, "bold"),
        ).pack(side=tk.LEFT, padx=(6, 12))

        self._session_badge = tk.Label(
            top, text=f"Сессия: {self._session_name}", bg=self.C["panel"],
            fg=self.C["muted"], font=("Segoe UI", 9),
        )
        self._session_badge.pack(side=tk.LEFT, padx=(0, 10))

        self._model_btn = tk.Button(
            top, text=self._model_button_text(), command=self._open_model_switcher,
            bg=self.C["bg3"], fg=self.C["fg"], activebackground=self.C["border"],
            activeforeground="white", relief=tk.FLAT, bd=0, padx=12, pady=6,
            cursor="hand2", font=("Segoe UI", 9, "bold"),
        )
        self._model_btn.pack(side=tk.LEFT, padx=4, pady=8)

        self._start_server_btn = tk.Button(
            top, text=self._server_start_button_text(), command=self._start_selected_server,
            bg=self._server_start_button_color(), fg="white",
            activebackground=self.C["green"], activeforeground="white",
            relief=tk.FLAT, bd=0, padx=10, pady=6, cursor="hand2",
            font=("Segoe UI", 9, "bold"),
        )
        self._start_server_btn.pack(side=tk.LEFT, padx=4, pady=8)

        self._deck_toggle_btn = self._flat_button(
            top, "▤", self._toggle_control_deck, width=3
        )
        self._deck_toggle_btn.pack(side=tk.RIGHT, padx=4, pady=8)

        self._settings_btn = self._flat_button(
            top, "⚙", lambda: self._show_right_tab("settings"), width=3
        )
        self._settings_btn.pack(side=tk.RIGHT, padx=(4, 8), pady=8)

        self._context_badge = tk.Label(
            top, text="Контекст: 0%", bg=self.C["panel"], fg=self.C["green"],
            font=("Segoe UI", 9, "bold"), cursor="hand2",
        )
        self._context_badge.pack(side=tk.RIGHT, padx=8)
        self._context_badge.bind("<Button-1>", lambda _e: self._show_right_tab("settings"))

        self._new_top_btn = self._flat_button(top, "＋ Новый чат", self._new_session)
        self._new_top_btn.pack(side=tk.RIGHT, padx=4, pady=8)

    # ──────────────────────────────────────────────
    # Панель быстрого управления — Control Deck
    # ──────────────────────────────────────────────
    @staticmethod
    def _compact_tokens(value: int) -> str:
        value = int(value)
        if value >= 1024:
            number = value / 1024
            return f"{number:.0f}K" if number.is_integer() else f"{number:.1f}K"
        return str(value)

    def _deck_scale(self, parent, *, from_, to, command, resolution=1):
        return tk.Scale(
            parent, from_=from_, to=to, orient=tk.HORIZONTAL,
            showvalue=False, resolution=resolution, command=command,
            bg=self.C["bg2"], fg=self.C["fg"], troughcolor=self.C["bg3"],
            activebackground=self.C["cyan"], highlightthickness=0,
            bd=0, sliderlength=14, sliderrelief=tk.FLAT,
            length=150, cursor="hand2",
        )

    def _deck_card(self, parent, title: str):
        card = tk.Frame(
            parent, bg=self.C["bg2"],
            highlightthickness=1, highlightbackground=self.C["border"],
        )
        head = tk.Frame(card, bg=self.C["bg2"])
        head.pack(fill=tk.X, padx=8, pady=(5, 0))
        tk.Label(
            head, text=title, bg=self.C["bg2"], fg=self.C["muted"],
            font=("Segoe UI", 7, "bold"),
        ).pack(side=tk.LEFT)
        value = tk.Label(
            head, text="—", bg=self.C["bg2"], fg=self.C["cyan"],
            font=("Consolas", 9, "bold"),
        )
        value.pack(side=tk.RIGHT)
        return card, value

    def _create_control_deck(self):
        """Компактные живые настройки прямо на главном экране."""
        deck = tk.Frame(
            self.root, bg=self.C["panel"], height=112,
            highlightthickness=1, highlightbackground=self.C["border"],
        )
        deck.pack(fill=tk.X, after=self._topbar)
        deck.pack_propagate(False)
        self.control_deck = deck

        header = tk.Frame(deck, bg=self.C["panel"], height=28)
        header.pack(fill=tk.X, padx=10, pady=(4, 1))
        header.pack_propagate(False)
        tk.Label(
            header, text="CONTROL DECK", bg=self.C["panel"], fg=self.C["accent"],
            font=("Consolas", 9, "bold"),
        ).pack(side=tk.LEFT)

        self._server_ctx_label = tk.Label(
            header, text="SERVER CTX: ?", bg=self.C["panel"], fg=self.C["muted"],
            font=("Consolas", 8, "bold"),
        )
        self._server_ctx_label.pack(side=tk.LEFT, padx=12)

        self._auto_ctx_check = tk.Checkbutton(
            header, text="AUTO CTX", variable=self._auto_context_var,
            command=self._on_auto_context_toggle,
            bg=self.C["panel"], fg=self.C["green"], selectcolor=self.C["bg3"],
            activebackground=self.C["panel"], activeforeground=self.C["green"],
            font=("Segoe UI", 8, "bold"), cursor="hand2",
        )
        self._auto_ctx_check.pack(side=tk.RIGHT, padx=(6, 2))
        self._flat_button(header, "APPLY", self._deck_apply_server_context, width=6).pack(
            side=tk.RIGHT, padx=2, pady=0
        )
        self._flat_button(header, "↻ SYNC", self._deck_sync_server_context, width=7).pack(
            side=tk.RIGHT, padx=2, pady=0
        )
        self._flat_button(header, "AUTO FIT", self._auto_fit_context, width=8).pack(
            side=tk.RIGHT, padx=2, pady=0
        )

        controls = tk.Frame(deck, bg=self.C["panel"])
        controls.pack(fill=tk.X, padx=10, pady=(1, 4))
        for index in range(5):
            controls.grid_columnconfigure(index, weight=1, uniform="deck")

        # Context Length — дискретные безопасные пресеты.
        ctx_card, self._deck_ctx_value = self._deck_card(controls, "CONTEXT LENGTH")
        ctx_card.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        self._deck_context_scale = self._deck_scale(
            ctx_card, from_=0, to=len(self._context_presets) - 1,
            resolution=1, command=self._on_deck_context_scale,
        )
        self._deck_context_scale.pack(fill=tk.X, padx=7, pady=(1, 5))

        out_card, self._deck_out_value = self._deck_card(controls, "MAX OUTPUT")
        out_card.grid(row=0, column=1, sticky="nsew", padx=4)
        self._deck_output_scale = self._deck_scale(
            out_card, from_=256, to=32768, resolution=256,
            command=self._on_deck_output_scale,
        )
        self._deck_output_scale.pack(fill=tk.X, padx=7, pady=(1, 5))

        temp_card, self._deck_temp_value = self._deck_card(controls, "TEMPERATURE")
        temp_card.grid(row=0, column=2, sticky="nsew", padx=4)
        self._deck_temp_scale = self._deck_scale(
            temp_card, from_=0.0, to=1.5, resolution=0.1,
            command=self._on_deck_temperature_scale,
        )
        self._deck_temp_scale.pack(fill=tk.X, padx=7, pady=(1, 5))

        file_card, self._deck_file_value = self._deck_card(controls, "FILE BUDGET")
        file_card.grid(row=0, column=3, sticky="nsew", padx=4)
        self._deck_file_scale = self._deck_scale(
            file_card, from_=1024, to=131072, resolution=1024,
            command=self._on_deck_file_scale,
        )
        self._deck_file_scale.pack(fill=tk.X, padx=7, pady=(1, 5))

        state_card = tk.Frame(
            controls, bg=self.C["bg2"],
            highlightthickness=1, highlightbackground=self.C["border"],
        )
        state_card.grid(row=0, column=4, sticky="nsew", padx=(4, 0))
        row = tk.Frame(state_card, bg=self.C["bg2"])
        row.pack(fill=tk.X, padx=8, pady=(6, 2))
        tk.Label(row, text="MODEL MODE", bg=self.C["bg2"], fg=self.C["muted"],
                 font=("Segoe UI", 7, "bold")).pack(side=tk.LEFT)
        self._deck_think_check = tk.Checkbutton(
            row, text="THINK", variable=self._think_var,
            command=self._on_generation_limits_changed,
            bg=self.C["bg2"], fg=self.C["gold"], selectcolor=self.C["bg3"],
            activebackground=self.C["bg2"], activeforeground=self.C["gold"],
            font=("Segoe UI", 8, "bold"), cursor="hand2",
        )
        self._deck_think_check.pack(side=tk.RIGHT)
        self._deck_profile_label = tk.Label(
            state_card, text="BALANCED", bg=self.C["bg2"], fg=self.C["green"],
            font=("Consolas", 10, "bold"),
        )
        self._deck_profile_label.pack(anchor=tk.W, padx=8, pady=(1, 0))
        tk.Label(
            state_card, text="click model to change profile", bg=self.C["bg2"],
            fg=self.C["muted"], font=("Segoe UI", 7),
        ).pack(anchor=tk.W, padx=8, pady=(0, 4))

        meter_row = tk.Frame(deck, bg=self.C["panel"], height=24)
        meter_row.pack(fill=tk.X, padx=10, pady=(0, 5))
        meter_row.pack_propagate(False)
        self._context_meter = tk.Canvas(
            meter_row, height=12, bg=self.C["bg3"],
            highlightthickness=1, highlightbackground=self.C["border"],
        )
        self._context_meter.pack(side=tk.LEFT, fill=tk.X, expand=True, pady=5)
        self._context_meter.bind("<Configure>", lambda _e: self._draw_context_meter())
        self._meter_legend = tk.Label(
            meter_row, text="CHAT 0 · FILES 0 · WEB 0 · OUT 0 · FREE 0",
            bg=self.C["panel"], fg=self.C["muted"], font=("Consolas", 7),
        )
        self._meter_legend.pack(side=tk.RIGHT, padx=(10, 0))

        self._deck_sync_guard = False
        for variable in (
            self._context_window_var, self._max_tokens_var,
            self._temperature_var, self._file_context_budget_var,
        ):
            variable.trace_add("write", lambda *_args: self._sync_control_deck())
        self._sync_control_deck()

    def _set_control_deck_visible(self, visible: bool):
        visible = bool(visible)
        if visible:
            if not self.control_deck.winfo_ismapped():
                self.control_deck.pack(fill=tk.X, after=self._topbar)
            self._deck_toggle_btn.config(text="▤")
        else:
            if self.control_deck.winfo_ismapped():
                self.control_deck.pack_forget()
            self._deck_toggle_btn.config(text="▥")
        self._control_deck_visible.set(visible)

    def _toggle_control_deck(self):
        self._set_control_deck_visible(not self.control_deck.winfo_ismapped())

    def _nearest_context_index(self, value: int) -> int:
        return min(
            range(len(self._context_presets)),
            key=lambda index: abs(self._context_presets[index] - int(value)),
        )

    def _on_deck_context_scale(self, value):
        if getattr(self, "_deck_sync_guard", False):
            return
        index = max(0, min(len(self._context_presets) - 1, int(round(float(value)))))
        self._context_window_var.set(self._context_presets[index])
        self._on_generation_limits_changed()

    def _on_deck_output_scale(self, value):
        if getattr(self, "_deck_sync_guard", False):
            return
        self._on_output_scale(value)

    def _on_deck_temperature_scale(self, value):
        if getattr(self, "_deck_sync_guard", False):
            return
        self._on_temperature_scale(value)

    def _on_deck_file_scale(self, value):
        if getattr(self, "_deck_sync_guard", False):
            return
        budget = max(1024, int(float(value) // 1024 * 1024))
        self._file_context_budget_var.set(budget)
        if hasattr(self, "_on_context_settings_changed"):
            self._on_context_settings_changed()

    def _on_auto_context_toggle(self):
        self._deck_profile_label.config(
            text="AUTO ADAPT" if self._auto_context_var.get() else "MANUAL",
            fg=self.C["green"] if self._auto_context_var.get() else self.C["gold"],
        )
        if hasattr(self, "_save_active_runtime_profile"):
            self._save_active_runtime_profile()
        self._autosave_session()

    def _sync_control_deck(self):
        if not hasattr(self, "_deck_context_scale"):
            return
        if getattr(self, "_deck_sync_guard", False):
            return
        self._deck_sync_guard = True
        try:
            window = self._effective_context_window()
            output = max(256, int(self._max_tokens_var.get()))
            temp = round(float(self._temperature_var.get()), 1)
            files = max(1024, int(self._file_context_budget_var.get()))
            self._deck_context_scale.set(self._nearest_context_index(window))
            self._deck_output_scale.set(output)
            self._deck_temp_scale.set(temp)
            self._deck_file_scale.set(files)
            self._deck_ctx_value.config(text=self._compact_tokens(window))
            self._deck_out_value.config(text=self._compact_tokens(output))
            self._deck_temp_value.config(text=f"{temp:.1f}")
            self._deck_file_value.config(text=self._compact_tokens(files))
            if not self._auto_context_var.get():
                self._deck_profile_label.config(text="MANUAL", fg=self.C["gold"])
            elif self._think_var.get():
                self._deck_profile_label.config(text="DEEP THINK", fg=self.C["gold"])
            else:
                self._deck_profile_label.config(text="AUTO ADAPT", fg=self.C["green"])
        finally:
            self._deck_sync_guard = False
        if getattr(self, "_server_context_window", None):
            self._update_server_context_badge(
                self._server_context_window,
                self._server_max_context_window,
                self._server_context_model,
            )
        self._draw_context_meter()

    def _draw_context_meter(self):
        canvas = getattr(self, "_context_meter", None)
        if canvas is None:
            return
        try:
            width = max(1, canvas.winfo_width())
            height = max(1, canvas.winfo_height())
            canvas.delete("all")
            values = self._context_token_breakdown()
            window = self._effective_context_window()
            output = max(256, int(self._max_tokens_var.get()))
            safety = max(512, int(window * 0.03))
            parts = [
                ("chat", values["chat"], self.C["accent"]),
                ("files", values["files"], self.C["green"]),
                ("web", values["web"], self.C["gold"]),
                ("output", output, "#b56cff"),
                ("safety", safety, self.C["red"]),
            ]
            used = sum(value for _name, value, _color in parts)
            free = max(0, window - used)
            x = 0.0
            for _name, value, color in parts:
                segment = width * min(value, window) / max(1, window)
                if segment > 0:
                    canvas.create_rectangle(x, 0, min(width, x + segment), height,
                                            fill=color, outline="")
                x += segment
            if x < width:
                canvas.create_rectangle(x, 0, width, height, fill=self.C["free"], outline="")
            if used > window:
                canvas.create_rectangle(0, 0, width, height, outline=self.C["red"], width=2)
            self._meter_legend.config(
                text=(f"CHAT {self._compact_tokens(values['chat'])} · "
                      f"FILES {self._compact_tokens(values['files'])} · "
                      f"WEB {self._compact_tokens(values['web'])} · "
                      f"OUT {self._compact_tokens(output)} · "
                      f"FREE {self._compact_tokens(free)}")
            )
        except (tk.TclError, AttributeError):
            pass

    def _auto_fit_context_for_prompt(self, prompt: str) -> int:
        tokens = self._context_token_breakdown()
        output = max(256, int(self._max_tokens_var.get()))
        required = tokens["total"] + self._tok(prompt) + output
        target = self._context_presets[-1]
        for preset in self._context_presets:
            safety = max(512, int(preset * 0.05))
            if required + safety <= int(preset * 0.88):
                target = preset
                break
        if target != self._effective_context_window():
            self._context_window_var.set(target)
            self._on_generation_limits_changed()
        return target

    def _auto_fit_context(self):
        tokens = self._context_token_breakdown()
        output = max(256, int(self._max_tokens_var.get()))
        base = tokens["total"] + output
        target = self._context_presets[-1]
        for preset in self._context_presets:
            safety = max(512, int(preset * 0.05))
            if base + safety <= int(preset * 0.88):
                target = preset
                break
        self._context_window_var.set(target)
        # Не разрешаем файлам занять место, предназначенное ответу и истории.
        max_files = max(1024, self._effective_input_budget() - tokens["chat"] - tokens["web"])
        if int(self._file_context_budget_var.get()) > max_files:
            self._file_context_budget_var.set(max_files // 1024 * 1024)
        self._on_generation_limits_changed()
        self._status.config(text=f"AUTO FIT: Context {target:,} · files до {int(self._file_context_budget_var.get()):,}")

    def _deck_sync_server_context(self):
        if hasattr(self, "_sync_server_context_async"):
            self._sync_server_context_async(announce=True)

    def _deck_apply_server_context(self):
        if hasattr(self, "_apply_context_to_server_async"):
            self._apply_context_to_server_async(self._effective_context_window())

    def _update_server_context_badge(self, loaded=None, maximum=None, model=""):
        self._server_context_window = loaded
        self._server_max_context_window = maximum
        self._server_context_model = model or self._model_name
        if not hasattr(self, "_server_ctx_label"):
            return
        if loaded:
            text = f"SERVER CTX: {self._compact_tokens(loaded)}"
            if maximum:
                text += f" / MAX {self._compact_tokens(maximum)}"
            match = loaded == self._effective_context_window()
            self._server_ctx_label.config(
                text=text,
                fg=self.C["green"] if match else self.C["gold"],
            )
        else:
            self._server_ctx_label.config(text="SERVER CTX: ?", fg=self.C["muted"])

    # ──────────────────────────────────────────────
    # Однооконная раскладка
    # ──────────────────────────────────────────────
    def _create_main_layout(self):
        body = tk.Frame(self.root, bg=self.C["bg"])
        body.pack(fill=tk.BOTH, expand=True)
        self._body = body

        self.sidebar = tk.Frame(
            body, bg=self.C["panel"], width=170,
            highlightthickness=1, highlightbackground=self.C["border"],
        )
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)
        self._sidebar_expanded = True
        self._sidebar_buttons = []

        self._sidebar_toggle = self._sidebar_button("◀  Свернуть", self._toggle_sidebar, role="toggle")
        tk.Frame(self.sidebar, bg=self.C["border"], height=1).pack(fill=tk.X, padx=10, pady=4)
        self._new_session_btn = self._sidebar_button("＋  Новый чат", self._new_session, role="new")
        self._sidebar_button("💬  Сессии", self._list_sessions, role="sessions")
        self._sidebar_button("📁  Файлы", lambda: self._show_right_tab("files"), role="files")
        self._sidebar_button("🌐  Поиск", lambda: self._show_right_tab("web"), role="web")
        self._sidebar_button("⚡  Код", lambda: self._show_right_tab("code"), role="code")
        self._reset_context_btn = self._sidebar_button("♻  Контекст", self._show_context_menu, role="context")
        self._clear_all_btn = self._sidebar_button("🧹  Очистить", self._clear_messages_and_searches, role="clear")

        tk.Frame(self.sidebar, bg=self.C["panel"]).pack(fill=tk.BOTH, expand=True)
        self._sidebar_button("⚙  Настройки", lambda: self._show_right_tab("settings"), role="settings")

        self.main_pw = ttk.PanedWindow(body, orient=tk.HORIZONTAL)
        self.main_pw.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.left_pw = ttk.PanedWindow(self.main_pw, orient=tk.VERTICAL)
        self.main_pw.add(self.left_pw, weight=5)

        self.chat_frame = tk.Frame(self.left_pw, bg=self.C["bg"])
        self.input_frame = tk.Frame(self.left_pw, bg=self.C["bg"])
        self.left_pw.add(self.chat_frame, weight=5)
        self.left_pw.add(self.input_frame, weight=1)

        self.right_frame = tk.Frame(
            self.main_pw, bg=self.C["panel"],
            highlightthickness=1, highlightbackground=self.C["border"],
        )
        if self._show_right.get():
            self.main_pw.add(self.right_frame, weight=2)

    def _sidebar_button(self, text, command, role=""):
        button = tk.Button(
            self.sidebar, text=text, command=command, anchor=tk.W,
            bg=self.C["panel"], fg=self.C["muted"],
            activebackground=self.C["bg3"], activeforeground=self.C["fg"],
            relief=tk.FLAT, bd=0, padx=14, pady=9, cursor="hand2",
            font=("Segoe UI", 9),
        )
        button.pack(fill=tk.X, padx=6, pady=1)
        button._full_text = text
        button._icon_text = text.split()[0] if text else "•"
        button._sidebar_role = role
        self._sidebar_buttons.append(button)
        return button

    def _toggle_sidebar(self):
        self._sidebar_expanded = not self._sidebar_expanded
        self.sidebar.config(width=170 if self._sidebar_expanded else 58)
        for button in self._sidebar_buttons:
            if self._sidebar_expanded:
                button.config(text=button._full_text, anchor=tk.W, padx=14)
            else:
                icon = "▶" if button._sidebar_role == "toggle" else button._icon_text
                button.config(text=icon, anchor=tk.CENTER, padx=4)
        if self._sidebar_expanded:
            self._sidebar_toggle.config(text="◀  Свернуть")
        else:
            self._sidebar_toggle.config(text="▶")

    def _right_is_visible(self) -> bool:
        return str(self.right_frame) in {str(item) for item in self.main_pw.panes()}

    def _show_right_tab(self, name: str):
        if not self._right_is_visible():
            self.main_pw.add(self.right_frame, weight=2)
        self._show_right.set(True)
        mapping = {
            "files": getattr(self, "tab_files", None),
            "web": getattr(self, "tab_web", None),
            "code": getattr(self, "tab_code", None),
            "settings": getattr(self, "tab_settings", None),
        }
        tab = mapping.get(name)
        if tab is not None:
            self.nb.select(tab)

    def _hide_right_panel(self):
        if self._right_is_visible():
            self.main_pw.forget(self.right_frame)
        self._show_right.set(False)

    def _create_chat_panel(self):
        header = tk.Frame(self.chat_frame, bg=self.C["bg"], height=42)
        header.pack(fill=tk.X, padx=14, pady=(8, 0))
        header.pack_propagate(False)
        tk.Label(
            header, text="Диалог", bg=self.C["bg"], fg=self.C["fg"],
            font=("Segoe UI", 11, "bold"),
        ).pack(side=tk.LEFT)
        self._ctx_label = tk.Label(
            header, text="Контекст: 0", bg=self.C["bg"], fg=self.C["muted"],
            font=("Segoe UI", 8), cursor="hand2",
        )
        self._ctx_label.pack(side=tk.RIGHT)
        self._ctx_label.bind("<Button-1>", lambda _e: self._show_right_tab("settings"))

        # Небольшой индикатор выделения/копирования. Он появляется только
        # когда пользователь выделил текст мышью или скопировал его.
        self._copy_hint = tk.Label(
            header, text="", bg=self.C["bg"], fg=self.C["selection_bg"],
            font=("Segoe UI", 8, "bold"),
        )

        chat_shell = tk.Frame(
            self.chat_frame, bg=self.C["bg2"],
            highlightthickness=1, highlightbackground=self.C["border"],
        )
        chat_shell.pack(fill=tk.BOTH, expand=True, padx=14, pady=(0, 8))

        self.chat_text = scrolledtext.ScrolledText(
            chat_shell, wrap=tk.WORD, font=("Segoe UI", 10),
            bg=self.C["bg2"], fg=self.C["fg"], insertbackground="white",
            cursor="xterm", state=tk.DISABLED, relief=tk.FLAT, bd=0,
            padx=14, pady=12,
            # exportselection=False сохраняет яркое выделение даже после
            # правого клика и открытия контекстного меню.
            exportselection=False,
            selectbackground=self.C["selection_bg"],
            selectforeground=self.C["selection_fg"],
            inactiveselectbackground=self.C["selection_bg"],
        )
        self.chat_text.pack(fill=tk.BOTH, expand=True)
        self.chat_text.tag_config("user", background=self.C["user_bg"],
                                  foreground=self.C["fg"], font=("Segoe UI", 10, "bold"),
                                  lmargin1=8, lmargin2=8, rmargin=8, spacing1=5, spacing3=10)
        self.chat_text.tag_config("assistant", background=self.C["llm_bg"],
                                  foreground=self.C["fg"], font=("Segoe UI", 10),
                                  lmargin1=8, lmargin2=8, rmargin=8, spacing1=5, spacing3=10)
        self.chat_text.tag_config("system", background=self.C["sys_bg"],
                                  foreground="#b8d7c5", font=("Segoe UI", 9, "italic"),
                                  lmargin1=8, lmargin2=8, rmargin=8, spacing1=4, spacing3=8)
        self.chat_text.tag_config("code", background=self.C["code_bg"],
                                  font=("Consolas", 10), foreground=self.C["code_fg"],
                                  lmargin1=16, lmargin2=16, rmargin=12, spacing1=4, spacing3=4)
        self.chat_text.tag_config("ts", font=("Segoe UI", 8), foreground="#606a7d")

        cm = tk.Menu(self.root, tearoff=0)
        cm.add_command(label="📋 Копировать", command=self._copy_selected)
        cm.add_command(label="📝 Копировать всё", command=self._copy_all)
        cm.add_separator()
        cm.add_command(label="⚡ Извлечь весь код", command=self._extract_all_code)
        cm.add_command(label="💾 Сохранить выделенное", command=self._save_selected)
        cm.add_command(label="📤 Экспорт ответа LLM", command=self._export_last_response)
        self.chat_text.bind("<Button-3>", lambda event: self._popup(cm, event))
        self._install_copy_bindings(self.chat_text, track_selection=True)
        # Теги user/assistant/code имеют собственный фон. Поднимаем системный
        # тег sel над ними, иначе цвет выделения может быть почти не виден.
        self._raise_selection_tag(self.chat_text)

        composer = tk.Frame(
            self.input_frame, bg=self.C["bg3"],
            highlightthickness=1, highlightbackground=self.C["border"],
        )
        composer.pack(fill=tk.BOTH, expand=True, padx=14, pady=(0, 12))

        input_row = tk.Frame(composer, bg=self.C["bg3"])
        input_row.pack(fill=tk.BOTH, expand=True, padx=8, pady=(8, 2))
        self.input_text = scrolledtext.ScrolledText(
            input_row, height=5, font=("Segoe UI", 10), bg=self.C["bg3"],
            fg=self.C["fg"], insertbackground="white", wrap=tk.WORD,
            relief=tk.FLAT, bd=0, padx=8, pady=6,
            selectbackground=self.C["accent2"],
        )
        self.input_text.pack(fill=tk.BOTH, expand=True)

        footer = tk.Frame(composer, bg=self.C["bg3"], height=40)
        footer.pack(fill=tk.X, padx=8, pady=(0, 7))
        footer.pack_propagate(False)

        for text, command in [
            ("📎", self._insert_file_to_input),
            ("📋", self._template_menu),
            ("🧹", self._clear_input),
        ]:
            self._flat_button(footer, text, command, width=3).pack(side=tk.LEFT, padx=(0, 4), pady=3)

        hint = "Enter — отправить / остановить   •   Shift+Enter — новая строка   •   Esc — стоп"
        tk.Label(footer, text=hint, bg=self.C["bg3"], fg=self.C["muted"],
                 font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=6)

        action = tk.Frame(footer, bg=self.C["bg3"], width=148, height=34)
        action.pack(side=tk.RIGHT, pady=2)
        action.pack_propagate(False)

        # Одна кнопка выполняет два действия:
        #   без генерации  → отправляет запрос;
        #   во время вывода → останавливает текущий HTTP-стрим.
        # Поэтому повторное нажатие на ту же кнопку мгновенно превращается
        # в команду Stop, как в современных чат-клиентах.
        self._action_btn = tk.Button(
            action, text="➤ Отправить", command=self._send_or_stop,
            bg=self.C["accent"], fg="white", activebackground=self.C["accent2"],
            activeforeground="white", relief=tk.FLAT, bd=0, cursor="hand2",
            font=("Segoe UI", 9, "bold"),
        )
        self._action_btn.pack(fill=tk.BOTH, expand=True)

        # Совместимость с кодом и расширениями предыдущих версий.
        self._send_btn = self._action_btn
        self._stop_btn = self._action_btn

        im = tk.Menu(self.root, tearoff=0)
        im.add_command(label="📎 Вставить файл как код", command=self._insert_file_to_input)
        im.add_command(label="📁 Вставить все файлы проекта", command=self._insert_all_files_to_input)
        im.add_separator()
        im.add_command(label="🔧 Нормализовать отступы", command=self._normalize_input)
        im.add_command(label="✂️ Обрезать до N токенов", command=self._trim_input_tokens)
        im.add_separator()
        im.add_command(label="📋 Вставить (Ctrl+V)", command=lambda: self.input_text.event_generate("<<Paste>>"))
        im.add_command(label="📝 Копировать всё", command=self._copy_input_all)
        im.add_command(label="🗑️ Очистить", command=self._clear_input)
        self.input_text.bind("<Button-3>", lambda event: self._popup(im, event))
        self.input_text.bind("<Return>", self._on_enter)
        self.input_text.bind("<Shift-Return>", self._on_shift_enter)
        self.input_text.bind("<Escape>", self._on_escape_generation)
        self._install_copy_bindings(self.input_text)
        self._setup_dnd()

    def _raise_selection_tag(self, widget):
        """Сделать системный тег выделения верхним по приоритету.

        В Text фон тегов сообщений и блоков кода может перекрывать стандартное
        выделение ``sel``. Поэтому после создания любого нового тега кода мы
        снова поднимаем ``sel`` наверх.
        """
        try:
            widget.tag_configure(
                tk.SEL,
                background=self.C["selection_bg"],
                foreground=self.C["selection_fg"],
            )
            widget.tag_raise(tk.SEL)
        except tk.TclError:
            pass

    def _selected_widget_text(self, widget) -> str:
        try:
            return widget.get(tk.SEL_FIRST, tk.SEL_LAST)
        except (tk.TclError, AttributeError):
            return ""

    def _set_copy_hint(self, text: str, *, copied: bool = False):
        """Показать компактный индикатор над чатом."""
        if not hasattr(self, "_copy_hint"):
            return
        try:
            self._copy_hint.config(
                text=text,
                fg=self.C["selection_fg"] if copied else self.C["selection_bg"],
                bg=self.C["selection_bg"] if copied else self.C["bg"],
                padx=7 if copied else 0,
                pady=2 if copied else 0,
            )
            if not self._copy_hint.winfo_ismapped():
                self._copy_hint.pack(side=tk.RIGHT, padx=(6, 10))
        except tk.TclError:
            return

    def _hide_copy_hint(self):
        if hasattr(self, "_copy_hint"):
            try:
                self._copy_hint.pack_forget()
                self._copy_hint.config(
                    text="", bg=self.C["bg"], fg=self.C["selection_bg"],
                    padx=0, pady=0,
                )
            except tk.TclError:
                pass

    def _show_copy_toast(self, count: int):
        """Показать яркое всплывающее окно подтверждения копирования."""
        previous = getattr(self, "_copy_toast", None)
        if previous is not None:
            try:
                previous.destroy()
            except tk.TclError:
                pass

        try:
            toast = tk.Toplevel(self.root)
            self._copy_toast = toast
            toast.overrideredirect(True)
            toast.attributes("-topmost", True)
            toast.configure(bg=self.C["selection_bg"], padx=1, pady=1)

            label = tk.Label(
                toast,
                text=f"📋 Скопировано: {count:,} симв.",
                bg=self.C["selection_bg"],
                fg=self.C["selection_fg"],
                font=("Segoe UI", 9, "bold"),
                padx=12, pady=7,
            )
            label.pack()

            self.root.update_idletasks()
            anchor = getattr(self, "chat_text", self.root)
            x = anchor.winfo_rootx() + max(12, anchor.winfo_width() - toast.winfo_reqwidth() - 20)
            y = anchor.winfo_rooty() + max(12, anchor.winfo_height() - toast.winfo_reqheight() - 20)
            toast.geometry(f"+{x}+{y}")

            def close_toast():
                if getattr(self, "_copy_toast", None) is toast:
                    self._copy_toast = None
                try:
                    toast.destroy()
                except tk.TclError:
                    pass

            toast.after(1300, close_toast)
        except tk.TclError:
            self._copy_toast = None

    def _copy_widget_selection(self, widget):
        """Копировать выделение, не снимая яркую подсветку."""
        selected = self._selected_widget_text(widget)
        if not selected:
            if hasattr(self, "_status"):
                self._status.config(text="Сначала выделите текст мышью")
            return "break"

        self.root.clipboard_clear()
        self.root.clipboard_append(selected)
        # update() фиксирует буфер Windows даже если приложение вскоре закроется.
        try:
            self.root.update()
        except tk.TclError:
            pass

        self._raise_selection_tag(widget)
        if widget is getattr(self, "chat_text", None):
            self._set_copy_hint(f"📋 Скопировано: {len(selected):,}", copied=True)
            self._show_copy_toast(len(selected))
            self.root.after(1600, self._refresh_chat_selection_hint)
        if hasattr(self, "_status"):
            self._status.config(text=f"📋 Скопировано {len(selected):,} символов")
        return "break"

    def _select_all_widget_text(self, widget):
        try:
            widget.tag_add(tk.SEL, "1.0", "end-1c")
            widget.mark_set(tk.INSERT, "1.0")
            widget.see("1.0")
            self._raise_selection_tag(widget)
            if widget is getattr(self, "chat_text", None):
                self._refresh_chat_selection_hint()
        except tk.TclError:
            pass
        return "break"

    def _clear_widget_selection(self, widget):
        try:
            widget.tag_remove(tk.SEL, "1.0", tk.END)
        except tk.TclError:
            pass
        if widget is getattr(self, "chat_text", None):
            self._hide_copy_hint()
        return "break"

    def _refresh_chat_selection_hint(self):
        """Обновить подсказку после выделения текста мышью."""
        widget = getattr(self, "chat_text", None)
        if widget is None:
            return
        self._raise_selection_tag(widget)
        selected = self._selected_widget_text(widget)
        if selected:
            self._set_copy_hint(f"Выделено: {len(selected):,} · Ctrl+C")
            if hasattr(self, "_status"):
                self._status.config(text=f"Выделено {len(selected):,} символов · Ctrl+C")
        else:
            self._hide_copy_hint()

    def _on_chat_selection_event(self, _event=None):
        # Стандартный bind класса Text сначала меняет диапазон sel, поэтому
        # считываем его через after_idle. Это сохраняет обычное поведение:
        # протягивание, двойной клик по слову и тройной клик по строке.
        self.root.after_idle(self._refresh_chat_selection_hint)

    def _install_copy_bindings(self, widget, *, track_selection: bool = False):
        """Разрешить выделение мышью, Ctrl+C и яркую подсветку текста."""
        try:
            widget.configure(exportselection=False)
            widget.configure(
                selectbackground=self.C["selection_bg"],
                selectforeground=self.C["selection_fg"],
                inactiveselectbackground=self.C["selection_bg"],
            )
        except tk.TclError:
            # Старые сборки Tk могут не иметь inactiveselectbackground.
            try:
                widget.configure(
                    selectbackground=self.C["selection_bg"],
                    selectforeground=self.C["selection_fg"],
                )
            except tk.TclError:
                pass

        self._raise_selection_tag(widget)
        widget.bind(
            "<Control-c>",
            lambda _event, value=widget: self._copy_widget_selection(value),
            add="+",
        )
        widget.bind(
            "<Control-C>",
            lambda _event, value=widget: self._copy_widget_selection(value),
            add="+",
        )
        widget.bind(
            "<Control-a>",
            lambda _event, value=widget: self._select_all_widget_text(value),
            add="+",
        )
        widget.bind(
            "<Control-A>",
            lambda _event, value=widget: self._select_all_widget_text(value),
            add="+",
        )

        if track_selection:
            widget.bind("<ButtonPress-1>", self._on_chat_selection_event, add="+")
            widget.bind("<B1-Motion>", self._on_chat_selection_event, add="+")
            widget.bind("<ButtonRelease-1>", self._on_chat_selection_event, add="+")
            widget.bind("<Double-Button-1>", self._on_chat_selection_event, add="+")
            widget.bind("<Triple-Button-1>", self._on_chat_selection_event, add="+")
            widget.bind(
                "<Escape>",
                lambda _event, value=widget: self._clear_widget_selection(value),
                add="+",
            )

    def _create_right_notebook(self):
        drawer_head = tk.Frame(self.right_frame, bg=self.C["panel"], height=42)
        drawer_head.pack(fill=tk.X)
        drawer_head.pack_propagate(False)
        tk.Label(drawer_head, text="Панель", bg=self.C["panel"], fg=self.C["fg"],
                 font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, padx=12)
        self._flat_button(drawer_head, "×", self._hide_right_panel, width=3).pack(
            side=tk.RIGHT, padx=6, pady=5
        )

        self.nb = ttk.Notebook(self.right_frame)
        self.nb.pack(fill=tk.BOTH, expand=True)

        self.tab_files = ttk.Frame(self.nb)
        self.nb.add(self.tab_files, text="📁 Файлы")
        self._build_files_tab()

        self.tab_web = ttk.Frame(self.nb)
        self.nb.add(self.tab_web, text="🌐 Веб")
        self._build_web_tab()

        self.tab_code = ttk.Frame(self.nb)
        self.nb.add(self.tab_code, text="⚡ Код")
        self._build_code_tab()

        self.tab_settings = ttk.Frame(self.nb)
        self.nb.add(self.tab_settings, text="⚙ Настройки")
        self._build_settings_tab()

    def _build_files_tab(self):
        hdr = tk.Frame(self.tab_files, bg=self.C["bg"])
        hdr.pack(fill=tk.X, padx=4, pady=4)
        tk.Label(
            hdr, text="📁 Файлы проекта", font=("Segoe UI", 10, "bold"),
            bg=self.C["bg"], fg=self.C["accent"],
        ).pack(side=tk.LEFT)
        tk.Button(
            hdr, text="👁 ПРЕДПРОСМОТР", command=self._preview_context_selection,
            bg="#6f42c1", fg="white", activebackground="#875bd1",
            activeforeground="white", relief=tk.RAISED, bd=2,
            padx=8, pady=3, cursor="hand2", font=("Segoe UI", 8, "bold"),
        ).pack(side=tk.RIGHT)

        # Режим включения файлов в запрос.
        mode_box = tk.LabelFrame(
            self.tab_files, text=" Контекст проекта ",
            bg=self.C["bg2"], fg="#a8d7ff",
            font=("Segoe UI", 9, "bold"), bd=1,
        )
        mode_box.pack(fill=tk.X, padx=4, pady=(0, 4))

        mode_row = tk.Frame(mode_box, bg=self.C["bg2"])
        mode_row.pack(fill=tk.X, padx=5, pady=(4, 2))
        for text, value in [
            ("🧠 Авто", "auto"),
            ("☑ Отмеченные", "selected"),
            ("📚 Весь проект", "all"),
        ]:
            tk.Radiobutton(
                mode_row, text=text, value=value,
                variable=self._context_mode_var,
                command=self._on_context_settings_changed,
                bg=self.C["bg2"], fg=self.C["fg"],
                selectcolor=self.C["bg3"],
                activebackground=self.C["bg2"],
                activeforeground="white",
                font=("Segoe UI", 8),
            ).pack(side=tk.LEFT, padx=3)

        budget_row = tk.Frame(mode_box, bg=self.C["bg2"])
        budget_row.pack(fill=tk.X, padx=5, pady=(2, 5))
        tk.Label(
            budget_row, text="Лимит файлов:", bg=self.C["bg2"],
            fg="#aaa", font=("Segoe UI", 8),
        ).pack(side=tk.LEFT)
        budget_combo = ttk.Combobox(
            budget_row,
            textvariable=self._file_context_budget_var,
            values=(8192, 16384, 24576, 32768, 49152, 65536, 98304, 131072),
            state="readonly", width=9,
        )
        budget_combo.pack(side=tk.LEFT, padx=5)
        budget_combo.bind("<<ComboboxSelected>>", self._on_context_settings_changed)
        tk.Label(
            budget_row, text="токенов", bg=self.C["bg2"], fg="#777",
            font=("Segoe UI", 8),
        ).pack(side=tk.LEFT)
        self._context_selection_label = tk.Label(
            budget_row, text="Отмечено: 0", bg=self.C["bg2"],
            fg=self.C["gold"], font=("Segoe UI", 8, "bold"),
        )
        self._context_selection_label.pack(side=tk.RIGHT)

        # Прогресс токенов.
        tok_row = tk.Frame(self.tab_files, bg=self.C["bg"])
        tok_row.pack(fill=tk.X, padx=4)
        self._file_tok_label = tk.Label(
            tok_row, text="Файлы: 0 токенов", font=("Segoe UI", 8),
            bg=self.C["bg"], fg="#888",
        )
        self._file_tok_label.pack(side=tk.LEFT)
        self._file_tok_bar = ttk.Progressbar(
            tok_row, mode="determinate", maximum=CONTEXT_BUDGET, length=100,
        )
        self._file_tok_bar.pack(side=tk.RIGHT, padx=4)

        # Список файлов: клик по флажку слева включает/исключает файл.
        lf = tk.Frame(self.tab_files, bg=self.C["bg"])
        lf.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        sb = tk.Scrollbar(lf)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.files_lb = tk.Listbox(
            lf, bg=self.C["bg2"], fg=self.C["fg"],
            selectbackground=self.C["accent"], yscrollcommand=sb.set,
            font=("Consolas", 9), exportselection=False,
        )
        self.files_lb.pack(fill=tk.BOTH, expand=True)
        sb.config(command=self.files_lb.yview)
        self.files_lb.bind("<Double-Button-1>", self._on_file_dbl)
        self.files_lb.bind("<Button-1>", self._on_file_list_click, add="+")
        self.files_lb.bind("<space>", self._on_file_list_space)

        select_row = tk.Frame(self.tab_files, bg=self.C["bg"])
        select_row.pack(fill=tk.X, padx=4, pady=(0, 2))
        for text, command in [
            ("☑ Все", self._select_all_context_files),
            ("☐ Снять", self._clear_context_file_selection),
            ("↕ Инвертировать", self._invert_context_file_selection),
        ]:
            tk.Button(
                select_row, text=text, command=command,
                bg="#364152", fg=self.C["fg"], relief=tk.FLAT,
                padx=6, pady=2, cursor="hand2", font=("Segoe UI", 8),
            ).pack(side=tk.LEFT, padx=2)

        br = tk.Frame(self.tab_files, bg=self.C["bg"])
        br.pack(fill=tk.X, padx=4, pady=4)
        for text, cmd in [
            ("📄 Файл", self._open_file),
            ("📦 ZIP", self._open_zip),
            ("📂 Папка", self._open_folder),
            ("💾 Сохранить", self._save_current_file),
            ("❌", self._remove_file),
        ]:
            tk.Button(
                br, text=text, command=cmd,
                bg=self.C["bg3"], fg=self.C["fg"],
                relief=tk.FLAT, padx=6, cursor="hand2",
            ).pack(side=tk.LEFT, padx=2)

    def _build_web_tab(self):
        # ── Строка поиска + источник ──
        top_frame = tk.Frame(self.tab_web, bg=self.C["bg"])
        top_frame.pack(fill=tk.X, padx=4, pady=4)

        # Кнопка выбора источника (индикатор)
        self._src_btn = tk.Button(
            top_frame, text="🔀 Авто", width=10,
            bg="#2a2a3a", fg="#aaaaff",
            relief=tk.FLAT, padx=6, cursor="hand2",
            font=("Segoe UI", 9, "bold"),
            command=self._show_source_picker
        )
        self._src_btn.pack(side=tk.LEFT, padx=(0, 4))

        self._search_entry = tk.Entry(
            top_frame, font=("Segoe UI", 10),
            bg=self.C["bg3"], fg=self.C["fg"],
            insertbackground="white", relief=tk.FLAT
        )
        self._search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4)
        self._search_entry.bind("<Return>", lambda e: self._do_search())

        tk.Button(top_frame, text="🔍", command=self._do_search,
                  bg=self.C["accent"], fg="white", relief=tk.FLAT,
                  padx=10, cursor="hand2",
                  font=("Segoe UI", 10, "bold")).pack(side=tk.RIGHT, padx=(4, 0))

        # Кнопка настройки API
        tk.Button(top_frame, text="🔑", command=self._open_api_settings,
                  bg="#2a3a2a", fg="#88ff88", relief=tk.FLAT,
                  padx=6, cursor="hand2",
                  font=("Segoe UI", 10)).pack(side=tk.RIGHT, padx=2)

        # ── URL строка ──
        ur = tk.Frame(self.tab_web, bg=self.C["bg"])
        ur.pack(fill=tk.X, padx=4, pady=(0, 4))
        self._url_entry = tk.Entry(
            ur, font=("Segoe UI", 9),
            bg=self.C["bg3"], fg="#aaa",
            insertbackground="white", relief=tk.FLAT
        )
        self._url_entry.insert(0, "https://  (вставь URL → Enter для загрузки страницы)")
        self._url_entry.bind("<FocusIn>",
            lambda e: self._url_entry.delete(0, tk.END)
            if self._url_entry.get().startswith("https://  ") else None)
        self._url_entry.bind("<Return>",
            lambda e: self._fetch_url(self._url_entry.get().strip()))
        self._url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=3)
        tk.Button(ur, text="⬇️", command=lambda: self._fetch_url(self._url_entry.get().strip()),
                  bg=self.C["bg3"], fg=self.C["fg"], relief=tk.FLAT,
                  padx=6, cursor="hand2").pack(side=tk.RIGHT, padx=2)

        # ── Статус источника ──
        self._src_status = tk.Label(
            self.tab_web, text="",
            font=("Segoe UI", 8), bg=self.C["bg"], fg="#888",
            anchor=tk.W
        )
        self._src_status.pack(fill=tk.X, padx=8, pady=(0, 2))

        # ── PanedWindow: список результатов / полный текст ──
        web_pw = ttk.PanedWindow(self.tab_web, orient=tk.VERTICAL)
        web_pw.pack(fill=tk.BOTH, expand=True, padx=4, pady=(0, 4))

        top = ttk.Frame(web_pw)
        web_pw.add(top, weight=1)

        lb_frame = tk.Frame(top, bg=self.C["bg"])
        lb_frame.pack(fill=tk.BOTH, expand=True)
        sb2 = tk.Scrollbar(lb_frame)
        sb2.pack(side=tk.RIGHT, fill=tk.Y)
        self._web_lb = tk.Listbox(
            lb_frame, bg=self.C["bg2"], fg=self.C["fg"],
            selectbackground=self.C["accent"],
            yscrollcommand=sb2.set, font=("Segoe UI", 9)
        )
        self._web_lb.pack(fill=tk.BOTH, expand=True)
        sb2.config(command=self._web_lb.yview)
        self._web_lb.bind("<<ListboxSelect>>", self._on_web_select)
        self._web_lb.bind("<Double-Button-1>",  self._fetch_selected_page)

        wb = tk.Frame(top, bg=self.C["bg"])
        wb.pack(fill=tk.X)
        for text, cmd in [
            ("⬇️ Загрузить",  self._fetch_selected_page),
            ("📋 В ввод",     self._web_to_input),
            ("🤖 LLM анализ", self._web_analyze_llm),
            ("🌐 Браузер",    self._open_browser),
        ]:
            tk.Button(wb, text=text, command=cmd,
                      bg=self.C["bg3"], fg=self.C["fg"],
                      relief=tk.FLAT, padx=5, cursor="hand2",
                      font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=2, pady=2)

        bot = ttk.Frame(web_pw)
        web_pw.add(bot, weight=2)

        web_hdr = tk.Frame(bot, bg=self.C["bg"])
        web_hdr.pack(fill=tk.X)
        tk.Label(web_hdr, text="📄 Текст страницы",
                 font=("Segoe UI", 9, "bold"),
                 bg=self.C["bg"], fg=self.C["accent"]).pack(side=tk.LEFT, padx=4, pady=2)
        self._web_tok_label = tk.Label(
            web_hdr, text="",
            font=("Segoe UI", 8), bg=self.C["bg"], fg="#888"
        )
        self._web_tok_label.pack(side=tk.RIGHT, padx=4)

        self._web_text = scrolledtext.ScrolledText(
            bot, font=("Segoe UI", 9), bg=self.C["bg2"],
            fg=self.C["fg"], wrap=tk.WORD, state=tk.DISABLED
        )
        self._web_text.pack(fill=tk.BOTH, expand=True)
        self._install_copy_bindings(self._web_text)

    def _build_code_tab(self):
        hdr = tk.Frame(self.tab_code, bg=self.C["bg"])
        hdr.pack(fill=tk.X, padx=4, pady=4)
        tk.Label(hdr, text="⚡ Code Viewer", font=("Segoe UI", 10, "bold"),
                 bg=self.C["bg"], fg=self.C["accent"]).pack(side=tk.LEFT)
        self._code_tok_label = tk.Label(hdr, text="",
                                        font=("Segoe UI", 8), bg=self.C["bg"], fg="#888")
        self._code_tok_label.pack(side=tk.RIGHT, padx=4)

        # Кнопки
        cb = tk.Frame(self.tab_code, bg=self.C["bg"])
        cb.pack(fill=tk.X, padx=4, pady=(0, 4))
        for text, cmd in [
            ("⚡ Извлечь из чата",   self._extract_all_code),
            ("💾 Сохранить .py",     self._save_code_viewer),
            ("📋 Копировать",        self._copy_code_viewer),
            ("✏️ В поле ввода",      self._code_to_input),
            ("🗑️ Очистить",         self._clear_code_viewer),
        ]:
            tk.Button(cb, text=text, command=cmd,
                      bg=self.C["bg3"], fg=self.C["fg"],
                      relief=tk.FLAT, padx=6, cursor="hand2",
                      font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=2)

        self._code_viewer = scrolledtext.ScrolledText(
            self.tab_code, font=("Consolas", 10),
            bg=self.C["code_bg"], fg=self.C["code_fg"],
            insertbackground="white", wrap=tk.NONE
        )
        self._code_viewer.pack(fill=tk.BOTH, expand=True, padx=4, pady=(0, 4))
        self._install_copy_bindings(self._code_viewer)


    def _build_settings_tab(self):
        canvas = tk.Canvas(self.tab_settings, bg=self.C["panel"], highlightthickness=0)
        scroll = tk.Scrollbar(self.tab_settings, orient=tk.VERTICAL, command=canvas.yview)
        inner = tk.Frame(canvas, bg=self.C["panel"])
        inner.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        window_id = canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(window_id, width=e.width))
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        def section(title):
            box = tk.LabelFrame(
                inner, text=f" {title} ", bg=self.C["bg2"], fg=self.C["fg"],
                font=("Segoe UI", 9, "bold"), bd=1, relief=tk.SOLID,
                highlightbackground=self.C["border"],
            )
            box.pack(fill=tk.X, padx=10, pady=8)
            return box

        connection = section("Сервер и модель")
        row = tk.Frame(connection, bg=self.C["bg2"])
        row.pack(fill=tk.X, padx=8, pady=7)
        tk.Label(row, text="Сервер", bg=self.C["bg2"], fg=self.C["muted"], width=13,
                 anchor=tk.W).pack(side=tk.LEFT)
        server_combo = ttk.Combobox(
            row, textvariable=self._server_var,
            values=tuple(SERVERS) + ("Свой",), state="readonly", width=18,
        )
        server_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        server_combo.bind("<<ComboboxSelected>>", lambda _e: self._select_server(self._server_var.get())
                          if self._server_var.get() in SERVERS else self._custom_server())

        row = tk.Frame(connection, bg=self.C["bg2"])
        row.pack(fill=tk.X, padx=8, pady=(0, 7))
        tk.Label(row, text="Модель", bg=self.C["bg2"], fg=self.C["muted"], width=13,
                 anchor=tk.W).pack(side=tk.LEFT)
        self._flat_button(row, "Выбрать модель", self._open_model_switcher).pack(side=tk.LEFT)
        self._flat_button(row, "Проверить", self._check_connection).pack(side=tk.LEFT, padx=5)

        limits = section("Контекст и длина ответа")
        tk.Label(
            limits,
            text=("Context Length можно менять с главного экрана. AUTO CTX проверяет "
                  "фактическое окно LM Studio/Ollama и применяет выбранное значение."),
            bg=self.C["bg2"], fg=self.C["muted"], justify=tk.LEFT, wraplength=330,
            font=("Segoe UI", 8),
        ).pack(fill=tk.X, padx=8, pady=(7, 4))

        auto_row = tk.Frame(limits, bg=self.C["bg2"])
        auto_row.pack(fill=tk.X, padx=8, pady=(2, 5))
        tk.Checkbutton(
            auto_row, text="AUTO CTX", variable=self._auto_context_var,
            command=self._on_auto_context_toggle,
            bg=self.C["bg2"], fg=self.C["green"], selectcolor=self.C["bg3"],
            activebackground=self.C["bg2"], activeforeground=self.C["green"],
            font=("Segoe UI", 8, "bold"),
        ).pack(side=tk.LEFT)
        self._flat_button(auto_row, "↻ Получить с сервера", self._deck_sync_server_context).pack(
            side=tk.RIGHT, padx=2
        )
        self._flat_button(auto_row, "Применить", self._deck_apply_server_context).pack(
            side=tk.RIGHT, padx=2
        )

        row = tk.Frame(limits, bg=self.C["bg2"])
        row.pack(fill=tk.X, padx=8, pady=5)
        tk.Label(row, text="Context Length", bg=self.C["bg2"], fg=self.C["fg"], width=16,
                 anchor=tk.W).pack(side=tk.LEFT)
        context_combo = ttk.Combobox(
            row, textvariable=self._context_window_var,
            values=(4096, 8192, 16384, 32768, 65536, 98304, 131072, 196608, 262144),
            width=12,
        )
        context_combo.pack(side=tk.LEFT)
        context_combo.bind("<<ComboboxSelected>>", self._on_generation_limits_changed)
        context_combo.bind("<FocusOut>", self._on_generation_limits_changed)

        row = tk.Frame(limits, bg=self.C["bg2"])
        row.pack(fill=tk.X, padx=8, pady=5)
        tk.Label(row, text="Max Output", bg=self.C["bg2"], fg=self.C["fg"], width=16,
                 anchor=tk.W).pack(side=tk.LEFT)
        token_scale = ttk.Scale(
            row, from_=512, to=32768, variable=self._max_tokens_var,
            orient=tk.HORIZONTAL, length=150,
            command=lambda value: self._on_output_scale(value),
        )
        token_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._tok_label = tk.Label(row, text=str(int(self._max_tokens_var.get())),
                                   bg=self.C["bg2"], fg=self.C["gold"], width=7,
                                   font=("Segoe UI", 9, "bold"))
        self._tok_label.pack(side=tk.RIGHT)

        row = tk.Frame(limits, bg=self.C["bg2"])
        row.pack(fill=tk.X, padx=8, pady=5)
        tk.Label(row, text="Температура", bg=self.C["bg2"], fg=self.C["fg"], width=16,
                 anchor=tk.W).pack(side=tk.LEFT)
        temp_scale = ttk.Scale(
            row, from_=0.0, to=1.5, variable=self._temperature_var,
            orient=tk.HORIZONTAL, length=150,
            command=lambda value: self._on_temperature_scale(value),
        )
        temp_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._temp_label = tk.Label(row, text=f"{self._temperature_var.get():.1f}",
                                    bg=self.C["bg2"], fg=self.C["gold"], width=7,
                                    font=("Segoe UI", 9, "bold"))
        self._temp_label.pack(side=tk.RIGHT)

        tk.Checkbutton(
            limits, text="Thinking mode (/think)", variable=self._think_var,
            command=self._on_generation_limits_changed,
            bg=self.C["bg2"], fg=self.C["fg"], selectcolor=self.C["bg3"],
            activebackground=self.C["bg2"], activeforeground=self.C["fg"],
        ).pack(anchor=tk.W, padx=8, pady=(4, 8))

        self._limits_summary = tk.Label(
            limits, text="", bg=self.C["bg2"], fg=self.C["green"],
            justify=tk.LEFT, anchor=tk.W, font=("Consolas", 8),
        )
        self._limits_summary.pack(fill=tk.X, padx=8, pady=(0, 8))

        interface = section("Интерфейс и защита")
        self._language_btn = tk.Button(
            interface, text=self._language_button_text(), command=self._show_language_menu,
            bg=self._language_button_color(), fg="white", relief=tk.FLAT, bd=0,
            padx=10, pady=7, cursor="hand2", font=("Segoe UI", 9, "bold"),
        )
        self._language_btn.pack(fill=tk.X, padx=8, pady=(8, 4))
        self._security_btn = tk.Button(
            interface, text=self._security_button_text(), command=self._open_security_settings,
            bg=self._security_button_color(), fg="white", relief=tk.FLAT, bd=0,
            padx=10, pady=7, cursor="hand2", font=("Segoe UI", 9, "bold"),
        )
        self._security_btn.pack(fill=tk.X, padx=8, pady=4)
        self._flat_button(interface, "📊 Статистика контекста", self._show_stats).pack(
            fill=tk.X, padx=8, pady=4
        )
        self._flat_button(interface, "♻ Новый контекст", self._show_context_menu).pack(
            fill=tk.X, padx=8, pady=(4, 8)
        )

        search = section("Инструменты")
        self._flat_button(search, "🔑 API ключи поиска", self._open_api_settings).pack(
            fill=tk.X, padx=8, pady=(8, 4)
        )
        self._flat_button(search, "⚡ Извлечь код из чата", self._extract_all_code).pack(
            fill=tk.X, padx=8, pady=4
        )
        self._flat_button(search, "💾 Сохранить сессию", self._save_current_session).pack(
            fill=tk.X, padx=8, pady=(4, 8)
        )
        self._update_limit_summary()

    def _on_output_scale(self, value):
        rounded = max(256, int(float(value) // 256 * 256))
        self._max_tokens_var.set(rounded)
        if hasattr(self, "_tok_label"):
            self._tok_label.config(text=str(rounded))
        self._on_generation_limits_changed()

    def _on_temperature_scale(self, value):
        temp = round(float(value), 1)
        self._temperature_var.set(temp)
        if hasattr(self, "_temp_label"):
            self._temp_label.config(text=f"{temp:.1f}")
        if hasattr(self, "_save_active_runtime_profile"):
            self._save_active_runtime_profile()

    def _on_generation_limits_changed(self, _event=None):
        try:
            window = int(self._context_window_var.get())
        except Exception:
            window = CONTEXT_BUDGET
        window = max(2048, min(window, MAX_CONTEXT_TOKENS))
        self._context_window_var.set(window)
        output = max(256, min(int(self._max_tokens_var.get()), max(256, window - 1024)))
        self._max_tokens_var.set(output)
        if hasattr(self, "_tok_label"):
            self._tok_label.config(text=str(output))
        self._update_limit_summary()
        self._update_ctx_label()
        if hasattr(self, "_save_active_runtime_profile"):
            self._save_active_runtime_profile()
        if hasattr(self, "_autosave_session"):
            self._autosave_session()

    def _update_limit_summary(self):
        if not hasattr(self, "_limits_summary"):
            return
        window = self._effective_context_window()
        output = int(self._max_tokens_var.get())
        input_budget = self._effective_input_budget()
        self._limits_summary.config(
            text=(f"Окно сервера:     {window:,}\n"
                  f"Резерв ответа:    {output:,}\n"
                  f"Входной бюджет:   ~{input_budget:,}"),
            fg=self.C["green"] if output < window * 0.5 else self.C["gold"],
        )

    def _create_status_bar(self):
        sf = tk.Frame(self.root, bg=self.C["panel"], height=28,
                      highlightthickness=1, highlightbackground=self.C["border"])
        sf.pack(side=tk.BOTTOM, fill=tk.X)
        sf.pack_propagate(False)

        self._conn_badge = tk.Label(sf, text="● сервер", font=("Segoe UI", 8, "bold"),
                                    bg=self.C["panel"], fg=self.C["muted"], padx=8)
        self._conn_badge.pack(side=tk.LEFT)

        self._status_model = tk.Label(
            sf, text=self._short_model_name(self._model_name, 30),
            bg=self.C["panel"], fg=self.C["muted"], font=("Segoe UI", 8),
        )
        self._status_model.pack(side=tk.LEFT, padx=(4, 10))

        self._status_context = tk.Label(
            sf, text="Контекст 0", bg=self.C["panel"], fg=self.C["muted"],
            font=("Segoe UI", 8), cursor="hand2",
        )
        self._status_context.pack(side=tk.LEFT, padx=6)
        self._status_context.bind("<Button-1>", lambda _e: self._show_right_tab("settings"))

        self._prog = ttk.Progressbar(sf, mode="indeterminate", length=90)
        self._phase_lbl = tk.Label(sf, text="", font=("Segoe UI", 8, "bold"),
                                   bg=self.C["panel"], fg=self.C["accent"])
        self._phase_lbl.pack(side=tk.RIGHT, padx=4)
        self._timer_lbl = tk.Label(sf, text="", font=("Segoe UI", 8),
                                   bg=self.C["panel"], fg=self.C["muted"])
        self._timer_lbl.pack(side=tk.RIGHT, padx=4)

        self._status = tk.Label(sf, text="✅ Готов", bg=self.C["panel"], fg=self.C["fg"],
                                anchor=tk.E, font=("Segoe UI", 8))
        self._status.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=8)

    def _set_phase(self, n: int, total: int, msg: str, spin=False):
        now = time.time()
        if n == 1:
            self._phase_start = now
        elapsed = now - self._phase_start
        self._phase_lbl.config(text=f"[{n}/{total}]")
        self._status.config(text=f" {msg}")
        self._timer_lbl.config(text=f"{elapsed:.1f}s")
        if spin:
            self._prog.config(mode="indeterminate")
            self._prog.pack(side=tk.LEFT, padx=2)
            self._prog.start(10)
        else:
            self._prog.stop()
            self._prog.config(mode="determinate",
                              value=int(n / total * 100), maximum=100)
            self._prog.pack(side=tk.LEFT, padx=2)

    def _clear_phase(self, msg=None):
        self._prog.stop()
        self._prog.pack_forget()
        self._phase_lbl.config(text="")
        self._timer_lbl.config(text="")
        self._status.config(text=msg or self._tr("done"))

    def _set_conn(self, ok: bool, name: str = ""):
        self._conn_badge.config(
            text=f"● {name or self._tr('server')}",
            fg=self.C["green"] if ok else self.C["red"]
        )

    @staticmethod
    def _tok(text: str) -> int:
        return max(1, len(text) // 4)


    def _effective_context_window(self) -> int:
        try:
            value = int(self._context_window_var.get())
        except Exception:
            value = CONTEXT_BUDGET
        return max(2048, min(value, MAX_CONTEXT_TOKENS))

    def _effective_input_budget(self) -> int:
        window = self._effective_context_window()
        output = max(256, int(self._max_tokens_var.get()))
        safety = max(512, int(window * 0.03))
        return max(1000, window - output - safety)

    def _context_token_breakdown(self) -> Dict[str, int]:
        """Вернуть приблизительный активный контекст следующего запроса."""
        active_messages = [
            message for message in self.chat_history
            if message.role in ("user", "assistant")
        ][-20:]
        chat_tok = sum(self._tok(message.content) for message in active_messages)

        all_file_tok = sum(self._file_tokens(name) for name in self.loaded_files)
        selected_file_tok = sum(
            self._file_tokens(name)
            for name in self.loaded_files
            if self._file_context_selected.get(name, False)
        )
        try:
            file_budget = int(self._file_context_budget_var.get())
        except Exception:
            file_budget = 32768
        mode = self._context_mode_var.get()
        if mode == "selected":
            file_tok = min(selected_file_tok, file_budget)
        else:
            file_tok = min(all_file_tok, file_budget)

        web_tok = sum(
            self._tok(result.full_text[:8000])
            for result in self.web_results
            if result.fetched and result.full_text
        )
        total = chat_tok + file_tok + web_tok
        return {
            "chat": chat_tok,
            "files": file_tok,
            "files_all": all_file_tok,
            "files_selected": selected_file_tok,
            "web": web_tok,
            "total": total,
        }

    def _update_ctx_label(self):
        tokens = self._context_token_breakdown()
        input_used = tokens["total"]
        output = max(256, int(self._max_tokens_var.get()))
        window = self._effective_context_window()
        safety = max(512, int(window * 0.03))
        projected = input_used + output + safety
        pct = projected / window * 100 if window else 0

        color = self.C["green"] if pct < 70 else self.C["gold"] if pct < 90 else self.C["red"]
        text = f"Контекст ~{input_used:,} + ответ {output:,} / {window:,} ({pct:.0f}%)"
        self._ctx_label.config(text=text, fg=color)

        if hasattr(self, "_context_badge"):
            self._context_badge.config(text=f"Контекст {pct:.0f}%", fg=color)
        if hasattr(self, "_status_context"):
            self._status_context.config(text=f"Контекст ~{input_used:,}/{window:,}", fg=color)
        if hasattr(self, "_status_model"):
            self._status_model.config(text=self._short_model_name(self._model_name, 30))
        if hasattr(self, "_reset_context_btn"):
            self._reset_context_btn.config(fg=color)
        self._update_limit_summary()
        if hasattr(self, "_draw_context_meter"):
            self._draw_context_meter()

        if pct >= 90 and not self._context_warning_shown:
            self._context_warning_shown = True
            self.root.after(
                50,
                lambda: messagebox.showwarning(
                    "Контекст почти заполнен",
                    f"Оценка входа, ответа и запаса занимает примерно {pct:.0f}% окна.\n\n"
                    "Проверьте Context Length в настройках сервера или начните новый контекст.",
                    parent=self.root,
                ),
            )
        elif pct < 70:
            self._context_warning_shown = False

    def _update_file_tokens(self):
        total = sum(self._file_tokens(name) for name in self.loaded_files)
        selected_names = [
            name for name in self.loaded_files
            if self._file_context_selected.get(name, False)
        ]
        selected_total = sum(self._file_tokens(name) for name in selected_names)
        try:
            budget = int(self._file_context_budget_var.get())
        except Exception:
            budget = 32768
        mode = self._context_mode_var.get()
        active_estimate = min(selected_total if mode == "selected" else total, budget)
        mode_label = self._context_mode_label(mode) if hasattr(self, "_context_mode_label") else self.CONTEXT_MODE_LABELS.get(mode, mode)
        self._file_tok_label.config(
            text=f"Всего ~{total:,} · в запрос до ~{active_estimate:,} ({mode_label})"
        )
        input_budget = self._effective_input_budget()
        self._file_tok_bar.configure(maximum=max(1, input_budget))
        self._file_tok_bar["value"] = min(active_estimate, input_budget)
        if hasattr(self, "_context_selection_label"):
            self._context_selection_label.config(
                text=f"Отмечено: {len(selected_names)} · ~{selected_total:,}"
            )
        self._update_ctx_label()
