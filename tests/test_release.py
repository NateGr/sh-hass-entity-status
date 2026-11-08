"""Exercise release versioning and recovery checks without Home Assistant."""

import json
import subprocess
from pathlib import Path

import pytest

from scripts.release import (
    MANIFEST,
    parse_version,
    prepare,
    recover,
    release_baseline,
    select_version,
    verify_release_metadata,
)


@pytest.mark.parametrize("version", ["0.0.0", "1.0.11", "12.34.56"])
def test_stable_version(version):
    assert parse_version(version) == tuple(int(part) for part in version.split("."))


@pytest.mark.parametrize(
    "version", ["v1.0.0", "1.0", "01.0.0", "1.0.0b1", "1.0.0\n", ""]
)
def test_invalid_version(version):
    with pytest.raises(ValueError):
        parse_version(version)


@pytest.mark.parametrize(
    ("bump", "expected"), [("patch", "1.2.4"), ("minor", "1.3.0"), ("major", "2.0.0")]
)
def test_version_bumps(bump, expected):
    assert select_version("1.2.3", bump) == expected


def test_explicit_version():
    assert select_version("0.2.0", "patch", "1.0.0") == "1.0.0"


@pytest.mark.parametrize("version", ["0.1.0", "0.2.0"])
def test_version_must_increase(version):
    with pytest.raises(ValueError, match="greater"):
        select_version("0.2.0", "patch", version)


def test_unknown_bump():
    with pytest.raises(ValueError, match="Unknown"):
        select_version("0.2.0", "automatic")


def test_release_baseline_ignores_unpublished_versions():
    pages = [
        [{"tag_name": "v0.3.0", "draft": False, "prerelease": False}],
        [
            {"tag_name": "v0.4.0", "draft": False, "prerelease": False},
            {"tag_name": "v9.0.0", "draft": True, "prerelease": False},
            {"tag_name": "v8.0.0", "draft": False, "prerelease": True},
            {"tag_name": "legacy", "draft": False, "prerelease": False},
        ],
    ]
    assert release_baseline("0.2.0", pages) == "0.4.0"
    assert release_baseline("1.0.0", pages) == "1.0.0"
    assert release_baseline("0.2.0", []) == "0.2.0"


def run_git(root: Path, *arguments: str) -> str:
    return subprocess.check_output(["git", *arguments], cwd=root, text=True).strip()


@pytest.fixture
def git_repository(tmp_path):
    path = tmp_path / MANIFEST
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps({"domain": "sh_entity_status", "version": "0.2.0"}), encoding="utf-8"
    )
    run_git(tmp_path, "init", "--initial-branch=main")
    run_git(tmp_path, "config", "user.name", "Release tests")
    run_git(tmp_path, "config", "user.email", "release-tests@example.invalid")
    run_git(tmp_path, "config", "commit.gpgsign", "false")
    run_git(tmp_path, "add", ".")
    run_git(tmp_path, "commit", "-m", "Initial")
    return tmp_path


def test_prepare_updates_only_version(git_repository):
    previous = json.loads((git_repository / MANIFEST).read_text(encoding="utf-8"))
    assert prepare(git_repository, [], "patch", "") == {"version": "0.2.1"}
    candidate = json.loads((git_repository / MANIFEST).read_text(encoding="utf-8"))
    verify_release_metadata(previous, candidate, "0.2.1")
    assert run_git(git_repository, "diff", "--name-only") == MANIFEST.as_posix()


def test_prepare_rejects_existing_tag(git_repository):
    run_git(git_repository, "tag", "v0.2.1")
    with pytest.raises(ValueError, match="already exists"):
        prepare(git_repository, [], "patch", "")


@pytest.fixture
def released_repository(git_repository):
    prepare(git_repository, [], "patch", "")
    run_git(git_repository, "add", MANIFEST.as_posix())
    run_git(
        git_repository, "commit", "-m", "Release v0.2.1\n\nSmartHass-Release: 0.2.1"
    )
    run_git(git_repository, "tag", "-a", "v0.2.1", "-m", "Release v0.2.1")
    run_git(git_repository, "update-ref", "refs/remotes/origin/main", "HEAD")
    return git_repository


def test_recovery_finds_release_commit(released_repository):
    expected = run_git(released_repository, "rev-parse", "HEAD")
    assert recover(released_repository, "0.2.1") == {
        "version": "0.2.1",
        "candidate": expected,
    }


def test_recovery_rejects_lightweight_tag(released_repository):
    run_git(released_repository, "tag", "-d", "v0.2.1")
    run_git(released_repository, "tag", "v0.2.1")
    with pytest.raises(ValueError, match="annotated"):
        recover(released_repository, "0.2.1")


def test_recovery_rejects_commit_outside_main(released_repository):
    run_git(released_repository, "update-ref", "refs/remotes/origin/main", "HEAD^")
    with pytest.raises(subprocess.CalledProcessError):
        recover(released_repository, "0.2.1")


@pytest.mark.parametrize(
    ("previous", "candidate", "version"),
    [
        ({"version": "0.2.0"}, {"version": "0.2.2"}, "0.2.1"),
        ({"version": "0.2.1"}, {"version": "0.2.1"}, "0.2.1"),
        ({"version": "0.2.0", "domain": "x"}, {"version": "0.2.1"}, "0.2.1"),
    ],
)
def test_invalid_release_metadata(previous, candidate, version):
    with pytest.raises(ValueError):
        verify_release_metadata(previous, candidate, version)


@pytest.mark.parametrize("defect", ["message", "extra-file"])
def test_recovery_rejects_invalid_release_commits(git_repository, defect):
    prepare(git_repository, [], "patch", "")
    if defect == "extra-file":
        (git_repository / "README.md").write_text("unexpected", encoding="utf-8")
        run_git(git_repository, "add", "README.md")
    run_git(git_repository, "add", MANIFEST.as_posix())
    message = "Unknown commit" if defect == "message" else "SmartHass-Release: 0.2.1"
    run_git(git_repository, "commit", "-m", message)
    run_git(git_repository, "tag", "-a", "v0.2.1", "-m", "Release v0.2.1")
    run_git(git_repository, "update-ref", "refs/remotes/origin/main", "HEAD")
    with pytest.raises(ValueError):
        recover(git_repository, "0.2.1")
