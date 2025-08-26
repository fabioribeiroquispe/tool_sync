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

`tool-sync` offers two installation options depending on your needs.

### Standard Installation (Synchronization only)

For the core synchronization features, you can install the package directly using pip:

```bash
pip install tool-sync
```

This will provide you with the `tool_sync sync` command and all necessary functionality to synchronize your work items.

### Installation with Analysis Features

To use the AI-powered analysis server with assistants like Cline, you need to install the package with the `[analysis]` extra. This includes additional libraries for vector indexing and language processing.

```bash
pip install "tool-sync[analysis]"
```

## Configuration

Tool Sync is configured via a `config.yml` file in your project's root directory. This file defines a list of "sync mappings", where each mapping is a rule that connects a remote Azure DevOps query to a local directory.

**NEW in 0.5.0:** You can now sync work items from **multiple projects** in the same configuration file.

Here is a detailed example `config.yml` demonstrating multi-project synchronization:

```yaml
# A list of synchronization rules.
sync_mappings:
  # Example 1: Sync User Stories from 'Project Alpha' for Team A
  - name: "Alpha Project - Team A Stories"
    # --- Connection details for this specific mapping ---
    azure_devops:
      organization_url: "https://dev.azure.com/your_org"
      project_name: "Project Alpha"
      personal_access_token: "your_pat_goes_here"
    # --- Sync rules for this mapping ---
    work_item_type: "User Story"
    local_path: "work_items/project_alpha/stories"
    area_path: 'Project Alpha\\Team A' # Syncs only items from this Area Path
    file_format: "md"
    fields_to_sync:
      - System.State
      - Microsoft.VSTS.Common.Priority
    template: |
      ---
      id: {{ id }}
      type: {{ type }}
      title: '{{ title }}'
      state: {{ fields['System.State'] | default('New') }}
      priority: {{ fields['Microsoft.VSTS.Common.Priority'] | default(2) }}
      ---
      {{ description }}

  # Example 2: Sync all Bugs from a different project, 'Project Bravo'
  - name: "Bravo Project - All Bugs"
    # --- Connection details for Project Bravo ---
    azure_devops:
      organization_url: "https://dev.azure.com/your_org" # Can be the same or a different org
      project_name: "Project Bravo"
      personal_access_token: "your_other_pat_if_needed"
    # --- Sync rules for this mapping ---
    work_item_type: "Bug"
    local_path: "work_items/project_bravo/bugs"
    # No area_path is specified, so it will sync all bugs from Project Bravo.
    file_format: "md"
    template: |
      ---
      id: {{ id }}
      title: '{{ title }}'
      state: {{ fields['System.State'] | default('New') }}
      severity: {{ fields['Microsoft.VSTS.Common.Severity'] | default('3 - Medium') }}
      ---
      **Bug Description:**
      {{ description }}
```

### Configuration Options

Each entry in the `sync_mappings` list has the following options:

-   `name`: A descriptive name for the mapping (e.g., "Frontend Team Bugs").
-   `azure_devops`: **(Required)** Contains the connection details for this specific mapping.
    -   `organization_url`: The URL of your Azure DevOps organization.
    -   `project_name`: The name of the Azure DevOps project for this mapping.
    -   `personal_access_token`: Your Personal Access Token (PAT) for authentication.
-   `work_item_type`: **(Required)** The type of work item to sync (e.g., "User Story", "Bug").
-   `local_path`: **(Required)** The local directory where the files for these work items will be stored.
-   `area_path` (Optional): The Azure DevOps Area Path to filter by. If provided, only work items under this path will be synchronized.
-   `fields_to_sync` (Optional): A list of additional Azure DevOps fields to sync.
-   `file_format`: **(Required)** The file extension for the local files (e.g., `md`, `json`).
-   `template` (Optional): The Jinja2 template to use for generating the content of the local files. If omitted, a default template is used.

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

### Using the Analysis Engine with Cline

To use the AI-powered analysis features, you will need an MCP client like the [Cline VS Code extension](https://marketplace.visualstudio.com/items?itemName=cline.bot). The following steps will guide you through the setup and usage.

#### Step 1: Configure the Cline MCP Server

This is the most crucial step. You need to tell Cline how to start the `tool_sync` server.

1.  **Find the settings file:** In VS Code, click on the **MCP Servers** icon in the activity bar. This will open a new panel.
2.  **Open the configuration:** In the MCP Servers panel, go to the **Installed** tab, find your `tool_sync_analyzer` server (it may appear here after the first attempt to use it), or simply click the "Configure MCP Servers" button or link. This will open the `cline_mcp_settings.json` file.

3.  **Update the configuration:** Paste the following JSON into the file. You **must** replace the placeholder path with the **absolute path** to the Python executable in your virtual environment.

    ```json
    {
      "mcpServers": {
        "tool_sync_analyzer": {
          "command": "C:\\path\\to\\your\\project\\.venv\\Scripts\\python.exe",
          "args": [
            "-m",
            "tool_sync.main",
            "analyze"
          ],
          "env": {
            "ANONYMIZED_TELEMETRY": "False"
          },
          "disabled": false,
          "timeout": 3600
        }
      }
    }
    ```

    **Configuration Notes:**
    - **`command`**: This **must** be the full, absolute path to your Python executable. On Windows, use double backslashes (`\\`). To find the path, activate your virtual environment and run `where python` (Windows) or `which python` (Linux/macOS).
    - **`env`**: This block is important. `ANONYMIZED_TELEMETRY: "False"` prevents some known stability issues with the `chromadb` dependency.
    - **`timeout`**: Increasing the timeout to `3600` seconds can help prevent the server from stopping during long-running tasks like indexing.

4.  **Restart VS Code:** It's good practice to restart VS Code to ensure Cline picks up the new configuration.

#### Step 2: Verify the Connection

After restarting VS Code, open the Cline chat. Type `@` and a list of available tools should appear. If you see **`@tool_sync_analyzer`** in the list, the connection was successful!

#### Step 3: Index Your Knowledge Base

Before you can ask questions, the server needs to build its knowledge base. With the new version, you can index **multiple folders**, including your work items, source code, and automated tests.

In the Cline chat, send a command listing all the paths you want to index. **Paths can be absolute or relative.**

**Example for indexing work items and source code:**
> @tool_sync_analyzer index_documents paths=['work_items/', 'src/', 'tests/']

**Example using absolute paths (useful if running `tool_sync` from a different directory):**
> @tool_sync_analyzer index_documents paths=['D:\\my_project\\work_items', 'D:\\my_project\\src']

You should receive a success message like: `"Successfully indexed all provided paths. The knowledge base is ready."`

This makes the analysis engine much more powerful, as it can now answer questions about your source code and tests in addition to your work items. It also allows the `tool_sync` server to be run from anywhere, as long as you provide absolute paths to the content you want to analyze.

#### Step 4: Ask Questions!

Now you can query your knowledge base. Ask questions related to the content of your work item files.

Example prompts for Cline:
- `@tool_sync_analyzer query_documents question='What is the most common cause of login errors?'`
- `@tool_sync_analyzer query_documents question='Summarize all defects related to the new API'`

The server will respond with the most relevant documents it found, providing rich, project-specific context for your questions.
