import pandas as pd
import streamlit as st
from sqlalchemy import text
from db_config import get_engine
from utils.retention import cleanup_expired_datasets, days_to_expiry

@st.cache_data(show_spinner=False)
def _read_table(table: str, _engine):
    """Cache pembacaan tabel. _engine diabaikan hashing-nya oleh Streamlit."""
    return pd.read_sql(table, con=_engine)

def show_dataset():
    st.markdown("### 📚 Dataset (Hasil Proses)")
    try:
        engine = get_engine()
    except Exception as e:
        st.error(f"❌ {e}")
        return

    removed = cleanup_expired_datasets(engine)
    if removed:
        st.info("🧹 Dataset kedaluwarsa dihapus otomatis: " + ", ".join(f"`{t}`" for t in removed))

    try:
        with engine.connect() as conn:
            result = conn.execute(text("SHOW TABLES"))
            clustered_tables = [
                row[0] for row in result
                if row[0].endswith("_clustered") and row[0] != "_datasets_meta"
            ]
    except Exception as e:
        st.error(f"❌ Gagal mengambil daftar tabel: {e}")
        return

    if not clustered_tables:
        st.info("Belum ada hasil clustering. Silakan lakukan proses clustering terlebih dahulu.")
        return

    # Sinkronisasi pilihan sebelumnya (pakai state khusus agar tidak bentrok dengan raw dataset)
    state_key = "selected_clustered"
    if state_key in st.session_state and st.session_state[state_key] not in clustered_tables:
        del st.session_state[state_key]

    selected_clustered = st.selectbox(
        "🗂️ Pilih Hasil Clustering:",
        options=sorted(clustered_tables),
        index=sorted(clustered_tables).index(st.session_state[state_key])
        if state_key in st.session_state and st.session_state[state_key] in clustered_tables
        else 0
    )
    st.session_state[state_key] = selected_clustered

    base_table = selected_clustered[:-10] if selected_clustered.endswith("_clustered") else selected_clustered
    sisa = days_to_expiry(engine, base_table)
    if sisa is not None:
        st.caption(f"⏳ Sisa masa simpan dataset ini: {sisa} hari (otomatis terhapus saat habis masa simpan)")

    try:
        df = _read_table(selected_clustered, engine)
        st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.error(f"❌ Gagal memuat `{selected_clustered}`: {e}")
        return

    if st.button("🗺️ Lihat di Peta", use_container_width=True):
        # Set tabel clustered yang dipakai halaman peta
        st.session_state.clustered_table = selected_clustered
        st.session_state.menu = "Peta Visualisasi"
        st.rerun()