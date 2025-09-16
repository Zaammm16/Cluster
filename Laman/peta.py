import os
import json
import pandas as pd
import streamlit as st
import folium
import altair as alt
from folium.plugins import Fullscreen
from streamlit_folium import st_folium
from db_config import get_engine

@st.cache_data
def load_geojson():
    candidates = [
        "/mnt/data/kecamatan_sulbar.geojson",
        "assets/GeoJson/kecamatan_sulbar.geojson",
        "assets/geojson/kecamatan_sulbar.geojson",
        "data/kecamatan_sulbar.geojson",
        "kecamatan_sulbar.geojson",
    ]
    for p in candidates:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
    raise FileNotFoundError("File GeoJSON tidak ditemukan di: " + ", ".join(candidates))

def get_name_from_props(props: dict) -> str | None:
    keys = ("nm_kecamatan","nama_kecamatan","namakecam","kecamatan",
            "NAMA_KEC","WADMKC","Kec","NAME_2","name")
    for k in keys:
        v = props.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None

def _iter_coords(geometry: dict):
    if not geometry or "type" not in geometry or "coordinates" not in geometry:
        return
    gtype = geometry["type"]
    coords = geometry["coordinates"]

    def _pair(c):
        if isinstance(c, (list, tuple)) and len(c) >= 2:
            try:
                return float(c[0]), float(c[1])
            except Exception:
                return None
        return None

    if gtype == "Point":
        p = _pair(coords); 
        if p: yield p
    elif gtype in ("MultiPoint", "LineString"):
        for c in coords:
            p = _pair(c); 
            if p: yield p
    elif gtype == "MultiLineString":
        for line in coords:
            for c in line:
                p = _pair(c); 
                if p: yield p
    elif gtype == "Polygon":
        for ring in coords:
            for c in ring:
                p = _pair(c); 
                if p: yield p
    elif gtype == "MultiPolygon":
        for poly in coords:
            for ring in poly:
                for c in ring:
                    p = _pair(c); 
                    if p: yield p

def _collect_bounds(feature_collection: dict) -> list[list[float]]:
    bounds = []
    for feat in feature_collection.get("features", []):
        geom = feat.get("geometry")
        if not geom: 
            continue
        for lon, lat in _iter_coords(geom):
            bounds.append([lat, lon])
    return bounds

