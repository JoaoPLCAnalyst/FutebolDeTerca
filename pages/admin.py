import streamlit as st
import json
import os
import re
import uuid
import io
from PIL import Image
import base64
import requests
import tempfile
import shutil
import glob
from datetime import datetime, timezone
from utils.scores import generate_and_apply_scores

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
    """Envia arquivo local ao GitHub (opcional). Retorna (ok, msg)."""
    if not GITHUB_USER or not GITHUB_REPO or not GITHUB_TOKEN:
        return False, "GitHub não configurado"
    try:
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
    except Exception as e:
        return False, f"erro: {e}"

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

def _write_atomic(path, data_bytes):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path))
    os.close(fd)
    with open(tmp, "wb") as f:
        f.write(data_bytes)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)

def _load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

# =========================
# REQUISITO: estar logado como admin (global)
# =========================
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
# INTERFACE - Cadastro de jogadores
# =========================
st.title("⚽ Cadastro de Jogadores")

nome = st.text_input("Nome do jogador")
imagem = st.file_uploader("Imagem do jogador (PNG/JPG)", type=["png", "jpg", "jpeg"])

if st.button("Cadastrar jogador"):
    if not nome or imagem is None:
        st.error("Preencha o nome e envie uma imagem")
        st.stop()

    ext = imagem.name.split(".")[-1].lower()
    if ext == "jpeg":
        ext = "jpg"
    img_filename = f"{slugify(nome)}-{uuid.uuid4().hex[:8]}.jpg"
    img_path = os.path.join(IMAGENS_DIR, img_filename)

    raw_bytes = imagem.getvalue()
    processed_bytes = resize_image_bytes(raw_bytes)

    with open(img_path, "wb") as f:
        f.write(processed_bytes)

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

# ------------------------
# Iniciar rodada (Admin)
# ------------------------
def next_rodada_id_for_date(base_dir, date_str, prefix="rodada", pad=2, max_attempts=1000):
    os.makedirs(base_dir, exist_ok=True)
    for n in range(1, max_attempts + 1):
        seq = str(n).zfill(pad)
        rodada_id = f"{date_str}-{prefix}-{seq}"
        path = os.path.join(base_dir, rodada_id)
        try:
            # tentativa atômica de criar a pasta; falha se já existir
            os.mkdir(path)
            # pasta criada com sucesso; devolve id
            return rodada_id
        except FileExistsError:
            continue
    raise RuntimeError("Não foi possível gerar rodada_id único após muitas tentativas")

def create_rodada(base_dir, nome, admin_user=None, github_upload_enabled=False):
    date_str = datetime.now().strftime("%Y-%m-%d")
    rodada_id = next_rodada_id_for_date(base_dir, date_str)
    rodada_dir = os.path.join(base_dir, rodada_id)
    matches_dir = os.path.join(rodada_dir, "matches")
    os.makedirs(matches_dir, exist_ok=True)

    meta = {
        "id": rodada_id,
        "nome": nome or f"Rodada {date_str}",
        "admin": admin_user or "",
        "inicio": datetime.now(timezone.utc).isoformat(),
        "fim": None,
        "status": "open",
        "matches": [],
        "match_count": 0
    }

    meta_path = os.path.join(rodada_dir, "meta.json")
    try:
        _write_atomic(meta_path, json.dumps(meta, ensure_ascii=False, indent=2).encode("utf-8"))
    except Exception as e:
        return False, None, f"Falha ao gravar meta.json: {e}"

    # opcional: upload para GitHub (não bloqueante)
    if github_upload_enabled and GITHUB_USER and GITHUB_REPO and GITHUB_TOKEN:
        try:
            github_upload(meta_path, f"database/rodadas/{rodada_id}/meta.json", f"Cria rodada {rodada_id}")
        except Exception:
            pass

    return True, rodada_id, "Rodada criada com sucesso"

