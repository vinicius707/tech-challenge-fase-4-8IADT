from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse

from app.alerts.router import router as alerts_router
from app.auth.router import router as auth_router
from app.auth.seed import seed_operators
from app.auth.service import get_operator_store
from app.cases.router import cases_router, patients_cases_router
from app.failures.router import router as failures_router
from app.health import HealthService, get_health_service
from app.patients.router import router as patients_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    seed_operators(get_operator_store())
    yield


app = FastAPI(
    title="Limen API",
    description="API do protótipo acadêmico Limen.",
    version="0.1.0",
    lifespan=lifespan,
)
app.include_router(auth_router)
app.include_router(patients_router)
app.include_router(patients_cases_router)
app.include_router(cases_router)
app.include_router(alerts_router)
app.include_router(failures_router)


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
