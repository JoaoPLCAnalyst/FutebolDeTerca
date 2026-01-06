# pages/admin.py
import streamlit as st
import os
import json
import re
import uuid
import io
from PIL import Image
import base64
import requests

st.set_page_config(page_title="Admin - Futebol de Terça", page_icon="⚽")

# -----------------------
# Config
# -----------------------
JOGADORES_FILE = "database/jogadores.json"
IMAGENS_DIR = "imagens/jogadores"
os.makedirs("database", exist_ok=True)
os.makedirs(IMAGENS_DIR, exist_ok=True)

# -----------------------
# Secrets esperados
# -----------------------
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD")  # senha do admin definida em secrets.toml

# -----------------------
# Utilitários
# -----------------------
def slugify(text: str) -> str:
    text = (text or "").lower().strip()
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
    try:
        with open(JOGADORES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def salvar_jogadores(jogadores_dict):
    with open(JOGADORES_FILE, "w", encoding="utf-8") as f:
        json.dump(jogadores_dict, f, indent=2, ensure_ascii=False)

# -----------------------
# Autenticação local na página (senha)
# -----------------------
if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False

st.title("Área Administrativa — Cadastro de Jogadores")

if not st.session_state.admin_authenticated:
    st.info("A página está visível, mas é necessária a senha do administrador para operar.")
    senha = st.text_input("Senha do administrador", type="password")
    if st.button("Entrar como admin"):
        if ADMIN_PASSWORD is None:
            st.error("Senha de administrador não configurada (verifique secrets).")
        elif senha == ADMIN_PASSWORD:
            st.session_state.admin_authenticated = True
            # reafirma is_admin para compatibilidade com outras páginas
            st.session_state["is_admin"] = True
            st.success("Autenticado como administrador.")
            st.rerun()
        else:
            st.error("Senha incorreta.")
    st.stop()

# -----------------------
# UI administrativa (autenticado)
# -----------------------
st.markdown("### ⚽ Cadastro de Jogadores")

# Formulário simples (não usar clear_on_submit=True para não perder uploader)
nome = st.text_input("Nome do jogador")
imagem = st.file_uploader("Imagem do jogador (PNG/JPG)", type=["png", "jpg", "jpeg"])

if st.button("Cadastrar jogador"):
    if not nome or imagem is None:
        st.error("Preencha o nome e envie uma imagem.")
    else:
        try:
            # 1) Leia os bytes imediatamente (obrigatório)
            raw_bytes = imagem.getvalue()

            # 2) Processa e salva imagem localmente antes de qualquer rerun
            ext = imagem.name.split(".")[-1].lower()
            if ext == "jpeg":
                ext = "jpg"
            img_filename = f"{slugify(nome)}-{uuid.uuid4().hex[:8]}.jpg"
            img_path = os.path.join(IMAGENS_DIR, img_filename)

            processed_bytes = resize_image_bytes(raw_bytes)
            with open(img_path, "wb") as f:
                f.write(processed_bytes)

            # 3) Atualiza JSON de jogadores
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

            # 4) Reafirma sessão admin (proteção extra) e dá feedback
            st.session_state["is_admin"] = True
            st.session_state.admin_authenticated = True
            st.success("✅ Jogador cadastrado com sucesso.")
            # atualiza lista local sem forçar rerun
            jogadores = jogadores_dict

        except Exception as e:
            st.error(f"Erro ao cadastrar jogador: {e}")

st.markdown("---")
st.markdown("### 📋 Jogadores cadastrados")

jogadores_dict = carregar_jogadores()

if not jogadores_dict:
    st.info("Nenhum jogador cadastrado")
else:
    sorted_items = sorted(jogadores_dict.items(), key=lambda kv: kv[1].get("nome", "").lower())
    for player_id, j in sorted_items:
        col1, col2, col3 = st.columns([1, 3, 1])
        with col1:
            try:
                if os.path.exists(j.get("imagem", "")):
                    st.image(j["imagem"], width=80)
            except Exception:
                pass
        with col2:
            st.write(f"**{j.get('nome', '—')}**")
            st.write(f"Gols: {j.get('gols', 0)} | Assistências: {j.get('assistencias', 0)}")
            st.caption(f"ID: {player_id}")
        with col3:
            if st.button("🗑️ Excluir", key=f"del-{player_id}"):
                nome_excl = j.get("nome", player_id)
                jogadores_dict.pop(player_id)
                salvar_jogadores(jogadores_dict)
                try:
                    if os.path.exists(j.get("imagem", "")):
                        os.remove(j["imagem"])
                except Exception:
                    pass
                st.success(f"Jogador {nome_excl} excluído.")
                st.rerun()

st.markdown("---")
if st.button("Sair (admin)"):
    # logout local da página (não apaga session_state globalmente, apenas flags relacionadas)
    if "is_admin" in st.session_state:
        del st.session_state["is_admin"]
    if "admin_authenticated" in st.session_state:
        del st.session_state["admin_authenticated"]
    st.success("Logout efetuado.")
    st.rerun()
