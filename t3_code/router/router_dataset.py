from fastapi import APIRouter, Depends

import t3_code.utility.functions_dataset as ds
from t3_code.utility.foundry_utility import FoundryConnection

router = APIRouter(
    prefix="/dataset",
    tags=["Dataset Endpoints"]
)

def get_foundry_connection():
    return FoundryConnection()

# - - - High Priority - - -

@router.post("/versions")
async def version(req: dict):
    return await ds.version(req)

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
    return await ds.delete_raw(req)

# - - - Less Priority - - -

@router.post("/delete/zip")
async def delete_zip(req: dict):
    return await ds.delete_zip(req)

@router.post("/delete")
async def delete(req: dict):
    return await ds.delete(req)

@router.post("/list")
async def list(req: dict):
    return await ds.list(req)

@router.post("/info")
async def info(req: dict):
    return await ds.info(req)
