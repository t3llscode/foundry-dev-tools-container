import os
from fastapi import FastAPI
import uvicorn

app = FastAPI(
    title="Foundry DevTools Container",
    description="API for providing Foundry Datasets",
    root_path="/fdtc-api",
    version="1.0.0"
)

python_env_env = os.getenv("PYTHON_ENV", "production").lower()  # this might be a double-check
PYTHON_ENV = python_env_env if python_env_env in ["development", "production"] else "production"

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
    
    if PYTHON_ENV == "production":
        uvicorn.run("t3_code.main:app", host="0.0.0.0", port=8888, timeout_graceful_shutdown=0, timeout_keep_alive=7200, ws_ping_interval=3600, ws_ping_timeout=7200)
    
    if PYTHON_ENV == "development":
        uvicorn.run("t3_code.main:app", host="0.0.0.0", port=8888, reload=True, reload_dirs=["/app/foundry-dev-tools-container/t3_code"], timeout_graceful_shutdown=0, timeout_keep_alive=7200, ws_ping_interval=3600, ws_ping_timeout=7200)
