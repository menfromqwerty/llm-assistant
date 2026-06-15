"""Сборка главного класса приложения из независимых функциональных модулей."""

from .common import *
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
):
    def __init__(self, root: tk.Tk):
        self.root = root

        self._model_name: str = DEFAULT_MODEL_NAME
        self._available_models: List[str] = []
        self.root.title(f"🚀 LLM Assistant v1.01 — {self._model_name}")
        self.root.geometry("1600x900")
        self.root.minsize(1000, 650)

        self.current_project: Optional[str] = None
        self.loaded_files: Dict[str, str]   = {}
        self.chat_history: List[Message]    = []
        self.web_results: List[WebResult]   = []
        self.is_loading: bool               = False
        self._context_warning_shown: bool    = False
        self._autosave_after_response: bool  = True
        self._shutdown_requested: bool        = False

        self._context_mode_var = tk.StringVar(value="auto")
        self._file_context_budget_var = tk.IntVar(value=32768)
        self._file_context_selected: Dict[str, bool] = {}
        self._file_token_cache: Dict[str, tuple] = {}
        self._file_list_names: List[str] = []

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
        self._llama_cpp_settings: Dict[str, object] = {
            "executable": "",
            "model": "",
            "port": 8080,
            "extra_args": "",
        }

        self._stream_buffer    = ""
        self._in_code_block    = False
        self._current_code_tag: Optional[str] = None
        self._code_block_counter = 0

        self._phase_start = 0.0

        self._server_var = tk.StringVar(value="LM Studio")
        self._server_url = SERVERS["LM Studio"]

        self._max_tokens_var  = tk.IntVar(value=DEFAULT_MAX_TOKENS)
        self._temperature_var = tk.DoubleVar(value=0.3)
        self._think_var       = tk.BooleanVar(value=False)
        self._language_var    = tk.StringVar(value=DEFAULT_LANGUAGE_MODE)

        self._show_right = tk.BooleanVar(value=True)

        self._session_name = DEFAULT_SESSION
        self._session_var  = tk.StringVar(value=DEFAULT_SESSION)

        self._api_keys: Dict[str, str] = {
            "github":    os.environ.get("GITHUB_TOKEN", ""),
            "tavily":    os.environ.get("TAVILY_API_KEY", ""),
            "so_key":    "",
        }
        self._search_source_var = tk.StringVar(value="auto")

        self._setup_styles()
        self._create_menu()
        self._create_toolbar()
        self._create_main_layout()
        self._create_chat_panel()
        self._create_right_notebook()
        self._create_status_bar()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._load_session(self._session_name, silent=True)
        if not self.chat_history:
            self._welcome()

        self._check_connection()
