# Robot Framework Azure Sync 

## Overview

The **Robot Framework Azure Sync** package provides synchronization capabilities for Azure-related tasks. It includes scripts to retrieve data from Azure Test Cases **(`robot_azure_sync_get.py`)**, to update Azure Test Cases **(`robot_azure_sync_patch.py`)**, and to run Robot Framework tests with specific tags.

## Installation

To install `robot_azure_sync`, you can use `pip`. Open a terminal and run:

```bash
pip install robot_azure_sync
```

## Using the project source code

Alternatively, you can download the project source code from the repository and use it directly. You will need to have Python installed on your system.

1. Clone the repository:

```bash
git clone https://github.com/fabiorisantosquispe/robot_azure_sync.git
```

2. Navigate to the project directory:

```bash
cd robot_azure_sync
```
3. Use the provided scripts

- sync_utils.py: Contains utility functions for synchronization.
- robot_azure_sync_get.py: Script to get data from Azure Test Cases.
- robot_azure_sync_patch.py: Script to patch data to Azure Test Cases.
- robot_azure_sync.py: Main script for synchronization and running Robot Framework tests.


# Usage
## Using the installed package
If you installed the package via pip, you can use the following commands:

```bash
#Run synchronize_get and synchronize_patch
robot_azure_sync

#Just run sync_get
robot_azure_sync get

#Run sync_patch only
robot_azure_sync patch
```

## Using the project source code
If you are using the project source code directly, you can execute the scripts using Python:

```bash
# Run synchronize_get and synchronize_patch
python robot_azure_sync.py

# Just run sync_get
python robot_azure_sync.py get

# Run sync_patch only
python robot_azure_sync.py patch
```

# Configuration
The package requires a configuration file **'sync_config.json'** with Azure-related settings. If the file is not found, it will be created interactively.

Example **'sync_config.json'**:
```JSON
{
     "path": "tests",
     "credentials": {
       "personal_access_token": "your_azure_personal_access_token",
       "organization_name": "your_organization_name",
       "project_name": "your_project_name"
     },
     "tag_config": {
       "test_case": "TC",
       "user_story": "US",
       "bug": "Bug",
       "title": "Title",
       "TestedBy-Reverse": "",
       "IterationPath": "",
       "AutomationStatus": "",
       "ignore_sync": "",
       "System.Tags": "",
       "Priority": ""
     },
     "constants": {
       "System.AreaPath": "",
       "System.TeamProject": "",
       "settings_section": "",
       "test_cases_section": ""
     }
}
```
