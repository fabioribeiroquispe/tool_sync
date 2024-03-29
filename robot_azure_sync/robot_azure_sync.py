"""
Module: robot_azure_sync

Description: This module provides synchronization functionalities for Azure-related tasks.
"""

import sys
import subprocess
import json
import os
import logging
from .robot_azure_sync_patch import robot_azure_sync_patch
from .robot_azure_sync_get import robot_azure_sync_get

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_sync_get():
    """
    Run the synchronization process for getting data from Azure.
    """
    robot_azure_sync_get()


def run_sync_patch():
    """
    Run the synchronization process for patching data to Azure.
    """
    robot_azure_sync_patch()


def run_robot_tests(tests_folder):
    """
    Run Robot Framework tests with a specific tag in the specified folder.

    :param tests_folder: The folder containing the Robot Framework tests.
    """
    subprocess.run(
        ["robot", '--xunit', 'output_xunit.xml', '-d', 'results', tests_folder],
        check=False
    )


def robot_azure_sync():
    """
    robot_azure_sync entry point of the synchronization script.

    If no command-line arguments are provided, it runs both sync_get and sync_patch.
    If 'get' is provided as an argument, only sync_get is executed.
    If 'patch' is provided as an argument, only sync_patch is executed.

    Additionally, if sync_config.json is present and contains the tests folder path,
    it runs Robot Framework tests with the tag 'Automation_Status Automated' in that folder.

    If sync_config.json is not found, create it interactively.
    """
    if len(sys.argv) == 1:
        run_sync_get()
        robot_azure_sync_patch()

        config_path = 'sync_config.json'
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as config_file:
                sync_config = json.load(config_file)
                tests_folder = sync_config.get('path', '')
                if tests_folder:
                    run_robot_tests(tests_folder)
                else:
                    logger.info(
                        "Tests folder path not specified in sync_config.json.")
        else:
            logger.info("sync_config.json not found.")
    elif len(sys.argv) == 2:
        if sys.argv[1] == "get":
            run_sync_get()
        elif sys.argv[1] == "patch":
            run_sync_patch()
        else:
            logger.info("Invalid argument. Use 'get' or 'patch'.")
    else:
        logger.info("Usage: python robot_azure_sync.py [get | patch]")


if __name__ == "__main__":
    robot_azure_sync()
