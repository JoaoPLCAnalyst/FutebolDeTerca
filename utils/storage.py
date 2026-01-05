import os
import json
import tempfile
from datetime import datetime

LINEUPS_DIR = "times/lineups"
HISTORY_DIR = "times/history"
os.makedirs(LINEUPS_DIR, exist_ok=True)
os.makedirs(HISTORY_DIR, exist_ok=True)

def _atomic_write(path: str, data: dict):
    dirn = os.path.dirname(path)
    os.makedirs(dirn, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=dirn)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            try: os.remove(tmp)
            except: pass

def carregar_lineup(user_id: str) -> dict:
    path = os.path.join(LINEUPS_DIR, f"{user_id}.json")
    if not os.path.exists(path):
        return {"user_id": user_id, "time": [], "atualizado_em": None}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def salvar_lineup(user_id: str, lineup: dict, save_history: bool = True):
    lineup["user_id"] = user_id
    lineup["atualizado_em"] = datetime.utcnow().isoformat() + "Z"
    path = os.path.join(LINEUPS_DIR, f"{user_id}.json")
    _atomic_write(path, lineup)
    if save_history:
        ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        hist_dir = os.path.join(HISTORY_DIR, user_id)
        os.makedirs(hist_dir, exist_ok=True)
        hist_path = os.path.join(hist_dir, f"{ts}.json")
        _atomic_write(hist_path, lineup)
    return True
