from copy import deepcopy
import unittest
from unittest.mock import patch

from pydantic import ValidationError

from rolematch.matcher import match_resume_to_job
from rolematch.schemas import JobDescription, MatchResult, Resume


class MatcherTests(unittest.TestCase):
    def setUp(self):
        self.resume = Resume(skills=["Python"])
        self.job = JobDescription(required_skills=["Python"])
        self.text = "Built services using Python."
        self.response = {
            "assessments": [{
                "requirement": "Python",
                "priority": "required",
                "status": "demonstrated",
                "evidence": [self.text],
                "reasoning": "The resume explicitly describes Python usage.",
            }],
            "summary": "Python usage is demonstrated.",
        }

    @patch("rolematch.matcher.call_llm")
    def test_returns_validated_assessments_for_all_requirement_groups(self, call):
        job = JobDescription(
            required_skills=["Python"],
            required_qualifications=["Bachelor's degree"],
            preferred_skills=["Docker"],
            preferred_qualifications=["Certification"],
        )
        response = deepcopy(self.response)
        for requirement, priority in [
            ("Bachelor's degree", "required"),
            ("Docker", "preferred"),
            ("Certification", "preferred"),
        ]:
            response["assessments"].append({
                "requirement": requirement, "priority": priority,
                "status": "insufficient_evidence", "evidence": [],
                "reasoning": "No supporting evidence was provided in the resume.",
            })
        call.return_value = response

        result = match_resume_to_job(self.resume, job, self.text)

        self.assertIsInstance(result, MatchResult)
        self.assertEqual(len(result.assessments), 4)
        self.assertEqual(result.assessments[0].evidence, [self.text])

    @patch("rolematch.matcher.call_llm")
    def test_missing_extra_duplicate_and_reclassified_requirements_are_rejected(self, call):
        for problem in ["missing", "extra", "duplicate", "priority"]:
            response = deepcopy(self.response)
            if problem == "missing":
                response["assessments"] = []
            elif problem == "extra":
                response["assessments"].append({
                    **response["assessments"][0], "requirement": "Java",
                })
            elif problem == "duplicate":
                response["assessments"].append(deepcopy(response["assessments"][0]))
            else:
                response["assessments"][0]["priority"] = "preferred"
            call.return_value = response
            with self.subTest(problem=problem):
                with self.assertRaisesRegex(ValueError, "every supplied requirement"):
                    match_resume_to_job(self.resume, self.job, self.text)

    @patch("rolematch.matcher.call_llm")
    def test_unsupported_empty_and_missing_evidence_are_rejected(self, call):
        for evidence in [["Expert in Python"], [" "], []]:
            for status in ["demonstrated", "partially_demonstrated"]:
                response = deepcopy(self.response)
                response["assessments"][0]["evidence"] = evidence
                response["assessments"][0]["status"] = status
                call.return_value = response
                with self.subTest(evidence=evidence, status=status):
                    with self.assertRaises(ValueError):
                        match_resume_to_job(self.resume, self.job, self.text)

    @patch("rolematch.matcher.call_llm")
    def test_quote_check_allows_whitespace_and_pdf_ligature_differences(self, call):
        response = deepcopy(self.response)
        response["assessments"][0]["evidence"] = ["Used Python for profiling."]
        call.return_value = response

        result = match_resume_to_job(self.resume, self.job, "Used Python\nfor proﬁling.")

        self.assertEqual(result.assessments[0].status, "demonstrated")

    @patch("rolematch.matcher.call_llm")
    def test_empty_resume_text_is_rejected_before_api_call(self, call):
        with self.assertRaisesRegex(ValueError, "Original resume text"):
            match_resume_to_job(self.resume, self.job, " \n")
        call.assert_not_called()

    @patch("rolematch.matcher.call_llm")
    def test_no_requirements_skips_api_call(self, call):
        result = match_resume_to_job(self.resume, JobDescription(), self.text)
        self.assertEqual(result.assessments, [])
        call.assert_not_called()

    @patch("rolematch.matcher.call_llm")
    def test_invalid_status_raises_pydantic_error(self, call):
        response = deepcopy(self.response)
        response["assessments"][0]["status"] = "matched"
        call.return_value = response
        with self.assertRaises(ValidationError):
            match_resume_to_job(self.resume, self.job, self.text)


if __name__ == "__main__":
    unittest.main()