def show_map():
    st.markdown('<h2 class="section-header">🗺️ Peta Hasil Clustering - Sulawesi Barat</h2>', unsafe_allow_html=True)

    if "clustered_table" not in st.session_state:
        st.warning("⚠️ Tidak ada data clustering. Silakan jalankan clustering dulu.")
        st.session_state.menu = "Lihat Hasil Clustering"
        st.rerun()
        return

    try:
        engine = get_engine()
    except Exception as e:
        st.error(f"❌ {e}")
        return

    table_name = st.session_state.clustered_table

    try:
        geojson = load_geojson()
    except Exception as e:
        st.error(f"❌ Gagal memuat GeoJSON: {e}")
        return

    try:
        df_cluster = pd.read_sql(table_name, con=engine)
    except Exception as e:
        st.error(f"❌ Gagal mengambil data clustering: {e}")
        return

    # Validasi kolom wajib
    if not {'KECAMATAN', 'Keterangan'}.issubset(df_cluster.columns):
        st.error("❌ Dataset wajib memiliki kolom 'KECAMATAN' dan 'Keterangan'.")
        return

    # Filter & pencarian
    labels_all = sorted(df_cluster['Keterangan'].dropna().unique().tolist())
    if not labels_all:
        st.info("Tidak ada label klaster untuk ditampilkan.")
        return

    sel_labels = st.multiselect("🎯 Filter Klaster :", labels_all, default=labels_all)
    q = st.text_input("🔎 Cari kecamatan :", value="").strip().lower()

    df_view = df_cluster[df_cluster['Keterangan'].isin(sel_labels)].copy()
    if q:
        df_view = df_view[df_view['KECAMATAN'].astype(str).str.lower().str.contains(q)]

    if df_view.empty:
        st.info("Tidak ada data yang cocok dengan filter.")
        return

    # Inisialisasi peta
    m = folium.Map(location=[-2.844, 119.232], zoom_start=8, tiles='OpenStreetMap')
    Fullscreen(position='topleft').add_to(m)

    # Index nama -> feature GeoJSON
    idx_feature = {}
    for feat in geojson.get("features", []):
        props = (feat.get("properties") or {})
        nm = get_name_from_props(props)
        if nm:
            idx_feature[nm.strip().lower()] = feat

    # Kolom numerik untuk tooltip
    num_cols = [c for c in df_view.select_dtypes(include='number').columns if c not in ['Cluster']]

    matched_features = []
    not_found = []
    for _, row in df_view.iterrows():
        nama = str(row['KECAMATAN']).strip().lower()
        feat = idx_feature.get(nama)
        if not feat:
            not_found.append(nama)
            continue
        new_feat = {
            "type": "Feature",
            "geometry": feat.get("geometry"),
            "properties": dict(feat.get("properties", {}))
        }
        nm_orig = get_name_from_props(new_feat["properties"]) or row['KECAMATAN']
        new_feat["properties"]["label_nama"] = nm_orig
        new_feat["properties"]["kategori"] = row["Keterangan"]
        for col in num_cols:
            new_feat["properties"][col] = row[col]
        matched_features.append(new_feat)

    if not_found:
        st.warning("⚠️ Tidak ditemukan di GeoJSON: " + ", ".join(sorted(set(not_found))))

    filtered_geojson = {"type": "FeatureCollection", "features": matched_features}

    # Palet warna konsisten dengan legenda
    color_map = {
        'Sangat Rendah': 'lightred',
        'Cukup Rendah': 'orange',
        'Rendah': 'red',
        'Agak Rendah': 'pink',
        'Sedikit Rendah': 'lightpink',
        'Sedang': 'blue',
        'Sedikit Tinggi': 'lightblue',
        'Agak Tinggi': 'cyan',
        'Tinggi': 'green',
        'Cukup Tinggi': 'lightgreen',
        'Sangat Tinggi': 'darkgreen'
    }

    def style_fn(feature):
        color = color_map.get(feature['properties'].get('kategori'), 'gray')
        return {"fillColor": color, "color": "black", "weight": 1, "fillOpacity": 0.7}

    tooltip_fields = ["label_nama", "kategori"] + num_cols
    tooltip_aliases = ["Kecamatan", "Potensi"] + num_cols

    gj = folium.GeoJson(
        filtered_geojson,
        name="Kecamatan Terklaster",
        style_function=style_fn,
        tooltip=folium.GeoJsonTooltip(fields=tooltip_fields, aliases=tooltip_aliases)
    ).add_to(m)

    folium.LayerControl().add_to(m)

    bounds = _collect_bounds(filtered_geojson)
    if bounds:
        try:
            m.fit_bounds(bounds)
        except Exception:
            pass
    else:
        st.info("ℹ️ Tidak ada koordinat yang dapat dihitung untuk fit bounds.")

    # Legenda
    st.markdown("### 🗒️ Keterangan Warna")
    for kategori in sorted(df_view['Keterangan'].dropna().unique().tolist()):
        st.markdown(
            f"<div style='display:flex;align-items:center;margin-bottom:4px;'>"
            f"<div style='background:{color_map.get(kategori,'gray')};width:15px;height:15px;border-radius:2px;margin-right:8px;'></div>"
            f"<span>{kategori}</span></div>", unsafe_allow_html=True
        )

    # Peta
    st.markdown("### 📍 Peta Klaster")
    st_folium(m, width='100%', height=600, returned_objects=[], key="folium_map_unique")

    # ===============================
    # 📊 BAR CHART DI BAWAH PETA
    # ===============================
    st.markdown("### 📊 Jumlah Kecamatan per Klaster")

    # Data agregasi jumlah kecamatan per klaster (mengikuti filter & pencarian)
    counts = (
        df_view.assign(KECAMATAN=df_view['KECAMATAN'].astype(str))
               .groupby('Keterangan', as_index=False)
               .agg(Jumlah=('KECAMATAN', 'count'))
    )

    if counts.empty:
        st.info("Tidak ada data untuk ditampilkan pada grafik.")
        return

    # Urutan domain kategori sesuai urutan tampil (bisa disesuaikan)
    domain = counts['Keterangan'].tolist()
    range_colors = [color_map.get(k, 'gray') for k in domain]

    base = alt.Chart(counts).encode(
        x=alt.X('Keterangan:N', title='Klaster', sort=domain),
        y=alt.Y('Jumlah:Q', title='Jumlah Kecamatan'),
        tooltip=[alt.Tooltip('Keterangan:N', title='Klaster'),
                 alt.Tooltip('Jumlah:Q', title='Jumlah')]
    )

    bars = base.mark_bar().encode(
        color=alt.Color('Keterangan:N',
                        scale=alt.Scale(domain=domain, range=range_colors),
                        legend=None)
    )

    labels = base.mark_text(dy=-5).encode(text='Jumlah:Q')

    chart = (bars + labels).properties(width='container', height=320)

    st.altair_chart(chart, use_container_width=True)

if __name__ == "__main__":
    show_map()