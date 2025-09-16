from __future__ import annotations
import random
from typing import Sequence, List, Dict, Any, Tuple

__all__ = [
    "MinMaxScaler",
    "KMeansCustom",
    "compute_dbi",
    "compute_cluster_means",
    "get_cluster_labels",
    "apply_descriptive_labels",
]

# MinMaxScaler
class MinMaxScaler:
    def __init__(self):
        self.min_vals: List[float] | None = None
        self.max_vals: List[float] | None = None
        self.means: List[float] | None = None
        self._range: List[float] | None = None

    def fit(self, data: Sequence[Sequence[float]]):
        if not data:
            raise ValueError("Data kosong.")
        n_features = len(data[0])
        self.min_vals = [float("inf")] * n_features
        self.max_vals = [float("-inf")] * n_features
        sums = [0.0] * n_features
        counts = [0] * n_features

        for row in data:
            for i, v in enumerate(row):
                if v is None or (isinstance(v, float) and v != v):  # NaN
                    continue
                if v < self.min_vals[i]: self.min_vals[i] = v
                if v > self.max_vals[i]: self.max_vals[i] = v
                sums[i] += v
                counts[i] += 1

        self.means = [(sums[i] / counts[i]) if counts[i] > 0 else 0.0 for i in range(n_features)]
        for i in range(n_features):
            if self.min_vals[i] == float("inf"): self.min_vals[i] = 0.0
            if self.max_vals[i] == float("-inf"): self.max_vals[i] = 0.0

        self._range = [self.max_vals[i] - self.min_vals[i] for i in range(n_features)]
        return self

    def transform(self, data: Sequence[Sequence[float]]) -> List[List[float]]:
        if self.min_vals is None or self._range is None or self.means is None:
            raise ValueError("Scaler belum di-fit.")
        out: List[List[float]] = []
        for row in data:
            scaled_row: List[float] = []
            for i, v in enumerate(row):
                if v is None or (isinstance(v, float) and v != v):
                    v = self.means[i]
                rng = self._range[i]
                scaled_row.append(0.0 if rng == 0 else (v - self.min_vals[i]) / rng)
            out.append(scaled_row)
        return out

    def fit_transform(self, data: Sequence[Sequence[float]]) -> List[List[float]]:
        return self.fit(data).transform(data)

