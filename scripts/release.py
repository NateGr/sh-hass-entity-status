"""Select release versions and verify release commits."""

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
PRERELEASE_PATTERN = re.compile(
    r"(?P<base>(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\."
    r"(?:0|[1-9][0-9]*))rc(?P<number>[1-9][0-9]*)"
)
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


def parse_release_version(value: str) -> tuple[tuple[int, int, int], bool]:
    if match := PRERELEASE_PATTERN.fullmatch(value):
        return parse_version(match["base"]), True
    return parse_version(value), False


def select_prerelease(root: Path, version: str) -> str:
    tags = git(root, "tag", "--list", f"v{version}rc*").splitlines()
    numbers = []
    for tag in tags:
        match = PRERELEASE_PATTERN.fullmatch(tag.removeprefix("v"))
        if match and match["base"] == version:
            numbers.append(int(match["number"]))
    return f"{version}rc{max(numbers, default=0) + 1}"


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


def check_readiness(root: Path) -> None:
    integration = root / MANIFEST.parent
    if not (integration / "__init__.py").is_file():
        raise ValueError("Missing integration __init__.py.")
    manifest = json.loads((root / MANIFEST).read_text(encoding="utf-8"))
    expected = {
        "domain": "sh_entity_status",
        "name": "SmartHass Entity Status",
        "documentation": "https://github.com/NateGr/sh-hass-entity-status",
        "issue_tracker": "https://github.com/NateGr/sh-hass-entity-status/issues",
    }
    for key, value in expected.items():
        if manifest.get(key) != value:
            raise ValueError(f"manifest.{key} must be {value!r}.")
    parse_release_version(manifest["version"])
    if "@NateGr" not in manifest.get("codeowners", []):
        raise ValueError("manifest.codeowners must include @NateGr.")
    if not (integration / "brand" / "icon.png").is_file():
        raise ValueError("Missing integration brand/icon.png required for HACS.")
    hacs = json.loads((root / "hacs.json").read_text(encoding="utf-8"))
    if hacs.get("name") != expected["name"] or hacs.get("content_in_root") is not False:
        raise ValueError("HACS metadata must match the integration name and layout.")
    if (
        not hacs.get("homeassistant")
        or manifest.get("homeassistant") != hacs["homeassistant"]
    ):
        raise ValueError(
            "Manifest and HACS minimum Home Assistant versions must match."
        )
    if hacs.get("zip_release") or "filename" in hacs:
        raise ValueError("Use tagged repository files, not custom HACS ZIP releases.")
    if not any(
        path.name != "test_release.py" for path in (root / "tests").rglob("test_*.py")
    ):
        raise ValueError("Integration tests are required.")
    requirements = (root / "requirements_test.txt").read_text(encoding="utf-8")
    if not re.search(
        r"^pytest-homeassistant-custom-component==\S+$", requirements, re.MULTILINE
    ):
        raise ValueError(
            "Pin pytest-homeassistant-custom-component in requirements_test.txt."
        )


def prepare(
    root: Path, pages: list, bump: str, override: str, prerelease: bool = False
) -> dict[str, str]:
    check_readiness(root)
    manifest_path = root / MANIFEST
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    version = select_version(
        release_baseline(manifest["version"], pages), bump, override
    )
    if prerelease:
        version = select_prerelease(root, version)
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
    base_version, _ = parse_release_version(version)
    if base_version <= parse_version(previous["version"]):
        raise ValueError("Release commit does not increase the manifest version.")
    previous = previous.copy()
    previous["version"] = version
    if previous != candidate:
        raise ValueError("Release commit must change only manifest.version.")


def recover(root: Path, version: str) -> dict[str, str]:
    """Locate an already-tagged release commit so publication can be retried."""
    _, prerelease = parse_release_version(version)
    if git(root, "cat-file", "-t", f"refs/tags/v{version}") != "tag":
        raise ValueError("Recovery requires an annotated release tag.")
    candidate = git(root, "rev-parse", f"refs/tags/v{version}^{{commit}}")
    parents = git(root, "rev-list", "--parents", "-n", "1", candidate).split()
    if len(parents) != 2:
        raise ValueError("Expected a release commit with exactly one parent.")
    git(
        root,
        "merge-base",
        "--is-ancestor",
        parents[1] if prerelease else candidate,
        "origin/main",
    )
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
    parser.add_argument("command", choices=["check", "prepare", "recover"])
    parser.add_argument("--bump", choices=["patch", "minor", "major"], default="patch")
    parser.add_argument("--version", default="")
    parser.add_argument("--releases", type=Path)
    parser.add_argument("--prerelease", action="store_true")
    arguments = parser.parse_args()
    try:
        if arguments.command == "check":
            check_readiness(ROOT)
            print("Integration readiness checks passed.")
            return
        if arguments.command == "recover":
            if arguments.prerelease:
                raise ValueError("Recovery determines release type from the version.")
            values = recover(ROOT, arguments.version)
        else:
            if arguments.releases is None:
                raise ValueError(
                    "prepare requires --releases with paginated GitHub release JSON."
                )
            pages = json.loads(arguments.releases.read_text(encoding="utf-8"))
            values = prepare(
                ROOT, pages, arguments.bump, arguments.version, arguments.prerelease
            )
    except (
        KeyError,
        OSError,
        TypeError,
        ValueError,
        subprocess.CalledProcessError,
    ) as error:
        parser.exit(1, f"Release preflight failed: {error}\n")
    values["prerelease"] = str(parse_release_version(values["version"])[1]).lower()
    print(json.dumps(values))
    if output := os.environ.get("GITHUB_OUTPUT"):
        with Path(output).open("a", encoding="utf-8") as stream:
            stream.writelines(f"{key}={value}\n" for key, value in values.items())


if __name__ == "__main__":
    sys.exit(main())
