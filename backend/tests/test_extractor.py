import unittest
from unittest.mock import patch

from pydantic import ValidationError

from rolematch.extractor import extract_job_description, extract_resume
from rolematch.schemas import JobDescription, Resume
from rolematch.schemas.resume import Experience


class ExtractResumeTests(unittest.TestCase):
    @patch("rolematch.extractor.call_llm")
    def test_returns_validated_resume_with_nested_experiences(self, call_llm):
        call_llm.return_value = {
            "name": "Ashutosh",
            "skills": ["Python"],
            "experiences": [{"company": "Example", "duration_months": 6}],
        }

        result = extract_resume("Ashutosh knows Python and worked at Example for 6 months.")

        self.assertIsInstance(result, Resume)
        self.assertEqual(result.name, "Ashutosh")
        self.assertIsInstance(result.experiences[0], Experience)
        self.assertEqual(result.experiences[0].duration_months, 6)
        self.assertIsNone(result.email)
        self.assertEqual(result.projects, [])

    @patch("rolematch.extractor.call_llm")
    def test_empty_input_skips_llm(self, call_llm):
        for text in ["", " \n\t "]:
            with self.subTest(text=text):
                self.assertEqual(extract_resume(text), Resume())
        call_llm.assert_not_called()

    @patch("rolematch.extractor.call_llm")
    def test_invalid_model_output_raises_validation_error(self, call_llm):
        for data in [{"skills": [42]}, {"experiences": [{"duration_months": -1}]}]:
            with self.subTest(data=data):
                call_llm.return_value = data
                with self.assertRaises(ValidationError):
                    extract_resume("Resume text")

    @patch("rolematch.extractor.call_llm", side_effect=ValueError("Invalid JSON"))
    def test_llm_failure_is_not_returned_as_empty_resume(self, call_llm):
        with self.assertRaisesRegex(ValueError, "Invalid JSON"):
            extract_resume("Resume text")


class ExtractJobDescriptionTests(unittest.TestCase):
    @patch("rolematch.extractor.call_llm")
    def test_returns_validated_job_description(self, call_llm):
        call_llm.return_value = {
            "title": "Software Engineer",
            "min_experience_years": 1,
            "required_skills": ["Python or Java"],
            "preferred_skills": ["Docker"],
        }

        result = extract_job_description(
            "Software Engineer: 1-3 years of experience. Python or Java required. Docker preferred."
        )

        self.assertIsInstance(result, JobDescription)
        self.assertEqual(result.min_experience_years, 1)
        self.assertEqual(result.required_skills, ["Python or Java"])
        self.assertEqual(result.preferred_skills, ["Docker"])
        self.assertIsNone(result.company)
        self.assertEqual(result.responsibilities, [])

    @patch("rolematch.extractor.call_llm")
    def test_empty_input_skips_llm(self, call_llm):
        for text in ["", " \n\t "]:
            with self.subTest(text=text):
                self.assertEqual(extract_job_description(text), JobDescription())
        call_llm.assert_not_called()

    @patch("rolematch.extractor.call_llm")
    def test_invalid_model_output_raises_validation_error(self, call_llm):
        for data in [{"min_experience_years": -1}, {"required_skills": [42]}]:
            with self.subTest(data=data):
                call_llm.return_value = data
                with self.assertRaises(ValidationError):
                    extract_job_description("Job description text")

    @patch("rolematch.extractor.call_llm", side_effect=ValueError("Invalid JSON"))
    def test_llm_failure_propagates(self, call_llm):
        with self.assertRaisesRegex(ValueError, "Invalid JSON"):
            extract_job_description("Job description text")


if __name__ == "__main__":
    unittest.main()
