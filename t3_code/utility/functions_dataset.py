from typing import Dict, List, Any, Optional, Union
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime
from pathlib import Path
import polars as pl
import traceback
import asyncio
import zipfile
import shutil
import hashlib
import logging
import json

from t3_code.utility.foundry_utility import FoundryConnection


logger = logging.getLogger(__name__)

# - - - Full Sequences - - -

async def get(websocket: WebSocket, foundry_con: FoundryConnection) -> Any:
    """ Get a dataset from the Foundry, using Websocket for continous updates """

    await websocket.accept()

    try:
        initial_req = await websocket.receive_json()
        names = initial_req.get("names", [])

        name_rid_pairs, message = foundry_con.get_valid_rids(names)
        
        if not name_rid_pairs:  # No valid RIDs
            await send_message(websocket, "error", False, f"ERROR | {message}")
            return

        # Send acknowledgment with validated datasets
        await send_message(websocket, "update", True, "Connection established, starting operation...", add={"datasets": list(name_rid_pairs.keys())})

        coroutines = []
        for name, rid in name_rid_pairs.items():
            coroutines.append(get_single_dataset(foundry_con, rid, name, "2025-06-01", "2025-06-30"))

        print("GOING TO RUN", flush=True)

        # Run all dataset retrievals concurrently
        results = await asyncio.gather(*coroutines, return_exceptions=True)

        print(results)

        print("RAN THROUGH", flush=True)

        # Send final overview message
        await send_message(websocket, "final", True, "DONE", add={"datasets": results})
            
    except WebSocketDisconnect:
        print("Client disconnected")

    except Exception as e:
        # Handle exceptions with a graceful error message to the client
        progress = progress if 'progress' in locals() else "-"
        func_amount = func_amount if 'func_amount' in locals() else "-"

        traceback.print_exc()

        await send_message(websocket, "final", False, f"ERROR | {e}")
        await websocket.close(code=1008)  # Policy violation code


# - - - - - High Priority - - - - -

# - - - Versions - - -

async def get_versions(rid: str) -> tuple[list[dict], str]:
    """
    Returns a list of dictionaries with the available versions of a dataset.

    Folder / File Structure:
    ```
    RID    | UUID for the Dataset (Foundry ID)
    SHA256 | SHA256 checksum of the zipped dataset, used as the filename for the zipped and unzipped files
    dates  | list of dates on which the dataset was created or a identical dataset was pulled

    datasets
    ├── metadata (RID.json)
    │   ├── 12a3b4c5-d6e7-8f90-1a2b-3c4d5e6f7g8h.json
    │   └── z9y8x7w6-v5u4-3210-z9y8-x7w6v5u4t3s2.json
    ├── zipped (SHA256.zip)
    │   ├── a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2.zip
    │   ├── f7e6d5c4b3a2f7e6d5c4b3a2f7e6d5c4b3a2f7e6d5c4b3a2f7e6d5c4b3a2f7e6.zip
    │   └── c3b2a1f7e6d5c3b2a1f7e6d5c3b2a1f7e6d5c3b2a1f7e6d5c3b2a1f7e6d5c3b2.zip
    └── unzipped (SHA256.csv)
        ├── a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2.csv
        └── c3b2a1f7e6d5c3b2a1f7e6d5c3b2a1f7e6d5c3b2a1f7e6d5c3b2a1f7e6d5c3b2.csv

    12a3b4c5-d6e7-8f90-1a2b-3c4d5e6f7g8h.json (metadata file)
    {
       "name": "<dataset_name>",
       "rid": "<dataset_uuid>",
       "versions": [
           {
               "sha256": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
               "dates": ["YYYY-MM-DD HH:MM:SS"],
               "zipped": True,
               "unzipped": True
           },
           ...
       ]
    }
    ```
    """

    BASE_DIR = Path(f"/app/metadata/{rid}.json")
    
    try:
        async with asyncio.Lock():
            async with open(BASE_DIR, 'r') as file:
                content = await file.read()
            data = json.loads(content)
            versions = data.get("versions", [])
            message = f"Found {len(versions)} versions for dataset '{rid}'."
    except FileNotFoundError:
        versions = []
        message = f"No metadata file found for dataset '{rid}'."
    except json.JSONDecodeError:
        versions = []
        message = f"Invalid JSON format in metadata file for dataset '{rid}'."
    except Exception as e:
        versions = []
        message = f"Error reading metadata: {str(e)}"

    if versions:  # Sort versions descending (newest first) based on the last date in each version's dates list # TODO: check if necessary, as already trying to do this while writing to the file
        versions.sort(key=lambda v: datetime.fromisoformat(v.get("dates", ["1970-01-01 00:00:00"])[-1]), reverse=True)

    return versions, message


