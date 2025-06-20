import pandas as pd
import geopandas as gpd
import streamlit as st
from sqlalchemy import create_engine

@st.cache_data
def load_data():
    db_url = st.secrets["db_url"]
    engine = create_engine(db_url)

    df = pd.read_sql("SELECT * FROM cam_ref_message WHERE received_at > '2025-06-11 00:00:00'", engine)
    df_denm = pd.read_sql("SELECT * FROM denm_ref_message WHERE received_at > '2025-06-11 00:00:00'", engine)

    df["received_at"] = pd.to_datetime(df["received_at"])
    df["received_at"] = df["received_at"] + pd.Timedelta(hours=1)
    if "weekday_es" in df.columns:
        df["weekday_es"] = pd.Categorical(
            df["weekday_es"],
            categories=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"],
            ordered=True
        )
    if "hour" in df.columns and "hour_label" not in df.columns:
        df["hour_label"] = df["hour"].apply(lambda x: f"{int(x):02d}:00")

    df_denm["received_at"] = pd.to_datetime(df_denm["received_at"])
    df_denm["received_at"] = df_denm["received_at"] + pd.Timedelta(hours=1)
    if "weekday_es" in df_denm.columns:
        df_denm["weekday_es"] = pd.Categorical(
            df_denm["weekday_es"],
            categories=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"],
            ordered=True
        )
    if "hour" in df_denm.columns and "hour_label" not in df_denm.columns:
        df["hour"] = (df["hour"] + 1) % 24  # Para que no se pase de 23
        df["hour_label"] = df["hour"].apply(lambda x: f"{int(x):02d}:00")

    return df, df_denm

@st.cache_data
def load_m30_data():
    gdf = gpd.read_file("./data/m30_osm_v3.shp")
    gdf = gdf.to_crs(epsg=4326)
    return gdf

