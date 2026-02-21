from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base
from .routes import router
import os

app = FastAPI()

Base.metadata.create_all(bind=engine)

origins = [
    os.getenv("CORS_ORIGINS", "*")
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
