"""
Process a signature upload (PDF or image) into a transparent PNG.
White / near-white pixels are made transparent so the signature
appears cleanly on any background in the leave PDF.
"""
import io
from PIL import Image


def _strip_white(pil_img, threshold=230):
    """Convert white/near-white pixels to transparent."""
    img = pil_img.convert("RGBA")
    data = img.getdata()
    new_data = []
    for r, g, b, a in data:
        if r >= threshold and g >= threshold and b >= threshold:
            new_data.append((255, 255, 255, 0))   # fully transparent
        else:
            new_data.append((r, g, b, a))
    img.putdata(new_data)
    return img


def process_signature(uploaded_file):
    """
    Accept an image (PNG/JPG/etc.) or PDF (first page only).
    Returns a BytesIO containing a transparent PNG ready to save.
    Returns None on failure.
    """
    name = uploaded_file.name.lower()

    try:
        if name.endswith('.pdf'):
            import fitz  # pymupdf
            data = uploaded_file.read()
            doc = fitz.open(stream=data, filetype='pdf')
            page = doc[0]
            # Render at 150 dpi — good quality without being oversized
            mat = fitz.Matrix(150 / 72, 150 / 72)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            pil_img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        else:
            uploaded_file.seek(0)
            pil_img = Image.open(uploaded_file)

        transparent = _strip_white(pil_img)
        out = io.BytesIO()
        transparent.save(out, format='PNG')
        out.seek(0)
        return out

    except Exception:
        return None
