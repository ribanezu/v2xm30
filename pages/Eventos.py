import streamlit as st
import pandas as pd
import plotly.express as px
import streamlit.components.v1 as components
from datetime import datetime
from streamlit_plotly_events import plotly_events
from sqlalchemy import create_engine

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

    return df

df_denm  = load_data()
orden_dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

# ---------------------------
# Mapa Kepler.gl
# ---------------------------
st.subheader("Mapa de Eventos DENM")
# HTML fix para forzar el redimensionamiento del mapa
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

html_content = load_html("./kepler_eventos_ok.gl.html")
html_inyectado = html_content + html_fix
components.html(html_inyectado, height=800, width=2000, scrolling=False) 

## ---------------------------

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