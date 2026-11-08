"""Select stable release versions and verify release commits."""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = Path("custom_components/sh_entity_status/manifest.json")
VERSION_PATTERN = re.compile(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")
RELEASE_TRAILER = "SmartHass-Release"


def parse_version(value: str) -> tuple[int, int, int]:
    if not VERSION_PATTERN.fullmatch(value):
        raise ValueError(f"Expected stable version X.Y.Z without a v prefix: {value!r}")
    major, minor, patch = value.split(".")
    return int(major), int(minor), int(patch)


def select_version(current: str, bump: str, override: str = "") -> str:
    major, minor, patch = parse_version(current)
    if override:
        if parse_version(override) <= (major, minor, patch):
            raise ValueError("New version must be greater than the release baseline.")
        return override
    if bump == "major":
        return f"{major + 1}.0.0"
    if bump == "minor":
        return f"{major}.{minor + 1}.0"
    if bump == "patch":
        return f"{major}.{minor}.{patch + 1}"
    raise ValueError(f"Unknown version bump: {bump}")


def release_baseline(current: str, pages: list) -> str:
    """Highest of the manifest version and all published stable releases."""
    versions = [parse_version(current)]
    for page in pages:
        for release in page:
            if release["draft"] or release["prerelease"]:
                continue
            try:
                versions.append(parse_version(release["tag_name"].removeprefix("v")))
            except ValueError:
                continue
    return ".".join(str(part) for part in max(versions))


def git(root: Path, *arguments: str) -> str:
    return subprocess.check_output(
        ["git", *arguments], cwd=root, text=True, encoding="utf-8"
    ).strip()


def prepare(root: Path, pages: list, bump: str, override: str) -> dict[str, str]:
    manifest_path = root / MANIFEST
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    version = select_version(
        release_baseline(manifest["version"], pages), bump, override
    )
    result = subprocess.run(
        ["git", "show-ref", "--verify", "--quiet", f"refs/tags/v{version}"],
        cwd=root,
        check=False,
    )
    if result.returncode != 1:
        raise ValueError(f"Tag v{version} already exists or tag lookup failed.")
    manifest["version"] = version
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return {"version": version}


def verify_release_metadata(previous: dict, candidate: dict, version: str) -> None:
    if candidate.get("version") != version:
        raise ValueError("Release manifest version does not match the requested tag.")
    if parse_version(version) <= parse_version(previous["version"]):
        raise ValueError("Release commit does not increase the manifest version.")
    previous = previous.copy()
    previous["version"] = version
    if previous != candidate:
        raise ValueError("Release commit must change only manifest.version.")


def recover(root: Path, version: str) -> dict[str, str]:
    """Locate an already-tagged release commit so publication can be retried."""
    parse_version(version)
    if git(root, "cat-file", "-t", f"refs/tags/v{version}") != "tag":
        raise ValueError("Recovery requires an annotated release tag.")
    candidate = git(root, "rev-parse", f"refs/tags/v{version}^{{commit}}")
    git(root, "merge-base", "--is-ancestor", candidate, "origin/main")
    parents = git(root, "rev-list", "--parents", "-n", "1", candidate).split()
    if len(parents) != 2:
        raise ValueError("Expected a release commit with exactly one parent.")
    message = git(root, "show", "-s", "--format=%B", candidate)
    if f"{RELEASE_TRAILER}: {version}" not in message.splitlines():
        raise ValueError("Tag does not point to a recognized release commit.")
    files = git(root, "diff", "--name-only", parents[1], candidate).splitlines()
    if files != [MANIFEST.as_posix()]:
        raise ValueError("Release commit must change only the integration manifest.")
    previous = json.loads(git(root, "show", f"{parents[1]}:{MANIFEST.as_posix()}"))
    manifest = json.loads(git(root, "show", f"{candidate}:{MANIFEST.as_posix()}"))
    verify_release_metadata(previous, manifest, version)
    return {"version": version, "candidate": candidate}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare", "recover"])
    parser.add_argument("--bump", choices=["patch", "minor", "major"], default="patch")
    parser.add_argument("--version", default="")
    parser.add_argument("--releases", type=Path)
    arguments = parser.parse_args()
    try:
        if arguments.command == "recover":
            values = recover(ROOT, arguments.version)
        else:
            if arguments.releases is None:
                raise ValueError(
                    "prepare requires --releases with paginated GitHub release JSON."
                )
            pages = json.loads(arguments.releases.read_text(encoding="utf-8"))
            values = prepare(ROOT, pages, arguments.bump, arguments.version)
    except (
        KeyError,
        OSError,
        TypeError,
        ValueError,
        subprocess.CalledProcessError,
    ) as error:
        parser.exit(1, f"Release preflight failed: {error}\n")
    print(json.dumps(values))
    if output := os.environ.get("GITHUB_OUTPUT"):
        with Path(output).open("a", encoding="utf-8") as stream:
            stream.writelines(f"{key}={value}\n" for key, value in values.items())


if __name__ == "__main__":
    sys.exit(main())
