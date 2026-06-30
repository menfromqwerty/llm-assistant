"""Загрузка файлов проекта, список файлов и просмотр кода."""

from .common import *  # noqa: F401,F403


class FileManagerMixin:
    PROJECT_EXTENSIONS = {
        ".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".cpp",
        ".cc", ".c", ".h", ".hpp", ".java", ".cs", ".rb", ".php",
        ".html", ".css", ".scss", ".sql", ".sh", ".ps1", ".ino",
        ".md", ".txt", ".json", ".yaml", ".yml", ".toml", ".cfg",
        ".ini", ".xml", ".cmake",
    }
    MAX_PROJECT_FILE_BYTES = 8 * 1024 * 1024
    MAX_ZIP_FILES = 5000
    MAX_ZIP_UNCOMPRESSED_BYTES = 300 * 1024 * 1024

    @staticmethod
    def _zip_member_is_symlink(info: zipfile.ZipInfo) -> bool:
        # POSIX file type is stored in the upper 16 bits of external_attr.
        return ((info.external_attr >> 16) & 0o170000) == 0o120000

    def _safe_extract_zip(self, archive: zipfile.ZipFile, destination: Path) -> List[Path]:
        """Распаковать ZIP без Zip Slip, симлинков и очевидных ZIP-bomb архивов."""
        infos = [item for item in archive.infolist() if not item.is_dir()]
        if len(infos) > self.MAX_ZIP_FILES:
            raise ValueError(
                f"В архиве слишком много файлов: {len(infos)} > {self.MAX_ZIP_FILES}."
            )
        total_size = sum(max(0, item.file_size) for item in infos)
        if total_size > self.MAX_ZIP_UNCOMPRESSED_BYTES:
            raise ValueError(
                "Распакованный архив слишком большой: "
                f"{total_size / (1024**2):.1f} МБ."
            )

        destination = destination.resolve()
        extracted: List[Path] = []
        for info in infos:
            if self._zip_member_is_symlink(info):
                continue
            # Backslash заменяется до Path, чтобы Windows-пути нельзя было
            # использовать для обхода каталога на другой платформе.
            normalized = info.filename.replace("\\", "/")
            relative = Path(normalized)
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError(f"Небезопасный путь в ZIP: {info.filename}")
            target = (destination / relative).resolve()
            try:
                target.relative_to(destination)
            except ValueError as exc:
                raise ValueError(f"Небезопасный путь в ZIP: {info.filename}") from exc
            if target.suffix.lower() not in self.PROJECT_EXTENSIONS:
                continue
            if info.file_size > self.MAX_PROJECT_FILE_BYTES:
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info, "r") as source, target.open("wb") as output:
                shutil.copyfileobj(source, output, length=1024 * 1024)
            extracted.append(target)
        return extracted

    def _open_file(self):
        path = filedialog.askopenfilename(
            title="Выберите файл",
            filetypes=[
                ("Исходный код", "*.py *.js *.ts *.cpp *.c *.h *.hpp *.java *.cs"),
                ("Text", "*.txt *.md *.json *.yaml *.yml *.toml *.ini *.cfg"),
                ("All", "*.*"),
            ],
        )
        if not path:
            return
        source_path = Path(path)
        try:
            if source_path.stat().st_size > self.MAX_PROJECT_FILE_BYTES:
                messagebox.showwarning(
                    "Файл слишком большой",
                    f"Максимальный размер одного файла: "
                    f"{self.MAX_PROJECT_FILE_BYTES / (1024**2):.0f} МБ.",
                    parent=self.root,
                )
                return
        except OSError as exc:
            messagebox.showerror("Ошибка файла", str(exc), parent=self.root)
            return
        name = source_path.name
        self._add_file(name, path, select_for_context=True)
        try:
            text = Path(path).read_text(encoding="utf-8", errors="replace")
            t = self._tok(text)
            prev = text[:600] + "..." if len(text) > 600 else text
            self._add_msg("system", f"📄 {name}  (~{t} токенов)\n```\n{prev}\n```")
        except Exception as exc:
            self._add_msg("system", f"⚠️ {name}: {exc}")

    def _open_zip(self):
        path = filedialog.askopenfilename(title="ZIP", filetypes=[("ZIP", "*.zip")])
        if not path:
            return
        self._set_phase(1, 3, "Распаковка ZIP...", spin=True)
        threading.Thread(target=self._zip_thread, args=(path,), daemon=True).start()

    def _open_folder(self):
        folder = filedialog.askdirectory(title="Выберите папку проекта")
        if not folder:
            return
        self.current_project = folder
        self._set_phase(1, 2, f"Сканирование {folder}", spin=True)
        threading.Thread(target=self._folder_thread, args=(folder,), daemon=True).start()

    def _zip_thread(self, zip_path: str):
        try:
            directory = tempfile.mkdtemp(prefix="llm_assistant_zip_")
            root = Path(directory)
            with zipfile.ZipFile(zip_path, "r") as archive:
                files = self._safe_extract_zip(archive, root)
            items = [
                (str(path.relative_to(root)).replace("\\", "/"), str(path))
                for path in files
            ]
            self.root.after(0, lambda data=items: self._add_files_batch(data))
            self.root.after(0, lambda: self._set_phase(3, 3, "ZIP загружен"))
            self.root.after(
                0,
                lambda: self._add_msg(
                    "system", f"📦 {Path(zip_path).name}: {len(items)} файлов"
                ),
            )
            self.root.after(400, lambda: self._clear_phase("✅ ZIP загружен"))
        except Exception as exc:
            error = str(exc)
            self.root.after(0, lambda: self._add_msg("system", f"❌ ZIP: {error}"))
            self.root.after(0, lambda: self._clear_phase("❌ Ошибка ZIP"))

    def _folder_thread(self, folder: str):
        extensions = self.PROJECT_EXTENSIONS
        ignored_parts = {
            ".git", ".idea", ".vscode", "__pycache__", "node_modules",
            ".venv", "venv", "dist", "build", ".pytest_cache", ".mypy_cache",
        }
        root = Path(folder)
        files = [
            path
            for path in root.rglob("*")
            if path.is_file()
            and path.suffix.lower() in extensions
            and not any(part in ignored_parts for part in path.parts)
            and path.stat().st_size <= self.MAX_PROJECT_FILE_BYTES
        ]
        items = [
            (str(path.relative_to(root)).replace("\\", "/"), str(path))
            for path in files
        ]
        self.root.after(0, lambda data=items: self._add_files_batch(data))
        self.root.after(
            0,
            lambda: self._add_msg(
                "system", f"📂 {folder}\n{len(items)} файлов загружено"
            ),
        )
        self.root.after(400, lambda: self._clear_phase("✅ Папка загружена"))

    def _add_files_batch(self, items: List[Tuple[str, str]]):
        for name, path in items:
            self.loaded_files[name] = path
            self._file_context_selected.setdefault(name, False)
            self._cache_file_tokens(name, path)
        self._refresh_files_list()
        self._update_file_tokens()

    def _cache_file_tokens(self, name: str, path: str) -> int:
        try:
            stat = Path(path).stat()
            cache_key = (str(path), stat.st_mtime_ns, stat.st_size)
            cached = self._file_token_cache.get(name)
            if cached and cached[0] == cache_key:
                return int(cached[1])
            text = Path(path).read_text(encoding="utf-8", errors="replace")
            tokens = self._tok(text)
            self._file_token_cache[name] = (cache_key, tokens)
            return tokens
        except Exception:
            self._file_token_cache.pop(name, None)
            return 0

    def _file_tokens(self, name: str) -> int:
        path = self.loaded_files.get(name, "")
        return self._cache_file_tokens(name, path) if path else 0

    def _add_file(
        self,
        name: str,
        path: str,
        status: str = "✅",
        select_for_context: bool = False,
    ):
        del status  # статус вычисляется по наличию файла
        self.loaded_files[name] = path
        self._file_context_selected[name] = bool(select_for_context)
        self._cache_file_tokens(name, path)
        self._refresh_files_list(select_name=name)
        self._update_file_tokens()

    def _refresh_files_list(self, select_name: Optional[str] = None):
        if not hasattr(self, "files_lb"):
            return
        current_name = select_name or self._selected_file_name()
        names = sorted(self.loaded_files, key=str.lower)
        self._file_list_names = names
        self.files_lb.delete(0, tk.END)
        selected_index = None
        for index, name in enumerate(names):
            path = self.loaded_files[name]
            checked = "☑" if self._file_context_selected.get(name, False) else "☐"
            exists = "✅" if Path(path).exists() else "⚠️"
            tokens = self._file_tokens(name)
            self.files_lb.insert(
                tk.END,
                f"{checked} {exists} {name}    ~{tokens:,}",
            )
            if name == current_name:
                selected_index = index
        if selected_index is not None:
            self.files_lb.selection_set(selected_index)
            self.files_lb.see(selected_index)

    def _selected_file_name(self) -> Optional[str]:
        if not hasattr(self, "files_lb"):
            return None
        selection = self.files_lb.curselection()
        if not selection:
            return None
        index = selection[0]
        names = getattr(self, "_file_list_names", [])
        if 0 <= index < len(names):
            return names[index]
        return None

    def _on_file_dbl(self, _event):
        name = self._selected_file_name()
        if not name:
            return
        path = self.loaded_files.get(name)
        if not path:
            return
        try:
            text = Path(path).read_text(encoding="utf-8", errors="replace")
            tokens = self._tok(text)
            self._code_viewer.delete("1.0", tk.END)
            self._code_viewer.insert("1.0", text)
            self._code_tok_label.config(text=f"{name}  ~{tokens:,} токенов")
            self._show_right_tab("code")
        except Exception as exc:
            self._add_msg("system", f"⚠️ {exc}")

    def _save_current_file(self):
        name = self._selected_file_name()
        if not name:
            return
        source = self.loaded_files.get(name)
        if not source:
            return
        destination = filedialog.asksaveasfilename(
            initialfile=Path(name).name,
            defaultextension=Path(name).suffix or ".py",
        )
        if destination:
            shutil.copy(source, destination)
            self._add_msg("system", f"💾 {Path(destination).name}")

    def _remove_file(self):
        name = self._selected_file_name()
        if not name:
            return
        self.loaded_files.pop(name, None)
        self._file_context_selected.pop(name, None)
        self._file_token_cache.pop(name, None)
        self._refresh_files_list()
        self._update_file_tokens()

    def _extract_all_code(self):
        """Извлечь все блоки кода из последнего ответа LLM."""
        for message in reversed(self.chat_history):
            if message.role != "assistant":
                continue
            blocks = re.findall(r"```[^\n]*\n(.*?)```", message.content, re.DOTALL)
            if blocks:
                code = ("\n\n# " + "─" * 50 + "\n\n").join(blocks)
                self._code_viewer.delete("1.0", tk.END)
                self._code_viewer.insert("1.0", code)
                tokens = self._tok(code)
                self._code_tok_label.config(
                    text=f"{len(blocks)} блоков  ~{tokens:,} токенов"
                )
                self._show_right_tab("code")
                self._status.config(text=f"✅ Извлечено {len(blocks)} блоков кода")
                return
        self._add_msg("system", "⚠️ Нет блоков кода в последнем ответе")

    def _save_code_viewer(self):
        code = self._code_viewer.get("1.0", tk.END).strip()
        if not code:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".py",
            filetypes=[("Python", "*.py"), ("Text", "*.txt"), ("All", "*.*")],
        )
        if path:
            Path(path).write_text(code, encoding="utf-8")
            self._status.config(text=f"💾 Сохранено: {Path(path).name}")

    def _copy_code_viewer(self):
        code = self._code_viewer.get("1.0", tk.END)
        self.root.clipboard_clear()
        self.root.clipboard_append(code)
        self._status.config(text="📋 Код скопирован")

    def _code_to_input(self):
        code = self._code_viewer.get("1.0", tk.END).strip()
        if code:
            self.input_text.delete("1.0", tk.END)
            self.input_text.insert("1.0", code)
            self.input_text.focus_set()

    def _clear_code_viewer(self):
        self._code_viewer.delete("1.0", tk.END)
        self._code_tok_label.config(text="")
