# pages/scout.py
import streamlit as st
import json
import os
import time
from datetime import datetime
import tempfile
import uuid
import base64
import requests

st.set_page_config(page_title="Olheiro - Futebol de Terça", layout="wide")

JOGADORES_FILE = "database/jogadores.json"
os.makedirs("database", exist_ok=True)

# ------------------------
# Proteção: só olheiro pode acessar
# ------------------------
if not st.session_state.get("is_scout"):
    st.title("Área do Olheiro")
    st.info("Acesso restrito. Faça login como olheiro para acessar esta página.")
    st.stop()

# ------------------------
# Utilitários
# ------------------------
def carregar_jogadores():
    if not os.path.exists(JOGADORES_FILE):
        return {}
    try:
        with open(JOGADORES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def salvar_jogadores(jogadores_dict):
    with open(JOGADORES_FILE, "w", encoding="utf-8") as f:
        json.dump(jogadores_dict, f, indent=2, ensure_ascii=False)

def ensure_match_state():
    if "match" not in st.session_state:
        st.session_state.match = {
            "running": False,
            "start_time": None,
            "elapsed": 0.0,
            "team_assign": {},   # player_id -> 0/1/2 (0 = none, 1 = team1, 2 = team2)
            "score": {"team1": 0, "team2": 0},
            "events": []  # list of {time, type, team, scorer, assister}
        }

# ------------------------
# GitHub upload opcional (usa secrets GITHUB_USER, GITHUB_REPO, GITHUB_TOKEN, GITHUB_BRANCH)
# ------------------------
GITHUB_USER = st.secrets.get("GITHUB_USER", "")
GITHUB_REPO = st.secrets.get("GITHUB_REPO", "")
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "")
GITHUB_BRANCH = st.secrets.get("GITHUB_BRANCH", "main")

def github_upload(path_local, repo_path, message):
    """Envia arquivo local ao GitHub (opcional). Retorna (ok, msg)."""
    if not GITHUB_USER or not GITHUB_REPO or not GITHUB_TOKEN:
        return False, "GitHub não configurado"
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/{repo_path}"
    with open(path_local, "rb") as f:
        content_b64 = base64.b64encode(f.read()).decode()
    get_file = requests.get(url, headers=headers, params={"ref": GITHUB_BRANCH})
    sha = get_file.json().get("sha") if get_file.status_code == 200 else None
    payload = {"message": message, "content": content_b64, "branch": GITHUB_BRANCH}
    if sha:
        payload["sha"] = sha
    resp = requests.put(url, headers=headers, json=payload)
    if resp.status_code in (200, 201):
        return True, f"ok ({resp.status_code})"
    else:
        return False, f"erro ({resp.status_code}): {resp.text}"

# ------------------------
# Inicialização
# ------------------------
ensure_match_state()
jogadores = carregar_jogadores()

# inicializa assign para novos jogadores
for pid in jogadores.keys():
    if pid not in st.session_state.match["team_assign"]:
        st.session_state.match["team_assign"][pid] = 0

# ------------------------
# Funções de evento e atribuição rápida
# ------------------------
def _now_elapsed():
    if st.session_state.match["running"]:
        return int(time.time() - st.session_state.match["start_time"])
    return int(st.session_state.match["elapsed"])

def start_match():
    if not st.session_state.match["running"]:
        if st.session_state.match["start_time"] is None:
            st.session_state.match["start_time"] = time.time()
            st.session_state.match["elapsed"] = 0.0
        else:
            st.session_state.match["start_time"] = time.time() - st.session_state.match["elapsed"]
        st.session_state.match["running"] = True
        st.rerun()

def pause_match():
    if st.session_state.match["running"]:
        st.session_state.match["elapsed"] = time.time() - st.session_state.match["start_time"]
        st.session_state.match["running"] = False
        st.rerun()

def reset_match():
    st.session_state.match = {
        "running": False,
        "start_time": None,
        "elapsed": 0.0,
        "team_assign": {},
        "score": {"team1": 0, "team2": 0},
        "events": []
    }
    for pid in jogadores.keys():
        st.session_state.match["team_assign"][pid] = 0
    st.rerun()

