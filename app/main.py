"""
FastAPI application for General-Purpose Document Q&A (RAG).
Handles document uploads, incremental session indexing, retrieval, and grounded chat generation.
"""
import os
from typing import List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.models import (
    ChatRequest,
    ChatResponse,
    UploadResponse,
    FileProcessResult,
    DocumentInfo,
    SessionInfoResponse
)
from app.parsers.pdf_parser import extract_text_from_pdf
from app.parsers.docx_parser import extract_text_from_docx
from app.parsers.text_parser import extract_text_from_txt
from app.chunker import chunk_text
from app.embedder import embed_texts, embed_query
from app.session_store import session_store
from app.retriever import retrieve_relevant_chunks
from app.llm import rewrite_query_if_needed, generate_answer

app = FastAPI(
    title="Document Q&A RAG Bot",
    description="Dynamic per-session RAG knowledge base powered by Gemini & FAISS",
    version="1.0.0"
)

# Enable CORS for local development and external hosting
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}

def _extract_text(filename: str, file_bytes: bytes) -> str:
    """Dispatches file bytes to format-specific parser."""
    ext = os.path.splitext(filename)[1].lower()
    if ext == ".pdf":
        return extract_text_from_pdf(file_bytes, filename)
    elif ext == ".docx":
        return extract_text_from_docx(file_bytes, filename)
    elif ext in [".txt", ".md"]:
        return extract_text_from_txt(file_bytes, filename)
    else:
        raise ValueError(
            f"Unsupported file format '{ext}'. Only PDF, .docx, .txt, and .md files are supported."
        )

@app.get("/health")
def health_check():
    """Health check endpoint for host pinging."""
    return {"status": "ok", "service": "document-qa-bot"}

@app.post("/upload", response_model=UploadResponse)
async def upload_documents(
    session_id: str = Form(...),
    files: List[UploadFile] = File(...)
):
    """
    Accepts one or more files and a session_id.
    Parses, chunks, embeds, and adds vectors to the session's FAISS index.
    """
    session_id = session_id.strip()
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A valid non-empty 'session_id' is required."
        )

    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files were provided for upload."
        )

    session = session_store.get_or_create_session(session_id)
    results: List[FileProcessResult] = []

    for upload_file in files:
        filename = upload_file.filename or "uploaded_file"
        ext = os.path.splitext(filename)[1].lower()

        if ext not in SUPPORTED_EXTENSIONS:
            results.append(FileProcessResult(
                filename=filename,
                status="failed",
                error=f"Unsupported format '{ext}'. Allowed: .pdf, .docx, .txt, .md"
            ))
            continue

        try:
            file_bytes = await upload_file.read()
            # 1. Parse text from document
            text = _extract_text(filename, file_bytes)

            # 2. Chunk generic text
            chunks = chunk_text(text, source_filename=filename)
            if not chunks:
                results.append(FileProcessResult(
                    filename=filename,
                    status="failed",
                    error="No textual content could be extracted."
                ))
                continue

            # 3. Embed chunks using Gemini text-embedding-004
            texts_to_embed = [c["text"] for c in chunks]
            vectors = embed_texts(texts_to_embed)

            # 4. Incrementally index into session FAISS index
            session.add_document(filename, chunks, vectors)

            results.append(FileProcessResult(
                filename=filename,
                status="success",
                chunks=len(chunks)
            ))
        except Exception as e:
            results.append(FileProcessResult(
                filename=filename,
                status="failed",
                error=str(e)
            ))

    doc_infos = [
        DocumentInfo(filename=d["filename"], chunk_count=d["chunk_count"])
        for d in session.documents
    ]

    success_count = sum(1 for r in results if r.status == "success")
    msg = f"Processed {len(files)} file(s): {success_count} indexed successfully."

    return UploadResponse(
        session_id=session_id,
        processed_files=results,
        documents=doc_infos,
        total_chunks=session.index.ntotal,
        message=msg
    )

@app.post("/chat", response_model=ChatResponse)
def chat_with_documents(request: ChatRequest):
    """
    Accepts a user question, session_id, and prior conversation history.
    Retrieves top chunks from the session's FAISS index and generates a grounded response.
    """
    session = session_store.get_session(request.session_id)
    if not session or session.index.ntotal == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No documents uploaded yet for this session. Please upload a document first to get started."
        )

    # Convert Pydantic chat history to list of dicts
    history_dicts = [{"role": msg.role, "content": msg.content} for msg in request.history]

    # 1. Conversational Query Rewriting (if history is non-empty)
    search_query = rewrite_query_if_needed(request.question, history_dicts)

    # 2. Embed Search Query using identical model
    query_vector = embed_query(search_query)

    # 3. Retrieve top-k relevant chunks from session FAISS index
    retrieved_chunks = retrieve_relevant_chunks(session, query_vector, top_k=4)

    # 4. Grounded answer generation via Gemini LLM
    generation_result = generate_answer(
        question=request.question,
        chunks=retrieved_chunks,
        history=history_dicts
    )

    return ChatResponse(
        answer=generation_result["answer"],
        sources=generation_result["sources"]
    )

@app.get("/session/{session_id}", response_model=SessionInfoResponse)
def get_session_info(session_id: str):
    """Returns active documents and chunk count for the requested session."""
    session = session_store.get_session(session_id)
    if not session:
        return SessionInfoResponse(session_id=session_id, documents=[], total_chunks=0)

    doc_infos = [
        DocumentInfo(filename=d["filename"], chunk_count=d["chunk_count"])
        for d in session.documents
    ]
    return SessionInfoResponse(
        session_id=session_id,
        documents=doc_infos,
        total_chunks=session.index.ntotal
    )

@app.delete("/session/{session_id}")
def clear_session_endpoint(session_id: str):
    """Resets and deletes a session knowledge base."""
    deleted = session_store.clear_session(session_id)
    return {"session_id": session_id, "cleared": deleted}

# Static file serving
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/")
    def serve_ui():
        return FileResponse(os.path.join(static_dir, "index.html"))
