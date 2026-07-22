"""Leitura de frames AVI RGB24 (fixtures sintéticas do Épico 6)."""

from __future__ import annotations

import struct
from dataclasses import dataclass


@dataclass(frozen=True)
class AviFrame:
    index: int
    width: int
    height: int
    # Pixels BGR top-down (convertidos do DIB bottom-up).
    bgr: bytes


def _u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def read_avi_bgr_frames(content: bytes) -> list[AviFrame]:
    """Extrai frames `00db` de AVI DIB/BGR24 gerado por `prepare_video_fixtures`."""
    if content[:4] != b"RIFF" or content[8:12] != b"AVI ":
        raise ValueError("conteúdo não é RIFF/AVI")

    # Localiza LIST movi
    offset = 12
    movi_payload: bytes | None = None
    width = height = 0
    while offset + 8 <= len(content):
        tag = content[offset : offset + 4]
        size = _u32(content, offset + 4)
        payload_start = offset + 8
        payload_end = payload_start + size
        if tag == b"LIST":
            list_type = content[payload_start : payload_start + 4]
            if list_type == b"hdrl":
                # strf BITMAPINFOHEADER: após avih/strl — busca 'strf'
                inner = content[payload_start + 4 : payload_end]
                pos = inner.find(b"strf")
                if pos >= 0:
                    # strf chunk: tag(4) size(4) biSize(4) width(4) height(4)
                    bi = pos + 8
                    width = _u32(inner, bi + 4)
                    height = abs(struct.unpack_from("<i", inner, bi + 8)[0])
            elif list_type == b"movi":
                movi_payload = content[payload_start + 4 : payload_end]
        # chunks alinhados em palavra
        offset = payload_end + (size % 2)
        if tag == b"LIST" and list_type == b"movi":
            break

    if not movi_payload or width <= 0 or height <= 0:
        raise ValueError("AVI sem frames movi/strf válidos")

    frames: list[AviFrame] = []
    pos = 0
    idx = 0
    row_stride = width * 3
    expected = row_stride * height
    while pos + 8 <= len(movi_payload):
        ctag = movi_payload[pos : pos + 4]
        csize = _u32(movi_payload, pos + 4)
        cstart = pos + 8
        cend = cstart + csize
        if ctag == b"00db":
            dib = movi_payload[cstart:cend]
            if len(dib) < expected:
                raise ValueError("frame DIB truncado")
            # DIB é bottom-up → inverter linhas para top-down.
            rows = [
                dib[i : i + row_stride]
                for i in range(0, expected, row_stride)
            ]
            top_down = b"".join(reversed(rows))
            frames.append(
                AviFrame(index=idx, width=width, height=height, bgr=top_down)
            )
            idx += 1
        pos = cend + (csize % 2)

    if not frames:
        raise ValueError("nenhum frame 00db encontrado")
    return frames
