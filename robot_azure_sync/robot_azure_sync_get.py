"""
Module: robot_azure_sync_get

This script facilitates the synchronization of test cases between Robot Framework and Azure DevOps.
It performs the extraction of test cases from Robot Framework content, 
queries Azure DevOps for new test cases, and subsequently updates the 
Robot Framework content with the newly obtained test cases.

Requirements:
- Python 3.x
- requests library

Ensure that a 'sync_config.json' file is in place with the required configuration parameters.

Usage:
1. Configure 'sync_config.json' with the necessary settings.
2. Run the script.
"""

import datetime
import re
import os
from html import unescape
from collections import namedtuple
import base64
import logging
import requests

from .sync_utils import (
    load_sync_config,
    read_robot_file,
    extract_test_tags_and_test_cases,
    extract_test_cases
)


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_id_azure_test_cases(base_url, headers_wiql, config_settings):
    """
    Function to retrieve Azure test cases based on the given Wiql query.

    Args:
        base_url (str): The base URL for Azure DevOps REST API.
        headers_wiql (dict): Headers for the Wiql request.

    Returns:
        set: A set of Azure test case IDs.
    """
    url_wiql = f"{base_url}wiql?api-version=7.1-preview.2"

    query = {
        "query": f"SELECT [System.Id]"
        f"FROM WorkItems "
        f"WHERE [System.AreaPath] = '{
            config_settings['constants']['System.AreaPath']}' "
        f"AND [System.WorkItemType] = 'Test Case'"
    }

    response_wiql = requests.post(
        url_wiql, json=query, headers=headers_wiql, timeout=10
    )

    if response_wiql.status_code == 200:
        data_wiql = response_wiql.json()
        return set(test_case["id"] for test_case in data_wiql["workItems"])


def create_robot_content(fields, pref_config):
    """
    Function to create Robot Framework content based on work item of Azure Test Cases fields.

    Args:
        fields (dict): Azure Test Case work item fields.
        pref_config (dict): Prefix configuration for tags.

    Returns:
        str: Robot Framework content.
    """
    WorkItemDetails = namedtuple(
        "WorkItemDetails",
        ["id", "title", "iteration_path", "priority", "automation_status", "sprint"],
    )

    def get_tags_line(work_item_details):
        prefix_test_case = prefix_config["test_case"]
        prefix_automation_status = prefix_config["AutomationStatus"]
        prefix_priority = prefix_config["Priority"]
        prefix_iteration_path = prefix_config["IterationPath"]
        tags_line = (
            f"    [tags]  {prefix_test_case} {work_item_details.id}    "
            f"{prefix_automation_status} {
                work_item_details.automation_status}    "
            f"{prefix_priority} {work_item_details.priority}    "
            f"{prefix_iteration_path} {
                work_item_details.sprint.replace(' ', '_')}"
        )

        tags_line += get_tags(fields)
        tags_line += get_relations_tags(fields)
        tags_line += "\n"

        return tags_line

    def get_steps_and_expected_results(steps_raw):
        steps_and_expected_results = re.findall(
            r'<step id="\d+" type=".*?">'
            r'<parameterizedString isformatted="true">(.*?)</parameterizedString>'
            r'<parameterizedString isformatted="true">(.*?)</parameterizedString>'
            r"<description/></step>",
            steps_raw,
            re.DOTALL,
        )

        return steps_and_expected_results

    def get_tags(fields):
        prefix_system_tags = prefix_config["System.Tags"]
        tags_line = ""
        if "System.Tags" in fields and fields["System.Tags"] is not None:
            tags_list = [tag.strip()
                         for tag in fields["System.Tags"].split(";")]
            tags_line += "    " + "    ".join(
                f"{prefix_system_tags} {tag}" for tag in tags_list
            )
        return tags_line

    def get_relations_tags(fields):
        prefix_user_story = prefix_config["user_story"]
        tags_line = ""
        if "relations" in fields:
            relations = fields["relations"]
            for relation in relations:
                if "url" in relation and "_apis/wit/workItems/" in relation["url"]:
                    us_id = re.search(
                        r"_apis/wit/workItems/(\d+)", relation["url"]
                    ).group(1)
                    tags_line += f"    {prefix_user_story} {us_id}"
        return tags_line

    work_item_details = WorkItemDetails(
        id=fields.get("System.Id", ""),
        title=fields.get("System.Title", ""),
        iteration_path=fields.get("System.IterationPath", ""),
        priority=fields.get("Microsoft.VSTS.Common.Priority", ""),
        automation_status=fields.get(
            "Microsoft.VSTS.TCM.AutomationStatus", ""),
        sprint=fields.get("System.IterationPath", ""),
    )

    sprint_number = re.search(r"\bSprint (\d+)\b", work_item_details.sprint)
    if sprint_number:
        work_item_details = work_item_details._replace(
            sprint=f"Sprint_{sprint_number.group(1)}"
        )

    tags_line = get_tags_line(work_item_details)

    rf_content = f"\n{pref_config['title']} {work_item_details.title}\n"
    rf_content += tags_line

    steps_raw = fields.get("Microsoft.VSTS.TCM.Steps", "")
    steps_and_expected_results = get_steps_and_expected_results(steps_raw)

    for _, (step, _) in enumerate(steps_and_expected_results, start=1):
        step = unescape(re.sub("<[^<]+?>", "", step.strip()))
        step = step.replace("<P>", "").replace("</P>", "")
        step = step.replace("<DIV>", "").replace("</DIV>", "")
        step = step.replace("<BR>", "").replace("<BR/>", "")

        if step:
            rf_content += f"    {step}\n"
    rf_content += "\n"

    return rf_content


