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

# Configuración de página
st.set_page_config(
    page_title="Dashboard de Tráfico V2X", 
    layout="wide", 
    initial_sidebar_state="collapsed",
    page_icon="🚗"
)

def load_custom_css(path="./style_dark_demanda.css"):
    """Carga CSS personalizado para el dashboard"""
    try:
        with open(path, encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning(f"No se pudo cargar el archivo CSS: {path}")

def clasificar_velocidad(v):
    """Clasifica la velocidad en rangos"""
    if v <= 30:
        return "0–30 km/h"
    elif v <= 50:
        return "30–50 km/h"
    elif v <= 70:
        return "50–70 km/h"
    else:
        return "70-90+ km/h"

@st.cache_resource
def load_kepler_config_trayectorias(hash_funcs={dict: lambda _: None}):
    """Carga configuración de Kepler.gl"""
    try:
        with open("./data/config/trayectorias.json") as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("No se pudo cargar la configuración del mapa")
        return {}

# Cargar estilos
load_custom_css("./style_dark_demanda.css")

# Cargar datos
try:
    df, df_denm = load_data()
    m30 = load_m30_data()
except Exception as e:
    st.error(f"Error al cargar los datos: {str(e)}")
    st.stop()

# Configuraciones
orden_dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
config_1 = load_kepler_config_trayectorias()

# Procesamiento de datos
df['received_at'] = pd.to_datetime(df['received_at'])
hoy = pd.Timestamp.today().normalize()
hace_una_semana = hoy - pd.Timedelta(days=7)

# Filtrado
df_ultima_semana = df[df['received_at'] >= hace_una_semana].copy()
fclasses_validas = ['motorway', 'motorway_link', 'primary_link']
df_cam_filtrado = df_ultima_semana[df_ultima_semana["fclass"].isin(fclasses_validas)].copy()
df_ultima_semana["velocidad_rango"] = df_ultima_semana["speed_kmh"].apply(clasificar_velocidad)
df_ultima_semana["date"] = df_ultima_semana["received_at"].dt.date

# ===== HEADER =====
st.markdown("""
<div class="main-title">
    DASHBOARD DE DATOS DE TRÁFICO V2X
</div>
<div style="text-align: center; color: #cbd5e1; font-size: 1.1rem; margin-bottom: 2rem;">
    Datos en tiempo real de la RSU instalada en M30
</div>
""", unsafe_allow_html=True)

# ===== CÁLCULO DE KPIS =====
last_update = df_ultima_semana["date"].max()
last_update2 = df_ultima_semana["day"].max()
total_ultimo_dia = df_ultima_semana[df_ultima_semana["day"] == last_update2]["station_id"].nunique()
total_semana = df_ultima_semana["station_id"].nunique()

# Hora pico
df_por_hora_dia = df_ultima_semana.groupby(["date", "hour_label"])["station_id"].nunique().reset_index(name="vehículos")
fila_pico = df_por_hora_dia.loc[df_por_hora_dia["vehículos"].idxmax()]
hora_pico = fila_pico["hour_label"]
fecha_pico = fila_pico["date"]
valor_pico = fila_pico["vehículos"]

# Velocidades
velocidad_media_semana = df_ultima_semana["speed_kmh"].mean()
df_hora_pico = df_ultima_semana[
    (df_ultima_semana["hour_label"] == hora_pico) & 
    (df_ultima_semana["date"] == fecha_pico)
]
velocidad_media_pico = df_hora_pico["speed_kmh"].mean()

# ===== SECCIÓN DE KPIS =====
st.markdown('<h3 class="section-title">  KPIs de la Última Semana</h3>', unsafe_allow_html=True)

# Primera fila de métricas
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Última Actualización", 
        str(last_update),
        help="Fecha del último registro de datos"
    )

with col2:
    st.metric(
        "Vehículos Último Día", 
        f"{total_ultimo_dia:,}",
        help="Vehículos únicos detectados en el último día"
    )