async def get_filtered_versions(rid: str, date_start: str, date_end: str = None) -> tuple[list[dict], str]:
    """ Returns the version object for a dataset filtered by date range """

    versions, message = await get_versions(rid)

    if not versions:
        return [], f"No versions for dataset '{rid}'. Internal Message: {message}"

    date_start_dt = datetime.fromisoformat(date_start)
    date_end_dt = datetime.fromisoformat(date_end) if date_end else datetime.now()

    filtered_versions = [  # Filter versions based on the date range
        version for version in versions
        if any(date_start_dt <= datetime.fromisoformat(date) <= date_end_dt for date in version.get("dates", []))
    ]

    if not filtered_versions:
        return [], f"No versions between '{date_start}' and '{date_end}' found for dataset '{rid}'. Internal Message: {message}"

    return filtered_versions, f"Found {len(filtered_versions)} versions for dataset '{rid}' between '{date_start}' and '{date_end}'."


async def get_first_filtered_version(rid: str, date_start: str, date_end: str = None) -> tuple[Optional[dict], str]:
    """ Returns the first version object for a dataset filtered by date range """

    versions, message = await get_filtered_versions(rid, date_start, date_end)

    if not versions:
        return None, message

    return versions[0], message

# - - - Load Datasets - - -

async def load_datasets(sha256: str) -> pl.DataFrame | None:

    unzipped_path = Path(f"/app/datasets/unzipped/{sha256}.csv")

    if unzipped_path.exists():
        try:
            df = pl.read_csv(unzipped_path)
            return df
        except Exception as e:
            return None
    else:
        return None
    
# - - - Unzip Datasets - - -

async def unzip_dataset(sha256: str) -> bool:
    """ 
    Unzips a dataset zip file to a CSV file in the unzipped directory.
    
    Args:
        sha256: The SHA256 hash identifier for the dataset
        
    Returns:
       True if successfully unzipped, False if file doesn't exist or on error

    Process:
        1. Checks if the zip file exists at the expected path
        2. Creates a temporary extraction directory
        3. Extracts all files from the zip archive
        4. Finds the first CSV file in the extracted contents
        5. Moves the CSV to the unzipped directory with the sha256 identifier
        6. Cleans up the temporary directory
    """
    
    zipped_path = Path(f"/app/datasets/zipped/{sha256}.zip")
    unzipped_path = Path(f"/app/datasets/unzipped/{sha256}.csv")
    temp_extract_dir = Path(f"/app/datasets/temp_extract_{sha256}")

    if not zipped_path.exists() or zipped_path.suffix != '.zip':
        return False

    try:
        temp_extract_dir.mkdir(exist_ok=True)
        
        with zipfile.ZipFile(zipped_path, 'r') as zip_ref:
            zip_ref.extractall(temp_extract_dir)
        
        csv_files = list(temp_extract_dir.glob("**/*.csv"))
        
        if not csv_files:
            shutil.rmtree(temp_extract_dir, ignore_errors=True)
            return False
        
        source_csv = csv_files[0]
        unzipped_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source_csv), str(unzipped_path))
        shutil.rmtree(temp_extract_dir, ignore_errors=True)
        
        return True
        
    except Exception as e:
        if temp_extract_dir.exists():
            shutil.rmtree(temp_extract_dir, ignore_errors=True)
        return False
    

