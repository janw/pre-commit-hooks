from pathlib import Path
from typing import Callable

import pytest

from pre_commit_hooks.utils.poetry import DepRev, PoetryUpdater

VALID = """

[tool.poetry.dependencies]
python = "^3.10"

[tool.poetry.dev-dependencies]
pre-commit = "^4"
ruff = "0.7.2"


[tool.poetry.group.tests.dependencies]
pytest = "^8"

"""


@pytest.fixture
def make_config(tmp_path: Path) -> Callable[[str], str]:
    def _conf_maker(conf: str) -> str:
        conffile = tmp_path / "conf.yaml"
        conffile.write_text(conf)
        return str(conffile)

    return _conf_maker


def test_pre_commit_versions(make_config: Callable[[str], str]) -> None:
    updater = PoetryUpdater.from_filename(make_config(VALID))
    versions = updater.get_versions()
    assert set(versions) == {"python", "ruff", "pre-commit", "pytest"}
    assert all(isinstance(ver, DepRev) for ver in versions.values())


def test_invalid(make_config: Callable[[str], str]) -> None:
    conf = make_config("false")
    with pytest.raises(ValueError, match=r"^Invalid pyproject config:.+"):
        PoetryUpdater.from_filename(make_config(conf))
