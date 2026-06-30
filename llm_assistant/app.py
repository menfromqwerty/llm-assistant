"""Сборка главного класса приложения из независимых функциональных модулей."""

from .common import *  # noqa: F401,F403
from .ui import UIMixin
from .context_manager import ContextManagerMixin
from .llm_client import LLMClientMixin
from .web_search import WebSearchMixin
from .file_manager import FileManagerMixin
from .model_manager import ModelManagerMixin
from .language_manager import LanguageManagerMixin
from .server_manager import ServerManagerMixin
from .utilities import UtilitiesMixin
from .input_tools import InputToolsMixin
from .sessions import SessionMixin
from .security_manager import SecurityMixin


class LLMAssistant(
    UIMixin,
    ContextManagerMixin,
    LLMClientMixin,
    WebSearchMixin,
    FileManagerMixin,
    ModelManagerMixin,
    LanguageManagerMixin,
    ServerManagerMixin,
    UtilitiesMixin,
    InputToolsMixin,
    SessionMixin,
    SecurityMixin,
):
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.withdraw()
        self._security_init_state()
        if not self._security_startup_unlock():
            self._startup_aborted = True
            self.root.after(0, self.root.destroy)
            return

        # Модель по умолчанию. Выбор другой модели хранится отдельно в каждой сессии.
        self._model_name: str = DEFAULT_MODEL_NAME
        self._available_models: List[str] = []
        self.root.title(f"LLM Assistant v2.0.0 — {self._model_name}")
        self.root.geometry("1440x900")
        self.root.minsize(920, 620)

        # Состояние
        self.current_project: Optional[str] = None
        self.loaded_files: Dict[str, str]   = {}
        self.chat_history: List[Message]    = []
        self.web_results: List[WebResult]   = []
        self.is_loading: bool               = False
        # Управление отменой текущего запроса. Event безопасно читается
        # рабочим потоком, а response/session закрываются кнопкой Stop.
        self._cancel_generation_event = threading.Event()
        self._active_response = None
        self._active_http_session = None
        self._active_prompt: str = ""
        self._context_warning_shown: bool    = False
        self._autosave_after_response: bool  = True
        self._shutdown_requested: bool        = False

        # Умное управление файловым контекстом.
        self._context_mode_var = tk.StringVar(value="auto")
        self._file_context_budget_var = tk.IntVar(value=32768)
        self._file_context_selected: Dict[str, bool] = {}
        self._file_token_cache: Dict[str, tuple] = {}
        self._file_list_names: List[str] = []

        # Контроль подключения к локальному серверу
        self._connection_check_running: bool = False
        self._connection_retry_active: bool  = False
        self._connection_retry_after_id = None
        self._connection_retry_attempts: int = 0
        self._connection_retry_max_attempts: int = 12
        self._connection_retry_interval_ms: int = 5000
        self._last_connection_error: str = ""
        self._server_processes: Dict[str, object] = {}
        self._server_model_selection: Dict[str, str] = {
            "LM Studio": DEFAULT_MODEL_NAME,
        }
        # Параметры генерации сохраняются отдельно для каждой пары сервер+модель.
        self._runtime_profiles: Dict[str, Dict[str, object]] = {}
        self._llama_cpp_settings: Dict[str, object] = {
            "executable": "",
            "model": "",
            "port": 8080,
            "extra_args": "",
        }

        # Стриминг
        self._stream_buffer    = ""
        self._in_code_block    = False
        self._current_code_tag: Optional[str] = None
        self._code_block_counter = 0

        # Статус-бар
        self._phase_start = 0.0

        # Сервер
        self._server_var = tk.StringVar(value="LM Studio")
        self._server_url = SERVERS["LM Studio"]

        # Настройки генерации
        self._context_window_var = tk.IntVar(value=DEFAULT_CONTEXT_WINDOW)
        self._max_tokens_var  = tk.IntVar(value=DEFAULT_MAX_TOKENS)
        self._temperature_var = tk.DoubleVar(value=0.3)
        self._think_var       = tk.BooleanVar(value=False)
        self._language_var    = tk.StringVar(value=DEFAULT_LANGUAGE_MODE)

        # Панель быстрого управления на главном экране.
        self._auto_context_var = tk.BooleanVar(value=True)
        self._control_deck_visible = tk.BooleanVar(value=True)
        self._server_context_window: Optional[int] = None
        self._server_max_context_window: Optional[int] = None
        self._server_context_model: str = ""
        self._context_presets = (4096, 8192, 16384, 32768, 65536, 98304,
                                 131072, 196608, 262144)

        # Видимость панелей
        self._show_right = tk.BooleanVar(value=False)

        # Сессия
        self._session_name = DEFAULT_SESSION
        self._session_var  = tk.StringVar(value=DEFAULT_SESSION)

        # API ключи поиска (загружаются из сессии)
        self._api_keys: Dict[str, str] = {
            "github":    os.environ.get("GITHUB_TOKEN", ""),
            "tavily":    os.environ.get("TAVILY_API_KEY", ""),
            "so_key":    "",   # Stack Overflow ключ (опционален)
        }
        # Активный источник (авто = умный роутинг)
        self._search_source_var = tk.StringVar(value="auto")

        self._setup_styles()
        self._create_menu()
        self._create_toolbar()
        self._create_control_deck()
        self._create_main_layout()
        self._create_chat_panel()
        self._create_right_notebook()
        self._create_status_bar()

        # Привязка закрытия — сохраняем сессию
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # Загружаем сессию
        self._load_session(self._session_name, silent=True)
        if not self.chat_history:
            self._welcome()

        self._check_connection()
        self._update_security_ui()
        self.root.deiconify()
