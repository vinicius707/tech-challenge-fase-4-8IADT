"""TDD T8.2 — contrato do workflow: build imagens + publish GHCR só em main."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CI_YML = REPO_ROOT / ".github" / "workflows" / "ci.yml"


@pytest.fixture(scope="module")
def ci_text() -> str:
    assert CI_YML.is_file()
    return CI_YML.read_text(encoding="utf-8")


def test_ci_builds_backend_and_frontend_docker_contexts(ci_text: str) -> None:
    lower = ci_text.lower()
    assert "backend/dockerfile" in lower or "context: ./backend" in lower
    assert "frontend/dockerfile" in lower or "context: ./frontend" in lower
    assert "docker/build-push-action" in lower or "docker build" in lower


def test_ci_publishes_to_ghcr_only_on_main(ci_text: str) -> None:
    assert "ghcr.io" in ci_text.lower()
    assert "docker/login-action" in ci_text.lower()
    # Publish / push somente em main (push na branch main).
    assert "refs/heads/main" in ci_text
    assert "push:" in ci_text.lower() or "push :" in ci_text.lower()
    # Não publicar em todo evento sem condição.
    assert "github.ref" in ci_text
    assert "main" in ci_text


def test_ci_ghcr_tags_include_main_sha_and_latest(ci_text: str) -> None:
    assert "latest" in ci_text
    assert "main-" in ci_text
    assert "github.sha" in ci_text


def test_ci_ghcr_uses_github_token_and_packages_write(ci_text: str) -> None:
    assert "packages: write" in ci_text or "packages:write" in ci_text.replace(
        " ", ""
    )
    assert "GITHUB_TOKEN" in ci_text
    assert "secrets.GITHUB_TOKEN" in ci_text or "${{ secrets.GITHUB_TOKEN }}" in ci_text


def test_ci_image_names_cover_backend_and_frontend(ci_text: str) -> None:
    lower = ci_text.lower()
    assert "limen-backend" in lower or "/backend" in lower
    assert "limen-frontend" in lower or "/frontend" in lower
