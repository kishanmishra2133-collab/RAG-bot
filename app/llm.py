"""
Gemini LLM generation module for grounded Q&A and conversational query rewriting.
Uses gemini-3.6-flash (with robust fallbacks) for fast, accurate response generation.
"""
import os
from typing import List, Dict, Any
from dotenv import load_dotenv
from google import genai
from google.genai import types
from app.prompt import (
    GROUNDED_SYSTEM_INSTRUCTION,
    QUERY_REWRITE_SYSTEM_INSTRUCTION,
    build_grounded_rag_prompt,
    build_rewrite_prompt
)

load_dotenv(override=True)

DEFAULT_GENERATION_MODELS = ["gemini-3.6-flash", "gemini-flash-latest", "gemini-2.5-flash-lite"]
ACTIVE_GENERATION_MODEL = os.getenv("GEMINI_GENERATION_MODEL", DEFAULT_GENERATION_MODELS[0])

def _get_api_key() -> str:
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
    return key.strip()

def _get_client() -> genai.Client:
    key = _get_api_key()
    if not key or key == "your_gemini_api_key_here":
        raise ValueError(
            "Gemini API key is not configured. Please set GEMINI_API_KEY in your .env file."
        )
    return genai.Client(api_key=key)

def rewrite_query_if_needed(question: str, history: List[Dict[str, str]] = None) -> str:
    """
    Rewrites ambiguous follow-up questions to resolve pronouns/references against recent history.
    If history is empty or rewrite fails, returns the original question.
    """
    global ACTIVE_GENERATION_MODEL
    if not history or len(history) == 0:
        return question

    key = _get_api_key()
    if not key or key == "your_gemini_api_key_here" or os.getenv("ENABLE_MOCK_EMBEDDINGS", "0") == "1":
        return question

    try:
        client = _get_client()
        prompt = build_rewrite_prompt(question, history)
        models_to_try = [ACTIVE_GENERATION_MODEL] + [m for m in DEFAULT_GENERATION_MODELS if m != ACTIVE_GENERATION_MODEL]
        for model_name in models_to_try:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=QUERY_REWRITE_SYSTEM_INSTRUCTION,
                        temperature=0.0,
                        max_output_tokens=150,
                    )
                )
                rewritten = response.text.strip() if response.text else ""
                if rewritten and len(rewritten) > 3:
                    ACTIVE_GENERATION_MODEL = model_name
                    return rewritten
            except Exception:
                continue
    except Exception:
        pass

    return question

def generate_answer(
    question: str,
    chunks: List[Dict[str, Any]],
    history: List[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Generates a grounded answer from retrieved context chunks using Gemini.
    
    Args:
        question: User's question (or rewritten standalone question).
        chunks: Retrieved context chunks from the session's FAISS index.
        history: Optional conversational history list.
        
    Returns:
        Dict: {"answer": str, "sources": List[str]}
    """
    global ACTIVE_GENERATION_MODEL
    if not chunks:
        return {
            "answer": "The uploaded documents do not contain information to answer this question.",
            "sources": []
        }

    sources = []
    seen = set()
    for chunk in chunks:
        src = chunk.get("source_filename")
        if src and src not in seen:
            seen.add(src)
            sources.append(src)

    key = _get_api_key()
    if not key or key == "your_gemini_api_key_here" or os.getenv("ENABLE_MOCK_EMBEDDINGS", "0") == "1":
        combined_snippets = " ".join([c.get("text", "")[:120] for c in chunks[:2]])
        return {
            "answer": f"[Demo/Offline Mode] Based on {', '.join(sources)}: {combined_snippets}...",
            "sources": sources
        }

    client = _get_client()
    prompt = build_grounded_rag_prompt(question, chunks, history)

    models_to_try = [ACTIVE_GENERATION_MODEL] + [m for m in DEFAULT_GENERATION_MODELS if m != ACTIVE_GENERATION_MODEL]
    answer_text = None
    last_err = None

    for model_name in models_to_try:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=GROUNDED_SYSTEM_INSTRUCTION,
                    temperature=0.1,
                    max_output_tokens=1024,
                )
            )
            answer_text = response.text.strip() if response.text else "Unable to generate answer."
            ACTIVE_GENERATION_MODEL = model_name
            break
        except Exception as e:
            last_err = e
            continue

    if answer_text is None:
        raise RuntimeError(f"Gemini generation call failed across models {models_to_try}: {str(last_err)}")

    lower_ans = answer_text.lower()
    if (
        "do not contain" in lower_ans
        or "does not contain" in lower_ans
        or "not mentioned in the provided" in lower_ans
        or "not found in the uploaded" in lower_ans
    ):
        sources = []

    return {
        "answer": answer_text,
        "sources": sources
    }
