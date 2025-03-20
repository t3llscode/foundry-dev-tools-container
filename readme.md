# Foundry DevTools Container

#### The idea is an 'isolated' container to...

- Run the foundry dev tools
- Download datasets from Foundry
- Keep copies of datasets compressed as zip
- Provide an API to download datasets (via docker network) 

### Technical Details

- Config file for mapping names to dataset RIDs
- Redis channel for communication with docker network
- API for dataset management / provisioning
- Docker network for communication with other containers

### Planned Endpoints

- `/dataset/versions` - Returns all available versions of a dataset
- `/dataset/download` - Trigger the download of a dataset from the Foundry
- `/dataset/unzip` - Trigger unzip of one or multiple datasets
- `/dataset/zip` - Trigger zip of one or multiple datasets
- `/dataset/delete_unzipped` - Trigger deletion of one or multiple unzipped dataset files

#### Additional Endpoints (less priority)

- `/dataset/delete_zipped` - Trigger deletion of one or multiple zipped dataset files
- `/dataset/delete` - Trigger deletion of dataset (both zipped and unzipped files)
- `/dataset/list` - Returns a list of all available datasets and their versions
- `/dataset/info` - Returns information about one or multiple datasets

## Process: Update and Download Dataset (initiated by foreign API)

  - External API requests /dataset_version for a dataset (name is given by the API, an mapping inside the foundry-dev-tools container is going to map the RID to it)

  - External API checks whether the dataset is new enough.

    If new enough:

      - subscribe to the redis channel for dataset zip updates
      - request /dataset_unzip for the dataset
      - wait for the unzip completion message

    If not new enough:

      - subscribe to the redis channel for dataset downloads
      - request /dataset_download for the dataset
      - wait for the download completion message
      - request /dataset_get for the dataset
      - request /dataset_zip for the dataset
      - request /dataset_delete_raw for the dataset

  - Continue with the operation of converting the DB to the database and so on

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
"Customer Demographics"="12a3b4c5-d6e7-8f90-1a2b-3c4d5e6f7g8h"
"Transaction History"="98f7e6d5-c4b3-2a10-9f8e-7d6c5b4a3210"
"Product Catalog"="a1b2c3d4-e5f6-7890-a1b2-c3d4e5f67890"
"Supplier Inventory"="z9y8x7w6-v5u4-3210-z9y8-x7w6v5u4t3s2"
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
    container_name: bullseye-fdt-container
    build:
    context: ./foundry-dev-tools-container
    dockerfile: Dockerfile
    restart: always
    networks:  # internal port 8000 - only expose a port if you want to access it outside of the Docker network
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