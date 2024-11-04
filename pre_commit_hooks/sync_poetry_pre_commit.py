from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from enum import Enum, auto
from sys import argv
from typing import NamedTuple

from semver import Version

from pre_commit_hooks.utils.poetry import DepRev, PoetryUpdater
from pre_commit_hooks.utils.pre_commit import HookRev, PrecommitUpdater

re_semver = re.compile(r"^.*?(\d+.*)$")


class Location(Enum):
    PYPROJECT = auto()
    PRECOMMIT = auto()


@dataclass
class DependencyPair:
    poetry: str
    hook: str
    _raw: str

    @classmethod
    def from_arg(cls, val: str) -> DependencyPair:
        pair = val.split("=", maxsplit=1)
        if len(pair) != 2:
            raise ValueError(f"Invalid dependency pair '{val}'")
        return cls(poetry=pair[0], hook=pair[1], _raw=val)

    def __str__(self) -> str:
        return self._raw

    def __hash__(self) -> int:
        return hash(self._raw)


class VersionChange(NamedTuple):
    location: Location
    new: Version


def solve_version(poetry_version: Version, hook_version: Version) -> str | None:
    if poetry_version == hook_version:
        return None

    return str(max(poetry_version, hook_version))


parser = argparse.ArgumentParser()
parser.add_argument(
    "-pr",
    "--pre-commit-config-file",
    default=".pre-commit-config.yaml",
)
parser.add_argument(
    "-py",
    "--pyproject-file",
    default="pyproject.toml",
)
parser.add_argument(
    "dependency",
    nargs="+",
    metavar="DEPENDENCY=PAIR",
)


def main(argv: list[str]) -> int:
    args = parser.parse_args(argv)
    pairs = [DependencyPair.from_arg(dep) for dep in args.dependency]
    precommit_updater = PrecommitUpdater.from_filename(args.pre_commit_config_file)
    precommit_versions = precommit_updater.get_versions()
    poetry_updater = PoetryUpdater.from_filename(args.pyproject_file)
    poetry_versions = poetry_updater.get_versions()

    precommit_changes: list[HookRev] = []
    poetry_changes: list[DepRev] = []
    for pair in pairs:
        if not (precommit := precommit_versions.get(pair.hook)):
            raise ValueError(f"Dependency not in {args.pyproject_file}: {pair.poetry}")
        if not (poetry := poetry_versions.get(pair.poetry)):
            raise ValueError(f"Dependency not in {args.pre_commit_config_file}: {pair.hook}")

        if not (new_version := solve_version(poetry.version, precommit.version)):
            continue
        precommit_changes.append(precommit.update(new_version))
        poetry_changes.append(poetry.update(new_version))

    poetry_updater.update_versions(poetry_changes)
    precommit_updater.update_versions(precommit_changes)
    if precommit_changes or poetry_changes:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(argv[1:]))