with col3:
    st.metric(
        "Vehículos Última Semana", 
        f"{total_semana:,}",
        help="Total de vehículos únicos en los últimos 7 días"
    )

with col4:
    # Calcular vehículos promedio por día
    vehiculos_promedio_dia = total_semana / 7
    st.metric(
        "Promedio Vehículps Diario", 
        f"{vehiculos_promedio_dia:.0f}",
        help="Promedio de vehículos únicos por día"
    )


# Segunda fila de métricas
col5, col6, col7, col8 = st.columns(4)

with col5:
    st.metric(
        "Hora con Más Tráfico",
        f"{valor_pico} vehículos",
        help=f"Registrado el {fecha_pico} a las {hora_pico}"
    )

with col6:
    st.metric(
        "Velocidad Media Semana", 
        f"{velocidad_media_semana:.1f} km/h",
        help="Velocidad promedio de todos los vehículos"
    )

with col7:
    st.metric(
        "Velocidad Hora Pico", 
        f"{velocidad_media_pico:.1f} km/h",
        f"{(velocidad_media_pico - velocidad_media_semana):.1f} km/h",
        help="Velocidad promedio durante la hora de mayor tráfico"
    )


with col8:
    rango_mas_comun = df_ultima_semana["velocidad_rango"].mode().iloc[0] if not df_ultima_semana["velocidad_rango"].mode().empty else "N/A"
    print(rango_mas_comun)
    st.metric(
        "Rango Más Común", 
        rango_mas_comun,
        help="Rango de velocidad más frecuente"
    )

# ===== GRÁFICO DE PERFIL DE TRÁFICO =====
st.markdown('<h3 class="section-title">  Perfil de Tráfico</h3>', unsafe_allow_html=True)

# Preparar datos para el gráfico
df_por_hora_dia["date"] = pd.to_datetime(df_por_hora_dia["date"])
df_por_hora_dia["datetime"] = pd.to_datetime(
    df_por_hora_dia["date"].astype(str) + " " + df_por_hora_dia["hour_label"]
)

# Crear gráfico mejorado
fig = px.line(
    df_por_hora_dia,
    x="datetime",
    y="vehículos",
    title="Evolución del Tráfico por Día y Hora",
    labels={"datetime": "Fecha y Hora", "vehículos": "Número de Vehículos"},
    markers=True,
    line_shape="spline"
)

