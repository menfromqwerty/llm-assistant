"""Часть главного окна LLM Assistant.

Модуль выделен из модульной версии проекта для удобства сопровождения.
"""

from .common import *  # noqa: F401,F403


class ModelManagerMixin:
    @staticmethod
    def _short_model_name(model_name: str, limit: int = 26) -> str:
        """Короткое имя модели для кнопки и заголовка."""
        short = model_name.rsplit("/", 1)[-1] or model_name
        return short if len(short) <= limit else short[:limit - 1] + "…"

    def _model_button_text(self) -> str:
        return f"🧠 {self._short_model_name(self._model_name, 24)}"

    def _runtime_profile_key(
        self,
        server_name: Optional[str] = None,
        model_name: Optional[str] = None,
    ) -> str:
        server = server_name or (self._server_var.get() if hasattr(self, "_server_var") else "")
        model = model_name or getattr(self, "_model_name", "")
        return f"{server}::{model}"

    def _save_active_runtime_profile(self) -> None:
        """Запомнить Context Length и параметры вывода для текущей модели."""
        if not hasattr(self, "_runtime_profiles"):
            return
        try:
            context_window = int(self._context_window_var.get())
            max_tokens = int(self._max_tokens_var.get())
            temperature = float(self._temperature_var.get())
            think = bool(self._think_var.get())
            auto_context = bool(self._auto_context_var.get()) if hasattr(self, "_auto_context_var") else True
        except Exception:
            return
        self._runtime_profiles[self._runtime_profile_key()] = {
            "context_window": context_window,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "think": think,
            "auto_context": auto_context,
        }

    def _restore_runtime_profile(self, apply_recommended: bool = True) -> bool:
        """Восстановить сохранённый профиль пары сервер+модель."""
        profile = self._runtime_profiles.get(self._runtime_profile_key(), {})
        if profile:
            self._context_window_var.set(int(profile.get("context_window", DEFAULT_CONTEXT_WINDOW)))
            self._max_tokens_var.set(int(profile.get("max_tokens", DEFAULT_MAX_TOKENS)))
            self._temperature_var.set(float(profile.get("temperature", 0.3)))
            self._think_var.set(bool(profile.get("think", False)))
            if hasattr(self, "_auto_context_var"):
                self._auto_context_var.set(bool(profile.get("auto_context", True)))
            return True
        if apply_recommended:
            recommended = self._profile_for_model(self._model_name)
            self._temperature_var.set(float(recommended["temperature"]))
            self._max_tokens_var.set(int(recommended["max_tokens"]))
            self._think_var.set(bool(recommended["think"]))
        return False

    def _update_model_ui(self):
        """Обновить модель, параметры и заголовок окна."""
        if hasattr(self, "_model_btn"):
            self._model_btn.config(text=self._model_button_text())
        if hasattr(self, "_temp_label"):
            self._temp_label.config(text=f"{self._temperature_var.get():.1f}")
        if hasattr(self, "_tok_label"):
            self._tok_label.config(text=str(int(self._max_tokens_var.get())))
        if hasattr(self, "_status_model"):
            self._status_model.config(text=self._short_model_name(self._model_name, 30))
        if hasattr(self, "_update_limit_summary"):
            self._update_limit_summary()
        if hasattr(self, "_update_ctx_label"):
            self._update_ctx_label()
        session = f"  [{self._session_name}]" if self._session_name else ""
        self.root.title(
            f"LLM Assistant v2.0.0 — {self._short_model_name(self._model_name, 42)}{session}"
        )

    def _profile_for_model(self, model_name: str) -> Dict[str, object]:
        """Безопасные профили вывода. Context Length задаётся пользователем."""
        name = model_name.lower()
        if model_name == DEFAULT_MODEL_NAME:
            return {"temperature": 0.3, "max_tokens": 8192, "think": False}
        if any(key in name for key in ("deepseek-r1", "qwq", "reasoning")):
            return {"temperature": 0.6, "max_tokens": 16000, "think": True}
        if "qwen3" in name:
            return {"temperature": 0.3, "max_tokens": 16000, "think": False}
        if any(key in name for key in ("coder", "codestral", "starcoder")):
            return {"temperature": 0.2, "max_tokens": 16000, "think": False}
        if any(key in name for key in ("llama", "mistral", "gemma")):
            return {"temperature": 0.5, "max_tokens": 8192, "think": False}
        return {"temperature": 0.3, "max_tokens": 8192, "think": False}

    def _set_model(self, model_name: str, apply_profile: bool = True):
        model_name = model_name.strip()
        if not model_name:
            return
        self._save_active_runtime_profile()
        self._model_name = model_name
        server_name = self._server_var.get() if hasattr(self, "_server_var") else ""
        if server_name:
            self._server_model_selection[server_name] = model_name
        restored = self._restore_runtime_profile(apply_recommended=apply_profile)
        self._save_active_runtime_profile()
        self._update_model_ui()
        suffix = " · восстановлен профиль" if restored else ""
        self._status.config(text=f"🧠 Активная модель: {model_name}{suffix}")
        if hasattr(self, "_update_server_context_badge"):
            self._update_server_context_badge(None, None, model_name)
        if hasattr(self, "_sync_server_context_async"):
            self.root.after(120, lambda: self._sync_server_context_async(announce=False))

    def _request_server_models(self) -> List[str]:
        """Получить модели выбранного сервера, включая Ollama /api/tags."""
        return self._fetch_server_models(
            self._server_var.get(),
            self._server_url,
        )

    def _open_model_switcher(self):
        """Диалог выбора модели с сервера или ручного ввода."""
        win = tk.Toplevel(self.root)
        win.title("🧠 Переключение модели")
        win.geometry("700x540")
        win.minsize(560, 430)
        win.configure(bg=self.C["bg"])
        win.transient(self.root)
        win.grab_set()

        header = tk.Frame(win, bg="#0d1117", pady=12)
        header.pack(fill=tk.X)
        tk.Label(
            header, text="🧠 Выбор языковой модели",
            bg="#0d1117", fg="white", font=("Segoe UI", 14, "bold")
        ).pack()
        tk.Label(
            header,
            text=f"Сервер: {self._server_var.get()}  •  {self._server_url}",
            bg="#0d1117", fg="#8b949e", font=("Segoe UI", 9)
        ).pack(pady=(3, 0))

        active_var = tk.StringVar(value=f"Активная: {self._model_name}")
        tk.Label(
            win, textvariable=active_var, anchor=tk.W,
            bg=self.C["bg"], fg=self.C["gold"], font=("Segoe UI", 10, "bold")
        ).pack(fill=tk.X, padx=14, pady=(12, 4))

        list_frame = tk.Frame(win, bg=self.C["bg"])
        list_frame.pack(fill=tk.BOTH, expand=True, padx=14, pady=4)
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        model_list = tk.Listbox(
            list_frame, bg=self.C["bg2"], fg=self.C["fg"],
            selectbackground=self.C["accent"],
            yscrollcommand=scrollbar.set, font=("Consolas", 10),
            activestyle="none"
        )
        model_list.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=model_list.yview)

        status_var = tk.StringVar(value="Нажмите «Обновить с сервера» для получения списка моделей.")
        tk.Label(
            win, textvariable=status_var, anchor=tk.W,
            bg=self.C["bg"], fg="#888", font=("Segoe UI", 8)
        ).pack(fill=tk.X, padx=14, pady=(2, 6))

        manual = tk.Frame(win, bg=self.C["bg"])
        manual.pack(fill=tk.X, padx=14, pady=(0, 8))
        tk.Label(
            manual, text="Своя модель:", bg=self.C["bg"], fg=self.C["fg"]
        ).pack(side=tk.LEFT)
        manual_entry = tk.Entry(
            manual, bg=self.C["bg3"], fg=self.C["fg"],
            insertbackground="white", relief=tk.FLAT, font=("Consolas", 10)
        )
        manual_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8, ipady=4)
        manual_entry.insert(0, self._model_name)

        apply_profile_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            win,
            text="Автоматически применить рекомендуемые temperature / max_tokens / think",
            variable=apply_profile_var,
            bg=self.C["bg"], fg="#aaa", selectcolor=self.C["bg3"],
            activebackground=self.C["bg"], activeforeground="white"
        ).pack(anchor=tk.W, padx=14, pady=(0, 8))

        def fill_list(models: List[str]):
            model_list.delete(0, tk.END)
            for model in models:
                prefix = "● " if model == self._model_name else "  "
                model_list.insert(tk.END, prefix + model)
            if self._model_name in models:
                index = models.index(self._model_name)
                model_list.selection_set(index)
                model_list.see(index)
            status_var.set(f"Получено моделей: {len(models)}")

        def refresh_models():
            status_var.set("Загрузка списка моделей...")
            refresh_btn.config(state=tk.DISABLED)

            def worker():
                try:
                    models = self._request_server_models()
                    self._available_models = models
                    self.root.after(0, lambda: fill_list(models))
                except Exception as exc:
                    error = str(exc)
                    self.root.after(0, lambda: status_var.set(f"Ошибка: {error}"))
                finally:
                    self.root.after(0, lambda: refresh_btn.config(state=tk.NORMAL))

            threading.Thread(target=worker, daemon=True).start()

        def selected_model() -> str:
            selection = model_list.curselection()
            if selection:
                value = model_list.get(selection[0])
                return value[2:] if value.startswith(("● ", "  ")) else value
            return manual_entry.get().strip()

        def apply_selection(close: bool = True):
            model_name = selected_model() or manual_entry.get().strip()
            if not model_name:
                messagebox.showwarning("Модель", "Введите или выберите имя модели", parent=win)
                return
            self._set_model(model_name, apply_profile=apply_profile_var.get())
            active_var.set(f"Активная: {self._model_name}")
            if close:
                win.destroy()

        def use_default():
            server_name = self._server_var.get()
            models = list(self._available_models)
            if server_name == "LM Studio":
                selected = DEFAULT_MODEL_NAME
                if models and selected not in models:
                    selected = self._preferred_model(server_name, models)
            else:
                selected = self._preferred_model(server_name, models)
            if not selected:
                messagebox.showwarning(
                    "Модель",
                    f"На сервере {server_name} пока нет доступных моделей.",
                    parent=win,
                )
                return
            manual_entry.delete(0, tk.END)
            manual_entry.insert(0, selected)
            self._set_model(selected, apply_profile=True)
            active_var.set(f"Активная: {self._model_name}")
            status_var.set(f"Выбрана модель по умолчанию для {server_name}.")

        buttons = tk.Frame(win, bg=self.C["bg"])
        buttons.pack(fill=tk.X, padx=14, pady=(0, 12))
        refresh_btn = tk.Button(
            buttons, text="🔄 Обновить с сервера", command=refresh_models,
            bg="#2d4a6a", fg="white", relief=tk.FLAT, padx=10, pady=5
        )
        refresh_btn.pack(side=tk.LEFT)
        tk.Button(
            buttons, text="⭐ По умолчанию для сервера", command=use_default,
            bg="#4a4020", fg="white", relief=tk.FLAT, padx=10, pady=5
        ).pack(side=tk.LEFT, padx=6)
        tk.Button(
            buttons, text="✅ Выбрать", command=apply_selection,
            bg=self.C["accent"], fg="white", relief=tk.FLAT, padx=14, pady=5
        ).pack(side=tk.RIGHT)
        tk.Button(
            buttons, text="Отмена", command=win.destroy,
            bg=self.C["bg3"], fg=self.C["fg"], relief=tk.FLAT, padx=12, pady=5
        ).pack(side=tk.RIGHT, padx=6)

        model_list.bind("<Double-Button-1>", lambda event: apply_selection())
        manual_entry.bind("<Return>", lambda event: apply_selection())

        # Если список уже был получен при проверке соединения — показываем сразу.
        if self._available_models:
            fill_list(self._available_models)
        else:
            refresh_models()