def assign_player(pid, team_num):
    # não permite alterar atribuições enquanto a partida estiver rodando
    if st.session_state.match.get("running"):
        st.warning("Não é possível alterar atribuições enquanto a partida estiver em andamento.")
        return
    st.session_state.match["team_assign"][pid] = team_num
    st.rerun()

def record_event(ev_type, team_num, scorer_pid=None, assister_pid=None, delta_scorer=0, delta_assister=0):
    t = _now_elapsed()
    ev = {
        "time": t,
        "type": ev_type,  # "gol" or "assist"
        "team": f"team{team_num}",
        "scorer": scorer_pid,
        "assister": assister_pid
    }
    st.session_state.match["events"].append(ev)
    # atualizar placar e jogadores
    if ev_type == "gol" and scorer_pid:
        if team_num == 1:
            st.session_state.match["score"]["team1"] += delta_scorer
        else:
            st.session_state.match["score"]["team2"] += delta_scorer
        jogadores[scorer_pid]["gols"] = jogadores[scorer_pid].get("gols", 0) + delta_scorer
    if assister_pid and delta_assister != 0:
        jogadores[assister_pid]["assistencias"] = jogadores[assister_pid].get("assistencias", 0) + delta_assister
    salvar_jogadores(jogadores)

def undo_last_event():
    if not st.session_state.match["events"]:
        st.warning("Nenhum evento para desfazer.")
        return
    last = st.session_state.match["events"].pop()  # remove último evento
    ev_type = last.get("type")
    team = last.get("team")
    scorer = last.get("scorer")
    assister = last.get("assister")
    # reverter alterações
    if ev_type == "gol" and scorer:
        if jogadores.get(scorer):
            jogadores[scorer]["gols"] = max(0, jogadores[scorer].get("gols", 0) - 1)
        if team == "team1":
            st.session_state.match["score"]["team1"] = max(0, st.session_state.match["score"]["team1"] - 1)
        else:
            st.session_state.match["score"]["team2"] = max(0, st.session_state.match["score"]["team2"] - 1)
    if assister:
        if jogadores.get(assister):
            jogadores[assister]["assistencias"] = max(0, jogadores[assister].get("assistencias", 0) - 1)
    salvar_jogadores(jogadores)
    st.success("Último evento desfeito.")
    st.rerun()

# ------------------------
# Função única para renderizar bloco de jogador (evita duplicação)
# ------------------------
def render_player_block(pid, p, team_num):
    """
    Renderiza um bloco de jogador com botões únicos.
    team_num: 1 (Time1), 2 (Time2)
    """
    nome = p.get("nome", pid)
    gols = p.get("gols", 0)
    asts = p.get("assistencias", 0)

    st.markdown(f"**{nome}**")
    st.caption(f"Gols: {gols} | Assistências: {asts}")

    cols = st.columns([1,1,1,1])
    # + Gol
    if cols[0].button("Adicionar Gol", key=f"+gol-{team_num}-{pid}"):
        record_event("gol", team_num, scorer_pid=pid, assister_pid=None, delta_scorer=1, delta_assister=0)
        st.rerun()
    # - Gol
    if cols[1].button("Remover Gol", key=f"-gol-{team_num}-{pid}"):
        if gols > 0:
            record_event("gol", team_num, scorer_pid=pid, assister_pid=None, delta_scorer=-1, delta_assister=0)
            st.rerun()
    # + Assist
    if cols[2].button("Adicionar Assist", key=f"+ast-{team_num}-{pid}"):
        record_event("assist", team_num, scorer_pid=None, assister_pid=pid, delta_scorer=0, delta_assister=1)
        st.rerun()
    # - Assist
    if cols[3].button("Remover Assist", key=f"-ast-{team_num}-{pid}"):
        if asts > 0:
            record_event("assist", team_num, scorer_pid=None, assister_pid=pid, delta_scorer=0, delta_assister=-1)
            st.rerun()

    # botões rápidos abaixo para mover entre times / remover
    # desabilita movimentação enquanto partida estiver rodando
    disabled_moves = st.session_state.match.get("running", False)
    b1, b2, b3 = st.columns([1,1,1])
    if team_num == 1:
        if b1.button("→ Time 2", key=f"move-to2-{pid}", disabled=disabled_moves):
            assign_player(pid, 2)
    else:
        if b1.button("→ Time 1", key=f"move-to1-{pid}", disabled=disabled_moves):
            assign_player(pid, 1)
    if b2.button("Remover", key=f"move-none-{team_num}-{pid}", disabled=disabled_moves):
        assign_player(pid, 0)
    # botão para ver detalhes (opcional)
    if b3.button("Detalhes", key=f"det-{team_num}-{pid}"):
        st.write(f"ID: {pid}")

