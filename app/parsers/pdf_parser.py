"""
PDF text extraction parser using pypdf.
Handles standard multi-page text PDFs and explicitly detects scanned/unextractable files.
"""
import io
from pypdf import PdfReader

def extract_text_from_pdf(file_bytes: bytes, filename: str = "document.pdf") -> str:
    """
    Extracts text content from raw PDF bytes.
    
    Args:
        file_bytes: Raw binary content of the PDF file.
        filename: Original filename for error reporting.
        
    Returns:
        Clean, concatenated text across all pages.
        
    Raises:
        ValueError: If the file is empty, encrypted, or scanned (contains no extractable text).
    """
    if not file_bytes:
        raise ValueError(f"Uploaded PDF '{filename}' is empty (0 bytes).")

    try:
        reader = PdfReader(io.BytesIO(file_bytes))
    except Exception as e:
        raise ValueError(f"Failed to parse PDF '{filename}': {str(e)}")

    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception:
            raise ValueError(f"PDF '{filename}' is password-protected and cannot be read.")

    extracted_pages = []
    for page_idx, page in enumerate(reader.pages):
        try:
            page_text = page.extract_text() or ""
            if page_text.strip():
                extracted_pages.append(page_text.strip())
        except Exception as e:
            # Continue reading remaining pages even if one has minor extraction issues
            continue

    combined_text = "\n\n".join(extracted_pages).strip()

    if not combined_text:
        raise ValueError(
            f"Could not extract text from '{filename}'. The file may be scanned, "
            "image-based, or contain unsupported font encodings (OCR is not supported in v1)."
        )

    return combined_text