# Personalizar el gráfico
fig.update_layout(
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

fig.update_traces(
    line_color='#3b82f6',
    marker_color='#3b82f6',
    marker_size=4,
    line_width=2
)

st.plotly_chart(fig, use_container_width=True)

# ===== GRÁFICO DE DISTRIBUCIÓN DE VELOCIDADES =====
st.markdown('<h3 class="section-title">  Distribución de Velocidades</h3>', unsafe_allow_html=True)

def crear_bins_velocidad(velocidad):
    """Crea bins de velocidad de 5 en 5 km/h"""
    if pd.isna(velocidad):
        return "Sin datos"
    
    # Redondear hacia abajo al múltiplo de 5 más cercano
    bin_start = int(velocidad // 5) * 5
    bin_end = bin_start + 5
    
    # Limitar el rango máximo
    if bin_start >= 100:
        return "100+ km/h"
    
    return f"{bin_start}-{bin_end} km/h"

# Agregar bins de velocidad al dataframe
df_ultima_semana["velocidad_bins"] = df_ultima_semana["speed_kmh"].apply(crear_bins_velocidad)

# Crear selector de hora
col_hora, col_info = st.columns([3, 1])

with col_hora:
    # Obtener las horas únicas disponibles
    horas_disponibles = sorted(df_ultima_semana["hour_label"].unique())
    horas_opciones = ["Todas las horas"] + horas_disponibles
    
    hora_seleccionada = st.selectbox(
        "Selecciona la hora:",
        options=horas_opciones,
        index=0,
        help="Filtra la distribución por hora específica"
    )

#with col_info:
#    st.markdown("""
#    <div style="padding: 10px; background: rgba(59, 130, 246, 0.1); border-radius: 8px; margin-top: 25px;">
#        <small style="color: #93c5fd;">
#        Valores en %<br>
#        Filtrable por hora
#        </small>
#    </div>
#    """, unsafe_allow_html=True)

# Filtrar datos según la hora seleccionada
if hora_seleccionada == "Todas las horas":
    df_filtrado = df_ultima_semana.copy()
    titulo_hora = "todas las horas"
else:
    df_filtrado = df_ultima_semana[df_ultima_semana["hour_label"] == hora_seleccionada].copy()
    titulo_hora = f"las {hora_seleccionada}"

# Verificar que hay datos
if df_filtrado.empty:
    st.warning(f"No hay datos disponibles para {titulo_hora}")
else:
    # Contar vehículos por bin de velocidad y convertir a porcentajes
    velocidad_counts = df_filtrado["velocidad_bins"].value_counts()
    total_vehiculos = len(df_filtrado)
    velocidad_percentages = (velocidad_counts / total_vehiculos * 100).round(1)
    
    # Ordenar los bins correctamente
    orden_bins = []
    for i in range(0, 105, 5):
        if i >= 100:
            bin_name = "100+ km/h"
        else:
            bin_name = f"{i}-{i+5} km/h"
        if bin_name in velocidad_percentages.index:
            orden_bins.append(bin_name)
    
    # Reordenar según el orden lógico
    velocidad_percentages = velocidad_percentages.reindex(orden_bins).fillna(0)
    
    # Crear dos columnas para mostrar estadísticas y gráfico
    col_grafico, col_stats = st.columns([3, 1])
    
    with col_grafico:
        # Crear gráfico de barras con porcentajes
        fig_velocidad = px.bar(
            x=velocidad_percentages.index,
            y=velocidad_percentages.values,
            title=f"Distribución de Velocidades - {titulo_hora.title()}",
            labels={"x": "Rango de Velocidad (km/h)", "y": "Porcentaje de Vehículos (%)"},
            color=velocidad_percentages.values,
            color_continuous_scale="plasma",
            text=[f"{val:.1f}%" for val in velocidad_percentages.values]
        )
        
        # Personalizar el gráfico
        fig_velocidad.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font_color='#f8fafc',
            title_font_size=16,
            title_font_color='#f8fafc',
            xaxis=dict(
                gridcolor='#475569', 
                showgrid=True,
                tickangle=45
            ),
            yaxis=dict(
                gridcolor='#475569', 
                showgrid=True
            ),
            showlegend=False,
            margin=dict(b=100)  
        )
        
        # Personalizar las barras y texto
        fig_velocidad.update_traces(
            texttemplate='%{text}',
            textposition='outside',
            textfont_color='#f8fafc',
            textfont_size=10
        )
        
        st.plotly_chart(fig_velocidad, use_container_width=True)
    
    with col_stats:
        # Mostrar estadísticas
        # st.markdown("### Estadísticas")
        
        # Calcular estadísticas
        velocidad_media = df_filtrado["speed_kmh"].mean()
        velocidad_v85 = df_filtrado["speed_kmh"].quantile(0.85)

        
        # Encontrar el bin más común
        bin_mas_comun = velocidad_percentages.idxmax()
        porcentaje_bin_comun = velocidad_percentages.max()
        
        # Mostrar métricas en formato card
        st.markdown(f"""

        <div style="padding: 15px; border-radius: 10px; margin-bottom: 10px;">
            <strong>Velocidad Media:</strong><br>
            <span style="font-size: 1.5em; ">{velocidad_media:.1f} km/h</span>
        </div>
        
        <div style="padding: 15px; border-radius: 10px; margin-bottom: 10px;">
            <strong>V85:</strong><br>
            <span style="font-size: 1.5em; ">{velocidad_v85:.1f} km/h</span>
        </div>
        

        """, unsafe_allow_html=True)

# Mostrar tabla resumen expandible
with st.expander("Ver tabla detallada de distribución", expanded=False):
    if not df_filtrado.empty:
        # Crear DataFrame para la tabla
        tabla_resumen = pd.DataFrame({
            'Rango de Velocidad': velocidad_percentages.index,
            'Porcentaje (%)': velocidad_percentages.values
         })
        
        # Agregar columna de porcentaje acumulado
        tabla_resumen['Porcentaje Acumulado (%)'] = tabla_resumen['Porcentaje (%)'].cumsum().round(1)
        
        st.dataframe(
            tabla_resumen,
            use_container_width=True,
            hide_index=True
        )
        
        # Botón para descargar datos
        csv = tabla_resumen.to_csv(index=False)
        st.download_button(
            label="📥 Descargar datos como CSV",
            data=csv,
            file_name=f'distribucion_velocidades_{hora_seleccionada.replace(":", "_")}.csv',
            mime='text/csv'
        )

# ===== MAPA DE TRAYECTORIAS =====
st.markdown('<h3 class="section-title">  Trayectorias y Velocidad de Vehículos</h3>', unsafe_allow_html=True)

with st.container():
    st.info("El mapa muestra las trayectorias de los vehículos detectados en la última semana con códigos de color según la velocidad.")
    
    def sample_station_group(group):
        n_total = len(group)
        if n_total < 5:
            return pd.DataFrame()  # excluir si hay menos de 5
        n_sample = max(int(n_total * 0.10), 5)
        n_sample = min(n_sample, n_total)  # no exceder el total
        return group.sample(n=n_sample, random_state=42)

    df_ultima_semana = df_ultima_semana.groupby('station_id', group_keys=False).apply(sample_station_group)




    kepler_map = KeplerGl(
        height=700,
        data={
            "Trayectorias ultima semana": df_ultima_semana
        },
        config=config_1
    )
    
    html_mapa_1 = kepler_map._repr_html_()
    #kepler_map.save_to_html(file_name="./data/trayectorias.html", read_only=True)
    if isinstance(html_mapa_1, bytes):
        html_mapa_1 = html_mapa_1.decode("utf-8")
    #@st.cache_resource
    #def load_html(filename):
    #    with open(filename, "r", encoding="utf-8") as f:
    #        return f.read()
    #print('cargando mapa...')
    #html_mapa_1 = load_html("data/trayectorias.html")
    #print('mapa cargado...')
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
    components.html(hide_side_panel_css + html_mapa_1 + resize_fix, height=700, width=2000, scrolling=False)    
    print('mapa pintado...')
            


# ===== INFORMACIÓN ADICIONAL =====
with st.expander("Información sobre los Datos", expanded=False):
    st.markdown("""
    **Fuente de Datos:** RSU (Road Side Unit) instalada en M30
    
    **Tecnología:** V2X (Vehicle-to-Everything) - Comunicación entre vehículos e infraestructura
    
    **Período:** Última semana (datos actualizados en tiempo real)
    
    **Tipos de Carretera Incluidos:**
    - 🛣️ Autopistas (motorway)
    - 🔗 Enlaces de autopista (motorway_link)  
    - 🚏 Enlaces primarios (primary_link)
    
    **Rangos de Velocidad:**
    - 🔴 0-30 km/h: Tráfico congestionado
    - 🟡 30-50 km/h: Tráfico moderado
    - 🟢 50-70 km/h: Tráfico fluido
    - 🔵 70-90+ km/h: Tráfico rápido
    """)

# ===== FOOTER =====
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #94a3b8; font-size: 0.875rem; padding: 1rem 0;">
    Dashboard de Tráfico V2X • Datos actualizados automáticamente • 
    <span style="color: #22c55e;">●</span> Sistema operativo
</div>
""", unsafe_allow_html=True)