# ------------------------
# Layout: três colunas (Time1 | Centro | Time2)
# ------------------------
left_col, center_col, right_col = st.columns([3, 2, 3])

# --- Centro: cronômetro e jogadores disponíveis ---
with center_col:
    st.markdown("<div style='text-align:center'>", unsafe_allow_html=True)
    st.markdown("### ⏱️ Cronômetro", unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1,1,1])
    with c1:
        if st.button("Iniciar / Retomar", disabled=st.session_state.match.get("running", False)):
            start_match()
    with c2:
        if st.button("Pausar", disabled=not st.session_state.match.get("running", False)):
            pause_match()
    with c3:
        if st.button("Reiniciar"):
            reset_match()

    if st.session_state.match["running"]:
        st.session_state.match["elapsed"] = time.time() - st.session_state.match["start_time"]

    elapsed = int(st.session_state.match["elapsed"])
    mins = elapsed // 60
    secs = elapsed % 60
    st.markdown(f"<h1 style='text-align:center;font-size:48px;margin:8px'>{mins:02d}:{secs:02d}</h1>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### Jogadores disponíveis")
    available = [ (pid, jogadores[pid]["nome"]) for pid,t in st.session_state.match["team_assign"].items() if t==0 and pid in jogadores ]
    if not available:
        st.write("Nenhum jogador disponível")
    else:
        # exibe em 3 colunas com botões rápidos para atribuir
        cols = st.columns(3)
        for i, (pid, nome) in enumerate(available):
            col = cols[i % 3]
            with col:
                st.markdown(f"**{nome}**")
                # desabilita atribuição enquanto partida estiver rodando
                if st.button("→ Time 1", key=f"avail-to1-{pid}", disabled=st.session_state.match.get("running", False)):
                    assign_player(pid, 1)
                if st.button("→ Time 2", key=f"avail-to2-{pid}", disabled=st.session_state.match.get("running", False)):
                    assign_player(pid, 2)

# --- Left: Time 1 ---
with left_col:
    st.markdown("## TIME 1")
    st.metric("Placar Time 1", st.session_state.match["score"]["team1"])
    st.markdown("---")
    team1 = [ (pid, jogadores[pid]) for pid,t in st.session_state.match["team_assign"].items() if t==1 and pid in jogadores ]
    if not team1:
        st.write("Nenhum jogador atribuído ao Time 1")
    else:
        for pid, p in team1:
            render_player_block(pid, p, team_num=1)
            st.markdown("---")

# --- Right: Time 2 ---
with right_col:
    st.markdown("## TIME 2")
    st.metric("Placar Time 2", st.session_state.match["score"]["team2"])
    st.markdown("---")
    team2 = [ (pid, jogadores[pid]) for pid,t in st.session_state.match["team_assign"].items() if t==2 and pid in jogadores ]
    if not team2:
        st.write("Nenhum jogador atribuído ao Time 2")
    else:
        for pid, p in team2:
            render_player_block(pid, p, team_num=2)
            st.markdown("---")

