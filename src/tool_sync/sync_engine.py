import logging
import os

from .config import Config, SyncMapping
from .azure_devops_client import AzureDevOpsClient
from .local_file_system import LocalFileSystem

logger = logging.getLogger(__name__)

class SyncEngine:
    """
    Orchestrates the synchronization process.
    """

    def __init__(self, config: Config):
        """
        Initializes the SyncEngine.

        Args:
            config (Config): The application configuration.
        """
        self.config = config

    def run(self):
        """
        Runs the synchronization for all mappings in the configuration.
        """
        logger.info("Starting synchronization...")
        for mapping in self.config.sync_mappings:
            logger.info(f"Processing mapping: '{mapping.name}'")
            ado_client = AzureDevOpsClient(self.config.azure_devops)
            local_fs = LocalFileSystem(mapping)
            self._sync_mapping(mapping, ado_client, local_fs)
        logger.info("Synchronization finished.")

    def _sync_mapping(self, mapping: SyncMapping, ado_client: AzureDevOpsClient, local_fs: LocalFileSystem):
        """
        Performs synchronization for a single mapping.

        Args:
            mapping (SyncMapping): The sync mapping to process.
            ado_client (AzureDevOpsClient): The client for Azure DevOps.
            local_fs (LocalFileSystem): The manager for the local file system.
        """
        # 1. Fetch remote and local items
        remote_items = ado_client.get_work_items(mapping.work_item_type, mapping.area_path)
        local_items = local_fs.get_local_work_items()

        # 2. Separate local items with and without IDs
        new_local_items = [item for item in local_items if item.id is None]
        existing_local_items = [item for item in local_items if item.id is not None]

        # 3. Index items by ID
        remote_items_by_id = {item.id: item for item in remote_items}
        local_items_by_id = {item.id: item for item in existing_local_items}

        # 4. Identify changes
        remote_ids = set(remote_items_by_id.keys())
        local_ids = set(local_items_by_id.keys())

        new_remote_ids = remote_ids - local_ids
        common_ids = remote_ids.intersection(local_ids)

        # 5. Process new local items -> create remote
        for new_item in new_local_items:
            logger.info(f"New local file found: {new_item.local_path}. Creating remote work item.")

            fields_to_create = {
                "System.Title": new_item.title,
                "System.Description": new_item.description,
            }
            for field_name in mapping.fields_to_sync:
                if field_name in new_item.fields:
                    fields_to_create[field_name] = new_item.fields[field_name]

            created_item = ado_client.create_work_item(
                mapping.work_item_type,
                fields_to_create
            )
            if created_item:
                # Delete old file and write new one with ID
                os.remove(new_item.local_path)
                local_fs.write_work_item(created_item)

        # 6. Process new remote items -> create locally
        for item_id in new_remote_ids:
            remote_item = remote_items_by_id[item_id]
            logger.info(f"New remote work item found: {item_id}. Creating locally.")
            local_fs.write_work_item(remote_item)

        # 7. Process common items -> check for updates
        for item_id in common_ids:
            remote_item = remote_items_by_id[item_id]
            local_item = local_items_by_id[item_id]

            # Last Write Wins strategy based on changed_date
            if remote_item.changed_date > local_item.changed_date:
                logger.info(f"Remote work item {item_id} is newer. Updating local file.")
                local_fs.write_work_item(remote_item)
            elif local_item.changed_date > remote_item.changed_date:
                logger.info(f"Local file for work item {item_id} is newer. Updating remote.")
                parsed_item = local_fs._parse_file(local_item.local_path)
                if parsed_item:
                    fields_to_update = {
                        "System.Title": parsed_item.title,
                        "System.Description": parsed_item.description,
                    }
                    for field_name in mapping.fields_to_sync:
                        if field_name in parsed_item.fields:
                            fields_to_update[field_name] = parsed_item.fields[field_name]

                    ado_client.update_work_item(parsed_item.id, fields_to_update)

        logger.info(f"Finished processing mapping: '{mapping.name}'")