# KMeans
class KMeansCustom:
    def __init__(self, n_clusters: int = 3, max_iters: int = 100, random_state: int = 42):
        self.n_clusters = int(n_clusters)
        self.max_iters = int(max_iters)
        self.random_state = int(random_state)
        self.centroids: List[List[float]] | None = None
        self.labels: List[int] | None = None

    # sqrt manual (Newton)
    def _sqrt(self, x: float, eps: float = 1e-10, max_iter: int = 100) -> float:
        if x < 0: raise ValueError("Tidak bisa akar bilangan negatif.")
        if x == 0: return 0.0
        g = x / 2.0
        for _ in range(max_iter):
            ng = 0.5 * (g + x / g)
            if abs(ng - g) < eps: return ng
            g = ng
        return g

    # jarak euclidean manual
    def _euclid(self, a: Sequence[float], b: Sequence[float]) -> float:
        s = 0.0
        for x, y in zip(a, b):
            d = x - y
            s += d * d
        return self._sqrt(s)

    # inisialisasi centroid random uniform dalam rentang fitur
    def _init_centroids(self, data: Sequence[Sequence[float]]) -> List[List[float]]:
        random.seed(self.random_state)
        n_features = len(data[0])
        mins = [float("inf")] * n_features
        maxs = [float("-inf")] * n_features
        for r in data:
            for i in range(n_features):
                if r[i] < mins[i]: mins[i] = r[i]
                if r[i] > maxs[i]: maxs[i] = r[i]
        cents: List[List[float]] = []
        for _ in range(self.n_clusters):
            cents.append([random.uniform(mins[i], maxs[i]) for i in range(n_features)])
        return cents

    # assignment step
    def _assign(self, data: Sequence[Sequence[float]], cents: Sequence[Sequence[float]]) -> List[int]:
        labels: List[int] = []
        for p in data:
            best = 0
            best_d = float("inf")
            for i, c in enumerate(cents):
                d = self._euclid(p, c)
                if d < best_d:
                    best_d = d
                    best = i
            labels.append(best)
        return labels

    # update step
    def _update(self, data: Sequence[Sequence[float]], labels: Sequence[int]) -> List[List[float]]:
        new_cents: List[List[float]] = []
        n_features = len(data[0])
        for cid in range(self.n_clusters):
            pts = [data[i] for i in range(len(data)) if labels[i] == cid]
            if pts:
                new_cents.append([sum(p[j] for p in pts) / len(pts) for j in range(n_features)])
            else:
                new_cents.append(self.centroids[cid])  # pertahankan jika kosong
        return new_cents

    # jumlah kuadrat jarak intra-cluster (WCSS)
    def _wcss(self, data: Sequence[Sequence[float]], labels: Sequence[int], cents: Sequence[Sequence[float]]) -> float:
        total = 0.0
        for i in range(len(data)):
            cid = labels[i]
            d = self._euclid(data[i], cents[cid])
            total += d * d
        return total

    # Elbow (k rekomendasi + daftar WCSS)
    def _elbow_method(self, data: Sequence[Sequence[float]], max_k: int = 10) -> Tuple[int, List[float]]:
        wcss_values: List[float] = []
        best_k = 3
        best_curve = float("-inf")
        for k in range(1, max_k + 1):
            self.n_clusters = k
            self.fit(data)
            wcss_values.append(self._wcss(data, self.labels, self.centroids))
            if k >= 3:
                d1 = wcss_values[-3] - wcss_values[-2]
                d2 = wcss_values[-2] - wcss_values[-1]
                curvature = d1 - d2
                if curvature > best_curve:
                    best_curve = curvature
                    best_k = k - 1
        return best_k, wcss_values

    # API publik
    def fit(self, data: Sequence[Sequence[float]]):
        self.centroids = self._init_centroids(data)
        last_labels: List[int] | None = None
        for _ in range(self.max_iters):
            labels = self._assign(data, self.centroids)
            new_cents = self._update(data, labels)
            if new_cents == self.centroids and last_labels == labels:
                self.labels = labels
                break
            self.centroids = new_cents
            self.labels = labels
            last_labels = labels
        return self

    def predict(self, data: Sequence[Sequence[float]]) -> List[int]:
        if self.centroids is None:
            raise ValueError("Model belum di-fit.")
        return self._assign(data, self.centroids)

    def fit_predict(self, data: Sequence[Sequence[float]]) -> List[int]:
        self.fit(data)
        return self.labels

# Davies–Bouldin Index 
def compute_dbi(
    data: Sequence[Sequence[float]],
    labels: Sequence[int],
    centroids: Sequence[Sequence[float]],
    n_clusters: int,
) -> float:
    # S_i: rata-rata jarak ke centroid dalam cluster i
    S: List[float] = []
    for i in range(n_clusters):
        pts = [data[j] for j in range(len(data)) if labels[j] == i]
        if not pts:
            S.append(0.0)
            continue
        dsum = 0.0
        for p in pts:
            s = 0.0
            for a, b in zip(p, centroids[i]):
                diff = a - b
                s += diff * diff
            dsum += s ** 0.5
        S.append(dsum / len(pts))

    # M_ij: jarak antar centroid
    M = [[0.0 for _ in range(n_clusters)] for _ in range(n_clusters)]
    for i in range(n_clusters):
        for j in range(n_clusters):
            if i == j: 
                continue
            s = 0.0
            for a, b in zip(centroids[i], centroids[j]):
                diff = a - b
                s += diff * diff
            M[i][j] = s ** 0.5

    # R_ij
    R = [[0.0 for _ in range(n_clusters)] for _ in range(n_clusters)]
    for i in range(n_clusters):
        for j in range(n_clusters):
            if i != j and M[i][j] != 0:
                R[i][j] = (S[i] + S[j]) / M[i][j]

    # DBI = rata-rata max R_i
    max_R = [max(R[i]) if any(R[i]) else 0.0 for i in range(n_clusters)]
    return (sum(max_R) / len(max_R)) if max_R else float("inf")

