"""Project scoping shared by the session helpers."""
from __future__ import annotations

import re


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.casefold()).strip("-")


def project_matches(needle: str, *haystacks: str) -> bool:
    """Case-insensitive substring match, slug-tolerant.

    Harnesses store projects as real cwds (``/home/me/app``), lossy slugs
    (``-home-me-app``, ``--home-me-app--``), or bare basenames. A real path
    passed as ``needle`` should still find slug-keyed sessions, so the match
    also succeeds when the slugified needle is inside the slugified haystack.
    """
    wanted = needle.casefold().strip()
    if not wanted:
        return True
    haystack = " ".join(haystacks)
    if wanted in haystack.casefold():
        return True
    slug = _slug(wanted)
    return bool(slug) and slug in _slug(haystack)
