# pages/admin.py
import streamlit as st
import json
import os
import base64
from github import Github, GithubException

st.set_page_config(page_title="Administração", layout="centered")

# =========================
# CONFIG
# =========================
DATABASE_PATH = "database/jogadores.json"
IMAGENS_DIR = "imagens/jogadores"

os.makedirs(os.path.dirname(DATABASE_PATH) or ".", exist_ok=True)
os.makedirs(IMAGENS_DIR, exist_ok=True)

# =========================
# GITHUB / SECRETS
# =========================
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN")
GITHUB_REPO = st.secrets.get("GITHUB_REPO")  # formato "owner/repo"
GITHUB_BRANCH = st.secrets.get("GITHUB_BRANCH", "main")

def github_repo():
    if not GITHUB_TOKEN or not GITHUB_REPO:
        raise RuntimeError("GITHUB_TOKEN ou GITHUB_REPO não configurados em secrets")
    g = Github(GITHUB_TOKEN)
    return g.get_repo(GITHUB_REPO)

def github_upload(local_path, repo_path, message, branch=None):
    """
    Faz upload (create/update) de um arquivo para o repo.
    - local_path: caminho local do arquivo já gravado
    - repo_path: caminho no repositório (ex: imagens/jogadores/foo.jpg)
    - message: mensagem do commit
    - branch: branch alvo (opcional)
    """
    branch = branch or GITHUB_BRANCH
    repo = github_repo()
    with open(local_path, "rb") as f:
        raw = f.read()
    # GitHub Contents API espera content em base64
    content_b64 = base64.b64encode(raw).decode()

    try:
        # tenta obter o arquivo no repo (na branch especificada)
        file = repo.get_contents(repo_path, ref=branch)
        # se existir, atualiza
        repo.update_file(path=repo_path, message=message, content=content_b64, sha=file.sha, branch=branch)
        return True, "updated"
    except GithubException as e:
        # se não existir (404) cria; se outro erro, retorna erro
        if e.status == 404:
            try:
                repo.create_file(path=repo_path, message=message, content=content_b64, branch=branch)
                return True, "created"
            except Exception as e2:
                return False, f"Erro ao criar arquivo no repo: {e2}"
        else:
            return False, f"Erro GitHub: {e.data if hasattr(e,'data') else str(e)}"
    except Exception as e:
        return False, f"Erro inesperado: {e}"

# =========================
# JSON helpers
# =========================
def carregar_jogadores():
    if not os.path.exists(DATABASE_PATH):
        return {}
    with open(DATABASE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def salvar_jogadores(jogadores):
    # grava localmente primeiro
    with open(DATABASE_PATH, "w", encoding="utf-8") as f:
        json.dump(jogadores, f, indent=4, ensure_ascii=False)

    # tenta enviar para o GitHub (se configurado)
    if GITHUB_TOKEN and GITHUB_REPO:
        ok, out = github_upload(DATABASE_PATH, DATABASE_PATH, "Atualiza jogadores.json", branch=GITHUB_BRANCH)
        return ok, out
    return True, "gravado localmente (sem upload GitHub)"

# =========================
# LÓGICA DO NÚMERO
# =========================
def proximo_numero_disponivel(jogadores):
    usados = sorted(
        j["numero"] for j in jogadores.values()
        if "numero" in j
    ) if jogadores else []

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

# debug rápido (remova em produção)
with st.expander("Debug (secrets e paths)", expanded=False):
    st.write("GITHUB_TOKEN configured:", bool(GITHUB_TOKEN))
    st.write("GITHUB_REPO:", GITHUB_REPO)
    st.write("GITHUB_BRANCH:", GITHUB_BRANCH)
    st.write("DATABASE_PATH (local):", os.path.abspath(DATABASE_PATH))
    st.write("IMAGENS_DIR (local):", os.path.abspath(IMAGENS_DIR))

# carrega jogadores (local)
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
        # salva localmente primeiro
        os.makedirs(IMAGENS_DIR, exist_ok=True)
        foto_filename = f"{jogador_id}.jpg"
        foto_local = os.path.join(IMAGENS_DIR, foto_filename)

        try:
            # grava bytes localmente
            with open(foto_local, "wb") as f:
                f.write(foto.getbuffer())
        except Exception as e:
            st.exception(e)
            st.error("Falha ao gravar imagem localmente. Verifique permissões.")
            st.stop()

        # tenta enviar para o GitHub (se configurado)
        if GITHUB_TOKEN and GITHUB_REPO:
            ok, out = github_upload(foto_local, f"{IMAGENS_DIR}/{foto_filename}", f"Adiciona imagem do jogador {nome}", branch=GITHUB_BRANCH)
            if not ok:
                st.warning(f"Imagem gravada localmente em {foto_local}, mas falha ao enviar para GitHub: {out}")
            else:
                st.info(f"Imagem enviada ao GitHub ({out}).")
        else:
            st.info("Imagem gravada localmente (upload GitHub desativado).")

        foto_path = f"{IMAGENS_DIR}/{foto_filename}"

    jogadores[jogador_id] = {
        "nome": nome,
        "numero": numero,
        "gols": 0,
        "assistencias": 0,
        "preco": 10,
        "foto": foto_path
    }

    ok, out = salvar_jogadores(jogadores)
    if ok:
        st.success(f"Jogador '{nome}' cadastrado com número {numero}")
        if out:
            st.info(out)
    else:
        st.error(f"Jogador salvo localmente, mas falha ao atualizar repo: {out}")

    # força recarregar a página para atualizar lista
    st.rerun()

# =========================
# LISTA DE JOGADORES
# =========================
st.divider()
st.subheader("📋 Jogadores cadastrados")

jogadores = carregar_jogadores()  # recarrega do disco
if not jogadores:
    st.info("Nenhum jogador cadastrado")
else:
    for jid, j in sorted(jogadores.items(), key=lambda x: x[1]["numero"]):
        cols = st.columns([1, 4])
        with cols[0]:
            if j.get("foto"):
                if GITHUB_REPO:
                    # URL raw no GitHub (assume branch principal)
                    url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/{GITHUB_BRANCH}/{j['foto']}"
                    st.image(url, width=80)
                else:
                    # exibe local se não houver GitHub configurado
                    local_path = j.get("foto")
                    if local_path and os.path.exists(local_path):
                        st.image(local_path, width=80)
                    else:
                        st.write("Sem imagem")
        with cols[1]:
            st.markdown(f"**#{j['numero']} – {j['nome']}**")
