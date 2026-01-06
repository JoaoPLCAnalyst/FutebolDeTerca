# pages/scout.py
import streamlit as st
import json
import os
import time
from datetime import datetime

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

def pause_match():
    if st.session_state.match["running"]:
        st.session_state.match["elapsed"] = time.time() - st.session_state.match["start_time"]
        st.session_state.match["running"] = False

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

def assign_player(pid, team_num):
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
        # decrementar gols do jogador e placar do time
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
# Layout: três colunas (Time1 | Centro | Time2)
# ------------------------
left_col, center_col, right_col = st.columns([3, 2, 3])

# --- Centro: cronômetro e jogadores disponíveis ---
with center_col:
    st.markdown("<div style='text-align:center'>", unsafe_allow_html=True)
    st.markdown("### ⏱️ Cronômetro", unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1,1,1])
    with c1:
        if st.button("Iniciar / Retomar"):
            start_match()
    with c2:
        if st.button("Pausar"):
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
        cols = st.columns(3)
        for i, (pid, nome) in enumerate(available):
            col = cols[i % 3]
            with col:
                st.markdown(f"**{nome}**")
                if st.button("→ Time 1", key=f"avail-to1-{pid}"):
                    assign_player(pid, 1)
                if st.button("→ Time 2", key=f"avail-to2-{pid}"):
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
            nome = p.get("nome", pid)
            cols = st.columns([3,1,1,1,1])
            with cols[0]:
                st.markdown(f"**{nome}**")
                st.caption(f"Gols: {p.get('gols',0)} | Assistências: {p.get('assistencias',0)}")
            with cols[1]:
                if st.button("+ Gol", key=f"+gol-{pid}"):
                    record_event("gol", 1, scorer_pid=pid, assister_pid=None, delta_scorer=1, delta_assister=0)
                    st.rerun()
            with cols[2]:
                if st.button("- Gol", key=f"-gol-{pid}"):
                    if p.get("gols",0) > 0:
                        record_event("gol", 1, scorer_pid=pid, assister_pid=None, delta_scorer=-1, delta_assister=0)
                        st.rerun()
            with cols[3]:
                if st.button("+ Assist", key=f"+ast-{pid}"):
                    record_event("assist", 1, scorer_pid=None, assister_pid=pid, delta_scorer=0, delta_assister=1)
                    st.rerun()
            with cols[4]:
                if st.button("- Assist", key=f"-ast-{pid}"):
                    if p.get("assistencias",0) > 0:
                        record_event("assist", 1, scorer_pid=None, assister_pid=pid, delta_scorer=0, delta_assister=-1)
                        st.rerun()
            # Botões rápidos abaixo do jogador para mover entre times
            b1, b2 = st.columns([1,1])
            with b1:
                if st.button("→ Time 2", key=f"move-to2-{pid}"):
                    assign_player(pid, 2)
            with b2:
                if st.button("Remover (Nenhum)", key=f"move-none-{pid}"):
                    assign_player(pid, 0)

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
            nome = p.get("nome", pid)
            cols = st.columns([3,1,1,1,1])
            with cols[0]:
                st.markdown(f"**{nome}**")
                st.caption(f"Gols: {p.get('gols',0)} | Assistências: {p.get('assistencias',0)}")
            with cols[1]:
                if st.button("+ Gol", key=f"+gol2-{pid}"):
                    record_event("gol", 2, scorer_pid=pid, assister_pid=None, delta_scorer=1, delta_assister=0)
                    st.rerun()
            with cols[2]:
                if st.button("- Gol", key=f"-gol2-{pid}"):
                    if p.get("gols",0) > 0:
                        record_event("gol", 2, scorer_pid=pid, assister_pid=None, delta_scorer=-1, delta_assister=0)
                        st.rerun()
            with cols[3]:
                if st.button("+ Assist", key=f"+ast2-{pid}"):
                    record_event("assist", 2, scorer_pid=None, assister_pid=pid, delta_scorer=0, delta_assister=1)
                    st.rerun()
            with cols[4]:
                if st.button("- Assist", key=f"-ast2-{pid}"):
                    if p.get("assistencias",0) > 0:
                        record_event("assist", 2, scorer_pid=None, assister_pid=pid, delta_scorer=0, delta_assister=-1)
                        st.rerun()
            # Botões rápidos abaixo do jogador para mover entre times
            b1, b2 = st.columns([1,1])
            with b1:
                if st.button("→ Time 1", key=f"move-to1-{pid}"):
                    assign_player(pid, 1)
            with b2:
                if st.button("Remover (Nenhum)", key=f"move-none2-{pid}"):
                    assign_player(pid, 0)

# ------------------------
# Painel de atribuição (abaixo): permite atribuir jogadores a times rapidamente (opcional)
# ------------------------
st.markdown("---")
st.markdown("### Atribuir jogadores rapidamente (lista)")
assign_cols = st.columns([3,3,2])
with assign_cols[0]:
    st.write("Jogadores")
    for pid, p in sorted(jogadores.items(), key=lambda kv: kv[1].get("nome","")):
        st.write(f"- {p.get('nome','—')} (ID: {pid})")
with assign_cols[1]:
    st.write("Atribuir")
    for pid, p in sorted(jogadores.items(), key=lambda kv: kv[1].get("nome","")):
        cur = st.session_state.match["team_assign"].get(pid, 0)
        choice = st.selectbox(f"team-{pid}", options=[0,1,2], index=cur,
                              format_func=lambda v: "Nenhum" if v==0 else ("Time 1" if v==1 else "Time 2"),
                              key=f"assign-{pid}")
        st.session_state.match["team_assign"][pid] = choice
with assign_cols[2]:
    if st.button("Salvar atribuições"):
        st.success("Atribuições salvas.")
        st.rerun()

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
# Finalizar / Logout
# ------------------------
st.markdown("---")
end_col1, end_col2 = st.columns([1,1])
with end_col1:
    if st.button("Finalizar partida (reiniciar estado)"):
        reset_match()
        st.success("Partida finalizada e estado reiniciado.")
        st.rerun()
with end_col2:
    if st.button("Sair (olheiro)"):
        for k in ["user_id","perfil","logged_in","is_admin","is_scout","login_message","login_time","match"]:
            if k in st.session_state:
                del st.session_state[k]
        st.success("Logout efetuado.")
        st.rerun()