# Urutan cluster & Label Deskriptif 
def compute_cluster_means(df, selected_features: List[str], cluster_col: str) -> List[int]:
    """
    Hitung rata-rata per cluster berdasarkan selected_features (tanpa numpy).
    Kembalikan urutan cluster_id dari total-mean terendah ke tertinggi.
    """
    cluster_sums: Dict[str, Dict[Any, float]] = {f: {} for f in selected_features}
    cluster_counts: Dict[str, Dict[Any, int]] = {f: {} for f in selected_features}

    for _, row in df.iterrows():
        cid = row[cluster_col]
        for f in selected_features:
            v = row[f]
            if v is None or (isinstance(v, float) and v != v):  # NaN
                continue
            cluster_sums[f][cid] = cluster_sums[f].get(cid, 0.0) + float(v)
            cluster_counts[f][cid] = cluster_counts[f].get(cid, 0) + 1

    total_means: Dict[Any, float] = {}
    all_cids = set()
    for d in cluster_sums.values():
        all_cids |= set(d.keys())

    for cid in all_cids:
        means = []
        for f in selected_features:
            s = cluster_sums[f].get(cid, 0.0)
            c = cluster_counts[f].get(cid, 0)
            means.append((s / c) if c > 0 else 0.0)
        total_means[cid] = sum(means) / (len(means) if means else 1)

    return sorted(total_means.keys(), key=lambda k: total_means[k])

def get_cluster_labels(n_clusters: int, sorted_clusters: List[int]) -> Dict[int, str]:
    """
    Petakan cluster id -> label deskriptif sesuai urutan (rendah→tinggi).
    """
    label_sets = {
        2: ["Rendah", "Tinggi"],
        3: ["Rendah", "Sedang", "Tinggi"],
        4: ["Sangat Rendah", "Rendah", "Tinggi", "Sangat Tinggi"],
        5: ["Sangat Rendah", "Rendah", "Sedang", "Tinggi", "Sangat Tinggi"],
        6: ["Sangat Rendah", "Rendah", "Agak Rendah", "Agak Tinggi", "Tinggi", "Sangat Tinggi"],
        7: ["Sangat Rendah", "Cukup Rendah", "Rendah", "Sedang", "Tinggi", "Cukup Tinggi", "Sangat Tinggi"],
        8: ["Sangat Rendah", "Cukup Rendah", "Rendah", "Agak Rendah", "Agak Tinggi", "Tinggi", "Cukup Tinggi", "Sangat Tinggi"],
        9: ["Sangat Rendah", "Cukup Rendah", "Rendah", "Agak Rendah", "Sedang", "Agak Tinggi", "Tinggi", "Cukup Tinggi", "Sangat Tinggi"],
        10: ["Sangat Rendah", "Cukup Rendah", "Rendah", "Agak Rendah", "Sedikit Rendah", "Sedikit Tinggi",
              "Agak Tinggi", "Tinggi", "Cukup Tinggi", "Sangat Tinggi"],
    }
    labels = label_sets.get(n_clusters, [f"Cluster {i+1}" for i in range(n_clusters)])
    return {cid: labels[i] for i, cid in enumerate(sorted_clusters)}

def apply_descriptive_labels(df, selected_features: List[str], cluster_col: str, n_clusters: int):
    """
    Utility: hitung urutan cluster → buat map label → kembalikan (df_with_labels, labels_map).
    """
    order = compute_cluster_means(df, selected_features, cluster_col)
    labels_map = get_cluster_labels(n_clusters, order)
    df_out = df.copy()
    df_out['Keterangan'] = [labels_map[c] for c in df_out[cluster_col]]
    return df_out, labels_map