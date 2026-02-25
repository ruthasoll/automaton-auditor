from pathlib import Path
import tempfile
from typing import List, Tuple

# import libraries lazily so that the module can be imported even if some
# dependencies are missing; functions will raise at runtime if necessary.
try:
    from pypdf import PdfReader
except ImportError:  # pragma: no cover - allow tests to import without pypdf
    PdfReader = None  # type: ignore

try:
    import fitz  # pymupdf
except ImportError:  # pragma: no cover - tests will skip if not available
    fitz = None  # type: ignore


class PDFExtractionError(Exception):
    """Raised when PDF extraction fails for any reason."""



def extract_pdf_text_and_images(pdf_path: Path) -> Tuple[str, List[Path]]:
    """Extract text and images from a PDF file.

    Text is read using :class:`pypdf.PdfReader`. Images are extracted with
    ``pymupdf`` (``fitz``) if available; up to five images are written to a
    temporary directory and their paths returned. The temporary directory is
    created via :func:`tempfile.mkdtemp` and not automatically removed – callers
    may discard it when finished.

    Parameters
    ----------
    pdf_path : Path
        Path to the PDF file to inspect.

    Returns
    -------
    Tuple[str, List[Path]]
        A tuple containing the full extracted text and a list of paths to
        image files extracted from the PDF.

    Raises
    ------
    PDFExtractionError
        If any step of the extraction process fails.
    """
    if not pdf_path.exists():
        raise PDFExtractionError(f"PDF path does not exist: {pdf_path}")

    # extract text
    if PdfReader is None:
        raise PDFExtractionError("pypdf is not installed; cannot read PDF text")
    try:
        reader = PdfReader(str(pdf_path))
        text_parts: List[str] = []
        for page in reader.pages:
            text_parts.append(page.extract_text() or "")
        full_text = "\n".join(text_parts)
    except Exception as exc:
        raise PDFExtractionError(f"Failed to read PDF text: {exc}")

    images: List[Path] = []
    if fitz is not None:
        try:
            doc = fitz.open(str(pdf_path))
            tmp_dir = Path(tempfile.mkdtemp(prefix="pdf_images_"))
            # iterate pages, grab images until we hit 5
            for page in doc:
                for img_index, img in enumerate(page.get_images(full=True)):
                    if len(images) >= 5:
                        break
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    ext = base_image.get("ext", "png")
                    data = base_image.get("image")
                    if data is None:
                        continue
                    out_path = tmp_dir / f"image_{page.number}_{img_index}.{ext}"
                    out_path.write_bytes(data)
                    images.append(out_path)
                if len(images) >= 5:
                    break
        except Exception as exc:
            # don't fail text extraction because of image issues
            raise PDFExtractionError(f"Failed to extract images: {exc}")
    return full_text, images
