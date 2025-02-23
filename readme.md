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
    
- `/dataset/version` - Get the latest version of a dataset
- `/dataset/download` - Download a dataset
- `/dataset/unzip` - Unzip a dataset
- `/dataset/download` - Get a dataset
- `/dataset/zip` - Zip a dataset
- `/dataset/delete_raw` - Delete raw dataset files

#### Additional Endpoints (less priority)

- `/dataset/delete_zip` - Delete zip dataset files
- `/dataset/delete` - Delete dataset (both raw and zip files)
- `/dataset/list` - List all datasets
- `/dataset/info` - Get information about a dataset

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