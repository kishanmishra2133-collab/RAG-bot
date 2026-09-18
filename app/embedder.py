"""
Gemini Embedding module using gemini-embedding-001 / gemini-embedding-2.
Ensures identical embedding model across both document ingestion and query retrieval.
Vectors are L2-normalized so inner product (faiss.IndexFlatIP) equals cosine similarity.
"""
import os
import hashlib
import numpy as np
from typing import List
from dotenv import load_dotenv
from google import genai

load_dotenv(override=True)

# Primary embedding model supported by Gemini API
DEFAULT_EMBEDDING_MODELS = ["gemini-embedding-001", "gemini-embedding-2", "text-embedding-004"]
ACTIVE_EMBEDDING_MODEL = os.getenv("GEMINI_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODELS[0])
EMBEDDING_DIM = 3072  # gemini-embedding-001 default dimension

def _get_api_key() -> str:
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
    return key.strip()

def _get_client() -> genai.Client:
    key = _get_api_key()
    if not key or key == "your_gemini_api_key_here":
        raise ValueError(
            "Gemini API key is not configured. Please provide a valid GEMINI_API_KEY in your .env file."
        )
    return genai.Client(api_key=key)

def _mock_embed(texts: List[str], dim: int = 3072) -> np.ndarray:
    """
    Deterministic pseudo-embedding fallback for offline testing or environments without an active API key.
    Generates a normalized vector based on SHA-256 hash of tokens.
    """
    vectors = []
    for text in texts:
        vec = np.zeros(dim, dtype=np.float32)
        words = text.lower().split()
        if not words:
            words = ["empty"]
        for word in words:
            h = int(hashlib.sha256(word.encode("utf-8")).hexdigest()[:8], 16)
            idx = h % dim
            sign = 1.0 if (h % 2 == 0) else -1.0
            vec[idx] += sign
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        else:
            vec[0] = 1.0
        vectors.append(vec)
    return np.array(vectors, dtype=np.float32)

def embed_texts(texts: List[str], batch_size: int = 64) -> np.ndarray:
    """
    Embeds a list of text strings into normalized float32 vectors.
    
    Args:
        texts: List of text strings to embed.
        batch_size: Maximum texts per Gemini API batch call.
        
    Returns:
        numpy ndarray of shape (len(texts), dim), dtype=float32, L2-normalized.
    """
    global ACTIVE_EMBEDDING_MODEL, EMBEDDING_DIM
    if not texts:
        return np.empty((0, EMBEDDING_DIM), dtype=np.float32)

    key = _get_api_key()
    if os.getenv("ENABLE_MOCK_EMBEDDINGS", "0") == "1" or not key or key == "your_gemini_api_key_here":
        if os.getenv("ENABLE_MOCK_EMBEDDINGS", "0") == "1":
            return _mock_embed(texts, EMBEDDING_DIM)
        if not key or key == "your_gemini_api_key_here":
            raise ValueError(
                "Gemini API key is missing. Please set your GEMINI_API_KEY in .env."
            )

    client = _get_client()
    all_embeddings = []

    models_to_try = [ACTIVE_EMBEDDING_MODEL] + [m for m in DEFAULT_EMBEDDING_MODELS if m != ACTIVE_EMBEDDING_MODEL]
    last_error = None

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        batch_embeddings = None

        for model_name in models_to_try:
            try:
                response = client.models.embed_content(
                    model=model_name,
                    contents=batch,
                )
                batch_embeddings = [emb.values for emb in response.embeddings]
                ACTIVE_EMBEDDING_MODEL = model_name
                if batch_embeddings:
                    EMBEDDING_DIM = len(batch_embeddings[0])
                break
            except Exception as e:
                last_error = e
                continue

        if batch_embeddings is None:
            raise RuntimeError(f"Gemini embedding API call failed across models {models_to_try}: {str(last_error)}")

        all_embeddings.extend(batch_embeddings)

    vectors = np.array(all_embeddings, dtype=np.float32)

    # L2 normalize vectors so dot product (IndexFlatIP) represents cosine similarity
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    normalized_vectors = vectors / norms

    return normalized_vectors.astype(np.float32)

def embed_query(query: str) -> np.ndarray:
    """
    Embeds a single query string using the exact same embedding model as document chunks.
    
    Returns:
        numpy ndarray of shape (1, dim), dtype=float32, L2-normalized.
    """
    return embed_texts([query])
