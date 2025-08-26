import yaml
from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass
class AzureDevOpsConfig:
    organization_url: str
    project_name: str
    personal_access_token: str

from typing import Optional

@dataclass
class SyncMapping:
    name: str
    work_item_type: str
    local_path: str
    file_format: str
    conflict_resolution: str
    template: str = ""
    fields_to_sync: List[str] = field(default_factory=list)
    area_path: Optional[str] = None

@dataclass
class Config:
    azure_devops: AzureDevOpsConfig
    sync_mappings: List[SyncMapping]

def load_config(path: str = "config.yml") -> Config:
    """
    Loads the configuration from a YAML file.

    Args:
        path (str): The path to the configuration file.

    Returns:
        Config: The validated configuration object.
    """
    with open(path, "r") as f:
        config_data = yaml.safe_load(f)

    # Basic validation
    if "azure_devops" not in config_data:
        raise ValueError("Missing 'azure_devops' section in config file.")
    if "sync_mappings" not in config_data:
        raise ValueError("Missing 'sync_mappings' section in config file.")

    ado_config = AzureDevOpsConfig(**config_data["azure_devops"])

    sync_mappings = [
        SyncMapping(**mapping) for mapping in config_data["sync_mappings"]
    ]

    return Config(azure_devops=ado_config, sync_mappings=sync_mappings)