# UI para iniciar rodada
st.markdown("---")
st.subheader("🟢 Iniciar nova rodada")
rodada_nome = st.text_input("Nome da rodada (opcional)", value="")
admin_user = st.session_state.get("user_id") or st.session_state.get("perfil") or "admin"
github_enabled = bool(GITHUB_USER and GITHUB_REPO and GITHUB_TOKEN)

if "creating_rodada" not in st.session_state:
    st.session_state.creating_rodada = False

if st.button("Iniciar rodada", disabled=st.session_state.creating_rodada):
    st.session_state.creating_rodada = True
    try:
        ok, rodada_id, msg = create_rodada(os.path.join("database", "rodadas"), rodada_nome, admin_user=admin_user, github_upload_enabled=github_enabled)
        if ok:
            st.success(f"Rodada iniciada: **{rodada_id}**")
            st.info(msg)
            # verificação rápida pós-criação
            meta_path = os.path.join("database", "rodadas", rodada_id, "meta.json")
            try:
                meta_check = _load_json(meta_path)
                if meta_check and meta_check.get("matches"):
                    st.warning("Atenção: meta.matches não está vazio após criação (investigar).")
            except Exception:
                pass
        else:
            st.error(msg)
    finally:
        st.session_state.creating_rodada = False
        st.rerun()

# Lista rápida de rodadas abertas (informativa)
st.markdown("Rodadas abertas")
rodadas_base = os.path.join("database", "rodadas")
if os.path.exists(rodadas_base):
    rows = []
    for name in sorted(os.listdir(rodadas_base)):
        meta_path = os.path.join(rodadas_base, name, "meta.json")
        if os.path.exists(meta_path):
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                if meta.get("status") == "open":
                    rows.append((name, meta.get("nome"), meta.get("inicio"), len(meta.get("matches", []))))
            except Exception:
                continue
    if not rows:
        st.write("Nenhuma rodada aberta")
    else:
        for r in rows:
            st.write(f"- **{r[0]}** — {r[1]} — início: {r[2]} — partidas: {r[3]}")
else:
    st.write("Nenhuma rodada encontrada")