# ------------------------
# Painel de atribuição (abaixo): permite atribuir jogadores a times rapidamente (opcional)
# ------------------------
# st.markdown("---")
# st.markdown("### Atribuir jogadores rapidamente (lista)")
# assign_cols = st.columns([3,3,2])
# with assign_cols[0]:
#     st.write("Jogadores")
#     for pid, p in sorted(jogadores.items(), key=lambda kv: kv[1].get("nome","")):
#         st.write(f"- {p.get('nome','—')} (ID: {pid})")
# with assign_cols[1]:
#     st.write("Atribuir")
#     for pid, p in sorted(jogadores.items(), key=lambda kv: kv[1].get("nome","")):
#         cur = st.session_state.match["team_assign"].get(pid, 0)
#         # desabilita selectbox enquanto partida estiver rodando
#         choice = st.selectbox(
#             f"team-{pid}",
#             options=[0,1,2],
#             index=cur,
#             format_func=lambda v: "Nenhum" if v==0 else ("Time 1" if v==1 else "Time 2"),
#             key=f"assign-{pid}",
#             disabled=st.session_state.match.get("running", False)
#         )
#         # só atualiza se não estiver rodando
#         if not st.session_state.match.get("running", False):
#             st.session_state.match["team_assign"][pid] = choice
# with assign_cols[2]:
#     if st.button("Salvar atribuições", disabled=st.session_state.match.get("running", False)):
#         st.success("Atribuições salvas.")
#         st.rerun()

# ------------------------
# Eventos registrados (histórico) com Desfazer
# ------------------------
st.markdown("---")
st.markdown("### Eventos registrados")
undo_col, events_col = st.columns([1,5])
with undo_col:
    if st.button("⟲ Desfazer último evento"):
        undo_last_event()
with events_col:
    if not st.session_state.match["events"]:
        st.write("Nenhum evento registrado.")
    else:
        for ev in st.session_state.match["events"]:
            t = ev["time"]
            mm = t // 60
            ss = t % 60
            if ev["type"] == "gol":
                scorer_name = jogadores.get(ev["scorer"], {}).get("nome", ev.get("scorer"))
                assister_name = jogadores.get(ev["assister"], {}).get("nome", "") if ev.get("assister") else ""
                st.write(f"{mm:02d}:{ss:02d} — {ev['team']} — Gol: **{scorer_name}**" + (f" | Assist: {assister_name}" if assister_name else ""))
            else:
                assister_name = jogadores.get(ev["assister"], {}).get("nome", ev.get("assister"))
                st.write(f"{mm:02d}:{ss:02d} — {ev['team']} — Assistência: **{assister_name}**")

# ------------------------
# Finalizar / Logout (gera arquivo por rodada e atualiza jogadores.json)
# ------------------------
def _write_atomic(path, data_bytes):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path))
    os.close(fd)
    with open(tmp, "wb") as f:
        f.write(data_bytes)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)

def _rodada_filepath(rodada_id):
    return os.path.join("database", "rodadas", f"{rodada_id}.json")

