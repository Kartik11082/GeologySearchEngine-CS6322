import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import MiniBatchKMeans, Birch, AgglomerativeClustering
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import Normalizer


DATA_FILE = Path("clustering/data/pages.jsonl")
OUTPUT_DIR = Path("clustering/output")

MAX_DOCS = None               # None = use all valid documents
N_CLUSTERS = 20               # more separation than 10
MAX_FEATURES = 5000

# Dimensionality reduction
SVD_COMPONENTS = 200

# BIRCH compression
BIRCH_THRESHOLD = 0.35        # higher than 0.2 to reduce centroid count
BIRCH_BRANCHING_FACTOR = 50


def clean_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def load_pages(file_path: Path, max_docs=None):
    documents = []
    meta = []

    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            if max_docs is not None and len(documents) >= max_docs:
                break

            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            if obj.get("status") != 200:
                continue

            text = obj.get("text", "")
            title = obj.get("title", "")
            url = obj.get("url", "")

            if not text or not url:
                continue

            combined = clean_text(f"{title} {text}")
            if len(combined.split()) < 20:
                continue

            documents.append(combined)
            meta.append({
                "url": url,
                "title": title
            })

    return documents, meta


def save_cluster_csv(meta, labels, output_path: Path, cluster_col: str):
    df = pd.DataFrame({
        "url": [m["url"] for m in meta],
        "title": [m["title"] for m in meta],
        cluster_col: labels
    })
    df.to_csv(output_path, index=False)
    print(f"Saved {output_path}")


def compute_birch_centroids(X_reduced: np.ndarray, birch_labels: np.ndarray):
    unique_labels = np.unique(birch_labels)
    unique_labels = unique_labels[unique_labels >= 0]

    centroids = []
    label_to_index = {}

    for idx, birch_label in enumerate(unique_labels):
        points = X_reduced[birch_labels == birch_label]
        centroid = points.mean(axis=0)
        centroids.append(centroid)
        label_to_index[int(birch_label)] = idx

    centroids = np.vstack(centroids)
    return centroids, label_to_index


def filter_zero_centroids(centroids: np.ndarray, label_to_index: dict, eps: float = 1e-12):
    norms = np.linalg.norm(centroids, axis=1)
    keep_mask = norms > eps
    filtered_centroids = centroids[keep_mask]

    filtered_old_indices = np.where(keep_mask)[0]

    old_index_to_new_index = {
        int(old_idx): int(new_idx)
        for new_idx, old_idx in enumerate(filtered_old_indices)
    }

    new_label_to_index = {}
    for birch_label, old_idx in label_to_index.items():
        if old_idx in old_index_to_new_index:
            new_label_to_index[birch_label] = old_index_to_new_index[old_idx]

    return filtered_centroids, filtered_old_indices, new_label_to_index


def normalize_rows(X: np.ndarray, eps: float = 1e-12):
    norms = np.linalg.norm(X, axis=1, keepdims=True)
    norms = np.maximum(norms, eps)
    return X / norms


