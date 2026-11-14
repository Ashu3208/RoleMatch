import json
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from rolematch.cli import compare_pairs, extract_directory, main
from rolematch.extractor import extract_job_description, extract_resume
from rolematch.schemas import JobDescription, Resume
from rolematch.storage import get_sha256_hash


class CliTests(unittest.TestCase):
    @patch("rolematch.cli.read_document")
    def test_progress_reports_work_without_polluting_stdout(self, read):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ["a.pdf", "b.docx", "empty.pdf"]:
                (root / name).touch()
            read.side_effect = lambda path: "" if path.name == "empty.pdf" else "Same resume"
            extractor = Mock(return_value=Resume(name="Ashutosh"))
            stdout, stderr = StringIO(), StringIO()

            with redirect_stdout(stdout), redirect_stderr(stderr):
                extract_directory(
                    root, extractor, output_directory=root / "cache", schema=Resume
                )

            self.assertEqual(stdout.getvalue(), "")
            progress = stderr.getvalue()
            self.assertIn("[1/3] a.pdf: reading text", progress)
            self.assertIn("calling LLM", progress)
            self.assertIn("saving extraction", progress)
            self.assertIn("[2/3] b.docx: using cached extraction", progress)
            self.assertIn("[3/3] empty.pdf: skipped (no text)", progress)
            self.assertIn("1 newly extracted, 1 cached, 1 empty", progress)
            self.assertEqual(len(list((root / "cache").glob("*.json"))), 1)
            extractor.assert_called_once_with("Same resume")

    @patch("rolematch.cli.sleep")
    @patch("rolematch.cli.read_document")
    def test_recursive_extraction_skips_hidden_unsupported_and_empty_files(self, read, sleep):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for filename in ["resume.PDF", "nested/resume.docx", "empty.pdf", ".hidden.pdf", ".hidden/resume.pdf", "notes.txt", "old.doc"]:
                path = root / filename
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()
            read.side_effect = lambda path: " " if path.name == "empty.pdf" else f"Resume text: {path.name}"
            extractor = Mock(return_value=Resume(name="Ashutosh"))

            extract_directory(
                root, extractor, output_directory=root / "extracted", schema=Resume
            )

            records = [
                json.loads(path.read_text(encoding="utf-8"))
                for path in (root / "extracted").glob("*.json")
            ]
            self.assertEqual(len(records), 2)
            self.assertEqual(extractor.call_count, 2)
            self.assertEqual(read.call_count, 3)
            self.assertTrue(all(record["data"]["name"] == "Ashutosh" for record in records))
            self.assertEqual(
                {Path(record["source"]).relative_to(root).as_posix() for record in records},
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

            extract_directory(
                path.parent, extractor, output_directory=path.parent / "extracted",
                schema=JobDescription, include_text=True,
            )

            extractor.assert_called_once_with("Python engineer required")
            cache = path.parent / "extracted" / f"{get_sha256_hash('Python engineer required')}.json"
            self.assertEqual(json.loads(cache.read_text(encoding="utf-8"))["data"]["title"], "Engineer")
            read.assert_not_called()
            sleep.assert_not_called()

    def test_missing_directory_is_skipped(self):
        with TemporaryDirectory() as directory:
            extractor = Mock()
            self.assertEqual(extract_directory(
                Path(directory) / "missing", extractor,
                output_directory=Path(directory) / "extracted", schema=Resume,
            ), [])
            extractor.assert_not_called()
            self.assertFalse((Path(directory) / "extracted").exists())

    @patch("rolematch.cli.compare_pairs")
    @patch("rolematch.cli.sleep")
    @patch("rolematch.cli.extract_directory")
    def test_main_routes_both_inputs_without_printing_json(self, extract, sleep, comparisons):
        resume_paths = [Path("resume-cache.json")]
        jd_paths = [Path("jd-cache.json")]
        extract.side_effect = [resume_paths, jd_paths]
        output = StringIO()
        with redirect_stdout(output):
            main()
        self.assertEqual(output.getvalue(), "")
        self.assertEqual(extract.call_args_list[0].args, (Path("data/Resume"), extract_resume))
        self.assertEqual(extract.call_args_list[1].args, (Path("data/JD"), extract_job_description))
        self.assertEqual(extract.call_args_list[0].kwargs["output_directory"], Path("data/extraction/Resume"))
        self.assertIs(extract.call_args_list[0].kwargs["schema"], Resume)
        self.assertEqual(extract.call_args_list[1].kwargs["output_directory"], Path("data/extraction/JD"))
        self.assertIs(extract.call_args_list[1].kwargs["schema"], JobDescription)
        self.assertTrue(extract.call_args_list[1].kwargs["include_text"])
        comparisons.assert_called_once_with(resume_paths, jd_paths, Path("data/reports"))

    @patch("rolematch.cli.sleep")
    @patch("rolematch.cli.read_document", return_value="Same resume text")
    def test_duplicate_text_and_later_runs_reuse_saved_data(self, read, sleep):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            inputs = root / "inputs"
            inputs.mkdir()
            (inputs / "first.pdf").touch()
            (inputs / "second.docx").touch()
            output = root / "extracted"
            extractor = Mock(return_value=Resume(name="Ashutosh"))

            first_paths = extract_directory(inputs, extractor, output_directory=output, schema=Resume)
            cache = output / f"{get_sha256_hash('Same resume text')}.json"
            saved_bytes = cache.read_bytes()
            second_paths = extract_directory(inputs, extractor, output_directory=output, schema=Resume)

            extractor.assert_called_once_with("Same resume text")
            self.assertEqual(cache.read_bytes(), saved_bytes)
            self.assertEqual(json.loads(saved_bytes)["data"]["name"], "Ashutosh")
            self.assertEqual(len(list(output.glob("*.json"))), 1)
            self.assertEqual(first_paths, [cache])
            self.assertEqual(second_paths, [cache])
            sleep.assert_not_called()

    @patch("rolematch.cli.read_document", return_value="Current resume")
    def test_only_current_cache_paths_are_returned(self, read):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            inputs, output = root / "inputs", root / "extracted"
            inputs.mkdir()
            output.mkdir()
            (inputs / "resume.pdf").touch()
            (output / "old-version.json").write_text("{}", encoding="utf-8")
            extractor = Mock(return_value=Resume(name="Example"))

            paths = extract_directory(inputs, extractor, output_directory=output, schema=Resume)

            self.assertEqual(paths, [output / f"{get_sha256_hash('Current resume')}.json"])
            self.assertEqual(len(list(output.glob("*.json"))), 2)

    @patch("rolematch.cli.sleep")
    @patch("rolematch.cli.compare_saved_extractions", return_value={"score": 60.0})
    def test_batch_compares_every_current_pair_and_reports_progress(self, compare, sleep):
        resumes = [Path("resume1.json"), Path("resume2.json")]
        jobs = [Path("job1.json"), Path("job2.json")]
        stdout, stderr = StringIO(), StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            compare_pairs(resumes, jobs, Path("reports"))

        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual([item.args for item in compare.call_args_list], [
            (resumes[0], jobs[0]), (resumes[0], jobs[1]),
            (resumes[1], jobs[0]), (resumes[1], jobs[1]),
        ])
        self.assertTrue(all(item.kwargs["output_directory"] == Path("reports") for item in compare.call_args_list))
        self.assertEqual(sleep.call_count, 3)
        self.assertIn("4 reports saved", stderr.getvalue())
        self.assertIn("60.00%", stderr.getvalue())

    @patch("rolematch.cli.sleep")
    @patch("rolematch.cli.compare_saved_extractions")
    def test_batch_with_no_pairs_skips_comparison(self, compare, sleep):
        for resumes, jobs in [([], [Path("job.json")]), ([Path("resume.json")], [])]:
            compare_pairs(resumes, jobs, Path("reports"))
        compare.assert_not_called()
        sleep.assert_not_called()

    @patch("rolematch.cli.compare_saved_extractions", return_value={"score": None})
    def test_batch_reports_unassessable_score(self, compare):
        stderr = StringIO()
        with redirect_stderr(stderr):
            compare_pairs([Path("resume.json")], [Path("job.json")], Path("reports"))
        self.assertIn("no assessable requirements", stderr.getvalue())

    @patch("rolematch.cli.sleep")
    @patch("rolematch.cli.read_document")
    def test_changed_text_requires_new_extraction(self, read, sleep):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "resume.pdf").touch()
            read.side_effect = ["Original resume", "Changed resume"]
            extractor = Mock(return_value=Resume(name="Ashutosh"))
            output = root / "extracted"

            extract_directory(root, extractor, output_directory=output, schema=Resume)
            extract_directory(root, extractor, output_directory=output, schema=Resume)

            self.assertEqual(extractor.call_count, 2)
            self.assertEqual(len(list(output.glob("*.json"))), 2)

    @patch("rolematch.cli.read_document", return_value="Resume text")
    def test_corrupt_cache_is_replaced(self, read):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "resume.pdf").touch()
            output = root / "extracted"
            output.mkdir()
            cache = output / f"{get_sha256_hash('Resume text')}.json"
            cache.write_text("broken JSON", encoding="utf-8")
            extractor = Mock(return_value=Resume(name="Ashutosh"))

            extract_directory(root, extractor, output_directory=output, schema=Resume)

            extractor.assert_called_once()
            self.assertEqual(json.loads(cache.read_text())["data"]["name"], "Ashutosh")

    @patch("rolematch.cli.read_document", return_value="Resume text")
    def test_failed_extraction_is_not_saved(self, read):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "resume.pdf").touch()
            output = root / "extracted"
            extractor = Mock(side_effect=ValueError("LLM failed"))

            with self.assertRaisesRegex(ValueError, "LLM failed"):
                extract_directory(root, extractor, output_directory=output, schema=Resume)

            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
