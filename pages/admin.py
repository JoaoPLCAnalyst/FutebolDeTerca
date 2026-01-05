
import streamlit as st
import json
import os
import base64
import requests
from datetime import datetime

# =========================
# CONFIG
# =========================
REPO_OWNER = "SEU_USUARIO"
REPO_NAME = "futeboldeterca"
BRANCH = "main"

TOKEN = st.secrets["GITHUB_TOKEN"]

JOGADORES_FILE = "database/jogadores.json"
IMAGENS_DIR = "imagens/jogadores"

API_BASE = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents"

HEADERS = {
    "Authorization": f"token {TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

# =========================
# FUNÇÕES
# =========================

def carregar_jogadores():
    if not os.path.exists(JOGADORES_FILE):
        return {}
    with open(JOGADORES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def salvar_jogadores(jogadores):
    os.makedirs("database", exist_ok=True)
    with open(JOGADORES_FILE, "w", encoding="utf-8") as f:
        json.dump(jogadores, f, indent=2, ensure_ascii=False)

def gerar_id():
    return f"jogador_{int(datetime.now().timestamp())}"

def upload_github(path, content_bytes, message):
    url = f"{API_BASE}/{path}"

    # verifica se já existe
    r = requests.get(url, headers=HEADERS)
    sha = r.json().get("sha") if r.status_code == 200 else None

    data = {
        "message": message,
        "content": base64.b64encode(content_bytes).decode("utf-8"),
        "branch": BRANCH
    }

    if sha:
        data["sha"] = sha

    res = requests.put(url, headers=HEADERS, json=data)
    return res.status_code in [200, 201], res.text

# =========================
# INTERFACE
# =========================

st.title("Administração de Jogadores")

jogadores = carregar_jogadores()

with st.form("novo_jogador"):
    nome = st.text_input("Nome")
    numero = st.number_input("Número", min_value=0, step=1)
    foto = st.file_uploader("Foto", type=["jpg", "png", "jpeg"])
    salvar = st.form_submit_button("Salvar")

if salvar:
    if not nome or not foto:
        st.error("Nome e foto são obrigatórios")
    else:
        jogador_id = gerar_id()
        nome_foto = f"{jogador_id}.jpg"
        caminho_foto = f"{IMAGENS_DIR}/{nome_foto}"

        ok, msg = upload_github(
            caminho_foto,
            foto.read(),
            f"Adiciona foto do jogador {nome}"
        )

        if not ok:
            st.error(f"Erro ao salvar imagem: {msg}")
            st.stop()

        jogadores[jogador_id] = {
            "nome": nome,
            "numero": numero,
            "foto": caminho_foto
        }

        salvar_jogadores(jogadores)

        st.success("Jogador salvo com sucesso")
