import streamlit as st
import pandas as pd
import re
from datetime import datetime
from sqlalchemy import text
from utils.baca_file import read_file
from db_config import get_engine, get_db_name, get_retention_days
from utils.retention import register_dataset

def clean_column_name(name: str) -> str:
    cleaned_name = re.sub(r'[\s()\/]+', '_', name)
    cleaned_name = re.sub(r'[^a-zA-Z0-9_]', '', cleaned_name)
    cleaned_name = re.sub(r'_+', '_', cleaned_name).strip('_')
    if not cleaned_name or not cleaned_name[0].isalpha():
        cleaned_name = 'col_' + cleaned_name
    return cleaned_name.lower()

def clean_table_name(name: str) -> str:
    cleaned_name = re.sub(r'[\s()\/]+', '_', name)
    cleaned_name = re.sub(r'[^a-zA-Z0-9_]', '', cleaned_name)
    cleaned_name = re.sub(r'_+', '_', cleaned_name).strip('_')
    if not cleaned_name or not cleaned_name[0].isalpha():
        cleaned_name = 'default_table'
    return cleaned_name.lower()

def table_exists(engine, schema: str, table_name: str) -> bool:
    with engine.connect() as conn:
        q = text("""
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_schema = :schema AND table_name = :name
        """)
        return bool(conn.execute(q, {"schema": schema, "name": table_name}).scalar())

def save_dataset(engine, table_name: str, df: pd.DataFrame):
    df.to_sql(table_name, con=engine, index=False, if_exists='replace')
    register_dataset(engine, table_name, retention_days=get_retention_days())

def show_upload():
    st.markdown('<h2 class="section-header">📁 Upload Data</h2>', unsafe_allow_html=True)
    st.markdown("*Wajib* ada kolom **KECAMATAN** (teks). Kolom numerik lain dipakai untuk clustering.")

    uploaded_file = st.file_uploader("Pilih file CSV/Excel:", type=['csv', 'xlsx', 'xls'])
    if uploaded_file is None:
        return

    try:
        data = read_file(uploaded_file)
        st.session_state.data = data
    except Exception as e:
        st.error(f"❌ Gagal membaca file: {e}")
        return

    if data.empty:
        st.error("❌ Data kosong.")
        return

    data_cols_lower = [c.lower() for c in data.columns]
    if 'kecamatan' not in data_cols_lower:
        st.error("❌ Kolom KECAMATAN wajib ada.")
        return
    kecamatan_col = next(c for c in data.columns if c.lower() == 'kecamatan')
    if kecamatan_col != 'KECAMATAN':
        data = data.rename(columns={kecamatan_col: 'KECAMATAN'})
        st.info(f"ℹ️ Kolom '{kecamatan_col}' diubah menjadi 'KECAMATAN'.")

    mapping = {}
    for col in data.columns:
        if col != 'KECAMATAN':
            mapping[col] = clean_column_name(col)
    if mapping:
        data = data.rename(columns=mapping)

    # --- Imputasi NaN & nol ke mean (kolom numerik)
    num_cols = data.select_dtypes(include='number').columns.tolist()
    filled_cols = []
    for col in num_cols:
        vals = data[col].tolist()
        valid = [float(v) for v in vals if (pd.notna(v) and v != 0)]
        mean_v = (sum(valid) / len(valid)) if valid else 0.0
        if data[col].isna().any() or (data[col] == 0).any():
            data[col] = [mean_v if (pd.isna(v) or v == 0) else v for v in vals]
            filled_cols.append(col)
        data[col] = [round(float(v), 2) for v in data[col]]

    st.dataframe(data.head(), use_container_width=True)

    default_table = clean_table_name(uploaded_file.name.rsplit('.', 1)[0])
    table_name = st.text_input("📝 Nama tabel:", value=default_table)

    reserved_words = {'select', 'from', 'where', 'table', 'insert', 'update', 'delete'}
    if not re.fullmatch(r'[a-z0-9_]+', table_name or ""):
        st.error("❌ Nama tabel hanya boleh huruf kecil, angka, underscore.")
        return
    if table_name.lower() in reserved_words or len(table_name) < 3:
        st.error("❌ Nama tabel tidak valid.")
        return

    try:
        engine = get_engine()
        schema = get_db_name()
    except Exception as e:
        st.error(f"❌ {e}")
        return

    try:
        exists = table_exists(engine, schema, table_name)
    except Exception as e:
        st.error(f"❌ Gagal memeriksa tabel: {e}")
        return

    if exists:
        st.warning(f"⚠️ Tabel `{table_name}` sudah ada.")
        c1, c2, c3 = st.columns(3)
        btn_overwrite = c1.button("💾 Lanjutkan Overwrite", use_container_width=True, key="btn_overwrite")
        btn_copy      = c2.button("📄 Simpan Sebagai Salinan", use_container_width=True, key="btn_copy")
        btn_cancel    = c3.button("❌ Batalkan", use_container_width=True, key="btn_cancel")

        if btn_cancel:
            st.info("Upload dibatalkan.")
            return

        if btn_overwrite:
            try:
                save_dataset(engine, table_name, data)
                st.session_state.selected_dataset = table_name
                st.success(f"✅ Ditimpa sebagai `{table_name}`")
                st.info("Mengalihkan ke halaman Clustering...")
                st.session_state.menu = "Lihat Hasil Clustering"
                st.rerun()
            except Exception as e:
                st.error(f"❌ Gagal menyimpan (overwrite): {e}")
            return

        if btn_copy:
            ver_name = f"{table_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            try:
                save_dataset(engine, ver_name, data)
                st.session_state.selected_dataset = ver_name
                st.success(f"✅ Disalin sebagai `{ver_name}`")
                st.info("Mengalihkan ke halaman Clustering...")
                st.session_state.menu = "Lihat Hasil Clustering"
                st.rerun()
            except Exception as e:
                st.error(f"❌ Gagal menyimpan salinan: {e}")
            return
        return

    if st.button("💾 Simpan ke Database", use_container_width=True, key="btn_save_new"):
        try:
            save_dataset(engine, table_name, data)
            st.session_state.selected_dataset = table_name
            st.success(f"✅ Dataset tersimpan sebagai `{table_name}`")
            st.info("Mengalihkan ke halaman Clustering...")
            st.session_state.menu = "Lihat Hasil Clustering"
            st.rerun()
        except Exception as e:
            st.error(f"❌ Gagal menyimpan dataset: {e}")
            return
