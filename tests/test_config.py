import pytest
from tool_sync.config import load_config, AzureDevOpsConfig, SyncMapping

def test_load_config_success(tmp_path):
    """
    Tests that the load_config function correctly loads a valid config file.
    """
    config_content = """
azure_devops:
  organization_url: "https://dev.azure.com/my_org"
  project_name: "my_project"
  personal_access_token: "my_pat"

sync_mappings:
  - name: "User Stories"
    work_item_type: "User Story"
    local_path: "stories"
    file_format: "md"
    conflict_resolution: "manual"
    template: "---id: {{ id }}---"
"""
    config_file = tmp_path / "config.yml"
    config_file.write_text(config_content)

    config = load_config(str(config_file))

    assert isinstance(config.azure_devops, AzureDevOpsConfig)
    assert config.azure_devops.organization_url == "https://dev.azure.com/my_org"
    assert len(config.sync_mappings) == 1
    assert isinstance(config.sync_mappings[0], SyncMapping)
    assert config.sync_mappings[0].name == "User Stories"

def test_load_config_with_area_path(tmp_path):
    """
    Tests that the load_config function correctly loads a config file with an area_path.
    """
    config_content = """
azure_devops:
  organization_url: "https://dev.azure.com/my_org"
  project_name: "my_project"
  personal_access_token: "my_pat"

sync_mappings:
  - name: "User Stories"
    work_item_type: "User Story"
    local_path: "stories"
    file_format: "md"
    conflict_resolution: "manual"
    template: "---id: {{ id }}---"
    area_path: 'MyProject\\MyTeam'
"""
    config_file = tmp_path / "config.yml"
    config_file.write_text(config_content)

    config = load_config(str(config_file))
    assert config.sync_mappings[0].area_path == "MyProject\\MyTeam"

def test_load_config_missing_section(tmp_path):
    """
    Tests that load_config raises a ValueError if a required section is missing.
    """
    config_content = """
sync_mappings:
  - name: "User Stories"
    work_item_type: "User Story"
    local_path: "stories"
    file_format: "md"
    conflict_resolution: "manual"
    template: "---id: {{ id }}---"
"""
    config_file = tmp_path / "config.yml"
    config_file.write_text(config_content)

    with pytest.raises(ValueError, match="Missing 'azure_devops' section"):
        load_config(str(config_file))

def test_load_config_file_not_found():
    """
    Tests that load_config raises a FileNotFoundError if the config file does not exist.
    """
    with pytest.raises(FileNotFoundError):
        load_config("non_existent_file.yml")
