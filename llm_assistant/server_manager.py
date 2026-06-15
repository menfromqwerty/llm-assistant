"""Управление локальными OpenAI-совместимыми серверами.

Поддерживаются LM Studio, Ollama, llama.cpp, Jan и произвольный URL.
Кнопка запуска и диагностика всегда относятся к выбранному серверу.
"""

from .common import *

class ServerManagerMixin:
    """Подключение, автоповтор, запуск серверов и диагностика API."""

    def _server_config(self, name: Optional[str] = None) -> Dict[str, object]:
        server_name = name or self._server_var.get()
        return dict(SERVER_CONFIGS.get(server_name, {}))

    def _server_start_button_text(self) -> str:
        config = self._server_config()
        if config:
            return str(config.get("button", "▶ СЕРВЕР"))
        return "🔄 ПРОВЕРИТЬ"

    def _server_start_button_color(self) -> str:
        config = self._server_config()
        return str(config.get("color", "#44617b"))

    def _update_server_ui(self):
        """Обновить цветную кнопку после смены провайдера."""
        if hasattr(self, "_start_server_btn"):
            self._start_server_btn.config(
                text=self._server_start_button_text(),
                bg=self._server_start_button_color(),
                state=tk.NORMAL,
            )
        if hasattr(self, "_status"):
            self._status.config(
                text=f"🖥️ Сервер: {self._server_var.get()} · {self._server_url}"
            )

    def _select_server(self, name: str):
        """Выбрать сервер, не принуждая использовать модель LM Studio."""
        if name not in SERVERS:
            return
        self._cancel_connection_retry()
        self._server_url = SERVERS[name]
        self._server_var.set(name)
        self._available_models = []
        self._update_server_ui()
        self._check_connection(auto_retry=True, announce=True)

    def _custom_server(self):
        url = simpledialog.askstring(
            "Свой сервер",
            "OpenAI-совместимый URL (например http://localhost:8080/v1):",
            parent=self.root,
        )
        if not url:
            return
        parsed = urlparse(url.strip())
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            messagebox.showwarning(
                "Некорректный адрес",
                "Укажите базовый http:// или https:// URL, например "
                "http://localhost:8000/v1",
                parent=self.root,
            )
            return
        if parsed.username or parsed.password:
            messagebox.showwarning(
                "Небезопасный адрес",
                "Не помещайте логин или пароль в URL. Используйте API-ключ/заголовок.",
                parent=self.root,
            )
            return
        self._cancel_connection_retry()
        self._server_url = url.strip().rstrip("/")
        self._server_var.set("Свой")
        self._available_models = []
        self._update_server_ui()
        self._check_connection(auto_retry=True, announce=True)

    def _ollama_native_base(self, url: str) -> str:
        parsed = urlparse(url)
        scheme = parsed.scheme or "http"
        netloc = parsed.netloc or "localhost:11434"
        return f"{scheme}://{netloc}"

    def _fetch_server_models(
        self,
        server_name: Optional[str] = None,
        url: Optional[str] = None,
    ) -> List[str]:
        """Получить модели активного сервера.

        Сначала используется OpenAI-совместимый ``/v1/models``. Для Ollama
        предусмотрен надёжный fallback на нативный ``/api/tags``.
        """
        name = server_name or self._server_var.get()
        base_url = (url or self._server_url).rstrip("/")

        primary_response = requests.get(
            f"{base_url}/models",
            timeout=(3, 12),
        )
        if primary_response.status_code == 200:
            data = primary_response.json()
            models = [
                str(item.get("id"))
                for item in data.get("data", [])
                if isinstance(item, dict) and item.get("id")
            ]
            if models or name != "Ollama":
                return sorted(set(models), key=str.lower)

        if name == "Ollama":
            native_response = requests.get(
                f"{self._ollama_native_base(base_url)}/api/tags",
                timeout=(3, 12),
            )
            if native_response.status_code == 200:
                data = native_response.json()
                models = []
                for item in data.get("models", []):
                    if not isinstance(item, dict):
                        continue
                    value = item.get("name") or item.get("model")
                    if value:
                        models.append(str(value))
                return sorted(set(models), key=str.lower)
            native_response.raise_for_status()

        primary_response.raise_for_status()
        return []

    def _preferred_model(self, server_name: str, models: List[str]) -> str:
        saved = self._server_model_selection.get(server_name, "")
        if saved in models:
            return saved
        if self._model_name in models:
            return self._model_name
        if server_name == "LM Studio" and DEFAULT_MODEL_NAME in models:
            return DEFAULT_MODEL_NAME

        chat_models = [
            model for model in models
            if not any(word in model.lower() for word in ("embed", "embedding"))
        ]
        return (chat_models or models)[0] if models else ""

    def _synchronize_model_for_server(
        self,
        server_name: str,
        models: List[str],
    ) -> Optional[str]:
        """Выбрать доступную модель отдельно для каждого сервера."""
        if not models:
            return None
        selected = self._preferred_model(server_name, models)
        if not selected:
            return None
        changed = selected != self._model_name
        self._server_model_selection[server_name] = selected
        if changed:
            self._set_model(selected, apply_profile=True)
        return selected if changed else None

    def _check_connection(self, auto_retry: bool = True, announce: bool = True):
        if self._shutdown_requested or self._connection_check_running:
            return

        if auto_retry and not self._connection_retry_active:
            self._connection_retry_active = True
            self._connection_retry_attempts = 0
            self._cancel_retry_timer_only()

        self._connection_check_running = True
        self._connection_retry_attempts += 1
        attempt = self._connection_retry_attempts
        max_attempts = self._connection_retry_max_attempts
        name = self._server_var.get()
        url = self._server_url.rstrip("/")
        self._set_connection_waiting(name, attempt, max_attempts)

        def worker():
            ok = False
            models: List[str] = []
            reason = ""
            details = ""
            try:
                models = self._fetch_server_models(name, url)
                ok = True
            except requests.exceptions.HTTPError as exc:
                response = exc.response
                if response is not None:
                    reason, details = self._classify_api_error(
                        response.status_code,
                        response.text,
                        model_name=self._model_name,
                        server_name=name,
                    )
                else:
                    reason = "HTTP-ошибка сервера"
                    details = str(exc)
            except requests.exceptions.ConnectionError as exc:
                reason, details = self._diagnose_connection_failure(
                    name, url, str(exc)
                )
            except requests.exceptions.Timeout:
                reason = "Тайм-аут подключения"
                details = f"Сервер не ответил за 12 секунд.\nАдрес: {url}"
            except json.JSONDecodeError as exc:
                reason = "Сервер вернул неверный JSON"
                details = f"Адрес: {url}\nОшибка: {exc}"
            except Exception as exc:
                reason = "Ошибка проверки сервера"
                details = f"{type(exc).__name__}: {exc}"

            if self._shutdown_requested:
                return
            self.root.after(
                0,
                lambda: self._finish_connection_check(
                    ok=ok,
                    name=name,
                    url=url,
                    models=models,
                    reason=reason,
                    details=details,
                    auto_retry=auto_retry,
                    announce=announce,
                    attempt=attempt,
                    max_attempts=max_attempts,
                ),
            )

        threading.Thread(target=worker, daemon=True).start()

    def _finish_connection_check(
        self,
        *,
        ok: bool,
        name: str,
        url: str,
        models: List[str],
        reason: str,
        details: str,
        auto_retry: bool,
        announce: bool,
        attempt: int,
        max_attempts: int,
    ):
        self._connection_check_running = False
        if self._shutdown_requested:
            return

        if name != self._server_var.get() or url != self._server_url.rstrip("/"):
            self.root.after(
                50,
                lambda: self._check_connection(auto_retry=True, announce=True),
            )
            return

        if ok:
            self._available_models = models
            self._connection_retry_active = False
            self._cancel_retry_timer_only()
            changed_model = self._synchronize_model_for_server(name, models)
            self._set_conn(True, name)
            self._status.config(
                text=f"✅ {name}: подключено · моделей: {len(models)}"
            )
            if announce or attempt > 1 or changed_model:
                model_preview = ", ".join(models[:6]) or "модели не установлены"
                extra = (
                    f"\nАвтоматически выбрана модель: {changed_model}"
                    if changed_model else ""
                )
                self._add_msg(
                    "system",
                    f"✅ Подключено к {name}\n"
                    f"URL: {url}\n"
                    f"Модели: {model_preview}{extra}",
                )
            if not models:
                self._show_empty_model_hint(name)
            return

        self._last_connection_error = f"{reason}\n{details}".strip()
        self._set_conn(False, name)
        can_retry = auto_retry and attempt < max_attempts
        if can_retry:
            seconds = self._connection_retry_interval_ms // 1000
            self._status.config(
                text=(
                    f"⚠️ {reason}. Повтор {attempt}/{max_attempts}; "
                    f"следующая попытка через {seconds} с"
                )
            )
            self._conn_badge.config(
                text=f"● {name} {attempt}/{max_attempts}",
                fg=self.C.get("gold", "#ffd700"),
            )
            if announce and attempt == 1:
                self._add_msg(
                    "system",
                    f"⚠️ {reason}\n{details}\n\n"
                    f"Автоповтор каждые {seconds} секунд в течение минуты.",
                )
            self._connection_retry_after_id = self.root.after(
                self._connection_retry_interval_ms,
                lambda: self._check_connection(
                    auto_retry=True,
                    announce=False,
                ),
            )
            return

        self._connection_retry_active = False
        self._cancel_retry_timer_only()
        self._status.config(text=f"❌ {reason}")
        self._add_msg(
            "system",
            f"❌ {reason}\n{details}\n\n"
            f"Проверено {attempt} раз. Нажмите "
            f"«{self._server_start_button_text()}» или «Проверить соединение».",
        )

    def _show_empty_model_hint(self, server_name: str):
        if server_name == "Ollama":
            self._add_msg(
                "system",
                "⚠️ Ollama запущен, но список моделей пуст.\n"
                "Модели LM Studio не появляются в Ollama автоматически. "
                "Установите модель отдельно командой:\n"
                "ollama pull <имя_модели>\n"
                "Затем нажмите «🧠 МОДЕЛЬ → Обновить с сервера».",
            )
        elif server_name == "Jan":
            self._add_msg(
                "system",
                "⚠️ Jan API работает, но моделей не найдено. "
                "Загрузите и запустите локальную модель в Jan.",
            )

    def _set_connection_waiting(self, name: str, attempt: int, maximum: int):
        if not hasattr(self, "_conn_badge"):
            return
        self._conn_badge.config(
            text=f"● {name} {attempt}/{maximum}",
            fg=self.C.get("gold", "#ffd700"),
        )
        self._status.config(
            text=f"🔄 Проверка {name}: попытка {attempt}/{maximum}..."
        )

    def _cancel_retry_timer_only(self):
        after_id = self._connection_retry_after_id
        self._connection_retry_after_id = None
        if after_id is not None:
            try:
                self.root.after_cancel(after_id)
            except Exception:
                pass

    def _cancel_connection_retry(self):
        self._cancel_retry_timer_only()
        self._connection_retry_active = False
        self._connection_retry_attempts = 0

    def _start_selected_server(self):
        name = self._server_var.get()
        if name == "LM Studio":
            self._start_lm_studio_server()
        elif name == "Ollama":
            self._start_ollama_server()
        elif name == "llama.cpp":
            self._open_llama_cpp_setup()
        elif name == "Jan":
            self._start_or_explain_jan()
        else:
            self._check_connection(auto_retry=True, announce=True)

    def _set_start_button_busy(self, text: str = "⏳ ЗАПУСК..."):
        if hasattr(self, "_start_server_btn"):
            self._start_server_btn.config(state=tk.DISABLED, text=text)

    def _finish_server_start(self, server_name: str, ok: bool, output: str):
        self._update_server_ui()
        if ok:
            self._add_msg(
                "system",
                f"✅ Команда запуска {server_name} выполнена.\n"
                + (output or self._server_url),
            )
            self._status.config(
                text=f"⏳ {server_name} запускается; проверяю подключение..."
            )
            self.root.after(
                1200,
                lambda: self._check_connection(
                    auto_retry=True,
                    announce=False,
                ),
            )
        else:
            self._set_conn(False, server_name)
            self._status.config(text=f"❌ Не удалось запустить {server_name}")
            self._add_msg(
                "system",
                f"❌ Не удалось запустить {server_name}.\n{output}",
            )

    def _start_lm_studio_server(self):
        if self._shutdown_requested:
            return
        self._server_var.set("LM Studio")
        self._server_url = SERVERS["LM Studio"]
        self._update_server_ui()
        self._cancel_connection_retry()
        self._set_start_button_busy()
        self._status.config(text="▶ Запуск LM Studio Server на порту 1234...")

        def worker():
            executable = shutil.which("lms")
            if not executable:
                ok = False
                output = (
                    "Команда lms не найдена в PATH.\n"
                    "Откройте LM Studio → Developer → Start Server."
                )
            else:
                ok, output = self._run_short_command(
                    executable,
                    ["server", "start", "--port", "1234"],
                    timeout=40,
                )
            if not self._shutdown_requested:
                self.root.after(
                    0,
                    lambda: self._finish_server_start("LM Studio", ok, output),
                )

        threading.Thread(target=worker, daemon=True).start()

    def _find_ollama_executable(self) -> Optional[str]:
        found = shutil.which("ollama")
        if found:
            return found
        local = Path(os.environ.get("LOCALAPPDATA", ""))
        candidates = [
            local / "Programs" / "Ollama" / "ollama.exe",
            local / "Ollama" / "ollama.exe",
        ]
        for candidate in candidates:
            if candidate.is_file():
                return str(candidate)
        return None

    def _start_ollama_server(self):
        if self._shutdown_requested:
            return
        self._server_var.set("Ollama")
        self._server_url = SERVERS["Ollama"]
        self._update_server_ui()
        self._cancel_connection_retry()
        self._set_start_button_busy()
        self._status.config(text="▶ Запуск Ollama на порту 11434...")

        def worker():
            if self._is_tcp_port_open("localhost", 11434):
                ok = True
                output = "Ollama уже работает на порту 11434."
            else:
                executable = self._find_ollama_executable()
                if not executable:
                    ok = False
                    output = (
                        "ollama.exe не найден. Установите Ollama или добавьте "
                        "команду ollama в PATH."
                    )
                else:
                    try:
                        creationflags = 0
                        if os.name == "nt":
                            creationflags = (
                                getattr(subprocess, "CREATE_NO_WINDOW", 0)
                                | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
                                | getattr(subprocess, "DETACHED_PROCESS", 0)
                            )
                        process = subprocess.Popen(
                            [executable, "serve"],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            stdin=subprocess.DEVNULL,
                            creationflags=creationflags,
                            start_new_session=(os.name != "nt"),
                        )
                        self._server_processes["Ollama"] = process
                        time.sleep(1.5)
                        ok = self._is_tcp_port_open("localhost", 11434)
                        output = (
                            "Ollama API доступен на http://localhost:11434/v1"
                            if ok
                            else "Процесс запущен, ожидается открытие порта 11434."
                        )
                        if process.poll() is None:
                            ok = True
                    except Exception as exc:
                        ok = False
                        output = f"{type(exc).__name__}: {exc}"
            if not self._shutdown_requested:
                self.root.after(
                    0,
                    lambda: self._finish_server_start("Ollama", ok, output),
                )

        threading.Thread(target=worker, daemon=True).start()

    def _open_llama_cpp_setup(self):
        """Настроить путь к llama-server и GGUF-модели."""
        win = tk.Toplevel(self.root)
        win.title("⚙ Запуск llama.cpp server")
        win.geometry("720x300")
        win.configure(bg=self.C["bg"])
        win.transient(self.root)
        win.grab_set()

        settings = self._llama_cpp_settings
        exe_var = tk.StringVar(value=str(settings.get("executable", "")))
        model_var = tk.StringVar(value=str(settings.get("model", "")))
        port_var = tk.StringVar(value=str(settings.get("port", 8080)))
        args_var = tk.StringVar(value=str(settings.get("extra_args", "")))

        def row(label: str, variable: tk.StringVar, browse=None):
            frame = tk.Frame(win, bg=self.C["bg"])
            frame.pack(fill=tk.X, padx=14, pady=7)
            tk.Label(
                frame, text=label, width=18, anchor=tk.W,
                bg=self.C["bg"], fg=self.C["fg"],
            ).pack(side=tk.LEFT)
            entry = tk.Entry(
                frame, textvariable=variable, bg=self.C["bg3"],
                fg=self.C["fg"], insertbackground="white",
            )
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4)
            if browse:
                tk.Button(
                    frame, text="Обзор...", command=browse,
                    bg=self.C["bg3"], fg=self.C["fg"], relief=tk.FLAT,
                ).pack(side=tk.LEFT, padx=(6, 0))

        def browse_exe():
            value = filedialog.askopenfilename(
                parent=win,
                title="Выберите llama-server.exe",
                filetypes=[("Executable", "*.exe"), ("Все файлы", "*.*")],
            )
            if value:
                exe_var.set(value)

        def browse_model():
            value = filedialog.askopenfilename(
                parent=win,
                title="Выберите GGUF-модель",
                filetypes=[("GGUF", "*.gguf"), ("Все файлы", "*.*")],
            )
            if value:
                model_var.set(value)

        row("llama-server:", exe_var, browse_exe)
        row("GGUF-модель:", model_var, browse_model)
        row("Порт:", port_var)
        row("Доп. аргументы:", args_var)

        tk.Label(
            win,
            text="Пример аргументов: -ngl 99 -c 32768",
            bg=self.C["bg"], fg="#888",
        ).pack(anchor=tk.W, padx=14)

        def start():
            executable = exe_var.get().strip()
            model = model_var.get().strip()
            try:
                port = int(port_var.get().strip())
                if not 1 <= port <= 65535:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Порт", "Введите порт от 1 до 65535", parent=win)
                return
            if not Path(executable).is_file():
                messagebox.showerror("llama.cpp", "Не найден llama-server.exe", parent=win)
                return
            if not Path(model).is_file():
                messagebox.showerror("Модель", "Не найден файл GGUF", parent=win)
                return

            self._llama_cpp_settings = {
                "executable": executable,
                "model": model,
                "port": port,
                "extra_args": args_var.get().strip(),
            }
            self._server_var.set("llama.cpp")
            self._server_url = f"http://localhost:{port}/v1"
            self._update_server_ui()
            win.destroy()
            self._start_llama_cpp_process()

        buttons = tk.Frame(win, bg=self.C["bg"])
        buttons.pack(fill=tk.X, padx=14, pady=14)
        tk.Button(
            buttons, text="▶ Запустить", command=start,
            bg="#b7791f", fg="white", relief=tk.FLAT, padx=14, pady=6,
        ).pack(side=tk.RIGHT)
        tk.Button(
            buttons, text="Отмена", command=win.destroy,
            bg=self.C["bg3"], fg=self.C["fg"], relief=tk.FLAT, padx=14, pady=6,
        ).pack(side=tk.RIGHT, padx=8)

    def _start_llama_cpp_process(self):
        settings = self._llama_cpp_settings
        executable = str(settings.get("executable", ""))
        model = str(settings.get("model", ""))
        port = int(settings.get("port", 8080))
        extra = str(settings.get("extra_args", ""))
        self._cancel_connection_retry()
        self._set_start_button_busy()
        self._status.config(text=f"▶ Запуск llama.cpp на порту {port}...")

        def worker():
            try:
                command = [executable, "-m", model, "--port", str(port)]
                if extra:
                    command.extend(shlex.split(extra, posix=(os.name != "nt")))
                creationflags = 0
                if os.name == "nt":
                    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
                process = subprocess.Popen(
                    command,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL,
                    creationflags=creationflags,
                )
                self._server_processes["llama.cpp"] = process
                time.sleep(1.2)
                ok = process.poll() is None
                output = " ".join(command)
            except Exception as exc:
                ok = False
                output = f"{type(exc).__name__}: {exc}"
            if not self._shutdown_requested:
                self.root.after(
                    0,
                    lambda: self._finish_server_start("llama.cpp", ok, output),
                )

        threading.Thread(target=worker, daemon=True).start()

    def _start_or_explain_jan(self):
        self._server_var.set("Jan")
        self._server_url = SERVERS["Jan"]
        self._update_server_ui()
        if self._is_tcp_port_open("localhost", 1337):
            self._check_connection(auto_retry=True, announce=True)
            return

        local = Path(os.environ.get("LOCALAPPDATA", ""))
        candidates = [
            local / "Programs" / "Jan" / "Jan.exe",
            local / "Programs" / "jan" / "Jan.exe",
        ]
        launched = False
        for candidate in candidates:
            if candidate.is_file():
                try:
                    subprocess.Popen([str(candidate)])
                    launched = True
                    break
                except Exception:
                    pass
        messagebox.showinfo(
            "Jan Local API Server",
            ("Jan запущен.\n\n" if launched else "Откройте приложение Jan.\n\n")
            + "Перейдите: Settings → Local API Server → Start Server.\n"
            + "Ожидаемый адрес: http://127.0.0.1:1337/v1\n\n"
            + "После запуска приложение проверит соединение автоматически.",
            parent=self.root,
        )
        self._check_connection(auto_retry=True, announce=False)

    def _run_short_command(
        self,
        executable: str,
        arguments: List[str],
        *,
        timeout: int,
    ) -> Tuple[bool, str]:
        creationflags = (
            getattr(subprocess, "CREATE_NO_WINDOW", 0)
            if os.name == "nt" else 0
        )
        is_batch = os.name == "nt" and executable.lower().endswith((".cmd", ".bat"))
        if is_batch:
            comspec = os.environ.get("COMSPEC", r"C:\Windows\System32\cmd.exe")
            command = [
                comspec, "/d", "/s", "/c",
                subprocess.list2cmdline([executable, *arguments]),
            ]
        else:
            command = [executable, *arguments]
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=False,
                creationflags=creationflags,
            )
            output = "\n".join(
                part.strip()
                for part in (completed.stdout, completed.stderr)
                if part and part.strip()
            )
            lower = output.lower()
            ok = completed.returncode == 0 or "already" in lower
            return ok, output
        except subprocess.TimeoutExpired:
            return False, f"Команда не завершилась за {timeout} секунд."
        except Exception as exc:
            return False, f"{type(exc).__name__}: {exc}"

    def _diagnose_connection_failure(
        self,
        server_name: str,
        url: str,
        original_error: str = "",
    ) -> Tuple[str, str]:
        parsed = urlparse(url)
        host = parsed.hostname or "localhost"
        port = parsed.port

        if server_name == "LM Studio":
            status = self._read_lms_server_status()
            if status["state"] == "stopped":
                return (
                    "LM Studio Server не запущен",
                    "Нажмите «▶ LM STUDIO» либо откройте "
                    "LM Studio → Developer → Start Server.",
                )
            if status["state"] == "running":
                running_port = status.get("port")
                if port and running_port and int(port) != int(running_port):
                    return (
                        "Указан неправильный порт LM Studio",
                        f"Приложение использует {port}, сервер работает на {running_port}.\n"
                        f"URL: {url}",
                    )

        if server_name == "Ollama" and port and not self._is_tcp_port_open(host, port):
            executable = self._find_ollama_executable()
            hint = (
                "Нажмите «▶ OLLAMA» или выполните в терминале: ollama serve."
                if executable else
                "Ollama не установлен или не найден в PATH."
            )
            return "Ollama не запущен", f"Порт {host}:{port} закрыт.\n{hint}"

        if server_name == "llama.cpp" and port and not self._is_tcp_port_open(host, port):
            return (
                "llama.cpp server не запущен",
                "Нажмите «⚙ LLAMA.CPP», выберите llama-server.exe и GGUF-модель.\n"
                f"Ожидаемый адрес: {url}",
            )

        if server_name == "Jan" and port and not self._is_tcp_port_open(host, port):
            return (
                "Jan Local API Server не запущен",
                "Откройте Jan → Settings → Local API Server → Start Server.\n"
                f"Ожидаемый адрес: {url}",
            )

        if port and not self._is_tcp_port_open(host, port):
            return (
                "Сервер не запущен или указан неправильный порт",
                f"На {host}:{port} нет слушающего процесса.\nURL: {url}",
            )
        return (
            f"{server_name} запущен, но API недоступен",
            f"URL: {url}\nОшибка: {original_error[:500]}",
        )

    def _read_lms_server_status(self) -> Dict[str, object]:
        executable = shutil.which("lms")
        if not executable:
            return {"state": "unknown", "port": None, "text": "lms not found"}
        ok, text = self._run_short_command(executable, ["server", "status"], timeout=8)
        lower = text.lower()
        if "not running" in lower or "не запущ" in lower:
            return {"state": "stopped", "port": None, "text": text}
        match = re.search(r"port\D+(\d{2,5})", lower)
        if not match:
            match = re.search(r"https?://[^:/\s]+:(\d{2,5})", lower)
        if ok or "running" in lower or match:
            return {
                "state": "running",
                "port": int(match.group(1)) if match else None,
                "text": text,
            }
        return {"state": "unknown", "port": None, "text": text}

    @staticmethod
    def _is_tcp_port_open(host: str, port: int) -> bool:
        try:
            with socket.create_connection((host, int(port)), timeout=1.5):
                return True
        except OSError:
            return False

    def _classify_api_error(
        self,
        status_code: int,
        body: str,
        *,
        model_name: str = "",
        server_name: str = "",
    ) -> Tuple[str, str]:
        raw = (body or "").strip()
        lower = raw.lower()
        model = model_name or self._model_name
        server = server_name or self._server_var.get()

        context_patterns = (
            "context length", "maximum context", "context window",
            "context size", "too many tokens", "prompt is too long",
            "exceeds the context", "n_ctx", "token limit",
        )
        oom_patterns = (
            "out of memory", "cuda out of memory", "failed to allocate",
            "cannot allocate memory", "insufficient memory",
            "not enough memory", "vram", "ggml_backend_alloc_buffer",
        )
        model_missing_patterns = (
            "model not found", "unknown model", "does not exist",
            "no such model", "invalid model",
        )
        model_load_patterns = (
            "failed to load model", "model failed to load",
            "could not load model", "model is not loaded",
            "no model loaded", "load model failed",
        )

        if any(pattern in lower for pattern in context_patterns):
            return (
                "Превышен размер контекста",
                "Очистите историю, отключите часть файлов или уменьшите "
                f"контекст в настройках {server}.\nОтвет: {raw[:1200]}",
            )
        if any(pattern in lower for pattern in oom_patterns):
            return (
                "Недостаточно RAM или VRAM",
                f"{server} не смог выделить память. Уменьшите контекст, "
                f"GPU offload или выберите более лёгкую модель.\nОтвет: {raw[:1200]}",
            )
        if any(pattern in lower for pattern in model_load_patterns):
            return (
                "Модель не загрузилась в память",
                f"Сервер: {server}\nМодель: {model}\n"
                f"Проверьте журнал сервера и объём RAM/VRAM.\nОтвет: {raw[:1200]}",
            )
        if any(pattern in lower for pattern in model_missing_patterns) or status_code == 404:
            return (
                "Выбранная модель отсутствует на текущем сервере",
                f"Сервер: {server}\nМодель: {model}\n"
                "Нажмите «🧠 МОДЕЛЬ → Обновить с сервера» и выберите модель "
                f"именно этого сервера.\nОтвет: {raw[:1200]}",
            )
        if status_code in (401, 403):
            return (
                "Ошибка авторизации API",
                f"Сервер {server} требует токен или запрещает запрос.\n"
                f"HTTP {status_code}: {raw[:1200]}",
            )
        if status_code == 429:
            return "Сервер временно перегружен", f"HTTP 429: {raw[:1200]}"
        return (
            f"Ошибка API {server}: HTTP {status_code}",
            raw[:1500] or "Сервер не передал описание ошибки.",
        )

    def _ensure_selected_model_exists(
        self,
        url: str,
        model_name: str,
        server_name: Optional[str] = None,
    ) -> Tuple[bool, List[str], str]:
        """Проверить сервер и модель без привязки к LM Studio."""
        name = server_name or self._server_var.get()
        try:
            models = self._fetch_server_models(name, url)
        except requests.exceptions.HTTPError as exc:
            response = exc.response
            if response is not None:
                reason, details = self._classify_api_error(
                    response.status_code,
                    response.text,
                    model_name=model_name,
                    server_name=name,
                )
                return False, [], f"{reason}\n{details}"
            return False, [], str(exc)
        except Exception as exc:
            reason, details = self._diagnose_connection_failure(
                name, url, str(exc)
            )
            return False, [], f"{reason}\n{details}"

        if model_name not in models:
            preview = "\n".join(f"  • {item}" for item in models[:15])
            return (
                False,
                models,
                f"Выбранная модель отсутствует на сервере {name}\n"
                f"Требуется: {model_name}\n"
                f"Доступны:\n{preview or '  список пуст'}",
            )
        return True, models, ""
