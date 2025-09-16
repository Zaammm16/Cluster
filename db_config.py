import os
import streamlit as st
from sqlalchemy import create_engine

DATA_RETENTION_DAYS = int(os.getenv("DATA_RETENTION_DAYS", "365"))

@st.cache_resource
def get_engine():
    if "db_url" in st.secrets:
        url = st.secrets["db_url"]
    elif os.getenv("DATABASE_URL"):
        url = os.getenv("DATABASE_URL")
    else:
        raise Exception("❌ Tidak ada konfigurasi DB ditemukan.")

    engine = create_engine(url, pool_pre_ping=True, pool_recycle=3600, future=True)
    with engine.connect() as conn:
        conn.exec_driver_sql("SELECT 1")
    return engine

def get_db_name():
    if "db_name" in st.secrets:
        return st.secrets["db_name"]
    return os.getenv("DB_NAME", "railway")

def get_retention_days():
    return DATA_RETENTION_DAYS
