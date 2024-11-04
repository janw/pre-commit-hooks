from __future__ import annotations

import re
from pathlib import Path
from typing import Any, NamedTuple

from pre_commit.clientlib import LOCAL, META, InvalidConfigError, load_config
from pre_commit.yaml import yaml_dump
from semver.version import Version

REV_LINE_RE = re.compile(r'^(\s+)rev:(\s*)([\'"]?)([^\s#]+)(.*)(\r?\n)$')


class HookRev(NamedTuple):
    repo: str
    rev: str
    idx: int
    hook_ids: frozenset[str] = frozenset()

    @classmethod
    def from_config(cls, config: dict[str, Any], idx: int) -> HookRev:
        rev = config["rev"].lstrip("v")
        return cls(
            repo=config["repo"],
            rev=rev,
            idx=idx,
            hook_ids=frozenset(h["id"] for h in config["hooks"]),
        )

    @property
    def version(self) -> Version:
        return Version.parse(self.rev)

    def to_hook_map(self) -> dict[str, HookRev]:
        return {hook_id: self for hook_id in self.hook_ids}

    def update(self, new_version: str) -> HookRev:
        print(f"Updating {self.repo}: {self.rev} -> {new_version}")
        return self._replace(rev=new_version)


class PrecommitUpdater:
    filename: Path
    config: dict[str, Any]

    _versions: list[HookRev]

    def __init__(self, filename: Path, config: dict[str, Any]) -> None:
        self.filename = filename
        self.config = config

    @classmethod
    def from_filename(cls, filename: str) -> PrecommitUpdater:
        try:
            return cls(filename=Path(filename), config=load_config(filename))
        except InvalidConfigError as exc:
            raise ValueError(f"Invalid pre-commit config: {exc}") from exc

    def get_versions(self) -> dict[str, HookRev]:
        config_repos = [repo for repo in self.config["repos"] if repo["repo"] not in {LOCAL, META}]
        versions: list[HookRev] = []
        for idx, repo in enumerate(config_repos):
            versions.append(HookRev.from_config(repo, idx=idx))
        self._versions = versions
        versions_map: dict[str, HookRev] = {}
        for ver in versions:
            versions_map.update(ver.to_hook_map())
        return versions_map

    def _original_lines(self) -> tuple[list[str], list[int]]:
        with self.filename.open(newline="") as fh:
            lines = fh.read().splitlines(True)
        indexes = [idx for idx, line in enumerate(lines) if REV_LINE_RE.match(line)]
        if len(indexes) != len(self._versions):
            breakpoint()
            raise ValueError(f"Could not parse hook versions in {self.filename}")
        return lines, indexes

    def update_versions(self, changes: list[HookRev]) -> None:
        lines, indexes = self._original_lines()
        for change in changes:
            rev_idx = indexes[change.idx]
            match = REV_LINE_RE.match(lines[rev_idx])
            assert match is not None
            new_rev_s = yaml_dump({"rev": change.rev}, default_style=match[3])
            new_rev = new_rev_s.split(":", 1)[1].strip()
            if match[5].strip().startswith("# frozen:"):
                comment = ""
            else:
                comment = match[5]
            lines[rev_idx] = f"{match[1]}rev:{match[2]}{new_rev}{comment}{match[6]}"

        with open(self.filename, "w", newline="") as fh:
            fh.write("".join(lines))
