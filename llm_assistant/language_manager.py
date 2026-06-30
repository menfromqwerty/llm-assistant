"""Мгновенная локализация интерфейса LLM Assistant.

Переключатель языка относится только к интерфейсу приложения. Язык ответа
модели определяется языком последнего запроса пользователя.
"""

from __future__ import annotations

import locale
from typing import Dict

from .common import *  # noqa: F401,F403


# В режиме EN + RU сохраняем компактный смешанный интерфейс, чтобы верхняя
# панель не становилась слишком широкой. Русский и English переводят весь
# основной интерфейс немедленно, без перезапуска приложения.
UI_TEXTS: Dict[str, Dict[str, str]] = {
    # Главное меню
    "menu_file": {"ru": "📁 Файл", "en": "📁 File", "bi": "📁 File / Файл"},
    "open_file": {"ru": "📄 Открыть файл", "en": "📄 Open file", "bi": "📄 Open / Открыть файл"},
    "open_zip": {"ru": "📦 Открыть ZIP", "en": "📦 Open ZIP", "bi": "📦 Open ZIP"},
    "open_folder": {"ru": "📂 Открыть папку", "en": "📂 Open folder", "bi": "📂 Folder / Папка"},
    "save_dialog": {"ru": "💾 Сохранить диалог", "en": "💾 Save conversation", "bi": "💾 Save / Сохранить диалог"},
    "export_code": {"ru": "📤 Экспорт кода", "en": "📤 Export code", "bi": "📤 Export / Экспорт кода"},
    "exit": {"ru": "🚪 Выход", "en": "🚪 Exit", "bi": "🚪 Exit / Выход"},
    "menu_server": {"ru": "🖥️ Сервер", "en": "🖥️ Server", "bi": "🖥️ Server / Сервер"},
    "custom_url": {"ru": "🔧 Свой URL...", "en": "🔧 Custom URL...", "bi": "🔧 Custom URL / Свой URL..."},
    "check_connection": {"ru": "🔄 Проверить соединение", "en": "🔄 Check connection", "bi": "🔄 Check / Проверить соединение"},
    "start_selected_server": {"ru": "▶ Запустить выбранный сервер", "en": "▶ Start selected server", "bi": "▶ Start / Запустить сервер"},
    "menu_view": {"ru": "👁️ Вид", "en": "👁️ View", "bi": "👁️ View / Вид"},
    "mode_code": {"ru": "📐 Режим: Код", "en": "📐 Mode: Code", "bi": "📐 Mode / Режим: Code"},
    "mode_read": {"ru": "📖 Режим: Чтение", "en": "📖 Mode: Reading", "bi": "📖 Mode / Режим: Reading"},
    "mode_standard": {"ru": "⚖️ Режим: Стандарт", "en": "⚖️ Mode: Standard", "bi": "⚖️ Mode / Режим: Standard"},
    "right_panel": {"ru": "📋 Правая панель", "en": "📋 Right panel", "bi": "📋 Right panel / Правая панель"},
    "clear_chat": {"ru": "🗑️ Очистить чат", "en": "🗑️ Clear chat", "bi": "🗑️ Clear / Очистить чат"},
    "statistics": {"ru": "📊 Статистика", "en": "📊 Statistics", "bi": "📊 Statistics / Статистика"},
    "menu_session": {"ru": "💾 Сессия", "en": "💾 Session", "bi": "💾 Session / Сессия"},
    "save_session": {"ru": "💾 Сохранить сессию", "en": "💾 Save session", "bi": "💾 Save / Сохранить сессию"},
    "save_as": {"ru": "💾 Сохранить как...", "en": "💾 Save as...", "bi": "💾 Save as / Сохранить как..."},
    "load_session": {"ru": "📂 Загрузить сессию...", "en": "📂 Load session...", "bi": "📂 Load / Загрузить сессию..."},
    "new_context": {"ru": "♻ Новый контекст...", "en": "♻ New context...", "bi": "♻ New / Новый контекст..."},
    "new_clean_session": {"ru": "🆕 Новая чистая сессия", "en": "🆕 New clean session", "bi": "🆕 Clean / Чистая сессия"},
    "session_list": {"ru": "📋 Список сессий", "en": "📋 Session list", "bi": "📋 Sessions / Сессии"},
    "delete_current": {"ru": "🗑️ Удалить текущую", "en": "🗑️ Delete current", "bi": "🗑️ Delete / Удалить текущую"},
    "templates": {"ru": "📋 Шаблоны", "en": "📋 Templates", "bi": "📋 Templates / Шаблоны"},
    "language_menu": {"ru": "🌐 Язык", "en": "🌐 Language", "bi": "🌐 Language / Язык"},
    "menu_security": {"ru": "🔐 Защита", "en": "🔐 Security", "bi": "🔐 Security / Защита"},
    "security_settings": {"ru": "⚙ Настройки защиты...", "en": "⚙ Security settings...", "bi": "⚙ Security / Настройки защиты..."},
    "lock_now": {"ru": "🔒 Заблокировать сейчас", "en": "🔒 Lock now", "bi": "🔒 Lock / Заблокировать сейчас"},

    # Пункты выбора языка и шаблонов
    "lang_bilingual": {"ru": "English + Русский", "en": "English + Russian", "bi": "English + Русский"},
    "lang_russian": {"ru": "Русский", "en": "Russian", "bi": "Русский / Russian"},
    "lang_english": {"ru": "Английский", "en": "English", "bi": "English / Английский"},
    "lang_auto": {"ru": "Авто", "en": "Auto", "bi": "Auto / Авто"},
    "tpl_explain": {"ru": "💬 Объясни код", "en": "💬 Explain code", "bi": "💬 Explain / Объяснить код"},
    "tpl_refactor": {"ru": "🔧 Рефакторинг", "en": "🔧 Refactor", "bi": "🔧 Refactor / Рефакторинг"},
    "tpl_tests": {"ru": "🧪 Написать тесты", "en": "🧪 Write tests", "bi": "🧪 Tests / Написать тесты"},
    "tpl_bugs": {"ru": "🐛 Найти баги", "en": "🐛 Find bugs", "bi": "🐛 Find bugs / Найти баги"},
    "tpl_docs": {"ru": "📝 Документация", "en": "📝 Documentation", "bi": "📝 Docs / Документация"},
    "tpl_optimize": {"ru": "⚡ Оптимизировать", "en": "⚡ Optimize", "bi": "⚡ Optimize / Оптимизировать"},
    "tpl_web": {"ru": "🌐 Веб-анализ", "en": "🌐 Web analysis", "bi": "🌐 Web analysis / Веб-анализ"},
    "tpl_search": {"ru": "🔍 Поиск-анализ", "en": "🔍 Search analysis", "bi": "🔍 Search analysis / Поиск-анализ"},

    # Минималистичная навигация v18
    "new_chat": {"ru": "＋ Новый чат", "en": "＋ New chat", "bi": "＋ New / Новый чат"},
    "collapse": {"ru": "◀  Свернуть", "en": "◀  Collapse", "bi": "◀  Collapse / Свернуть"},
    "sessions_nav": {"ru": "💬  Сессии", "en": "💬  Sessions", "bi": "💬  Sessions / Сессии"},
    "files_nav": {"ru": "📁  Файлы", "en": "📁  Files", "bi": "📁  Files / Файлы"},
    "web_nav": {"ru": "🌐  Поиск", "en": "🌐  Search", "bi": "🌐  Search / Поиск"},
    "code_nav": {"ru": "⚡  Код", "en": "⚡  Code", "bi": "⚡  Code / Код"},
    "context_nav": {"ru": "♻  Контекст", "en": "♻  Context", "bi": "♻  Context / Контекст"},
    "clear_nav": {"ru": "🧹  Очистить", "en": "🧹  Clear", "bi": "🧹  Clear / Очистить"},
    "settings_nav": {"ru": "⚙  Настройки", "en": "⚙  Settings", "bi": "⚙  Settings / Настройки"},
    "panel": {"ru": "Панель", "en": "Panel", "bi": "Panel / Панель"},
    "conversation_plain": {"ru": "Диалог", "en": "Conversation", "bi": "Conversation / Диалог"},
    "send_compact": {"ru": "➤ Отправить", "en": "➤ Send", "bi": "➤ Send / Отправить"},
    "stop_compact": {"ru": "■ Остановить", "en": "■ Stop", "bi": "■ Stop / Остановить"},
    "settings_tab": {"ru": "⚙ Настройки", "en": "⚙ Settings", "bi": "⚙ Settings / Настройки"},

    # Верхняя панель
    "file_short": {"ru": "📄 Файл", "en": "📄 File", "bi": "📄 File / Файл"},
    "folder_short": {"ru": "📂 Папка", "en": "📂 Folder", "bi": "📂 Folder / Папка"},
    "search": {"ru": "🔍 Поиск", "en": "🔍 Search", "bi": "🔍 Search / Поиск"},
    "url_to_text": {"ru": "🌐 URL→Текст", "en": "🌐 URL→Text", "bi": "🌐 URL→Text / Текст"},
    "api_keys": {"ru": "🔑 API ключи", "en": "🔑 API keys", "bi": "🔑 API keys / Ключи"},
    "extract_code": {"ru": "⚡ Извлечь код", "en": "⚡ Extract code", "bi": "⚡ Extract / Извлечь код"},
    "tokens": {"ru": "📊 Токены", "en": "📊 Tokens", "bi": "📊 Tokens / Токены"},
    "temperature": {"ru": "Темп.:", "en": "Temp:", "bi": "Temp:"},
    "max_tokens": {"ru": "Макс. токенов:", "en": "Max tokens:", "bi": "Max tokens:"},

    # Панель сессии
    "work": {"ru": "РАБОТА:", "en": "WORK:", "bi": "WORK / РАБОТА:"},
    "save_upper": {"ru": "💾 СОХРАНИТЬ", "en": "💾 SAVE", "bi": "💾 SAVE / СОХРАНИТЬ"},
    "save_as_upper": {"ru": "💾 СОХРАНИТЬ КАК...", "en": "💾 SAVE AS...", "bi": "💾 SAVE AS / СОХРАНИТЬ КАК..."},
    "open_session_upper": {"ru": "📂 ОТКРЫТЬ СЕССИЮ", "en": "📂 OPEN SESSION", "bi": "📂 OPEN / ОТКРЫТЬ СЕССИЮ"},
    "new_context_upper": {"ru": "♻ НОВЫЙ КОНТЕКСТ", "en": "♻ NEW CONTEXT", "bi": "♻ NEW / НОВЫЙ КОНТЕКСТ"},
    "clean_session_upper": {"ru": "🆕 ЧИСТАЯ СЕССИЯ", "en": "🆕 CLEAN SESSION", "bi": "🆕 CLEAN / ЧИСТАЯ СЕССИЯ"},
    "clear_all_upper": {"ru": "🧹 ОЧИСТИТЬ", "en": "🧹 CLEAR", "bi": "🧹 CLEAR / ОЧИСТИТЬ"},

    # Чат и ввод
    "dialog": {"ru": "💬 Диалог", "en": "💬 Conversation", "bi": "💬 Conversation / Диалог"},
    "copy": {"ru": "📋 Копировать", "en": "📋 Copy", "bi": "📋 Copy / Копировать"},
    "copy_all": {"ru": "📝 Копировать всё", "en": "📝 Copy all", "bi": "📝 Copy all / Копировать всё"},
    "extract_all_code": {"ru": "⚡ Извлечь весь код", "en": "⚡ Extract all code", "bi": "⚡ Extract all / Извлечь весь код"},
    "save_selected": {"ru": "💾 Сохранить выделенное", "en": "💾 Save selection", "bi": "💾 Save / Сохранить выделенное"},
    "export_llm": {"ru": "📤 Экспорт ответа LLM", "en": "📤 Export LLM response", "bi": "📤 Export / Экспорт ответа LLM"},
    "input": {"ru": "✏️ Ввод", "en": "✏️ Input", "bi": "✏️ Input / Ввод"},
    "dnd_hint": {"ru": "🖱️ Перетащи файл сюда  •  ", "en": "🖱️ Drop a file here  •  ", "bi": "🖱️ Drop / Перетащи файл  •  "},
    "enter_hint": {"ru": "Enter=отправить  Shift+Enter=новая строка", "en": "Enter=send  Shift+Enter=new line", "bi": "Enter=send/отправить  Shift+Enter=new line"},
    "send": {"ru": "📤 Отправить", "en": "📤 Send", "bi": "📤 Send / Отправить"},
    "stop": {"ru": "⛔ Остановить", "en": "⛔ Stop", "bi": "⛔ Stop / Остановить"},
    "file_to_input": {"ru": "📎 Файл→ввод", "en": "📎 File→input", "bi": "📎 File / Файл→input"},
    "normalize": {"ru": "🔧 Нормализовать", "en": "🔧 Normalize", "bi": "🔧 Normalize / Нормализовать"},
    "clear": {"ru": "🗑️ Очистить", "en": "🗑️ Clear", "bi": "🗑️ Clear / Очистить"},
    "template_single": {"ru": "📋 Шаблон", "en": "📋 Template", "bi": "📋 Template / Шаблон"},
    "insert_file_code": {"ru": "📎 Вставить файл как код", "en": "📎 Insert file as code", "bi": "📎 Insert / Вставить файл как код"},
    "insert_all_files": {"ru": "📁 Вставить все файлы проекта", "en": "📁 Insert all project files", "bi": "📁 Insert / Вставить все файлы"},
    "normalize_indents": {"ru": "🔧 Нормализовать отступы", "en": "🔧 Normalize indentation", "bi": "🔧 Normalize / Нормализовать отступы"},
    "trim_tokens": {"ru": "✂️ Обрезать до N токенов", "en": "✂️ Trim to N tokens", "bi": "✂️ Trim / Обрезать до N токенов"},
    "paste": {"ru": "📋 Вставить (Ctrl+V)", "en": "📋 Paste (Ctrl+V)", "bi": "📋 Paste / Вставить (Ctrl+V)"},

    # Вкладки и файлы
    "tab_files": {"ru": "📁 Файлы", "en": "📁 Files", "bi": "📁 Files / Файлы"},
    "tab_web": {"ru": "🌐 Веб", "en": "🌐 Web", "bi": "🌐 Web / Веб"},
    "tab_code": {"ru": "⚡ Код", "en": "⚡ Code", "bi": "⚡ Code / Код"},
    "project_files": {"ru": "📁 Файлы проекта", "en": "📁 Project files", "bi": "📁 Project files / Файлы проекта"},
    "preview": {"ru": "👁 ПРЕДПРОСМОТР", "en": "👁 PREVIEW", "bi": "👁 PREVIEW / ПРЕДПРОСМОТР"},
    "project_context": {"ru": " Контекст проекта ", "en": " Project context ", "bi": " Project context / Контекст проекта "},
    "auto": {"ru": "🧠 Авто", "en": "🧠 Auto", "bi": "🧠 Auto / Авто"},
    "selected": {"ru": "☑ Отмеченные", "en": "☑ Selected", "bi": "☑ Selected / Отмеченные"},
    "all_project": {"ru": "📚 Весь проект", "en": "📚 Entire project", "bi": "📚 Entire / Весь проект"},
    "file_limit": {"ru": "Лимит файлов:", "en": "File limit:", "bi": "File limit / Лимит:"},
    "token_word": {"ru": "токенов", "en": "tokens", "bi": "tokens / токенов"},
    "select_all": {"ru": "☑ Все", "en": "☑ All", "bi": "☑ All / Все"},
    "deselect": {"ru": "☐ Снять", "en": "☐ Clear", "bi": "☐ Clear / Снять"},
    "invert": {"ru": "↕ Инвертировать", "en": "↕ Invert", "bi": "↕ Invert / Инвертировать"},
    "save": {"ru": "💾 Сохранить", "en": "💾 Save", "bi": "💾 Save / Сохранить"},

    # Веб и просмотр кода
    "source_auto": {"ru": "🔀 Авто", "en": "🔀 Auto", "bi": "🔀 Auto / Авто"},
    "url_placeholder": {"ru": "https://  (вставь URL → Enter для загрузки страницы)", "en": "https://  (paste URL → Enter to load page)", "bi": "https://  (paste URL / вставьте URL → Enter)"},
    "load": {"ru": "⬇️ Загрузить", "en": "⬇️ Load", "bi": "⬇️ Load / Загрузить"},
    "to_input": {"ru": "📋 В ввод", "en": "📋 To input", "bi": "📋 To input / В ввод"},
    "llm_analysis": {"ru": "🤖 LLM анализ", "en": "🤖 LLM analysis", "bi": "🤖 LLM analysis / Анализ"},
    "browser": {"ru": "🌐 Браузер", "en": "🌐 Browser", "bi": "🌐 Browser / Браузер"},
    "page_text": {"ru": "📄 Текст страницы", "en": "📄 Page text", "bi": "📄 Page text / Текст страницы"},
    "code_viewer": {"ru": "⚡ Просмотр кода", "en": "⚡ Code Viewer", "bi": "⚡ Code Viewer / Просмотр кода"},
    "extract_from_chat": {"ru": "⚡ Извлечь из чата", "en": "⚡ Extract from chat", "bi": "⚡ Extract / Извлечь из чата"},
    "save_py": {"ru": "💾 Сохранить .py", "en": "💾 Save .py", "bi": "💾 Save / Сохранить .py"},
    "to_input_field": {"ru": "✏️ В поле ввода", "en": "✏️ To input field", "bi": "✏️ To input / В поле ввода"},

    # Служебные подписи
    "server": {"ru": "сервер", "en": "server", "bi": "server / сервер"},
    "ready": {"ru": "✅ Готов", "en": "✅ Ready", "bi": "✅ Ready / Готов"},
    "done": {"ru": "✅ Готово", "en": "✅ Done", "bi": "✅ Done / Готово"},
    "session_prefix": {"ru": "Сессия: ", "en": "Session: ", "bi": "Session / Сессия: "},
    "context_prefix": {"ru": "Контекст: ", "en": "Context: ", "bi": "Context / Контекст: "},
    "selected_prefix": {"ru": "Отмечено: ", "en": "Selected: ", "bi": "Selected / Отмечено: "},
    "files_prefix": {"ru": "Файлы: ", "en": "Files: ", "bi": "Files / Файлы: "},
}


