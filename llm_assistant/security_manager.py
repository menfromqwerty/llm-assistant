"""Optional startup password and encrypted local session storage.

The password itself is never stored. A memory-hard scrypt derivation produces
an AES-256-GCM key kept only in RAM for the current process. When protection is
enabled, saved sessions are migrated from readable JSON to authenticated
``.llms`` containers.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from pathlib import Path
from typing import Dict, Optional, Tuple

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .common import *  # noqa: F401,F403


SECURITY_DIR = Path.home() / ".llm_assistant" / "security"
SECURITY_CONFIG_PATH = SECURITY_DIR / "security.json"

_SECURITY_MAGIC = b"LLMASST1"
_SECURITY_AAD_PREFIX = b"llm-assistant-v1:"
_PASSWORD_VERIFIER_MESSAGE = b"LLM Assistant password verifier v1"

# ~32 MiB per derivation. This is intentionally expensive enough to slow down
# offline guessing while still remaining practical on an ordinary desktop.
_DEFAULT_SCRYPT_N = 2**15
_DEFAULT_SCRYPT_R = 8
_DEFAULT_SCRYPT_P = 1
_DEFAULT_SCRYPT_MAXMEM = 128 * 1024 * 1024


class SecurityMixin:
    """Password protection and authenticated encryption support."""

    def _security_init_state(self) -> None:
        self._security_config: Dict[str, object] = {}
        self._security_key: Optional[bytes] = None
        self._security_unlocked: bool = False
        self._startup_aborted: bool = False
        self._security_failed_attempts: int = 0
        self._security_load_config()

    # ------------------------------------------------------------------
    # Configuration and key derivation
    # ------------------------------------------------------------------

    def _security_load_config(self) -> Dict[str, object]:
        config: Dict[str, object] = {}
        try:
            if SECURITY_CONFIG_PATH.exists():
                loaded = json.loads(SECURITY_CONFIG_PATH.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    config = loaded
        except Exception:
            # A malformed protection file must not silently unlock encrypted
            # content. Treat it as enabled but unusable and report at startup.
            config = {"enabled": True, "corrupt": True}
        self._security_config = config
        return config

    def _security_write_config(self, config: Dict[str, object]) -> None:
        SECURITY_DIR.mkdir(parents=True, exist_ok=True)
        temp = SECURITY_CONFIG_PATH.with_suffix(".json.tmp")
        temp.write_text(
            json.dumps(config, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temp.replace(SECURITY_CONFIG_PATH)
        try:
            os.chmod(SECURITY_CONFIG_PATH, 0o600)
        except OSError:
            pass
        self._security_config = dict(config)

    def _security_enabled(self) -> bool:
        return bool(self._security_config.get("enabled", False))

    @staticmethod
    def _security_derive_material(
        password: str,
        salt: bytes,
        *,
        n: int = _DEFAULT_SCRYPT_N,
        r: int = _DEFAULT_SCRYPT_R,
        p: int = _DEFAULT_SCRYPT_P,
    ) -> Tuple[bytes, bytes]:
        if not isinstance(password, str):
            raise TypeError("password must be a string")
        material = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=n,
            r=r,
            p=p,
            maxmem=_DEFAULT_SCRYPT_MAXMEM,
            dklen=64,
        )
        encryption_key = material[:32]
        verifier_key = material[32:]
        verifier = hmac.new(
            verifier_key,
            _PASSWORD_VERIFIER_MESSAGE,
            hashlib.sha256,
        ).digest()
        return encryption_key, verifier

    @staticmethod
    def _security_decode_b64(value: object, field_name: str) -> bytes:
        if not isinstance(value, str):
            raise ValueError(f"Invalid {field_name}")
        try:
            return base64.b64decode(value.encode("ascii"), validate=True)
        except Exception as exc:
            raise ValueError(f"Invalid {field_name}") from exc

    def _security_kdf_params(self) -> Tuple[int, int, int]:
        kdf = self._security_config.get("kdf", {})
        if not isinstance(kdf, dict):
            kdf = {}
        try:
            n = int(kdf.get("n", _DEFAULT_SCRYPT_N))
            r = int(kdf.get("r", _DEFAULT_SCRYPT_R))
            p = int(kdf.get("p", _DEFAULT_SCRYPT_P))
        except Exception as exc:
            raise ValueError("Invalid password KDF settings") from exc

        # Do not trust arbitrary values from a local JSON file: oversized KDF
        # parameters could otherwise be abused for denial of service.
        if n not in {2**14, 2**15, 2**16} or not (1 <= r <= 16) or not (1 <= p <= 4):
            raise ValueError("Unsupported password KDF settings")
        return n, r, p

    def _security_verify_password(self, password: str) -> Optional[bytes]:
        if not self._security_enabled() or self._security_config.get("corrupt"):
            return None
        salt = self._security_decode_b64(self._security_config.get("salt"), "salt")
        expected = self._security_decode_b64(
            self._security_config.get("verifier"), "verifier"
        )
        n, r, p = self._security_kdf_params()
        key, verifier = self._security_derive_material(
            password,
            salt,
            n=n,
            r=r,
            p=p,
        )
        return key if hmac.compare_digest(verifier, expected) else None

    @staticmethod
    def _security_new_config(password: str) -> Tuple[Dict[str, object], bytes]:
        salt = secrets.token_bytes(16)
        key, verifier = SecurityMixin._security_derive_material(password, salt)
        config: Dict[str, object] = {
            "version": 1,
            "enabled": True,
            "encrypt_sessions": True,
            "salt": base64.b64encode(salt).decode("ascii"),
            "verifier": base64.b64encode(verifier).decode("ascii"),
            "kdf": {
                "name": "scrypt",
                "n": _DEFAULT_SCRYPT_N,
                "r": _DEFAULT_SCRYPT_R,
                "p": _DEFAULT_SCRYPT_P,
                "dklen": 64,
            },
            "cipher": "AES-256-GCM",
        }
        return config, key

    # ------------------------------------------------------------------
    # Authenticated encryption
    # ------------------------------------------------------------------

    def _security_encrypt_bytes(
        self,
        plaintext: bytes,
        purpose: str = "session",
        *,
        key: Optional[bytes] = None,
    ) -> bytes:
        active_key = key or self._security_key
        if not active_key:
            raise RuntimeError("Protection is locked")
        nonce = secrets.token_bytes(12)
        aad = _SECURITY_AAD_PREFIX + purpose.encode("utf-8")
        ciphertext = AESGCM(active_key).encrypt(nonce, plaintext, aad)
        return _SECURITY_MAGIC + nonce + ciphertext

    def _security_decrypt_bytes(
        self,
        payload: bytes,
        purpose: str = "session",
        *,
        key: Optional[bytes] = None,
    ) -> bytes:
        active_key = key or self._security_key
        if not active_key:
            raise RuntimeError("Protection is locked")
        if not payload.startswith(_SECURITY_MAGIC) or len(payload) < len(_SECURITY_MAGIC) + 13:
            raise ValueError("Unsupported encrypted file format")
        nonce_start = len(_SECURITY_MAGIC)
        nonce = payload[nonce_start:nonce_start + 12]
        ciphertext = payload[nonce_start + 12:]
        aad = _SECURITY_AAD_PREFIX + purpose.encode("utf-8")
        try:
            return AESGCM(active_key).decrypt(nonce, ciphertext, aad)
        except InvalidTag as exc:
            raise ValueError("Encrypted data is damaged or the password is incorrect") from exc

    # ------------------------------------------------------------------
    # Startup unlock
    # ------------------------------------------------------------------

    def _security_startup_unlock(self) -> bool:
        """Unlock protected data before the main interface loads.

        If no password has ever been configured, this returns immediately and
        no startup prompt is shown.
        """
        self._security_load_config()
        if not self._security_enabled():
            self._security_unlocked = True
            return True

        if self._security_config.get("corrupt"):
            messagebox.showerror(
                "Security / Защита",
                "The protection settings are damaged.\n\n"
                "Файл настроек защиты повреждён. Приложение не будет открыто, "
                "чтобы не обходить пароль.",
                parent=self.root,
            )
            return False

        for attempt in range(1, 6):
            password = self._security_password_prompt(
                title="🔐 LLM Assistant",
                prompt=(
                    "Enter the startup password / Введите пароль запуска\n\n"
                    f"Attempt / Попытка: {attempt}/5"
                ),
            )
            if password is None:
                return False
            try:
                key = self._security_verify_password(password)
            except Exception as exc:
                messagebox.showerror(
                    "Security error / Ошибка защиты",
                    str(exc),
                    parent=self.root,
                )
                return False
            if key:
                self._security_key = key
                self._security_unlocked = True
                self._security_failed_attempts = 0
                try:
                    self._security_encrypt_remaining_plaintext_sessions()
                except Exception as exc:
                    messagebox.showwarning(
                        "Security / Защита",
                        "The application was unlocked, but some old session files "
                        f"could not be encrypted.\n\n{exc}",
                        parent=self.root,
                    )
                return True

            self._security_failed_attempts += 1
            if attempt < 5:
                delay = min(2 ** (attempt - 1), 8)
                messagebox.showwarning(
                    "Wrong password / Неверный пароль",
                    f"Incorrect password. Try again in {delay} sec.\n"
                    f"Неверный пароль. Повтор через {delay} сек.",
                    parent=self.root,
                )
                self.root.update_idletasks()
                time.sleep(delay)

        messagebox.showerror(
            "Access denied / Доступ запрещён",
            "Too many failed attempts. The application will close.\n\n"
            "Слишком много неверных попыток. Приложение будет закрыто.",
            parent=self.root,
        )
        return False

    def _security_password_prompt(self, title: str, prompt: str) -> Optional[str]:
        """Small modal password entry with show/hide control."""
        result: Dict[str, Optional[str]] = {"value": None}
        win = tk.Toplevel(self.root)
        win.title(title)
        win.geometry("470x235")
        win.resizable(False, False)
        win.configure(bg="#171a1f")
        win.transient(self.root)
        win.grab_set()

        tk.Label(
            win,
            text="🔐",
            font=("Segoe UI Emoji", 26),
            bg="#171a1f",
            fg="#58a6ff",
        ).pack(pady=(16, 2))
        tk.Label(
            win,
            text=prompt,
            justify=tk.CENTER,
            wraplength=420,
            font=("Segoe UI", 10),
            bg="#171a1f",
            fg="#e6edf3",
        ).pack(padx=20, pady=(0, 10))

        entry = tk.Entry(
            win,
            show="●",
            width=38,
            font=("Segoe UI", 11),
            bg="#2d333b",
            fg="white",
            insertbackground="white",
            relief=tk.FLAT,
        )
        entry.pack(ipady=6, padx=24)

        show_var = tk.BooleanVar(value=False)

        def toggle_show() -> None:
            entry.config(show="" if show_var.get() else "●")

        tk.Checkbutton(
            win,
            text="Show password / Показать пароль",
            variable=show_var,
            command=toggle_show,
            bg="#171a1f",
            fg="#9da7b3",
            activebackground="#171a1f",
            activeforeground="white",
            selectcolor="#171a1f",
        ).pack(pady=(5, 7))

        buttons = tk.Frame(win, bg="#171a1f")
        buttons.pack(fill=tk.X, padx=24)

        def accept() -> None:
            result["value"] = entry.get()
            win.destroy()

        def cancel() -> None:
            result["value"] = None
            win.destroy()

        tk.Button(
            buttons,
            text="Unlock / Открыть",
            command=accept,
            bg="#238636",
            fg="white",
            relief=tk.FLAT,
            padx=18,
            pady=6,
            font=("Segoe UI", 9, "bold"),
        ).pack(side=tk.LEFT)
        tk.Button(
            buttons,
            text="Exit / Выход",
            command=cancel,
            bg="#6e2631",
            fg="white",
            relief=tk.FLAT,
            padx=18,
            pady=6,
        ).pack(side=tk.RIGHT)

        win.protocol("WM_DELETE_WINDOW", cancel)
        win.bind("<Return>", lambda _event: accept())
        win.bind("<Escape>", lambda _event: cancel())
        entry.focus_set()
        self.root.wait_window(win)
        return result["value"]

    # ------------------------------------------------------------------
    # Session migration
    # ------------------------------------------------------------------

    @staticmethod
    def _security_atomic_write(path: Path, payload: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(path.suffix + ".tmp")
        temp.write_bytes(payload)
        temp.replace(path)
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass

    def _security_encrypt_remaining_plaintext_sessions(self) -> None:
        if not self._security_enabled() or not self._security_key:
            return
        self._security_encrypt_plaintext_sessions_with_key(self._security_key)

    def _security_encrypt_plaintext_sessions_with_key(self, key: bytes) -> None:
        sources = sorted(SESSION_DIR.glob("*.json"))
        prepared = []
        for source in sources:
            target = source.with_suffix(".llms")
            payload = source.read_bytes()
            encrypted = self._security_encrypt_bytes(payload, "session", key=key)
            temp = target.with_suffix(".llms.tmp")
            temp.write_bytes(encrypted)
            prepared.append((source, target, temp))

        for _source, target, temp in prepared:
            temp.replace(target)
            try:
                os.chmod(target, 0o600)
            except OSError:
                pass
        for source, _target, _temp in prepared:
            source.unlink(missing_ok=True)

    def _security_decrypt_sessions_with_key(self, key: bytes) -> None:
        sources = sorted(SESSION_DIR.glob("*.llms"))
        prepared = []
        for source in sources:
            target = source.with_suffix(".json")
            plaintext = self._security_decrypt_bytes(
                source.read_bytes(), "session", key=key
            )
            # Validate before committing a readable file.
            json.loads(plaintext.decode("utf-8"))
            temp = target.with_suffix(".json.tmp")
            temp.write_bytes(plaintext)
            prepared.append((source, target, temp))

        for _source, target, temp in prepared:
            temp.replace(target)
            try:
                os.chmod(target, 0o600)
            except OSError:
                pass
        for source, _target, _temp in prepared:
            source.unlink(missing_ok=True)

    def _security_reencrypt_sessions(self, old_key: bytes, new_key: bytes) -> None:
        sources = sorted(SESSION_DIR.glob("*.llms"))
        prepared = []
        for source in sources:
            plaintext = self._security_decrypt_bytes(
                source.read_bytes(), "session", key=old_key
            )
            json.loads(plaintext.decode("utf-8"))
            encrypted = self._security_encrypt_bytes(
                plaintext, "session", key=new_key
            )
            temp = source.with_suffix(".llms.rekey")
            temp.write_bytes(encrypted)
            prepared.append((source, temp))

        for source, temp in prepared:
            temp.replace(source)
            try:
                os.chmod(source, 0o600)
            except OSError:
                pass

    # ------------------------------------------------------------------
    # In-app settings
    # ------------------------------------------------------------------

    def _security_ui_code(self) -> str:
        if hasattr(self, "_ui_language_code"):
            return self._ui_language_code()
        return "bi"

    def _security_button_text(self) -> str:
        code = self._security_ui_code()
        enabled = self._security_enabled()
        if enabled:
            return {
                "ru": "🔒 ЗАЩИТА",
                "en": "🔒 SECURITY",
                "bi": "🔒 SECURITY / ЗАЩИТА",
            }.get(code, "🔒 SECURITY")
        return {
            "ru": "🔓 ЗАЩИТА",
            "en": "🔓 SECURITY",
            "bi": "🔓 SECURITY / ЗАЩИТА",
        }.get(code, "🔓 SECURITY")

    def _security_button_color(self) -> str:
        return "#238636" if self._security_enabled() else "#8a5a12"

    def _update_security_ui(self) -> None:
        if hasattr(self, "_security_btn"):
            self._security_btn.config(
                text=self._security_button_text(),
                bg=self._security_button_color(),
            )

    def _security_request_new_password(self) -> Optional[str]:
        first = self._security_password_prompt(
            "Set password / Установить пароль",
            "Create a password with at least 8 characters.\n"
            "Создайте пароль длиной не менее 8 символов.",
        )
        if first is None:
            return None
        if len(first) < 8:
            messagebox.showwarning(
                "Weak password / Слабый пароль",
                "Use at least 8 characters.\nИспользуйте минимум 8 символов.",
                parent=self.root,
            )
            return None
        second = self._security_password_prompt(
            "Confirm password / Подтверждение",
            "Repeat the new password / Повторите новый пароль",
        )
        if second is None:
            return None
        if not hmac.compare_digest(first, second):
            messagebox.showerror(
                "Password mismatch / Пароли не совпадают",
                "The passwords are different.\nВведённые пароли отличаются.",
                parent=self.root,
            )
            return None
        return first

    def _open_security_settings(self) -> None:
        win = tk.Toplevel(self.root)
        win.title("🔐 Security / Защита")
        win.geometry("610x430")
        win.resizable(False, False)
        win.configure(bg=self.C.get("bg", "#171a1f"))
        win.transient(self.root)
        win.grab_set()

        enabled = self._security_enabled()
        status_text = (
            "🔒 ENABLED / ВКЛЮЧЕНА" if enabled else "🔓 DISABLED / ОТКЛЮЧЕНА"
        )
        status_color = "#3fb950" if enabled else "#d29922"

        tk.Label(
            win,
            text="🔐 Application protection / Защита приложения",
            bg=self.C.get("bg", "#171a1f"),
            fg="white",
            font=("Segoe UI", 15, "bold"),
        ).pack(anchor=tk.W, padx=18, pady=(16, 4))
        tk.Label(
            win,
            text=status_text,
            bg=self.C.get("bg", "#171a1f"),
            fg=status_color,
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor=tk.W, padx=18, pady=(0, 10))

        explanation = (
            "When enabled, a password is requested at startup and saved sessions "
            "are encrypted with AES-256-GCM. The password and encryption key are "
            "never stored.\n\n"
            "После включения пароль запрашивается при запуске, а сохранённые "
            "сессии шифруются AES-256-GCM. Пароль и ключ шифрования не сохраняются."
        )
        tk.Label(
            win,
            text=explanation,
            justify=tk.LEFT,
            wraplength=565,
            bg=self.C.get("bg", "#171a1f"),
            fg="#b7c0ca",
            font=("Segoe UI", 10),
        ).pack(anchor=tk.W, padx=18, pady=(0, 14))

        warning = (
            "⚠ No password recovery is possible. Keep a backup of important files.\n"
            "⚠ Восстановить забытый пароль невозможно. Храните резервные копии."
        )
        tk.Label(
            win,
            text=warning,
            justify=tk.LEFT,
            wraplength=565,
            bg="#3a2b12",
            fg="#ffd580",
            padx=10,
            pady=8,
            font=("Segoe UI", 9, "bold"),
        ).pack(fill=tk.X, padx=18, pady=(0, 16))

        buttons = tk.Frame(win, bg=self.C.get("bg", "#171a1f"))
        buttons.pack(fill=tk.X, padx=18)

        if not enabled:
            tk.Button(
                buttons,
                text="🔐 Set password / Установить пароль",
                command=lambda: self._security_enable_from_dialog(win),
                bg="#238636",
                fg="white",
                relief=tk.FLAT,
                padx=16,
                pady=8,
                font=("Segoe UI", 10, "bold"),
            ).pack(fill=tk.X, pady=4)
        else:
            tk.Button(
                buttons,
                text="🔁 Change password / Изменить пароль",
                command=lambda: self._security_change_from_dialog(win),
                bg="#1f6feb",
                fg="white",
                relief=tk.FLAT,
                padx=16,
                pady=8,
                font=("Segoe UI", 10, "bold"),
            ).pack(fill=tk.X, pady=4)
            tk.Button(
                buttons,
                text="🔒 Lock now / Заблокировать сейчас",
                command=lambda: self._security_lock_from_dialog(win),
                bg="#6f42c1",
                fg="white",
                relief=tk.FLAT,
                padx=16,
                pady=8,
                font=("Segoe UI", 10, "bold"),
            ).pack(fill=tk.X, pady=4)
            tk.Button(
                buttons,
                text="🔓 Remove password / Удалить пароль",
                command=lambda: self._security_disable_from_dialog(win),
                bg="#9b2c2c",
                fg="white",
                relief=tk.FLAT,
                padx=16,
                pady=8,
                font=("Segoe UI", 10, "bold"),
            ).pack(fill=tk.X, pady=4)

        tk.Button(
            win,
            text="Close / Закрыть",
            command=win.destroy,
            bg=self.C.get("bg3", "#2d333b"),
            fg=self.C.get("fg", "white"),
            relief=tk.FLAT,
            padx=16,
            pady=6,
        ).pack(side=tk.BOTTOM, anchor=tk.E, padx=18, pady=14)

    def _security_save_current_before_change(self) -> None:
        if hasattr(self, "_save_session") and hasattr(self, "_session_name"):
            if not self._save_session(self._session_name, silent=True):
                raise RuntimeError(
                    "The current session could not be saved before changing protection"
                )

    def _security_enable_from_dialog(self, parent: tk.Toplevel) -> None:
        password = self._security_request_new_password()
        if not password:
            return
        try:
            self._security_save_current_before_change()
            config, key = self._security_new_config(password)
            # Commit the verifier before migrating old JSON. If migration is
            # interrupted, plaintext files remain readable and are retried on
            # the next successful unlock instead of being lost.
            self._security_write_config(config)
            self._security_key = key
            self._security_unlocked = True
        except Exception as exc:
            messagebox.showerror(
                "Security error / Ошибка защиты",
                f"Protection was not enabled.\nЗащита не включена.\n\n{exc}",
                parent=self.root,
            )
            return

        migration_error = None
        try:
            self._security_encrypt_plaintext_sessions_with_key(key)
        except Exception as exc:
            migration_error = str(exc)

        self._update_security_ui()
        parent.destroy()
        if migration_error:
            messagebox.showwarning(
                "Security enabled with warning / Защита включена",
                "The password is active, but one or more old session files "
                "remain unencrypted and will be retried at the next startup.\n\n"
                "Пароль активен, но некоторые старые сессии пока остались "
                f"незашифрованными.\n\n{migration_error}",
                parent=self.root,
            )
        else:
            messagebox.showinfo(
                "Security enabled / Защита включена",
                "A startup password is now required and sessions are encrypted.\n\n"
                "Теперь при запуске требуется пароль, а сессии зашифрованы.",
                parent=self.root,
            )

    def _security_change_from_dialog(self, parent: tk.Toplevel) -> None:
        current = self._security_password_prompt(
            "Current password / Текущий пароль",
            "Enter the current password / Введите текущий пароль",
        )
        if current is None:
            return
        old_key = self._security_verify_password(current)
        if not old_key:
            messagebox.showerror(
                "Wrong password / Неверный пароль",
                "The current password is incorrect.\nТекущий пароль неверен.",
                parent=self.root,
            )
            return
        new_password = self._security_request_new_password()
        if not new_password:
            return
        try:
            self._security_save_current_before_change()
            new_config, new_key = self._security_new_config(new_password)
            # First decrypt all containers with the old key. If a later step is
            # interrupted, readable JSON remains and no session is lost.
            self._security_decrypt_sessions_with_key(old_key)
            self._security_write_config(new_config)
            self._security_key = new_key
            self._security_unlocked = True
        except Exception as exc:
            messagebox.showerror(
                "Security error / Ошибка защиты",
                f"Password was not changed.\nПароль не изменён.\n\n{exc}",
                parent=self.root,
            )
            return

        migration_error = None
        try:
            self._security_encrypt_plaintext_sessions_with_key(new_key)
        except Exception as exc:
            migration_error = str(exc)

        self._update_security_ui()
        parent.destroy()
        if migration_error:
            messagebox.showwarning(
                "Password changed with warning / Пароль изменён",
                "The new password is active, but some sessions remain plaintext "
                "and will be retried at the next startup.\n\n"
                "Новый пароль активен, но некоторые сессии пока не зашифрованы.\n\n"
                + migration_error,
                parent=self.root,
            )
        else:
            messagebox.showinfo(
                "Password changed / Пароль изменён",
                "The password and session encryption key were changed.\n"
                "Пароль и ключ шифрования сессий изменены.",
                parent=self.root,
            )

    def _security_disable_from_dialog(self, parent: tk.Toplevel) -> None:
        current = self._security_password_prompt(
            "Remove password / Удаление пароля",
            "Enter the current password / Введите текущий пароль",
        )
        if current is None:
            return
        key = self._security_verify_password(current)
        if not key:
            messagebox.showerror(
                "Wrong password / Неверный пароль",
                "The current password is incorrect.\nТекущий пароль неверен.",
                parent=self.root,
            )
            return
        if not messagebox.askyesno(
            "Remove protection / Отключить защиту",
            "Saved sessions will be converted back to readable JSON and startup "
            "will no longer require a password. Continue?\n\n"
            "Сессии снова станут обычными JSON, а пароль при запуске будет "
            "отключён. Продолжить?",
            parent=self.root,
        ):
            return
        try:
            self._security_save_current_before_change()
            self._security_decrypt_sessions_with_key(key)
            SECURITY_CONFIG_PATH.unlink(missing_ok=True)
            self._security_config = {}
            self._security_key = None
            self._security_unlocked = True
        except Exception as exc:
            messagebox.showerror(
                "Security error / Ошибка защиты",
                f"Protection was not removed.\nЗащита не отключена.\n\n{exc}",
                parent=self.root,
            )
            return
        self._update_security_ui()
        parent.destroy()
        messagebox.showinfo(
            "Protection removed / Защита отключена",
            "The application will now start without a password.\n"
            "Теперь приложение запускается без пароля.",
            parent=self.root,
        )

    def _security_lock_from_dialog(self, parent: tk.Toplevel) -> None:
        parent.destroy()
        self._security_lock_now()

    def _security_lock_now(self) -> None:
        if not self._security_enabled():
            self._open_security_settings()
            return
        if getattr(self, "is_loading", False):
            messagebox.showwarning(
                "Model is running / Модель работает",
                "Wait for the current response before locking.\n"
                "Дождитесь завершения ответа перед блокировкой.",
                parent=self.root,
            )
            return
        if hasattr(self, "_save_session"):
            self._save_session(self._session_name, silent=True)
        self._security_key = None
        self._security_unlocked = False
        self.root.withdraw()
        unlocked = self._security_startup_unlock()
        if unlocked:
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()
        else:
            self._startup_aborted = True
            self.root.destroy()

    def _security_forget_key(self) -> None:
        self._security_key = None
        self._security_unlocked = False
