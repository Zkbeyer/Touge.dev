import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routers import auth, garage, inventory, profile, run, settings as settings_router
# !! TEST HELPERS — DELETE BEFORE PRODUCTION !!
from app.routers import test_helpers

_frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")

app = FastAPI(
    title="Touge.Dev",
    description="Gamified coding streak app — Initial D touge racing aesthetic",
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
# !! TEST HELPERS — DELETE BEFORE PRODUCTION !!
if settings.debug:
    app.include_router(test_helpers.router)


app.mount("/static", StaticFiles(directory=_frontend_dir), name="static")


@app.get("/")
async def serve_index():
    return FileResponse(os.path.join(_frontend_dir, "index.html"))


@app.get("/health")
async def health():
    return {"status": "ok"}
