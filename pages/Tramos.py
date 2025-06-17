import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
from datetime import datetime

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

st.title("Tramos M30")


# HTML fix para redimensionamiento
html_fix = """
<script>
  setTimeout(() => {
    window.dispatchEvent(new Event('resize'));
  }, 200);
</script>
"""

@st.cache_resource
def load_html(filename):
    with open(filename, "r", encoding="utf-8") as f:
        return f.read()

# ---------------------------
# Visualización de Mapas
# ---------------------------
st.subheader("Visualización de Mapas M30")

# CSS personalizado para grid de mapas
st.markdown("""
<style>
.map-container {
    display: grid;
    grid-template-columns: repeat(2, 1fr); /* 2 columnas */
    gap: 1.5rem;
    margin-bottom: 2rem;
}
.map-item {
    border-radius: 1px;
    overflow: hidden;
    box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    background: #2a2a2a;
    display: flex;
    flex-direction: column;
}
.map-title {
    text-align: center;
    padding: 0.75rem;
    font-weight: bold;
    background: #4B5563;
    color: white;
    font-size: 1rem;
    border-bottom: 1px solid #6B7280;
}
</style>
""", unsafe_allow_html=True)


# Archivos de mapas Kepler
map_files = [
    "./kepler_velocidades_maximas.gl.html",
    "./kepler_densidad_horapico.gl.html",
    "./kepler_zonas_congestionadas.gl.html",
    "./kepler_exceso_velocidad.gl.html",
    "./kepler_aceleracion_media.gl.html"
]

map_titles = [
    "Velocidades máximas por Tramo",
    "Densidad de vehículos por Tramo en Hora Punta",
    "Niveles de Congestión (%)",
    "Exceso de Velocidad por Tramo",
    "Aceleración Media por Tramo"
]

# Renderizar mapas en 3 filas y 2 columnas
for i in range(0, len(map_files), 2):
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown(f"##### {map_titles[i]}")
        html_content = load_html(map_files[i]) + html_fix
        components.html(html_content, height=600, scrolling=False)
        st.markdown('</div>', unsafe_allow_html=True)



    if i + 1 < len(map_files):
        with col2:
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown(f"##### {map_titles[i+1]}")
            html_content = load_html(map_files[i+1]) + html_fix
            components.html(html_content, height=600, scrolling=False)
            st.markdown('</div>', unsafe_allow_html=True)
