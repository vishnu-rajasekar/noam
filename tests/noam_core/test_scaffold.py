import tempfile
import unittest
from pathlib import Path
from unittest import mock

from noam.models import Study
from noam.models.common import Domain
from noam.studies.scaffold import SUBFOLDERS, create_study


class TestScaffold(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        (self.root / "pyproject.toml").write_text("", encoding="utf-8")
        (self.root / "studies").mkdir()
        (self.root / "domains").mkdir()

        patcher = mock.patch("noam.registry.paths.repo_root", return_value=self.root)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_creates_folder_and_files(self) -> None:
        study = Study(
            id="S001",
            title="Airport Unitised Curtain Wall",
            domain=Domain.MAXWELL,
            engineering_question="q",
            decision_required="d",
        )
        directory = create_study(study)

        self.assertTrue((directory / "study.yaml").is_file())
        self.assertTrue((directory / "brief.md").is_file())
        self.assertTrue((directory / "model" / "model-hypothesis.md").is_file())
        for sub in SUBFOLDERS:
            self.assertTrue((directory / sub).is_dir(), f"missing {sub}/")

        brief_text = (directory / "brief.md").read_text(encoding="utf-8")
        self.assertIn("# Engineering question", brief_text)
        self.assertIn("# Confidentiality notes", brief_text)

        hypothesis_text = (directory / "model" / "model-hypothesis.md").read_text(encoding="utf-8")
        self.assertIn("Unknown", hypothesis_text)

    def test_second_create_with_same_id_raises(self) -> None:
        study = Study(
            id="S001",
            title="Airport Unitised Curtain Wall",
            domain=Domain.MAXWELL,
            engineering_question="q",
            decision_required="d",
        )
        create_study(study)
        with self.assertRaises(FileExistsError):
            create_study(study)


if __name__ == "__main__":
    unittest.main()
