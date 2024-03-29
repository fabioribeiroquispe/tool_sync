"""
Module: robot_azure_sync_patch

This module provides functionality to synchronize test cases between Robot Framework
and Azure DevOps. It includes classes and functions for extracting, parsing, and updating
test cases in both systems.

Requirements:
- Python 3.x
- requests library

Make sure a 'sync_config.json' file is installed with the required configuration parameters.

Use:
1. Configure 'sync_config.json' with the required settings.
2. Run the script.
"""

import base64
import datetime
import json
import os
import re
from venv import logger
import requests

from .sync_utils import (
    read_robot_file,
    extract_test_cases,
    extract_test_tags_and_test_cases,
    load_sync_config
)


class TestStep:
    """
    Class representing a test step in Azure DevOps.

    Attributes:
        action (str): The action or instruction for the test step.
        description (str): The description or expected result of the test step.
    """

    def __init__(self, action, description):
        """
        Initializes a TestStep instance.

        Args:
            action (str): The action or instruction for the test step.
            description (str): The description or expected result of the test step.
        """
        self.action = action
        self.description = description
        self.validate()

    def validate(self):
        """
        Validates the TestStep instance.

        Raises:
            ValueError: If the action is not a string.
        """
        if not isinstance(self.action, str):
            raise ValueError("Action must be strings.")

    def to_dict(self, step_id):
        """
        Converts the TestStep instance to a dictionary.

        Args:
            step_id (int): The ID of the test step.

        Returns:
            dict: A dictionary representing the test step in Azure DevOps format.
        """
        return {
            "step": {
                "id": step_id,
                "type": "ActionStep",
                "action": (
                    f'<parameterizedString isformatted="true">'
                    f"&lt;P&gt;{
                        self.action}&lt;BR/&gt;&lt;/P&gt;</parameterizedString>"
                ),
                "expectedResult": (
                    '<parameterizedString isformatted="true">'
                    "&lt;DIV&gt;&lt;P&gt;&lt;BR/&gt;&lt;/P&gt;&lt;/DIV&gt;</parameterizedString>"
                ),
                "description": f"{self.description}",
            }
        }


def find_robot_files(folder_path):
    """
    Finds Robot Framework files in the specified folder and its subfolders.

    Args:
        folder_path (str): The path to the folder to search.

    Returns:
        list: A list of paths to Robot Framework files.
    """
    robot_files = []
    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.endswith(".robot"):
                robot_files.append(os.path.normpath(os.path.join(root, file)))
    return robot_files


def parse_tags(tag_string):
    """
    Parses test tags from a string.

    Args:
        tag_string (str): The string containing test tags.

    Returns:
        dict: A dictionary representing parsed test tags.
    """
    tag_dict = {}
    categories_and_values = re.findall(r"(\S+)\s*(?::|\s)\s*(\S+)", tag_string)
    for category, value in categories_and_values:
        if category not in tag_dict:
            tag_dict[category] = []
        tag_dict[category].append(value)
    return tag_dict


def transform_steps(steps_list):
    """
    Transforms a list of raw test steps into a list of TestStep objects.

    Args:
        steps_list (list): List of raw test steps.

    Returns:
        list: List of TestStep objects.
    """
    transformed_steps = []
    for step_id, step in enumerate(steps_list, start=1):
        test_step = TestStep(step, step_id)
        transformed_steps.append(test_step)
    return transformed_steps


def extract_tags_info(case_tag, sync_configuration):
    """
    Extracts information from test case tags.

    Args:
        case_tag (dict): Dictionary containing information about test case tags.
        sync_configuration (dict): Configuration settings.

    Returns:
        tuple: A tuple containing automation status tag key, priority tag key, and tags value.
    """
    automation_status_tag_key_match = re.search(
        rf"{sync_configuration['tag_config']['AutomationStatus']}\s*([^\s]+)",
        case_tag["Tags"],
    )
    automation_status_tag_key = (
        automation_status_tag_key_match.group(1)
        .strip()
        .replace("_", " " if automation_status_tag_key_match else None)
    )
    priority_tag_key_match = re.search(
        rf"{sync_configuration['tag_config']
            ['Priority']}\s*([^\s]+)", case_tag["Tags"]
    )
    priority_tag_key = (
        priority_tag_key_match.group(
            1).strip() if priority_tag_key_match else None
    )
    test_tags_key = case_tag["Tags"].strip() if case_tag["Tags"] else None
    system_tags_key_match = re.search(
        rf"{sync_configuration['tag_config']['System.Tags']}\s*([\w\s]+)",
        case_tag["Tags"],
    )
    system_tags_key = (
        system_tags_key_match.group(
            1).strip() if system_tags_key_match else None
    )

    tags_value = ""
    if test_tags_key and not system_tags_key:
        tags_value = test_tags_key
    elif system_tags_key and not test_tags_key:
        tags_value = system_tags_key
    elif system_tags_key and test_tags_key:
        tags_value = f"{test_tags_key}; {system_tags_key}"

    return automation_status_tag_key, priority_tag_key, tags_value


