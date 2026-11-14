import hashlib
import json
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from pydantic import BaseModel, ValidationError


def get_sha256_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_extraction(
    text: str, directory: Path, schema: type[BaseModel]
) -> BaseModel | None:
    """Load a matching, valid cached extraction; otherwise return None."""
    text_hash = get_sha256_hash(text)
    path = directory / f"{text_hash}.json"
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError):
        return None

    if not isinstance(record, dict):
        return None
    if record.get("text_hash") != text_hash or record.get("text") != text:
        return None
    if not isinstance(record.get("data"), dict):
        return None
    try:
        return schema.model_validate(record["data"])
    except ValidationError:
        return None


def save_extraction(
    text: str, source: Path, result: BaseModel, directory: Path
) -> Path:
    """Save validated data atomically, using the exact text's hash as the filename."""
    text_hash = get_sha256_hash(text)
    path = directory / f"{text_hash}.json"
    record = {
        "source": str(source),
        "text_hash": text_hash,
        "text": text,
        "data": result.model_dump(mode="json"),
    }
    return _save_json(record, path)


def save_comparison(report: dict[str, Any], directory: Path) -> Path:
    """Save one report per ordered resume/JD text-hash pair, replacing prior output."""
    sources = report["sources"]
    pair_key = json.dumps([
        sources["resume"]["text_hash"],
        sources["job_description"]["text_hash"],
    ])
    path = directory / f"{get_sha256_hash(pair_key)}.json"
    return _save_json(report, path)


def _save_json(record: dict[str, Any], path: Path) -> Path:
    """Atomically write JSON without exposing an incomplete destination file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, suffix=".tmp", delete=False
        ) as file:
            temporary_path = Path(file.name)
            json.dump(record, file, indent=2, ensure_ascii=False, allow_nan=False)
        temporary_path.replace(path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
    return path
