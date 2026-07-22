#!/usr/bin/env python3
"""Gera fixtures sintéticas de vídeo (AVI RGB24) — reprodutível, sem download.

Clips mínimos para TDD/demo da modalidade `video` (Épico 6 / E6.1).
Fontes públicas de referência (3DYoga90, stock CC) ficam documentadas no
README; brutos grandes não entram no Git nem no CI.
"""

from __future__ import annotations

import json
import struct
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = REPO_ROOT / "data" / "fixtures" / "video"

CALIBRATION_VERSION = "2026-07-21.1"
SEED = 20260721
WIDTH = 64
HEIGHT = 48
FRAMES = 12
FPS = 4


def _u16(value: int) -> bytes:
    return struct.pack("<H", value)


def _u32(value: int) -> bytes:
    return struct.pack("<I", value)


def _chunk(tag: bytes, payload: bytes) -> bytes:
    # Chunks AVI alinhados em palavra (pad 0 se tamanho ímpar).
    pad = b"\x00" if len(payload) % 2 else b""
    return tag + _u32(len(payload)) + payload + pad


def _list(list_type: bytes, payload: bytes) -> bytes:
    return b"LIST" + _u32(len(list_type) + len(payload)) + list_type + payload


def _frame_rgb(width: int, height: int, paint) -> bytes:
    """BGR bottom-up (padrão DIB) sem padding — width*3 já alinhado (64*3=192)."""
    rows: list[bytes] = []
    for y in range(height - 1, -1, -1):
        row = bytearray()
        for x in range(width):
            b, g, r = paint(x, y)
            row.extend((b, g, r))
        rows.append(bytes(row))
    return b"".join(rows)


def _physio_paint(frame_idx: int):
    """Silhueta simples se movendo — proxy de Análise Postural (sem PHI)."""

    cx = 20 + frame_idx * 2

    def paint(x: int, y: int) -> tuple[int, int, int]:
        # Fundo azul-acinzentado.
        bg = (90, 70, 40)
        # "Tronco" + "cabeça" + "braço" articulado.
        if abs(x - cx) <= 4 and 18 <= y <= 36:
            return (40, 40, 200)
        if (x - cx) ** 2 + (y - 14) ** 2 <= 16:
            return (40, 40, 200)
        arm_y = 22 + (frame_idx % 3)
        if abs(y - arm_y) <= 1 and cx <= x <= cx + 12:
            return (30, 30, 180)
        return bg

    return paint


def _surgery_paint(frame_idx: int):
    """Cena sintética teal + figura — proxy de Detecção em Cena (sem claim clínico)."""

    cx = 32 + (1 if frame_idx % 2 == 0 else -1)

    def paint(x: int, y: int) -> tuple[int, int, int]:
        # Fundo "scrub"/teal — não representa sangramento nem anatomia.
        bg = (120, 140, 40)
        if 8 <= x <= 56 and 4 <= y <= 10:
            return (200, 200, 200)  # faixa clara (luz/ambiente)
        if abs(x - cx) <= 6 and 16 <= y <= 40:
            return (50, 50, 50)  # figura genérica (pessoa)
        if 44 <= x <= 58 and 28 <= y <= 40:
            return (180, 120, 60)  # objeto genérico (COCO-like proxy)
        return bg

    return paint


def write_avi(
    path: Path,
    *,
    paint_for_frame,
    width: int = WIDTH,
    height: int = HEIGHT,
    frames: int = FRAMES,
    fps: int = FPS,
) -> None:
    frame_size = width * height * 3
    assert (width * 3) % 2 == 0, "stride deve ser par para AVI sem padding"

    movi_parts: list[bytes] = []
    index_entries: list[bytes] = []
    # Offset relativo ao primeiro byte após 'movi' (padrão idx1).
    offset = 4
    for i in range(frames):
        frame = _frame_rgb(width, height, paint_for_frame(i))
        assert len(frame) == frame_size
        chunk = _chunk(b"00db", frame)
        # idx1: tag, flags (keyframe), offset, size
        index_entries.append(b"00db" + _u32(0x10) + _u32(offset) + _u32(frame_size))
        movi_parts.append(chunk)
        offset += len(chunk)

    movi = _list(b"movi", b"".join(movi_parts))
    idx1 = _chunk(b"idx1", b"".join(index_entries))

    # BITMAPINFOHEADER (40) + RGB
    strf = (
        _u32(40)
        + _u32(width)
        + _u32(height)
        + _u16(1)
        + _u16(24)
        + _u32(0)
        + _u32(frame_size)
        + _u32(0)
        + _u32(0)
        + _u32(0)
        + _u32(0)
    )
    strh = (
        b"vids"
        + b"DIB "
        + _u32(0)
        + _u16(0)
        + _u16(0)
        + _u32(0)
        + _u32(1)  # scale
        + _u32(fps)  # rate → fps = rate/scale
        + _u32(0)
        + _u32(frames)
        + _u32(frame_size)
        + _u32(0xFFFFFFFF)
        + _u32(0)
        + struct.pack("<HH", 0, 0)
        + struct.pack("<HHHH", 0, 0, width, height)
    )
    strl = _list(b"strl", _chunk(b"strh", strh) + _chunk(b"strf", strf))

    microsec = int(1_000_000 / fps)
    max_bytes = frame_size * fps
    avih = (
        _u32(microsec)
        + _u32(max_bytes)
        + _u32(0)
        + _u32(0x10)  # AVIF_HASINDEX
        + _u32(frames)
        + _u32(0)
        + _u32(1)  # streams
        + _u32(frame_size)
        + _u32(width)
        + _u32(height)
        + _u32(0)
        + _u32(0)
        + _u32(0)
        + _u32(0)
    )
    hdrl = _list(b"hdrl", _chunk(b"avih", avih) + strl)

    body = hdrl + movi + idx1
    riff = b"RIFF" + _u32(4 + len(body)) + b"AVI " + body
    path.write_bytes(riff)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    fixtures = (
        {
            "file": "video_physio.avi",
            "scenario": "physio",
            "analysis": "pose",
            "paint": _physio_paint,
            "notes": "Silhueta sintética para Análise Postural (proxy de yoga/fisio).",
        },
        {
            "file": "video_surgery_light.avi",
            "scenario": "surgery_light",
            "analysis": "scene",
            "paint": _surgery_paint,
            "notes": (
                "Cena sintética para Detecção em Cena (proxy stock CC); "
                "sem claim clínico."
            ),
        },
    )

    manifest_fixtures = []
    for item in fixtures:
        path = OUTPUT_DIR / item["file"]
        write_avi(path, paint_for_frame=item["paint"])
        digest = __import__("hashlib").sha256(path.read_bytes()).hexdigest()
        manifest_fixtures.append(
            {
                "file": item["file"],
                "scenario": item["scenario"],
                "analysis": item["analysis"],
                "width": WIDTH,
                "height": HEIGHT,
                "frames": FRAMES,
                "fps": FPS,
                "container": "avi",
                "pixel_format": "bgr24",
                "sha256": digest,
                "notes": item["notes"],
            }
        )

    manifest = {
        "version": CALIBRATION_VERSION,
        "seed": SEED,
        "fixtures": manifest_fixtures,
        "reference_sources": {
            "physio": "https://github.com/seonokkim/3dyoga90",
            "surgery_light": (
                "https://creativecommons.org/publicdomain/zero/1.0/ "
                "(stock CC genérico — URL concreta no README)"
            ),
        },
    }
    (OUTPUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(manifest_fixtures)} video fixtures → {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
