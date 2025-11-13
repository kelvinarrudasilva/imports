# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from io import BytesIO
import re

# ======================
# Config visual (Alto contraste: Preto + Dourado)
# ======================
st.set_page_config(page_title="Painel - Loja Importados", layout="wide")

st.markdown("""
<style>
:root { --gold:#FFD700; --bg:#000000; --card:#0f0f0f; --muted:#bfbfbf; }
.stApp { background-color: var(--bg); color: var(--gold); }
.title { color: var(--gold); font-weight:700; font-size:22px; }
.subtitle { color: var(--muted); font-size:12px; margin-bottom:12px; }
.kpi { background: linear-gradient(90deg, #111111, #0b0b0b); padding:12px; border-radius:10px; text-align:center; }
.kpi-value { color: var(--gold); font-size:20px; font-weight:700; }
.kpi-label { color:var(--muted); font-size:13px; }
.stDataFrame table { background-color:#050505; color:#e6e2d3; }
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='title'>📊 Painel — Loja Importados</div>", unsafe_allow_html=True)
st.markdown("<div class='subtitle'>Tema: Alto contraste —
