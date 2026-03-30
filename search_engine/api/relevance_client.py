"""
Relevance Engine Client (X2 Interface)
--------------------------------------
Stub that returns mock geology search results.
When teammates deliver the real relevance engine, replace the body of
`search()` with the actual call — nothing else in the project changes.
"""

from __future__ import annotations

import random

# ---------------------------------------------------------------------------
# Mock document pool — realistic geology pages from the crawled corpus
# ---------------------------------------------------------------------------
_MOCK_DOCS = [
    {
        "doc_id": 1,
        "title": "Plate Tectonics and Continental Drift — USGS",
        "url": "https://www.usgs.gov/science/plate-tectonics",
        "snippet": "Plate tectonics describes the large-scale motion of Earth's lithosphere. The theory explains earthquakes, volcanic activity, and mountain building.",
    },
    {
        "doc_id": 2,
        "title": "Sedimentary Rock Formation Processes",
        "url": "https://www.geosociety.org/sedimentary-rocks",
        "snippet": "Sedimentary rocks form through the deposition and cementation of mineral or organic particles on the Earth's surface, followed by diagenesis.",
    },
    {
        "doc_id": 3,
        "title": "Earthquake Hazard Assessment — Seismic Risk",
        "url": "https://www.usgs.gov/natural-hazards/earthquake-hazards",
        "snippet": "Earthquake hazard maps depict the likelihood of ground shaking across regions, guiding building codes and emergency preparedness.",
    },
    {
        "doc_id": 4,
        "title": "Volcanic Eruptions: Types and Mechanisms",
        "url": "https://www.usgs.gov/volcanoes/eruption-types",
        "snippet": "Volcanic eruptions range from effusive lava flows to explosive pyroclastic events. The eruption style depends on magma composition and gas content.",
    },
    {
        "doc_id": 5,
        "title": "Mineral Identification and Classification Guide",
        "url": "https://opengeology.org/mineralogy",
        "snippet": "Minerals are classified by chemical composition and crystal structure. Key physical properties include hardness, luster, cleavage, and specific gravity.",
    },
    {
        "doc_id": 6,
        "title": "Stratigraphy: Reading the Rock Record",
        "url": "https://www.geosociety.org/stratigraphy",
        "snippet": "Stratigraphy studies rock layers and their chronological relationships, using principles of superposition, cross-cutting, and faunal succession.",
    },
    {
        "doc_id": 7,
        "title": "Metamorphic Rocks and Processes",
        "url": "https://opengeology.org/metamorphic",
        "snippet": "Metamorphism transforms existing rocks through heat, pressure, and chemical fluids. Common metamorphic rocks include slate, schist, and gneiss.",
    },
    {
        "doc_id": 8,
        "title": "Igneous Petrology: Magma to Rock",
        "url": "https://pubs.geoscienceworld.org/petrology",
        "snippet": "Igneous rocks crystallize from molten magma or lava. Texture and mineral composition depend on cooling rate and chemical composition of the melt.",
    },
    {
        "doc_id": 9,
        "title": "Geologic Time Scale and Dating Methods",
        "url": "https://www.geosociety.org/geochronology",
        "snippet": "Radiometric dating uses the decay of isotopes to determine absolute ages of rocks. The geologic time scale spans 4.6 billion years of Earth history.",
    },
    {
        "doc_id": 10,
        "title": "Tectonic Faults: Types and Earthquake Generation",
        "url": "https://www.usgs.gov/science/faults",
        "snippet": "Faults are fractures where rocks on either side have moved. Normal, reverse, and strike-slip faults each produce distinct seismic signatures.",
    },
]


def search(query: str, model: str = "vector") -> dict:
    """
    Search the relevance engine.

    Parameters
    ----------
    query : str
        User search query.
    model : str
        One of: vector, pagerank, hits, combined.

    Returns
    -------
    dict with keys:
        source  — the model name used
        documents — list of {doc_id, title, url, snippet, score, rank}
    """
    # --- STUB: replace this block with real X2 call ---
    query_lower = query.lower()
    scored = []
    for doc in _MOCK_DOCS:
        text = f"{doc['title']} {doc['snippet']}".lower()
        # Simple keyword overlap scoring
        terms = query_lower.split()
        overlap = sum(1 for t in terms if t in text)
        if overlap == 0:
            base = random.uniform(0.05, 0.25)
        else:
            base = overlap / max(len(terms), 1) * random.uniform(0.6, 0.95)

        # Model-specific score variation
        model_bump = {
            "vector": random.uniform(0.0, 0.1),
            "pagerank": random.uniform(0.02, 0.15),
            "hits": random.uniform(0.0, 0.12),
            "combined": random.uniform(0.05, 0.18),
        }.get(model, 0.0)

        scored.append({**doc, "score": round(base + model_bump, 4)})

    scored.sort(key=lambda d: d["score"], reverse=True)
    for rank, doc in enumerate(scored, start=1):
        doc["rank"] = rank

    return {"source": model, "documents": scored}
