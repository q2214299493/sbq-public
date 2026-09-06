from __future__ import annotations

import posixpath
import re
import shlex
from pathlib import PurePosixPath
from typing import Iterable


_SAFE_REMOTE_PATH = re.compile(r"^[A-Za-z0-9._~/-]+$")


class PathAuthorityError(ValueError):
    """Raised when a requested path violates an approved path boundary."""


def _require_text(value: object, label: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise PathAuthorityError(f"{label} must be non-empty")
    if "\x00" in text:
        raise PathAuthorityError(f"{label} contains a NUL byte")
    if not _SAFE_REMOTE_PATH.fullmatch(text):
        raise PathAuthorityError(
            f"{label} contains forbidden shell/path characters"
        )
    return text


def _path_style(value: str, label: str) -> str:
    if value == "~" or value.startswith("~/"):
        if "~" in value[1:]:
            raise PathAuthorityError(
                f"{label} contains an invalid '~' component"
            )
        return "home"
    if value.startswith("/"):
        if "~" in value:
            raise PathAuthorityError(
                f"{label} contains an invalid '~' component"
            )
        return "absolute"
    raise PathAuthorityError(
        f"{label} must be an absolute POSIX path or a ~/ path"
    )


def _reject_traversal(value: str, label: str) -> None:
    parts = PurePosixPath(value).parts
    if ".." in parts:
        raise PathAuthorityError(
            f"{label} contains parent-directory traversal '..'"
        )


def _normalize(value: str) -> str:
    if value == "~":
        return "~"
    if value.startswith("~/"):
        relative = value[2:]
        normalized = posixpath.normpath("/" + relative).lstrip("/")
        if normalized in {"", "."}:
            return "~"
        return "~/" + normalized
    return posixpath.normpath(value)


def _anchored(value: str) -> PurePosixPath:
    if value == "~":
        return PurePosixPath("/__PATH_AUTHORITY_HOME__")
    if value.startswith("~/"):
        return PurePosixPath("/__PATH_AUTHORITY_HOME__") / value[2:]
    return PurePosixPath(value)


def require_remote_path(
    value: object,
    *,
    root: str,
    label: str = "remote path",
    allow_root: bool = True,
) -> str:
    candidate_raw = _require_text(value, label)
    root_raw = _require_text(root, "approved path root")

    candidate_style = _path_style(candidate_raw, label)
    root_style = _path_style(root_raw, "approved path root")

    if candidate_style != root_style:
        raise PathAuthorityError(
            f"{label} and approved path root use incompatible path styles"
        )

    _reject_traversal(candidate_raw, label)
    _reject_traversal(root_raw, "approved path root")

    candidate = _normalize(candidate_raw)
    approved_root = _normalize(root_raw)

    candidate_path = _anchored(candidate)
    root_path = _anchored(approved_root)

    try:
        candidate_path.relative_to(root_path)
    except ValueError as exc:
        raise PathAuthorityError(
            f"{label} escapes the configured write boundary"
        ) from exc

    if not allow_root and candidate_path == root_path:
        raise PathAuthorityError(
            f"{label} must be below, not equal to, the approved root"
        )

    return candidate


def remote_shell_path(value: str) -> str:
    value = _require_text(value, "remote shell path")
    _path_style(value, "remote shell path")
    _reject_traversal(value, "remote shell path")
    value = _normalize(value)
    if value == "~":
        return '"$HOME"'
    if value.startswith("~/"):
        relative = value[2:]
        return f'"$HOME"/{shlex.quote(relative)}'
    return shlex.quote(value)


def require_remote_child(value: object, *, root: str, label: str = "remote file") -> str:
    """Validate a manifest-relative filename before joining local or remote paths."""
    relative = _require_text(value, label)
    if relative.startswith(("/", "~")):
        raise PathAuthorityError(f"{label} must be relative to its approved directory")
    return require_remote_path(f"{root}/{relative}", root=root, label=label, allow_root=False)


def build_remote_containment_guard(
    root: str,
    paths: Iterable[str],
) -> str:
    root_raw = _require_text(root, "approved path root")
    _path_style(root_raw, "approved path root")
    _reject_traversal(root_raw, "approved path root")
    normalized_root = _normalize(root_raw)

    normalized_paths = [
        require_remote_path(
            value,
            root=normalized_root,
            label="remote execution path",
        )
        for value in paths
    ]

    root_expr = remote_shell_path(normalized_root)

    commands = [
        "set -eu",
        f"__pa_root={root_expr}",
        (
            'test -d "$__pa_root" || '
            '{ echo "PATH_AUTHORITY_ROOT_MISSING" >&2; exit 71; }'
        ),
        (
            '__pa_root_real="$(realpath -e -- "$__pa_root")" || '
            '{ echo "PATH_AUTHORITY_ROOT_REALPATH_FAILED" >&2; exit 72; }'
        ),
    ]

    for index, path in enumerate(normalized_paths):
        path_expr = remote_shell_path(path)
        commands.extend(
            [
                f"__pa_path_{index}={path_expr}",
                (
                    f'__pa_real_{index}="$(realpath -m -- '
                    f'"$__pa_path_{index}")" || '
                    f'{{ echo "PATH_AUTHORITY_REALPATH_FAILED" >&2; exit 73; }}'
                ),
                (
                    f'case "$__pa_real_{index}" in '
                    f'"$__pa_root_real"|"${{__pa_root_real%/}}"/*) ;; '
                    f'*) echo "PATH_AUTHORITY_ESCAPE_REJECTED" >&2; '
                    f'exit 74 ;; esac'
                ),
            ]
        )

    return "; ".join(commands)
