import os
import re
import hashlib
import logging
from datetime import datetime
from typing import List, Optional

import yaml
from dateutil.parser import parse as parse_date

from .config import SyncMapping
from .models import WorkItem

logger = logging.getLogger(__name__)

class LocalFileSystem:
    """
    Manages the local file representation of work items.
    """

    def __init__(self, mapping: SyncMapping):
        """
        Initializes the LocalFileSystem manager.

        Args:
            mapping (SyncMapping): The synchronization mapping for this file system.
        """
        self.mapping = mapping
        self.local_path = mapping.local_path
        os.makedirs(self.local_path, exist_ok=True)

    def get_local_work_items(self) -> List[WorkItem]:
        """
        Scans the local directory and returns a list of WorkItem objects.

        Returns:
            List[WorkItem]: A list of work items found locally.
        """
        local_items = []
        for filename in os.listdir(self.local_path):
            if filename.endswith(f".{self.mapping.file_format}"):
                file_path = os.path.join(self.local_path, filename)
                work_item = self._parse_file(file_path)
                if work_item:
                    local_items.append(work_item)
        return local_items

    def write_work_item(self, work_item: WorkItem) -> None:
        """
        Writes a WorkItem to a local file.

        Args:
            work_item (WorkItem): The work item to write.
        """
        file_path = self._get_file_path(work_item)
        content = self._render_template(work_item)

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info(f"Work item {work_item.id} written to {file_path}")
        except IOError as e:
            logger.error(f"Error writing to file {file_path}: {e}")

    def _get_file_path(self, work_item: WorkItem) -> str:
        """
        Determines the file path for a given work item.

        Args:
            work_item (WorkItem): The work item.

        Returns:
            str: The file path for the work item.
        """
        # Sanitize title for filename
        sanitized_title = re.sub(r'[\\/*?:"<>|]', "", work_item.title).replace(" ", "_")
        filename = f"{work_item.id}_{sanitized_title}.{self.mapping.file_format}"
        return os.path.join(self.local_path, filename)

    def _parse_file(self, file_path: str) -> Optional[WorkItem]:
        """
        Parses a single file and returns a WorkItem object.

        Args:
            file_path (str): The path to the file.

        Returns:
            Optional[WorkItem]: A WorkItem object, or None if parsing fails.
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            front_matter_match = re.match(r"---\s*\n(.*?)\n---\s*\n(.*)", content, re.DOTALL)
            if not front_matter_match:
                logger.warning(f"Could not parse front matter from {file_path}")
                return None

            front_matter_str, description = front_matter_match.groups()
            metadata = yaml.safe_load(front_matter_str)

            content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()

            created_date_val = metadata.get("created_date")
            changed_date_val = metadata.get("changed_date")

            # PyYAML can automatically parse dates into datetime objects
            created_date = created_date_val if isinstance(created_date_val, datetime) else parse_date(created_date_val)
            changed_date = changed_date_val if isinstance(changed_date_val, datetime) else parse_date(changed_date_val)

            return WorkItem(
                id=metadata.get("id"),
                type=metadata.get("type"),
                title=metadata.get("title", "No Title"), # Title is in the metadata now
                state=metadata.get("state"),
                description=description.strip(),
                created_date=created_date,
                changed_date=changed_date,
                local_path=file_path,
                content_hash=content_hash
            )
        except (IOError, yaml.YAMLError, KeyError) as e:
            logger.error(f"Error parsing file {file_path}: {e}")
            return None

    def _render_template(self, work_item: WorkItem) -> str:
        """
        Renders the file content for a work item using the mapping's template.

        Args:
            work_item (WorkItem): The work item.

        Returns:
            str: The rendered file content.
        """
        if not self.mapping.template:
            return work_item.description

        # Simple string replacement for now. A more robust templating engine
        # like Jinja2 could be used in the future.
        template = self.mapping.template
        content = template.replace("{{ id }}", str(work_item.id))
        content = content.replace("{{ type }}", work_item.type)
        content = content.replace("{{ title }}", work_item.title)
        content = content.replace("{{ state }}", work_item.state)
        content = content.replace("{{ created_date }}", work_item.created_date.isoformat())
        content = content.replace("{{ changed_date }}", work_item.changed_date.isoformat())
        content = content.replace("{{ description }}", work_item.description or "")

        # Add title to metadata for parsing
        if '---' in content:
            parts = content.split('---', 2)
            if len(parts) > 1:
                front_matter = parts[1]
                if 'title:' not in front_matter:
                    front_matter += f"\ntitle: {work_item.title}"
                content = f"---{front_matter}---{parts[2]}"

        return content