# ------------------------
# Fechar rodada (Admin)
# ------------------------
def fechar_rodada(rodada_id, fazer_backup_jogadores=True, github_upload_enabled=False):
    base = os.path.join("database", "rodadas", rodada_id)
    meta_path = os.path.join(base, "meta.json")
    matches_dir = os.path.join(base, "matches")
    summary_path = os.path.join(base, "summary.json")

    # valida meta
    meta = _load_json(meta_path)
    if not meta:
        return False, "meta.json não encontrado ou inválido"
    if meta.get("status") != "open":
        return False, f"Rodada já está com status '{meta.get('status')}'"

    # lista arquivos de partida
    match_files = sorted(glob.glob(os.path.join(matches_dir, "*.json")))
    if not match_files:
        return False, "Nenhuma partida encontrada para agregar"

    # agregadores
    resumo_por_jogador = {}
    placar_por_partida = {}
    matches_list = []

    for mf in match_files:
        m = _load_json(mf)
        if not m:
            # pula arquivos inválidos
            continue
        match_id = m.get("id") or os.path.splitext(os.path.basename(mf))[0]
        matches_list.append(match_id)
        placar_por_partida[match_id] = m.get("score", {"team1":0,"team2":0})

        # determina vencedor da partida
        s = m.get("score", {"team1":0,"team2":0})
        if s.get("team1",0) > s.get("team2",0):
            vencedor_match = "team1"
        elif s.get("team2",0) > s.get("team1",0):
            vencedor_match = "team2"
        else:
            vencedor_match = "empate"

        # resumo por eventos (gols/assist)
        events = m.get("events", [])
        for ev in events:
            if ev.get("type") == "gol" and ev.get("scorer"):
                pid = ev["scorer"]
                resumo_por_jogador.setdefault(pid, {"gols":0,"assistencias":0,"vitorias":0})
                resumo_por_jogador[pid]["gols"] += 1
            if ev.get("type") == "assist" and ev.get("assister"):
                pid = ev["assister"]
                resumo_por_jogador.setdefault(pid, {"gols":0,"assistencias":0,"vitorias":0})
                resumo_por_jogador[pid]["assistencias"] += 1

        # vitorias por jogador: incrementa para jogadores atribuídos ao time vencedor
        if vencedor_match in ("team1","team2"):
            team_assign = m.get("team_assign", {})
            winning_team_num = 1 if vencedor_match == "team1" else 2
            for pid, team in team_assign.items():
                if team == winning_team_num:
                    resumo_por_jogador.setdefault(pid, {"gols":0,"assistencias":0,"vitorias":0})
                    resumo_por_jogador[pid]["vitorias"] = resumo_por_jogador[pid].get("vitorias",0) + 1

    # monta summary
    summary = {
        "rodada_id": rodada_id,
        "timestamp_closed": datetime.now(timezone.utc).isoformat(),
        "matches": matches_list,
        "placar_por_partida": placar_por_partida,
        "resumo_por_jogador": resumo_por_jogador,
        "meta_snapshot": meta
    }

    # grava summary atômico
    try:
        _write_atomic(summary_path, json.dumps(summary, ensure_ascii=False, indent=2).encode("utf-8"))
    except Exception as e:
        return False, f"Falha ao gravar summary.json: {e}"

        # gera scores.json e aplica em jogadores.json (idempotente)
    try:
        github_fn = (lambda p, rp, m: github_upload(p, rp, m)) if (github_upload_enabled and GITHUB_USER and GITHUB_REPO and GITHUB_TOKEN) else None
        res_scores = generate_and_apply_scores(base, summary, formula={"gol":8,"assist":4,"vitoria":4}, jogadores_path=JOGADORES_FILE, github_upload_fn=github_fn)
        # opcional: mostrar resultado no admin
        # st.info(f"Scores aplicados: {res_scores['applied']} | pulados: {res_scores['skipped']}")
    except Exception as e:
        return False, f"Falha ao gerar/aplicar scores.json: {e}"

    # backup jogadores.json
    if fazer_backup_jogadores and os.path.exists(JOGADORES_FILE):
        try:
            ts = datetime.now().strftime("%Y%m%dT%H%M%S")
            shutil.copy(JOGADORES_FILE, f"{JOGADORES_FILE}.bak-{ts}")
        except Exception as e:
            return False, f"Falha ao criar backup de jogadores.json: {e}"

    # atualiza jogadores.json incrementalmente
    try:
        jogadores_on_disk = {}
        if os.path.exists(JOGADORES_FILE):
            with open(JOGADORES_FILE, "r", encoding="utf-8") as f:
                jogadores_on_disk = json.load(f)

        # aplica incrementos
        for pid, vals in resumo_por_jogador.items():
            if pid not in jogadores_on_disk:
                jogadores_on_disk[pid] = {
                    "nome": pid,
                    "valor": 0,
                    "gols": 0,
                    "assistencias": 0,
                    "imagem": "",
                    "vitorias": 0
                }
            jogadores_on_disk[pid]["gols"] = jogadores_on_disk[pid].get("gols",0) + vals.get("gols",0)
            jogadores_on_disk[pid]["assistencias"] = jogadores_on_disk[pid].get("assistencias",0) + vals.get("assistencias",0)
            jogadores_on_disk[pid]["vitorias"] = jogadores_on_disk[pid].get("vitorias",0) + vals.get("vitorias",0)

        # grava atômico jogadores.json
        _write_atomic(JOGADORES_FILE, json.dumps(jogadores_on_disk, ensure_ascii=False, indent=2).encode("utf-8"))
    except Exception as e:
        return False, f"Falha ao atualizar jogadores.json: {e}"

    # atualiza meta.json somente após sucesso completo, com verificação
    try:
        meta["fim"] = datetime.now(timezone.utc).isoformat()
        meta["status"] = "closed"
        meta["summary_file"] = os.path.basename(summary_path)
        meta["match_count"] = len(matches_list)
        _write_atomic(meta_path, json.dumps(meta, ensure_ascii=False, indent=2).encode("utf-8"))

        # leitura de verificação imediata
        verified = False
        for attempt in range(3):
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta_check = json.load(f)
                if meta_check.get("status") == "closed" and meta_check.get("fim"):
                    verified = True
                    break
            except Exception:
                pass
            import time as _time
            _time.sleep(0.1)

        if not verified:
            # tenta uma segunda escrita antes de falhar
            try:
                _write_atomic(meta_path, json.dumps(meta, ensure_ascii=False, indent=2).encode("utf-8"))
            except Exception as e:
                meta["status"] = "error"
                meta["error_message"] = f"Falha ao gravar meta.json: {e}"
                try:
                    _write_atomic(meta_path, json.dumps(meta, ensure_ascii=False, indent=2).encode("utf-8"))
                except Exception:
                    pass
                return False, f"Falha ao confirmar gravação de meta.json: {e}"
            # última verificação
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta_check = json.load(f)
                if meta_check.get("status") != "closed":
                    return False, "Gravado meta.json, mas verificação final falhou (status diferente de closed)."
            except Exception as e:
                return False, f"Gravado meta.json, mas não foi possível ler para verificação: {e}"

    except Exception as e:
        try:
            meta["status"] = "error"
            meta["error_message"] = str(e)
            _write_atomic(meta_path, json.dumps(meta, ensure_ascii=False, indent=2).encode("utf-8"))
        except Exception:
            pass
        return False, f"Erro ao fechar rodada (atualizando meta.json): {e}"

    # upload GitHub opcional
    if github_upload_enabled and GITHUB_USER and GITHUB_REPO and GITHUB_TOKEN:
        try:
            ok1, out1 = github_upload(summary_path, f"database/rodadas/{rodada_id}/summary.json", f"Adiciona summary da rodada {rodada_id}")
            ok2, out2 = github_upload(meta_path, f"database/rodadas/{rodada_id}/meta.json", f"Fecha rodada {rodada_id}")
            ok3, out3 = github_upload(JOGADORES_FILE, JOGADORES_FILE, f"Atualiza jogadores após fechamento de {rodada_id}")
            if not ok1 or not ok2 or not ok3:
                return True, f"Rodada fechada localmente; upload parcial: {out1}; {out2}; {out3}"
        except Exception as e:
            return True, f"Rodada fechada localmente; erro no upload GitHub: {e}"

    return True, "Rodada fechada com sucesso"

