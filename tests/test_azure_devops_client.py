import pytest
from unittest.mock import MagicMock, patch
import requests
from tool_sync.azure_devops_client import AzureDevOpsClient
from tool_sync.config import AzureDevOpsConfig
from tool_sync.models import WorkItem
from datetime import datetime

@pytest.fixture
def mock_ado_config():
    return AzureDevOpsConfig(
        organization_url="https://dev.azure.com/my_org",
        project_name="my_project",
        personal_access_token="my_pat"
    )

@pytest.fixture
def ado_client(mock_ado_config):
    return AzureDevOpsClient(mock_ado_config)

def test_azure_devops_client_init(ado_client, mock_ado_config):
    """
    Tests the initialization of the AzureDevOpsClient.
    """
    assert ado_client.config == mock_ado_config
    assert "Authorization" in ado_client.headers

@patch('requests.post')
def test_get_work_item_ids_success(mock_post, ado_client):
    """
    Tests successful fetching of work item IDs.
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"workItems": [{"id": 1}, {"id": 2}]}
    mock_post.return_value = mock_response

    ids = ado_client.get_work_item_ids("User Story")
    assert ids == [1, 2]

@patch('requests.get')
def test_get_work_item_success(mock_get, ado_client):
    """
    Tests successful fetching of a single work item.
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "id": 1,
        "fields": {
            "System.WorkItemType": "User Story",
            "System.Title": "Test Story",
            "System.State": "New",
            "System.Description": "A test story.",
            "System.CreatedDate": "2023-01-01T12:00:00Z",
            "System.ChangedDate": "2023-01-01T13:00:00Z",
        }
    }
    mock_get.return_value = mock_response

    item = ado_client.get_work_item(1)
    assert isinstance(item, WorkItem)
    assert item.id == 1
    assert item.title == "Test Story"

@patch('requests.post')
def test_get_work_item_ids_api_error(mock_post, ado_client):
    """
    Tests handling of API errors when fetching work item IDs.
    """
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = requests.RequestException("API Error")
    mock_post.return_value = mock_response

    ids = ado_client.get_work_item_ids("User Story")
    assert ids == []

@patch('requests.post')
def test_get_work_item_ids_with_area_path(mock_post, ado_client):
    """
    Tests that the WIQL query includes the area path when provided.
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"workItems": []}
    mock_post.return_value = mock_response

    ado_client.get_work_item_ids("User Story", "MyProject\\MyTeam")

    # Check that the query sent to the API contains the Area Path clause
    sent_query = mock_post.call_args[1]['json']['query']
    assert "AND [System.AreaPath] = 'MyProject\\MyTeam'" in sent_query

@patch('requests.post')
def test_get_work_item_ids_without_area_path(mock_post, ado_client):
    """
    Tests that the WIQL query does not include the area path when not provided.
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"workItems": []}
    mock_post.return_value = mock_response

    ado_client.get_work_item_ids("User Story")

    sent_query = mock_post.call_args[1]['json']['query']
    assert "AND [System.AreaPath]" not in sent_query

@patch('requests.patch')
def test_update_work_item_success(mock_patch, ado_client):
    """
    Tests successful update of a work item.
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_patch.return_value = mock_response

    fields_to_update = {"System.Title": "New Title"}
    success = ado_client.update_work_item(1, fields_to_update)
    assert success is True

@patch('requests.post')
def test_create_work_item_success(mock_post, ado_client):
    """
    Tests successful creation of a work item.
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"id": 3}
    mock_post.return_value = mock_response

    # Mock the get_work_item call that happens after creation
    with patch.object(ado_client, 'get_work_item') as mock_get:
        mock_get.return_value = WorkItem(id=3, title="New Item", type="Bug", state="New", description="", created_date=datetime.now(), changed_date=datetime.now())

        fields_to_create = {"System.Title": "New Item"}
        new_item = ado_client.create_work_item("Bug", fields_to_create)

        assert new_item is not None
        assert new_item.id == 3
