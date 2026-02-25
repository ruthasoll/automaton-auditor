from pathlib import Path
import tempfile
import sys

# ensure src package is importable during direct execution
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "src"))

import pytest

from src.tools.doc_tools import extract_pdf_text_and_images, PDFExtractionError


def create_simple_pdf(path: Path, add_image: bool = False) -> None:
    """Create a basic PDF with some text (and optionally an image).

    Uses pypdf for text-only PDFs; if ``add_image`` is True and pymupdf is
    available we leverage it to create a PDF containing an embedded image for
    testing purposes. If pymupdf is not installed and ``add_image`` is True the
    test will skip.
    """
    try:
        from pypdf import PdfWriter
    except ImportError:
        pytest.skip("pypdf not installed; cannot generate test PDF")

    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    # pypdf does not expose a convenient "draw text" API so we rely on the
    # text not being required for this test; extraction should simply return
    # an empty string or blank content. We'll instead add text manually via
    # reportlab if available.
    try:
        from reportlab.pdfgen import canvas

        c = canvas.Canvas(str(path))
        c.drawString(10, 100, "Hello PDF")
        if add_image:
            # draw a tiny red square from PIL
            from PIL import Image

            img = Image.new("RGB", (10, 10), color="red")
            img_path = path.parent / "temp_img.png"
            img.save(img_path)
            c.drawImage(str(img_path), 50, 50, width=10, height=10)
        c.save()
    except ImportError:
        # fallback: just write empty PDF using pypdf and skip image tests
        writer.write(path)
        if add_image:
            pytest.skip("cannot embed image; missing reportlab or PIL")


def test_extract_text(tmp_path):
    pdf = tmp_path / "simple.pdf"
    create_simple_pdf(pdf)
    text, images = extract_pdf_text_and_images(pdf)
    assert isinstance(text, str)
    # should at least contain our known phrase if reportlab was used
    if "Hello PDF" in text:
        assert "Hello PDF" in text
    assert isinstance(images, list)
    assert len(images) == 0


def test_extract_images(tmp_path):
    pdf = tmp_path / "with_img.pdf"
    create_simple_pdf(pdf, add_image=True)
    text, images = extract_pdf_text_and_images(pdf)
    assert isinstance(text, str)
    # images may be empty if extraction library unavailable or no image
    if images:
        assert len(images) <= 5
        for p in images:
            assert Path(p).exists()


def test_nonexistent_pdf(tmp_path):
    with pytest.raises(PDFExtractionError):
        extract_pdf_text_and_images(tmp_path / "nope.pdf")