# UI: botão para fechar rodada
st.markdown("---")
st.subheader("🔴 Fechar rodada")
rodadas_base = os.path.join("database", "rodadas")
open_rodadas = []
if os.path.exists(rodadas_base):
    for name in sorted(os.listdir(rodadas_base)):
        mp = os.path.join(rodadas_base, name, "meta.json")
        if os.path.exists(mp):
            try:
                with open(mp, "r", encoding="utf-8") as f:
                    m = json.load(f)
                if m.get("status") == "open":
                    open_rodadas.append(name)
            except Exception:
                continue

if not open_rodadas:
    st.info("Nenhuma rodada aberta para fechar.")
else:
    rodada_to_close = st.selectbox("Selecionar rodada para fechar", options=open_rodadas)
    github_enabled = bool(GITHUB_USER and GITHUB_REPO and GITHUB_TOKEN)

    if "closing_rodada" not in st.session_state:
        st.session_state.closing_rodada = False

    if st.button("Fechar rodada selecionada", disabled=st.session_state.closing_rodada):
        st.session_state.closing_rodada = True
        try:
            ok, msg = fechar_rodada(rodada_to_close, fazer_backup_jogadores=True, github_upload_enabled=github_enabled)
            if ok:
                st.success(msg)
            else:
                st.error(msg)
        finally:
            st.session_state.closing_rodada = False
            st.rerun()

