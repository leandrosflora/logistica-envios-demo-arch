#!/usr/bin/env python3
"""Stage MkDocs sources so English is the default i18n language.

The repository keeps Portuguese pages as unsuffixed ``*.md`` files and English
translations as ``*.en.md`` files. When an English translation exists, this
hook exposes the original Portuguese source as ``*.pt.md`` in a temporary docs
tree expected by ``mkdocs-static-i18n``.

Pages that do not yet have an English translation remain unsuffixed so they stay
reachable during incremental migration instead of producing broken links.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from mkdocs.plugins import event_priority

_SOURCE_DOCS_DIR: Path | None = None
_STAGE_ROOT: Path | None = None
_STAGE_DOCS_DIR: Path | None = None


def _prepare_stage() -> None:
    if _SOURCE_DOCS_DIR is None or _STAGE_DOCS_DIR is None:
        raise RuntimeError("MkDocs language staging was not initialized")

    if _STAGE_DOCS_DIR.exists():
        shutil.rmtree(_STAGE_DOCS_DIR)
    shutil.copytree(_SOURCE_DOCS_DIR, _STAGE_DOCS_DIR)

    for page in sorted(_STAGE_DOCS_DIR.rglob("*.md")):
        if page.name.endswith((".en.md", ".pt.md")):
            continue

        english_page = page.with_name(f"{page.stem}.en.md")
        if not english_page.exists():
            continue

        portuguese_page = page.with_name(f"{page.stem}.pt.md")
        if portuguese_page.exists():
            raise RuntimeError(
                f"Cannot stage Portuguese page because {portuguese_page} already exists"
            )
        page.rename(portuguese_page)


@event_priority(100)
def on_config(config):
    """Point MkDocs at a staged i18n-compatible docs tree."""

    global _SOURCE_DOCS_DIR, _STAGE_ROOT, _STAGE_DOCS_DIR

    incoming_docs_dir = Path(config.docs_dir).resolve()

    # Internal language builds triggered by mkdocs-static-i18n reuse the same
    # config instance. Keep using the already staged tree in those builds.
    if _STAGE_DOCS_DIR is not None and incoming_docs_dir == _STAGE_DOCS_DIR:
        return config

    _SOURCE_DOCS_DIR = incoming_docs_dir

    if _STAGE_ROOT is not None and _STAGE_ROOT.exists():
        shutil.rmtree(_STAGE_ROOT)

    _STAGE_ROOT = Path(tempfile.mkdtemp(prefix="mkdocs-english-default-"))
    _STAGE_DOCS_DIR = _STAGE_ROOT / "docs"
    _STAGE_DOCS_DIR.mkdir(parents=True, exist_ok=True)
    config.docs_dir = str(_STAGE_DOCS_DIR)
    return config


@event_priority(100)
def on_pre_build(config) -> None:
    """Refresh staged content before each MkDocs language build."""

    _prepare_stage()


def on_page_context(context, page, **kwargs):
    """Keep Material's edit link pointed at the real Portuguese source file."""

    edit_url = getattr(page, "edit_url", None)
    if edit_url and ".pt.md" in edit_url:
        page.edit_url = edit_url.replace(".pt.md", ".md")
    return context


def on_shutdown() -> None:
    """Remove the temporary staging tree after build/serve exits."""

    global _STAGE_ROOT, _STAGE_DOCS_DIR
    if _STAGE_ROOT is not None and _STAGE_ROOT.exists():
        shutil.rmtree(_STAGE_ROOT)
    _STAGE_ROOT = None
    _STAGE_DOCS_DIR = None
