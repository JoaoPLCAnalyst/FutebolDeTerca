import streamlit as st
import json
import os
from typing import Dict, Any, List, Tuple

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="Futebol de Terça", layout="wide")

JOGADORES_FILE = "database/jogadores.json"
RODADAS_DIR = "database/rodadas"
IMAGENS_DIR = "imagens/jogadores"

# =========================
# UTILITÁRIOS
# =========================
def safe_load_json(path: str) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def carregar_jogadores() -> Dict[str, dict]:
    """Carrega jogadores do arquivo local JSON."""
    if not os.path.exists(JOGADORES_FILE):
        return {}
    data = safe_load_json(JOGADORES_FILE)
    if not data:
        return {}
    if isinstance(data, dict):
        return data
    if isinstance(data, list):
        return {f"j{idx:04d}": item for idx, item in enumerate(data)}
    return {}

def list_rodadas() -> List[str]:
    """Retorna lista de ids de rodadas ordenadas (pasta names)."""
    base = RODADAS_DIR
    if not os.path.exists(base):
        return []
    rodadas = []
    for name in sorted(os.listdir(base)):
        path = os.path.join(base, name)
        if not os.path.isdir(path):
            continue
        meta_path = os.path.join(path, "meta.json")
        if os.path.exists(meta_path):
            rodadas.append(name)
    return rodadas

def load_scores_for_rodada(rodada_id: str) -> Dict[str, dict]:
    """Carrega scores.json.scores (map player_id -> {gols, assistencias, vitorias, pontos})."""
    if not rodada_id:
        return {}
    path = os.path.join(RODADAS_DIR, rodada_id, "scores.json")
    data = safe_load_json(path)
    if not data:
        return {}
    return data.get("scores", {}) or {}

def compute_top_players_from_scores(scores: Dict[str, dict], top_n: int = 3) -> List[Tuple[str, dict]]:
    """Retorna lista (player_id, score_obj) ordenada por pontos desc, limitada a top_n."""
    items = [(pid, vals) for pid, vals in scores.items()]
    items.sort(key=lambda kv: kv[1].get("pontos", 0), reverse=True)
    return items[:top_n]

def format_points(n: int) -> str:
    return str(int(n)) if n is not None else "0"

# =========================
# INTERFACE
# =========================
st.title("⚽ Futebol de Terça")

jogadores = carregar_jogadores()
if not jogadores:
    st.warning("Nenhum jogador cadastrado.")
    st.stop()

# Seleção de rodada
rodadas_opts = ["Todas as rodadas"] + list_rodadas()
selected_rodada = st.selectbox("Mostrar dados da rodada", options=rodadas_opts, index=0)

# Carrega scores da rodada selecionada (se houver)
rodada_scores = {}
if selected_rodada != "Todas as rodadas":
    rodada_scores = load_scores_for_rodada(selected_rodada)

# Se houver rodada selecionada, destaca top 3
if selected_rodada != "Todas as rodadas" and rodada_scores:
    st.markdown("### 🏆 Destaques da rodada")
    top_players = compute_top_players_from_scores(rodada_scores, top_n=3)
    cols = st.columns(len(top_players))
    for idx, (pid, score) in enumerate(top_players):
        col = cols[idx]
        player = jogadores.get(pid, {})
        nome = player.get("nome", pid)
        imagem = player.get("imagem", "")
        pontos = score.get("pontos", 0)
        gols = score.get("gols", 0)
        assists = score.get("assistencias", 0)
        with col:
            st.markdown(f"#### #{idx+1} — {nome}")
            if imagem and os.path.exists(imagem):
                st.image(imagem, width=140)
            st.metric(label="Pontos (rodada)", value=format_points(pontos))
            st.write(f"Gols: **{gols}**  •  Assistências: **{assists}**")
            st.caption(f"ID: {pid}")
    st.divider()

# Preparar ordenação: se rodada selecionada, ordenar por pontos da rodada; senão por pontos_total
def sort_key(item):
    pid, j = item
    if selected_rodada != "Todas as rodadas":
        s = rodada_scores.get(pid)
        if s:
            return (-int(s.get("pontos", 0)), (j.get("nome") or "").lower())
        else:
            return (0, (j.get("nome") or "").lower())
    else:
        return (-int(j.get("pontos_total", 0)), (j.get("nome") or "").lower())

sorted_items = sorted(jogadores.items(), key=sort_key)

# Cabeçalho explicativo
st.markdown("### Jogadores — totais e por rodada")
if selected_rodada == "Todas as rodadas":
    st.caption("Exibindo totais acumulados (gols, assistências e pontos). Selecione uma rodada para ver os valores daquela rodada.")
else:
    st.caption(f"Exibindo totais acumulados e os valores da rodada **{selected_rodada}** (gols, assistências, pontos).")

# Renderiza lista (compacta) com destaque visual para top 1 quando aplicável
for jogador_id, j in sorted_items:
    col1, col2 = st.columns([1, 3])
    imagem_path = j.get("imagem", "")
    nome = j.get("nome", "—")
    gols_total = int(j.get("gols", 0))
    assistencias_total = int(j.get("assistencias", 0))
    pontos_total = int(j.get("pontos_total", 0))
    valor = j.get("valor", "—")

    # dados da rodada selecionada (se existir)
    rodada_gols = None
    rodada_assists = None
    rodada_pontos = None
    if selected_rodada != "Todas as rodadas":
        s = rodada_scores.get(jogador_id)
        if s:
            rodada_gols = int(s.get("gols", 0))
            rodada_assists = int(s.get("assistencias", 0))
            rodada_pontos = int(s.get("pontos", 0))
        else:
            rodada_gols = 0
            rodada_assists = 0
            rodada_pontos = 0

    # destaque visual para o melhor da rodada (top 1)
    is_top1 = False
    if selected_rodada != "Todas as rodadas" and rodada_scores:
        top = compute_top_players_from_scores(rodada_scores, top_n=1)
        if top and top[0][0] == jogador_id:
            is_top1 = True

    with col1:
        if imagem_path and os.path.exists(imagem_path):
            st.image(imagem_path, width=120)
        else:
            st.write("")

    with col2:
        if is_top1:
            st.markdown(f"### 🥇 **{nome}**")
        else:
            st.markdown(f"**{nome}**")

        # Totais
        st.write(f"Gols (total): **{gols_total}**")
        st.write(f"Assistências (total): **{assistencias_total}**")
        st.write(f"Pontos (total): **{pontos_total}**")

        # Valores da rodada (se aplicável)
        if selected_rodada != "Todas as rodadas":
            st.markdown("---")
            st.write(f"Gols na rodada: **{rodada_gols}**")
            st.write(f"Assistências na rodada: **{rodada_assists}**")
            st.write(f"Pontos na rodada: **{rodada_pontos}**")

        st.write(f"Valor: **{valor}**")
        st.caption(f"ID: {jogador_id}")
        st.divider()

# Resumo final opcional: top 5 da rodada em tabela
if selected_rodada != "Todas as rodadas" and rodada_scores:
    st.markdown("### 📊 Top 5 da rodada")
    top5 = compute_top_players_from_scores(rodada_scores, top_n=5)
    rows = []
    for rank, (pid, s) in enumerate(top5, start=1):
        player = jogadores.get(pid, {})
        rows.append({
            "Rank": rank,
            "Jogador": player.get("nome", pid),
            "Gols": s.get("gols", 0),
            "Assistências": s.get("assistencias", 0),
            "Pontos": s.get("pontos", 0)
        })
    st.table(rows)
