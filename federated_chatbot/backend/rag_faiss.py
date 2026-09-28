import os
import pickle
import numpy as np
import faiss
from typing import List
from sentence_transformers import SentenceTransformer
from PyPDF2 import PdfReader

BASE_INDEX_DIR = "faiss_index"

DOMAINS = {
    "fitness": "data/fitness",
    "mental": "data/mental",
    "academic": "data/academic"
}

EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
embedder = SentenceTransformer(EMBED_MODEL)


def ensure_index_dir():
    os.makedirs(BASE_INDEX_DIR, exist_ok=True)


def text_from_pdf(path: str) -> str:
    reader = PdfReader(path)
    pages = []
    for p in reader.pages:
        t = p.extract_text()
        if t:
            pages.append(t)
    return "\n".join(pages)


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    tokens = text.split()
    chunks = []

    i = 0
    while i < len(tokens):
        chunk = tokens[i:i + chunk_size]
        chunks.append(" ".join(chunk))
        i += chunk_size - overlap

    return chunks


def build_domain_index(domain: str):
    if domain not in DOMAINS:
        raise ValueError("Invalid domain")

    data_dir = DOMAINS[domain]
    docs = []
    meta = []

    for fn in os.listdir(data_dir):
        if not fn.lower().endswith(".pdf"):
            continue

        fullpath = os.path.join(data_dir, fn)
        raw = text_from_pdf(fullpath)

        if not raw.strip():
            continue

        chunks = chunk_text(raw)
        for idx, chunk in enumerate(chunks):
            docs.append(chunk)
            meta.append({"source": fn, "chunk": idx})

    if not docs:
        return 0

    embeddings = embedder.encode(docs, convert_to_numpy=True)
    vector_dim = embeddings.shape[1]

    index = faiss.IndexFlatL2(vector_dim)
    index.add(embeddings)

    ensure_index_dir()
    faiss.write_index(index, os.path.join(BASE_INDEX_DIR, f"{domain}.index"))

    with open(os.path.join(BASE_INDEX_DIR, f"{domain}_meta.pkl"), "wb") as f:
        pickle.dump({"texts": docs, "meta": meta}, f)

    return len(docs)


def load_index(domain: str):
    index_path = os.path.join(BASE_INDEX_DIR, f"{domain}.index")
    meta_path = os.path.join(BASE_INDEX_DIR, f"{domain}_meta.pkl")

    if not (os.path.exists(index_path) and os.path.exists(meta_path)):
        return None, None

    index = faiss.read_index(index_path)
    with open(meta_path, "rb") as f:
        data = pickle.load(f)

    return index, data


def search_domain(query: str, domain: str, top_k: int = 3, threshold: float = 1.1):
    index, data = load_index(domain)
    if index is None:
        return []

    q_emb = embedder.encode([query], convert_to_numpy=True)
    D, I = index.search(q_emb, top_k)

    # Apply similarity threshold
    filtered_results = []
    for dist, idx in zip(D[0], I[0]):
        if dist < threshold:   # lower = more similar
            filtered_results.append(data["texts"][idx])

    return filtered_results
