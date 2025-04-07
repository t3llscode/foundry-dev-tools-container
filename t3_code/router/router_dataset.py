from fastapi import APIRouter, Depends, WebSocket, WebSocketException, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pathlib import Path
from time import sleep
import asyncio
import aiofiles

import t3_code.utility.functions_dataset as ds
from t3_code.utility.foundry_utility import FoundryConnection

router = APIRouter(
    prefix="/dataset",
    tags=["Dataset Endpoints"]
)

def get_foundry_connection():
    return FoundryConnection()

# - - - Full Sequences - - -

@router.websocket("/test")
async def get(websocket: WebSocket, foundry_con: FoundryConnection = Depends(get_foundry_connection)):
    try:
        await websocket.accept()

        # Send one message per second for 5 seconds
        for i in range(5):
            # Send just the number (1-5)
            await websocket.send_json({"message": f"Message {i+1}/5", "count": i+1})
            if i < 4:  # Don't sleep after the last message
                await asyncio.sleep(1)
        # Only close the websocket if no exception occurred
        await websocket.close()
    except Exception as e:
        print("ERROR HAPPENDED")
        # Don't send error if connection is already closing
        if not websocket.client_state.DISCONNECTED:
            await websocket.send_json({"error": str(e)})
    finally:
        sleep(5)
        print("STATE:", websocket.client_state, flush=True)
        print("FINALLY HAPPENED")


@router.websocket("/get")
async def get(websocket: WebSocket, foundry_con: FoundryConnection = Depends(get_foundry_connection)):
    await ds.get(websocket, foundry_con)

# - - - Download Endpoints - - -

CHUNKSIZE = 32 * 1024 * 1024  # 32MB # Allow to provide this in a config file or something

@router.get("/download/zip/{sha256}")
async def download_zip(sha256: str):
    """Download zipped dataset by SHA256 with streaming"""
    zip_path = Path(f"/app/datasets/zipped/{sha256}.zip")
    
    if not zip_path.exists():
        raise HTTPException(status_code=404, detail="Zipped dataset not found")
    
    async def generate():
        async with aiofiles.open(zip_path, 'rb') as file:
            while chunk := await file.read(CHUNKSIZE):  # chunksize
                yield chunk
    
    return StreamingResponse(
        generate(),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={sha256}.zip"}
    )

@router.get("/download/csv/{sha256}")
async def download_csv(sha256: str):
    """Download unzipped CSV dataset by SHA256 with streaming"""
    csv_path = Path(f"/app/datasets/unzipped/{sha256}.csv")
    
    if not csv_path.exists():
        raise HTTPException(status_code=404, detail="CSV dataset not found")
    
    async def generate():
        async with aiofiles.open(csv_path, 'rb') as file:
            while chunk := await file.read(CHUNKSIZE):  # chunksize
                yield chunk
    
    return StreamingResponse(
        generate(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={sha256}.csv"}
    )

# - - - High Priority - - -

# @router.post("/get")
# async def version(req: dict):
#     return {"REAL TEST": True}

@router.post("/versions")
async def version(req: dict):
    return await ds.versions(req)

@router.post("/download")
async def download(req: dict, foundry_con: FoundryConnection = Depends(get_foundry_connection)):
    return await ds.download(req, foundry_con)

@router.post("/unzip")
async def unzip(req: dict):
    return await ds.unzip(req)

@router.post("/zip")
async def zip(req: dict):
    return await ds.zip(req)

@router.post("/delete/raw")
async def delete_raw(req: dict):
    return await ds.delete_unzipped(req)

# - - - Less Priority - - -

@router.post("/delete/zip")
async def delete_zip(req: dict):
    return await ds.delete_zipped(req)

@router.post("/delete")
async def delete(req: dict):
    return await ds.delete(req)

@router.post("/list")
async def list(req: dict):
    return await ds.list_datasets(req)

@router.post("/info")
async def info(req: dict):
    return await ds.info(req)
