"""Secrets & .gitignore setup (tasks.md #2)."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


def _run_django_setup(secret_key_value):
    """Import settings / run django.setup() in a subprocess with a controlled
    DJANGO_SECRET_KEY. Passing an explicit value (even "") beats the .env
    autoloader, which uses os.environ.setdefault."""
    env = {
        "PATH": os.environ.get("PATH", ""),
        "DJANGO_SETTINGS_MODULE": "config.settings",
    }
    if secret_key_value is not None:
        env["DJANGO_SECRET_KEY"] = secret_key_value
    return subprocess.run(
        [sys.executable, "-c", "import django; django.setup()"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )


def test_empty_secret_key_raises_improperly_configured():
    result = _run_django_setup("")

    assert result.returncode != 0
    assert "ImproperlyConfigured" in result.stderr
    assert "DJANGO_SECRET_KEY" in result.stderr


def test_secret_key_from_environment_boots():
    result = _run_django_setup("a-perfectly-usable-secret-key")

    assert result.returncode == 0, result.stderr


def test_no_secret_key_literal_in_settings():
    source = (REPO_ROOT / "config" / "settings.py").read_text()

    assert "django-insecure-" not in source
    assert "os.environ" in source


def test_env_example_committed_without_a_real_value():
    lines = (REPO_ROOT / ".env.example").read_text().splitlines()

    key_lines = [ln for ln in lines if ln.strip().startswith("DJANGO_SECRET_KEY")]
    assert key_lines == ["DJANGO_SECRET_KEY="]
    assert "get_random_secret_key" in "\n".join(lines)


@pytest.mark.parametrize(
    "pattern",
    [
        "*.sqlite3",
        "*.sqlite3-journal",
        "*.sqlite3-wal",
        "__pycache__/",
        "*.py[cod]",
        ".venv/",
        "venv/",
        ".env",
        ".pytest_cache/",
        ".DS_Store",
    ],
)
def test_gitignore_covers_required_pattern(pattern):
    entries = (REPO_ROOT / ".gitignore").read_text().splitlines()

    assert pattern in entries


def test_env_and_sqlite_are_git_ignored():
    for path in (".env", "db.sqlite3"):
        result = subprocess.run(
            ["git", "check-ignore", path],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"{path} is not git-ignored"


def test_no_pycache_or_sqlite_tracked_by_git():
    tracked = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()

    assert not [p for p in tracked if "__pycache__" in p or p.endswith(".sqlite3")]


def test_env_loader_populates_environ_without_overriding(tmp_path, monkeypatch):
    from config.settings import _load_env_file

    env_file = tmp_path / ".env"
    env_file.write_text(
        '# a comment\n'
        'FROM_ENV_FILE=loaded\n'
        'QUOTED="with spaces"\n'
        'ALREADY_SET=from_file\n'
        '\n'
        'MALFORMED_LINE\n'
    )
    monkeypatch.setenv("ALREADY_SET", "from_real_env")
    monkeypatch.delenv("FROM_ENV_FILE", raising=False)
    monkeypatch.delenv("QUOTED", raising=False)

    _load_env_file(env_file)

    assert os.environ["FROM_ENV_FILE"] == "loaded"
    assert os.environ["QUOTED"] == "with spaces"
    assert os.environ["ALREADY_SET"] == "from_real_env"
    assert "MALFORMED_LINE" not in os.environ


def test_env_loader_is_a_noop_when_file_missing(tmp_path):
    from config.settings import _load_env_file

    _load_env_file(tmp_path / "does-not-exist")  # must not raise
