"""Branch / commit / PR plumbing.

A fresh worktree is created from origin/master for every PR, so a run
can never inherit a stale base (the PR #37 failure mode) and the user's
own checkout is left untouched.
"""
from __future__ import annotations

import subprocess
import tempfile
import shutil
from pathlib import Path

from .config import REPO_ROOT


def sh(args: list[str], cwd: Path | None = None, check: bool = True) -> str:
    p = subprocess.run(args, cwd=cwd or REPO_ROOT, capture_output=True, text=True)
    if check and p.returncode != 0:
        raise RuntimeError(f"{' '.join(args)} failed: {p.stderr.strip()}")
    return p.stdout


def open_pr(branch: str, files: dict[Path, str], title: str, body: str,
            labels: list[str] | None = None) -> str:
    """Create a branch off the latest origin/master, commit `files`, open a PR."""
    sh(["git", "fetch", "origin", "master", "--quiet"])
    workdir = Path(tempfile.mkdtemp(prefix="ml4db-pr-"))
    wt = workdir / "wt"
    created = False
    try:
        sh(["git", "worktree", "add", "--detach", str(wt), "origin/master"])
        created = True
        sh(["git", "checkout", "-B", branch], cwd=wt)
        for path, content in files.items():
            dest = wt / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")
        sh(["git", "add", "-A"], cwd=wt)
        sh(["git", "commit", "-m", title], cwd=wt)
        sh(["git", "push", "-u", "origin", branch], cwd=wt)
        body_file = workdir / "body.md"
        body_file.write_text(body, encoding="utf-8")
        args = ["gh", "pr", "create", "--repo", "LumingSun/ML4DB-paper-list",
                "--base", "master", "--head", branch, "--title", title,
                "--body-file", str(body_file)]
        out = sh(args, cwd=wt)
        url = out.strip().splitlines()[-1] if out.strip() else ""
        if labels and url:
            sh(["gh", "pr", "edit", url, "--add-label", ",".join(labels)], cwd=wt, check=False)
        return url
    finally:
        if created:
            sh(["git", "worktree", "remove", "--force", str(wt)], check=False)
        shutil.rmtree(workdir, ignore_errors=True)
