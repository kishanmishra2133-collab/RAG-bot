"""
Prompt templates and context builders for grounded RAG generation and query rewriting.
Enforces strict grounding and transparent refusal when context lacks required information.
"""
from typing import List, Dict, Any

GROUNDED_SYSTEM_INSTRUCTION = """You are a precise, reliable document Q&A assistant.
Your job is to answer the user's question accurately based ONLY on the provided context excerpts from their uploaded documents.

CRITICAL RULES:
1. Base your answer strictly on the provided context excerpts. Do not invent, extrapolate, or bring in outside knowledge.
2. If the context does not contain enough information to answer the question, clearly and politely state: "The uploaded documents do not contain information to answer this question." Do not attempt to guess or hallucinate.
3. Be direct, concise, and professional.
4. When synthesizing facts across multiple documents, present the combined facts coherently.
5. Do not include fabricated citations. The backend will attach source file tags based on retrieved passages."""

QUERY_REWRITE_SYSTEM_INSTRUCTION = """You are a conversational query rewriter for a document search engine.
Given the recent chat history and the user's latest question, rewrite the latest question into a single, standalone search query that resolves all pronouns (e.g. 'it', 'they', 'his', 'that project') and implicit references.

RULES:
- If the question is already clear and self-contained, return it unchanged.
- Do not answer the question; only output the standalone rewritten question.
- Do not add conversational preamble, greetings, or explanations."""

def build_context_block(chunks: List[Dict[str, Any]]) -> str:
    """
    Formats retrieved chunks into a clean, structured context string with source document tags.
    """
    if not chunks:
        return "No relevant excerpts found in the uploaded documents."

    formatted_parts = []
    for i, chunk in enumerate(chunks, 1):
        source = chunk.get("source_filename", "Unknown Document")
        text = chunk.get("text", "").strip()
        formatted_parts.append(
            f"--- Excerpt {i} [Source Document: {source}] ---\n{text}"
        )

    return "\n\n".join(formatted_parts)

def build_grounded_rag_prompt(
    question: str,
    chunks: List[Dict[str, Any]],
    history: List[Dict[str, str]] = None
) -> str:
    """
    Constructs the complete user prompt incorporating retrieved document context and chat history.
    """
    context_str = build_context_block(chunks)

    history_str = ""
    if history:
        # Include last 4 turns for local conversational context
        recent_history = history[-4:]
        turns = []
        for msg in recent_history:
            role = "User" if msg.get("role") == "user" else "Assistant"
            turns.append(f"{role}: {msg.get('content', '').strip()}")
        if turns:
            history_str = "Recent Conversation History:\n" + "\n".join(turns) + "\n\n"

    prompt = (
        f"{history_str}"
        f"Context excerpts from uploaded documents:\n"
        f"{context_str}\n\n"
        f"Question: {question}\n\n"
        f"Answer (grounded strictly in the excerpts above):"
    )
    return prompt

def build_rewrite_prompt(question: str, history: List[Dict[str, str]]) -> str:
    """
    Constructs the prompt for resolving ambiguous pronouns and references in follow-up questions.
    """
    recent_turns = []
    for msg in history[-4:]:
        role = "User" if msg.get("role") == "user" else "Assistant"
        recent_turns.append(f"{role}: {msg.get('content', '').strip()}")

    conversation_context = "\n".join(recent_turns)

    prompt = (
        f"Conversation History:\n{conversation_context}\n\n"
        f"Follow-up Question: {question}\n\n"
        f"Standalone Rewritten Question:"
    )
    return prompt
