from __future__ import annotations

import re
from pathlib import Path
from typing import Iterator, NamedTuple, cast

from semver.version import Version
from tomlkit.exceptions import ParseError
from tomlkit.items import String, Table
from tomlkit.toml_document import TOMLDocument
from tomlkit.toml_file import TOMLFile

prefixed_version = re.compile(r"^.*?(\d+.*)$")


class DepRev(NamedTuple):
    name: str
    rev: str
    parent: Table
    parent_key: str

    @classmethod
    def from_config(cls, name: str, spec: String | Table, *, parent: Table) -> DepRev:
        if isinstance(spec, str | String):
            rev = str(spec)
            parent_key = name
        else:
            rev = str(spec["version"])
            parent = spec
            parent_key = "version"

        if match := prefixed_version.match(rev):
            rev = match.group(1)

        return cls(name=name, rev=rev, parent=parent, parent_key=parent_key)

    @property
    def version(self) -> Version:
        return Version.parse(self.rev)

    def update(self, new_version: str) -> DepRev:
        print(f"Updating {self.name}: {self.rev} -> {new_version}")
        return self._replace(rev=new_version)

    def change_config(self) -> None:
        self.parent[self.parent_key] = self.rev


class PoetryUpdater:
    filename: Path
    config: TOMLDocument

    def __init__(self, filename: Path, config: TOMLDocument) -> None:
        self.filename = filename
        self.config = config

    @classmethod
    def from_filename(cls, filename: str) -> PoetryUpdater:
        try:
            return cls(filename=Path(filename), config=TOMLFile(filename).read())
        except ParseError as exc:
            raise ValueError(f"Invalid pyproject config: {exc}") from exc

    @staticmethod
    def _poetry_tables_iter(config: TOMLDocument) -> Iterator[Table]:
        poetry = cast(Table, config["tool"]["poetry"])  # type: ignore[index]
        if deps := poetry.get("dependencies"):
            yield deps
        if deps := poetry.get("dev-dependencies"):
            yield deps
        groups = poetry.get("group", {})
        for group in groups.values():
            if deps := group.get("dependencies"):
                yield deps

    def get_versions(self) -> dict[str, DepRev]:
        versions: dict[str, DepRev] = {}
        for table in self._poetry_tables_iter(self.config):
            for name, spec in table.items():
                versions[name] = DepRev.from_config(name, spec, parent=table)
        return versions

    def update_versions(self, changes: list[DepRev]) -> None:
        for change in changes:
            change.change_config()
        TOMLFile(self.filename).write(self.config)
