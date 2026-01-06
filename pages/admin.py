import streamlit as st
import json
import os
import re
import uuid
import io
from PIL import Image
import base64, requests

# =========================
# CONFIGURAÇÃO DA PÁGINA
# =========================
st.set_page_config(page_title="Admin - Futebol de Terça", page_icon="⚽")

PASSWORD = st.secrets["ADMIN_PASSWORD"]

JOGADORES_FILE = "database/jogadores.json"
IMAGENS_DIR = "imagens/jogadores"
os.makedirs("database", exist_ok=True)
os.makedirs(IMAGENS_DIR, exist_ok=True)

# =========================
# GITHUB CONFIG (opcional)
# =========================
GITHUB_USER = st.secrets.get("GITHUB_USER", "")
GITHUB_REPO = st.secrets.get("GITHUB_REPO", "")
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "")
GITHUB_BRANCH = st.secrets.get("GITHUB_BRANCH", "main")

def github_upload(path_local, repo_path, message):
    """Envia arquivo local ao GitHub (opcional)."""
    if not GITHUB_USER or not GITHUB_REPO or not GITHUB_TOKEN:
        return None
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/{repo_path}"
    with open(path_local, "rb") as f:
        content_b64 = base64.b64encode(f.read()).decode()
    get_file = requests.get(url, headers=headers)
    sha = get_file.json().get("sha") if get_file.status_code == 200 else None
    payload = {"message": message, "content": content_b64}
    if sha:
        payload["sha"] = sha
    return requests.put(url, headers=headers, json=payload)

# =========================
# UTILITÁRIOS
# =========================
def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\-_ ]", "", text)
    text = re.sub(r"\s+", "-", text)
    return text

def resize_image_bytes(uploaded_file_bytes: bytes, max_size=(800, 800), quality=85) -> bytes:
    buf = io.BytesIO(uploaded_file_bytes)
    img = Image.open(buf)
    img = img.convert("RGB")
    img.thumbnail(max_size)
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=quality)
    out.seek(0)
    return out.read()

def carregar_jogadores():
    if not os.path.exists(JOGADORES_FILE):
        return {}
    with open(JOGADORES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def salvar_jogadores(jogadores_dict):
    with open(JOGADORES_FILE, "w", encoding="utf-8") as f:
        json.dump(jogadores_dict, f, indent=2, ensure_ascii=False)

# =========================
# REQUISITO: estar logado como admin (global)
# =========================
# A página só será exibida se a flag global de admin estiver presente.
# Se você usa outra página de login que define st.session_state["is_admin"] = True,
# o acesso será liberado. Caso contrário, a execução é interrompida.
if not st.session_state.get("is_admin"):
    st.title("🔐 Área Administrativa")
    st.warning("Acesso restrito: faça login com o usuário administrador na página de login para acessar esta área.")
    st.stop()

# =========================
# LOGIN LOCAL (mantido conforme solicitado)
# =========================
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔐 Área Administrativa (login local)")
    senha = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if senha == PASSWORD:
            st.session_state.auth = True
            st.rerun()
        else:
            st.error("Senha incorreta")
    st.stop()

# =========================
# INTERFACE
# =========================
st.title("⚽ Cadastro de Jogadores")

nome = st.text_input("Nome do jogador")
imagem = st.file_uploader("Imagem do jogador (PNG/JPG)", type=["png", "jpg", "jpeg"])

# =========================
# CADASTRAR JOGADOR
# =========================
if st.button("Cadastrar jogador"):
    if not nome or imagem is None:
        st.error("Preencha o nome e envie uma imagem")
        st.stop()

    # Processar imagem
    ext = imagem.name.split(".")[-1].lower()
    if ext == "jpeg":
        ext = "jpg"
    img_filename = f"{slugify(nome)}-{uuid.uuid4().hex[:8]}.jpg"
    img_path = os.path.join(IMAGENS_DIR, img_filename)

    raw_bytes = imagem.getvalue()
    processed_bytes = resize_image_bytes(raw_bytes)

    with open(img_path, "wb") as f:
        f.write(processed_bytes)

    # Atualizar jogadores.json
    jogadores_dict = carregar_jogadores()
    player_id = f"{slugify(nome)}-{uuid.uuid4().hex[:8]}"
    novo_jogador = {
        "nome": nome,
        "valor": 10,
        "gols": 0,
        "assistencias": 0,
        "imagem": img_path
    }
    jogadores_dict[player_id] = novo_jogador
    salvar_jogadores(jogadores_dict)

    # Upload opcional ao GitHub
    github_upload(img_path, f"{IMAGENS_DIR}/{img_filename}", f"Adiciona imagem do jogador {nome}")
    github_upload(JOGADORES_FILE, JOGADORES_FILE, f"Atualiza jogadores.json com {nome}")

    st.success("✅ Jogador cadastrado!")
    st.rerun()

# =========================
# LISTA DE JOGADORES
# =========================
st.markdown("### 📋 Jogadores cadastrados")

jogadores_dict = carregar_jogadores()

if not jogadores_dict:
    st.info("Nenhum jogador cadastrado")
else:
    sorted_items = sorted(jogadores_dict.items(), key=lambda kv: kv[1].get("nome", "").lower())
    for player_id, j in sorted_items:
        col1, col2, col3 = st.columns([1, 3, 1])
        with col1:
            if os.path.exists(j["imagem"]):
                st.image(j["imagem"], width=80)
        with col2:
            st.write(f"**{j.get('nome', '—')}**")
            st.write(f"Gols: {j.get('gols', 0)} | Assistências: {j.get('assistencias', 0)}")
            st.caption(f"ID: {player_id}")
        with col3:
            if st.button("🗑️ Excluir", key=f"del-{player_id}"):
                jogadores_dict.pop(player_id)
                salvar_jogadores(jogadores_dict)
                try:
                    os.remove(j["imagem"])
                except Exception:
                    pass
                github_upload(JOGADORES_FILE, JOGADORES_FILE, f"Remove jogador {j['nome']}")
                st.success(f"Jogador {j['nome']} excluído!")
                st.rerun()
