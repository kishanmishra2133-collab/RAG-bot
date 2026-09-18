"""
Phase 1 Standalone Pipeline Verification.
Tests parser extraction, chunking, embedding, FAISS indexing, retrieval, and citation.
"""
import os
import sys

os.environ.setdefault("ENABLE_MOCK_EMBEDDINGS", "1")

# Ensure repo root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.parsers.pdf_parser import extract_text_from_pdf
from app.parsers.docx_parser import extract_text_from_docx
from app.parsers.text_parser import extract_text_from_txt
from app.chunker import chunk_text
from app.embedder import embed_texts, embed_query
from app.session_store import SessionData
from app.retriever import retrieve_relevant_chunks
from app.llm import generate_answer

def test_full_pipeline():
    sample_dir = os.path.join(os.path.dirname(__file__), "sample_docs")
    session = SessionData(session_id="test-session-phase1")

    # 1. Test PDF extraction
    pdf_path = os.path.join(sample_dir, "acme_hr_policy.pdf")
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()
    pdf_text = extract_text_from_pdf(pdf_bytes, "acme_hr_policy.pdf")
    assert "Annual Paid Time Off" in pdf_text, "Failed to extract PDF content"
    print(f"[OK] PDF Parser: Extracted {len(pdf_text)} characters")

    # 2. Test DOCX extraction
    docx_path = os.path.join(sample_dir, "project_titan_specs.docx")
    with open(docx_path, "rb") as f:
        docx_bytes = f.read()
    docx_text = extract_text_from_docx(docx_bytes, "project_titan_specs.docx")
    assert "Project Titan" in docx_text, "Failed to extract DOCX content"
    print(f"[OK] DOCX Parser: Extracted {len(docx_text)} characters")

    # 3. Test Markdown extraction
    md_path = os.path.join(sample_dir, "quarterly_financials.md")
    with open(md_path, "rb") as f:
        md_bytes = f.read()
    md_text = extract_text_from_txt(md_bytes, "quarterly_financials.md")
    assert "Q3 2024 Financial Performance" in md_text, "Failed to extract MD content"
    print(f"[OK] MD Parser: Extracted {len(md_text)} characters")

    # 4. Test Plain Text extraction
    txt_path = os.path.join(sample_dir, "incident_runbook.txt")
    with open(txt_path, "rb") as f:
        txt_bytes = f.read()
    txt_text = extract_text_from_txt(txt_bytes, "incident_runbook.txt")
    assert "INCIDENT RUNBOOK" in txt_text, "Failed to extract TXT content"
    print(f"[OK] TXT Parser: Extracted {len(txt_text)} characters")

    # 5. Test Generic Chunking
    docs = [
        ("acme_hr_policy.pdf", pdf_text),
        ("project_titan_specs.docx", docx_text),
        ("quarterly_financials.md", md_text),
        ("incident_runbook.txt", txt_text)
    ]

    total_chunks = 0
    for filename, text in docs:
        chunks = chunk_text(text, filename)
        assert len(chunks) > 0, f"No chunks generated for {filename}"
        total_chunks += len(chunks)
        # Embed and index
        vectors = embed_texts([c["text"] for c in chunks])
        session.add_document(filename, chunks, vectors)

    print(f"[OK] Chunker & Embedder: Indexed {total_chunks} chunks across 4 documents")
    assert session.index.ntotal == total_chunks, "Index size mismatch"
    assert len(session.chunks) == total_chunks, "Metadata list size mismatch"

    # 6. Test Retrieval: Single-doc query
    q1 = "What is the standard annual paid time off (PTO) policy?"
    q1_vec = embed_query(q1)
    retrieved_q1 = retrieve_relevant_chunks(session, q1_vec, top_k=2)
    assert len(retrieved_q1) > 0
    assert any("acme_hr_policy.pdf" == c["source_filename"] for c in retrieved_q1)
    print(f"[OK] Retrieval (Single Doc): Top hit from '{retrieved_q1[0]['source_filename']}'")

    # 7. Test Retrieval: Cross-document query
    q2 = "What lead architect is responsible for deployment and incident runbooks?"
    q2_vec = embed_query(q2)
    retrieved_q2 = retrieve_relevant_chunks(session, q2_vec, top_k=3)
    sources_q2 = {c["source_filename"] for c in retrieved_q2}
    print(f"[OK] Retrieval (Cross Doc): Sources retrieved: {sources_q2}")

    # 8. Test Answer Generation & Source Citations
    ans_result = generate_answer(q1, retrieved_q1)
    assert "answer" in ans_result
    assert "sources" in ans_result
    print(f"[OK] Answer Generation: Citations = {ans_result['sources']}")
    print(f"    Sample Answer: {ans_result['answer'][:120]}...")

    print("\nPhase 1 Pipeline verification completed successfully!")

if __name__ == "__main__":
    test_full_pipeline()
