import pytest
from unittest.mock import MagicMock, patch
from src.tool_sync.sync_engine import SyncEngine
from src.tool_sync.config import Config, AzureDevOpsConfig, SyncMapping
from src.tool_sync.models import WorkItem
from datetime import datetime, timedelta
from src.tool_sync.azure_devops_client import AzureDevOpsClient
from src.tool_sync.local_file_system import LocalFileSystem
import os

@pytest.fixture
def mock_config():
    ado_config = AzureDevOpsConfig("https://dev.azure.com/my_org", "project", "pat")
    mapping = SyncMapping("Test", "User Story", "path", "md", "manual", "template")
    return Config(azure_devops=ado_config, sync_mappings=[mapping])

@pytest.fixture
def sync_engine(mock_config):
    return SyncEngine(mock_config)

@patch('tool_sync.sync_engine.os.remove')
def test_sync_engine_new_local_item(mock_os_remove, sync_engine, mock_config):
    """
    Tests that a new local item is created remotely.
    """
    # Arrange
    now = datetime.now()
    local_item = WorkItem(id=None, title="New Local Item", changed_date=now, type="User Story", state="New", description="desc", created_date=now, local_path="path/new_item.md")
    created_item = WorkItem(id=2, title="New Local Item", changed_date=now, type="User Story", state="New", description="desc", created_date=now)

    mock_ado_client = MagicMock(spec=AzureDevOpsClient)
    mock_ado_client.get_work_items.return_value = []
    mock_ado_client.create_work_item.return_value = created_item

    mock_local_fs = MagicMock(spec=LocalFileSystem)
    mock_local_fs.get_local_work_items.return_value = [local_item]

    # Act
    sync_engine._sync_mapping(mock_config.sync_mappings[0], mock_ado_client, mock_local_fs)

    # Assert
    mock_ado_client.create_work_item.assert_called_once_with("User Story", "New Local Item", "desc")
    mock_os_remove.assert_called_once_with("path/new_item.md")
    mock_local_fs.write_work_item.assert_called_once_with(created_item)

def test_sync_engine_updated_local_item(sync_engine, mock_config):
    """
    Tests that an updated local item updates the remote item.
    """
    # Arrange
    now = datetime.now()
    remote_item = WorkItem(id=1, title="Remote Item", changed_date=now - timedelta(days=1), type="User Story", state="New", description="", created_date=now - timedelta(days=1))
    local_item = WorkItem(id=1, title="Updated Local", changed_date=now, type="User Story", state="New", description="updated desc", created_date=now - timedelta(days=1), local_path="path/1_item.md")

    mock_ado_client = MagicMock(spec=AzureDevOpsClient)
    mock_ado_client.get_work_items.return_value = [remote_item]

    mock_local_fs = MagicMock(spec=LocalFileSystem)
    mock_local_fs.get_local_work_items.return_value = [local_item]
    mock_local_fs._parse_file.return_value = local_item

    # Act
    sync_engine._sync_mapping(mock_config.sync_mappings[0], mock_ado_client, mock_local_fs)

    # Assert
    mock_ado_client.update_work_item.assert_called_once_with(local_item)
