from pydantic import BaseModel, Field


class Experience(BaseModel):
    company: str | None = None
    role: str | None = None
    duration_months: int | None = Field(default=None, ge=0)
    description: str | None = None
    skills: list[str] = Field(default_factory=list)


class Resume(BaseModel):
    name: str | None = None
    email: str | None = None
    contact: str | None = None
    total_experience_yrs: float | None = Field(default=None, ge=0)
    skills: list[str] = Field(default_factory=list)
    experiences: list[Experience] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)

