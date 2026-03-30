"""
Clustering Client (X4 Interface)
---------------------------------
Stub that returns mock clustered results.
When teammates deliver X4, replace `get_clusters()` body with real call.
"""

from __future__ import annotations


# Mock cluster structure keyed by broad geology topics
_MOCK_CLUSTERS = {
    "Tectonics & Seismology": [
        {
            "doc_id": 1,
            "title": "Plate Tectonics and Continental Drift — USGS",
            "url": "https://www.usgs.gov/science/plate-tectonics",
            "snippet": "Plate tectonics describes the large-scale motion of Earth's lithosphere.",
            "score": 0.92,
        },
        {
            "doc_id": 3,
            "title": "Earthquake Hazard Assessment — Seismic Risk",
            "url": "https://www.usgs.gov/natural-hazards/earthquake-hazards",
            "snippet": "Earthquake hazard maps depict the likelihood of ground shaking.",
            "score": 0.88,
        },
        {
            "doc_id": 10,
            "title": "Tectonic Faults: Types and Earthquake Generation",
            "url": "https://www.usgs.gov/science/faults",
            "snippet": "Faults are fractures where rocks on either side have moved.",
            "score": 0.85,
        },
    ],
    "Petrology & Mineralogy": [
        {
            "doc_id": 5,
            "title": "Mineral Identification and Classification Guide",
            "url": "https://opengeology.org/mineralogy",
            "snippet": "Minerals are classified by chemical composition and crystal structure.",
            "score": 0.90,
        },
        {
            "doc_id": 8,
            "title": "Igneous Petrology: Magma to Rock",
            "url": "https://pubs.geoscienceworld.org/petrology",
            "snippet": "Igneous rocks crystallize from molten magma or lava.",
            "score": 0.87,
        },
        {
            "doc_id": 7,
            "title": "Metamorphic Rocks and Processes",
            "url": "https://opengeology.org/metamorphic",
            "snippet": "Metamorphism transforms existing rocks through heat and pressure.",
            "score": 0.84,
        },
    ],
    "Stratigraphy & Geochronology": [
        {
            "doc_id": 6,
            "title": "Stratigraphy: Reading the Rock Record",
            "url": "https://www.geosociety.org/stratigraphy",
            "snippet": "Stratigraphy studies rock layers and their chronological relationships.",
            "score": 0.89,
        },
        {
            "doc_id": 9,
            "title": "Geologic Time Scale and Dating Methods",
            "url": "https://www.geosociety.org/geochronology",
            "snippet": "Radiometric dating determines absolute ages of rocks.",
            "score": 0.86,
        },
    ],
    "Volcanology": [
        {
            "doc_id": 4,
            "title": "Volcanic Eruptions: Types and Mechanisms",
            "url": "https://www.usgs.gov/volcanoes/eruption-types",
            "snippet": "Volcanic eruptions range from effusive lava flows to explosive events.",
            "score": 0.91,
        },
    ],
}


def get_clusters(query: str) -> list[dict]:
    """
    Return clustered search results.

    Parameters
    ----------
    query : str
        User search query.

    Returns
    -------
    list of dicts, each with:
        cluster_label — human-readable cluster name
        documents     — list of docs in this cluster
    """
    # --- STUB: replace with real X4 call ---
    clusters = []
    for label, docs in _MOCK_CLUSTERS.items():
        clusters.append({"cluster_label": label, "documents": docs})
    return clusters
