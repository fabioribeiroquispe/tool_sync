# Tool Sync: Bidirectional Azure DevOps Synchronization

## Overview

**Tool Sync** is a powerful and flexible command-line tool that provides bidirectional synchronization between Azure DevOps work items and local files. Unlike other tools that are often unidirectional or limited to specific work item types, Tool Sync allows you to keep any type of work item (User Stories, Bugs, Tasks, etc.) in sync with local files in your Git repository.

This enables a "Work-Items-as-Code" approach, where your Azure DevOps project can be treated as a single source of truth that is perfectly mirrored in a local directory, allowing you to leverage the power of your favorite text editors and version control systems to manage your work.

## Features

-   **Bidirectional Synchronization:** Changes made locally or in Azure DevOps are reflected on the other side.
-   **Generic Work Item Support:** Sync any type of work item, not just Test Cases or User Stories.
-   **Configurable Mappings:** Define which work item types to sync, where to store them, and in what format.
-   **Local File Representation:** Work items are stored as local files (e.g., Markdown with YAML front matter), making them easy to read, edit, and version control.
-   **"Last Write Wins" Strategy:** The tool uses a timestamp-based "last write wins" strategy to handle updates.

## Installation

To install Tool Sync, you can use `pip`. Open a terminal and run:

```bash
pip install tool_sync
```

(Note: The package is not yet published to PyPI. To install from source, see the next section.)

### Installation from Source

1.  Clone the repository:
    ```bash
    git clone https://github.com/fabioribeiroquispe/tool_sync.git
    ```
2.  Navigate to the project directory:
    ```bash
    cd tool_sync
    ```
3.  Install the package in editable mode:
    ```bash
    pip install -e .
    ```

## Configuration

Tool Sync requires a `config.yml` file in the root of your project. This file defines the connection to your Azure DevOps project and how different work item types should be synchronized.

Here is an example `config.yml`:

```yaml
azure_devops:
  organization_url: "https://dev.azure.com/your_org"
  project_name: "your_project"
  personal_access_token: "your_pat"

sync_mappings:
  - name: "User Stories for Team A"
    work_item_type: "User Story"
    local_path: "work_items/team_a/stories"
    area_path: 'MyProject\\TeamA' # Optional: Sync only items from this Area Path
    file_format: "md"
    fields_to_sync:
      - System.State
      - Microsoft.VSTS.Common.Priority
    template: |
      ---
      id: {{ id }}
      type: {{ type }}
      title: '{{ title }}'
      state: {{ fields['System.State'] | default('') }}
      priority: {{ fields['Microsoft.VSTS.Common.Priority'] | default('') }}
      created_date: '{{ created_date }}'
      changed_date: '{{ changed_date }}'
      ---

      # {{ title }}

      {{ description }}

  - name: "All Bugs"
    work_item_type: "Bug"
    local_path: "work_items/bugs"
    file_format: "md"
```

### Configuration Options

-   **`azure_devops`**:
    -   `organization_url`: The URL of your Azure DevOps organization (e.g., `https://dev.azure.com/my-org`).
    -   `project_name`: The name of your Azure DevOps project.
    -   `personal_access_token`: Your Personal Access Token (PAT) for authenticating with the Azure DevOps API.
-   **`sync_mappings`**: A list of mappings, where each mapping defines a sync relationship.
    -   `name`: A descriptive name for the mapping.
    -   `work_item_type`: The type of work item to sync (e.g., "User Story", "Bug").
    -   `local_path`: The local directory where the files for these work items will be stored.
    -   `area_path` (Optional): The Azure DevOps Area Path to filter by. If provided, only work items under this path will be synchronized.
    -   `fields_to_sync` (Optional): A list of additional Azure DevOps fields to sync (e.g., `System.State`, `System.Tags`).
    -   `file_format`: The file extension for the local files (e.g., `md`, `json`).
    -   `conflict_resolution`: (Future feature) The strategy to use when a conflict is detected.
    -   `template`: The Jinja2 template to use for generating the content of the local files.

## Usage

To run the synchronization, simply execute the following command in your terminal:

```bash
tool_sync sync
```

The tool will read your `config.yml`, connect to Azure DevOps, and perform the synchronization based on your defined mappings.

### Creating New Work Items

You can create a new work item in Azure DevOps by creating a new file in the corresponding local directory. The file should follow the format defined in your template, but without an `id` field in the front matter.

For example, to create a new User Story, you could create a new file `work_items/user_stories/my-new-story.md` with the following content:

```yaml
---
type: User Story
state: New
created_date: '2023-10-27T10:00:00Z'
changed_date: '2023-10-27T10:00:00Z'
title: 'My New User Story'
---

# My New User Story

This is the description of my new user story.
```

The next time you run `tool_sync sync`, the tool will detect this new file, create a corresponding User Story in Azure DevOps, and then update the local file with the newly assigned ID.

## AI-Powered Analysis with Cline

`tool_sync` is more than just a synchronization tool. It includes a powerful **AI analysis engine** that can be used as a local MCP (Model Context Protocol) server for AI assistants like the [Cline VS Code extension](https://marketplace.visualstudio.com/items?itemName=cline.bot).

This allows you to have rich, context-aware conversations about your project's data, ask complex questions, find patterns, and identify root causes.

### How It Works

The analysis engine uses a **Retrieval-Augmented Generation (RAG)** pipeline. When you start the server, it can index all your local work item files into a local vector database. When you ask a question via Cline, the server finds the most relevant documents and provides them as context to the LLM, leading to highly accurate and relevant answers.

### Usage

#### Step 1: Install All Dependencies

The analysis engine requires additional libraries (`mcp`, `chromadb`, etc.). They are included in the main installation. Ensure you have installed the project from source with all dependencies:
```bash
pip install -e .
```

#### Step 2: Start the Analysis Server

To start the MCP server, run the following command in your terminal:
```bash
tool_sync analyze
```
The server will start and listen for connections from Cline via STDIO.

#### Step 3: (First time only) Index Your Documents

The first time you use the analysis feature, or after you have synchronized new work items, you need to tell the server to build its knowledge base. You can do this by asking Cline to run the `index_documents` tool.

Example prompt for Cline:
> Using the `tool_sync_analyzer` tool, please run the `index_documents` command. The `work_items_path` is 'work_items/'.

#### Step 4: Configure Cline

You need to tell Cline how to connect to the `tool_sync` server. Open your `cline_mcp_settings.json` file and add the following server configuration.

**Important:** You must replace `/path/to/your/repo/` with the absolute path to this project's directory on your machine.

```json
{
  "mcpServers": {
    "tool_sync_analyzer": {
      "command": "/path/to/your/repo/venv/bin/python",
      "args": [
        "-m",
        "tool_sync.main",
        "analyze"
      ],
      "disabled": false
    }
  }
}
```
*Note: The `command` should point to the Python executable within the virtual environment where you installed `tool_sync` to ensure it finds all the correct libraries.*

#### Step 5: Ask Questions!

Once configured, you can ask Cline complex questions about your project. Remember to tell Cline to use your tool.

Example prompts for Cline:
- "Using the `tool_sync_analyzer` tool, what is the most common cause of login errors?"
- "Please summarize the defects related to the 'Roteirizador Product' using the `query_documents` tool."
