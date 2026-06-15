"""Часть главного окна LLM Assistant.

Модуль выделен из монолитного файла v9 для удобства сопровождения.
"""

from .common import *

class UtilitiesMixin:
    def _template_menu(self):
        m = tk.Menu(self.root, tearoff=0)
        for label in TEMPLATES:
            m.add_command(label=label,
                          command=lambda l=label: self._apply_template(l))
        m.tk_popup(self.root.winfo_pointerx(), self.root.winfo_pointery())

    def _apply_template(self, label: str):
        prefix = TEMPLATES[label]
        cur    = self.input_text.get("1.0", tk.END).strip()
        self.input_text.delete("1.0", tk.END)
        self.input_text.insert("1.0", prefix + cur)
        self.input_text.focus_set()

    def _layout_preset(self, mode: str):
        if mode == "code":
            self.left_pw.sashpos(0, int(self.root.winfo_height() * 0.35))
            self.nb.select(self.tab_code)
        elif mode == "read":
            self.left_pw.sashpos(0, int(self.root.winfo_height() * 0.85))
            self.nb.select(self.tab_files)
        else:
            self.left_pw.sashpos(0, int(self.root.winfo_height() * 0.62))
            self.nb.select(self.tab_files)
        self._status.config(text=f"📐 Режим: {mode}")

    def _toggle_right_panel(self):
        if self._show_right.get():
            self.main_pw.add(self.right_frame, weight=2)
        else:
            self.main_pw.forget(self.right_frame)

    def _popup(self, menu: tk.Menu, event):
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _copy_selected(self):
        try:
            sel = self.chat_text.get(tk.SEL_FIRST, tk.SEL_LAST)
            self.root.clipboard_clear()
            self.root.clipboard_append(sel)
            self._status.config(text="📋 Скопировано")
        except Exception:
            pass

    def _copy_all(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.chat_text.get("1.0", tk.END))
        self._status.config(text="📋 Весь чат скопирован")

    def _save_selected(self):
        try:
            sel  = self.chat_text.get(tk.SEL_FIRST, tk.SEL_LAST)
            path = filedialog.asksaveasfilename(defaultextension=".txt",
                                                filetypes=[("Text","*.txt"),("Markdown","*.md")])
            if path:
                Path(path).write_text(sel, encoding="utf-8")
                self._status.config(text=f"💾 {Path(path).name}")
        except Exception:
            pass

    def _export_last_response(self):
        for msg in reversed(self.chat_history):
            if msg.role == "assistant":
                path = filedialog.asksaveasfilename(
                    defaultextension=".md",
                    filetypes=[("Markdown","*.md"),("Text","*.txt")]
                )
                if path:
                    hdr = (f"# LLM Ответ\n\nДата: {msg.timestamp}\n"
                           f"Модель: {self._model_name}\nСервер: {self._server_url}\n\n---\n\n")
                    Path(path).write_text(hdr + msg.content, encoding="utf-8")
                    self._status.config(text=f"📤 {Path(path).name}")
                return
        self._add_msg("system", "⚠️ Нет ответов для экспорта")

    def _export_all_code(self):
        """Собрать весь код из всего диалога в один файл."""
        all_code = []
        for msg in self.chat_history:
            if msg.role == "assistant":
                blocks = re.findall(r"```[^\n]*\n(.*?)```", msg.content, re.DOTALL)
                all_code.extend(blocks)
        if not all_code:
            self._add_msg("system", "⚠️ Блоков кода не найдено")
            return
        code = f"# Экспорт кода — {datetime.now()}\n# {self._model_name}\n\n"
        code += "\n\n# " + "─" * 50 + "\n\n".join(all_code)
        path = filedialog.asksaveasfilename(
            defaultextension=".py",
            filetypes=[("Python","*.py"),("Text","*.txt")]
        )
        if path:
            Path(path).write_text(code, encoding="utf-8")
            self._status.config(text=f"📤 {len(all_code)} блоков → {Path(path).name}")

    def _save_conversation(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".md",
            filetypes=[("Markdown","*.md"),("Text","*.txt")]
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"# LLM Assistant v9\n\nМодель: {self._model_name}\n\n---\n\n")
                for msg in self.chat_history:
                    f.write(f"## {msg.role.upper()} [{msg.timestamp}]\n\n{msg.content}\n\n---\n\n")
            self._status.config(text=f"💾 {Path(path).name}")

    def _clear_chat(self):
        """Безопасно очистить историю через механизм нового контекста."""
        self._reset_context("chat")

    def _clear_input(self):
        self.input_text.delete("1.0", tk.END)

    def _show_stats(self):
        tokens = self._context_token_breakdown()
        total = tokens["total"]
        self._add_msg(
            "system",
            f"📊 Активный контекст модели:\n"
            f"  Чат (последние 20): ~{tokens['chat']:,}\n"
            f"  Файлы:              ~{tokens['files']:,}  ({len(self.loaded_files)} файлов)\n"
            f"  Веб:                 ~{tokens['web']:,}  "
            f"({sum(1 for result in self.web_results if result.fetched)} страниц)\n"
            f"  ─────────────────────────\n"
            f"  Итого: ~{total:,} / {CONTEXT_BUDGET:,} "
            f"({total / CONTEXT_BUDGET * 100:.0f}%)\n"
            f"  Полная история сессии: {len(self.chat_history)} сообщений\n"
            f"  Окно модели: {MAX_CONTEXT_TOKENS:,} токенов\n"
            f"  max_tokens ответа: {int(self._max_tokens_var.get())}\n"
            f"  Температура: {self._temperature_var.get():.1f}\n"
            f"  Сервер: {self._server_var.get()} ({self._server_url})\n"
            f"  Модель: {self._model_name}\n"
            f"  Сессия: {self._session_name}"
        )

    def _welcome(self):
        self._add_msg("system",
            "🚀 LLM Assistant v9 — Qwen3-Coder-30B\n\n"
            "🔍 Умный поиск (вкладка 🌐 Веб):\n"
            "  🐙 GitHub — реальный код из репозиториев (бесплатно)\n"
            "  🟠 Stack Overflow — решения ошибок (бесплатно)\n"
            "  🔷 Tavily — AI-ready контент (1000 req/month бесплатно)\n"
            "  🦆 DuckDuckGo — fallback без ключа\n"
            "  🔀 Авто — выбирает источник по ключевым словам запроса\n"
            "  🔑 Настройка ключей — кнопка в тулбаре или в поиске\n\n"
            "⚡ При затыке:\n"
            "  Авто-переключение: GitHub → SO → Tavily → DuckDuckGo\n"
            "  Статус источника виден в строке под поиском\n\n"
            "📐 Раскладки: [Код] [Чтение] [Стандарт]\n"
            "💾 Сессия сохраняется автоматически при закрытии\n"
            f"  Ключи сохраняются в сессии: {SESSION_DIR}\n\n"
            f"🔢 Контекст: {CONTEXT_BUDGET:,} токенов  •  max_tokens: до 32 000\n"
            "  Слайдеры в тулбаре сверху"
        )
