# 🛣️ Visualización de Tráfico y Eventos en la M30

Este proyecto implementa un **dashboard interactivo** con Streamlit para analizar datos de tráfico y eventos DENM en la M-30 de Madrid, utilizando tecnologías como **Kepler.gl**, **Plotly**, y herramientas geoespaciales con **GeoPandas** y **PostGIS**.

## Estructura

El dashboard está dividido en tres secciones principales:

---

## **1. Demanda de Tráfico**

Esta sección permite analizar el flujo de vehículos a lo largo del tiempo, desglosado por día de la semana y hora.

### Funcionalidades:
- **Selector de día de la semana**: Filtra el tráfico por días laborales, fin de semana o uno específico.
- **Gráfico de líneas por hora**: Muestra el número de vehículos únicos por hora agrupado por día.
- **KPIs de tráfico**:
  - Pico diario (vehículos únicos)
  - Velocidad media
  - Hora pico
  - Última actualización
- **Mapa de calor**: Visualiza la intensidad horaria del tráfico por día.
- **Gráficos complementarios**:
  - Distribución de vehículos por hora.
  - Comparativa entre días.

---

## **Eventos DENM**

Esta sección analiza los **eventos de notificación de peligro** (DENM) que afectan a la circulación.

### Funcionalidades:
- **Mapa interactivo Kepler.gl**: Visualiza todos los eventos sobre el trazado de la M30.
- **Gráfico de quesitos interactivo**:
  - Distribución de causas (traffic condition, stationary vehicle, etc.).
  - Subcausas filtradas al seleccionar una causa.
- **Selector de tipo de evento**: Permite filtrar los eventos para ver cómo se distribuyen por hora del día.
- **Gráfico de barras por hora**: Visualiza la frecuencia horaria de cada tipo de evento.
  
---

## 🧮 Página 3: **Tramos M30**

Esta sección analiza métricas calculadas para cada **tramo de vía** de la M30.

### Datos analizados:
- Velocidades estadísticas: media, máxima, mínima, cuartiles, desviación típica.
- Aceleraciones: longitudinal y lateral.
- Número de vehículos por tramo.
- Hora pico por tramo (hora con más tráfico según los vehículos que lo recorren).
- Porcentaje de congestión (vehículos que recorren más de 100m por debajo de 20 km/h).
- Exceso de velocidad con respecto al límite legal.
- Densidad de tráfico (veh/km).

### Visualización:
- Seis mapas interactivos (Kepler.gl), organizados en **rejilla de 3 filas y 2 columnas**:
  1. Velocidades máximas por tramo
  2. Densidad de vehículos en hora pico
  3. Niveles de congestión
  4. Exceso de velocidad
  5. Aceleración media
  6. Densidad total de vehículos

---

## 🧰 Tecnologías utilizadas

- **Python** con:
  - Streamlit
  - GeoPandas
  - Pandas
  - Plotly
  - Keplergl
- **Datos geoespaciales** en EPSG:25830 (Madrid - UTM zona 30N)
- **Custom CSS** para tema oscuro y visualización consistente.

---

## 📦 Requisitos

- Python 3.9+
- Paquetes: `streamlit`, `geopandas`, `plotly`, `keplergl`, `pandas`, `shapely`, `streamlit_plotly_events`, etc.

Instalación recomendada:

```bash
pip install -r requirements.txt
