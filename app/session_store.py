"""
In-memory per-session storage for FAISS indices, chunk metadata, and uploaded documents.
Supports incremental indexing (index.add()) without full re-indexing.
Includes thread-safe locking and TTL-based session eviction for memory safety.
"""
import time
import threading
from typing import Dict, List, Any, Optional
import numpy as np
import faiss

SESSION_TTL_SECONDS = 3600  # 1 hour idle eviction
MAX_ACTIVE_SESSIONS = 100

class SessionData:
    def __init__(self, session_id: str):
        self.session_id: str = session_id
        # Inner Product index on normalized vectors = Cosine Similarity
        self.index: Optional[faiss.IndexFlatIP] = None
        self.dim: Optional[int] = None
        # Parallel list of metadata dicts corresponding 1-to-1 with FAISS vector IDs
        self.chunks: List[Dict[str, Any]] = []
        # List of uploaded documents: [{"filename": str, "chunk_count": int, "uploaded_at": float}]
        self.documents: List[Dict[str, Any]] = []
        self.last_active: float = time.time()

    @property
    def ntotal(self) -> int:
        return self.index.ntotal if self.index is not None else 0

    def touch(self):
        self.last_active = time.time()

    def add_document(self, filename: str, chunks: List[Dict[str, Any]], vectors: np.ndarray):
        """
        Incrementally appends vectors and metadata to this session's knowledge base.
        Order is strictly preserved so vector index i maps directly to chunks[i].
        """
        if len(chunks) == 0 or len(vectors) == 0:
            return

        if len(chunks) != len(vectors):
            raise ValueError(
                f"Mismatch: received {len(chunks)} chunks but {len(vectors)} embedding vectors."
            )

        # Lazily initialize FAISS index with the exact dimension of the input vectors
        if self.index is None:
            self.dim = vectors.shape[1]
            self.index = faiss.IndexFlatIP(self.dim)

        # Append vectors to FAISS index
        self.index.add(vectors)
        # Append corresponding metadata to parallel list
        self.chunks.extend(chunks)

        # Update document tracker
        self.documents.append({
            "filename": filename,
            "chunk_count": len(chunks),
            "uploaded_at": time.time()
        })
        self.touch()

    def remove_document(self, filename: str):
        """
        Removes a document from the session.
        """
        self.documents = [d for d in self.documents if d["filename"] != filename]
        # In v1, if clearing documents, reset index
        if len(self.documents) == 0:
            self.index = None
            self.chunks = []
        self.touch()


class SessionStore:
    def __init__(self):
        self._sessions: Dict[str, SessionData] = {}
        self._lock = threading.Lock()

    def get_or_create_session(self, session_id: str) -> SessionData:
        """Retrieves an existing session or initializes a fresh one."""
        with self._lock:
            self._cleanup_expired_sessions()

            if session_id not in self._sessions:
                if len(self._sessions) >= MAX_ACTIVE_SESSIONS:
                    oldest_key = min(self._sessions, key=lambda k: self._sessions[k].last_active)
                    del self._sessions[oldest_key]

                self._sessions[session_id] = SessionData(session_id)

            session = self._sessions[session_id]
            session.touch()
            return session

    def get_session(self, session_id: str) -> Optional[SessionData]:
        """Retrieves a session if it exists, without auto-creating."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session.touch()
            return session

    def clear_session(self, session_id: str) -> bool:
        """Explicitly deletes a session and frees its in-memory index."""
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                return True
            return False

    def _cleanup_expired_sessions(self):
        """Removes sessions that have been idle past SESSION_TTL_SECONDS."""
        now = time.time()
        expired = [
            sid for sid, s in self._sessions.items()
            if (now - s.last_active) > SESSION_TTL_SECONDS
        ]
        for sid in expired:
            del self._sessions[sid]

# Global singleton session store instance
session_store = SessionStore()