def map_birch_to_final_labels(
    birch_labels: np.ndarray,
    label_to_index: dict,
    centroid_final_labels: np.ndarray
):
    final_doc_labels = []

    for b_label in birch_labels:
        if b_label < 0:
            final_doc_labels.append(-1)
            continue

        if int(b_label) not in label_to_index:
            final_doc_labels.append(-1)
            continue

        centroid_idx = label_to_index[int(b_label)]
        final_label = int(centroid_final_labels[centroid_idx])
        final_doc_labels.append(final_label)

    return np.array(final_doc_labels)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading pages...")
    documents, meta = load_pages(DATA_FILE, MAX_DOCS)
    print(f"Loaded {len(documents)} documents")

    print("\nVectorizing with TF-IDF...")
    vectorizer = TfidfVectorizer(
        stop_words="english",
        max_features=MAX_FEATURES,
        min_df=2,
        max_df=0.8
    )
    X = vectorizer.fit_transform(documents)
    print("TF-IDF shape:", X.shape)

    # ---------------------------------------------------
    # 1. Flat clustering: MiniBatchKMeans on all data
    # ---------------------------------------------------
    print("\nRunning MiniBatchKMeans on all documents...")
    kmeans = MiniBatchKMeans(
        n_clusters=N_CLUSTERS,
        random_state=42,
        batch_size=1024,
        n_init=10
    )
    kmeans_labels = kmeans.fit_predict(X)

    save_cluster_csv(
        meta,
        kmeans_labels,
        OUTPUT_DIR / "kmeans_clusters.csv",
        "flat_cluster"
    )

    # ---------------------------------------------------
    # 2. Reduce dimensions
    # ---------------------------------------------------
    print(f"\nReducing dimensions with TruncatedSVD to {SVD_COMPONENTS} components...")
    svd = TruncatedSVD(n_components=SVD_COMPONENTS, random_state=42)
    normalizer = Normalizer(copy=False)
    lsa = make_pipeline(svd, normalizer)

    X_reduced = lsa.fit_transform(X)
    print("Reduced matrix shape:", X_reduced.shape)

    # ---------------------------------------------------
    # 3. BIRCH compression
    # ---------------------------------------------------
    print("\nRunning BIRCH on reduced vectors...")
    birch = Birch(
        threshold=BIRCH_THRESHOLD,
        branching_factor=BIRCH_BRANCHING_FACTOR,
        n_clusters=None
    )
    birch_labels = birch.fit_predict(X_reduced)

    n_birch_clusters = len(set(birch_labels)) - (1 if -1 in birch_labels else 0)
    print(f"BIRCH produced {n_birch_clusters} subclusters")

    save_cluster_csv(
        meta,
        birch_labels,
        OUTPUT_DIR / "birch_subclusters.csv",
        "birch_cluster"
    )

    # ---------------------------------------------------
    # 4. Compute BIRCH centroids
    # ---------------------------------------------------
    print("\nComputing centroids for BIRCH subclusters...")
    centroids, label_to_index = compute_birch_centroids(X_reduced, birch_labels)
    print("Original centroid matrix shape:", centroids.shape)

    print("Filtering zero / near-zero centroids...")
    centroids, _, label_to_index = filter_zero_centroids(centroids, label_to_index)
    print("Filtered centroid matrix shape:", centroids.shape)

    print("Normalizing centroids for cosine distance...")
    centroids = normalize_rows(centroids)

    # ---------------------------------------------------
    # 5. Agglomerative Average on BIRCH centroids
    # ---------------------------------------------------
    print("\nRunning Agglomerative Clustering (average linkage, cosine metric) on BIRCH centroids...")
    try:
        agg_average = AgglomerativeClustering(
            n_clusters=N_CLUSTERS,
            linkage="average",
            metric="cosine"
        )
    except TypeError:
        agg_average = AgglomerativeClustering(
            n_clusters=N_CLUSTERS,
            linkage="average",
            affinity="cosine"
        )

    agg_average_centroid_labels = agg_average.fit_predict(centroids)

    agg_average_doc_labels = map_birch_to_final_labels(
        birch_labels,
        label_to_index,
        agg_average_centroid_labels
    )

    save_cluster_csv(
        meta,
        agg_average_doc_labels,
        OUTPUT_DIR / "agg_average_mapped_clusters.csv",
        "agg_average_cluster"
    )

    # ---------------------------------------------------
    # 6. Agglomerative Complete on BIRCH centroids
    # ---------------------------------------------------
    print("\nRunning Agglomerative Clustering (complete linkage, cosine metric) on BIRCH centroids...")
    try:
        agg_complete = AgglomerativeClustering(
            n_clusters=N_CLUSTERS,
            linkage="complete",
            metric="cosine"
        )
    except TypeError:
        agg_complete = AgglomerativeClustering(
            n_clusters=N_CLUSTERS,
            linkage="complete",
            affinity="cosine"
        )

    agg_complete_centroid_labels = agg_complete.fit_predict(centroids)

    agg_complete_doc_labels = map_birch_to_final_labels(
        birch_labels,
        label_to_index,
        agg_complete_centroid_labels
    )

    save_cluster_csv(
        meta,
        agg_complete_doc_labels,
        OUTPUT_DIR / "agg_complete_mapped_clusters.csv",
        "agg_complete_cluster"
    )

    # ---------------------------------------------------
    # 7. Combined output
    # ---------------------------------------------------
    print("\nSaving combined cluster assignments...")
    combined_df = pd.DataFrame({
        "url": [m["url"] for m in meta],
        "title": [m["title"] for m in meta],
        "flat_cluster": kmeans_labels,
        "birch_cluster": birch_labels,
        "agg_average_cluster": agg_average_doc_labels,
        "agg_complete_cluster": agg_complete_doc_labels
    })
    combined_df.to_csv(OUTPUT_DIR / "combined_clusters_all_methods.csv", index=False)
    print(f"Saved {OUTPUT_DIR / 'combined_clusters_all_methods.csv'}")

    # ---------------------------------------------------
    # 8. Sample output
    # ---------------------------------------------------
    print("\nSample cluster assignments:")
    for i in range(min(10, len(meta))):
        print(
            f"{meta[i]['url']} | "
            f"Flat={kmeans_labels[i]} | "
            f"BIRCH={birch_labels[i]} | "
            f"AggAvg={agg_average_doc_labels[i]} | "
            f"AggComplete={agg_complete_doc_labels[i]}"
        )

    print("\nDone. All clustering methods completed.")


if __name__ == "__main__":
    main()