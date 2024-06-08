import argparse
from pathlib import Path

import tomlkit
import tomlkit.exceptions
import yaml


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("-pr", "--pre-commit-config", default=".pre-commit-config.yaml")
    parser.add_argument("-py", "--pyproject", default="pyproject.toml")
    parser.add_argument("-g", "--poetry-group", default="dev")
    parser.add_argument("-r", "--ruff-repo", default="https://github.com/astral-sh/ruff-pre-commit")
    args = parser.parse_args()

    with Path(args.pre_commit_config).open() as fh:
        pc_conf = yaml.safe_load(fh)

    hook_rev = None
    for repo in pc_conf["repos"]:
        if repo["repo"] == args.ruff_repo:
            hook_rev = repo["rev"].lstrip("v")
            break
    if not hook_rev:
        print("Ruff hook not found.")
        return 1

    with Path(args.pyproject).open() as fh:
        proj_conf = tomlkit.load(fh)
    try:
        dep_rev = proj_conf["tool"]["poetry"]["group"][args.poetry_group]["dependencies"]["ruff"]  # type: ignore[index]
    except tomlkit.exceptions.NonExistentKey:
        print("Ruff dependency not found.")
        return 1

    if hook_rev != dep_rev:
        proj_conf["tool"]["poetry"]["group"][args.poetry_group]["dependencies"]["ruff"] = hook_rev  # type: ignore[index]

        with Path(args.pyproject).open("w") as fh:
            tomlkit.dump(proj_conf, fh)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