def get_robot_test_case_ids_recursive(folder_path, config):
    """
    Function to recursively retrieve Robot Framework test case IDs from 
    files in specified folder and its
    subdirectories.

    Args:
        folder_path (str): The path to the folder containing Robot Framework files.
        prefix_test_case (str): The prefix for identifying test cases in tags.
        config (dict): Configuration data for synchronization.

    Returns:
        set: A set of Robot Framework test case IDs.
    """
    rf_test_case_ids = set()
    prefix_test_case = config["tag_config"]["test_case"]
    test_cases_section = constants["test_cases_section"]
    settings_section = constants["settings_section"]

    for root, _, files in os.walk(folder_path):
        for rf_file in files:
            if rf_file.endswith(".robot"):
                file_path = os.path.join(root, rf_file)
                content = read_robot_file(file_path)
                test_cases_data, _ = extract_test_tags_and_test_cases(
                    content, settings_section, test_cases_section)
                cases = extract_test_cases(test_cases_data, config)
                rf_test_case_ids.update(
                    int(
                        re.search(rf"{prefix_test_case}\s*(\d+)",
                                  case["Tags"]).group(1)
                    )
                    for case in cases
                    if re.search(rf"{prefix_test_case}\s*(\d+)", case["Tags"])
                )

    return rf_test_case_ids


def process_new_test_cases(new_test_case_ids, robot_test_case_ids):
    """
    Function to process new test cases by querying Azure DevOps and updating lists.

    Args:
        new_test_case_ids (set): Set of new test case IDs.
        robot_test_case_ids (set): Set of existing Robot Framework test case IDs.
        url (str): Base URL for Azure DevOps REST API.
        headers (dict): Headers for HTTP requests.

    Returns:
        list: A list of JSON responses for the new test cases.
    """
    response_json_list = []
    personal_access_token = credentials["personal_access_token"]
    organization = credentials["organization_name"]
    project = credentials["project_name"]
    url = f"https://dev.azure.com/{organization}/{project}/_apis/wit/"
    headers = {
        "Authorization": "Basic "
        + base64.b64encode(f"{personal_access_token}:".encode()).decode(),
    }

    for test_case_id in new_test_case_ids:
        if test_case_id not in robot_test_case_ids:
            url_workitems = f"{url}workitems?ids={
                test_case_id}&$expand=all&api-version=7.1-preview.3"
            response_workitems = requests.get(
                url_workitems, headers=headers, timeout=10
            )

            if response_workitems.status_code == 200:
                data_workitems = response_workitems.json()
                work_item = data_workitems["value"][0]["fields"]
                azure_last_updated_date = work_item.get(
                    "System.ChangedDate", "")
                try:
                    azure_last_updated_date = datetime.datetime.strptime(
                        azure_last_updated_date, "%Y-%m-%dT%H:%M:%S.%fZ"
                    )
                except ValueError as e:
                    logger.info("Error parsing date '%s': %s",
                                azure_last_updated_date, e)

                # timestamp = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
                # test_case_dates = f"GET Test Case ID: {test_case_id} - Robot Date Change: {
                #     timestamp} - Azure Date Change: {azure_last_updated_date}\n"

                logger.info("ID: %s, Title: %s", test_case_id,
                            work_item['System.Title'])
                response_json_list.append(data_workitems)
            else:
                logger.info(
                    "Error in request: %s - %s",
                    response_workitems.status_code,
                    response_workitems.text
                )

    return response_json_list


