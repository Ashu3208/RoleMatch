from typing import Any

from rolematch.schemas import MatchResult


def get_score(assessment: MatchResult) -> dict[str, Any]:
    """Calculate weighted coverage, rounded to two decimal places.

    Required criteria weigh 2 and preferred criteria weigh 1. Demonstrated
    criteria earn full credit, partial criteria half, and insufficient evidence
    zero. Return assessments with calculated points and totals by priority.
    With no criteria, the score is None rather than zero coverage.
    """
    earned_points = 0.0
    possible_points = 0
    required_totals = {"earned_points": 0.0, "possible_points": 0}
    preferred_totals = {"earned_points": 0.0, "possible_points": 0}
    scored_assessments = []
    for item in assessment.assessments:
        weight = 2 if item.priority == "required" else 1
        if item.status == "demonstrated":
            points = float(weight)
        elif item.status == "partially_demonstrated":
            points = weight * 0.5
        else:
            points = 0.0

        earned_points += points
        possible_points += weight
        totals = required_totals if item.priority == "required" else preferred_totals
        totals["earned_points"] += points
        totals["possible_points"] += weight
        scored_assessments.append({
            **item.model_dump(mode="json"),
            "earned_points": points,
            "possible_points": weight,
        })

    score = (
        round(earned_points / possible_points * 100, 2)
        if possible_points
        else None
    )
    return {
        "score": score,
        "earned_points": earned_points,
        "possible_points": possible_points,
        "required_totals": required_totals,
        "preferred_totals": preferred_totals,
        "assessments": scored_assessments,
    }
