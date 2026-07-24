"""TDD T11.5 — fechamento docs E11 (README, .env.example, índice)."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SPEC = (
    REPO_ROOT
    / "specs"
    / "epic-11-yolo-video-real"
    / "01-ultralytics-mediapipe-evidencia.md"
)
DOCS = REPO_ROOT / "docs" / "README.md"
README = REPO_ROOT / "README.md"
ENV_EXAMPLE = REPO_ROOT / ".env.example"


def test_spec_e11_marked_concluded_with_dod() -> None:
    text = SPEC.read_text(encoding="utf-8")
    assert "Concluída" in text
    dod = text.split("## Critérios de pronto")[-1]
    assert "- [x]" in dod
    assert "- [ ]" not in dod
    assert text.count("- [x]") >= 6


def test_docs_index_marks_e11_concluded() -> None:
    text = DOCS.read_text(encoding="utf-8")
    assert "epic-11-yolo-video-real" in text
    assert "Concluída (E11)" in text or "Concluído (E11)" in text
    for line in text.splitlines():
        if "epic-11-yolo-video-real" in line and "|" in line:
            assert "pendente" not in line.lower()
            break
    else:
        raise AssertionError("linha da spec E11 ausente no índice")


def test_readme_documents_video_real_and_evidencia() -> None:
    text = README.read_text(encoding="utf-8")
    lower = text.lower()
    assert "epic-11-yolo-video-real" in text or "Épico 11" in text
    assert "LIMEN_YOLO_BACKEND" in text
    assert "LIMEN_POSE_BACKEND" in text
    assert "ultralytics" in lower
    assert "mediapipe" in lower
    assert "gerar-evidencia-video" in lower
    assert "data/evidencia/video" in lower or "evidencia/video" in lower
    assert "docker-compose.video-real" in lower


def test_env_example_has_yolo_and_pose_backends() -> None:
    text = ENV_EXAMPLE.read_text(encoding="utf-8")
    assert "LIMEN_YOLO_BACKEND=synthetic" in text
    assert "LIMEN_POSE_BACKEND=synthetic" in text
    assert "ultralytics" in text.lower()
    assert "mediapipe" in text.lower()
