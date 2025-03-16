import os
import time
import logging
from urllib.parse import quote
from fastapi import HTTPException

def read_docker_secret(secret_name):
    """ Read Docker Secrets by name from the 'default' path """
    try:
        with open(f'/run/secrets/{secret_name}', 'r') as secret_file:
            return quote(secret_file.read().strip())
    except IOError:
        # Fallback for development environments or when not using Docker secrets
        return quote(os.environ.get(f'SECRET_{secret_name.upper()}', ''))

def force_list(value):
    """ Force a value to be a list if it's not None """
    if value is None:
        return []
    return [value] if not isinstance(value, list) else value


class BodyHandling:

    @staticmethod
    def error_if_undefined(search, search_in, search_in_name = "no name specified"):
        """ Checks if all items of search are in search_in """
        search = BodyHandling.force_list(search)
        missing_fields = [field for field in search if field not in search_in]
        if missing_fields:
            raise HTTPException(status_code=400, detail=f'''Missing required fields '{"', '".join(missing_fields)}' in '{search_in_name}\'''')
        
    @staticmethod
    def get_from(get, get_from, error = True):
        """ Get a value from a dictionary or raise an error """
        if error:
            BodyHandling.error_if_undefined(get, get_from, "")

    @staticmethod
    def force_list(value, type = None, name = "no name specified", error = True,):
        """ Ensure value is a list as long as it is not None, if type is set also check for correct type, throws HTTPException if error is True """
        
        if value and not isinstance(value, list):
            if type is not None and not isinstance(value, type):
                raise HTTPException(status_code=400, detail=f"Parameter '{name}' with value '{value}' must be a {type} or a list of {type}")
            return [value]
        elif value and type:
                for item in value:
                    if not isinstance(item, type):
                        if error:
                            raise HTTPException(status_code=400, detail=f"All elements of parameter '{name}' must be a {type}")
        return value

# # # # #

class Timer:

    def __init__(self, logger=None):
        self.last_time = time.time()
        # Use provided logger or get the root logger
        self.logger = logger or logging.getLogger()
        # Ensure handler is attached if using root logger
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            if self.logger.level == logging.NOTSET:
                self.logger.setLevel(logging.INFO)

    def print(self, message=""):
        """ Print the elapsed time since the last call with an additional message """
        current_time = time.time()
        elapsed_time = current_time - self.last_time
        self.last_time = current_time
        
        if message:
            # Force immediate output through logging
            log_message = f"{message}: {elapsed_time:.3f} seconds"
            self.logger.info(log_message)
            
            # Ensure handlers flush immediately
            for handler in self.logger.handlers:
                handler.flush()

# # # # #