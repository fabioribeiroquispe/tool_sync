import pytest
from unittest.mock import MagicMock
from src.tool_sync.sync_engine import SyncEngine
from src.tool_sync.config import Config, AzureDevOpsConfig, SyncMapping
from src.tool_sync.models import WorkItem
from datetime import datetime, timedelta
from src.tool_sync.azure_devops_client import AzureDevOpsClient
from src.tool_sync.local_file_system import LocalFileSystem

@pytest.fixture
def mock_config():
    ado_config = AzureDevOpsConfig("https://dev.azure.com/my_org", "project", "pat")
    mapping = SyncMapping("Test", "User Story", "path", "md", "manual", "template")
    return Config(azure_devops=ado_config, sync_mappings=[mapping])

@pytest.fixture
def sync_engine(mock_config):
    return SyncEngine(mock_config)

def test_sync_engine_new_remote_item(sync_engine, mock_config):
    """
    Tests that a new remote item is created locally.
    """
    # Arrange
    remote_item = WorkItem(id=1, title="Remote Item", changed_date=datetime.now(), type="User Story", state="New", description="", created_date=datetime.now())

    mock_ado_client = MagicMock(spec=AzureDevOpsClient)
    mock_ado_client.get_work_items.return_value = [remote_item]

    mock_local_fs = MagicMock(spec=LocalFileSystem)
    mock_local_fs.get_local_work_items.return_value = []

    # Act
    sync_engine._sync_mapping(mock_config.sync_mappings[0], mock_ado_client, mock_local_fs)

    # Assert
    mock_local_fs.write_work_item.assert_called_once_with(remote_item)

def test_sync_engine_updated_remote_item(sync_engine, mock_config):
    """
    Tests that an updated remote item updates the local file.
    """
    # Arrange
    now = datetime.now()
    remote_item = WorkItem(id=1, title="Remote Item", changed_date=now, type="User Story", state="New", description="", created_date=now)
    local_item = WorkItem(id=1, title="Local Item", changed_date=now - timedelta(days=1), type="User Story", state="New", description="", created_date=now - timedelta(days=1))

    mock_ado_client = MagicMock(spec=AzureDevOpsClient)
    mock_ado_client.get_work_items.return_value = [remote_item]

    mock_local_fs = MagicMock(spec=LocalFileSystem)
    mock_local_fs.get_local_work_items.return_value = [local_item]

    # Act
    sync_engine._sync_mapping(mock_config.sync_mappings[0], mock_ado_client, mock_local_fs)

    # Assert
    mock_local_fs.write_work_item.assert_called_once_with(remote_item)

def test_sync_engine_no_changes(sync_engine, mock_config):
    """
    Tests that no action is taken when items are in sync.
    """
    # Arrange
    now = datetime.now()
    remote_item = WorkItem(id=1, title="Item", changed_date=now, type="User Story", state="New", description="", created_date=now)
    local_item = WorkItem(id=1, title="Item", changed_date=now, type="User Story", state="New", description="", created_date=now)

    mock_ado_client = MagicMock(spec=AzureDevOpsClient)
    mock_ado_client.get_work_items.return_value = [remote_item]

    mock_local_fs = MagicMock(spec=LocalFileSystem)
    mock_local_fs.get_local_work_items.return_value = [local_item]

    # Act
    sync_engine._sync_mapping(mock_config.sync_mappings[0], mock_ado_client, mock_local_fs)

    # Assert
    mock_local_fs.write_work_item.assert_not_called()
