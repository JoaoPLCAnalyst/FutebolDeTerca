import streamlit as st
import json
import os
import base64
from github import Github

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="Administração", layout="centered")

DATABASE_PATH = "database/jogadores.json"
IMAGENS_DIR = "imagens/jogadores"

# =========================
# GITHUB
# =========================
def github_repo():
    g = Github(st.secrets["GITHUB_TOKEN"])
    return g.get_repo(st.secrets["GITHUB_REPO"])

def github_upload(local_path, repo_path, message):
    repo = github_repo()
    with open(local_path, "rb") as f:
        content = base64.b64encode(f.read()).decode()

    try:
        file = repo.get_contents(repo_path)
        repo.update_file(repo_path, message, content, file.sha)
    except:
        repo.create_file(repo_path, message, content)

# =========================
# JSON
# =========================
def carregar_jogadores():
    if not os.path.exists(DATABASE_PATH):
        return {}
    with open(DATABASE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def salvar_jogadores(jogadores):
    with open(DATABASE_PATH, "w", encoding="utf-8") as f:
        json.dump(jogadores, f, indent=4, ensure_ascii=False)

    github_upload(
        DATABASE_PATH,
        DATABASE_PATH,
        "Atualiza jogadores.json"
    )

# =========================
# LÓGICA DO NÚMERO
# =========================
def proximo_numero_disponivel(jogadores):
    usados = sorted(
        j["numero"] for j in jogadores.values()
        if "numero" in j
    )

    numero = 1
    for n in usados:
        if n == numero:
            numero += 1
        elif n > numero:
            break

    return numero

# =========================
# INTERFACE
# =========================
st.title("🔒 Área Administrativa")

jogadores = carregar_jogadores()

st.divider()
st.subheader("➕ Adicionar jogador")

nome = st.text_input("Nome do jogador")
foto = st.file_uploader("Foto do jogador", type=["jpg", "jpeg", "png"])

if st.button("Salvar jogador"):
    if not nome:
        st.error("Informe o nome do jogador")
        st.stop()

    numero = proximo_numero_disponivel(jogadores)
    jogador_id = f"jogador_{numero}"

    foto_path = ""
    if foto:
        os.makedirs(IMAGENS_DIR, exist_ok=True)
        foto_filename = f"{jogador_id}.jpg"
        foto_local = os.path.join(IMAGENS_DIR, foto_filename)

        with open(foto_local, "wb") as f:
            f.write(foto.getbuffer())

        github_upload(
            foto_local,
            f"{IMAGENS_DIR}/{foto_filename}",
            f"Adiciona imagem do jogador {nome}"
        )

        foto_path = f"{IMAGENS_DIR}/{foto_filename}"

    jogadores[jogador_id] = {
        "nome": nome,
        "numero": numero,
        "gols": 0,
        "assistencias": 0,
        "preco": 10,
        "foto": foto_path
    }

    salvar_jogadores(jogadores)

    st.success(f"Jogador '{nome}' cadastrado com número {numero}")
    st.rerun()

# =========================
# LISTA DE JOGADORES
# =========================
st.divider()
st.subheader("📋 Jogadores cadastrados")

if not jogadores:
    st.info("Nenhum jogador cadastrado")
else:
    for jid, j in sorted(jogadores.items(), key=lambda x: x[1]["numero"]):
        cols = st.columns([1, 4])
        with cols[0]:
            if j.get("foto"):
                repo = st.secrets["GITHUB_REPO"]
                url = f"https://raw.githubusercontent.com/{repo}/main/{j['foto']}"
                st.image(url, width=80)
        with cols[1]:
            st.markdown(f"**#{j['numero']} – {j['nome']}**")
