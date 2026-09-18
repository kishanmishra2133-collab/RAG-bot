"""
Phase 2 API Endpoint and Session Isolation Tests.
Tests /upload, /chat, session isolation, and edge cases using FastAPI TestClient.
"""
import os
import sys
from fastapi.testclient import TestClient

os.environ.setdefault("ENABLE_MOCK_EMBEDDINGS", "1")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app

client = TestClient(app)
sample_dir = os.path.join(os.path.dirname(__file__), "sample_docs")

def test_chat_without_documents():
    """Chat before uploading any document should return 400 with helpful error."""
    resp = client.post("/chat", json={
        "session_id": "empty-session-123",
        "question": "What is the policy?"
    })
    assert resp.status_code == 400
    assert "No documents uploaded yet" in resp.json()["detail"]
    print("[OK] Empty session chat correctly rejected with 400")

def test_upload_and_chat():
    """Upload multiple files and chat against them."""
    session_id = "test-session-api-1"

    pdf_path = os.path.join(sample_dir, "acme_hr_policy.pdf")
    docx_path = os.path.join(sample_dir, "project_titan_specs.docx")

    with open(pdf_path, "rb") as f_pdf, open(docx_path, "rb") as f_docx:
        files = [
            ("files", ("acme_hr_policy.pdf", f_pdf, "application/pdf")),
            ("files", ("project_titan_specs.docx", f_docx, "application/vnd.openxmlformats-officedocument.wordprocessingml.document"))
        ]
        resp = client.post(
            "/upload",
            data={"session_id": session_id},
            files=files
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == session_id
    assert len(data["documents"]) == 2
    assert data["total_chunks"] >= 2
    print(f"[OK] Uploaded 2 documents successfully, total chunks: {data['total_chunks']}")

    # Check session info
    info_resp = client.get(f"/session/{session_id}")
    assert info_resp.status_code == 200
    assert len(info_resp.json()["documents"]) == 2

    # Query about PDF
    chat_resp = client.post("/chat", json={
        "session_id": session_id,
        "question": "What is the annual PTO allowance?",
        "history": []
    })
    assert chat_resp.status_code == 200
    ans_data = chat_resp.json()
    assert "answer" in ans_data
    assert "sources" in ans_data
    assert len(ans_data["sources"]) > 0
    print(f"[OK] Chat answered: sources = {ans_data['sources']}")

def test_session_isolation():
    """Verify session isolation: Session B cannot retrieve Session A's documents."""
    session_a = "isolation-session-A"
    session_b = "isolation-session-B"

    # Upload only to Session A
    txt_path = os.path.join(sample_dir, "incident_runbook.txt")
    with open(txt_path, "rb") as f_txt:
        files = [("files", ("incident_runbook.txt", f_txt, "text/plain"))]
        resp_a = client.post("/upload", data={"session_id": session_a}, files=files)
    assert resp_a.status_code == 200

    # Session B should have no documents and fail chat
    resp_b_chat = client.post("/chat", json={
        "session_id": session_b,
        "question": "What is the Sev-1 incident escalation protocol?"
    })
    assert resp_b_chat.status_code == 400
    assert "No documents uploaded yet" in resp_b_chat.json()["detail"]

    # Session A should succeed
    resp_a_chat = client.post("/chat", json={
        "session_id": session_a,
        "question": "What is the Sev-1 incident escalation protocol?"
    })
    assert resp_a_chat.status_code == 200
    assert "incident_runbook.txt" in resp_a_chat.json()["sources"]
    print("[OK] Session isolation verified: Session B cannot see Session A's data")

def test_unsupported_file_format():
    """Uploading an unsupported format should return failure in processed_files."""
    session_id = "test-session-unsupported"
    files = [("files", ("malicious.exe", b"binary content", "application/octet-stream"))]
    resp = client.post("/upload", data={"session_id": session_id}, files=files)
    assert resp.status_code == 200
    res = resp.json()["processed_files"][0]
    assert res["status"] == "failed"
    assert "Unsupported format" in res["error"]
    print("[OK] Unsupported format gracefully handled")

if __name__ == "__main__":
    test_chat_without_documents()
    test_upload_and_chat()
    test_session_isolation()
    test_unsupported_file_format()
    print("\nAll FastAPI API and session isolation tests passed successfully!")
