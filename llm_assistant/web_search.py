"""Часть главного окна LLM Assistant.

Модуль выделен из монолитного файла v9 для удобства сопровождения.
"""

from .common import *  # noqa: F401,F403


class WebSearchMixin:
    API_ENV_NAMES = {
        "github": "GITHUB_TOKEN",
        "tavily": "TAVILY_API_KEY",
        "so_key": "STACKAPPS_KEY",
    }

    @staticmethod
    def _validate_public_web_url(url: str) -> Tuple[bool, str]:
        """Разрешить только публичные HTTP(S)-страницы для веб-загрузчика.

        Локальные LLM-серверы настраиваются отдельно в ServerManagerMixin.
        Эта проверка уменьшает риск SSRF через результаты поиска и ручной URL.
        """
        try:
            parsed = urlparse(url.strip())
        except Exception:
            return False, "Некорректный URL."
        if parsed.scheme not in {"http", "https"}:
            return False, "Разрешены только http:// и https:// адреса."
        if not parsed.hostname:
            return False, "В URL отсутствует имя сервера."
        if parsed.username or parsed.password:
            return False, "URL со встроенным логином или паролем запрещён."
        host = parsed.hostname.lower().rstrip(".")
        if host == "localhost" or host.endswith(".localhost"):
            return False, "Локальные адреса нельзя загружать как веб-страницы."
        try:
            addresses = {
                item[4][0]
                for item in socket.getaddrinfo(host, parsed.port or 443, type=socket.SOCK_STREAM)
            }
        except OSError as exc:
            return False, f"Не удалось определить адрес сервера: {exc}"
        for address in addresses:
            try:
                ip = ipaddress.ip_address(address.split("%", 1)[0])
            except ValueError:
                continue
            if (
                ip.is_private or ip.is_loopback or ip.is_link_local
                or ip.is_reserved or ip.is_multicast or ip.is_unspecified
            ):
                return False, "Локальные и служебные сетевые адреса заблокированы."
        return True, ""

    def _route_source(self, query: str) -> str:
        """Определить лучший источник по ключевым словам запроса."""
        forced = self._search_source_var.get()
        if forced != "auto":
            return forced
        ql = query.lower()
        for src, keywords in SOURCE_ROUTING.items():
            if any(kw in ql for kw in keywords):
                # Проверить доступность источника
                if src == "tavily" and not self._api_keys.get("tavily"):
                    continue
                return src
        return "duckduckgo"

    def _do_search(self):
        q = self._search_entry.get().strip()
        if not q:
            return
        source = self._route_source(q)
        self._set_phase(1, 2, f"Поиск...", spin=True)
        self._update_src_indicator(source, "searching")
        threading.Thread(
            target=self._smart_search_thread,
            args=(q, source),
            daemon=True
        ).start()

    def _smart_search_thread(self, query: str, source: str):
        """
        Пробует source, при ошибке/пустом результате переключается
        на следующий по приоритету.
        """
        priority = self._build_fallback_chain(source)
        last_err = ""

        for src in priority:
            try:
                results = self._search_with(query, src)
                if results:
                    self.web_results = results
                    self.root.after(0, self._refresh_web_list)
                    self.root.after(0, lambda s=src, n=len(results):
                        self._update_src_indicator(s, "done", n))
                    self.root.after(0, lambda s=src, n=len(results):
                        self._clear_phase(f"✅ {SEARCH_SOURCES[s]['icon']} {SEARCH_SOURCES[s]['name']}: {n} результатов"))
                    # Автозагрузка первых 3 страниц в фоне
                    for i in range(min(3, len(results))):
                        threading.Thread(
                            target=self._fetch_page_bg, args=(i,), daemon=True
                        ).start()
                    return
                else:
                    last_err = f"{src}: пустой ответ"
                    self.root.after(0, lambda s=src:
                        self._src_status.config(
                            text=f"⚠️ {SEARCH_SOURCES[s]['name']}: нет результатов → переключаюсь...",
                            fg="#ffaa00"))
            except Exception as e:
                last_err = f"{src}: {str(e)[:60]}"
                self.root.after(0, lambda s=src, err=last_err:
                    self._src_status.config(
                        text=f"⚠️ {SEARCH_SOURCES[s]['name']}: {err} → следующий...",
                        fg="#ff6666"))
                time.sleep(0.3)

        # Все источники исчерпаны
        self.root.after(0, lambda: self._add_msg(
            "system", f"❌ Все источники поиска недоступны.\nПоследняя ошибка: {last_err}\n"
            "Попробуй добавить API ключи (кнопка 🔑) или проверь соединение."))
        self.root.after(0, lambda: self._clear_phase("❌ Поиск не удался"))

    def _build_fallback_chain(self, primary: str) -> List[str]:
        """Построить цепочку: primary → остальные по приоритету."""
        order = ["github", "stackoverflow", "tavily", "duckduckgo"]
        chain = [primary] + [s for s in order if s != primary]
        # Убрать tavily если нет ключа
        if not self._api_keys.get("tavily"):
            chain = [s for s in chain if s != "tavily"]
        return chain

    def _search_with(self, query: str, source: str) -> List["WebResult"]:
        """Выполнить поиск через конкретный источник."""
        if source == "github":
            return self._search_github(query)
        elif source == "stackoverflow":
            return self._search_stackoverflow(query)
        elif source == "tavily":
            return self._search_tavily(query)
        else:
            return self._search_duckduckgo(query)

    def _search_github(self, query: str) -> List["WebResult"]:
        """Поиск кода на GitHub (бесплатно, до 30 req/min без ключа, 5000 с ключом)."""
        headers = {"Accept": "application/vnd.github+json"}
        token = self._api_keys.get("github", "")
        if token:
            headers["Authorization"] = f"Bearer {token}"

        results = []

        # 1) Поиск репозиториев
        r = requests.get(
            "https://api.github.com/search/repositories",
            params={"q": query, "sort": "stars", "per_page": 5},
            headers=headers, timeout=10
        )
        if r.status_code == 200:
            for item in r.json().get("items", []):
                desc = item.get("description") or ""
                stars = item.get("stargazers_count", 0)
                lang = item.get("language") or ""
                snippet = f"⭐ {stars:,}  {lang}  —  {desc}"
                results.append(WebResult(
                    title    = f"🐙 {item['full_name']}",
                    url      = item["html_url"],
                    snippet  = snippet,
                    source   = "github",
                ))
        elif r.status_code == 403:
            raise Exception("GitHub rate limit. Добавь токен в 🔑 настройки.")

        # 2) Поиск файлов с кодом
        r2 = requests.get(
            "https://api.github.com/search/code",
            params={"q": f"{query} language:python", "per_page": 8},
            headers=headers, timeout=10
        )
        if r2.status_code == 200:
            for item in r2.json().get("items", []):
                repo = item.get("repository", {})
                results.append(WebResult(
                    title    = f"📄 {item['name']} ({repo.get('full_name','')})",
                    url      = item.get("html_url", ""),
                    snippet  = f"Файл: {item['path']}",
                    source   = "github",
                ))

        return results

    def _search_stackoverflow(self, query: str) -> List["WebResult"]:
        """Stack Overflow API — бесплатно, 300 req/day без ключа, с ключом больше."""
        params = {
            "order":   "desc",
            "sort":    "votes",
            "q":       query,
            "site":    "stackoverflow",
            "filter":  "withbody",
            "pagesize": 8,
        }
        key = self._api_keys.get("so_key", "")
        if key:
            params["key"] = key

        r = requests.get(
            "https://api.stackexchange.com/2.3/search/advanced",
            params=params, timeout=12
        )
        if r.status_code != 200:
            raise Exception(f"SO HTTP {r.status_code}")

        data = r.json()
        if data.get("error_id"):
            raise Exception(data.get("error_message", "SO error"))

        results = []
        for item in data.get("items", []):
            # Очистить HTML из body
            body = item.get("body", "")
            if HAS_BS4:
                body = BeautifulSoup(body, "html.parser").get_text(separator="\n")
            else:
                body = re.sub(r"<[^>]+>", " ", body)
            body = body[:3000]

            score    = item.get("score", 0)
            answers  = item.get("answer_count", 0)
            accepted = "✅" if item.get("is_answered") else "○"
            snippet  = f"{accepted} votes:{score} answers:{answers}"

            res = WebResult(
                title     = f"🟠 {item.get('title', '')}",
                url       = item.get("link", ""),
                snippet   = snippet,
                full_text = body,
                fetched   = bool(body),
                source    = "stackoverflow",
            )
            results.append(res)

        return results

    def _search_tavily(self, query: str) -> List["WebResult"]:
        """Tavily API — AI-ready поиск, 1000 req/month бесплатно."""
        key = self._api_keys.get("tavily", "")
        if not key:
            raise Exception("Нет API ключа Tavily. Добавь в 🔑 настройки.")

        if HAS_TAVILY:
            client = TavilyClient(api_key=key)
            data = client.search(
                query,
                search_depth="advanced",
                include_raw_content=True,
                max_results=8
            )
            results = []
            for r in data.get("results", []):
                content = r.get("raw_content") or r.get("content", "")
                results.append(WebResult(
                    title     = f"🔷 {r.get('title', '')}",
                    url       = r.get("url", ""),
                    snippet   = r.get("content", "")[:200],
                    full_text = content[:50000],
                    fetched   = bool(content),
                    source    = "tavily",
                ))
            return results
        else:
            # Fallback: прямой HTTP запрос к Tavily API
            r = requests.post(
                "https://api.tavily.com/search",
                json={"api_key": key, "query": query,
                      "search_depth": "advanced",
                      "include_raw_content": True,
                      "max_results": 8},
                timeout=15
            )
            if r.status_code != 200:
                raise Exception(f"Tavily HTTP {r.status_code}: {r.text[:100]}")
            results = []
            for item in r.json().get("results", []):
                content = item.get("raw_content") or item.get("content", "")
                results.append(WebResult(
                    title     = f"🔷 {item.get('title', '')}",
                    url       = item.get("url", ""),
                    snippet   = item.get("content", "")[:200],
                    full_text = content[:50000],
                    fetched   = bool(content),
                    source    = "tavily",
                ))
            return results

    def _search_duckduckgo(self, query: str) -> List["WebResult"]:
        """DuckDuckGo — полностью бесплатно, без ключа."""
        if not HAS_DDGS:
            raise Exception("duckduckgo-search не установлен.\npip install duckduckgo-search")
        with DDGS() as ddgs:
            raw = list(ddgs.text(query, max_results=12))
        return [
            WebResult(
                title   = f"🦆 {r.get('title', '')}",
                url     = r.get("href", ""),
                snippet = r.get("body", ""),
                source  = "duckduckgo",
            )
            for r in raw
        ]

    def _update_src_indicator(self, source: str, state: str = "done", count: int = 0):
        """Обновить кнопку источника и строку статуса."""
        info = SEARCH_SOURCES.get(source, {"icon": "🔀", "name": source, "color": "#888"})
        icon = info["icon"]
        name = info["name"]
        color = info["color"]

        if state == "searching":
            self._src_btn.config(text=f"{icon} {name}...", bg="#1a1a2e", fg=color)
            self._src_status.config(
                text=f"Поиск через {name}...",
                fg=color
            )
        elif state == "done":
            self._src_btn.config(text=f"{icon} {name}", bg="#1a1a2e", fg=color)
            self._src_status.config(
                text=f"{icon} {name}: найдено {count} результатов",
                fg=color
            )

    def _show_source_picker(self):
        """Всплывающее меню выбора источника поиска."""
        m = tk.Menu(self.root, tearoff=0, bg=self.C["bg2"],
                    fg=self.C["fg"], activebackground=self.C["accent"])

        def pick(src):
            self._search_source_var.set(src)
            if src == "auto":
                self._src_btn.config(text="🔀 Авто", bg="#2a2a3a", fg="#aaaaff")
                self._src_status.config(text="Режим: авто-роутинг по ключевым словам", fg="#888")
            else:
                info = SEARCH_SOURCES[src]
                self._src_btn.config(
                    text=f"{info['icon']} {info['name']}",
                    bg="#1a1a2e", fg=info["color"])
                self._src_status.config(
                    text=f"Фиксированный источник: {info['name']}",
                    fg=info["color"])

        m.add_command(label="🔀 Авто (умный роутинг)", command=lambda: pick("auto"))
        m.add_separator()
        for src, info in SEARCH_SOURCES.items():
            has_key = not info["needs_key"] or bool(self._api_keys.get(src))
            ok_mark = "✅" if has_key else "🔑"
            label = f"{info['icon']} {info['name']}  {ok_mark}"
            m.add_command(label=label, command=lambda s=src: pick(s))
        m.add_separator()
        m.add_command(label="🔑 Настроить API ключи...", command=self._open_api_settings)

        m.tk_popup(
            self._src_btn.winfo_rootx(),
            self._src_btn.winfo_rooty() + self._src_btn.winfo_height()
        )

    def _open_api_settings(self):
        """Красивый диалог настройки источников поиска."""
        win = tk.Toplevel(self.root)
        win.title("🔑 Источники поиска")
        win.geometry("620x580")
        win.configure(bg=self.C["bg"])
        win.resizable(False, False)
        win.grab_set()

        # Заголовок
        hdr = tk.Frame(win, bg="#0d1117", pady=12)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text="🔍 Источники поиска",
                 font=("Segoe UI", 14, "bold"),
                 bg="#0d1117", fg="white").pack()
        tk.Label(hdr, text="Настрой API ключи для получения лучших результатов по коду",
                 font=("Segoe UI", 9),
                 bg="#0d1117", fg="#888").pack(pady=(2, 0))

        scroll_frame = tk.Frame(win, bg=self.C["bg"])
        scroll_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=12)

        entries = {}   # source_key → Entry widget

        sources_config = [
            {
                "key":      "github",
                "title":    "🐙 GitHub Code Search",
                "subtitle": "Реальный код из репозиториев • Бесплатно без токена (30 req/min)",
                "fields": [
                    ("github", "Personal Access Token (опционально)", False,
                     "https://github.com/settings/tokens",
                     "Без токена: 30 req/min  •  С токеном: 5 000 req/min"),
                ],
                "color": "#238636",
                "free": True,
            },
            {
                "key":      "stackoverflow",
                "title":    "🟠 Stack Overflow",
                "subtitle": "Решения ошибок и паттернов • Бесплатно без ключа (300 req/day)",
                "fields": [
                    ("so_key", "API Key (опционально, для увеличения лимита)", False,
                     "https://stackapps.com/apps/oauth/register",
                     "Без ключа: 300 req/day  •  С ключом: 10 000 req/day"),
                ],
                "color": "#f48024",
                "free": True,
            },
            {
                "key":      "tavily",
                "title":    "🔷 Tavily AI Search",
                "subtitle": "AI-ready контент, обходит JS-сайты • 1 000 req/month бесплатно",
                "fields": [
                    ("tavily", "API Key (нужен для работы)", True,
                     "https://app.tavily.com/sign-up",
                     "Бесплатно: 1 000 req/month  •  Регистрация бесплатная"),
                ],
                "color": "#2563eb",
                "free": False,
            },
            {
                "key":      "duckduckgo",
                "title":    "🦆 DuckDuckGo",
                "subtitle": "Всегда работает • Полностью бесплатно • Без регистрации",
                "fields":   [],
                "color":    "#de5833",
                "free":     True,
                "always_on": True,
            },
        ]

        for cfg in sources_config:
            # Карточка источника
            card = tk.Frame(scroll_frame, bg="#161b22",
                            relief=tk.FLAT, bd=0)
            card.pack(fill=tk.X, pady=6)

            # Левая полоска цвета
            accent_bar = tk.Frame(card, bg=cfg["color"], width=4)
            accent_bar.pack(side=tk.LEFT, fill=tk.Y)

            inner = tk.Frame(card, bg="#161b22", padx=12, pady=10)
            inner.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

            # Заголовок карточки
            title_row = tk.Frame(inner, bg="#161b22")
            title_row.pack(fill=tk.X)
            tk.Label(title_row, text=cfg["title"],
                     font=("Segoe UI", 11, "bold"),
                     bg="#161b22", fg=cfg["color"]).pack(side=tk.LEFT)

            # Бейдж «Бесплатно» / «Ключ нужен»
            badge_text  = "✅ Бесплатно"  if cfg["free"]  else "🔑 Нужен ключ"
            badge_color = "#238636"       if cfg["free"]  else "#9e6a03"
            tk.Label(title_row, text=badge_text,
                     font=("Segoe UI", 8), padx=6, pady=1,
                     bg=badge_color, fg="white",
                     relief=tk.FLAT).pack(side=tk.RIGHT)

            tk.Label(inner, text=cfg["subtitle"],
                     font=("Segoe UI", 8),
                     bg="#161b22", fg="#888").pack(anchor=tk.W, pady=(2, 6))

            if cfg.get("always_on"):
                tk.Label(inner, text="⚡ Всегда активен — ключ не нужен",
                         font=("Segoe UI", 9, "italic"),
                         bg="#161b22", fg="#5cb85c").pack(anchor=tk.W)
                continue

            for field_key, label, required, link_url, hint in cfg["fields"]:
                f_row = tk.Frame(inner, bg="#161b22")
                f_row.pack(fill=tk.X, pady=2)

                lbl_text = f"{label}{'  *' if required else ''}"
                tk.Label(f_row, text=lbl_text,
                         font=("Segoe UI", 8),
                         bg="#161b22", fg="#ccc",
                         width=38, anchor=tk.W).pack(side=tk.LEFT)

                entry = tk.Entry(f_row, font=("Consolas", 9),
                                 bg="#0d1117", fg="#58a6ff",
                                 insertbackground="white",
                                 relief=tk.FLAT, width=28, show="•")
                entry.pack(side=tk.LEFT, padx=(4, 4), ipady=3)
                # Вставить текущее значение
                cur = self._api_keys.get(field_key, "")
                if cur:
                    entry.insert(0, cur)

                # Показать/скрыть ключ
                def toggle_show(e=entry):
                    e.config(show="" if e.cget("show") == "•" else "•")

                tk.Button(f_row, text="👁", command=toggle_show,
                          bg="#161b22", fg="#888", relief=tk.FLAT,
                          cursor="hand2", padx=2).pack(side=tk.LEFT)

                entries[field_key] = entry

                # Ссылка для получения ключа
                link = tk.Label(inner, text=f"🔗 Получить ключ: {link_url}",
                                font=("Segoe UI", 8),
                                bg="#161b22", fg="#58a6ff", cursor="hand2")
                link.pack(anchor=tk.W)
                link.bind("<Button-1>", lambda e, u=link_url: __import__("webbrowser").open(u))

                tk.Label(inner, text=f"ℹ️ {hint}",
                         font=("Segoe UI", 8),
                         bg="#161b22", fg="#666").pack(anchor=tk.W, pady=(1, 0))

        # Кнопки внизу
        btn_frame = tk.Frame(win, bg=self.C["bg"], pady=10)
        btn_frame.pack(fill=tk.X, padx=16)

        def save_keys():
            for field_key, entry in entries.items():
                val = entry.get().strip()
                self._api_keys[field_key] = val
                env_name = self.API_ENV_NAMES.get(field_key)
                if val and env_name:
                    os.environ[env_name] = val
            # Обновить статус источников
            self._update_src_indicator(
                self._search_source_var.get()
                if self._search_source_var.get() != "auto"
                else "duckduckgo",
                "done", 0
            )
            win.destroy()
            self._add_msg("system",
                "✅ API ключи применены только для текущего запуска. "
                "Для постоянного хранения используйте .env; в сессии секреты не записываются.\n\n"
                + "\n".join(
                    f"  {SEARCH_SOURCES[k]['icon']} {SEARCH_SOURCES[k]['name']}: "
                    f"{'✅ ключ задан' if self._api_keys.get(k) else '○ без ключа (бесплатный режим)'}"
                    for k in SEARCH_SOURCES
                )
            )

        def test_sources():
            """Сохранить введённые значения и проверить источники."""
            for field_key, entry in entries.items():
                val = entry.get().strip()
                self._api_keys[field_key] = val
                env_name = self.API_ENV_NAMES.get(field_key)
                if val and env_name:
                    os.environ[env_name] = val
            win.destroy()
            self._add_msg("system", "🔄 Тестирую источники поиска...")
            threading.Thread(target=self._test_all_sources, daemon=True).start()

        tk.Button(btn_frame, text="💾 Сохранить", command=save_keys,
                  bg=self.C["accent"], fg="white", relief=tk.FLAT,
                  padx=16, pady=6, cursor="hand2",
                  font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, padx=4)
        tk.Button(btn_frame, text="🧪 Тест всех источников", command=test_sources,
                  bg="#238636", fg="white", relief=tk.FLAT,
                  padx=12, pady=6, cursor="hand2",
                  font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=4)
        tk.Button(btn_frame, text="Отмена", command=win.destroy,
                  bg=self.C["bg3"], fg=self.C["fg"], relief=tk.FLAT,
                  padx=12, pady=6, cursor="hand2").pack(side=tk.RIGHT, padx=4)

    def _test_all_sources(self):
        """Протестировать все источники тестовым запросом."""
        test_query = "python async generator example"
        results_log = []
        for src in SEARCH_SOURCES:
            if src == "tavily" and not self._api_keys.get("tavily"):
                results_log.append("🔷 Tavily: пропущен (нет ключа)")
                continue
            try:
                start = time.time()
                res = self._search_with(test_query, src)
                elapsed = time.time() - start
                info = SEARCH_SOURCES[src]
                results_log.append(
                    f"{info['icon']} {info['name']}: ✅ {len(res)} результатов  ({elapsed:.1f}s)")
            except Exception as e:
                info = SEARCH_SOURCES[src]
                results_log.append(
                    f"{info['icon']} {info['name']}: ❌ {str(e)[:60]}")

        report = "🧪 Тест источников поиска:\n\n" + "\n".join(results_log)
        self.root.after(0, lambda: self._add_msg("system", report))

    def _fetch_page_bg(self, idx: int):
        """Загружает полный текст страницы в фоне."""
        if idx >= len(self.web_results):
            return
        r = self.web_results[idx]
        if r.fetched:
            return
        allowed, reason = self._validate_public_web_url(r.url)
        if not allowed:
            self.root.after(
                0,
                lambda msg=reason: self._add_msg("system", f"❌ URL заблокирован: {msg}"),
            )
            return
        try:
            headers = {"User-Agent": "LLM-Assistant/13 (+local desktop application)"}
            resp = requests.get(
                r.url, headers=headers, timeout=(5, 15), allow_redirects=True
            )
            resp.raise_for_status()
            final_allowed, final_reason = self._validate_public_web_url(resp.url)
            if not final_allowed:
                raise ValueError(f"Небезопасное перенаправление: {final_reason}")
            if HAS_BS4:
                soup = BeautifulSoup(resp.text, "html.parser")
                for tag in soup(["script", "style", "nav", "footer", "header"]):
                    tag.decompose()
                text = soup.get_text(separator="\n", strip=True)
                # Убираем пустые строки
                lines = [line for line in text.splitlines() if line.strip()]
                text  = "\n".join(lines)
            else:
                # Простая очистка без BS4
                text = re.sub(r"<[^>]+>", " ", resp.text)
                text = re.sub(r"\s+", " ", text).strip()
            r.full_text = text[:50000]  # до 50K символов (~12K токенов)
            r.fetched   = True
            self.root.after(0, lambda i=idx: self._refresh_web_list())
            self.root.after(0, self._update_ctx_label)
        except Exception as exc:
            error = str(exc)
            self.root.after(
                0,
                lambda msg=error: self._add_msg("system", f"❌ Не удалось загрузить страницу: {msg}"),
            )

    def _fetch_selected_page(self, event=None):
        sel = self._web_lb.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx >= len(self.web_results):
            return
        r = self.web_results[idx]
        self._set_phase(1, 2, f"Загрузка: {r.url[:50]}...", spin=True)
        threading.Thread(target=self._fetch_page_thread, args=(idx,), daemon=True).start()

    def _fetch_page_thread(self, idx: int):
        self._fetch_page_bg(idx)
        self.root.after(0, lambda: self._on_web_select(None))
        self.root.after(0, lambda: self._clear_phase("✅ Страница загружена"))

    def _on_web_select(self, event):
        sel = self._web_lb.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx >= len(self.web_results):
            return
        r = self.web_results[idx]
        self._web_text.config(state=tk.NORMAL)
        self._web_text.delete("1.0", tk.END)
        if r.fetched and r.full_text:
            self._web_text.insert("1.0", r.full_text)
            t = self._tok(r.full_text)
            self._web_tok_label.config(text=f"~{t:,} токенов", fg=self.C["green"])
        else:
            self._web_text.insert("1.0",
                f"🔗 {r.url}\n\n{r.snippet}\n\n"
                "⬇️ Дважды кликни или нажми «Загрузить страницу» для полного текста.")
            self._web_tok_label.config(text="не загружено", fg="#888")
        self._web_text.config(state=tk.DISABLED)

    def _refresh_web_list(self):
        self._web_lb.delete(0, tk.END)
        for i, r in enumerate(self.web_results):
            fetched_icon = "✅" if r.fetched else "○"
            src_icon = SEARCH_SOURCES.get(r.source, {}).get("icon", "🌐")
            title = r.title[:60] if r.title else r.url[:60]
            self._web_lb.insert(tk.END, f"{fetched_icon}{src_icon} {i+1}. {title}")

    def _web_to_input(self):
        sel = self._web_lb.curselection()
        if not sel or sel[0] >= len(self.web_results):
            return
        r = self.web_results[sel[0]]
        text = r.full_text if r.fetched else f"{r.title}\n{r.url}\n{r.snippet}"
        tok  = self._tok(text)
        self.input_text.delete("1.0", tk.END)
        self.input_text.insert("1.0",
            f"Проанализируй эту веб-страницу (~{tok} токенов):\n\n"
            f"Заголовок: {r.title}\nURL: {r.url}\n\n{text[:10000]}")
        self._hide_right_panel()
        self.input_text.focus_set()

    def _web_analyze_llm(self):
        sel = self._web_lb.curselection()
        if not sel or sel[0] >= len(self.web_results):
            return
        r = self.web_results[sel[0]]
        text = r.full_text if r.fetched else r.snippet
        self.input_text.delete("1.0", tk.END)
        self.input_text.insert("1.0",
            f"Проанализируй содержимое страницы и выдели:\n"
            f"1. Ключевые факты\n2. Примеры кода (если есть)\n3. Практическое применение\n\n"
            f"Страница: {r.title}\nURL: {r.url}\n\n{text[:8000]}")
        self._send_message()

    def _open_browser(self):
        sel = self._web_lb.curselection()
        if not sel or sel[0] >= len(self.web_results):
            return
        import webbrowser
        webbrowser.open(self.web_results[sel[0]].url)

    def _fetch_url(self, url: str):
        allowed, reason = self._validate_public_web_url(url)
        if not allowed:
            messagebox.showwarning(
                "URL заблокирован", reason, parent=self.root
            )
            return
        r = WebResult(title=url, url=url, snippet="")
        self.web_results.insert(0, r)
        self._refresh_web_list()
        self._set_phase(1, 2, f"Загрузка {url[:50]}...", spin=True)
        threading.Thread(target=self._fetch_page_thread, args=(0,), daemon=True).start()

    def _fetch_url_dialog(self):
        url = simpledialog.askstring("Загрузить URL",
                                     "Введите URL страницы:", parent=self.root)
        if url:
            self._fetch_url(url.strip())
            self._show_right_tab("web")

    def _quick_search(self):
        q = simpledialog.askstring("Быстрый поиск", "Поисковый запрос:", parent=self.root)
        if q:
            self._search_entry.delete(0, tk.END)
            self._search_entry.insert(0, q)
            self._show_right_tab("web")
            self._do_search()
