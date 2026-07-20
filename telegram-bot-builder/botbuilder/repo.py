"""Fetch a repository and build a condensed digest for analysis."""

import os
import re
import subprocess
from typing import Dict, List, Optional, Tuple

from .config import (
    ENTRY_POINT_NAMES,
    IGNORE_DIRS,
    LANG_BY_EXT,
    MANIFEST_FILES,
    MAX_FILE_BYTES,
    MAX_TOTAL_DIGEST_BYTES,
    MAX_TREE_ENTRIES,
)
from .models import RepoDigest

_README_RE = re.compile(r"^readme(\.md|\.rst|\.txt|\.markdown)?$", re.IGNORECASE)


def normalize_source(source: str) -> Tuple[str, bool]:
    """Return (resolved, is_local). Accepts local paths and several URL forms."""
    if os.path.isdir(source):
        return os.path.abspath(source), True
    if source.startswith(("http://", "https://", "git@", "ssh://")):
        return source, False
    # Shorthand like "owner/repo" or "github.com/owner/repo".
    if re.match(r"^[\w.-]+/[\w.-]+$", source):
        return f"https://github.com/{source}", False
    if source.startswith("github.com/"):
        return f"https://{source}", False
    raise ValueError(f"Unrecognized repo source: {source!r}")


def clone_repo(url: str, dest: str, timeout: int = 180) -> str:
    """Shallow-clone `url` into `dest` and return the checkout path."""
    proc = subprocess.run(
        ["git", "clone", "--depth", "1", "--quiet", url, dest],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"git clone failed: {proc.stderr.strip() or proc.stdout.strip()}")
    return dest


def repo_name(source: str) -> str:
    base = source.rstrip("/").split("/")[-1]
    return base[:-4] if base.endswith(".git") else base or "repo"


def _read_text(path: str, limit: int = MAX_FILE_BYTES) -> Optional[str]:
    """Read up to `limit` bytes of a text file, or None if it looks binary."""
    try:
        with open(path, "rb") as fh:
            chunk = fh.read(limit + 1)
    except OSError:
        return None
    if b"\x00" in chunk:
        return None
    text = chunk.decode("utf-8", errors="replace")
    if len(chunk) > limit:
        text = text[:limit] + "\n... [truncated]\n"
    return text


def build_digest(root: str, url: str, name: str) -> RepoDigest:
    """Walk the repo and assemble a bounded RepoDigest."""
    languages: Dict[str, int] = {}
    tree: List[str] = []
    entry_points: List[str] = []
    manifest_paths: List[str] = []
    readme_path: Optional[str] = None
    total_files = 0

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS and not d.startswith(".")]
        rel_dir = os.path.relpath(dirpath, root)
        for fn in sorted(filenames):
            total_files += 1
            rel = fn if rel_dir == "." else os.path.join(rel_dir, fn)
            if len(tree) < MAX_TREE_ENTRIES:
                tree.append(rel)

            ext = os.path.splitext(fn)[1].lower()
            lang = LANG_BY_EXT.get(ext)
            if lang:
                languages[lang] = languages.get(lang, 0) + 1

            if fn in MANIFEST_FILES:
                manifest_paths.append(rel)
            if fn in ENTRY_POINT_NAMES or rel_dir.split(os.sep)[0] in ("cmd", "bin"):
                if lang or fn in ENTRY_POINT_NAMES:
                    entry_points.append(rel)
            if readme_path is None and _README_RE.match(fn) and rel_dir == ".":
                readme_path = rel

    primary_language = max(languages, key=languages.get) if languages else None

    # Collect content, respecting a global byte budget so the digest stays small.
    budget = MAX_TOTAL_DIGEST_BYTES
    manifests: Dict[str, str] = {}
    key_files: Dict[str, str] = {}
    readme_text: Optional[str] = None

    def take(rel: str) -> Optional[str]:
        nonlocal budget
        if budget <= 0:
            return None
        text = _read_text(os.path.join(root, rel), min(MAX_FILE_BYTES, budget))
        if text is not None:
            budget -= len(text)
        return text

    if readme_path:
        readme_text = take(readme_path)
    for rel in manifest_paths:
        text = take(rel)
        if text is not None:
            manifests[os.path.basename(rel)] = text
    for rel in entry_points[:12]:
        text = take(rel)
        if text is not None:
            key_files[rel] = text

    return RepoDigest(
        name=name,
        url=url,
        root=root,
        languages=languages,
        primary_language=primary_language,
        file_tree=tree,
        manifests=manifests,
        readme=readme_text,
        entry_points=entry_points,
        key_files=key_files,
        total_files=total_files,
        truncated=(total_files > len(tree)) or budget <= 0,
    )
