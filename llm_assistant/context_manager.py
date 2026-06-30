"""Умный выбор файлов и построение ограниченного контекста проекта."""

from .common import *  # noqa: F401,F403


class ContextManagerMixin:
    CONTEXT_MODE_LABELS = {
        "auto": "Авто",
        "selected": "Только отмеченные",
        "all": "Весь проект",
    }

    def _context_mode_label(self, mode: str) -> str:
        code = self._ui_language_code() if hasattr(self, "_ui_language_code") else "ru"
        labels = {
            "ru": {"auto": "Авто", "selected": "Только отмеченные", "all": "Весь проект"},
            "en": {"auto": "Auto", "selected": "Selected only", "all": "Entire project"},
            "bi": {"auto": "Auto / Авто", "selected": "Selected / Отмеченные", "all": "Entire / Весь проект"},
        }
        return labels.get(code, labels["ru"]).get(mode, mode)

    _CONTEXT_STOP_WORDS = {
        "этот", "эта", "это", "эти", "того", "того", "кода", "код", "файл",
        "файла", "файлы", "проект", "проекта", "проверь", "посмотри", "нужно",
        "сделать", "добавить", "исправить", "работает", "работать", "почему",
        "как", "что", "для", "или", "при", "без", "весь", "все", "там",
        "the", "this", "that", "with", "from", "into", "code", "file",
        "files", "project", "check", "fix", "add", "make", "why", "how",
    }

    def _context_options_snapshot(self) -> Dict[str, object]:
        """Снять все настройки контекста в главном Tk-потоке."""
        try:
            budget = int(self._file_context_budget_var.get())
        except Exception:
            budget = 32768
        context_cap = (
            self._effective_input_budget()
            if hasattr(self, "_effective_input_budget")
            else CONTEXT_BUDGET
        )
        return {
            "mode": self._context_mode_var.get(),
            "budget": max(1000, min(budget, context_cap)),
            "selected_files": [
                name
                for name, selected in self._file_context_selected.items()
                if selected and name in self.loaded_files
            ],
            "loaded_files": dict(self.loaded_files),
        }

    @classmethod
    def _context_query_terms(cls, prompt: str) -> List[str]:
        terms = re.findall(r"[A-Za-zА-Яа-яЁё_][A-Za-zА-Яа-яЁё0-9_.-]{2,}", prompt.lower())
        result: List[str] = []
        for term in terms:
            cleaned = term.strip("._-")
            if len(cleaned) < 3 or cleaned in cls._CONTEXT_STOP_WORDS:
                continue
            if cleaned not in result:
                result.append(cleaned)
        return result[:40]

    def _read_context_file(self, path: str) -> str:
        try:
            return Path(path).read_text(encoding="utf-8", errors="replace")
        except Exception:
            return ""

    def _score_context_file(
        self,
        name: str,
        text: str,
        prompt_l: str,
        terms: List[str],
        pinned: bool,
    ) -> Tuple[int, List[str]]:
        """Оценить полезность файла для текущего запроса."""
        path_l = name.lower().replace("\\", "/")
        base_l = Path(name).name.lower()
        stem_l = Path(name).stem.lower()
        sample_l = text[:200_000].lower()

        score = 0
        reasons: List[str] = []

        if pinned:
            score += 1000
            reasons.append("отмечен вручную")
        if path_l and path_l in prompt_l:
            score += 600
            reasons.append("путь указан в запросе")
        elif base_l and base_l in prompt_l:
            score += 450
            reasons.append("имя указано в запросе")
        elif len(stem_l) >= 3 and re.search(rf"(?<!\w){re.escape(stem_l)}(?!\w)", prompt_l):
            score += 280
            reasons.append("модуль указан в запросе")

        path_hits = [term for term in terms if term in path_l]
        if path_hits:
            score += min(240, len(path_hits) * 55)
            reasons.append("совпадение по имени")

        content_hits = 0
        for term in terms:
            if term in sample_l:
                content_hits += min(sample_l.count(term), 6)
        if content_hits:
            score += min(220, content_hits * 7)
            reasons.append("совпадение в коде")

        if base_l in {"main.py", "app.py", "index.js", "index.ts", "main.cpp", "main.c"}:
            score += 35
            reasons.append("точка входа")
        if base_l.startswith("readme"):
            score += 8

        return score, reasons

    @staticmethod
    def _python_local_imports(text: str) -> List[str]:
        modules: List[str] = []
        patterns = (
            r"^\s*from\s+\.?([A-Za-z_][\w.]*)\s+import\s+",
            r"^\s*import\s+([A-Za-z_][\w.]*)",
        )
        for pattern in patterns:
            for match in re.finditer(pattern, text, flags=re.MULTILINE):
                module = match.group(1).split(".")[-1]
                if module and module not in modules:
                    modules.append(module)
        return modules

    def _plan_file_context(
        self,
        prompt: str,
        options: Dict[str, object],
    ) -> List[Dict[str, object]]:
        """Построить ранжированный план файлов без формирования итогового текста."""
        loaded_files = dict(options.get("loaded_files", {}))
        selected = set(options.get("selected_files", []))
        mode = str(options.get("mode", "auto"))
        prompt_l = prompt.lower()
        terms = self._context_query_terms(prompt)

        candidates: List[Dict[str, object]] = []
        texts: Dict[str, str] = {}
        for name, path in loaded_files.items():
            if not path or not Path(path).exists():
                continue
            text = self._read_context_file(path)
            if not text:
                continue
            texts[name] = text
            tokens = self._tok(text)
            pinned = name in selected
            score, reasons = self._score_context_file(
                name, text, prompt_l, terms, pinned
            )
            candidates.append({
                "name": name,
                "path": path,
                "tokens": tokens,
                "score": score,
                "reasons": reasons,
                "pinned": pinned,
                "text": text,
            })

        if mode == "selected":
            result = [item for item in candidates if item["pinned"]]
            return sorted(result, key=lambda item: str(item["name"]).lower())

        if mode == "all":
            return sorted(
                candidates,
                key=lambda item: (
                    -int(item["score"]),
                    str(item["name"]).lower(),
                ),
            )

        # Авто: ручные отметки являются закреплёнными, затем идёт релевантность.
        by_stem: Dict[str, List[Dict[str, object]]] = {}
        for item in candidates:
            stem = Path(str(item["name"])).stem.lower()
            by_stem.setdefault(stem, []).append(item)

        preliminary = sorted(
            candidates,
            key=lambda item: (-int(item["score"]), int(item["tokens"])),
        )[:10]
        for item in preliminary:
            if int(item["score"]) <= 0:
                continue
            if Path(str(item["name"])).suffix.lower() != ".py":
                continue
            for module in self._python_local_imports(str(item["text"])):
                for dependency in by_stem.get(module.lower(), []):
                    dependency["score"] = int(dependency["score"]) + 90
                    reasons = list(dependency["reasons"])
                    if "локальная зависимость" not in reasons:
                        reasons.append("локальная зависимость")
                    dependency["reasons"] = reasons

        relevant = [
            item for item in candidates
            if item["pinned"] or int(item["score"]) > 0
        ]

        # При общем запросе без ключевых совпадений всё равно берём точки входа
        # и несколько небольших файлов, а не весь проект.
        if not relevant:
            entries = [
                item for item in candidates
                if Path(str(item["name"])).name.lower()
                in {"main.py", "app.py", "main.cpp", "main.c", "index.js", "index.ts"}
            ]
            relevant.extend(entries)
            for item in sorted(candidates, key=lambda value: int(value["tokens"])):
                if item not in relevant:
                    relevant.append(item)
                if len(relevant) >= 5:
                    break

        return sorted(
            relevant,
            key=lambda item: (
                0 if item["pinned"] else 1,
                -int(item["score"]),
                int(item["tokens"]),
            ),
        )

    def _extract_relevant_chunks(
        self,
        text: str,
        terms: List[str],
        token_budget: int,
    ) -> str:
        """Вырезать несколько релевантных окон из большого файла."""
        max_chars = max(800, token_budget * 4)
        if len(text) <= max_chars:
            return text

        lines = text.splitlines()
        hit_indexes: List[int] = []
        lowered = [line.lower() for line in lines]
        for index, line in enumerate(lowered):
            if any(term in line for term in terms):
                hit_indexes.append(index)

        if not hit_indexes:
            # Без совпадений оставляем начало и объявления функций/классов.
            hit_indexes = [0]
            for index, line in enumerate(lines):
                stripped = line.lstrip()
                if stripped.startswith(("def ", "class ", "async def ", "function ")):
                    hit_indexes.append(index)
                if len(hit_indexes) >= 8:
                    break

        windows: List[Tuple[int, int]] = []
        radius = 24
        for index in hit_indexes[:20]:
            start = max(0, index - radius)
            end = min(len(lines), index + radius + 1)
            if windows and start <= windows[-1][1] + 8:
                windows[-1] = (windows[-1][0], max(windows[-1][1], end))
            else:
                windows.append((start, end))

        parts: List[str] = []
        used = 0
        for start, end in windows:
            header = f"\n... [строки {start + 1}–{end}] ...\n"
            body = "\n".join(lines[start:end])
            block = header + body
            if used + len(block) > max_chars:
                remaining = max_chars - used
                if remaining > 300:
                    parts.append(block[:remaining])
                break
            parts.append(block)
            used += len(block)
            if used >= max_chars:
                break

        result = "".join(parts).strip()
        return result or text[:max_chars]

    def _build_file_context(
        self,
        prompt: str,
        options: Optional[Dict[str, object]] = None,
    ) -> Tuple[str, int, Dict[str, object]]:
        """Собрать контекст по выбранному режиму, не превышая бюджет."""
        if options is None:
            options = self._context_options_snapshot()
        loaded_files = dict(options.get("loaded_files", {}))
        if not loaded_files:
            return "", 0, {"included": [], "skipped": [], "mode": "none"}

        mode = str(options.get("mode", "auto"))
        budget = max(0, int(options.get("budget", 32768)))
        plan = self._plan_file_context(prompt, options)
        terms = self._context_query_terms(prompt)

        if mode == "selected" and not plan:
            return (
                "\n\n⚠️ РЕЖИМ КОНТЕКСТА: только отмеченные файлы, "
                "но ни один файл не отмечен.",
                0,
                {"included": [], "skipped": [], "mode": mode},
            )

        parts: List[str] = []
        included: List[Dict[str, object]] = []
        skipped: List[str] = []
        used = 0

        for item in plan:
            remaining = budget - used
            if remaining < 200:
                skipped.append(str(item["name"]))
                continue

            text = str(item["text"])
            full_tokens = int(item["tokens"])
            pinned = bool(item["pinned"])

            if mode == "auto":
                per_file_cap = 16000 if pinned or int(item["score"]) >= 400 else 8000
                allocation = min(remaining, full_tokens, per_file_cap)
            else:
                allocation = min(remaining, full_tokens)

            partial = allocation < full_tokens
            content = (
                self._extract_relevant_chunks(text, terms, allocation)
                if partial
                else text
            )
            actual_tokens = min(allocation, self._tok(content))
            if actual_tokens <= 0:
                skipped.append(str(item["name"]))
                continue

            marker = (
                f"ЧАСТИЧНО: ~{actual_tokens:,} из ~{full_tokens:,} токенов"
                if partial
                else f"~{actual_tokens:,} токенов"
            )
            reason = ", ".join(list(item["reasons"])[:3]) or "по порядку проекта"
            parts.append(
                f"\n{'─' * 72}\n"
                f"📄 {item['name']}  ({marker}; {reason})\n"
                f"{'─' * 72}\n{content}"
            )
            included.append({
                "name": str(item["name"]),
                "tokens": actual_tokens,
                "full_tokens": full_tokens,
                "partial": partial,
                "score": int(item["score"]),
                "reason": reason,
            })
            used += actual_tokens

        planned_names = {str(item["name"]) for item in plan}
        included_names = {str(item["name"]) for item in included}
        skipped.extend(sorted(planned_names - included_names - set(skipped)))

        if not parts:
            return "", 0, {"included": [], "skipped": skipped, "mode": mode}

        mode_label = self._context_mode_label(mode)
        header = (
            f"\n\n{'═' * 72}\n"
            f"КОНТЕКСТ ПРОЕКТА · режим: {mode_label} · "
            f"{len(included)} файлов · ~{used:,}/{budget:,} токенов\n"
            f"{'═' * 72}"
        )
        context = header + "".join(parts)
        if skipped:
            context += (
                "\n\n⚠️ Не вошли из-за бюджета или низкого приоритета: "
                + ", ".join(skipped[:30])
            )

        return context, used, {
            "included": included,
            "skipped": skipped,
            "mode": mode,
            "budget": budget,
        }

    def _on_context_settings_changed(self, *_args):
        self._update_file_tokens()
        self._autosave_session()

    def _select_all_context_files(self):
        for name in self.loaded_files:
            self._file_context_selected[name] = True
        self._refresh_files_list()
        self._update_file_tokens()

    def _clear_context_file_selection(self):
        for name in self.loaded_files:
            self._file_context_selected[name] = False
        self._refresh_files_list()
        self._update_file_tokens()

    def _invert_context_file_selection(self):
        for name in self.loaded_files:
            self._file_context_selected[name] = not self._file_context_selected.get(name, False)
        self._refresh_files_list()
        self._update_file_tokens()

    def _toggle_context_file_at_index(self, index: int):
        if index < 0 or index >= len(getattr(self, "_file_list_names", [])):
            return
        name = self._file_list_names[index]
        self._file_context_selected[name] = not self._file_context_selected.get(name, False)
        self._refresh_files_list(select_name=name)
        self._update_file_tokens()

    def _on_file_list_click(self, event):
        """Переключать флажок только при клике по левой части строки."""
        if event.x > 38:
            return None
        index = self.files_lb.nearest(event.y)
        self._toggle_context_file_at_index(index)
        return "break"

    def _on_file_list_space(self, _event):
        selection = self.files_lb.curselection()
        if selection:
            self._toggle_context_file_at_index(selection[0])
        return "break"

    def _preview_context_selection(self):
        prompt = self.input_text.get("1.0", "end-1c").strip()
        options = self._context_options_snapshot()
        self._set_phase(1, 2, "Анализ файлов для контекста...", spin=True)

        def worker():
            try:
                _ctx, used, summary = self._build_file_context(prompt, options)
                self.root.after(
                    0,
                    lambda: self._show_context_preview_window(prompt, used, summary),
                )
                self.root.after(0, lambda: self._clear_phase("✅ План контекста готов"))
            except Exception as exc:
                error = str(exc)
                self.root.after(0, lambda: self._clear_phase("❌ Ошибка контекста"))
                self.root.after(
                    0,
                    lambda: messagebox.showerror(
                        "Предпросмотр контекста", error, parent=self.root
                    ),
                )

        threading.Thread(target=worker, daemon=True).start()

    def _show_context_preview_window(
        self,
        prompt: str,
        used: int,
        summary: Dict[str, object],
    ):
        win = tk.Toplevel(self.root)
        win.title("👁 Предпросмотр контекста")
        win.geometry("900x650")
        win.configure(bg=self.C["bg"])
        win.transient(self.root)

        mode = self._context_mode_label(str(summary.get("mode", "auto")))
        budget = int(summary.get("budget", 0) or 0)
        tk.Label(
            win,
            text=f"Режим: {mode}    Будет отправлено файлов: {len(summary.get('included', []))}    ~{used:,}/{budget:,} токенов",
            bg=self.C["bg"], fg=self.C["gold"],
            font=("Segoe UI", 11, "bold"),
        ).pack(fill=tk.X, padx=12, pady=(12, 4))
        tk.Label(
            win,
            text=(f"Запрос: {prompt[:180]}" if prompt else "Запрос пока пуст — показан общий план"),
            bg=self.C["bg"], fg="#999", anchor=tk.W,
            font=("Segoe UI", 9),
        ).pack(fill=tk.X, padx=12, pady=(0, 8))

        columns = ("tokens", "type", "reason")
        tree = ttk.Treeview(win, columns=columns, show="tree headings")
        tree.heading("#0", text="Файл")
        tree.heading("tokens", text="Токены")
        tree.heading("type", text="Передача")
        tree.heading("reason", text="Почему выбран")
        tree.column("#0", width=310)
        tree.column("tokens", width=100, anchor=tk.E)
        tree.column("type", width=110)
        tree.column("reason", width=280)
        tree.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)

        for item in summary.get("included", []):
            tree.insert(
                "", tk.END,
                text=str(item["name"]),
                values=(
                    f"~{int(item['tokens']):,}",
                    "фрагменты" if item["partial"] else "целиком",
                    item["reason"],
                ),
            )

        skipped = list(summary.get("skipped", []))
        if skipped:
            tk.Label(
                win,
                text="Не вошли: " + ", ".join(skipped[:25]),
                bg=self.C["bg"], fg="#d99", anchor=tk.W,
                wraplength=850, justify=tk.LEFT,
                font=("Segoe UI", 9),
            ).pack(fill=tk.X, padx=12, pady=(0, 8))

        tk.Button(
            win, text="Закрыть", command=win.destroy,
            bg=self.C["accent"], fg="white", relief=tk.FLAT,
            padx=18, pady=7,
        ).pack(pady=(0, 12))
