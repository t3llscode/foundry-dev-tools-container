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