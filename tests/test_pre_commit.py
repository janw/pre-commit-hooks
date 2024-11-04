from pathlib import Path
from typing import Callable

import pytest

from pre_commit_hooks.utils.pre_commit import HookRev, PrecommitUpdater

VALID = """repos:
  - repo: https://github.com/janw/pre-commit-hooks
    rev: v0.1.0
    hooks:
      - id: sync_ruff_version

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: 'v0.6.9'
    hooks:
      - id: ruff
        args: [ --fix, --exit-non-zero-on-fix ]
      - id: ruff-format
"""


@pytest.fixture
def make_config(tmp_path: Path) -> Callable[[str], str]:
    def _conf_maker(conf: str) -> str:
        conffile = tmp_path / "conf.yaml"
        conffile.write_text(conf)
        return str(conffile)

    return _conf_maker


def test_pre_commit_versions(make_config: Callable[[str], str]) -> None:
    updater = PrecommitUpdater.from_filename(make_config(VALID))
    versions = updater.get_versions()
    assert set(versions) == {"sync_ruff_version", "ruff", "ruff-format"}
    assert all(isinstance(ver, HookRev) for ver in versions.values())


def test_meta(make_config: Callable[[str], str]) -> None:
    conf = "repos: [{repo: meta, hooks: [{id: check-hooks-apply}]}]"
    updater = PrecommitUpdater.from_filename(make_config(conf))
    assert not updater.get_versions()


def test_local(make_config: Callable[[str], str]) -> None:
    conf = """
        repos:
          - repo: local
            hooks:
              - id: somehook
                name: somename
                entry: 'true'
                language: system
        """

    updater = PrecommitUpdater.from_filename(make_config(conf))
    assert not updater.get_versions()


def test_invalid(make_config: Callable[[str], str]) -> None:
    conf = make_config("[{nope:true}]")
    with pytest.raises(ValueError, match=r"^Invalid pre-commit config:.+"):
        PrecommitUpdater.from_filename(make_config(conf))
