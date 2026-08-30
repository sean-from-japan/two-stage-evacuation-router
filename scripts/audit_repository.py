"""Fail on common publication-safety findings in files and Git blobs."""

from __future__ import annotations

import argparse
import re
import subprocess
from collections.abc import Iterable
from pathlib import Path

WINDOWS_HOME = b"C:" + bytes([92]) + b"Users" + bytes([92])

PATTERNS = {
    "email address": re.compile(
        rb"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
    ),
    "private key": re.compile(rb"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "GitHub token": re.compile(rb"gh[pousr]_[A-Za-z0-9_]{30,}"),
    "AWS access key": re.compile(rb"AKIA[0-9A-Z]{16}"),
    "secret assignment": re.compile(
        rb"(?i)(api[_-]?key|password|secret|token)\s*[:=]\s*['\"][^'\"]+['\"]"
    ),
    "macOS home path": re.compile((b"/" + b"Users" + b"/") + rb"[^/\s]+/"),
    "Windows home path": re.compile(re.escape(WINDOWS_HOME) + rb"[^\\\s]+" + rb"\\"),
    "seven-digit identifier": re.compile(rb"(?<!\d)\d{7}(?!\d)"),
}

TEXT_SUFFIXES = {
    ".cfg",
    ".css",
    ".html",
    ".ini",
    ".json",
    ".md",
    ".py",
    ".toml",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
}

IGNORED_PARTS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
}


def working_tree_files(root: Path) -> Iterable[tuple[str, bytes]]:
    for path in sorted(root.rglob("*")):
        if (
            not path.is_file()
            or IGNORED_PARTS.intersection(path.parts)
            or any(part.endswith(".egg-info") for part in path.parts)
            or path.suffix not in TEXT_SUFFIXES
        ):
            continue
        yield str(path.relative_to(root)), path.read_bytes()


def git_blobs(root: Path) -> Iterable[tuple[str, bytes]]:
    listing = subprocess.run(
        ["git", "rev-list", "--objects", "--all"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    seen: set[str] = set()
    for line in listing:
        sha, separator, path = line.partition(" ")
        if not separator or sha in seen or Path(path).suffix not in TEXT_SUFFIXES:
            continue
        object_type = subprocess.run(
            ["git", "cat-file", "-t", sha],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        if object_type != "blob":
            continue
        seen.add(sha)
        content = subprocess.run(
            ["git", "cat-file", "blob", sha],
            cwd=root,
            check=True,
            capture_output=True,
        ).stdout
        yield f"git:{sha[:12]}:{path}", content


def scan(entries: Iterable[tuple[str, bytes]]) -> list[str]:
    findings = []
    for label, content in entries:
        for name, pattern in PATTERNS.items():
            if pattern.search(content):
                findings.append(f"{label}: {name}")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", type=Path, default=Path.cwd())
    parser.add_argument("--git-history", action="store_true")
    arguments = parser.parse_args()
    root = arguments.root.resolve()
    findings = scan(working_tree_files(root))
    if arguments.git_history:
        findings.extend(scan(git_blobs(root)))
    if findings:
        print("Publication audit failed:")
        for finding in sorted(set(findings)):
            print(f"- {finding}")
        return 1
    print("Publication audit passed: no configured patterns found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