def build_iteration_path_tags(iteration_path_tags, sync_configuration):
    """
    Builds the iteration path tags for updating Azure Test Cases.

    Args:
        iteration_path_tags (list): List of iteration path tags.
        sync_configuration (dict): Configuration settings.

    Returns:
        dict: Azure DevOps update operation for iteration path.
    """
    update_iteration_path = None
    iteration_path_tag_candidate_with_spaces = None

    for iteration_path_tag_candidate in iteration_path_tags:
        iteration_path_tag_candidate_with_spaces = iteration_path_tag_candidate.replace(
            "_", " "
        )
        iteration_path_value = (
            f"{sync_configuration['constants']['System.AreaPath']}"
            f"{iteration_path_tag_candidate_with_spaces}"
        )
        update_iteration_path = {
            "op": "replace",
            "path": "/fields/System.IterationPath",
            "value": iteration_path_value,
        }

    return update_iteration_path


def build_linked_items(linked_work_items, organization_name, project_name):
    """
    Builds the linked items for updating Azure Test Cases.

    Args:
        linked_work_items (list): List of linked work items.
        organization_name (str): Azure DevOps organization name.
        project_name (str): Azure DevOps project name.

    Returns:
        list: List of linked items for Azure Test Cases.
    """
    linked_items = []

    for linked_item in linked_work_items:
        linked_items.append(
            {
                "op": "add",
                "path": "/relations/-",
                "value": {
                    "rel": "Microsoft.VSTS.Common.TestedBy-Reverse",
                    "url": (
                        f"https://dev.azure.com/{organization_name}/"
                        f"{project_name}/_apis/wit/workitems/{linked_item}"
                    ),
                    "attributes": {"comment": "Associated test case with work item"},
                },
            }
        )

    return linked_items


def build_steps_xml(transformed_steps):
    """
    Builds XML representation of test steps for updating Azure Test Cases.

    Args:
        transformed_steps (list): List of transformed test steps.

    Returns:
        str: XML representation of test steps.
    """
    test_steps = [step.to_dict(i)
                  for i, step in enumerate(transformed_steps, start=1)]
    steps_xml = f'<steps id="0" last="{len(test_steps)}">'
    steps_xml += "".join(
        f'<step id="{step_id}" type="{step["step"]["type"]}">'
        f'{step["step"]["action"]}{step["step"]["expectedResult"]}'
        f"<description/></step>"
        for step_id, step in enumerate(test_steps, start=1)
    )
    steps_xml += "</steps>"
    return steps_xml


def build_fields(data_tags, title, linked_items, transformed_steps):
    """
    Builds the fields for updating Azure Test Cases.

    Args:
        automation_status_tag_key (str): Automation status tag key.
        priority_tag_key (str): Priority tag key.
        tags_value (str): Combined value of test tags.
        title (str): Test case title.
        linked_items (list): List of linked items for Azure Test Cases.
        transformed_steps (list): List of transformed test steps.

    Returns:
        list: List of fields for updating Azure Test Cases.
    """
    steps_xml = build_steps_xml(transformed_steps)
    fields = [
        *filter(
            None,
            [
                {
                    "op": "replace",
                    "path": "/fields/Microsoft.VSTS.Common.Priority",
                    "value": data_tags[1],
                },
                {
                    "op": "replace",
                    "path": "/fields/System.Title",
                    "value": title,
                },
                {
                    "op": "replace",
                    "path": "/fields/Microsoft.VSTS.TCM.Steps",
                    "value": steps_xml,
                },
                {
                    "op": "replace",
                    "path": "/fields/System.Tags",
                    "value": data_tags[2],
                },
                *linked_items,
            ],
        )
    ]

    return list(filter(lambda x: x["value"] is not None and x["value"] != "", fields))


