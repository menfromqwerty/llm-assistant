"""Часть главного окна LLM Assistant.

Модуль выделен из монолитного файла v9 для удобства сопровождения.
"""

from .common import *  # noqa: F401,F403


class InputToolsMixin:
    def _setup_dnd(self):
        """Настройка drag-and-drop через tkinterdnd2 или Windows/X11 fallback."""
        if HAS_DND:
            # tkinterdnd2 — кросс-платформенный DnD
            try:
                self.input_text.drop_target_register(DND_FILES)
                self.input_text.dnd_bind("<<Drop>>",     self._on_dnd_drop)
                self.input_text.dnd_bind("<<DragEnter>>",self._on_dnd_enter)
                self.input_text.dnd_bind("<<DragLeave>>",self._on_dnd_leave)
                if hasattr(self, "_status"):
                    self._status.config(text="✅ Drag-and-drop готов (tkinterdnd2)")
                return
            except Exception:
                pass

        # Fallback: Windows нативный DnD через win32
        if sys.platform == "win32":
            try:
                self._setup_win32_dnd()
                return
            except Exception:
                pass

        # Если ничего не работает — просто показываем подсказку
        if hasattr(self, "_status"):
            self._status.config(
                text="ℹ️ Для DnD установи: pip install tkinterdnd2  (сейчас используй кнопку 📎)"
            )

    def _setup_win32_dnd(self):
        """Windows-нативный drag-and-drop через ctypes (без доп. зависимостей)."""
        import ctypes
        import ctypes.wintypes
        # Регистрируем окно как drop target через OleInitialize
        # Упрощённый вариант: перехватываем WM_DROPFILES
        hwnd = self.input_text.winfo_id()
        ctypes.windll.shell32.DragAcceptFiles(hwnd, True)
        self.input_text.bind("<Configure>", lambda e: None)  # force window creation
        # Привязываем через Tcl/Tk event
        self.root.bind("<<Win32Drop>>", self._on_win32_drop)

    def _on_dnd_enter(self, event):
        """Подсветить поле при наведении файла."""
        self.input_text.config(bg="#1a2a1a", relief=tk.SOLID)
        self._dnd_active = True

    def _on_dnd_leave(self, event):
        """Убрать подсветку."""
        self.input_text.config(bg=self.C["bg3"], relief=tk.FLAT)
        self._dnd_active = False

    def _on_dnd_drop(self, event):
        """Обработка брошенных файлов (tkinterdnd2)."""
        self.input_text.config(bg=self.C["bg3"], relief=tk.FLAT)
        self._dnd_active = False
        # event.data может содержать один или несколько путей в {}
        raw   = event.data.strip()
        paths = self._parse_dnd_paths(raw)
        for path in paths:
            self._handle_dropped_file(path)

    def _on_win32_drop(self, event):
        """Windows WM_DROPFILES fallback."""
        pass  # реализуется при наличии win32api

    def _parse_dnd_paths(self, raw: str) -> List[str]:
        """Разобрать строку путей из DnD события."""
        # tkinterdnd2 возвращает {путь1} {путь2} или просто путь
        paths = []
        if raw.startswith("{"):
            # Формат: {/path/to/file1} {/path/to/file2}
            for m in re.finditer(r'\{([^}]+)\}', raw):
                paths.append(m.group(1))
        else:
            paths = raw.split()
        return [p.strip() for p in paths if p.strip()]

    def _handle_dropped_file(self, path: str):
        """Обработать один брошенный файл."""
        p = Path(path)
        if not p.exists():
            return

        if p.suffix.lower() == ".zip":
            # ZIP → автораспаковать в проект
            self._add_msg("system", f"📦 Обнаружен ZIP: {p.name} — распаковываю...")
            self._set_phase(1, 3, f"Распаковка {p.name}...", spin=True)
            threading.Thread(target=self._zip_thread, args=(str(p),), daemon=True).start()
        elif p.is_file():
            # Текстовый файл → вставить содержимое в поле ввода
            self._insert_path_to_input(p)
        elif p.is_dir():
            # Папка → загрузить как проект
            self._add_msg("system", f"📂 Папка: {p.name} — загружаю файлы...")
            self._set_phase(1, 2, f"Загрузка папки {p.name}...", spin=True)
            threading.Thread(target=self._folder_thread, args=(str(p),), daemon=True).start()

    def _insert_path_to_input(self, p: Path):
        """Вставить содержимое файла в поле ввода как блок кода."""
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            self._add_msg("system", f"⚠️ Не удалось прочитать {p.name}: {e}")
            return

        lang  = EXT_LANG.get(p.suffix.lower(), "")
        tok   = self._tok(text)
        block = f"# Файл: {p.name}  (~{tok} токенов)\n```{lang}\n{text}\n```\n"

        cur = self.input_text.get("1.0", tk.END).strip()
        if cur:
            self.input_text.insert(tk.END, "\n\n" + block)
        else:
            self.input_text.insert("1.0", block)

        self.input_text.see(tk.END)
        self._status.config(text=f"📎 Вставлен {p.name}  (~{tok} токенов)")

        # Также добавить в список файлов
        self._add_file(p.name, str(p))

    def _insert_file_to_input(self):
        """Диалог выбора файла → вставка содержимого в поле ввода."""
        path = filedialog.askopenfilename(
            title="Выберите файл для вставки в ввод",
            filetypes=[
                ("Код",   "*.py *.js *.ts *.go *.rs *.cpp *.c *.java *.cs *.rb *.sh"),
                ("Text",  "*.txt *.md *.json *.yaml *.toml *.cfg *.ini *.html *.css *.sql"),
                ("Все",   "*.*"),
            ]
        )
        if path:
            self._insert_path_to_input(Path(path))

    def _insert_all_files_to_input(self):
        """Вставить все загруженные файлы проекта в поле ввода."""
        if not self.loaded_files:
            self._add_msg("system", "⚠️ Нет загруженных файлов")
            return
        self.input_text.delete("1.0", tk.END)
        total_tok = 0
        for name, path in self.loaded_files.items():
            p = Path(path)
            if not p.exists():
                continue
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
                lang  = EXT_LANG.get(p.suffix.lower(), "")
                tok   = self._tok(text)
                total_tok += tok
                block = f"# {name}  (~{tok} токенов)\n```{lang}\n{text}\n```\n\n"
                self.input_text.insert(tk.END, block)
            except Exception:
                pass
        self._status.config(text=f"📎 Вставлено {len(self.loaded_files)} файлов  (~{total_tok:,} токенов)")

    def _normalize_input(self):
        """
        Нормализовать код в поле ввода:
        - Заменить табы на 4 пробела
        - Убрать trailing whitespace
        - Убрать лишние пустые строки (>2 подряд → 1)
        - Нормализовать переносы строк
        """
        raw = self.input_text.get("1.0", tk.END)

        # Заменить \r\n и \r на \n
        text = raw.replace("\r\n", "\n").replace("\r", "\n")

        # Обработать блоки кода отдельно, текст вне блоков — отдельно
        result_parts = []
        in_code = False
        code_buf = []
        text_buf = []

        for line in text.split("\n"):
            if line.strip().startswith("```"):
                if not in_code:
                    # Начало блока: нормализуем накопленный текст
                    if text_buf:
                        normalized_text = self._normalize_text_block("\n".join(text_buf))
                        result_parts.append(normalized_text)
                        text_buf = []
                    in_code = True
                    code_buf = [line]
                else:
                    # Конец блока: нормализуем код
                    code_buf.append(line)
                    normalized_code = self._normalize_code_block(code_buf)
                    result_parts.append(normalized_code)
                    code_buf = []
                    in_code = False
            elif in_code:
                code_buf.append(line)
            else:
                text_buf.append(line)

        # Остатки
        if code_buf:
            result_parts.append(self._normalize_code_block(code_buf))
        if text_buf:
            result_parts.append(self._normalize_text_block("\n".join(text_buf)))

        normalized = "\n".join(result_parts).strip() + "\n"

        self.input_text.delete("1.0", tk.END)
        self.input_text.insert("1.0", normalized)
        tok = self._tok(normalized)
        self._status.config(text=f"🔧 Нормализовано  ~{tok:,} токенов")

    def _normalize_code_block(self, lines: List[str]) -> str:
        """Нормализовать код внутри ``` блока."""
        if not lines:
            return ""
        header = lines[0]  # строка ```python
        if len(lines) < 2:
            return header
        code_lines = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
        footer     = lines[-1]  if lines[-1].strip() == "```" else "```"

        # Заменить табы на 4 пробела
        clean = []
        for line in code_lines:
            line = line.replace("\t", "    ")
            line = line.rstrip()  # убрать trailing spaces
            clean.append(line)

        # Убрать >2 пустых строк подряд
        result = []
        empty_count = 0
        for line in clean:
            if line.strip() == "":
                empty_count += 1
                if empty_count <= 1:
                    result.append(line)
            else:
                empty_count = 0
                result.append(line)

        return "\n".join([header] + result + [footer])

    def _normalize_text_block(self, text: str) -> str:
        """Нормализовать обычный текст (не код)."""
        lines = text.split("\n")
        # Убрать trailing spaces
        lines = [l.rstrip() for l in lines]
        # Убрать >2 пустых строк подряд
        result = []
        empty = 0
        for line in lines:
            if line.strip() == "":
                empty += 1
                if empty <= 2:
                    result.append(line)
            else:
                empty = 0
                result.append(line)
        return "\n".join(result)

    def _trim_input_tokens(self):
        """Обрезать поле ввода до заданного числа токенов."""
        n = simpledialog.askinteger("Обрезать токены",
                                    "Максимум токенов в поле ввода:",
                                    initialvalue=2000, minvalue=100,
                                    maxvalue=self._effective_input_budget() if hasattr(self, "_effective_input_budget") else CONTEXT_BUDGET,
                                    parent=self.root)
        if not n:
            return
        text = self.input_text.get("1.0", tk.END)
        # Обрезаем по символам (4 символа ≈ 1 токен)
        limit = n * 4
        if len(text) > limit:
            text = text[:limit] + f"\n\n... [обрезано до ~{n} токенов]"
            self.input_text.delete("1.0", tk.END)
            self.input_text.insert("1.0", text)
        self._status.config(text=f"✂️ Обрезано до ~{n} токенов")

    def _copy_input_all(self):
        text = self.input_text.get("1.0", tk.END)
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self._status.config(text="📋 Поле ввода скопировано")
