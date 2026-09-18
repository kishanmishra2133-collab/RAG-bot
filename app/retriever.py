"""
Retriever module for querying a session's FAISS index with normalized query embeddings.
Scoped strictly to the provided session data.
"""
from typing import List, Dict, Any
import numpy as np
from app.session_store import SessionData

def retrieve_relevant_chunks(
    session: SessionData,
    query_vector: np.ndarray,
    top_k: int = 4
) -> List[Dict[str, Any]]:
    """
    Searches the session's FAISS index for the top-k most similar chunks.
    
    Args:
        session: The active SessionData object.
        query_vector: Normalized query embedding of shape (1, dim).
        top_k: Number of chunks to retrieve.
        
    Returns:
        List of retrieved chunk dictionaries with text, source_filename, and similarity score.
    """
    if session.ntotal == 0 or session.index is None or len(session.chunks) == 0:
        return []

    # FAISS search requires float32 contiguous array
    query_arr = np.ascontiguousarray(query_vector, dtype=np.float32)
    k = min(top_k, session.ntotal)

    scores, indices = session.index.search(query_arr, k)

    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx < 0 or idx >= len(session.chunks):
            continue
        chunk = dict(session.chunks[idx])
        chunk["similarity_score"] = float(score)
        results.append(chunk)

    return results
