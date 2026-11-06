import json
from collections.abc import Callable
from pathlib import Path
from time import sleep
from typing import Any

from pydantic import BaseModel

from rolematch.extractor import extract_job_description, extract_resume
from rolematch.parser import read_document


def extract_directory(
    directory: Path,
    extractor: Callable[[str], BaseModel],
    *,
    include_text: bool = False,
) -> list[dict[str, Any]]:
    """Extract supported files recursively, skipping hidden and empty inputs."""
    extensions = {".pdf", ".docx"}
    if include_text:
        extensions.add(".txt")

    results = []
    for file_path in sorted(directory.rglob("*")):
        if not file_path.is_file():
            continue
        if any(part.startswith(".") for part in file_path.relative_to(directory).parts):
            continue
        if file_path.suffix.lower() not in extensions:
            continue

        if file_path.suffix.lower() == ".txt":
            text = file_path.read_text(encoding="utf-8")
        else:
            text = read_document(file_path)
        if not text.strip():
            continue

        # Space requests apart; API rate limits also depend on token usage.
        if results:
            sleep(5)
        result = extractor(text)
        results.append({"source": str(file_path), "data": result.model_dump()})

    return results


def main() -> None:
    resumes = extract_directory(Path("data/Resume"), extract_resume)
    if resumes:
        sleep(5)
    job_descriptions = extract_directory(
        Path("data/JD"), extract_job_description, include_text=True
    )
    print(json.dumps({"resumes": resumes, "job_descriptions": job_descriptions}, indent=2))
