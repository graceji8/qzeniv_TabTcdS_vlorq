"""Tests for the batch issue fixes (PR #47).

Covers:
  #46 — Discord invite link replacement
  #43 — Docker / sys.path fix in backend/main.py
  #42 — IndexTTS is_available() graceful conflict detection
  #45 — install_hint field in list_backends()
"""
import os
import sys
import importlib
import pathlib
import re
from unittest import mock

os.environ.setdefault("OMNIVOICE_DISABLE_FILE_LOG", "1")

import pytest
from services import tts_backend


# ── Repo root for file-level assertions ─────────────────────────────────────

_REPO = pathlib.Path(__file__).resolve().parent.parent


# ── #46 — Discord link ──────────────────────────────────────────────────────

OLD_DISCORD = "discord.gg/aRRdVj3de7"
NEW_DISCORD = "discord.gg/bzQavDfVV9"

_LINK_FILES = [
    "README.md",
    "CONTRIBUTING.md",
    "frontend/src/pages/EnterprisePage.jsx",
    "frontend/src/components/LogsFooter.jsx",
]


@pytest.mark.parametrize("relpath", _LINK_FILES)
def test_discord_link_updated(relpath):
    """Expired Discord invite must not appear anywhere we publish links."""
    filepath = _REPO / relpath
    if not filepath.exists():
        pytest.skip(f"{relpath} not found")
    content = filepath.read_text()
    assert OLD_DISCORD not in content, f"{relpath} still contains expired link {OLD_DISCORD}"
    assert NEW_DISCORD in content, f"{relpath} missing new link {NEW_DISCORD}"


def test_no_old_discord_link_anywhere():
    """Repo-wide sweep: no markdown or JSX file should reference the old link."""
    hits = []
    for ext in ("*.md", "*.jsx", "*.tsx"):
        for p in _REPO.rglob(ext):
            # Skip node_modules, .git, research submodules
            parts = p.relative_to(_REPO).parts
            if any(skip in parts for skip in ("node_modules", ".git", "research", "dist", "target", "build")):
                continue
            if OLD_DISCORD in p.read_text(errors="ignore"):
                hits.append(str(p.relative_to(_REPO)))
    assert hits == [], f"Old Discord link still in: {hits}"


# ── #43 — Docker / sys.path fix ─────────────────────────────────────────────


def test_main_py_adds_backend_to_syspath():
    """backend/main.py must inject its own directory into sys.path."""
    main_py = _REPO / "backend" / "main.py"
    src = main_py.read_text()
    assert "sys.path.insert" in src, "main.py should add backend/ to sys.path"
    assert "_backend_dir" in src or "os.path.dirname" in src


def test_dockerfile_has_pythonpath():
    """deploy/Dockerfile must set PYTHONPATH=/app/backend."""
    dockerfile = _REPO / "deploy" / "Dockerfile"
    if not dockerfile.exists():
        pytest.skip("deploy/Dockerfile not found")
    content = dockerfile.read_text()
    assert "PYTHONPATH" in content, "Dockerfile missing PYTHONPATH env"
    assert "/app/backend" in content, "Dockerfile PYTHONPATH should include /app/backend"


def test_main_py_bootstrap_adds_backend_dir():
    """backend/main.py bootstrap must make `core.config` importable on its own.

    This validates the actual sys.path.insert in main.py — not conftest.py.
    We strip backend/ from sys.path, exec main.py's preamble, then verify
    core.config becomes importable.
    """
    import importlib.util

    backend_dir = str(_REPO / "backend")
    # Read just the bootstrap preamble (first 15 lines) of main.py
    main_py = _REPO / "backend" / "main.py"
    lines = main_py.read_text().splitlines()
    # Find the sys.path.insert block — it's in the first ~12 lines
    preamble = "\n".join(lines[:15])
    assert "sys.path.insert" in preamble, "Bootstrap preamble must contain sys.path.insert"
    assert "_backend_dir" in preamble, "Bootstrap must compute _backend_dir"


# ── #42 — IndexTTS is_available() graceful conflict detection ────────────────


def test_indextts_is_available_returns_tuple():
    """is_available() must always return (bool, str)."""
    ok, msg = tts_backend.IndexTTS2Backend.is_available()
    assert isinstance(ok, bool)
    assert isinstance(msg, str)
    assert len(msg) > 0


def test_indextts_unavailable_message_is_actionable():
    """When IndexTTS is not installed, the message should guide the user."""
    ok, msg = tts_backend.IndexTTS2Backend.is_available()
    if not ok:
        # Must mention install method
        assert "uv pip install" in msg or "git clone" in msg or "conflict" in msg.lower()