async def zip_dataset(sha256: str) -> bool:
    """ 
    Zips a dataset CSV file into a zip file in the zipped directory.
    
    Args:
        sha256: The SHA256 hash identifier for the dataset
    Returns:
        True if successfully zipped, False if file doesn't exist or on error
    Process:
        1. Checks if the CSV file exists at the expected path
        2. Creates a zip file in the zipped directory with the sha256 identifier
        3. Writes the CSV file into the zip archive
    """
    
    unzipped_path = Path(f"/app/datasets/unzipped/{sha256}.csv")
    zipped_path = Path(f"/app/datasets/zipped/{sha256}.zip")

    if not unzipped_path.exists() or unzipped_path.suffix != '.csv':
        return False

    try:
        with zipfile.ZipFile(zipped_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(unzipped_path, arcname=f"{sha256}.csv")
        return True
    
    except Exception as e:
        return False

# - - - Download - - -

async def download_dataset(foundry_con: FoundryConnection, rid: str, name: str) -> bool:
    """ Trigger the download of a dataset from the Foundry """
    
    # Execute the Foundry SQL query asynchronously
    df = await asyncio.to_thread(
        foundry_con.foundry_context.foundry_sql_server.query_foundry_sql,
        f"SELECT * FROM `ri.foundry.main.dataset.{rid}`"  # TODO: make this use the prefix defined in the foundry_datasets.toml file
    )
    
    # CHECKSUM
    utf_data = df.to_json(orient='records').encode('utf-8')
    sha256 = hashlib.sha256(utf_data).hexdigest()
    
    # SAVE
    unzipped_path = Path(f"/app/datasets/unzipped/{sha256}.csv")
    df.to_csv(unzipped_path, index=False, encoding='utf-8')
    
    # ZIP
    is_zipped = await zip_dataset(sha256)
    if not is_zipped:
        return False
    
    # METADATA
    version = {
        "sha256": sha256,
        "dates": [datetime.now().isoformat()],
        "unzipped": True,
        "zipped": True
    }

    is_added = await add_version_to_metadata(name, rid, version)
    if not is_added:
        return False

    return True

# - - - Metadata Maintenance - - -

async def add_metadata(name: str, rid: str, versions: list[dict] = []):

    metadata_path = Path(f"/app/datasets/metadata/{rid}.json")

    if not metadata_path.exists():
        metadata_path.write_text(json.dumps({"name": name, "rid": rid, "versions": versions}, indent=4))
        return True

    return False


async def add_version_to_metadata(name: str, rid: str, version: dict) -> bool:
    """ Add a new version entry to the dataset metadata """

    is_new_created = await add_metadata(name, rid, [version])
    if not is_new_created:
        # If metadata already exists, update it
        metadata_path = Path(f"/app/datasets/metadata/{rid}.json")
        metadata = json.loads(metadata_path.read_text())

        tmp = metadata["versions"]
        tmp.append(version)

        if tmp:  # Sort versions descending (newest first) based on the last date in each version's dates list
            tmp.sort(key=lambda v: datetime.fromisoformat(v.get("dates", ["1970-01-01 00:00:00"])[-1]), reverse=True)

        metadata["versions"] = tmp

        metadata_path.write_text(json.dumps(metadata, indent=4))

    return True

# - - - Delete Datasets - - -

async def delete_unzipped(req: dict) -> Any:
    """ Trigger deletion of one or multiple unzipped dataset files """
    return {"message": "delete_unzipped endpoint not implemented yet"}

# - - - Less Priority - - -

async def delete_zipped(req: dict) -> Any:
    """ Trigger deletion of one or multiple zipped dataset files """
    return {"message": "delete_zipped endpoint not implemented yet"}

async def delete(req: dict) -> Any:
    """ Trigger deletion of dataset (both zipped and unzipped files) """
    return {"message": "delete endpoint not implemented yet"}

async def list_datasets(req: dict) -> Any:
    """ Returns a list of all available datasets and their versions """
    return {"message": "list endpoint not implemented yet"}

async def info(req: dict) -> Any:
    """ Returns information about one or multiple datasets """
    return {"message": "info endpoint not implemented yet"}

# - - - Core Processes - - -

async def get_single_dataset(foundry_con: FoundryConnection, rid: str, name: str, date_start, date_end = None) -> Union[pl.DataFrame, None]:
    """ Get a single dataset by name and uuid from the Foundry """

    version, message = await get_first_filtered_version(rid, date_start, date_end)

    if version:

        sha256 = version.get('sha256', None)
        if not sha256:
            raise ValueError(f"SHA256 not found in version data for dataset {rid}.")
        
        # UNZIP
        if not version.get("unzipped", False):
            is_unzipped = await unzip_dataset(version['sha256'])
            if not is_unzipped:
                raise FileNotFoundError(f"Unzipped file for {rid} with SHA256 {version['sha256']} not found or could not be unzipped.")

    # - NO VERSION FOUND -
    is_downloaded = await download_dataset(foundry_con, rid, name)
    if not is_downloaded:
        raise FileNotFoundError(f"Dataset {rid} could not be downloaded or does not exist.")

    # GET DATASET
    df = await load_datasets(sha256)

    if df is None:
        raise FileNotFoundError(f"Dataset {rid} with SHA256 {sha256} not found.")

    return df

# - - - Utility Functions - - -

async def send_message(websocket: WebSocket, type: str, is_success: bool, message: str, add: dict = None) -> None:
    """ Send a message to the WebSocket client """
    await websocket.send_json({
        "type": type,
        "success": is_success,
        "message": message,
        **(add or {})
    })

# - - - Cancellation - - - (implement later)

# async def check_cancellation_non_blocking(websocket: WebSocket) -> tuple[str, bool]:
#     """ Check if the request contains a cancellation signal without blocking """
#     try:
#         # Use asyncio.wait_for with timeout=0 to make it non-blocking
#         req = await asyncio.wait_for(websocket.receive_json(), timeout=0.001)
#         if req.get("cancel", False) is True:
#             return "CANCELED | The process was canceled by the user.", True
#         return "", False
#     except asyncio.TimeoutError:
#         # No message received, continue processing
#         return "", False
#     except Exception:
#         # Any other error (like connection closed), treat as cancellation
#         return "CANCELED | Connection lost.", True

# async def check_cancellation(websocket: WebSocket) -> tuple[str, bool]:
#     """ Check if the request contains a cancellation signal (blocking version) """
#     try:
#         req = await websocket.receive_json()
#         if req.get("cancel", False) is True:
#             return "CANCELED | The process was canceled by the user.", False
#         return "", True
#     except Exception:
#         return "CANCELED | Connection lost.", False