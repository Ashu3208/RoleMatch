import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from rolematch.schemas import JobDescription, Resume
from rolematch.storage import get_sha256_hash, load_extraction, save_extraction


class StorageTests(unittest.TestCase):
    def test_known_sha256(self):
        self.assertEqual(
            get_sha256_hash("hello"),
            "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824",
        )

    def test_round_trip_preserves_source_text_and_nested_data(self):
        with TemporaryDirectory() as directory:
            output = Path(directory) / "Resume"
            text = "Résumé\nPython experience"
            resume = Resume.model_validate({"name": "Ashutosh", "experiences": [{"company": "Example"}]})

            path = save_extraction(text, Path("input/resume.pdf"), resume, output)
            result = load_extraction(text, output, Resume)

            self.assertEqual(result, resume)
            self.assertIsInstance(result, Resume)
            record = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(record["source"], "input/resume.pdf")
            self.assertEqual(record["text"], text)
            self.assertEqual(path.stem, record["text_hash"])
            self.assertEqual(list(output.glob("*.tmp")), [])

    def test_identical_text_has_separate_resume_and_jd_caches(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            text = "Python engineer"
            save_extraction(text, Path("resume.pdf"), Resume(name="Ashutosh"), root / "Resume")
            self.assertIsNone(load_extraction(text, root / "JD", JobDescription))
            save_extraction(text, Path("job.txt"), JobDescription(title="Engineer"), root / "JD")
            self.assertEqual(load_extraction(text, root / "JD", JobDescription).title, "Engineer")

    def test_invalid_record_is_not_reused(self):
        with TemporaryDirectory() as directory:
            output = Path(directory)
            text = "Resume text"
            path = output / f"{get_sha256_hash(text)}.json"
            valid = {"text_hash": get_sha256_hash(text), "text": text, "data": {}}
            for record in [
                [],
                {},
                {**valid, "text": "Different text"},
                {**valid, "text_hash": "wrong"},
                {**valid, "data": []},
                {**valid, "data": {"skills": [42]}},
            ]:
                with self.subTest(record=record):
                    path.write_text(json.dumps(record), encoding="utf-8")
                    self.assertIsNone(load_extraction(text, output, Resume))


if __name__ == "__main__":
    unittest.main()
