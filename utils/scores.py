# utils/scores.py
import os, json, tempfile, shutil
from datetime import datetime, timezone

def _write_atomic(path, data_bytes):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path))
    os.close(fd)
    with open(tmp, "wb") as f:
        f.write(data_bytes)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)

def compute_scores_from_summary(summary: dict, formula=None):
    """
    Retorna dict com estrutura:
    {
      "rodada_id": "...",
      "timestamp": "...",
      "points_formula": {...},
      "scores": { player_id: {"gols":n,"assistencias":m,"vitorias":v,"pontos":p}, ... }
    }
    """
    if formula is None:
        formula = {"gol": 8, "assist": 4, "vitoria": 4}
    resumo = summary.get("resumo_por_jogador", {})
    rodada_id = summary.get("rodada_id")
    timestamp = summary.get("timestamp_closed") or datetime.now(timezone.utc).isoformat()
    scores = {}
    for pid, vals in resumo.items():
        gols = int(vals.get("gols", 0))
        assist = int(vals.get("assistencias", 0))
        vitorias = int(vals.get("vitorias", 0))
        pontos = gols * formula["gol"] + assist * formula["assist"] + vitorias * formula["vitoria"]
        scores[pid] = {"gols": gols, "assistencias": assist, "vitorias": vitorias, "pontos": int(pontos)}
    return {
        "rodada_id": rodada_id,
        "timestamp": timestamp,
        "points_formula": formula,
        "scores": scores
    }

def write_scores_file(rodada_dir: str, scores_obj: dict):
    """
    Grava scores.json em database/rodadas/<rodada>/scores.json (atômico).
    Retorna path do arquivo.
    """
    path = os.path.join(rodada_dir, "scores.json")
    _write_atomic(path, json.dumps(scores_obj, ensure_ascii=False, indent=2).encode("utf-8"))
    return path

def apply_scores_to_jogadores(scores_obj: dict, jogadores_path="database/jogadores.json", backup=True):
    """
    Aplica incrementos em jogadores.json de forma idempotente.
    - Verifica se pontos por rodada já existem e pula se já aplicados.
    - Cria backup antes de gravar.
    Retorna (applied_count, skipped_count).
    """
    rodada_id = scores_obj.get("rodada_id")
    if not rodada_id:
        raise ValueError("scores_obj precisa conter rodada_id")

    # carrega jogadores
    jogadores = {}
    if os.path.exists(jogadores_path):
        with open(jogadores_path, "r", encoding="utf-8") as f:
            try:
                jogadores = json.load(f)
            except Exception:
                jogadores = {}

    # backup
    if backup and os.path.exists(jogadores_path):
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        shutil.copy(jogadores_path, f"{jogadores_path}.bak-{ts}")

    applied = 0
    skipped = 0
    for pid, vals in scores_obj.get("scores", {}).items():
        pontos = int(vals.get("pontos", 0))
        # cria jogador se não existir
        if pid not in jogadores:
            jogadores[pid] = {
                "nome": pid,
                "imagem": "",
                "gols": 0,
                "assistencias": 0,
                "vitorias": 0,
                "pontos_total": 0,
                "pontos_por_rodada": {}
            }
        # idempotência: se já existe pontos para essa rodada, pular
        pontos_por_rodada = jogadores[pid].setdefault("pontos_por_rodada", {})
        if rodada_id in pontos_por_rodada:
            skipped += 1
            continue
        # aplicar incrementos (mantendo campos históricos)
        jogadores[pid]["gols"] = jogadores[pid].get("gols", 0) + int(vals.get("gols", 0))
        jogadores[pid]["assistencias"] = jogadores[pid].get("assistencias", 0) + int(vals.get("assistencias", 0))
        jogadores[pid]["vitorias"] = jogadores[pid].get("vitorias", 0) + int(vals.get("vitorias", 0))
        jogadores[pid]["pontos_total"] = jogadores[pid].get("pontos_total", 0) + pontos
        pontos_por_rodada[rodada_id] = pontos
        applied += 1

    # grava atômico
    _write_atomic(jogadores_path, json.dumps(jogadores, ensure_ascii=False, indent=2).encode("utf-8"))
    return applied, skipped

def generate_and_apply_scores(rodada_dir: str, summary_obj: dict, formula=None, jogadores_path="database/jogadores.json", github_upload_fn=None):
    """
    Fluxo completo:
      - compute scores
      - write scores.json
      - apply to jogadores.json (idempotente)
      - opcional: chamar github_upload_fn(path_local, repo_path, message) para upload
    Retorna dict com resultados.
    """
    scores_obj = compute_scores_from_summary(summary_obj, formula=formula)
    scores_path = write_scores_file(rodada_dir, scores_obj)

    applied, skipped = apply_scores_to_jogadores(scores_obj, jogadores_path=jogadores_path, backup=True)

    # opcional: upload
    upload_results = {}
    if github_upload_fn:
        try:
            ok, msg = github_upload_fn(scores_path, os.path.join("database", "rodadas", os.path.basename(rodada_dir), "scores.json"), f"Adiciona scores da {scores_obj.get('rodada_id')}")
            upload_results["scores"] = (ok, msg)
        except Exception as e:
            upload_results["scores"] = (False, str(e))

    return {
        "scores_path": scores_path,
        "applied": applied,
        "skipped": skipped,
        "upload": upload_results
    }
