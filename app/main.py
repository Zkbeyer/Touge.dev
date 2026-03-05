from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth, garage, inventory, profile, run, settings as settings_router

app = FastAPI(
    title="Mountain Pass Streak",
    description="Gamified coding streak app — retro touge aesthetic",
    version="0.1.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else [settings.app_base_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(settings_router.router)
app.include_router(run.router)
app.include_router(inventory.router)
app.include_router(garage.router)
app.include_router(profile.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
