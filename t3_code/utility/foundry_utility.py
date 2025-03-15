import os
import toml
from foundry_dev_tools import FoundryContext

class FoundryConnection:

    def __init__(self, config_secret_name: str = "foundry_dev_tools.toml", dataset_secret_name: str = "foundry_datasets.toml"):
        self.foundry_context = FoundryConnection.get_FoundryContext_with_fresh_config(config_secret_name)
        self.prefix, self.datasets = FoundryConnection.get_prefix_and_datasets(dataset_secret_name)

    @staticmethod
    def get_FoundryContext_with_fresh_config(config_secret_name: str = "foundry_dev_tools.toml"):
        """ Check and move the foundry_dev_tools.toml secret to the expected location and create FoundryContext """
        path = "/etc/xdg/foundry-dev-tools/config.toml"
        
        with open(f"/run/secrets/{config_secret_name}", "r") as secret_file:
            content = secret_file.read()

            # Check for '[Credentials]', 'domain' and 'jwt' within the .toml
            message = ""
            if "[credentials]" not in content:
                message += "Section '[credentials]' is missing\n"
            if "domain" not in content:
                message += "Parameter 'domain' is missing\n"
            if "jwt" not in content:
                message += "Parameter 'jwt' is missing\n"

            if message:  # Throw a detailed error if the format is invalid
                print(f"- - - - -\nERROR: foundry_dev_tools.toml secret is not matching the expected format:\n\n[credentials]\n\ndomain = \"\"\n\njwt = \"\"\n\nIssues:\n{message}- - - - -")

            else:
                print(f"SUCCESS: foundry_dev_tools.toml secret was placed in {path}.")

                os.makedirs(os.path.dirname(path), exist_ok=True)  # Create directory if it doesn't exist
                with open(path, "w") as config_file:  # Write content to file
                    config_file.write(content)
        
            return FoundryContext()

    @staticmethod
    def get_prefix_and_datasets(dataset_config_name: str = "foundry_datasets.toml") -> dict:
        """ Load dataset configuration from foundry_datasets.toml secret """
        with open(f"/run/secrets/{dataset_config_name}", "r") as secret_file:
            content = secret_file.read()
            file = toml.loads(content)

            datasets = file.get("datasets", {})
            prefix = file.get("prefix", "ri.foundry.main.dataset.")

            return prefix, datasets
