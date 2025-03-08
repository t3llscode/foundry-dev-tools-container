from typing import Dict, List, Any, Optional, Union
import polars as pl
import logging

logger = logging.getLogger(__name__)

# - - - High Priority - - -

async def versions(req: dict) -> Any:
    """ Returns all available versions of a dataset """
    pass

async def download(req: dict) -> Any:
    """ Trigger the download of a dataset from the Foundry """
    pass

async def unzip(req: dict) -> Any:
    """ Trigger unzip of one or multiple datasets """
    pass

async def zip(req: dict) -> Any:
    """ Trigger zip of one or multiple datasets """
    pass

async def delete_unzipped(req: dict) -> Any:
    """ Trigger deletion of one or multiple unzipped dataset files """
    pass

# - - - Less Priority - - -

async def delete_zipped(req: dict) -> Any:
    """ Trigger deletion of one or multiple zipped dataset files """
    pass

async def delete(req: dict) -> Any:
    """ Trigger deletion of dataset (both zipped and unzipped files) """
    pass

async def list(req: dict) -> Any:
    """ Returns a list of all available datasets and their versions """
    pass

async def info(req: dict) -> Any:
    """ Returns information about one or multiple datasets """
    pass