class LanguageManagerMixin:
    """Управляет языком интерфейса без влияния на язык ответа модели."""

    _PREFIX_KEYS = (
        "session_prefix",
        "context_prefix",
        "selected_prefix",
        "files_prefix",
    )

    def _language_profile(self, mode: Optional[str] = None) -> Dict[str, str]:
        selected = mode or self._language_var.get()
        return dict(
            LANGUAGE_PROFILES.get(
                selected,
                LANGUAGE_PROFILES[DEFAULT_LANGUAGE_MODE],
            )
        )

    def _ui_language_code(self) -> str:
        language_var = getattr(self, "_language_var", None)
        mode = language_var.get() if language_var is not None else DEFAULT_LANGUAGE_MODE
        if mode == "Русский":
            return "ru"
        if mode == "English":
            return "en"
        if mode == "Авто":
            language = (locale.getlocale()[0] or os.environ.get("LANG", "")).lower()
            return "ru" if language.startswith("ru") else "en"
        return "bi"

    def _tr(self, key: str, fallback: str = "") -> str:
        values = UI_TEXTS.get(key)
        if not values:
            return fallback or key
        code = self._ui_language_code()
        return values.get(code) or values.get("bi") or values.get("ru") or fallback

    @staticmethod
    def _strip_selection_prefix(text: str) -> tuple[str, str]:
        for prefix in ("● ", "   "):
            if text.startswith(prefix):
                return prefix, text[len(prefix):]
        return "", text

    def _translation_reverse_map(self) -> Dict[str, str]:
        reverse: Dict[str, str] = {}
        for key, variants in UI_TEXTS.items():
            for value in variants.values():
                reverse[value] = key
        return reverse

    def _translate_literal(self, text: str) -> str:
        if not isinstance(text, str) or not text:
            return text
        prefix, core = self._strip_selection_prefix(text)
        reverse = self._translation_reverse_map()
        key = reverse.get(core)
        if key:
            return prefix + self._tr(key, core)

        # Динамические подписи: сохраняем значение после переведённого префикса.
        for prefix_key in self._PREFIX_KEYS:
            variants = UI_TEXTS[prefix_key]
            for old_prefix in variants.values():
                if core.startswith(old_prefix):
                    suffix = core[len(old_prefix):]
                    return prefix + self._tr(prefix_key) + suffix
        return text

    def _translate_menu(self, menu: tk.Menu, visited: set[str]) -> None:
        menu_name = str(menu)
        if menu_name in visited:
            return
        visited.add(menu_name)
        end = menu.index("end")
        if end is None:
            return
        for index in range(end + 1):
            try:
                entry_type = menu.type(index)
            except tk.TclError:
                continue
            if entry_type == "separator":
                continue
            try:
                label = menu.entrycget(index, "label")
                translated = self._translate_literal(label)
                if translated != label:
                    menu.entryconfig(index, label=translated)
            except tk.TclError:
                pass
            if entry_type == "cascade":
                try:
                    submenu_name = menu.entrycget(index, "menu")
                    if submenu_name:
                        submenu = menu.nametowidget(submenu_name)
                        if isinstance(submenu, tk.Menu):
                            self._translate_menu(submenu, visited)
                except (tk.TclError, KeyError):
                    pass

    def _translate_widget_tree(self, widget: tk.Misc) -> None:
        if isinstance(widget, tk.Menu):
            self._translate_menu(widget, set())
            return
        try:
            current = widget.cget("text")
        except (tk.TclError, AttributeError):
            current = None
        if isinstance(current, str) and current:
            translated = self._translate_literal(current)
            if translated != current:
                try:
                    widget.configure(text=translated)
                except tk.TclError:
                    pass

        if isinstance(widget, ttk.Notebook):
            for tab_id in widget.tabs():
                current_tab = widget.tab(tab_id, "text")
                translated_tab = self._translate_literal(current_tab)
                if translated_tab != current_tab:
                    widget.tab(tab_id, text=translated_tab)

        for child in widget.winfo_children():
            self._translate_widget_tree(child)

    def _translate_main_window(self) -> None:
        """Немедленно перевести уже созданные элементы главного окна."""
        self._translate_widget_tree(self.root)
        menu = getattr(self, "_main_menu", None)
        if isinstance(menu, tk.Menu):
            self._translate_menu(menu, set())

        # Entry не имеет свойства text, поэтому placeholder обновляется отдельно.
        url_entry = getattr(self, "_url_entry", None)
        if url_entry is not None:
            current = url_entry.get()
            reverse = self._translation_reverse_map()
            placeholder_variants = UI_TEXTS["url_placeholder"].values()
            if current in placeholder_variants or reverse.get(current) == "url_placeholder":
                url_entry.delete(0, tk.END)
                url_entry.insert(0, self._tr("url_placeholder"))

    def _language_button_text(self) -> str:
        return self._language_profile().get("button", "🌐 LANGUAGE")

    def _language_button_color(self) -> str:
        return self._language_profile().get("color", "#0d6efd")

    def _language_instruction(self) -> str:
        """Язык модели не зависит от языка интерфейса."""
        return (
            "Отвечай на языке последнего запроса пользователя. "
            "Не меняй язык без явной просьбы. Имена API, классов, методов, "
            "параметров, команд и исходный код сохраняй без перевода."
        )

    def _update_language_ui(self) -> None:
        if hasattr(self, "_language_btn"):
            self._language_btn.config(
                text=self._language_button_text(),
                bg=self._language_button_color(),
            )
        self._translate_main_window()
        if hasattr(self, "_update_session_ui"):
            self._update_session_ui()
        if hasattr(self, "_update_file_tokens"):
            self._update_file_tokens()
        if hasattr(self, "_update_security_ui"):
            self._update_security_ui()
        if hasattr(self, "_status"):
            code = self._ui_language_code()
            status = {
                "ru": f"🌐 Язык интерфейса: {self._language_var.get()}",
                "en": f"🌐 Interface language: {self._language_var.get()}",
                "bi": f"🌐 Interface / Интерфейс: {self._language_var.get()}",
            }[code]
            self._status.config(text=status)

    def _set_language(self, mode: str) -> None:
        if mode not in LANGUAGE_PROFILES:
            return
        self._language_var.set(mode)
        self._update_language_ui()
        if hasattr(self, "_autosave_session"):
            self._autosave_session()

    def _show_language_menu(self) -> None:
        menu = tk.Menu(
            self.root,
            tearoff=0,
            bg=self.C["bg2"],
            fg=self.C["fg"],
            activebackground=self.C["accent"],
            activeforeground="white",
        )
        code = self._ui_language_code()
        labels = {
            "ru": {
                "English + Русский": "🇬🇧 + 🇷🇺  English + Русский (по умолчанию)",
                "Русский": "🇷🇺  Русский интерфейс",
                "English": "🇬🇧  Английский интерфейс",
                "Авто": "🔄  Авто — язык Windows",
            },
            "en": {
                "English + Русский": "🇬🇧 + 🇷🇺  English + Russian (default)",
                "Русский": "🇷🇺  Russian interface",
                "English": "🇬🇧  English interface",
                "Авто": "🔄  Auto — Windows language",
            },
            "bi": {
                "English + Русский": "🇬🇧 + 🇷🇺  English + Русский (default / по умолчанию)",
                "Русский": "🇷🇺  Русский interface",
                "English": "🇬🇧  English интерфейс",
                "Авто": "🔄  Auto / Авто — Windows",
            },
        }
        for mode in LANGUAGE_PROFILES:
            prefix = "● " if self._language_var.get() == mode else "   "
            menu.add_command(
                label=prefix + labels[code].get(mode, mode),
                command=lambda value=mode: self._set_language(value),
            )
        menu.add_separator()
        info = {
            "ru": "ℹ️ Переключатель меняет интерфейс, а не язык ответа модели",
            "en": "ℹ️ This changes the UI, not the model response language",
            "bi": "ℹ️ UI / Интерфейс only; model answers follow the prompt language",
        }[code]
        menu.add_command(label=info, state=tk.DISABLED)
        button = getattr(self, "_language_btn", None)
        if button is not None and button.winfo_ismapped():
            x = button.winfo_rootx()
            y = button.winfo_rooty() + button.winfo_height()
        else:
            x = self.root.winfo_pointerx()
            y = self.root.winfo_pointery()
        menu.tk_popup(x, y)
