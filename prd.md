# PRD — General-Purpose Document Q&A Chatbot (RAG)

## 1. Overview

A general-purpose conversational chatbot: any user uploads one or more documents (PDF, .txt/.md, .docx), and the system builds a knowledge base from them for that session, then answers questions grounded in that content via retrieval-augmented generation.

This is no longer domain-specific (college FAQs) — it works for any document set a user brings: study notes, contracts, research papers, manuals, resumes, whatever.

**Primary purpose:** Portfolio / resume project for a fresher AI Engineer role, demonstrating a complete, understood RAG pipeline including dynamic (runtime) ingestion, not just a static pre-built index.

## 2. Problem Statement

People have documents and want quick, specific answers from them without reading the whole thing or manually searching (Ctrl+F) across multiple files. Tools like ChatPDF/NotebookLM solve this commercially — this project reimplements the core mechanism to demonstrate understanding, not to compete with them.

## 3. Goals

- Let a user upload multiple documents and treat them as a single combined knowledge base for that session
- Support the three target formats (PDF, .txt/.md, .docx) reliably
- Ground every answer in the uploaded content; refuse/hedge when the answer isn't present
- Support multi-turn conversation (follow-ups resolve correctly against the session's knowledge base)
- Ship a simple, clean UI: upload documents, see them listed, ask questions, see sourced answers
- Be fully explainable end-to-end in an interview

## 4. Non-Goals (v1)

- Persistence across sessions/visits — no accounts, no saved libraries. Uploaded documents and their index exist only for the current session and are discarded after (explicitly documented, not an oversight)
- OCR for scanned/image-only PDFs — text-extractable PDFs only
- Real-time collaboration / multi-user shared knowledge bases
- Admin tools, usage analytics, billing, rate limiting
- Handling extremely large documents (100s of pages) gracefully — v1 targets reasonably sized documents (roughly under ~50 pages / a few MB per file); document this limit rather than silently failing on huge files

## 5. Users

- Any user with documents they want to ask questions about — no domain assumption
- Recruiters/interviewers evaluating the project as a portfolio piece

## 6. Core Use Cases

1. User uploads 2–3 documents (mixed formats) → system parses, chunks, and indexes them into one session knowledge base
2. User asks a direct question → system retrieves relevant chunks (possibly from different documents) and answers, citing which document(s) it drew from
3. User asks a follow-up question depending on prior context → system resolves the reference correctly against the session's knowledge base
4. User asks something not covered by any uploaded document → system says so plainly, rather than guessing
5. User adds another document mid-session → system re-indexes to include it in the same knowledge base without losing earlier documents

## 7. Functional Requirements

| ID | Requirement |
|----|-------------|
| FR1 | User can upload one or more files (PDF, .txt, .md, .docx) via the frontend |
| FR2 | Backend parses each format correctly and extracts clean text |
| FR3 | Backend chunks extracted text generically (fixed-size with overlap) and embeds each chunk |
| FR4 | Backend builds/updates a per-session FAISS index plus a chunk metadata store (text + source filename) |
| FR5 | Frontend displays the list of currently uploaded documents in the session, with the ability to see what's active |
| FR6 | User can ask a question via chat; backend retrieves top-k relevant chunks across all session documents |
| FR7 | Backend builds a grounded prompt (retrieved context + conversation history + question) and calls the LLM |
| FR8 | Response includes an answer plus which source document(s) it was drawn from |
| FR9 | System handles out-of-scope questions by clearly stating the answer isn't in the uploaded documents |
| FR10 | Session data (index, documents, history) is scoped per session and cleared when the session ends |

## 8. Success Criteria

- Correctly answers questions that require pulling from a single document, at least 90% on a hand-built test set
- Correctly answers at least 3 questions that require synthesizing information across two different uploaded documents
- Correctly resolves at least 8/10 follow-up questions using session context
- Correctly refuses/hedges on at least 8/10 out-of-scope test questions
- Handles all three supported formats without crashing on reasonably clean, text-based files
- A new user can upload files and get a useful answer without any instructions beyond what's visible in the UI

## 9. Constraints

- Solo developer, learning FastAPI hands-on
- No budget for managed vector DB, cloud storage, or paid infra — FAISS in-memory per session, free-tier hosting
- No accounts/auth in v1 — session identified via a client-side session ID (e.g., stored in browser, sent with each request)
- Timeline: MVP in roughly 2–3 weeks of evenings/weekends (increased from the FAQ-only version due to file parsing and dynamic indexing)

## 10. Risks (acknowledged, not solved in v1)

- **Memory growth**: since indices live in server memory per session with no persistence or expiry logic in the true MVP, many concurrent sessions could exhaust memory on a free-tier host. A basic session expiry/cleanup is planned for later phases, not the initial cut.
- **Parsing failures**: scanned PDFs, password-protected files, or malformed .docx files will fail to extract text — needs a clear error message, not a silent empty result.
- **Large files**: no chunked/streaming upload handling in v1 — very large files may time out or use excessive memory during embedding.
- **Cross-document confusion**: if two documents contain conflicting information (e.g., two versions of the same contract), the system has no way to know which is authoritative — it will retrieve and potentially blend both. Worth calling out as a known limitation, not silently ignoring it.
- **No formal eval framework** beyond a manually maintained test question set.

## 11. Deliverables

- Working web app: upload UI + chat UI, FastAPI backend, deployed with a live link
- GitHub repo with clean structure and README documenting architecture, decisions, and known limitations
- This set of planning docs (PRD, architecture, design, phases) included to demonstrate process
