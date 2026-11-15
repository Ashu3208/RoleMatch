from pathlib import Path
from typing import cast

import pymupdf
from docx import Document
from docx.text.paragraph import Paragraph


def read_pdf(path: Path) -> str:
    """Extract PDF text in positional order, returning an empty string if empty."""
    with pymupdf.open(path) as document:
        text = "\n\n".join(
            cast(str, page.get_text("text", sort=True)) for page in document
        ).strip()

    return text


def read_docx(path: Path) -> str:
    """Extract body paragraphs and tables, returning an empty string if empty."""
    document = Document(str(path))
    parts = []

    for block in document.iter_inner_content():
        if isinstance(block, Paragraph):
            parts.append(block.text)
        else:
            # The other body block type is a table. Keep cells grouped by row.
            for row in block.rows:
                parts.append("\t".join(cell.text for cell in row.cells))

    text = "\n".join(part for part in parts if part.strip()).strip()
    return text


def read_document(path: str | Path) -> str:
    """Read a PDF or DOCX file and return its extracted text."""
    file_path = Path(path).expanduser()
    extension = file_path.suffix.lower()
    if extension == ".pdf":
        return read_pdf(file_path)
    if extension == ".docx":
        return read_docx(file_path)
    if extension == ".doc":
        raise ValueError("Legacy .doc files are not supported. Convert to .docx first.")
    raise ValueError(f"Unsupported file extension: {extension or '(none)'}. Use PDF or DOCX.")
