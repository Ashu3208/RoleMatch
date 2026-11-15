from pydantic import BaseModel, Field


class JobDescription(BaseModel):
    title: str | None = None
    company: str | None = None
    location: str | None = None
    employment_type: str | None = None
    description: str | None = None
    min_experience_years: float | None = Field(default=None, ge=0)
    responsibilities: list[str] = Field(default_factory=list)
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    required_qualifications: list[str] = Field(default_factory=list)
    preferred_qualifications: list[str] = Field(default_factory=list)
