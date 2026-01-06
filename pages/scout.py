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
            "paused_at": 0.0,
            "elapsed": 0.0,
            "team_assign": {},   # player_id -> 0/1/2 (0 = none, 1 = team1, 2 = team2)
            "score": {"team1": 0, "team2": 0},
            "events": []  # list of {time, team, scorer, assister}
        }

# ------------------------
# Inicialização
# ------------------------
ensure_match_state()
jogadores = carregar_jogadores()

# central layout: cronômetro e controles
st.title("📋 Painel do Olheiro")
st.markdown("### Cronômetro da partida (centralizado)")

# Cronômetro centralizado
timer_col1, timer_col2, timer_col3 = st.columns([1, 2, 1])
with timer_col2:
    timer_placeholder = st.empty()
    # controls
    c1, c2, c3 = st.columns([1,1,1])
    with c1:
        if st.button("Iniciar / Retomar"):
            if not st.session_state.match["running"]:
                # iniciar ou retomar
                if st.session_state.match["start_time"] is None:
                    st.session_state.match["start_time"] = time.time()
                    st.session_state.match["paused_at"] = 0.0
                else:
                    # retomar: ajusta start_time para descontar pausa
                    st.session_state.match["start_time"] = time.time() - st.session_state.match["elapsed"]
                st.session_state.match["running"] = True
    with c2:
        if st.button("Pausar"):
            if st.session_state.match["running"]:
                st.session_state.match["running"] = False
                st.session_state.match["elapsed"] = time.time() - st.session_state.match["start_time"]
    with c3:
        if st.button("Reiniciar"):
            st.session_state.match = {
                "running": False,
                "start_time": None,
                "paused_at": 0.0,
                "elapsed": 0.0,
                "team_assign": {},
                "score": {"team1": 0, "team2": 0},
                "events": []
            }

# Atualiza e exibe cronômetro
if st.session_state.match["running"]:
    st.session_state.match["elapsed"] = time.time() - st.session_state.match["start_time"]

elapsed = st.session_state.match["elapsed"]
mins = int(elapsed // 60)
secs = int(elapsed % 60)
timer_placeholder.markdown(f"<h1 style='text-align:center'>{mins:02d}:{secs:02d}</h1>", unsafe_allow_html=True)

st.markdown("---")

# ------------------------
# Lista de jogadores centralizada com atribuição de time
# ------------------------
st.markdown("### Jogadores cadastrados (atribua Time 1 / Time 2)")
players_col1, players_col2, players_col3 = st.columns([1, 3, 1])
with players_col2:
    if not jogadores:
        st.info("Nenhum jogador cadastrado.")
    else:
        # inicializa assign se necessário
        for pid in jogadores.keys():
            if pid not in st.session_state.match["team_assign"]:
                st.session_state.match["team_assign"][pid] = 0

        # exibe cada jogador com selectbox para time
        for pid, p in sorted(jogadores.items(), key=lambda kv: kv[1].get("nome","").lower()):
            nome = p.get("nome", pid)
            cols = st.columns([3,1])
            with cols[0]:
                st.markdown(f"**{nome}**")
            with cols[1]:
                choice = st.selectbox(
                    label=f"team-{pid}",
                    options=[0,1,2],
                    format_func=lambda v: "Nenhum" if v==0 else ("Time 1" if v==1 else "Time 2"),
                    index=st.session_state.match["team_assign"].get(pid,0)
                )
                st.session_state.match["team_assign"][pid] = choice

st.markdown("---")

# ------------------------
# Placar e registro de eventos (apenas quando partida iniciou)
# ------------------------
st.markdown("### Placar e registro de gols/assistências")
score_col1, score_col2, score_col3 = st.columns([1,1,1])
with score_col1:
    st.metric("Time 1", st.session_state.match["score"]["team1"])
with score_col3:
    st.metric("Time 2", st.session_state.match["score"]["team2"])

# Função auxiliar para obter players por time
def players_in_team(team_num):
    return [(pid, jogadores[pid]["nome"]) for pid, t in st.session_state.match["team_assign"].items() if t==team_num and pid in jogadores]

# Registrar gol
st.markdown("#### Registrar Gol")
if st.session_state.match["running"]:
    tcol1, tcol2 = st.columns(2)
    with tcol1:
        team_choice = st.radio("Escolha o time", [1,2], index=0, horizontal=True)
    with tcol2:
        team_players = players_in_team(team_choice)
        if not team_players:
            st.warning("Nenhum jogador atribuído a esse time.")
        else:
            scorer_pid = st.selectbox("Autor do gol", options=[pid for pid,_ in team_players], format_func=lambda pid: jogadores[pid]["nome"])
            assister_options = [pid for pid,_ in team_players if pid != scorer_pid]
            assister_pid = st.selectbox("Assistência (opcional)", options=[None]+assister_options, format_func=lambda v: (jogadores[v]["nome"] if v else "Nenhuma"))
            if st.button("Registrar Gol"):
                # atualiza placar e eventos
                if team_choice == 1:
                    st.session_state.match["score"]["team1"] += 1
                else:
                    st.session_state.match["score"]["team2"] += 1
                event = {
                    "time": int(st.session_state.match["elapsed"]),
                    "team": f"team{team_choice}",
                    "scorer": scorer_pid,
                    "assister": assister_pid
                }
                st.session_state.match["events"].append(event)
                # incrementa contadores locais (não persiste ainda)
                jogadores[scorer_pid]["gols"] = jogadores[scorer_pid].get("gols",0) + 1
                if assister_pid:
                    jogadores[assister_pid]["assistencias"] = jogadores[assister_pid].get("assistencias",0) + 1
                salvar_jogadores(jogadores)
                st.success("Gol registrado!")
                st.experimental_rerun()
else:
    st.info("Inicie o cronômetro para registrar gols/assistências.")

st.markdown("---")

# ------------------------
# Eventos registrados
# ------------------------
st.markdown("### Eventos registrados")
if not st.session_state.match["events"]:
    st.write("Nenhum evento registrado.")
else:
    for ev in st.session_state.match["events"]:
        t = ev["time"]
        mm = t//60
        ss = t%60
        scorer_name = jogadores.get(ev["scorer"], {}).get("nome", ev["scorer"])
        assister_name = jogadores.get(ev["assister"], {}).get("nome", "") if ev.get("assister") else ""
        st.write(f"{mm:02d}:{ss:02d} — {ev['team']} — Gol: **{scorer_name}**" + (f" | Assist: {assister_name}" if assister_name else ""))

st.markdown("---")

# ------------------------
# Finalizar partida / salvar / logout
# ------------------------
end_col1, end_col2 = st.columns([1,1])
with end_col1:
    if st.button("Finalizar partida (salvar e zerar)"):
        # já salvamos gols/assistências no arquivo a cada gol; aqui apenas limpa estado de partida
        st.session_state.match = {
            "running": False,
            "start_time": None,
            "paused_at": 0.0,
            "elapsed": 0.0,
            "team_assign": {},
            "score": {"team1": 0, "team2": 0},
            "events": []
        }
        st.success("Partida finalizada e estado reiniciado.")
        st.experimental_rerun()
with end_col2:
    if st.button("Sair (olheiro)"):
        for k in ["user_id","perfil","logged_in","is_admin","is_scout","login_message","login_time","match"]:
            if k in st.session_state:
                del st.session_state[k]
        st.success("Logout efetuado.")
        st.experimental_rerun()
