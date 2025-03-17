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

    # # Get query parameters from the connection request
    # connection_params = dict(websocket.scope.get('query_string', b'').decode().split('&'))
    # connection_params = {k: v for k, v in (param.split('=') if '=' in param else (param, '') for param in connection_params if param)}

    # # Log the connection parameters
    # logger.info(f"WebSocket connected with parameters: {connection_params}")

    # # Send acknowledgment with the received parameters
    # await websocket.send_json({
    #     "status": "connected",
    #     "message": "Connection established",
    #     "params_received": connection_params
    # })

    # name = req.get("name", [])
    # name_uuid_pairs, message = foundry_con.get_valid_uuids(name)

    # for name, uuid in name_uuid_pairs.items():
    #     pass

    try:
        # Functions to execute in given order
        functions = {
            # PLACEHOLDER
            "Download": download,
            "Unzip": unzip,
            "Zip": zip,
            "Delete Unzipped": delete_unzipped,
            "Delete Zipped": delete_zipped,
            "Delete": delete,
            "List": list,
            "Info": info
        }
        func_names = list(functions.keys())
        func_amount = len(functions.keys())

        # Iterate through functions
        is_success = True
        progress = 0  # count of successfully executes functions

        while is_success and progress < func_amount:
            func_name = func_names[progress]
            func = functions[func_name]

            message, is_success = await func() if asyncio.iscoroutinefunction(func) else await asyncio.to_thread(func())
            progress += is_success  # only increase if the function was successful

            await websocket.send_json({
                "type": "info",
                "success": is_success,
                "progress": f"{progress}/{func_amount}",
                "function": func_name,
                "message": message
            })

            # Catch cancellation
            req = await websocket.receive_json()
            message, is_success = await check_cancellation(req)

        final_message = "SUCCESS | All functions were executed successfully." if is_success == True else message

        # Send final overview message
        await websocket.send_json({
            "type": "final",
            "success": is_success,
            "progress": f"{progress}/{func_amount}",
            "message": final_message
        })
            
    except WebSocketDisconnect:
        print("Client disconnected")

    except Exception as e:
        # Handle exceptions with a graceful error message to the client
        progress = progress if progress else "-"
        func_acount = func_acount if func_amount else "-"

        await websocket.send_json({
            "type": "final",
            "success": False,
            "progress": f"{progress}/{func_amount}",
            "message": str(f"ERROR | {e}")
        })
        await websocket.close(code=1008)  # Policy violation code

    return {"test": "test"}


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

async def list(req: dict) -> Any:
    """ Returns a list of all available datasets and their versions """
    return {"message": "list endpoint not implemented yet"}

async def info(req: dict) -> Any:
    """ Returns information about one or multiple datasets """
    return {"message": "info endpoint not implemented yet"}

# - - - Utility

async def check_cancellation(req: dict) -> tuple[str, bool]:
    """ Check if the request contains a cancellation signal """
    if req.get("cancel", False) is True:
        return "CANCELED | The process was canceled by the user.", False
    return "", True