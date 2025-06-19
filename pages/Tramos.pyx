import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
from datetime import datetime
import geopandas as gpd
from sqlalchemy import create_engine
from shapely.geometry import Point
from keplergl import KeplerGl
import json
from utils.shared_data import load_data_cam
from utils.metrics_calculator import calculate_metrics_osmid, calculate_velocity_metrics
from utils.create_map_kepler import show_kepler_map
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)


# Configuración de página
st.set_page_config(
    page_title="Tramos", 
    layout="wide",
    initial_sidebar_state="collapsed",
    page_icon="🚦"
)

# Cargar CSS personalizado
def load_custom_css(path="./style_dark_tramos.css"):
    with open(path, encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# load_custom_css()

# ---------------------------
# Cargar datos
# ---------------------------

df_cam = load_data_cam()


# ---------------------------
# Calcular métricas
# ---------------------------
with st.spinner("Calculando métricas de tráfico..."):
    # Métricas principales (para el mapa)
    gdf_tramos = calculate_metrics_osmid(df_cam)
    
    # Métricas de velocidad (para gráficos adicionales)
    gdf_velocidades = calculate_velocity_metrics(df_cam)



st.title("Tramos M30")
# -------------------------------
# VISUALIZAR EN KEPLERGL
# -------------------------------
def load_kepler_config(hash_funcs={dict: lambda _: None}):
    """Carga la configuración de KeplerGL desde un archivo JSON"""
    with open("./data/config/niveles_servicio_ok.json", encoding='utf-8') as f:
        return json.load(f)
    
config = load_kepler_config()

show_kepler_map(
    gdf=gdf_tramos,
    config=config,
    height=900,
    display_height=800,
    layer_name="Tramos M30"  # Nombre de la capa principal
)
