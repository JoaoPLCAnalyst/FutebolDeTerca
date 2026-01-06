import os, json, tempfile

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
    meta = {}
    if os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            try:
                meta = json.load(f)
            except Exception:
                meta = {}
    meta.setdefault("id", rodada_id)
    meta.setdefault("matches", [])
    if match_id not in meta["matches"]:
        meta["matches"].append(match_id)
        meta["match_count"] = len(meta["matches"])
        _write_atomic(meta_path, json.dumps(meta, ensure_ascii=False, indent=2).encode("utf-8"))
        return True
    return False
