import json
from collections.abc import Callable
from pathlib import Path
from time import sleep
from typing import Any

from pydantic import BaseModel

from rolematch.extractor import extract_job_description, extract_resume
from rolematch.parser import read_document
from rolematch.schemas import JobDescription, Resume
from rolematch.storage import get_sha256_hash, load_extraction, save_extraction


def extract_directory(
    directory: Path,
    extractor: Callable[[str], BaseModel],
    *,
    output_directory: Path,
    schema: type[BaseModel],
    include_text: bool = False,
) -> list[dict[str, Any]]:
    """Extract supported files recursively, skipping hidden and empty inputs."""
    extensions = {".pdf", ".docx"}
    if include_text:
        extensions.add(".txt")

    results = []
    made_request = False
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

        result = load_extraction(text, output_directory, schema)
        if result is None:
            # Cache hits need no delay. API limits also depend on token usage.
            if made_request:
                sleep(5)
            result = schema.model_validate(extractor(text).model_dump())
            made_request = True
            save_extraction(text, file_path, result, output_directory)
        results.append({
            "source": str(file_path),
            "text_hash": get_sha256_hash(text),
            "data": result.model_dump(),
        })

    return results


def main() -> None:
    resumes = extract_directory(
        Path("data/Resume"), extract_resume,
        output_directory=Path("data/extraction/Resume"), schema=Resume,
    )
    job_descriptions = extract_directory(
        Path("data/JD"), extract_job_description,
        output_directory=Path("data/extraction/JD"), schema=JobDescription,
        include_text=True,
    )
    print(json.dumps({"resumes": resumes, "job_descriptions": job_descriptions}, indent=2))
