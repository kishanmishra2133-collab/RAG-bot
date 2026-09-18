# Design — Visual & Interaction Design

## 1. Design Philosophy

Unchanged from before: calm, restrained, intentional — "senior developer's side project," not a flashy consumer app. The addition of file upload should feel like a natural extension of that same quiet interface, not a bolted-on widget.

Avoid: gradient backgrounds, generic bot emoji avatars, bouncy oversized chat bubbles, cluttered upload zones with too much visual noise (progress bars with excessive animation, celebratory "upload complete!" confetti, etc.)

## 2. Layout

Two-panel layout on desktop, stacked on mobile:

- **Left/top panel — Documents**: a compact list of uploaded files with a simple "+" or drag-drop zone above it. Each file shows its name, format icon (simple, not skeuomorphic), and a small remove (×) button. A subtle "processing..." state appears while a newly uploaded file is being parsed/embedded.
- **Right/bottom panel — Chat**: same chat interface as the FAQ version — scrolling message history, input bar pinned at the bottom.

On mobile, stack vertically: documents panel collapses into a small expandable strip at the top ("3 documents uploaded ▾") so the chat area still gets most of the screen.

## 3. Visual Direction (unchanged core, extended)

**Colors, typography, chat bubbles**: same as before — one neutral base, one muted accent, one typeface with two weights, minimal shadows, subtle fade-ins rather than bouncy animations. See prior direction: off-white or dark-neutral background, near-black/near-white text, muted secondary gray for metadata.

**New: Document panel styling**
- File rows: plain text filename + small format tag (e.g., "PDF" in a tiny muted badge), not large file-type icons — keep it text-forward and quiet
- Upload zone: a simple dashed-border rectangle with "Drop files here or click to upload" — no illustration, no icon-heavy graphic
- Processing state: a small inline spinner or pulsing dot next to the filename, not a full progress bar (you likely won't have real byte-level progress anyway — don't fake precision you don't have)
- Once processed, the file row settles into its final quiet state (just the name + tag)

**Source citations in chat** (updated for multi-document case)
- When an answer draws from multiple documents, list them compactly: "Sources: Fee_Policy.pdf, Notes.docx" in the same small muted style used before — don't create a heavy citation card for this, a single small line is enough

## 4. Empty & Edge States

- **No documents uploaded yet**: chat input should be disabled or show a placeholder like "Upload a document to get started" rather than letting the user ask into a void and get a confusing empty-context answer
- **Unsupported file type**: clear, calm inline message near the upload zone ("Only PDF, .txt, .md, and .docx are supported") — not a jarring browser alert
- **Parsing failure** (e.g., scanned PDF): the file row should show a small error state ("Couldn't read this file") instead of pretending it succeeded
- **No-answer state**: unchanged from before — presented plainly as a valid answer, not styled as an error
- **Session note**: since sessions aren't persisted, consider a small, unobtrusive note near the upload panel like "Documents are only kept for this session" — sets honest expectations without being an alarming disclaimer banner

## 5. Micro-interactions

- Same restrained approach as before: fade-ins over bounces, typing indicator over spinners for chat, disabled send button during a pending response
- New: drag-over state on the upload zone (border color shifts slightly on drag-hover) — small, functional feedback, not decorative

## 6. What to Explicitly Leave Out (v1)

- No file preview/viewer pane (viewing the PDF itself inline) — out of scope, adds real complexity for limited resume-project value
- No per-document toggle ("only search this document") — v1 treats all uploaded documents as one combined knowledge base, per your scoping decision; a per-document filter is a reasonable "future work" callout
- No drag-to-reorder documents, no folders/organization — a flat list is enough at this scale
- No dark/light toggle — pick one and execute it well

## 7. Reference Feel

Still: a well-designed internal tool or docs-search experience, not a consumer chat app. Think of how a clean file-upload + search tool would look in a well-built SaaS product's settings page — plain, legible, no unnecessary ornamentation. The upload panel should feel like it belongs to the same design system as the chat panel, not like a different component library got pasted in next to it.
