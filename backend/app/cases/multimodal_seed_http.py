"""Seed demo multimodal via HTTP (Compose / API) — Épico 8 / T8.5."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.cases.multimodal_seed import (
    DEMO_AUDIO_IDEMPOTENCY_KEY,
    DEMO_CASE_IDEMPOTENCY_KEY,
    DEMO_PRESCRIPTIONS_IDEMPOTENCY_KEY,
    DEMO_VIDEO_IDEMPOTENCY_KEY,
)
from app.smoke.caso_vitais import SmokeTransport, UrllibTransport

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURES = REPO_ROOT / "data" / "fixtures"

_VITALS = FIXTURES / "vitals" / "vitals_medium.csv"
_VIDEO = FIXTURES / "video" / "video_physio.avi"
_AUDIO = FIXTURES / "audio" / "audio_speech.wav"
_RX = FIXTURES / "prescriptions" / "prescriptions_normal.csv"


class MultimodalSeedHttpError(RuntimeError):
    """Falha do seed HTTP (auth, upload ou contrato de modalidades)."""


@dataclass(frozen=True)
class MultimodalSeedHttpConfig:
    base_url: str
    username: str
    password: str
    sensitive_label: str = "Limen Demo Multimodal"
    vitals_path: Path = _VITALS
    video_path: Path = _VIDEO
    audio_path: Path = _AUDIO
    prescriptions_path: Path = _RX


@dataclass(frozen=True)
class MultimodalSeedHttpResult:
    patient_id: str
    case_id: str
    created_case: bool
    modalities: tuple[str, ...]


def seed_multimodal_demo_http(
    config: MultimodalSeedHttpConfig,
    *,
    transport: SmokeTransport | None = None,
) -> MultimodalSeedHttpResult:
    """
    Login → Paciente → Caso vitais (chave demo) → anexa video/audio/prescriptions.

    Idempotente: reexecutar com as mesmas `Idempotency-Key` reutiliza o Caso.
    Não aguarda workers (`done`); só garante Artefatos/modalidades anexados.
    """
    for path in (
        config.vitals_path,
        config.video_path,
        config.audio_path,
        config.prescriptions_path,
    ):
        if not path.is_file():
            raise MultimodalSeedHttpError(f"Fixture ausente: {path}")

    client: SmokeTransport = transport or UrllibTransport(base_url=config.base_url)

    status, login = client.request(
        "POST",
        "/auth/login",
        json_body={"username": config.username, "password": config.password},
    )
    if status != 200 or not isinstance(login, dict) or not login.get("access_token"):
        raise MultimodalSeedHttpError(
            f"POST /auth/login falhou: HTTP {status} body={login!r}"
        )
    auth = {"Authorization": f"Bearer {login['access_token']}"}

    status, patient = client.request(
        "POST",
        "/patients",
        headers=auth,
        json_body={"sensitive_label": config.sensitive_label},
    )
    if status not in (200, 201) or not isinstance(patient, dict) or not patient.get("id"):
        raise MultimodalSeedHttpError(
            f"POST /patients falhou: HTTP {status} body={patient!r}"
        )
    # Paciente pode ser descartável no replay: a chave do Caso resolve o existente.
    _ = str(patient["id"])

    status, case_body = client.request(
        "POST",
        f"/patients/{patient['id']}/cases",
        headers={**auth, "Idempotency-Key": DEMO_CASE_IDEMPOTENCY_KEY},
        multipart_file=(
            config.vitals_path.name,
            config.vitals_path.read_bytes(),
            "text/csv",
        ),
    )
    if status not in (200, 201) or not isinstance(case_body, dict) or not case_body.get(
        "id"
    ):
        raise MultimodalSeedHttpError(
            f"POST .../cases falhou: HTTP {status} body={case_body!r}"
        )
    case_id = str(case_body["id"])
    patient_id = str(case_body.get("patient_id") or patient["id"])
    created_case = status == 201

    attachments: list[tuple[str, str, Path, str]] = [
        (
            "video",
            DEMO_VIDEO_IDEMPOTENCY_KEY,
            config.video_path,
            "video/x-msvideo",
        ),
        (
            "audio",
            DEMO_AUDIO_IDEMPOTENCY_KEY,
            config.audio_path,
            "audio/wav",
        ),
        (
            "prescriptions",
            DEMO_PRESCRIPTIONS_IDEMPOTENCY_KEY,
            config.prescriptions_path,
            "text/csv",
        ),
    ]
    for modality, key, path, content_type in attachments:
        status, body = client.request(
            "POST",
            f"/cases/{case_id}/modalities/{modality}",
            headers={**auth, "Idempotency-Key": key},
            multipart_file=(path.name, path.read_bytes(), content_type),
        )
        if status not in (200, 201) or not isinstance(body, dict):
            raise MultimodalSeedHttpError(
                f"POST modalities/{modality} falhou: HTTP {status} body={body!r}"
            )

    status, detail = client.request("GET", f"/cases/{case_id}", headers=auth)
    if status != 200 or not isinstance(detail, dict):
        raise MultimodalSeedHttpError(
            f"GET /cases/{case_id} falhou: HTTP {status} body={detail!r}"
        )
    modalities = tuple(
        sorted(
            {
                str(m.get("modality"))
                for m in (detail.get("modalities") or [])
                if isinstance(m, dict) and m.get("modality")
            }
        )
    )
    expected = ("audio", "prescriptions", "video", "vitals")
    if modalities != expected:
        raise MultimodalSeedHttpError(
            f"Modalidades inesperadas no Caso {case_id}: {modalities!r}"
        )

    return MultimodalSeedHttpResult(
        patient_id=patient_id,
        case_id=case_id,
        created_case=created_case,
        modalities=modalities,
    )
