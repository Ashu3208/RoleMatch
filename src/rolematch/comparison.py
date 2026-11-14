import json
from pathlib import Path
from typing import Any

from rolematch.matcher import match_resume_to_job
from rolematch.schemas import JobDescription, Resume
from rolematch.scoring import get_score
from rolematch.storage import get_sha256_hash, save_comparison


def compare(
    resume: Resume, jd: JobDescription, resume_text: str
) -> dict[str, Any]:
    """Return requirement assessments, evidence, summary, and calculated score."""
    result = match_resume_to_job(resume, jd, resume_text)
    return {**result.model_dump(mode="json"), **get_score(result)}


def _read_extraction(path: Path) -> dict[str, Any]:
    record = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(record, dict):
        raise ValueError(f"Expected a saved extraction object in {path}.")
    for field in ("source", "text", "text_hash"):
        if not isinstance(record.get(field), str) or not record[field].strip():
            raise ValueError(f"Missing or invalid {field} in {path}.")
    if record["text_hash"] != get_sha256_hash(record["text"]):
        raise ValueError(f"Text hash does not match the saved text in {path}.")
    return record


def compare_saved_extractions(
    resume_path: str | Path,
    jd_path: str | Path,
    *,
    output_directory: Path = Path("data/reports"),
) -> dict[str, Any]:
    """Load two extraction records and return a comparison with source references.

    Validate both records before matching. File, JSON, Pydantic, and matching
    errors propagate. Save the report to output_directory.
    """
    resume_record = _read_extraction(Path(resume_path).expanduser())
    jd_record = _read_extraction(Path(jd_path).expanduser())
    resume = Resume.model_validate(resume_record.get("data"))
    jd = JobDescription.model_validate(jd_record.get("data"))

    report = compare(resume, jd, resume_record["text"])
    report["sources"] = {
        "resume": {
            "source": resume_record["source"],
            "text_hash": resume_record["text_hash"],
        },
        "job_description": {
            "source": jd_record["source"],
            "text_hash": jd_record["text_hash"],
        },
    }
    save_comparison(report, output_directory)
    return report
