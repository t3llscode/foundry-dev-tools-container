from typing import Dict, List, Any, Optional, Union
from fastapi import WebSocket, WebSocketDisconnect
import asyncio

import polars as pl
import logging

from t3_code.utility.foundry_utility import FoundryConnection

logger = logging.getLogger(__name__)

# - - - Full Sequences - - -

async def get(websocket: WebSocket, foundry_con: FoundryConnection) -> Any:
    """ Get a dataset from the Foundry, using Websocket for continous updates """

    await websocket.accept()

    try:
        initial_req = await websocket.receive_json()
        names = initial_req.get("names", [])

        name_uuid_pairs, message = foundry_con.get_valid_uuids(names)
        
        if not name_uuid_pairs:  # No valid UUIDs
            await send_message(websocket, "error", False, "", f"ERROR | {message}")
            return

        # Send acknowledgment with validated datasets
        await send_message(websocket, "update", True, "Connection established, starting operation...", add={"datasets": list(name_uuid_pairs.keys())})

        is_success = True
        progress = 0  # count of successfully executed functions

        # Check for initial cancellation (non-blocking) (implement later)
        # message, is_success = await check_cancellation_non_blocking(websocket)

        # Functions to execute in given order
        functions = {
            # PLACEHOLDER
            "Download": download,
            "Unzip": unzip,
            "Zip": zip,
            "Delete Unzipped": delete_unzipped,
            "Delete Zipped": delete_zipped,
            "Delete": delete,
            "List": list_datasets,  # Renamed to avoid shadowing built-in list()
            "Info": info
        }

        func_names = list(functions.keys())
        func_amount = len(functions.keys())

        # Iterate through functions
        while is_success and progress < func_amount:
            func_name = func_names[progress]
            func = functions[func_name]

            message, is_success = (f"Dataset was {func_name.lower()}", True)
            # message, is_success = await func() if asyncio.iscoroutinefunction(func) else await asyncio.to_thread(func())
            progress += is_success  # only increase if the function was successful

            await send_message(websocket, "info", is_success, f"{progress}/{func_amount}", f"{func_name}: {message}")

            # Check for cancellation (non-blocking) (implement later)
            # message, is_success = await check_cancellation_non_blocking(websocket)

        final_message = "SUCCESS | All functions were executed successfully." if is_success == True else message

        # Send final overview message
        await send_message(websocket, "final", is_success, f"{progress}/{func_amount}", final_message)
            
    except WebSocketDisconnect:
        print("Client disconnected")

    except Exception as e:
        # Handle exceptions with a graceful error message to the client
        progress = progress if 'progress' in locals() else "-"
        func_amount = func_amount if 'func_amount' in locals() else "-"

        await send_message(websocket, "final", False, f"{progress}/{func_amount}", f"ERROR | {e}")
        await websocket.close(code=1008)  # Policy violation code


# - - - High Priority - - -

async def versions(req: dict) -> Any:
    """ Returns all available versions of a dataset """
    return {"message": "versions endpoint not implemented yet"}

async def download(req: dict, foundry_connection: FoundryConnection) -> Any:
    """ Trigger the download of a dataset from the Foundry """
    return {"message": "download endpoint not implemented yet"}

async def unzip(req: dict) -> Any:
    """ Trigger unzip of one or multiple datasets """
    return {"message": "unzip endpoint not implemented yet"}

async def zip(req: dict) -> Any:
    """ Trigger zip of one or multiple datasets """
    return {"message": "zip endpoint not implemented yet"}

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

# - - - Utility

async def send_message(websocket: WebSocket, type: str, is_success: bool, message: str, progress: str = None, add: dict = None) -> None:
    """ Send a message to the WebSocket client """
    await websocket.send_json({
        "type": type,
        "success": is_success,
        "message": message,
        **({"progress": progress} if progress is not None else {}),
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