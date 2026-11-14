import unittest

from rolematch.schemas import MatchResult
from rolematch.scoring import get_score


class ScoringTests(unittest.TestCase):
    def assert_totals(self, result, expected):
        score = get_score(result)
        self.assertEqual({key: score[key] for key in expected}, expected)

    def make_result(self, entries: list[tuple[str, str]]) -> MatchResult:
        return MatchResult.model_validate({
            "summary": "Example requirement assessments.",
            "assessments": [
                {
                    "requirement": f"Requirement {index + 1}",
                    "priority": priority,
                    "status": status,
                    "evidence": [] if status == "insufficient_evidence" else ["Example source excerpt."],
                    "reasoning": "Example explanation of the assessment.",
                }
                for index, (priority, status) in enumerate(entries)
            ],
        })

    def test_mixed_assessments_match_agreed_example(self):
        result = self.make_result([
            ("required", "demonstrated"),
            ("required", "partially_demonstrated"),
            ("preferred", "insufficient_evidence"),
        ])

        self.assertEqual(get_score(result), {
            "score": 60.0, "earned_points": 3.0, "possible_points": 5,
            "required_totals": {"earned_points": 3.0, "possible_points": 4},
            "preferred_totals": {"earned_points": 0.0, "possible_points": 1},
            "assessments": [
                {
                    "requirement": "Requirement 1", "priority": "required",
                    "status": "demonstrated", "earned_points": 2.0,
                    "possible_points": 2,
                    "evidence": ["Example source excerpt."],
                    "reasoning": "Example explanation of the assessment.",
                },
                {
                    "requirement": "Requirement 2", "priority": "required",
                    "status": "partially_demonstrated", "earned_points": 1.0,
                    "possible_points": 2,
                    "evidence": ["Example source excerpt."],
                    "reasoning": "Example explanation of the assessment.",
                },
                {
                    "requirement": "Requirement 3", "priority": "preferred",
                    "status": "insufficient_evidence", "earned_points": 0.0,
                    "possible_points": 1,
                    "evidence": [],
                    "reasoning": "Example explanation of the assessment.",
                },
            ],
        })

    def test_all_demonstrated_earns_full_score(self):
        result = self.make_result([
            ("required", "demonstrated"), ("preferred", "demonstrated"),
        ])
        self.assert_totals(result, {
            "score": 100.0, "earned_points": 3.0, "possible_points": 3,
            "required_totals": {"earned_points": 2.0, "possible_points": 2},
            "preferred_totals": {"earned_points": 1.0, "possible_points": 1},
        })

    def test_all_insufficient_earns_zero_without_division_error(self):
        result = self.make_result([
            ("required", "insufficient_evidence"),
            ("preferred", "insufficient_evidence"),
        ])
        self.assert_totals(result, {
            "score": 0.0, "earned_points": 0.0, "possible_points": 3,
            "required_totals": {"earned_points": 0.0, "possible_points": 2},
            "preferred_totals": {"earned_points": 0.0, "possible_points": 1},
        })

    def test_partial_evidence_earns_half_credit(self):
        result = self.make_result([
            ("required", "partially_demonstrated"),
            ("preferred", "partially_demonstrated"),
        ])
        self.assert_totals(result, {
            "score": 50.0, "earned_points": 1.5, "possible_points": 3,
            "required_totals": {"earned_points": 1.0, "possible_points": 2},
            "preferred_totals": {"earned_points": 0.5, "possible_points": 1},
        })

    def test_required_evidence_contributes_twice_as_much_as_preferred(self):
        required_match = self.make_result([
            ("required", "demonstrated"), ("preferred", "insufficient_evidence"),
        ])
        preferred_match = self.make_result([
            ("required", "insufficient_evidence"), ("preferred", "demonstrated"),
        ])
        self.assertEqual(get_score(required_match)["earned_points"], 2.0)
        self.assertEqual(get_score(preferred_match)["earned_points"], 1.0)
        self.assertEqual(get_score(required_match)["score"], 66.67)
        self.assertEqual(get_score(preferred_match)["score"], 33.33)

    def test_empty_assessments_have_no_score(self):
        self.assertEqual(get_score(self.make_result([])), {
            "score": None, "earned_points": 0.0, "possible_points": 0,
            "required_totals": {"earned_points": 0.0, "possible_points": 0},
            "preferred_totals": {"earned_points": 0.0, "possible_points": 0},
            "assessments": [],
        })

    def test_repeated_requirement_text_keeps_each_assessment(self):
        result = self.make_result([
            ("required", "demonstrated"),
            ("preferred", "partially_demonstrated"),
        ])
        for item in result.assessments:
            item.requirement = "Python"

        score = get_score(result)

        self.assertEqual(len(score["assessments"]), 2)
        self.assertEqual(
            [item["earned_points"] for item in score["assessments"]],
            [2.0, 0.5],
        )

    def test_absent_priority_has_zero_totals(self):
        for priority, absent in [("required", "preferred"), ("preferred", "required")]:
            with self.subTest(priority=priority):
                score = get_score(self.make_result([(priority, "demonstrated")]))
                self.assertEqual(score[f"{absent}_totals"], {
                    "earned_points": 0.0, "possible_points": 0,
                })

    def test_scoring_does_not_modify_assessments(self):
        result = self.make_result([("required", "partially_demonstrated")])
        original = result.model_dump()
        score = get_score(result)
        score["assessments"][0]["evidence"].append("Changed report evidence.")
        self.assertEqual(result.model_dump(), original)


if __name__ == "__main__":
    unittest.main()
