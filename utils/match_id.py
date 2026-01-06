# utils_files.py  (ou cole no topo de pages/scout.py)
import os, glob, json, tempfile
from datetime import datetime, timezone
import uuid


def _write_atomic(path, data_bytes):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path))
    os.close(fd)
    with open(tmp, "wb") as f:
        f.write(data_bytes)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)

def add_match_to_meta(rodada_id, match_id):
    meta_path = os.path.join("database", "rodadas", rodada_id, "meta.json")
    # carrega meta atual
    meta = {}
    if os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            try:
                meta = json.load(f)
            except Exception:
                meta = {}
    # garante estrutura mínima
    meta.setdefault("id", rodada_id)
    meta.setdefault("matches", [])
    # idempotência: só adiciona se não existir
    if match_id not in meta["matches"]:
        meta["matches"].append(match_id)
        # opcional: atualiza campo de contagem explícita
        meta["match_count"] = len(meta["matches"])
        # grava atômico
        _write_atomic(meta_path, json.dumps(meta, ensure_ascii=False, indent=2).encode("utf-8"))
        return True
    return False


def next_match_id_for_date(matches_dir, date_str, prefix="match", pad=2):
    os.makedirs(matches_dir, exist_ok=True)
    base_prefix = f"{date_str}-{prefix}-"
    existing = glob.glob(os.path.join(matches_dir, f"{base_prefix}*.json"))
    start = len(existing) + 1
    for n in range(start, start + 1000):
        seq = str(n).zfill(pad)
        match_id = f"{date_str}-{prefix}-{seq}"
        filepath = os.path.join(matches_dir, f"{match_id}.json")
        try:
            fd = os.open(filepath, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
            os.close(fd)
            # arquivo criado vazio; remove e devolve caminho (vamos gravar atômico depois)
            os.remove(filepath)
            return match_id, filepath
        except FileExistsError:
            continue
    raise RuntimeError("Não foi possível gerar match_id único")

def create_match_file(matches_dir, match_data, date_for_id=None):
    if date_for_id is None:
        date_for_id = datetime.now().strftime("%Y-%m-%d")
    match_id, filepath = next_match_id_for_date(matches_dir, date_for_id)
    match_data.setdefault("id", match_id)
    match_data.setdefault("timestamp_utc", datetime.now(timezone.utc).isoformat())
    _write_atomic(filepath, json.dumps(match_data, ensure_ascii=False, indent=2).encode("utf-8"))
    return match_id, filepath
