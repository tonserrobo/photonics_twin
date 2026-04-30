from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

def create_app() -> FastAPI:
    app = FastAPI(title="Photonics Twin", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/healthz")
    def healthz():
        return {"status": "ok"}

    from photonics_twin_app.routers import simulate
    app.include_router(simulate.router)

    from photonics_twin_app.routers import mock_slurm
    app.include_router(mock_slurm.router)

    from photonics_twin_app.routers import ws
    app.include_router(ws.router)

    return app

app = create_app()
