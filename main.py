import streamlit as st
from streamlit_option_menu import option_menu
from Laman.upload import show_upload
from Laman.dataset import show_dataset
from Laman.hasil_cluster import show_clustering
from Laman.peta import show_map

st.set_page_config(
    page_title="Aplikasi Clustering Potensi Perkebunan",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inisialisasi session_state untuk menu
if "menu" not in st.session_state:
    st.session_state.menu = "Upload Dataset"

# CSS kecil untuk efek hover ikon di sidebar
st.markdown("""
<style>
.nav-link .icon { transition: transform 0.3s ease; }
.nav-link:hover .icon { transform: scale(1.2); }
.nav-link-selected .icon { transform: none !important; }
</style>
""", unsafe_allow_html=True)

# Sidebar Navigasi
with st.sidebar:
    st.markdown("""
    <div style="text-align: center; margin-bottom: 20px;">
        <h3 style="color: #FF914D; font-family: 'Arial', sans-serif;">
            Clustering Potensi Perkebunan
        </h3>
    </div>
    """, unsafe_allow_html=True)

    menu = option_menu(
        menu_title=None,
        options=["Upload Dataset", "Dataset Tersimpan", "Lihat Hasil Clustering", "Peta Visualisasi"],
        icons=["cloud-upload-fill", "database-fill", "bar-chart-fill", "geo-alt-fill"],
        default_index=[
            "Upload Dataset", "Dataset Tersimpan", "Lihat Hasil Clustering", "Peta Visualisasi"
        ].index(st.session_state.get("menu", "Upload Dataset")),
        orientation="vertical",
        styles={
            "container": {"padding": "10px", "background-color": "#1a1a1a",
                          "border-radius": "10px", "box-shadow": "0 4px 8px rgba(0,0,0,0.2)"},
            "icon": {"color": "#FFFFFF", "font-size": "20px"},
            "nav-link": {"font-size": "16px", "font-family": "'Arial', sans-serif", "text-align": "left",
                         "margin": "5px 0", "padding": "10px", "border-radius": "5px",
                         "--hover-color": "#333333", "transition": "all 0.3s ease"},
            "nav-link-selected": {"background-color": "#FF914D", "color": "#ffffff", "font-weight": "bold"}
        }
    )

# Simpan menu terpilih ke session_state
st.session_state.menu = menu

# Routing antar halaman
if menu == "Upload Dataset":
    show_upload()
elif menu == "Lihat Hasil Clustering":
    show_clustering()
elif menu == "Dataset Tersimpan":
    show_dataset()
elif menu == "Peta Visualisasi":
    show_map()

# Footer
st.markdown("---")
st.markdown("<div style='text-align:center;color:#7f8c8d;'>Sistem Clustering Perkebunan</div>", unsafe_allow_html=True)