import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from pydantic import ValidationError

from rolematch.comparison import compare, compare_saved_extractions
from rolematch.schemas import JobDescription, Resume
from rolematch.storage import save_extraction


class ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.text = "Built Python services. Contributed to an internal REST endpoint."
        self.resume = Resume(name="Example Applicant", skills=["Python"])
        self.job = JobDescription(
            required_skills=["Python", "REST API development"],
            preferred_skills=["Docker"],
        )
        self.response = {
            "summary": "Python is supported; REST API scope is partial and Docker is unmentioned.",
            "assessments": [
                {
                    "requirement": "Python", "priority": "required",
                    "status": "demonstrated", "evidence": ["Built Python services."],
                    "reasoning": "Explicit Python usage is stated.",
                },
                {
                    "requirement": "REST API development", "priority": "required",
                    "status": "partially_demonstrated",
                    "evidence": ["Contributed to an internal REST endpoint."],
                    "reasoning": "A contribution is stated, but broader development scope is not established.",
                },
                {
                    "requirement": "Docker", "priority": "preferred",
                    "status": "insufficient_evidence", "evidence": [],
                    "reasoning": "Docker is not mentioned.",
                },
            ],
        }

    def save_pair(self, directory: Path) -> tuple[Path, Path]:
        resume_path = save_extraction(
            self.text, Path("data/Resume/example.pdf"), self.resume, directory / "Resume"
        )
        jd_path = save_extraction(
            "Python and REST API development required; Docker preferred.",
            Path("data/JD/example.txt"), self.job, directory / "JD",
        )
        return resume_path, jd_path

    @patch("rolematch.matcher.call_llm")
    def test_compare_preserves_assessments_and_returns_calculated_score(self, call):
        call.return_value = self.response

        report = compare(self.resume, self.job, self.text)

        self.assertEqual(report["score"], 60.0)
        self.assertEqual(report["earned_points"], 3.0)
        self.assertEqual(report["possible_points"], 5)
        self.assertEqual(report["assessments"], self.response["assessments"])
        self.assertEqual(report["summary"], self.response["summary"])

    @patch("rolematch.matcher.call_llm")
    def test_saved_pair_produces_report_with_source_references(self, call):
        call.return_value = self.response
        with TemporaryDirectory() as directory:
            resume_path, jd_path = self.save_pair(Path(directory))

            reports_directory = Path(directory) / "reports"
            report = compare_saved_extractions(
                str(resume_path), jd_path, output_directory=reports_directory
            )

            self.assertEqual(report["score"], 60.0)
            self.assertEqual(report["sources"]["resume"]["source"], "data/Resume/example.pdf")
            self.assertEqual(report["sources"]["resume"]["text_hash"], resume_path.stem)
            self.assertEqual(report["sources"]["job_description"]["text_hash"], jd_path.stem)
            self.assertEqual(len(report["assessments"]), 3)
            reports = list(reports_directory.glob("*.json"))
            self.assertEqual(len(reports), 1)
            self.assertEqual(json.loads(reports[0].read_text(encoding="utf-8")), report)
            call.assert_called_once()

    @patch("rolematch.matcher.call_llm")
    def test_corrupted_hash_is_rejected_before_llm_call(self, call):
        with TemporaryDirectory() as directory:
            resume_path, jd_path = self.save_pair(Path(directory))
            record = json.loads(resume_path.read_text())
            record["text"] = "Changed text without updating its hash"
            resume_path.write_text(json.dumps(record), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Text hash"):
                compare_saved_extractions(resume_path, jd_path)
        call.assert_not_called()

    @patch("rolematch.matcher.call_llm")
    def test_invalid_jd_data_is_rejected_before_llm_call(self, call):
        with TemporaryDirectory() as directory:
            resume_path, jd_path = self.save_pair(Path(directory))
            record = json.loads(jd_path.read_text())
            record["data"]["required_skills"] = [42]
            jd_path.write_text(json.dumps(record), encoding="utf-8")
            with self.assertRaises(ValidationError):
                compare_saved_extractions(resume_path, jd_path)
        call.assert_not_called()

    @patch("rolematch.matcher.call_llm")
    def test_missing_original_text_is_rejected_before_llm_call(self, call):
        with TemporaryDirectory() as directory:
            resume_path, jd_path = self.save_pair(Path(directory))
            record = json.loads(resume_path.read_text())
            del record["text"]
            resume_path.write_text(json.dumps(record), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "text"):
                compare_saved_extractions(resume_path, jd_path)
        call.assert_not_called()

    @patch("rolematch.matcher.call_llm")
    def test_no_requirements_returns_no_score_without_llm_call(self, call):
        report = compare(self.resume, JobDescription(), self.text)
        self.assertEqual(report["assessments"], [])
        self.assertIsNone(report["score"])
        call.assert_not_called()

    @patch("rolematch.matcher.call_llm", side_effect=ValueError("Invalid evidence"))
    def test_matching_failure_does_not_produce_a_score(self, call):
        with self.assertRaisesRegex(ValueError, "Invalid evidence"):
            compare(self.resume, self.job, self.text)


if __name__ == "__main__":
    unittest.main()
