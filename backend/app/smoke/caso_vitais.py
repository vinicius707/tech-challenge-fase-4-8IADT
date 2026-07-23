"""Smoke HTTP: Caso sintético só com vitais até status=done (Épico 8 / T8.1)."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol
from uuid import uuid4


class SmokeCasoVitaisError(RuntimeError):
    """Falha do smoke (health, auth, criação ou timeout/failed)."""


@dataclass(frozen=True)
class SmokeCasoVitaisConfig:
    base_url: str
    username: str
    password: str
    vitals_csv_path: Path
    idempotency_key: str = "smoke-caso-vitais"
    poll_timeout_seconds: float = 120.0
    poll_interval_seconds: float = 1.0
    sensitive_label: str = "Smoke Caso Vitais"


@dataclass(frozen=True)
class SmokeCasoVitaisResult:
    case_id: str
    patient_id: str
    status: str


class SmokeTransport(Protocol):
    def request(
        self,
        method: str,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        json_body: dict[str, Any] | None = None,
        multipart_file: tuple[str, bytes, str] | None = None,
    ) -> tuple[int, Any]:
        """Retorna (status_code, body_json_ou_texto)."""


@dataclass
class UrllibTransport:
    """Transport HTTP real via urllib (Compose / API local)."""

    base_url: str
    timeout_seconds: float = 30.0

    def request(
        self,
        method: str,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        json_body: dict[str, Any] | None = None,
        multipart_file: tuple[str, bytes, str] | None = None,
    ) -> tuple[int, Any]:
        url = self.base_url.rstrip("/") + path
        hdrs = dict(headers or {})
        data: bytes | None = None
        if multipart_file is not None:
            filename, content, content_type = multipart_file
            boundary = f"----limen{uuid4().hex}"
            body = (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="file"; '
                f'filename="{filename}"\r\n'
                f"Content-Type: {content_type}\r\n\r\n"
            ).encode() + content + f"\r\n--{boundary}--\r\n".encode()
            data = body
            hdrs["Content-Type"] = f"multipart/form-data; boundary={boundary}"
        elif json_body is not None:
            data = json.dumps(json_body).encode()
            hdrs.setdefault("Content-Type", "application/json")
        req = urllib.request.Request(url, data=data, headers=hdrs, method=method.upper())
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                raw = resp.read()
                status = getattr(resp, "status", 200)
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            status = exc.code
        if not raw:
            return status, None
        try:
            return status, json.loads(raw.decode())
        except (json.JSONDecodeError, UnicodeDecodeError):
            return status, raw.decode(errors="replace")


def run_smoke_caso_vitais(
    config: SmokeCasoVitaisConfig,
    *,
    transport: SmokeTransport | None = None,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> SmokeCasoVitaisResult:
    """
    Contrato (spec E8.1):

    1. GET /health
    2. POST /auth/login
    3. POST /patients
    4. POST /patients/{id}/cases (CSV vitais + Idempotency-Key)
    5. Poll GET /cases/{id} até done (ou erro com case_id + status)
    """
    if not config.vitals_csv_path.is_file():
        raise SmokeCasoVitaisError(
            f"Fixture de vitais ausente: {config.vitals_csv_path}"
        )

    client: SmokeTransport = transport or UrllibTransport(base_url=config.base_url)

    status, health = client.request("GET", "/health")
    expected_health = {
        "status": "ok",
        "checks": {"postgres": "ok", "redis": "ok", "minio": "ok"},
    }
    if status != 200 or health != expected_health:
        raise SmokeCasoVitaisError(
            f"GET /health inválido: HTTP {status} body={health!r}"
        )

    status, login = client.request(
        "POST",
        "/auth/login",
        json_body={"username": config.username, "password": config.password},
    )
    if status != 200 or not isinstance(login, dict) or not login.get("access_token"):
        raise SmokeCasoVitaisError(
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
        raise SmokeCasoVitaisError(
            f"POST /patients falhou: HTTP {status} body={patient!r}"
        )
    patient_id = str(patient["id"])

    csv_bytes = config.vitals_csv_path.read_bytes()
    status, case_body = client.request(
        "POST",
        f"/patients/{patient_id}/cases",
        headers={**auth, "Idempotency-Key": config.idempotency_key},
        multipart_file=(
            config.vitals_csv_path.name,
            csv_bytes,
            "text/csv",
        ),
    )
    if status not in (200, 201) or not isinstance(case_body, dict) or not case_body.get(
        "id"
    ):
        raise SmokeCasoVitaisError(
            f"POST /patients/.../cases falhou: HTTP {status} body={case_body!r}"
        )
    case_id = str(case_body["id"])
    last_status = str(case_body.get("status") or "unknown")

    deadline = clock() + config.poll_timeout_seconds
    while True:
        status, detail = client.request(
            "GET",
            f"/cases/{case_id}",
            headers=auth,
        )
        if status != 200 or not isinstance(detail, dict):
            raise SmokeCasoVitaisError(
                f"GET /cases/{case_id} falhou: HTTP {status} body={detail!r}"
            )
        last_status = str(detail.get("status") or "unknown")
        if last_status == "done":
            modalities = detail.get("modalities") or []
            vitals_ok = any(
                isinstance(m, dict)
                and m.get("modality") == "vitals"
                and m.get("status") == "done"
                for m in modalities
            )
            if modalities and not vitals_ok:
                raise SmokeCasoVitaisError(
                    f"Caso {case_id} done sem modalidade vitals done: {modalities!r}"
                )
            return SmokeCasoVitaisResult(
                case_id=case_id,
                patient_id=patient_id,
                status="done",
            )
        if last_status == "failed":
            raise SmokeCasoVitaisError(
                f"Caso {case_id} falhou (status={last_status})"
            )
        if clock() >= deadline:
            raise SmokeCasoVitaisError(
                f"Timeout aguardando Caso {case_id} (último status={last_status})"
            )
        sleep(config.poll_interval_seconds)
