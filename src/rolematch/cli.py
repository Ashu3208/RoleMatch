import sys
from collections.abc import Callable
from pathlib import Path
from time import perf_counter, sleep

from pydantic import BaseModel

from rolematch.extractor import extract_job_description, extract_resume
from rolematch.parser import read_document
from rolematch.schemas import JobDescription, Resume
from rolematch.storage import load_extraction, save_extraction


def report_progress(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def extract_directory(
    directory: Path,
    extractor: Callable[[str], BaseModel],
    *,
    output_directory: Path,
    schema: type[BaseModel],
    include_text: bool = False,
) -> None:
    """Extract supported files recursively, skipping hidden and empty inputs."""
    extensions = {".pdf", ".docx"}
    if include_text:
        extensions.add(".txt")

    report_progress(f"Scanning {directory}...")
    if not directory.is_dir():
        report_progress(f"Skipping {directory}: input directory not found.")
        return

    files = [
        path for path in sorted(directory.rglob("*"))
        if path.is_file()
        and not any(part.startswith(".") for part in path.relative_to(directory).parts)
        and path.suffix.lower() in extensions
    ]
    report_progress(f"Found {len(files)} supported files in {directory}.")
    started = perf_counter()
    made_request = False
    extracted = cached = empty = 0
    for index, file_path in enumerate(files, start=1):
        label = f"[{index}/{len(files)}] {file_path.relative_to(directory)}"
        report_progress(f"{label}: reading text...")

        if file_path.suffix.lower() == ".txt":
            text = file_path.read_text(encoding="utf-8")
        else:
            text = read_document(file_path) # extracts the text from pdf/doc
        if not text.strip():
            empty += 1
            report_progress(f"{label}: skipped (no text).")
            continue

        report_progress(f"{label}: checking cache...")
        result = load_extraction(text, output_directory, schema)
        if result is None:
            # Cache hits need no delay. API limits also depend on token usage.
            if made_request:
                report_progress(f"{label}: waiting 5 seconds before next request...")
                sleep(5)
            report_progress(f"{label}: calling LLM and validating response...")
            result = extractor(text)
            made_request = True
            report_progress(f"{label}: saving extraction...")
            saved_path = save_extraction(text, file_path, result, output_directory)
            extracted += 1
            report_progress(f"{label}: saved to {saved_path}.")
        else:
            cached += 1
            report_progress(f"{label}: using cached extraction.")

    elapsed = perf_counter() - started
    report_progress(
        f"Finished {directory}: {extracted} newly extracted, {cached} cached, "
        f"{empty} empty; {elapsed:.1f}s elapsed."
    )


def main() -> None:
    extract_directory(
        Path("data/Resume"), extract_resume,
        output_directory=Path("data/extraction/Resume"), schema=Resume,
    )
    extract_directory(
        Path("data/JD"), extract_job_description,
        output_directory=Path("data/extraction/JD"), schema=JobDescription,
        include_text=True,
    )