def robot_azure_sync_get():
    """
    Main function to synchronize Azure test cases with Robot Framework.

    This function retrieves Azure test cases, identifies new test cases that are not present in the
    Robot Framework,and updates the Robot Framework file todo_organize.robot 
    with the new test cases.
    """
    # Retrieving Azure test cases
    personal_access_token = credentials["personal_access_token"]
    organization = credentials["organization_name"]
    project = credentials["project_name"]
    url = f"https://dev.azure.com/{organization}/{project}/_apis/wit/"
    headers = {
        "Authorization": "Basic "
        + base64.b64encode(f"{personal_access_token}:".encode()).decode(),
    }
    settings_section = constants["settings_section"]
    test_cases_section = constants["test_cases_section"]
    azure_test_cases = get_id_azure_test_cases(url, headers, sync_config)

    # Retrieving Robot Framework test case IDs
    robot_test_case_ids = get_robot_test_case_ids_recursive(
        robot_folder_path, sync_config
    )

    # Identifying new test cases
    new_test_case_ids = azure_test_cases - robot_test_case_ids
    response_json_list = []

    # Processing new test cases
    response_json_list = process_new_test_cases(
        new_test_case_ids, robot_test_case_ids
    )

    # Creating log file and updating Robot Framework file
    if not os.path.exists(robot_folder_path):
        os.makedirs(robot_folder_path)
    log_file_name = os.path.join(robot_folder_path, "sync_log.txt")

    with open(log_file_name, "a", encoding="utf-8") as log_file:
        for test_case_id, response_json in zip(new_test_case_ids, response_json_list):
            work_item = response_json["value"][0]["fields"]
            azure_last_updated_date = work_item.get("System.ChangedDate", "")
            try:
                azure_last_updated_date = datetime.datetime.strptime(
                    azure_last_updated_date, "%Y-%m-%dT%H:%M:%S.%fZ"
                )
            except ValueError as e:
                logger.info("Error parsing date '%s': %s",
                            azure_last_updated_date, e)
            timestamp = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            log_file.write(
                f"GET Test Case ID: {test_case_id} - Robot Date Change: {
                    timestamp} - Azure Date Change: {azure_last_updated_date}\n"
            )

    # Constructing Robot Framework content
    robot_content: str = ""
    for response_json in response_json_list:
        work_item = response_json["value"][0]["fields"]
        robot_content += create_robot_content(work_item, prefix_config)

    # Updating Robot Framework file
    file_name = os.path.join(robot_folder_path, "todo_organize.robot")

    existing_content: str = ""

    if os.path.exists(file_name):
        with open(file_name, "r", encoding="utf-8") as existing_file:
            existing_content = existing_file.read()

    if not existing_content or (
        settings_section not in existing_content
        and test_cases_section not in existing_content
    ):
        existing_content += f"{settings_section}\n\n{test_cases_section}\n"

    if robot_content:
        existing_content += f"{robot_content}\n"

    with open(file_name, "w", encoding="utf-8") as file:
        file.write(existing_content)
    logger.info("Robot Framework file '%s' updated successfully.", file_name)


# Loading synchronization configuration
sync_config = load_sync_config()
robot_folder_path = sync_config["path"]
constants = sync_config["constants"]
credentials = sync_config["credentials"]
prefix_config = sync_config["tag_config"]
# settings_section = constants["settings_section"]
# test_cases_section = constants["test_cases_section"]
# personal_access_token = credentials["personal_access_token"]
# organization = credentials["organization_name"]
# project = credentials["project_name"]
# prefix_user_story = prefix_config["user_story"]
# prefix_system_tags = prefix_config["System.Tags"]
# prefix_priority = prefix_config["Priority"]
# prefix_test_case = prefix_config["test_case"]
# prefix_automation_status = prefix_config["AutomationStatus"]
# prefix_iteration_path = prefix_config["IterationPath"]
# url = f"https://dev.azure.com/{organization}/{project}/_apis/wit/"
# headers = {
#     "Authorization": "Basic "
#     + base64.b64encode(f"{personal_access_token}:".encode()).decode(),
# }


if __name__ == "__main__":
    robot_azure_sync_get()
