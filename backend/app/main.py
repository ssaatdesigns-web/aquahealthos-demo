import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import engine, Base, SessionLocal
from .models import Pond
from .routes import router

app = FastAPI(title="AquaHealthOS", version="1.0.0")

def _parse_origins(raw: str) -> list[str]:
    if not raw:
        return ["*"]
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    return parts or ["*"]

origins = _parse_origins(os.getenv("CORS_ORIGINS", ""))

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)

    # Seed ponds if empty
    db = SessionLocal()
    try:
        if db.query(Pond).count() == 0:
            db.add_all([
                Pond(name="Pond A", species="fish"),
                Pond(name="Pond B", species="shrimp"),
            ])
            db.commit()
    finally:
        db.close()

@app.get("/healthz")
def healthz():
    return {"ok": True}

app.include_router(router)
