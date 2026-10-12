from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import models  # noqa: F401  (register tables)
from .database import Base, engine
from .routers import jobs

FRONTEND = Path(__file__).resolve().parent.parent / "frontend"


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="Resume Screening System", version="1.0.0", lifespan=lifespan)
app.include_router(jobs.router)
app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="frontend")
