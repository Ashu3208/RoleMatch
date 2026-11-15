from typing import Literal
from pydantic import BaseModel, Field


class RequirementAssessment(BaseModel):
    requirement: str = Field(min_length=1)
    priority: Literal["required", "preferred"]
    status: Literal[
        "demonstrated",
        "partially_demonstrated",
        "insufficient_evidence",
    ]
    evidence: list[str] = Field(default_factory=list)
    reasoning: str = Field(min_length=1)


class MatchResult(BaseModel):
    assessments: list[RequirementAssessment]
    summary: str = Field(min_length=1)