import io
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st
from db_config import get_engine
from utils.algoritma import (
    KMeansCustom,
    MinMaxScaler,
    compute_dbi,
    apply_descriptive_labels,
)

def show_clustering():
    st.markdown('<h2 class="section-header">📊 Hasil Clustering</h2>', unsafe_allow_html=True)

    if "selected_dataset" not in st.session_state:
        st.warning("⚠️ Pilih dataset dulu di halaman Dataset.")
        st.session_state.menu = "Dataset Tersimpan"
        st.rerun()

    table_name = st.session_state.selected_dataset
    engine = get_engine()

    try:
        df = pd.read_sql(table_name, con=engine)
        st.markdown(f"### Dataset: `{table_name}`")
        st.dataframe(df, use_container_width=True)

        numeric_cols = df.select_dtypes(include='number').columns.tolist()
        st.markdown("### 🔢 Pilih Kolom untuk Clustering")
        default_feats = numeric_cols[:2] if len(numeric_cols) >= 2 else numeric_cols
        selected_features = st.multiselect("Pilih Kolom:", numeric_cols, default=default_feats)
        if len(selected_features) < 2:
            st.info("💡 Pilih minimal 2 kolom numerik.")
            return

        if 'KECAMATAN' not in df.columns:
            st.error("❌ Wajib ada kolom 'KECAMATAN' untuk visualisasi peta.")
            return

        X = df[selected_features].values.tolist()
        X_scaled = MinMaxScaler().fit_transform(X)

        # Elbow (WCSS) & DBI plots
        kmeans = KMeansCustom(random_state=42)
        recommended_k, wcss_values = kmeans._elbow_method(X_scaled)

        dbi_values = []
        k_range_dbi = list(range(2, 11))
        for k in k_range_dbi:
            kmeans.n_clusters = k
            kmeans.fit(X_scaled)
            dbi_values.append(compute_dbi(X_scaled, kmeans.labels, kmeans.centroids, k))

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 📈 Elbow Method")
            fig1, ax1 = plt.subplots(figsize=(5.5, 3.2))
            ax1.plot(range(1, len(wcss_values) + 1), wcss_values, marker='o')
            ax1.set_xlabel("Jumlah Cluster (k)")
            ax1.set_ylabel("WCSS")
            ax1.set_title("Elbow Method")
            st.pyplot(fig1, use_container_width=False)
            st.caption(f"Rekomendasi k (kurvatur): **{recommended_k}**")

        with col2:
            st.markdown("### 📉 Davies-Bouldin Index")
            fig2, ax2 = plt.subplots(figsize=(5.5, 3.2))
            ax2.plot(k_range_dbi, dbi_values, marker='o')
            ax2.set_xlabel("Jumlah Cluster (k)")
            ax2.set_ylabel("DBI")
            ax2.set_title("Davies-Bouldin Index")
            st.pyplot(fig2, use_container_width=False)
            best_k_dbi = k_range_dbi[dbi_values.index(min(dbi_values))]
            st.caption(f"DBI terendah di k = **{best_k_dbi}**, nilai = **{min(dbi_values):.3f}**")

        st.markdown("### 🔢 Tentukan Jumlah Klaster")
        n_clusters = st.slider("Jumlah Cluster (K):", 2, 10, value=int(recommended_k) if 2 <= recommended_k <= 10 else 3)

        if st.button("🚀 Jalankan Clustering"):
            kmeans = KMeansCustom(n_clusters=n_clusters, random_state=42)
            df['Cluster'] = kmeans.fit_predict(X_scaled)

            df_labeled, labels_map = apply_descriptive_labels(df, selected_features, 'Cluster', n_clusters)
            result_df = df_labeled[['KECAMATAN'] + selected_features + ['Cluster', 'Keterangan']]

            clustered_table = f"{table_name}_clustered"
            result_df.to_sql(clustered_table, con=engine, index=False, if_exists='replace')

            st.session_state.clustered_table = clustered_table
            st.session_state.clustered_result_df = result_df.copy()

            dbi_val = compute_dbi(X_scaled, df_labeled['Cluster'].tolist(), kmeans.centroids, n_clusters)
            st.success(f"✅ Clustering selesai untuk k={n_clusters}. Nilai DBI = {dbi_val:.3f}")

        if "clustered_result_df" in st.session_state:
            st.markdown("### 📋 Hasil Clustering")
            st.dataframe(st.session_state.clustered_result_df, use_container_width=True)

            st.markdown("### 💾 Unduh Hasil")
            col_csv, col_xlsx = st.columns(2)
            with col_csv:
                csv_str = st.session_state.clustered_result_df.to_csv(index=False)
                st.download_button(
                    "📥 CSV",
                    data=csv_str,
                    file_name=f"{st.session_state.clustered_table}.csv",
                    mime="text/csv",
                    key="dl_csv_left"
                )
            with col_xlsx:
                buf = io.BytesIO()
                st.session_state.clustered_result_df.to_excel(buf, index=False, engine='openpyxl')
                buf.seek(0)
                st.download_button(
                    "📥 Excel",
                    data=buf,
                    file_name=f"{st.session_state.clustered_table}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="dl_xlsx_right"
                )

            st.markdown("### 🌍 Lanjut ke Peta Visualisasi")
            if st.button("🗺️ Lihat Peta Dataset Ini"):
                st.session_state.menu = "Peta Visualisasi"
                st.rerun()

    except Exception as e:
        st.error(f"❌ Gagal memproses dataset: {e}")

if __name__ == "__main__":
    show_clustering()