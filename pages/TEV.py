# applicazione/pages/TEV.py

import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import timedelta, datetime
from utils import format_date#, check_page_access_auth0

# ============================================
# 🔐 CONTROLLO ACCESSO
# ============================================
#check_page_access_auth0("TEV")

# === Logica della Pagina TEV ===
st.set_page_config(layout="wide")
st.title("🔬 Analisi TEV (Tracking Error Volatility)")

df = st.session_state.get("tev_data", pd.DataFrame())

if df.empty:
    st.warning("Dati TEV non caricati. Impossibile visualizzare la pagina.")
    st.stop()

vista = st.sidebar.radio("Seleziona la vista", ["Serie storica", "Fotografia attuale"])

if vista == "Serie storica":
    fondi = sorted(df["Fondo"].unique())
    fondo_sel = st.sidebar.selectbox("Seleziona il fondo", fondi)
    df_fondo = df[df["Fondo"] == fondo_sel].sort_values("Data")

    min_date, max_date = df_fondo["Data"].min().to_pydatetime(), df_fondo["Data"].max().to_pydatetime()

    preset = st.sidebar.selectbox(
        "Periodo predefinito",
        ["Tutto", "Ultimi 3 mesi", "Ultimi 6 mesi", "Ultimo anno", "YTD", "Personalizzato"]
    )
    today = max_date
    if preset == "Ultimi 3 mesi": start_date, end_date = today - timedelta(days=90), today
    elif preset == "Ultimi 6 mesi": start_date, end_date = today - timedelta(days=180), today
    elif preset == "Ultimo anno": start_date, end_date = today - timedelta(days=365), today
    elif preset == "YTD": start_date, end_date = datetime(year=today.year, month=1, day=1), today
    elif preset == "Tutto": start_date, end_date = min_date, max_date
    else:
        start_date, end_date = st.sidebar.slider(
            "Seleziona l'intervallo temporale",
            min_value=min_date, max_value=max_date, value=(min_date, max_date), format="DD/MM/YYYY"
        )
    
    df_fondo = df_fondo[(df_fondo["Data"] >= start_date) & (df_fondo["Data"] <= end_date)]
    
    fig = px.line(
        df_fondo, x="Data", y=["TEV", "Limite", "Limite maggiorato"],
        labels={"value": "TEV", "variable": "Serie"}, title=f"TEV - {fondo_sel}", height=600
    )
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(df_fondo)

elif vista == "Fotografia attuale":
    ultima_data = df["Data"].max()
    df_last = df[df["Data"] == ultima_data]
    
    st.subheader(f"📸 Fotografia attuale - TEV (contenitori) al {format_date(ultima_data.date())}")
    df_fasce = st.session_state.get("fasce_data", pd.DataFrame())

    df_last_sorted = df_last.sort_values("TEV", ascending=False)
    fondi = df_last_sorted["Fondo"].unique()
    n_fondi = len(fondi)

    fig = make_subplots(rows=1, cols=n_fondi, shared_yaxes=True)

    for i, fondo in enumerate(fondi, start=1):
        row, col = 1, i
        tev_val = df_last.loc[df_last["Fondo"] == fondo, "TEV"].values[0]
        limite = df_last.loc[df_last["Fondo"] == fondo, "Limite"].values[0]
        limite_magg = df_last.loc[df_last["Fondo"] == fondo, "Limite maggiorato"].values[0]

        if fondo not in df_fasce.index:
            st.warning(f"⚠️ Fasce non trovate per {fondo}")
            continue

        fasce = df_fasce.loc[fondo]
        max_fascia = fasce.max()

        # Contenitore e riempimento
        fig.add_trace(go.Bar(x=[fondo], y=[max_fascia],
                             marker=dict(color="rgba(230,230,230,0.3)", line=dict(color="black", width=1)),
                             showlegend=False), row=row, col=col)
        fig.add_trace(go.Bar(x=[fondo], y=[tev_val],
                             marker=dict(color="rgba(0,150,255,0.6)", line=dict(color="rgba(0,150,255,0.8)", width=1)),
                             showlegend=False), row=row, col=col)

        # Linee fasce, limite e limite maggiorato
        for fascia_nome, fascia_val in fasce.items():
            if fascia_val < max_fascia:
                fig.add_shape(type="line", x0=-0.4, x1=0.4, y0=fascia_val, y1=fascia_val,
                              line=dict(color="gray", width=1, dash="dot"), row=row, col=col)
                fig.add_trace(go.Scatter(x=[fondo, fondo], y=[fascia_val, fascia_val],
                                         mode='lines', line=dict(color='rgba(0,0,0,0)', width=5),
                                         hovertemplate=f'<b>{fascia_nome}</b><br>Valore: %{{y:.4f}}<extra></extra>',
                                         showlegend=False), row=row, col=col)
        
        fig.add_shape(type="line", x0=-0.4, x1=0.4, y0=limite, y1=limite,
                      line=dict(color="orange", width=2), row=row, col=col)
        fig.add_trace(go.Scatter(x=[fondo, fondo], y=[limite, limite],
                                 mode='lines', line=dict(color='rgba(0,0,0,0)', width=5),
                                 hovertemplate='<b>Limite</b><br>Valore: %{y:.4f}<extra></extra>',
                                 showlegend=False), row=row, col=col)
        
        fig.add_shape(type="line", x0=-0.4, x1=0.4, y0=limite_magg, y1=limite_magg,
                      line=dict(color="red", width=2), row=row, col=col)
        fig.add_trace(go.Scatter(x=[fondo, fondo], y=[limite_magg, limite_magg],
                                 mode='lines', line=dict(color='rgba(0,0,0,0)', width=5),
                                 hovertemplate='<b>Limite Maggiorato</b><br>Valore: %{y:.4f}<extra></extra>',
                                 showlegend=False), row=row, col=col)

    fig.update_layout(height=600, width=max(1000, 200 * n_fondi),
                      title_text=f"Fotografia TEV al {ultima_data.date()}",
                      barmode="overlay", xaxis_tickangle=-30)
    for i in range(1, n_fondi + 1):
        fig.update_xaxes(tickangle=-30, row=1, col=i)
    
    st.plotly_chart(fig, use_container_width=True)
    # 👇 Nota discreta per Etica Obiettivo Sociale
    if "Etica Obiettivo Sociale" in fondi:
        st.caption("ℹ️ Per *Etica Obiettivo Sociale* il valore riportato corrisponde alla **volatilità** e non alla TEV, poiché il fondo non ha un benchmark di riferimento.")
    
    st.dataframe(df_last_sorted)
