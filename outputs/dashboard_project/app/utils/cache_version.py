# app/utils/cache_version.py
import json
from datetime import datetime
from pathlib import Path

_VERSION_FILE = Path("cache_version.json")

def get_cache_version() -> str:
    """Retorna a versão atual de cache (string UTC)."""
    if not _VERSION_FILE.exists():
        return bump_cache_version()
    try:
        payload = json.loads(_VERSION_FILE.read_text(encoding="utf-8"))
        return str(payload.get("version"))
    except Exception:
        return bump_cache_version()

def bump_cache_version() -> str:
    """Cria uma nova versão de cache (timestamp UTC)."""
    now = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    _VERSION_FILE.write_text(json.dumps({"version": now}), encoding="utf-8")
    return now
