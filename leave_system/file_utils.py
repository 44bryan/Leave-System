"""
Shared file-upload validation utilities.
Applied at every upload endpoint to prevent oversized or unexpected file types.
"""
import os

# 10 MB hard limit on all uploaded documents
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB

# Whitelist of safe document / image extensions
ALLOWED_EXTENSIONS = {
    '.pdf', '.doc', '.docx', '.xls', '.xlsx',
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif',
    '.txt', '.csv', '.odt', '.ods',
}


def validate_upload(file_obj):
    """
    Return (ok: bool, error_message: str).
    Call before saving any user-supplied file.
    Does NOT raise — returns the error so the view can surface it cleanly.
    """
    if file_obj is None:
        return False, "No file was provided."

    # Size check
    if file_obj.size > MAX_UPLOAD_BYTES:
        mb = file_obj.size / (1024 * 1024)
        return False, f"File is too large ({mb:.1f} MB). Maximum allowed is 10 MB."

    # Extension check (case-insensitive)
    _, ext = os.path.splitext(file_obj.name)
    if ext.lower() not in ALLOWED_EXTENSIONS:
        return False, (
            f"File type '{ext}' is not allowed. "
            "Please upload a PDF, Word, Excel, or common image file."
        )

    return True, ""
