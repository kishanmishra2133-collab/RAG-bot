"""
Generic fixed-size text chunker with overlap and boundary preservation.
Produces structured chunks tagged with source filename and index metadata.
"""
from typing import List, Dict, Any

def chunk_text(
    text: str,
    source_filename: str,
    chunk_size: int = 1500,
    chunk_overlap: int = 200
) -> List[Dict[str, Any]]:
    """
    Splits generic document text into overlapping chunks while respecting sentence/paragraph boundaries.
    
    Args:
        text: The clean extracted document text.
        source_filename: Name of the original source file.
        chunk_size: Target character length per chunk (approx. 450-500 tokens).
        chunk_overlap: Number of overlapping characters between consecutive chunks.
        
    Returns:
        List of dicts: [{"text": str, "source_filename": str, "chunk_index": int}]
    """
    if not text or not text.strip():
        return []

    # Clean and normalize newlines
    normalized_text = text.replace("\r\n", "\n").replace("\r", "\n").strip()

    if len(normalized_text) <= chunk_size:
        return [{
            "text": normalized_text,
            "source_filename": source_filename,
            "chunk_index": 0
        }]

    chunks: List[Dict[str, Any]] = []
    start = 0
    text_length = len(normalized_text)
    chunk_idx = 0

    while start < text_length:
        end = min(start + chunk_size, text_length)

        if end < text_length:
            # Try to snap to the nearest paragraph break near the end
            paragraph_break = normalized_text.rfind("\n\n", start + chunk_size // 2, end)
            if paragraph_break != -1:
                end = paragraph_break + 2
            else:
                # Try to snap to the nearest sentence end (.!?)
                sentence_break = -1
                for punct in [". ", "? ", "! ", ".\n", "?\n", "!\n"]:
                    pos = normalized_text.rfind(punct, start + chunk_size // 2, end)
                    if pos > sentence_break:
                        sentence_break = pos + 1
                if sentence_break != -1:
                    end = sentence_break
                else:
                    # Try to snap to nearest whitespace
                    space_break = normalized_text.rfind(" ", start + chunk_size // 2, end)
                    if space_break != -1:
                        end = space_break + 1

        chunk_str = normalized_text[start:end].strip()
        if chunk_str:
            chunks.append({
                "text": chunk_str,
                "source_filename": source_filename,
                "chunk_index": chunk_idx
            })
            chunk_idx += 1

        if end >= text_length:
            break

        # Advance start with overlap, ensuring forward progress
        next_start = end - chunk_overlap
        if next_start <= start:
            next_start = start + 1
        start = next_start

    return chunks
