from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from docx import Document
from pypdf import PdfWriter

from rolematch.parser import read_document, read_pdf


class ParserTests(unittest.TestCase):
    def test_pdf_includes_all_pages_and_handles_missing_text(self):
        pages = [Mock(), Mock(), Mock()]
        for page, text in zip(pages, ["Experience", None, "Skills"]):
            page.extract_text.return_value = text
        with patch("rolematch.parser.PdfReader", return_value=SimpleNamespace(pages=pages)):
            self.assertEqual(read_document("resume.PDF"), "Experience\n\n\n\nSkills")
        for page in pages:
            page.extract_text.assert_called_once_with()

    def test_blank_pdf_returns_empty_string(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "blank.pdf"
            writer = PdfWriter()
            writer.add_blank_page(width=612, height=792)
            writer.write(path)
            self.assertEqual(read_pdf(path), "")

    def test_docx_preserves_paragraph_and_table_order(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "resume.DOCX"
            document = Document()
            document.add_paragraph("Ashutosh")
            document.add_paragraph("")
            table = document.add_table(rows=2, cols=2)
            table.cell(0, 0).text = "Skill"
            table.cell(0, 1).text = "Experience"
            table.cell(1, 0).text = "Python"
            table.cell(1, 1).text = "Two years"
            document.add_paragraph("Projects")
            document.save(path)
            self.assertEqual(
                read_document(str(path)),
                "Ashutosh\nSkill\tExperience\nPython\tTwo years\nProjects",
            )

    def test_empty_docx_returns_empty_string(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "empty.docx"
            Document().save(path)
            self.assertEqual(read_document(path), "")

    def test_unsupported_extensions(self):
        for filename in ["resume.txt", "resume"]:
            with self.subTest(filename=filename):
                with self.assertRaisesRegex(ValueError, "Unsupported file extension"):
                    read_document(filename)
        with self.assertRaisesRegex(ValueError, "Convert to .docx"):
            read_document("resume.doc")


if __name__ == "__main__":
    unittest.main()
