import yaml
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class AzureDevOpsConfig:
    organization_url: str
    project_name: str
    personal_access_token: str

@dataclass
class SyncMapping:
    name: str
    work_item_type: str
    local_path: str
    file_format: str
    azure_devops: AzureDevOpsConfig  # Moved here
    template: str = ""
    fields_to_sync: List[str] = field(default_factory=list)
    area_path: Optional[str] = None
    conflict_resolution: Optional[str] = "last_write_wins" # Added default

@dataclass
class Config:
    sync_mappings: List[SyncMapping]

def load_config(path: str = "config.yml") -> Config:
    """
    Loads the configuration from a YAML file.

    Args:
        path (str): The path to the configuration file.

    Returns:
        Config: The validated configuration object.
    """
    with open(path, "r", encoding="utf-8") as f:
        config_data = yaml.safe_load(f)

    if "sync_mappings" not in config_data:
        raise ValueError("Missing 'sync_mappings' section in config file.")

    sync_mappings = []
    for mapping_data in config_data["sync_mappings"]:
        if "azure_devops" not in mapping_data:
            raise ValueError(f"Missing 'azure_devops' section in mapping: {mapping_data.get('name', 'N/A')}")

        ado_config_data = mapping_data.pop("azure_devops")
        ado_config = AzureDevOpsConfig(**ado_config_data)

        mapping = SyncMapping(azure_devops=ado_config, **mapping_data)
        sync_mappings.append(mapping)

    return Config(sync_mappings=sync_mappings)
