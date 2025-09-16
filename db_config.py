import os
import streamlit as st
from sqlalchemy import create_engine

# Kebijakan retensi (hari)
DATA_RETENTION_DAYS = int(os.getenv("DATA_RETENTION_DAYS", "365"))

def _build_local_url():
    user = os.getenv("DB_USER", "root")
    pwd  = os.getenv("DB_PASS", "")
    host = os.getenv("DB_HOST", "localhost")
    port = int(os.getenv("DB_PORT", "3306"))
    name = os.getenv("DB_NAME", "cluster_db")
    return f"mysql+pymysql://{user}:{pwd}@{host}:{port}/{name}?charset=utf8mb4"

def get_engine():
    """
    Prioritas URL:
    1) st.secrets['db_url'] (Cloud)
    2) env var DATABASE_URL
    3) fallback ke MySQL lokal (untuk development)
    """
    if hasattr(st, "secrets") and "db_url" in st.secrets:
        url = st.secrets["db_url"]
    elif os.getenv("DATABASE_URL"):
        url = os.getenv("DATABASE_URL")
    else:
        url = _build_local_url()

    engine = create_engine(url, pool_pre_ping=True, pool_recycle=3600, future=True)
    # Tes singkat koneksi
    with engine.connect() as conn:
        conn.exec_driver_sql("SELECT 1")
    return engine

def get_db_name():
    # dipakai upload.py saat cek schema di MySQL
    if hasattr(st, "secrets") and "db_name" in st.secrets:
        return st.secrets["db_name"]
    return os.getenv("DB_NAME", "cluster_db")

def get_retention_days():
    return DATA_RETENTION_DAYS
