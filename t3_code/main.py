from fastapi import FastAPI

app = FastAPI(
    title="Foundry DevTools Container",
    description="API for providing Foundry Datasets",
    version="1.0.0"
)

# Include routers
from t3_code.router.router_dataset import router as database_router

for r in [database_router]:
    app.include_router(r, flush=True)


@app.get("/")
async def root():
    return {
        "online": True,
        "message": "Foundry DevTools Container API is available!",
    }
