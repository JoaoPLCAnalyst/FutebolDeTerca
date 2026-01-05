import json
import streamlit as st

st.title("Futebol de Terça ⚽")

with open("jogadores.json", "r", encoding="utf-8") as arquivo:
    jogadores = json.load(arquivo)

lista_jogadores = []
somatoria_pontos = 0

for id_jogador, dados in jogadores.items():
    lista_jogadores.append({
        "ID": id_jogador,
        "Nome": dados["nome"],
        "Posição": dados["posicao"],
        "Gols" : dados["gols"],
        "Assistencias" : dados["assistencias"],
        "Pontos": dados["pontos"]
    })

ranking = sorted(
    lista_jogadores,
    key=lambda x: x["Pontos"],
    reverse=True
)

st.subheader("🏆 Ranking de Jogadores")
st.dataframe(ranking)