def _persistir_rodada_e_atualizar_jogadores():
    # prepara diretório de rodadas
    rodadas_dir = os.path.join("database", "rodadas")
    os.makedirs(rodadas_dir, exist_ok=True)

    # gera id e caminho
    rodada_id = f"rodada-{uuid.uuid4().hex[:8]}"
    rodada_path = _rodada_filepath(rodada_id)

    # monta resumo_jogadores a partir dos events
    resumo = {}
    for ev in st.session_state.match.get("events", []):
        if ev.get("type") == "gol" and ev.get("scorer"):
            pid = ev["scorer"]
            resumo.setdefault(pid, {"gols": 0, "assistencias": 0})
            resumo[pid]["gols"] += 1
        if ev.get("type") == "assist" and ev.get("assister"):
            pid = ev["assister"]
            resumo.setdefault(pid, {"gols": 0, "assistencias": 0})
            resumo[pid]["assistencias"] += 1

    score = st.session_state.match.get("score", {"team1": 0, "team2": 0})
    if score.get("team1", 0) > score.get("team2", 0):
        vencedor = "team1"
    elif score.get("team2", 0) > score.get("team1", 0):
        vencedor = "team2"
    else:
        vencedor = "empate"

    rodada_entry = {
        "id": rodada_id,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "vencedor": vencedor,
        "placar": score,
        "events": st.session_state.match.get("events", []),
        "resumo_jogadores": resumo
    }

    # idempotência simples: se arquivo já existe, aborta
    if os.path.exists(rodada_path):
        st.warning("Rodada já registrada. Operação abortada.")
        return False

    # grava rodada atômica
    try:
        _write_atomic(rodada_path, json.dumps(rodada_entry, ensure_ascii=False, indent=2).encode("utf-8"))
    except Exception as e:
        st.error(f"Falha ao salvar arquivo da rodada: {e}")
        return False

    # atualiza jogadores.json incrementando totais
    try:
        # carrega do disco para evitar sobrescrever mudanças externas
        if os.path.exists(JOGADORES_FILE):
            with open(JOGADORES_FILE, "r", encoding="utf-8") as f:
                jogadores_on_disk = json.load(f)
        else:
            jogadores_on_disk = {}

        # aplica incrementos do resumo
        for pid, vals in resumo.items():
            if pid not in jogadores_on_disk:
                # cria registro mínimo se não existir
                jogadores_on_disk[pid] = {
                    "nome": pid,
                    "valor": 0,
                    "gols": 0,
                    "assistencias": 0,
                    "imagem": ""
                }
            jogadores_on_disk[pid]["gols"] = jogadores_on_disk[pid].get("gols", 0) + vals.get("gols", 0)
            jogadores_on_disk[pid]["assistencias"] = jogadores_on_disk[pid].get("assistencias", 0) + vals.get("assistencias", 0)

        # incrementa vitorias por jogador se desejar: aqui incrementa vitorias para todos do time vencedor
        if vencedor in ("team1", "team2"):
            for pid, team in st.session_state.match.get("team_assign", {}).items():
                if team == (1 if vencedor == "team1" else 2):
                    jogadores_on_disk[pid]["vitorias"] = jogadores_on_disk[pid].get("vitorias", 0) + 1

        # grava jogadores.json atômico
        _write_atomic(JOGADORES_FILE, json.dumps(jogadores_on_disk, ensure_ascii=False, indent=2).encode("utf-8"))

        # opcional: upload para GitHub dos arquivos novos/alterados
        if GITHUB_USER and GITHUB_REPO and GITHUB_TOKEN:
            ok1, out1 = github_upload(rodada_path, f"database/rodadas/{os.path.basename(rodada_path)}", f"Adiciona rodada {rodada_id}")
            ok2, out2 = github_upload(JOGADORES_FILE, JOGADORES_FILE, f"Atualiza jogadores após {rodada_id}")
            if not ok1:
                st.warning(f"Rodada salva localmente, mas falha ao enviar para GitHub: {out1}")
            if not ok2:
                st.warning(f"Jogadores atualizados localmente, mas falha ao enviar para GitHub: {out2}")

    except Exception as e:
        st.error(f"Falha ao atualizar jogadores: {e}")
        # opcional: remover o arquivo de rodada se desejar rollback
        return False

    return True

# Botões finais: Finalizar partida e Sair (olheiro)
st.markdown("---")
end_col1, end_col2 = st.columns([1,1])
with end_col1:
    if st.button("Finalizar partida (reiniciar estado)"):
        ok = _persistir_rodada_e_atualizar_jogadores()
        if ok:
            reset_match()
            st.success("Partida finalizada, resultado registrado e estado reiniciado.")
        else:
            st.error("Ocorreu um problema ao registrar a rodada; verifique os logs e tente novamente.")
        st.rerun()
with end_col2:
    if st.button("Sair (olheiro)"):
        for k in ["user_id","perfil","logged_in","is_admin","is_scout","login_message","login_time","match"]:
            if k in st.session_state:
                del st.session_state[k]
        st.success("Logout efetuado.")
        st.rerun()
