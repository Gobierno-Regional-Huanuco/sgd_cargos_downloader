from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


APP_DIR = Path.home() / ".sgd_cargos_downloader"
CONFIG_FILE = APP_DIR / "config.json"


def service_config_path() -> Path:
    """Keeps the SGD endpoint portable with the packaged executable."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "sgd_service.json"
    return Path.cwd() / "sgd_service.json"


@dataclass
class AppConfig:
    service_url: str = ""
    output_dir: str = str(Path.home() / "Downloads" / "cargos_sgd")
    last_username: str = ""
    period: int = 2023
    group_size: int = 1000
    per_page: int = 500
    include_related: bool = True
    include_personal_for_office: bool = False
    related_batch_size: int = 200


def load_config() -> AppConfig:
    defaults = asdict(AppConfig())
    if CONFIG_FILE.exists():
        try:
            raw = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            raw = {}
        defaults.update(
            {key: value for key, value in raw.items() if key in defaults and key != "service_url"}
        )
    defaults["service_url"] = _load_service_url()
    return AppConfig(**defaults)


def save_config(config: AppConfig) -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    values = asdict(config)
    values.pop("service_url", None)
    CONFIG_FILE.write_text(
        json.dumps(values, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    _save_service_url(config.service_url)


def _load_service_url() -> str:
    path = service_config_path()
    if not path.exists():
        return ""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    if not isinstance(raw, dict):
        return ""
    return str(raw.get("service_url") or "").strip()


def _save_service_url(service_url: str) -> None:
    value = service_url.strip()
    if not value:
        return
    path = service_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"service_url": value}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
