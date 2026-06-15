"""Часть главного окна LLM Assistant.

Модуль выделен из модульной версии проекта для удобства сопровождения.
"""

from .common import *

class UIMixin:
    def _setup_styles(self):
        s = ttk.Style()
        s.theme_use("clam")
        self.C = {
            "bg":        "#1e1e1e",
            "bg2":       "#252526",
            "bg3":       "#2d2d30",
            "fg":        "#d4d4d4",
            "accent":    "#007acc",
            "user_bg":   "#2d2d2d",
            "llm_bg":    "#1e3a5f",
            "sys_bg":    "#1e3a2f",
            "code_bg":   "#0d1117",
            "code_fg":   "#ce9178",
            "code_hover":"#1a1a0a",
            "gold":      "#ffd700",
            "green":     "#5cb85c",
            "red":       "#d9534f",
        }
        self.root.configure(bg=self.C["bg"])
        s.configure("TSash", sashrelief="raised", sashwidth=6)
        s.configure("TNotebook",        background=self.C["bg2"])
        s.configure("TNotebook.Tab",    background=self.C["bg3"], foreground=self.C["fg"], padding=[8, 4])
        s.map("TNotebook.Tab",          background=[("selected", self.C["accent"])])

    def _create_menu(self):
        mb = tk.Menu(self.root)
        self._main_menu = mb
        self.root.config(menu=mb)

        fm = tk.Menu(mb, tearoff=0)
        mb.add_cascade(label="📁 Файл", menu=fm)
        fm.add_command(label="📄 Открыть файл",       command=self._open_file)
        fm.add_command(label="📦 Открыть ZIP",         command=self._open_zip)
        fm.add_command(label="📂 Открыть папку",       command=self._open_folder)
        fm.add_separator()
        fm.add_command(label="💾 Сохранить диалог",    command=self._save_conversation)
        fm.add_command(label="📤 Экспорт кода",        command=self._export_all_code)
        fm.add_separator()
        fm.add_command(label="🚪 Выход",               command=self.root.quit)

        sm = tk.Menu(mb, tearoff=0)
        mb.add_cascade(label="🖥️ Сервер", menu=sm)
        for name, url in SERVERS.items():
            sm.add_radiobutton(label=f"{name}  ({url})",
                               variable=self._server_var, value=name,
                               command=lambda n=name: self._select_server(n))
        sm.add_separator()
        sm.add_command(label="🔧 Свой URL...",         command=self._custom_server)
        sm.add_command(label="🔄 Проверить соединение", command=self._check_connection)
        sm.add_command(label="▶ Запустить выбранный сервер", command=self._start_selected_server)

        vm = tk.Menu(mb, tearoff=0)
        mb.add_cascade(label="👁️ Вид", menu=vm)
        vm.add_command(label="📐 Режим: Код",          command=lambda: self._layout_preset("code"))
        vm.add_command(label="📖 Режим: Чтение",       command=lambda: self._layout_preset("read"))
        vm.add_command(label="⚖️ Режим: Стандарт",     command=lambda: self._layout_preset("std"))
        vm.add_separator()
        vm.add_checkbutton(label="📋 Правая панель",   variable=self._show_right,
                           command=self._toggle_right_panel)
        vm.add_separator()
        vm.add_command(label="🗑️ Очистить чат",        command=self._clear_chat)
        vm.add_command(label="📊 Статистика",          command=self._show_stats)

        sess_m = tk.Menu(mb, tearoff=0)
        mb.add_cascade(label="💾 Сессия", menu=sess_m)
        sess_m.add_command(label="💾 Сохранить сессию",      command=self._save_current_session)
        sess_m.add_command(label="💾 Сохранить как...",      command=self._save_session_as)
        sess_m.add_command(label="📂 Загрузить сессию...",   command=self._load_session_dialog)
        sess_m.add_separator()
        sess_m.add_command(label="♻ Новый контекст...",      command=self._show_context_menu)
        sess_m.add_command(label="🆕 Новая чистая сессия", command=self._new_session)
        sess_m.add_separator()
        sess_m.add_command(label="📋 Список сессий",         command=self._list_sessions)
        sess_m.add_command(label="🗑️ Удалить текущую",       command=self._delete_session)

        tm = tk.Menu(mb, tearoff=0)
        mb.add_cascade(label="📋 Шаблоны", menu=tm)
        for label in TEMPLATES:
            tm.add_command(label=label,
                           command=lambda l=label: self._apply_template(l))

        lang_m = tk.Menu(mb, tearoff=0)
        mb.add_cascade(label="🌐 Language", menu=lang_m)
        for mode in LANGUAGE_PROFILES:
            lang_m.add_radiobutton(
                label=mode,
                variable=self._language_var,
                value=mode,
                command=lambda m=mode: self._set_language(m),
            )

    def _create_toolbar(self):
        """Создать две строки управления.

        Верхняя строка содержит основные инструменты и модель.
        Нижняя строка всегда показывает управление сессиями и контекстом.
        """
        toolbar_wrap = tk.Frame(self.root, bg=self.C["bg3"])
        toolbar_wrap.pack(fill=tk.X, padx=0, pady=0)

        tb = tk.Frame(toolbar_wrap, bg=self.C["bg3"], height=48)
        tb.pack(fill=tk.X)
        tb.pack_propagate(False)

        def btn(text, cmd, tip=""):
            b = tk.Button(
                tb, text=text, command=cmd,
                bg=self.C["bg3"], fg=self.C["fg"],
                relief=tk.FLAT, padx=8, pady=4,
                activebackground=self.C["accent"],
                activeforeground="white", cursor="hand2",
                font=("Segoe UI", 9),
            )
            b.pack(side=tk.LEFT, padx=2, pady=4)
            return b

        btn("📄 Файл", self._open_file)
        btn("📦 ZIP", self._open_zip)
        btn("📂 Папка", self._open_folder)

        self._model_btn = tk.Button(
            tb,
            text=self._model_button_text(),
            command=self._open_model_switcher,
            bg="#ff8c00",
            fg="#101010",
            activebackground="#ffb347",
            activeforeground="#000000",
            relief=tk.RAISED,
            bd=2,
            padx=14,
            pady=5,
            cursor="hand2",
            font=("Segoe UI", 10, "bold"),
        )
        self._model_btn.pack(side=tk.LEFT, padx=(10, 6), pady=4)

        self._start_server_btn = tk.Button(
            tb,
            text=self._server_start_button_text(),
            command=self._start_selected_server,
            bg=self._server_start_button_color(),
            fg="white",
            activebackground="#35c47c",
            activeforeground="white",
            relief=tk.RAISED,
            bd=2,
            padx=12,
            pady=5,
            cursor="hand2",
            font=("Segoe UI", 10, "bold"),
        )
        self._start_server_btn.pack(side=tk.LEFT, padx=(2, 6), pady=4)

        tk.Frame(tb, bg="#666", width=2).pack(
            side=tk.LEFT, fill=tk.Y, padx=6, pady=6
        )

        btn("🔍 Поиск", self._quick_search)
        btn("🌐 URL→Текст", self._fetch_url_dialog)
        btn("🔑 API ключи", self._open_api_settings)

        tk.Frame(tb, bg="#444", width=1).pack(
            side=tk.LEFT, fill=tk.Y, padx=6, pady=6
        )

        btn("📋 Шаблоны", self._template_menu)

        self._language_btn = tk.Button(
            tb,
            text=self._language_button_text(),
            command=self._show_language_menu,
            bg=self._language_button_color(),
            fg="white",
            activebackground="#3390ff",
            activeforeground="white",
            relief=tk.RAISED,
            bd=2,
            padx=10,
            pady=4,
            cursor="hand2",
            font=("Segoe UI", 9, "bold"),
        )
        self._language_btn.pack(side=tk.LEFT, padx=(3, 5), pady=4)

        btn("⚡ Извлечь код", self._extract_all_code)
        btn("📊 Токены", self._show_stats)

        right = tk.Frame(tb, bg=self.C["bg3"])
        right.pack(side=tk.RIGHT, padx=8)

        tk.Checkbutton(
            right, text="/think", variable=self._think_var,
            bg=self.C["bg3"], fg="#aaa",
            selectcolor=self.C["bg3"],
            activebackground=self.C["bg3"],
            font=("Segoe UI", 9),
        ).pack(side=tk.RIGHT, padx=4)

        tk.Label(
            right, text="Temp:", bg=self.C["bg3"], fg="#aaa",
            font=("Segoe UI", 9),
        ).pack(side=tk.RIGHT)
        self._temp_label = tk.Label(
            right, text="0.3", bg=self.C["bg3"],
            fg=self.C["gold"], width=3,
            font=("Segoe UI", 9, "bold"),
        )
        self._temp_label.pack(side=tk.RIGHT)
        temp_sl = ttk.Scale(
            right, from_=0.0, to=1.5,
            variable=self._temperature_var, orient=tk.HORIZONTAL,
            length=80,
            command=lambda v: self._temp_label.config(text=f"{float(v):.1f}"),
        )
        temp_sl.pack(side=tk.RIGHT, padx=4)

        tk.Label(
            right, text="Max tokens:", bg=self.C["bg3"], fg="#aaa",
            font=("Segoe UI", 9),
        ).pack(side=tk.RIGHT, padx=(8, 0))
        self._tok_label = tk.Label(
            right, text="8192", bg=self.C["bg3"],
            fg=self.C["gold"], width=6,
            font=("Segoe UI", 9, "bold"),
        )
        self._tok_label.pack(side=tk.RIGHT)
        tok_sl = ttk.Scale(
            right, from_=1000, to=32000,
            variable=self._max_tokens_var, orient=tk.HORIZONTAL,
            length=120,
            command=lambda v: self._tok_label.config(text=str(int(float(v)))),
        )
        tok_sl.pack(side=tk.RIGHT, padx=4)

        session_tb = tk.Frame(toolbar_wrap, bg="#20252b", height=42)
        session_tb.pack(fill=tk.X)
        session_tb.pack_propagate(False)

        tk.Label(
            session_tb, text="РАБОТА:", bg="#20252b", fg="#9aa4ad",
            font=("Segoe UI", 9, "bold"),
        ).pack(side=tk.LEFT, padx=(8, 4))

        tk.Button(
            session_tb, text="💾 СОХРАНИТЬ", command=self._save_current_session,
            bg="#198754", fg="white", activebackground="#20a66a",
            activeforeground="white", relief=tk.RAISED, bd=2,
            padx=11, pady=3, cursor="hand2",
            font=("Segoe UI", 9, "bold"),
        ).pack(side=tk.LEFT, padx=3, pady=4)

        tk.Button(
            session_tb, text="💾 СОХРАНИТЬ КАК...", command=self._save_session_as,
            bg="#326b4b", fg="white", activebackground="#438b63",
            activeforeground="white", relief=tk.FLAT,
            padx=9, pady=4, cursor="hand2",
            font=("Segoe UI", 9),
        ).pack(side=tk.LEFT, padx=3, pady=4)

        tk.Button(
            session_tb, text="📂 ОТКРЫТЬ СЕССИЮ", command=self._load_session_dialog,
            bg="#0d6efd", fg="white", activebackground="#3d8bfd",
            activeforeground="white", relief=tk.RAISED, bd=2,
            padx=11, pady=3, cursor="hand2",
            font=("Segoe UI", 9, "bold"),
        ).pack(side=tk.LEFT, padx=3, pady=4)

        self._reset_context_btn = tk.Button(
            session_tb, text="♻ НОВЫЙ КОНТЕКСТ", command=self._show_context_menu,
            bg="#b43b8f", fg="white", activebackground="#d34eaa",
            activeforeground="white", relief=tk.RAISED, bd=2,
            padx=12, pady=3, cursor="hand2",
            font=("Segoe UI", 9, "bold"),
        )
        self._reset_context_btn.pack(side=tk.LEFT, padx=(8, 3), pady=4)

        self._new_session_btn = tk.Button(
            session_tb, text="🆕 ЧИСТАЯ СЕССИЯ", command=self._new_session,
            bg="#6f42c1", fg="white", activebackground="#8a63d2",
            activeforeground="white", relief=tk.RAISED, bd=2,
            padx=11, pady=3, cursor="hand2",
            font=("Segoe UI", 9, "bold"),
        )
        self._new_session_btn.pack(side=tk.LEFT, padx=3, pady=4)

        self._session_badge = tk.Label(
            session_tb,
            text=f"Сессия: {self._session_name}",
            bg="#20252b", fg="#a8d7ff",
            font=("Segoe UI", 9, "bold"),
        )
        self._session_badge.pack(side=tk.LEFT, padx=8)

        self._context_badge = tk.Label(
            session_tb,
            text="Контекст: 0%",
            bg="#20252b", fg=self.C["green"],
            font=("Segoe UI", 9, "bold"),
        )
        self._context_badge.pack(side=tk.RIGHT, padx=10)

    def _create_main_layout(self):
        self.main_pw = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_pw.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        self.left_pw = ttk.PanedWindow(self.main_pw, orient=tk.VERTICAL)
        self.main_pw.add(self.left_pw, weight=3)

        self.chat_frame  = ttk.Frame(self.left_pw)
        self.input_frame = ttk.Frame(self.left_pw)
        self.left_pw.add(self.chat_frame,  weight=4)
        self.left_pw.add(self.input_frame, weight=1)

        self.right_frame = ttk.Frame(self.main_pw)
        self.main_pw.add(self.right_frame, weight=2)

    def _create_chat_panel(self):
        hdr = tk.Frame(self.chat_frame, bg=self.C["bg"])
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text="💬 Диалог", font=("Segoe UI", 11, "bold"),
                 bg=self.C["bg"], fg=self.C["accent"]).pack(side=tk.LEFT, padx=8, pady=4)
        self._ctx_label = tk.Label(hdr, text="Контекст: 0 / 131 072 токенов",
                                   font=("Segoe UI", 9), bg=self.C["bg"], fg="#888")
        self._ctx_label.pack(side=tk.RIGHT, padx=8)

        self.chat_text = scrolledtext.ScrolledText(
            self.chat_frame, wrap=tk.WORD,
            font=("Consolas", 10), bg=self.C["bg2"],
            fg=self.C["fg"], insertbackground="white", cursor="arrow",
            state=tk.DISABLED
        )
        self.chat_text.pack(fill=tk.BOTH, expand=True, padx=4, pady=(0, 4))

        self.chat_text.tag_config("user",
            background=self.C["user_bg"], font=("Segoe UI", 10, "bold"), spacing3=8)
        self.chat_text.tag_config("assistant",
            background=self.C["llm_bg"], font=("Segoe UI", 10), spacing3=8)
        self.chat_text.tag_config("system",
            background=self.C["sys_bg"], font=("Segoe UI", 9, "italic"), spacing3=6)
        self.chat_text.tag_config("code",
            background=self.C["code_bg"], font=("Consolas", 10),
            foreground=self.C["code_fg"])
        self.chat_text.tag_config("ts",
            font=("Segoe UI", 8), foreground="#555")

        cm = tk.Menu(self.root, tearoff=0)
        cm.add_command(label="📋 Копировать", command=self._copy_selected)
        cm.add_command(label="📝 Копировать всё", command=self._copy_all)
        cm.add_separator()
        cm.add_command(label="⚡ Извлечь весь код", command=self._extract_all_code)
        cm.add_command(label="💾 Сохранить выделенное", command=self._save_selected)
        cm.add_command(label="📤 Экспорт ответа LLM", command=self._export_last_response)
        self.chat_text.bind("<Button-3>", lambda e: self._popup(cm, e))

        inp_hdr = tk.Frame(self.input_frame, bg=self.C["bg"])
        inp_hdr.pack(fill=tk.X)
        tk.Label(inp_hdr, text="✏️ Ввод", font=("Segoe UI", 9),
                 bg=self.C["bg"], fg="#888").pack(side=tk.LEFT, padx=8, pady=2)

        dnd_hint = "🖱️ Перетащи файл сюда  •  " if HAS_DND else ""
        tk.Label(inp_hdr,
                 text=dnd_hint + "Enter=отправить  Shift+Enter=новая строка",
                 font=("Segoe UI", 8), bg=self.C["bg"], fg="#555").pack(side=tk.RIGHT, padx=8)

        inner = tk.Frame(self.input_frame, bg=self.C["bg"])
        inner.pack(fill=tk.BOTH, expand=True, padx=4, pady=(0, 4))

        self.input_text = scrolledtext.ScrolledText(
            inner, font=("Consolas", 10),
            bg=self.C["bg3"], fg=self.C["fg"],
            insertbackground="white", wrap=tk.WORD
        )
        self.input_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._dnd_active = False

        btn_col = tk.Frame(inner, bg=self.C["bg"])
        btn_col.pack(side=tk.RIGHT, fill=tk.Y, padx=(4, 0))

        def tbtn(parent, text, cmd, color=None, tip=""):
            c = color or self.C["accent"]
            b = tk.Button(parent, text=text, command=cmd,
                          bg=c, fg="white", relief=tk.FLAT,
                          padx=6, pady=4, cursor="hand2",
                          font=("Segoe UI", 9, "bold"),
                          activebackground=self.C["accent"])
            b.pack(fill=tk.X, pady=2)
            return b

        tbtn(btn_col, "📤 Отправить",   self._send_message)
        tbtn(btn_col, "📎 Файл→ввод",   self._insert_file_to_input,  color="#2d4a6a")
        tbtn(btn_col, "🔧 Нормализовать",self._normalize_input,        color="#3a3a1e")
        tbtn(btn_col, "🗑️ Очистить",    self._clear_input,            color="#444")
        tbtn(btn_col, "📋 Шаблон",      self._template_menu,          color="#2d4a2d")

        im = tk.Menu(self.root, tearoff=0)
        im.add_command(label="📎 Вставить файл как код",     command=self._insert_file_to_input)
        im.add_command(label="📁 Вставить все файлы проекта",command=self._insert_all_files_to_input)
        im.add_separator()
        im.add_command(label="🔧 Нормализовать отступы",     command=self._normalize_input)
        im.add_command(label="✂️ Обрезать до N токенов",     command=self._trim_input_tokens)
        im.add_separator()
        im.add_command(label="📋 Вставить (Ctrl+V)",         command=lambda: self.input_text.event_generate("<<Paste>>"))
        im.add_command(label="📝 Копировать всё",            command=self._copy_input_all)
        im.add_command(label="🗑️ Очистить",                  command=self._clear_input)
        self.input_text.bind("<Button-3>", lambda e: self._popup(im, e))

        self.input_text.bind("<Return>",       self._on_enter)
        self.input_text.bind("<Shift-Return>", self._on_shift_enter)

        self._setup_dnd()

    def _create_right_notebook(self):
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
        top_frame = tk.Frame(self.tab_web, bg=self.C["bg"])
        top_frame.pack(fill=tk.X, padx=4, pady=4)

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

        tk.Button(top_frame, text="🔑", command=self._open_api_settings,
                  bg="#2a3a2a", fg="#88ff88", relief=tk.FLAT,
                  padx=6, cursor="hand2",
                  font=("Segoe UI", 10)).pack(side=tk.RIGHT, padx=2)

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

        self._src_status = tk.Label(
            self.tab_web, text="",
            font=("Segoe UI", 8), bg=self.C["bg"], fg="#888",
            anchor=tk.W
        )
        self._src_status.pack(fill=tk.X, padx=8, pady=(0, 2))

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

    def _build_code_tab(self):
        hdr = tk.Frame(self.tab_code, bg=self.C["bg"])
        hdr.pack(fill=tk.X, padx=4, pady=4)
        tk.Label(hdr, text="⚡ Code Viewer", font=("Segoe UI", 10, "bold"),
                 bg=self.C["bg"], fg=self.C["accent"]).pack(side=tk.LEFT)
        self._code_tok_label = tk.Label(hdr, text="",
                                        font=("Segoe UI", 8), bg=self.C["bg"], fg="#888")
        self._code_tok_label.pack(side=tk.RIGHT, padx=4)

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

    def _create_status_bar(self):
        sf = tk.Frame(self.root, bg=self.C["bg3"], height=26)
        sf.pack(side=tk.BOTTOM, fill=tk.X)
        sf.pack_propagate(False)

        self._conn_badge = tk.Label(sf, text="● сервер", font=("Segoe UI", 8),
                                    bg=self.C["bg3"], fg="#888", padx=8)
        self._conn_badge.pack(side=tk.RIGHT)

        self._timer_lbl = tk.Label(sf, text="", font=("Segoe UI", 8),
                                   bg=self.C["bg3"], fg="#888")
        self._timer_lbl.pack(side=tk.RIGHT, padx=4)

        self._phase_lbl = tk.Label(sf, text="", font=("Segoe UI", 8, "bold"),
                                   bg=self.C["bg3"], fg=self.C["accent"])
        self._phase_lbl.pack(side=tk.RIGHT, padx=4)

        self._prog = ttk.Progressbar(sf, mode="indeterminate", length=100)

        self._status = tk.Label(sf, text="✅ Готов",
                                bg=self.C["bg3"], fg=self.C["fg"],
                                anchor=tk.W, font=("Segoe UI", 9))
        self._status.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)

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

    def _context_token_breakdown(self) -> Dict[str, int]:
        """Вернуть примерный активный контекст следующего запроса."""
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
        """Обновить счётчики и предупредить о заполнении контекста."""
        tokens = self._context_token_breakdown()
        total = tokens["total"]
        pct = total / CONTEXT_BUDGET * 100 if CONTEXT_BUDGET else 0

        color = (
            self.C["green"]
            if pct < 70
            else self.C["gold"]
            if pct < 85
            else self.C["red"]
        )
        self._ctx_label.config(
            text=(
                f"{self._tr('context_prefix')}~{total:,} / {CONTEXT_BUDGET:,} "
                f"{self._tr('token_word')} ({pct:.0f}%)"
            ),
            fg=color,
        )

        if hasattr(self, "_context_badge"):
            self._context_badge.config(
                text=f"{self._tr('context_prefix')}{pct:.0f}%  (~{total:,})",
                fg=color,
            )

        if hasattr(self, "_reset_context_btn"):
            if pct >= 85:
                self._reset_context_btn.config(bg="#c62828", activebackground="#e53935")
            elif pct >= 70:
                self._reset_context_btn.config(bg="#d97706", activebackground="#f59e0b")
            else:
                self._reset_context_btn.config(bg="#b43b8f", activebackground="#d34eaa")

        if pct >= 85 and not self._context_warning_shown:
            self._context_warning_shown = True
            self.root.after(
                50,
                lambda: messagebox.showwarning(
                    "Контекст почти заполнен",
                    f"Использовано примерно {pct:.0f}% контекста.\n\n"
                    "Сохраните сессию и нажмите «♻ НОВЫЙ КОНТЕКСТ», "
                    "чтобы продолжить работу без переполнения.",
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
        active_estimate = min(
            selected_total if mode == "selected" else total,
            budget,
        )
        mode_label = self._context_mode_label(mode) if hasattr(self, "_context_mode_label") else self.CONTEXT_MODE_LABELS.get(mode, mode)
        pct = active_estimate / CONTEXT_BUDGET * 100 if CONTEXT_BUDGET else 0
        self._file_tok_label.config(
            text=(
                (f"Total / Всего ~{total:,} · request / запрос ≤ ~{active_estimate:,} "
                 if self._ui_language_code() == "bi" else
                 f"Total ~{total:,} · request up to ~{active_estimate:,} "
                 if self._ui_language_code() == "en" else
                 f"Всего ~{total:,} · в запрос до ~{active_estimate:,} ")
                + f"({mode_label})"
            )
        )
        self._file_tok_bar["value"] = min(active_estimate, CONTEXT_BUDGET)
        if hasattr(self, "_context_selection_label"):
            self._context_selection_label.config(
                text=f"{self._tr('selected_prefix')}{len(selected_names)} · ~{selected_total:,}"
            )
        self._update_ctx_label()
