import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import numpy as np
from datetime import date, timedelta
import calendar

# ─── PAGE CONFIG ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Capacidad Productiva",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── THEME / CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');

    html, body, [class*="css"] {
        font-family: 'DM Sans', sans-serif;
    }

    .stApp {
        background-color: #0f1117;
        color: #e8eaf0;
    }

    section[data-testid="stSidebar"] {
        background-color: #161b27;
        border-right: 1px solid #232b3e;
    }

    section[data-testid="stSidebar"] .stMarkdown h3 {
        color: #5b9cf6;
        font-size: 0.7rem;
        font-weight: 600;
        letter-spacing: 0.15em;
        text-transform: uppercase;
        margin-top: 1.5rem;
        margin-bottom: 0.5rem;
    }

    .kpi-card {
        background: linear-gradient(135deg, #161b27 0%, #1a2035 100%);
        border: 1px solid #232b3e;
        border-radius: 12px;
        padding: 1.2rem 1.4rem;
        margin-bottom: 0.5rem;
    }

    .kpi-label {
        font-size: 0.72rem;
        font-weight: 500;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: #6b7a99;
        margin-bottom: 0.3rem;
    }

    .kpi-value {
        font-family: 'DM Mono', monospace;
        font-size: 1.9rem;
        font-weight: 500;
        color: #e8eaf0;
        line-height: 1;
    }

    .kpi-value.good   { color: #4ade80; }
    .kpi-value.warn   { color: #facc15; }
    .kpi-value.bad    { color: #f87171; }

    .kpi-sub {
        font-size: 0.72rem;
        color: #6b7a99;
        margin-top: 0.3rem;
    }

    .section-title {
        font-size: 0.7rem;
        font-weight: 600;
        letter-spacing: 0.15em;
        text-transform: uppercase;
        color: #5b9cf6;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 1px solid #232b3e;
    }

    div[data-testid="stPlotlyChart"] {
        border: 1px solid #232b3e;
        border-radius: 12px;
        overflow: hidden;
        background: #161b27;
    }

    .stSlider > div > div > div { background: #232b3e; }
    .stSlider > div > div > div > div { background: #5b9cf6; }

    hr { border-color: #232b3e; }

    .badge {
        display: inline-block;
        padding: 0.2rem 0.6rem;
        border-radius: 20px;
        font-size: 0.7rem;
        font-weight: 600;
        letter-spacing: 0.05em;
    }
    .badge-green { background: #14532d; color: #4ade80; }
    .badge-yellow { background: #422006; color: #facc15; }
    .badge-red { background: #450a0a; color: #f87171; }
</style>
""", unsafe_allow_html=True)

# ─── HELPERS ────────────────────────────────────────────────────────────────────
PLOTLY_LAYOUT = dict(
    paper_bgcolor="#161b27",
    plot_bgcolor="#161b27",
    font=dict(family="DM Sans", color="#9ba8c0", size=12),
    margin=dict(t=40, b=40, l=50, r=30),
    xaxis=dict(gridcolor="#232b3e", linecolor="#232b3e", tickcolor="#232b3e"),
    yaxis=dict(gridcolor="#232b3e", linecolor="#232b3e", tickcolor="#232b3e"),
)

def dias_habiles(year: int, month: int) -> int:
    _, days_in_month = calendar.monthrange(year, month)
    count = 0
    for d in range(1, days_in_month + 1):
        if date(year, month, d).weekday() < 5:  # lun-vie
            count += 1
    return count

def utilization_color(pct: float) -> str:
    if pct >= 90: return "bad"
    if pct >= 75: return "warn"
    return "good"

def kpi(label: str, value: str, sub: str = "", color_class: str = "") -> None:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value {color_class}">{value}</div>
        {"<div class='kpi-sub'>" + sub + "</div>" if sub else ""}
    </div>
    """, unsafe_allow_html=True)

# ─── SIDEBAR ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🏭 Simulador")

    st.markdown("### Producción")
    ton_por_dia = st.slider("Toneladas / día", 10, 50, 20, 1)

    st.markdown("### Demanda")
    venta_base = st.slider("Venta mensual base (ton)", 100, 600, 320, 10)
    crecimiento_pct = st.slider("Crecimiento mensual (%)", -5, 15, 3, 1)

    st.markdown("### Restricciones")
    dias_feriados = st.slider("Feriados por mes", 0, 5, 1, 1)
    dias_limpiezas = st.slider("Limpiezas por mes (días)", 0, 4, 1, 1)

    st.markdown("### Campaña Especial")
    tiene_campana = st.checkbox("Activar campaña especial", value=False)
    if tiene_campana:
        dias_fab_campana = st.slider("Días de fabricación campaña", 3, 15, 7, 1)
        ton_campana = st.slider("Toneladas extra / día campaña", 0, 20, 5, 1)
    else:
        dias_fab_campana = 0
        ton_campana = 0

    st.markdown("### Inventario")
    stock_inicial = st.slider("Stock inicial (ton)", 0, 500, 100, 10)
    stock_objetivo_dias = st.slider("Objetivo de stock (días)", 30, 120, 60, 5)

    st.markdown("### Horizonte")
    n_meses = st.slider("Meses a simular", 3, 18, 12, 1)

# ─── SIMULACIÓN ─────────────────────────────────────────────────────────────────
today = date.today()
registros = []
stock_actual = stock_inicial

for i in range(n_meses):
    # mes
    mes_offset = (today.month - 1 + i)
    year = today.year + mes_offset // 12
    month = mes_offset % 12 + 1

    # dias
    dh = dias_habiles(year, month)
    dias_perdidos = dias_feriados + dias_limpiezas

    # campaña: -2 dias limpieza previa, dias_fab, +1 dia limpieza post
    dias_campana_total = 0
    produccion_campana = 0
    if tiene_campana:
        dias_campana_total = 2 + dias_fab_campana + 1  # overhead
        dias_perdidos_campana = 2 + 1
        dias_perdidos += dias_perdidos_campana
        produccion_campana = dias_fab_campana * (ton_por_dia + ton_campana)

    dias_prod = max(0, dh - dias_perdidos)

    capacidad_std = dias_prod * ton_por_dia + produccion_campana
    capacidad_max = dh * ton_por_dia  # sin restricciones

    # demanda
    venta = venta_base * ((1 + crecimiento_pct / 100) ** i)
    venta = round(venta, 1)

    # utilizacion
    utilizacion = (venta / capacidad_std * 100) if capacidad_std > 0 else 0
    utilizacion = round(utilizacion, 1)

    # inventario
    produccion_mes = min(capacidad_std, capacidad_std)  # produce lo disponible
    delta_inv = produccion_mes - venta
    stock_actual = max(0, stock_actual + delta_inv)

    # stock objetivo en toneladas
    consumo_diario = venta / 30
    stock_objetivo_ton = consumo_diario * stock_objetivo_dias

    registros.append({
        "mes": f"{calendar.month_abbr[month]} {year}",
        "year": year,
        "month": month,
        "dias_habiles": dh,
        "dias_perdidos": dias_perdidos,
        "dias_prod": dias_prod,
        "capacidad_max": capacidad_max,
        "capacidad_std": round(capacidad_std, 1),
        "venta": venta,
        "utilizacion": utilizacion,
        "delta_inv": round(delta_inv, 1),
        "stock": round(stock_actual, 1),
        "stock_objetivo_ton": round(stock_objetivo_ton, 1),
    })

df = pd.DataFrame(registros)

# ─── HEADER ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div style='margin-bottom:1.5rem'>
    <span style='font-size:0.75rem;letter-spacing:0.15em;text-transform:uppercase;color:#5b9cf6;font-weight:600'>
        Dashboard Operativo
    </span>
    <h1 style='margin:0.2rem 0 0;font-size:1.6rem;font-weight:300;color:#e8eaf0;letter-spacing:-0.02em'>
        Capacidad Productiva vs Demanda
    </h1>
</div>
""", unsafe_allow_html=True)

# ─── KPIs ────────────────────────────────────────────────────────────────────────
row = df.iloc[0]  # primer mes como referencia actual
dias_a_objetivo = None
for _, r in df.iterrows():
    if r["stock"] >= r["stock_objetivo_ton"]:
        dias_a_objetivo = r["mes"]
        break

cols = st.columns(6)
with cols[0]:
    kpi("Capacidad mes 1", f"{int(row.capacidad_std):,} ton",
        f"max: {int(row.capacidad_max):,} ton")
with cols[1]:
    kpi("Venta mes 1", f"{int(row.venta):,} ton")
with cols[2]:
    uc = utilization_color(row.utilizacion)
    kpi("Utilizacion", f"{row.utilizacion:.1f}%", color_class=uc)
with cols[3]:
    kpi("Dias perdidos", str(int(row.dias_perdidos)),
        f"{int(row.dias_habiles)} habiles / {int(row.dias_prod)} prod.")
with cols[4]:
    kpi("Stock actual", f"{int(df.iloc[0].stock):,} ton",
        f"objetivo: {int(df.iloc[0].stock_objetivo_ton):,} ton")
with cols[5]:
    if dias_a_objetivo:
        kpi("Alcanza objetivo", dias_a_objetivo, color_class="good")
    else:
        kpi("Alcanza objetivo", "No alcanza", color_class="bad")

st.markdown("<hr style='margin:1.2rem 0'>", unsafe_allow_html=True)

# ─── CHARTS ─────────────────────────────────────────────────────────────────────
col_left, col_right = st.columns([3, 2])

with col_left:
    st.markdown("<div class='section-title'>Ventas vs Capacidad</div>", unsafe_allow_html=True)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["mes"], y=df["capacidad_max"],
        name="Cap. maxima",
        marker_color="rgba(91,156,246,0.15)",
        marker_line_color="rgba(91,156,246,0.4)",
        marker_line_width=1,
    ))
    fig.add_trace(go.Bar(
        x=df["mes"], y=df["capacidad_std"],
        name="Cap. disponible",
        marker_color="rgba(91,156,246,0.45)",
    ))
    fig.add_trace(go.Scatter(
        x=df["mes"], y=df["venta"],
        name="Venta",
        mode="lines+markers",
        line=dict(color="#4ade80", width=2.5),
        marker=dict(size=6, color="#4ade80"),
    ))
    fig.update_layout(
        **PLOTLY_LAYOUT,
        barmode="overlay",
        legend=dict(orientation="h", y=-0.15, x=0, bgcolor="rgba(0,0,0,0)"),
        yaxis_title="Toneladas",
        height=320,
    )
    st.plotly_chart(fig, use_container_width=True)

with col_right:
    st.markdown("<div class='section-title'>Utilizacion (%)</div>", unsafe_allow_html=True)

    colors = ["#f87171" if u >= 90 else "#facc15" if u >= 75 else "#4ade80"
              for u in df["utilizacion"]]

    fig2 = go.Figure(go.Bar(
        x=df["mes"],
        y=df["utilizacion"],
        marker_color=colors,
        text=[f"{u:.0f}%" for u in df["utilizacion"]],
        textposition="outside",
        textfont=dict(size=10, color="#9ba8c0"),
    ))
    fig2.add_hline(y=90, line_dash="dot", line_color="#f87171",
                   annotation_text="90%", annotation_font_color="#f87171",
                   annotation_font_size=10)
    fig2.add_hline(y=75, line_dash="dot", line_color="#facc15",
                   annotation_text="75%", annotation_font_color="#facc15",
                   annotation_font_size=10)
    fig2.update_layout(
        **PLOTLY_LAYOUT,
        yaxis=dict(range=[0, 120], **PLOTLY_LAYOUT["yaxis"]),
        yaxis_title="%",
        height=320,
        showlegend=False,
    )
    st.plotly_chart(fig2, use_container_width=True)

# ─── INVENTARIO ─────────────────────────────────────────────────────────────────
st.markdown("<div class='section-title'>Inventario Acumulado</div>", unsafe_allow_html=True)

fig3 = go.Figure()

# zona entre 0 y objetivo (sombreada)
fig3.add_trace(go.Scatter(
    x=df["mes"].tolist() + df["mes"].tolist()[::-1],
    y=df["stock_objetivo_ton"].tolist() + [0]*len(df),
    fill="toself",
    fillcolor="rgba(91,156,246,0.05)",
    line=dict(color="rgba(0,0,0,0)"),
    showlegend=False,
    hoverinfo="skip",
))

fig3.add_trace(go.Scatter(
    x=df["mes"], y=df["stock_objetivo_ton"],
    name="Objetivo stock",
    mode="lines",
    line=dict(color="#5b9cf6", width=1.5, dash="dash"),
))

# colores por encima/debajo objetivo
colores_stock = [
    "#4ade80" if s >= o else "#f87171"
    for s, o in zip(df["stock"], df["stock_objetivo_ton"])
]

fig3.add_trace(go.Bar(
    x=df["mes"], y=df["stock"],
    name="Stock real",
    marker_color=colores_stock,
    opacity=0.75,
))

fig3.add_trace(go.Scatter(
    x=df["mes"], y=df["stock"],
    mode="lines+markers",
    name="Tendencia",
    line=dict(color="#e8eaf0", width=1.5),
    marker=dict(size=5, color="#e8eaf0"),
))

fig3.update_layout(
    **PLOTLY_LAYOUT,
    barmode="overlay",
    legend=dict(orientation="h", y=-0.15, x=0, bgcolor="rgba(0,0,0,0)"),
    yaxis_title="Toneladas",
    height=300,
)
st.plotly_chart(fig3, use_container_width=True)

# ─── TABLA DETALLE ───────────────────────────────────────────────────────────────
with st.expander("Ver tabla detalle por mes"):
    display_df = df[[
        "mes", "dias_habiles", "dias_perdidos", "dias_prod",
        "capacidad_max", "capacidad_std", "venta",
        "utilizacion", "delta_inv", "stock"
    ]].copy()
    display_df.columns = [
        "Mes", "Dias hab.", "Dias perd.", "Dias prod.",
        "Cap. max", "Cap. disp.", "Venta",
        "Utiliz. %", "Delta inv.", "Stock"
    ]
    st.dataframe(
        display_df.style
            .format({
                "Cap. max": "{:,.0f}",
                "Cap. disp.": "{:,.0f}",
                "Venta": "{:,.0f}",
                "Utiliz. %": "{:.1f}%",
                "Delta inv.": "{:+,.0f}",
                "Stock": "{:,.0f}",
            })
            .background_gradient(subset=["Utiliz. %"], cmap="RdYlGn_r", vmin=50, vmax=110),
        use_container_width=True,
        hide_index=True,
    )

# ─── FOOTER ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div style='margin-top:2rem;padding-top:1rem;border-top:1px solid #232b3e;
            font-size:0.7rem;color:#3d4a63;text-align:right;letter-spacing:0.05em'>
    MVP — Simulador Capacidad Productiva
</div>
""", unsafe_allow_html=True)
