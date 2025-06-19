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
warnings.simplefilter(action='ignore', category=FutureWarning)

# ---------------------------
# Configuración de la app
# ---------------------------
st.set_page_config(page_title="Demanda de Tráfico", layout="wide", initial_sidebar_state="collapsed")

def load_custom_css(path="./style_dark_demanda.css"):
    with open(path, encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_custom_css()

# ---------------------------
# Cargar datos
# ---------------------------
@st.cache_data

def load_data():
    # Conexión a la base de datos
    db_url = st.secrets["db_url"]
    engine = create_engine(db_url)

    df = pd.read_sql("SELECT * FROM cam_ref_message", engine)
    df_denm = pd.read_sql("SELECT * FROM denm_ref_message", engine)

    df["received_at"] = pd.to_datetime(df["received_at"])
    if "weekday_es" in df.columns:
        df["weekday_es"] = pd.Categorical(
            df["weekday_es"],
            categories=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"],
            ordered=True
        )
    if "hour" in df.columns and "hour_label" not in df.columns:
        df["hour_label"] = df["hour"].apply(lambda x: f"{int(x):02d}:00")

    df_denm["received_at"] = pd.to_datetime(df_denm["received_at"])
    if "weekday_es" in df_denm.columns:
        df_denm["weekday_es"] = pd.Categorical(
            df_denm["weekday_es"],
            categories=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"],
            ordered=True
        )
    if "hour" in df_denm.columns and "hour_label" not in df_denm.columns:
        df_denm["hour_label"] = df_denm["hour"].apply(lambda x: f"{int(x):02d}:00")

    return df, df_denm

@st.cache_data
def load_m30_data():
    gdf = gpd.read_file("data/m30_osm_v3.shp")
    gdf = gdf.to_crs(epsg=4326)
    return gdf


df,df_denm = load_data()
orden_dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
m30 = load_m30_data()



def clasificar_velocidad(v):
    if v <= 30:
        return "0–30 km/h"
    elif v <= 50:
        return "30–50 km/h"
    elif v <= 70:
        return "50–70 km/h"
    else:
        return "70-90+ km/h"





df['received_at'] = pd.to_datetime(df['received_at'])
hoy = pd.Timestamp.today().normalize()
hace_una_semana = hoy - pd.Timedelta(days=7)

# Filtrado
df_ultima_semana = df[df['received_at'] >= hace_una_semana].copy()
fclasses_validas = ['motorway', 'motorway_link', 'primary_link']
df_cam_filtrado = df_ultima_semana[df_ultima_semana["fclass"].isin(fclasses_validas)].copy()
df_ultima_semana["velocidad_rango"] = df_ultima_semana["speed_kmh"].apply(clasificar_velocidad)

@st.cache_resource
def load_kepler_config_trayectorias(hash_funcs={dict: lambda _: None}):
    with open("./data/config/trayectorias.json") as f:
        return json.load(f)

config_1 = load_kepler_config_trayectorias()

st.markdown("## Trayectorias")
st.markdown("### Trayectorias de la última semana")

kepler_map = KeplerGl(
    height=800,
    data={
        "Trayectorias ultima semana": df_ultima_semana
    },
    config=config_1
)
html_mapa_1 = kepler_map._repr_html_()
if isinstance(html_mapa_1, bytes):
    html_mapa_1 = html_mapa_1.decode("utf-8")

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
with st.container():
    components.html(hide_side_panel_css + html_mapa_1 + resize_fix, height=700, width=2000, scrolling=False)

# # ---------------------------
# # Mapa Kepler.gl
# # ---------------------------
# st.markdown("# Trayectorias")
# # HTML fix para forzar el redimensionamiento del mapa
# html_fix = """
# <script>
#   setTimeout(() => {
#     window.dispatchEvent(new Event('resize'));
#   }, 200);
# </script>
# """
# @st.cache_resource
# def load_html(filename):
#     with open(filename, "r", encoding="utf-8") as f:
#         return f.read()

# # Cargar el mapa Kepler
# html_content = load_html("./kepler_trayectorias.gl.html")

# # Inyectar el fix
# html_inyectado = html_content + html_fix

# # Mostrar en Streamlit
# components.html(html_inyectado, height=800, width=2000, scrolling=False)






# ---------------------------
# KPIs
# ---------------------------
df["date"] = df["received_at"].dt.date

# #Esto suma vehículos únicos por franja horaria entre todos los días, lo que puede contar un mismo vehículo más de una vez si apareció varios días en la misma franja.
# df_por_hora = df.groupby("hour_label")["station_id"].nunique().reset_index(name="vehículos") 
# df_por_hora_avg = df_por_hora.groupby("hour_label")["vehículos"].mean().round(1).reset_index()
# valor_pico = df_por_hora_avg["vehículos"].max()
# hora_pico = df_por_hora_avg[df_por_hora_avg["vehículos"] == valor_pico]["hour_label"].values[0]


# 1. Agrupar por fecha y franja horaria para contar vehículos únicos por día y franja
df_por_hora_dia = df.groupby(["date", "hour_label"])["station_id"].nunique().reset_index(name="vehículos")

# 2. Encontrar la franja horaria con mayor número de vehículos únicos
fila_pico = df_por_hora_dia.loc[df_por_hora_dia["vehículos"].idxmax()]
hora_pico = fila_pico["hour_label"]
fecha_pico = fila_pico["date"]
valor_pico = fila_pico["vehículos"]

# 3. Filtrar DataFrame original a ese pico (hora y fecha concretas)
df_hora_pico = df[(df["date"] == fecha_pico) & (df["hour_label"] == hora_pico)].copy()
# 4. Calcular KPIs sobre ese subconjunto:
vel_media = (
    df_hora_pico.groupby("station_id")["speed_kmh"]
    .mean()
    .mean()
    .round(1)
)

last_update = df["day"].max()


st.markdown("### KPIs de Tráfico Pico")
###<h3 style='margin: 0.25rem 0; font-size: 1.5rem'>{valor_pico} vehículos únicos </h3></div>""", unsafe_allow_html=True)

with st.container():
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""<div class='kpi-card' style='padding: 0.85rem; font-size: 0.85rem'>
        <p style='margin: 0.25rem 0'>Pico Diario</p>
        <h3 style='margin: 0.25rem 0; font-size: 1.5rem'>{valor_pico} vehículos únicos en la fecha {fecha_pico}</h3>""", unsafe_allow_html=True)

    with col2:
        st.markdown(f"""<div class='kpi-card' style='padding: 0.85; font-size: 0.85rem'>
        <p style='margin: 0.25rem 0'>Velocidad Media</p>
        <h3 style='margin: 0.25rem 0; font-size: 1.5rem'>{vel_media} km/h</h3></div>""", unsafe_allow_html=True)
    with col3:
        st.markdown(f"""<div class='kpi-card' style='padding: 0.85; font-size: 0.85rem'>
        <p style='margin: 0.25rem 0'>Hora Pico</p>
        <h3 style='margin: 0.25rem 0; font-size: 1.5rem'>{hora_pico}h</h3></div>""", unsafe_allow_html=True)
    with col4:
        st.markdown(f"""<div class='kpi-card' style='padding: 0.85; font-size: 0.85rem'>
        <p style='margin: 0.25rem 0'>Última actualización</p>
        <h3 style='margin: 0.25rem 0; font-size: 1.5rem'>{last_update}</h3></div>""", unsafe_allow_html=True)


st.markdown("## Intensidad de Tráfico")
st.markdown("### Análisis Global")

# ---------------------------
# Vehículos hora (mod)
# ---------------------------
frecuencias = {
    "30 minutos": "30T",
    "1 hora": "1H",
    "4 horas": "4H",
    "8 horas": "8H"
}

etiqueta = st.selectbox("Selecciona el período de agregación:", list(frecuencias.keys()))
periodo = frecuencias[etiqueta]


# Crear la columna de tramo horario sin fecha
df["tramo_horario"] = df["received_at"].dt.floor(periodo)
df["hora_label"] = df["tramo_horario"].dt.strftime("%H:%M")

# Agrupar ignorando la fecha
df_grouped = (
    df.groupby("hora_label")["station_id"]
    .nunique()
    .reset_index(name="vehículos")
)

# Ordenar cronológicamente
df_grouped["orden"] = pd.to_datetime(df_grouped["hora_label"], format="%H:%M").dt.hour * 60 + pd.to_datetime(df_grouped["hora_label"], format="%H:%M").dt.minute
df_grouped = df_grouped.sort_values("orden")

# Graficar
fig_bar = px.bar(
    df_grouped,
    x="hora_label",
    y="vehículos",
    color="vehículos",
    color_continuous_scale=px.colors.sequential.Viridis_r,
    labels={"hora_label": "Hora", "vehículos": "Nº vehículos únicos"},
    template="plotly_dark"
)
fig_bar.update_layout(height=400, margin=dict(t=50, b=20), coloraxis_showscale=False)

# ---------------------------
# Heatmap semanal
# ---------------------------
df_heatmap = df.groupby(["weekday_es", "hour_label"])["station_id"].nunique().reset_index(name="vehículos")

fig_heatmap = px.density_heatmap(
    df_heatmap,
    x="hour_label",
    y="weekday_es",
    z="vehículos",
    color_continuous_scale=px.colors.sequential.Inferno_r,
    labels={"vehículos": "Vehículos únicos", "hour_label": "Hora", "weekday_es": "Día de la semana"},
    template="plotly_dark",
    height=400
)
fig_heatmap.update_layout(
    title="",
    xaxis=dict(dtick=1),
    margin=dict(t=40, b=20),
    coloraxis_colorbar=dict(title="Vehículos únicos")
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




# ---------------------------
# LAYOUT - Análisis Global
# ---------------------------
col1, col2 = st.columns(2)
with col1:
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    st.markdown(f'<div class="chart-title">Vehículos hora ({etiqueta}) </div>', unsafe_allow_html=True)
    st.plotly_chart(fig_bar, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
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
st.markdown("## Análisis por Día de la Semana")
selected_day = st.selectbox("Selecciona un día", df["weekday_es"].cat.categories, key="select_dia_semana")

df_day = df[df["weekday_es"] == selected_day]
df_day["hour_label"] = df_day["hour"].apply(lambda h: f"{h:02d}:00")

# Vehículos por hora
df_day_vph = df_day.groupby("hour_label")["station_id"].nunique().reset_index(name="Vehículos únicos")
fig_day_vph = px.bar(df_day_vph, x="hour_label", y="Vehículos únicos",
                     color= "Vehículos únicos", color_continuous_scale=["#FED7AA", "#FB923C", "#EA580C"], 
                     template="plotly_dark", labels={"hour_label": "Hora del día", "Vehículos únicos": "Vehículos únicos"})

fig_day_vph.update_layout(
    height=400,
    margin=dict(t=50, b=20),
    coloraxis_showscale=True
)


# ---------------------------
# Tráfico por hora según el día (filtrado por día seleccionado)
# ---------------------------
# Agrupar por día y hora
df_dia_hora = df_day.groupby(["weekday_es", "hour_label"])["station_id"].nunique().reset_index(name="vehículos")
df_dia_hora["weekday_es"] = pd.Categorical(df_dia_hora["weekday_es"], categories=orden_dias, ordered=True)
df_dia_hora["hour_label"] = pd.Categorical(df_dia_hora["hour_label"], categories=[f"{h:02d}:00" for h in range(24)], ordered=True)

df_dia_hora_filtrado = df_dia_hora[df_dia_hora["weekday_es"] == selected_day]

fig_dia = px.line(
    df_dia_hora_filtrado.sort_values("hour_label"),
    x="hour_label",
    y="vehículos",
    line_shape="spline",
    markers=True,
    labels={
        "hour_label": "Hora del día",
        "vehículos": "Vehículos únicos"
    },
    template="plotly_dark"
)

fig_dia.update_traces(marker=dict(size=6), line=dict(width=2))
fig_dia.update_layout(
    height=400,
    margin=dict(t=50, b=20),
    xaxis=dict(tickmode="linear", tickangle=-45),
    yaxis=dict(title="Vehículos únicos")
)


# Frenada media
df_day_freno = df_day[df_day["longitudinal_acc"] < 0].copy()
df_day_freno["braking_intensity"] = -df_day_freno["longitudinal_acc"]
df_day_frenadas = df_day_freno.groupby("hour_label")["braking_intensity"].mean().reset_index()
fig_day_frenadas = px.area(df_day_frenadas, x="hour_label", y="braking_intensity",
                           title=f"Intensidad de frenada media por hora del dia - {selected_day}",
                           labels={"braking_intensity": "Intensidad frenada media (m/s²)"},
                           template="plotly_dark")

# ---------------------------
# LAYOUT - Día de la Semana
# ---------------------------
col5, col6 = st.columns(2)
with col5:
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    st.markdown(f'<div class="chart-title">Vehículos por hora - {selected_day}</div>', unsafe_allow_html=True)
    st.plotly_chart(fig_day_vph, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

with col6: 
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    st.markdown(f'<div class="chart-title">Tráfico por hora - {selected_day}</div>', unsafe_allow_html=True)
    st.plotly_chart(fig_dia, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)


# ---------------------------
# Patrones de Conducción
# ---------------------------
st.markdown("# Patrones de Conducción")
st.markdown("## Análisis Global")


#### Perfil de velocidad global
grupo_hora = df.groupby("hora_label")["speed_kmh"]
vel_mean = grupo_hora.mean()
vel_p25 = grupo_hora.quantile(0.25)
vel_p75 = grupo_hora.quantile(0.75)
n_vehiculos = df.groupby("hora_label")["station_id"].nunique()



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


# # Perfil de velocidad global -- antiguo
# grupo_hora = df.groupby("hour_label")["speed_kmh"]
# vel_mean = grupo_hora.mean()
# vel_p25 = grupo_hora.quantile(0.25)
# vel_p75 = grupo_hora.quantile(0.75)

# fig_vel = go.Figure()
# fig_vel.add_trace(go.Scatter(
#     x=vel_mean.index, y=vel_mean,
#     mode="lines+markers", name="Media",
#     line=dict(color="#007ACC", shape="spline", width=2),
#     marker=dict(symbol="circle", size=6)
# ))
# fig_vel.add_trace(go.Scatter(x=vel_mean.index, y=vel_p25, mode="lines", line=dict(width=0), showlegend=False))
# fig_vel.add_trace(go.Scatter(
#     x=vel_mean.index, y=vel_p75, mode="lines", fill="tonexty",
#     name="P25–P75", fillcolor="rgba(0, 122, 204, 0.2)", line=dict(width=0)
# ))
# fig_vel.update_layout(
#     xaxis_title="Hora del día", yaxis_title="Velocidad (km/h)",
#     template="plotly_dark", height=400, margin=dict(t=50, b=20),
#     xaxis=dict(tickmode="linear", dtick=1)
# )

# # Frenadas globales por hora
df_frenadas = df[df["longitudinal_acc"] < 0].copy()
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

##---------------------------------
##### Analisis por Día de la Semana #####

# Velocidad media por dia seleccionado
df_day_vel = df_day.groupby("hour_label")["speed_kmh"].mean().reset_index(name="Velocidad media (km/h)")

df_day_vel["hour_label"] = pd.Categorical(
    df_day_vel["hour_label"],
    categories=[f"{h:02d}:00" for h in range(24)],
    ordered=True
)
df_day_vel = df_day_vel.sort_values("hour_label")

fig_day_vel = px.line(
    df_day_vel,
    x="hour_label",
    y="Velocidad media (km/h)",
    markers=True,
    template="plotly_dark",
    line_shape="spline"
)

fig_day_vel.update_traces(
    line=dict(width=2, color="#7687E6"),
    marker=dict(size=4, color="#7687E6")
)

fig_day_vel.update_layout(
    height=400,
    margin=dict(t=50, b=20),
    xaxis_title="Hora del día",
    yaxis_title="Velocidad media (km/h)"
)


df_day_freno = df_day[df_day["longitudinal_acc"] < 0].copy()
df_day_freno["braking_intensity"] = -df_day_freno["longitudinal_acc"]

df_day_freno["hour_label"] = pd.Categorical(
    df_day_freno["hour_label"],
    categories=[f"{i:02d}:00" for i in range(24)],
    ordered=True
)

frenadas_dia_hora = df_day_freno.groupby("hour_label")["braking_intensity"].mean().reset_index()
frenadas_dia_hora = frenadas_dia_hora.sort_values("hour_label")

fig_day_freno = go.Figure()
fig_day_freno.add_trace(go.Scatter(
    x=frenadas_dia_hora["hour_label"],
    y=frenadas_dia_hora["braking_intensity"],
    mode="lines",
    fill="tozeroy",
    name="Frenada media",
    line=dict(color="#7F92C5", shape="spline", width=2),
    hovertemplate="Hora: %{x}<br>Frenada media: %{y:.2f} m/s²<extra></extra>"
))

fig_day_freno.update_layout(
    height=400,
    margin=dict(t=50, b=20),
    xaxis_title="Hora del día",
    yaxis_title="Frenada media (m/s²)",
    template="plotly_dark",
    xaxis=dict(
        tickmode="array",
        tickvals=[f"{i:02d}:00" for i in range(24)],
        ticktext=[f"{i:02d}:00" for i in range(24)]
    )
)

# ---------------------------
# LAYOUT - Patrones de Conducción
# ---------------------------

col7, col8 = st.columns(2)

with col7:
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    st.markdown(f'<div class="chart-title">Perfil de velocidades ({etiqueta})</div>', unsafe_allow_html=True)
    st.plotly_chart(fig_vel, use_container_width=True)

with col8:
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    st.markdown(f'<div class="chart-title">Intensidad frenada media por hora del dia</div>', unsafe_allow_html=True)
    st.plotly_chart(fig_freno, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)


st.markdown("## Análisis por Día de la Semana")


col9, col10 = st.columns(2)
with col9:
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    st.markdown(f'<div class="chart-title">Velocidad media por hora - {selected_day}</div>', unsafe_allow_html=True)
    st.plotly_chart(fig_day_vel, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)
with col10:
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    st.markdown(f'<div class="chart-title"> Intensidad de frenada media por hora del dia - {selected_day}</div>', unsafe_allow_html=True)
    st.plotly_chart(fig_day_freno, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)



# ---------------------------
# Informe Día Tipo
# ---------------------------

st.markdown("# Informe Día Tipo")

# 1. Selección de tramo físico
tramos_disponibles = df["name_osmid"].dropna().unique()
tramo_seleccionado = st.selectbox("Selecciona un tramo:", sorted(tramos_disponibles))
df_tramo = df[df["name_osmid"] == tramo_seleccionado].copy()
df_denm_tramo = df_denm[df_denm["station_id"].isin(df_tramo["station_id"].unique())].copy()

for _df in [df_tramo, df_denm_tramo]:
    _df["tramo_horario"] = _df["received_at"].dt.floor(periodo)
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

fig_intensidad_dia_tipo = px.bar(
    df_diatipo,
    x="hora_label", y="vehículos",
    labels={"hora_label": "Hora", "vehículos": "Vehículos únicos"},
    template="plotly_dark",
    color_discrete_sequence=["#3C7FFB"]
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

col13, col14 = st.columns(2)
with col13:
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    st.markdown(f'<div class="chart-title">Evento: {evento_seleccionado} - {selected_day} - Tramo {tramo_seleccionado}</div>', unsafe_allow_html=True)
    st.plotly_chart(fig_eventos, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)


#########################
m30_filtrado = m30[['osm_id', 'geometry']]
df_cam = df.merge(m30_filtrado, on="osm_id", how="left")

# 2. Filtrar solo las fclass válidas ANTES de calcular métricas
fclasses_validas = ['motorway', 'motorway_link', 'primary_link']
df_cam_filtrado = df_cam[df_cam["fclass"].isin(fclasses_validas)].copy()

df_cam_filtrado['received_at'] = pd.to_datetime(df_cam_filtrado['received_at'])
df_cam_filtrado['fecha'] = df_cam_filtrado['received_at']



df_global = df_cam_filtrado.groupby(['station_id', 'osm_id', 'hour', 'weekday_es']).agg({
    'speed_kmh': 'mean',
    'longitudinal_acc': 'mean',
    'lateral_acc': 'mean',
    'lanes': 'first',
    'fecha': 'first'
}).reset_index()

# Paso 2: Agregar métricas por osm_id, hour y weekday
metricas_2 = (
    df_global
    .groupby(['osm_id', 'hour', 'weekday_es'])
    .agg({
        'station_id': 'nunique',
        'speed_kmh': ['mean', 'max', 'min', 'std',
                      lambda x: x.quantile(0.25),
                      lambda x: x.quantile(0.75)],
        'longitudinal_acc': ['mean', 'max', 'min'],
        'lateral_acc': ['mean', 'max'],
        'lanes': 'first',
        'fecha': 'first'  
    })
)

# Renombrar columnas
metricas_2.columns = [
    'conteo_vehiculos',
    'speed_mean', 'speed_max', 'speed_min', 'speed_std',
    'speed_q25', 'speed_q75',
    'long_acc_mean', 'long_acc_max', 'long_acc_min',
    'lat_acc_mean', 'lat_acc_max',
    'lanes',
    'fecha'
]

# Restaurar índice como columnas
metricas_2.reset_index(inplace=True)

# Crear hour_label como "08:00"
metricas_2['hour_label'] = metricas_2['hour'].apply(lambda x: f"{int(x):02d}:00")
df_velocidades = metricas_2.merge(
    m30[['osm_id', 'geometry', 'name', 'maxspeed','fclass', 'ref']],
    on='osm_id',
    how='left'
)
gdf_velocidades = gpd.GeoDataFrame(df_velocidades, geometry='geometry', crs=m30.crs)

gdf_velocidades["fecha_kepler"] = pd.to_datetime("2025-06-19 " + metricas_2["hour_label"])


gdf_velocidades["velocidad_rango"] = gdf_velocidades["speed_mean"].apply(clasificar_velocidad)


### -------------------------------
### MAPA 2
st.markdown("# Mapa de Velocidades por Tramo historico")

@st.cache_resource
def load_kepler_config_velocidades(hash_funcs={dict: lambda _: None}):
    with open("./data/config/velocidades_tramos.json") as f:
        return json.load(f)

config_2 = load_kepler_config_velocidades()


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