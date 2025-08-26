import pytest
from tool_sync.local_file_system import LocalFileSystem
from tool_sync.config import SyncMapping
from tool_sync.models import WorkItem
from datetime import datetime
import os

@pytest.fixture
def sync_mapping(tmp_path):
    local_path = tmp_path / "work_items"
    return SyncMapping(
        name="Test Mapping",
        work_item_type="Test Item",
        local_path=str(local_path),
        file_format="md",
        conflict_resolution="manual",
        fields_to_sync=["System.State", "Custom.Field"],
        template="---\nid: {{ id }}\ntitle: '{{ title }}'\nstate: {{ fields['System.State'] }}\ncustom: {{ fields['Custom.Field'] }}\nchanged_date: '{{ changed_date }}'\n---\n\n{{ description }}"
    )

@pytest.fixture
def local_fs(sync_mapping):
    return LocalFileSystem(sync_mapping)

@pytest.fixture
def sample_work_item():
    return WorkItem(
        id=1,
        type="Test Item",
        title="Sample Item",
        state="Active",
        description="This is a test item.",
        created_date=datetime(2023, 1, 1, 12, 0, 0),
        changed_date=datetime(2023, 1, 1, 13, 0, 0),
        fields={
            "System.State": "Active",
            "Custom.Field": "Custom Value"
        }
    )

def test_local_file_system_init(local_fs, sync_mapping):
    """
    Tests the initialization of the LocalFileSystem.
    """
    assert os.path.exists(sync_mapping.local_path)

def test_write_and_read_work_item(local_fs, sample_work_item):
    """
    Tests writing a WorkItem to a file and then reading it back.
    """
    local_fs.write_work_item(sample_work_item)

    local_items = local_fs.get_local_work_items()
    assert len(local_items) == 1

    read_item = local_items[0]
    assert read_item.id == sample_work_item.id
    assert read_item.title == sample_work_item.title
    assert read_item.description == sample_work_item.description
    assert read_item.changed_date.replace(tzinfo=None) == sample_work_item.changed_date
    assert read_item.state == "Active"
    assert read_item.fields["custom"] == "Custom Value"

def test_get_file_path(local_fs, sample_work_item):
    """
    Tests the _get_file_path method.
    """
    path = local_fs._get_file_path(sample_work_item)
    assert path.endswith("1_Sample_Item.md")

def test_parse_file_no_front_matter(tmp_path, local_fs):
    """
    Tests that parsing a file with no front matter returns None.
    """
    # Create a dummy file in the local_fs path
    invalid_file = os.path.join(local_fs.local_path, "invalid.md")
    with open(invalid_file, "w") as f:
        f.write("Just some content.")

    item = local_fs._parse_file(str(invalid_file))
    assert item is None
