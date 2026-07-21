from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.auth.deps import AccessTokenClaims, get_current_access_claims
from app.auth.schemas import LoginRequest, LoginResponse, LogoutRequest, RefreshRequest
from app.auth.service import AuthService, get_auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Autentica um Operador e emite tokens",
    responses={401: {"description": "Credenciais inválidas"}},
)
def login(
    payload: LoginRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> LoginResponse:
    result = service.login(username=payload.username, password=payload.password)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas",
        )
    return result


@router.post(
    "/refresh",
    response_model=LoginResponse,
    summary="Renova access e refresh tokens",
    responses={401: {"description": "Refresh token inválido"}},
)
def refresh(
    payload: RefreshRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> LoginResponse:
    result = service.refresh(refresh_token=payload.refresh_token)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token inválido",
        )
    return result


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Encerra a sessão e invalida o access token",
    responses={401: {"description": "Access token ausente ou inválido"}},
)
def logout(
    claims: Annotated[AccessTokenClaims, Depends(get_current_access_claims)],
    service: Annotated[AuthService, Depends(get_auth_service)],
    payload: LogoutRequest | None = None,
) -> Response:
    body = payload or LogoutRequest()
    service.logout(
        jti=claims.jti,
        exp=claims.exp,
        operator_id=claims.sub,
        refresh_token=body.refresh_token,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
