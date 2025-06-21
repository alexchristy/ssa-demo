import hashlib


def get_pdf_hash(pdf_content: bytes) -> str:
    """Calculate the SHA-256 hash of the PDF content.

    Args:
    ----
        pdf_content (bytes): Content of the PDF.

    Returns:
    -------
        str: sha256sum of PDF content.

    """
    return hashlib.sha256(pdf_content).hexdigest()
