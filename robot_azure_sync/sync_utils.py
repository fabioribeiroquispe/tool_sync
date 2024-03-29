"""
Module: sync_utils.py

Description:
This module contains the SyncUtils class, which provides materials for synchronization operations.
"""
import json
import os
import re
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_credentials():
    '''
    Get the credentials for the sync_config.json file.
    '''
    personal_access_token = input(
        "Azure personal access token with read and write permission: "
    )
    organization_name = input(
        "Organization name (the one that comes after "
        "https://dev.azure.com/): "
    )
    project_name = input(
        f"Project name (the one after "
        f"https://dev.azure.com/{organization_name}/): "
    )
    return {
        "personal_access_token": personal_access_token,
        "organization_name": organization_name,
        "project_name": project_name
    }


def get_tag_config():
    '''
    Get the tag configuration for the sync_config.json file.
    '''
    test_case = input(
        "Prefix used to identify the Test Case id example (TC, TestCase): "
    )
    user_story = input(
        "Prefix used to identify the User Story id related to the "
        "Test Case example (US, UserStory): "
    )
    bug = input(
        "Prefix used to identify the Bug id related to the Test Case "
        "example (Bug): "
    )
    title = input(
        "Prefix used to identify the title of the "
        "Test Case example(Title, Scenario): "
    )
    tested_by_reverse = input(
        "Reverse the 'Tested By' relationship between "
        "Test Cases and User Stories: "
    )
    iteration_path = input("Azure DevOps field for Iteration Path: ")
    automation_status = input(
        "Azure DevOps field for Automation Status: "
    )
    ignore_sync = input(
        "Azure DevOps field to mark Test Cases that should be ignored "
        "during synchronization: "
    )
    system_tags = input("Azure DevOps field for System Tags: ")
    priority = input("Azure DevOps field for Priority: ")
    return {
        "test_case": test_case,
        "user_story": user_story,
        "bug": bug,
        "title": title,
        "TestedBy-Reverse": tested_by_reverse,
        "IterationPath": iteration_path,
        "AutomationStatus": automation_status,
        "ignore_sync": ignore_sync,
        "System.Tags": system_tags,
        "Priority": priority
    }


def get_constants():
    '''
    Get the constants for the sync_config.json file.
    '''
    area_path = input("Azure DevOps field for Area Path: ")
    team_project = input("Azure DevOps field for Team Project: ")
    settings_section = input(
        "Section in the Robot Framework settings file to store "
        "Azure-related settings: "
    )
    test_cases_section = input(
        "Section in the Robot Framework settings file to store "
        "synchronized Test Cases: "
    )
    return {
        "System.AreaPath": area_path,
        "System.TeamProject": team_project,
        "settings_section": settings_section,
        "test_cases_section": test_cases_section
    }


def create_sync_config():
    """
    Create the sync_config.json file interactively.
    """
    logger.info("The sync_config.json file was not found. Let's create it.")

    # Gather information interactively
    credentials = get_credentials()
    tag_config = get_tag_config()
    constants = get_constants()

    tests_folder = input(
        "Folder with Robot Framework tests to be "
        "synchronized (default: tests): "
    )

    # Populate the sync_config structure
    sync_config = {
        "path": tests_folder,
        "credentials": credentials,
        "tag_config": tag_config,
        "constants": constants
    }

    # Save the sync_config.json file
    with open("sync_config.json", "w", encoding="utf-8") as config_file:
        json.dump(sync_config, config_file, indent=2)

    logger.info("sync_config.json created successfully.")


def load_sync_config(file_path="sync_config.json"):
    """
    Function to load synchronization configuration from JSON file.

    Args:
        file_path (str, optional): The path to the synchronization
        configuration JSON file.
            Defaults to "sync_config.json".

    Returns:
        dict: A dictionary containing synchronization configuration.
    """

    # Creating sync configuration if not present
    if not os.path.isfile("sync_config.json"):
        create_sync_config()

    with open(file_path, "r", encoding="utf-8") as config_file:
        sync_config = json.load(config_file)
    return sync_config


def read_robot_file(file_name):
    """
    Function to read the contents of a Robot Framework file.

    Args:
        file_path (str): The path to the Robot Framework file.

    Returns:
        str: The contents of the Robot Framework file.
    """

    file_path = f"{file_name}"
    with open(file_path, "r", encoding="utf-8") as rf_file:
        return rf_file.read()


def extract_test_tags_and_test_cases(
        rf_content, settings_section, test_cases_section):
    """
    Function to extract test tags and test cases from
    Robot Framework content.

    Args:
        rf_content (str): Robot Framework content.
        settings_section (str): Section in the Robot Framework
        settings file.

        test_cases_section (str): Section in the Robot Framework settings
        file to store synchronized Test Cases.

    Returns:
        Tuple[str, str]: A tuple containing raw test cases data and
        case tags.
    """
    settings_match = re.search(
        rf"{
            re.escape(settings_section)
        }(.*?)\*\*\*", rf_content, re.DOTALL
    )
    settings_data = settings_match.group(
        1).strip() if settings_match else ""
    settings_lines = settings_data.split("\n")
    settings_dict = {}
    for line in settings_lines:
        parts = line.split()
        if len(parts) >= 2:
            key = parts[0]
            value = " ".join(parts[1:])
            settings_dict[key] = value
            test_tags_match = re.search(
                r"Test\s*Tags\s+(.+)", settings_data, re.IGNORECASE
            )
            case_tags = test_tags_match.group(
                1).strip() if test_tags_match else None
            case_tags = "; ".join(case_tags.split())
        else:
            case_tags = None
    test_cases_match = re.search(
        rf"{re.escape(test_cases_section)
            }(.*?)(?=\*\*\*|$)", rf_content, re.DOTALL
    )
    raw_test_cases_data = test_cases_match.group(
        1).strip() if test_cases_match else ""
    return raw_test_cases_data, case_tags


def extract_test_cases(raw_test_cases_data, config_settings):
    """
    Function to extract test cases from Robot Framework data.

    Args:
        raw_test_cases_data (str): The data containing test cases.
        config_settings (dict): Configuration data for synchronization.

    Returns:
        List[dict]: A list of dictionaries representing extracted
        test cases.
    """
    test_cases = []
    current_test_case = {}
    lines = raw_test_cases_data.split("\n")
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith(config_settings["tag_config"]["title"]):
            if current_test_case:
                test_cases.append(current_test_case)
            current_test_case = {
                "Title": line[len(
                    config_settings["tag_config"]["title"]):].strip(),
                "Tags": "",
                "Steps": [],
            }
        elif line.startswith("[tags]"):
            current_test_case["Tags"] = line[len("[tags]"):].strip()
        else:
            current_test_case["Steps"].append(line)
    if current_test_case:
        test_cases.append(current_test_case)
    return test_cases
