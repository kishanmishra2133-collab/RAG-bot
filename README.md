# Document Q&A Chatbot (RAG)

A full-stack, general-purpose Retrieval-Augmented Generation (RAG) web application built with **FastAPI**, **FAISS**, and the **Gemini API**.

Users upload one or more documents across multiple formats (PDF, DOCX, Markdown, TXT) which are ingested on-the-fly into a session-scoped in-memory vector index. The conversational chat interface answers user questions grounded strictly in the uploaded materials, with transparent source citations and multi-turn reference resolution.

---

## Architecture & Data Flow

```mermaid
flowchart TD
    subgraph Browser["Browser Client"]
        A[Drag & Drop Upload] -->|POST /upload<br/>files + session_id| B(FastAPI Server)
        C[Chat Interface] -->|POST /chat<br/>question + session_id + history| B
    end

    subgraph Server["FastAPI Backend (Session Scoped)"]
        B --> D{Route}
        D -->|/upload| E[Format Parsers<br/>PDF / DOCX / TXT / MD]
        E --> F[Generic Chunker<br/>fixed-size + overlap]
        F --> G[Gemini Embedder<br/>text-embedding-004]
        G --> H[(In-Memory Session Store<br/>FAISS IndexFlatIP + Metadata)]

        D -->|/chat| I[Query Rewriter<br/>Resolves history pronouns]
        I --> J[Gemini Embedder<br/>text-embedding-004]
        J --> K[FAISS Vector Search<br/>Top-k Cosine Similarity]
        H -.Search.-> K
        K --> L[Extract Excerpts + Source Filenames]
        L --> M[Grounded Prompt Builder]
        M --> N[Gemini 2.5 Flash Generator]
        N --> O[Answer + Source Citations]
    end

    O -->|JSON {answer, sources}| C
```

For full system architecture specifications, see [`architecture.md`](./architecture.md).  
For product requirements and scoping, see [`prd.md`](./prd.md).  
For UI/UX design direction, see [`design.md`](./design.md).  
For project engineering phases, see [`phases.md`](./phases.md).

---

## Key Features

- **Multi-Format Runtime Ingestion**:
  - PDF text extraction via `pypdf` with detection of scanned/unreadable documents.
  - DOCX parsing via `python-docx` covering both body paragraphs and structured table cells.
  - Plain text & Markdown parsing with UTF-8 decoding and Latin-1 fallback.
- **Dynamic In-Memory Knowledge Base**:
  - Client-generated session UUIDs scope every knowledge base to a single session.
  - Incremental vector indexing via `faiss.IndexFlatIP` — upload additional files mid-session without rebuilding from scratch.
  - L2 vector normalization ensures inner products represent exact cosine similarity.
- **Symmetrical Gemini Embedding Pipeline**:
  - Consistent use of `text-embedding-004` (768 dimensions) for both document chunking and runtime search queries.
- **Strict Grounding & Transparent Refusal**:
  - Engineered prompt boundaries instruct Gemini 2.5 Flash to answer solely from retrieved excerpts and explicitly decline unanswerable questions without hallucinating.
- **Conversational Query Rewriting**:
  - Multi-turn follow-ups (e.g., *"How is that replicated?"*) are rewritten into self-contained search queries using prior turns before vector search.
- **Senior-Developer UI & Interactive Canvas**:
  - Two-panel layout (Documents + Chat) with high-contrast, frosted dark aesthetic.
  - Ambient particle background in pure HTML5 Canvas with velocity-oriented elongated particles that gently react to cursor movements.
  - Completely responsive: collapses into a mobile-friendly expandable strip on small screens.

---

## File & Folder Structure

