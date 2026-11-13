from rolematch.schemas import MatchResult


def get_score(assessment: MatchResult) -> dict[str, float | int | None]:
    """Calculate weighted coverage, rounded to two decimal places.

    Required criteria weigh 2 and preferred criteria weigh 1. Demonstrated
    criteria earn full credit, partial criteria half, and insufficient evidence
    zero. With no criteria, the score is None rather than zero coverage.
    """
    earned_points = 0.0
    possible_points = 0

    for item in assessment.assessments:
        weight = 2 if item.priority == "required" else 1
        possible_points += weight

        if item.status == "demonstrated":
            earned_points += weight
        elif item.status == "partially_demonstrated":
            earned_points += weight * 0.5

    score = (
        round(earned_points / possible_points * 100, 2)
        if possible_points
        else None
    )
    return {
        "score": score,
        "earned_points": earned_points,
        "possible_points": possible_points,
    }
