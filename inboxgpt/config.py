"""Configuration and persistent state directory manager for InboxGPT."""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
from dotenv import load_dotenv

# Load local environment variables if present
load_dotenv()

DEFAULT_CONFIG_DIR = Path.home() / ".inboxgpt"


class Config:
    """Manages paths and persistent settings for InboxGPT."""

    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or Path(
            os.getenv("INBOXGPT_HOME", str(DEFAULT_CONFIG_DIR))
        )
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.config_dir / "config.json"
        self.credentials_file = self.config_dir / "credentials.json"
        self.token_file = self.config_dir / "token.json"
        self.log_file = self.config_dir / "inboxgpt.log"

    def _load_json(self, path: Path) -> Dict[str, Any]:
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_json(self, path: Path, data: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def get_settings(self) -> Dict[str, Any]:
        return self._load_json(self.config_file)

    def update_settings(self, updates: Dict[str, Any]) -> None:
        data = self.get_settings()
        data.update(updates)
        self._save_json(self.config_file, data)

    def get_gemini_api_key(self) -> Optional[str]:
        # 1. Environment variable
        env_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if env_key:
            return env_key.strip()
        # 2. Config file
        settings = self.get_settings()
        return settings.get("gemini_api_key")

    def set_gemini_api_key(self, key: str) -> None:
        self.update_settings({"gemini_api_key": key.strip()})

    def get_nvidia_api_key(self) -> Optional[str]:
        env_key = os.getenv("NVIDIA_API_KEY")
        if env_key:
            return env_key.strip()
        return self.get_settings().get("nvidia_api_key")

    def set_nvidia_api_key(self, key: str) -> None:
        self.update_settings({"nvidia_api_key": key.strip()})

    def get_groq_api_key(self) -> Optional[str]:
        env_key = os.getenv("GROQ_API_KEY")
        if env_key:
            return env_key.strip()
        return self.get_settings().get("groq_api_key")

    def set_groq_api_key(self, key: str) -> None:
        self.update_settings({"groq_api_key": key.strip()})

    def get_openai_api_key(self) -> Optional[str]:
        env_key = os.getenv("OPENAI_API_KEY")
        if env_key:
            return env_key.strip()
        return self.get_settings().get("openai_api_key")

    def get_active_provider(self) -> str:
        env_prov = os.getenv("INBOXGPT_PROVIDER")
        if env_prov:
            return env_prov.lower().strip()
        settings = self.get_settings()
        if settings.get("provider"):
            return settings.get("provider").lower().strip()
        if self.get_nvidia_api_key():
            return "nvidia"
        if self.get_groq_api_key():
            return "groq"
        if self.get_gemini_api_key():
            return "gemini"
        if self.get_openai_api_key():
            return "openai"
        return "heuristic"


    def get_model_name(self) -> str:
        settings = self.get_settings()
        return settings.get(
            "model_name", os.getenv("INBOXGPT_MODEL", "gemini-3.5-flash-lite")
        )

    def set_model_name(self, model_name: str) -> None:
        self.update_settings({"model_name": model_name})

    def get_google_client_id(self) -> Optional[str]:
        env_val = os.getenv("GOOGLE_CLIENT_ID")
        if env_val:
            return env_val.strip()
        return self.get_settings().get("google_client_id")

    def get_google_client_secret(self) -> Optional[str]:
        env_val = os.getenv("GOOGLE_CLIENT_SECRET")
        if env_val:
            return env_val.strip()
        return self.get_settings().get("google_client_secret")

    def set_google_credentials(self, client_id: str, client_secret: str) -> None:
        self.update_settings({
            "google_client_id": client_id.strip(),
            "google_client_secret": client_secret.strip(),
        })

    def has_google_credentials(self) -> bool:
        if self.get_google_client_id() and self.get_google_client_secret():
            return True
        if os.getenv("GOOGLE_CLIENT_SECRETS_FILE"):
            return Path(os.environ["GOOGLE_CLIENT_SECRETS_FILE"]).exists()
        return self.credentials_file.exists()

    def get_credentials_path(self) -> Path:
        env_path = os.getenv("GOOGLE_CLIENT_SECRETS_FILE")
        if env_path and Path(env_path).exists():
            return Path(env_path)
        return self.credentials_file

    def has_google_token(self) -> bool:
        return self.token_file.exists()

    @property
    def cache_file(self) -> Path:
        return self.config_dir / "cache_emails.json"

    def load_cached_emails(self) -> list:
        """Load locally cached emails for instantaneous 0ms startup."""
        if not self.cache_file.exists():
            return []
        try:
            from inboxgpt.gmail.models import EmailMessage
            with open(self.cache_file, "r", encoding="utf-8") as f:
                raw_list = json.load(f)
            return [EmailMessage(**item) for item in raw_list]
        except Exception:
            return []

    def save_cached_emails(self, emails: list) -> None:
        """Persist emails to local disk cache."""
        try:
            data = [e.model_dump(mode="json") for e in emails]
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except Exception:
            pass


    def clear_session(self) -> None:
        """Clear active OAuth token, session email, and email disk cache for logout or account switching."""
        if self.token_file.exists():
            try:
                self.token_file.unlink()
            except Exception:
                pass
        if self.cache_file.exists():
            try:
                self.cache_file.unlink()
            except Exception:
                pass
        try:
            settings = self.get_settings()
            if "last_authenticated_email" in settings:
                settings.pop("last_authenticated_email", None)
                with open(self.settings_file, "w", encoding="utf-8") as f:
                    json.dump(settings, f, indent=2)
        except Exception:
            pass


# Global default configuration instance
config = Config()



import logging
from logging.handlers import RotatingFileHandler

def configure_logging(log_level: int = logging.INFO) -> logging.Logger:
    """Configures structured rotating file logger for InboxGPT (5MB, 3 backups)."""
    log_path = config.log_file
    logger = logging.getLogger("inboxgpt")
    if not logger.handlers:
        logger.setLevel(log_level)
        try:
            handler = RotatingFileHandler(
                str(log_path),
                maxBytes=5 * 1024 * 1024,
                backupCount=3,
                encoding="utf-8",
            )
            formatter = logging.Formatter(
                "%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        except Exception:
            pass
    return logger

logger = configure_logging()
