# Foundry DevTools Container

#### The idea is an 'isolated' container to...

- Run the foundry dev tools
- Download datasets from Foundry
- Keep copies of datasets compressed as zip
- Provide an API to download datasets (via docker network) 
- Integrate upstream improvements from the [EMD Group Foundry Dev Tools](https://github.com/emdgroup/foundry-dev-tools)
- Pair with the [t3llscode/foundry-dev-tools-container-client](https://github.com/t3llscode/foundry-dev-tools-container-client) for convenient remote control via WebSockets

### Technical Details

- Config file for mapping names to dataset RIDs (`foundry_datasets.toml`)
- **WebSocket** for real-time communication and progress updates during dataset operations
- **HTTP streaming endpoints** for downloading dataset files (zip/csv)
- API for dataset management / provisioning
- Docker network for communication with other containers
- Internal port: **8888** (accessible via container name on docker network)

### Related Projects

- **EMD Group Foundry Dev Tools** – upstream tooling, documentation, and changelog live at [github.com/emdgroup/foundry-dev-tools](https://github.com/emdgroup/foundry-dev-tools).
- **Foundry DevTools Container Client** – the [t3llscode/foundry-dev-tools-container-client](https://github.com/t3llscode/foundry-dev-tools-container-client) library can orchestrate this container over WebSockets, providing helper APIs for logging, scheduling refresh windows, and incremental downloads.

### Endpoints

#### WebSocket Endpoints (Real-time Communication)

- `WS /dataset/get` - Full dataset retrieval workflow with live progress updates
- `WS /dataset/test` - Test WebSocket connection

#### HTTP Streaming Downloads

- `GET /dataset/download/zip/{sha256}` - Download zipped dataset by SHA256 checksum
- `GET /dataset/download/csv/{sha256}` - Download CSV dataset by SHA256 checksum

#### REST Endpoints (Dataset Management)

- `POST /dataset/versions` - Returns all available versions of a dataset
- `POST /dataset/download` - Trigger the download of a dataset from the Foundry
- `POST /dataset/unzip` - Trigger unzip of one or multiple datasets
- `POST /dataset/zip` - Trigger zip of one or multiple datasets
- `POST /dataset/delete/raw` - Trigger deletion of one or multiple unzipped dataset files

#### Additional Endpoints (less priority)

- `POST /dataset/delete/zip` - Trigger deletion of one or multiple zipped dataset files
- `POST /dataset/delete` - Trigger deletion of dataset (both zipped and unzipped files)
- `POST /dataset/list` - Returns a list of all available datasets and their versions
- `POST /dataset/info` - Returns information about one or multiple datasets

## Process: Update and Download Dataset (initiated by foreign API)

  1. External API opens a **WebSocket connection** to `/dataset/get`

  2. External API sends a JSON message with dataset names and optional date range:
     ```json
     {"names": ["Dataset Name 1", "Dataset Name 2"], "from_dt": "2025-06-01", "to_dt": "2025-06-30"}
     ```

  3. The container validates the dataset names against the configured RID mappings

  4. For each dataset, the container checks for existing versions within the date range:

     **If a valid version exists:**
       - Unzips the dataset if needed
       - Sends progress updates via WebSocket

     **If no valid version exists:**
       - Downloads the dataset from Foundry (with batch support for large datasets)
       - Computes SHA256 checksum
       - Saves as CSV and creates ZIP archive
       - Updates metadata file
       - Sends progress updates via WebSocket

  5. The container sends a `final` message with the SHA256 of the processed dataset(s)

  6. External API can then download the files via HTTP:
     - `GET /dataset/download/csv/{sha256}` for the CSV file
     - `GET /dataset/download/zip/{sha256}` for the ZIP archive

  7. Continue with the operation of converting the data to the database and so on

# Setup

### Using Docker Compose


<b>Step 1:</b> Create a `.secrets` directory and add a `foundry_dev_tools.toml` file with the following content. This file is passed to the `foundry-dev-tools` as your configuration.

```toml
[credentials]
domain="palantir.company.com"
jwt="eyJhbGciOiJIUzI1NiIs..."
```


<b>Step 2:</b> Also add a `foundry_datasets.toml` file to the `.secrets` directory, which maps names to dataset RIDs. Within the whole container datasets will always be referred to by their names, so this is essential. You only need to map the UUID part of the RID, `ri.foundry.main.dataset.` will automatically be added in front of the UUID.

```toml
"prefix"="ri.foundry.main.dataset."

[datasets]
"Customer Demographics"="12a3b4c5-d6e7-8f90-1a2b-3c4d5e6f7g8f"
"Transaction History"="98f7e6d5-c4b3-2a10-9f8e-7d6c5b4a3210"
"Product Catalog"="a1b2c3d4-e5f6-7890-a1b2-c3d4e5f67890"
"Supplier Inventory"="a9b8c7d6-e5f4-3210-f9e8-a7b6c5d4e3f2"
```

<b>Step 3:</b> Add the following parts to your `docker-compose.yml`:

```yaml
# Network to connect with other containers and the internet, if not exposing a port
networks:
  api--fdt-container_net:
    driver: bridge

# Secrets for the config and datasets
secrets:
  fdt_config:
    file: .secrets/foundry_dev_tools.toml

  fdt_datasets:
    file: .secrets/foundry_datasets.toml

# The Foundry DevTools Container
services:
  fdt-container:
    container_name: project-fdt-container
    build:
      context: ./foundry-dev-tools-container
      dockerfile: Dockerfile
    restart: always
    networks:  # internal port 8888 - only expose a port if you want to access it outside of the Docker network
      - api--fdt-container_net
    volumes:
      - ./foundry-dev-tools-container/t3_code:/app/t3_code  # allow for code adjustments
      - ./foundry-dev-tools-container/datasets:/app/datasets  # persistent dataset storage
      - ./foundry-dev-tools-container/.vscode-server:/root/.vscode-server  # faster access to the container
    environment:
      - PYTHONPATH=/app/t3_code
    secrets:
      - fdt_config
      - fdt_datasets
    stop_grace_period: 0s
```

## Test

The following script can be used to test the API endpoints of the Foundry DevTools Container. Make sure to execute this within a Docker network which has access to the `project-fdt-container` service - if you have no port exposed.

```python
import asyncio
import websockets
import json
import httpx  # for downloading files

# WebSocket URL for dataset retrieval (note: port 8888)
DATASET_URL = "ws://project-fdt-container:8888/fdtc-api/dataset/get"
# If you expose the port: ws://localhost:8888/fdtc-api/dataset/get

DATASET_NAMES = ["Customer Demographics", "Transaction History"]

async def test_websocket():
    try:
        async with websockets.connect(DATASET_URL) as websocket: 
            print("Connected to WebSocket")
            
            # Send initial request with dataset names and optional date range
            initial_request = {
                "names": DATASET_NAMES,
                "from_dt": "2025-06-01",
                "to_dt": "2025-06-30"
            }
            await websocket.send(json.dumps(initial_request))
            print(f"Sent initial request: {initial_request}")
            
            sha256_result = None
            
            # Listen for responses
            async for message in websocket:
                response = json.loads(message)
                print(f"Received: {response}")
                
                # type final marks the last message in the stream
                if response.get("type") == "final":
                    sha256_result = response.get("datasets")
                    break
                    
            return sha256_result
            
    except Exception as e:
        print(f"Error: {e}")
        return None

async def download_dataset(sha256: str):
    """Download the dataset file after WebSocket workflow completes"""
    base_url = "http://project-fdt-container:8888/fdtc-api"
    
    async with httpx.AsyncClient() as client:
        # Download CSV
        csv_response = await client.get(f"{base_url}/dataset/download/csv/{sha256}")
        if csv_response.status_code == 200:
            with open(f"{sha256}.csv", "wb") as f:
                f.write(csv_response.content)
            print(f"Downloaded: {sha256}.csv")
        
        # Or download ZIP
        zip_response = await client.get(f"{base_url}/dataset/download/zip/{sha256}")
        if zip_response.status_code == 200:
            with open(f"{sha256}.zip", "wb") as f:
                f.write(zip_response.content)
            print(f"Downloaded: {sha256}.zip")

async def main():
    sha256 = await test_websocket()
    if sha256:
        await download_dataset(sha256)

asyncio.run(main())
```

## WebSocket Message Types

During the WebSocket workflow, you'll receive messages with the following structure:

```json
{
    "type": "update|final|error|keepalive",
    "success": true,
    "message": "Description of current status",
    "datasets": ["sha256_hash"]  // only in final message
}
```

- `update` - Progress updates during processing
- `keepalive` - Heartbeat messages (every 50 seconds) for long-running operations
- `final` - Operation completed, contains the SHA256 hash(es) of processed datasets
- `error` - Error occurred during processing

## File Storage Structure

```
datasets/
├── metadata/          # Metadata JSON files (by RID)
│   └── {rid}.json
├── zipped/            # Compressed datasets (by SHA256)
│   └── {sha256}.zip
├── unzipped/          # Uncompressed CSV files (by SHA256)
│   └── {sha256}.csv
└── tmp/               # Temporary files during processing
```

### Metadata File Format

```json
{
    "name": "Dataset Name",
    "rid": "dataset-uuid",
    "versions": [
        {
            "sha256": "a1b2c3d4...",
            "dates": ["2025-06-15T10:30:00"],
            "zipped": true,
            "unzipped": true
        }
    ]
}
```
