import json
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from rolematch.cli import extract_directory, main
from rolematch.extractor import extract_job_description, extract_resume
from rolematch.schemas import JobDescription, Resume


class CliTests(unittest.TestCase):
    @patch("rolematch.cli.sleep")
    @patch("rolematch.cli.read_document")
    def test_recursive_extraction_skips_hidden_unsupported_and_empty_files(self, read, sleep):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for filename in ["resume.PDF", "nested/resume.docx", "empty.pdf", ".hidden.pdf", ".hidden/resume.pdf", "notes.txt", "old.doc"]:
                path = root / filename
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()
            read.side_effect = lambda path: " " if path.name == "empty.pdf" else "Resume text"
            extractor = Mock(return_value=Resume(name="Ashutosh"))

            results = extract_directory(root, extractor)

            self.assertEqual(len(results), 2)
            self.assertEqual(extractor.call_count, 2)
            self.assertEqual(read.call_count, 3)
            self.assertTrue(all(result["data"]["name"] == "Ashutosh" for result in results))
            self.assertEqual(
                {Path(result["source"]).relative_to(root).as_posix() for result in results},
                {"resume.PDF", "nested/resume.docx"},
            )
            sleep.assert_called_once_with(5)

    @patch("rolematch.cli.sleep")
    @patch("rolematch.cli.read_document")
    def test_job_description_can_be_read_from_plain_text(self, read, sleep):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "job.TXT"
            path.write_text("Python engineer required", encoding="utf-8")
            extractor = Mock(return_value=JobDescription(title="Engineer"))

            results = extract_directory(path.parent, extractor, include_text=True)

            extractor.assert_called_once_with("Python engineer required")
            self.assertEqual(results[0]["data"]["title"], "Engineer")
            read.assert_not_called()
            sleep.assert_not_called()

    def test_missing_directory_returns_no_results(self):
        with TemporaryDirectory() as directory:
            extractor = Mock()
            self.assertEqual(extract_directory(Path(directory) / "missing", extractor), [])
            extractor.assert_not_called()

    @patch("rolematch.cli.sleep")
    @patch("rolematch.cli.extract_directory")
    def test_main_routes_both_inputs_and_prints_valid_json(self, extract, sleep):
        extract.side_effect = [
            [{"source": "data/Resume/resume.pdf", "data": {"name": "Ashutosh"}}],
            [{"source": "data/JD/job.txt", "data": {"title": "Engineer"}}],
        ]
        output = StringIO()
        with redirect_stdout(output):
            main()
        result = json.loads(output.getvalue())
        self.assertEqual(result["resumes"][0]["data"]["name"], "Ashutosh")
        self.assertEqual(result["job_descriptions"][0]["data"]["title"], "Engineer")
        self.assertEqual(extract.call_args_list[0].args, (Path("data/Resume"), extract_resume))
        self.assertEqual(extract.call_args_list[1].args, (Path("data/JD"), extract_job_description))
        self.assertTrue(extract.call_args_list[1].kwargs["include_text"])


if __name__ == "__main__":
    unittest.main()