def log_sync_changes(test_case_id, operation):
    """
    Logs synchronization changes to the sync_log.txt file.

    Args:
        test_case_id (str): The ID of the test case.
        operation (str): The type of operation performed (e.g., "PATCH").

    Returns:
        None
    """
    path = sync_config["path"]
    timestamp = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    log_entry = f"{operation} Test Case ID: {
        test_case_id} - {operation} Date Change: {timestamp}"
    if not os.path.exists(path):
        os.makedirs(path)
    log_file_path = os.path.join(path, "sync_log.txt")
    with open(log_file_path, "r+", encoding="utf-8") as log_file:
        lines = log_file.readlines()
        log_file.seek(0)
        updated = False
        for line in lines:
            if f"{operation} Test Case ID: {test_case_id}" in line:
                log_file.write(log_entry + "\n")
                updated = True
            else:
                log_file.write(line)
        if not updated:
            log_file.write(log_entry + "\n")
        log_file.truncate()


def update_azure_test_case(
    cases_dict, system_tags, transformed_steps, sync_configuration, linked_work_items
):
    """
    Updates an Azure Test Case with the provided information.

    Args:
        cases_dict (dict): Dictionary containing information about the test case.
        system_tags (str): Tags related to the test case.
        transformed_steps (list): List of transformed test steps.
        sync_configuration (dict): Configuration settings.
        linked_work_items (list): List of linked work items.

    Returns:
        None
    """
    tags = parse_tags(cases_dict["Tags"])
    for test_step in transformed_steps:
        test_step.validate()

    automation_status_tag_key, priority_tag_key, _ = extract_tags_info(
        cases_dict, sync_configuration
    )

    organization_name = sync_configuration["credentials"]["organization_name"]
    project_name = sync_configuration["credentials"]["project_name"]
    personal_access_token = sync_configuration["credentials"]["personal_access_token"]

    title_test_case = cases_dict["Title"]

    test_case_id_match = re.search(r"TestCase\s*(\d+)", cases_dict["Tags"])
    test_case_id = test_case_id_match.group(1) if test_case_id_match else ""

    iteration_path_tags = tags.get(
        sync_configuration["tag_config"]["IterationPath"], []
    )
    build_iteration_path_tags(iteration_path_tags, sync_configuration)

    url = (
        f"https://dev.azure.com/{organization_name}/"
        f"{project_name}/_apis/wit/workitems/{test_case_id}"
        "?api-version=7.2-preview.3"
    )

    linked_items = build_linked_items(
        linked_work_items, organization_name, project_name
    )

    tags_info = [automation_status_tag_key, priority_tag_key, system_tags]

    fields = build_fields(
        tags_info,
        title_test_case,
        linked_items,
        transformed_steps,
    )

    headers = {
        "Content-Type": "application/json-patch+json",
        "Authorization": "Basic "
        + base64.b64encode(f"{personal_access_token}:".encode()).decode(),
    }
    payload = json.dumps(fields)
    timeout_seconds = 10

    try:
        response = requests.patch(
            url, data=payload, headers=headers, timeout=timeout_seconds
        )
        if response.status_code == 200:
            test_case_id_match = re.search(
                r"TestCase\s*(\d+)", cases_dict["Tags"])
            test_case_id = test_case_id_match.group(
                1) if test_case_id_match else ""
            log_sync_changes(test_case_id, "PATCH")
            logger.info("Atualização dos Tests Cases na Azure bem-sucedida!")
        else:
            logger.info(
                "Erro na atualização dos Tests Cases na Azure. "
                "Código de status: %s", response.status_code
            )
            logger.info(response.text)

    except requests.Timeout:
        logger.info(
            "A atualização dos Tests Cases na Azure excedeu o "
            "tempo limite de %s segundos.", timeout_seconds
        )
    except requests.RequestException as e:
        logger.info("Erro na atualização dos Tests Cases na Azure: %s", e)


def robot_azure_sync_patch():
    """
    This function performs synchronization between the Robot Framework and Azure DevOps.
    It reads Robot Framework files, extracts test cases and tags, and updates
    the corresponding test cases in Azure DevOps.
    """
    path_robot_files = find_robot_files(sync_config["path"])
    for robot_file in path_robot_files:
        if "todo_organize.robot" not in robot_file:
            content = read_robot_file(robot_file)
            test_cases_data, test_tags = extract_test_tags_and_test_cases(
                content,
                sync_config["constants"]["settings_section"],
                sync_config["constants"]["test_cases_section"]
            )
            cases = extract_test_cases(test_cases_data, sync_config)
            for case in cases:
                logger.info("\n%s", "=" * 70)
                tags = parse_tags(case["Tags"])
                user_story_ids = tags.get("UserStory", [])
                bug_ids = tags.get("Bug", [])
                linked_item_id = user_story_ids + bug_ids
                steps = transform_steps(case["Steps"])
                update_azure_test_case(
                    case, test_tags, steps, sync_config, linked_item_id
                )


sync_config = load_sync_config()

if __name__ == "__main__":
    robot_azure_sync_patch()
