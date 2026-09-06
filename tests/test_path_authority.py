from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from scripts.path_authority import (
    PathAuthorityError,
    build_remote_containment_guard,
    remote_shell_path,
    require_remote_child,
    require_remote_path,
)


@pytest.mark.parametrize("suffix", ["job", "a/b", "project/model.pt", "potcars/POTCAR"])
@pytest.mark.parametrize("root", ["/home/sbq/sbq", "~/sbq"])
def test_descendants_pass(root, suffix):
    path = f"{root}/{suffix}"
    assert require_remote_path(path, root=root) == path


@pytest.mark.parametrize("suffix", ["../outside", "a/../../outside", "a/../job", "../sbq/job"])
@pytest.mark.parametrize("root", ["/home/sbq/sbq", "~/sbq"])
def test_traversal_rejected_even_if_normalization_would_return_inside(root, suffix):
    with pytest.raises(PathAuthorityError, match="traversal"):
        require_remote_path(f"{root}/{suffix}", root=root)


@pytest.mark.parametrize("root,path", [
    ("/home/sbq/sbq", "/home/sbq/sbq-other/job"),
    ("/home/sbq/sbq", "/home/sbq/other/job"),
    ("~/sbq", "~/other/job"), ("~/sbq", "~/sbq-other/job"),
    ("~/sbq", "/home/sbq/sbq/job"), ("/home/sbq/sbq", "~/sbq/job"),
])
def test_sibling_and_incompatible_style_rejected(root, path):
    with pytest.raises(PathAuthorityError):
        require_remote_path(path, root=root)


@pytest.mark.parametrize("path", [
    "~/sbq/job;rm", "~/sbq/job&&whoami", "~/sbq/job|cat", "~/sbq/$(whoami)",
    "~/sbq/job`whoami`", "~/sbq/job name", "~/sbq/jo\x00b", "~/sbq/job\nwhoami",
    "~/sbq/job'", '~/sbq/job"', "~/sbq/\\outside", "~/sbq/~other/job", "~other/sbq/job",
    "sbq/job", "", None,
])
def test_unsafe_text_rejected(path):
    with pytest.raises(PathAuthorityError):
        require_remote_path(path, root="~/sbq")


@pytest.mark.parametrize("root,path,expected", [
    ("~/sbq", "~/sbq//project/./job", "~/sbq/project/job"),
    ("/home/sbq/sbq/", "/home/sbq/sbq//project/./job/", "/home/sbq/sbq/project/job"),
])
def test_normalization(root, path, expected):
    assert require_remote_path(path, root=root) == expected


def test_root_policy_and_invalid_roots():
    assert require_remote_path("~/sbq/.", root="~/sbq") == "~/sbq"
    with pytest.raises(PathAuthorityError, match="must be below"):
        require_remote_path("~/sbq/", root="~/sbq", allow_root=False)
    for root in ("~/sbq/../sbq", "/home/~other", "relative", "~/sbq;id"):
        with pytest.raises(PathAuthorityError):
            build_remote_containment_guard(root, [])


def test_shell_expression_preserves_home_expansion():
    assert remote_shell_path("~") == '"$HOME"'
    assert remote_shell_path("~/sbq/project/job") == '"$HOME"/sbq/project/job'
    assert remote_shell_path("/home/sbq/sbq/job") == "/home/sbq/sbq/job"
    with pytest.raises(PathAuthorityError):
        remote_shell_path("~/sbq/../outside")


@pytest.mark.parametrize("name", ["../POTCAR", "/tmp/POTCAR", "~/other/POTCAR", ".", "INCAR;id", "C:\\POTCAR"])
def test_manifest_child_rejects_absolute_traversal_and_shell_paths(name):
    with pytest.raises(PathAuthorityError):
        require_remote_child(name, root="~/sbq/job")


@pytest.fixture
def bash():
    executable = shutil.which("bash")
    if executable is None and os.name == "nt":
        candidate = Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Git/bin/bash.exe"
        executable = str(candidate) if candidate.is_file() else None
    if executable is None:
        pytest.skip("canonical filesystem test requires bash")
    probe = subprocess.run([executable, "-c", "command -v realpath"], capture_output=True, timeout=10)
    if probe.returncode:
        pytest.skip("canonical filesystem test requires realpath")
    return executable


def _execute_guard(bash, home, paths):
    return subprocess.run(
        [bash, "-c", build_remote_containment_guard("~/sbq", paths)],
        env={**os.environ, "HOME": home.as_posix()}, text=True, capture_output=True, timeout=10,
    )


@pytest.mark.parametrize("target_exists", [True, False])
def test_remote_canonical_symlink_escape_rejected(tmp_path, bash, target_exists):
    home = tmp_path / "home"
    (home / "sbq").mkdir(parents=True)
    outside = tmp_path / "outside"
    if target_exists:
        outside.mkdir()
    (home / "sbq/link").symlink_to(outside, target_is_directory=True)
    result = _execute_guard(bash, home, ["~/sbq/link/job"])
    assert result.returncode != 0
    assert "PATH_AUTHORITY_ESCAPE_REJECTED" in result.stderr


def test_remote_normal_descendant_and_internal_symlink_pass(tmp_path, bash):
    home = tmp_path / "home"
    (home / "sbq/project").mkdir(parents=True)
    (home / "sbq/link").symlink_to(home / "sbq/project", target_is_directory=True)
    result = _execute_guard(bash, home, (path for path in ["~/sbq/project/job", "~/sbq/link/job"]))
    assert result.returncode == 0, result.stderr
    assert not (home / "sbq/project/job").exists()  # Guard must remain read-only.


def test_missing_approved_root_fails_closed(tmp_path, bash):
    result = _execute_guard(bash, tmp_path, ["~/sbq/job"])
    assert result.returncode != 0
    assert "PATH_AUTHORITY_ROOT_MISSING" in result.stderr


def test_leaf_file_symlink_escape_rejected(tmp_path, bash):
    home = tmp_path / "home"
    (home / "sbq/job").mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.write_text("test fixture", encoding="utf-8")
    (home / "sbq/job/POTCAR").symlink_to(outside)
    result = _execute_guard(bash, home, ["~/sbq/job", "~/sbq/job/POTCAR"])
    assert result.returncode != 0
    assert "PATH_AUTHORITY_ESCAPE_REJECTED" in result.stderr
