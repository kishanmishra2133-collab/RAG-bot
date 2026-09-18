"""
Plain text and Markdown extraction parser.
Handles UTF-8 encoding with resilient fallback to latin-1.
"""

def extract_text_from_txt(file_bytes: bytes, filename: str = "document.txt") -> str:
    """
    Extracts text from raw TXT or MD bytes.
    
    Args:
        file_bytes: Raw binary content of the file.
        filename: Original filename for error reporting.
        
    Returns:
        Decoded text string.
        
    Raises:
        ValueError: If the file is empty or decoding fails completely.
    """
    if not file_bytes:
        raise ValueError(f"Uploaded text file '{filename}' is empty (0 bytes).")

    # Attempt UTF-8 decode first, falling back to latin-1
    try:
        text = file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = file_bytes.decode("latin-1")
        except Exception as e:
            raise ValueError(f"Failed to decode text file '{filename}': {str(e)}")

    cleaned_text = text.strip()
    if not cleaned_text:
        raise ValueError(f"Uploaded text file '{filename}' contains only whitespace.")

    return cleaned_text
