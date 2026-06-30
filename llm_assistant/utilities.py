"""Часть главного окна LLM Assistant.

Модуль выделен из монолитного файла v9 для удобства сопровождения.
"""

from .common import *  # noqa: F401,F403


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
            # Большое поле ввода + Code Viewer справа
            self.left_pw.sashpos(0, int(self.root.winfo_height() * 0.35))
            self._show_right_tab("code")
        elif mode == "read":
            # Чат во весь экран
            self.left_pw.sashpos(0, int(self.root.winfo_height() * 0.85))
            self._show_right_tab("files")
        else:  # std
            self.left_pw.sashpos(0, int(self.root.winfo_height() * 0.62))
            self._show_right_tab("files")
        self._status.config(text=f"📐 Режим: {mode}")

    def _toggle_right_panel(self):
        if self._show_right.get():
            self._show_right_tab("files")
        else:
            self._hide_right_panel()

    def _popup(self, menu: tk.Menu, event):
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _copy_selected(self):
        # Единая функция сохраняет яркую подсветку и показывает окно
        # подтверждения копирования.
        return self._copy_widget_selection(self.chat_text)

    def _copy_all(self):
        self._select_all_widget_text(self.chat_text)
        return self._copy_widget_selection(self.chat_text)

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
                f.write(f"# LLM Assistant v2.0.0\n\nМодель: {self._model_name}\n\n---\n\n")
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
        window = self._effective_context_window()
        output = int(self._max_tokens_var.get())
        safety = max(512, int(window * 0.03))
        projected = total + output + safety
        last = getattr(self, "_last_generation_stats", {})
        last_text = ""
        if last:
            last_text = (
                f"\n  Последний запрос: вход {last.get('prompt_tokens', 0):,}, "
                f"выход {last.get('completion_tokens', 0):,}, "
                f"причина {last.get('finish_reason', 'unknown')}"
            )
        self._add_msg(
            "system",
            f"📊 Активный контекст модели:\n"
            f"  Чат (последние 20): ~{tokens['chat']:,}\n"
            f"  Файлы:              ~{tokens['files']:,}  ({len(self.loaded_files)} файлов)\n"
            f"  Веб:                 ~{tokens['web']:,}  "
            f"({sum(1 for result in self.web_results if result.fetched)} страниц)\n"
            f"  ─────────────────────────\n"
            f"  Текущий вход:        ~{total:,}\n"
            f"  Резерв ответа:       {output:,}\n"
            f"  Технический запас:   ~{safety:,}\n"
            f"  Окно сервера:        {window:,}\n"
            f"  Прогноз заполнения:  {projected / window * 100:.0f}%\n"
            f"  Полная история:      {len(self.chat_history)} сообщений\n"
            f"  Температура:         {self._temperature_var.get():.1f}\n"
            f"  Сервер:              {self._server_var.get()} ({self._server_url})\n"
            f"  Модель:              {self._model_name}\n"
            f"  Сессия:              {self._session_name}"
            f"{last_text}"
        )

    def _welcome(self):
        self._add_msg(
            "system",
            "LLM Assistant v2.0.0 готов к работе.\n\n"
            "• Чат занимает основную часть окна.\n"
            "• Файлы, веб, код и настройки открываются справа.\n"
            "• Обычное выделение мышью и Ctrl+C работают для текста и кода.\n"
            "• Ctrl+клик по блоку кода открывает его в Code Viewer.\n"
            "• Во время генерации кнопка Отправить заменяется кнопкой Остановить.\n"
            "• Context Length и Max Output настраиваются отдельно и сохраняются в сессии."
        )
