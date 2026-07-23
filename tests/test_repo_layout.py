from __future__ import annotations

from pathlib import Path


REQUIRED = [
    "README.md",
    "install.ps1",
    "install.sh",
    "pyproject.toml",
    "requirements.txt",
    "requirements-dev.txt",
    "src/python/ai_tts/__main__.py",
    "src/python/ai_tts/speak.py",
    "src/python/ai_tts/daemon_server.py",
    "docs/platforms.md",
    "docs/testing.md",
    "docs/DEPRECATED_POWERSHELL.md",
    "scripts/run-tests.sh",
    "scripts/smoke.sh",
    "scripts/smoke.ps1",
    "uninstall.sh",
    "src/python/ai_tts/doctor.py",
    "src/python/ai_tts/voices.py",
    "src/python/ai_tts/uninstall.py",
    "src/python/ai_tts/cli_config.py",
    "src/python/ai_tts/install_ui.py",
    "Dockerfile",
    "docker-compose.test.yml",
    ".github/workflows/test.yml",
]


def test_required_files_exist(repo_root: Path):
    missing = [p for p in REQUIRED if not (repo_root / p).is_file()]
    assert missing == [], f"missing: {missing}"


def test_install_sh_has_shebang(repo_root: Path):
    text = (repo_root / "install.sh").read_text(encoding="utf-8")
    assert text.startswith("#!/")
    assert "python" in text.lower()


def test_python_package_version():
    from ai_tts import __version__

    assert __version__
