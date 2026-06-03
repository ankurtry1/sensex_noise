from __future__ import annotations

from fastapi import FastAPI

from sensex_noise.web.routes_admin import router as admin_router
from sensex_noise.web.routes_kite import router as kite_router


app = FastAPI(title="Sensex Noise Auth Service")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(kite_router)
app.include_router(admin_router)
