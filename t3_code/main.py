from fastapi import FastAPI


app = FastAPI(
    title="Foundry DevTools Container",
    description="API for providing Foundry Datasets",
    root_path="/fdtc-api",
    version="1.0.0"
)


# Include routers
from t3_code.router.router_dataset import router as database_router

for r in [database_router]:
    app.include_router(r)


# Online Status / Health Check
@app.get("/")
async def root():
    return {
        "online": True,
        "message": "Foundry DevTools Container API is available!",
    }


if __name__ == "__main__":
    # Run uvicorn using the import string so reload/workers work correctly.
    import uvicorn
    uvicorn.run("t3_code.main:app", host="0.0.0.0", port=8000, reload=True, reload_dirs=["/app/t3_code"], timeout_graceful_shutdown=0, timeout_keep_alive=7200, ws_ping_interval=3600, ws_ping_timeout=7200)