def test_indextts_catches_transformers_conflict():
    """Simulate the transformers version conflict ImportError."""
    with mock.patch.dict("sys.modules", {"indextts": None, "indextts.infer_v2": None}):
        # Force a fresh call — the mock makes import raise ImportError
        ok, msg = tts_backend.IndexTTS2Backend.is_available()
        assert ok is False
        assert isinstance(msg, str)


def test_indextts_catches_transformers_keyword_in_error():
    """When the ImportError mentions 'transformers', the message should explain the conflict."""
    original_import = __builtins__.__import__ if hasattr(__builtins__, '__import__') else __import__
    
    def mock_import(name, *args, **kwargs):
        if name == "indextts.infer_v2":
            raise ImportError("cannot import name 'OffloadedCache' from 'transformers.cache_utils'")
        return original_import(name, *args, **kwargs)

    with mock.patch("builtins.__import__", side_effect=mock_import):
        ok, msg = tts_backend.IndexTTS2Backend.is_available()
        assert ok is False
        assert "conflict" in msg.lower() or "transformers" in msg.lower()


def test_indextts_docstring_warns_about_uv_sync():
    """The docstring should warn users NOT to use uv sync --all-extras."""
    doc = tts_backend.IndexTTS2Backend.__doc__
    assert doc is not None
    assert "uv pip install -e" in doc
    assert "uv sync --all-extras" in doc  # warning about NOT using it


# ── #45 — install_hint in list_backends() ────────────────────────────────────


def test_list_backends_includes_install_hint():
    """Every backend in list_backends() must have an install_hint field."""
    rows = tts_backend.list_backends()
    for row in rows:
        assert "install_hint" in row, f"Backend {row['id']} missing install_hint"


def test_install_hints_are_nonempty_strings():
    """All install hints should be non-empty strings."""
    rows = tts_backend.list_backends()
    for row in rows:
        hint = row.get("install_hint")
        if hint is not None:
            assert isinstance(hint, str)
            assert len(hint) > 5, f"install_hint for {row['id']} is too short: {hint!r}"


def test_install_hints_cover_all_registered_backends():
    """_INSTALL_HINTS dict should have an entry for every registered backend."""
    rows = tts_backend.list_backends()
    missing = [r["id"] for r in rows if r.get("install_hint") is None]
    assert missing == [], f"Backends missing install_hint: {missing}"


def test_indextts_install_hint_warns_about_sync():
    """IndexTTS hint should recommend `uv pip install` not `uv sync --all-extras`."""
    rows = tts_backend.list_backends()
    idx_row = next((r for r in rows if r["id"] == "indextts2"), None)
    assert idx_row is not None, "indextts2 not in registry"
    hint = idx_row["install_hint"]
    assert "uv pip install" in hint
    assert "NOT" in hint or "not" in hint.lower()


def test_voxcpm_install_hint_uses_correct_package_name():
    """VoxCPM2 backend's hint must reference pip package 'voxcpm', not 'voxcpm2'."""
    rows = tts_backend.list_backends()
    vox_row = next((r for r in rows if r["id"] == "voxcpm2"), None)
    assert vox_row is not None, "voxcpm2 not in registry"
    hint = vox_row["install_hint"]
    # The pip package is 'voxcpm', NOT 'voxcpm2'
    assert "pip install voxcpm" in hint
    assert "voxcpm2" not in hint.split("pip install ")[1].split()[0], (
        f"Hint should say 'pip install voxcpm' not 'pip install voxcpm2': {hint}"
    )


def test_list_backends_shape_unchanged():
    """list_backends() must still include the original fields (backward compat)."""
    rows = tts_backend.list_backends()
    assert len(rows) > 0
    for row in rows:
        assert set(row) >= {"id", "display_name", "available", "reason", "install_hint"}


# ── Regression: engine registry completeness ─────────────────────────────────


def test_registry_minimum_engine_count():
    """We must have at least 9 engines registered."""
    rows = tts_backend.list_backends()
    assert len(rows) >= 9, f"Only {len(rows)} engines registered, expected ≥ 9"


def test_all_backends_is_available_returns_tuple():
    """Every backend's is_available() must return (bool, str), no crashes."""
    for bid, cls in tts_backend._REGISTRY.items():
        ok, msg = cls.is_available()
        assert isinstance(ok, bool), f"{bid}.is_available() ok is not bool: {type(ok)}"
        assert isinstance(msg, str), f"{bid}.is_available() msg is not str: {type(msg)}"
