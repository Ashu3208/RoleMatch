import sys
from collections.abc import Callable
from pathlib import Path
from time import perf_counter, sleep

from pydantic import BaseModel

from rolematch.comparison import compare_saved_extractions
from rolematch.extractor import extract_job_description, extract_resume
from rolematch.parser import read_document
from rolematch.schemas import JobDescription, Resume
from rolematch.storage import get_sha256_hash, load_extraction, save_extraction


def report_progress(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def extract_directory(
    directory: Path,
    extractor: Callable[[str], BaseModel],
    *,
    output_directory: Path,
    schema: type[BaseModel],
    include_text: bool = False,
) -> list[Path]:
    """Extract current inputs and return their unique, valid cache paths."""
    extensions = {".pdf", ".docx"}
    if include_text:
        extensions.add(".txt")

    report_progress(f"Scanning {directory}...")
    if not directory.is_dir():
        report_progress(f"Skipping {directory}: input directory not found.")
        return []

    files = [
        path for path in sorted(directory.rglob("*"))
        if path.is_file()
        and not any(part.startswith(".") for part in path.relative_to(directory).parts)
        and path.suffix.lower() in extensions
    ]
    report_progress(f"Found {len(files)} supported files in {directory}.")
    started = perf_counter()
    made_request = False
    extraction_paths = []
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
            saved_path = output_directory / f"{get_sha256_hash(text)}.json"
            cached += 1
            report_progress(f"{label}: using cached extraction.")
        if saved_path not in extraction_paths:
            extraction_paths.append(saved_path)

    elapsed = perf_counter() - started
    report_progress(
        f"Finished {directory}: {extracted} newly extracted, {cached} cached, "
        f"{empty} empty; {elapsed:.1f}s elapsed."
    )
    return extraction_paths


def compare_pairs(
    resume_paths: list[Path], jd_paths: list[Path], output_directory: Path
) -> None:
    """Compare the current extraction pairs and save each complete report."""
    total = len(resume_paths) * len(jd_paths)
    report_progress(f"Comparing {len(resume_paths)} resumes against {len(jd_paths)} JDs: {total} pairs.")
    if not total:
        report_progress("Skipping comparisons: both a resume and a JD are needed.")
        return

    started = perf_counter()
    completed = 0
    for resume_path in resume_paths:
        for jd_path in jd_paths:
            label = f"[{completed + 1}/{total}] {resume_path.stem[:8]} / {jd_path.stem[:8]}"
            if completed:
                report_progress(f"{label}: waiting 5 seconds before next comparison...")
                sleep(5)
            report_progress(f"{label}: matching requirements and calculating score...")
            report = compare_saved_extractions(
                resume_path, jd_path, output_directory=output_directory
            )
            score = report["score"]
            score_label = f"{score:.2f}%" if score is not None else "no assessable requirements"
            completed += 1
            report_progress(f"{label}: report saved; score {score_label}.")
    report_progress(
        f"Finished comparisons: {completed} reports saved to {output_directory}; "
        f"{perf_counter() - started:.1f}s elapsed."
    )


def main() -> None:
    resume_paths = extract_directory(
        Path("data/Resume"), extract_resume,
        output_directory=Path("data/extraction/Resume"), schema=Resume,
    )
    jd_paths = extract_directory(
        Path("data/JD"), extract_job_description,
        output_directory=Path("data/extraction/JD"), schema=JobDescription,
        include_text=True,
    )
    compare_pairs(resume_paths, jd_paths, Path("data/reports"))
