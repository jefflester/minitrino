from __future__ import annotations

import asyncio
import csv
import io
import os
import sys
import time
from collections import defaultdict
from functools import wraps
from pathlib import Path
from sys import platform

import aiofiles
import aiohttp
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from minitrino.core.cluster.cluster import Cluster
    from minitrino.core.context import MinitrinoContext

# Decorator for CLI commands to enable telemetry
def telemetrize(func):

        """
        Decorator to run the orchestrate_telemetry

        This function wraps the ClusterOperations method and ensure the telemetry logic runs only once the full MinitrinoContext is ready
        """
        @wraps(func)
        async def wrapper(self, *args, **kwargs):

            #Access the global initialized telemetry object
        

           
            # Execute the original command first

            result = func(self, *args, **kwargs)

            #Check if the result is an awaitable 
            if asyncio.iscoroutine(result):
                result = await result

            #orchestrate_telmetry is async, so we'll await it
            # Use self to call it
            if hasattr(self, 'telmetry') and isinstance(self.telemetry, MinitrinoTelemetry):
                await self.telemetry.orchestrate_telemetry()
            else:
                print("Telemetyr instance not found on CLusterOperations instance.")

            #Return Original Result
            return result
        return wrapper



class MinitrinoTelemetry:
    def __init__(self, ctx: MinitrinoContext):
        self._ctx = ctx

        self.enabled = self._is_enabled()
        self.endpoint = os.getenv("MINITRINO_TELMETRY_ENDPOINT","http://localhost:5432")

    def _is_enabled(self) -> bool:
        return self._ctx.env.get("MINITRINO_TELEMETRY", "true") == "true"
    
    def create_payload(self, command, os_name, os_version, python_version):
        """Create a telemetry payload."""
         
        payload = defaultdict(lambda: defaultdict(dict))
        payload["command"] =  command
        #payload["module"] = module
        #payload["version"] =  version
        payload["metadata"]["os_name"] = os_name
        payload["metadata"]["os_version"] =  os_version
        payload["metadata"]["python_version"] =  python_version
        payload["metadata"]["timestamp"] = time.time()
        
        return payload
    
    async def jsonDecoder(self, response: aiohttp.ClientResponse) -> dict:
        """
        Gracefully handles non-JSON response to prevent crashes 
        """
        try:
            return await response.json()
        except aiohttp.ContentTypeError:
            self._ctx.logger.log("Received a non-JSON response from the server")
            return {"message": await response.txt()}
        except Exception as e:
            self._ctx.logger.log(f"Failed to decode JSON response: {e}")
            return {"error": "Failed to decode JSON response"}


    async def async_helper(self, url, verb="get", data=None, files=None, retries: int = 5, delay: int = 2) -> tuple:

        for retry in range(retries):
            try:
                async with aiohttp.ClientSession() as session:
                    match verb:
                        case "get":
                            response =  await session.get(url)
                                
                        case "post":
                            response = await session.post(url, data=files)
                                
                        case "put":
                            response = await session.put(url) 
                              
                        case "patch":
                            response = await session.patch(url, json=data) 
                               
                        case "delete":
                            response = await session.delete(url, json=data)
                        case _:
                                raise ValueError(f"Unsupported HTTP verb: {verb}")
                saferesponse = await self.jsonDecoder(response)
                return response.status, saferesponse
            except aiohttp.ClientError as e:
                self._ctx.logger.log(f"Request failed with aiohttp.ClientError: {e}. Retrying in {delay**retry}s")
                await asyncio.sleep(delay ** retry)
        return 500, {"error": "Could not send request"}


    
    async def orchestrate_telemetry(self) -> None:
        """Send telemetry data if enabled."""
       
        # Example: send to a server or log it
        # requests.post("https://telemetry.server/collect", json=payload)

        # pull out the command name from click
        # pull out command options
        # if provision command and moduels are present, grab the modules

        # if moduels are found, check fif they are the standard library
        # if it's custom, replace module name with custom

        command = self._ctx.command.name
        #command_options = self.ctx.paramas
     
        # --- Get System/App Details ---

        #version = self.get_app_version()
        os_name = platform.system()
        os_version = platform.release()
        python_version = sys.version.split('\n')[0]
       

       # --- Get Modules --- #  
            
        payload = self.create_payload(command, os_name, os_version, python_version)
     
       
        try:

            await self.write_record_to_file(payload)

            status, response = await self.batch_to_db()

        except Exception as e:
            self._ctx.logger.log(f"this is the error {e}")

        
        if status == 200:
            self._ctx.logger.log("Telemetry data sent successfully.")
            return True, response
        else:
            self._ctx.logger.log(f"Telemetry payload not send due to network error. status: {status}, response: {response}")
            return False, response
    


    
        # Pull out the command name from Click
        # Pull out command options
        # If provision command and modules are present, grab the modules
        
        # if modules are found, check if they are the STANDARD library (tbd on reference)
        # if it's custom, replace module name with <custom>

    async def write_record_to_file(self,payload: dict):
        ctx: MinitrinoContext = MinitrinoContext()
        ctx.minitrino_user_dir # ~/.minitrino

        file_path = self.get_telemetry_filepath()

        fieldnames = list(payload.keys())

        file_exists = os.path.exists(file_path)
        mode = 'a' if file_exists else 'w'

        try:

            async with aiofiles.open(file_path, mode=mode, newline='', encoding='utf-8') as csvfile:

                csv_writer = csv.DictWriter(csvfile, fieldnames=payload.keys())

                if not file_exists:
                    
                    io_file = io.StringIO()
                    csv_writer = csv.DictWriter(io_file, fieldnames=fieldnames)
                    csv_writer.writeheader()
                    await csvfile.write(io_file.getvalue())
                
                #append data here
                io_file = io.StringIO()

                csv_writer = csv.DictWriter(io_file, fieldnames=fieldnames)

                csv_writer.writerow(payload)

                await csvfile.write(io_file.getvalue())

        
        except Exception as e:
            self._ctx.logger.log(f"Failed to write record to file: {e}")

        
        # if ~/.minitrino/telemetry/telemetry.csv exists, append to it
        # else create it

    

    def get_telemetry_filepath() -> Path:
        """
        Returns the full filepath for the telemetry log.

        This function creates a hidden directory for the application telemetry data if it dosn't already exist
        """

        app_name = "minitrino"
        filename = "telemetry.csv"


        home_dir = Path.home()

        app_dir = home_dir / f".{app_name}"

        app_dir.mkdir(parents=True, exist_ok=True)

        return app_dir / filename
    
    async def batch_to_db(self, file_path):
        ctx: MinitrinoContext = MinitrinoContext()
        ctx.minitrino_user_dir

        file_exists = os.path.exists(file_path)
        mode = 'a' if file_exists else 'w'

        
        try:
            with open(file_path, mode=mode, newline='', encoding = 'utf-8') as csvfile:
                reader = csv.reader(csvfile)
                row_count = sum(1 for row in reader)

                if row_count > 7:
                    files_payload = {'telemetry_batch': open(file_path, 'rb')}
                    status, response = await self.async_helper(
                        self.endpoint,
                        verb="post",
                        files=files_payload
                    )
                    return status,response

        except Exception as e:
            self._ctx.logger.log(f"An error occured: {e}")
            



        # Batch it 
        # Clear the file