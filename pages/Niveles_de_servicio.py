import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
from datetime import datetime
import geopandas as gpd
from sqlalchemy import create_engine
from shapely.geometry import Point
from keplergl import KeplerGl
import json
from utils.loaders import load_data, load_m30_data
import psutil
import os



st.set_page_config(
    page_title="Dashboard de Tráfico V2X", 
    layout="wide", 
    initial_sidebar_state="collapsed",
    page_icon="🚗"
)




def load_custom_css(path="./style_dark_demanda.css"):
    with open(path, encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_custom_css()

# Función para monitorear memoria (opcional)
def show_memory_usage():
    """Muestra el uso de memoria actual"""
    try:
        process = psutil.Process(os.getpid())
        memory_mb = process.memory_info().rss / 1024 / 1024
        return f"{memory_mb:.1f} MB"
    except:
        return "N/A"

# ===== HEADER =====
st.markdown("""
<div class="main-title">
    DASHBOARD DE DATOS DE TRÁFICO V2X
</div>
<div style="text-align: center; color: #cbd5e1; font-size: 1.1rem; margin-bottom: 2rem;">
    Niveles de servicio
</div>
""", unsafe_allow_html=True)

st.markdown('<h3 class="section-title">  Mapa de niveles de servicio en la última hora</h3>', unsafe_allow_html=True)


# Mostrar uso de memoria en sidebar (opcional)
with st.sidebar:
    st.metric("Memoria en uso", show_memory_usage())

# ---------------------------
# Cargar datos
# ---------------------------

#m30 = load_m30_data()


#df_cam,df_denm = load_data()


#### Mapa dinamico de eventos DENM
st.markdown("""
    <div class="map-container">
        <p class="map-title">Niveles de servicio de la M30 en la última hora</p>
    </div>
""", unsafe_allow_html=True)


gdf_tramos = gpd.read_file("./data/gdf_tramos.geojson")


# -------------------------------
# VISUALIZAR EN KEPLERGL
# -------------------------------

@st.cache_resource
def load_kepler_config_tramos(hash_funcs={dict: lambda _: None}):
    with open("./data/config/niveles_servicio_ok.json") as f:
        return json.load(f)

config = load_kepler_config_tramos()


# ---------------------------
# if st.button("Recargar datos", key="reload_btn"):
#     # Limpiar solo lo necesario (no todo)
#     load_data.clear()         # Solo los datos tabulares
#     load_kepler_config_tramos.clear() # Solo la configuración
#     st.rerun()



kepler_map = KeplerGl(
    height=800,
    data={
        "Tramos M30": gdf_tramos
    },
    config=config
)

html_mapa = kepler_map._repr_html_()
if isinstance(html_mapa, bytes):
    html_mapa = html_mapa.decode("utf-8")

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

# Mostrar el mapa en Streamlit
components.html(hide_side_panel_css + html_mapa + resize_fix, height=700, width=2000, scrolling=False)




# # ---------------------------
# # Velocidades 
# # ---------------------------
# # Paso 1: Agregación intermedia por vehículo, tramo, hora y día
# df_global = df_cam_filtrado.groupby(['station_id', 'osm_id', 'hour', 'weekday_es']).agg({
#     'speed_kmh': 'mean',
#     'longitudinal_acc': 'mean',
#     'lateral_acc': 'mean',
#     'lanes': 'first',
#     'fecha': 'first'
# }).reset_index()

# # Paso 2: Agregar métricas por osm_id, hour y weekday
# metricas_2 = (
#     df_global
#     .groupby(['osm_id', 'hour', 'weekday_es'])
#     .agg({
#         'station_id': 'nunique',
#         'speed_kmh': ['mean', 'max', 'min', 'std',
#                       lambda x: x.quantile(0.25),
#                       lambda x: x.quantile(0.75)],
#         'longitudinal_acc': ['mean', 'max', 'min'],
#         'lateral_acc': ['mean', 'max'],
#         'lanes': 'first',
#         'fecha': 'first'  
#     })
# )

# # Renombrar columnas
# metricas_2.columns = [
#     'conteo_vehiculos',
#     'speed_mean', 'speed_max', 'speed_min', 'speed_std',
#     'speed_q25', 'speed_q75',
#     'long_acc_mean', 'long_acc_max', 'long_acc_min',
#     'lat_acc_mean', 'lat_acc_max',
#     'lanes',
#     'fecha'
# ]

# # Restaurar índice como columnas
# metricas_2.reset_index(inplace=True)

# # Crear hour_label como "08:00"
# metricas_2['hour_label'] = metricas_2['hour'].apply(lambda x: f"{int(x):02d}:00")
# df_velocidades = metricas_2.merge(
#     m30[['osm_id', 'geometry', 'name', 'maxspeed','fclass', 'ref']],
#     on='osm_id',
#     how='left'
# )
# gdf_velocidades = gpd.GeoDataFrame(df_velocidades, geometry='geometry', crs=m30.crs)

# gdf_velocidades["fecha_kepler"] = pd.to_datetime("2025-06-19 " + metricas_2["hour_label"])


# def clasificar_velocidad(v):
#     if v <= 30:
#         return "0–30 km/h"
#     elif v <= 50:
#         return "30–50 km/h"
#     elif v <= 70:
#         return "50–70 km/h"
#     else:
#         return "70-90+ km/h"

# gdf_velocidades["velocidad_rango"] = gdf_velocidades["speed_mean"].apply(clasificar_velocidad)


# ### -------------------------------
# ### MAPA 2


# @st.cache_resource
# def load_kepler_config_velocidades(hash_funcs={dict: lambda _: None}):
#     with open("./data/config/velocidades_tramos.json") as f:
#         return json.load(f)

# config_2 = load_kepler_config_velocidades()


# kepler_map = KeplerGl(
#     height=800,
#     data={
#         "Velocidad tramos historico": gdf_velocidades
#     },
#     config=config_2
# )



# html_mapa_2 = kepler_map._repr_html_()
# if isinstance(html_mapa_2, bytes):
#     html_mapa_2 = html_mapa_2.decode("utf-8")

# #CSS y resize fix
# hide_side_panel_css = """
# <style>
# div[class*="side-bar__close"] {
#     display: none !important;
# }
# </style>
# """

# resize_fix = """
# <script>
#   setTimeout(() => {
#     window.dispatchEvent(new Event('resize'));
#   }, 300);
# </script>
# """

# # # Mostrar el mapa en Streamlit
# # components.html(hide_side_panel_css + html_mapa_2 + resize_fix, height=700, width=2000, scrolling=False)



# with st.container():
#     components.html(hide_side_panel_css + html_mapa + resize_fix, height=700, width=2000, scrolling=False)


# st.markdown("""Velocidades medias históricas de los tramos de la M30""")

# with st.container():
#     components.html(hide_side_panel_css + html_mapa_2 + resize_fix, height=700, width=2000, scrolling=False)