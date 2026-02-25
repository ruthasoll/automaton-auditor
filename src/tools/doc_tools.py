from pathlib import Path
import tempfile
import logging
from typing import Dict, List, Optional

# Lazy imports for optional dependencies
try:
    from pypdf import PdfReader
except ImportError:  # pragma: no cover
    PdfReader = None

try:
    import fitz  # pymupdf
except ImportError:  # pragma: no cover
    fitz = None

logger = logging.getLogger(__name__)


class PDFExtractionError(Exception):
    """Raised when critical PDF text extraction fails."""


def chunk_text(text: str, max_chunk_size: int = 800) -> List[Dict[str, str]]:
    """Split text into chunks respecting paragraph boundaries."""
    if not text.strip():
        return []

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    current = ""
    chunk_index = 1

    for para in paragraphs:
        if len(current) + len(para) + 2 <= max_chunk_size:
            current += para + "\n\n"
        else:
            if current:
                chunks.append({
                    "text": current.strip(),
                    "chunk_index": chunk_index
                })
                chunk_index += 1
            current = para + "\n\n"

    if current:
        chunks.append({
            "text": current.strip(),
            "chunk_index": chunk_index
        })

    return chunks


def extract_pdf_content(pdf_path: Path) -> Dict[str, any]:
    """
    Extract text, chunks, and images from PDF.

    Returns:
    {
        "full_text": str,
        "chunks": List[Dict["text": str, "chunk_index": int]],
        "image_paths": List[Path],
        "temp_dir": Optional[Path],          # caller should clean up
        "success": bool,
        "errors": List[str]
    }
    """
    if not pdf_path.exists() or not pdf_path.is_file():
        return {
            "full_text": "",
            "chunks": [],
            "image_paths": [],
            "temp_dir": None,
            "success": False,
            "errors": [f"Invalid PDF path: {pdf_path}"]
        }

    result: Dict[str, any] = {
        "full_text": "",
        "chunks": [],
        "image_paths": [],
        "temp_dir": None,
        "success": False,
        "errors": []
    }

    # Text extraction (critical)
    if PdfReader is None:
        result["errors"].append("pypdf not installed")
        return result

    try:
        reader = PdfReader(str(pdf_path))
        text_parts = [page.extract_text() or "" for page in reader.pages]
        result["full_text"] = "\n".join(text_parts).strip()
        result["chunks"] = chunk_text(result["full_text"])
    except Exception as exc:
        result["errors"].append(f"Text extraction failed: {exc}")
        return result

    # Image extraction (optional)
    if fitz is not None:
        try:
            doc = fitz.open(str(pdf_path))
            tmp_dir = Path(tempfile.mkdtemp(prefix="audit_pdf_images_"))
            result["temp_dir"] = tmp_dir

            image_count = 0
            for page in doc:
                if image_count >= 5:
                    break
                for img_idx, img in enumerate(page.get_images(full=True)):
                    if image_count >= 5:
                        break
                    xref = img[0]
                    base_img = doc.extract_image(xref)
                    if base_img is None or base_img.get("image") is None:
                        continue
                    ext = base_img.get("ext", "png")
                    out_path = tmp_dir / f"page{page.number+1}_img{img_idx}.{ext}"
                    out_path.write_bytes(base_img["image"])
                    result["image_paths"].append(out_path)
                    image_count += 1
            doc.close()
        except Exception as exc:
            logger.warning(f"Image extraction failed (continuing): {exc}")
            result["errors"].append(f"Image extraction issue: {exc}")
    else:
        logger.info("pymupdf not installed → no images extracted")

    result["success"] = bool(result["full_text"])
    return result


def cleanup_pdf_temp_dir(temp_dir: Optional[Path]) -> None:
    """Safely remove temporary image directory."""
    if temp_dir is None or not temp_dir.exists():
        return
    try:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
        logger.debug(f"Cleaned temp dir: {temp_dir}")
    except Exception as exc:
        logger.warning(f"Failed to clean {temp_dir}: {exc}")
