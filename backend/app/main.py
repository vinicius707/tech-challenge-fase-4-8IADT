from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse

from app.auth.router import router as auth_router
from app.health import HealthService, get_health_service

app = FastAPI(
    title="Limen API",
    description="API do protótipo acadêmico Limen.",
    version="0.1.0",
)
app.include_router(auth_router)


@app.get(
    "/health",
    summary="Verifica a prontidão da API e suas dependências",
    responses={503: {"description": "Uma ou mais dependências estão indisponíveis"}},
)
def health(
    service: Annotated[HealthService, Depends(get_health_service)],
) -> JSONResponse:
    report = service.check()
    return JSONResponse(status_code=report.status_code, content=report.as_dict())
