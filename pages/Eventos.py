import streamlit as st
import pandas as pd
import plotly.express as px
import streamlit.components.v1 as components
from datetime import datetime
from streamlit_plotly_events import plotly_events
from sqlalchemy import create_engine
import json
from keplergl import KeplerGl
from streamlit_keplergl import keplergl_static
import geopandas as gpd
from shapely.geometry import Point


# Configuración
st.set_page_config(page_title="Eventos DENM - M30", layout="wide",
    initial_sidebar_state="collapsed",
    page_icon="🚦")

def load_custom_css(path="./style_dark_eventos.css"):
    with open(path, encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_custom_css()

st.title("Eventos DENM")




# ----------- Cargar datos -----------

@st.cache_data
def load_data():
    # Conexión a la base de datos
    db_url = st.secrets["db_url"]
    engine = create_engine(db_url)

    df = pd.read_sql("SELECT * FROM denm_ref_message", engine)

    df["received_at"] = pd.to_datetime(df["received_at"])
    if "weekday_es" in df.columns:
        df["weekday_es"] = pd.Categorical(
            df["weekday_es"],
            categories=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"],
            ordered=True
        )
    if "hour" in df.columns and "hour_label" not in df.columns:
        df["hour_label"] = df["hour"].apply(lambda x: f"{int(x):02d}:00")

    df["geometry"] = df.apply(lambda row: Point(row["longitude"], row["latitude"]), axis=1)
    gdf = gpd.GeoDataFrame(df, geometry="geometry", crs="EPSG:4326")
    return df, gdf

df_denm, gdf  = load_data()
orden_dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


@st.cache_resource
def load_shapefile():
    gdf = gpd.read_file("data/m30_osm_v3.shp")
    return gdf.to_crs(epsg=25830)

m30 = load_shapefile()


@st.cache_resource
def load_kepler_config(hash_funcs={dict: lambda _: None}):
    with open("data/config/eventos_denm.json") as f:
        return json.load(f)

config = load_kepler_config()
# if st.button("Recargar config"):
#     load_kepler_config.clear()
#     st.rerun()


# ---------------------------
if st.button("Recargar datos", key="reload_btn"):
    # Limpiar solo lo necesario (no todo)
    load_data.clear()         # Solo los datos tabulares
    load_kepler_config.clear() # Solo la configuración
    st.rerun()

#### Mapa dinamico de eventos DENM
st.markdown("## Mapa de Eventos DENM ")
st.markdown("""
    <div class="map-container">
        <p class="map-title">Eventos DENM en la última semana</p>
    </div>
""", unsafe_allow_html=True)

# Asegúrate de que la columna 'received_at' es datetime
df_denm["received_at"] = pd.to_datetime(df_denm["received_at"])

hoy = pd.Timestamp.now().normalize()
una_semana_atras = hoy - pd.Timedelta(days=7)
df_semanal = df_denm[df_denm["received_at"] >= una_semana_atras].copy()

#### MAPA KEPLER
kepler_map = KeplerGl(height=800, data={"Eventos DENM": df_semanal}, config=config)
html_mapa = kepler_map._repr_html_()
if isinstance(html_mapa, bytes):
    html_mapa = html_mapa.decode("utf-8")


# -------------------------
# 4. Inyectar CSS para ocultar el side panel de Kepler
# -------------------------
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

# Mostrar en Streamlit
components.html(hide_side_panel_css + html_mapa + resize_fix, height=700, width=2000, scrolling=False)



## ---------------------------
# Gráficos de causas y subcausas
# ---------------------------
st.markdown("## Causas y subcausas de los eventos DENM")

# Crear dos columnas
col1, col2 = st.columns(2)

df_causas = df_denm["cause_desc"].value_counts().reset_index()
df_causas.columns = ["cause_desc", "frecuencia"]

with col1:
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    st.markdown('<div class="chart-title">Distribución de Causas</div>', unsafe_allow_html=True)
    st.markdown('<div class="select-container">', unsafe_allow_html=True)
    causa_seleccionada = st.selectbox("", options=df_causas["cause_desc"], key="select_causa")
    st.markdown('</div>', unsafe_allow_html=True)

    fig_causa = px.pie(
        df_causas,
        values="frecuencia",
        names="cause_desc",
        color_discrete_sequence=px.colors.qualitative.Set3,
        template="plotly_dark"
    )
    fig_causa.update_layout(height=400, margin=dict(t=50, b=20))

    st.plotly_chart(fig_causa, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    st.markdown(f'<div class="chart-title"> Subcausa de - {causa_seleccionada}</div>', unsafe_allow_html=True)
    st.markdown('<div class="chart-title"></div>', unsafe_allow_html=True)
    st.markdown('<div class="chart-title"></div>', unsafe_allow_html=True)
    st.markdown('<div class="chart-title"></div>', unsafe_allow_html=True)
    st.markdown('<div class="chart-title"></div>', unsafe_allow_html=True)
    st.markdown('<div class="chart-title"></div>', unsafe_allow_html=True)
    st.markdown('<div class="chart-title"></div>', unsafe_allow_html=True)
    st.markdown('<div class="chart-title"></div>', unsafe_allow_html=True)
    df_subcausas = df_denm[df_denm["cause_desc"] == causa_seleccionada]
    subcausas_counts = df_subcausas["subcause_desc"].value_counts().reset_index()
    subcausas_counts.columns = ["subcause_desc", "frecuencia"]
    
    if not subcausas_counts.empty:
        fig_subcausa = px.pie(
            subcausas_counts,
            values="frecuencia",
            names="subcause_desc",
            color_discrete_sequence=px.colors.qualitative.Set2,
            template="plotly_dark"
        )
        fig_subcausa.update_layout(height=400, margin=dict(t=50, b=20))
        st.plotly_chart(fig_subcausa, use_container_width=True)
    else:
        st.warning(f"No hay subcausas registradas para: {causa_seleccionada}")






# ---------------------------
# Eventos por hora según tipo de causa
# ---------------------------
st.markdown("## Tipos de evento por hora")

# Crear un DataFrame con todas las horas posibles
horas_completas = pd.DataFrame({'hour': range(24)})
horas_completas['hour_label'] = horas_completas['hour'].apply(lambda x: f"{x:02d}:00")
tipos_evento = df_denm["cause_desc"].dropna().unique()
tipos_evento_sorted = sorted(tipos_evento)

# Filtrar y contar eventos
df_filtrado = df_denm[df_denm["cause_desc"] == causa_seleccionada]
eventos_por_hora = df_filtrado.groupby("hour").size().reset_index(name="Número de eventos")
eventos_completos = horas_completas.merge(
    eventos_por_hora, 
    on='hour', 
    how='left'
).fillna(0)

eventos_completos = eventos_completos.sort_values("hour")

# Gráfico de barras mejorado
fig_barras = px.bar(
    eventos_completos,
    x="hour_label",
    y="Número de eventos",
    labels={"hour_label": "Hora del día", "Número de eventos": "Eventos"},
    template="plotly_dark",
    color_discrete_sequence=["#D49161"]
)

# Configuración del eje X para mostrar todas las horas
fig_barras.update_layout(
    xaxis=dict(
        type='category',
        categoryorder='array',
        categoryarray=horas_completas['hour_label'].tolist(), 
        tickmode='array',
        tickvals=horas_completas['hour_label'].tolist(),
        tickangle=45 
    ),
    height=400,
    margin=dict(t=50, b=100) 
)

# Renderizado
st.plotly_chart(fig_barras, use_container_width=True)