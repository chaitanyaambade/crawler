from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import router
from app.storage import close_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_db()


app = FastAPI(title="Crawler Experiment", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
