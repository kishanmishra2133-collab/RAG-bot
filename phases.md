# Phases — Build Plan (General-Purpose Document Q&A)

Stack: Python, FastAPI, FAISS (in-memory, per-session), sentence-transformers (or API embeddings), `pypdf`/`pdfplumber`, `python-docx`, HTML/CSS/JS frontend.

Total estimate: **~28–38 hours**, solo. This is meaningfully more than the FAQ-only version (~20–28 hrs) because of multi-format parsing and dynamic per-session indexing — budget accordingly and don't be discouraged if Phase 1 takes longer than expected.

---

## Phase 0 — Setup & Test Material (~1–2 hrs)

- Set up project structure (see `architecture.md`)
- Install `fastapi`, `uvicorn`, `faiss-cpu`, `sentence-transformers` (or embedding API SDK), your LLM SDK, `pypdf` (or `pdfplumber`), `python-docx`
- Gather 3–4 varied test documents across all three formats (a PDF, a .docx, a .md/.txt) — mix content so some questions require single-document lookup and some require combining info across two documents
- Write a ~15-question test set up front: mix of single-doc questions, cross-document questions, follow-ups, and deliberately out-of-scope questions

**Done when:** you have real test files and a written test set, before any code exists.

---

## Phase 1 — Parsing, Chunking & Embedding (No Web Layer) (~7–10 hrs)

- Write format-specific parsers: PDF, .docx, .txt/.md — each returning clean extracted text, each handling failure explicitly (don't let a bad file crash the whole script)
- Write the generic chunker: fixed-size chunks with overlap, tagging each chunk with its source filename
- Write the embedder and build a FAISS index from a small set of test documents in a throwaway script
- Test retrieval quality by eye: hardcode a question, embed it, search, print the retrieved chunks — confirm they're relevant and correctly attributed to the right source file
- Add the LLM call, build the grounded prompt, print the final answer
- Run your Phase 0 test set through this script manually, note failures (this is expected — chunk size and k value will need tuning)

**Done when:** a script can take multiple uploaded-style files, build a combined index, answer a question, and correctly cite which file(s) it came from.

---

## Phase 2 — FastAPI Backend with Session-Based Indexing (~8–11 hrs, includes FastAPI learning)

- Learn FastAPI basics: routes, Pydantic models, file upload handling (`UploadFile`), running via `uvicorn`
- Implement `session_store.py`: an in-memory dict keyed by `session_id`, holding each session's FAISS index + chunk metadata + document list
- Implement `POST /upload`: accepts multiple files + `session_id`, parses/chunks/embeds them, adds to (or creates) that session's index, returns the updated document list
- Implement `POST /chat`: accepts `session_id`, `question`, `history`; retrieves from that session's index only; returns answer + sources
- Handle the "no documents uploaded yet" case explicitly with a clear response, not a crash
- Test both endpoints via `/docs` or `curl` before building the frontend — confirm a multi-file upload followed by a cross-document question works correctly

**Done when:** you can upload multiple files and chat against them entirely through API calls, with correct session isolation (two different `session_id`s don't see each other's documents).

---

## Phase 3 — Frontend: Upload + Chat UI (~6–9 hrs)

- Build the two-panel layout per `design.md`: document panel + chat panel
- Generate a `session_id` client-side (UUID) on page load, store in a JS variable (or `localStorage`), send with every request
- Implement drag-drop/file-picker upload, show processing state, update the document list on success, show clear errors on failure
- Implement chat UI as before: bubbles, input bar, typing indicator, source citations (now potentially multiple sources per answer)
- Disable/placeholder the chat input until at least one document is uploaded
- Mount static files in FastAPI so everything runs from one server

**Done when:** a new user can land on the page, upload a few files of different formats, and have a working multi-turn conversation grounded in them — entirely through the browser.

---

## Phase 4 — Polish & Resume-Readiness (~6–8 hrs)

- Run your full test set (single-doc, cross-doc, follow-up, out-of-scope questions) against the deployed app, record results honestly
- Tune chunk size/overlap, k value, and system prompt based on real failures
- Add basic session safety: a cap on max documents per session, a max file size, and ideally a simple time-based session eviction so memory doesn't grow unbounded during a demo period
- Write the README: architecture summary, key decisions (why fixed-size chunking here vs Q&A-pair chunking in an earlier iteration, why in-memory session store, why FAISS), known limitations (no persistence, no OCR, cross-document conflicts unresolved), and what you'd change for production
- Deploy to Render/Railway free tier; note in the README if the host spins down idle instances (which would clear sessions)

**Done when:** you have a live link, a clean README, and can explain — out loud, unscripted — exactly what happens from file upload through to a cited answer.

---

## Explicit Non-Phases (v1 — call these out as conscious scope decisions, not gaps)

- Persistent storage / accounts / saved libraries across visits
- OCR for scanned/image-based PDFs
- Per-document search filtering (v1 always searches the combined session knowledge base)
- Automated conflict resolution between documents with contradictory information
- Real concurrency/load handling beyond a basic session cap

Being explicit about these in your README — "here's what I deliberately left out and why" — reads as engineering maturity in an interview, especially for a fresher role where interviewers are gauging judgment as much as raw output.
