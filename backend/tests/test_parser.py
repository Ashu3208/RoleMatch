from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import pymupdf
from docx import Document

from rolematch.parser import read_document, read_pdf


class ParserTests(unittest.TestCase):
    def test_pdf_includes_all_pages_and_handles_missing_text(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "resume.PDF"
            with pymupdf.open() as document:
                document.new_page().insert_text((50, 50), "Experience")
                document.new_page()
                document.new_page().insert_text((50, 50), "Skills")
                document.save(path)

            text = read_document(path)

            self.assertEqual(text.split(), ["Experience", "Skills"])

    def test_pdf_sorts_later_inserted_text_into_visual_position(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "edited.pdf"
            with pymupdf.open() as document:
                page = document.new_page()
                page.insert_text((50, 50), "RoleMatch")
                page.insert_text((50, 150), "Mess Automation")
                page.insert_text((50, 230), "Education")
                # A later PDF edit adds this bullet above the other sections.
                page.insert_text((50, 80), "Implemented PDF extraction")
                document.save(path)

            text = read_pdf(path)

            self.assertLess(text.index("RoleMatch"), text.index("Implemented PDF extraction"))
            self.assertLess(text.index("Implemented PDF extraction"), text.index("Mess Automation"))
            self.assertLess(text.index("Mess Automation"), text.index("Education"))

    def test_blank_pdf_returns_empty_string(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "blank.pdf"
            with pymupdf.open() as document:
                document.new_page(width=612, height=792)
                document.save(path)
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
            document.save(str(path))
            self.assertEqual(
                read_document(str(path)),
                "Ashutosh\nSkill\tExperience\nPython\tTwo years\nProjects",
            )

    def test_empty_docx_returns_empty_string(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "empty.docx"
            Document().save(str(path))
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
