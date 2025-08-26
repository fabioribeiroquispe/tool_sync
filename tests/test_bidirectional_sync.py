import pytest
from unittest.mock import MagicMock, patch
from tool_sync.sync_engine import SyncEngine
from tool_sync.config import Config, AzureDevOpsConfig, SyncMapping
from tool_sync.models import WorkItem
from datetime import datetime, timedelta
from tool_sync.azure_devops_client import AzureDevOpsClient
from tool_sync.local_file_system import LocalFileSystem
import os

@pytest.fixture
def mock_config():
    ado_config = AzureDevOpsConfig("https://dev.azure.com/my_org", "project", "pat")
    mapping = SyncMapping(
        name="Test",
        work_item_type="User Story",
        local_path="path",
        file_format="md",
        conflict_resolution="manual",
        template="template",
        fields_to_sync=["System.State"]
    )
    return Config(azure_devops=ado_config, sync_mappings=[mapping])

@pytest.fixture
def sync_engine(mock_config):
    return SyncEngine(mock_config)

@patch('tool_sync.sync_engine.os.remove')
def test_sync_engine_new_local_item(mock_os_remove, sync_engine, mock_config):
    """
    Tests that a new local item is created remotely with the correct fields.
    """
    # Arrange
    now = datetime.now()
    local_item = WorkItem(id=None, title="New Local", changed_date=now, type="User Story", state="New", description="desc", created_date=now, local_path="path/new.md", fields={"System.State": "New"})
    created_item = WorkItem(id=2, title="New Local", changed_date=now, type="User Story", state="New", description="desc", created_date=now, fields={"System.State": "New"})

    mock_ado_client = MagicMock(spec=AzureDevOpsClient)
    mock_ado_client.get_work_items.return_value = []
    mock_ado_client.create_work_item.return_value = created_item

    mock_local_fs = MagicMock(spec=LocalFileSystem)
    mock_local_fs.get_local_work_items.return_value = [local_item]

    # Act
    sync_engine._sync_mapping(mock_config.sync_mappings[0], mock_ado_client, mock_local_fs)

    # Assert
    expected_fields = {
        "System.Title": "New Local",
        "System.Description": "desc",
        "System.State": "New"
    }
    mock_ado_client.create_work_item.assert_called_once_with("User Story", expected_fields)
    mock_os_remove.assert_called_once_with("path/new.md")
    mock_local_fs.write_work_item.assert_called_once_with(created_item)

def test_sync_engine_updated_local_item(sync_engine, mock_config):
    """
    Tests that an updated local item updates the remote item with the correct fields.
    """
    # Arrange
    now = datetime.now()
    remote_item = WorkItem(id=1, title="Remote", changed_date=now - timedelta(days=1), type="User Story", state="Active", description="old", created_date=now - timedelta(days=1))
    local_item = WorkItem(id=1, title="Updated Local", changed_date=now, type="User Story", state="Resolved", description="new desc", created_date=now - timedelta(days=1), local_path="path/1.md", fields={"System.State": "Resolved"})

    mock_ado_client = MagicMock(spec=AzureDevOpsClient)
    mock_ado_client.get_work_items.return_value = [remote_item]

    mock_local_fs = MagicMock(spec=LocalFileSystem)
    mock_local_fs.get_local_work_items.return_value = [local_item]
    mock_local_fs._parse_file.return_value = local_item

    # Act
    sync_engine._sync_mapping(mock_config.sync_mappings[0], mock_ado_client, mock_local_fs)

    # Assert
    expected_fields = {
        "System.Title": "Updated Local",
        "System.Description": "new desc",
        "System.State": "Resolved"
    }
    mock_ado_client.update_work_item.assert_called_once_with(1, expected_fields)
