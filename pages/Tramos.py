import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
from datetime import datetime
import geopandas as gpd
from sqlalchemy import create_engine
from shapely.geometry import Point
from keplergl import KeplerGl
import json




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
### M30
@st.cache_resource
def load_shapefile():
    gdf = gpd.read_file("data/m30_osm_v3.shp")
    return gdf.to_crs(epsg=25830)

m30 = load_shapefile()


### CAM y DENM
def load_data():
    # Conexión a la base de datos
    db_url = st.secrets["db_url"]
    engine = create_engine(db_url)

    df = pd.read_sql("SELECT * FROM cam_ref_message", engine)
    df = df.drop(columns=['lanes'])

    df["received_at"] = pd.to_datetime(df["received_at"])
    if "weekday_es" in df.columns:
        df["weekday_es"] = pd.Categorical(
            df["weekday_es"],
            categories=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"],
            ordered=True
        )
    if "hour" in df.columns and "hour_label" not in df.columns:
        df["hour_label"] = df["hour"].apply(lambda x: f"{int(x):02d}:00")

    df = df.sort_values(by='received_at', ascending=False)
    df = df.reset_index(drop=True)
    
    return df

df_cam = load_data()

st.title("Tramos M30")
st.markdown("#### Niveles de servicio de la M30 en la última hora")

m30_lineas = m30[["osm_id", "geometry", "lanes"]]
df_cam = df_cam.merge(m30_lineas, on="osm_id", how="left")

# 2. Filtrar solo las fclass válidas ANTES de calcular métricas
fclasses_validas = ['motorway', 'motorway_link', 'primary_link']
df_cam_filtrado = df_cam[df_cam["fclass"].isin(fclasses_validas)].copy()

df_cam_filtrado['received_at'] = pd.to_datetime(df_cam_filtrado['received_at'])
df_cam_filtrado['fecha'] = df_cam_filtrado['received_at']

ultima_hora = df_cam_filtrado['received_at'].max()
inicio_ultima_hora = ultima_hora - pd.Timedelta(hours=1)

df_ultima_hora = df_cam_filtrado[
    (df_cam_filtrado['received_at'] > inicio_ultima_hora)
].copy()


# Evitar hacer el drop duplicates y agregamos por vehiculo en osmid
#si quiero hacer global (por hora y dia tipo) --> meterlo en el groupby
df_evitar = df_ultima_hora.groupby(['station_id','osm_id']).agg({'speed_kmh': 'mean',
        'longitudinal_acc':'mean',
        'lateral_acc': 'mean',
        'lanes': 'first',
        'fecha': 'first'}).reset_index()

# 3. Agregar métricas por osm_id (vehículos únicos por tramo)
metricas = (
    df_evitar
    .groupby('osm_id')
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

# 4. Renombrar columnas
metricas.columns = [
    'conteo_vehiculos',
    'speed_mean', 'speed_max', 'speed_min', 'speed_std',
    'speed_q25', 'speed_q75',
    'long_acc_mean', 'long_acc_max', 'long_acc_min',
    'lat_acc_mean', 'lat_acc_max',
    'lanes','fecha'
]
metricas = metricas.sort_values(by='fecha')
metricas.reset_index(inplace=True)


gdf_tramos = metricas.merge(
    m30[['osm_id', 'geometry', 'name', 'maxspeed','fclass', 'ref']],
    on='osm_id',
    how='left'
)
gdf_tramos = gpd.GeoDataFrame(gdf_tramos, geometry='geometry', crs=m30.crs)


# 1. Aseguramos que la geometría esté proyectada en metros
if gdf_tramos.crs.is_geographic:
    gdf_tramos = gdf_tramos.to_crs(epsg=25830)  # UTM Zona 30N para Madrid

gdf_tramos["lanes"] = pd.to_numeric(gdf_tramos["lanes"], errors="coerce")

# 2. Calcular longitud del tramo en km
gdf_tramos["longitud_km"] = gdf_tramos.geometry.length / 1000

# 3. Calcular densidad (vehículos ligeros equivalentes por km y carril)
gdf_tramos["densidad"] = gdf_tramos["conteo_vehiculos"] / (gdf_tramos["longitud_km"] * gdf_tramos["lanes"])

# 4. Asignar nivel de servicio según NS 5.2-IC
def nivel_servicio_ns(densidad):
    if pd.isna(densidad):
        return None
    if densidad <= 7:
        return "A"
    elif densidad <= 11:
        return "B"
    elif densidad <= 16:
        return "C"
    elif densidad <= 22:
        return "D"
    elif densidad <= 28:
        return "E"
    else:
        return "F"

gdf_tramos["nivel_servicio"] = gdf_tramos["densidad"].apply(nivel_servicio_ns)
gdf_tramos = gdf_tramos.to_crs(epsg=4326)





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