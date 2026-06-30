"""Сохранение сессий и управление контекстом LLM Assistant."""

from .common import *  # noqa: F401,F403


class SessionMixin:
    def _session_safe_name(self, name: str) -> str:
        return re.sub(r"[^\w\-]", "_", name.strip()) or DEFAULT_SESSION

    def _session_path(self, name: str, for_write: bool = False) -> Path:
        """Return the correct plaintext or encrypted path for a session."""
        safe = self._session_safe_name(name)
        encrypted = SESSION_DIR / f"{safe}.llms"
        plaintext = SESSION_DIR / f"{safe}.json"
        if for_write:
            protected = bool(
                hasattr(self, "_security_enabled")
                and self._security_enabled()
            )
            return encrypted if protected else plaintext
        if encrypted.exists():
            return encrypted
        if plaintext.exists():
            return plaintext
        protected = bool(
            hasattr(self, "_security_enabled")
            and self._security_enabled()
        )
        return encrypted if protected else plaintext

    def _session_files(self) -> List[Path]:
        """Return all session containers, deduplicated by session stem."""
        by_stem: Dict[str, Path] = {}
        # Prefer encrypted containers if both variants exist after an interrupted
        # migration. The plaintext copy can then be cleaned up on the next save.
        for path in SESSION_DIR.glob("*.json"):
            by_stem[path.stem] = path
        for path in SESSION_DIR.glob("*.llms"):
            by_stem[path.stem] = path
        return list(by_stem.values())

    def _read_session_data(self, path: Path) -> Dict[str, object]:
        payload = path.read_bytes()
        if path.suffix.lower() == ".llms":
            if not hasattr(self, "_security_decrypt_bytes"):
                raise RuntimeError("Encrypted sessions are not supported")
            payload = self._security_decrypt_bytes(payload, "session")
        data = json.loads(payload.decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Invalid session format")
        return data

    def _update_session_ui(self):
        """Обновить подпись текущей сессии в интерфейсе."""
        if hasattr(self, "_session_badge"):
            self._session_badge.config(text=f"{self._tr('session_prefix')}​{self._session_name}")
        if hasattr(self, "_session_var"):
            self._session_var.set(self._session_name)
        if hasattr(self, "_update_model_ui"):
            self._update_model_ui()
        if hasattr(self, "_sync_control_deck"):
            self._sync_control_deck()
        if hasattr(self, "_set_control_deck_visible") and hasattr(self, "_control_deck_visible"):
            self._set_control_deck_visible(bool(self._control_deck_visible.get()))

    def _save_current_session(self):
        self._save_session(self._session_name)

    def _autosave_session(self):
        """Тихое автосохранение после завершения ответа модели."""
        if not getattr(self, "_autosave_after_response", True):
            return
        try:
            self._save_session(self._session_name, silent=True)
        except Exception as exc:
            if hasattr(self, "_status"):
                self._status.config(text=f"⚠️ Автосохранение не выполнено: {exc}")

    def _save_session(self, name: str, silent: bool = False) -> bool:
        """Сохранить текущую сессию в JSON.

        Сохраняются чат, модель, настройки, файлы проекта, веб-контекст,
        черновик ввода и содержимое просмотрщика кода.
        """
        name = (name or DEFAULT_SESSION).strip()
        tokens = self._context_token_breakdown()

        web_results = [
            {
                "title": result.title,
                "url": result.url,
                "snippet": result.snippet,
                "full_text": result.full_text,
                "fetched": result.fetched,
                "source": result.source,
            }
            for result in self.web_results
        ]

        draft_input = ""
        if hasattr(self, "input_text"):
            draft_input = self.input_text.get("1.0", "end-1c")

        code_viewer = ""
        if hasattr(self, "_code_viewer"):
            code_viewer = self._code_viewer.get("1.0", "end-1c")

        if hasattr(self, "_save_active_runtime_profile"):
            self._save_active_runtime_profile()

        data = {
            "version": 16,
            "name": name,
            "saved_at": datetime.now().isoformat(),
            "estimated_tokens": tokens,
            "model": self._model_name,
            "server_name": self._server_var.get(),
            "server_url": self._server_url,
            "server_model_selection": self._server_model_selection,
            "llama_cpp_settings": self._llama_cpp_settings,
            "context_window": int(
                self._context_window_var.get()
                if hasattr(self, "_context_window_var")
                else DEFAULT_CONTEXT_WINDOW
            ),
            "max_tokens": int(self._max_tokens_var.get()),
            "temperature": round(self._temperature_var.get(), 2),
            "runtime_profiles": getattr(self, "_runtime_profiles", {}),
            "think": self._think_var.get(),
            "auto_context": self._auto_context_var.get() if hasattr(self, "_auto_context_var") else True,
            "control_deck_visible": self._control_deck_visible.get() if hasattr(self, "_control_deck_visible") else True,
            "language_mode": self._language_var.get(),
            "search_source": self._search_source_var.get(),
            "context_mode": self._context_mode_var.get(),
            "file_context_budget": int(self._file_context_budget_var.get()),
            "context_selected_files": [
                file_name
                for file_name in self.loaded_files
                if self._file_context_selected.get(file_name, False)
            ],
            "chat_history": [
                {
                    "role": message.role,
                    "content": message.content,
                    "timestamp": message.timestamp.isoformat(),
                }
                for message in self.chat_history
            ],
            "loaded_files": self.loaded_files,
            "current_project": self.current_project,
            "web_results": web_results,
            "draft_input": draft_input,
            "code_viewer": code_viewer,
        }

        try:
            path = self._session_path(name, for_write=True)
            path.parent.mkdir(parents=True, exist_ok=True)
            serialized = json.dumps(
                data, ensure_ascii=False, indent=2
            ).encode("utf-8")
            if path.suffix.lower() == ".llms":
                serialized = self._security_encrypt_bytes(serialized, "session")
            temp_path = path.with_suffix(path.suffix + ".tmp")
            temp_path.write_bytes(serialized)
            temp_path.replace(path)
            # Remove a stale alternate-format copy only after the new file has
            # been committed successfully.
            alternate = path.with_suffix(
                ".json" if path.suffix.lower() == ".llms" else ".llms"
            )
            alternate.unlink(missing_ok=True)
            try:
                os.chmod(path, 0o600)
            except OSError:
                pass
        except Exception as exc:
            if not silent:
                messagebox.showerror(
                    "Ошибка сохранения",
                    f"Не удалось сохранить сессию:\n{exc}",
                    parent=self.root,
                )
            return False

        self._session_name = name
        self._update_session_ui()
        if not silent and hasattr(self, "_status"):
            self._status.config(
                text=f"💾 Сессия сохранена: {name}  (~{tokens['total']:,} токенов)"
            )
        return True

    def _load_session(self, name: str, silent: bool = False) -> bool:
        """Загрузить сессию из JSON."""
        path = self._session_path(name)
        if not path.exists():
            if not silent:
                messagebox.showwarning(
                    "Сессия не найдена",
                    f"Сессия «{name}» не найдена.",
                    parent=self.root,
                )
            return False

        try:
            data = self._read_session_data(path)
            # Старые версии могли хранить API-ключи в сессии. Они удаляются
            # только из памяти и никогда не возвращаются в новый файл.
            data.pop("api_keys", None)
        except Exception as exc:
            if not silent:
                messagebox.showerror(
                    "Ошибка загрузки",
                    f"Не удалось открыть сессию:\n{exc}",
                    parent=self.root,
                )
            return False

        # Настройки модели и сервера.
        saved_server_name = data.get("server_name", "LM Studio")
        saved_server_url = data.get("server_url", SERVERS["LM Studio"])
        self._server_var.set(saved_server_name)
        # Для известных серверов используем актуальный URL из конфигурации,
        # чтобы старый адрес из сессии не ломал подключение.
        if saved_server_name in SERVERS:
            self._server_url = SERVERS[saved_server_name]
        else:
            self._server_url = str(saved_server_url).rstrip("/")
        saved_server_models = data.get("server_model_selection", {})
        if isinstance(saved_server_models, dict):
            self._server_model_selection.update(
                {
                    str(key): str(value)
                    for key, value in saved_server_models.items()
                    if key and value
                }
            )
        saved_llama_settings = data.get("llama_cpp_settings", {})
        if isinstance(saved_llama_settings, dict):
            self._llama_cpp_settings.update(saved_llama_settings)
        if saved_server_name == "llama.cpp":
            try:
                llama_port = int(self._llama_cpp_settings.get("port", 8080))
            except Exception:
                llama_port = 8080
            self._server_url = f"http://localhost:{llama_port}/v1"
        self._model_name = (
            self._server_model_selection.get(saved_server_name)
            or data.get("model")
            or DEFAULT_MODEL_NAME
        )
        saved_profiles = data.get("runtime_profiles", {})
        if isinstance(saved_profiles, dict):
            self._runtime_profiles = {
                str(key): dict(value)
                for key, value in saved_profiles.items()
                if isinstance(value, dict)
            }
        try:
            context_window = int(data.get("context_window", DEFAULT_CONTEXT_WINDOW))
        except Exception:
            context_window = DEFAULT_CONTEXT_WINDOW
        if hasattr(self, "_context_window_var"):
            self._context_window_var.set(context_window)
        self._max_tokens_var.set(data.get("max_tokens", DEFAULT_MAX_TOKENS))
        self._temperature_var.set(data.get("temperature", 0.3))
        self._think_var.set(data.get("think", False))
        if hasattr(self, "_auto_context_var"):
            self._auto_context_var.set(bool(data.get("auto_context", True)))
        if hasattr(self, "_control_deck_visible"):
            self._control_deck_visible.set(bool(data.get("control_deck_visible", True)))
        if hasattr(self, "_restore_runtime_profile"):
            self._restore_runtime_profile(apply_recommended=False)

        # Секреты намеренно не загружаются из сессий. Старые v12-файлы могут
        # содержать api_keys в открытом виде; приложение их игнорирует.
        self._language_var.set(
            data.get("language_mode", DEFAULT_LANGUAGE_MODE)
            if data.get("language_mode", DEFAULT_LANGUAGE_MODE) in LANGUAGE_PROFILES
            else DEFAULT_LANGUAGE_MODE
        )
        self._search_source_var.set(data.get("search_source", "auto"))
        self._context_mode_var.set(data.get("context_mode", "auto"))
        try:
            saved_budget = int(data.get("file_context_budget", 32768))
        except Exception:
            saved_budget = 32768
        self._file_context_budget_var.set(saved_budget)

        # Чат.
        self.chat_history.clear()
        self.chat_text.config(state=tk.NORMAL)
        self.chat_text.delete("1.0", tk.END)
        self.chat_text.config(state=tk.DISABLED)

        for item in data.get("chat_history", []):
            try:
                timestamp = datetime.fromisoformat(item.get("timestamp", ""))
            except Exception:
                timestamp = datetime.now()
            message = Message(
                item.get("role", "system"),
                item.get("content", ""),
                timestamp,
            )
            self.chat_history.append(message)
            self._render_msg(message.role, message.content, message.timestamp)

        # Файлы проекта.
        loaded_files = data.get("loaded_files", {})
        self.loaded_files = (
            {str(name): str(file_path) for name, file_path in loaded_files.items()}
            if isinstance(loaded_files, dict)
            else {}
        )
        selected_files = set(data.get("context_selected_files", []))
        self._file_context_selected = {
            file_name: file_name in selected_files
            for file_name in self.loaded_files
        }
        self._file_token_cache.clear()
        self._refresh_files_list()
        self.current_project = data.get("current_project")

        # Веб-контекст.
        self.web_results.clear()
        for item in data.get("web_results", []):
            try:
                self.web_results.append(
                    WebResult(
                        title=item.get("title", ""),
                        url=item.get("url", ""),
                        snippet=item.get("snippet", ""),
                        full_text=item.get("full_text", ""),
                        fetched=bool(item.get("fetched", False)),
                        source=item.get("source", "duckduckgo"),
                    )
                )
            except Exception:
                continue
        if hasattr(self, "_refresh_web_list"):
            self._refresh_web_list()
        self._clear_web_preview()

        # Незавершённый текст и Code Viewer.
        if hasattr(self, "input_text"):
            self.input_text.delete("1.0", tk.END)
            self.input_text.insert("1.0", data.get("draft_input", ""))
        if hasattr(self, "_code_viewer"):
            self._code_viewer.delete("1.0", tk.END)
            self._code_viewer.insert("1.0", data.get("code_viewer", ""))

        self._session_name = data.get("name") or name
        if hasattr(self, "_update_server_ui"):
            self._update_server_ui()
        self._update_model_ui()
        self._update_session_ui()
        if hasattr(self, "_update_language_ui"):
            self._update_language_ui()
        self._update_file_tokens()
        self._update_ctx_label()

        if not silent:
            saved_at = data.get("saved_at", "")[:19].replace("T", " ")
            self._status.config(
                text=(
                    f"📂 Загружена сессия «{self._session_name}» · "
                    f"{len(self.chat_history)} сообщений · {saved_at}"
                )
            )
        return True

    def _render_msg(self, role: str, content: str, ts: datetime):
        """Отрисовать сообщение из сессии без повторного добавления в историю."""
        self.chat_text.config(state=tk.NORMAL)
        self.chat_text.insert(tk.END, f"\n[{ts.strftime('%H:%M')}] ", "ts")
        prefix = {
            "user": "👤 Вы:\n",
            "assistant": "🤖 LLM:\n",
        }.get(role, "ℹ️ Система:\n")
        self.chat_text.insert(tk.END, prefix, role)

        if "```" in content:
            parts = content.split("```")
            for index, part in enumerate(parts):
                if index % 2 == 0:
                    self.chat_text.insert(tk.END, part, role)
                else:
                    lines = part.split("\n")
                    code = "\n".join(lines[1:]) if len(lines) > 1 else part
                    self._code_block_counter += 1
                    tag = f"cb_{self._code_block_counter}"
                    self.chat_text.tag_config(
                        tag,
                        background=self.C["code_bg"],
                        font=("Consolas", 10),
                        foreground=self.C["code_fg"],
                    )
                    self._bind_code_tag(tag)
                    self.chat_text.insert(tk.END, f"\n{code}\n", tag)
        else:
            self.chat_text.insert(tk.END, content, role)

        self.chat_text.insert(tk.END, "\n\n")
        self.chat_text.see(tk.END)
        self.chat_text.config(state=tk.DISABLED)

    def _save_session_as(self):
        name = simpledialog.askstring(
            "Сохранить сессию как",
            "Имя сессии:",
            initialvalue=self._session_name,
            parent=self.root,
        )
        if name and name.strip():
            self._save_session(name.strip())

    def _read_session_summary(self, path: Path) -> Dict[str, object]:
        """Безопасно прочитать краткие сведения о сохранённой сессии."""
        try:
            data = self._read_session_data(path)
            tokens = data.get("estimated_tokens", {})
            if isinstance(tokens, dict):
                token_total = int(tokens.get("total", 0))
            else:
                token_total = int(tokens or 0)
            return {
                "name": data.get("name") or path.stem,
                "saved_at": data.get("saved_at", "")[:16].replace("T", " "),
                "messages": len(data.get("chat_history", [])),
                "files": len(data.get("loaded_files", {})),
                "tokens": token_total,
                "path": path,
            }
        except Exception:
            return {
                "name": path.stem,
                "saved_at": datetime.fromtimestamp(path.stat().st_mtime).strftime(
                    "%Y-%m-%d %H:%M"
                ),
                "messages": 0,
                "files": 0,
                "tokens": 0,
                "path": path,
            }

    def _load_session_dialog(self):
        summaries = [
            self._read_session_summary(path)
            for path in sorted(
                self._session_files(),
                key=lambda item: item.stat().st_mtime,
                reverse=True,
            )
        ]
        if not summaries:
            messagebox.showinfo(
                "Сессии",
                "Сохранённых сессий пока нет.",
                parent=self.root,
            )
            return

        win = tk.Toplevel(self.root)
        win.title("📂 Сохранённые сессии")
        win.geometry("760x430")
        win.minsize(660, 360)
        win.configure(bg=self.C["bg"])
        win.transient(self.root)
        win.grab_set()

        tk.Label(
            win,
            text="Сохранённые сессии",
            bg=self.C["bg"],
            fg="white",
            font=("Segoe UI", 14, "bold"),
        ).pack(anchor=tk.W, padx=14, pady=(12, 2))
        tk.Label(
            win,
            text=f"Папка: {SESSION_DIR}",
            bg=self.C["bg"],
            fg="#888",
            font=("Segoe UI", 9),
        ).pack(anchor=tk.W, padx=14, pady=(0, 8))

        columns = ("name", "date", "messages", "files", "tokens")
        tree = ttk.Treeview(win, columns=columns, show="headings", selectmode="browse")
        tree.heading("name", text="Название")
        tree.heading("date", text="Сохранена")
        tree.heading("messages", text="Сообщений")
        tree.heading("files", text="Файлов")
        tree.heading("tokens", text="~Токенов")
        tree.column("name", width=250, anchor=tk.W)
        tree.column("date", width=140, anchor=tk.CENTER)
        tree.column("messages", width=90, anchor=tk.CENTER)
        tree.column("files", width=70, anchor=tk.CENTER)
        tree.column("tokens", width=110, anchor=tk.E)
        tree.pack(fill=tk.BOTH, expand=True, padx=14, pady=4)

        for index, item in enumerate(summaries):
            tree.insert(
                "",
                tk.END,
                iid=str(index),
                values=(
                    item["name"],
                    item["saved_at"],
                    item["messages"],
                    item["files"],
                    f"{item['tokens']:,}",
                ),
            )
        if summaries:
            tree.selection_set("0")
            tree.focus("0")

        def selected_summary() -> Optional[Dict[str, object]]:
            selection = tree.selection()
            if not selection:
                return None
            return summaries[int(selection[0])]

        def do_load():
            item = selected_summary()
            if not item:
                return
            self._save_session(self._session_name, silent=True)
            win.destroy()
            self._load_session(str(item["name"]))

        def do_delete():
            item = selected_summary()
            if not item:
                return
            if not messagebox.askyesno(
                "Удалить сессию",
                f"Удалить сессию «{item['name']}»?",
                parent=win,
            ):
                return
            try:
                Path(item["path"]).unlink(missing_ok=True)
            except Exception as exc:
                messagebox.showerror("Ошибка", str(exc), parent=win)
                return
            index = summaries.index(item)
            summaries.remove(item)
            tree.delete(str(index))
            # Перестроить iid после удаления.
            for row in tree.get_children():
                tree.delete(row)
            for idx, summary in enumerate(summaries):
                tree.insert(
                    "",
                    tk.END,
                    iid=str(idx),
                    values=(
                        summary["name"],
                        summary["saved_at"],
                        summary["messages"],
                        summary["files"],
                        f"{summary['tokens']:,}",
                    ),
                )

        buttons = tk.Frame(win, bg=self.C["bg"])
        buttons.pack(fill=tk.X, padx=14, pady=10)
        tk.Button(
            buttons,
            text="📂 Открыть",
            command=do_load,
            bg="#0d6efd",
            fg="white",
            relief=tk.FLAT,
            padx=16,
            pady=6,
            font=("Segoe UI", 9, "bold"),
        ).pack(side=tk.LEFT, padx=(0, 6))
        tk.Button(
            buttons,
            text="🗑️ Удалить",
            command=do_delete,
            bg="#8b2635",
            fg="white",
            relief=tk.FLAT,
            padx=14,
            pady=6,
        ).pack(side=tk.LEFT, padx=6)
        tk.Button(
            buttons,
            text="Закрыть",
            command=win.destroy,
            bg=self.C["bg3"],
            fg=self.C["fg"],
            relief=tk.FLAT,
            padx=14,
            pady=6,
        ).pack(side=tk.RIGHT)

        tree.bind("<Double-Button-1>", lambda _event: do_load())

    def _show_context_menu(self):
        """Показать варианты освобождения контекста."""
        menu = tk.Menu(
            self.root,
            tearoff=0,
            bg=self.C["bg2"],
            fg=self.C["fg"],
            activebackground=self.C["accent"],
            activeforeground="white",
        )
        menu.add_command(
            label="🧹 Очистить только историю диалога",
            command=lambda: self._reset_context("chat"),
        )
        menu.add_command(
            label="📄 Очистить чат и веб, оставить файлы проекта",
            command=lambda: self._reset_context("keep_files"),
        )
        menu.add_separator()
        menu.add_command(
            label="♻ Полностью новая сессия...",
            command=self._new_session,
        )

        if hasattr(self, "_reset_context_btn"):
            x = self._reset_context_btn.winfo_rootx()
            y = (
                self._reset_context_btn.winfo_rooty()
                + self._reset_context_btn.winfo_height()
            )
        else:
            x = self.root.winfo_pointerx()
            y = self.root.winfo_pointery()
        try:
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    def _continuation_name(self, old_name: str) -> str:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{old_name}_new_{stamp}"

    def _clear_chat_context(self):
        self.chat_history.clear()
        self.chat_text.config(state=tk.NORMAL)
        self.chat_text.delete("1.0", tk.END)
        self.chat_text.config(state=tk.DISABLED)

    def _clear_web_preview(self):
        if hasattr(self, "_web_text"):
            self._web_text.config(state=tk.NORMAL)
            self._web_text.delete("1.0", tk.END)
            self._web_text.config(state=tk.DISABLED)
        if hasattr(self, "_web_tok_label"):
            self._web_tok_label.config(text="")

    def _clear_web_context(self):
        self.web_results.clear()
        if hasattr(self, "_web_lb"):
            self._web_lb.delete(0, tk.END)
        self._clear_web_preview()

    def _clear_messages_and_searches(self):
        """Удалить чат и все результаты веб-поиска из текущей сессии.

        Файлы проекта, выбранный сервер, модель, язык интерфейса и параметры
        генерации остаются без изменений. Очищенное состояние сразу
        сохраняется, поэтому удалённые сообщения не восстановятся после
        перезапуска приложения.
        """
        if self.is_loading:
            code = self._ui_language_code() if hasattr(self, "_ui_language_code") else "ru"
            titles = {
                "ru": "Модель работает",
                "en": "Model is running",
                "bi": "Model / Модель работает",
            }
            messages = {
                "ru": "Сначала дождитесь завершения текущего ответа.",
                "en": "Wait for the current response to finish first.",
                "bi": "Wait for the response / Дождитесь завершения ответа.",
            }
            messagebox.showwarning(
                titles.get(code, titles["ru"]),
                messages.get(code, messages["ru"]),
                parent=self.root,
            )
            return

        code = self._ui_language_code() if hasattr(self, "_ui_language_code") else "ru"
        titles = {
            "ru": "Очистить сообщения и поиск",
            "en": "Clear messages and searches",
            "bi": "Clear / Очистить сообщения и поиск",
        }
        questions = {
            "ru": (
                "Удалить все сообщения чата и все результаты веб-поиска?\n\n"
                "Также будут очищены загруженные тексты веб-страниц и поля поиска.\n"
                "Файлы проекта, модель, сервер и настройки останутся.\n\n"
                "Отменить это действие после сохранения будет нельзя."
            ),
            "en": (
                "Delete all chat messages and all web-search results?\n\n"
                "Loaded page text and search fields will also be cleared.\n"
                "Project files, model, server and settings will remain.\n\n"
                "This cannot be undone after the session is saved."
            ),
            "bi": (
                "Delete all messages and searches / Удалить все сообщения и поиск?\n\n"
                "Web results and page text / Результаты и тексты страниц будут очищены.\n"
                "Project files and settings / Файлы и настройки останутся."
            ),
        }
        if not messagebox.askyesno(
            titles.get(code, titles["ru"]),
            questions.get(code, questions["ru"]),
            parent=self.root,
        ):
            return

        self._clear_chat_context()
        self._clear_web_context()

        # Очистить введённые поисковые адреса и запросы, но не черновик чата.
        if hasattr(self, "_search_entry"):
            self._search_entry.delete(0, tk.END)
        if hasattr(self, "_url_entry"):
            self._url_entry.delete(0, tk.END)
            placeholder = (
                self._tr("url_placeholder")
                if hasattr(self, "_tr")
                else "https://  (вставь URL → Enter для загрузки страницы)"
            )
            self._url_entry.insert(0, placeholder)
        if hasattr(self, "_src_status"):
            self._src_status.config(text="")

        # Сбросить остатки незавершённого потокового форматирования.
        self._stream_buffer = ""
        self._in_code_block = False
        self._current_code_tag = None
        self._context_warning_shown = False

        if hasattr(self, "_update_ctx_label"):
            self._update_ctx_label()

        saved = self._save_session(self._session_name, silent=True)
        if hasattr(self, "_status"):
            status_messages = {
                "ru": "🧹 Все сообщения и результаты поиска удалены",
                "en": "🧹 All messages and search results were cleared",
                "bi": "🧹 Cleared / Сообщения и поиск удалены",
            }
            suffix = "" if saved else " ⚠️"
            self._status.config(
                text=status_messages.get(code, status_messages["ru"]) + suffix
            )

    def _reset_context(self, mode: str):
        """Очистить историю, не уничтожая сохранённую старую сессию."""
        if self.is_loading:
            messagebox.showwarning(
                "Модель работает",
                "Сначала дождитесь завершения текущего ответа.",
                parent=self.root,
            )
            return

        if mode == "chat":
            question = (
                "Сохранить текущую сессию и очистить только историю диалога?\n\n"
                "Файлы проекта и загруженные веб-страницы останутся в контексте."
            )
        else:
            question = (
                "Сохранить текущую сессию и очистить чат вместе с веб-контекстом?\n\n"
                "Открытые файлы проекта останутся подключёнными."
            )

        if not messagebox.askyesno(
            "Новый контекст",
            question,
            parent=self.root,
        ):
            return

        old_name = self._session_name
        if not self._save_session(old_name, silent=True):
            return

        self._clear_chat_context()
        if mode == "keep_files":
            self._clear_web_context()

        # Старая сессия остаётся нетронутой. Продолжение получает новое имя.
        self._session_name = self._continuation_name(old_name)
        self._update_session_ui()
        self._context_warning_shown = False
        self._update_ctx_label()
        self._save_session(self._session_name, silent=True)

        kept = "файлы и веб-контекст" if mode == "chat" else "файлы проекта"
        self._status.config(
            text=(
                f"♻ Контекст очищен; сохранены {kept}. "
                f"Старая сессия: {old_name}"
            )
        )

    def _new_session(self):
        """Начать полностью чистую сессию, сохранив сервер и модель.

        Текущий диалог автоматически сохраняется. Затем очищаются история,
        файлы проекта, веб-контекст, черновик и Code Viewer. Настройки
        подключения, выбранный сервер и активная модель остаются прежними.
        Это особенно важно при работе через Ollama: новая сессия не должна
        самопроизвольно переключаться на модель LM Studio по умолчанию.
        """
        if self.is_loading:
            messagebox.showwarning(
                "Модель работает",
                "Сначала дождитесь завершения текущего ответа.",
                parent=self.root,
            )
            return

        current_server = self._server_var.get()
        current_model = self._model_name

        suggested = f"session_{datetime.now().strftime('%Y%m%d_%H%M')}"
        name = simpledialog.askstring(
            "Новая чистая сессия",
            "Имя новой сессии:\n\n"
            "Будут очищены чат, файлы, веб-контекст и черновики.\n"
            f"Сервер и модель останутся: {current_server} / {current_model}",
            initialvalue=suggested,
            parent=self.root,
        )
        if not name or not name.strip():
            return

        # Сначала надёжно сохранить предыдущую работу.
        old_name = self._session_name
        if not self._save_session(old_name, silent=True):
            return

        # Полностью очистить рабочий контекст.
        self._clear_chat_context()
        self.loaded_files.clear()
        self._file_context_selected.clear()
        self._file_token_cache.clear()
        self._file_list_names.clear()
        self.current_project = None
        self._refresh_files_list()
        self._clear_web_context()

        if hasattr(self, "input_text"):
            self.input_text.delete("1.0", tk.END)
        if hasattr(self, "_clear_code_viewer"):
            self._clear_code_viewer()
        if hasattr(self, "_search_entry"):
            self._search_entry.delete(0, tk.END)
        if hasattr(self, "_url_entry"):
            self._url_entry.delete(0, tk.END)
            self._url_entry.insert(
                0,
                "https://  (вставь URL → Enter для загрузки страницы)",
            )

        # Новая сессия получает чистые настройки контекста, но сервер,
        # модель и параметры генерации намеренно сохраняются.
        self._session_name = name.strip()
        self._context_mode_var.set("auto")
        self._file_context_budget_var.set(32768)
        self._context_warning_shown = False

        self._update_model_ui()
        self._update_session_ui()
        if hasattr(self, "_update_language_ui"):
            self._update_language_ui()
        self._update_file_tokens()
        self._update_ctx_label()

        self._add_msg(
            "system",
            "🆕 Начата новая чистая сессия.\n"
            f"Сервер: {current_server}\n"
            f"Модель: {current_model}\n"
            f"Предыдущая сессия сохранена: {old_name}",
        )
        self._save_session(self._session_name, silent=True)
        self._status.config(
            text=(
                f"🆕 Новая сессия: {self._session_name} · "
                f"{current_server} · {current_model}"
            )
        )

    def _list_sessions(self):
        paths = sorted(
            self._session_files(),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
        if not paths:
            self._status.config(text="📂 Сохранённых сессий нет")
            return
        self._load_session_dialog()

    def _list_session_names(self) -> List[str]:
        names = []
        for path in self._session_files():
            summary = self._read_session_summary(path)
            names.append(str(summary["name"]))
        return sorted(set(names))

    def _delete_session(self):
        if not messagebox.askyesno(
            "Удалить сессию",
            f"Удалить сессию «{self._session_name}»?",
            parent=self.root,
        ):
            return
        safe = self._session_safe_name(self._session_name)
        paths = [
            SESSION_DIR / f"{safe}.json",
            SESSION_DIR / f"{safe}.llms",
        ]
        try:
            for path in paths:
                path.unlink(missing_ok=True)
        except Exception as exc:
            messagebox.showerror("Ошибка", str(exc), parent=self.root)
            return
        self._status.config(text=f"🗑️ Сессия удалена: {self._session_name}")
        self._session_name = DEFAULT_SESSION
        self._update_session_ui()

    def _on_close(self):
        """Автосохранение и безопасная остановка таймеров при закрытии."""
        self._shutdown_requested = True
        try:
            self._cancel_connection_retry()
            self._save_session(self._session_name, silent=True)
        finally:
            if hasattr(self, "_security_forget_key"):
                self._security_forget_key()
            self.root.destroy()
