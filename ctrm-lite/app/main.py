from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .config import settings
from .db import Database
from .errors import DomainError
from .routers import analytics, reference, trades


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.db = Database(settings.database_url)
    app.state.db.open()
    yield
    app.state.db.close()


app = FastAPI(title="CTRM-lite", version="1.0.0", lifespan=lifespan)


@app.exception_handler(DomainError)
async def domain_error_handler(_: Request, exc: DomainError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}


app.include_router(reference.router)
app.include_router(trades.router)
app.include_router(analytics.router)