```
document-qa-bot/
├── app/
│   ├── parsers/
│   │   ├── pdf_parser.py       # pypdf text extraction & scanned detection
│   │   ├── docx_parser.py      # python-docx paragraph & table extraction
│   │   └── text_parser.py      # UTF-8 / latin-1 text extraction
│   ├── chunker.py              # Generic fixed-size chunking (~500 tokens) with overlap
│   ├── embedder.py             # Gemini text-embedding-004 wrapper
│   ├── session_store.py        # In-memory FAISS store & TTL session cleanup
│   ├── retriever.py            # Top-k vector similarity search
│   ├── prompt.py               # Grounded prompt templates & context builder
│   ├── llm.py                  # Gemini 2.5 Flash caller & query rewriter
│   ├── models.py               # Pydantic request/response schemas
│   └── main.py                 # FastAPI endpoints & static file serving
├── static/
│   ├── index.html              # Responsive two-panel interface
│   ├── style.css               # Restrained dark aesthetic & layout
│   └── script.js               # Canvas particle animation & client logic
├── tests/
│   ├── sample_docs/            # Realistic test docs (.pdf, .docx, .md, .txt)
│   ├── create_sample_docs.py   # Script to generate sample docs
│   ├── test_pipeline_standalone.py # Phase 1 pipeline verification
│   ├── test_api_endpoints.py   # Phase 2 FastAPI test suite
│   └── test_questions.json     # 16 benchmark test questions
├── architecture.md             # Technical architecture document
├── design.md                   # UI/UX design specifications
├── phases.md                   # Build phases and engineering roadmap
├── prd.md                      # Product requirements document
├── requirements.txt            # Pinned dependencies
├── .env.example                # API key template
├── .gitignore                  # Git ignore rules
└── README.md                   # Project documentation
```

---

## Getting Started

### 1. Clone & Setup Environment

```bash
git clone https://github.com/your-username/document-qa-bot.git
cd document-qa-bot

python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Gemini API Key

Copy the example configuration and add your Gemini API key from [Google AI Studio](https://aistudio.google.com/):

```bash
cp .env.example .env
```

Edit `.env`:
```env
GEMINI_API_KEY=AIzaSy...your_actual_api_key_here
```

### 4. Run Locally

Launch the FastAPI development server with `uvicorn`:

```bash
uvicorn app.main:app --reload --port 8000
```

Open your browser and navigate to:
```
http://localhost:8000
```

---

## Running Tests

Run the standalone pipeline test suite:
```bash
python tests/test_pipeline_standalone.py
```

Run the FastAPI endpoints and session isolation test suite:
```bash
python tests/test_api_endpoints.py
```

Generate new sample test documents:
```bash
python tests/create_sample_docs.py
```

---

## Known Limitations (v1 Scope)

As documented in [`prd.md`](./prd.md) and [`architecture.md`](./architecture.md):

- **In-Memory Sessions (No Persistence)**: Document chunks and FAISS indices exist strictly in server RAM for the duration of the session. Server restarts or host reboots clear all active sessions.
- **No OCR for Scanned Documents**: PDFs must contain extractable text characters. Scanned image-only PDFs are detected and rejected with a descriptive error message.
- **Cross-Document Conflicts**: If two uploaded documents contain contradictory statements (e.g. conflicting versions of a contract), the retriever surfaces both and the LLM synthesizes both without resolving authority.
- **No Authentication / Multi-Tenant Database**: Sessions are identified purely by client-generated UUIDs stored in browser session storage.
- **File Size Target**: Designed for typical business/academic documents (roughly under 50 pages or ~25MB). Extremely large multi-hundred-page files may experience latency during synchronous vector generation.

---

## Interview & Resume Talking Points

1. **Dynamic Ingestion vs. Static RAG**: Explaining how runtime document parsing, sliding-window chunking, batch vector generation, and incremental FAISS indexing work together on-the-fly.
2. **Symmetrical Embedding Guarantee**: Why using `text-embedding-004` at both ingestion and query time is mathematically required for vector dot-product ranking.
3. **Session Scoping & Isolation**: Maintaining distinct vector indexes and parallel metadata arrays per session ID to prevent cross-tenant data leakage in multi-user environments.
4. **Context Injection & Hallucination Mitigation**: How low temperature settings (0.1), explicit boundary instructions, and negative constraint prompts eliminate fabricated citations.
