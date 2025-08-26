import base64
import logging
from typing import List, Dict, Any, Optional

import requests
from dateutil.parser import parse as parse_date

from .config import AzureDevOpsConfig
from .models import WorkItem

logger = logging.getLogger(__name__)

class AzureDevOpsClient:
    """
    A client for interacting with the Azure DevOps REST API.
    """

    def __init__(self, config: AzureDevOpsConfig):
        """
        Initializes the AzureDevOpsClient.

        Args:
            config (AzureDevOpsConfig): The Azure DevOps configuration.
        """
        self.config = config
        self.base_url = f"{config.organization_url}/{config.project_name}/_apis/wit"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {self._get_basic_auth_token()}",
        }

    def _get_basic_auth_token(self) -> str:
        """
        Generates a basic authentication token for the Azure DevOps API.

        Returns:
            str: The base64 encoded authentication token.
        """
        pat = self.config.personal_access_token
        return base64.b64encode(f":{pat}".encode("ascii")).decode("ascii")

    def get_work_item_ids(self, work_item_type: str, area_path: Optional[str] = None) -> List[int]:
        """
        Gets the IDs of all work items of a specific type.

        Args:
            work_item_type (str): The type of work item to query (e.g., "User Story").
            area_path (Optional[str]): The area path to filter by.

        Returns:
            List[int]: A list of work item IDs.
        """
        wiql_query = f"SELECT [System.Id] FROM WorkItems WHERE [System.WorkItemType] = '{work_item_type}' AND [System.TeamProject] = '{self.config.project_name}'"
        if area_path:
            wiql_query += f" AND [System.AreaPath] = '{area_path}'"

        query = {"query": wiql_query}
        url = f"{self.base_url}/wiql?api-version=6.0"

        try:
            response = requests.post(url, headers=self.headers, json=query)
            response.raise_for_status()
            results = response.json()
            return [wi["id"] for wi in results.get("workItems", [])]
        except requests.RequestException as e:
            logger.error(f"Error querying work item IDs: {e}")
            return []

    def get_work_item(self, work_item_id: int) -> WorkItem | None:
        """
        Gets the details of a single work item.

        Args:
            work_item_id (int): The ID of the work item.

        Returns:
            WorkItem | None: A WorkItem object, or None if not found.
        """
        url = f"{self.base_url}/workitems/{work_item_id}?$expand=all&api-version=6.0"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            fields = data["fields"]

            return WorkItem(
                id=data["id"],
                type=fields.get("System.WorkItemType"),
                title=fields.get("System.Title"),
                state=fields.get("System.State"),
                description=fields.get("System.Description", ""),
                created_date=parse_date(fields.get("System.CreatedDate")),
                changed_date=parse_date(fields.get("System.ChangedDate")),
                fields=fields,
            )
        except requests.RequestException as e:
            logger.error(f"Error fetching work item {work_item_id}: {e}")
            return None

    def get_work_items(self, work_item_type: str, area_path: Optional[str] = None) -> List[WorkItem]:
        """
        Gets all work items of a specific type.

        Args:
            work_item_type (str): The type of work item to query.
            area_path (Optional[str]): The area path to filter by.

        Returns:
            List[WorkItem]: A list of WorkItem objects.
        """
        work_item_ids = self.get_work_item_ids(work_item_type, area_path)
        if not work_item_ids:
            return []

        # ADO API has a limit of 200 work items per request
        work_items_data = []
        for i in range(0, len(work_item_ids), 200):
            chunk = work_item_ids[i:i+200]
            ids_str = ",".join(map(str, chunk))
            url = f"{self.base_url}/workitems?ids={ids_str}&$expand=all&api-version=6.0"
            try:
                response = requests.get(url, headers=self.headers)
                response.raise_for_status()
                work_items_data.extend(response.json().get("value", []))
            except requests.RequestException as e:
                logger.error(f"Error fetching work items chunk: {e}")

        work_items = []
        for data in work_items_data:
            fields = data["fields"]
            work_items.append(
                WorkItem(
                    id=data["id"],
                    type=fields.get("System.WorkItemType"),
                    title=fields.get("System.Title"),
                    state=fields.get("System.State"),
                    description=fields.get("System.Description", ""),
                    created_date=parse_date(fields.get("System.CreatedDate")),
                    changed_date=parse_date(fields.get("System.ChangedDate")),
                    fields=fields,
                )
            )
        return work_items

    def update_work_item(self, work_item_id: int, fields: Dict[str, Any]) -> bool:
        """
        Updates an existing work item in Azure DevOps.

        Args:
            work_item_id (int): The ID of the work item to update.
            fields (Dict[str, Any]): A dictionary of fields to update.

        Returns:
            bool: True if the update was successful, False otherwise.
        """
        url = f"{self.base_url}/workitems/{work_item_id}?api-version=6.0"

        # Construct the JSON patch document
        patch_document = [
            {"op": "replace", "path": f"/fields/{field}", "value": value} for field, value in fields.items()
        ]

        try:
            response = requests.patch(
                url,
                headers={**self.headers, "Content-Type": "application/json-patch+json"},
                json=patch_document
            )
            response.raise_for_status()
            logger.info(f"Successfully updated work item {work_item_id} in Azure DevOps.")
            return True
        except requests.RequestException as e:
            logger.error(f"Error updating work item {work_item.id}: {e}")
            return False

    def create_work_item(self, work_item_type: str, fields: Dict[str, Any]) -> WorkItem | None:
        """
        Creates a new work item in Azure DevOps.

        Args:
            work_item_type (str): The type of the work item to create.
            fields (Dict[str, Any]): A dictionary of fields for the new work item.

        Returns:
            WorkItem | None: The created work item, or None if creation fails.
        """
        url = f"{self.base_url}/workitems/${work_item_type}?api-version=6.0"

        patch_document = [
            {"op": "add", "path": f"/fields/{field}", "value": value} for field, value in fields.items()
        ]

        try:
            response = requests.post(
                url,
                headers={**self.headers, "Content-Type": "application/json-patch+json"},
                json=patch_document
            )
            response.raise_for_status()
            data = response.json()
            logger.info(f"Successfully created work item {data['id']} in Azure DevOps.")
            return self.get_work_item(data['id'])
        except requests.RequestException as e:
            logger.error(f"Error creating work item: {e}")
            return None
