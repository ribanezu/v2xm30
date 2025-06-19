import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from streamlit.components.v1 import html as html_component
import streamlit.components.v1 as components
import pyodbc
from sqlalchemy import create_engine
import geopandas as gpd
import json
from keplergl import KeplerGl
import warnings
from utils.loaders import load_data, load_m30_data
warnings.simplefilter(action='ignore', category=FutureWarning)

# ---------------------------
# Configuración de la app
# ---------------------------
st.set_page_config(page_title="Demanda de Tráfico", layout="wide", initial_sidebar_state="collapsed")

def load_custom_css(path="./style_dark_demanda.css"):
    with open(path, encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_custom_css()

def clasificar_velocidad(v):
    """Clasifica la velocidad en rangos"""
    if v <= 30:
        return "🔴 0–30 km/h"
    elif v <= 50:
        return "🟡 30–50 km/h"
    elif v <= 70:
        return "🟢 50–70 km/h"
    else:
        return "🔵 70-90+ km/h"
    

df,df_denm = load_data()
orden_dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
m30 = load_m30_data()



# ===== HEADER =====
st.markdown("""
<div class="main-title">
    DASHBOARD DE DATOS DE TRÁFICO V2X
</div>
<div style="text-align: center; color: #cbd5e1; font-size: 1.1rem; margin-bottom: 2rem;">
    Análisis de datos históricos recopilados
</div>
""", unsafe_allow_html=True)

st.markdown('<h3 class="section-title">  Datos globales (todo el tramo)</h3>', unsafe_allow_html=True)



# ---------------------------
# Vehículos hora (mod)
# ---------------------------

# ---------------------------
# Heatmap semanal
# ---------------------------


df["day"] = pd.to_datetime(df["day"])
conteo_dias = (
    df.drop_duplicates(subset=["day"])
    .groupby("weekday_es")["day"]
    .count()
    .reset_index(name="n_días")
)
df_heatmap = (
    df.groupby(["weekday_es", "hour_label"])["station_id"]
    .nunique()
    .reset_index(name="vehículos")
)
df_heatmap = df_heatmap.merge(conteo_dias, on="weekday_es")
df_heatmap["vehículos"] = df_heatmap["vehículos"] / df_heatmap["n_días"]

# Crear el heatmap
fig_heatmap = px.density_heatmap(
    df_heatmap,
    x="hour_label",
    y="weekday_es",
    z="vehículos",
    color_continuous_scale=px.colors.sequential.Inferno_r,
    labels={
        "vehículos": "Vehículos únicos promedio",
        "hour_label": "Hora",
        "weekday_es": "Día de la semana"
    },
    template="plotly_dark",
    height=400
)

fig_heatmap.update_layout(
    title="",
    xaxis=dict(dtick=1),
    margin=dict(t=40, b=20),
    coloraxis_colorbar=dict(title="Vehículos únicos promedio")
)
fig_heatmap.update_layout(
    plot_bgcolor='rgba(0,0,0,0)',
    paper_bgcolor='rgba(0,0,0,0)',
    font_color='#f8fafc',
    title_font_size=16,
    title_font_color='#f8fafc',
    xaxis=dict(
        gridcolor='#475569',
        showgrid=True,
        zeroline=False
    ),
    yaxis=dict(
        gridcolor='#475569',
        showgrid=True,
        zeroline=False
    ),
    hovermode='x unified'
)






# ---------------------------
# Vehículos por día (Radar)
# ---------------------------
# df_por_dia = df.groupby("weekday_es")["station_id"].nunique().reset_index(name="vehículos")
# df_por_dia["weekday_es"] = pd.Categorical(df_por_dia["weekday_es"], categories=orden_dias, ordered=True)

df_por_dia = df.drop_duplicates(["station_id", "weekday_es"]) \
    .groupby("weekday_es")["station_id"].count() \
    .reset_index(name="vehículos")

df_por_dia["weekday_es"] = pd.Categorical(df_por_dia["weekday_es"], categories=orden_dias, ordered=True)
df_por_dia = df_por_dia.merge(conteo_dias, on="weekday_es")
df_por_dia["vehículos"] = df_por_dia["vehículos"] / df_por_dia["n_días"]
fig_radar = go.Figure()
fig_radar.add_trace(go.Scatterpolar(
    r=df_por_dia["vehículos"],
    theta=df_por_dia["weekday_es"],
    fill='toself',
    line=dict(color="orangered", width=2),
    hovertemplate='%{theta}: %{r} vehículos<extra></extra>'
))
fig_radar.update_layout(
    template="plotly_dark",
    height=400,
    polar=dict(
        radialaxis=dict(visible=True, tickfont=dict(size=10)),
        angularaxis=dict(rotation=90, direction="clockwise", tickfont=dict(size=14))
    ),
    showlegend=False,
    margin=dict(t=50, b=20)
)
fig_radar.update_layout(
    plot_bgcolor='rgba(0,0,0,0)',
    paper_bgcolor='rgba(0,0,0,0)',
    font_color='#f8fafc',
    xaxis=dict(
        gridcolor='#475569',
        showgrid=True,
        zeroline=False
    ),
    yaxis=dict(
        gridcolor='#475569',
        showgrid=True,
        zeroline=False
    ),
    hovermode='x unified'
)

# ---------------------------
# Tráfico por hora según el día
# ---------------------------
df_dia_hora = df.groupby(["weekday_es", "hour_label"])["station_id"].nunique().reset_index(name="vehículos")
df_dia_hora["weekday_es"] = pd.Categorical(df_dia_hora["weekday_es"], categories=orden_dias, ordered=True)

# Asegurar orden correcto en el eje X
df_dia_hora["hour_label"] = pd.Categorical(
    df_dia_hora["hour_label"],
    categories=[f"{h:02d}:00" for h in range(24)],
    ordered=True
)
df_dia_hora = df_dia_hora.merge(conteo_dias, on="weekday_es")
df_dia_hora["vehículos"] = df_dia_hora["vehículos"] / df_dia_hora["n_días"]
fig_dia_hora = px.line(
    df_dia_hora.sort_values(["weekday_es", "hour_label"]),
    x="hour_label",
    y="vehículos",
    color="weekday_es",
    line_shape="spline",
    markers=True,
    labels={
        "hour_label": "Hora del día",
        "vehículos": "Vehículos únicos",
        "weekday_es": "Día de la semana"
    },
    template="plotly_dark"
)

fig_dia_hora.update_traces(marker=dict(size=6), line=dict(width=2))

fig_dia_hora.update_layout(
    height=400,
    margin=dict(t=50, b=20),
    xaxis=dict(tickmode="linear", tickangle=-45),
    yaxis=dict(title="Vehículos únicos")
)
fig_dia_hora.update_layout(
    plot_bgcolor='rgba(0,0,0,0)',
    paper_bgcolor='rgba(0,0,0,0)',
    font_color="#f8fafc",
    xaxis=dict(
        gridcolor='#475569',
        showgrid=True,
        zeroline=False
    ),
    yaxis=dict(
        gridcolor='#475569',
        showgrid=True,
        zeroline=False
    ),
    hovermode='x unified'
)





st.markdown('<div class="chart-container">', unsafe_allow_html=True)
st.markdown('<div class="chart-title">Mapa de calor de tráfico semanal</div>', unsafe_allow_html=True)
st.plotly_chart(fig_heatmap, use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)

col3, col4 = st.columns(2)
with col3:
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    st.markdown('<div class="chart-title">Vehículos únicos por día de la semana</div>', unsafe_allow_html=True)
    st.plotly_chart(fig_radar, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

with col4:
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    st.markdown('<div class="chart-title">Tráfico por hora según el día de la semana</div>', unsafe_allow_html=True)
    st.plotly_chart(fig_dia_hora, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

#----------------------------------------------------------------------------------------------------------------------------------------------------------------
# --------------------------------------------------------------------------------------------------------------------------------
# ---------------------------
# ---------------------------
# Análisis por Día de la Semana
# ---------------------------
st.markdown('<h3 class="section-title">  Informe día tipo</h3>', unsafe_allow_html=True)

selected_day = st.selectbox("Selecciona un día", df["weekday_es"].cat.categories, key="select_dia_semana")

df_day = df[df["weekday_es"] == selected_day]
df_day["hour_label"] = df_day["hour"].apply(lambda h: f"{h:02d}:00")
num_dias = df_day['day'].nunique()
# Vehículos por hora
df_day_vph = df_day.groupby("hour_label")["station_id"].nunique().reset_index(name="Vehículos únicos")
df_day_vph['Vehículos únicos']=df_day_vph['Vehículos únicos']/num_dias

fig_day_vph = px.bar(df_day_vph, x="hour_label", y="Vehículos únicos",
                     color= "Vehículos únicos", color_continuous_scale=["#FED7AA", "#FB923C", "#EA580C"], 
                     template="plotly_dark", labels={"hour_label": "Hora del día", "Vehículos únicos": "Vehículos únicos"})

fig_day_vph.update_layout(
    height=400,
    margin=dict(t=50, b=20),
    coloraxis_showscale=True
)
fig_day_vph.update_layout(
    plot_bgcolor='rgba(0,0,0,0)',
    paper_bgcolor='rgba(0,0,0,0)',
    font_color="#f8fafc",
    xaxis=dict(
        gridcolor='#475569',
        showgrid=True,
        zeroline=False
    ),
    yaxis=dict(
        gridcolor='#475569',
        showgrid=True,
        zeroline=False
    ),
    hovermode='x unified'
)

# Frenada media
df_day_freno = df_day[df_day["longitudinal_acc"] < 0].copy()
df_day_freno["braking_intensity"] = -df_day_freno["longitudinal_acc"]
df_day_frenadas = df_day_freno.groupby("hour_label")["braking_intensity"].mean().reset_index()
fig_day_frenadas = px.area(df_day_frenadas, x="hour_label", y="braking_intensity",
                           title=f"Intensidad de frenada media por hora del dia - {selected_day}",
                           labels={"braking_intensity": "Intensidad frenada media (m/s²)"},
                           template="plotly_dark")
fig_day_frenadas.update_layout(
    plot_bgcolor='rgba(0,0,0,0)',
    paper_bgcolor='rgba(0,0,0,0)',
    font_color="#f8fafc",
    xaxis=dict(
        gridcolor='#475569',
        showgrid=True,
        zeroline=False
    ),
    yaxis=dict(
        gridcolor='#475569',
        showgrid=True,
        zeroline=False
    ),
    hovermode='x unified'
)

# ---------------------------
# LAYOUT - Día de la Semana
# ---------------------------
st.markdown('<div class="chart-container">', unsafe_allow_html=True)
st.markdown(f'<div class="chart-title">Vehículos por hora - {selected_day}</div>', unsafe_allow_html=True)
st.plotly_chart(fig_day_vph, use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)



#### Perfil de velocidad global
grupo_hora = df_day.groupby("hour_label")["speed_kmh"]
vel_mean = grupo_hora.mean()
vel_p25 = grupo_hora.quantile(0.25)
vel_p75 = grupo_hora.quantile(0.75)
n_vehiculos = df_day.groupby("hour_label")["station_id"].nunique()



# Asegurar orden correcto en el eje X
orden = (
    pd.to_datetime(vel_mean.index, format="%H:%M")
    .hour * 60 + pd.to_datetime(vel_mean.index, format="%H:%M").minute
)
orden_index = vel_mean.index.to_series()[orden.argsort()].tolist()

# Construcción del gráfico
fig_vel = go.Figure()
fig_vel.add_trace(go.Scatter(
    x=orden_index, y=vel_mean[orden_index],
    mode="lines+markers", name="Media", 
    text=[f"Nº vehículos: {v}" for v in n_vehiculos[orden_index]],
    line=dict(color="#007ACC", shape="spline", width=2),
    marker=dict(symbol="circle", size=6)
))
fig_vel.add_trace(go.Scatter(
    x=orden_index, y=vel_p25[orden_index],
    mode="lines", line=dict(width=0), showlegend=False
))
fig_vel.add_trace(go.Scatter(
    x=orden_index, y=vel_p75[orden_index],
    mode="lines", fill="tonexty", name="P25–P75",
    fillcolor="rgba(0, 122, 204, 0.2)", line=dict(width=0)
))

fig_vel.update_layout(
    xaxis_title="Hora del día", yaxis_title="Velocidad (km/h)",
    template="plotly_dark", height=400, margin=dict(t=50, b=20),
    xaxis=dict(tickmode="array", tickvals=orden_index, ticktext=orden_index)
)
fig_vel.update_layout(
    plot_bgcolor='rgba(0,0,0,0)',
    paper_bgcolor='rgba(0,0,0,0)',
    font_color="#f8fafc",
    xaxis=dict(
        gridcolor='#475569',
        showgrid=True,
        zeroline=False
    ),
    yaxis=dict(
        gridcolor='#475569',
        showgrid=True,
        zeroline=False
    ),
    hovermode='x unified'
)

# # Frenadas globales por hora
df_frenadas = df_day[df_day["longitudinal_acc"] < 0].copy()
df_frenadas["braking_intensity"] = -df_frenadas["longitudinal_acc"]
frenadas_hora = df_frenadas.groupby("hour_label")["braking_intensity"].mean().reset_index()
frenadas_hora["hour_label"] = pd.Categorical(frenadas_hora["hour_label"], categories=[f"{i:02d}:00" for i in range(24)], ordered=True)
frenadas_hora = frenadas_hora.sort_values("hour_label")

fig_freno = go.Figure()
fig_freno.add_trace(go.Scatter(
    x=frenadas_hora["hour_label"],
    y=frenadas_hora["braking_intensity"],
    mode="lines", fill="tozeroy", name="Frenada media",
    line=dict(color="#108AD1", shape="spline", width=2),
    hovertemplate="Hora: %{x}<br>Intensidad frenada media: %{y:.2f} m/s²<extra></extra>"
))
fig_freno.update_layout(
    xaxis_title="Hora del día", yaxis_title="Frenada media (m/s²)",
    template="plotly_dark", height=400, margin=dict(t=50, b=20),
    xaxis=dict(tickmode="linear", tickvals=[f"{i:02d}:00" for i in range(24)])
)
fig_freno.update_layout(
    plot_bgcolor='rgba(0,0,0,0)',
    paper_bgcolor='rgba(0,0,0,0)',
    font_color="#f8fafc",
    xaxis=dict(
        gridcolor='#475569',
        showgrid=True,
        zeroline=False
    ),
    yaxis=dict(
        gridcolor='#475569',
        showgrid=True,
        zeroline=False
    ),
    hovermode='x unified'
)

col7, col8 = st.columns(2)

with col7:
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    st.markdown(f'<div class="chart-title">Velocidad media por hora - {selected_day}</div>', unsafe_allow_html=True)
    st.plotly_chart(fig_vel, use_container_width=True)

with col8:
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    st.markdown(f'<div class="chart-title">Intensidad frenada media por hora - {selected_day}</div>', unsafe_allow_html=True)
    st.plotly_chart(fig_freno, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)


# ---------------------------
# Informe Día Tipo
# ---------------------------
st.markdown('<h3 class="section-title">  Día tipo por tramo</h3>', unsafe_allow_html=True)

# 1. Selección de tramo físico
tramos_disponibles = df["name_osmid"].dropna().unique()
tramo_seleccionado = st.selectbox("Selecciona un tramo:", sorted(tramos_disponibles))
df_tramo = df[df["name_osmid"] == tramo_seleccionado].copy()
df_denm_tramo = df_denm[df_denm["station_id"].isin(df_tramo["station_id"].unique())].copy()

for _df in [df_tramo, df_denm_tramo]:
    _df["tramo_horario"] = _df["received_at"].dt.floor("1H")
    _df["hora_label"] = _df["tramo_horario"].dt.strftime("%H:%M")
    _df["hora_label"] = pd.Categorical(_df["hora_label"], categories=[f"{h:02d}:00" for h in range(24)], ordered=True)

df_tramo = df_tramo[df_tramo["weekday_es"] == selected_day]
df_denm_tramo = df_denm_tramo[df_denm_tramo["weekday_es"] == selected_day]

# 4. Agregación tráfico
df_diatipo = (
    df_tramo.groupby(["hora_label"])
    .agg(
        velocidad_media=("speed_kmh", "mean"),
        vehículos=("station_id", "nunique")
    )
    .reset_index()
)

# 5. Agregación de alertas totales
alertas = (
    df_denm_tramo.groupby(["hora_label"])
    .size()
    .reset_index(name="alertas")
)

# 6. Unión tráfico + alertas
df_diatipo = df_diatipo.merge(alertas, on="hora_label", how="left")
df_diatipo["alertas"] = df_diatipo["alertas"].fillna(0)
df_diatipo = df_diatipo.sort_values("hora_label")

# 7. Gráficos tráfico y velocidad
fig_vel_tipo_dia = px.line(
    df_diatipo,
    x="hora_label", y="velocidad_media",
    labels={"hora_label": "Hora", "velocidad_media": "Velocidad (km/h)"},
    template="plotly_dark",
    markers=True,
    line_shape="spline",
    color_discrete_sequence=["#00BFFF"]
)
fig_vel_tipo_dia.update_layout(
    plot_bgcolor='rgba(0,0,0,0)',
    paper_bgcolor='rgba(0,0,0,0)',
    font_color="#f8fafc",
    xaxis=dict(
        gridcolor='#475569',
        showgrid=True,
        zeroline=False
    ),
    yaxis=dict(
        gridcolor='#475569',
        showgrid=True,
        zeroline=False
    ),
    hovermode='x unified'
)

fig_intensidad_dia_tipo = px.bar(
    df_diatipo,
    x="hora_label", y="vehículos",
    labels={"hora_label": "Hora", "vehículos": "Vehículos únicos"},
    template="plotly_dark",
    color_discrete_sequence=["#3C7FFB"]
)
fig_intensidad_dia_tipo.update_layout(
    plot_bgcolor='rgba(0,0,0,0)',
    paper_bgcolor='rgba(0,0,0,0)',
    font_color="#f8fafc",
    xaxis=dict(
        gridcolor='#475569',
        showgrid=True,
        zeroline=False
    ),
    yaxis=dict(
        gridcolor='#475569',
        showgrid=True,
        zeroline=False
    ),
    hovermode='x unified'
)



# -----------------------------
# Selector único de evento (cause_desc)
# -----------------------------
tipos_evento = df_denm_tramo["cause_desc"].dropna().unique()
evento_seleccionado = st.selectbox("Selecciona tipo de evento (cause_desc):", ["Todos"] + sorted(tipos_evento))

df_eventos = df_denm_tramo.copy()
if evento_seleccionado != "Todos":
    df_eventos = df_eventos[df_eventos["cause_desc"] == evento_seleccionado]

# Agregación de eventos y subcausas
df_eventos_agg = (
    df_eventos.groupby("hora_label")
    .agg(
        eventos=("id", "count"),
        subcausas=("subcause_desc", lambda x: ', '.join(x.dropna().unique()))
    )
    .reset_index()
)

# Gráfico de eventos
fig_eventos = px.bar(
    df_eventos_agg.sort_values("hora_label"),
    x="hora_label", y="eventos",
    labels={"hora_label": "Hora", "eventos": "Eventos"},
    template="plotly_dark",
    hover_data={"subcausas": True},
    color_discrete_sequence=["#76D5E6"]
)
fig_eventos.update_layout(
    plot_bgcolor='rgba(0,0,0,0)',
    paper_bgcolor='rgba(0,0,0,0)',
    font_color="#f8fafc",
    xaxis=dict(
        gridcolor='#475569',
        showgrid=True,
        zeroline=False
    ),
    yaxis=dict(
        gridcolor='#475569',
        showgrid=True,
        zeroline=False
    ),
    hovermode='x unified'
)

# ---------------------------
# Layout visual
# ---------------------------
col11, col12 = st.columns(2)
with col11:
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    st.markdown(f'<div class="chart-title">Velocidad media - {selected_day} - Tramo {tramo_seleccionado}</div>', unsafe_allow_html=True)
    st.plotly_chart(fig_vel_tipo_dia, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

with col12:
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    st.markdown(f'<div class="chart-title">Intensidad de tráfico - {selected_day} - Tramo {tramo_seleccionado}</div>', unsafe_allow_html=True)
    st.plotly_chart(fig_intensidad_dia_tipo, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)



st.markdown('<div class="chart-container">', unsafe_allow_html=True)
st.markdown(f'<div class="chart-title">Evento: {evento_seleccionado} - {selected_day} - Tramo {tramo_seleccionado}</div>', unsafe_allow_html=True)
st.plotly_chart(fig_eventos, use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)


gdf_velocidades = gpd.read_file("./data/gdf_velocidades.geojson")

### -------------------------------
### MAPA 2
st.markdown('<h3 class="section-title">  Velocidades medias por tramo - todo el histórico</h3>', unsafe_allow_html=True)
@st.cache_resource
def load_kepler_config_velocidades(hash_funcs={dict: lambda _: None}):
    with open("./data/config/velocidades_tramos.json") as f:
        return json.load(f)

config_2 = load_kepler_config_velocidades()
print(config_2)

kepler_map = KeplerGl(
    height=800,
    data={
        "Velocidad tramos historico": gdf_velocidades
    },
    config=config_2
)



html_mapa_2 = kepler_map._repr_html_()
if isinstance(html_mapa_2, bytes):
    html_mapa_2 = html_mapa_2.decode("utf-8")

#CSS y resize fix
hide_side_panel_css = """
<style>
div[class*="side-bar__close"] {
    display: none !important;
}
</style>
"""

resize_fix = """
<script>
  setTimeout(() => {
    window.dispatchEvent(new Event('resize'));
  }, 300);
</script>
"""

# # Mostrar el mapa en Streamlit
with st.container():
    components.html(hide_side_panel_css + html_mapa_2 + resize_fix, height=700, width=2000, scrolling=False)